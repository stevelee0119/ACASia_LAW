"""TK-232: Code diet, diagnostics alignment, and commercial API embeddings + deterministic legal reranker tests."""
from __future__ import annotations

from dataclasses import replace as dc_replace
from types import SimpleNamespace

from packages.common.config import Settings, get_settings
from packages.rag_engine import relevance
from packages.rag_engine.hybrid_retriever import (
    DeterministicLegalReranker,
    GeminiEmbeddingAdapter,
    OpenAIEmbeddingAdapter,
    build_rag_adapters_from_env,
    retrieve_hybrid_chunks,
)
from packages.rag_engine.library import ReferenceLibrary
from packages.verification_engine.environment import next_gen_feature_diagnostics


# ---------------------------------------------------------------------------
# Positive tests (>= 3)
# ---------------------------------------------------------------------------


def test_tk232_pos1_openai_embedding_and_deterministic_reranker_with_revision_cache(tmp_path, monkeypatch) -> None:
    """OpenAIEmbeddingAdapter reuses OPENAI_API_KEY, caches per revision, and pairs with DeterministicLegalReranker."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LV_RAG_EMBEDDING_ENDPOINT", raising=False)
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "hybrid")

    emb, rerank, diag = build_rag_adapters_from_env(allow_network=True)
    assert isinstance(emb, OpenAIEmbeddingAdapter)
    assert isinstance(rerank, DeterministicLegalReranker)
    assert diag["configured_mode"] == "HYBRID"
    assert diag["effective_mode"] == "HYBRID"
    assert diag["reranker_enabled"] is True
    assert diag["provider_kind"] == "openai"

    calls: list[int] = []

    def _fake_openai_post(url, *, json=None, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer sk-test-openai-key"
        texts = json["input"]
        calls.append(len(texts))
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"data": [{"index": i, "embedding": [0.9, 0.1]} for i in range(len(texts))]},
        )

    emb._post_fn = _fake_openai_post
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk232_123456", storage_root=tmp_path)
    lib = ReferenceLibrary(settings)
    lib.directory.mkdir(parents=True, exist_ok=True)
    text1 = "민법 제750조 불법행위 손해배상 요건에 관한 판례입니다."
    with lib.connect() as db:
        db.execute(
            "INSERT INTO chunks (file_id, revision, page, start, text, terms) VALUES (?,?,?,?,?,?)",
            ("f1", "rev1", 1, 0, text1, " ".join(relevance.tokens(text1))),
        )
        db.commit()
    lib.eligible = {
        "f1": {
            "file_id": "f1",
            "title": "손해배상.pdf",
            "folder_path": "",
            "format": "pdf",
            "mime_type": "application/pdf",
            "revision": "rev1",
            "chunk_count": 1,
            "metadata_score": 10,
        }
    }

    out1 = lib.select("불법행위 손해배상", embedding_adapter=emb, reranker_adapter=rerank)
    assert out1["retrieval_telemetry"]["effective_mode"] == "HYBRID_RERANK"
    assert out1["retrieval_telemetry"]["cache_misses"] >= 1

    out2 = lib.select("불법행위 손해배상", embedding_adapter=emb, reranker_adapter=rerank)
    assert out2["retrieval_telemetry"]["effective_mode"] == "HYBRID_RERANK"
    assert out2["retrieval_telemetry"]["cache_hits"] >= 1
    assert calls[1] == 1  # only query embedded on repeat


def test_tk232_pos2_gemini_embedding_adapter_used_when_only_gemini_key_present(monkeypatch) -> None:
    """GeminiEmbeddingAdapter reuses GEMINI_API_KEY when OPENAI_API_KEY is absent."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LV_RAG_EMBEDDING_ENDPOINT", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-test-key")
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "auto")

    emb, rerank, diag = build_rag_adapters_from_env(allow_network=True)
    assert isinstance(emb, GeminiEmbeddingAdapter)
    assert isinstance(rerank, DeterministicLegalReranker)
    assert diag["provider_kind"] == "gemini"

    def _fake_gem_post(url, *, json=None, headers=None, timeout=None):
        assert headers["x-goog-api-key"] == "gem-test-key"
        reqs = json["requests"]
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"embeddings": [{"values": [0.7, 0.3]} for _ in reqs]},
        )

    emb._post_fn = _fake_gem_post
    out = retrieve_hybrid_chunks(
        "계약 해지 손해배상",
        [{"chunk_id": "c1", "text": "계약 해지 및 손해배상 판결"}],
        embedding_adapter=emb,
        reranker_adapter=rerank,
    )
    assert out["retrieval_telemetry"]["effective_mode"] == "HYBRID_RERANK"
    assert out["retrieval_telemetry"]["embedding_successes"] == 1


