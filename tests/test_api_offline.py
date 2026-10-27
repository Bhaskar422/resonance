"""Offline tests for the API layer: cost estimates, ledger, and SAM output parsing.
No network calls; the SAM sample line is the documented example from
https://dev.meta.ai/docs/sam/reading-segmentation."""

import json

import numpy as np
import pytest

from resonance import api, sam_client

DOC_LINE = (
    "<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x(|>"
    ",1<|box;x1=155;y1=228;x2=202;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,48,~!!!!J!0c[q=Pj_zs=*4C4(/./x#:/`S_GnD`=o3?X{emCgO$y@|>"
)


def test_cost_estimates_follow_published_prices():
    assert api.estimate_cost("sam-3.1", {}, {"images": 1}) == pytest.approx(0.0025)
    assert api.estimate_cost("sam-3.1", {"video_frames_processed": 1200}) == pytest.approx(0.24)
    assert api.estimate_cost("sam-3.1", {}, {"video_frames": 10}) == pytest.approx(0.01)  # 50-frame minimum
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "input_tokens_details": {"cached_tokens": 200_000}}
    assert api.estimate_cost("muse-spark-1.3", usage) == pytest.approx(0.8 * 1.25 + 0.2 * 0.15 + 0.1 * 4.25)
    assert api.estimate_cost("muse-image-1.0", {}, {"images": 2}) == pytest.approx(0.02)


def test_contributor_models_are_refused():
    with pytest.raises(api.APIError):
        api.check_model("muse-spark-1.3-contributor")


def test_ledger_appends_jsonl(tmp_path):
    ledger = api.CostLedger(tmp_path / "costs.jsonl", run_id="r1")
    ledger.record("sam-3.1", "responses:image", {"total_tokens": 0}, {"images": 1})
    ledger.record("sam-3.1", "responses:video", {"video_frames_processed": 500})
    lines = [json.loads(x) for x in (tmp_path / "costs.jsonl").read_text().splitlines()]
    assert [x["run"] for x in lines] == ["r1", "r1"]
    assert ledger.run_total == pytest.approx(0.0025 + 0.1)
    assert ledger.all_time_total() == pytest.approx(0.1025)


def test_parses_documented_sam_output_into_full_frame_masks():
    dets = sam_client.parse_output(DOC_LINE, "image")
    assert [d.object_id for d in dets] == ["0", "1"]
    d0 = dets[0]
    assert d0.box == (211, 228, 271, 255)  # x2/y2 inclusive on the wire -> half-open here
    assert d0.local_mask.shape == (27, 60)
    full = d0.full_mask((334, 320))
    ys, xs = np.nonzero(full)
    assert xs.min() >= 211 and xs.max() < 271 and ys.min() >= 228 and ys.max() < 255
    assert full.sum() == d0.area

    union = sam_client.select_mask(dets, (334, 320), "all")
    assert union.sum() == dets[0].area + dets[1].area
    assert sam_client.select_mask(dets, (334, 320), "largest").sum() == max(d.area for d in dets)
    assert sam_client._source_size(DOC_LINE) == (334, 320)


def test_video_output_keeps_frame_indices():
    raw = DOC_LINE + "\n" + DOC_LINE.replace("<0f>", "<5f>") + "\n"
    dets = sam_client.parse_output(raw, "video")
    assert sorted({d.frame_index for d in dets}) == [0, 5]


def test_empty_detection_list_is_a_clear_error():
    with pytest.raises(api.APIError, match="found nothing"):
        sam_client.select_mask([], (10, 10))
