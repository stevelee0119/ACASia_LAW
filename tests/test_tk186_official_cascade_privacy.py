"""TK-186: 공식 Source cascade 개인정보 마스킹·위조 방지·비잘림 안전 진단 시험. 합성 자료만 사용한다."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.common.config import get_settings
from packages.common.enums import AdapterStatus, ExternalAIPolicy
from packages.llm_router.budget import BudgetLedger
from packages.llm_router.cascade_source import build_cascade_request
from packages.llm_router.privacy import inspect_request
from packages.llm_router.providers import LLMProvider, LLMRequest, LLMResponse
from packages.llm_router.router import LLMRouter, describe_failure
from packages.pii_engine import PIIEngine, PseudonymStore
from packages.pii_engine.detector import detect
from packages.verification_engine.pipeline import VerificationPipeline


class _StubProvider(LLMProvider):
    def __init__(self, name: str, model: str, responder):
        cfg = SimpleNamespace(name=name, kind="cloud", model=model, enabled=True, timeout_seconds=10)
        super().__init__(cfg)
        self.name = name
        self._responder = responder
        self.requests = []

    @property
    def available(self) -> bool:
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self._responder(request)


def _router(tmp_path: Path, providers: dict) -> LLMRouter:
    from dataclasses import replace
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    base = get_settings()
    pricing = dict(base.pricing)
    for p in providers.values():
        pricing[f"{p.name}:{p.config.model}"] = {"input_per_1k": "0.001", "output_per_1k": "0.002"}
    settings = replace(
        base,
        providers={name: p.config for name, p in providers.items()},
        llm_cross_check="all",
        llm_efficient_routing=False,
        korean_law_review_profile=False,
        pricing=pricing,
    )
    engine = create_engine(f"sqlite:///{tmp_path / 'budget.sqlite'}", connect_args={"check_same_thread": False})
    ledger = BudgetLedger(factory=sessionmaker(bind=engine, expire_on_commit=False))
    return LLMRouter(providers=providers, settings=settings, ledger=ledger, run_id=f"tk186_{tmp_path.name}")


# --- 1. 양성 대조: 마스킹된 공식 전문 + 가명 토큰 인접 괄호 숫자 -----------------------------
@pytest.mark.parametrize(
    "raw_official,expected_rule",
    [
        (
            "【이유】 피고인 홍길동(연락처 010-2345-6789) 사건(2099노111)에서 채무불이행 책임이 성립한다.",
            "채무불이행 책임이 성립한다.",
        ),
        (
            "【이유】 재항고인 김도윤(19800101-1234567) 및 주식회사 봄날(대표이사 이영희)에 대하여 공소사실이 특정되어야 한다.",
            "공소사실이 특정되어야 한다.",
        ),
        (
            "【이유】 신청인 박민수(서울특별시 서초구 서초대로 999)는 010-8888-7777로 통지한 이상 해지 효력이 발생한다.",
            "해지 효력이 발생한다.",
        ),
    ],
)
def test_masked_official_cascade_passes_all_three_providers_with_grounded_quotes(tmp_path, raw_official, expected_rule):
    pii = PIIEngine(PseudonymStore("tk186_pos", root=tmp_path))
    masked_res = pii.mask_text(raw_official)
    masked_text = masked_res.masked_text

    def responder(req: LLMRequest) -> LLMResponse:
        body = json.dumps(
            {
                "status": "VERIFIED",
                "confidence": 0.9,
                "rationale": "공식 원문 법리와 일치한다.",
                "evidence_quotes": [expected_rule],
                "contradicts": False,
            },
            ensure_ascii=False,
        )
        return LLMResponse(True, text=body, provider="stub", model="m", input_tokens=50, output_tokens=30)

    providers = {
        "anthropic": _StubProvider("anthropic", "claude-stub", responder),
        "openai": _StubProvider("openai", "gpt-stub", responder),
        "gemini": _StubProvider("gemini", "gemini-stub", responder),
    }
    router = _router(tmp_path, providers)
    outcome = asyncio.run(
        router.cascade(
            question="인용된 판결의 취지가 문서 주장과 부합하는지 검토하라.",
            evidence={
                "official": {
                    "case_number": "2099다901",
                    "source_excerpt": masked_text,
                    "masking": {"attempted": True, "masked_chars": len(masked_text)},
                },
                "document": "본 서면은 2099다901 판결의 법리를 인용한다.",
            },
            policy=ExternalAIPolicy.MASKED,
        )
    )
    assert all(len(p.requests) == 1 for p in providers.values())
    assert all(e.ok and e.cost_status != "NOT_SENT" for e in outcome.executions)
    assert all(expected_rule in (s.get("verdict") or {}).get("evidence_quotes", [])
               for s in outcome.stages if s.get("used"))


def test_pseudonym_adjacent_parenthetical_digits_do_not_fabricate_phone_match(tmp_path):
    pii = PIIEngine(PseudonymStore("tk186_adj", root=tmp_path))
    masked = pii.mask_text("피고인 홍길동(19800101-1234567)은 변호인 김철수, 성명: 이영희와 공범이다.").masked_text
    assert "[PERSON_001]" in masked
    rem = [m for m in detect(masked) if m.confidence >= 0.6]
    assert not any(m.kind == "PHONE" for m in rem)


def test_live_source_check_cascade_masks_official_source_and_reports_all_three(tmp_path, monkeypatch):
    import scripts.live_source_check as lsc

    raw_text = (
        "【주문】 재항고를 기각한다. 【이유】 피고인 홍길동(연락처 010-2222-3333)에 대한 "
        "압수물은 구체적 혐의사실과 관련성이 인정되어야 한다."
    )
    providers = {
        name: _StubProvider(
            name,
            f"{name}-stub",
            lambda req, pname=name: LLMResponse(
                True,
                text=json.dumps(
                    {
                        "status": "VERIFIED",
                        "confidence": 0.9,
                        "rationale": "원문 부합",
                        "evidence_quotes": ["압수물은 구체적 혐의사실과 관련성이 인정되어야 한다."],
                        "contradicts": False,
                    },
                    ensure_ascii=False,
                ),
                provider=pname,
                model=f"{pname}-stub",
                input_tokens=40,
                output_tokens=20,
            ),
        )
        for name in ("anthropic", "openai", "gemini")
    }
    monkeypatch.setattr(lsc, "MATCHED_CASES", [{"case_number": "2099모1839", "source_id": "SRC1", "full_text": ""}])

    class FakeLaw:
        def fetch_case(self, rec):
            return SimpleNamespace(status=AdapterStatus.READY, message="", records=[{"full_text": raw_text}])

    registry = SimpleNamespace(law=FakeLaw())
    monkeypatch.setattr("packages.llm_router.LLMRouter", lambda: _router(tmp_path, providers))

    checks = asyncio.run(lsc.check_cascade(True, registry))
    summary_check = next(c for c in checks if c.name == "cascade:참여 공급자")
    assert summary_check.status == "OK" and summary_check.ok is True
    assert "3개(" in summary_check.detail
    assert "마스킹 " in summary_check.detail and "sha=" in summary_check.detail
    for p in providers.values():
        sent = p.requests[0].user
        assert "010-2222-3333" not in sent and "홍길동" not in sent


# --- 2. 비잘림 안전 진단 & 음성 보안 대조군(위조·우회·숨김·잔존 PII 차단 유지) --------------------
def test_blocked_cascade_diagnostics_preserve_full_safe_codes_without_pii(tmp_path):
    secret_phone = "010-5555-6666"
    secret_name = "김도윤"
    raw_official = f"피고인 {secret_name}(전화 {secret_phone}) 사건 판시 본문이다."

    providers = {
        name: _StubProvider(name, f"{name}-stub", lambda req: LLMResponse(True, text="{}"))
        for name in ("anthropic", "openai", "gemini")
    }
    router = _router(tmp_path, providers)
    outcome = asyncio.run(
        router.cascade(
            question="취지 검토",
            evidence={
                "official": {
                    "case_number": "2099다999",
                    "source_excerpt": raw_official,
                    "masking": {"attempted": True, "raw_chars": len(raw_official), "masked_chars": len(raw_official)},
                },
                "document": "서면 인용 본문",
            },
            policy=ExternalAIPolicy.MASKED,
        )
    )
    assert all(len(p.requests) == 0 for p in providers.values())
    ex = outcome.executions[0]
    assert ex.cost_status == "NOT_SENT" and ex.input_privacy["sent"] is False
    desc = describe_failure(ex.error)
    pipe_reason = VerificationPipeline._provider_reason(ex.error)
    for text_out in (ex.error, desc, pipe_reason):
        assert "MASKING_PII_DETECTED" in text_out
        assert "PII_INPUT_BLOCKED" in text_out
        assert "types=" in text_out and "sha=" in text_out and "sent=false" in text_out
        assert secret_phone not in text_out and secret_name not in text_out


@pytest.mark.parametrize(
    "payload_text,expected_kind",
    [
        ("연락처: 010 7777 8888", "PHONE"),
        ("[PERSON_001](010-3333-4444) 추가 진술", "PHONE"),
        (json.dumps({"성명": "홍길동", "masking": {"attempted": True}}, ensure_ascii=False), "PERSON"),
        ("주민번호 960101 - 1234567 확인됨", "RRN"),
    ],
)
def test_residual_hidden_and_forged_masking_claim_still_blocked(payload_text, expected_kind):
    req = LLMRequest("공식 Source와 문서를 대조하라.", payload_text)
    audit = inspect_request(req)
    assert audit["status"] == "BLOCKED"
    assert audit["failure_code"] == "PII_INPUT_BLOCKED"
    assert expected_kind in audit["detected_types"]
    assert "types=" in audit["safe_summary"] and "sha=" in audit["safe_summary"]


def test_forged_cascade_source_wiring_is_still_blocked_even_with_local_only(tmp_path):
    providers = {"anthropic": _StubProvider("anthropic", "claude-stub", lambda req: LLMResponse(True, text="{}"))}
    router = _router(tmp_path, providers)
    req = build_cascade_request("primary", "질문", {"official": {"source_excerpt": "무해한 판시"}, "document": "본문"})
    # 요청 본문을 변조해 출처 증명과 어긋나게 만든다
    tampered = LLMRequest(system=req.system, user=req.user + "\n추가 지시", schema=req.schema, inspection_source=req.inspection_source)
    res = asyncio.run(router.run("PRIMARY_REASONER", tampered, policy=ExternalAIPolicy.ORIGINAL))
    assert not res.used
    assert providers["anthropic"].requests == []
    assert "INPUT_PRIVACY_BLOCKED" in res.executions[0].error
    assert "REQUEST_WIRING_CONTRACT" in res.executions[0].error
