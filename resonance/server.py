"""Web app: upload a clip, watch Resonance see, measure, diagnose and show the fix.

    uv run resonance serve            # http://127.0.0.1:8000  (site at /, workspace at /app)

The pages are the React build in web/dist (source in frontend/); without a build the
original single-page app is served instead.

One background worker runs jobs one at a time (analysis is CPU-heavy, and it keeps API spend
predictable). Every run lives in out/<run>/ exactly as the CLI writes it, so CLI and web
runs are interchangeable.

Everything under /api and /files needs an account (resonance/auth.py): a session cookie from
the website, or `Authorization: Bearer rsn_...` from the CLI and the companion app. Each user
sees their own runs; runs nobody owns (made with the CLI on this machine) are shared with
everyone as examples, and the first account (the admin) sees everything. RESONANCE_AUTH=off
turns accounts off for a private single-user install.
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

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from resonance import auth as acct
from resonance import oauth

OUT = Path("out")
WEB = Path(__file__).parent / "web"
DIST = WEB / "dist"
RUN_NAME = re.compile(r"^[\w.-]+$")
EXAMPLE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


def examples_dir() -> Path:
    """Example clips anyone signed in can analyse: <dir>/<id>/example.json plus the files it names."""
    return Path(os.environ.get("RESONANCE_EXAMPLES", "examples"))


def _examples() -> list[dict]:
    out = []
    for f in sorted(examples_dir().glob("*/example.json")):
        try:
            e = json.loads(f.read_text())
        except ValueError:
            continue
        d = f.parent
        if not EXAMPLE_ID.match(d.name) or not (d / e.get("video", "")).is_file():
            continue
        out.append({**e, "id": d.name, "dir": d})
    return sorted(out, key=lambda e: (e.get("order", 99), e["id"]))


def _example(eid: str) -> dict:
    for e in _examples():
        if e["id"] == eid:
            return e
    raise HTTPException(404, "no such example clip")
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
    owner: str | None = None
    started: float = field(default_factory=time.time)
    finished: float | None = None


app = FastAPI(title="Resonance")
_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=1)

# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

COOKIE = "resonance_session"
STATE_COOKIE = "resonance_oauth"
LOCAL_USER = {"id": "local", "email": "local@localhost", "name": "Local", "avatar": None, "admin": 1, "password": None}
_accounts: acct.Accounts | None = None
_devices = acct.DeviceLogins()
_states = oauth.States()


def accounts() -> acct.Accounts:
    global _accounts
    path = OUT / "accounts.db"
    if _accounts is None or _accounts.path != path:
        _accounts = acct.Accounts(path)
    return _accounts


def auth_off() -> bool:
    return os.environ.get("RESONANCE_AUTH", "on").strip().lower() == "off"


def optional_user(request: Request) -> dict | None:
    if auth_off():
        return LOCAL_USER
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return accounts().token_user(header[7:].strip())
    return accounts().session_user(request.cookies.get(COOKIE))


def current_user(request: Request) -> dict:
    user = optional_user(request)
    if user is None:
        raise HTTPException(401, "sign in first")
    return user


def _owner(run: str) -> str | None:
    return None if auth_off() else accounts().owners().get(run)


def showcase_ids() -> set[str]:
    """Accounts whose runs every signed-in user can open (read-only): RESONANCE_SHOWCASE_EMAILS."""
    emails = [e.strip().lower() for e in os.environ.get("RESONANCE_SHOWCASE_EMAILS", "").split(",") if e.strip()]
    return {u["id"] for u in (accounts().by_email(e) for e in emails) if u}


def _visible(user: dict, run: str, owners: dict[str, str] | None = None) -> bool:
    if user["admin"]:
        return True
    owner = (owners if owners is not None else accounts().owners()).get(run)
    return owner is None or owner == user["id"] or owner in showcase_ids()


def _own(user: dict, run: str) -> bool:
    return bool(user["admin"]) or _owner(run) == user["id"]


# ---- spend caps: every paid model call starts from one of the endpoints below ----
LIMITS = {"analysis": ("RESONANCE_DAILY_ANALYSES", 5), "diagnosis": ("RESONANCE_DAILY_DIAGNOSES", 3)}
PLURAL = {"analysis": "analyses", "diagnosis": "diagnoses"}


def _limit(kind: str) -> int:
    env, default = LIMITS[kind]
    try:
        return int(os.environ.get(env, default))
    except ValueError:
        return default


def spent_today() -> float:
    """Model spend so far today (server local date), from the cost ledger."""
    path, day, total = OUT / "costs.jsonl", time.strftime("%Y-%m-%d"), 0.0
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if str(e.get("ts", "")).startswith(day):
                total += float(e.get("est_cost_usd") or 0)
    return total


def _budget() -> float | None:
    v = os.environ.get("RESONANCE_DAILY_BUDGET_USD", "").strip()
    try:
        return float(v) if v else None
    except ValueError:
        return None


def guard_spend(user: dict, *kinds: str) -> None:
    """Refuse a paid job once the account's daily allowance or the site's daily budget is used up.
    Admins and single-user installs (RESONANCE_AUTH=off) have no per-account limit."""
    budget = _budget()
    if budget is not None and spent_today() >= budget:
        raise HTTPException(429, f"this server has used today's model budget (${budget:.2f}); try again tomorrow, or browse the example runs")
    if auth_off() or user.get("admin"):
        return
    for kind in kinds:
        used, cap = accounts().used_today(user["id"], kind), _limit(kind)
        if used >= cap:
            raise HTTPException(429, f"daily limit reached: {cap} {PLURAL[kind]} per account per day; try again tomorrow")
    for kind in kinds:
        accounts().count_use(user["id"], kind)


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", Path(name or "upload").name)[:80]
    return stem or "upload"


def _run_dir(run: str, user: dict | None = None, write: bool = False) -> Path:
    """The run's folder, if it exists and this user may see it (or change it, with write)."""
    if not RUN_NAME.match(run) or not (OUT / run / "report.json").exists():
        raise HTTPException(404, "no such run")
    if user is not None and not _visible(user, run):
        raise HTTPException(404, "no such run")
    if user is not None and write and not _own(user, run):
        raise HTTPException(403, "this is a shared example run; analyse your own clip to diagnose it")
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


