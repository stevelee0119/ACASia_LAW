"""Unit tests for Hybrid Retrieval Tier 1 IdentifierIndex & Tier 2 BM25 (P1 PR-07)."""
from __future__ import annotations

from packages.rag_engine.identifier_index import (
    IdentifierIndex,
    bm25_score_chunks,
    extract_legal_identifiers,
)


def test_extract_legal_identifiers_case_statute_exhibit():
    text = (
        "대법원 2020다12345 판결 및 민법 제750조 제1항에 따라 손해배상 책임을 지며, "
        "이는 갑 제3호증의1 계약서에 의하여 입증된다."
    )
    idents = extract_legal_identifiers(text)
    keys = {(i.kind, i.canonical) for i in idents}
    assert ("CASE", "2020다12345") in keys
    assert any(k == "STATUTE" and "민법:" in c for k, c in keys)
    assert ("EXHIBIT", "갑제3호증의1") in keys


def test_identifier_index_pins_exact_match_above_lexical_noise():
    idx = IdentifierIndex()
    chunks = [
        {
            "chunk_id": "c_noise",
            "file_id": "f1",
            "text": "손해배상 책임 성립 요건 손해배상 청구 손해배상 범위 산정 기준 손해배상",
        },
        {
            "chunk_id": "c_target",
            "file_id": "f2",
            "text": "대법원 2021다55555 판결은 채무불이행과 민법 제390조의 적용 요건을 판시하였다.",
        },
    ]
    for ch in chunks:
        idx.index_chunk(ch["chunk_id"], ch["file_id"], ch["text"])

    query = "손해배상 청구에서 2021다55555 판결의 취지"
    hits = idx.lookup(query)
    assert "c_target" in hits
    assert "c_noise" not in hits

    ranked = bm25_score_chunks(query, chunks, identifier_hits=hits)
    assert ranked[0]["chunk_id"] == "c_target"
    assert ranked[0]["tier1_pinned"] is True
    assert ranked[1]["tier1_pinned"] is False


def test_statute_normalization_and_reindex_removes_deleted_identifiers():
    bare = extract_legal_identifiers("민법 제10조")
    prefixed = extract_legal_identifiers("관련 민법 제10조")
    assert len(bare) == 1
    assert bare == prefixed
    assert bare[0].canonical == "민법:10"

    idx = IdentifierIndex()
    idx.index_chunk("c1", "f1", "원고는 갑 제2호증 및 민법 제10조를 인용한다.")
    assert "c1" in idx.lookup("갑 제2호증")
    assert "c1" in idx.lookup("민법 제10조")

    # Re-index same chunk with exhibit removed
    idx.index_chunk("c1", "f1", "원고는 민법 제10조만 인용한다.")
    assert "c1" not in idx.lookup("갑 제2호증")
    assert "c1" in idx.lookup("민법 제10조")

