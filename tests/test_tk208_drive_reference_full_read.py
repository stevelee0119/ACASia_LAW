"""Tests for TK-208 (Drive reference full read, cause classification, coverage vs readability, page-level resume).

All test documents, filenames, and IDs are synthetic.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import types

from packages.common.config import get_settings
from packages.rag_engine import extract as rag_extract
from packages.rag_engine.drive import ReferenceError as AppReferenceError
from packages.rag_engine.library import ReferenceLibrary


ROOT = "synthetic_folder_tk208"
_MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _write_dummy_pdf(path: Path, tag: str = "") -> Path:
    path.write_bytes(_MINIMAL_PDF + tag.encode("utf-8"))
    return path


class _FakePdfPage:
    def __init__(self, text: str = "", *, visual_objects: bool = False, error: Exception | None = None):
        self._text = text
        self._visual = visual_objects
        self._error = error
        self.images = [object()] if visual_objects else []

    def extract_text(self):
        if self._error is not None:
            raise self._error
        return self._text

    def get_contents(self):
        return None


def _install_fake_pypdf(monkeypatch, pages: list[_FakePdfPage]):
    class _FakeReader:
        def __init__(self, path):
            self.is_encrypted = False
            self.metadata = {}
            self.pages = pages

    class _FakeTextPage:
        def __init__(self, page: _FakePdfPage):
            self._page = page
        def get_text_range(self):
            return self._page.extract_text()
        def close(self):
            pass

    class _FakeNativePage:
        def __init__(self, page: _FakePdfPage):
            self._page = page
        def get_textpage(self):
            return _FakeTextPage(self._page)
        def get_objects(self):
            return [object()] if self._page._visual else []
        def close(self):
            pass

    class _FakePdfDocument:
        def __init__(self, path):
            self._pages = pages
        def __getitem__(self, idx):
            return _FakeNativePage(self._pages[idx])
        def close(self):
            pass

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _FakeReader
    fake_pdfium = types.ModuleType("pypdfium2")
    fake_pdfium.PdfDocument = _FakePdfDocument
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    monkeypatch.setitem(sys.modules, "pypdfium2", fake_pdfium)
    monkeypatch.setenv("LV_REFERENCE_OCR_MAX_PAGES", "0")


class _StubDrive:
    def __init__(self, files: dict[str, tuple[str, bytes, str]]):
        self.files = dict(files)
        self.downloads = 0
        self.fail_on: dict[str, Exception] = {}

    def _item(self, fid, name, data, mime, **extra):
        return {
            "id": fid,
            "name": name,
            "mimeType": mime,
            "version": "1",
            "createdTime": "2026-08-01T00:00:00Z",
            "modifiedTime": "2026-10-01T00:00:00Z",
            "parents": [ROOT],
            "size": str(len(data)),
            "capabilities": {"canDownload": True},
            "md5Checksum": hashlib.md5(data).hexdigest(),
            "folder_path": "참고자료",
            **extra,
        }

    def __call__(self, **kwargs):
        return self

    def remaining(self):
        return 120

    def inventory(self, *args, **kwargs):
        return [self._item(fid, n, d, m) for fid, (n, d, m) in self.files.items()]

    def metadata(self, file_id):
        n, d, m = self.files[file_id]
        return self._item(file_id, n, d, m)

    def search_fulltext(self, *args, **kwargs):
        return []

    def download(self, item, **kwargs):
        file_id = item["id"] if isinstance(item, dict) else item
        if file_id in self.fail_on:
            raise self.fail_on[file_id]
        self.downloads += 1
        name, data, mime = self.files[file_id]
        return data, name, mime

    def close(self):
        pass


def test_tk208_coverage_complete_vs_content_readable_complete_separation(tmp_path, monkeypatch):
    pdf_path = _write_dummy_pdf(tmp_path / "sample.pdf", "sep")

    # Case A: text + verified blank page -> coverage_complete=True, content_readable_complete=False, VERIFIED_BLANK_PAGES
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 계약 이행 사실관계 정리"),
        _FakePdfPage("", visual_objects=False),
    ])
    out_blank = rag_extract.extract(pdf_path, "sample.pdf", "application/pdf")
    assert out_blank["coverage_complete"] is True
    assert out_blank["content_readable_complete"] is False
    assert out_blank["reason"] == "VERIFIED_BLANK_PAGES"
    assert out_blank["execution_incomplete_pages"] == []
    assert out_blank["unread_pages_by_cause"]["CONTENT_NO_TEXT"] == [2]

    # Case B: text + scanned/visual-no-text -> coverage_complete=True, content_readable_complete=False, CONTENT_UNREADABLE_PAGES
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 계약 이행 사실관계 정리"),
        _FakePdfPage("", visual_objects=True),
    ])
    out_scan = rag_extract.extract(pdf_path, "sample.pdf", "application/pdf")
    assert out_scan["coverage_complete"] is True
    assert out_scan["content_readable_complete"] is False
    assert out_scan["reason"] == "CONTENT_UNREADABLE_PAGES"
    assert out_scan["execution_incomplete_pages"] == []
    assert out_scan["content_unreadable_pages"] == [2]
    assert out_scan["unread_pages_by_cause"]["CONTENT_NO_TEXT"] == [2]

    # Case C: all text -> coverage_complete=True, content_readable_complete=True, reason=""
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 계약 이행 사실관계 정리"),
        _FakePdfPage("제2쪽 손해배상 산정 기준"),
    ])
    out_full = rag_extract.extract(pdf_path, "sample.pdf", "application/pdf")
    assert out_full["coverage_complete"] is True
    assert out_full["content_readable_complete"] is True
    assert out_full["reason"] == ""
    assert out_full["unread_pages"] == []


def test_tk208_mixed_causes_classified_without_guessing(tmp_path, monkeypatch):
    # 5-page PDF: p1 text, p2 scanned (CONTENT_NO_TEXT), p3 error (PARSE_FAILED), p4-5 unprocessed under MAX_CHARS (BUDGET_EXHAUSTED)
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 정상 본문"),
        _FakePdfPage("", visual_objects=True),
        _FakePdfPage("", error=RuntimeError("corrupt page stream")),
        _FakePdfPage("제4쪽 본문 " + ("가" * 50)),
        _FakePdfPage("제5쪽 본문"),
    ])
    monkeypatch.setattr(rag_extract, "MAX_CHARS", 20)

    dummy_pdf = _write_dummy_pdf(tmp_path / "mixed.pdf", "mixed")
    out = rag_extract.extract(dummy_pdf, "mixed.pdf", "application/pdf")

    assert out["coverage_complete"] is False
    assert out["content_readable_complete"] is False
    assert out["reason"] == "REFERENCE_PARTIALLY_READ"
    assert out["unread_pages_by_cause"]["CONTENT_NO_TEXT"] == [2]
    assert out["unread_pages_by_cause"]["PARSE_FAILED"] == [3]
    assert out["unread_pages_by_cause"]["BUDGET_EXHAUSTED"] == [4, 5]
    assert out["execution_incomplete_pages"] == [3, 4, 5]
    assert out["content_unreadable_pages"] == [2]
    assert out["continuation"]["next_page"] == 4


def test_tk208_library_sync_separates_content_unreadable_from_partial_read(tmp_path):
    pdf_path = _write_dummy_pdf(tmp_path / "ref.pdf", "ref")
    pdf_bytes = pdf_path.read_bytes()
    client = _StubDrive({"f1": ("참고자료_스캔혼합.pdf", pdf_bytes, "application/pdf")})

    def fake_extractor(path, filename, mime, **kwargs):
        return {
            "chunks": [{"page": 1, "start": 0, "text": "계약금 반환 의무 관련 참고자료 본문"}],
            "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
            "partial": True,
            "coverage_complete": True,
            "content_readable_complete": False,
            "reason": "CONTENT_UNREADABLE_PAGES",
            "pages": 3,
            "read_pages": 1,
            "extracted_text_pages": 1,
            "completed_pages": 3,
            "unread_pages": [2, 3],
            "unread_pages_by_cause": {
                "BUDGET_EXHAUSTED": [],
                "READ_TIMEOUT": [],
                "PARSE_FAILED": [],
                "CONTENT_NO_TEXT": [2, 3],
            },
            "execution_incomplete_pages": [],
            "content_unreadable_pages": [2, 3],
        }

    settings = replace(
        get_settings(),
        storage_root=tmp_path / "lib",
        rag_drive_folder_id=ROOT,
        allow_network=True,
        rag_metadata_first=False,
        rag_sync_seconds=60,
    )
    lib = ReferenceLibrary(settings, client_factory=client, extractor=fake_extractor)
    summary = lib.sync()

    entry = summary["inventory"][0]
    assert entry["status"] == "INDEXED"
    assert entry["reason"] == "CONTENT_UNREADABLE_PAGES"
    assert entry["coverage_complete"] is True
    assert entry["content_readable_complete"] is False
    assert summary["diagnostics"]["unread_cause_counts"]["pages"]["CONTENT_NO_TEXT"] == 2
    assert summary["diagnostics"]["unread_cause_counts"]["files"]["CONTENT_NO_TEXT"] == 1
    assert not any(i.get("reason") == "REFERENCE_PARTIALLY_READ" for i in summary["issues"])


def test_tk208_page_level_continuation_reuses_raw_cache_without_redownload(tmp_path):
    pdf_path = _write_dummy_pdf(tmp_path / "large.pdf", "large")
    pdf_bytes = pdf_path.read_bytes()
    client = _StubDrive({"f_large": ("대용량_참고자료.pdf", pdf_bytes, "application/pdf")})
    seen_continuations = []

    def paged_extractor(path, filename, mime, **kwargs):
        cont = kwargs.get("continuation")
        seen_continuations.append(cont)
        digest = hashlib.sha256(pdf_bytes).hexdigest()
        if not cont:
            return {
                "chunks": [{"page": 1, "start": 0, "text": "제1쪽 본문"}],
                "sha256": digest,
                "partial": True,
                "coverage_complete": False,
                "content_readable_complete": False,
                "reason": "REFERENCE_PARTIALLY_READ",
                "pages": 3,
                "read_pages": 1,
                "unread_pages": [2, 3],
                "unread_pages_by_cause": {
                    "BUDGET_EXHAUSTED": [2, 3],
                    "READ_TIMEOUT": [],
                    "PARSE_FAILED": [],
                    "CONTENT_NO_TEXT": [],
                },
                "execution_incomplete_pages": [2, 3],
                "content_unreadable_pages": [],
                "continuation": {"next_page": 2, "chars": 6},
            }
        return {
            "chunks": [
                {"page": 2, "start": 0, "text": "제2쪽 본문"},
                {"page": 3, "start": 0, "text": "제3쪽 본문"},
            ],
            "sha256": digest,
            "resumed": True,
            "partial": False,
            "coverage_complete": True,
            "content_readable_complete": True,
            "reason": "",
            "pages": 3,
            "read_pages": 3,
            "unread_pages": [],
            "unread_pages_by_cause": {
                "BUDGET_EXHAUSTED": [],
                "READ_TIMEOUT": [],
                "PARSE_FAILED": [],
                "CONTENT_NO_TEXT": [],
            },
            "execution_incomplete_pages": [],
            "content_unreadable_pages": [],
            "continuation": None,
        }

    settings = replace(
        get_settings(),
        storage_root=tmp_path / "lib",
        rag_drive_folder_id=ROOT,
        allow_network=True,
        rag_metadata_first=False,
        rag_sync_seconds=60,
    )
    lib = ReferenceLibrary(settings, client_factory=client, extractor=paged_extractor)

    s1 = lib.sync()
    assert s1["inventory"][0]["status"] == "INDEXED_PARTIAL"
    assert client.downloads == 1

    s2 = lib.sync()
    assert s2["inventory"][0]["status"] == "INDEXED"
    assert s2["inventory"][0]["read_pages"] == 3
    assert s2["inventory"][0]["coverage_complete"] is True
    assert client.downloads == 1  # Reused raw_cache without re-downloading from Drive
    assert len(seen_continuations) == 2
    assert seen_continuations[0] is None
    assert seen_continuations[1]["next_page"] == 2


def test_tk208_timeout_and_budget_causes_in_library_sync(tmp_path):
    b1 = _MINIMAL_PDF + b"t"
    b2 = _MINIMAL_PDF + b"budget_deferred"
    client = _StubDrive({
        "f_timeout": ("시간초과.pdf", b1, "application/pdf"),
        "f_budget": ("예산소진.pdf", b2, "application/pdf"),
    })
    client.fail_on["f_budget"] = AppReferenceError("SYNC_BUDGET_EXHAUSTED")

    def timeout_extractor(path, filename, mime, **kwargs):
        return {
            "chunks": [],
            "sha256": hashlib.sha256(b1).hexdigest(),
            "partial": True,
            "coverage_complete": False,
            "content_readable_complete": False,
            "reason": "REFERENCE_PARSE_TIMEOUT",
        }

    settings = replace(
        get_settings(),
        storage_root=tmp_path / "lib",
        rag_drive_folder_id=ROOT,
        allow_network=True,
        rag_metadata_first=False,
        rag_sync_seconds=60,
    )
    lib = ReferenceLibrary(settings, client_factory=client, extractor=timeout_extractor)
    summary = lib.sync()
    by_id = {item["file_id"]: item for item in summary["inventory"]}
    assert by_id["f_timeout"]["status"] == "PARSE_FAILED"
    assert by_id["f_budget"]["unread_cause"] == "BUDGET_EXHAUSTED"
