"""Tests for TK-208 (Drive reference full read, cause classification, coverage vs readability, page-level resume & raw_cache cleanup).

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


def _install_fake_pypdf(monkeypatch, pages: list[_FakePdfPage], *, ocr_max_pages: str = "0"):
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
    monkeypatch.setenv("LV_REFERENCE_OCR_MAX_PAGES", ocr_max_pages)


class _StubDrive:
    def __init__(self, files: dict[str, tuple[str, bytes, str]]):
        self.files = dict(files)
        self.downloads = 0
        self.fail_on: dict[str, Exception] = {}
        self.denied: set[str] = set()

    def _item(self, fid, name, data, mime, **extra):
        caps = {"canDownload": fid not in self.denied}
        return {
            "id": fid,
            "name": name,
            "mimeType": mime,
            "version": "1",
            "createdTime": "2026-08-01T00:00:00Z",
            "modifiedTime": "2026-10-01T00:00:00Z",
            "parents": [ROOT],
            "size": str(len(data)),
            "capabilities": caps,
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


def test_tk208_scanned_with_zero_ocr_budget_is_execution_incomplete(tmp_path, monkeypatch):
    """이미지만 있는 쪽 + OCR 예산 0 -> coverage_complete=False, 실행 사유(OCR_UNAVAILABLE), 라이브러리 PARTIAL."""
    pdf_path = _write_dummy_pdf(tmp_path / "scan.pdf", "scan")
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 계약 이행 사실관계 정리"),
        _FakePdfPage("", visual_objects=True),
        _FakePdfPage("", visual_objects=True),
    ], ocr_max_pages="0")
    out = rag_extract.extract(pdf_path, "scan.pdf", "application/pdf")

    assert out["coverage_complete"] is False
    assert out["content_readable_complete"] is False
    assert out["reason"] == "REFERENCE_PARTIALLY_READ"
    assert out["unread_pages_by_cause"]["OCR_UNAVAILABLE"] == [2, 3]
    assert out["unread_pages_by_cause"]["CONTENT_NO_TEXT"] == []
    assert out["execution_incomplete_pages"] == [2, 3]
    assert out["content_unreadable_pages"] == []

    # Library sync must mark PARTIAL so H-REF gate does not pass on unread scan pages
    pdf_bytes = pdf_path.read_bytes()
    client = _StubDrive({"f_scan": ("스캔자료.pdf", pdf_bytes, "application/pdf")})
    settings = replace(
        get_settings(),
        storage_root=tmp_path / "lib",
        rag_drive_folder_id=ROOT,
        allow_network=True,
        rag_metadata_first=False,
        rag_sync_seconds=60,
    )
    lib = ReferenceLibrary(settings, client_factory=client, extractor=lambda *a, **kw: dict(out))
    summary = lib.sync()
    assert summary["status"] == "PARTIAL"
    assert summary["inventory"][0]["status"] == "INDEXED_PARTIAL"
    assert summary["diagnostics"]["unread_cause_counts"]["pages"]["OCR_UNAVAILABLE"] == 2


def test_tk208_verified_blank_pages_only_is_coverage_complete_content_no_text(tmp_path, monkeypatch):
    """시각적으로 확인된 빈 쪽만 남은 경우 -> coverage_complete=True, 사유 CONTENT_NO_TEXT, 라이브러리 READY."""
    pdf_path = _write_dummy_pdf(tmp_path / "blank.pdf", "blank")
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 계약 이행 사실관계 정리"),
        _FakePdfPage("", visual_objects=False),
    ])
    out_blank = rag_extract.extract(pdf_path, "blank.pdf", "application/pdf")

    assert out_blank["coverage_complete"] is True
    assert out_blank["content_readable_complete"] is False
    assert out_blank["reason"] == "VERIFIED_BLANK_PAGES"
    assert out_blank["execution_incomplete_pages"] == []
    assert out_blank["unread_pages_by_cause"]["CONTENT_NO_TEXT"] == [2]

    pdf_bytes = pdf_path.read_bytes()
    client = _StubDrive({"f_blank": ("빈쪽포함.pdf", pdf_bytes, "application/pdf")})
    settings = replace(
        get_settings(),
        storage_root=tmp_path / "lib",
        rag_drive_folder_id=ROOT,
        allow_network=True,
        rag_metadata_first=False,
        rag_sync_seconds=60,
    )
    lib = ReferenceLibrary(settings, client_factory=client, extractor=lambda *a, **kw: dict(out_blank))
    summary = lib.sync()
    assert summary["status"] == "READY"
    assert summary["inventory"][0]["status"] == "INDEXED"


def test_tk208_mixed_causes_classified_without_guessing(tmp_path, monkeypatch):
    # 5-page PDF: p1 text, p2 scanned (OCR_UNAVAILABLE), p3 error (PARSE_FAILED), p4-5 unprocessed under MAX_CHARS (BUDGET_EXHAUSTED)
    _install_fake_pypdf(monkeypatch, [
        _FakePdfPage("제1쪽 정상 본문"),
        _FakePdfPage("", visual_objects=True),
        _FakePdfPage("", error=RuntimeError("corrupt page stream")),
        _FakePdfPage("제4쪽 본문 " + ("가" * 50)),
        _FakePdfPage("제5쪽 본문"),
    ], ocr_max_pages="0")
    monkeypatch.setattr(rag_extract, "MAX_CHARS", 20)

    dummy_pdf = _write_dummy_pdf(tmp_path / "mixed.pdf", "mixed")
    out = rag_extract.extract(dummy_pdf, "mixed.pdf", "application/pdf")

    assert out["coverage_complete"] is False
    assert out["content_readable_complete"] is False
    assert out["reason"] == "REFERENCE_PARTIALLY_READ"
    assert out["unread_pages_by_cause"]["OCR_UNAVAILABLE"] == [2]
    assert out["unread_pages_by_cause"]["PARSE_FAILED"] == [3]
    assert out["unread_pages_by_cause"]["BUDGET_EXHAUSTED"] == [4, 5]
    assert out["unread_pages_by_cause"]["CONTENT_NO_TEXT"] == []
    assert out["execution_incomplete_pages"] == [2, 3, 4, 5]
    assert out["continuation"]["next_page"] == 4


def test_tk208_page_level_continuation_reuses_and_deletes_raw_cache_on_completion(tmp_path):
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
                "unread_pages_by_cause": {"BUDGET_EXHAUSTED": [2, 3]},
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
            "unread_pages_by_cause": {},
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
    cache_file = lib.directory / "raw_cache" / "f_large.bin"

    s1 = lib.sync()
    assert s1["inventory"][0]["status"] == "INDEXED_PARTIAL"
    assert client.downloads == 1
    assert cache_file.is_file()

    s2 = lib.sync()
    assert s2["inventory"][0]["status"] == "INDEXED"
    assert s2["inventory"][0]["read_pages"] == 3
    assert s2["inventory"][0]["coverage_complete"] is True
    assert client.downloads == 1  # Reused raw_cache without re-downloading
    assert not cache_file.exists()  # Deleted upon continuation completion
    assert len(seen_continuations) == 2
    assert seen_continuations[0] is None
    assert seen_continuations[1]["next_page"] == 2


def test_tk208_raw_cache_deleted_on_drive_removal_access_loss_and_evicted_on_cap(tmp_path):
    b1 = _MINIMAL_PDF + b"a" * 40
    b2 = _MINIMAL_PDF + b"b" * 40
    client = _StubDrive({
        "f_a": ("파일A.pdf", b1, "application/pdf"),
        "f_b": ("파일B.pdf", b2, "application/pdf"),
    })

    def partial_extractor(data, filename, mime, **kwargs):
        return {
            "chunks": [{"page": 1, "start": 0, "text": "일부 본문"}],
            "sha256": hashlib.sha256(data).hexdigest(),
            "partial": True,
            "coverage_complete": False,
            "content_readable_complete": False,
            "reason": "REFERENCE_PARTIALLY_READ",
            "pages": 2,
            "read_pages": 1,
            "unread_pages": [2],
            "unread_pages_by_cause": {"BUDGET_EXHAUSTED": [2]},
            "execution_incomplete_pages": [2],
            "content_unreadable_pages": [],
            "continuation": {"next_page": 2, "chars": 5},
        }

    settings = replace(
        get_settings(),
        storage_root=tmp_path / "lib",
        rag_drive_folder_id=ROOT,
        allow_network=True,
        rag_metadata_first=False,
        rag_sync_seconds=60,
    )
    lib = ReferenceLibrary(settings, client_factory=client, extractor=partial_extractor)
    # Set cache cap small enough to hold only 1 file (evicts oldest when 2nd is cached)
    lib.max_raw_cache_bytes = len(b1) + 10
    lib.sync()
    cache_dir = lib.directory / "raw_cache"
    remaining_bins = list(cache_dir.glob("*.bin"))
    assert len(remaining_bins) == 1

    # Remove all files from Drive -> raw_cache must be swept completely
    client.files.clear()
    lib.sync()
    assert list(cache_dir.glob("*.bin")) == []

    # Re-add f_a, sync once, then revoke download permission -> _purge_file must delete raw_cache
    client.files["f_a"] = ("파일A.pdf", b1, "application/pdf")
    lib.sync()
    assert (cache_dir / "f_a.bin").is_file()
    client.denied.add("f_a")
    lib.sync()
    assert not (cache_dir / "f_a.bin").exists()


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


def test_tk208_d1_native_open_failure_classified_as_ocr_unavailable_and_logged(tmp_path, monkeypatch):
    """D1: pypdfium2.PdfDocument 실패 시 BUDGET_EXHAUSTED가 아닌 OCR_UNAVAILABLE + ocr_blocked + 예외 진단을 남긴다."""
    pdf_path = _write_dummy_pdf(tmp_path / "native_fail.pdf", "native_fail")

    class _FakeReader:
        def __init__(self, path):
            self.is_encrypted = False
            self.metadata = {}
            self.pages = [
                _FakePdfPage("제1쪽 정상 본문"),
                _FakePdfPage("", visual_objects=True),
                _FakePdfPage("", visual_objects=True),
            ]

    class _BrokenPdfDocument:
        def __init__(self, path):
            raise RuntimeError("synthetic pdfium open failure")

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _FakeReader
    fake_pdfium = types.ModuleType("pypdfium2")
    fake_pdfium.PdfDocument = _BrokenPdfDocument
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    monkeypatch.setitem(sys.modules, "pypdfium2", fake_pdfium)
    monkeypatch.setenv("LV_REFERENCE_OCR_MAX_PAGES", "5")

    out = rag_extract.extract(pdf_path, "native_fail.pdf", "application/pdf")
    assert out["unread_pages_by_cause"]["OCR_UNAVAILABLE"] == [2, 3]
    assert out["unread_pages_by_cause"]["BUDGET_EXHAUSTED"] == []
    assert out["page_diagnostics"]["2"]["ocr_available"] is False
    assert out["page_diagnostics"]["2"]["ocr_blocked"] == "NATIVE_RENDERER_UNAVAILABLE"
    assert out["page_diagnostics"]["2"]["ocr_blocked_error"] == "RuntimeError"
    assert out["native_open_error"]["error_type"] == "RuntimeError"
    assert "synthetic pdfium open failure" in out["native_open_error"]["message"]
    assert out["coverage_complete"] is True
    assert out["confirmed_unreadable_pages"] == [2, 3]
    assert out["read_completeness"] == "READABLE_COMPLETE_WITH_UNREADABLE"


def test_tk208_d2_confirmed_unreadable_retries_once_then_distinguishes_ready_library(tmp_path):
    """(다) 도구 미독 쪽은 1회 재시도 후 확정되고, 라이브러리/자료에 진짜 완독과 구분되는 표식 및 문구가 생성된다."""
    pdf_path = _write_dummy_pdf(tmp_path / "unreadable_confirm.pdf", "unreadable_confirm")
    pdf_bytes = pdf_path.read_bytes()
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    client = _StubDrive({"f_unreadable": ("합성스캔자료_식별불가.pdf", pdf_bytes, "application/pdf")})
    extract_calls = 0

    def tool_unreadable_extractor(path, filename, mime, **kwargs):
        nonlocal extract_calls
        extract_calls += 1
        return {
            "chunks": [{"page": 1, "start": 0, "text": "제1쪽 판시 요약"}],
            "sha256": digest,
            "partial": True,
            "coverage_complete": True,
            "content_readable_complete": False,
            "read_completeness": "READABLE_COMPLETE_WITH_UNREADABLE",
            "reason": "CONTENT_UNREADABLE_PAGES",
            "pages": 3,
            "read_pages": 1,
            "unread_pages": [2, 3],
            "unread_pages_by_cause": {"OCR_UNAVAILABLE": [2, 3]},
            "execution_incomplete_pages": [],
            "content_unreadable_pages": [],
            "confirmed_unreadable_pages": [2, 3],
            "confirmed_unreadable_causes": {"OCR_UNAVAILABLE": 2},
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
    lib = ReferenceLibrary(settings, client_factory=client, extractor=tool_unreadable_extractor)

    # 1차 동기화: 즉시 종결하지 않고 INDEXED_PARTIAL로 1회 재시도 대기
    s1 = lib.sync()
    assert extract_calls == 1
    assert s1["status"] == "PARTIAL"
    assert s1["inventory"][0]["status"] == "INDEXED_PARTIAL"
    assert s1["inventory"][0]["unreadable_confirmed"] is False

    # 2차 동기화: 1회 재시도 후 동일 결과이면 확정 -> INDEXED + READY_WITH_UNREADABLE
    s2 = lib.sync()
    assert extract_calls == 2
    assert s2["status"] == "READY"
    assert s2["read_completeness"] == "READY_WITH_UNREADABLE"
    assert s2["inventory"][0]["status"] == "INDEXED"
    assert s2["inventory"][0]["unreadable_confirmed"] is True
    assert s2["inventory"][0]["read_completeness"] == "READABLE_COMPLETE_WITH_UNREADABLE"
    assert s2["unreadable_summary"] == {"files": 1, "pages": 2, "by_cause": {"OCR_UNAVAILABLE": 2}}

    # 3차 동기화: 확정 후에는 재추출 없이 재사용
    s3 = lib.sync()
    assert extract_calls == 2
    assert s3["inventory"][0].get("reused") is True

    # 보고서 요약 문구 검증: 파일 ID·파일명·본문 없이 건수·사유만 표시
    from packages.report_engine.reference_opinions import format_unreadable_summary
    msg = format_unreadable_summary({"reference_library": s2})
    assert "자료 1건의 2쪽은 읽을 수 없습니다" in msg
    assert "OCR 미가용 2쪽" in msg
    assert "f_unreadable" not in msg
    assert "합성스캔자료_식별불가" not in msg
    assert "판시 요약" not in msg


def test_tk208_d2_retryable_unread_without_token_retries_and_stops_when_unchanged(tmp_path):
    """(가) 토큰 없는 재시도 가능 미완독 쪽은 다음 동기화에서 재시도되고, 동일 결과 반복 시 무한 재시도를 멈춘다."""
    pdf_path = _write_dummy_pdf(tmp_path / "retry_no_token.pdf", "retry_no_token")
    pdf_bytes = pdf_path.read_bytes()
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    client = _StubDrive({"f_retry": ("재시도대상.pdf", pdf_bytes, "application/pdf")})
    extract_calls = 0

    def stuck_budget_extractor(path, filename, mime, **kwargs):
        nonlocal extract_calls
        extract_calls += 1
        return {
            "chunks": [{"page": 1, "start": 0, "text": "제1쪽 본문"}],
            "sha256": digest,
            "partial": True,
            "coverage_complete": False,
            "content_readable_complete": False,
            "reason": "REFERENCE_PARTIALLY_READ",
            "pages": 2,
            "read_pages": 1,
            "unread_pages": [2],
            "unread_pages_by_cause": {"BUDGET_EXHAUSTED": [2]},
            "execution_incomplete_pages": [2],
            "retryable_unread_pages": [2],
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
    lib = ReferenceLibrary(settings, client_factory=client, extractor=stuck_budget_extractor)

    lib.sync()
    assert extract_calls == 1
    # 2차: 토큰이 없어도 재시도됨 (retry_attempts=1)
    lib.sync()
    assert extract_calls == 2
    # 3차: 최대 2회 재시도 (retry_attempts=2)
    lib.sync()
    assert extract_calls == 3
    # 4차: 상한에 도달했으므로 더는 무한 재다운로드·재추출하지 않음
    s4 = lib.sync()
    assert extract_calls == 3
    assert s4["inventory"][0].get("reused") is True


def test_tk208_d2_alternating_retryable_unread_stops_at_max_attempts(tmp_path):
    """N1: 읽은 쪽 수가 오르내리며 서명이 번갈아 바뀌어도 best_read_pages 기준으로 retry_attempts를 누적해 3회 추출에서 멈춘다."""
    pdf_path = _write_dummy_pdf(tmp_path / "alternating.pdf", "alternating")
    pdf_bytes = pdf_path.read_bytes()
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    client = _StubDrive({"f_alt": ("합성변동자료.pdf", pdf_bytes, "application/pdf")})
    extract_calls = 0

    def alternating_extractor(path, filename, mime, **kwargs):
        nonlocal extract_calls
        extract_calls += 1
        read_pages = 2 if extract_calls % 2 == 1 else 1
        unread = [3] if read_pages == 2 else [2, 3]
        return {
            "chunks": [{"page": 1, "start": 0, "text": "제1쪽 본문"}],
            "sha256": digest,
            "partial": True,
            "coverage_complete": False,
            "content_readable_complete": False,
            "reason": "REFERENCE_PARTIALLY_READ",
            "pages": 3,
            "read_pages": read_pages,
            "unread_pages": unread,
            "unread_pages_by_cause": {"BUDGET_EXHAUSTED": unread},
            "execution_incomplete_pages": unread,
            "retryable_unread_pages": unread,
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
    lib = ReferenceLibrary(settings, client_factory=client, extractor=alternating_extractor)

    for _ in range(6):
        s = lib.sync()
    assert extract_calls <= 3
    assert s["inventory"][0].get("reused") is True


def test_tk208_d2_fluctuating_confirmed_unreadable_stops_after_one_retry(tmp_path):
    """F2: 확정 미독 쪽 집합이 회차마다 달라져도 1회 재시도(총 2회 추출) 후 확정해 무한 재다운로드를 막는다."""
    pdf_path = _write_dummy_pdf(tmp_path / "fluctuating.pdf", "fluctuating")
    pdf_bytes = pdf_path.read_bytes()
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    client = _StubDrive({"f_fluc": ("합성경계자료.pdf", pdf_bytes, "application/pdf")})
    extract_calls = 0

    def fluctuating_extractor(path, filename, mime, **kwargs):
        nonlocal extract_calls
        extract_calls += 1
        unread = [2] if extract_calls % 2 == 1 else [3]
        return {
            "chunks": [{"page": 1, "start": 0, "text": "제1쪽 정상 본문"}],
            "sha256": digest,
            "partial": True,
            "coverage_complete": True,
            "content_readable_complete": False,
            "read_completeness": "READABLE_COMPLETE_WITH_UNREADABLE",
            "reason": "CONTENT_UNREADABLE_PAGES",
            "pages": 3,
            "read_pages": 2,
            "unread_pages": unread,
            "unread_pages_by_cause": {"OCR_LOW_QUALITY": unread},
            "confirmed_unreadable_pages": unread,
            "confirmed_unreadable_causes": {"OCR_LOW_QUALITY": 1},
            "execution_incomplete_pages": [],
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
    lib = ReferenceLibrary(settings, client_factory=client, extractor=fluctuating_extractor)

    for _ in range(6):
        s = lib.sync()
    assert extract_calls == 2
    assert s["status"] == "READY"
    assert s["read_completeness"] == "READY_WITH_UNREADABLE"
    assert s["inventory"][0].get("reused") is True

