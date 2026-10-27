"""Motion magnification restricted to a mask.

Linear Eulerian video magnification (Wu et al., "Eulerian Video Magnification for Revealing
Subtle Changes in the World", SIGGRAPH 2012), implemented from the paper: each frame's
luminance is decomposed into a Laplacian pyramid, every level is band-pass filtered in time
around the vibration frequency, amplified, and added back. Our own implementation; no code
from the authors' reference release is used.

Two choices make it practical for phone slow-motion clips:

* Streaming. The temporal filter is a causal Butterworth band-pass whose state is carried
  between chunks, so a 10 s, 240 fps clip never has to sit in memory.
* Masked. Only a crop around the segmented part is processed, and the result is feathered
  back into the original frame. Every pixel outside the (grown) mask is left bit-identical.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy import signal as sps


@dataclass(frozen=True)
class MagnifyConfig:
    low_hz: float
    high_hz: float
    fs: float
    alpha: float = 20.0
    lambda_c: float = 16.0  # spatial wavelength (px) below which amplification is tapered
    exaggeration: float = 2.0  # boost over the paper's strict bound, as in the paper's own results
    filter_order: int = 2

    @staticmethod
    def around(freq_hz: float, fs: float, *, rel_bw: float = 0.1, min_bw_hz: float = 1.0, **kw) -> "MagnifyConfig":
        """Band of ±max(rel_bw·f, min_bw_hz) around ``freq_hz``, clipped below Nyquist."""
        half = max(rel_bw * freq_hz, min_bw_hz)
        lo = max(freq_hz - half, 0.1)
        hi = min(freq_hz + half, 0.95 * fs / 2)
        if lo >= hi:
            raise ValueError(f"cannot build a band around {freq_hz} Hz at fs={fs}")
        return MagnifyConfig(lo, hi, fs, **kw)


def _n_levels(shape: tuple[int, int], min_size: int = 8) -> int:
    return max(2, int(np.floor(np.log2(min(shape) / min_size))) + 1)


def _laplacian_pyramid(img: np.ndarray, levels: int) -> list[np.ndarray]:
    pyr, cur = [], img
    for _ in range(levels - 1):
        down = cv2.pyrDown(cur)
        pyr.append(cur - cv2.pyrUp(down, dstsize=cur.shape[::-1]))
        cur = down
    pyr.append(cur)  # low-pass residual
    return pyr


def _collapse(pyr: list[np.ndarray]) -> np.ndarray:
    cur = pyr[-1]
    for band in reversed(pyr[:-1]):
        cur = cv2.pyrUp(cur, dstsize=band.shape[::-1]) + band
    return cur


def level_alphas(shape: tuple[int, int], levels: int, cfg: MagnifyConfig) -> list[float]:
    """Per-level amplification following the paper's spatial-wavelength bound
    (1 + α)·δ < λ/8. Finest and coarsest levels are not amplified (noise and DC)."""
    lam = np.hypot(*shape) / 3.0  # representative wavelength of the coarsest band
    delta = cfg.lambda_c / 8.0 / (1.0 + cfg.alpha)
    alphas = [0.0] * levels
    for lvl in range(levels - 1, -1, -1):
        cur = (lam / delta / 8.0 - 1.0) * cfg.exaggeration
        if 0 < lvl < levels - 1:
            alphas[lvl] = float(min(cfg.alpha, max(cur, 0.0)))
        lam /= 2.0
    return alphas


class EulerianMagnifier:
    """Streaming linear Eulerian magnification of luminance for a fixed frame size."""

    def __init__(self, shape: tuple[int, int], cfg: MagnifyConfig):
        self.shape = shape
        self.cfg = cfg
        self.levels = _n_levels(shape)
        self.alphas = level_alphas(shape, self.levels, cfg)
        self.sos = sps.butter(cfg.filter_order, [cfg.low_hz, cfg.high_hz], btype="band", fs=cfg.fs, output="sos")
        self._zi: list[np.ndarray] | None = None

    def process(self, frames: np.ndarray) -> np.ndarray:
        """Magnify a chunk of (N, H, W, 3) uint8 BGR frames; call repeatedly for the next chunk."""
        if frames.shape[1:3] != self.shape:
            raise ValueError(f"expected frames of shape {self.shape}, got {frames.shape[1:3]}")
        ycc = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2YCrCb) for f in frames]).astype(np.float32)
        pyrs = [_laplacian_pyramid(y, self.levels) for y in ycc[..., 0]]

        if self._zi is None:
            # Start the filter in steady state for the first frame so there is no step transient.
            zi0 = sps.sosfilt_zi(self.sos)[:, :, None, None]
            self._zi = [zi0 * pyrs[0][lvl][None, None] for lvl in range(self.levels)]

        amplified = [[np.zeros_like(b) for b in pyrs[0]] for _ in frames]
        for lvl, a in enumerate(self.alphas):
            if a == 0.0:
                continue
            stack = np.stack([p[lvl] for p in pyrs])
            filtered, self._zi[lvl] = sps.sosfilt(self.sos, stack, axis=0, zi=self._zi[lvl])
            for i in range(len(frames)):
                amplified[i][lvl] = a * filtered[i].astype(np.float32)

        out = np.empty_like(frames)
        for i in range(len(frames)):
            ycc[i, ..., 0] += _collapse(amplified[i])
            out[i] = cv2.cvtColor(np.clip(ycc[i], 0, 255).astype(np.uint8), cv2.COLOR_YCrCb2BGR)
        return out


def soft_mask(mask: np.ndarray, grow_px: int = 6, feather_px: float = 3.0) -> np.ndarray:
    """Grown, feathered float mask in [0, 1]. Growing leaves room for magnified edges to move
    past the original boundary; feathering hides the seam."""
    m = mask.astype(np.uint8)
    if grow_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow_px + 1, 2 * grow_px + 1))
        m = cv2.dilate(m, k)
    soft = m.astype(np.float32)
    if feather_px > 0:
        soft = cv2.GaussianBlur(soft, (0, 0), feather_px)
        soft[soft < 1e-3] = 0.0  # exact zero outside, so untouched pixels stay bit-identical
    return soft


class MaskedMagnifier:
    """Magnify only inside a mask: process a crop around it, feather the result back in."""

    def __init__(self, frame_shape: tuple[int, int], mask: np.ndarray, cfg: MagnifyConfig, *, grow_px: int = 6, margin_px: int = 24):
        if mask.shape != frame_shape:
            raise ValueError("mask and frame shapes differ")
        self.soft = soft_mask(mask, grow_px)
        ys, xs = np.nonzero(self.soft)
        if ys.size == 0:
            raise ValueError("mask is empty")
        h, w = frame_shape
        y0, y1 = max(ys.min() - margin_px, 0), min(ys.max() + margin_px + 1, h)
        x0, x1 = max(xs.min() - margin_px, 0), min(xs.max() + margin_px + 1, w)
        self.window = (slice(y0, y1), slice(x0, x1))
        self.alpha_crop = self.soft[self.window][None, ..., None]
        self.magnifier = EulerianMagnifier((y1 - y0, x1 - x0), cfg)

    def process(self, frames: np.ndarray) -> np.ndarray:
        out = frames.copy()
        crop = frames[(slice(None), *self.window)]
        mag = self.magnifier.process(np.ascontiguousarray(crop))
        a = self.alpha_crop
        blended = np.rint(crop.astype(np.float32) * (1 - a) + mag.astype(np.float32) * a).astype(np.uint8)
        # Where the mask weight is exactly zero, copy the original bytes untouched.
        out[(slice(None), *self.window)] = np.where(a > 0, blended, crop)
        return out
