"""TK-222: Adaptive OCR fallback observability, Fail-Closed retention, and reindex searchable-page delta tests."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PIL import Image

from packages.common.schemas import BBox
from packages.document_engine.ocr import (
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    build_ocr_page_telemetry,
    page_quality,
    summarize_ocr_fallback_telemetry,
)
from packages.rag_engine import extract as rag_extract


class _FakeOCRAdapter(OCRAdapter):
    def __init__(
        self,
        name: str,
        *,
        version: str = "1.0.0",
        available: bool = True,
        lines: list[OCRLine] | None = None,
        error: Exception | None = None,
        last_error: str | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.available = available
        self._lines = lines or []
        self._error = error
        self.last_error = last_error
        self.calls = 0

    def recognize(self, path: str, page_numbers=None) -> list[OCRLine]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return list(self._lines)

    def recognize_image(self, image, *, page: int = 1, scale: float = 1.0, **kwargs) -> list[OCRLine]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return list(self._lines)


def _line(text: str, conf: float, page: int = 1) -> OCRLine:
    return OCRLine(text=text, page=page, bbox=BBox(10.0, 10.0, 120.0, 30.0), confidence=conf)


# ---------------------------------------------------------------------------
# Positive cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk222_pos1_low_quality_attempts_and_adopts_better_fallback() -> None:
    """Low-quality primary triggers fallback; improved fallback is adopted with full telemetry."""
    pri = _FakeOCRAdapter(
        "tesseract",
        version="5.3.4",
        lines=[_line("흐릿한 스캔 문서 본문", 0.42)],
    )
    fb = _FakeOCRAdapter(
        "rapidocr",
        version="1.4.0",
        lines=[_line("선명하게 복원된 계약서 본문", 0.91)],
    )
    adapter = CompositeOCRAdapter(pri, fb)
    img = Image.new("RGB", (64, 64), color="white")

    out = adapter.recognize_image(img, page=1)
    q_out = page_quality(out)
    tel = build_ocr_page_telemetry(adapter, q_out, page=1)

    assert fb.calls == 1
    assert out[0].text == "선명하게 복원된 계약서 본문"
    assert tel["primary_engine"] == "tesseract"
    assert tel["primary_version"] == "5.3.4"
    assert tel["primary_confidence"] == pytest.approx(0.42, abs=1e-3)
    assert tel["fallback_attempted"] is True
    assert tel["fallback_adopted"] is True
    assert tel["fallback_engine"] == "rapidocr"
    assert tel["fallback_version"] == "1.4.0"
    assert tel["fallback_confidence"] == pytest.approx(0.91, abs=1e-3)
    assert tel["decision_reason"] == "FALLBACK_IMPROVED_QUALITY"
    assert tel["selected_engine"] == "rapidocr"
    assert tel["selected_version"] == "1.4.0"
    assert tel["selected_confidence"] == pytest.approx(0.91, abs=1e-3)


def test_tk222_pos2_fallback_failure_keeps_low_quality_fail_closed(monkeypatch) -> None:
    """When fallback raises an error, Fail-Closed keeps OCR_LOW_QUALITY and records FALLBACK_FAILED."""
    pri = _FakeOCRAdapter(
        "tesseract",
        version="5.3.4",
        lines=[_line("판독 신뢰도 미달 텍스트", 0.38)],
    )
    fb = _FakeOCRAdapter(
        "paddleocr",
        version="2.7.0",
        error=RuntimeError("model load failure"),
    )
    composite = CompositeOCRAdapter(pri, fb)
    monkeypatch.setattr("packages.document_engine.ocr.get_ocr_adapter", lambda: composite)

    class _FakeBitmap:
        def to_pil(self):
            return Image.new("RGB", (64, 64), color="white")

        def close(self):
            pass

    class _FakePdfPage:
        def render(self, scale=2.0):
            return _FakeBitmap()

    _, diag = rag_extract._ocr_pdf_page(_FakePdfPage(), page_number=2)

    assert diag["status"] == "ocr_low_quality"
    assert diag["state"] == "OCR_LOW_QUALITY"
    fb_tel = diag["ocr_fallback"]
    assert fb_tel["fallback_attempted"] is True
    assert fb_tel["fallback_adopted"] is False
    assert fb_tel["decision_reason"] == "FALLBACK_FAILED"
    assert fb_tel["fallback_error"] == "RuntimeError"
    assert fb_tel["primary_confidence"] == pytest.approx(0.38, abs=1e-3)


def test_tk222_pos3_unconfigured_or_unavailable_fallback_records_reason_and_fail_closed() -> None:
    """Unconfigured or unavailable fallback never fabricates adoption and records explicit reason."""
    pri = _FakeOCRAdapter("tesseract", version="5.3.4", lines=[_line("저품질 스캔", 0.40)])
    img = Image.new("RGB", (32, 32), color="white")

    no_fb = CompositeOCRAdapter(pri, None)
    no_fb.recognize_image(img, page=1)
    tel_none = build_ocr_page_telemetry(no_fb, page_quality(pri._lines), page=1)
    assert tel_none["fallback_attempted"] is False
    assert tel_none["fallback_adopted"] is False
    assert tel_none["decision_reason"] == "FALLBACK_NOT_CONFIGURED"

    unavail_fb = CompositeOCRAdapter(pri, _FakeOCRAdapter("rapidocr", available=False))
    unavail_fb.recognize_image(img, page=1)
    tel_unavail = build_ocr_page_telemetry(unavail_fb, page_quality(pri._lines), page=1)
    assert tel_unavail["fallback_attempted"] is False
    assert tel_unavail["fallback_adopted"] is False
    assert tel_unavail["decision_reason"] == "FALLBACK_UNAVAILABLE"


def test_tk222_pos4_reindex_tracks_searchable_pages_increase(tmp_path) -> None:
    """Reindexing an improved scan PDF reports searchable_pages increase in entry & coverage_ledger."""
    from packages.common.config import get_settings
    from packages.rag_engine.library import ReferenceLibrary

    calls = {"n": 0}

    def _fake_extractor(data, filename, mime, *, timeout=None, continuation=None, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "chunks": [],
                "sha256": "hash-v1",
                "partial": True,
                "coverage_complete": False,
                "content_readable_complete": False,
                "read_completeness": "INCOMPLETE",
                "pages": 2,
                "read_pages": 0,
                "extracted_text_pages": 0,
                "searchable_pages": 0,
                "completed_pages": 0,
                "ocr_low_quality_pages": [1, 2],
                "ocr_fallback_summary": summarize_ocr_fallback_telemetry({
                    "1": {"page": 1, "primary_engine": "tesseract", "primary_version": "5.3.4",
                          "primary_confidence": 0.40, "fallback_attempted": True, "fallback_adopted": False,
                          "decision_reason": "FALLBACK_NOT_IMPROVED"},
                }),
                "page_diagnostics": {"1": {"status": "ocr_low_quality", "state": "OCR_LOW_QUALITY"}},
                "reason": "REFERENCE_PARTIALLY_READ",
            }
        return {
            "chunks": [
                {"page": 1, "start": 0, "text": "개선된 스캔 1쪽 본문"},
                {"page": 2, "start": 0, "text": "개선된 스캔 2쪽 본문"},
            ],
            "sha256": "hash-v2",
            "partial": False,
            "coverage_complete": True,
            "content_readable_complete": True,
            "read_completeness": "FULL",
            "pages": 2,
            "read_pages": 2,
            "extracted_text_pages": 2,
            "searchable_pages": 2,
            "completed_pages": 2,
            "ocr_low_quality_pages": [],
            "ocr_fallback_summary": summarize_ocr_fallback_telemetry({
                "1": {"page": 1, "primary_engine": "tesseract", "primary_version": "5.3.4",
                      "primary_confidence": 0.40, "fallback_attempted": True, "fallback_adopted": True,
                      "fallback_engine": "rapidocr", "fallback_version": "1.4.0",
                      "fallback_confidence": 0.92, "decision_reason": "FALLBACK_IMPROVED_QUALITY"},
            }),
            "page_diagnostics": {"1": {"status": "ocr_applied", "state": "OCR_TEXT"}},
            "reason": "",
        }

    class _FakeClient:
        def __init__(self, _settings) -> None:
            self.payload = b"%PDF-1.4\n%fake\n"
            self.call_totals = {}
            self.calls = []
            self.rev = 1
            self.last_error_reason = None

        def remaining(self) -> float:
            return 60.0

        def inventory(self, folder_id, *, max_files=None):
            import hashlib
            return [{
                "id": "f1",
                "name": "계약서_스캔.pdf",
                "mimeType": "application/pdf",
                "md5Checksum": hashlib.md5(self.payload).hexdigest(),
                "modifiedTime": f"2026-11-21T00:0{self.rev}:00Z",
                "headRevisionId": f"rev{self.rev}",
            }]

        def metadata(self, file_id):
            return self.inventory("folder1")[0]

        def download(self, item, *, max_bytes=None):
            return self.payload, item["name"], item["mimeType"]

        def close(self) -> None:
            pass

    from dataclasses import replace as dc_replace
    settings = dc_replace(
        get_settings(),
        rag_drive_folder_id="folder_id_1234567890",
        allow_network=True,
        storage_root=tmp_path,
    )
    client = _FakeClient(settings)
    lib = ReferenceLibrary(settings, client_factory=lambda **_kw: client, extractor=_fake_extractor)

    s1 = lib.sync("계약", collect_all=True)
    assert s1["coverage_ledger"]["global_library"]["searchable_pages"] == 0

    client.rev = 2
    client.payload = b"%PDF-1.4\n%fake-improved\n"
    s2 = lib.sync("계약", collect_all=True)
    assert s2["status"] == "READY", (s2["status"], s2.get("issues"), s2.get("inventory"))
    gl2 = s2["coverage_ledger"]["global_library"]
    assert gl2["searchable_pages"] == 2
    assert gl2["searchable_pages_delta"] == 2
    assert gl2["ocr_fallback_adopted_pages"] == 1
    inv_entry = next(i for i in s2["inventory"] if i["file_id"] == "f1")
    assert inv_entry["previous_searchable_pages"] == 0
    assert inv_entry["searchable_pages"] == 2
    assert inv_entry["searchable_pages_delta"] == 2


# ---------------------------------------------------------------------------
# Control cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk222_ctrl1_normal_quality_scan_does_not_adopt_or_call_fallback() -> None:
    """Normal quality scan (confidence 0.89) must not trigger unnecessary fallback."""
    pri = _FakeOCRAdapter(
        "tesseract",
        version="5.3.4",
        lines=[_line("정상 품질의 스캔 문서 텍스트입니다", 0.89)],
    )
    fb = _FakeOCRAdapter(
        "rapidocr",
        version="1.4.0",
        lines=[_line("불필요한 폴백 결과", 0.95)],
    )
    adapter = CompositeOCRAdapter(pri, fb)
    img = Image.new("RGB", (64, 64), color="white")

    out = adapter.recognize_image(img, page=1)
    tel = build_ocr_page_telemetry(adapter, page_quality(out), page=1)

    assert fb.calls == 0
    assert tel["fallback_attempted"] is False
    assert tel["fallback_adopted"] is False
    assert tel["decision_reason"] == "PRIMARY_QUALITY_SUFFICIENT"
    assert tel["selected_engine"] == "tesseract"
    assert tel["selected_confidence"] == pytest.approx(0.89, abs=1e-3)


def test_tk222_ctrl2_worse_fallback_is_rejected_and_primary_retained() -> None:
    """Fallback with lower confidence than primary is rejected with FALLBACK_NOT_IMPROVED."""
    pri = _FakeOCRAdapter(
        "tesseract",
        version="5.3.4",
        lines=[_line("부분 인식된 원문 텍스트", 0.48)],
    )
    fb = _FakeOCRAdapter(
        "rapidocr",
        version="1.4.0",
        lines=[_line("더 나쁜 폴백 결과", 0.31)],
    )
    adapter = CompositeOCRAdapter(pri, fb)
    img = Image.new("RGB", (64, 64), color="white")

    out = adapter.recognize_image(img, page=1)
    tel = build_ocr_page_telemetry(adapter, page_quality(out), page=1)

    assert fb.calls == 1
    assert out[0].text == "부분 인식된 원문 텍스트"
    assert tel["fallback_attempted"] is True
    assert tel["fallback_adopted"] is False
    assert tel["decision_reason"] == "FALLBACK_NOT_IMPROVED"
    assert tel["primary_confidence"] == pytest.approx(0.48, abs=1e-3)
    assert tel["fallback_confidence"] == pytest.approx(0.31, abs=1e-3)


def test_tk222_ctrl3_empty_fallback_is_rejected_with_explicit_reason() -> None:
    """Fallback returning empty lines is rejected with FALLBACK_EMPTY."""
    pri = _FakeOCRAdapter(
        "tesseract",
        version="5.3.4",
        lines=[_line("희미한 본문", 0.35)],
    )
    fb = _FakeOCRAdapter("rapidocr", version="1.4.0", lines=[])
    adapter = CompositeOCRAdapter(pri, fb)
    img = Image.new("RGB", (64, 64), color="white")

    out = adapter.recognize_image(img, page=1)
    tel = build_ocr_page_telemetry(adapter, page_quality(out), page=1)

    assert fb.calls == 1
    assert out[0].text == "희미한 본문"
    assert tel["fallback_attempted"] is True
    assert tel["fallback_adopted"] is False
    assert tel["decision_reason"] == "FALLBACK_EMPTY"
