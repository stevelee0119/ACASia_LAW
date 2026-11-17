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


def test_retry_preserves_minimal_thinking_level_and_rechecks_privacy_and_guard(monkeypatch, tmp_path):
    """복구 재시도는 MINIMAL을 LOW로 올리지 않으며, 재시도 전 개인정보 검사·provider guard·예약 회계를 모두 통과해야 한다."""
    from packages.llm_router import router as router_module
    from packages.llm_router.budget import BudgetReservation

    sent_payloads = []
    mode = "minimal"

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            sent_payloads.append(json)
            if len(sent_payloads) == 1:
                return httpx.Response(
                    200,
                    json={
                        "candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}],
                        "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 0, "thoughtsTokenCount": 4090},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json_lib.dumps(
                                            {"overall_summary": "완료", "rows": [{"item_id": 1, "validity_verdict": "타당"}]},
                                            ensure_ascii=False,
                                        )
                                    }
                                ]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 90, "thoughtsTokenCount": 120},
                },
            )

    import json as json_lib

    _setup_env(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    monkeypatch.setattr(GeminiProvider, "_quirks", {})
    try:
        settings = get_settings()

        # 1) MINIMAL thinking_level은 LOW로 높이지 않고 유지하며 별도 예약을 재계산·정산한다.
        ledger_min = _ledger(tmp_path, "minimal.db")
        router_min = LLMRouter(
            {"gemini": GeminiProvider(_gemini_config("gemini-3.6-flash"))},
            settings=settings,
            ledger=ledger_min,
            run_id="tk190-minimal",
        )
        req_min = LLMRequest(
            system=_OPINION_SYSTEM,
            user=json.dumps({"items": [{"item_id": 1, "claim": "합성 법리 주장"}]}, ensure_ascii=False),
            max_tokens=4096,
            schema=_OPINION_SCHEMA,
            metadata={"thinking_level": "MINIMAL"},
        )
        res_min = asyncio.run(router_min.run(LLMRole.PRIMARY_REASONER, req_min, policy=ExternalAIPolicy.MASKED))
        assert res_min.used
        assert len(sent_payloads) == 2
        assert sent_payloads[0]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "MINIMAL"}
        assert sent_payloads[1]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "MINIMAL"}
        assert sent_payloads[1]["generationConfig"]["maxOutputTokens"] == 8192

        with ledger_min.factory() as session:
            rows = list(
                session.execute(
                    select(BudgetReservation).where(BudgetReservation.run_id == "tk190-minimal")
                ).scalars()
            )
        assert len(rows) == 2
        assert rows[0].detail["output_cap"] == 4096
        assert rows[1].detail["output_cap"] == 8192
        assert rows[1].reserved_units > rows[0].reserved_units
        assert all(row.state == "SETTLED" for row in rows)
        assert ledger_min.account("run:tk190-minimal")["reserved"] == Decimal(0)

        # 2) 재시도 전 개인정보 검사에서 차단되면 2차 예약/전송 없이 첫 실행만 남기고 차단한다.
        sent_payloads.clear()
        privacy_calls = []
        orig_inspect = router_module.LLMRouter.run

        class _MockPrivacy:
            calls = 0

        from packages.llm_router import privacy as privacy_mod

        def _fail_second_privacy(req, *, _original_system=None):
            _MockPrivacy.calls += 1
            privacy_calls.append(req.max_tokens)
            if _MockPrivacy.calls >= 2:
                return {"status": "BLOCKED", "failure_code": "RETRY_POLICY_DENIED", "diagnostic_category": "RETRY_POLICY"}
            return {"status": "PASSED"}

        monkeypatch.setattr(privacy_mod, "inspect_request", _fail_second_privacy)
        ledger_priv = _ledger(tmp_path, "priv_retry.db")
        router_priv = LLMRouter(
            {"gemini": GeminiProvider(_gemini_config("gemini-4-hydrogen"))},
            settings=settings,
            ledger=ledger_priv,
            run_id="tk190-priv-retry",
        )
        res_priv = asyncio.run(
            router_priv.run(LLMRole.PRIMARY_REASONER, LLMRequest("sys", "합성 주장", max_tokens=4096), policy=ExternalAIPolicy.MASKED)
        )
        assert not res_priv.used
        assert len(sent_payloads) == 1
        assert privacy_calls == [4096, 8192]
        assert len(res_priv.executions) == 2
        assert res_priv.executions[0].error.startswith("EMPTY_RESPONSE:")
        assert res_priv.executions[1].error.startswith("INPUT_PRIVACY_BLOCKED")
        assert ledger_priv.account("run:tk190-priv-retry")["reserved"] == Decimal(0)
        assert orig_inspect is not None

        # 3) 재시도 dispatch 시 provider_guard가 거부하면 2차 예약을 즉시 release하고 첫 실행/정산을 보존한다.
        sent_payloads.clear()
        monkeypatch.undo()
        _setup_env(monkeypatch)
        monkeypatch.setattr(httpx, "AsyncClient", _Client)
        monkeypatch.setattr(GeminiProvider, "_quirks", {})
        guard_calls = 0

        def _guard_block_second(provider, policy, *, session=None):
            nonlocal guard_calls
            guard_calls += 1
            if guard_calls >= 2:
                raise PermissionError("재시도 공급자 차단")

        ledger_guard = _ledger(tmp_path, "guard_retry.db")
        router_guard = LLMRouter(
            {"gemini": GeminiProvider(_gemini_config("gemini-4-hydrogen"))},
            settings=settings,
            ledger=ledger_guard,
            run_id="tk190-guard-retry",
            provider_guard=_guard_block_second,
        )
        res_guard = asyncio.run(
            router_guard.run(LLMRole.PRIMARY_REASONER, LLMRequest("sys", "안전한 입력", max_tokens=4096), policy=ExternalAIPolicy.MASKED)
        )
        assert not res_guard.used
        assert len(sent_payloads) == 1
        assert len(res_guard.executions) == 2
        assert res_guard.executions[0].error.startswith("EMPTY_RESPONSE:")
        assert res_guard.executions[0].cost_status == "REPORTED"
        assert res_guard.executions[1].error.startswith("PROVIDER_POLICY_BLOCKED:")
        assert res_guard.executions[1].cost_status == "NOT_SENT"
        with ledger_guard.factory() as session:
            guard_rows = list(
                session.execute(
                    select(BudgetReservation).where(BudgetReservation.run_id == "tk190-guard-retry")
                ).scalars()
            )
        assert [row.state for row in guard_rows] == ["SETTLED", "RELEASED"]
        assert ledger_guard.account("run:tk190-guard-retry")["reserved"] == Decimal(0)
        assert mode == "minimal"
    finally:
        reset_settings()


