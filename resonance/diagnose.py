"""Evidence-backed diagnosis with Muse Spark.

Muse Spark 1.3 receives everything Resonance measured, as numbers and as media: the
measurement report, the original|magnified video, the vibration spectrum, the key frame with
the analysed part outlined, and the equipment manual PDF. It returns a structured fault
report under a strict JSON schema. The soundtrack goes to Muse Spark 1.2 (audio is not yet
fully supported on 1.3), and its description joins the evidence.

Nothing the model says about the manual is taken on trust: every quoted passage is looked up
in the PDF's text and marked verified (with the page it was actually found on) or not.
"""

from __future__ import annotations

import base64
import difflib
import json
import re
from pathlib import Path

import cv2

from resonance import audio as audio_mod
from resonance.api import CostLedger, check_model, get_client

DIAGNOSIS_MODEL = "muse-spark-1.3"
AUDIO_MODEL = "muse-spark-1.2"

FAULT_TYPES = [
    "imbalance", "misalignment", "mechanical_looseness", "bent_shaft", "bearing_defect",
    "blade_or_aerodynamic", "electrical", "resonance", "rubbing", "none_detected", "other",
]
EVIDENCE_SOURCES = ["spectrum", "harmonics", "magnified_video", "original_video", "audio", "accelerometer", "manual", "camera_reference"]

DIAGNOSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "machine", "summary", "primary_fault", "severity", "confidence", "rotation", "faults",
        "recommended_actions", "action_point", "manual_citations", "fixed_state_description",
        "fix_image_prompt", "rescan_expectation", "uncertainties",
    ],
    "properties": {
        "machine": {"type": "string", "description": "What the machine is, as identified from the video and manual"},
        "summary": {"type": "string", "description": "Two sentences for a technician: what is wrong and what to do"},
        "primary_fault": {"type": "string", "enum": FAULT_TYPES},
        "severity": {"type": "string", "enum": ["normal", "monitor", "act_soon", "stop_now"]},
        "confidence": {"type": "number", "description": "0 to 1"},
        "rotation": {
            "type": "object",
            "additionalProperties": False,
            "required": ["rated_rpm", "rated_rpm_source", "measured_hz", "relation"],
            "properties": {
                "rated_rpm": {"type": ["number", "null"], "description": "Rated speed if the manual or nameplate gives one"},
                "rated_rpm_source": {"type": ["string", "null"], "description": "Where the rated speed came from (manual page, nameplate)"},
                "measured_hz": {"type": "number", "description": "Dominant vibration frequency measured from the video"},
                "relation": {"type": "string", "description": "How the measured frequency relates to running speed (e.g. '1x running speed')"},
            },
        },
        "faults": {
            "type": "array",
            "description": "Candidate faults, most likely first",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["fault_type", "likelihood", "frequency_hz", "harmonic_relation", "supporting_evidence", "contradicting_evidence"],
                "properties": {
                    "fault_type": {"type": "string", "enum": FAULT_TYPES},
                    "likelihood": {"type": "number", "description": "0 to 1"},
                    "frequency_hz": {"type": ["number", "null"]},
                    "harmonic_relation": {"type": "string"},
                    "supporting_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["source", "detail"],
                            "properties": {"source": {"type": "string", "enum": EVIDENCE_SOURCES}, "detail": {"type": "string"}},
                        },
                    },
                    "contradicting_evidence": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "recommended_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["step", "where", "manual_page"],
                "properties": {
                    "step": {"type": "string"},
                    "where": {"type": "string", "description": "The location on the machine, as visible in the key frame"},
                    "manual_page": {"type": ["integer", "null"]},
                },
            },
        },
        "action_point": {
            "type": "object",
            "additionalProperties": False,
            "required": ["x", "y", "label"],
            "properties": {
                "x": {"type": "integer", "description": "0-1000, left to right across the key frame"},
                "y": {"type": "integer", "description": "0-1000, top to bottom across the key frame"},
                "label": {"type": "string", "description": "Short label for the spot to act on, e.g. 'balance weight on blade 2'"},
            },
        },
        "manual_citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["page", "quote", "relevance"],
                "properties": {
                    "page": {"type": "integer", "description": "1-based page number in the PDF file"},
                    "quote": {"type": "string", "description": "Verbatim text copied from that page, at most 30 words"},
                    "relevance": {"type": "string"},
                },
            },
        },
        "fixed_state_description": {"type": "string", "description": "What the machine looks like once fixed"},
        "fix_image_prompt": {
            "type": "string",
            "description": "Instruction for an image editor applied to the key frame, showing the fixed state; keep everything else unchanged",
        },
        "rescan_expectation": {"type": "string", "description": "What should change in the spectrum after the fix"},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
}

