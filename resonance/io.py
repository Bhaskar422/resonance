"""Video in and out, for clips from any phone.

Phone slow-motion files vary a lot: iPhones record HEVC, often 10-bit HDR (HLG or Dolby
Vision), and Android phones often write variable frame rate. Both platforms store rotation
as metadata, and a slow-mo clip can be re-timed on export so that 240 fps footage claims to
be 30 fps. Measuring Hz from pixels needs the *true* time of every frame, so:

1. :func:`probe` reads the container: frame rates, rotation, HDR transfer, capture-fps tags.
2. :func:`prepare` transcodes once to an 8-bit H.264 working copy with rotation applied and
   HDR tone-mapped (the same file is what SAM 3.1 receives), keeping every frame's original
   timestamp, then corrects the timeline when the clip was re-timed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import cv2
import numpy as np

from resonance.frequency import is_uniform

MIN_SLOWMO_FPS = 120.0
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}  # PQ (HDR10 / Dolby Vision) and HLG


class VideoError(RuntimeError):
    pass


def _run(cmd: list[str]) -> str:
    if shutil.which(cmd[0]) is None:
        raise VideoError(f"{cmd[0]} not found on PATH; install ffmpeg")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise VideoError(f"{cmd[0]} failed: {res.stderr.strip()[-2000:]}")
    return res.stdout


def _ratio(s: str | None) -> float:
    if not s or s in ("0/0", "N/A"):
        return 0.0
    num, _, den = s.partition("/")
    return float(num) / float(den or 1) if float(den or 1) else 0.0


@dataclass
class VideoInfo:
    path: Path
    width: int  # display size, after rotation
    height: int
    rotation: int  # degrees from the display matrix
    codec: str
    pix_fmt: str
    color_transfer: str
    nominal_fps: float  # r_frame_rate
    avg_fps: float
    n_frames: int
    duration_s: float
    capture_fps: float | None  # slow-mo capture rate from metadata, when present
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def is_hdr(self) -> bool:
        return self.color_transfer in HDR_TRANSFERS

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "tags"}
        d["path"] = str(self.path)
        d["is_hdr"] = self.is_hdr
        return d


def _capture_fps_from_tags(tags: dict[str, str]) -> float | None:
    # Android writes com.android.capture.fps for high-speed recordings.
    for k, v in tags.items():
        if k.lower().endswith("capture.fps"):
            try:
                fps = float(v)
            except ValueError:
                continue
            if fps > 0:
                return fps
    return None


def probe(path: str | Path) -> VideoInfo:
    path = Path(path)
    if not path.exists():
        raise VideoError(f"no such file: {path}")
    out = json.loads(_run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]))
    video = [s for s in out.get("streams", []) if s.get("codec_type") == "video"]
    if not video:
        raise VideoError(f"{path} has no video stream")
    s = video[0]
    rotation = 0
    for sd in s.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(round(float(sd["rotation"])))
    if not rotation and "rotate" in s.get("tags", {}):
        rotation = -int(s["tags"]["rotate"])
    w, h = int(s["width"]), int(s["height"])
    if rotation % 180:
        w, h = h, w
    tags = {**out.get("format", {}).get("tags", {}), **s.get("tags", {})}
    duration = float(s.get("duration") or out.get("format", {}).get("duration") or 0.0)
    avg_fps = _ratio(s.get("avg_frame_rate"))
    n_frames = int(s.get("nb_frames") or 0) or int(round(duration * avg_fps))
    return VideoInfo(
        path=path,
        width=w,
        height=h,
        rotation=rotation,
        codec=s.get("codec_name", "?"),
        pix_fmt=s.get("pix_fmt", "?"),
        color_transfer=s.get("color_transfer", "unknown"),
        nominal_fps=_ratio(s.get("r_frame_rate")),
        avg_fps=avg_fps,
        n_frames=n_frames,
        duration_s=duration,
        capture_fps=_capture_fps_from_tags(tags),
        tags=tags,
    )


def frame_timestamps(path: str | Path) -> np.ndarray:
    """Presentation time (s) of every video frame, in display order, starting at 0."""
    out = _run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)])
    t = np.sort(np.array([float(x) for x in out.split() if x.strip() not in ("", "N/A")]))
    if t.size == 0:
        raise VideoError(f"could not read frame timestamps from {path}")
    return t - t[0]


@cache
def _has_filter(name: str) -> bool:
    out = _run(["ffmpeg", "-hide_banner", "-filters"])
    return any(line.split()[1:2] == [name] for line in out.splitlines() if len(line.split()) > 1)


@dataclass
class PreparedVideo:
    path: Path  # 8-bit H.264 working copy, rotation applied
    source: VideoInfo
    timestamps: np.ndarray  # true capture time of each frame (s), from 0
    fs: float  # effective sample rate (frames per second of real time)
    time_scale: float  # 1.0, or the re-timing correction applied to file timestamps
    width: int
    height: int
    warnings: list[str] = field(default_factory=list)

    @property
    def nyquist_hz(self) -> float:
        return self.fs / 2

    @property
    def is_vfr(self) -> bool:
        return not is_uniform(self.timestamps)

    def to_dict(self) -> dict:
        return {
            "working_copy": str(self.path),
            "source": self.source.to_dict(),
            "frames": int(self.timestamps.size),
            "fps": round(self.fs, 3),
            "nyquist_hz": round(self.nyquist_hz, 3),
            "variable_frame_rate": self.is_vfr,
            "time_scale": self.time_scale,
            "width": self.width,
            "height": self.height,
            "warnings": self.warnings,
        }


def prepare(
    src: str | Path,
    workdir: str | Path,
    *,
    max_height: int = 1080,
    capture_fps: float | None = None,
    start_s: float | None = None,
    duration_s: float | None = None,
) -> PreparedVideo:
    """Transcode ``src`` into a normalized working copy and recover true frame timing.

    ``capture_fps`` overrides the frame rate the footage was *recorded* at, for clips whose
    file timestamps were stretched on export (e.g. a 240 fps slow-mo saved as 30 fps).
    """
    info = probe(src)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "working.mp4"
    warnings: list[str] = []

    filters = []
    if info.is_hdr:
        if _has_filter("zscale") and _has_filter("tonemap"):
            filters.append(
                "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv"
            )
        else:
            warnings.append("HDR source but ffmpeg lacks zscale/tonemap; colours will look flat (measurement unaffected)")
    if info.height > max_height:
        filters.append(f"scale=-2:{max_height}")
    filters.append("format=yuv420p")

    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start_s:
        cmd += ["-ss", str(start_s)]
    cmd += ["-i", str(src)]
    if duration_s:
        cmd += ["-t", str(duration_s)]
    # Keep every frame and its exact timestamp: passthrough stops frame dropping/duplication,
    # and the demuxer time base stops the encoder snapping VFR timestamps onto a 1/fps grid.
    cmd += ["-map", "0:v:0", "-an", "-vf", ",".join(filters), "-fps_mode", "passthrough", "-enc_time_base:v", "demux"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-movflags", "+faststart", str(out)]
    _run(cmd)

    t = frame_timestamps(out)
    if t.size < 2:
        raise VideoError("clip has fewer than 2 frames")
    file_fs = 1.0 / float(np.median(np.diff(t)))

    time_scale = 1.0
    claimed = capture_fps or info.capture_fps
    if claimed and claimed > 1.5 * file_fs:
        time_scale = file_fs / claimed
        source = "--capture-fps" if capture_fps else "capture-fps metadata"
        warnings.append(
            f"clip was re-timed: file plays at {file_fs:.1f} fps but was captured at {claimed:.1f} fps "
            f"({source}); timestamps scaled by {time_scale:.4f}"
        )
    elif capture_fps and abs(capture_fps - file_fs) > 0.05 * file_fs:
        warnings.append(f"--capture-fps {capture_fps} ignored: it is not higher than the file's {file_fs:.1f} fps")
    t = t * time_scale
    fs = 1.0 / float(np.median(np.diff(t)))

    if not is_uniform(t):
        warnings.append("variable frame rate: the motion signal is resampled to a uniform time grid")
    if fs < MIN_SLOWMO_FPS:
        warnings.append(
            f"only {fs:.1f} fps (Nyquist {fs / 2:.1f} Hz). Record in slow motion (240 fps) for reliable results; "
            "if this is a slow-mo clip saved at normal speed, pass --capture-fps"
        )

    cap = cv2.VideoCapture(str(out))
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return PreparedVideo(out, info, t, fs, time_scale, width, height, warnings)


def iter_frames(path: str | Path, *, start: int = 0, stop: int | None = None) -> Iterator[np.ndarray]:
    """Decode BGR uint8 frames in order."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise VideoError(f"OpenCV cannot open {path}")
    try:
        i = 0
        while stop is None or i < stop:
            ok, frame = cap.read()
            if not ok:
                break
            if i >= start:
                yield frame
            i += 1
    finally:
        cap.release()


