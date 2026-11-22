"""TK-228: HTTP embedding & reranker RAG adapter connection, chunk-revision caching, and fallback telemetry tests."""
from __future__ import annotations

from dataclasses import replace as dc_replace
from types import SimpleNamespace

from packages.common.config import get_settings
from packages.rag_engine import relevance
from packages.rag_engine.hybrid_retriever import (
    HttpEmbeddingAdapter,
    HttpRerankerAdapter,
    build_rag_adapters_from_env,
    retrieve_hybrid_chunks,
)
from packages.rag_engine.library import ReferenceLibrary


# ---------------------------------------------------------------------------
# Positive cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk228_pos1_http_embedding_and_reranker_execute_and_report_effective_mode() -> None:
    """HttpEmbeddingAdapter + HttpRerankerAdapter execute real requests and report HYBRID_RERANK."""
    def _emb_post(url, *, json=None, headers=None, timeout=None):
        texts = json["input"]
        vecs = [[1.0, 0.0] if "손해배상" in t or i == 0 else [0.1, 0.9] for i, t in enumerate(texts)]
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"data": [{"index": i, "embedding": v} for i, v in enumerate(vecs)]},
        )

    def _rerank_post(url, *, json=None, headers=None, timeout=None):
        docs = json["documents"]
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "results": [
                    {"index": i, "relevance_score": 0.95 if "손해배상" in d else 0.15}
                    for i, d in enumerate(docs)
                ]
            },
        )

    emb = HttpEmbeddingAdapter("https://emb.example.com/v1/embeddings", model="bge-m3", api_key="secret", post_fn=_emb_post)
    rerank = HttpRerankerAdapter("https://rerank.example.com/v1/rerank", model="bge-reranker", post_fn=_rerank_post)

    chunks = [
        {"chunk_id": "c1", "text": "임대차 목적물 인도 지연에 관한 일반 절차입니다."},
        {"chunk_id": "c2", "text": "채무불이행으로 인한 손해배상 책임 성립 요건입니다."},
    ]
    out = retrieve_hybrid_chunks("손해배상 책임", chunks, embedding_adapter=emb, reranker_adapter=rerank, top_k=2)

    tel = out["retrieval_telemetry"]
    assert tel["effective_mode"] == "HYBRID_RERANK"
    assert tel["embedding_requests"] == 1
    assert tel["embedding_successes"] == 1
    assert tel["reranker_requests"] == 1
    assert tel["reranker_successes"] == 1
    assert out["chunks"][0]["chunk_id"] == "c2"


