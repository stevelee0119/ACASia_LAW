from __future__ import annotations

from packages.common.config import Settings
from packages.rag_engine.hybrid_retriever import build_rag_adapters_from_env
from packages.verification_engine.environment import next_gen_feature_diagnostics


def test_dead_http_embedding_endpoint_ignored(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LV_RAG_EMBEDDING_ENDPOINT", "https://dead-server.example.com/v1/embeddings")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    emb, rerank, diag = build_rag_adapters_from_env(allow_network=True)
    assert emb is None and rerank is None
    assert diag["effective_mode"] == "LEXICAL_ONLY"
    assert diag["fallback_reason"] == "NO_EMBEDDING_ADAPTER_CONFIGURED"

    env_diag = next_gen_feature_diagnostics(Settings(providers={}, allow_network=True))
    assert env_diag["rag"]["effective_mode"] == "LEXICAL_ONLY"
    assert env_diag["rag"]["fallback_reason"] == "NO_EMBEDDING_ADAPTER_CONFIGURED"


def test_diagnostics_3way_contract_and_network_disabled(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "0")
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "hybrid")
    diag = next_gen_feature_diagnostics(Settings(providers={}, allow_network=False))
    assert diag["rag"]["configured_mode"] == "HYBRID"
    assert diag["rag"]["effective_mode"] == "LEXICAL_ONLY"
    assert diag["rag"]["actual_calls"] == 0
    assert diag["rag"]["fallback_reason"] == "NETWORK_DISABLED"
    assert diag["ocr_fallback"]["configured_mode"] == "off"
    assert diag["ocr_fallback"]["effective_mode"] == "off"
    assert diag["ocr_fallback"]["actual_calls"] == 0
