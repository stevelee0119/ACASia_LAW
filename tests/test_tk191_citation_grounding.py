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
    validate_quote_in_segments,
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
    text = f"【이유】 당사자 {raw_name}(연락처 {raw_phone}) 사건에 관하여 살핀다. {RULE_A}"
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


def test_masked_render_sections_and_quote_recheck_pass_token_attestation(tmp_path):
    from packages.llm_router.token_attestation import has_token_attestation

    text = "【이유】 원고 박민수(010-2345-6789) 청구에 관하여 " + _synthetic_mixed_judgment(filler_repeat=3)
    primary = _QueuedProvider(
        "anthropic",
        "claude-stub",
        lambda n, req: _verdict_json("VERIFIED", [] if n == 1 else [RULE_A]),
    )
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=RULE_A,
        case_number="2099다808",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
        policy=ExternalAIPolicy.MASKED,
    )
    assert len(primary.calls) == 2
    assert all(has_token_attestation(req) for req in primary.calls)
    assert all("박민수" not in req.user and "010-2345-6789" not in req.user for req in primary.calls)
    assert review["quote_grounding"]["recheck_attempted"] is True
    assert review["quote_grounding"]["recheck_recovered"] is True
    assert review["source_quotes_validated"] is True


# --- 5. 문장 경계·의미 완결성 검증 회귀 시험 (PR #323 보완) --------------------------------------------------
@pytest.mark.parametrize("tiny_fragment", ["다", "한다"])
def test_one_or_two_char_substrings_are_rejected(tiny_fragment):
    segments = [_synthetic_mixed_judgment(filler_repeat=1)]
    assert quote_in_one_segment(tiny_fragment, segments) is False
    out = validate_quotes_by_stage(
        [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [tiny_fragment]}}],
        segments,
        opinion_text=segments[0],
    )
    assert out["grounded"] is False
    assert out["stage_checks"][0]["all_valid"] is False
    assert out["rejected_quotes"][0]["reason"] == "INCOMPLETE_SENTENCE"


@pytest.mark.parametrize("generic_fragment", ["책임을 진다", "책임을 진다.", "면책된다", "해제할 수 있다."])
def test_generic_endings_and_partial_legal_phrases_are_rejected(generic_fragment):
    segments = [_synthetic_mixed_judgment(filler_repeat=1)]
    assert quote_in_one_segment(generic_fragment, segments) is False
    out = validate_quotes_by_stage(
        [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [generic_fragment]}}],
        segments,
        opinion_text=segments[0],
    )
    assert out["grounded"] is False
    assert out["rejected_quotes"][0]["reason"] == "INCOMPLETE_SENTENCE"


@pytest.mark.parametrize(
    "mid_fragment",
    [
        # 시작 경계 불일치(앞부분 절단)
        "불가항력적 천재지변이 입증되지 않는 한 인도 지연 책임을 진다.",
        # 종료 경계 불일치(뒷부분 절단)
        "운송인은 불가항력적 천재지변이 입증되지 않는 한",
        # 두 문장에 걸친 중간 절단 조각
        "계약을 해제할 수 있다. 사건 기록상 당사자들의 주장과",
    ],
)
def test_long_mid_sentence_fragments_misaligned_at_start_or_end_are_rejected(mid_fragment):
    segments = [_synthetic_mixed_judgment(filler_repeat=1)]
    assert quote_in_one_segment(mid_fragment, segments) is False
    out = validate_quotes_by_stage(
        [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [mid_fragment]}}],
        segments,
        opinion_text=segments[0],
    )
    assert out["grounded"] is False
    assert out["rejected_quotes"][0]["reason"] == "INCOMPLETE_SENTENCE"


