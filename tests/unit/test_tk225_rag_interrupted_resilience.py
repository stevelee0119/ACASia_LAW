"""TK-225: RAG SQLite progress-handler interrupted resilience, diagnostics, and no-false-green tests."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import replace as dc_replace
from types import SimpleNamespace

import pytest

from packages.common.config import get_settings
from packages.rag_engine import relevance
from packages.rag_engine.library import ReferenceLibrary
from packages.rag_engine.review import review_document


def _make_library_with_fake_db(tmp_path, execute_fn):
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_id_1234567890", storage_root=tmp_path)
    lib = ReferenceLibrary(settings)
    lib.eligible = {
        "f1": {
            "file_id": "f1",
            "title": "손해배상 판례집.pdf",
            "folder_path": "",
            "format": "pdf",
            "mime_type": "application/pdf",
            "revision": "rev1",
            "chunk_count": 10,
            "metadata_score": 10,
        }
    }

    class _FakeCursor:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return list(self._rows)

        def fetchone(self):
            return self._rows[0] if self._rows else None

    class _FakeDB:
        def set_progress_handler(self, *_a, **_kw):
            pass

        def execute(self, sql, params=()):
            return _FakeCursor(execute_fn(sql, params))

        def executemany(self, *_a, **_kw):
            pass

    @contextmanager
    def _fake_connect():
        yield _FakeDB()

    lib.connect = _fake_connect  # type: ignore[method-assign]
    return lib


# ---------------------------------------------------------------------------
# Positive cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk225_pos1_select_recovers_on_main_fts_interrupted_with_reduced_retry(tmp_path) -> None:
    """When main FTS hits OperationalError: interrupted, select() retries with reduced scope and records diagnostics."""
    fts_calls = {"n": 0}
    sample_text = "계약 해지 통지 및 손해배상 책임에 관한 대법원 판례 본문입니다."
    sample_terms = " ".join(relevance.tokens(sample_text))

    def _exec(sql, params):
        if "FROM chunk_terms" in sql:
            return [(t, 1) for t in params]
        if "WHERE chunks MATCH" in sql and "JOIN eligible" in sql:
            fts_calls["n"] += 1
            if fts_calls["n"] == 1:
                raise sqlite3.OperationalError("interrupted")
            return [("f1", 1, 0, sample_text, sample_terms)]
        return []

    lib = _make_library_with_fake_db(tmp_path, _exec)
    out = lib.select("계약 해지 통지 및 손해배상 책임에 관한 청구원인 서면입니다.")

    diag = out["search_diagnostics"]
    assert diag["query_kind"] == "document_select"
    assert diag["interrupted"] is True
    assert "main_fts" in diag["interrupted_phases"]
    assert diag["retried_queries"] == 1
    assert diag["partial_results"] is True
    assert diag["incomplete_reason"] == "SQLITE_QUERY_INTERRUPTED"
    assert diag["candidate_chunks"] >= 1
    assert out["coverage"] == "INCOMPLETE_COVERAGE"
    assert out["search_interrupted"] is True
    assert len(out["sources"]) >= 1


def test_tk225_pos2_search_claim_recovers_when_stem_scan_interrupted(tmp_path) -> None:
    """When instr() stem scan hits OperationalError: interrupted, search_claim preserves FTS hits and diagnostics."""
    sample_text = "임대차 보증금 반환 지연에 따른 지연손해금 산정 기준을 판시한 사례입니다."
    sample_terms = " ".join(relevance.tokens(sample_text))

    def _exec(sql, params):
        if "WHERE chunks MATCH" in sql:
            return [("f1", 2, 0, sample_text, sample_terms)]
        if "instr(c.text" in sql:
            raise sqlite3.OperationalError("interrupted")
        return []

    lib = _make_library_with_fake_db(tmp_path, _exec)
    hits = lib.search_claim("임대차 보증금 반환 지연에 따른 지연손해금을 청구합니다.")

    assert len(hits) >= 1
    diag = lib._last_claim_search_diag
    assert diag["query_kind"] == "claim_search"
    assert diag["interrupted"] is True
    assert "claim_stem_scan" in diag["interrupted_phases"]
    assert diag["incomplete_reason"] == "SQLITE_QUERY_INTERRUPTED"
    assert diag["candidate_count"] >= 1


def test_tk225_pos3_review_document_records_search_diagnostics_on_interrupted(tmp_path) -> None:
    """review_document completes without propagating OperationalError and exposes search_diagnostics."""
    sample_text = "공사대금 정산 합의의 효력 범위에 관한 판례 본문입니다."
    sample_terms = " ".join(relevance.tokens(sample_text))

    def _exec(sql, params):
        if "FROM chunk_terms" in sql:
            return [(t, 1) for t in params]
        if "WHERE chunks MATCH" in sql:
            return [("f1", 1, 0, sample_text, sample_terms)]
        if "instr(c.text" in sql:
            raise sqlite3.OperationalError("interrupted")
        return []

    from packages.common.enums import ExternalAIPolicy, VerificationProfile
    from packages.common.schemas import Block

    lib = _make_library_with_fake_db(tmp_path, _exec)
    lib.summary["status"] = "READY"
    lib.case_table_status = lambda: {"status": "NO_CASE_TABLE", "candidates": [], "indexed_rows": 0}
    lib.has_case_tables = lambda: False

    doc_result = SimpleNamespace(
        document_id="doc1",
        filename="brief.pdf",
        normalized=SimpleNamespace(
            visible_text="공사대금 정산 합의의 효력 범위에 관한 주장입니다.",
            blocks=[Block(block_id="B1", text="공사대금 정산 합의의 효력 범위에 관한 주장입니다.", page=1)],
            pages=[],
        ),
        claims=[{"claim_id": "C1", "type": "LEGAL_RULE", "text": "공사대금 정산 합의의 효력 범위를 다툽니다."}],
        citations=[],
        findings=[],
        engine_data={},
    )
    context = SimpleNamespace(
        requested_issues=[],
        external_ai_policy=ExternalAIPolicy.ORIGINAL,
        profile=VerificationProfile.STANDARD,
        project_id="p1",
    )
    router = SimpleNamespace(settings=get_settings(), has_available_provider=lambda **_kw: False)
    pii = SimpleNamespace(store=None)

    review = review_document(doc_result, lib, router, context, pii)
    assert review["search_interrupted"] is True
    assert review["incomplete_reason"] == "SQLITE_QUERY_INTERRUPTED"
    assert review["search_diagnostics"]["claim_search"]["interrupted"] is True
    assert review["search_diagnostics"]["claim_search"]["interrupted_queries"] >= 1


# ---------------------------------------------------------------------------
# Control cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk225_ctrl1_normal_search_reports_no_interruption(tmp_path) -> None:
    """Normal search within deadline has interrupted=False and retried_queries=0."""
    sample_text = "매매계약 해제에 따른 원상회복 의무를 인정한 판례입니다."
    sample_terms = " ".join(relevance.tokens(sample_text))

    def _exec(sql, params):
        if "FROM chunk_terms" in sql:
            return [(t, 1) for t in params]
        if "WHERE chunks MATCH" in sql:
            return [("f1", 1, 0, sample_text, sample_terms)]
        return []

    lib = _make_library_with_fake_db(tmp_path, _exec)
    out = lib.select("매매계약 해제에 따른 원상회복 의무를 구합니다.")
    diag = out["search_diagnostics"]
    assert diag["interrupted"] is False
    assert diag["retried_queries"] == 0
    assert diag["incomplete_reason"] is None

    lib.search_claim("매매계약 해제에 따른 원상회복 의무를 구합니다.")
    c_diag = lib._last_claim_search_diag
    assert c_diag["interrupted"] is False
    assert c_diag["retried_queries"] == 0
    assert c_diag["incomplete_reason"] is None


def test_tk225_ctrl2_non_interrupted_sqlite_error_is_not_swallowed(tmp_path) -> None:
    """Non-interrupted SQLite errors (e.g. disk image malformed) must propagate (no false green)."""
    def _exec(sql, params):
        if "FROM chunk_terms" in sql:
            raise sqlite3.OperationalError("database disk image is malformed")
        return []

    lib = _make_library_with_fake_db(tmp_path, _exec)
    with pytest.raises(sqlite3.OperationalError, match="malformed"):
        lib.select("손해배상 청구")


def test_tk225_ctrl3_interrupted_zero_results_marked_incomplete_never_checked(tmp_path) -> None:
    """If both initial and reduced-scope FTS queries are interrupted with 0 results, coverage stays INCOMPLETE_COVERAGE."""
    def _exec(sql, params):
        if "FROM chunk_terms" in sql:
            return [(t, 1) for t in params]
        if "WHERE chunks MATCH" in sql:
            raise sqlite3.OperationalError("interrupted")
        return []

    lib = _make_library_with_fake_db(tmp_path, _exec)
    out = lib.select("손해배상 청구 및 계약 해지")
    assert out["sources"] == []
    assert out["coverage"] == "INCOMPLETE_COVERAGE"
    assert out["decision"] == "INCOMPLETE_COVERAGE"
    assert out["search_interrupted"] is True
    assert out["search_diagnostics"]["incomplete_reason"] == "SQLITE_QUERY_INTERRUPTED"
