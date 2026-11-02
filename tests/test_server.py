"""Web API smoke test on an offline synthetic run (no model calls)."""

import pytest
from fastapi.testclient import TestClient

from resonance import server
from resonance.io import write_video
from resonance.pipeline import AnalyzeOptions, analyze
from resonance.synthetic import make_vibrating_clip


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "OUT", tmp_path)
    clip = make_vibrating_clip(duration_s=1.0)
    src = write_video(tmp_path / "clip.mp4", clip.frames, clip.fps, crf=0)
    analyze(src, AnalyzeOptions(out_root=tmp_path, run_name="r1", mask_array=clip.target_mask))
    return TestClient(server.app)


def test_index_and_run_listing(client):
    assert "Resonance" in client.get("/").text
    runs = client.get("/api/runs").json()
    assert [r["run"] for r in runs] == ["r1"]
    assert runs[0]["freq_hz"] == pytest.approx(17.0, abs=0.3)


def test_run_detail_and_files(client):
    d = client.get("/api/runs/r1").json()
    assert d["report"]["run"] == "r1" and d["diagnosis"] is None
    assert client.get(d["files"]["side_by_side.mp4"]).status_code == 200


def test_paths_outside_the_run_are_refused(client):
    assert client.get("/files/r1/signals.npz").status_code == 404  # not in the served list
    assert client.get("/files/..%2F..%2Fetc/passwd").status_code == 404
    assert client.get("/api/runs/..").status_code == 404
