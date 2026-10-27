"""Accelerometer ground truth from a phyphox export.

Put the phone on the running machine, record "Acceleration (without g)" in phyphox (iOS or
Android), and export CSV or the zip phyphox produces. The vibration frequency seen by the
accelerometer is then compared with the one measured from the video's pixels. Only peak
frequencies are compared, so the two recordings need no time sync.

phyphox exports either comma-separated values with decimal points, or semicolon/tab
separated values with decimal commas (the locale formats); all are handled here.
"""

from __future__ import annotations

import csv
import io as _io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from resonance import frequency as fq


class AccelError(ValueError):
    pass


@dataclass
class AccelRecording:
    t: np.ndarray  # (N,) seconds
    xyz: np.ndarray  # (N, 3) m/s²
    fs: float  # median sample rate
    source: str
    columns: list[str] = field(default_factory=list)

    @property
    def nyquist_hz(self) -> float:
        return self.fs / 2


def _read_text(path: Path) -> tuple[str, str]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            # Prefer the accelerometer table over metadata tables (device.csv, time.csv).
            names.sort(key=lambda n: (not re.search(r"acc|raw data", n, re.I), n))
            if not names:
                raise AccelError(f"{path} contains no CSV file")
            return z.read(names[0]).decode("utf-8-sig"), f"{path.name}:{names[0]}"
    return path.read_text(encoding="utf-8-sig"), path.name


def _parse_table(text: str) -> tuple[list[str], np.ndarray]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        raise AccelError("CSV has no data rows")
    header = lines[0]
    delim = max([",", ";", "\t"], key=header.count)
    decimal_comma = delim != "," and any("," in ln for ln in lines[1:4])
    rows = list(csv.reader(_io.StringIO("\n".join(lines)), delimiter=delim))
    cols = [c.strip() for c in rows[0]]
    data = []
    for r in rows[1:]:
        if len(r) < len(cols):
            continue
        vals = [v.strip().replace(",", ".") if decimal_comma else v.strip() for v in r[: len(cols)]]
        try:
            data.append([float(v) if v else np.nan for v in vals])
        except ValueError:
            continue
    if not data:
        raise AccelError("CSV has no numeric rows")
    return cols, np.asarray(data, float)


def _pick(cols: list[str], pattern: str) -> int | None:
    for i, c in enumerate(cols):
        if re.search(pattern, c, re.I):
            return i
    return None


def load_phyphox(path: str | Path) -> AccelRecording:
    path = Path(path)
    if not path.exists():
        raise AccelError(f"no such file: {path}")
    text, source = _read_text(path)
    cols, data = _parse_table(text)

    ti = _pick(cols, r"^time")
    axes = [_pick(cols, rf"acc\w*\s*{a}\b|^{a}\b") for a in "xyz"]
    if ti is None or any(a is None for a in axes):
        raise AccelError(f"{source}: expected a time column and x/y/z acceleration columns, got {cols}")
    keep = ~np.isnan(data[:, [ti, *axes]]).any(axis=1)
    t, xyz = data[keep, ti], data[keep][:, axes]
    if t.size < 16:
        raise AccelError(f"{source}: too few samples ({t.size})")
    fs = 1.0 / float(np.median(np.diff(t)))
    return AccelRecording(t - t[0], xyz, fs, source, cols)


def accel_spectrum(rec: AccelRecording) -> fq.Spectrum:
    """Direction-independent spectrum of the three axes, on a uniform time grid."""
    _, xyz, fs = fq.resample_uniform(rec.t, rec.xyz)
    return fq.amplitude_spectrum(xyz, fs)


@dataclass
class Comparison:
    video_hz: float
    accel_dominant: fq.Peak
    accel_match: fq.Peak | None  # accelerometer peak nearest the video frequency
    accel_fs: float
    percent_error: float | None
    verifiable: bool
    note: str

    def to_dict(self) -> dict:
        return {
            "video_hz": round(self.video_hz, 4),
            "accel_dominant": self.accel_dominant.to_dict(),
            "accel_match": self.accel_match.to_dict() if self.accel_match else None,
            "accel_sample_rate_hz": round(self.accel_fs, 2),
            "percent_error": None if self.percent_error is None else round(self.percent_error, 3),
            "verifiable": self.verifiable,
            "note": self.note,
        }


def compare(video_hz: float, rec: AccelRecording, *, rel_tol: float = 0.1, fmin: float = 2.0) -> Comparison:
    spec = accel_spectrum(rec)
    dominant = fq.dominant_peak(spec, fmin=fmin)
    if video_hz >= rec.nyquist_hz:
        return Comparison(
            video_hz, dominant, None, rec.fs, None, False,
            f"video peak {video_hz:.2f} Hz is above the accelerometer's Nyquist limit "
            f"({rec.nyquist_hz:.1f} Hz at {rec.fs:.0f} Hz sampling); cannot verify",
        )
    match = fq.peak_near(spec, video_hz, max(rel_tol * video_hz, 2 * spec.resolution_hz))
    if match is None or match.snr < 3.0:
        return Comparison(
            video_hz, dominant, match, rec.fs, None, False,
            f"no clear accelerometer peak within ±{rel_tol:.0%} of {video_hz:.2f} Hz "
            f"(accelerometer dominant: {dominant.freq_hz:.2f} Hz)",
        )
    err = abs(video_hz - match.freq_hz) / match.freq_hz * 100.0
    note = "video and accelerometer agree" if err < 2.0 else "video and accelerometer peaks differ"
    if abs(dominant.freq_hz - match.freq_hz) > spec.resolution_hz * 2:
        note += f"; accelerometer's strongest peak is at {dominant.freq_hz:.2f} Hz"
    return Comparison(video_hz, dominant, match, rec.fs, err, True, note)
