"""TK-83 효율 라우팅(auto) 법리 검토 부분 에스컬레이션 단위 시험.

승인된 설계 메모 docs/handoff/requests/95_tk83_argument_review_partial_escalation_design.md 기준:
1. 시나리오 1: 2건 묶음 전 항목 판정 일치 시 세 번째 공급자 호출 없이 조기 종료 (2개 공급자 호출, AGREE 2건)
2. 시나리오 2: 2건 묶음 중 1건 판정 엇갈림 시 세 번째 공급자에게 해당 항목만 축소 전송 (전송 항목 축소 및 3차 취합)
3. 시나리오 3: 세 번째 공급자 호출 실패 시 1·2차 의견 보존 및 DISAGREE 처리, failure_summary 기록
4. 시나리오 4: 2차 공급자 응답에서 특정 항목 누락 시 세 번째 공급자에게 누락 항목만 축소 전송하여 완결성(2개 이상 의견) 충족
5. 발췌 바인딩(bind_argument_excerpts) 보존: 축소 요청이 first-party 발췌 보안 검사를 무결하게 통과함을 검증
"""
import asyncio
import json
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.common.config import Settings
from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.llm_router.budget import BudgetAccount, BudgetLedger, BudgetReservation
from packages.llm_router.providers import LLMRequest
from packages.llm_router.router import LLMRouter, failure_summary
from packages.legal_engine.argument_validity_verifier import (
    _OPINION_SCHEMA,
    _OPINION_SYSTEM,
    ArgumentValidityResult,
    _attach_ai_opinions,
)
from packages.common.source_trace import render_argument_context
from packages.llm_router.excerpt_source import bind_argument_excerpts, valid_excerpt_source
from packages.llm_router.routing import complete_argument_reviews, build_partial_argument_request


