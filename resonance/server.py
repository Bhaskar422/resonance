"""Web app: upload a clip, watch Resonance see, measure, diagnose and show the fix.

    uv run resonance serve            # http://127.0.0.1:8000  (site at /, workspace at /app)

The pages are the React build in web/dist (source in frontend/); without a build the
original single-page app is served instead.

One background worker runs jobs one at a time (analysis is CPU-heavy, and it keeps API spend
predictable). Every run lives in out/<run>/ exactly as the CLI writes it, so CLI and web
runs are interchangeable.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

OUT = Path("out")
WEB = Path(__file__).parent / "web"
DIST = WEB / "dist"
RUN_NAME = re.compile(r"^[\w.-]+$")
SERVED_FILES = {
    "side_by_side.mp4", "spectrum.png", "mask_overlay.png", "mask_measured.png", "key_frame.png", "action_point.png",
    "where_to_act.png", "fixed_state.png", "now_vs_fixed.png", "compare.png", "report.json", "diagnosis.json",
    "diagnosis.md", "compare.json", "visualize.json",
}
STAGES = ["upload", "prepare", "mask", "measure", "accel", "magnify", "plot", "diagnose", "visualize", "done"]


@dataclass
class Job:
    id: str
    stage: str = "upload"
    status: str = "queued"  # queued | running | done | error
    run: str | None = None
    done: list[str] = field(default_factory=lambda: ["upload"])
    error: str | None = None
    started: float = field(default_factory=time.time)
    finished: float | None = None


app = FastAPI(title="Resonance")
_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=1)


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", Path(name or "upload").name)[:80]
    return stem or "upload"


def _run_dir(run: str) -> Path:
    if not RUN_NAME.match(run) or not (OUT / run / "report.json").exists():
        raise HTTPException(404, "no such run")
    return OUT / run


def _read(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _spectrum(run_dir: Path, bins: int = 600) -> dict | None:
    """The measured spectrum, max-pooled to a fixed number of bins so peaks survive."""
    import numpy as np

    from resonance.compare import _load

    try:
        _, spec, _ = _load(run_dir)
    except (OSError, KeyError, ValueError):
        return None
    edges = np.linspace(0, spec.nyquist, bins + 1)
    idx = np.clip(np.searchsorted(edges, spec.freqs, side="right") - 1, 0, bins - 1)
    amp = np.zeros(bins)
    np.maximum.at(amp, idx, spec.amplitude)
    return {"fmax": round(float(spec.nyquist), 3), "amp": [float(f"{a:.4g}") for a in amp]}


def _files(run_dir: Path) -> dict[str, str]:
    return {n: f"/files/{run_dir.name}/{n}" for n in sorted(SERVED_FILES) if (run_dir / n).exists()}


def run_created(run_dir: Path) -> float:
    """When the run was made: from its name (YYYYMMDD-HHMMSS_…), else the report's mtime."""
    from datetime import datetime

    try:
        return datetime.strptime(run_dir.name[:15], "%Y%m%d-%H%M%S").timestamp()
    except ValueError:
        return (run_dir / "report.json").stat().st_mtime


def _summary(run_dir: Path) -> dict:
    r = json.loads((run_dir / "report.json").read_text())
    dx = _read(run_dir / "diagnosis.json")
    return {
        "run": r["run"],
        "created": run_created(run_dir),
        "input": Path(r["input"]).name,
        "machine": r.get("machine"),
        "prompt": r["mask"].get("prompt"),
        "freq_hz": r["vibration"]["dominant"]["freq_hz"],
        "fault": dx["diagnosis"]["primary_fault"] if dx else None,
        "severity": dx["diagnosis"]["severity"] if dx else None,
        "thumb": f"/files/{r['run']}/key_frame.png" if (run_dir / "key_frame.png").exists() else f"/files/{r['run']}/mask_overlay.png",
    }


def _set(job: Job, **kw) -> None:
    with _lock:
        for k, v in kw.items():
            setattr(job, k, v)


def _finish_stage(job: Job, name: str, nxt: str) -> None:
    with _lock:
        job.done = [*job.done, name]
        job.stage = nxt


def _work(job: Job, video: Path, form: dict) -> None:
    from resonance.diagnose import diagnose
    from resonance.pipeline import AnalyzeOptions, analyze
    from resonance.visualize import render_fix

    _set(job, status="running", stage="prepare")
    try:
        nxt = {s: STAGES[i + 1] for i, s in enumerate(STAGES[:-1])}
        opts = AnalyzeOptions(
            prompt=form["prompt"] or None,
            machine=form["machine"] or None,
            accel_path=form.get("accel"),
            out_root=OUT,
            capture_fps=form.get("capture_fps"),
            duration_s=form.get("duration") or 10.0,
            on_stage=lambda done: _finish_stage(job, done, nxt.get(done, done)),
        )
        result = analyze(video, opts)
        _set(job, run=result["run"])
        run_dir = OUT / result["run"]
        if form["diagnose"]:
            _set(job, stage="diagnose")
            diagnose(run_dir, manual=form.get("manual"), machine_hint=form.get("machine") or None)
            _finish_stage(job, "diagnose", "visualize" if form["visualize"] else "done")
            if form["visualize"]:
                render_fix(run_dir)
                _finish_stage(job, "visualize", "done")
        _set(job, status="done", stage="done", finished=time.time())
    except Exception as e:  # report any failure to the page instead of dying silently
        traceback.print_exc()
        _set(job, status="error", error=f"{type(e).__name__}: {e}"[:600], finished=time.time())