def _summary(run_dir: Path, owner: str | None = None, user: dict | None = None, showcase: set[str] | None = None) -> dict:
    r = json.loads((run_dir / "report.json").read_text())
    dx = _read(run_dir / "diagnosis.json")
    mine = bool(user and owner == user["id"])
    return {
        "mine": mine,
        "shared": owner is None or (not mine and owner in (showcase or set())),
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
            start_s=form.get("start"),
            duration_s=form.get("duration") or 10.0,
            on_stage=lambda done: _finish_stage(job, done, nxt.get(done, done)),
        )
        result = analyze(video, opts)
        if job.owner and job.owner != LOCAL_USER["id"]:
            if accounts().user(job.owner) is None:  # the account was deleted while this ran
                shutil.rmtree(OUT / result["run"], ignore_errors=True)
                shutil.rmtree(video.parent, ignore_errors=True)
                _set(job, status="error", error="the account was deleted", finished=time.time())
                return
            accounts().set_owner(result["run"], job.owner)
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


@app.get("/privacy", response_class=HTMLResponse)
def privacy() -> str:
    return _page("privacy.html")


@app.get("/terms", response_class=HTMLResponse)
def terms() -> str:
    return _page("terms.html")


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
def costs(user: dict = Depends(current_user)) -> list[dict]:
    """Logged model calls, newest first, from the cost ledger: every call for the admin, the
    calls for their own runs for everyone else."""
    from datetime import datetime

    ledger = OUT / "costs.jsonl"
    rows = []
    owners = {} if user["admin"] else accounts().owners()
    for line in ledger.read_text().splitlines() if ledger.exists() else []:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        model = next((v for k, v in MODEL_NAMES.items() if e.get("model", "").startswith(k)), e.get("model"))
        run = (e.get("run") or "").split(":")[0] or None
        if not user["admin"] and (run is None or owners.get(run) != user["id"]):
            continue
        rows.append({
            "time": datetime.fromisoformat(e["ts"]).timestamp(),
            "model": model,
            "endpoint": e.get("endpoint", "").split(":")[-1].replace("_", " "),
            "cost_usd": e.get("est_cost_usd") or 0.0,
            "run_id": run if run and (OUT / run / "report.json").exists() else None,
        })
    return sorted(rows, key=lambda r: r["time"], reverse=True)


