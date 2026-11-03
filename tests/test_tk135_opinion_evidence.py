"""TK-135: 별개의견 귀속과 의미 검토 근거의 의견 구간. 판결 문장은 모두 합성이다(실제 판결·서면이 아니다)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from packages.common.enums import CitationType, EvidenceGrade, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.evidence_pack import build_evidence_pack
from packages.legal_engine.opinion_attribution import opinion_ranges, quote_opinion

MAJ = "임대인은 임차인이 지출한 필요비를 지체 없이 상환하여야 한다."
CON = "필요비 상환의무의 근거는 신의칙이 아니라 계약의 해석에서 찾아야 한다."
DIS = "임차인이 미리 알리지 않고 지출한 비용은 상환 대상이 아니라고 보아야 한다."
FULL = (f"【이유】 상고이유를 판단한다. 1. {MAJ} 그러므로 상고를 기각한다. "
        f"2. 대법관 갑의 별개의견은 다음과 같다. {CON} "
        f"3. 대법관 을의 반대의견은 다음과 같다. {DIS} "
        f"4. 다수의견에 대한 대법관 병의 보충의견은 다음과 같다. 다수의견의 논거를 보충한다.")


def citation(quoted, context=""):
    c = Citation.create(type=CitationType.CASE, raw_text="대법원 2099. 1. 1. 선고 2099다1 전원합의체 판결",
                        document_id="d1", quoted_text=quoted)
    c.context = context or f"대법원 2099다1 판결은 '{quoted}'라고 판시하였다."
    c.attributes["case_claim"] = c.context
    return c


# --- 의견 구간 위치 -----------------------------------------------------------------------------------------
def test_opinion_ranges_follow_markers_and_map_majority_supplementary_to_majority():
    kinds = [(k, FULL[s:e]) for s, e, k in opinion_ranges(FULL)]
    assert [k for k, _ in kinds] == ["MAJORITY", "CONCURRING", "DISSENT", "MAJORITY"]
    assert MAJ in kinds[0][1] and CON in kinds[1][1] and DIS in kinds[2][1]
    assert opinion_ranges("【이유】 " + MAJ) == [(0, len("【이유】 " + MAJ), "MAJORITY")]


def test_quote_opinion_classifies_each_section_and_ignores_unmarked_text():
    assert quote_opinion(MAJ, FULL) == "MAJORITY"
    assert quote_opinion(CON.replace(" ", ""), FULL) == "CONCURRING"
    assert quote_opinion(DIS, FULL) == "DISSENT"
    assert quote_opinion("다수의견의 논거를 보충한다", FULL) == "MAJORITY"
    assert quote_opinion(MAJ, "【이유】 " + MAJ) is None              # 표지 없는 판결은 판단하지 않는다


def test_evidence_pack_segments_carry_opinion_kinds():
    [seg] = build_evidence_pack(FULL, quotes=[DIS])["segments"]
    assert seg["opinion_kinds"] == ["CONCURRING", "DISSENT", "MAJORITY"]
    [plain] = build_evidence_pack("【이유】 " + MAJ)["segments"]
    assert plain["opinion_kinds"] == ["MAJORITY"]


# --- 직접 인용 귀속(검증기) -------------------------------------------------------------------------------
def test_verbatim_quote_from_concurring_opinion_is_suspicious_grade_b():
    from packages.legal_engine.verifier import LegalVerifier
    findings = LegalVerifier._opinion_findings(citation(CON), {"full_text": FULL})
    [mis] = [f for f in findings if f.confidence_features["verdict_label"] == "MISATTRIBUTED_OPINION"]
    assert mis.status == VerificationStatus.SUSPICIOUS and mis.evidence_grade == EvidenceGrade.B
    assert mis.confidence_features["closest"] == "CONCURRING" and "별개의견" in mis.title


def test_concurring_quote_labelled_as_concurring_in_the_document_is_not_flagged():
    from packages.legal_engine.verifier import LegalVerifier
    c = citation(CON, context=f"위 판결의 별개의견은 '{CON}'라고 하였다.")
    assert not [f for f in LegalVerifier._opinion_findings(c, {"full_text": FULL})
                if f.confidence_features["verdict_label"] == "MISATTRIBUTED_OPINION"]


def test_majority_and_dissent_quotes_keep_existing_results():
    from packages.legal_engine.verifier import LegalVerifier
    assert not [f for f in LegalVerifier._opinion_findings(citation(MAJ), {"full_text": FULL})
                if f.confidence_features["verdict_label"] == "MISATTRIBUTED_OPINION"]
    [mis] = [f for f in LegalVerifier._opinion_findings(citation(DIS), {"full_text": FULL})
             if f.confidence_features["verdict_label"] == "MISATTRIBUTED_OPINION"]
    assert mis.status == VerificationStatus.CONTRADICTED and mis.evidence_grade == EvidenceGrade.A


# --- 의미 검토(실제 진입점 _semantic_review) ---------------------------------------------------------------
def run_review(full_text, status, model_quotes, quoted=MAJ):
    from packages.llm_router.router import CascadeOutcome, ModelExecution
    from packages.pii_engine import PIIEngine, PseudonymStore
    from packages.source_adapters.registry import SourceRegistry
    from packages.verification_engine.pipeline import DocumentResult, ProjectContext, VerificationPipeline

    sent = {}

    class Router:
        async def cascade(self, **kwargs):
            sent.update(kwargs)
            return CascadeOutcome(VerificationStatus.VERIFIED, EvidenceGrade.A, "모델 의견",
                                  stages=[{"used": True, "verdict": {"status": status, "rationale": "모델 의견",
                                                                     "evidence_quotes": model_quotes}}],
                                  executions=[ModelExecution("PRIMARY_REASONER", "stub", "test", True)])

    c = Citation(citation_id="CIT_TK135", raw_text="대법원 2099다1 판결", type=CitationType.CASE,
                 case_number="2099다1", quoted_text=quoted,
                 context=f"대법원 2099다1 판결은 '{quoted}'고 판시하였다.", span=(0, 10))
    pipeline = VerificationPipeline(registry=SourceRegistry(), router=Router())
    result = DocumentResult("d", "sample")
    result.engine_data["legal_verdicts"] = [{"citation_id": c.citation_id, "levels": {"level4": "PENDING_LLM"},
                                             "official_record": {"full_text": full_text}}]
    with tempfile.TemporaryDirectory() as tmp:
        pipeline._semantic_review(result, [c], ProjectContext("tk135"),
                                  PIIEngine(PseudonymStore("tk135", root=Path(tmp))))
    return sent, result.engine_data["semantic_reviews"][0]


def test_supporting_verdict_grounded_only_in_dissent_is_not_adopted():
    sent, review = run_review(FULL, "VERIFIED", [DIS])
    assert review["source_quotes_validated"] is False and review["minority_opinion_evidence"] is True
    assert review["evidence_quotes"] == [] and "반대의견·별개의견" in review["reason"]
    official = sent["evidence"]["official"]
    assert {"segment_id": "S0", "opinion_kinds": ["CONCURRING", "DISSENT", "MAJORITY"]} in official["opinion_sections"]
    assert "판시가 아니므로" in sent["question"]


def test_supporting_verdict_with_a_majority_quote_is_adopted():
    _, review = run_review(FULL, "VERIFIED", [DIS, MAJ])
    assert review["source_quotes_validated"] is True and review["minority_opinion_evidence"] is False


def test_contradicting_verdict_may_cite_the_dissent():
    _, review = run_review(FULL, "CONTRADICTED", [DIS], quoted=DIS)
    assert review["source_quotes_validated"] is True and review["minority_opinion_evidence"] is False


def test_unanimous_judgment_is_unchanged():
    sent, review = run_review("【이유】 " + MAJ, "VERIFIED", [MAJ])
    assert review["source_quotes_validated"] is True and sent["evidence"]["official"]["opinion_sections"] == []