def test_retry_quarantined_preserves_first_exec_and_cascade_stays_unverified(monkeypatch, tmp_path):
    """복구 재시도가 출력 보안 검사에서 격리되어도 첫 실행 기록·원장 정산을 보존하고 Cascade는 UNVERIFIED를 유지한다."""
    calls = 0

    class _QuarantineRetryProvider(LLMProvider):
        name = "gemini"
        available = True

        def __init__(self):
            super().__init__(_gemini_config("gemini-4-hydrogen"))

        async def generate(self, request: LLMRequest) -> LLMResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                return LLMResponse(
                    False,
                    provider="gemini",
                    model="gemini-4-hydrogen",
                    input_tokens=120,
                    output_tokens=4090,
                    thinking_tokens=4090,
                    error="EMPTY_RESPONSE: 본문 없는 응답(finishReason=MAX_TOKENS, thinking 4090 tokens, 한도 4096)",
                )
            return LLMResponse(
                True,
                provider="gemini",
                model="gemini-4-hydrogen",
                input_tokens=120,
                output_tokens=80,
                text='{"status": "VERIFIED", "rationale": "https://evil.example/leak"}',
            )

    _setup_env(monkeypatch)
    try:
        settings = get_settings()
        ledger = _ledger(tmp_path, "quarantine_retry.db")
        router = LLMRouter(
            {"gemini": _QuarantineRetryProvider()},
            settings=settings,
            ledger=ledger,
            run_id="tk190-quarantine-retry",
        )
        res = asyncio.run(
            router.run(LLMRole.WEB_GROUNDER, LLMRequest("sys", "안전한 원문", max_tokens=4096), policy=ExternalAIPolicy.MASKED)
        )
        assert not res.used
        assert res.quarantined
        assert len(res.executions) == 2
        assert res.executions[0].error.startswith("EMPTY_RESPONSE:")
        assert res.executions[0].thinking_tokens == 4090
        assert res.executions[1].error.startswith("OUTPUT_QUARANTINED:")
        assert res.executions[0].reservation_id != res.executions[1].reservation_id
        assert ledger.account("run:tk190-quarantine-retry")["reserved"] == Decimal(0)
        assert ledger.account("run:tk190-quarantine-retry")["spent"] > Decimal(0)

        calls = 0
        outcome = asyncio.run(
            router.cascade(
                question="판례 확인",
                evidence={"official": {"full_text": "공식 판결 요지"}, "document": "문서 주장 본문"},
            )
        )
        assert outcome.status == VerificationStatus.UNVERIFIED
        assert outcome.evidence_grade == EvidenceGrade.U
    finally:
        reset_settings()