def test_tk232_pos3_lexical_only_diagnostics_matches_configured_effective_and_reranker(monkeypatch) -> None:
    """When LV_RAG_RETRIEVAL_MODE=lexical_only or off, diagnostics reports LEXICAL_ONLY and reranker_enabled=False."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-present")
    monkeypatch.setenv("LV_RERANKER_MODEL", "legacy-reranker")

    for mode_val in ("lexical_only", "off"):
        monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", mode_val)
        diag = next_gen_feature_diagnostics(Settings(providers={}))
        assert diag["rag"]["configured_mode"] == "LEXICAL_ONLY"
        assert diag["rag"]["effective_mode"] == "LEXICAL_ONLY"
        assert diag["rag"]["dense_enabled"] is False
        assert diag["rag"]["reranker_enabled"] is False
        assert diag["feature_modes"]["rag_retrieval_mode"] == "LEXICAL_ONLY"


# ---------------------------------------------------------------------------
# Control tests (>= 3)
# ---------------------------------------------------------------------------


def test_tk232_ctrl1_lexical_only_makes_zero_commercial_api_requests(monkeypatch) -> None:
    """Even with OPENAI_API_KEY set, LV_RAG_RETRIEVAL_MODE=lexical_only makes 0 embedding HTTP requests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-present")
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "lexical_only")

    emb, rerank, diag = build_rag_adapters_from_env(allow_network=True)
    assert emb is None and rerank is None
    assert diag["configured_mode"] == "LEXICAL_ONLY"
    assert diag["effective_mode"] == "LEXICAL_ONLY"
    assert diag["reranker_enabled"] is False

    out = retrieve_hybrid_chunks(
        "손해배상",
        [{"chunk_id": "c1", "text": "손해배상 청구"}],
        embedding_adapter=emb,
        reranker_adapter=rerank,
    )
    assert out["retrieval_telemetry"]["effective_mode"] == "LEXICAL_ONLY"
    assert out["retrieval_telemetry"]["embedding_requests"] == 0


def test_tk232_ctrl2_commercial_api_failure_falls_back_to_lexical_only_safely(monkeypatch) -> None:
    """HTTP 429/500 from commercial embedding API safely falls back to LEXICAL_ONLY without crashing."""
    emb = OpenAIEmbeddingAdapter(
        "sk-test-key",
        post_fn=lambda *_a, **_kw: SimpleNamespace(status_code=429, json=lambda: {}),
    )
    chunks = [
        {"chunk_id": "c1", "text": "일반 설명 문단"},
        {"chunk_id": "c2", "text": "2020다12345 손해배상 책임", "tier1_pinned": True},
    ]
    out = retrieve_hybrid_chunks("2020다12345 손해배상", chunks, embedding_adapter=emb, top_k=2)
    tel = out["retrieval_telemetry"]
    assert tel["effective_mode"] == "LEXICAL_ONLY"
    assert tel["embedding_failures"] == 1
    assert out["chunks"][0]["chunk_id"] == "c2"


def test_tk232_ctrl3_non_operational_local_llm_and_cassette_eval_only_status() -> None:
    """Diagnostics clearly reports removed local_llm and evaluation_only source_cassette."""
    diag = next_gen_feature_diagnostics(Settings(providers={}))
    assert diag["local_llm"]["registered"] is False
    assert diag["local_llm"]["operational"] is False
    assert diag["local_llm"]["status"] == "REMOVED_NOT_OPERATIONAL"
    assert diag["source_cassette"]["evaluation_only"] is True