@app.get("/api/runs")
def list_runs(user: dict = Depends(current_user)) -> list[dict]:
    owners = {} if auth_off() else accounts().owners()
    runs = [d for d in OUT.glob("*") if d.is_dir() and (d / "report.json").exists() and (d / "key_frame.png").exists() and _visible(user, d.name, owners)]
    show = set() if auth_off() else showcase_ids()
    return sorted((_summary(d, owners.get(d.name), user, show) for d in runs), key=lambda r: r["created"], reverse=True)


@app.get("/api/runs/{run}")
def get_run(run: str, user: dict = Depends(current_user)) -> dict:
    d = _run_dir(run, user)
    return {
        "report": _read(d / "report.json"),
        "diagnosis": _read(d / "diagnosis.json"),
        "visualize": _read(d / "visualize.json"),
        "compare": _read(d / "compare.json"),
        "spectrum": _spectrum(d),
        "files": _files(d),
    }


@app.get("/files/{run}/{name}")
def get_file(run: str, name: str, user: dict = Depends(current_user)) -> FileResponse:
    if name not in SERVED_FILES:
        raise HTTPException(404, "not served")
    path = _run_dir(run, user) / name
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)


@app.post("/api/analyze")
async def start_analysis(
    video: UploadFile | None = File(None),
    example: str = Form(""),
    prompt: str = Form(""),
    machine: str = Form(""),
    capture_fps: float | None = Form(None),
    duration: float | None = Form(None),
    diagnose: bool = Form(True),
    visualize: bool = Form(True),
    accel: UploadFile | None = File(None),
    manual: UploadFile | None = File(None),
    user: dict = Depends(current_user),
) -> dict:
    ex = _example(example.strip()) if example.strip() else None
    if ex is None and (video is None or not video.filename):
        raise HTTPException(400, "upload a video, or pick an example clip")
    guard_spend(user, "analysis", *(("diagnosis",) if diagnose else ()))
    job = Job(id=uuid.uuid4().hex[:12], owner=user["id"])
    up = OUT / "uploads" / job.id
    up.mkdir(parents=True, exist_ok=True)

    def save(f: UploadFile | None) -> Path | None:
        if f is None or not f.filename:
            return None
        path = up / _safe_name(f.filename)
        with path.open("wb") as dst:
            shutil.copyfileobj(f.file, dst)
        return path

    def copy(name: str | None) -> Path | None:  # an example's file, linked into this job's folder
        if not name or not (ex["dir"] / name).is_file():
            return None
        dst = up / _safe_name(name)
        try:
            os.link(ex["dir"] / name, dst)
        except OSError:
            shutil.copy2(ex["dir"] / name, dst)
        return dst

    if ex:
        video_path, accel_path, manual_path = copy(ex["video"]), copy(ex.get("accel")), copy(ex.get("manual"))
        prompt, machine = prompt or ex.get("prompt", ""), machine or ex.get("machine", "")
        capture_fps, duration = capture_fps or ex.get("capture_fps"), duration or ex.get("duration")
    else:
        video_path, accel_path, manual_path = save(video), save(accel), save(manual)
    form = {
        "prompt": prompt.strip(), "machine": machine.strip(), "capture_fps": capture_fps, "duration": duration,
        "start": ex.get("start") if ex else None,
        "diagnose": diagnose, "visualize": visualize, "accel": accel_path, "manual": manual_path,
    }
    with _lock:
        _jobs[job.id] = job
    _pool.submit(_work, job, video_path, form)
    return {"job": job.id}


