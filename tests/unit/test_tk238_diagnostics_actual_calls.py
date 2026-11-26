"""TK-238 unit tests: run-level actual_calls aggregation, pre-run unmeasured distinction, and retrieval latency."""
from __future__ import annotations

from types import SimpleNamespace

from packages.common.config import Settings
from packages.rag_engine.hybrid_retriever import (
    DeterministicLegalReranker,
    EmbeddingAdapter,
    retrieve_hybrid_chunks,
)
from packages.verification_engine.environment import (
    aggregate_run_feature_diagnostics,
    next_gen_feature_diagnostics,
)


class _StubEmbedder(EmbeddingAdapter):
    available = True

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


def test_tk238_pos1_dense_and_reranker_calls_and_latency_aggregated():
    """양성 1: Dense 임베딩·재순위 실호출 및 지연(ms)이 문서 단위에서 run 단위로 정확히 합산된다."""
    ret = retrieve_hybrid_chunks(
        "계약 해지 통지",
        [{"chunk_id": "c1", "text": "계약 해지 통지에 관한 대법원 판례"}],
        embedding_adapter=_StubEmbedder(),
        reranker_adapter=DeterministicLegalReranker(),
    )
    telem = ret["retrieval_telemetry"]
    assert isinstance(telem["embedding_ms"], int)
    assert isinstance(telem["reranker_ms"], int)
    assert isinstance(telem["retrieval_ms"], int)

    doc = SimpleNamespace(engine_data={"rag": {"search_diagnostics": {"retrieval": telem}}})
    base = {
        "rag": {"configured_mode": "HYBRID", "effective_mode": "HYBRID", "measured": False, "actual_calls": None},
        "ocr_fallback": {"configured_mode": "auto", "effective_mode": "auto", "measured": False, "actual_calls": None},
    }
    agg = aggregate_run_feature_diagnostics(base, [doc])
    assert agg["rag"]["measured"] is True
    assert agg["rag"]["embedding_requests"] == 1
    assert agg["rag"]["embedding_successes"] == 1
    assert agg["rag"]["reranker_requests"] == 1
    assert agg["rag"]["actual_calls"] == 2
    assert agg["rag"]["retrieval_ms"] == telem["retrieval_ms"]


def test_tk238_pos2_ocr_fallback_attempted_adopted_rejected_aggregated():
    """양성 2: OCR 폴백 시도·채택·거부 건수가 run 단위로 합산된다."""
    docs = [
        SimpleNamespace(engine_data={"ocr_fallback_summary": {"attempted_pages": [1, 2], "adopted_pages": [1], "rejected_pages": [2]}}),
        SimpleNamespace(engine_data={"ocr_fallback_summary": {"attempted_pages": [3], "adopted_pages": [3]}}),
    ]
    base = {
        "rag": {"configured_mode": "LEXICAL_ONLY", "effective_mode": "LEXICAL_ONLY", "measured": False, "actual_calls": 0},
        "ocr_fallback": {"configured_mode": "auto", "effective_mode": "auto", "measured": False, "actual_calls": None},
    }
    agg = aggregate_run_feature_diagnostics(base, docs)
    assert agg["ocr_fallback"]["measured"] is True
    assert agg["ocr_fallback"]["actual_calls"] == 3
    assert agg["ocr_fallback"]["attempted_pages"] == 3
    assert agg["ocr_fallback"]["adopted_pages"] == 2
    assert agg["ocr_fallback"]["rejected_pages"] == 1


def test_tk238_pos3_multi_doc_partial_dense_and_zero_calls_reason():
    """양성 3: 다문서 부분 사용 합산과 HYBRID인데 실제 호출 0건인 경우 fallback_reason 기록."""
    d1 = SimpleNamespace(engine_data={"rag": {"search_diagnostics": {"retrieval": {
        "effective_mode": "HYBRID_RERANK", "embedding_requests": 1, "embedding_successes": 1,
        "embedding_failures": 0, "embedding_ms": 12, "reranker_requests": 1, "reranker_successes": 1,
        "reranker_failures": 0, "reranker_ms": 3, "retrieval_ms": 15, "cache_hits": 4, "cache_misses": 1,
    }}}})
    d2 = SimpleNamespace(engine_data={"rag": {"search_diagnostics": {"retrieval": {
        "effective_mode": "LEXICAL_ONLY", "embedding_requests": 0, "embedding_successes": 0,
        "embedding_failures": 0, "embedding_ms": 0, "reranker_requests": 0, "reranker_successes": 0,
        "reranker_failures": 0, "reranker_ms": 0, "retrieval_ms": 1, "cache_hits": 0, "cache_misses": 0,
    }}}})
    base = {"rag": {"configured_mode": "HYBRID", "effective_mode": "HYBRID", "measured": False, "actual_calls": None, "fallback_reason": None}}
    agg = aggregate_run_feature_diagnostics(base, [d1, d2])
    assert agg["rag"]["actual_calls"] == 2
    assert agg["rag"]["embedding_ms"] == 12
    assert agg["rag"]["cache_hits"] == 4

    agg_zero = aggregate_run_feature_diagnostics(base, [d2])
    assert agg_zero["rag"]["measured"] is True
    assert agg_zero["rag"]["actual_calls"] == 0
    assert agg_zero["rag"]["fallback_reason"] == "NO_RELEVANT_DOCUMENTS_OR_CHUNKS_FOR_DENSE"


