"""TK-190: Gemini 추론 토큰 소진 방지·예산·유한 재시도·대체 공급자·실패 보존 검증."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from packages.common.config import ProviderConfig, get_settings, reset_settings
from packages.common.enums import EvidenceGrade, ExternalAIPolicy, LLMRole, VerificationStatus
from packages.legal_engine.argument_validity_verifier import (
    _OPINION_SCHEMA,
    _OPINION_SYSTEM,
    _retry_truncated_singly,
)
from packages.llm_router.budget import BudgetLedger, budget_settings, estimate_call
from packages.llm_router.cascade_source import build_cascade_request
from packages.llm_router.providers import GeminiProvider, LLMProvider, LLMRequest, LLMResponse
from packages.llm_router.router import LLMRouter, RouterResult, describe_failure


def _ledger(tmp_path, name="budget.db"):
    engine = create_engine(f"sqlite:///{tmp_path / name}", future=True)
    return BudgetLedger(sessionmaker(engine))


def _gemini_config(model: str) -> ProviderConfig:
    return ProviderConfig(
        name="gemini",
        enabled=True,
        api_key_env="GEMINI_API_KEY",
        model=model,
        base_url="https://generativelanguage.googleapis.com/v1beta",
        kind="cloud",
    )


def _setup_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    monkeypatch.delenv("LV_LLM_MAX_OUTPUT_TOKENS", raising=False)
    reset_settings()


@pytest.mark.parametrize(
    "model_name, metadata, expected_thinking, expected_temp",
    [
        ("gemini-4-hydrogen", {}, {"thinkingLevel": "LOW"}, False),
        ("gemini-4-argon", {}, {"thinkingLevel": "LOW"}, True),
        ("gemini-4-carbon", {"thinking_level": "MINIMAL"}, {"thinkingLevel": "LOW"}, True),
        ("gemini-3.8-flash", {"thinking_level": "MINIMAL"}, {"thinkingLevel": "LOW"}, True),
        ("gemini-3.1-pro", {}, {"thinkingLevel": "LOW"}, True),
        ("gemini-3.6-flash", {"thinking_level": "MINIMAL"}, {"thinkingLevel": "MINIMAL"}, True),
        ("gemini-2.5-pro", {}, {"thinkingBudget": 1024}, True),
        ("gemini-2.5-flash", {"thinking_level": "LOW"}, {"thinkingBudget": 512}, True),
        ("operator-custom-gemini", {}, None, True),
    ],
)
def test_gemini_thinking_config_respects_model_contract_without_guessing(
    monkeypatch, model_name, metadata, expected_thinking, expected_temp
):
    sent = []

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            sent.append(json)
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": '{"status": "VERIFIED"}'}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 12, "thoughtsTokenCount": 40},
                },
            )

    _setup_env(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    monkeypatch.setattr(GeminiProvider, "_quirks", {})
    try:
        provider = GeminiProvider(_gemini_config(model_name))
        req = LLMRequest("sys", "user", max_tokens=4096, temperature=0.2, schema={"type": "object"}, metadata=metadata)
        res = asyncio.run(provider.generate(req))
        assert res.ok
        assert res.thinking_tokens == 40
        assert res.output_tokens == 52
        gen_cfg = sent[-1]["generationConfig"]
        assert gen_cfg.get("thinkingConfig") == expected_thinking
        if expected_temp:
            assert gen_cfg["temperature"] == 0.2
        else:
            assert "temperature" not in gen_cfg
    finally:
        reset_settings()


@pytest.mark.parametrize(
    "label, verdict_payload",
    [
        (
            "short_korean_citation",
            {
                "status": "VERIFIED",
                "confidence": 0.92,
                "rationale": "공식 판례 원문과 대조한 결과 법리가 일치한다.",
                "evidence_quotes": ["손해배상 책임의 성립 요건을 충족한다."],
                "contradicts": False,
            },
        ),
        (
            "long_korean_multi_quote",
            {
                "status": "PARTIALLY_VERIFIED",
                "confidence": 0.78,
                "rationale": "원고 주장의 일반 원칙은 공식 원문과 부합하나, 예외 사유 적용 범위가 더 좁다. " * 3,
                "evidence_quotes": [
                    "법원은 계약 해석의 객관적 기준을 우선한다.",
                    "다만 신의칙 위반 여부는 구체적 사정을 종합해 판단한다.",
                ],
                "contradicts": False,
            },
        ),
        (
            "contradicted_korean_verdict",
            {
                "status": "CONTRADICTED",
                "confidence": 0.89,
                "rationale": "서면이 인용한 효력 기준과 달리 공식 원문은 반대 취지로 판시하였다.",
                "evidence_quotes": ["단독 사유만으로 취소권을 행사할 수 없다."],
                "contradicts": True,
            },
        ),
    ],
)
def test_gemini4_cascade_grounded_korean_verdicts_record_tokens_cost_and_model(
    monkeypatch, tmp_path, label, verdict_payload
):
    sent = []

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            sent.append(json)
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {"parts": [{"text": json_lib.dumps(verdict_payload, ensure_ascii=False)}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 420,
                        "candidatesTokenCount": 180,
                        "thoughtsTokenCount": 240,
                    },
                },
            )

    import json as json_lib

    _setup_env(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    monkeypatch.setattr(GeminiProvider, "_quirks", {})
    try:
        settings = get_settings()
        provider = GeminiProvider(_gemini_config("gemini-4-hydrogen"))
        router = LLMRouter({"gemini": provider}, settings=settings, ledger=_ledger(tmp_path, f"{label}.db"))
        req = build_cascade_request(
            "grounder",
            "판례 요지 대조",
            {
                "official": {"full_text": " ".join(verdict_payload["evidence_quotes"])},
                "document": f"검토 대상 주장 ({label})",
            },
        )
        assert req.max_tokens <= router.limits["max_output_tokens"]
        result = asyncio.run(router.run(LLMRole.WEB_GROUNDER, req, policy=ExternalAIPolicy.MASKED))
        assert result.used
        assert result.parsed["status"] == verdict_payload["status"]
        assert result.parsed["evidence_quotes"] == verdict_payload["evidence_quotes"]
        ex = result.executions[0]
        assert ex.model == "gemini-4-hydrogen"
        assert ex.thinking_tokens == 240
        assert ex.output_tokens == 420
        assert ex.cost_status == "REPORTED"
        assert ex.cost_usd > 0
        assert sent[-1]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}
    finally:
        reset_settings()


def test_multi_opinion_argument_review_and_retry_recovery_on_max_tokens(monkeypatch, tmp_path):
    """MAX_TOKENS 빈 본문 1회 실패 후 예산 범위 내 유한 재시도로 복구하며, 최초 실패와 재시도를 모두 보존한다."""
    calls = []

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            calls.append(json)
            if len(calls) == 1:
                return httpx.Response(
                    200,
                    json={
                        "candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}],
                        "usageMetadata": {"promptTokenCount": 500, "candidatesTokenCount": 0, "thoughtsTokenCount": 4093},
                    },
                )
            body = {
                "overall_summary": "보존된 법리 요약",
                "rows": [
                    {
                        "item_id": 1,
                        "claim_text": "법정 요건 충족 주장",
                        "validity_verdict": "일부 타당",
                        "legal_reasoning": "공식 원문상 일반 원칙은 인정되나 적용 조건 확인이 필요하다.",
                        "recommended_check": "계약 체결 경위를 추가로 확인한다.",
                    }
                ],
            }
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": json_lib.dumps(body, ensure_ascii=False)}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 500, "candidatesTokenCount": 140, "thoughtsTokenCount": 310},
                },
            )

    import json as json_lib

    _setup_env(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    monkeypatch.setattr(GeminiProvider, "_quirks", {})
    try:
        settings = get_settings()
        ledger = _ledger(tmp_path, "retry.db")
        provider = GeminiProvider(_gemini_config("gemini-4-hydrogen"))
        router = LLMRouter({"gemini": provider}, settings=settings, ledger=ledger, run_id="tk190-retry")
        req = LLMRequest(
            system=_OPINION_SYSTEM,
            user=json.dumps({"items": [{"item_id": 1, "claim": "주장 1"}]}, ensure_ascii=False),
            max_tokens=4096,
            schema=_OPINION_SCHEMA,
        )
        res = asyncio.run(router.run(LLMRole.PRIMARY_REASONER, req, policy=ExternalAIPolicy.MASKED))
        assert res.used
        assert len(calls) == 2
        assert calls[1]["generationConfig"]["maxOutputTokens"] == 8192
        assert calls[1]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}
        assert len(res.executions) == 2
        first, second = res.executions
        assert not first.ok and "EMPTY_RESPONSE" in first.error and "MAX_TOKENS" in first.error
        assert first.thinking_tokens == 4093
        assert second.ok and second.thinking_tokens == 310
        assert first.reservation_id != second.reservation_id
        acct = ledger.account("run:tk190-retry")
        assert acct["reserved"] == Decimal(0)
        assert acct["spent"] > Decimal(0)
    finally:
        reset_settings()


def test_argument_validity_retry_singly_triggers_on_empty_max_tokens():
    calls = []

    class _Router:
        async def run(self, role, request, exclude=None, **kwargs):
            item_id = json.loads(request.user)["items"][0]["item_id"]
            calls.append((item_id, exclude))
            return RouterResult(
                used=True,
                parsed={"rows": [{"item_id": item_id, "validity_verdict": "타당", "legal_reasoning": "개별 확인"}]},
                executions=[SimpleNamespace(provider="gemini", model="gemini-4-hydrogen", ok=True, error="")],
            )

    batch = [
        {"item_id": 1, "cited_case": "합성 사건 1"},
        {"item_id": 2, "cited_case": "합성 사건 2"},
    ]
    replies = [
        RouterResult(
            used=False,
            executions=[
                SimpleNamespace(
                    provider="gemini",
                    error="EMPTY_RESPONSE: 본문 없는 응답(finishReason=MAX_TOKENS, thinking 4093 tokens, 한도 4096)",
                )
            ],
        ),
        RouterResult(
            used=True,
            parsed={"rows": []},
            executions=[SimpleNamespace(provider="openai", error="")],
        ),
    ]
    recovered = asyncio.run(_retry_truncated_singly(_Router(), replies, batch, ExternalAIPolicy.MASKED))
    assert len(recovered) == 2
    assert calls == [(1, ["openai"]), (2, ["openai"])]


def test_empty_response_other_is_distinct_and_not_retried(monkeypatch, tmp_path):
    calls = 0

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            nonlocal calls
            calls += 1
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": []}, "finishReason": "OTHER"}],
                    "usageMetadata": {"promptTokenCount": 80, "candidatesTokenCount": 0, "thoughtsTokenCount": 0},
                },
            )

    _setup_env(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    monkeypatch.setattr(GeminiProvider, "_quirks", {})
    try:
        settings = get_settings()
        router = LLMRouter({"gemini": GeminiProvider(_gemini_config("gemini-4-hydrogen"))}, settings=settings, ledger=_ledger(tmp_path, "other.db"))
        res = asyncio.run(router.run(LLMRole.WEB_GROUNDER, LLMRequest("s", "u", max_tokens=4096)))
        assert not res.used
        assert calls == 1
        assert "finishReason=OTHER" in res.executions[0].error
        assert describe_failure(res.executions[0].error) == "본문 없는 응답(OTHER)"
        assert describe_failure("EMPTY_RESPONSE: 본문 없는 응답(finishReason=MAX_TOKENS, thinking 4093 tokens, 한도 4096)") == "본문 없는 응답(출력 한도·추론 토큰 소진)"
    finally:
        reset_settings()


def test_truncated_json_and_400_thinking_quirk_fallback(monkeypatch):
    sent = []
    mode = "truncated"

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            sent.append(json)
            if mode == "truncated":
                return httpx.Response(
                    200,
                    json={
                        "candidates": [{"content": {"parts": [{"text": '{"status": "VERIFIED", "rationale": "중단'}]}, "finishReason": "MAX_TOKENS"}],
                        "usageMetadata": {"promptTokenCount": 30, "candidatesTokenCount": 500, "thoughtsTokenCount": 100},
                    },
                )
            if len(sent) == 2:
                return httpx.Response(400, text='{"error": {"message": "Unknown name \\"thinkingLevel\\": Cannot find field"}}')
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": '{"status": "VERIFIED"}'}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 30, "candidatesTokenCount": 10, "thoughtsTokenCount": 0},
                },
            )

    _setup_env(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    monkeypatch.setattr(GeminiProvider, "_quirks", {})
    try:
        provider = GeminiProvider(_gemini_config("gemini-3.8-flash"))
        req = LLMRequest("s", "u", max_tokens=4096, schema={"type": "object"})
        trunc = asyncio.run(provider.generate(req))
        assert not trunc.ok and trunc.error.startswith("OUTPUT_TRUNCATED")

        mode = "quirk"
        recovered = asyncio.run(provider.generate(req))
        assert recovered.ok
        assert "thinkingConfig" in sent[1]["generationConfig"]
        assert "thinkingConfig" not in sent[2]["generationConfig"]

        # 학습된 quirk는 다음 호출에 매번 400을 맞지 않도록 재사용한다.
        sent.clear()
        again = asyncio.run(provider.generate(req))
        assert again.ok and len(sent) == 1 and "thinkingConfig" not in sent[0]["generationConfig"]
    finally:
        reset_settings()


def test_budget_cap_exhaustion_and_fallback_failure_stay_fail_closed(monkeypatch, tmp_path):
    class _FailingProvider(LLMProvider):
        available = True

        def __init__(self, name: str, err: str, *, kind: str = "local"):
            self.name = name
            super().__init__(ProviderConfig(name=name, enabled=True, model="gemini-4-hydrogen", kind=kind))
            self.err = err
            self.calls = 0

        async def generate(self, request: LLMRequest) -> LLMResponse:
            self.calls += 1
            return LLMResponse(False, provider=self.name, model="gemini-4-hydrogen", input_tokens=50, output_tokens=10, error=self.err)

    _setup_env(monkeypatch)
    try:
        settings = get_settings()
        assert budget_settings(settings)["max_output_tokens"] == 8192

        # 1) 출력 상한 초과 요청은 예산 검사에서 거절한다.
        gemini = GeminiProvider(_gemini_config("gemini-4-hydrogen"))
        router = LLMRouter({"gemini": gemini}, settings=settings, ledger=_ledger(tmp_path, "cap.db"))
        over_cap = asyncio.run(router.run(LLMRole.WEB_GROUNDER, LLMRequest("s", "u", max_tokens=16384)))
        assert not over_cap.used
        assert over_cap.executions[0].error.startswith("BUDGET_ADMISSION_FAILED:")
        assert over_cap.executions[0].cost_status == "NOT_SENT"

        # 2) 예산 부족 상태에서 MAX_TOKENS 재시도는 예산을 우회하지 않고 차단된다.
        tight_ledger = _ledger(tmp_path, "tight.db")
        tight_cap = _FailingProvider(
            "gemini",
            "EMPTY_RESPONSE: 본문 없는 응답(finishReason=MAX_TOKENS, thinking 4093 tokens, 한도 4096)",
            kind="cloud",
        )
        tight_router = LLMRouter(
            {"gemini": tight_cap},
            settings=replace(settings, pricing={"gemini-4-hydrogen": {"input": 1.5, "output": 7.5}}),
            ledger=tight_ledger,
            run_id="tight-run",
            limits={**budget_settings(settings), "run_limit": "0.06", "max_input_tokens": 4096},
        )
        estimate, _ = estimate_call(tight_router.settings, tight_cap, LLMRequest("s", "u", max_tokens=4096), tight_router.limits)
        assert Decimal("0.01") < estimate < Decimal("0.06")
        tight_res = asyncio.run(tight_router.run(LLMRole.WEB_GROUNDER, LLMRequest("s", "u", max_tokens=4096)))
        assert not tight_res.used
        assert tight_res.executions[0].error.startswith("EMPTY_RESPONSE:")
        assert tight_res.executions[-1].error.startswith("BUDGET_ADMISSION_FAILED:")
        assert tight_cap.calls == 1

        # 3) 주 공급자·재시도·대체 공급자 모두 실패하면 모든 기록을 보존하고 UNVERIFIED를 반환한다.
        g_fail = _FailingProvider("gemini", "EMPTY_RESPONSE: 본문 없는 응답(finishReason=MAX_TOKENS, thinking 4096 tokens, 한도 4096)")
        o_fail = _FailingProvider("openai", "HTTP 503: overloaded")
        fallback_router = LLMRouter({"gemini": g_fail, "openai": o_fail}, settings=settings, ledger=_ledger(tmp_path, "fb.db"))
        fallback_router.retry_delays = ()
        grounder_res = asyncio.run(
            fallback_router.run_any(LLMRole.WEB_GROUNDER, LLMRequest("s", "u", max_tokens=4096))
        )
        assert not grounder_res.used
        assert g_fail.calls == 2
        assert o_fail.calls == 1
        assert [e.provider for e in grounder_res.executions] == ["gemini", "gemini", "openai"]

        outcome = asyncio.run(
            fallback_router.cascade(
                question="판례 확인",
                evidence={"official": {"full_text": "공식 원문"}, "document": "문서 주장"},
            )
        )
        assert outcome.status == VerificationStatus.UNVERIFIED
        assert outcome.evidence_grade == EvidenceGrade.U
    finally:
        reset_settings()


def test_privacy_and_output_injection_boundaries_hold_after_tk190(tmp_path):
    class _LeakyProvider(LLMProvider):
        name = "gemini"
        available = True

        def __init__(self):
            super().__init__(_gemini_config("gemini-4-hydrogen"))

        async def generate(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(True, provider="gemini", model="gemini-4-hydrogen", text='{"url": "https://evil.example/exfil"}')

    router = LLMRouter({"gemini": _LeakyProvider()}, ledger=_ledger(tmp_path, "sec.db"))
    blocked = asyncio.run(
        router.run(
            LLMRole.WEB_GROUNDER,
            LLMRequest("sys", "식별번호 900101-1234567 원문", max_tokens=4096),
            policy=ExternalAIPolicy.MASKED,
        )
    )
    assert not blocked.used and blocked.executions[0].error.startswith("INPUT_PRIVACY_BLOCKED")

    quarantined = asyncio.run(
        router.run(
            LLMRole.WEB_GROUNDER,
            LLMRequest("sys", "안전한 입력", max_tokens=4096),
            policy=ExternalAIPolicy.MASKED,
        )
    )
    assert not quarantined.used and quarantined.quarantined
