# Resonance

Point a phone at a running machine, film it in slow motion, and Resonance shows you the
vibration you can't see, measures its frequency, and tells you what is wrong.

1. **See**: Segment Anything Model 3.1 (SAM 3.1) finds the part you name ("motor housing",
   "fan guard"). Motion magnification is then applied *only inside that mask*, so invisible
   shaking becomes visible.
2. **Measure**: the vibration frequency (Hz) comes straight from the pixels inside the mask,
   checked against a phone accelerometer (phyphox) as ground truth.
3. **Diagnose** *(in progress)*: Muse Spark combines the magnified video, the audio and the
   equipment manual into an evidence-backed diagnosis.

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
| API probes | `scripts/probe_*.py` | Print raw API responses to verify schemas before relying on them |
| Tests | `tests/` | 38 tests, all offline |

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
```

Each run writes `out/<run>/`:

| File | Contents |
|---|---|
| `side_by_side.mp4` | Original and magnified, mask outlined, played back in slow motion |
| `spectrum.png` | Vibration spectrum from the video (and the accelerometer, when given) |
| `report.json` | fps, dominant Hz, harmonics, accelerometer match and % error, warnings, API cost |
| `mask_overlay.png`, `mask.png` | The segmented part |
| `signals.npz` | Raw displacement signals and timestamps |

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