def test_tk238_ctrl1_lexical_only_zero_calls(monkeypatch):
    """대조 1: lexical_only 설정 시 effective_mode=LEXICAL_ONLY, actual_calls=0 유지."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "lexical_only")
    diag = next_gen_feature_diagnostics(Settings(providers={}, allow_network=True))
    assert diag["rag"]["configured_mode"] == "LEXICAL_ONLY"
    assert diag["rag"]["effective_mode"] == "LEXICAL_ONLY"
    assert diag["rag"]["actual_calls"] == 0
    assert diag["rag"]["measured"] is False


def test_tk238_ctrl2_network_disabled_zero_calls(monkeypatch):
    """대조 2: 네트워크 비허용 시 effective_mode=LEXICAL_ONLY, actual_calls=0 유지."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "hybrid")
    diag = next_gen_feature_diagnostics(Settings(providers={}, allow_network=False))
    assert diag["rag"]["effective_mode"] == "LEXICAL_ONLY"
    assert diag["rag"]["actual_calls"] == 0
    assert diag["rag"]["fallback_reason"] == "NETWORK_DISABLED"


def test_tk238_ctrl3_prerun_hybrid_unmeasured_distinguished(monkeypatch):
    """대조 3: 실행 전 HYBRID/auto 조회는 measured=False로 미집계를 드러낸다."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    monkeypatch.setenv("LV_RAG_RETRIEVAL_MODE", "hybrid")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    diag = next_gen_feature_diagnostics(Settings(providers={}, allow_network=True))
    assert diag["rag"]["effective_mode"] == "HYBRID"
    assert diag["rag"]["measured"] is False
    assert diag["ocr_fallback"]["effective_mode"] == "auto"
    assert diag["ocr_fallback"]["measured"] is False


def test_tk238_a1_actual_calls_spec_matches_code():
    """A-1: 설계 명세에 actual_calls 정의가 명시되고 코드 집계식(embedding_requests + reranker_requests)과 일치한다."""
    from pathlib import Path

    spec_text = Path("docs/handoff/requests/TK-238_rag_diagnostics_contract.md").read_text(encoding="utf-8")
    assert "actual_calls = embedding_requests + reranker_requests" in spec_text

    doc = SimpleNamespace(engine_data={"rag": {"search_diagnostics": {"retrieval": {
        "effective_mode": "HYBRID_RERANK", "embedding_requests": 2, "reranker_requests": 3,
    }}}})
    agg = aggregate_run_feature_diagnostics({"rag": {}, "ocr_fallback": {}}, [doc])
    assert agg["rag"]["actual_calls"] == agg["rag"]["embedding_requests"] + agg["rag"]["reranker_requests"] == 5


def test_tk238_a2_zero_documents_stays_unmeasured():
    """A-2: 문서 0개 및 검색 기록 없는 문서는 rag.measured=False(사유 없음)로 미집계 유지, 검색 기록 있는 문서는 measured=True."""
    base = {
        "rag": {"configured_mode": "HYBRID", "effective_mode": "HYBRID", "measured": False, "actual_calls": 0, "fallback_reason": None},
        "ocr_fallback": {"configured_mode": "auto", "effective_mode": "auto", "measured": False, "actual_calls": 0},
    }
    agg_empty = aggregate_run_feature_diagnostics(base, [])
    assert agg_empty["rag"]["measured"] is False
    assert agg_empty["ocr_fallback"]["measured"] is False

    doc = SimpleNamespace(engine_data={})
    agg_one = aggregate_run_feature_diagnostics(base, [doc])
    assert agg_one["rag"]["measured"] is False
    assert agg_one["rag"].get("fallback_reason") is None
    assert agg_one["ocr_fallback"]["measured"] is True

    doc_with_ret = SimpleNamespace(engine_data={"rag": {"search_diagnostics": {"retrieval": {
        "effective_mode": "HYBRID_RERANK", "embedding_requests": 1, "reranker_requests": 1,
    }}}})
    agg_measured = aggregate_run_feature_diagnostics(base, [doc_with_ret])
    assert agg_measured["rag"]["measured"] is True
    assert agg_measured["rag"]["actual_calls"] == 2


def test_tk238_a3_effective_mode_unified_with_document_level():
    """A-3: 같은 실행에서 문서 단위 effective_mode(HYBRID_RERANK)와 run 단위 effective_mode가 일치한다."""
    ret = retrieve_hybrid_chunks(
        "계약 해지",
        [{"chunk_id": "c1", "text": "계약 해지에 관한 판례"}],
        embedding_adapter=_StubEmbedder(),
        reranker_adapter=DeterministicLegalReranker(),
    )
    telem = ret["retrieval_telemetry"]
    assert telem["effective_mode"] == "HYBRID_RERANK"
    doc = SimpleNamespace(engine_data={"rag": {"search_diagnostics": {"retrieval": telem}}})
    base = {"rag": {"configured_mode": "HYBRID", "effective_mode": "HYBRID", "measured": False, "actual_calls": 0}, "ocr_fallback": {}}
    agg = aggregate_run_feature_diagnostics(base, [doc], references_summary={"retrieval_mode": "HYBRID"})
    assert agg["rag"]["effective_mode"] == telem["effective_mode"] == "HYBRID_RERANK"

