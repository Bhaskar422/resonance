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


def test_fast_moving_parts_are_excluded_from_the_mask(clip):
    # Inside the target, a patch whose texture changes completely every frame (like a fan
    # blade sweeping past behind a guard).
    frames = clip.frames.copy()
    rng = np.random.default_rng(5)
    ys, xs = np.nonzero(clip.target_mask)
    y0, x0 = ys.min() + 10, xs.min() + 10
    patch = (slice(y0, y0 + 40), slice(x0, x0 + 30))
    for f in frames:
        f[patch] = rng.integers(60, 220, (40, 30, 1), dtype=np.uint8)

    fast = fq.fast_motion_mask(frames, clip.target_mask)
    assert fast[patch].mean() > 0.95
    assert fast[clip.target_mask].mean() < 0.35  # the vibrating texture itself is kept

    spec = fq.amplitude_spectrum(fq.translation_signal(frames, clip.target_mask & ~fast), clip.fps)
    assert fq.dominant_peak(spec).freq_hz == pytest.approx(17.0, abs=0.25)
    assert fq.dominant_peak(spec).amplitude == pytest.approx(0.3, rel=0.15)


def test_textureless_mask_is_rejected():
    frames = np.full((5, 64, 64), 128, np.uint8)
    mask = np.ones((64, 64), bool)
    with pytest.raises(ValueError):
        fq.translation_signal(frames, mask)


def test_tiny_or_off_frequency_lines_are_not_called_harmonics():
    fs = 240.0
    t = np.arange(int(3 * fs)) / fs
    rng = np.random.default_rng(4)
    x = (
        0.25 * np.sin(2 * np.pi * 17.0 * t)
        + 0.08 * np.sin(2 * np.pi * 34.0 * t)  # real 2x harmonic
        + 0.0005 * np.sin(2 * np.pi * 68.0 * t)  # 0.2 % of 1x: negligible
        + 0.01 * np.sin(2 * np.pi * 103.0 * t)  # compression sideband at fs/2 - f0, near 6x = 102
        + 0.0002 * rng.standard_normal(t.size)
    )
    harm = fq.harmonics(fq.amplitude_spectrum(x, fs), 17.0)
    assert [h.order for h in harm if h.present] == [1, 2]


def test_window_sidelobes_are_not_listed_as_peaks():
    fs = 240.0
    t = np.arange(int(2 * fs)) / fs  # 2 s: sidelobes ~1.25 Hz either side of 19 Hz
    x = 0.5 * np.sin(2 * np.pi * 19.0 * t) + 0.15 * np.sin(2 * np.pi * 38.0 * t)
    x += 1e-4 * np.random.default_rng(6).standard_normal(t.size)
    freqs = [p.freq_hz for p in fq.top_peaks(fq.amplitude_spectrum(x, fs))]
    assert freqs[:2] == pytest.approx([19.0, 38.0], abs=0.05)
    assert not any(15.0 < f < 18.5 or 19.5 < f < 23.0 for f in freqs)


def test_dropped_frames_keep_the_true_frequency():
    # A phone in low light keeps 2 of every 3 frames of its 240 Hz clock. A 70 Hz tone is
    # above half the average rate (80 fps after drops would be fine, but interpolation is not).
    fs, f, a = 240.0, 70.0, 0.05
    t = np.arange(int(10 * fs)) / fs
    t = t[np.arange(t.size) % 3 != 2]
    x = a * np.sin(2 * np.pi * f * t) + 0.002 * np.random.default_rng(2).standard_normal(t.size)
    for cut in (t, t[:-1], t[1:]):  # odd and even numbers of gaps
        assert fq.clock_rate(cut) == pytest.approx(fs, rel=1e-6)
    spec = fq.nonuniform_spectrum(t, x)
    peak = fq.dominant_peak(spec)
    assert spec.nyquist == pytest.approx(120.0)
    assert peak.freq_hz == pytest.approx(f, abs=0.02)
    assert peak.amplitude == pytest.approx(a, rel=0.05)
    # Interpolating onto a uniform grid would have smeared it (the old behaviour).
    _, xu, fsu = fq.resample_uniform(t, x)
    assert fq.dominant_peak(fq.amplitude_spectrum(xu, fsu)).amplitude < 0.7 * a


def test_nonuniform_spectrum_matches_fft_on_even_samples():
    fs = 240.0
    t = np.arange(960) / fs
    x = 0.3 * np.sin(2 * np.pi * 17.0 * t)
    a, b = fq.amplitude_spectrum(x, fs), fq.nonuniform_spectrum(t, x, fs)
    assert fq.dominant_peak(b).freq_hz == pytest.approx(fq.dominant_peak(a).freq_hz, abs=0.01)
    assert fq.dominant_peak(b).amplitude == pytest.approx(fq.dominant_peak(a).amplitude, rel=0.01)


def test_light_flicker_is_not_measured_as_motion(clip):
    # 100 Hz mains flicker with rolling-shutter banding: brightness gain changing per frame and
    # down the frame. Real motion must still come out right, with nothing at the flicker rate.
    t = np.arange(len(clip.frames)) / clip.fps
    rows = np.linspace(-1, 1, clip.frames[0].shape[0]).reshape(-1, *[1] * (clip.frames[0].ndim - 1))
    flicker = [np.clip(f.astype(np.float32) * (1 + 0.25 * np.sin(2 * np.pi * 100 * ti) * (1 + 0.5 * rows)) + 6 * np.sin(2 * np.pi * 100 * ti), 0, 255).astype(np.float32)
               for f, ti in zip(clip.frames, t)]
    d = fq.translation_signal(flicker, clip.target_mask)
    truth = clip.target_displacement - clip.target_displacement[0]
    assert np.sqrt(np.mean((d - truth) ** 2)) < 0.05
    spec = fq.amplitude_spectrum(d, clip.fps)
    assert fq.dominant_peak(spec).freq_hz == pytest.approx(17.0, abs=0.25)
    at_flicker = fq.peak_near(spec, 100.0, 1.0)
    assert at_flicker is None or at_flicker.amplitude < 0.02
