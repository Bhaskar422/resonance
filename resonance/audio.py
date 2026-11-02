"""The clip's soundtrack as extra evidence.

A machine's sound carries the same physics as its motion: blade-pass tones, motor hum at
twice the line frequency, rattles from looseness. We measure tonal peaks locally (no API)
and express each as a multiple of the vibration frequency measured from the video, so the
diagnosis can link what is heard to what is seen.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy import signal as sps
from scipy.io import wavfile

SAMPLE_RATE = 16000


@dataclass
class Tone:
    freq_hz: float
    level_db: float  # above the median spectral level
    ratio_to_f0: float | None  # freq / vibration frequency, when one is given


def has_audio(path: str | Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    return out.returncode == 0 and bool(json.loads(out.stdout or "{}").get("streams"))


def extract_wav(src: str | Path, out: str | Path, *, start_s: float | None = None, duration_s: float | None = 20.0) -> Path | None:
    """Mono 16 kHz WAV of the clip's audio, or None when the clip has no audio track."""
    if not has_audio(src):
        return None
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start_s:
        cmd += ["-ss", str(start_s)]
    cmd += ["-i", str(src)]
    if duration_s:
        cmd += ["-t", str(duration_s)]
    cmd += ["-map", "0:a:0", "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return Path(out) if res.returncode == 0 and Path(out).stat().st_size > 1000 else None


def tonal_peaks(wav: str | Path, *, f0: float | None = None, fmin: float = 20.0, fmax: float = 2000.0, n: int = 8) -> list[Tone]:
    sr, x = wavfile.read(str(wav))
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if x.size < sr // 2:
        return []
    f, pxx = sps.welch(x, sr, nperseg=min(x.size, 2 * sr))  # 0.5 Hz resolution
    db = 10 * np.log10(pxx + 1e-20)
    band = (f >= fmin) & (f <= fmax)
    floor = np.median(db[band])
    idx, props = sps.find_peaks(db[band], prominence=6.0, distance=max(1, int(2.0 / (f[1] - f[0]))))
    order = np.argsort(props["prominences"])[::-1][:n]
    tones = []
    for i in idx[order]:
        fi = float(f[band][i])
        tones.append(Tone(round(fi, 2), round(float(db[band][i] - floor), 1), round(fi / f0, 3) if f0 else None))
    return sorted(tones, key=lambda t: t.level_db, reverse=True)


def tones_to_dicts(tones: list[Tone]) -> list[dict]:
    return [asdict(t) for t in tones]
