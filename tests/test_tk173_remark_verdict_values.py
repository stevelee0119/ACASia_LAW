"""TK-173: 모델의 사실 지적을 결정론 판정의 기재값·계산값으로도 잇는다(0.20.0 온라인 D hwpx 관찰 O1).

온라인 실행에서 표 합계 판정(제목에는 차액만, 기재·계산 합계는 상세 값에만)과 같은 오류를 짚은 모델 지적이
'결정론 재계산으로 확인하지 못함'으로 따로 남았다. 지적 뒤의 풀이 문장('이는 … 모순일 뿐 …')도 확인하지 못한
문장으로 남았다. 금액·문장은 시험용 합성이다.
"""
from __future__ import annotations

import pytest

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, Finding, NormalizedDocument, Page
from packages.verification_engine.ai_document_detector import (_fact_category, _fact_remark_finding,
                                                               reconcile_model_fact_remarks, verdict_anchors)


def _doc():
    page = Page(page_number=1, blocks=[Block(block_id="b0", text="본문", page=1)])
    return NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0", pages=[page])


def remark(text):
    return _fact_remark_finding(_doc(), text, _fact_category(text) or "OTHER")


def total_verdict(status=VerificationStatus.CONTRADICTED):
    return Finding.create(type=FindingType.ARITHMETIC_MISMATCH, status=status, severity=Severity.HIGH,
                          evidence_grade=EvidenceGrade.A, title="합계가 세부 금액 합산값과 다르다 (차이 200,000원)",
                          detail="세부 2건 합산 4,500,000 / 문서 기재 4,700,000. 차액 200,000원.",
                          confidence_features={"rule_id": "claim_engine.calculation:ARITHMETIC_MISMATCH",
                                               "stated": "4700000", "computed": "4500000", "difference": "200000"},
                          document_id="d")


def date_verdict():
    return Finding.create(type=FindingType.ARITHMETIC_MISMATCH, status=VerificationStatus.CONTRADICTED, severity=Severity.HIGH,
                          evidence_grade=EvidenceGrade.A, title="기간 만료일이 계산과 다르다: 문서 2027. 8. 1. / 계산 2027. 2. 1.",
                          detail="차이 181일", confidence_features={"rule_id": "CALC.EXPIRY_DATE", "difference": 181,
                                                                 "stated": "4700000"}, document_id="d")


def run(findings):
    stats = {}
    out = reconcile_model_fact_remarks(findings, stats)
    return [f for f in out if f.type == FindingType.MODEL_FACT_REMARK], stats


def test_amount_verdict_anchors_include_recorded_stated_and_computed_values():
    assert verdict_anchors(total_verdict()) == {"A:200000", "A:4700000", "A:4500000"}


def test_non_amount_verdict_does_not_turn_its_numbers_into_amounts():
    assert not any(a.startswith("A:") for a in verdict_anchors(date_verdict()))


@pytest.mark.parametrize("values", ["4,700,000원과 4,500,000원", "470만 원과 450만 원", "금 4,700,000원과 금 4,500,000원"])
def test_remark_with_the_verdicts_recorded_totals_is_folded_into_the_verdict(values):
    verdict = total_verdict()
    left, stats = run([verdict, remark(f"[m] 표1 합계 {values}이 서로 다르다.")])
    assert not left and stats["confirmed"] == 1 and verdict.confidence_features["model_remarks"]


def test_back_reference_explanation_does_not_keep_the_remark_open():
    verdict = total_verdict()
    left, stats = run([verdict, remark("[m] 표1 항목 합(4,500,000원)과 기재 합계(4,700,000원)가 다르다. "
                                       "이는 문서 내부 모순일 뿐 작성 주체의 근거가 아니다.")])
    assert not left and stats == {"confirmed": 1, "partial": 0, "unconfirmed": 0}


def test_independent_contradiction_without_values_still_needs_a_person():
    verdict = total_verdict()
    left, stats = run([verdict, remark("[m] 표1 합계 4,700,000원과 4,500,000원이 다르다. 원고 성명도 서로 다르게 적혀 있다.")])
    [kept] = left
    assert stats["partial"] == 1 and "성명" in kept.confidence_features["unconfirmed_sentences"][0]


def test_back_reference_with_its_own_unmatched_value_still_needs_a_person():
    left, stats = run([total_verdict(), remark("[m] 표1 합계 4,700,000원과 4,500,000원이 다르다. 이는 3,000,000원과도 다르다.")])
    assert len(left) == 1 and stats["partial"] == 1


@pytest.mark.parametrize("status", [VerificationStatus.UNVERIFIED, VerificationStatus.SUSPICIOUS])
def test_only_contradicted_verdicts_confirm(status):
    left, stats = run([total_verdict(status), remark("[m] 표1 합계 4,700,000원과 4,500,000원이 서로 다르다.")])
    assert len(left) == 1 and stats["unconfirmed"] == 1


def test_hypothetical_remark_is_not_confirmed():
    left, stats = run([total_verdict(), remark("[m] 만약 표1 합계 4,700,000원과 4,500,000원이 서로 다르다면 오기일 수 있다.")])
    assert len(left) == 1 and stats["unconfirmed"] == 1


def test_date_verdict_numbers_do_not_confirm_an_amount_remark():
    left, stats = run([date_verdict(), remark("[m] 청구 금액 4,700,000원과 영수증 금액이 서로 다르다.")])
    assert len(left) == 1 and stats["unconfirmed"] == 1
