"""Is this clip good enough to measure? A free, local check of a video before uploading it.

It reads only the container (ffprobe) and the frame timestamps: the true frame clock (240 for
iPhone slow motion), how many frames were dropped in low light, length, size, and the
iPhone's 30 fps "edited" copy that AirDrop sends by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from resonance import frequency as fq
from resonance import io as rio

ANALYSED_S = 10.0  # the default window `analyze` and the website measure


@dataclass
class Check:
    path: Path
    width: int
    height: int
    codec: str
    duration_s: float
    frames: int
    clock_fps: float  # the camera's frame clock
    arrived_fps: float  # frames that actually arrived, per second
    retimed_from: float | None  # Android files store slow motion at playback speed
    findings: list[tuple[str, str]] = field(default_factory=list)  # (ok | warn | bad, message)

    @property
    def usable(self) -> bool:
        return not any(level == "bad" for level, _ in self.findings)

    @property
    def nyquist_hz(self) -> float:
        return self.clock_fps / 2  # measured on the true frame times, so dropped frames do not lower it

    def to_dict(self) -> dict:
        return {
            "file": self.path.name, "width": self.width, "height": self.height, "codec": self.codec,
            "duration_s": round(self.duration_s, 2), "frames": self.frames, "clock_fps": round(self.clock_fps, 2),
            "arrived_fps": round(self.arrived_fps, 2), "retimed_from": self.retimed_from,
            "max_hz": round(self.nyquist_hz, 1), "usable": self.usable,
            "findings": [{"level": lvl, "message": msg} for lvl, msg in self.findings],
        }


def check(path: str | Path) -> Check:
    info = rio.probe(path)
    t = rio.frame_timestamps(path)
    span = float(t[-1] - t[0]) if t.size > 1 else info.duration_s
    clock = fq.clock_rate(t) if t.size > 2 else info.nominal_fps
    arrived = (t.size - 1) / span if span > 0 else info.avg_fps
    scale = 1.0
    if info.capture_fps and info.capture_fps > clock * 1.5:  # stored slower than it was filmed
        scale = info.capture_fps / clock
        clock, arrived, span = info.capture_fps, arrived * scale, span / scale
    c = Check(Path(path), info.width, info.height, info.codec, span, int(t.size), clock, arrived, info.capture_fps if scale != 1.0 else None)
    f = c.findings

    if c.retimed_from:
        f.append(("ok", f"slow motion stored at playback speed; measured on the true {c.retimed_from:.0f} fps clock"))
    if clock < 100:
        tip = ("this looks like the iPhone's edited 30 fps copy: AirDrop the clip with Options > All Photos Data and use IMG_xxxx.MOV, not IMG_Exxxx"
               if Path(path).name.upper().startswith("IMG_E") or round(clock) == 30
               else "record in Slo-mo at 240 fps (iPhone: Settings > Camera > Record Slo-mo)")
        f.append(("bad", f"filmed at {clock:.0f} fps, so nothing above {clock / 2:.0f} Hz can be measured; {tip}"))
    else:
        f.append(("ok", f"slow motion: {clock:.0f} fps frame clock"))
    dropped = 1 - arrived / clock if clock else 0.0
    if dropped > 0.15:
        f.append(("warn", f"{dropped:.0%} of frames were dropped ({arrived:.0f} fps arrived on a {clock:.0f} fps clock), "
                          "which phones do in dim light: add light; Resonance still uses the true frame times"))
    if span < 3:
        f.append(("bad", f"only {span:.1f} s long: record at least 5 s, ideally 10-15 s"))
    elif span < 8:
        f.append(("warn", f"{span:.1f} s long: 10-15 s gives sharper frequency resolution"))
    else:
        f.append(("ok", f"{span:.1f} s long; the first {min(span, ANALYSED_S):.0f} s are analysed"))
    if min(info.width, info.height) < 720:
        f.append(("warn", f"{info.width}x{info.height} is small: tiny vibrations need 1080p"))
    return c