INSTRUCTIONS = """You are a senior vibration analyst. Diagnose the machine from the evidence below.

Evidence you receive:
1. MEASUREMENTS (JSON): vibration measured from the video's pixels inside a segmented part.
   Frequencies are exact; amplitudes are in pixels (relative, not mm/s). Harmonics flagged
   "present" passed significance tests. "camera_reference" is the motion of the background
   around the part; a high ratio means camera shake, not machine vibration.
   "light_flicker_peaks" are the room light flickering, not vibration; ignore them.
2. A video: original (left) and motion-magnified (right) in slow motion, the analysed part
   outlined. Use it to see the shape of the motion (rocking, wobble, twisting) and any visible
   cause (attachments on blades, loose parts, missing screws).
3. The vibration spectrum image, and the key frame with the analysed part outlined.
4. AUDIO findings, when present: tonal peaks (with their ratio to the vibration frequency)
   and a listener's description.
5. ACCELEROMETER comparison, when present (ground truth from a phone on the machine). That
   phone, and any cloth or tape holding it, may be visible on or under the machine: it is the
   measuring sensor, not part of the machine and not a fault. Never recommend removing it.
6. The equipment manual PDF, when present.

Standard rules of thumb (apply them, but let the evidence decide):
- Dominant 1x running speed, mostly radial, low harmonics: imbalance (mass on one side).
- Strong 2x (and 1x): misalignment or bent shaft; many harmonics or sub-harmonics: looseness.
- Number-of-blades x running speed: blade-pass (aerodynamic); 2x line frequency (100/120 Hz):
  electrical. Non-synchronous high frequencies: bearings.

Requirements:
- Every claim must cite evidence you were given. Put conflicts in contradicting_evidence and
  unknowns in uncertainties; never invent measurements.
- Manual citations: copy the quote verbatim from the PDF (at most 30 words) and give the
  1-based PDF page number. Use an empty list when no manual is given or nothing relevant is in it.
  If the manual states a rated speed, use it to relate the measured frequency to running speed.
- recommended_actions: first the step that removes the primary fault's cause on the machine
  itself (for imbalance: stop the machine and inspect the rotating part for added, missing or
  shifted mass, dirt build-up, damaged or loosely seated blades, then clean or rebalance it);
  checks of mounting and setup come after.
- action_point: the single spot on the KEY FRAME (0-1000 coordinates) where the technician
  should act on the primary fault's cause.
- fix_image_prompt: an edit instruction for that key frame showing the fixed state, changing
  only what the fix changes.
"""

AUDIO_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["description", "character", "irregular"],
    "properties": {
        "description": {"type": "string", "description": "What the machine sounds like, in one or two sentences"},
        "character": {"type": "array", "items": {"type": "string", "enum": ["steady_hum", "tonal_whine", "rhythmic_thump", "rattle", "scrape_or_grind", "clicking", "whoosh_airflow", "silent", "other"]}},
        "irregular": {"type": "boolean", "description": "True if the sound pulses, wobbles or changes over time"},
    },
}


def _json_format(name: str, schema: dict) -> dict:
    return {"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}}


def _data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def describe_audio(client, wav: Path, ledger: CostLedger) -> dict:
    data = base64.b64encode(wav.read_bytes()).decode()
    resp = client.responses.create(
        model=check_model(AUDIO_MODEL),
        input=[{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": "This is a recording of a running machine. Describe how it sounds, as a maintenance technician would."},
            {"type": "input_audio", "input_audio": {"data": data, "format": "wav"}},
        ]}],
        reasoning={"effort": "low"},
        max_output_tokens=4000,
        text=_json_format("audio_description", AUDIO_SCHEMA),
    )
    ledger.record(AUDIO_MODEL, "responses:audio", resp.usage, note="audio description")
    return json.loads(resp.output_text)


# ---------------------------------------------------------------------------
# Manual citation verification
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


def pdf_pages(pdf: Path) -> list[str]:
    from pypdf import PdfReader

    pages = []
    for p in PdfReader(str(pdf)).pages:
        try:  # a page pypdf cannot parse (huge drawing streams) just can't verify quotes
            pages.append(_norm(p.extract_text() or ""))
        except Exception:
            pages.append("")
    return pages


def _match_score(quote: str, page: str) -> float:
    if not quote or not page:
        return 0.0
    if quote in page:
        return 1.0
    sm = difflib.SequenceMatcher(None, page, quote, autojunk=False)
    blocks = sm.get_matching_blocks()
    return sum(b.size for b in blocks) / len(quote)


