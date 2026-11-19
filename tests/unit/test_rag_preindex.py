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
