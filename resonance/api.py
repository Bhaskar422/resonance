"""Meta Model API client and a cost ledger for every call.

Meta Model API is OpenAI-SDK compatible (https://dev.meta.ai/docs/sdks). Every request made
through this module is appended to ``out/costs.jsonl`` with its raw usage and an estimated
cost, using the published prices (https://dev.meta.ai/docs/pricing-rate-limits).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_URL = "https://api.meta.ai/v1"
DEFAULT_LEDGER = Path("out/costs.jsonl")

# USD. Token prices are per 1M tokens (Standard mode).
PRICES: dict[str, dict[str, float]] = {
    "muse-spark-1.3": {"input": 1.25, "cached_input": 0.15, "output": 4.25},
    "muse-spark-1.2": {"input": 1.25, "cached_input": 0.15, "output": 4.25},
    "muse-spark-1.1": {"input": 1.25, "cached_input": 0.15, "output": 4.25},
    "muse-wonder-1.0": {"input": 4.00, "cached_input": 0.20, "output": 20.00},
    "sam-3.1": {"image": 2.50 / 1000, "video_frame": 0.20 / 1000, "min_video_frames": 50},
    "muse-image-1.0": {"image": 0.01},
    "muse-voice-transcribe-1.0": {"audio_hour": 0.18},
}


class APIError(RuntimeError):
    pass


def check_model(model: str) -> str:
    # Contributor-mode models let Meta train on what we send; this project never uses them.
    if model.endswith("-contributor"):
        raise APIError(f"{model} is a Contributor-mode model; use the Standard-mode model instead")
    return model


def get_client(timeout_s: float = 600.0):
    from openai import OpenAI

    load_dotenv()
    key = os.environ.get("META_API_KEY")
    if not key:
        raise APIError("META_API_KEY is not set; copy .env.example to .env and add your key")
    return OpenAI(base_url=BASE_URL, api_key=key, timeout=timeout_s, max_retries=3)


def _usage_dict(usage) -> dict:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump(exclude_none=True)
    return dict(usage)


def estimate_cost(model: str, usage: dict, units: dict | None = None) -> float | None:
    """Estimated USD for one call. ``units`` carries non-token quantities
    (``images``, ``video_frames``, ``audio_seconds``) when the usage object lacks them."""
    p = PRICES.get(model)
    if p is None:
        return None
    units = units or {}
    if model == "sam-3.1":
        # SAM reports what it billed: video_frames_processed or images_processed.
        frames = usage.get("video_frames_processed") or units.get("video_frames")
        if frames:
            return max(frames, p["min_video_frames"]) * p["video_frame"]
        return (usage.get("images_processed") or units.get("images", 1)) * p["image"]
    if model == "muse-image-1.0":
        return units.get("images", 1) * p["image"]
    if model == "muse-voice-transcribe-1.0":
        return units.get("audio_seconds", 0) / 3600 * p["audio_hour"]
    inp = usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
    out = usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0) or 0
    return ((inp - cached) * p["input"] + cached * p["cached_input"] + out * p["output"]) / 1e6


@dataclass
class CostLedger:
    path: Path = DEFAULT_LEDGER
    run_id: str | None = None

    def __post_init__(self):
        self.path = Path(self.path)
        self.run_total = 0.0
        self.calls: list[dict] = []

    def record(self, model: str, endpoint: str, usage=None, units: dict | None = None, note: str = "") -> float | None:
        u = _usage_dict(usage)
        cost = estimate_cost(model, u, units)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "run": self.run_id,
            "model": model,
            "endpoint": endpoint,
            "usage": u,
            "units": units or {},
            "est_cost_usd": None if cost is None else round(cost, 6),
            "note": note,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        self.calls.append(entry)
        self.run_total += cost or 0.0
        return cost

    def all_time_total(self) -> float:
        if not self.path.exists():
            return 0.0
        total = 0.0
        for line in self.path.read_text().splitlines():
            if line.strip():
                total += json.loads(line).get("est_cost_usd") or 0.0
        return total
