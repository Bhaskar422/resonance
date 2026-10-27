"""End-to-end analysis: video in, mask, Hz, magnified video, plot and report out.

Kept free of CLI concerns so the same function can sit behind the FastAPI backend later.
Frames are streamed twice (measure, then magnify and render), so memory stays flat
regardless of clip length.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from resonance import __version__, accel, sam_client
from resonance import frequency as fq
from resonance import io as rio
from resonance import report
from resonance.api import CostLedger, get_client
from resonance.magnify import MagnifyConfig, MaskedMagnifier

CAMERA_RING = (10, 40)  # px: inner/outer radius of the background ring around the mask
CROP_MARGIN = 48


@dataclass
class AnalyzeOptions:
    prompt: str | None = None
    accel_path: Path | None = None
    out_root: Path = Path("out")
    run_name: str | None = None
    capture_fps: float | None = None
    start_s: float | None = None
    duration_s: float | None = 10.0
    max_height: int = 1080
    key_frame: int = 0
    select: str = "largest"
    mask_path: Path | None = None
    box: tuple[int, int, int, int] | None = None
    mask_array: np.ndarray | None = None  # programmatic callers (tests, synthetic demo)
    alpha: float = 20.0
    fmin: float = 2.0
    fmax: float | None = None
    playback_fps: float = 30.0
    use_cache: bool = True
    chunk: int = 64


@dataclass
class _Timer:
    marks: dict = field(default_factory=dict)
    t0: float = field(default_factory=time.time)

    def lap(self, name: str) -> None:
        now = time.time()
        self.marks[name] = round(now - self.t0, 2)
        self.t0 = now


def _bbox(mask: np.ndarray, margin: int) -> tuple[slice, slice]:
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    return slice(max(ys.min() - margin, 0), min(ys.max() + margin + 1, h)), slice(max(xs.min() - margin, 0), min(xs.max() + margin + 1, w))


def _dilate(mask: np.ndarray, r: int) -> np.ndarray:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(mask.astype(np.uint8), k).astype(bool)


def _frame_key(frame: np.ndarray, prompt: str, select: str) -> str:
    thumb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 36), interpolation=cv2.INTER_AREA) >> 4
    h = hashlib.sha256(thumb.tobytes() + f"|{frame.shape}|{prompt}|{select}".encode())
    return h.hexdigest()[:20]


def _get_mask(opts: AnalyzeOptions, frame: np.ndarray, run_dir: Path, ledger: CostLedger) -> tuple[np.ndarray, dict]:
    shape = frame.shape[:2]
    if opts.mask_array is not None:
        return opts.mask_array.astype(bool), {"source": "array"}
    if opts.mask_path:
        m = cv2.imread(str(opts.mask_path), cv2.IMREAD_GRAYSCALE)
        if m is None:
            raise ValueError(f"cannot read mask image {opts.mask_path}")
        if m.shape != shape:
            m = cv2.resize(m, shape[::-1], interpolation=cv2.INTER_NEAREST)
        return m > 127, {"source": "file", "path": str(opts.mask_path)}
    if opts.box:
        x1, y1, x2, y2 = opts.box
        m = np.zeros(shape, bool)
        m[y1:y2, x1:x2] = True
        return m, {"source": "box", "box": list(opts.box)}
    if not opts.prompt:
        raise ValueError("give --prompt (SAM 3.1), --mask or --box")

    cache_dir = opts.out_root / "cache" / "sam"
    key = _frame_key(frame, opts.prompt, opts.select)
    cached = cache_dir / f"{key}.npz"
    if opts.use_cache and cached.exists():
        z = np.load(cached, allow_pickle=False)
        return z["mask"], {"source": "sam-3.1 (cached)", "prompt": opts.prompt, **json.loads(str(z["meta"]))}

    client = get_client()
    res = sam_client.segment_image(client, frame, opts.prompt, ledger=ledger)
    (run_dir / "sam_raw.txt").write_text(res.raw)
    mask = sam_client.select_mask(res.detections, shape, opts.select)
    meta = {"selection": opts.select, "detections": [d.to_dict() for d in res.detections], "usage": res.usage, "cost_usd": res.cost_usd}
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cached, mask=mask, meta=json.dumps(meta))
    return mask, {"source": "sam-3.1", "prompt": opts.prompt, **meta}


def _measure(prep: rio.PreparedVideo, mask: np.ndarray, window: tuple[slice, slice]) -> tuple[np.ndarray, np.ndarray | None]:
    """Displacement of the masked part and of a background ring around it (camera reference)."""
    m_crop = mask[window]
    ring = (_dilate(mask, CAMERA_RING[1]) & ~_dilate(mask, CAMERA_RING[0]))[window]
    frames = prep.iter_frames()
    first = next(frames)[window]
    target = fq.TranslationTracker(first, m_crop)
    try:
        camera = fq.TranslationTracker(first, ring) if ring.sum() > 500 else None
    except ValueError:
        camera = None
    d_t, d_c = [target.update(first)], [camera.update(first)] if camera else []
    for f in frames:
        c = f[window]
        d_t.append(target.update(c))
        if camera:
            d_c.append(camera.update(c))
    return np.asarray(d_t), (np.asarray(d_c) if camera else None)


def _uniform(prep: rio.PreparedVideo, d: np.ndarray) -> tuple[np.ndarray, float]:
    n = min(len(d), prep.timestamps.size)
    if prep.is_vfr:
        _, du, fs = fq.resample_uniform(prep.timestamps[:n], d[:n])
        return du, fs
    return d[:n], prep.fs


def analyze(video: str | Path, opts: AnalyzeOptions) -> dict:
    timer = _Timer()
    video = Path(video)
    run_name = opts.run_name or f"{time.strftime('%Y%m%d-%H%M%S')}_{video.stem}"
    run_dir = opts.out_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger = CostLedger(opts.out_root / "costs.jsonl", run_id=run_name)

    prep = rio.prepare(video, run_dir / "work", max_height=opts.max_height, capture_fps=opts.capture_fps, start_s=opts.start_s, duration_s=opts.duration_s)
    timer.lap("prepare")

    key = prep.frame(opts.key_frame)
    mask, mask_meta = _get_mask(opts, key, run_dir, ledger)
    if mask.sum() < 64:
        raise ValueError("mask is too small to measure motion")
    report.save_mask_overlay(run_dir / "mask_overlay.png", key, mask)
    cv2.imwrite(str(run_dir / "mask.png"), mask.astype(np.uint8) * 255)
    timer.lap("mask")

    window = _bbox(_dilate(mask, CAMERA_RING[1]), CROP_MARGIN)
    d_target, d_camera = _measure(prep, mask, window)
    sig, fs = _uniform(prep, d_target)
    spec = fq.amplitude_spectrum(sig, fs)
    fmax = min(opts.fmax or fs / 2, fs / 2)
    peak = fq.dominant_peak(spec, opts.fmin, fmax)
    harmonics = fq.harmonics(spec, peak.freq_hz)
    cam_spec = None
    cam_info = None
    if d_camera is not None:
        cam_sig, _ = _uniform(prep, d_camera)
        cam_spec = fq.amplitude_spectrum(cam_sig, fs)
        cam_at_f0 = fq.peak_near(cam_spec, peak.freq_hz, max(0.03 * peak.freq_hz, 2 * spec.resolution_hz))
        ratio = cam_at_f0.amplitude / peak.amplitude if cam_at_f0 else 0.0
        cam_info = {"amplitude_at_f0_px": round(cam_at_f0.amplitude, 5) if cam_at_f0 else None, "ratio_to_target": round(ratio, 3)}
        if ratio > 0.3:
            prep.warnings.append(
                f"the background around the mask moves at {peak.freq_hz:.2f} Hz with {ratio:.0%} of the target's amplitude; "
                "the camera may be shaking (put the phone on a separate tripod, not on the machine's table)"
            )
    timer.lap("measure")

    accel_result = None
    accel_spec = accel_harm = None
    if opts.accel_path:
        rec = accel.load_phyphox(opts.accel_path)
        cmp = accel.compare(peak.freq_hz, rec, fmin=opts.fmin)
        accel_spec = accel.accel_spectrum(rec)
        accel_harm = fq.harmonics(accel_spec, cmp.accel_match.freq_hz if cmp.accel_match else cmp.accel_dominant.freq_hz)
        accel_result = {"source": rec.source, "samples": int(rec.t.size), "duration_s": round(float(rec.t[-1]), 2), **cmp.to_dict()}
    timer.lap("accel")

    cfg = MagnifyConfig.around(peak.freq_hz, fs, alpha=opts.alpha)
    magnifier = MaskedMagnifier(mask.shape, mask, cfg)
    caption = (
        f"{peak.freq_hz:.2f} Hz ({peak.freq_hz * 60:.0f} cpm)  |  magnified x{cfg.alpha:g} in {cfg.low_hz:.1f}-{cfg.high_hz:.1f} Hz  |  "
        f"{prep.fs:.0f} fps, played at {opts.playback_fps:g} fps ({prep.fs / opts.playback_fps:.0f}x slower)"
    )
    sbs = report.SideBySideWriter(run_dir / "side_by_side.mp4", mask.shape, mask, playback_fps=opts.playback_fps, caption=caption)
    buf: list[np.ndarray] = []

    def flush() -> None:
        chunk = np.stack(buf)
        for orig, mag in zip(chunk, magnifier.process(chunk)):
            sbs.write(orig, mag)
        buf.clear()

    for f in prep.iter_frames():
        buf.append(f)
        if len(buf) == opts.chunk:
            flush()
    if buf:
        flush()
    sbs.close()
    timer.lap("magnify")

    report.plot_spectra(run_dir / "spectrum.png", spec, harmonics, camera=cam_spec, accel=accel_spec, accel_harmonics=accel_harm, fmax=opts.fmax)
    timer.lap("plot")

    result = {
        "resonance_version": __version__,
        "run": run_name,
        "input": str(video),
        "video": prep.to_dict(),
        "analysis_fs": round(fs, 3),
        "mask": {**mask_meta, "area_px": int(mask.sum()), "key_frame": opts.key_frame},
        "vibration": {
            "dominant": peak.to_dict(),
            "dominant_cpm": round(peak.freq_hz * 60, 1),
            "direction_deg": round(fq.principal_direction_deg(sig), 1),
            "spectral_resolution_hz": round(spec.resolution_hz, 4),
            "harmonics": [
                {
                    "order": h.order,
                    "expected_hz": round(h.expected_hz, 3),
                    "present": h.present,
                    "relative_amplitude": None if h.rel_amplitude is None else round(h.rel_amplitude, 4),
                    "peak": h.peak.to_dict() if h.peak else None,
                }
                for h in harmonics
            ],
            "top_peaks": [p.to_dict() for p in fq.top_peaks(spec, fmin=opts.fmin, fmax=fmax)],
            "motion_model": "rigid translation of the masked region (Lucas-Kanade)",
            "camera_reference": cam_info,
        },
        "accelerometer": accel_result,
        "magnification": {"method": "linear Eulerian (Wu et al. 2012)", "alpha": cfg.alpha, "band_hz": [round(cfg.low_hz, 3), round(cfg.high_hz, 3)]},
        "outputs": {k: str(run_dir / v) for k, v in {"video": "side_by_side.mp4", "spectrum": "spectrum.png", "mask": "mask_overlay.png"}.items()},
        "api_cost_usd": {"this_run": round(ledger.run_total, 4), "all_time": round(ledger.all_time_total(), 4), "calls": ledger.calls},
        "warnings": prep.warnings,
        "timings_s": timer.marks,
    }
    np.savez_compressed(run_dir / "signals.npz", target=d_target, camera=d_camera if d_camera is not None else np.empty((0, 2)), timestamps=prep.timestamps)
    report.write_json(run_dir / "report.json", result)
    return result
