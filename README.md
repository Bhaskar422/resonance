# Resonance

Point a phone at a running machine, film it in slow motion, and Resonance shows you the
vibration you can't see, measures its frequency, and tells you what is wrong.

1. **See**: Segment Anything Model 3.1 (SAM 3.1) finds the part you name ("motor housing",
   "fan guard"). Motion magnification is then applied *only inside that mask*, so invisible
   shaking becomes visible.
2. **Measure**: the vibration frequency (Hz) comes straight from the pixels inside the mask,
   checked against a phone accelerometer (phyphox) as ground truth.
3. **Diagnose**: Muse Spark combines the measurements, the magnified video, the audio and the
   equipment manual into an evidence-backed diagnosis. Every manual quote it cites is checked
   against the PDF.
4. **Show the fix**: Muse Image edits the real frame to show where to act and what the fixed
   machine looks like.
5. **Check the fix**: film again after the repair; Resonance compares the vibration before and
   after, and Muse Spark judges whether the repair did what the diagnosis predicted.

Entry for the Meta Global AI Developer Hackathon (Indie Developer track).

## Built during the hackathon (Oct 27 – Nov 4, 2026)

All code in this repository was written during the hackathon. The git history is the record.

| Component | Path | What it does |
|---|---|---|
| Project scaffold | `pyproject.toml`, `LICENSE`, `README.md` | uv packaging, Apache-2.0 |
| Synthetic test clips | `resonance/synthetic.py` | Textured square vibrating at known sub-pixel amplitudes, plus a distractor outside the mask |
| Frequency measurement | `resonance/frequency.py` | Lucas–Kanade motion inside a mask, FFT spectrum, peak refinement, harmonic detection robust to codec artifacts |
| Masked motion magnification | `resonance/magnify.py` | Streaming linear Eulerian magnification (from the paper), applied only inside the mask |
| Video I/O for any phone | `resonance/io.py` | Rotation, HDR tone-mapping, VFR timestamps, re-timed slow-mo correction, lossless frame streaming |
| Accelerometer ground truth | `resonance/accel.py` | phyphox CSV/zip (iOS and Android formats), video-vs-sensor comparison with Nyquist checks |
| Meta Model API client and cost ledger | `resonance/api.py` | Every call logged to `out/costs.jsonl` with an estimated cost; refuses Contributor-mode models |
| SAM 3.1 client | `resonance/sam_client.py` | Image and video segmentation over the Responses API, decoded with `meta_sam_parser` |
| Analysis pipeline and CLI | `resonance/pipeline.py`, `resonance/cli.py`, `resonance/report.py` | `resonance analyze` and `resonance demo`, side-by-side video, spectrum plot, `report.json` |
| Diagnosis | `resonance/diagnose.py`, `resonance/audio.py` | Muse Spark 1.3 strict-schema fault report from measurements, video, spectrum, key frame and manual; Muse Spark 1.2 listens to the soundtrack; manual citations verified against the PDF |
| Fix visualization | `resonance/visualize.py` | Muse Image edits of the real key frame: where to act, and the fixed state |
| Rescan after fix | `resonance/compare.py` | Before/after amplitude at the fault frequency and harmonics, verdict, Muse Spark check against the diagnosis's prediction |
| Web API | `resonance/server.py` | Upload, background jobs with per-stage progress, runs, files, rescan comparison, cost ledger |
| Web app | `frontend/` (built into `resonance/web/dist/`), `scripts/export_sample.py` | React + Tailwind: marketing site, dashboard, machines, guided analysis, run report, certificate of fix, recording guide, usage & cost, settings |
| API probes | `scripts/probe_*.py` | Print raw API responses to verify schemas before relying on them |
| Tests | `tests/` | 55 tests, all offline |

## Setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), ffmpeg on `PATH`.

```bash
uv sync
cp .env.example .env   # then put your Meta Model API key in META_API_KEY
```

## Usage

```bash
# Offline sanity check: full pipeline on a synthetic clip with a known 17 Hz vibration
uv run resonance demo

# A real clip: SAM 3.1 segments the part, then measure, magnify and compare
uv run resonance analyze samples/fan.mov --prompt "motor housing" --accel samples/phyphox.zip

# No API: give the region yourself
uv run resonance analyze samples/fan.mov --box 400,300,900,700

# Diagnose (Muse Spark), then show the fix on the real frame (Muse Image)
uv run resonance diagnose out/<run> --manual samples/fan_manual.pdf --machine "desk fan"
uv run resonance visualize out/<run>

# After the repair, film again from the same spot and compare
uv run resonance compare out/<before-run> out/<after-run>

# Or do everything in the browser
uv run resonance serve        # site at http://127.0.0.1:8000, workspace at /app
```

### Web app

