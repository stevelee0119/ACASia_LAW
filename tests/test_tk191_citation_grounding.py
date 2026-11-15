"""TK-191: 정상 인용 근거 확인 미완료 해소(구간 표지 연결·유한 재확인·3축 진단 분리). 합성 판결만 사용한다."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.common.enums import CitationType, ExternalAIPolicy, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.evidence_pack import (
    build_evidence_pack,
    is_display_tag,
    quote_in_one_segment,
    render_sections,
    segment_tag,
    validate_quotes_by_stage,
)
from packages.llm_router.providers import LLMProvider, LLMResponse
from packages.llm_router.router import LLMRouter
from packages.pii_engine import PIIEngine, PseudonymStore
from packages.source_adapters.registry import SourceRegistry
from packages.verification_engine.pipeline import (
    DocumentResult,
    ProjectContext,
    VerificationPipeline,
)


RULE_A = "매수인이 약정 기한까지 잔금을 지급하지 아니하면 계약을 해제할 수 있다."
RULE_B = "운송인은 불가항력적 천재지변이 입증되지 않는 한 인도 지연 책임을 진다."
RULE_C = "보증인의 책임 범위는 주채무의 원본과 이자 및 지연손해금에 한정된다."
EXCEPTION_B = "다만 송하인이 화물의 성질을 고지하지 않은 경우에는 면책된다."
DISSENT_C = "보증계약의 문언이 불명확한 경우에는 보증인에게 유리하게 제한 해석하여야 한다."


def _synthetic_mixed_judgment(filler_repeat: int = 12) -> str:
    filler = "사건 기록상 당사자들의 주장과 증거관계를 순서대로 살핀다. "
    return (
        "【주문】 상고를 기각한다.\n"
        f"【이유】 1. {RULE_A}\n"
        + filler * filler_repeat
        + f"\n2. {RULE_B} {EXCEPTION_B}\n"
        + filler * filler_repeat
        + f"\n3. 대법관 가의 반대의견은 다음과 같다. {DISSENT_C}\n"
        "【결론】 원심판결에는 법리오해의 잘못이 없다."
    )


def _synthetic_unanimous_judgment() -> str:
    return f"【주문】 항소를 기각한다. 【이유】 {RULE_C} 따라서 청구는 이유 있다."


def _verdict_json(status: str, quotes, rationale: str = "법리 대조 결과") -> str:
    return json.dumps(
        {
            "status": status,
            "confidence": 0.9,
            "rationale": rationale,
            "evidence_quotes": list(quotes),
            "contradicts": status in {"CONTRADICTED", "DISTORTED"},
        },
        ensure_ascii=False,
    )


class _QueuedProvider(LLMProvider):
    """요청 순서대로 응답을 돌려주는 합성 Provider(PII·예산·스키마 게이트를 실제로 통과한다)."""

    def __init__(self, name: str, model: str, handler):
        cfg = SimpleNamespace(name=name, kind="cloud", model=model, enabled=True, timeout_seconds=10)
        super().__init__(cfg)
        self.name = name
        self._handler = handler
        self.calls = []

    @property
    def available(self) -> bool:
        return True

    async def generate(self, request) -> LLMResponse:
        self.calls.append(request)
        res = self._handler(len(self.calls), request)
        if isinstance(res, LLMResponse):
            return res
        return LLMResponse(True, text=res, provider=self.name, model=self.config.model, input_tokens=100, output_tokens=80)


def _build_router(tmp_path: Path, providers: dict, *, cross_check: str = "all") -> LLMRouter:
    from dataclasses import replace
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from packages.common.config import get_settings
    from packages.llm_router.budget import BudgetLedger

    base = get_settings()
    pricing = dict(base.pricing)
    for p in providers.values():
        pricing[f"{p.name}:{p.config.model}"] = {"input_per_1k": "0.001", "output_per_1k": "0.002"}
    settings = replace(
        base,
        providers={name: p.config for name, p in providers.items()},
        llm_cross_check=cross_check,
        llm_efficient_routing=False,
        korean_law_review_profile=False,
        pricing=pricing,
    )
    engine = create_engine(f"sqlite:///{tmp_path / 'budget.sqlite'}", connect_args={"check_same_thread": False})
    ledger = BudgetLedger(factory=sessionmaker(bind=engine, expire_on_commit=False))
    return LLMRouter(providers=providers, settings=settings, ledger=ledger, run_id=f"tk191_{tmp_path.name}")


def _run_pipeline(
    tmp_path: Path,
    *,
    full_text: str,
    quoted_text: str,
    case_number: str,
    providers: dict,
    policy: ExternalAIPolicy = ExternalAIPolicy.MASKED,
):
    router = _build_router(tmp_path, providers)
    citation = Citation(
        citation_id="CIT_TK191",
        raw_text=f"대법원 2099. 5. 1. 선고 {case_number} 판결",
        type=CitationType.CASE,
        case_number=case_number,
        quoted_text=quoted_text,
        context=f"{case_number} 판결은 '{quoted_text}'라는 법리를 설시하였다.",
        span=(0, 12),
    )
    pipeline = VerificationPipeline(registry=SourceRegistry(), router=router)
    result = DocumentResult("doc_tk191", "synthetic.docx")
    result.engine_data["legal_verdicts"] = [
        {
            "citation_id": citation.citation_id,
            "levels": {"level4": "PENDING_LLM"},
            "official_record": {"case_number": case_number, "full_text": full_text},
        }
    ]
    pii = PIIEngine(PseudonymStore("tk191", root=tmp_path))
    pipeline._semantic_review(result, [citation], ProjectContext("tk191", external_ai_policy=policy), pii)
    return router, result.engine_data["semantic_reviews"][0], result


# --- 1. 구간 표지 및 비인용 태그 판정 ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "tag_text",
    [
        "[구간 S0 · 의견: MAJORITY · 원문 0~240자]",
        "[구간 S1 | 의견: DISSENT]",
        "[구간 S2 · 의견: CONCURRING, MAJORITY · 원문 1200~1800자] 일부 문장",
        "원문 문장 …(공식 원문 일부 생략)… 다음 문장",
        "(공식 원문 일부 생략)",
    ],
)
def test_display_tags_and_gap_markers_are_strictly_rejected(tag_text):
    segments = [RULE_A, RULE_B, RULE_C]
    assert is_display_tag(tag_text) is True
    assert quote_in_one_segment(tag_text, segments) is False
    out = validate_quotes_by_stage(
        [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [tag_text]}}],
        segments,
    )
    assert out["grounded"] is False
    assert out["rejected_quotes"][0]["reason"] == "DISPLAY_TAG_FORBIDDEN"


def test_render_sections_binds_every_segment_id_and_opinion_without_polluting_opinion_sections(tmp_path):
    mixed = _synthetic_mixed_judgment(filler_repeat=4)
    pack = build_evidence_pack(mixed, quotes=[RULE_A, EXCEPTION_B])
    rendered = render_sections(pack["segments"])
    for seg in pack["segments"]:
        expected_tag = segment_tag(
            seg["segment_id"],
            seg["opinion_kinds"],
            start=seg["original_start"],
            end=seg["original_end"],
        )
        assert expected_tag in rendered

    providers = {
        "anthropic": _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_C])),
        "openai": _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_C])),
        "gemini": _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_C])),
    }
    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=_synthetic_unanimous_judgment(),
        quoted_text=RULE_C,
        case_number="2099다101",
        providers=providers,
    )
    sent_payload = providers["anthropic"].calls[0].user
    assert "[구간 S0 · 의견: MAJORITY" in sent_payload
    assert review["quote_grounding"]["section_map"][0]["segment_id"] == "S0"
    assert review["quote_grounding"]["section_map"][0]["opinion_kinds"] == ["MAJORITY"]
    # 전원일치 다수의견에서도 기존 opinion_sections == [] 계약을 유지한다.
    assert json.loads(providers["anthropic"].calls[0].inspection_source._inspection_text())["official"]["opinion_sections"] == []


# --- 2. 부분 유효·다수/별개·미발견 분기 보존 및 보수적 합의 유지 ----------------------------------------------
def test_partial_valid_quotes_are_preserved_in_diagnostics_while_strict_grounded_stays_false():
    text = _synthetic_mixed_judgment(filler_repeat=3)
    pack = build_evidence_pack(text, quotes=[RULE_A, DISSENT_C])
    segments = [s["text"] for s in pack["segments"]]
    stages = [
        {"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [RULE_A, "원문에 없는 꾸민 문장"]}},
        {"used": True, "name": "critic", "verdict": {"status": "VERIFIED", "evidence_quotes": [RULE_B]}},
        {"used": True, "name": "grounder", "verdict": {"status": "VERIFIED", "evidence_quotes": [segment_tag("S0", ["MAJORITY"])]}},
    ]
    out = validate_quotes_by_stage(stages, segments, opinion_text=text, segments_meta=pack["segments"])
    assert out["grounded"] is False
    valid_texts = {q["quote"] for q in out["validated_quotes"]}
    assert RULE_A in valid_texts and RULE_B in valid_texts
    rejected_reasons = {r["reason"] for r in out["rejected_quotes"]}
    assert "NOT_FOUND_IN_EXCERPT" in rejected_reasons
    assert "DISPLAY_TAG_FORBIDDEN" in rejected_reasons


def test_cross_segment_splice_and_unsent_full_text_quote_remain_rejected():
    head = "제1원문 구간에 있는 유효한 판시 문장이다."
    tail = "제2원문 구간에 있는 또 다른 판시 문장이다."
    unsent_sentence = "발췌에서 생략된 중간 원문 문장이다."
    full_text = f"{head} {'가나다라 ' * 400} {unsent_sentence} {'마바사아 ' * 400} {tail}"
    segments = [head, tail]
    stages = [
        {"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [head + tail]}},
        {"used": True, "name": "critic", "verdict": {"status": "VERIFIED", "evidence_quotes": [unsent_sentence]}},
    ]
    out = validate_quotes_by_stage(stages, segments, opinion_text=full_text)
    assert out["grounded"] is False
    assert {r["reason"] for r in out["rejected_quotes"]} == {"NOT_FOUND_IN_EXCERPT", "UNSENT_FULL_TEXT_QUOTE"}


# --- 3. 유한 1회 인용 재확인 복구 및 한계 유지 ---------------------------------------------------------------
def test_recheck_recovers_missing_primary_quotes_and_preserves_initial_audit(tmp_path):
    primary = _QueuedProvider(
        "anthropic",
        "claude-stub",
        lambda n, req: _verdict_json("VERIFIED", [] if n == 1 else [RULE_A], rationale="요건 부합"),
    )
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A]))

    _, review, result = _run_pipeline(
        tmp_path,
        full_text=_synthetic_mixed_judgment(filler_repeat=3),
        quoted_text=RULE_A,
        case_number="2099다202",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert len(primary.calls) == 2 and len(critic.calls) == 1 and len(grounder.calls) == 1
    assert review["source_quotes_validated"] is True
    assert review["status"] == "SUPPORTED"
    assert review["quote_grounding"]["recheck_attempted"] is True
    assert review["quote_grounding"]["recheck_recovered"] is True
    assert review["legal_principle_consensus"]["status"] == "SUPPORTED"
    # 문구 일치·법리 합의와 달리 사건 적용 판단은 항상 검토 필요(보수적)로 분리한다.
    assert review["case_applicability"]["status"] == "REVIEW_NEEDED"
    assert review["case_applicability"]["advisory_only"] is True
    assert review["case_applicability"]["applies_to_case"] is None
    assert review["stages"][1]["initial_verdict"]["evidence_quotes"] == []
    assert len(result.engine_data["model_executions"]) == 4


def test_recheck_keeps_incomplete_models_honest_when_third_provider_failed(tmp_path):
    primary = _QueuedProvider(
        "anthropic",
        "claude-stub",
        lambda n, req: _verdict_json(
            "VERIFIED",
            ["[구간 S0 · 의견: MAJORITY · 원문 0~100자]"] if n == 1 else [RULE_B],
        ),
    )
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_B]))
    grounder = _QueuedProvider(
        "gemini",
        "gemini-stub",
        lambda n, req: LLMResponse(False, provider="gemini", model="gemini-stub", error="HTTP 503"),
    )

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=_synthetic_mixed_judgment(filler_repeat=3),
        quoted_text=RULE_B,
        case_number="2099다303",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert len(primary.calls) == 2
    assert review["source_quotes_validated"] is True
    assert review["quote_grounding"]["validated_quotes"][0]["quote"] == RULE_B
    assert review["consensus"]["incomplete_models"] is True
    assert review["legal_principle_consensus"]["incomplete_models"] is True
    assert review["legal_principle_consensus"]["status"] == "UNVERIFIED"
    assert review["status"] == "UNVERIFIED"
    assert review["case_applicability"]["incomplete_models"] is True


def test_recheck_is_strictly_bounded_to_one_attempt_when_model_still_lacks_valid_quotes(tmp_path):
    primary = _QueuedProvider(
        "anthropic",
        "claude-stub",
        lambda n, req: _verdict_json("VERIFIED", ["판결문에 없는 추정 문장"]),
    )
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_C]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_C]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=_synthetic_unanimous_judgment(),
        quoted_text=RULE_C,
        case_number="2099다404",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert len(primary.calls) == 2
    assert review["quote_grounding"]["recheck_attempted"] is True
    assert review["quote_grounding"]["recheck_recovered"] is False
    assert review["source_quotes_validated"] is False
    assert review["status"] == "UNVERIFIED"
    assert review["evidence_quotes"] == []
    assert any(q["quote"] == RULE_C for q in review["quote_grounding"]["validated_quotes"])
    assert any(r["reason"] == "NOT_FOUND_IN_EXCERPT" for r in review["quote_grounding"]["rejected_quotes"])


# --- 4. 대조군: 부정·예외 반박, 반대의견만 지지, 다른 판결 인용, PII 비노출 ------------------------------
def test_negation_and_exception_contradiction_separates_applicability_and_grounds_exception(tmp_path):
    text = _synthetic_mixed_judgment(filler_repeat=2)
    providers = {
        "anthropic": _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("CONTRADICTED", [EXCEPTION_B])),
        "openai": _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("CONTRADICTED", [EXCEPTION_B])),
        "gemini": _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("CONTRADICTED", [EXCEPTION_B])),
    }
    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=RULE_B,
        case_number="2099다505",
        providers=providers,
    )
    assert review["source_quotes_validated"] is True
    assert review["status"] == "CONTRADICTED"
    assert review["legal_principle_consensus"]["status"] == "CONTRADICTED"
    assert review["case_applicability"]["status"] == "CONTRADICTED"
    assert review["quote_grounding"]["validated_quotes"][0]["quote"] == EXCEPTION_B


def test_minority_opinion_only_supporting_verdict_never_triggers_recheck_and_stays_rejected(tmp_path):
    text = _synthetic_mixed_judgment(filler_repeat=2)
    primary = _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", [DISSENT_C]))
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [DISSENT_C]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [DISSENT_C]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=DISSENT_C,
        case_number="2099다606",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert len(primary.calls) == 1
    assert review["minority_opinion_evidence"] is True
    assert review["source_quotes_validated"] is False
    assert review["quote_grounding"]["recheck_attempted"] is False
    assert review["evidence_quotes"] == []


def test_pii_is_masked_before_rendering_sections_and_never_leaks_into_grounding_diagnostics(tmp_path):
    raw_name = "홍길동"
    raw_phone = "010-9876-5432"
    text = f"【이유】 당사자 {raw_name}(연락처 {raw_phone}) 사건에서 {RULE_A}"
    providers = {
        "anthropic": _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A])),
        "openai": _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A])),
        "gemini": _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A])),
    }
    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=RULE_A,
        case_number="2099다707",
        providers=providers,
        policy=ExternalAIPolicy.MASKED,
    )
    sent_user = providers["anthropic"].calls[0].user
    assert raw_phone not in sent_user
    serialized = json.dumps(review["quote_grounding"], ensure_ascii=False)
    assert raw_phone not in serialized
    assert review["source_quotes_validated"] is True
