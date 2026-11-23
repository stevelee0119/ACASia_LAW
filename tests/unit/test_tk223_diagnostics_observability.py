"""TK-223 차세대 실행 경로 진단 가시성 및 시험 가능성 확보 단위 시험."""
from __future__ import annotations

import json
from types import SimpleNamespace

from apps.api.capabilities import runtime_capabilities
from packages.common.config import ProviderConfig, Settings, reset_settings
from packages.verification_engine.environment import next_gen_feature_diagnostics, preflight
from packages.verification_engine.pipeline import _summarize_legal_nli


def test_next_gen_diagnostics_exposes_effective_modes_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("LV_LEGAL_NLI_MODE", "assist")
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_SOURCE_REPLAY_MODE", "REPLAY")
    monkeypatch.setenv("LV_SOURCE_CASSETTE_DIR", "/tmp/cassettes-secret-path")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-emb-secret-key")
    monkeypatch.setenv("LV_OPENAI_API_KEY", "sk-super-secret-token-12345")
    reset_settings()

    try:
        settings = Settings(providers={}, allow_network=True)
        diag = next_gen_feature_diagnostics(settings)
        # 양성 1: 유효 기능 모드 노출
        modes = diag["feature_modes"]
        assert modes["legal_nli_mode"] == "assist"
        assert modes["source_replay_mode"] == "REPLAY"
        assert modes["rag_retrieval_mode"] == "HYBRID"
        assert diag["rag"]["configured_mode"] == "HYBRID"
        assert diag["rag"]["effective_mode"] == "HYBRID"
        assert diag["rag"]["actual_calls"] == 0
        assert modes["clause_normalizer_mode"] == "default"
        # 양성 2: Hybrid RAG 활성 및 폴백 사유 없음
        assert diag["rag"]["effective_mode"] == "HYBRID"
        assert diag["rag"]["dense_enabled"] is True
        assert diag["rag"]["reranker_enabled"] is True
        assert diag["rag"]["fallback_reason"] is None
        # 양성 3: 로컬 LLM 미운영 제거 상태 및 카세트 모드(평가 전용)
        assert diag["local_llm"]["registered"] is False
        assert diag["local_llm"]["provider_count"] == 0
        assert diag["local_llm"]["status"] == "REMOVED_NOT_OPERATIONAL"
        assert diag["source_cassette"]["mode"] == "REPLAY"
        assert diag["source_cassette"]["evaluation_only"] is True
        assert diag["source_cassette"]["allow_network"] is True

        # 불변식(대조): 비밀값·토큰·자격포함 URL·원시 경로가 절대 포함되지 않음
        serialized = json.dumps(diag, ensure_ascii=False)
        assert "sk-super-secret-token-12345" not in serialized
        assert "local-secret-key" not in serialized
        assert "user:pass" not in serialized
        assert "/tmp/cassettes-secret-path" not in serialized
    finally:
        reset_settings()


def test_next_gen_diagnostics_controls_lexical_fallback_and_unconfigured_local(monkeypatch) -> None:
    monkeypatch.delenv("LV_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("LV_RAG_EMBEDDING_ENDPOINT", raising=False)
    monkeypatch.delenv("LV_RERANKER_MODEL", raising=False)
    monkeypatch.delenv("LV_RAG_RERANKER_ENDPOINT", raising=False)
    monkeypatch.delenv("LV_OCR_FALLBACK_ENGINE", raising=False)
    monkeypatch.delenv("LV_SOURCE_REPLAY_MODE", raising=False)
    monkeypatch.delenv("LV_SOURCE_CASSETTE_DIR", raising=False)
    reset_settings()

    try:
        settings = Settings(providers={})
        diag = next_gen_feature_diagnostics(settings)
        # 대조군 1: 임베딩 미설정 시 LEXICAL_ONLY + 명확한 폴백 사유
        assert diag["rag"]["effective_mode"] == "LEXICAL_ONLY"
        assert diag["rag"]["fallback_reason"] == "NO_EMBEDDING_ADAPTER_CONFIGURED"
        # 대조군 2: OCR 폴백 미설정 시 NOT_CONFIGURED
        assert diag["ocr_fallback"]["engine"] == "none"
        assert diag["ocr_fallback"]["available"] is False
        assert diag["ocr_fallback"]["fallback_reason"] == "NOT_CONFIGURED"
        # 대조군 3: 로컬 LLM 미등록 및 기본 LIVE 카세트
        assert diag["local_llm"]["registered"] is False
        assert diag["local_llm"]["provider_count"] == 0
        assert diag["source_cassette"]["mode"] == "LIVE"
        assert diag["source_cassette"]["cassette_dir_configured"] is False
    finally:
        reset_settings()


def test_runtime_capabilities_and_preflight_include_next_gen_features() -> None:
    caps = runtime_capabilities()
    assert "next_gen_features" in caps
    assert "local_count" in caps["llm"]
    assert "cloud_count" in caps["llm"]
    env = preflight()
    assert "next_gen_features" in env


def test_summarize_legal_nli_counts_executed_and_full_text() -> None:
    docs = [
        SimpleNamespace(
            engine_data={
                "legal_verdicts": [
                    {
                        "type": "CASE",
                        "official_record": {"full_text": "판결문 본문..."},
                        "review": {"stage2_nli": {"verdict": "CONTRADICTED"}, "stage2_nli_assisted": True},
                    },
                    {
                        "type": "CASE",
                        "official_record": {},
                        "review": {},
                    },
                    {
                        "type": "STATUTE",
                        "official_record": {},
                        "review": {},
                    },
                ]
            }
        )
    ]
    summary = _summarize_legal_nli(docs, mode="assist")
    assert summary["mode"] == "assist"
    assert summary["executed_count"] == 1
    assert summary["assisted_count"] == 1
    assert summary["full_text_available_count"] == 1
    assert summary["full_text_missing_count"] == 1
    assert summary["verdict_counts"] == {"CONTRADICTED": 1}
