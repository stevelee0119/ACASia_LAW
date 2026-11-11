"""LV-05: 판시 취지 및 명제 왜곡 탐지 (CIT-MIS) 단위 및 통합 시험.

- 3건의 양성 시험:
  1. 전원합의체 변경 판례 인용 왜곡 (CHANGED_PRECEDENT)
  2. 파기환송 원심 판단 오인 (REVERSED_REMAND_CONFUSION)
  3. 반대의견 오인 및 원문 근거 인용문 검증 (MISATTRIBUTED_OPINION + grounded_evidence_quote)
- 3건의 대조 시험:
  4. 정상 현행 다수의견 인용 (정상)
  5. 문맥상 별개의견임을 명시한 인용 (정상)
  6. 판시사항 결론 방향과 일치하는 요약 (정상)
"""
from __future__ import annotations

import unittest
from packages.common.enums import CitationType, EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.opinion_attribution import (
    attribute_claim,
    detect_changed_precedent_distortion,
    detect_reversed_remand_confusion,
    direction_conflict,
    extract_grounded_evidence_quote,
)
from packages.legal_engine.verifier import LegalVerifier


class TestLV05HoldingDistortion(unittest.TestCase):
    def setUp(self):
        self.verifier = LegalVerifier()

    # 1. 양성 시험 1: 전원합의체 변경 판례 인용 왜곡
    def test_changed_precedent_distortion_positive(self):
        full_text = (
            "【이유】 상고이유를 판단한다. 종전에 이와 달리 근로계약 체결 시 사용자의 일방적 해고 권한을 유보한 약정은 "
            "그 효력을 인정할 수 없다고 판시한 대법원 2015다77777 판결 등은 이 판결의 견해에 배치되는 범위 내에서 "
            "이를 변경하기로 한다."
        )
        summary = "[다수의견] 일방적 해고 권한 유보 약정도 근로기준법상 정당한 이유가 있는 한 유효하다."
        claim = "사용자의 일방적 해고 권한을 유보한 약정은 그 효력을 인정할 수 없다고 판시하였다."

        result = detect_changed_precedent_distortion(
            claim=claim,
            full_text=full_text,
            summary=summary,
            cited_case_number="2015다77777",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "CHANGED_PRECEDENT")
        self.assertIn("2015다77777", result["old_cases"])
        self.assertIn("변경하기로 한다", result["grounded_evidence_quote"])

    # 2. 양성 시험 2: 파기환송 판결의 원심 판단 오인
    def test_reversed_remand_confusion_positive(self):
        full_text = (
            "원심은 피고의 이 사건 부당이득반환 의무가 소멸시효 완성으로 소멸하였다고 판단하였다. "
            "그러나 이러한 원심의 판단에는 부당이득반환청구권의 소멸시효 기산점에 관한 법리를 오해하여 "
            "판결에 영향을 미친 위법이 있다. 그러므로 원심판결을 파기하고 사건을 환송한다."
        )
        claim = "부당이득반환 의무가 소멸시효 완성으로 소멸하였다고 판단하였다."

        result = detect_reversed_remand_confusion(
            claim=claim,
            full_text=full_text,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "REVERSED_REMAND_CONFUSION")
        self.assertIn("소멸시효 완성", result["lower_holding"])
        self.assertIn("법리를 오해", result["grounded_evidence_quote"])

    # 3. 양성 시험 3: 반대의견 오인 및 공식 원문 근거 인용문 검증
    def test_opinion_findings_grounded_evidence_quote_positive(self):
        citation = Citation(
            citation_id="cit_test_lv05_pos",
            type=CitationType.CASE,
            raw_text="대법원 2021다88888 판결",
            case_number="2021다88888",
            canonical_case_number="2021다88888",
            quoted_text="군인은 먼저 군 내부의 건의 절차를 거쳐야 하고 이를 거치지 아니한 소 제기는 복종의무 위반이다.",
            attributes={"case_claim": "군인은 먼저 건의 절차를 거쳐야 한다."},
        )
        official = {
            "case_number": "2021다88888",
            "full_text": (
                "상고이유를 판단한다. 군인이 상관의 지시에 대하여 소송을 제기하기 전에 반드시 군 내부 건의 절차를 거쳐야 하는 것은 아니다. "
                "대법관 갑의 반대의견은 다음과 같다. 군인은 먼저 군 내부의 건의 절차를 거쳐야 하고 이를 거치지 아니한 소 제기는 복종의무 위반이다."
            ),
            "summary": "[다수의견] 건의 절차를 먼저 거칠 필요 없다. [반대의견] 군인은 먼저 군 내부의 건의 절차를 거쳐야 하고 이를 거치지 아니한 소 제기는 복종의무 위반이다.",
        }

        findings = self.verifier._opinion_findings(citation, official)
        self.assertTrue(len(findings) >= 1)
        finding = findings[0]
        self.assertEqual(finding.type, FindingType.CASE_HOLDING_DISTORTION)
        self.assertEqual(finding.status, VerificationStatus.CONTRADICTED)
        self.assertIn("CIT-MIS", finding.tags)
        self.assertIn("MISATTRIBUTED_OPINION", finding.tags)
        self.assertIn("grounded_evidence_quote", finding.confidence_features)
        # 증거 객체 검증
        official_ev = next((ev for ev in finding.evidence if "근거 문장" in ev.description), None)
        self.assertIsNotNone(official_ev)
        self.assertEqual(official_ev.grade, EvidenceGrade.A)
        self.assertIn("복종의무 위반", official_ev.excerpt)

    # 4. 대조 시험 1: 정상 현행 다수의견 인용
    def test_valid_majority_holding_control(self):
        full_text = (
            "상고이유를 판단한다. 근로자에 대한 전보발령은 인사권자인 사용자의 고유권한에 속하므로 업무상 필요성이 인정된다. "
            "대법관 정의 반대의견은 다음과 같다. 근로자의 동의 없는 전보는 무효이다."
        )
        summary = "[다수의견] 전보발령은 업무상 필요성이 인정된다. [반대의견] 근로자의 동의가 필요하다."
        claim = "근로자에 대한 전보발령은 업무상 필요성이 인정되는 범위 내에서 사용자의 고유권한이라고 판시하였다."

        changed = detect_changed_precedent_distortion(claim, full_text, summary, "2020다99999")
        remand = detect_reversed_remand_confusion(claim, full_text, summary)
        attr = attribute_claim(claim, full_text, summary)

        self.assertIsNone(changed)
        self.assertIsNone(remand)
        self.assertIsNone(attr["verdict"])

    # 5. 대조 시험 2: 문맥상 별개의견임을 명시한 인용
    def test_explicit_concurring_opinion_control(self):
        citation = Citation(
            citation_id="cit_test_lv05_concurring",
            type=CitationType.CASE,
            raw_text="대법원 2022다11111 판결",
            case_number="2022다11111",
            canonical_case_number="2022다11111",
            quoted_text="기본권 침해 여부를 직접 심사하여야 한다",
            context="대법관 누구의 별개의견에 의하면 기본권 침해 여부를 직접 심사하여야 한다고 보았다.",
        )
        official = {
            "case_number": "2022다11111",
            "full_text": (
                "상고이유를 판단한다. 행정청의 처분은 적법하다. "
                "대법관 갑의 별개의견은 다음과 같다. 기본권 침해 여부를 직접 심사하여야 한다."
            ),
            "summary": "[다수의견] 행정청의 처분은 적법하다. [별개의견] 기본권 침해 여부를 직접 심사하여야 한다.",
        }

        findings = self.verifier._opinion_findings(citation, official)
        # 별개의견임을 문맥에서 명시했으므로 오경고 발생하지 않음
        misattributed = [f for f in findings if f.confidence_features.get("verdict_label") == "MISATTRIBUTED_OPINION"]
        self.assertEqual(len(misattributed), 0)

    # 6. 대조 시험 3: 판시사항 결론 방향과 일치하는 요약
    def test_direction_matches_holding_control(self):
        holding = "[1] 사용자가 근로자에게 안전배려의무를 부담하는지 여부(적극)"
        claim = "사용자는 근로자에 대하여 안전배려의무를 부담한다고 판시하였다."

        conflict = direction_conflict(claim, holding)
        self.assertIsNone(conflict)


