"""Command line.

Local, on this machine: analyze, diagnose, visualize, compare, demo, serve, check.
With a Resonance server and your account: login, logout, whoami, upload, runs, pull.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(add_completion=False, help="See, measure and diagnose machine vibration from phone slow-motion video.")


def _parse_box(box: str | None) -> tuple[int, int, int, int] | None:
    if not box:
        return None
    parts = [int(float(v)) for v in box.split(",")]
    if len(parts) != 4:
        raise typer.BadParameter("--box takes x1,y1,x2,y2")
    return tuple(parts)  # type: ignore[return-value]


def _summary(r: dict) -> None:
    v = r["vibration"]
    d = v["dominant"]
    typer.secho(f"\n  Dominant vibration: {d['freq_hz']:.2f} Hz  ({v['dominant_cpm']:.0f} cpm)   SNR {d['snr']:.0f}", bold=True)
    present = [f"{h['order']}x" for h in v["harmonics"] if h["present"]]
    typer.echo(f"  Harmonics present:  {', '.join(present) or 'none'}")
    typer.echo(f"  Video:              {r['video']['fps']:.1f} fps, {r['video']['frames']} frames, Nyquist {r['video']['nyquist_hz']:.1f} Hz")
    if r["accelerometer"]:
        a = r["accelerometer"]
        if a["verifiable"]:
            typer.echo(f"  Accelerometer:      {a['accel_match']['freq_hz']:.2f} Hz  -> error {a['percent_error']:.2f} %  ({a['note']})")
        else:
            typer.echo(f"  Accelerometer:      {a['note']}")
    cost = r["api_cost_usd"]
    typer.echo(f"  API cost:           ${cost['this_run']:.4f} this run, ${cost['all_time']:.4f} all time")
    for w in r["warnings"]:
        typer.secho(f"  ! {w}", fg=typer.colors.YELLOW)
    typer.echo(f"  Outputs:            {Path(r['outputs']['video']).parent}/")


@app.command()
def analyze(
    video: Path = typer.Argument(..., exists=True, dir_okay=False, help="Slow-motion clip from any phone"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help='Part to segment with SAM 3.1, e.g. "motor housing"'),
    accel_csv: Optional[Path] = typer.Option(None, "--accel", exists=True, dir_okay=False, help="phyphox export (CSV or zip) for ground truth"),
    out: Path = typer.Option(Path("out"), help="Output root; each run gets out/<run>/"),
    capture_fps: Optional[float] = typer.Option(None, help="True recording fps, if the file was re-timed on export"),
    start: Optional[float] = typer.Option(None, help="Start time (s) in the clip"),
    duration: Optional[float] = typer.Option(10.0, help="Seconds to analyse (default 10)"),
    max_height: int = typer.Option(1080, help="Downscale taller videos to this height"),
    key_frame: int = typer.Option(0, help="Frame sent to SAM 3.1 for the mask"),
    select: str = typer.Option("largest", help="Which SAM detection to use: largest, confident, all"),
    mask: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, help="Use this mask PNG instead of SAM"),
    box: Optional[str] = typer.Option(None, help="Use a rectangle x1,y1,x2,y2 instead of SAM (offline)"),
    alpha: float = typer.Option(20.0, help="Magnification factor"),
    fmin: float = typer.Option(2.0, help="Ignore frequencies below this (Hz)"),
    fmax: Optional[float] = typer.Option(None, help="Ignore frequencies above this (Hz)"),
    playback_fps: float = typer.Option(30.0, help="Playback fps of the output video (slow motion)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Always call SAM, even for a frame seen before"),
    run_diagnosis: bool = typer.Option(False, "--diagnose", help="Then diagnose with Muse Spark"),
    manual: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, help="Equipment manual PDF for the diagnosis"),
    machine: Optional[str] = typer.Option(None, help='What the machine is, e.g. "desk fan"; runs with the same name are grouped'),
):
    """Segment a part, measure its vibration, magnify it, and compare with an accelerometer."""
    from resonance.pipeline import AnalyzeOptions, analyze as run

    opts = AnalyzeOptions(
        prompt=prompt, machine=machine, accel_path=accel_csv, out_root=out, capture_fps=capture_fps, start_s=start, duration_s=duration,
        max_height=max_height, key_frame=key_frame, select=select, mask_path=mask, box=_parse_box(box), alpha=alpha,
        fmin=fmin, fmax=fmax, playback_fps=playback_fps, use_cache=not no_cache,
    )
    result = run(video, opts)
    _summary(result)
    if run_diagnosis:
        _diagnose(Path(result["outputs"]["video"]).parent, manual, machine, "high", True)


def _diagnose(run_dir: Path, manual: Optional[Path], machine: Optional[str], effort: str, use_audio: bool) -> None:
    from resonance.diagnose import diagnose as run_dx

    typer.echo("\n  Diagnosing with Muse Spark ...")
    r = run_dx(run_dir, manual=manual, machine_hint=machine, effort=effort, use_audio=use_audio)
    dx = r["diagnosis"]
    typer.secho(f"\n  {dx['primary_fault'].replace('_', ' ').upper()}  severity {dx['severity']}  confidence {dx['confidence']:.0%}", bold=True)
    typer.echo(f"  {dx['summary']}")
    for i, a in enumerate(dx["recommended_actions"], 1):
        typer.echo(f"  {i}. {a['step']}")
    cites = dx.get("manual_citations") or []
    if cites:
        ok = sum(1 for c in cites if c.get("verified"))
        typer.echo(f"  Manual citations: {ok}/{len(cites)} verified against the PDF")
    typer.echo(f"  Cost: ${r['api_cost_usd']:.4f}   ->  {run_dir}/diagnosis.md, action_point.png")


@app.command()
def diagnose(
    run_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="An analysis run, e.g. out/<run>"),
    manual: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, help="Equipment manual PDF"),
    machine: Optional[str] = typer.Option(None, help='What the machine is, e.g. "desk fan"'),
    effort: str = typer.Option("high", help="Muse Spark reasoning effort: minimal, low, medium, high, xhigh, max"),
    no_audio: bool = typer.Option(False, "--no-audio", help="Skip the soundtrack"),
):
    """Diagnose an analysed run with Muse Spark: fault, evidence, actions, manual citations."""
    _diagnose(run_dir, manual, machine, effort, not no_audio)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Interface to bind"),
    port: int = typer.Option(8000, help="Port"),
):
    """Run the web app: upload a clip and see every result in the browser."""
    import uvicorn

    typer.echo(f"  Resonance at http://{host}:{port}")
    uvicorn.run("resonance.server:app", host=host, port=port, log_level="warning")


@app.command()
def visualize(
    run_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="A diagnosed run, e.g. out/<run>"),
):
    """Edit the real key frame with Muse Image: where to act, and the fixed state."""
    from resonance.visualize import render_fix

    r = render_fix(run_dir)
    typer.echo(f"  where to act: {r['where_to_act']}\n  fixed state:  {r['fixed_state']}\n  side by side: {r['now_vs_fixed']}\n  cost: ${r['api_cost_usd']:.4f}")


@app.command()
def compare(
    before: Path = typer.Argument(..., exists=True, file_okay=False, help="Run before the fix, e.g. out/<run>"),
    after: Path = typer.Argument(..., exists=True, file_okay=False, help="Run after the fix, same camera position"),
    no_spark: bool = typer.Option(False, "--no-spark", help="Skip the Muse Spark verdict"),
):
    """Rescan after a fix: compare vibration before and after, and judge the repair."""
    from resonance.compare import compare_runs

    r = compare_runs(before, after, ask_spark=not no_spark)
    f = r["fundamental"]
    typer.secho(f"\n  {r['verdict'].replace('_', ' ').upper()}: {r['fault_frequency_hz']:.2f} Hz went {f['before_px']:.3f} -> {f['after_px']:.3f} px ({f['change_pct']:+.0f} %, {f['change_db']:+.1f} dB)", bold=True)
    for h in r["harmonics"][1:]:
        typer.echo(f"  {h['order']}x {h['freq_hz']:.2f} Hz: {h['change_pct']:+.0f} %")
    if r["spark"]:
        typer.echo(f"  Muse Spark: {r['spark']['verdict'].replace('_', ' ')} (matches prediction: {r['spark']['matches_prediction']}). {r['spark']['explanation']}")
    for w in r["warnings"]:
        typer.secho(f"  ! {w}", fg=typer.colors.YELLOW)
    typer.echo(f"  -> {after}/compare.png, compare.json")


@app.command()
def demo(
    out: Path = typer.Option(Path("out"), help="Output root"),
    hz: float = typer.Option(17.0, help="Vibration frequency of the synthetic part"),
):
    """Run the full pipeline offline on a synthetic clip with a known vibration (no API calls)."""
    from resonance.io import write_video
    from resonance.pipeline import AnalyzeOptions, analyze as run
    from resonance.synthetic import Vibration, make_vibrating_clip

    clip = make_vibrating_clip(duration_s=3.0, size=(360, 480), target_vibrations=[Vibration(hz, 0.25, 30.0), Vibration(2 * hz, 0.08, 30.0)])
    src = out / "demo_synthetic.mp4"
    src.parent.mkdir(parents=True, exist_ok=True)
    write_video(src, clip.frames, clip.fps, crf=0)  # lossless: show ground truth, not codec artifacts
    typer.echo(f"synthetic clip: {src} (true vibration {hz} Hz, 0.25 px)")
    _summary(run(src, AnalyzeOptions(out_root=out, run_name="demo", mask_array=clip.target_mask)))


# ---------------------------------------------------------------------------
# Before you upload
# ---------------------------------------------------------------------------


@app.command()
def check(
    videos: list[Path] = typer.Argument(..., exists=True, dir_okay=False, help="One or more clips"),
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of text"),
):
    """Check a clip before analysing it: frame clock, dropped frames, length (free, local)."""
    import json

    from resonance.clipcheck import check as run_check

    results = [run_check(v) for v in videos]
    if as_json:
        typer.echo(json.dumps([r.to_dict() for r in results], indent=1))
    for r in [] if as_json else results:
        verdict = ("READY", typer.colors.GREEN) if r.usable else ("NOT USABLE", typer.colors.RED)
        typer.secho(f"\n  {r.path.name}  {verdict[0]}", fg=verdict[1], bold=True)
        typer.echo(f"  {r.width}x{r.height} {r.codec}, {r.frames} frames, measures up to {r.nyquist_hz:.0f} Hz ({r.nyquist_hz * 60:,.0f} RPM)")
        for level, msg in r.findings:
            mark, color = {"ok": ("  ok ", None), "warn": ("  !  ", typer.colors.YELLOW), "bad": ("  x  ", typer.colors.RED)}[level]
            typer.secho(f"{mark} {msg}", fg=color)
    raise typer.Exit(0 if all(r.usable for r in results) else 1)


# ---------------------------------------------------------------------------
# Your account on a Resonance server
# ---------------------------------------------------------------------------

SERVER = typer.Option(None, "--server", "-s", help="Server URL (default: the one you logged in to, else https://resonance.mindgears.dev)")
TOKEN = typer.Option(None, "--token", help="Access token (default: RESONANCE_TOKEN, else the saved login)")


def _client(server: str | None, token: str | None):
    from resonance.remote import Client

    return Client(server, token)


def _remote(fn):
    """Run a server command, turning server errors into a short message."""
    from resonance.remote import RemoteError

    try:
        return fn()
    except RemoteError as e:
        typer.secho(f"  {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from None


@app.command()
def login(
    server: Optional[str] = SERVER,
    token: Optional[str] = typer.Option(None, "--token", help="Save this access token (from Settings) instead of approving in the browser"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Print the link instead of opening it"),
):
    """Sign this computer in to your account on a Resonance server."""
    import socket
    import webbrowser

    from resonance import remote

    c = _client(server, token)

    def show(code: str, url: str) -> None:
        typer.echo(f"\n  Approve this computer in the browser:\n  {url}\n\n  Check the code matches: ", nl=False)
        typer.secho(code, bold=True)
        if not no_browser:
            webbrowser.open(url)
        typer.echo("  Waiting for approval...")

    if token:
        me = _remote(c.me)
    else:
        me = _remote(lambda: c.device_login(f"resonance CLI on {socket.gethostname()}", show)["user"])
    path = remote.save(c.server, c.token, me.get("email"))
    typer.secho(f"\n  Signed in to {c.server} as {me.get('email')}", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Saved to {path} (only you can read it). Revoke it any time in Settings > Access tokens.")


@app.command()
def logout():
    """Forget the saved login on this computer (revoke the token itself in Settings)."""
    from resonance import remote

    typer.echo("  Signed out." if remote.forget() else "  Not signed in.")


@app.command()
def whoami(server: Optional[str] = SERVER, token: Optional[str] = TOKEN):
    """Show which account and server the CLI uses."""
    c = _client(server, token)
    me = _remote(c.me)
    typer.echo(f"  {me['name']} <{me['email']}>{'  (admin)' if me.get('admin') else ''} on {c.server}")


@app.command()
def upload(
    video: Path = typer.Argument(..., exists=True, dir_okay=False, help="Slow-motion clip"),
    prompt: str = typer.Option(..., "--prompt", "-p", help='Part to segment with SAM 3.1, e.g. "fan"'),
    machine: Optional[str] = typer.Option(None, help='Machine name, e.g. "NUUK LIT v2 table fan"; runs with the same name are grouped'),
    accel_csv: Optional[Path] = typer.Option(None, "--accel", exists=True, dir_okay=False, help="phyphox export (CSV or zip)"),
    manual: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, help="Equipment manual PDF"),
    duration: float = typer.Option(10.0, help="Seconds to analyse"),
    capture_fps: Optional[float] = typer.Option(None, help="True recording fps, if the file was re-timed on export"),
    no_diagnose: bool = typer.Option(False, "--no-diagnose", help="Measure only; skip Muse Spark (and the fix images)"),
    no_visualize: bool = typer.Option(False, "--no-visualize", help="Skip the Muse Image fix pictures"),
    skip_check: bool = typer.Option(False, "--skip-check", help="Upload even if the clip check fails"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Start the job and return"),
    server: Optional[str] = SERVER,
    token: Optional[str] = TOKEN,
):
    """Analyse a clip on the server, in your account, and print the report link."""
    from resonance.clipcheck import check as run_check

    if not skip_check:
        ck = run_check(video)
        if not ck.usable:
            for level, msg in ck.findings:
                if level == "bad":
                    typer.secho(f"  x  {msg}", fg=typer.colors.RED, err=True)
            typer.echo("  Not uploaded. Use --skip-check to upload anyway.", err=True)
            raise typer.Exit(1)
    c = _client(server, token)
    fields = {"prompt": prompt, "machine": machine or "", "duration": duration, "capture_fps": capture_fps,
              "diagnose": not no_diagnose, "visualize": not (no_diagnose or no_visualize)}
    typer.echo(f"  Uploading {video.name} ({video.stat().st_size / 1e6:.0f} MB) to {c.server} ...")
    job = _remote(lambda: c.upload(video, fields, accel_csv, manual))
    if no_wait:
        typer.echo(f"  Started job {job}. Follow it in Runs on {c.server}/app")
        return
    j = _remote(lambda: c.wait(job, lambda s: typer.echo(f"  done: {s}")))
    if j["status"] == "error":
        typer.secho(f"  Failed: {j['error']}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    d = _remote(lambda: c.run(j["run"]))
    v = d["report"]["vibration"]["dominant"]
    typer.secho(f"\n  {v['freq_hz']:.2f} Hz ({v['freq_hz'] * 60:,.0f} cpm), SNR {v['snr']:.0f}", bold=True)
    dx = (d.get("diagnosis") or {}).get("diagnosis")
    if dx:
        typer.echo(f"  {dx['primary_fault'].replace('_', ' ')}, {dx['severity'].replace('_', ' ')}, confidence {dx['confidence']:.0%}")
    for w in d["report"].get("warnings", []):
        typer.secho(f"  ! {w}", fg=typer.colors.YELLOW)
    typer.echo(f"  Report: {c.report_url(j['run'])}")


@app.command()
def runs(
    limit: int = typer.Option(20, help="How many to list"),
    server: Optional[str] = SERVER,
    token: Optional[str] = TOKEN,
):
    """List your runs on the server, newest first."""
    from datetime import datetime

    c = _client(server, token)
    rows = _remote(c.runs)
    if not rows:
        typer.echo("  No runs yet. Try: resonance upload clip.MOV --prompt fan")
    for r in rows[:limit]:
        when = datetime.fromtimestamp(r["created"]).strftime("%Y-%m-%d %H:%M")
        fault = (r.get("fault") or "not diagnosed").replace("_", " ")
        tag = "" if r.get("mine") else "  [shared example]" if r.get("shared") else ""
        typer.echo(f"  {when}  {r['run']:<36} {r['freq_hz']:>8.2f} Hz  {(r.get('machine') or r.get('prompt') or ''):<24.24} {fault}{tag}")


@app.command()
def pull(
    run: str = typer.Argument(..., help="Run id, from `resonance runs`"),
    to: Path = typer.Option(Path("out"), help="Folder to download into; the run lands in <to>/<run>/"),
    server: Optional[str] = SERVER,
    token: Optional[str] = TOKEN,
):
    """Download a run's report, diagnosis, images and magnified video."""
    c = _client(server, token)
    files = _remote(lambda: c.download(run, to / run))
    typer.echo(f"  {len(files)} files -> {to / run}/")


if __name__ == "__main__":
    app()
