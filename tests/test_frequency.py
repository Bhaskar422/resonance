import numpy as np
import pytest

from resonance import frequency as fq
from resonance.synthetic import Vibration, make_vibrating_clip


@pytest.fixture(scope="module")
def clip():
    return make_vibrating_clip(duration_s=2.0)


def test_spectrum_recovers_frequency_and_amplitude_of_a_sine():
    fs, f, a = 240.0, 17.3, 0.25
    t = np.arange(int(4 * fs)) / fs
    rng = np.random.default_rng(1)
    x = a * np.sin(2 * np.pi * f * t) + 0.02 * rng.standard_normal(t.size) + 0.1 * t  # noise + drift
    peak = fq.dominant_peak(fq.amplitude_spectrum(x, fs))
    assert peak.freq_hz == pytest.approx(f, abs=0.05)
    assert peak.amplitude == pytest.approx(a, rel=0.05)
    assert peak.snr > 20


def test_lucas_kanade_measures_subpixel_vibration_inside_mask(clip):
    d = fq.translation_signal(clip.frames, clip.target_mask)
    truth = clip.target_displacement - clip.target_displacement[0]
    # Per-frame displacement error well under a tenth of a pixel.
    assert np.sqrt(np.mean((d - truth) ** 2)) < 0.03

    spec = fq.amplitude_spectrum(d, clip.fps)
    peak = fq.dominant_peak(spec)
    assert peak.freq_hz == pytest.approx(17.0, abs=0.25)
    assert peak.amplitude == pytest.approx(0.3, rel=0.15)

    harm = fq.harmonics(spec, peak.freq_hz)
    assert harm[1].present and harm[1].peak.freq_hz == pytest.approx(34.0, abs=0.3)
    assert fq.principal_direction_deg(d) == pytest.approx(30.0, abs=3.0)


def test_distractor_outside_mask_does_not_leak_in(clip):
    spec = fq.amplitude_spectrum(fq.translation_signal(clip.frames, clip.target_mask), clip.fps)
    near_41 = fq.peak_near(spec, 41.0, 1.0)
    assert near_41.snr < 3.0

    spec_d = fq.amplitude_spectrum(fq.translation_signal(clip.frames, clip.distractor_mask), clip.fps)
    assert fq.dominant_peak(spec_d).freq_hz == pytest.approx(41.0, abs=0.25)


def test_farneback_cross_check_agrees(clip):
    d = fq.farneback_signal(clip.frames[:240], clip.target_mask)
    assert fq.dominant_peak(fq.amplitude_spectrum(d, clip.fps)).freq_hz == pytest.approx(17.0, abs=0.5)


def test_large_motion_needs_refinement_iterations():
    clip = make_vibrating_clip(duration_s=1.0, target_vibrations=[Vibration(12.0, 1.5, 0.0)], distractor_vibrations=[])
    d = fq.translation_signal(clip.frames, clip.target_mask, iterations=4)
    amp = fq.dominant_peak(fq.amplitude_spectrum(d, clip.fps)).amplitude
    assert amp == pytest.approx(1.5, rel=0.1)


def test_resample_uniform_handles_jittered_timestamps():
    rng = np.random.default_rng(2)
    t = np.cumsum(rng.uniform(0.8, 1.2, 2000)) / 240.0  # VFR-like jitter around 240 fps
    x = np.sin(2 * np.pi * 20.0 * t)
    assert not fq.is_uniform(t)
    tu, xu, fs = fq.resample_uniform(t, x)
    assert fq.is_uniform(tu)
    assert fs == pytest.approx(240.0, rel=0.02)
    assert fq.dominant_peak(fq.amplitude_spectrum(xu, fs)).freq_hz == pytest.approx(20.0, abs=0.1)


def test_harmonics_above_nyquist_are_reported_as_missing():
    fs = 100.0
    t = np.arange(400) / fs
    spec = fq.amplitude_spectrum(np.sin(2 * np.pi * 20.0 * t), fs)
    harm = fq.harmonics(spec, 20.0, n_max=4)
    assert harm[0].present and harm[1].peak is not None
    assert harm[2].peak is None and harm[3].peak is None


def test_textureless_mask_is_rejected():
    frames = np.full((5, 64, 64), 128, np.uint8)
    mask = np.ones((64, 64), bool)
    with pytest.raises(ValueError):
        fq.translation_signal(frames, mask)