def verify_citations(citations: list[dict], pages: list[str], threshold: float = 0.85) -> list[dict]:
    """Mark each citation verified when its quote is found in the PDF text; correct the page
    number when the quote is on a different page than claimed."""
    out = []
    for c in citations:
        q = _norm(c.get("quote", ""))
        claimed = c.get("page")
        scores = [_match_score(q, p) for p in pages]
        best = max(range(len(scores)), key=scores.__getitem__) if scores else None
        on_claimed = scores[claimed - 1] if isinstance(claimed, int) and 1 <= claimed <= len(pages) else 0.0
        verified = on_claimed >= threshold or (best is not None and scores[best] >= threshold)
        found = claimed if on_claimed >= threshold else (best + 1 if verified else None)
        out.append({**c, "verified": verified, "found_on_page": found, "match_score": round(max(on_claimed, scores[best] if best is not None else 0.0), 3)})
    return out


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def _measurements_for_model(report: dict, accel_present: bool) -> dict:
    v = report["vibration"]
    keep = {
        "video": {k: report["video"][k] for k in ("fps", "nyquist_hz", "frames", "variable_frame_rate", "warnings")},
        "segmented_part": {k: report["mask"].get(k) for k in ("prompt", "source", "area_px", "measured_area_px", "fast_motion_excluded_fraction")},
        "dominant": v["dominant"],
        "dominant_cpm": v["dominant_cpm"],
        "motion_direction_deg": v["direction_deg"],
        "harmonics": v["harmonics"],
        "top_peaks": v["top_peaks"],
        "light_flicker_peaks": v.get("light_flicker_peaks", []),
        "camera_reference": v["camera_reference"],
        "magnification": report["magnification"],
    }
    if accel_present:
        keep["accelerometer"] = report["accelerometer"]
    return keep


def diagnose(run_dir: str | Path, *, manual: Path | None = None, machine_hint: str | None = None, effort: str = "high", use_audio: bool = True) -> dict:
    run_dir = Path(run_dir)
    report = json.loads((run_dir / "report.json").read_text())
    ledger = CostLedger(Path(report.get("api_cost_ledger", "out/costs.jsonl")), run_id=report["run"] + ":diagnose")
    client = get_client()
    f0 = report["vibration"]["dominant"]["freq_hz"]

    # Audio: local tonal analysis plus Muse Spark 1.2's description.
    audio_findings = None
    src = Path(report["input"])
    if use_audio and src.exists():
        wav = audio_mod.extract_wav(src, run_dir / "audio.wav", start_s=report.get("start_s"), duration_s=min(report.get("duration_s") or 20.0, 20.0))
        if wav is not None:
            retimed = report["video"].get("time_scale", 1.0) != 1.0
            audio_findings = {
                "tonal_peaks": audio_mod.tones_to_dicts(audio_mod.tonal_peaks(wav, f0=None if retimed else f0)),
                "note": "clip was re-timed; audio frequencies may be stretched" if retimed else None,
            }
            try:
                audio_findings["listener"] = describe_audio(client, wav, ledger)
            except Exception as e:  # audio is supporting evidence; never block the diagnosis on it
                audio_findings["listener_error"] = str(e)[:300]

    # Key frame, scaled for the model, with its size so action_point maps back exactly.
    key = cv2.imread(str(run_dir / "mask_overlay.png"))
    key_h, key_w = key.shape[:2]

    content = [
        {"type": "input_text", "text": INSTRUCTIONS},
        {"type": "input_text", "text": "MEASUREMENTS:\n" + json.dumps(_measurements_for_model(report, bool(report.get("accelerometer"))), indent=1)},
    ]
    if machine_hint:
        content.append({"type": "input_text", "text": f"The operator says the machine is: {machine_hint}"})
    if audio_findings:
        content.append({"type": "input_text", "text": "AUDIO:\n" + json.dumps(audio_findings, indent=1)})

    uploads = []
    with (run_dir / "side_by_side.mp4").open("rb") as f:
        uploads.append(client.files.create(file=f, purpose="user_data").id)
    content.append({"type": "input_text", "text": "VIDEO: original (left) and magnified (right), slow motion."})
    content.append({"type": "input_video", "file_id": uploads[-1]})
    content.append({"type": "input_text", "text": "SPECTRUM:"})
    content.append({"type": "input_image", "image_url": _data_url(run_dir / "spectrum.png", "image/png")})
    content.append({"type": "input_text", "text": f"KEY FRAME ({key_w}x{key_h}), analysed part outlined:"})
    content.append({"type": "input_image", "image_url": _data_url(run_dir / "mask_overlay.png", "image/png")})
    if manual:
        with Path(manual).open("rb") as f:
            uploads.append(client.files.create(file=f, purpose="user_data").id)
        content.append({"type": "input_text", "text": f"EQUIPMENT MANUAL ({Path(manual).name}):"})
        content.append({"type": "input_file", "file_id": uploads[-1]})

    resp = client.responses.create(
        model=check_model(DIAGNOSIS_MODEL),
        input=[{"type": "message", "role": "user", "content": content}],
        reasoning={"effort": effort},
        max_output_tokens=16000,
        text=_json_format("vibration_diagnosis", DIAGNOSIS_SCHEMA),
    )
    cost = ledger.record(DIAGNOSIS_MODEL, "responses:diagnosis", resp.usage, note=f"effort={effort}")
    if resp.status != "completed":
        raise RuntimeError(f"diagnosis did not complete: {resp.status} {getattr(resp, 'incomplete_details', None)}")
    dx = json.loads(resp.output_text)

    if manual:
        try:
            pages = pdf_pages(Path(manual))
        except Exception:  # an unreadable PDF leaves the quotes unverified, never loses the diagnosis
            pages = []
        dx["manual_citations"] = verify_citations(dx["manual_citations"], pages)
    ap = dx["action_point"]
    dx["action_point_px"] = {"x": round(ap["x"] / 1000 * key_w), "y": round(ap["y"] / 1000 * key_h)}
    result = {
        "diagnosis": dx,
        "audio": audio_findings,
        "model": DIAGNOSIS_MODEL,
        "reasoning_effort": effort,
        "manual": str(manual) if manual else None,
        "usage": resp.usage.model_dump(exclude_none=True) if resp.usage else None,
        "api_cost_usd": round(ledger.run_total, 4),
        "diagnosis_call_cost_usd": round(cost or 0.0, 4),
    }
    (run_dir / "diagnosis.json").write_text(json.dumps(result, indent=2))
    _annotate_action(run_dir, dx)
    (run_dir / "diagnosis.md").write_text(to_markdown(result, report))
    return result