The built app is committed in `resonance/web/dist/`, so `resonance serve` needs no JavaScript
toolchain. To change it, edit `frontend/` and rebuild with [Bun](https://bun.sh):

```bash
cd frontend
bun install
bun run dev      # http://localhost:5173, proxies /api and /files to resonance serve on :8000
bun run build    # writes resonance/web/dist
```

The workspace starts in **Live** mode (your runs from `out/`). Settings → Data source switches to
**Sample** mode, which shows labelled sample and demo data without a backend.

Each run writes `out/<run>/`:

| File | Contents |
|---|---|
| `side_by_side.mp4` | Original and magnified, mask outlined, played back in slow motion |
| `spectrum.png` | Vibration spectrum from the video (and the accelerometer, when given) |
| `report.json` | fps, dominant Hz, harmonics, accelerometer match and % error, warnings, API cost |
| `mask_overlay.png`, `mask.png` | The segmented part |
| `signals.npz` | Raw displacement signals and timestamps |
| `diagnosis.json`, `diagnosis.md`, `action_point.png` | Muse Spark diagnosis (after `diagnose`) |
| `where_to_act.png`, `fixed_state.png`, `now_vs_fixed.png` | Muse Image edits (after `visualize`) |
| `compare.json`, `compare.png` | Rescan comparison (after `compare`, in the after-run folder) |

Run `uv run resonance analyze --help` for all options (`--capture-fps` for re-timed slow-mo,
`--start`/`--duration`, `--alpha`, `--fmin`/`--fmax`, `--select`).

### Recording a clip (iPhone or Android)

1. Put the phone on a tripod that does **not** touch the machine or its table. Resonance
   measures the camera too (a ring around the mask) and warns if the camera shakes.
2. Record in slow motion at 240 fps, in good light, for 5–10 s.
3. Transfer the original file. iPhone: AirDrop, or share with "All Photos Data" enabled.
   Android: copy the file over USB. If a clip was saved at normal speed, pass
   `--capture-fps 240`.
4. Optional ground truth: lay a second phone on the machine, record "Acceleration (without g)"
   in [phyphox](https://phyphox.org), and export CSV. iPhones sample at about 100 Hz, so only
   frequencies below about 50 Hz can be checked against them.

### API probes

```bash
uv run python scripts/probe_models.py                                      # free
uv run python scripts/probe_sam_image.py samples/fan.mov --prompt "motor housing"   # $0.0025
uv run python scripts/probe_sam_video.py samples/fan.mov --prompt "fan blade"       # ~$0.05
uv run python scripts/probe_image_gen.py "a desk fan on a table" --out samples/fan.png  # $0.01
uv run python scripts/probe_spark_video.py out/<run>/side_by_side.mp4 out/<run>/spectrum.png  # ~$0.01
```

## Third-party credits and licenses

| Material | Use | License |
|---|---|---|
| [Meta Model API](https://dev.meta.ai/docs) (SAM 3.1, Muse Spark, Muse Image) | Hosted models called over HTTPS | Meta Model API terms |
| [meta-sam-parser](https://github.com/meta-models/meta-sam) | Parses SAM 3.1 output (pip dependency, not vendored) | [SAM License](https://github.com/meta-models/meta-sam/blob/main/LICENSE) |
| NumPy, SciPy | Numerics, FFT, filters | BSD-3-Clause |
| OpenCV (`opencv-python`) | Video decoding, image pyramids | Apache-2.0 |
| Matplotlib | Spectrum plots | Matplotlib License (BSD-style) |
| Typer | CLI | MIT |
| OpenAI Python SDK | HTTP client for the OpenAI-compatible Meta Model API | Apache-2.0 |
| python-dotenv | Loads `.env` | BSD-3-Clause |
| pypdf | Reads manual text to verify citations | BSD-3-Clause |
| FastAPI, Starlette | Web API | MIT, BSD-3-Clause |
| Uvicorn | Web server | BSD-3-Clause |
| python-multipart | Upload parsing | Apache-2.0 |
| React, React DOM | Web app UI | MIT |
| Vite, @vitejs/plugin-react | Web app build | MIT |
| Tailwind CSS | Web app styling | MIT |
| [IBM Plex Sans and Mono](https://github.com/IBM/plex) | Web app typefaces (loaded from Google Fonts) | SIL Open Font License 1.1 |
| FFmpeg | Video probing and decoding (external binary, not distributed) | LGPL/GPL |

Methods implemented from the literature (our own code, no reference implementations used):

- H.-Y. Wu, M. Rubinstein, E. Shih, J. Guttag, F. Durand, W. T. Freeman. *Eulerian Video
  Magnification for Revealing Subtle Changes in the World.* ACM SIGGRAPH 2012.
- B. D. Lucas, T. Kanade. *An Iterative Image Registration Technique with an Application to
  Stereo Vision.* IJCAI 1981.
- G. Farnebäck. *Two-Frame Motion Estimation Based on Polynomial Expansion.* SCIA 2003
  (via OpenCV, as a cross-check).

## License

Apache-2.0. See [LICENSE](LICENSE).
