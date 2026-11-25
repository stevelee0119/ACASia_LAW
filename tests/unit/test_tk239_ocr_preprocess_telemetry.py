"""TK-239 unit tests: dual raw vs preprocessed OCR comparison, adaptive preprocessing, and full telemetry."""
from __future__ import annotations

import numpy as np

from packages.document_engine.ocr import (
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    RapidOCRAdapter,
    build_ocr_page_telemetry,
    page_quality,
)
from packages.common.schemas import BBox


def _make_line(text: str, conf: float) -> OCRLine:
    return OCRLine(text=text, page=1, bbox=BBox(0, 0, 100, 20), confidence=conf)


def test_tk239_pos1_dual_compare_picks_raw_when_preprocess_degrades():
    """양성 1: 전처리가 오히려 신뢰도를 낮추면 원본(raw)을 선택하고 양쪽 신뢰도·선택 근거를 기록한다."""
    adapter = RapidOCRAdapter()
    adapter.available = True
    adapter._ensure_engine = lambda: True  # type: ignore[method-assign]

    calls = 0

    def _fake_engine(img):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ([[[[0, 0], [100, 0], [100, 20], [0, 20]], "계약 해지 통지서 본문입니다.", 0.72]], None)
        return ([[[[0, 0], [100, 0], [100, 20], [0, 20]], "계약 해지", 0.51]], None)

    adapter._engine = _fake_engine
    img = np.full((120, 200, 3), 240, dtype=np.uint8)
    img[20:40, 20:100] = 30
    lines = adapter.recognize_image(img, preprocess=True)
    assert len(lines) == 1
    assert lines[0].confidence == 0.72
    tel = adapter.last_preprocess_telemetry
    assert tel["preprocess_applied"] is True
    assert tel["raw_confidence"] == 0.72
    assert tel["preprocessed_confidence"] == 0.51
    assert tel["selected_variant"] == "raw"
    assert tel["selection_reason"] == "RAW_HIGHER_OR_EQUAL_QUALITY"


def test_tk239_pos2_dual_compare_picks_preprocessed_when_improved():
    """양성 2: 전처리본 신뢰도·품질이 더 높으면 preprocessed를 선택하고 양쪽 수치를 기록한다."""
    adapter = RapidOCRAdapter()
    adapter.available = True
    adapter._ensure_engine = lambda: True  # type: ignore[method-assign]

    calls = 0

    def _fake_engine(img):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ([[[[0, 0], [100, 0], [100, 20], [0, 20]], "판결", 0.45]], None)
        return ([[[[0, 0], [100, 0], [100, 20], [0, 20]], "대법원 판결 원문 복구 완료", 0.86]], None)

    adapter._engine = _fake_engine
    img = np.full((120, 200, 3), 180, dtype=np.uint8)
    img[20:40, 20:100] = 150
    lines = adapter.recognize_image(img, preprocess=True)
    assert len(lines) == 1
    assert lines[0].confidence == 0.86
    tel = adapter.last_preprocess_telemetry
    assert tel["selected_variant"] == "preprocessed"
    assert tel["selection_reason"] == "PREPROCESSED_HIGHER_QUALITY"
    assert tel["raw_confidence"] == 0.45
    assert tel["preprocessed_confidence"] == 0.86


def test_tk239_pos3_composite_telemetry_exposes_both_confidences_and_recovered():
    """양성 3: CompositeOCRAdapter와 build_ocr_page_telemetry가 양쪽 신뢰도·선택 근거·recovered를 노출한다."""
    class _StubPri(OCRAdapter):
        name = "tesseract"
        available = True
        def recognize(self, path, page_numbers=None):
            return [_make_line("흐린 글자", 0.483)]

    class _StubFb(OCRAdapter):
        name = "rapidocr"
        available = True
        last_preprocess_telemetry = {
            "preprocess_applied": True,
            "raw_confidence": 0.582,
            "preprocessed_confidence": 0.537,
            "raw_chars": 25,
            "preprocessed_chars": 18,
            "selected_variant": "raw",
            "selection_reason": "RAW_HIGHER_OR_EQUAL_QUALITY",
        }
        def recognize(self, path, page_numbers=None):
            return [_make_line("제1조 손해배상 청구에 관한 계약서 본문입니다.", 0.84)]

    comp = CompositeOCRAdapter(_StubPri(), _StubFb(), mode="auto")
    out = comp.recognize("dummy.pdf")
    q = page_quality(out)
    tel = build_ocr_page_telemetry(comp, q, page=1)
    assert tel["fallback_adopted"] is True
    assert tel["raw_confidence"] == 0.582
    assert tel["preprocessed_confidence"] == 0.537
    assert tel["selected_variant"] == "raw"
    assert tel["recovered"] is True


def test_tk239_ctrl1_clean_scan_skips_fallback():
    """대조 1: 정상 스캔은 폴백을 시도·채택하지 않는다."""
    class _StubPri(OCRAdapter):
        name = "tesseract"
        available = True
        def recognize(self, path, page_numbers=None):
            return [_make_line("정상적인 법률 서면 본문 문장입니다. 계약 이행을 청구합니다.", 0.91)]

    class _StubFb(OCRAdapter):
        name = "rapidocr"
        available = True
        def recognize(self, path, page_numbers=None):
            raise AssertionError("fallback must not be called")

    comp = CompositeOCRAdapter(_StubPri(), _StubFb(), mode="auto")
    out = comp.recognize("clean.pdf")
    tel = build_ocr_page_telemetry(comp, page_quality(out), page=1)
    assert tel["fallback_attempted"] is False
    assert tel["fallback_adopted"] is False
    assert tel["decision_reason"] == "PRIMARY_QUALITY_SUFFICIENT"


def test_tk239_ctrl2_preprocess_disabled_records_disabled():
    """대조 2: preprocess=False이면 전처리를 수행하지 않고 PREPROCESS_DISABLED를 기록한다."""
    adapter = RapidOCRAdapter()
    adapter.available = True
    adapter._ensure_engine = lambda: True  # type: ignore[method-assign]
    adapter._engine = lambda img: ([[[[0, 0], [50, 0], [50, 20], [0, 20]], "정상 본문", 0.88]], None)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    adapter.recognize_image(img, preprocess=False)
    tel = adapter.last_preprocess_telemetry
    assert tel["preprocess_applied"] is False
    assert tel["preprocessed_confidence"] is None
    assert tel["selection_reason"] == "PREPROCESS_DISABLED"


def test_tk239_ctrl3_low_confidence_not_marked_recovered():
    """대조 3: 폴백이 채택되더라도 품질 기준(low_quality) 미달이면 recovered=False를 유지한다."""
    class _StubPri(OCRAdapter):
        name = "tesseract"
        available = True
        def recognize(self, path, page_numbers=None):
            return [_make_line("계약 이행 및 손해배상 청구에 관한 본문 내용입니다.", 0.10)]

    class _StubFb(OCRAdapter):
        name = "rapidocr"
        available = True
        def recognize(self, path, page_numbers=None):
            return [_make_line("계약 이행 및 손해배상 청구에 관한 본문 내용입니다.", 0.25)]

    comp = CompositeOCRAdapter(_StubPri(), _StubFb(), mode="auto")
    out = comp.recognize("low.pdf")
    q = page_quality(out)
    assert q["low_quality"] is True
    tel = build_ocr_page_telemetry(comp, q, page=1)
    assert tel["recovered"] is False
