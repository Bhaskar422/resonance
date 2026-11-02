"""Web app: upload a clip, watch Resonance see, measure, diagnose and show the fix.

    uv run resonance serve            # http://127.0.0.1:8000

One background worker runs jobs one at a time (analysis is CPU-heavy, and it keeps API spend
predictable). Every run lives in out/<run>/ exactly as the CLI writes it, so CLI and web
runs are interchangeable.
"""

from __future__ import annotations

import json
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
from pydantic import BaseModel

OUT = Path("out")
WEB = Path(__file__).parent / "web"
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


def _files(run_dir: Path) -> dict[str, str]:
    return {n: f"/files/{run_dir.name}/{n}" for n in sorted(SERVED_FILES) if (run_dir / n).exists()}


def _summary(run_dir: Path) -> dict:
    r = json.loads((run_dir / "report.json").read_text())
    dx = _read(run_dir / "diagnosis.json")
    return {
        "run": r["run"],
        "created": (run_dir / "report.json").stat().st_mtime,
        "input": Path(r["input"]).name,
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


def _work(job: Job, video: Path, form: dict) -> None:
    from resonance.diagnose import diagnose
    from resonance.pipeline import AnalyzeOptions, analyze
    from resonance.visualize import render_fix

    _set(job, status="running", stage="prepare")
    try:
        nxt = {s: STAGES[i + 1] for i, s in enumerate(STAGES[:-1])}
        opts = AnalyzeOptions(
            prompt=form["prompt"] or None,
            accel_path=form.get("accel"),
            out_root=OUT,
            capture_fps=form.get("capture_fps"),
            duration_s=form.get("duration") or 10.0,
            on_stage=lambda done: _set(job, stage=nxt.get(done, done)),
        )
        result = analyze(video, opts)
        _set(job, run=result["run"])
        run_dir = OUT / result["run"]
        if form["diagnose"]:
            _set(job, stage="diagnose")
            diagnose(run_dir, manual=form.get("manual"), machine_hint=form.get("machine") or None)
            if form["visualize"]:
                _set(job, stage="visualize")
                render_fix(run_dir)
        _set(job, status="done", stage="done", finished=time.time())
    except Exception as e:  # report any failure to the page instead of dying silently
        traceback.print_exc()
        _set(job, status="error", error=f"{type(e).__name__}: {e}"[:600], finished=time.time())


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB / "index.html").read_text()


@app.get("/api/runs")
def list_runs() -> list[dict]:
    runs = [d for d in OUT.glob("*") if d.is_dir() and (d / "report.json").exists() and (d / "key_frame.png").exists()]
    return [_summary(d) for d in sorted(runs, key=lambda d: (d / "report.json").stat().st_mtime, reverse=True)]


@app.get("/api/runs/{run}")
def get_run(run: str) -> dict:
    d = _run_dir(run)
    return {
        "report": _read(d / "report.json"),
        "diagnosis": _read(d / "diagnosis.json"),
        "visualize": _read(d / "visualize.json"),
        "compare": _read(d / "compare.json"),
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
        return {**asdict(job), "stages": STAGES}


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
