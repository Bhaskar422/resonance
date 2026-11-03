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
    c = TestClient(server.app)
    c.post("/api/auth/signup", json={"email": "admin@example.com", "password": "correct horse"})
    return c


def test_index_and_run_listing(client):
    assert "Resonance" in client.get("/").text
    runs = client.get("/api/runs").json()
    assert [r["run"] for r in runs] == ["r1"]
    assert runs[0]["freq_hz"] == pytest.approx(17.0, abs=0.3)


def test_run_detail_and_files(client):
    d = client.get("/api/runs/r1").json()
    assert d["report"]["run"] == "r1" and d["diagnosis"] is None
    spec = d["spectrum"]
    assert len(spec["amp"]) == 600 and spec["fmax"] == pytest.approx(120.0, abs=0.5)
    assert spec["amp"].index(max(spec["amp"])) * spec["fmax"] / 600 == pytest.approx(17.0, abs=0.5)
    assert client.get(d["files"]["side_by_side.mp4"]).status_code == 200


def test_paths_outside_the_run_are_refused(client):
    assert client.get("/files/r1/signals.npz").status_code == 404  # not in the served list
    assert client.get("/files/..%2F..%2Fetc/passwd").status_code == 404
    assert client.get("/api/runs/..").status_code == 404


def test_job_progress_lists_finished_stages(client):
    job = server.Job(id="j1", stage="measure", done=["upload", "prepare", "mask"])
    server._jobs[job.id] = job
    d = client.get("/api/jobs/j1").json()
    assert d["stage"] == "measure" and d["stages"] == ["upload", "prepare", "mask"]


def test_cost_ledger_and_health(client, tmp_path):
    (tmp_path / "costs.jsonl").write_text(
        '{"ts": "2026-10-27T11:01:13+0530", "run": "r1:visualize", "model": "muse-image-1.0", "endpoint": "responses:image_edit", "est_cost_usd": 0.01}\n'
        '{"ts": "2026-10-27T11:02:13+0530", "run": null, "model": "sam-3.1", "endpoint": "responses:image", "est_cost_usd": 0.0025}\n'
    )
    rows = client.get("/api/costs").json()
    assert [r["model"] for r in rows] == ["SAM 3.1", "Muse Image"]
    assert rows[1]["run_id"] == "r1" and rows[1]["endpoint"] == "image edit" and rows[0]["run_id"] is None
    assert client.get("/api/health").json()["ok"] is True


def test_diagnose_existing_run_runs_in_background(client, monkeypatch):
    import resonance.diagnose
    import resonance.visualize

    calls = []
    monkeypatch.setattr(resonance.diagnose, "diagnose", lambda run_dir, **kw: calls.append(("diagnose", run_dir.name, kw)))
    monkeypatch.setattr(resonance.visualize, "render_fix", lambda run_dir: calls.append(("visualize", run_dir.name)))
    job = client.post("/api/runs/r1/diagnose", data={"machine": "Desk fan", "visualize": "true"}).json()["job"]
    server._pool.submit(lambda: None).result()  # the single worker has finished the job
    d = client.get(f"/api/jobs/{job}").json()
    assert d["status"] == "done" and d["run"] == "r1" and d["stages"] == ["diagnose", "visualize"]
    assert calls[0][0] == "diagnose" and calls[0][2]["machine_hint"] == "Desk fan" and calls[1] == ("visualize", "r1")
    assert client.post("/api/runs/nope/diagnose").status_code == 404
