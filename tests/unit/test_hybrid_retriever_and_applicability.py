"""Unit tests for 4-tier Hybrid Legal Retriever & Legal Applicability Filter (P1 PR-08)."""
from __future__ import annotations

from packages.rag_engine.applicability_filter import check_chunk_applicability
from packages.rag_engine.hybrid_retriever import (
    CallableEmbeddingAdapter,
    CallableRerankerAdapter,
    retrieve_hybrid_chunks,
)
from packages.rag_engine.identifier_index import IdentifierIndex


def test_hybrid_retriever_rrf_dense_rerank_and_tier1_pinning():
    chunks = [
        {"chunk_id": "c_lex", "file_id": "f1", "text": "임대차 보증금 반환 지연 이자 계산"},
        {"chunk_id": "c_para", "file_id": "f2", "text": "임차인의 목적물 명도 의무와 집주인의 전세금 지급은 동시이행 관계이다."},
        {"chunk_id": "c_pin", "file_id": "f3", "text": "대법원 2022다11111 판결은 동시이행 항변권을 판시하였다."},
    ]
    idx = IdentifierIndex()
    for ch in chunks:
        idx.index_chunk(ch["chunk_id"], ch["file_id"], ch["text"])

    def _fake_embed(texts):
        # Query and c_para share semantic vector [1, 0]; c_lex is [0, 1]; c_pin is [0.5, 0.5]
        out = []
        for t in texts:
            if "전세금" in t or "보증금" in t and "명도" in t:
                out.append([1.0, 0.0])
            elif "2022다11111" in t:
                out.append([0.6, 0.4])
            else:
                out.append([0.0, 1.0])
        return out

    def _fake_rerank(query, passages):
        return [0.95 if "명도" in p else 0.30 for p in passages]

    res = retrieve_hybrid_chunks(
        "보증금 반환과 임차인 명도 의무 2022다11111",
        chunks,
        identifier_index=idx,
        embedding_adapter=CallableEmbeddingAdapter(_fake_embed),
        reranker_adapter=CallableRerankerAdapter(_fake_rerank),
        top_k=3,
    )
    assert res["retrieval_mode"] == "RRF_RERANK"
    assert res["chunks"][0]["chunk_id"] == "c_pin"
    assert res["chunks"][1]["chunk_id"] == "c_para"


def test_applicability_filter_blocks_repealed_overruled_and_procedure_mismatch():
    # 1. Overruled precedent
    v_over = check_chunk_applicability(
        {"chunk_id": "c1", "metadata": {"authority_status": "OVERRULED"}},
    )
    assert v_over.eligible_for_support is False
    assert "APPLICABILITY_WARNING:AUTHORITY_INVALIDATED" in v_over.warnings

    # 2. Statute not yet effective at incident date
    v_future = check_chunk_applicability(
        {"chunk_id": "c2", "metadata": {"effective_from": "2025-01-01"}},
        target_date="2023-06-15",
    )
    assert v_future.eligible_for_support is False
    assert "APPLICABILITY_WARNING:NOT_YET_EFFECTIVE" in v_future.warnings

    # 3. Repealed statute before target date
    v_rep = check_chunk_applicability(
        {"chunk_id": "c3", "metadata": {"repealed_at": "2022-01-01"}},
        target_date="2023-06-15",
    )
    assert v_rep.eligible_for_support is False
    assert "APPLICABILITY_WARNING:REPEALED_AT_TARGET_DATE" in v_rep.warnings

    # 4. Procedure mismatch
    v_proc = check_chunk_applicability(
        {"chunk_id": "c4", "metadata": {"case_type": "CRIMINAL"}},
        case_type="CIVIL",
    )
    assert v_proc.eligible_for_support is False
    assert "APPLICABILITY_WARNING:PROCEDURE_MISMATCH" in v_proc.warnings

    # 5. Valid in-force statute
    v_ok = check_chunk_applicability(
        {"chunk_id": "c5", "metadata": {"effective_from": "2020-01-01", "case_type": "CIVIL"}},
        target_date="2023-06-15",
        case_type="CIVIL",
    )
    assert v_ok.eligible_for_support is True
    assert v_ok.warnings == []