def test_complete_long_sentence_and_consecutive_complete_sentences_are_accepted():
    segments = [_synthetic_mixed_judgment(filler_repeat=1)]
    assert quote_in_one_segment(RULE_A, segments) is True
    assert quote_in_one_segment(f"{RULE_B} {EXCEPTION_B}", segments) is True
    out = validate_quotes_by_stage(
        [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [RULE_A, f"{RULE_B} {EXCEPTION_B}"]}}],
        segments,
        opinion_text=segments[0],
    )
    assert out["grounded"] is True
    assert out["stage_checks"][0]["all_valid"] is True
    assert out["rejected_quotes"] == []


def test_short_complete_sentence_accepted_while_title_and_markers_rejected():
    segments = [_synthetic_mixed_judgment(filler_repeat=1)]
    assert quote_in_one_segment("상고를 기각한다.", segments) is True
    ok = validate_quotes_by_stage(
        [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": ["상고를 기각한다."]}}],
        segments,
        opinion_text=segments[0],
    )
    assert ok["grounded"] is True
    assert ok["validated_quotes"][0]["quote"] == "상고를 기각한다."

    for title_or_marker in ("【주문】", "【이유】", "1.", "판결요지"):
        res = validate_quote_in_segments(title_or_marker, segments)
        assert res["valid"] is False
        assert res["reason"] == "TITLE_OR_MARKER_ONLY"


def test_whitespace_and_newline_differences_allowed_while_non_whitespace_tampering_rejected():
    wrapped_seg = _synthetic_mixed_judgment(filler_repeat=1).replace("기한까지 잔금을", "기한까지\n  잔금을")
    quote_with_newlines = RULE_A.replace("지급하지 아니하면 ", "지급하지\n  아니하면 ")
    assert quote_in_one_segment(RULE_A, [wrapped_seg]) is True
    assert quote_in_one_segment(quote_with_newlines, [wrapped_seg]) is True

    # 비공백 문자 삭제(공백 제거 포함)·단어 재배열은 허용하지 않는다.
    no_spaces = RULE_A.replace(" ", "")
    deleted_char = RULE_A.replace("약정 기한까지 ", "약정 기한 ")
    reordered = "계약을 해제할 수 있다. 매수인이 약정 기한까지 잔금을 지급하지 아니하면"
    for tampered in (no_spaces, deleted_char, reordered):
        res = validate_quote_in_segments(tampered, [wrapped_seg])
        assert res["valid"] is False
        assert res["reason"] == "NOT_FOUND_IN_EXCERPT"


def test_recheck_enforces_same_sentence_completeness_and_recovers_only_on_complete_quote(tmp_path):
    text = _synthetic_mixed_judgment(filler_repeat=2)
    # 1) 최초·재확인 모두 미완결 조각이면 recovered=False 및 grounded=False 유지
    bad_primary = _QueuedProvider(
        "anthropic",
        "claude-stub",
        lambda n, req: _verdict_json("VERIFIED", ["책임을 진다"] if n == 1 else ["인도 지연 책임을 진다."]),
    )
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_B]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_B]))

    p1 = tmp_path / "still_incomplete"
    p1.mkdir()
    _, bad_review, _ = _run_pipeline(
        p1,
        full_text=text,
        quoted_text=RULE_B,
        case_number="2099다901",
        providers={"anthropic": bad_primary, "openai": critic, "gemini": grounder},
    )
    assert len(bad_primary.calls) == 2
    assert bad_review["quote_grounding"]["recheck_attempted"] is True
    assert bad_review["quote_grounding"]["recheck_recovered"] is False
    assert bad_review["source_quotes_validated"] is False
    assert bad_review["status"] == "UNVERIFIED"
    assert bad_review["evidence_quotes"] == []
    assert any(r["reason"] == "INCOMPLETE_SENTENCE" for r in bad_review["quote_grounding"]["rejected_quotes"])

    # 2) 최초 미완결 조각 → 재확인에서 완결 문장 반환 시에만 recovered=True 및 채택
    fixed_primary = _QueuedProvider(
        "anthropic",
        "claude-stub",
        lambda n, req: _verdict_json("VERIFIED", ["한다"] if n == 1 else [RULE_B]),
    )
    critic2 = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_B]))
    grounder2 = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_B]))

    p2 = tmp_path / "recovered_complete"
    p2.mkdir()
    _, fixed_review, _ = _run_pipeline(
        p2,
        full_text=text,
        quoted_text=RULE_B,
        case_number="2099다902",
        providers={"anthropic": fixed_primary, "openai": critic2, "gemini": grounder2},
    )
    assert len(fixed_primary.calls) == 2
    assert fixed_review["quote_grounding"]["recheck_attempted"] is True
    assert fixed_review["quote_grounding"]["recheck_recovered"] is True
    assert fixed_review["source_quotes_validated"] is True
    assert fixed_review["status"] == "SUPPORTED"