@app.get("/api/examples")
def list_examples(user: dict = Depends(current_user)) -> list[dict]:
    """Ready-made clips (with their sensor recording and manual) for people without their own footage."""
    return [{k: e.get(k) for k in ("id", "title", "note", "prompt", "machine", "duration")}
            | {"file": e["video"], "size_mb": round((e["dir"] / e["video"]).stat().st_size / 1e6, 1), "accel": e.get("accel"), "manual": e.get("manual"),
               "thumb": f"/api/examples/{e['id']}/thumb" if (e["dir"] / "thumb.jpg").is_file() else None} for e in _examples()]


@app.get("/api/examples/{eid}/thumb")
def example_thumb(eid: str, user: dict = Depends(current_user)) -> FileResponse:
    p = _example(eid)["dir"] / "thumb.jpg"
    if not p.is_file():
        raise HTTPException(404, "no thumbnail")
    return FileResponse(p)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, user: dict = Depends(current_user)) -> dict:
    job = _jobs.get(job_id)
    if job is None or not (user["admin"] or job.owner == user["id"]):
        raise HTTPException(404, "no such job")
    with _lock:
        d = asdict(job)
        return {**d, "stages": d.pop("done")}  # stages finished so far


class CompareRequest(BaseModel):
    before: str
    after: str
    spark: bool = True


def _diagnose_work(job: Job, run_dir: Path, manual: Path | None, machine: str | None, visualize: bool) -> None:
    from resonance.diagnose import diagnose
    from resonance.visualize import render_fix

    _set(job, status="running", stage="diagnose")
    try:
        report = json.loads((run_dir / "report.json").read_text())
        diagnose(run_dir, manual=manual, machine_hint=machine or report.get("machine"))
        _finish_stage(job, "diagnose", "visualize" if visualize else "done")
        if visualize:
            render_fix(run_dir)
            _finish_stage(job, "visualize", "done")
        _set(job, status="done", stage="done", finished=time.time())
    except Exception as e:  # report any failure to the page instead of dying silently
        traceback.print_exc()
        _set(job, status="error", error=f"{type(e).__name__}: {e}"[:600], finished=time.time())


@app.post("/api/runs/{run}/diagnose")
async def diagnose_run(
    run: str,
    machine: str = Form(""),
    visualize: bool = Form(True),
    manual: UploadFile | None = File(None),
    user: dict = Depends(current_user),
) -> dict:
    """Diagnose an already-measured run (Muse Spark), then optionally show the fix (Muse Image)."""
    run_dir = _run_dir(run, user, write=True)
    guard_spend(user, "diagnosis")
    job = Job(id=uuid.uuid4().hex[:12], run=run, stage="diagnose", done=[], owner=user["id"])
    manual_path = None
    if manual is not None and manual.filename:
        up = OUT / "uploads" / job.id
        up.mkdir(parents=True, exist_ok=True)
        manual_path = up / _safe_name(manual.filename)
        with manual_path.open("wb") as dst:
            shutil.copyfileobj(manual.file, dst)
    with _lock:
        _jobs[job.id] = job
    _pool.submit(_diagnose_work, job, run_dir, manual_path, machine.strip() or None, visualize)
    return {"job": job.id}


@app.post("/api/compare")
def compare(req: CompareRequest, user: dict = Depends(current_user)) -> dict:
    from resonance.compare import compare_runs

    before, after = _run_dir(req.before, user), _run_dir(req.after, user, write=True)
    if req.spark:
        guard_spend(user)  # the Spark verdict is a few tenths of a cent: only the site budget applies
    if before == after:
        raise HTTPException(400, "pick two different runs")
    result = compare_runs(before, after, ask_spark=req.spark)
    return {"result": result, "plot": f"/files/{after.name}/compare.png"}


# ---------------------------------------------------------------------------
# Account endpoints
# ---------------------------------------------------------------------------


class Credentials(BaseModel):
    email: str
    password: str
    name: str | None = None


class TokenRequest(BaseModel):
    name: str = "token"


