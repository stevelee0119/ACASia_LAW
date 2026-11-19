"""Tests for TK-216 (RAG stage failure reflected in H-ENGINE health check and unreviewed scope).

All documents and failures are synthetic.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sqlite3

from packages.common.config import get_settings
from packages.common.enums import ExternalAIPolicy, VerificationProfile
from packages.rag_engine import library as rag_library
from packages.rag_engine import review as rag_review
from packages.verification_engine.pipeline import DocumentInput, ProjectContext, VerificationPipeline
from scripts import score_report


def test_tk216_rag_exception_fails_h_engine_health_check(tmp_path, monkeypatch):
    """합성 RAG 단계 예외(OperationalError 포함)가 발생하면 H-ENGINE이 불통과로 드러난다."""
    doc_path = tmp_path / "synthetic_brief.txt"
    doc_path.write_text("당사자는 2024. 3. 1. 계약금 10,000,000원을 지급하였다.", encoding="utf-8")

    settings = replace(
        get_settings(),
        storage_root=tmp_path / "storage",
        rag_drive_folder_id="synthetic_folder_tk216",
        allow_network=False,
    )
    pipe = VerificationPipeline()
    pipe.settings = settings

    class _StubRefLib:
        def __init__(self, *args, **kwargs):
            self.summary = {
                "status": "READY",
                "folder_id": "synthetic_folder_tk216",
                "files_seen": 1,
                "files_indexed": 1,
                "files_reused": 0,
                "diagnostics": {"elapsed_ms": 1, "http": {"totals": {"count": 1, "by_status": {"200": 1}}}},
                "snapshot_hash": "abc",
                "checked_at": "2026-11-19T00:00:00Z",
                "issues": [],
                "sources": [],
                "duplicates": [],
                "similar_names": [],
                "inventory": [],
            }

        def sync(self, query=""):
            return self.summary

    def _boom_review(*args, **kwargs):
        raise sqlite3.OperationalError("synthetic database is locked")

    monkeypatch.setattr(rag_library, "ReferenceLibrary", _StubRefLib)
    monkeypatch.setattr(rag_review, "review_document", _boom_review)

    ctx = ProjectContext(
        project_id="proj_tk216",
        external_ai_policy=ExternalAIPolicy.LOCAL_ONLY,
        profile=VerificationProfile.STANDARD,
    )
    res = pipe.run(
        "run_tk216_1",
        ctx,
        [DocumentInput(document_id="doc_tk216_1", filename="synthetic_brief.txt", path=str(doc_path), mime_type="text/plain")],
    )
    rag = res.documents[0].engine_data["rag"]
    assert rag["status"] == "UNVERIFIED"
    assert rag["reason"] == "REFERENCE_REVIEW_FAILED"
    assert rag["error"] == "OperationalError"
    assert rag["review_completed"] is False
    assert rag["unreviewed_scope"] == "DOCUMENT_REFERENCE_REVIEW"

    ok, detail = score_report.run_health({"check": "engine_errors", "allow": ["reference_sync"]}, res.run_manifest)
    assert ok is False
    assert "reference_review:OperationalError" in detail


def test_tk216_rag_unverified_return_fails_h_engine_while_retrieved_only_passes(tmp_path, monkeypatch):
    """review_document가 예외 없이 UNVERIFIED를 반환해도 H-ENGINE 불통과, RETRIEVED_ONLY는 통과."""
    doc_path = tmp_path / "synthetic_brief2.txt"
    doc_path.write_text("원고는 2024. 5. 1. 피고에게 이행을 청구하였다.", encoding="utf-8")

    settings = replace(
        get_settings(),
        storage_root=tmp_path / "storage",
        rag_drive_folder_id="synthetic_folder_tk216",
        allow_network=False,
    )
    pipe = VerificationPipeline()
    pipe.settings = settings

    class _StubRefLib:
        def __init__(self, *args, **kwargs):
            self.summary = {
                "status": "READY",
                "folder_id": "synthetic_folder_tk216",
                "files_seen": 1,
                "files_indexed": 1,
                "files_reused": 0,
                "diagnostics": {"elapsed_ms": 1, "http": {"totals": {"count": 1, "by_status": {"200": 1}}}},
                "snapshot_hash": "abc",
                "checked_at": "2026-11-19T00:00:00Z",
                "issues": [],
                "sources": [],
                "duplicates": [],
                "similar_names": [],
                "inventory": [],
            }

        def sync(self, query=""):
            return self.summary

    monkeypatch.setattr(rag_library, "ReferenceLibrary", _StubRefLib)
    ctx = ProjectContext(
        project_id="proj_tk216_2",
        external_ai_policy=ExternalAIPolicy.LOCAL_ONLY,
        profile=VerificationProfile.STANDARD,
    )

    monkeypatch.setattr(
        rag_review,
        "review_document",
        lambda doc, *a, **kw: doc.engine_data.__setitem__(
            "rag", {"status": "UNVERIFIED", "reason": "REFERENCE_REVIEW_FAILED", "review_completed": False}
        ) or doc.engine_data["rag"],
    )
    res_fail = pipe.run(
        "run_tk216_2a",
        ctx,
        [DocumentInput(document_id="doc_tk216_2", filename="synthetic_brief2.txt", path=str(doc_path), mime_type="text/plain")],
    )
    ok_fail, _ = score_report.run_health({"check": "engine_errors", "allow": ["reference_sync"]}, res_fail.run_manifest)
    assert ok_fail is False

    monkeypatch.setattr(
        rag_review,
        "review_document",
        lambda doc, *a, **kw: doc.engine_data.__setitem__(
            "rag", {"status": "RETRIEVED_ONLY", "reason": "MODEL_NOT_AVAILABLE_OR_QUICK_PROFILE", "review_completed": True}
        ) or doc.engine_data["rag"],
    )
    res_ok = pipe.run(
        "run_tk216_2b",
        ctx,
        [DocumentInput(document_id="doc_tk216_2", filename="synthetic_brief2.txt", path=str(doc_path), mime_type="text/plain")],
    )
    ok_pass, _ = score_report.run_health({"check": "engine_errors", "allow": ["reference_sync"]}, res_ok.run_manifest)
    assert ok_pass is True
