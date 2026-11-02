"""Offline checks for the diagnosis helpers: manual citation verification and audio peaks."""

import numpy as np
import pytest
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from scipy.io import wavfile

from resonance import audio, diagnose


@pytest.fixture
def manual_pdf(tmp_path):
    path = tmp_path / "manual.pdf"
    pages = [
        "Model DF-30 Desk Fan. Safety instructions. Unplug before cleaning.",
        "Specifications: rated speed 1250 rpm on high. If the fan wobbles or vibrates, check that the blade is seated and the spinner cap is tight.",
    ]
    with PdfPages(path) as pdf:
        for text in pages:
            fig = plt.figure(figsize=(8.5, 11))
            fig.text(0.05, 0.9, text, wrap=True, fontsize=10)
            pdf.savefig(fig)
            plt.close(fig)
    return path


def test_citations_are_verified_and_page_corrected(manual_pdf):
    pages = diagnose.pdf_pages(manual_pdf)
    cites = [
        {"page": 2, "quote": "rated speed 1250 rpm on high", "relevance": "running speed"},
        {"page": 1, "quote": "check that the blade is seated and the spinner cap is tight", "relevance": "fix"},  # actually on page 2
        {"page": 2, "quote": "replace the motor bearings every 500 hours", "relevance": "invented"},
    ]
    out = diagnose.verify_citations(cites, pages)
    assert [c["verified"] for c in out] == [True, True, False]
    assert out[0]["found_on_page"] == 2
    assert out[1]["found_on_page"] == 2  # corrected from the claimed page 1
    assert out[2]["found_on_page"] is None


def test_audio_tonal_peaks_report_ratio_to_vibration(tmp_path):
    sr = audio.SAMPLE_RATE
    t = np.arange(4 * sr) / sr
    rng = np.random.default_rng(0)
    x = 0.3 * np.sin(2 * np.pi * 57.0 * t) + 0.1 * np.sin(2 * np.pi * 120.0 * t) + 0.02 * rng.standard_normal(t.size)
    wav = tmp_path / "a.wav"
    wavfile.write(wav, sr, (x * 32767 / np.abs(x).max()).astype(np.int16))
    tones = audio.tonal_peaks(wav, f0=19.0)
    assert tones[0].freq_hz == pytest.approx(57.0, abs=0.6)
    assert tones[0].ratio_to_f0 == pytest.approx(3.0, abs=0.05)  # blade-pass of a 3-blade fan
    assert any(abs(t.freq_hz - 120.0) < 0.6 for t in tones)


def test_diagnosis_schema_is_strict_compatible():
    # Strict subset: every object lists all its properties as required and forbids extras.
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(diagnose.DIAGNOSIS_SCHEMA)
    walk(diagnose.AUDIO_SCHEMA)


def test_action_labels_are_shortened_at_word_boundaries():
    from resonance.visualize import short_label

    assert short_label("fan hub / blade assembly - inspect and balance") == "fan hub / blade assembly"
    assert short_label("the left rear mounting bolt of the motor bracket near the base") == "the left rear mounting bolt of"
    assert short_label("blade 2") == "blade 2"