class DeviceStart(BaseModel):
    name: str = "Resonance CLI"


class DeviceCode(BaseModel):
    code: str


def _public_base(request: Request) -> str:
    return (os.environ.get("RESONANCE_PUBLIC_URL") or str(request.base_url)).rstrip("/")


def _signed_in(request: Request, user: dict, response: Response) -> dict:
    response.set_cookie(
        COOKIE, accounts().new_session(user["id"]), max_age=acct.SESSION_DAYS * 86400,
        httponly=True, samesite="lax", secure=request.url.scheme == "https", path="/",
    )
    return _me(user)


def _me(user: dict) -> dict:
    providers = [] if user["id"] == LOCAL_USER["id"] else accounts().providers(user["id"])
    usage = None if auth_off() or user.get("admin") else {k: {"used": accounts().used_today(user["id"], k), "limit": _limit(k)} for k in LIMITS}
    return {**acct.public(user), "providers": providers, "auth": not auth_off(), "usage": usage}


def _fail(e: Exception, status: int = 400) -> HTTPException:
    return HTTPException(429 if "too many" in str(e) else status, str(e))


@app.get("/api/auth/config")
def auth_config() -> dict:
    """Which ways to sign in this server offers."""
    return {"required": not auth_off(), "password": True, "providers": oauth.configured()}


@app.get("/api/me")
def me(user: dict = Depends(current_user)) -> dict:
    return _me(user)


@app.delete("/api/me")
def delete_me(response: Response, user: dict = Depends(current_user)) -> dict:
    """Delete the account, its runs and the clips and files uploaded for them."""
    if auth_off():
        raise HTTPException(400, "accounts are off on this server")
    runs = accounts().delete_user(user["id"])
    uploads = (OUT / "uploads").resolve()
    for run in runs:
        run_dir = OUT / run
        if not RUN_NAME.match(run) or not run_dir.is_dir():
            continue
        try:
            report = json.loads((run_dir / "report.json").read_text())
        except (OSError, ValueError):
            report = {}
        src = Path(str(report.get("input") or "")).resolve()  # uploads/<job>/ holds the clip, accelerometer file and manual
        if src.parent.parent == uploads:
            shutil.rmtree(src.parent, ignore_errors=True)
        shutil.rmtree(run_dir, ignore_errors=True)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True, "runs_deleted": len(runs)}


@app.post("/api/auth/signup")
def sign_up(body: Credentials, request: Request, response: Response) -> dict:
    try:
        user = accounts().sign_up(body.email, body.password, body.name)
    except acct.AuthError as e:
        raise _fail(e) from None
    return _signed_in(request, user, response)


@app.post("/api/auth/signin")
def sign_in(body: Credentials, request: Request, response: Response) -> dict:
    try:
        user = accounts().sign_in(body.email, body.password)
    except acct.AuthError as e:
        raise _fail(e, 401) from None
    return _signed_in(request, user, response)


