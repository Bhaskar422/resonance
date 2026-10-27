"""End-to-end pipeline on a synthetic clip, fully offline (mask given, no SAM call)."""

import json

import numpy as np
import pytest

from resonance.io import write_video
from resonance.pipeline import AnalyzeOptions, analyze
from resonance.synthetic import Vibration, make_vibrating_clip


def _phyphox_csv(path, f, fs=400.0, seconds=8.0):
    t = np.arange(int(fs * seconds)) / fs
    rng = np.random.default_rng(0)
    rows = ['"Time (s)","Linear Acceleration x (m/s^2)","Linear Acceleration y (m/s^2)","Linear Acceleration z (m/s^2)"']
    for ti in t:
        x = 0.05 * np.sin(2 * np.pi * f * ti) + 0.003 * rng.standard_normal()
        rows.append(f"{ti:.6f},{x:.6f},{0.002 * rng.standard_normal():.6f},{0.002 * rng.standard_normal():.6f}")
    path.write_text("\n".join(rows))
    return path


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pipeline")
    clip = make_vibrating_clip(duration_s=2.0, target_vibrations=[Vibration(19.0, 0.25, 0.0), Vibration(38.0, 0.08, 0.0)])
    src = write_video(tmp / "clip.mp4", clip.frames, clip.fps, crf=0)
    opts = AnalyzeOptions(out_root=tmp / "out", run_name="t", mask_array=clip.target_mask, accel_path=_phyphox_csv(tmp / "a.csv", 19.0))
    return analyze(src, opts), tmp / "out" / "t"


def test_report_has_correct_frequency_and_accel_agreement(result):
    r, _ = result
    assert r["vibration"]["dominant"]["freq_hz"] == pytest.approx(19.0, abs=0.2)
    assert [h["order"] for h in r["vibration"]["harmonics"] if h["present"]] == [1, 2]
    assert r["accelerometer"]["verifiable"]
    assert r["accelerometer"]["percent_error"] < 1.0
    assert r["api_cost_usd"]["this_run"] == 0.0
    assert r["video"]["fps"] == pytest.approx(240.0)


def test_all_outputs_are_written(result):
    r, run_dir = result
    for name in ("side_by_side.mp4", "spectrum.png", "mask_overlay.png", "mask.png", "report.json", "signals.npz"):
        assert (run_dir / name).stat().st_size > 0, name
    assert json.loads((run_dir / "report.json").read_text())["run"] == "t"
