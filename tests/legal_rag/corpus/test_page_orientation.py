"""Source coordinate preservation for an upstream four-way orientation classifier."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from legal_rag.corpus.pdf_extraction import normalize_dotsmocr  # noqa: E402
from test_pdf_extraction import DIGEST, looped_result, rotated_result, saved_result  # noqa: E402


POLICY = {"package": "rapid-orientation", "version": "0.0.11", "backend": "CPUExecutionProvider",
          "model_sha256": "2f62c9bfb830a0b417241269fde7ef2d0ad5446c0ed2b8af33b1f6543545e8e2",
          "direction": "counterclockwise", "min_confidence": 0.85, "score": "minimum_crop_probability"}


def oriented_result(angle=270, factory=saved_result):
    document, run = factory()
    page = document["pages"][0]
    width, height = page["image_size"]
    # Existing layout/native describe the image actually sent to dots.mocr.
    page["image_size"] = [height, width] if angle in (90, 270) else [width, height]
    page["page_orientation"] = {"angle": angle, "predicted_angle": angle, "confidence": 0.99,
                                "image_size": [width, height]}
    run["config"]["page_orientation"] = copy.deepcopy(POLICY)
    for other in document["pages"][1:]:
        other["page_orientation"] = {"angle": 0, "predicted_angle": 0, "confidence": 0.99,
                                     "image_size": other["image_size"]}
    for cell in page["layout"]:
        left, top, right, bottom = cell["bbox"]
        if angle:
            cell["oriented_bbox"] = cell["bbox"]
            cell["bbox"] = {90: [height-bottom, left, height-top, right],
                            180: [width-right, height-bottom, width-left, height-top],
                            270: [top, width-right, bottom, width-left]}[angle]
    return document, run


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("factory", [saved_result, looped_result, rotated_result])
def test_orientation_composes_with_native_recovery_and_preserves_source_boxes(angle, factory):
    document, run = oriented_result(angle, factory)
    before = copy.deepcopy(document)
    result = normalize_dotsmocr(document, run, DIGEST)
    page = result["pages"][0]
    assert page["page_orientation"] == document["pages"][0]["page_orientation"]
    assert page["image_size"] == document["pages"][0]["image_size"]
    assert [r["bbox"] for r in page["regions"]] == [r["bbox"] for r in document["pages"][0]["layout"]]
    assert document == before


@pytest.mark.parametrize("mutation", ["angle", "boolean", "size", "bbox", "text", "policy", "missing"])
def test_orientation_rejects_inconsistent_retained_evidence(mutation):
    document, run = oriented_result()
    page = document["pages"][0]
    if mutation == "angle":
        page["page_orientation"]["angle"] = 45
    elif mutation == "boolean":
        page["page_orientation"]["angle"] = True
    elif mutation == "size":
        page["page_orientation"]["image_size"] = [200, 300]
    elif mutation == "bbox":
        page["layout"][0]["bbox"][0] += 1
    elif mutation == "text":
        page["layout"][0]["text"] = "Подмена текста"
    elif mutation == "policy":
        run["config"]["page_orientation"]["model_sha256"] = "bad"
    else:
        del page["page_orientation"]
    with pytest.raises(ValueError, match="orientation|oriented"):
        normalize_dotsmocr(document, run, DIGEST)


def test_orientation_cannot_hide_incomplete_primary_response():
    document, run = oriented_result()
    page = document["pages"][0]
    page["native"]["choices"][0]["finish_reason"] = "length"
    with pytest.raises(ValueError, match="truncated"):
        normalize_dotsmocr(document, run, DIGEST)


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_orientation_accepts_recovered_timeout_after_stop_but_before_stream_done(angle):
    document, run = oriented_result(angle, lambda: looped_result(primary="timeout"))
    document["pages"][0]["native"]["choices"][0]["finish_reason"] = "stop"
    assert normalize_dotsmocr(document, run, DIGEST)["pages"][0]["loop_retry"]


@pytest.mark.parametrize("confidence,accepted", [(0.2669, True), (0.85, False), (float('nan'), False)])
def test_uncertain_prediction_keeps_source_orientation_and_cannot_disguise_a_confident_turn(confidence, accepted):
    document, run = oriented_result(0)
    document["pages"][0]["page_orientation"].update(predicted_angle=180, confidence=confidence)
    if accepted:
        assert normalize_dotsmocr(document, run, DIGEST)["pages"][0]["page_orientation"]["angle"] == 0
    else:
        with pytest.raises(ValueError, match="orientation"):
            normalize_dotsmocr(document, run, DIGEST)