import pytest
from packages.source_adapters import SourceRegistry
from packages.source_adapters.base import AdapterResponse
from packages.common.enums import AdapterStatus


class _MockLaw:
    def __init__(self, records):
        self.records = records

    def search_case(self, *args, **kw):
        return AdapterResponse(AdapterStatus.READY, self.records, None, "synthetic")


def _make_mock_verifier(records):
    registry = SourceRegistry()
    registry.legal[0] = _MockLaw(records)
    return LegalVerifier(registry)


@pytest.mark.parametrize("party,duty", [("매수인", "대금지급"), ("임차인", "차임지급"), ("수급인", "공사완성")])
def test_lv05_explicit_lower_court_history_is_not_supreme_adoption(party: str, duty: str):
    holding = f"{party}의 {duty} 의무가 계약 해제로 소멸하였"
    full = f"원심은 {holding}다고 판단하였다. 그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다."
    claim = f"원심은 {holding}다고 판단하였다. 이 내용은 사건 경과의 설명이다."
    c = Citation(citation_id="c", type=CitationType.CASE, raw_text="대법원 2021다67283 판결",
                 court="대법원", case_number="2021다67283", canonical_case_number="2021다67283",
                 page=1, attributes={"case_claim": claim}, context=claim)
    result = _make_mock_verifier([dict(case_number=c.case_number, court="대법원", full_text=full)]).verify_citations([c])
    assert not any(f.confidence_features.get("verdict_label") == "REVERSED_REMAND_CONFUSION" for f in result.findings)


if __name__ == "__main__":
    unittest.main()