@app.post("/api/auth/signout")
def sign_out(request: Request, response: Response) -> dict:
    if not auth_off():
        accounts().end_session(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.post("/api/auth/token")
def password_token(body: Credentials) -> dict:
    """Email and password -> an access token, for the companion app's sign-in screen."""
    try:
        user = accounts().sign_in(body.email, body.password)
    except acct.AuthError as e:
        raise _fail(e, 401) from None
    raw, info = accounts().new_token(user["id"], body.name or "Companion app")
    return {"token": raw, "info": info, "user": _me(user)}


@app.get("/api/auth/{provider}/start")
def oauth_start(provider: str, request: Request, next: str = "/app") -> RedirectResponse:
    if provider not in ("github", "google"):
        raise HTTPException(404, "unknown provider")
    if not next.startswith("/") or next.startswith("//"):
        next = "/app"
    try:
        state, verifier = _states.new(provider, next)
        url = oauth.authorize_url(provider, f"{_public_base(request)}/api/auth/{provider}/callback", state, verifier)
    except oauth.OAuthError as e:
        raise HTTPException(400, str(e)) from None
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(STATE_COOKIE, state, max_age=oauth.STATE_TTL, httponly=True, samesite="lax", secure=request.url.scheme == "https", path="/")
    return resp


@app.get("/api/auth/{provider}/callback")
def oauth_callback(provider: str, request: Request, code: str = "", state: str = "", error: str = "") -> RedirectResponse:
    from urllib.parse import quote

    def back(msg: str) -> RedirectResponse:
        return RedirectResponse(f"/app?auth_error={quote(msg)}", status_code=302)

    if provider not in acct.PROVIDER_NAMES:
        raise HTTPException(404, "unknown provider")

    if error:
        return back("sign-in was cancelled" if error == "access_denied" else f"{acct.PROVIDER_NAMES[provider]} said: {error}")
    try:
        if not state or request.cookies.get(STATE_COOKIE) != state:
            raise oauth.OAuthError("this sign-in did not start in this browser; try again")
        entry = _states.take(state, provider)
        who = oauth.identity(provider, code, f"{_public_base(request)}/api/auth/{provider}/callback", entry["verifier"])
        user = accounts().sign_in_with(who.provider, who.subject, who.email, who.verified, who.name, who.avatar)
    except (oauth.OAuthError, acct.AuthError) as e:
        return back(str(e))
    except Exception as e:  # network trouble talking to the provider
        traceback.print_exc()
        return back(f"could not reach {acct.PROVIDER_NAMES[provider]} ({type(e).__name__})")
    resp = RedirectResponse(entry["next"], status_code=302)
    _signed_in(request, user, resp)
    resp.delete_cookie(STATE_COOKIE, path="/")
    return resp


@app.get("/api/tokens")
def list_tokens(user: dict = Depends(current_user)) -> list[dict]:
    return accounts().tokens(user["id"])


@app.post("/api/tokens")
def create_token(body: TokenRequest, user: dict = Depends(current_user)) -> dict:
    """A new access token for the CLI or the companion app. The token is shown only once."""
    if auth_off():
        raise HTTPException(400, "accounts are off on this server; no token is needed")
    raw, info = accounts().new_token(user["id"], body.name)
    return {"token": raw, "info": info}


@app.delete("/api/tokens/{token_id}")
def revoke_token(token_id: str, user: dict = Depends(current_user)) -> dict:
    if not accounts().revoke(user["id"], token_id):
        raise HTTPException(404, "no such token")
    return {"ok": True}


@app.post("/api/cli/device")
def device_start(body: DeviceStart, request: Request) -> dict:
    """Step 1 of `resonance login`: a code for the user to approve on the website."""
    d = _devices.start(body.name.strip()[:60] or "Resonance CLI")
    return {**d, "interval": 2, "verification_uri": f"{_public_base(request)}/app#/link?code={d['user_code']}"}


@app.get("/api/cli/device/{user_code}")
def device_info(user_code: str, user: dict = Depends(current_user)) -> dict:
    entry = _devices.lookup(user_code)
    if entry is None:
        raise HTTPException(404, "this code expired or was already used; run resonance login again")
    return {"user_code": entry["user_code"], "name": entry["name"], "approved": entry["token"] is not None}


@app.post("/api/cli/approve")
def device_approve(body: DeviceCode, user: dict = Depends(current_user)) -> dict:
    entry = _devices.lookup(body.code)
    if entry is None or entry["token"] is not None:
        raise HTTPException(404, "this code expired or was already used; run resonance login again")
    raw, _ = accounts().new_token(user["id"], entry["name"])
    _devices.approve(body.code, raw, _me(user))
    return {"ok": True}


@app.post("/api/cli/poll")
def device_poll(body: DeviceCode) -> JSONResponse:
    """Step 2: the CLI asks until the user approves; the token is handed out once."""
    got = _devices.poll(body.code)
    if got is None:
        return JSONResponse({"status": "expired"}, status_code=404)
    if not got:
        return JSONResponse({"status": "pending"}, status_code=202)
    return JSONResponse({"status": "approved", **got})