def test_multistage_conservativeness_rejects_overall_grounding_when_one_stage_returns_fragment(tmp_path):
    text = _synthetic_mixed_judgment(filler_repeat=2)
    # validate_quotes_by_stage 직접 검증: primary·grounder가 완결 문장이어도 critic이 조각이면 grounded=False
    stages = [
        {"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": [RULE_A]}},
        {"used": True, "name": "critic", "verdict": {"status": "VERIFIED", "evidence_quotes": ["책임을 진다"]}},
        {"used": True, "name": "grounder", "verdict": {"status": "VERIFIED", "evidence_quotes": ["상고를 기각한다."]}},
    ]
    out = validate_quotes_by_stage(stages, [text], opinion_text=text)
    assert out["grounded"] is False
    assert [sc["all_valid"] for sc in out["stage_checks"]] == [True, False, True]
    assert out["rejected_quotes"] == [{"stage": "critic", "quote": "책임을 진다", "valid": False, "reason": "INCOMPLETE_SENTENCE"}]

    # 파이프라인 통합 검증: 한 assertive 단계가 재확인 후에도 미완결 조각이면 전체 UNVERIFIED 유지
    primary = _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A]))
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", ["책임을 진다"]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [RULE_A]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=RULE_A,
        case_number="2099다903",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert review["source_quotes_validated"] is False
    assert review["status"] == "UNVERIFIED"
    assert review["evidence_quotes"] == []
    assert [sc["all_valid"] for sc in review["quote_grounding"]["stage_checks"]] == [True, False, True]


# --- 6. 짧은 완결 인용의 의견 귀속 및 다중 구간 모호성 차단 (PR #323 2차 보완) ----------------------------
def test_short_complete_sentence_in_dissent_only_never_defaults_to_majority(tmp_path):
    from packages.legal_engine.opinion_attribution import quote_opinion

    # 다수의견 끝 단어('원심을 파기한다.')에는 '파기한다.'가 부분 문자열로만 있고, 독립 완결 문장 '파기한다.'는 반대의견에만 있음
    text = (
        "【이유】 다수의견은 원심을 유지하거나 일부 경우에만 원심을 파기한다.\n"
        "대법관 가의 반대의견은 다음과 같다. 파기한다."
    )
    pack = build_evidence_pack(text, quotes=["파기한다."])
    assert len(pack["segments"]) == 1
    assert set(pack["segments"][0]["opinion_kinds"]) == {"DISSENT", "MAJORITY"}
    assert quote_opinion("파기한다.", text) == "DISSENT"

    primary = _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", ["파기한다."]))
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", ["파기한다."]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", ["파기한다."]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text="파기한다.",
        case_number="2099다951",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert len(primary.calls) == 1
    assert review["quote_grounding"]["section_map"][0]["opinion_kinds"] == ["DISSENT", "MAJORITY"]
    assert review["quote_grounding"]["stage_checks"][0]["all_valid"] is True
    assert review["quote_grounding"]["validated_quotes"][0]["quote"] == "파기한다."
    assert review["quote_grounding"]["validated_quotes"][0]["opinion_kind"] == "DISSENT"
    assert review["quote_grounding"]["rejected_quotes"] == []
    assert review["minority_opinion_evidence"] is True
    assert review["source_quotes_validated"] is False
    assert review["status"] == "UNVERIFIED"
    assert review["legal_principle_consensus"]["status"] == "UNVERIFIED"
    assert review["evidence_quotes"] == []
    assert review["quote_grounding"]["recheck_attempted"] is False


