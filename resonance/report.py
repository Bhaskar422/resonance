"""Run outputs: spectrum plot, side-by-side comparison video, report.json."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from resonance import frequency as fq
from resonance.io import VideoWriter

# Reference dataviz palette (light mode).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_1 = "#2a78d6"  # video
SERIES_2 = "#eb6834"  # accelerometer


def _style(ax, title: str, ylabel: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=10, color=INK, pad=6)
    ax.set_ylabel(ylabel, fontsize=9, color=INK_2)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.tick_params(colors=MUTED, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)


def _mark_harmonics(ax, harmonics: list[fq.Harmonic], color: str) -> None:
    for h in harmonics:
        if h.order > 4 or not h.present:
            continue
        p = h.peak
        ax.plot([p.freq_hz], [p.amplitude], "o", ms=5, color=color, mec=SURFACE, mew=1.5, zorder=3)
        label = f"{h.order}×  {p.freq_hz:.2f} Hz" if h.order == 1 else f"{h.order}×"
        ax.annotate(label, (p.freq_hz, p.amplitude), xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK)


def plot_spectra(
    path: Path,
    video: fq.Spectrum,
    video_harmonics: list[fq.Harmonic],
    *,
    camera: fq.Spectrum | None = None,
    accel: fq.Spectrum | None = None,
    accel_harmonics: list[fq.Harmonic] | None = None,
    fmax: float | None = None,
) -> Path:
    f0 = video_harmonics[0].peak.freq_hz if video_harmonics and video_harmonics[0].peak else None
    xmax = fmax or video.nyquist
    if f0:
        xmax = min(xmax, max(6 * f0, 60.0))

    rows = 2 if accel is not None else 1
    fig, axes = plt.subplots(rows, 1, figsize=(9, 3.2 * rows), sharex=True, facecolor=SURFACE, squeeze=False)
    ax = axes[0, 0]
    sel = video.freqs <= xmax
    ax.plot(video.freqs[sel], video.amplitude[sel], color=SERIES_1, lw=1.6, label="Inside mask")
    if camera is not None:
        csel = camera.freqs <= xmax
        ax.plot(camera.freqs[csel], camera.amplitude[csel], color=MUTED, lw=1.0, ls="--", label="Around mask (camera reference)")
        ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper right")
    _mark_harmonics(ax, video_harmonics, SERIES_1)
    _style(ax, "Video: motion measured from pixels", "Amplitude (px)")
    ax.set_ylim(bottom=0)

    if accel is not None:
        ax2 = axes[1, 0]
        asel = accel.freqs <= xmax
        ax2.plot(accel.freqs[asel], accel.amplitude[asel], color=SERIES_2, lw=1.6)
        if accel_harmonics:
            _mark_harmonics(ax2, accel_harmonics, SERIES_2)
        if accel.nyquist < xmax:
            ax2.axvline(accel.nyquist, color=MUTED, lw=0.8, ls=":")
            ax2.annotate("sensor Nyquist", (accel.nyquist, 0), xytext=(4, 6), textcoords="offset points", fontsize=8, color=INK_2)
        _style(ax2, "Accelerometer: ground truth (phyphox)", "Amplitude (m/s²)")
        ax2.set_ylim(bottom=0)
    axes[-1, 0].set_xlabel("Frequency (Hz)", fontsize=9, color=INK_2)
    axes[-1, 0].set_xlim(0, xmax)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


class SideBySideWriter:
    """Original | magnified, with the mask outline and a caption bar, as browser-playable MP4."""

    BAR_H = 44

    def __init__(self, path: Path, frame_shape: tuple[int, int], mask: np.ndarray, *, playback_fps: float, caption: str, max_width: int = 1920):
        h, w = frame_shape
        self.scale = min(1.0, max_width / (2 * w))
        self.size = (int(round(w * self.scale)) // 2 * 2, int(round(h * self.scale)) // 2 * 2)
        m = cv2.resize(mask.astype(np.uint8), self.size, interpolation=cv2.INTER_NEAREST)
        self.contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.caption = caption
        self.writer = VideoWriter(path, playback_fps)

    def _panel(self, frame: np.ndarray, label: str) -> np.ndarray:
        img = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA) if self.scale < 1 else frame.copy()
        cv2.drawContours(img, self.contours, -1, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.putText(img, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(img, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        return img

    def write(self, original: np.ndarray, magnified: np.ndarray) -> None:
        row = np.hstack([self._panel(original, "Original"), self._panel(magnified, "Magnified")])
        bar = np.full((self.BAR_H, row.shape[1], 3), 24, np.uint8)
        cv2.putText(bar, self.caption, (12, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 239, 236), 1, cv2.LINE_AA)
        self.writer.write(np.vstack([bar, row]))

    def close(self) -> None:
        self.writer.close()


def save_mask_overlay(path: Path, frame: np.ndarray, mask: np.ndarray) -> Path:
    img = frame.copy()
    tint = np.array([0, 200, 255], np.float32)
    img[mask] = (0.55 * img[mask] + 0.45 * tint).astype(np.uint8)
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, contours, -1, (0, 200, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(path), img)
    return path


def _jsonable(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serializable: {type(o)}")


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2, default=_jsonable))
    return path