def read_frame(path: str | Path, index: int) -> np.ndarray:
    for frame in iter_frames(path, start=index, stop=index + 1):
        return frame
    raise VideoError(f"{path} has no frame {index}")


class VideoWriter:
    """Writes BGR frames to an H.264 MP4 that plays in browsers, through an ffmpeg pipe."""

    def __init__(self, path: str | Path, fps: float, *, crf: int = 18, extra_metadata: dict[str, str] | None = None):
        self.path = Path(path)
        self.fps = fps
        self.crf = crf
        self.metadata = extra_metadata or {}
        self._proc: subprocess.Popen | None = None
        self._shape: tuple[int, int] | None = None

    def _open(self, h: int, w: int) -> None:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{self.fps}", "-i", "-"]
        cmd += ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(self.crf), "-pix_fmt", "yuv420p"]
        for k, v in self.metadata.items():
            cmd += ["-metadata", f"{k}={v}"]
        if self.metadata:
            cmd += ["-movflags", "+use_metadata_tags"]
        cmd += [str(self.path)]
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self._shape = (h, w)

    def write(self, frame: np.ndarray) -> None:
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if self._proc is None:
            self._open(*frame.shape[:2])
        if frame.shape[:2] != self._shape:
            raise ValueError(f"frame size changed from {self._shape} to {frame.shape[:2]}")
        self._proc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())

    def close(self) -> None:
        if self._proc is None:
            return
        self._proc.stdin.close()
        err = self._proc.stderr.read().decode()
        if self._proc.wait() != 0:
            raise VideoError(f"ffmpeg failed writing {self.path}: {err[-2000:]}")
        self._proc = None

    def __enter__(self) -> "VideoWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def write_video(path: str | Path, frames, fps: float, **kw) -> Path:
    with VideoWriter(path, fps, **kw) as w:
        for f in frames:
            w.write(f)
    return Path(path)
