import subprocess

import numpy as np
import pytest

from resonance import frequency as fq
from resonance import io as rio
from resonance.synthetic import make_vibrating_clip


@pytest.fixture(scope="module")
def clip():
    return make_vibrating_clip(fps=240.0, duration_s=1.0)


def _measure_hz(prepared: rio.PreparedVideo, mask: np.ndarray) -> float:
    d = fq.translation_signal(prepared.iter_frames(), mask)
    n = min(len(d), prepared.timestamps.size)
    _, du, fs = fq.resample_uniform(prepared.timestamps[:n], d[:n])
    return fq.dominant_peak(fq.amplitude_spectrum(du, fs)).freq_hz


def test_true_240fps_clip_round_trips(tmp_path, clip):
    src = rio.write_video(tmp_path / "clip.mp4", clip.frames, clip.fps, crf=8)
    info = rio.probe(src)
    assert info.nominal_fps == pytest.approx(240.0)
    assert (info.width, info.height) == (256, 192)
    assert info.n_frames == len(clip.frames)

    prep = rio.prepare(src, tmp_path / "work")
    assert prep.fs == pytest.approx(240.0, rel=1e-3)
    assert prep.timestamps.size == len(clip.frames)
    assert not prep.is_vfr
    assert not prep.warnings
    assert _measure_hz(prep, clip.target_mask) == pytest.approx(17.0, abs=0.5)


def test_retimed_slowmo_is_corrected_by_capture_fps(tmp_path, clip):
    # 240 fps footage stored as a 30 fps file: plays 8x slower, so naive Hz would be 8x too low.
    src = rio.write_video(tmp_path / "retimed.mp4", clip.frames, 30.0, crf=8)
    naive = rio.prepare(src, tmp_path / "naive")
    assert naive.fs == pytest.approx(30.0, rel=1e-3)
    assert any("Record in slow motion" in w for w in naive.warnings)

    fixed = rio.prepare(src, tmp_path / "fixed", capture_fps=240.0)
    assert fixed.fs == pytest.approx(240.0, rel=1e-3)
    assert fixed.time_scale == pytest.approx(0.125, rel=1e-3)
    assert _measure_hz(fixed, clip.target_mask) == pytest.approx(17.0, abs=0.5)


def test_android_capture_fps_tag_is_detected(tmp_path, clip):
    src = rio.write_video(tmp_path / "android.mp4", clip.frames[:60], 30.0, extra_metadata={"com.android.capture.fps": "240.000000"})
    assert rio.probe(src).capture_fps == pytest.approx(240.0)
    prep = rio.prepare(src, tmp_path / "work")
    assert prep.fs == pytest.approx(240.0, rel=1e-3)
    assert any("re-timed" in w for w in prep.warnings)


def test_rotation_metadata_is_applied(tmp_path, clip):
    src = rio.write_video(tmp_path / "flat.mp4", clip.frames[:10], 240.0)
    rotated = tmp_path / "rotated.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-display_rotation", "90", "-i", str(src), "-c", "copy", str(rotated)], check=True)
    info = rio.probe(rotated)
    assert abs(info.rotation) == 90
    assert (info.width, info.height) == (192, 256)
    prep = rio.prepare(rotated, tmp_path / "work")
    assert prep.frame(0).shape[:2] == (256, 192)
    assert next(rio.iter_frames(prep.working_copy())).shape[:2] == (256, 192)


def test_variable_frame_rate_is_detected(tmp_path, clip):
    src = rio.write_video(tmp_path / "cfr.mp4", clip.frames[:120], 240.0)
    vfr = tmp_path / "vfr.mp4"
    jitter = "settb=1/240000,setpts='(N/240+0.0015*sin(N))/TB'"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", jitter, "-fps_mode", "passthrough", "-enc_time_base:v", "filter", "-video_track_timescale", "240000", str(vfr)],
        check=True,
    )
    prep = rio.prepare(vfr, tmp_path / "work")
    assert prep.is_vfr
    assert prep.fs == pytest.approx(240.0, rel=0.05)
    assert any("uneven frame timing" in w for w in prep.warnings)


def test_missing_file_raises(tmp_path):
    with pytest.raises(rio.VideoError):
        rio.probe(tmp_path / "nope.mp4")


def test_analysis_frames_are_not_re_encoded(tmp_path, clip):
    # A lossless source must measure the same sub-pixel amplitude as the raw frames; any
    # re-encode in the analysis path would shrink it (CRF 14 loses ~20 %).
    def amp(frames):
        spec = fq.amplitude_spectrum(fq.translation_signal(frames, clip.target_mask), clip.fps)
        return fq.peak_near(spec, 17.0, 1.0).amplitude

    src = rio.write_video(tmp_path / "lossless.mp4", clip.frames, clip.fps, crf=0)
    prep = rio.prepare(src, tmp_path / "work")
    assert amp(prep.iter_frames()) == pytest.approx(amp(clip.frames), rel=0.01)
