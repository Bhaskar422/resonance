"""Show the fix on the real frame with Muse Image.

Two edits of the actual key frame (not a generic illustration): one highlights where the
technician should act, at the spot Muse Spark chose; the other shows the machine in its
fixed state, from the diagnosis's own edit instruction. Both go through the Responses API
image editor (https://dev.meta.ai/docs/cookbook/image-editing-with-reasoning).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import cv2
import numpy as np

from resonance.api import CostLedger, check_model, get_client

MODEL = "muse-image-1.0"


def _key_frame(run_dir: Path, report: dict) -> Path:
    clean = run_dir / "key_frame.png"
    if clean.exists():
        return clean
    # Older runs: take the frame from the source clip.
    cap = cv2.VideoCapture(report["input"])
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return run_dir / "mask_overlay.png"
    cv2.imwrite(str(clean), frame)
    return clean


def _edit(client, image: Path, instruction: str, out: Path, ledger: CostLedger, note: str) -> Path:
    url = "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode()
    resp = client.responses.create(
        model=check_model(MODEL),
        input=[{"role": "user", "content": [{"type": "input_text", "text": instruction}, {"type": "input_image", "image_url": url}]}],
    )
    ledger.record(MODEL, "responses:image_edit", resp.usage, {"images": 1}, note=note)
    b64 = next((item.result for item in resp.output if item.type == "image_generation_call"), None)
    if not b64:
        raise RuntimeError(f"Muse Image returned no image (status {resp.status})")
    raw = base64.b64decode(b64)
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    cv2.imwrite(str(out), img)  # normalize to PNG whatever format came back
    return out


def short_label(label: str, max_chars: int = 32) -> str:
    """'fan hub / blade assembly - inspect and balance' -> 'fan hub / blade assembly'."""
    head = label.split(" - ")[0].split(";")[0].strip()
    if len(head) <= max_chars:
        return head
    words, out = head.split(), ""
    for w in words:
        if len(out) + len(w) + 1 > max_chars:
            break
        out = f"{out} {w}".strip()
    return out or head[:max_chars]


def where_to_act_instruction(dx: dict) -> str:
    ap = dx["action_point"]
    return (
        f"This is a photo of a {dx['machine']}. Highlight the part to service: {ap['label']}, located about "
        f"{ap['x'] / 10:.0f}% from the left and {ap['y'] / 10:.0f}% from the top of the photo. Draw a bright red outline "
        "around that part and a short red arrow pointing to it with a small clear label reading "
        f"\"{short_label(ap['label'])}\". Keep the photo otherwise exactly unchanged: same machine, lighting, background "
        "and framing. No people, hands or tools."
    )


def _side_by_side(left: Path, right: Path, out: Path, labels: tuple[str, str]) -> Path:
    a, b = cv2.imread(str(left)), cv2.imread(str(right))
    b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    panels = []
    for img, label in ((a, labels[0]), (b, labels[1])):
        img = img.copy()
        scale = max(img.shape[1] / 1280, 1.0)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.9 * scale, 2)
        pad = int(10 * scale)
        cv2.rectangle(img, (pad, pad), (pad + tw + 2 * pad, pad + th + 2 * pad), (24, 24, 24), -1)
        cv2.putText(img, label, (2 * pad, pad + th + pad), cv2.FONT_HERSHEY_SIMPLEX, 0.9 * scale, (240, 239, 236), 2, cv2.LINE_AA)
        panels.append(img)
    cv2.imwrite(str(out), np.hstack(panels))
    return out


def render_fix(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    report = json.loads((run_dir / "report.json").read_text())
    dx = json.loads((run_dir / "diagnosis.json").read_text())["diagnosis"]
    key = _key_frame(run_dir, report)
    ledger = CostLedger(Path(report.get("api_cost_ledger", "out/costs.jsonl")), run_id=report["run"] + ":visualize")
    client = get_client()

    where = _edit(client, key, where_to_act_instruction(dx), run_dir / "where_to_act.png", ledger, "where to act")
    fixed = _edit(client, key, dx["fix_image_prompt"], run_dir / "fixed_state.png", ledger, "fixed state")
    pair = _side_by_side(key, fixed, run_dir / "now_vs_fixed.png", ("Now", "After the fix (Muse Image)"))
    result = {
        "where_to_act": str(where),
        "fixed_state": str(fixed),
        "now_vs_fixed": str(pair),
        "prompts": {"where_to_act": where_to_act_instruction(dx), "fixed_state": dx["fix_image_prompt"]},
        "api_cost_usd": round(ledger.run_total, 4),
    }
    (run_dir / "visualize.json").write_text(json.dumps(result, indent=2))
    return result
