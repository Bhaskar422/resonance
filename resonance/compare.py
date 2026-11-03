"""Rescan after a fix: did the vibration actually go away?

Compares two analysis runs of the same machine from the same camera position (before and
after a repair): amplitude at the original fault frequency and its harmonics, in % and dB,
with a verdict. When the "before" run was diagnosed, Muse Spark checks the result against the
diagnosis's own prediction of what the rescan should show, closing the loop.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as sps

from resonance import frequency as fq
from resonance import report as rpt
from resonance.api import CostLedger, check_model, get_client

VERDICT_MODEL = "muse-spark-1.3"


def _load(run_dir: Path) -> tuple[dict, fq.Spectrum, float]:
    """Report, spectrum, and RMS displacement (px) above 2 Hz of a run."""
    r = json.loads((run_dir / "report.json").read_text())
    z = np.load(run_dir / "signals.npz")
    d, t = z["target"], z["timestamps"]
    n = min(len(d), t.size)
    if r["video"]["variable_frame_rate"]:
        spec = fq.nonuniform_spectrum(t[:n], d[:n])
        _, d, fs = fq.resample_uniform(t[:n], d[:n])
    else:
        d, fs = d[:n], r["analysis_fs"]
        spec = fq.amplitude_spectrum(d, fs)
    hp = sps.sosfiltfilt(sps.butter(4, 2.0, btype="high", fs=fs, output="sos"), sps.detrend(d, axis=0), axis=0)
    rms = float(np.sqrt(np.mean(np.sum(hp**2, axis=1))))
    return r, spec, rms


def _change(before: float, after: float) -> dict:
    ratio = after / before if before > 0 else float("inf")
    return {
        "before_px": round(before, 5),
        "after_px": round(after, 5),
        "change_pct": round((ratio - 1) * 100, 1),
        "change_db": round(20 * np.log10(max(ratio, 1e-6)), 1),
    }


def verdict_from(change_pct: float) -> str:
    if change_pct <= -70:
        return "resolved"
    if change_pct <= -30:
        return "improved"
    if change_pct < 30:
        return "no_change"
    return "worse"


VERDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["matches_prediction", "verdict", "explanation", "next_step"],
    "properties": {
        "matches_prediction": {"type": "boolean", "description": "Did the rescan show what the diagnosis predicted?"},
        "verdict": {"type": "string", "enum": ["fixed", "partially_fixed", "not_fixed", "new_problem"]},
        "explanation": {"type": "string", "description": "Two sentences citing the numbers"},
        "next_step": {"type": "string"},
    },
}


def _spark_verdict(before_dir: Path, result: dict, ledger: CostLedger) -> dict | None:
    dx_path = before_dir / "diagnosis.json"
    if not dx_path.exists():
        return None
    dx = json.loads(dx_path.read_text())["diagnosis"]
    prompt = (
        "A machine was diagnosed, repaired, and filmed again from the same camera position.\n"
        f"DIAGNOSIS (before the fix): {json.dumps({k: dx[k] for k in ('primary_fault', 'summary', 'recommended_actions', 'rescan_expectation')})}\n"
        f"RESCAN COMPARISON (vibration amplitudes measured from video, same units both times): {json.dumps(result)}\n"
        "Judge whether the repair worked, against what the diagnosis predicted the rescan would show."
    )
    client = get_client()
    resp = client.responses.create(
        model=check_model(VERDICT_MODEL),
        input=[{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        reasoning={"effort": "low"},
        max_output_tokens=4000,
        text={"format": {"type": "json_schema", "name": "rescan_verdict", "schema": VERDICT_SCHEMA, "strict": True}},
    )
    ledger.record(VERDICT_MODEL, "responses:rescan_verdict", resp.usage, note="rescan verdict")
    return json.loads(resp.output_text)


def plot_compare(path: Path, before: fq.Spectrum, after: fq.Spectrum, f0: float, labels: tuple[str, str]) -> Path:
    xmax = min(before.nyquist, after.nyquist, max(6 * f0, 60.0))
    fig, ax = plt.subplots(figsize=(9, 3.4), facecolor=rpt.SURFACE)
    for spec, color, label in ((before, rpt.SERIES_1, labels[0]), (after, rpt.SERIES_2, labels[1])):
        sel = spec.freqs <= xmax
        ax.plot(spec.freqs[sel], spec.amplitude[sel], color=color, lw=1.6, label=label)
    ax.legend(frameon=False, fontsize=8, labelcolor=rpt.INK_2, loc="upper right")
    rpt._style(ax, "Rescan after fix: vibration spectrum", "Amplitude (px)")
    ax.set_xlabel("Frequency (Hz)", fontsize=9, color=rpt.INK_2)
    ax.set_xlim(0, xmax)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=rpt.SURFACE)
    plt.close(fig)
    return path


def compare_runs(before_dir: str | Path, after_dir: str | Path, *, ask_spark: bool = True) -> dict:
    before_dir, after_dir = Path(before_dir), Path(after_dir)
    rb, sb, rms_b = _load(before_dir)
    ra, sa, rms_a = _load(after_dir)
    f0 = rb["vibration"]["dominant"]["freq_hz"]
    warnings = []

    area_b, area_a = rb["mask"].get("measured_area_px", rb["mask"]["area_px"]), ra["mask"].get("measured_area_px", ra["mask"]["area_px"])
    if abs(area_a - area_b) > 0.2 * area_b:
        warnings.append(
            f"the analysed region changed size ({area_b} -> {area_a} px); the camera may have moved, "
            "so pixel amplitudes are not directly comparable"
        )

    tol = max(0.03 * f0, 2 / min(sb.duration_s, sa.duration_s))
    harmonics = []
    for h in rb["vibration"]["harmonics"]:
        if not h["present"] or not h["peak"]:
            continue
        fk = h["peak"]["freq_hz"]
        pa = fq.peak_near(sa, fk, tol)
        harmonics.append({"order": h["order"], "freq_hz": round(fk, 3), **_change(h["peak"]["amplitude"], pa.amplitude if pa else 0.0)})
    fundamental = harmonics[0] if harmonics else _change(rb["vibration"]["dominant"]["amplitude"], 0.0)

    result = {
        "before_run": rb["run"],
        "after_run": ra["run"],
        "fault_frequency_hz": round(f0, 3),
        "fundamental": fundamental,
        "harmonics": harmonics,
        "rms_displacement": _change(rms_b, rms_a),  # all motion above 2 Hz, both axes
        "after_dominant": ra["vibration"]["dominant"],
        "verdict": verdict_from(fundamental["change_pct"]),
        "warnings": warnings,
    }
    ledger = CostLedger(Path(rb.get("api_cost_ledger", "out/costs.jsonl")), run_id=f"{ra['run']}:compare")
    result["spark"] = _spark_verdict(before_dir, result, ledger) if ask_spark else None
    result["api_cost_usd"] = round(ledger.run_total, 4)

    plot_compare(after_dir / "compare.png", sb, sa, f0, ("Before fix", "After fix"))
    (after_dir / "compare.json").write_text(json.dumps(result, indent=2))
    return result