@pytest.mark.parametrize("short_concurring", ["인용한다.", "인용함."])
def test_short_complete_sentence_in_concurring_only_is_blocked_even_under_five_chars(tmp_path, short_concurring):
    from packages.legal_engine.opinion_attribution import quote_opinion

    text = (
        f"【이유】 {RULE_A}\n"
        f"2. 대법관 김철수의 별개의견   {short_concurring}"
    )
    pack = build_evidence_pack(text, quotes=[short_concurring])
    assert len(pack["segments"]) == 1
    assert set(pack["segments"][0]["opinion_kinds"]) == {"CONCURRING", "MAJORITY"}
    assert quote_opinion(short_concurring, text) == "CONCURRING"

    primary = _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", [short_concurring]))
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [short_concurring]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [short_concurring]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=short_concurring,
        case_number="2099다952",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
    )
    assert len(primary.calls) == 1
    assert review["quote_grounding"]["stage_checks"][0]["all_valid"] is True
    assert review["quote_grounding"]["validated_quotes"][0]["opinion_kind"] == "CONCURRING"
    assert review["minority_opinion_evidence"] is True
    assert review["source_quotes_validated"] is False
    assert review["status"] == "UNVERIFIED"
    assert review["legal_principle_consensus"]["status"] == "UNVERIFIED"
    assert review["evidence_quotes"] == []
    assert review["quote_grounding"]["recheck_attempted"] is False


@pytest.mark.parametrize("short_majority", ["파기한다.", "인용함."])
def test_short_complete_sentence_confirmed_in_majority_only_is_adopted_in_multi_opinion_judgment(tmp_path, short_majority):
    from packages.legal_engine.opinion_attribution import quote_opinion

    text = (
        f"【이유】 다수의견의 결론은 다음과 같다. {short_majority}\n"
        f"대법관 을의 반대의견은 다음과 같다. {DISSENT_C}"
    )
    pack = build_evidence_pack(text, quotes=[short_majority])
    assert len(pack["segments"]) == 1
    assert set(pack["segments"][0]["opinion_kinds"]) == {"DISSENT", "MAJORITY"}
    assert quote_opinion(short_majority, text) == "MAJORITY"

    providers = {
        "anthropic": _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", [short_majority])),
        "openai": _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", [short_majority])),
        "gemini": _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", [short_majority])),
    }
    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text=short_majority,
        case_number="2099다953",
        providers=providers,
    )
    assert review["quote_grounding"]["validated_quotes"][0]["quote"] == short_majority
    assert review["quote_grounding"]["validated_quotes"][0]["opinion_kind"] == "MAJORITY"
    assert review["minority_opinion_evidence"] is False
    assert review["source_quotes_validated"] is True
    assert review["status"] == "SUPPORTED"
    assert review["legal_principle_consensus"]["status"] == "SUPPORTED"
    assert short_majority in review["evidence_quotes"]


