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


def test_hybrid_retriever_degrades_gracefully_on_embedding_timeout():
    chunks = [
        {"chunk_id": "c1", "file_id": "f1", "text": "임대차 보증금 반환 지연 이자"},
        {"chunk_id": "c2", "file_id": "f2", "text": "매매 대금 지급 기한 도과"},
    ]

    def _timeout_embed(texts):
        raise TimeoutError("embedding model timed out")

    res = retrieve_hybrid_chunks(
        "임대차 보증금 반환",
        chunks,
        embedding_adapter=CallableEmbeddingAdapter(_timeout_embed),
        top_k=2,
    )
    assert res["retrieval_mode"] == "LEXICAL_ONLY"
    assert "EMBEDDING_FALLBACK:TimeoutError" in res["retrieval_warnings"]
    assert len(res["chunks"]) == 2
    assert res["chunks"][0]["chunk_id"] == "c1"


def test_reference_library_select_surfaces_applicability_and_excludes_invalid(tmp_path):
    from types import SimpleNamespace
    from packages.rag_engine import relevance
    from packages.rag_engine.library import ReferenceLibrary

    settings = SimpleNamespace(
        storage_root=str(tmp_path),
        rag_drive_folder_id="folder_hybrid_test",
        rag_hybrid_semantic=False,
    )
    lib = ReferenceLibrary(settings)
    lib.directory.mkdir(parents=True, exist_ok=True)
    q_text = "손해배상 청구권 소멸시효 기산점 판례 기준 불법행위 채무불이행"
    text_overruled = q_text + " 폐기된 기존 법리"
    text_valid = q_text + " 유효한 현행 법리"
    text_bg = "특허권 침해 금지 청구 등록 청구범위 기술 분야"
    with lib.connect() as db:
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?, ?, ?, ?, ?, ?)",
            ("f_overruled", "r1", 1, 0, text_overruled, " ".join(relevance.tokens(text_overruled))),
        )
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?, ?, ?, ?, ?, ?)",
            ("f_valid", "r1", 1, 0, text_valid, " ".join(relevance.tokens(text_valid))),
        )
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?, ?, ?, ?, ?, ?)",
            ("f_bg", "r1", 1, 0, text_bg, " ".join(relevance.tokens(text_bg))),
        )
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?, ?, ?, ?, ?, ?)",
            ("f_bg2", "r1", 1, 0, "조세 부과 처분 취소 소송 기간", " ".join(relevance.tokens("조세 부과 처분 취소 소송 기간"))),
        )
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?, ?, ?, ?, ?, ?)",
            ("f_bg3", "r1", 1, 0, "근로 기준 임금 체불 퇴직금 산정", " ".join(relevance.tokens("근로 기준 임금 체불 퇴직금 산정"))),
        )
        db.commit()

    lib.eligible = {
        "f_overruled": {
            "file_id": "f_overruled",
            "title": "폐기판례.pdf",
            "revision": "r1",
            "chunk_count": 1,
            "authority_status": "OVERRULED",
        },
        "f_valid": {
            "file_id": "f_valid",
            "title": "유효판례.pdf",
            "revision": "r1",
            "chunk_count": 1,
        },
        "f_bg": {
            "file_id": "f_bg",
            "title": "배경문서.pdf",
            "revision": "r1",
            "chunk_count": 1,
        },
        "f_bg2": {
            "file_id": "f_bg2",
            "title": "배경문서2.pdf",
            "revision": "r1",
            "chunk_count": 1,
        },
        "f_bg3": {
            "file_id": "f_bg3",
            "title": "배경문서3.pdf",
            "revision": "r1",
            "chunk_count": 1,
        },
    }

    log = lib.select(q_text)
    assert log["decision"] == "USED"
    delivered_ids = [s["file_id"] for s in log["sources"]]
    assert "f_valid" in delivered_ids
    assert "f_overruled" not in delivered_ids
    assert len(log["applicability_warnings"]) == 1
    assert log["applicability_warnings"][0]["file_id"] == "f_overruled"
    assert "APPLICABILITY_WARNING:AUTHORITY_INVALIDATED" in log["applicability_warnings"][0]["warnings"]

