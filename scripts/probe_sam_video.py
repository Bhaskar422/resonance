"""Probe 2: SAM 3.1 video tracking on a short clip. Costs $0.0002 per frame (min 50).

    uv run python scripts/probe_sam_video.py samples/fan.mov --prompt "fan blade" --seconds 1

Normalizes and trims the clip (default 1 s, about 240 frames, about $0.05), uploads it with
the Files API, streams segmentation, and checks SAM's frame indexing against our own frame
count, which is what decides whether SAM tracks every frame of a 240 fps clip.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _probe_util import PROBE_DIR, stream_raw

from resonance import io as rio
from resonance import sam_client
from resonance.api import CostLedger, get_client

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--prompt", required=True)
ap.add_argument("--seconds", type=float, default=1.0)
ap.add_argument("--start", type=float, default=0.0)
args = ap.parse_args()

prep = rio.prepare(args.video, PROBE_DIR / "work", start_s=args.start, duration_s=args.seconds)
n = prep.timestamps.size
print(f"working copy {prep.width}x{prep.height}, {n} frames at {prep.fs:.2f} fps, warnings: {prep.warnings}")
print(f"expected cost: ${max(n, 50) * 0.0002:.4f}")

client = get_client()
file_id = sam_client.upload_video(client, prep.working_copy())
print("uploaded:", file_id)
body = sam_client._request(args.prompt, {"type": "input_video", "file_id": file_id}, True)
raw, usage, log_path = stream_raw(client, body, "sam_video")
cost = CostLedger().record("sam-3.1", "responses:video", usage, {"video_frames": n}, note=f"probe: {args.prompt}")

print("\nusage:", usage.model_dump(exclude_none=True) if usage else None, f"est. ${cost:.4f}")
dets = sam_client.parse_output(raw, "video") if raw.strip() else []
frames = sorted({d.frame_index for d in dets})
ids = Counter(d.object_id for d in dets)
print(f"lines with detections: {len(frames)} / {n} local frames")
if frames:
    print(f"frame index range: {frames[0]}..{frames[-1]} (local frames 0..{n - 1})")
    missing = sorted(set(range(frames[0], frames[-1] + 1)) - set(frames))
    print(f"gaps inside range: {len(missing)} {missing[:20]}")
print("object ids -> frames present:", dict(ids))
print("source size reported by SAM (h, w):", sam_client._source_size(raw), "ours:", (prep.height, prep.width))