def test_attested_argument_review_split_retry_on_empty_max_tokens(monkeypatch, tmp_path):
    """EMPTY_RESPONSE+MAX_TOKENS 단건 분할 재시도에서도 TK-181 item_provenance·excerpt·exclude·원래 item_id를 보존한다."""
    from packages.common.enums import CitationType
    from packages.common.schemas import Block, Citation, NormalizedDocument, Page
    from packages.common.source_trace import model_input_renderer
    from packages.legal_engine.argument_validity_verifier import verify_argument_validity
    from packages.llm_router.token_attestation import has_token_attestation, valid_token_attestation
    from packages.pii_engine.engine import PIIEngine
    from packages.pii_engine.pseudonym import PseudonymStore

    engine = PIIEngine(PseudonymStore("tk190_arg_attest", root=tmp_path))
    renderer = model_input_renderer(engine, [], original=False)

    body = "당사자 홍길동(010-2222-3333)은 대법원 2020다11111 판결 및 대법원 2021다22222 판결을 인용하여 주장한다."
    doc = NormalizedDocument(
        document_id="doc_tk190_arg",
        filename="합성_준비서면.pdf",
        mime_type="application/pdf",
        sha256="sha_tk190_arg",
        pages=[Page(1, blocks=[Block("b1", body, 1, source_layer="visible_text")])],
    )
    doc.raw_layers["visible_text"] = body
    c_confirmed = Citation(
        citation_id="cit_0", document_id="doc_tk190_arg", type=CitationType.CASE,
        raw_text="대법원 2019다99999 판결", page=1, context=body,
    )
    c1 = Citation(
        citation_id="cit_1", document_id="doc_tk190_arg", type=CitationType.CASE,
        raw_text="대법원 2020다11111 판결", page=1, context=body,
    )
    c2 = Citation(
        citation_id="cit_2", document_id="doc_tk190_arg", type=CitationType.CASE,
        raw_text="대법원 2021다22222 판결", page=1, context=body,
    )
    verdicts = [
        {"citation_id": "cit_0", "status": "NOT_FOUND", "levels": {}, "official_record": {"case_number": "2019다99999"}},
        {"citation_id": "cit_1", "status": "NOT_FOUND", "levels": {}, "official_record": None},
        {"citation_id": "cit_2", "status": "NOT_FOUND", "levels": {}, "official_record": None},
    ]

    gemini_sent = []
    anthropic_sent = []

    class _Provider(LLMProvider):
        available = True

        def __init__(self, name: str):
            self.name = name
            super().__init__(ProviderConfig(name=name, enabled=True, model=f"{name}-model", kind="cloud"))

        async def generate(self, request: LLMRequest) -> LLMResponse:
            payload = json.loads(request.user)["items"]
            if self.name == "gemini":
                gemini_sent.append((request, payload))
                if len(payload) > 1:
                    return LLMResponse(
                        False,
                        provider="gemini",
                        model="gemini-model",
                        input_tokens=200,
                        output_tokens=4090,
                        thinking_tokens=4090,
                        error="EMPTY_RESPONSE: 본문 없는 응답(finishReason=MAX_TOKENS, thinking 4090 tokens, 한도 4096)",
                    )
                return LLMResponse(
                    True,
                    provider="gemini",
                    model="gemini-model",
                    input_tokens=150,
                    output_tokens=100,
                    text=json.dumps(
                        {
                            "overall_summary": "단건 복구 완료",
                            "rows": [
                                {
                                    "item_id": payload[0]["item_id"],
                                    "claim_text": "합성 주장 요약",
                                    "validity_verdict": "판단 불가",
                                    "legal_reasoning": "개별 검토 결과",
                                    "recommended_check": "원문 확인",
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                )
            anthropic_sent.append((request, payload))
            return LLMResponse(
                True,
                provider="anthropic",
                model="anthropic-model",
                input_tokens=200,
                output_tokens=120,
                text=json.dumps(
                    {
                        "overall_summary": "일괄 완료",
                        "rows": [
                            {
                                "item_id": it["item_id"],
                                "claim_text": "합성 주장 요약",
                                "validity_verdict": "판단 불가",
                                "legal_reasoning": "일괄 검토 결과",
                                "recommended_check": "원문 확인",
                            }
                            for it in payload
                        ],
                    },
                    ensure_ascii=False,
                ),
            )

    _setup_env(monkeypatch)
    try:
        settings = replace(
            get_settings(),
            pricing={
                "gemini-model": {"input": 1.0, "output": 5.0},
                "anthropic-model": {"input": 1.0, "output": 5.0},
            },
        )
        ledger = _ledger(tmp_path, "arg_split.db")
        router = LLMRouter(
            {"anthropic": _Provider("anthropic"), "gemini": _Provider("gemini")},
            settings=settings,
            ledger=ledger,
            run_id="tk190-arg-split",
        )
        arg_res = asyncio.run(
            verify_argument_validity(
                doc,
                [c_confirmed, c1, c2],
                verdicts,
                [],
                router=router,
                external_ai_policy=ExternalAIPolicy.MASKED,
                mask=renderer,
            )
        )
        # anthropic: 1 batch call; gemini: 1 batch (4096) + 1 max-tokens retry (8192) + 2 single-item retries
        assert len(anthropic_sent) == 1
        assert len(gemini_sent) == 4
        single_reqs = [req for req, items in gemini_sent if len(items) == 1]
        assert len(single_reqs) == 2
        from packages.llm_router.privacy import inspect_request

        assert all(has_token_attestation(req) for req, _ in gemini_sent)
        assert all(valid_token_attestation(req, original_system=_OPINION_SYSTEM) for req in single_reqs)
        assert all(inspect_request(req, _original_system=_OPINION_SYSTEM)["status"] == "PASSED" for req in single_reqs)
        assert sorted(items[0]["item_id"] for _, items in gemini_sent if len(items) == 1) == [2, 3]
        assert [row.item_id for row in arg_res.rows] == [1, 2, 3]
        assert arg_res.rows[0].ai_opinions == []
        assert all(sorted(op["provider"] for op in row.ai_opinions) == ["anthropic", "gemini"] for row in arg_res.rows[1:])
        assert ledger.account("run:tk190-arg-split")["reserved"] == Decimal(0)
    finally:
        reset_settings()

