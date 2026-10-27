"""Probe 1: SAM 3.1 on one image. Costs $0.0025.

    uv run python scripts/probe_sam_image.py samples/fan.jpg --prompt "motor housing"
    uv run python scripts/probe_sam_image.py samples/fan.mov --frame 0 --prompt "fan guard"

Prints the raw streaming events, the usage object, the parsed detections, and saves an
overlay PNG next to the raw log in out/probes/.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cv2
import numpy as np
from _probe_util import PROBE_DIR, stream_raw

from resonance import io as rio
from resonance import sam_client
from resonance.api import CostLedger, get_client

ap = argparse.ArgumentParser()
ap.add_argument("media", help="image file, or a video (use --frame)")
ap.add_argument("--prompt", required=True)
ap.add_argument("--frame", type=int, default=0)
args = ap.parse_args()

path = Path(args.media)
frame = cv2.imread(str(path)) if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else None
if frame is None:
    prep = rio.prepare(path, PROBE_DIR / "work", duration_s=1.0)
    frame = prep.frame(args.frame)
print(f"frame {frame.shape[1]}x{frame.shape[0]}, prompt {args.prompt!r}")

client = get_client()
body = sam_client._request(args.prompt, {"type": "input_image", "image_url": sam_client.image_data_url(frame)}, True)
raw, usage, log_path = stream_raw(client, body, "sam_image")
cost = CostLedger().record("sam-3.1", "responses:image", usage, {"images": 1}, note=f"probe: {args.prompt}")

print("\nusage:", usage.model_dump(exclude_none=True) if usage else None, f"est. ${cost:.4f}")
print("source size reported by SAM (h, w):", sam_client._source_size(raw))
dets = sam_client.parse_output(raw, "image") if raw.strip() else []
print(f"{len(dets)} detection(s):")
overlay = frame.copy()
for d in dets:
    print("  ", d.to_dict())
    m = d.full_mask(frame.shape[:2])
    overlay[m] = (0.5 * overlay[m] + 0.5 * np.array([0, 200, 255])).astype(np.uint8)
    l, t, r, b = d.box
    cv2.rectangle(overlay, (l, t), (r - 1, b - 1), (0, 255, 0), 2)
out = log_path.with_suffix(".png")
cv2.imwrite(str(out), overlay)
print("overlay:", out)
