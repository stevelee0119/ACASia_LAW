"""Unit tests for adaptive OCR fallback router CompositeOCRAdapter (P2 PR-11)."""
from __future__ import annotations

from typing import Any, List, Optional

from packages.common.schemas import BBox
from packages.document_engine.ocr import CompositeOCRAdapter, OCRAdapter, OCRLine


class _StubOCR(OCRAdapter):
    def __init__(self, name: str, lines: List[OCRLine], *, available: bool = True, fail: bool = False) -> None:
        self.name = name
        self._lines = lines
        self.available = available
        self._fail = fail

    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        if self._fail:
            raise RuntimeError("ocr failed")
        return list(self._lines)

    def recognize_image(self, image: Any, *, page: int = 1, scale: float = 1.0) -> List[OCRLine]:
        if self._fail:
            raise RuntimeError("ocr image failed")
        return list(self._lines)


def test_composite_ocr_keeps_primary_when_high_quality():
    pri = _StubOCR(
        "tesseract",
        [OCRLine(text="임대차 보증금 반환 청구 소장 본문입니다.", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.92)],
    )
    fb = _StubOCR(
        "paddleocr",
        [OCRLine(text="다른 결과", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.95)],
    )
    router = CompositeOCRAdapter(pri, fb)
    out = router.recognize_image(None, page=1)
    assert out[0].text == "임대차 보증금 반환 청구 소장 본문입니다."
    assert router.last_route["selected"] == "tesseract"


def test_composite_ocr_falls_back_on_low_quality_and_recovers_from_fallback_error():
    low_pri = _StubOCR(
        "tesseract",
        [OCRLine(text="broken ascii xj ot aoo qk zzz", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.35)],
    )
    good_fb = _StubOCR(
        "paddleocr",
        [OCRLine(text="대한민국 민법 제750조 손해배상 청구", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.91)],
    )
    router = CompositeOCRAdapter(low_pri, good_fb)
    out = router.recognize_image(None, page=1)
    assert out[0].text == "대한민국 민법 제750조 손해배상 청구"
    assert router.last_route["selected"] == "paddleocr"

    # Fallback exception must not propagate; returns primary lines safely
    failing_fb = _StubOCR("paddleocr", [], fail=True)
    safe_router = CompositeOCRAdapter(low_pri, failing_fb)
    safe_out = safe_router.recognize_image(None, page=1)
    assert safe_out[0].text == "broken ascii xj ot aoo qk zzz"
    assert safe_router.last_route["selected"] == "tesseract"


def test_composite_ocr_accepts_smaller_low_quality_improvement_and_recovers_primary_errors(monkeypatch):
    import sys
    import types
    from packages.document_engine.ocr import _build_optional_fallback

    # 1. Small confidence improvement (0.35 -> 0.38) while both are still low_quality must still pick better fallback
    low_pri = _StubOCR(
        "tesseract",
        [OCRLine(text="broken ascii xj ot aoo qk zzz", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.35)],
    )
    better_low_fb = _StubOCR(
        "rapidocr",
        [OCRLine(text="broken ascii xj ot aoo 한글", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.38)],
    )
    router = CompositeOCRAdapter(low_pri, better_low_fb)
    out = router.recognize_image(None, page=1)
    assert out[0].text == "broken ascii xj ot aoo 한글"
    assert router.last_route["selected"] == "rapidocr"

    # 2. Primary exceptions in both recognize() and recognize_image() recover cleanly via fallback
    crashing_pri = _StubOCR("tesseract", [], fail=True)
    good_fb = _StubOCR(
        "rapidocr",
        [OCRLine(text="민사소송법 제202조 자유심증주의", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.90)],
    )
    err_router = CompositeOCRAdapter(crashing_pri, good_fb)
    assert err_router.recognize("dummy.png")[0].text == "민사소송법 제202조 자유심증주의"
    assert err_router.recognize_image(None, page=1)[0].text == "민사소송법 제202조 자유심증주의"

    # 3. Missing packages return None cleanly; installed RapidOCR/PaddleOCR construct real adapters
    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", None)
    monkeypatch.setitem(sys.modules, "paddleocr", None)
    assert _build_optional_fallback("rapidocr") is None
    assert _build_optional_fallback("paddleocr") is None

    fake_rapid_mod = types.ModuleType("rapidocr_onnxruntime")

    class _FakeRapidOCR:
        def __call__(self, image):
            return ([[[[0, 0], [50, 0], [50, 10], [0, 10]], "계약 체결일 확인", 0.93]], None)

    fake_rapid_mod.RapidOCR = _FakeRapidOCR
    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", fake_rapid_mod)
    rapid_adapter = _build_optional_fallback("rapidocr")
    assert rapid_adapter is not None
    assert rapid_adapter.available is True
    assert rapid_adapter.recognize_image(None, page=1)[0].text == "계약 체결일 확인"

