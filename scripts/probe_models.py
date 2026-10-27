"""Probe 0 (free): confirm the API key works and list the models it can use.

    uv run python scripts/probe_models.py
"""

from resonance.api import get_client

client = get_client()
for m in sorted(client.models.list(), key=lambda m: m.id):
    flag = "  (Contributor mode: do not use)" if m.id.endswith("-contributor") else ""
    print(f"{m.id}{flag}")