@pytest.fixture
def mock_llm_env(monkeypatch, tmp_path):
    """3개 공급자(Anthropic, OpenAI, Gemini) Mock 환경 구성."""
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(name, "synthetic-test-key")

    settings = Settings(
        allow_network=True,
        storage_root=tmp_path,
        llm_cross_check="auto",
        llm_efficient_routing=True,
    )
    requests_sent = []
    responses_by_family = {}

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, *, json=None, **kwargs):
            requests_sent.append((url, json))
            family = (
                "anthropic" if "anthropic" in url
                else "gemini" if "googleapis" in url
                else "openai"
            )
            resp = responses_by_family.get(family, {"rows": []})
            if isinstance(resp, int):
                return httpx.Response(resp, json={"error": "synthetic failure"})

            text = __import__("json").dumps(resp, ensure_ascii=False)
            if family == "anthropic":
                body = {"content": [{"text": text}], "usage": {"input_tokens": 100, "output_tokens": 50}}
            elif family == "gemini":
                body = {
                    "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50, "thoughtsTokenCount": 0},
                }
            else:
                body = {
                    "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                }
            return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    engine = create_engine("sqlite:///:memory:")
    BudgetAccount.metadata.create_all(engine, tables=[BudgetAccount.__table__, BudgetReservation.__table__])
    ledger = BudgetLedger(sessionmaker(engine))
    router = LLMRouter(settings=settings, ledger=ledger)
    return router, requests_sent, responses_by_family


def _make_test_request(items):
    """테스트용 argument_review_v1 요청 생성."""
    return LLMRequest(
        system=_OPINION_SYSTEM,
        user=json.dumps({"items": items}, ensure_ascii=False),
        temperature=0.1,
        max_tokens=4096,
        schema=_OPINION_SCHEMA,
        input_contract="argument_review_v1",
    )


def test_scenario_1_all_consensus_early_exit(mock_llm_env):
    """시나리오 1: 2개 항목 모두 1·2차 공급자 판정이 일치하면 3차 공급자 호출 없이 조기 종료."""
    router, requests_sent, responses = mock_llm_env

    # Anthropic(1차)와 OpenAI(2차)가 item 1, 2 모두 '타당'으로 일치 응답
    responses["anthropic"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["openai"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["gemini"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "부당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }

    items = [
        {"item_id": 1, "page": 1, "cited_case": "대법원 2020다1234", "확인 상태": "확인", "surrounding_context_and_claim": "문맥1"},
        {"item_id": 2, "page": 1, "cited_case": "대법원 2021다5678", "확인 상태": "확인", "surrounding_context_and_claim": "문맥2"},
    ]
    request = _make_test_request(items)

    answers = asyncio.run(router.consult_all(LLMRole.PRIMARY_REASONER, request))

    # 1·2차 2곳만 호출되고 Gemini는 호출되지 않아야 함
    assert len(requests_sent) == 2
    called_providers = {e.provider for a in answers for e in a.executions if e.ok}
    assert called_providers == {"anthropic", "openai"}


def test_scenario_2_partial_conflict_reduced_payload(mock_llm_env):
    """시나리오 2: 2개 항목 중 1개 항목만 엇갈린 경우 세 번째 공급자에게 해당 항목만 축소 전송."""
    router, requests_sent, responses = mock_llm_env

    # item 1은 둘 다 '타당' 일치, item 2는 '타당' vs '부당' 불일치
    responses["anthropic"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["openai"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["gemini"] = {
        "rows": [
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2_gemini", "recommended_check": "확인2"},
        ]
    }

    items = [
        {"item_id": 1, "page": 1, "cited_case": "대법원 2020다1234", "확인 상태": "확인", "surrounding_context_and_claim": "문맥1"},
        {"item_id": 2, "page": 1, "cited_case": "대법원 2021다5678", "확인 상태": "확인", "surrounding_context_and_claim": "문맥2"},
    ]
    request = _make_test_request(items)

    answers = asyncio.run(router.consult_all(LLMRole.PRIMARY_REASONER, request))

    # 3개 공급자가 모두 호출됨
    assert len(requests_sent) == 3
    called_providers = {e.provider for a in answers for e in a.executions if e.ok}
    assert called_providers == {"anthropic", "openai", "gemini"}

    # 세 번째 공급자(Gemini)에게 전달된 user 본문 검증: 오직 item_id 2만 포함되어야 함
    gemini_body = requests_sent[2][1]
    gemini_user_raw = gemini_body["contents"][0]["parts"][0]["text"]
    gemini_items = json.loads(gemini_user_raw)["items"]
    assert [it["item_id"] for it in gemini_items] == [2]

    # 전송 항목 축소율 측정: 원래 2개 항목 중 1개만 전송 (50% 전송 항목 축소 달성)
    gemini_answer = [a for a in answers if any(e.provider == "gemini" for e in a.executions)][0]
    assert gemini_answer.used


def test_scenario_3_third_provider_failure_preserves_disagree(mock_llm_env):
    """시나리오 3: 세 번째 공급자 호출 실패 시 1·2차 의견을 보존하여 DISAGREE로 안전하게 처리."""
    router, requests_sent, responses = mock_llm_env

    responses["anthropic"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["openai"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    # Gemini는 500 서버 에러로 실패 (재시도 후 최종 실패)
    responses["gemini"] = 500

    items = [
        {"item_id": 1, "page": 1, "cited_case": "대법원 2020다1234", "확인 상태": "확인", "surrounding_context_and_claim": "문맥1"},
        {"item_id": 2, "page": 1, "cited_case": "대법원 2021다5678", "확인 상태": "확인", "surrounding_context_and_claim": "문맥2"},
    ]
    request = _make_test_request(items)

    answers = asyncio.run(router.consult_all(LLMRole.PRIMARY_REASONER, request))

    # Gemini 요청이 시도되었으나 최종 실패
    assert len(requests_sent) >= 3
    gemini_executions = [e for a in answers for e in a.executions if e.provider == "gemini"]
    assert len(gemini_executions) > 0
    assert all(e.ok is False for e in gemini_executions)

    # 1·2차 의견은 보존되어 used answers는 2개
    used_answers = [a for a in answers if a.used]
    assert len(used_answers) == 2

    # failures summary에 gemini 오류 기록 확인
    failures = failure_summary(answers)
    assert "gemini" in failures


def test_scenario_4_incomplete_response_triggers_partial_escalation(mock_llm_env):
    """시나리오 4: 2차 공급자에서 한 항목이 누락된 경우 미비 항목만 세 번째 공급자에게 축소 전송하여 완결성 보장."""
    router, requests_sent, responses = mock_llm_env

    # 1차(Anthropic)는 1, 2 모두 응답
    responses["anthropic"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    # 2차(OpenAI)는 item 1만 응답하고 item 2를 누락함
    responses["openai"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
        ]
    }
    # 3차(Gemini)는 누락된 item 2에 대해 응답
    responses["gemini"] = {
        "rows": [
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2_gemini", "recommended_check": "확인2"},
        ]
    }

    items = [
        {"item_id": 1, "page": 1, "cited_case": "대법원 2020다1234", "확인 상태": "확인", "surrounding_context_and_claim": "문맥1"},
        {"item_id": 2, "page": 1, "cited_case": "대법원 2021다5678", "확인 상태": "확인", "surrounding_context_and_claim": "문맥2"},
    ]
    request = _make_test_request(items)

    answers = asyncio.run(router.consult_all(LLMRole.PRIMARY_REASONER, request))

    assert len(requests_sent) == 3
    # Gemini에게 전달된 요청에 item 1은 없고 누락되었던 item 2만 포함되어야 함
    gemini_body = requests_sent[2][1]
    gemini_user_raw = gemini_body["contents"][0]["parts"][0]["text"]
    gemini_items = json.loads(gemini_user_raw)["items"]
    assert [it["item_id"] for it in gemini_items] == [2]

    # 완결성 검사(complete_argument_reviews) 통과 확인
    assert complete_argument_reviews(request, answers) is True


def test_excerpt_binding_preservation_in_partial_escalation(mock_llm_env):
    """발췌 바인딩(bind_argument_excerpts)을 갖는 요청에서 축소된 요청이 유효한 first-party 발췌 출처를 보존함을 검증."""
    router, requests_sent, responses = mock_llm_env

    responses["anthropic"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["openai"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    responses["gemini"] = {
        "rows": [
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2_gemini", "recommended_check": "확인2"},
        ]
    }

    rendered_1, piece_1 = render_argument_context(lambda x: x, "문맥1의 출처 원문")
    rendered_2, piece_2 = render_argument_context(lambda x: x, "문맥2의 출처 원문")

    items = [
        {"item_id": 1, "page": 1, "cited_case": "대법원 2020다1234", "확인 상태": "확인", "surrounding_context_and_claim": rendered_1},
        {"item_id": 2, "page": 1, "cited_case": "대법원 2021다5678", "확인 상태": "확인", "surrounding_context_and_claim": rendered_2},
    ]
    base_req = _make_test_request(items)
    excerpt_req = bind_argument_excerpts(base_req, (piece_1, piece_2))

    assert valid_excerpt_source(excerpt_req)

    reduced_req = build_partial_argument_request(excerpt_req, {"2"})

    # 축소된 요청도 valid_excerpt_source 검사를 통과해야 함
    assert valid_excerpt_source(reduced_req)
    reduced_items = json.loads(reduced_req.user)["items"]
    assert len(reduced_items) == 1
    assert reduced_items[0]["item_id"] == 2
    assert reduced_items[0]["surrounding_context_and_claim"] == rendered_2


def test_attach_ai_opinions_end_to_end_synthesis(mock_llm_env):
    """_attach_ai_opinions 전체 파이프라인에서 부분 에스컬레이션 결과가 정상 합성됨을 검증."""
    from types import SimpleNamespace
    from packages.legal_engine.argument_validity_verifier import HallucinationTableRow

    router, requests_sent, responses = mock_llm_env

    # 1차(Anthropic): item 1 타당, item 2 타당
    responses["anthropic"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "타당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    # 2차(OpenAI): item 1 타당, item 2 부당 (item 2 엇갈림)
    responses["openai"] = {
        "rows": [
            {"item_id": 1, "validity_verdict": "타당", "claim_text": "주장1", "legal_reasoning": "이유1", "recommended_check": "확인1"},
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2", "recommended_check": "확인2"},
        ]
    }
    # 3차(Gemini): item 2만 축소 전달받고 부당으로 응답
    responses["gemini"] = {
        "rows": [
            {"item_id": 2, "validity_verdict": "부당", "claim_text": "주장2", "legal_reasoning": "이유2_gemini", "recommended_check": "확인2"},
        ]
    }

    row1 = HallucinationTableRow(
        location="1페이지", claim_text="주장1", cited_authority="판례1",
        authority_exists=False, ai_generation_basis="", validity_verdict="타당",
        legal_reasoning="검토의견1", recommended_counteraction="", item_id=1,
    )
    row2 = HallucinationTableRow(
        location="2페이지", claim_text="주장2", cited_authority="판례2",
        authority_exists=False, ai_generation_basis="", validity_verdict="부당",
        legal_reasoning="검토의견2", recommended_counteraction="", item_id=2,
    )
    result = ArgumentValidityResult(rows=[row1, row2])

    unverified_cases = [
        {"citation": SimpleNamespace(raw_text="판례1", page=1), "basis": "UNCONFIRMED", "context": "주장1 문맥"},
        {"citation": SimpleNamespace(raw_text="판례2", page=2), "basis": "UNCONFIRMED", "context": "주장2 문맥"},
    ]

    asyncio.run(_attach_ai_opinions(result, unverified_cases, router, ExternalAIPolicy.MASKED, None))

    # item 1: 2개 모델 일치 -> AGREE
    assert row1.ai_agreement == "AGREE"
    assert "2개 모델 의견 일치" in row1.ai_label
    assert len(row1.ai_opinions) == 2

    # item 2: 3개 모델 의견 불일치 (타당 1, 부당 2) -> DISAGREE
    assert row2.ai_agreement == "DISAGREE"
    assert "3개 모델 의견 불일치" in row2.ai_label
    assert len(row2.ai_opinions) == 3

    # Gemini에 전달된 user 요청 본문에 item 2만 존재했는지 재확인 (50% 항목 축소)
    gemini_body = requests_sent[2][1]
    gemini_user_raw = gemini_body["contents"][0]["parts"][0]["text"]
    gemini_items = json.loads(gemini_user_raw)["items"]
    assert [it["item_id"] for it in gemini_items] == [2]

