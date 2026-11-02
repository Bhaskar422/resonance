"""Rescan comparison on two synthetic runs (before: strong imbalance, after: mostly fixed)."""

import pytest

from resonance.compare import compare_runs, verdict_from
from resonance.io import write_video
from resonance.pipeline import AnalyzeOptions, analyze
from resonance.synthetic import Vibration, make_vibrating_clip


def _run(tmp, name, amp):
    clip = make_vibrating_clip(duration_s=2.0, target_vibrations=[Vibration(19.0, amp, 0.0), Vibration(38.0, amp / 4, 0.0)], seed=1)
    src = write_video(tmp / f"{name}.mp4", clip.frames, clip.fps, crf=0)
    analyze(src, AnalyzeOptions(out_root=tmp / "out", run_name=name, mask_array=clip.target_mask))
    return tmp / "out" / name


def test_rescan_reports_the_reduction(tmp_path):
    before = _run(tmp_path, "before", 0.4)
    after = _run(tmp_path, "after", 0.06)
    r = compare_runs(before, after, ask_spark=False)
    assert r["fault_frequency_hz"] == pytest.approx(19.0, abs=0.2)
    assert r["fundamental"]["change_pct"] == pytest.approx(-85.0, abs=5.0)
    assert r["verdict"] == "resolved"
    assert [h["order"] for h in r["harmonics"]] == [1, 2]
    assert not r["warnings"]
    # RMS of a sine is amplitude/sqrt(2): 0.4 px at 1x (+0.1 at 2x) -> about 0.29 px
    assert r["rms_displacement"]["before_px"] == pytest.approx(0.29, rel=0.1)
    assert (after / "compare.png").stat().st_size > 0


def test_verdict_thresholds():
    assert [verdict_from(x) for x in (-80, -50, 0, 50)] == ["resolved", "improved", "no_change", "worse"]
