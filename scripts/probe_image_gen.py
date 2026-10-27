"""Probe 3: Muse Image generation. Costs $0.01 per image.

    uv run python scripts/probe_image_gen.py "a desk fan on a wooden table" --out samples/fan.png

Prints the raw response (base64 truncated) and usage, and saves the image.
"""

import argparse
import base64
import json
from pathlib import Path

from resonance.api import CostLedger, check_model, get_client

ap = argparse.ArgumentParser()
ap.add_argument("prompt")
ap.add_argument("--out", type=Path, default=Path("out/probes/image.png"))
ap.add_argument("--size", default="1920x1080", help="only the aspect ratio is used")
ap.add_argument("--reasoning", choices=["low", "high"], default="low")
args = ap.parse_args()

client = get_client()
resp = client.images.generate(
    model=check_model("muse-image-1.0"),
    prompt=args.prompt,
    n=1,
    size=args.size,
    output_format="png",
    extra_body={"reasoning_strength": args.reasoning},
)
d = resp.model_dump(exclude_none=True)
for item in d.get("data", []):
    if "b64_json" in item:
        item["b64_json"] = item["b64_json"][:60] + f"... ({len(item['b64_json'])} chars)"
print(json.dumps(d, indent=2))

cost = CostLedger().record("muse-image-1.0", "images/generations", resp.usage, {"images": len(resp.data)}, note=args.prompt[:80])
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_bytes(base64.b64decode(resp.data[0].b64_json))
print(f"saved {args.out}, est. ${cost:.4f}")
