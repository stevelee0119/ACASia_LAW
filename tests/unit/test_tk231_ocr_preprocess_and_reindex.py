"""TK-231: RapidOCR low-quality image preprocessing and Drive selective low-quality re-OCR/reindex tests."""
from __future__ import annotations

from dataclasses import replace as dc_replace
import json
from types import SimpleNamespace
import numpy as np

from packages.common.config import get_settings
from packages.document_engine.ocr import (
    BBox,
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    RapidOCRAdapter,
)
from packages.rag_engine.drive import revision
from packages.rag_engine.extract import EXTRACTOR_VERSION
from packages.rag_engine.library import OCR_REPROCESS_VERSION, ReferenceLibrary


class _StubAdapter(OCRAdapter):
    def __init__(self, name: str, lines: list[OCRLine], available: bool = True) -> None:
        self.name = name
        self._lines = lines
        self.available = available
        self.calls = 0
        self.last_kwargs: dict = {}

    def recognize(self, path: str, page_numbers=None):
        self.calls += 1
        return list(self._lines)

    def recognize_image(self, image, *, page: int = 1, scale: float = 1.0, **kwargs):
        self.calls += 1
        self.last_kwargs = dict(kwargs)
        return list(self._lines)


# ---------------------------------------------------------------------------
# Positive tests (>= 3)
# ---------------------------------------------------------------------------


def test_tk231_pos1_preprocess_low_quality_image_enhances_and_improves_rapidocr():
    """Low-quality image triggers preprocess=True in CompositeOCRAdapter and RapidOCRAdapter picks improved output."""
    adapter = RapidOCRAdapter(lazy=True)
    call_shapes: list[tuple[int, int]] = []

    def _fake_engine(img):
        arr = np.asarray(img)
        call_shapes.append((arr.shape[0], arr.shape[1]))
        if arr.shape[1] <= 640:
            return SimpleNamespace(
                boxes=[[[10.0, 10.0], [100.0, 10.0], [100.0, 30.0], [10.0, 30.0]]],
                txts=("계약",),
                scores=(0.51,),
            )
        return SimpleNamespace(
            boxes=[[[20.0, 20.0], [240.0, 20.0], [240.0, 60.0], [20.0, 60.0]]],
            txts=("계약 금액 지급 의무 확인",),
            scores=(0.91,),
        )

    adapter._engine = _fake_engine
    low_primary = _StubAdapter(
        "tesseract",
        [OCRLine(text="x8k2m9q1z7w4p0", page=1, bbox=BBox(0, 0, 10, 10), confidence=0.35)],
    )
    comp = CompositeOCRAdapter(low_primary, adapter, mode="auto")
    img = np.full((240, 640, 3), 240, dtype=np.uint8)
    lines = comp.recognize_image(img, page=1, scale=1.0)
    assert len(call_shapes) == 2
    assert call_shapes[1][1] > call_shapes[0][1]
    assert lines[0].text == "계약 금액 지급 의무 확인"
    assert comp.last_route["fallback_adopted"] is True


