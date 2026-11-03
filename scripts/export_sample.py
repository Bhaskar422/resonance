"""Export a before/after pair of runs as the web app's built-in sample.

The marketing site and the workspace's Sample mode show this real pipeline output instead of
invented numbers. Images are re-encoded as JPEG and the video at web size.

    uv run python scripts/export_sample.py out/<before-run> out/<after-run> --machine "Desk fan"
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2

from resonance.server import SERVED_FILES, _read, _spectrum, run_created

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public" / "sample"
DATA = ROOT / "frontend" / "src" / "lib" / "sample-fan.json"


def export_run(run_dir: Path, slot: str, machine: str) -> dict:
    dest = PUBLIC / slot
    dest.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in sorted(SERVED_FILES):
        src = run_dir / name
        if not src.exists():
            continue
        if name.endswith(".png"):
            img = cv2.imread(str(src))
            scale = min(1.0, 1280 / img.shape[1])
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            out = dest / name.replace(".png", ".jpg")
            cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        elif name.endswith(".mp4"):
            out = dest / name
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale='min(1600,iw)':-2",
                 "-c:v", "libx264", "-crf", "26", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(out)],
                check=True,
            )
        else:
            continue
        files[name] = f"/sample/{slot}/{out.name}"

    report = json.loads((run_dir / "report.json").read_text())
    report["machine"] = machine
    dx = _read(run_dir / "diagnosis.json")
    return {
        "run": report["run"],
        "created": round(run_created(run_dir)),
        "input": Path(report["input"]).name,
        "prompt": report["mask"].get("prompt") or "fan",
        "machine": machine,
        "freq_hz": report["vibration"]["dominant"]["freq_hz"],
        "fault": dx["diagnosis"]["primary_fault"] if dx else None,
        "severity": dx["diagnosis"]["severity"] if dx else None,
        "thumb": files.get("key_frame.png"),
        "detail": {
            "report": report,
            "diagnosis": dx,
            "visualize": _read(run_dir / "visualize.json"),
            "compare": _read(run_dir / "compare.json"),
            "spectrum": _spectrum(run_dir),
            "files": files,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--machine", default="Desk fan")
    args = ap.parse_args()
    data = {"before": export_run(args.before, "before", args.machine), "after": export_run(args.after, "after", args.machine)}
    DATA.write_text(json.dumps(data, indent=1))
    print(f"wrote {DATA.relative_to(ROOT)} and {PUBLIC.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
