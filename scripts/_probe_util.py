"""Shared helpers for the probe scripts: print raw streaming events and save them."""

from __future__ import annotations

import json
import time
from pathlib import Path

PROBE_DIR = Path("out/probes")


def dump_event(event, max_chars: int = 600) -> str:
    d = event.model_dump(exclude_none=True) if hasattr(event, "model_dump") else dict(event)
    s = json.dumps(d, default=str)
    return s if len(s) <= max_chars else s[:max_chars] + f"... (+{len(s) - max_chars} chars)"


def stream_raw(client, body: dict, label: str):
    """Stream a Responses request, printing every non-delta event in full and a sample of
    deltas. Returns (output_text, usage, path_of_saved_log)."""
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    log_path = PROBE_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{label}.jsonl"
    text, usage, n_delta = [], None, 0
    t0 = time.time()
    with client.responses.create(stream=True, **body) as stream, log_path.open("w") as log:
        for event in stream:
            log.write(json.dumps(event.model_dump(exclude_none=True), default=str) + "\n")
            kind = getattr(event, "type", "?")
            if kind == "response.output_text.delta":
                n_delta += 1
                text.append(event.delta)
                if n_delta <= 2:
                    print(f"[{time.time() - t0:6.2f}s] {kind} #{n_delta}: {event.delta[:300]!r}...")
                continue
            if kind == "response.completed":
                usage = event.response.usage
            print(f"[{time.time() - t0:6.2f}s] {dump_event(event)}")
    print(f"... {n_delta} output_text.delta events in total; raw events saved to {log_path}")
    return "".join(text), usage, log_path
