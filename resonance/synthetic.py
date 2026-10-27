"""Synthetic vibrating-object clips with known ground truth.

Used to prove the frequency measurement and motion magnification before touching real
footage or spending API credits. A textured square vibrates by a sub-pixel amount at known
frequencies; a second "distractor" square outside the target mask vibrates at a different
frequency, so tests can check that analysis really stays inside the mask.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class Vibration:
    """One sinusoidal motion component: amplitude in pixels along a direction in degrees."""

    freq_hz: float
    amplitude_px: float
    direction_deg: float = 0.0
    phase_rad: float = 0.0


@dataclass
class SyntheticClip:
    frames: np.ndarray  # (T, H, W, 3) uint8 BGR
    fps: float
    timestamps: np.ndarray  # (T,) seconds
    target_mask: np.ndarray  # (H, W) bool, footprint of the target square at rest
    distractor_mask: np.ndarray  # (H, W) bool
    target_displacement: np.ndarray  # (T, 2) true (dx, dy) in pixels
    target_vibrations: list[Vibration] = field(default_factory=list)
    distractor_vibrations: list[Vibration] = field(default_factory=list)


def _smooth_texture(shape: tuple[int, int], rng: np.random.Generator, sigma: float, lo: float, hi: float) -> np.ndarray:
    tex = cv2.GaussianBlur(rng.standard_normal(shape).astype(np.float32), (0, 0), sigma)
    tex = (tex - tex.min()) / (np.ptp(tex) + 1e-9)
    return lo + (hi - lo) * tex


def _displacement(t: np.ndarray, vibrations: list[Vibration]) -> np.ndarray:
    d = np.zeros((t.size, 2), dtype=np.float64)
    for v in vibrations:
        s = v.amplitude_px * np.sin(2 * np.pi * v.freq_hz * t + v.phase_rad)
        theta = np.deg2rad(v.direction_deg)
        d[:, 0] += s * np.cos(theta)
        d[:, 1] += s * np.sin(theta)
    return d


def _square_layer(
    size: tuple[int, int], rect: tuple[int, int, int, int], rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Textured square and its soft-edged alpha, both full-frame float32."""
    h, w = size
    x, y, sw, sh = rect
    tex = np.zeros((h, w), np.float32)
    tex[y : y + sh, x : x + sw] = _smooth_texture((sh, sw), rng, sigma=2.5, lo=90, hi=230)
    alpha = np.zeros((h, w), np.float32)
    alpha[y : y + sh, x : x + sw] = 1.0
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.0)
    return tex, alpha


def _shift(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    # Cubic-spline shift. OpenCV's INTER_CUBIC warp over-shifts sub-pixel motion by ~14 %,
    # which would corrupt the ground truth; the spline shift is accurate to ~1 %.
    return ndimage.shift(img, (dy, dx), order=3, mode="nearest")


def make_vibrating_clip(
    *,
    fps: float = 240.0,
    duration_s: float = 2.0,
    size: tuple[int, int] = (192, 256),
    target_vibrations: list[Vibration] | None = None,
    distractor_vibrations: list[Vibration] | None = None,
    noise_sigma: float = 1.0,
    timestamps: np.ndarray | None = None,
    seed: int = 0,
) -> SyntheticClip:
    """Render a clip of a textured square vibrating at known frequencies.

    Defaults: target at 17 Hz (0.3 px) with a 34 Hz harmonic (0.1 px), the regime of a desk
    fan with an imbalanced blade; distractor at 41 Hz (0.4 px). Pass ``timestamps`` to
    simulate variable frame rate; otherwise frames are uniformly spaced at ``fps``.
    """
    if target_vibrations is None:
        target_vibrations = [Vibration(17.0, 0.3, 30.0), Vibration(34.0, 0.1, 30.0, 0.7)]
    if distractor_vibrations is None:
        distractor_vibrations = [Vibration(41.0, 0.4, 90.0)]

    rng = np.random.default_rng(seed)
    h, w = size
    t = np.arange(int(round(fps * duration_s))) / fps if timestamps is None else np.asarray(timestamps, float)

    background = _smooth_texture((h, w), rng, sigma=6.0, lo=40, hi=80)
    target_rect = (w // 8, h // 4, w // 3, h // 2)
    distractor_rect = (w * 5 // 8, h // 4, w // 4, h // 3)
    target_tex, target_alpha = _square_layer(size, target_rect, rng)
    distractor_tex, distractor_alpha = _square_layer(size, distractor_rect, rng)

    d_target = _displacement(t, target_vibrations)
    d_distractor = _displacement(t, distractor_vibrations)

    # Shift only a padded window around each square: same result, far less work.
    pad = 8
    layers = []
    for rect, tex, alpha, d in ((target_rect, target_tex, target_alpha, d_target), (distractor_rect, distractor_tex, distractor_alpha, d_distractor)):
        x, y, sw, sh = rect
        win = (slice(max(y - pad, 0), y + sh + pad), slice(max(x - pad, 0), x + sw + pad))
        layers.append((win, tex[win], alpha[win], d))

    frames = np.empty((t.size, h, w, 3), np.uint8)
    for i in range(t.size):
        img = background.copy()
        for win, tex, alpha, d in layers:
            a = _shift(alpha, d[i, 0], d[i, 1])
            img[win] = img[win] * (1 - a) + _shift(tex, d[i, 0], d[i, 1]) * a
        img += rng.normal(0.0, noise_sigma, img.shape).astype(np.float32)
        frames[i] = np.clip(np.rint(img), 0, 255).astype(np.uint8)[..., None]

    def rect_mask(rect: tuple[int, int, int, int]) -> np.ndarray:
        x, y, sw, sh = rect
        m = np.zeros((h, w), bool)
        m[y : y + sh, x : x + sw] = True
        return m

    return SyntheticClip(
        frames=frames,
        fps=fps,
        timestamps=t,
        target_mask=rect_mask(target_rect),
        distractor_mask=rect_mask(distractor_rect),
        target_displacement=d_target,
        target_vibrations=list(target_vibrations),
        distractor_vibrations=list(distractor_vibrations),
    )
