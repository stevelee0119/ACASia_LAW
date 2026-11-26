"""TK-243 unit tests: exact non-whitespace character counts (chars, raw_chars, preprocessed_chars) in page_quality and RapidOCR dual comparison."""
from __future__ import annotations

import numpy as np

from packages.common.schemas import BBox
from packages.document_engine.ocr import (
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    RapidOCRAdapter,
    build_ocr_page_telemetry,
    page_quality,
)


def _sample_image() -> np.ndarray:
    img = np.full((120, 200, 3), 235, dtype=np.uint8)
    img[20:45, 20:140] = 35
    return img


def _make_adapter(raw_items: list[tuple[str, float]], pre_items: list[tuple[str, float]]) -> RapidOCRAdapter:
    adapter = RapidOCRAdapter()
    adapter.available = True
    adapter._ensure_engine = lambda: True  # type: ignore[method-assign]
    box = [[0, 0], [100, 0], [100, 20], [0, 20]]
    calls = 0

    def _engine(_img):
        nonlocal calls
        calls += 1
        items = raw_items if calls == 1 else pre_items
        return ([[box, text, conf] for text, conf in items], None)

    adapter._engine = _engine
    return adapter


def test_tk243_pos1_raw_only_recognized_counts_exact_chars():
    """양성 1: 원본(raw)만 인식되고 전처리본은 빈 결과일 때 raw_chars는 인식 글자 수(공백·잡음 제외), preprocessed_chars는 0이다."""
    # "손해배상 청구 원문" -> 공백 제거 8자, "---"는 잡음 줄로 제외
    adapter = _make_adapter([("손해배상 청구 원문", 0.78), ("---", 0.90)], [])
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    assert len(lines) == 1
    tel = adapter.last_preprocess_telemetry
    assert tel["preprocess_applied"] is True
    assert tel["raw_chars"] == 8
    assert tel["preprocessed_chars"] == 0
    assert tel["selected_variant"] == "raw"


def test_tk243_pos2_preprocessed_only_recognized_counts_exact_chars():
    """양성 2: 원본은 빈 결과이고 전처리본만 인식될 때 raw_chars=0, preprocessed_chars는 전처리본 인식 글자 수와 일치한다."""
    # "대법원 판결 요지" (7자) + "제1조 적용" (5자) = 12자
    adapter = _make_adapter([], [("대법원 판결 요지", 0.82), ("제1조 적용", 0.80)])
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    assert len(lines) == 2
    tel = adapter.last_preprocess_telemetry
    assert tel["preprocess_applied"] is True
    assert tel["raw_chars"] == 0
    assert tel["preprocessed_chars"] == 12
    assert tel["selected_variant"] == "preprocessed"
    assert tel["selection_reason"] == "PREPROCESSED_NO_RAW"


def test_tk243_pos3_both_recognized_counts_both_exact_chars_and_propagates():
    """양성 3: 원본·전처리본 둘 다 인식될 때 두 글자 수가 각각 정확히 계산되고 build_ocr_page_telemetry까지 그대로 전달된다."""
    # raw: "임대차 계약 해지 통지서." -> 공백 제거 11자 ("임대차계약해지통지서.")
    # pre: "임대차 계약" -> 공백 제거 5자 ("임대차계약")
    fb = _make_adapter([("임대차 계약 해지 통지서.", 0.582)], [("임대차 계약", 0.534)])

    class _StubPri(OCRAdapter):
        name = "tesseract"
        available = True

        def recognize_image(self, image, *, page=1, scale=1.0, **kwargs):
            return [OCRLine(text="흐린 본문", page=page, bbox=BBox(0, 0, 50, 20), confidence=0.41)]

        def recognize(self, path, page_numbers=None):
            return self.recognize_image(None)

    comp = CompositeOCRAdapter(_StubPri(), fb, mode="auto")
    out = comp.recognize_image(_sample_image(), page=1, scale=1.0)
    q_out = page_quality(out)
    assert q_out["chars"] == 11
    tel = build_ocr_page_telemetry(comp, q_out, page=1)
    assert tel["raw_chars"] == 11
    assert tel["preprocessed_chars"] == 5
    assert tel["raw_confidence"] == 0.582
    assert tel["preprocessed_confidence"] == 0.534


def test_tk243_ctrl1_empty_recognition_yields_zero_chars():
    """대조 1: 원본·전처리본 모두 인식 줄이 비어 있으면 raw_chars=0, preprocessed_chars=0이다."""
    adapter = _make_adapter([], [])
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    assert lines == []
    tel = adapter.last_preprocess_telemetry
    assert tel["raw_chars"] == 0
    assert tel["preprocessed_chars"] == 0
    assert page_quality([])["chars"] == 0


def test_tk243_ctrl2_noise_only_lines_excluded_from_chars():
    """대조 2: 의미 있는 글자 2자 미만인 잡음 줄만 인식된 경우 chars·raw_chars·preprocessed_chars는 모두 0이다."""
    adapter = _make_adapter([("...", 0.91), ("가", 0.85)], [("---", 0.88), ("1", 0.75)])
    adapter.recognize_image(_sample_image(), preprocess=True)
    tel = adapter.last_preprocess_telemetry
    assert tel["raw_chars"] == 0
    assert tel["preprocessed_chars"] == 0
    q = page_quality([OCRLine(text="...", page=1, confidence=0.9), OCRLine(text="가", page=1, confidence=0.9)])
    assert q["lines"] == 0
    assert q["chars"] == 0


def test_tk243_ctrl3_preprocess_disabled_counts_raw_chars_and_none_preprocessed():
    """대조 3: 전처리 비활성(preprocess=False) 시 raw_chars는 정확히 계산되고 preprocessed_chars는 None이다."""
    # "정상 스캔 문서 본문" -> 공백 제거 8자
    adapter = _make_adapter([("정상 스캔 문서 본문", 0.91)], [("호출 금지", 0.50)])
    adapter.recognize_image(_sample_image(), preprocess=False)
    tel = adapter.last_preprocess_telemetry
    assert tel["preprocess_applied"] is False
    assert tel["raw_chars"] == 8
    assert tel["preprocessed_chars"] is None
    assert tel["selection_reason"] == "PREPROCESS_DISABLED"
