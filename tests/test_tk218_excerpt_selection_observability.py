"""Tests for TK-218 (excerpt selection observability without altering selection or exposing text/identifiers).

All test documents, filenames, and excerpts are synthetic.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from packages.common.config import get_settings
from packages.rag_engine import relevance
from packages.rag_engine.library import ReferenceLibrary
from packages.rag_engine.review import review_document
from tests.test_tk209_rag_support_diagnostics import _FakeRouter, _make_context, _make_doc_result, _make_pii


def _build_synthetic_library(tmp_path: Path) -> tuple[ReferenceLibrary, list[str], list[str], list[str]]:
    settings = replace(get_settings(), storage_root=tmp_path, rag_drive_folder_id="folder_tk218")
    lib = ReferenceLibrary(settings=settings)
    lib.directory.mkdir(parents=True, exist_ok=True)
    file_ids = ["drive_id_alpha_001", "drive_id_beta_002", "drive_id_gamma_003"]
    titles = ["합성_참고서면_갑.pdf", "합성_참고서면_을.pdf", "합성_참고서면_병.pdf"]

    # Query terms will be drawn from these shared Korean legal/factual tokens.
    shared_core = "안전관리 의무 이행 손해배상 책임 인정 여부 과실 비율 산정 기준 계약 위반"
    # Alpha: 5 chunks (4 qualified + 1 below threshold), including a longer chunk that exceeds PER_FILE_EXCERPTS
    # and a longer chunk that is below threshold.
    alpha_p1 = f"{shared_core} 원칙 판시 사항 첫째 문단"  # short, high coverage (rank 1)
    alpha_p2 = f"{shared_core} 둘째 문단 보충 설명 " + ("부가서술 " * 12)  # longer, qualified (rank 2)
    alpha_p3 = f"{shared_core} 셋째 문단 추가 근거 " + ("상세내용 " * 18)  # longer, qualified (rank 3)
    alpha_p4 = f"{shared_core} 넷째 문단 비교 검토 " + ("비교내용 " * 25)  # longest qualified -> EXCEEDED_PER_FILE_EXCERPTS if > PER_FILE_EXCERPTS
    alpha_p5 = "안전관리 관련 일반 배경 설명과 무관한 부록 표지 안내문구 " + ("일반배경 " * 30)  # long but below threshold

    # Beta: 1 chunk with exact/fingerprint duplicate of alpha_p1 (to trigger DUPLICATE_FINGERPRINT_SUPPRESSED when limit is tight)
    beta_p1 = alpha_p1

    # Gamma: 2 qualified chunks with distinct content
    gamma_p1 = f"{shared_core} 감마 문서 제1쟁점 핵심 요지"
    gamma_p2 = f"{shared_core} 감마 문서 제2쟁점 별도 근거 " + ("별도서술 " * 16)

    all_texts = [alpha_p1, alpha_p2, alpha_p3, alpha_p4, alpha_p5, beta_p1, gamma_p1, gamma_p2]

    lib.summary = {
        "status": "READY",
        "snapshot_hash": "snap_tk218",
        "inventory": [
            {"file_id": file_ids[0], "title": titles[0], "status": "INDEXED", "mime_type": "application/pdf"},
            {"file_id": file_ids[1], "title": titles[1], "status": "INDEXED", "mime_type": "application/pdf"},
            {"file_id": file_ids[2], "title": titles[2], "status": "INDEXED", "mime_type": "application/pdf"},
        ],
    }
    lib.eligible = {
        file_ids[0]: {"file_id": file_ids[0], "title": titles[0], "revision": "r1", "chunk_count": 5, "mime_type": "application/pdf"},
        file_ids[1]: {"file_id": file_ids[1], "title": titles[1], "revision": "r1", "chunk_count": 1, "mime_type": "application/pdf"},
        file_ids[2]: {"file_id": file_ids[2], "title": titles[2], "revision": "r1", "chunk_count": 2, "mime_type": "application/pdf"},
    }

    chunks_rows = [
        (file_ids[0], "r1", 1, 0, alpha_p1),
        (file_ids[0], "r1", 2, 100, alpha_p2),
        (file_ids[0], "r1", 3, 200, alpha_p3),
        (file_ids[0], "r1", 4, 300, alpha_p4),
        (file_ids[0], "r1", 5, 400, alpha_p5),
        (file_ids[1], "r1", 1, 0, beta_p1),
        (file_ids[2], "r1", 1, 0, gamma_p1),
        (file_ids[2], "r1", 2, 100, gamma_p2),
    ]

    with lib.connect() as db:
        for fid, rev, page, start, text in chunks_rows:
            toks = set(relevance.query_tokens(text))
            db.execute(
                "INSERT INTO chunks(file_id, revision, page, start, text, terms) VALUES (?,?,?,?,?,?)",
                (fid, rev, page, start, text, " ".join(sorted(toks))),
            )
        db.commit()

    return lib, file_ids, titles, all_texts


def test_tk218_observability_records_chunks_distributions_and_drop_reasons(tmp_path: Path):
    lib, file_ids, titles, all_texts = _build_synthetic_library(tmp_path)
    query_text = "안전관리 의무 이행 손해배상 책임 인정 여부 과실 비율 산정 기준 계약 위반 판단"

    # limit=2 forces both DUPLICATE_FINGERPRINT_SUPPRESSED (beta_p1) and GLOBAL_LIMIT_REACHED (remaining qualified chunks),
    # while alpha_p4 exceeds PER_FILE_EXCERPTS=3 and alpha_p5 is BELOW_THRESHOLD.
    log = lib.select(query_text, limit=2)
    obs = log["excerpt_selection_observability"]

    assert obs["candidate_files_total"] == 3
    assert obs["delivered_excerpts_count"] == 2
    assert obs["per_file_excerpts_cap"] == relevance.PER_FILE_EXCERPTS
    assert obs["global_limit"] == 2

    counts = obs["drop_reason_counts"]
    assert counts.get("BELOW_THRESHOLD", 0) >= 1
    assert counts.get("EXCEEDED_PER_FILE_EXCERPTS", 0) >= 1
    assert counts.get("DUPLICATE_FINGERPRINT_SUPPRESSED", 0) >= 1
    assert counts.get("GLOBAL_LIMIT_REACHED", 0) >= 1

    # Verify per-file chunk length distribution (min/median/max) and counts
    alpha_file = next(f for f in obs["files"] if f["candidate_chunks_total"] == 5)
    assert alpha_file["qualified_chunks_count"] == 4
    assert alpha_file["below_threshold_chunks_count"] == 1
    dist = alpha_file["chunk_length_distribution"]
    assert dist["min"] <= dist["median"] <= dist["max"]
    assert dist["min"] == len(all_texts[0])
    assert dist["max"] >= len(all_texts[3])

    # Verify delivered excerpts include rank_in_file, text_coverage, shared_terms, and longer dropped chunks
    delivered = obs["delivered_excerpts"]
    assert len(delivered) == 2
    first = delivered[0]
    assert first["source_id"] == "R1"
    assert first["rank_in_file"] == 1
    assert first["text_coverage"] > 0
    assert first["shared_terms"] > 0
    assert len(first["longer_dropped_chunks_in_file"]) >= 2
    dropped_reasons = {c["drop_reason"] for c in first["longer_dropped_chunks_in_file"]}
    assert "BELOW_THRESHOLD" in dropped_reasons
    assert "EXCEEDED_PER_FILE_EXCERPTS" in dropped_reasons

    # Verify NO body text, NO filenames, NO file_ids appear anywhere in observability
    serialized = json.dumps(obs, ensure_ascii=False)
    for fid in file_ids:
        assert fid not in serialized
    for title in titles:
        assert title not in serialized
    for txt in all_texts:
        assert txt not in serialized
        assert txt[:15] not in serialized


def test_tk218_review_propagates_observability_and_preserves_selection(tmp_path: Path):
    lib, file_ids, titles, all_texts = _build_synthetic_library(tmp_path)
    query_text = "안전관리 의무 이행 손해배상 책임 인정 여부 과실 비율 산정 기준 계약 위반 판단"

    # Selection invariance check: default limit=12 returns deterministic sources without altering scoring/thresholds
    sel_a = lib.select(query_text, limit=12)
    sel_b = lib.select(query_text, limit=12)
    assert [
        (s["source_id"], s["file_id"], s["page"], s["start"], s["text"])
        for s in sel_a["sources"]
    ] == [
        (s["source_id"], s["file_id"], s["page"], s["start"], s["text"])
        for s in sel_b["sources"]
    ]

    # Review propagation check
    res = _make_doc_result(query_text)
    router = _FakeRouter({"observations": []})
    review = review_document(res, lib, router, _make_context(), _make_pii())

    diag_obs = review["support_diagnostics"]["excerpt_delivery"]["selection_observability"]
    assert diag_obs["candidate_files_total"] == sel_a["excerpt_selection_observability"]["candidate_files_total"]
    assert diag_obs["delivered_excerpts_count"] == len(sel_a["sources"])
    assert diag_obs["files"] == sel_a["excerpt_selection_observability"]["files"]

    serialized = json.dumps(diag_obs, ensure_ascii=False)
    for fid in file_ids:
        assert fid not in serialized
    for title in titles:
        assert title not in serialized
    for txt in all_texts:
        assert txt[:15] not in serialized