def _page(name: str) -> str:
    built = DIST / name
    return built.read_text() if built.exists() else (WEB / "index.html").read_text()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _page("index.html")


@app.get("/app", response_class=HTMLResponse)
def workspace() -> str:
    return _page("app.html")


for _static in ("assets", "sample"):  # built JS/CSS, and the sample run shown on the site
    if (DIST / _static).is_dir():
        app.mount(f"/{_static}", StaticFiles(directory=DIST / _static), name=_static)


@app.get("/favicon.svg")
def favicon() -> FileResponse:
    if not (DIST / "favicon.svg").exists():
        raise HTTPException(404, "no icon")
    return FileResponse(DIST / "favicon.svg")


@app.get("/api/health")
def health() -> dict:
    from dotenv import load_dotenv

    load_dotenv()
    return {"ok": True, "api_key_configured": bool(os.environ.get("META_API_KEY"))}


MODEL_NAMES = {"sam": "SAM 3.1", "muse-spark": "Muse Spark", "muse-image": "Muse Image"}


@app.get("/api/costs")
def costs() -> list[dict]:
    """Every logged model call, newest first, from the cost ledger."""
    from datetime import datetime

    ledger = OUT / "costs.jsonl"
    rows = []
    for line in ledger.read_text().splitlines() if ledger.exists() else []:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        model = next((v for k, v in MODEL_NAMES.items() if e.get("model", "").startswith(k)), e.get("model"))
        run = (e.get("run") or "").split(":")[0] or None
        rows.append({
            "time": datetime.fromisoformat(e["ts"]).timestamp(),
            "model": model,
            "endpoint": e.get("endpoint", "").split(":")[-1].replace("_", " "),
            "cost_usd": e.get("est_cost_usd") or 0.0,
            "run_id": run if run and (OUT / run / "report.json").exists() else None,
        })
    return sorted(rows, key=lambda r: r["time"], reverse=True)


@app.get("/api/runs")
def list_runs() -> list[dict]:
    runs = [d for d in OUT.glob("*") if d.is_dir() and (d / "report.json").exists() and (d / "key_frame.png").exists()]
    return sorted((_summary(d) for d in runs), key=lambda r: r["created"], reverse=True)


@app.get("/api/runs/{run}")
def get_run(run: str) -> dict:
    d = _run_dir(run)
    return {
        "report": _read(d / "report.json"),
        "diagnosis": _read(d / "diagnosis.json"),
        "visualize": _read(d / "visualize.json"),
        "compare": _read(d / "compare.json"),
        "spectrum": _spectrum(d),
        "files": _files(d),
    }


@app.get("/files/{run}/{name}")
def get_file(run: str, name: str) -> FileResponse:
    if name not in SERVED_FILES:
        raise HTTPException(404, "not served")
    path = _run_dir(run) / name
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)


@app.post("/api/analyze")
async def start_analysis(
    video: UploadFile = File(...),
    prompt: str = Form(""),
    machine: str = Form(""),
    capture_fps: float | None = Form(None),
    duration: float | None = Form(None),
    diagnose: bool = Form(True),
    visualize: bool = Form(True),
    accel: UploadFile | None = File(None),
    manual: UploadFile | None = File(None),
) -> dict:
    job = Job(id=uuid.uuid4().hex[:12])
    up = OUT / "uploads" / job.id
    up.mkdir(parents=True, exist_ok=True)

    def save(f: UploadFile | None) -> Path | None:
        if f is None or not f.filename:
            return None
        path = up / _safe_name(f.filename)
        with path.open("wb") as dst:
            shutil.copyfileobj(f.file, dst)
        return path

    video_path = save(video)
    form = {
        "prompt": prompt.strip(), "machine": machine.strip(), "capture_fps": capture_fps, "duration": duration,
        "diagnose": diagnose, "visualize": visualize, "accel": save(accel), "manual": save(manual),
    }
    with _lock:
        _jobs[job.id] = job
    _pool.submit(_work, job, video_path, form)
    return {"job": job.id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    with _lock:
        d = asdict(job)
        return {**d, "stages": d.pop("done")}  # stages finished so far


class CompareRequest(BaseModel):
    before: str
    after: str
    spark: bool = True


@app.post("/api/compare")
def compare(req: CompareRequest) -> dict:
    from resonance.compare import compare_runs

    before, after = _run_dir(req.before), _run_dir(req.after)
    if before == after:
        raise HTTPException(400, "pick two different runs")
    result = compare_runs(before, after, ask_spark=req.spark)
    return {"result": result, "plot": f"/files/{after.name}/compare.png"}
