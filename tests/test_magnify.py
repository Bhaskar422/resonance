import numpy as np
import pytest

from resonance import frequency as fq
from resonance.magnify import MagnifyConfig, MaskedMagnifier, level_alphas
from resonance.synthetic import Vibration, make_vibrating_clip

FS = 240.0
SETTLE = int(0.25 * FS)  # skip the band-pass filter's start-up


@pytest.fixture(scope="module")
def clip():
    # In-band 12 Hz and out-of-band 40 Hz motion on the target, 41 Hz on the distractor.
    return make_vibrating_clip(
        fps=FS,
        duration_s=2.0,
        target_vibrations=[Vibration(12.0, 0.1, 0.0), Vibration(40.0, 0.1, 0.0, 1.0)],
        seed=3,
    )


@pytest.fixture(scope="module")
def magnified(clip):
    cfg = MagnifyConfig.around(12.0, FS, alpha=10.0)
    mm = MaskedMagnifier(clip.target_mask.shape, clip.target_mask, cfg)
    return np.concatenate([mm.process(clip.frames[i : i + 64]) for i in range(0, len(clip.frames), 64)])


def _amp_at(frames, mask, f):
    spec = fq.amplitude_spectrum(fq.translation_signal(frames[SETTLE:], mask), FS)
    return fq.peak_near(spec, f, 1.0).amplitude


def test_in_band_motion_is_amplified_and_out_of_band_is_not(clip, magnified):
    gain_in = _amp_at(magnified, clip.target_mask, 12.0) / _amp_at(clip.frames, clip.target_mask, 12.0)
    gain_out = _amp_at(magnified, clip.target_mask, 40.0) / _amp_at(clip.frames, clip.target_mask, 40.0)
    assert 5.0 < gain_in < 14.0
    assert 0.6 < gain_out < 1.5


def test_magnified_video_still_measures_the_right_frequency(clip, magnified):
    spec = fq.amplitude_spectrum(fq.translation_signal(magnified[SETTLE:], clip.target_mask), FS)
    assert fq.dominant_peak(spec).freq_hz == pytest.approx(12.0, abs=0.3)


def test_pixels_outside_the_mask_are_untouched(clip, magnified):
    cfg = MagnifyConfig.around(12.0, FS, alpha=10.0)
    mm = MaskedMagnifier(clip.target_mask.shape, clip.target_mask, cfg)
    outside = mm.soft == 0
    assert np.array_equal(magnified[:, outside], clip.frames[:, outside])
    # The distractor (outside the mask) keeps its original motion.
    ratio = _amp_at(magnified, clip.distractor_mask, 41.0) / _amp_at(clip.frames, clip.distractor_mask, 41.0)
    assert ratio == pytest.approx(1.0, abs=0.02)


def test_chunked_streaming_matches_single_pass(clip):
    cfg = MagnifyConfig.around(12.0, FS, alpha=10.0)
    frames = clip.frames[:150]
    whole = MaskedMagnifier(frames.shape[1:3], clip.target_mask, cfg).process(frames)
    mm = MaskedMagnifier(frames.shape[1:3], clip.target_mask, cfg)
    chunked = np.concatenate([mm.process(frames[i : i + 37]) for i in range(0, len(frames), 37)])
    assert np.abs(whole.astype(int) - chunked.astype(int)).max() <= 1


def test_band_is_clipped_below_nyquist_and_levels_taper():
    cfg = MagnifyConfig.around(110.0, 240.0)
    assert cfg.high_hz < 120.0
    alphas = level_alphas((256, 256), 6, cfg)
    assert alphas[0] == 0.0 and alphas[-1] == 0.0
    assert max(alphas) <= cfg.alpha
