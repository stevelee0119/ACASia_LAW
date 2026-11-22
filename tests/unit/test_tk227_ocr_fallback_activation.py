"""TK-227: Operational Korean OCR fallback, LV_OCR_FALLBACK_MODE, and diagnostics tests."""
from __future__ import annotations

from types import SimpleNamespace
import numpy as np

from packages.document_engine.ocr import (
    BBox,
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    RapidOCRAdapter,
    get_ocr_adapter,
    reset_ocr_adapter,
)
from packages.verification_engine.environment import next_gen_feature_diagnostics


class _StubAdapter(OCRAdapter):
    def __init__(self, name: str, lines: list[OCRLine], available: bool = True) -> None:
        self.name = name
        self._lines = lines
        self.available = available
        self.calls = 0

    def recognize(self, path: str, page_numbers=None):
        self.calls += 1
        return list(self._lines)

    def recognize_image(self, image, *, page: int = 1, scale: float = 1.0):
        self.calls += 1
        return list(self._lines)


# ---------------------------------------------------------------------------
# Positive tests (3+)
# ---------------------------------------------------------------------------


def test_rapidocr_adapter_lazy_init_and_korean_recognition(monkeypatch):
    adapter = RapidOCRAdapter(lazy=True)
    assert adapter.available is True
    assert adapter._engine is None  # lazy: no ONNX session loaded at startup

    fake_output = SimpleNamespace(
        boxes=[[[10.0, 10.0], [100.0, 10.0], [100.0, 30.0], [10.0, 30.0]]],
        txts=("법률 문서 검증",),
        scores=(0.94,),
    )
    adapter._engine = lambda img: fake_output
    lines = adapter.recognize_image(np.full((64, 128, 3), 255, dtype=np.uint8), page=2, scale=2.0)
    assert len(lines) == 1
    assert lines[0].text == "법률 문서 검증"
    assert lines[0].page == 2
    assert lines[0].confidence == 0.94
    assert lines[0].bbox == BBox(5.0, 5.0, 50.0, 15.0)


def test_low_quality_scan_triggers_fallback_and_adopts_improved_result():
    primary = _StubAdapter(
        "tesseract",
        [OCRLine(text="x8k2m9q1z7w4p0", page=1, bbox=BBox(0, 0, 10, 10), confidence=0.35)],
    )
    fallback = _StubAdapter(
        "rapidocr",
        [OCRLine(text="계약 금액 지급 의무 확인", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.92)],
    )
    comp = CompositeOCRAdapter(primary, fallback, mode="auto")
    out = comp.recognize_image(None, page=1)
    assert len(out) == 1
    assert out[0].text == "계약 금액 지급 의무 확인"
    assert fallback.calls == 1
    assert comp.last_route["fallback_attempted"] is True
    assert comp.last_route["fallback_adopted"] is True
    assert comp.last_route["decision_reason"] == "FALLBACK_IMPROVED_QUALITY"


def test_diagnostics_reports_rapidocr_available_when_configured_auto(monkeypatch):
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    diag = next_gen_feature_diagnostics()
    assert diag["ocr_fallback"]["engine"] == "rapidocr"
    assert diag["ocr_fallback"]["mode"] == "auto"
    assert diag["ocr_fallback"]["available"] is True
    assert diag["ocr_fallback"]["fallback_reason"] is None


# ---------------------------------------------------------------------------
# Control tests (3+)
# ---------------------------------------------------------------------------


def test_normal_high_quality_scan_keeps_primary_without_fallback():
    primary = _StubAdapter(
        "tesseract",
        [
            OCRLine(text="계약서 본문 조항 확인 완료", page=1, bbox=BBox(0, 0, 120, 20), confidence=0.89),
            OCRLine(text="당사자 서명 및 날인 확인", page=1, bbox=BBox(0, 25, 120, 45), confidence=0.91),
        ],
    )
    fallback = _StubAdapter(
        "rapidocr",
        [OCRLine(text="다른 결과", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.95)],
    )
    comp = CompositeOCRAdapter(primary, fallback, mode="auto")
    out = comp.recognize_image(None, page=1)
    assert len(out) == 2
    assert fallback.calls == 0
    assert comp.last_route["fallback_attempted"] is False
    assert comp.last_route["decision_reason"] == "PRIMARY_QUALITY_SUFFICIENT"


def test_ocr_fallback_mode_off_prevents_fallback_even_on_low_quality(monkeypatch):
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "off")
    reset_ocr_adapter()
    try:
        adapter = get_ocr_adapter()
        assert not isinstance(adapter, CompositeOCRAdapter)

        primary = _StubAdapter("tesseract", [])
        fallback = _StubAdapter("rapidocr", [OCRLine(text="복구", page=1, bbox=BBox(0, 0, 10, 10), confidence=0.9)])
        comp = CompositeOCRAdapter(primary, fallback, mode="off")
        out = comp.recognize_image(None, page=1)
        assert out == []
        assert fallback.calls == 0
        assert comp.last_route["decision_reason"] == "FALLBACK_DISABLED_BY_MODE"

        diag = next_gen_feature_diagnostics()
        assert diag["ocr_fallback"]["available"] is False
        assert diag["ocr_fallback"]["fallback_reason"] == "DISABLED_BY_MODE"
    finally:
        reset_ocr_adapter()


def test_ocr_fallback_mode_shadow_attempts_without_adopting():
    primary_line = OCRLine(text="x8k2m9q1z7w4p0", page=1, bbox=BBox(0, 0, 10, 10), confidence=0.35)
    primary = _StubAdapter("tesseract", [primary_line])
    fallback = _StubAdapter(
        "rapidocr",
        [OCRLine(text="정상 복구 텍스트", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.93)],
    )
    comp = CompositeOCRAdapter(primary, fallback, mode="shadow")
    out = comp.recognize_image(None, page=1)
    assert out == [primary_line]
    assert fallback.calls == 1
    assert comp.last_route["fallback_attempted"] is True
    assert comp.last_route["fallback_adopted"] is False
    assert comp.last_route["decision_reason"] == "SHADOW_MODE"