def test_tk231_pos2_drive_selective_reprocess_only_reocr_low_quality_files(tmp_path, monkeypatch):
    """Drive sync re-processes ONLY cached files with ocr_low_quality_pages without re-downloading clean files."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk231_123456", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "clean_f", "name": "clean.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
        {"id": "low_f", "name": "low.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []

    class _FakeDrive:
        credential_mode = "injected"
        folders = {}

        def remaining(self):
            return 100.0

        def close(self):
            pass

        def inventory(self, folder, max_files=50):
            return list(items)

        def metadata(self, fid):
            return next(i for i in items if i["id"] == fid)

        def download(self, item, **_kw):
            downloaded.append(item["id"])
            return b"%PDF-1.4 dummy", item["name"], item["mimeType"]

    def _fake_extractor(content, name, mime, **_kw):
        chunks = [
            {"page": 1, "start": 0, "text": "일부 본문"},
            {"page": 2, "start": 0, "text": "복구된 2쪽 계약 내용"},
            {"page": 3, "start": 0, "text": "복구된 3쪽 손해배상"},
        ]
        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "searchable_pages": 3,
            "extracted_text_pages": 3,
            "ocr_low_quality_pages": [],
            "coverage_complete": True,
            "content_readable_complete": True,
        }

    lib = ReferenceLibrary(settings, client_factory=lambda **_kw: _FakeDrive(), extractor=_fake_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        clean_ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        low_ver = revision(items[1]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "clean_f", clean_ver,
            json.dumps({"chunk_count": 1, "searchable_pages": 3, "extracted_text_pages": 3, "coverage_complete": True, "content_readable_complete": True}),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("clean_f", clean_ver, 1, 0, "정상 판례 본문입니다.", "정상 판례 본문"))
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "low_f", low_ver,
            json.dumps({"chunk_count": 1, "searchable_pages": 1, "extracted_text_pages": 1, "ocr_low_quality_pages": [2, 3], "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2, 3]}, "coverage_complete": True, "content_readable_complete": False}),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("low_f", low_ver, 1, 0, "일부 본문", "일부 본문"))
        db.commit()

    summary = lib.sync(collect_all=True)
    assert downloaded == ["low_f"]
    gl = summary["coverage_ledger"]["global_library"]
    assert gl["low_quality_pages_before"] == 2
    assert gl["low_quality_pages_after"] == 0
    assert gl["reprocessed_pages"] == 2
    assert gl["recovered_pages"] == 2
    assert gl["searchable_pages_delta"] == 2


def test_tk231_pos3_explicit_reprocess_low_quality_flag_triggers_even_same_version(tmp_path):
    """Explicit reprocess_low_quality=True re-processes low-quality files even if OCR_REPROCESS_VERSION matches."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk231_explicit", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "low_f2", "name": "low2.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []

    class _FakeDrive:
        credential_mode = "injected"
        folders = {}
        def remaining(self): return 100.0
        def close(self): pass
        def inventory(self, folder, max_files=50): return list(items)
        def metadata(self, fid): return items[0]
        def download(self, item, **_kw):
            downloaded.append(item["id"])
            return b"%PDF-1.4 dummy", item["name"], item["mimeType"]

    def _fake_extractor(*_a, **_kw):
        return {
            "chunks": [{"page": 1, "start": 0, "text": "복구된 본문"}],
            "chunk_count": 1,
            "searchable_pages": 1,
            "ocr_low_quality_pages": [],
            "coverage_complete": True,
            "content_readable_complete": True,
        }

    lib = ReferenceLibrary(settings, client_factory=lambda **_kw: _FakeDrive(), extractor=_fake_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "low_f2", ver,
            json.dumps({"chunk_count": 1, "searchable_pages": 0, "ocr_low_quality_pages": [1], "low_quality_reprocess_version": OCR_REPROCESS_VERSION, "coverage_complete": True, "content_readable_complete": False}),
        ))
        db.commit()

    summary = lib.sync(collect_all=True, reprocess_low_quality=True)
    assert downloaded == ["low_f2"]
    assert summary["coverage_ledger"]["global_library"]["recovered_pages"] == 1


# ---------------------------------------------------------------------------
# Control tests (>= 3)
# ---------------------------------------------------------------------------


def test_tk231_ctrl1_normal_high_quality_scan_does_not_call_preprocess_or_fallback():
    """Normal high-quality scan (0.89) never invokes preprocessing or fallback."""
    primary = _StubAdapter(
        "tesseract",
        [
            OCRLine(text="계약서 본문 조항 확인 완료", page=1, bbox=BBox(0, 0, 120, 20), confidence=0.89),
            OCRLine(text="당사자 서명 및 날인 확인", page=1, bbox=BBox(0, 25, 120, 45), confidence=0.91),
        ],
    )
    fallback = _StubAdapter("rapidocr", [OCRLine(text="fallback", page=1, bbox=BBox(0, 0, 100, 20), confidence=0.95)])
    comp = CompositeOCRAdapter(primary, fallback, mode="auto")
    out = comp.recognize_image(np.full((100, 100, 3), 255, dtype=np.uint8), page=1)
    assert len(out) == 2
    assert fallback.calls == 0
    assert comp.last_route["fallback_attempted"] is False
    assert comp.last_route["decision_reason"] == "PRIMARY_QUALITY_SUFFICIENT"


def test_tk231_ctrl2_blank_page_is_not_fabricated_as_extracted():
    """Blank page returns empty lines and does not fabricate OCR_EXTRACTED."""
    adapter = RapidOCRAdapter(lazy=True)
    adapter._engine = lambda _img: SimpleNamespace(boxes=None, txts=None, scores=None)
    lines = adapter.recognize_image(np.full((64, 64, 3), 255, dtype=np.uint8), page=1, preprocess=True)
    assert lines == []


def test_tk231_ctrl3_clean_cached_files_reused_without_reprocess(tmp_path, monkeypatch):
    """When all cached files have 0 ocr_low_quality_pages, 0 downloads occur."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk231_clean", storage_root=tmp_path, allow_network=True)
    items = [{"id": "c1", "name": "ok.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 50}]
    downloaded: list[str] = []

    class _FakeDrive:
        credential_mode = "injected"
        folders = {}
        def remaining(self): return 100.0
        def close(self): pass
        def inventory(self, folder, max_files=50): return list(items)
        def metadata(self, fid): return items[0]
        def download(self, item, **_kw):
            downloaded.append(item["id"])
            return b"", item["name"], item["mimeType"]

    lib = ReferenceLibrary(settings, client_factory=lambda **_kw: _FakeDrive())
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "c1", ver,
            json.dumps({"chunk_count": 1, "searchable_pages": 2, "coverage_complete": True, "content_readable_complete": True}),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("c1", ver, 1, 0, "정상 문서", "정상 문서"))
        db.commit()

    summary = lib.sync(collect_all=True)
    assert downloaded == []
    assert summary["files_reused"] == 1
    assert summary["coverage_ledger"]["global_library"]["reprocessed_pages"] == 0
