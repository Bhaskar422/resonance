"""Probe 4: Muse Spark 1.3 on an uploaded MP4 + an image, with structured output.

    uv run python scripts/probe_spark_video.py out/<run>/side_by_side.mp4 out/<run>/spectrum.png

Prints the raw response (output items, usage) so the video-input and text.format schema are
verified before the diagnosis module relies on them.
"""

import argparse
import base64
import json
import time
from pathlib import Path

from resonance.api import CostLedger, check_model, get_client

ap = argparse.ArgumentParser()
ap.add_argument("video", type=Path)
ap.add_argument("image", type=Path)
ap.add_argument("--model", default="muse-spark-1.3")
ap.add_argument("--effort", default="low")
args = ap.parse_args()

client = get_client()
t0 = time.time()
with args.video.open("rb") as f:
    file_id = client.files.create(file=f, purpose="user_data").id
print(f"uploaded {args.video} ({args.video.stat().st_size / 1e6:.1f} MB) -> {file_id} in {time.time() - t0:.1f}s")

schema = {
    "type": "object",
    "properties": {
        "left_panel": {"type": "string", "description": "What the left panel shows"},
        "right_panel": {"type": "string", "description": "What the right panel shows and how its motion differs"},
        "moving_part": {"type": "string"},
        "caption_text": {"type": "string", "description": "Text in the top caption bar, verbatim"},
        "spectrum_peak_hz": {"type": "number", "description": "Frequency of the tallest peak in the spectrum image"},
    },
    "required": ["left_panel", "right_panel", "moving_part", "caption_text", "spectrum_peak_hz"],
    "additionalProperties": False,
}
image_url = "data:image/png;base64," + base64.b64encode(args.image.read_bytes()).decode()
t0 = time.time()
resp = client.responses.create(
    model=check_model(args.model),
    input=[{
        "type": "message",
        "role": "user",
        "content": [
            {"type": "input_text", "text": "This video is a side-by-side vibration analysis of a machine (original left, motion-magnified right). The image is its vibration spectrum. Describe what you observe."},
            {"type": "input_video", "file_id": file_id},
            {"type": "input_image", "image_url": image_url},
        ],
    }],
    reasoning={"effort": args.effort},
    max_output_tokens=4000,
    text={"format": {"type": "json_schema", "name": "probe", "schema": schema, "strict": True}},
)
print(f"response in {time.time() - t0:.1f}s, status {resp.status}")
d = resp.model_dump(exclude_none=True)
for item in d.get("output", []):
    for c in item.get("content", []) or []:
        if isinstance(c.get("text"), str) and len(c["text"]) > 2000:
            c["text"] = c["text"][:2000] + "..."
print(json.dumps({k: d[k] for k in ("output", "usage") if k in d}, indent=2)[:6000])
print("output_text:", resp.output_text)
cost = CostLedger().record(args.model, "responses:video+image", resp.usage, note="probe spark video")
print(f"est. ${cost:.4f}")