def _annotate_action(run_dir: Path, dx: dict) -> None:
    img = cv2.imread(str(run_dir / "mask_overlay.png"))
    p = dx["action_point_px"]
    r = max(12, img.shape[1] // 60)
    cv2.circle(img, (p["x"], p["y"]), r, (0, 0, 255), 3, cv2.LINE_AA)
    cv2.circle(img, (p["x"], p["y"]), 3, (0, 0, 255), -1, cv2.LINE_AA)
    label = dx["action_point"]["label"][:60]
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    x0 = min(max(p["x"] + r + 8, 0), img.shape[1] - tw - 16)
    y0 = min(max(p["y"] - th // 2 - 8, 0), img.shape[0] - th - 16)
    cv2.rectangle(img, (x0, y0), (x0 + tw + 16, y0 + th + 16), (24, 24, 24), -1)
    cv2.putText(img, label, (x0 + 8, y0 + th + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 239, 236), 2, cv2.LINE_AA)
    cv2.imwrite(str(run_dir / "action_point.png"), img)


def to_markdown(result: dict, report: dict) -> str:
    dx = result["diagnosis"]
    lines = [
        f"# Diagnosis: {dx['machine']}",
        "",
        f"**{dx['primary_fault'].replace('_', ' ')}** · severity **{dx['severity'].replace('_', ' ')}** · confidence {dx['confidence']:.0%}",
        "",
        dx["summary"],
        "",
        f"Measured: {report['vibration']['dominant']['freq_hz']:.2f} Hz ({report['vibration']['dominant_cpm']:.0f} cpm). {dx['rotation']['relation']}",
        "",
        "## Candidate faults",
    ]
    for f in dx["faults"]:
        lines.append(f"- **{f['fault_type'].replace('_', ' ')}** ({f['likelihood']:.0%}): {f['harmonic_relation']}")
        lines += [f"  - [{e['source']}] {e['detail']}" for e in f["supporting_evidence"]]
        lines += [f"  - against: {c}" for c in f["contradicting_evidence"]]
    lines += ["", "## What to do"]
    for i, a in enumerate(dx["recommended_actions"], 1):
        page = f" (manual p. {a['manual_page']})" if a["manual_page"] else ""
        lines.append(f"{i}. {a['step']}. *Where:* {a['where']}{page}")
    if dx["manual_citations"]:
        lines += ["", "## Manual citations"]
        for c in dx["manual_citations"]:
            mark = "verified" if c.get("verified") else ("NOT FOUND in PDF" if "verified" in c else "unverified")
            page = c.get("found_on_page") or c["page"]
            lines.append(f"- p. {page} ({mark}): \"{c['quote']}\" ({c['relevance']})")
    lines += ["", "## After the fix", dx["fixed_state_description"], "", f"Rescan should show: {dx['rescan_expectation']}"]
    if dx["uncertainties"]:
        lines += ["", "## Uncertainties"] + [f"- {u}" for u in dx["uncertainties"]]
    lines += ["", f"*Muse Spark 1.3, reasoning effort {result['reasoning_effort']}, API cost ${result['api_cost_usd']:.4f}*"]
    return "\n".join(lines) + "\n"