def test_tk228_pos2_library_select_persists_and_reuses_chunk_embeddings_by_revision(tmp_path) -> None:
    """ReferenceLibrary.select() stores chunk embeddings per revision and reuses them on repeat queries."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_id_1234567890", storage_root=tmp_path)
    lib = ReferenceLibrary(settings)
    lib.directory.mkdir(parents=True, exist_ok=True)
    text1 = "계약 해지 통지 및 손해배상 청구에 관한 판례 본문입니다."
    terms1 = " ".join(relevance.tokens(text1))
    with lib.connect() as db:
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?,?,?,?,?,?)",
            ("f1", "rev1", 1, 0, text1, terms1),
        )
        db.commit()

    lib.eligible = {
        "f1": {
            "file_id": "f1",
            "title": "판례집.pdf",
            "folder_path": "",
            "format": "pdf",
            "mime_type": "application/pdf",
            "revision": "rev1",
            "chunk_count": 1,
            "metadata_score": 10,
        }
    }

    embed_batch_sizes: list[int] = []

    def _emb_post(url, *, json=None, headers=None, timeout=None):
        texts = json["input"]
        embed_batch_sizes.append(len(texts))
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"data": [{"index": i, "embedding": [0.8, 0.2]} for i in range(len(texts))]},
        )

    emb = HttpEmbeddingAdapter("https://emb.example.com/v1/embeddings", model="bge-m3", post_fn=_emb_post)

    out1 = lib.select("계약 해지 손해배상 청구", embedding_adapter=emb)
    assert out1["retrieval_telemetry"]["effective_mode"] == "HYBRID_DENSE"
    assert out1["retrieval_telemetry"]["cache_misses"] >= 1
    assert out1["retrieval_telemetry"]["cache_hits"] == 0

    out2 = lib.select("계약 해지 손해배상 청구", embedding_adapter=emb)
    assert out2["retrieval_telemetry"]["effective_mode"] == "HYBRID_DENSE"
    assert out2["retrieval_telemetry"]["cache_hits"] >= 1
    assert out2["retrieval_telemetry"]["cache_misses"] == 0
    assert embed_batch_sizes[1] == 1  # Only query text was embedded on second call


def test_tk228_pos3_build_rag_adapters_from_env_connects_without_leaking_keys(monkeypatch) -> None:
    """build_rag_adapters_from_env constructs adapters when endpoints are configured and never leaks secrets."""
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "hybrid")
    monkeypatch.setenv("LV_RAG_EMBEDDING_ENDPOINT", "https://emb.example.com/v1/embeddings")
    monkeypatch.setenv("LV_EMBEDDING_MODEL", "bge-m3")
    monkeypatch.setenv("LV_RAG_EMBEDDING_API_KEY", "super-secret-emb-key")
    monkeypatch.setenv("LV_RAG_RERANKER_ENDPOINT", "https://rerank.example.com/v1/rerank")
    monkeypatch.setenv("LV_RERANKER_MODEL", "bge-reranker")

    emb, rerank, diag = build_rag_adapters_from_env(allow_network=True)
    assert emb is not None and emb.available is True
    assert rerank is not None and rerank.available is True
    assert "super-secret-emb-key" not in str(diag)


# ---------------------------------------------------------------------------
# Control cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk228_ctrl1_unconfigured_endpoints_stay_lexical_only(monkeypatch) -> None:
    """When no endpoints are configured, effective_mode is LEXICAL_ONLY with 0 HTTP requests."""
    monkeypatch.delenv("LV_RAG_EMBEDDING_ENDPOINT", raising=False)
    monkeypatch.delenv("LV_RAG_RERANKER_ENDPOINT", raising=False)
    emb, rerank, diag = build_rag_adapters_from_env(allow_network=True)
    assert emb is None and rerank is None
    assert "EMBEDDING_ENDPOINT_UNCONFIGURED" in diag["fallback_reasons"]

    out = retrieve_hybrid_chunks(
        "손해배상",
        [{"chunk_id": "c1", "text": "손해배상 책임에 관한 판례"}],
        embedding_adapter=emb,
        reranker_adapter=rerank,
    )
    assert out["retrieval_telemetry"]["effective_mode"] == "LEXICAL_ONLY"
    assert out["retrieval_telemetry"]["embedding_requests"] == 0
    assert out["retrieval_telemetry"]["reranker_requests"] == 0


def test_tk228_ctrl2_endpoint_failures_fallback_safely_and_preserve_tier1_pin() -> None:
    """HTTP 503/Timeout on embedding & reranker safely falls back to LEXICAL_ONLY and keeps exact pins."""
    def _fail_post(*_a, **_kw):
        return SimpleNamespace(status_code=503, json=lambda: {})

    def _timeout_post(*_a, **_kw):
        raise TimeoutError("rerank timeout")

    emb = HttpEmbeddingAdapter("https://emb.example.com/v1/embeddings", post_fn=_fail_post)
    rerank = HttpRerankerAdapter("https://rerank.example.com/v1/rerank", post_fn=_timeout_post)

    chunks = [
        {"chunk_id": "c1", "text": "손해배상 일반론"},
        {"chunk_id": "c2", "text": "2019다54321 손해배상 책임", "tier1_pinned": True},
    ]
    out = retrieve_hybrid_chunks("2019다54321 손해배상", chunks, embedding_adapter=emb, reranker_adapter=rerank, top_k=2)

    tel = out["retrieval_telemetry"]
    assert tel["effective_mode"] == "LEXICAL_ONLY"
    assert tel["embedding_failures"] == 1
    assert tel["reranker_failures"] == 1
    assert any("EMBEDDING_FALLBACK" in r for r in tel["fallback_reasons"])
    assert any("RERANKER_FALLBACK" in r for r in tel["fallback_reasons"])
    assert out["chunks"][0]["chunk_id"] == "c2"


def test_tk228_ctrl3_lexical_mode_or_network_disabled_blocks_http_adapters(monkeypatch) -> None:
    """LV_RAG_RETRIEVAL_MODE=lexical or allow_network=False disables HTTP adapters even with endpoints set."""
    monkeypatch.setenv("LV_RAG_EMBEDDING_ENDPOINT", "https://emb.example.com/v1/embeddings")
    monkeypatch.setenv("LV_RAG_RERANKER_ENDPOINT", "https://rerank.example.com/v1/rerank")

    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "lexical")
    emb1, rerank1, diag1 = build_rag_adapters_from_env(allow_network=True)
    assert emb1 is None and rerank1 is None
    assert diag1["fallback_reason"] == "LEXICAL_MODE_CONFIGURED"

    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "hybrid")
    emb2, rerank2, diag2 = build_rag_adapters_from_env(allow_network=False)
    assert emb2 is None and rerank2 is None
    assert diag2["fallback_reason"] == "NETWORK_DISABLED"
