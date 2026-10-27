"""Command line: ``resonance analyze`` and ``resonance demo``."""

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
):
    """Segment a part, measure its vibration, magnify it, and compare with an accelerometer."""
    from resonance.pipeline import AnalyzeOptions, analyze as run

    opts = AnalyzeOptions(
        prompt=prompt, accel_path=accel_csv, out_root=out, capture_fps=capture_fps, start_s=start, duration_s=duration,
        max_height=max_height, key_frame=key_frame, select=select, mask_path=mask, box=_parse_box(box), alpha=alpha,
        fmin=fmin, fmax=fmax, playback_fps=playback_fps, use_cache=not no_cache,
    )
    _summary(run(video, opts))


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


if __name__ == "__main__":
    app()
