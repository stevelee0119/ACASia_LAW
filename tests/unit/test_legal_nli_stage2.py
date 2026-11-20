"""Unit tests for sliding-window passage alignment and Stage 2 Legal NLI (P1 PR-09)."""
from __future__ import annotations

from packages.legal_engine.nli_verifier import (
    NLISignal,
    evaluate_citation_nli_stage2,
    sliding_window_passages,
)


def test_stage2_nli_detects_paraphrased_contradictions_with_located_span():
    cases = [
        (
            "채무불이행으로 인한 손해배상 청구권은 당사자 사이에 특별한 약정이 없는 한 10년의 소멸시효에 걸린다. 다만 상행위로 인한 채권은 5년이다.",
            "대법원은 손해배상 청구권의 소멸시효가 10년에 걸리지 않는다고 판시하였다.",
        ),
        (
            "행정청은 처분을 하기 전에 당사자에게 사전 통지를 하여야 한다. 예외 사유가 없으면 생략할 수 없다.",
            "법원은 행정청이 재량으로 사전 통지를 할 수 있다고 판시하였다.",
        ),
        (
            "임대인이 보증금을 반환할 의무는 임차인의 목적물 인도의무와 동시이행 관계에 있다.",
            "판례는 임대인의 보증금 반환 의무가 임차인의 인도의무와 동시이행 관계에 있지 않다고 보았다.",
        ),
    ]
    for official, claim in cases:
        res = evaluate_citation_nli_stage2(official, claim)
        assert res.located_passage is not None
        assert res.verdict == "CONTRADICTED"
        assert res.nli_signal is not None
        assert res.nli_signal.structural_reasons


def test_stage2_nli_controls_entailment_insufficient_and_never_auto_contradicts_without_structure():
    # 1. Missing official source -> INSUFFICIENT (fail-closed)
    missing = evaluate_citation_nli_stage2("", "대법원은 손해배상 책임을 인정하였다.")
    assert missing.verdict == "INSUFFICIENT"
    assert missing.located_passage is None

    # 2. Unrelated official source -> INSUFFICIENT
    unrelated = evaluate_citation_nli_stage2(
        "특허권 침해 금지 청구는 등록된 청구범위를 기준으로 판단한다.",
        "근로기준법상 해고 예고 수당 지급 요건이 충족되었다.",
    )
    assert unrelated.verdict == "INSUFFICIENT"

    # 3. Consistent paraphrase -> SUPPORTED
    aligned = evaluate_citation_nli_stage2(
        "불법행위로 인한 손해배상 청구권은 피해자가 손해 및 가해자를 안 날로부터 3년간 행사하지 아니하면 시효로 소멸한다.",
        "불법행위 손해배상 청구권은 피해자가 손해 및 가해자를 안 날로부터 3년간 행사하지 않으면 시효로 소멸한다.",
    )
    assert aligned.verdict == "SUPPORTED"
    assert aligned.located_passage is not None

    # 4. Neural NLI high contradiction WITHOUT independent structural inversion -> PENDING_REVIEW
    #    even if the external scorer supplies its own structural_reasons.
    def _opaque_contradict_scorer(premise: str, hypothesis: str) -> NLISignal:
        return NLISignal(
            label="CONTRADICTION",
            entail_prob=0.02,
            contradict_prob=0.95,
            neutral_prob=0.03,
            structural_reasons=["MODEL_CLAIMED_INVERSION"],
        )

    guarded = evaluate_citation_nli_stage2(
        "당사자는 계약 내용을 성실히 이행할 의무를 부담한다.",
        "당사자는 계약 내용을 성실히 이행할 의무를 부담한다.",
        nli_scorer=_opaque_contradict_scorer,
    )
    assert guarded.verdict == "PENDING_REVIEW"