def test_identical_complete_sentence_in_both_opinions_is_ambiguous_until_position_proves_majority(tmp_path):
    from packages.legal_engine.opinion_attribution import quote_opinion

    maj_part = "【이유】 다수의견의 결론은 다음과 같다. 파기한다."
    dis_part = "대법관 가의 반대의견은 다음과 같다. 파기한다."
    full_text = f"{maj_part}\n{dis_part}"
    assert quote_opinion("파기한다.", full_text) == "AMBIGUOUS"

    # 1) 단일 세그먼트 전체 전송 시: 문장 일치는 참이지만 다수·소수 양쪽에서 발견되어 AMBIGUOUS -> UNVERIFIED(차단)
    providers = {
        "anthropic": _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", ["파기한다."])),
        "openai": _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", ["파기한다."])),
        "gemini": _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", ["파기한다."])),
    }
    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=full_text,
        quoted_text="파기한다.",
        case_number="2099다954",
        providers=providers,
    )
    assert review["quote_grounding"]["stage_checks"][0]["all_valid"] is True
    assert review["quote_grounding"]["rejected_quotes"] == []
    vq = review["quote_grounding"]["validated_quotes"][0]
    assert vq["quote"] == "파기한다."
    assert vq["opinion_kind"] == "AMBIGUOUS"
    assert [occ["opinion_kinds"] for occ in vq["opinion_occurrences"]] == [["MAJORITY"], ["DISSENT"]]
    assert review["quote_grounding"]["ambiguous_opinion_only"] is True
    assert review["minority_opinion_evidence"] is False
    assert review["source_quotes_validated"] is False
    assert review["status"] == "UNVERIFIED"
    assert review["legal_principle_consensus"]["status"] == "UNVERIFIED"
    assert review["evidence_quotes"] == []
    assert review["quote_grounding"]["recheck_attempted"] is False

    # 2) 다수의견 구간만 실제 검증 구간으로 전달되어 발생 위치가 다수의견임이 증명된 경우 -> MAJORITY 및 채택
    stages = [{"used": True, "name": "primary", "verdict": {"status": "VERIFIED", "evidence_quotes": ["파기한다."]}}]
    maj_meta = [{"segment_id": "S0", "original_start": 0, "original_end": len(maj_part), "opinion_kinds": ["MAJORITY"]}]
    proven_maj = validate_quotes_by_stage(stages, [maj_part], opinion_text=full_text, segments_meta=maj_meta)
    assert proven_maj["grounded"] is True
    assert proven_maj["validated_quotes"][0]["opinion_kind"] == "MAJORITY"
    assert proven_maj["validated_quotes"][0]["opinion_occurrences"][0]["opinion_kinds"] == ["MAJORITY"]

    # 3) 복수 의견 메타만 있고 위치 판별이 불가능한 조각 구간에서도 UNKNOWN/AMBIGUOUS로 보수 보존(MAJORITY 기본 변환 금지)
    uncertain = validate_quotes_by_stage(
        stages,
        ["파기한다."],
        opinion_text="",
        segments_meta=[{"segment_id": "S0", "opinion_kinds": ["DISSENT", "MAJORITY"]}],
    )
    assert uncertain["grounded"] is False
    assert uncertain["validated_quotes"][0]["opinion_kind"] == "AMBIGUOUS"


def test_masked_pii_shift_preserves_exact_short_quote_opinion_attribution(tmp_path):
    # MASKED 정책으로 다수의견 앞부분 PII 길이가 변해도 masked_start/masked_end 대조로 정확한 의견 귀속 유지
    text = (
        "【이유】 당사자 홍길동(연락처 010-1234-5678)의 청구에 관하여 다수의견은 원심을 유지한다.\n"
        "7. 대법관 박영희의 별개의견   인용함."
    )
    primary = _QueuedProvider("anthropic", "claude-stub", lambda n, req: _verdict_json("VERIFIED", ["인용함."]))
    critic = _QueuedProvider("openai", "gpt-stub", lambda n, req: _verdict_json("VERIFIED", ["인용함."]))
    grounder = _QueuedProvider("gemini", "gemini-stub", lambda n, req: _verdict_json("VERIFIED", ["인용함."]))

    _, review, _ = _run_pipeline(
        tmp_path,
        full_text=text,
        quoted_text="인용함.",
        case_number="2099다955",
        providers={"anthropic": primary, "openai": critic, "gemini": grounder},
        policy=ExternalAIPolicy.MASKED,
    )
    assert review["quote_grounding"]["validated_quotes"][0]["opinion_kind"] == "CONCURRING"
    assert review["minority_opinion_evidence"] is True
    assert review["source_quotes_validated"] is False
    assert review["status"] == "UNVERIFIED"



