"""The clip check, and the CLI's server client against the real app (no network)."""

import pytest
from fastapi.testclient import TestClient

from resonance import clipcheck, remote, server
from resonance.io import write_video
from resonance.pipeline import AnalyzeOptions, analyze
from resonance.synthetic import make_vibrating_clip


@pytest.fixture(scope="module")
def clip():
    return make_vibrating_clip(duration_s=1.0)


def test_clip_check_passes_slow_motion_and_explains_the_30fps_copy(tmp_path, clip):
    good = clipcheck.check(write_video(tmp_path / "IMG_0001.mov", list(clip.frames) * 4, 240.0))
    assert good.usable and round(good.clock_fps) == 240 and good.nyquist_hz == pytest.approx(120, abs=1)
    export = clipcheck.check(write_video(tmp_path / "IMG_E0001.mov", list(clip.frames) * 2, 30.0))
    assert not export.usable
    assert any(lvl == "bad" and "All Photos Data" in msg for lvl, msg in export.findings)
    short = clipcheck.check(write_video(tmp_path / "short.mp4", clip.frames, 240.0))
    assert not short.usable and any("long" in msg for _, msg in short.findings)


@pytest.fixture
def api(tmp_path, monkeypatch, clip):
    monkeypatch.setattr(server, "OUT", tmp_path)
    monkeypatch.delenv("RESONANCE_AUTH", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    src = write_video(tmp_path / "clip.mp4", clip.frames, clip.fps, crf=0)
    analyze(src, AnalyzeOptions(out_root=tmp_path, run_name="r1", mask_array=clip.target_mask))
    browser = TestClient(server.app)
    browser.post("/api/auth/signup", json={"email": "ada@example.com", "password": "correct horse"})
    token = browser.post("/api/tokens", json={"name": "cli"}).json()["token"]
    c = remote.Client("http://testserver", token)
    c.http = TestClient(server.app)
    return c


def test_client_reads_account_runs_and_downloads(api, tmp_path):
    assert api.me()["email"] == "ada@example.com"
    assert [r["run"] for r in api.runs()] == ["r1"]
    files = api.download("r1", tmp_path / "pulled")
    assert {p.name for p in files} >= {"report.json", "side_by_side.mp4", "spectrum.png"}
    assert api.report_url("r1") == "http://testserver/app#/runs/r1"


def test_client_explains_a_missing_login(api):
    api.token = None
    with pytest.raises(remote.RemoteError, match="resonance login"):
        api.runs()


def test_saved_login_is_private_and_scoped_to_its_server(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("RESONANCE_TOKEN", raising=False)
    monkeypatch.delenv("RESONANCE_SERVER", raising=False)
    path = remote.save("https://resonance.example", "rsn_abc", "ada@example.com")
    assert path.stat().st_mode & 0o777 == 0o600
    assert remote.Client().server == "https://resonance.example" and remote.Client().token == "rsn_abc"
    assert remote.Client("http://other.example").token is None  # never sent to another server
    assert remote.forget() and not path.exists()
