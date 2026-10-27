"""Segment Anything Model 3.1 on Meta Model API.

SAM 3.1 runs over the Responses API (https://dev.meta.ai/docs/sam/overview): one user
message holding a short noun phrase plus an ``input_image`` or ``input_video`` part. Results
stream back as a special-token text grammar (https://dev.meta.ai/docs/sam/reading-segmentation),
which is decoded here with Meta's official ``meta_sam_parser``. Each mask arrives box-local;
:class:`Detection` keeps it that way and expands to a full-frame mask on demand, so a tracked
1,000-frame clip does not hold 1,000 full-resolution masks.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from meta_sam_parser import CompletedOutcome, decode_mask_to_raster, image_segmentation_format, video_segmentation_format

from resonance.api import APIError, CostLedger, check_model

MODEL = "sam-3.1"


@dataclass
class Detection:
    object_id: str
    box: tuple[int, int, int, int]  # left, top, right, bottom (half-open), source pixels
    local_mask: np.ndarray  # (h, w) bool raster covering the box
    confidence: float | None
    frame_index: int | None

    @property
    def area(self) -> int:
        return int(self.local_mask.sum())

    def full_mask(self, frame_shape: tuple[int, int]) -> np.ndarray:
        h, w = frame_shape
        out = np.zeros((h, w), bool)
        l, t, r, b = self.box
        local = self.local_mask
        if local.shape != (b - t, r - l):
            local = cv2.resize(local.astype(np.uint8), (r - l, b - t), interpolation=cv2.INTER_NEAREST).astype(bool)
        # Clip to the frame in case a box touches the border.
        y0, x0 = max(t, 0), max(l, 0)
        y1, x1 = min(b, h), min(r, w)
        out[y0:y1, x0:x1] = local[y0 - t : y1 - t, x0 - l : x1 - l]
        return out

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "box": list(self.box),
            "area_px": self.area,
            "confidence": self.confidence,
            "frame_index": self.frame_index,
        }


def _source_size(raw: str) -> tuple[int, int] | None:
    m = re.search(r"<\|box;[^|]*?w=(\d+);h=(\d+)", raw)
    return (int(m.group(2)), int(m.group(1))) if m else None


def parse_output(raw: str, media: str) -> list[Detection]:
    """Decode SAM output text into detections (box-local masks)."""
    fmt = image_segmentation_format() if media == "image" else video_segmentation_format()
    parser = fmt.create_parser()
    parser.push(raw if raw.endswith("\n") or not raw else raw + "\n")
    result = parser.finish(CompletedOutcome()).result
    errors = [d for d in result.diagnostics if str(d.severity).lower().endswith("error")]
    if errors:
        raise APIError(f"SAM output could not be parsed: {errors[0].message}")
    dets = []
    for rec in result.records:
        if rec.kind != "mask":
            continue
        raster = np.frombuffer(decode_mask_to_raster(rec.mask), np.uint8).reshape(rec.mask.height, rec.mask.width).astype(bool)
        b = rec.bounds
        dets.append(
            Detection(
                object_id=rec.object_id,
                box=(int(b.left), int(b.top), int(b.right), int(b.bottom)),
                local_mask=raster,
                confidence=rec.confidence,
                frame_index=rec.frame.frame_index if rec.frame else None,
            )
        )
    return dets


def image_data_url(frame_bgr: np.ndarray, quality: int = 95) -> str:
    ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise APIError("could not encode frame as JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def _stream(client, body: dict) -> tuple[str, object]:
    """Run a streaming Responses request; return the output text and the usage object."""
    text, usage = [], None
    with client.responses.create(stream=True, **body) as stream:
        for event in stream:
            kind = getattr(event, "type", "")
            if kind == "response.output_text.delta":
                text.append(event.delta)
            elif kind == "response.completed":
                usage = getattr(event.response, "usage", None)
            elif kind in ("response.failed", "response.incomplete", "error"):
                detail = getattr(getattr(event, "response", None), "error", None) or getattr(event, "message", "")
                raise APIError(f"SAM request ended with {kind}: {detail}")
    return "".join(text), usage


def _request(prompt: str, media_part: dict, include_confidence: bool, extra_meta: dict | None = None) -> dict:
    meta = {"mask_encoding": "one_bit", "include_confidence": "true" if include_confidence else "false"}
    meta.update(extra_meta or {})
    return {
        "model": check_model(MODEL),
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}, media_part]}],
        "metadata": meta,
    }


@dataclass
class SamResult:
    detections: list[Detection]
    raw: str
    usage: dict
    cost_usd: float | None
    source_size: tuple[int, int] | None  # (h, w) SAM reports for the media


def segment_image(client, frame_bgr: np.ndarray, prompt: str, *, ledger: CostLedger | None = None, include_confidence: bool = True) -> SamResult:
    body = _request(prompt, {"type": "input_image", "image_url": image_data_url(frame_bgr)}, include_confidence)
    raw, usage = _stream(client, body)
    cost = ledger.record(MODEL, "responses:image", usage, {"images": 1}, note=prompt) if ledger else None
    dets = parse_output(raw, "image") if raw.strip() else []
    size = _source_size(raw)
    if size and size != frame_bgr.shape[:2]:
        raise APIError(f"SAM reported a {size} source but we sent {frame_bgr.shape[:2]}")
    usage_d = usage.model_dump(exclude_none=True) if hasattr(usage, "model_dump") else {}
    return SamResult(dets, raw, usage_d, cost, size)


def upload_video(client, path: str | Path) -> str:
    with open(path, "rb") as f:
        return client.files.create(file=f, purpose="user_data").id


def segment_video(
    client, file_id: str, prompt: str, *, n_frames: int, ledger: CostLedger | None = None, include_confidence: bool = True
) -> SamResult:
    body = _request(prompt, {"type": "input_video", "file_id": file_id}, include_confidence)
    raw, usage = _stream(client, body)
    cost = ledger.record(MODEL, "responses:video", usage, {"video_frames": n_frames}, note=prompt) if ledger else None
    dets = parse_output(raw, "video") if raw.strip() else []
    usage_d = usage.model_dump(exclude_none=True) if hasattr(usage, "model_dump") else {}
    return SamResult(dets, raw, usage_d, cost, _source_size(raw))


def select_mask(detections: list[Detection], frame_shape: tuple[int, int], how: str = "largest") -> np.ndarray:
    """Pick the mask to analyse: the largest detection, the most confident, or the union of all."""
    if not detections:
        raise APIError("SAM found nothing matching the prompt; try a more concrete noun phrase")
    if how == "all":
        return np.logical_or.reduce([d.full_mask(frame_shape) for d in detections])
    if how == "confident":
        best = max(detections, key=lambda d: (d.confidence or 0.0, d.area))
    elif how == "largest":
        best = max(detections, key=lambda d: d.area)
    else:
        raise ValueError(f"unknown selection {how!r}")
    return best.full_mask(frame_shape)
