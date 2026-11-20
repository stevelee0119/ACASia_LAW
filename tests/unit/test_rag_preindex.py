"""Unit tests for Drive RAG pre-indexing runner (P0 PR-02)."""
from __future__ import annotations

from types import SimpleNamespace

from packages.rag_engine.preindex import preindex_drive_library


def test_preindex_disabled_when_folder_missing():
    settings = SimpleNamespace(rag_drive_folder_id="")
    report = preindex_drive_library(settings)
    assert report.status == "DISABLED"
    assert report.converged is True
    assert report.rounds_executed == 0


def test_preindex_loops_until_continuations_converge():
    calls = []

    class _FakeLibrary:
        round_num = 0

        def __init__(self, settings, **kwargs):
            self.settings = settings

        def sync(self, query="", *, collect_all=None):
            _FakeLibrary.round_num += 1
            calls.append(collect_all)
            if _FakeLibrary.round_num == 1:
                return {
                    "status": "PARTIAL",
                    "files": [
                        {"file_id": "f1", "status": "INDEXED_PARTIAL", "continuation": True, "pages": 12, "read_pages": 5},
                        {"file_id": "f2", "status": "INDEXED", "continuation": False, "pages": 3, "read_pages": 3},
                    ],
                    "coverage_ledger": {"total_files": 2},
                    "issues": [{"file_id": "f1", "reason": "BUDGET_EXHAUSTED"}],
                }
            if _FakeLibrary.round_num == 2:
                return {
                    "status": "PARTIAL",
                    "files": [
                        {"file_id": "f1", "status": "INDEXED_PARTIAL", "continuation": True, "pages": 12, "read_pages": 10},
                        {"file_id": "f2", "status": "INDEXED", "continuation": False, "pages": 3, "read_pages": 3},
                    ],
                    "coverage_ledger": {"total_files": 2},
                    "issues": [{"file_id": "f1", "reason": "BUDGET_EXHAUSTED"}],
                }
            return {
                "status": "READY",
                "files": [
                    {"file_id": "f1", "status": "INDEXED", "continuation": False, "pages": 12, "read_pages": 12},
                    {"file_id": "f2", "status": "INDEXED", "continuation": False, "pages": 3, "read_pages": 3},
                ],
                "coverage_ledger": {"total_files": 2},
                "issues": [],
            }

    settings = SimpleNamespace(rag_drive_folder_id="folder_abc")
    report = preindex_drive_library(settings, max_rounds=5, ocr_pages_per_batch=5, library_factory=_FakeLibrary)
    assert calls == [True, True, True]
    assert report.converged is True
    assert report.rounds_executed == 3
    assert report.files_total == 2
    assert report.files_complete == 2
    assert report.files_partial == 0
    assert report.pages_total == 15
    assert report.pages_read == 15
    assert report.page_completion_rate == 1.0
    assert report.remaining_continuations == 0


def test_preindex_does_not_report_complete_on_failed_only_or_unknown_pages():
    class _FailedOnlyLibrary:
        def __init__(self, settings, **kwargs):
            pass

        def sync(self, query="", *, collect_all=None):
            return {
                "status": "PARTIAL",
                "files": [
                    {"file_id": "f_fail", "status": "PARSE_FAILED", "continuation": False, "pages": None, "read_pages": None},
                ],
                "coverage_ledger": {"total_files": 1},
                "issues": [{"file_id": "f_fail", "reason": "REFERENCE_PARSE_FAILED"}],
            }

    settings = SimpleNamespace(rag_drive_folder_id="folder_fail")
    failed_report = preindex_drive_library(settings, max_rounds=2, library_factory=_FailedOnlyLibrary)
    assert failed_report.converged is False
    assert failed_report.files_failed == 1
    assert failed_report.page_completion_rate == 0.0

    class _UnknownPagesLibrary:
        def __init__(self, settings, **kwargs):
            pass

        def sync(self, query="", *, collect_all=None):
            return {
                "status": "READY",
                "files": [
                    {"file_id": "f_ok", "status": "INDEXED", "continuation": False, "pages": None, "read_pages": None},
                ],
                "coverage_ledger": {"total_files": 1},
                "issues": [],
            }

    unknown_report = preindex_drive_library(settings, max_rounds=2, library_factory=_UnknownPagesLibrary)
    assert unknown_report.converged is True
    assert unknown_report.files_complete == 1
    assert unknown_report.page_completion_rate is None