def test_sliding_window_passages_locates_best_sentence_in_multi_sentence_judgment():
    doc = (
        "  원심은 이 사건 매매계약이 적법하게 체결되었다고 보았다. "
        "그러나 매도인이 기망행위를 한 사실이 인정되면 매수인은 계약을 취소할 수 있다. "
        "소송비용은 패소자의 부담으로 한다."
    )
    passages = sliding_window_passages(doc, "기망행위가 인정되면 매수인이 계약을 취소할 수 있다.", top_k=2)
    assert passages
    assert "기망행위" in passages[0].text
    assert doc[passages[0].start:passages[0].end] == passages[0].text

    res = evaluate_citation_nli_stage2(
        "  당사자는 계약 내용을 성실히 이행할 의무를 부담한다.",
        "당사자는 계약 내용을 성실히 이행할 의무를 부담한다.",
    )
    assert res.located_passage is not None
    assert "  당사자는 계약 내용을 성실히 이행할 의무를 부담한다."[res.located_passage.start:res.located_passage.end] == res.located_passage.text


def test_legal_verifier_verify_case_stage2_nli_shadow_and_assist(monkeypatch):
    from types import SimpleNamespace
    from packages.common.config import reset_settings
    from packages.common.enums import AdapterStatus, CitationType, VerificationStatus
    from packages.common.schemas import Citation
    from packages.legal_engine.verifier import LegalVerifier

    class _MockLawAdapter:
        def search_case(self, case_number, court=None):
            return SimpleNamespace(
                found=True,
                source="mock_db",
                status=AdapterStatus.READY,
                message="",
                error=None,
                source_record=None,
                source_url=None,
                meta={},
                records=[{
                    "case_number": case_number,
                    "date": "2022. 5. 10.",
                    "court": "대법원",
                    "full_text": "매수인은 기망행위를 이유로 매매계약을 취소할 수 있다. 다만 손해배상은 별도다.",
                    "holding": "매수인은 기망행위를 이유로 매매계약을 취소할 수 있다.",
                    "summary": "",
                }],
            )

    verifier = LegalVerifier(registry=SimpleNamespace(law=_MockLawAdapter()))
    # Paraphrased inverted quote: similar tokens (high ratio -> MODIFIED in Stage 1), inverted polarity ("할 수 없다")
    cit_inverted = Citation(
        citation_id="CIT_NLI_1",
        type=CitationType.CASE,
        raw_text="대법원 2022다10001 판결",
        canonical_case_number="2022다10001",
        quoted_text="기망행위 사유로 매수인은 그 계약을 취소할 수 없다.",
    )

    # 1) Shadow mode (default): records stage2_nli without changing level3
    monkeypatch.setenv("LV_LEGAL_NLI_MODE", "shadow")
    reset_settings()
    verdict_shadow = verifier.verify_case(cit_inverted)
    assert "stage2_nli" in verdict_shadow.review
    assert verdict_shadow.review["stage2_nli"]["verdict"] == "CONTRADICTED"
    assert not verdict_shadow.review.get("stage2_nli_assisted")

    # 2) Assist mode: ensures CONTRADICTED when full_text + structural inversion confirmed
    monkeypatch.setenv("LV_LEGAL_NLI_MODE", "assist")
    reset_settings()
    verdict_assist = verifier.verify_case(cit_inverted)
    assert verdict_assist.levels["level3"] == "CONTRADICTED"
    assert verdict_assist.status == VerificationStatus.CONTRADICTED
    assert verdict_assist.review["stage2_nli"]["verdict"] == "CONTRADICTED"

    # 3) Control in assist mode: non-inverted quote must NOT be escalated to CONTRADICTED
    cit_valid = Citation(
        citation_id="CIT_NLI_2",
        type=CitationType.CASE,
        raw_text="대법원 2022다10001 판결",
        canonical_case_number="2022다10001",
        quoted_text="매수인은 기망행위를 이유로 매매계약을 취소할 수 있다.",
    )
    verdict_ctrl = verifier.verify_case(cit_valid)
    assert verdict_ctrl.levels["level3"] != "CONTRADICTED"
    assert not verdict_ctrl.review.get("stage2_nli_assisted")
    reset_settings()

