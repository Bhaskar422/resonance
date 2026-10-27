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

| Component | Path | Status |
|---|---|---|
| Project scaffold | `pyproject.toml`, `README.md`, `LICENSE` | done |

## Setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), ffmpeg on `PATH`.

```bash
uv sync
cp .env.example .env   # then put your Meta Model API key in META_API_KEY
```

## Usage

```bash
uv run resonance analyze samples/fan.mov --prompt "motor housing" --accel samples/phyphox.csv
```

Outputs go to `out/<run>/`.

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
| FFmpeg | Video probing and transcoding (external binary) | LGPL/GPL |

## License

Apache-2.0. See [LICENSE](LICENSE).
