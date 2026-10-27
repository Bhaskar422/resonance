"""Vibration frequency from pixels: a motion signal inside a mask, then an FFT.

The main motion estimator is a global Lucas–Kanade translation solve over the masked
region. For the sub-pixel motion of a vibrating machine housing, the brightness change at
each pixel is linear in the displacement, so one 2×2 least-squares solve per frame recovers
(dx, dy) to a few hundredths of a pixel. Farneback dense flow is available as a cross-check.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

import cv2
import numpy as np
from scipy import signal as sps


# ---------------------------------------------------------------------------
# Motion signal
# ---------------------------------------------------------------------------


def to_gray(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame.astype(np.float32)


class TranslationTracker:
    """Estimates the translation of a masked region relative to a reference frame.

    Streaming: call :meth:`update` once per frame, so long clips never need to sit in
    memory. ``iterations`` > 1 adds Gauss–Newton refinement for motions near or above 1 px.
    """

    def __init__(self, reference: np.ndarray, mask: np.ndarray, *, blur_sigma: float = 1.0, iterations: int = 2):
        self.blur_sigma = blur_sigma
        self.iterations = iterations
        self.ref = self._prep(reference)
        gy, gx = np.gradient(self.ref)
        # Trim a border so warps and gradients never read outside the image.
        weight = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        if weight.sum() < 16:
            raise ValueError("mask is too small to track")
        self.w = weight
        self.gx, self.gy = gx * weight, gy * weight
        g = np.array([[np.sum(self.gx * gx), np.sum(self.gx * gy)], [np.sum(self.gy * gx), np.sum(self.gy * gy)]])
        if np.linalg.cond(g) > 1e6:
            raise ValueError("masked region has too little texture to measure motion (aperture problem)")
        self.g_inv = np.linalg.inv(g)

    def _prep(self, frame: np.ndarray) -> np.ndarray:
        f = to_gray(frame)
        return cv2.GaussianBlur(f, (0, 0), self.blur_sigma) if self.blur_sigma > 0 else f

    def update(self, frame: np.ndarray) -> tuple[float, float]:
        cur = self._prep(frame)
        d = np.zeros(2)
        warped = cur
        for _ in range(self.iterations):
            diff = warped - self.ref
            d -= self.g_inv @ np.array([np.sum(self.gx * diff), np.sum(self.gy * diff)])
            # Undo the current estimate and re-solve for the residual motion.
            m = np.float32([[1, 0, -d[0]], [0, 1, -d[1]]])
            warped = cv2.warpAffine(cur, m, cur.shape[::-1], flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return float(d[0]), float(d[1])


def translation_signal(frames: Iterable[np.ndarray], mask: np.ndarray, *, reference: np.ndarray | None = None, **kw) -> np.ndarray:
    """(T, 2) displacement in pixels of the masked region, relative to the first frame."""
    it = iter(frames)
    first = next(it)
    tracker = TranslationTracker(first if reference is None else reference, mask, **kw)
    out = [tracker.update(first)]
    out.extend(tracker.update(f) for f in it)
    return np.asarray(out)


def farneback_signal(frames: Iterable[np.ndarray], mask: np.ndarray) -> np.ndarray:
    """(T, 2) mean Farneback flow inside the mask, relative to the first frame."""
    it = iter(frames)
    ref = to_gray(next(it)).astype(np.uint8)
    m = mask.astype(bool)
    out = [(0.0, 0.0)]
    for f in it:
        flow = cv2.calcOpticalFlowFarneback(ref, to_gray(f).astype(np.uint8), None, 0.5, 3, 15, 3, 5, 1.2, 0)
        out.append((float(flow[..., 0][m].mean()), float(flow[..., 1][m].mean())))
    return np.asarray(out)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def resample_uniform(t: np.ndarray, x: np.ndarray, fs: float | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    """Interpolate samples taken at times ``t`` onto a uniform grid.

    Variable-frame-rate video and phone sensors both deliver jittered timestamps; the FFT
    needs uniform spacing. ``fs`` defaults to the median sample rate.
    """
    t = np.asarray(t, float)
    x = np.asarray(x, float)
    order = np.argsort(t)
    t, x = t[order], x[order]
    keep = np.concatenate([[True], np.diff(t) > 0])
    t, x = t[keep], x[keep]
    if fs is None:
        fs = 1.0 / np.median(np.diff(t))
    tu = t[0] + np.arange(int(np.floor((t[-1] - t[0]) * fs)) + 1) / fs
    if x.ndim == 1:
        return tu, np.interp(tu, t, x), fs
    return tu, np.stack([np.interp(tu, t, x[:, k]) for k in range(x.shape[1])], axis=1), fs


def is_uniform(t: np.ndarray, rel_tol: float = 0.02) -> bool:
    dt = np.diff(np.asarray(t, float))
    return bool(dt.size == 0 or np.max(np.abs(dt - np.median(dt))) <= rel_tol * np.median(dt))


# ---------------------------------------------------------------------------
# Spectrum and peaks
# ---------------------------------------------------------------------------


@dataclass
class Spectrum:
    freqs: np.ndarray  # Hz
    amplitude: np.ndarray  # sinusoid peak amplitude, in the signal's units
    fs: float

    @property
    def nyquist(self) -> float:
        return self.fs / 2

    @property
    def resolution_hz(self) -> float:
        return self.freqs[1] - self.freqs[0]


@dataclass
class Peak:
    freq_hz: float
    amplitude: float
    snr: float  # amplitude over the median amplitude of the searched band

    def to_dict(self) -> dict:
        return {k: round(float(v), 4) for k, v in asdict(self).items()}


@dataclass
class Harmonic:
    order: int
    expected_hz: float
    peak: Peak | None  # None when above Nyquist

    @property
    def present(self) -> bool:
        return self.peak is not None and self.peak.snr >= 3.0


def amplitude_spectrum(x: np.ndarray, fs: float, *, pad_factor: int = 4) -> Spectrum:
    """Single-sided amplitude spectrum. ``x`` may be (T,) or (T, K); multi-axis signals are
    combined as the root-sum-square over axes, which does not depend on motion direction."""
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    x = sps.detrend(x, axis=0, type="linear")
    n = x.shape[0]
    win = np.hanning(n)
    nfft = int(2 ** np.ceil(np.log2(n * pad_factor)))
    spec = np.fft.rfft(x * win[:, None], n=nfft, axis=0)
    amp = 2.0 * np.abs(spec) / win.sum()
    amp = np.sqrt(np.sum(amp**2, axis=1))
    return Spectrum(np.fft.rfftfreq(nfft, 1.0 / fs), amp, fs)


def _band(spec: Spectrum, fmin: float, fmax: float | None) -> np.ndarray:
    fmax = spec.nyquist if fmax is None else min(fmax, spec.nyquist)
    return np.nonzero((spec.freqs >= fmin) & (spec.freqs <= fmax))[0]


def _refine(spec: Spectrum, i: int, floor: float) -> Peak:
    """Parabolic interpolation of a spectral peak on log amplitude."""
    a = spec.amplitude
    freq, amp = spec.freqs[i], a[i]
    if 0 < i < a.size - 1 and min(a[i - 1], a[i], a[i + 1]) > 0:
        l, c, r = np.log(a[i - 1]), np.log(a[i]), np.log(a[i + 1])
        denom = l - 2 * c + r
        if denom < 0:
            p = 0.5 * (l - r) / denom
            freq = spec.freqs[i] + p * spec.resolution_hz
            amp = float(np.exp(c - 0.25 * (l - r) * p))
    return Peak(float(freq), float(amp), float(amp / floor) if floor > 0 else float("inf"))


def noise_floor(spec: Spectrum, fmin: float = 0.0, fmax: float | None = None) -> float:
    return float(np.median(spec.amplitude[_band(spec, fmin, fmax)]))


def dominant_peak(spec: Spectrum, fmin: float = 2.0, fmax: float | None = None) -> Peak:
    band = _band(spec, fmin, fmax)
    if band.size == 0:
        raise ValueError(f"no spectrum bins between {fmin} and {fmax} Hz")
    i = band[np.argmax(spec.amplitude[band])]
    return _refine(spec, i, noise_floor(spec, fmin, fmax))


def top_peaks(spec: Spectrum, n: int = 5, fmin: float = 2.0, fmax: float | None = None, min_snr: float = 3.0) -> list[Peak]:
    band = _band(spec, fmin, fmax)
    floor = noise_floor(spec, fmin, fmax)
    # Peaks closer than ~4 bins of the unpadded FFT are the same spectral line.
    distance = max(1, int(round(0.5 / spec.resolution_hz)))
    idx, _ = sps.find_peaks(spec.amplitude[band], distance=distance)
    peaks = [_refine(spec, band[i], floor) for i in idx]
    peaks = [p for p in peaks if p.snr >= min_snr]
    return sorted(peaks, key=lambda p: p.amplitude, reverse=True)[:n]


def peak_near(spec: Spectrum, freq_hz: float, tol_hz: float) -> Peak | None:
    if freq_hz - tol_hz > spec.nyquist:
        return None
    lo = max(freq_hz - tol_hz, spec.freqs[1])
    band = _band(spec, lo, freq_hz + tol_hz)
    if band.size == 0:
        return None
    i = band[np.argmax(spec.amplitude[band])]
    return _refine(spec, i, noise_floor(spec, 2.0))


def harmonics(spec: Spectrum, f0: float, n_max: int = 6, rel_tol: float = 0.03) -> list[Harmonic]:
    """Look for k·f0 for k = 1..n_max, within ±max(3 %, 2 bins) of the expected frequency."""
    out = []
    for k in range(1, n_max + 1):
        fk = k * f0
        if fk > spec.nyquist:
            out.append(Harmonic(k, fk, None))
            continue
        tol = max(rel_tol * fk, 2 * spec.resolution_hz)
        out.append(Harmonic(k, fk, peak_near(spec, fk, tol)))
    return out


def principal_direction_deg(d: np.ndarray) -> float:
    """Dominant motion axis of a (T, 2) displacement signal, in degrees (image coordinates)."""
    d = sps.detrend(np.asarray(d, float), axis=0)
    _, _, vt = np.linalg.svd(d, full_matrices=False)
    return float(np.rad2deg(np.arctan2(vt[0, 1], vt[0, 0])) % 180.0)
