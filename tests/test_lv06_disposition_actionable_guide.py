"""LV-06: 청구원인 요건사실 점검 및 실무 조치 안내 단위 시험.

- 3건의 양성 시험:
  1. 청구원인(불법행위) 요건사실 주장 누락 점검 (ELEMENT_OMISSION)
  2. 부존재/가공 판례에 대한 석명 촉구 신청서 안 생성 (Tier 1 CLARIFICATION_MOTION)
  3. 판시 취지 왜곡에 대한 변론 재구성 권고 생성 (Tier 3 HOLDING_CORRECTION)
- 3건의 대조 시험:
  4. 모든 요건사실이 충족된 정상 서면 (경고 0건)
  5. 공식 원문 일치 판례의 사건 적용성 직접 검토 안내 (Tier 4 APPLICATION_CHECK)
  6. 하급심 출처 한계에 대한 판결서 열람 신청 안내 (Tier 2 SOURCE_VERIFICATION)
"""
from __future__ import annotations

import unittest
from packages.common.enums import FindingType, VerificationStatus
from packages.common.schemas import NormalizedDocument, Page, Block
from packages.legal_engine.actionable_guidance import (
    check_cause_of_action_elements,
    generate_actionable_guidance,
)


def _make_doc(text: str) -> NormalizedDocument:
    block = Block(
        block_id="b1",
        page=1,
        text=text,
    )
    page = Page(page_number=1, width=1000.0, height=1400.0, blocks=[block])
    return NormalizedDocument(
        document_id="doc_test_lv06",
        filename="test.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


class TestLV06ActionableGuide(unittest.TestCase):
    # 1. 양성 시험 1: 청구원인 요건사실 주장 누락 점검
    def test_cause_of_action_element_omission_positive(self):
        # 민법 750조 불법행위 손해배상을 주장하지만 손해 발생 및 인과관계 주장이 누락된 경우
        text = (
            "청 구 원 인\n"
            "1. 피고의 불법행위 책임 성립\n"
            "피고는 원고에 대하여 중대한 주의의무를 위반한 과실이 있고 위법행위를 저질렀습니다.\n"
            "따라서 민법 제750조에 따른 불법행위 손해배상 책임을 부담합니다."
        )
        doc = _make_doc(text)
        findings = check_cause_of_action_elements(doc)

        self.assertTrue(len(findings) >= 1)
        finding = findings[0]
        self.assertEqual(finding.type, FindingType.LEGAL_ARGUMENT_INVALID)
        self.assertIn("ELEMENT_OMISSION", finding.tags)
        self.assertIn("손해 발생", finding.confidence_features["missing_elements"])
        self.assertIn("인과관계", finding.confidence_features["missing_elements"])

    # 2. 양성 시험 2: 부존재/가공 판례에 대한 석명 촉구 신청서 안 생성
    def test_actionable_guidance_confirmed_nonexistent_positive(self):
        guidance = generate_actionable_guidance(
            basis="CONFIRMED_NONEXISTENT",
            cited_authority="대법원 2021다999999 판결",
            claim_text="해당 법리에 따라 손해배상 책임이 인정된다.",
        )
        self.assertEqual(guidance["action_tier"], "CONFIRMED_ERROR")
        self.assertEqual(guidance["action_type"], "CLARIFICATION_MOTION")
        self.assertIn("석명 촉구 신청서", guidance["action_title"])
        self.assertIsNotNone(guidance["draft_motion_text"])
        self.assertIn("석명촉구신청서 안", guidance["draft_motion_text"])
        self.assertIn("2021다999999", guidance["draft_motion_text"])
        self.assertTrue(len(guidance["recommended_steps"]) >= 2)

    # 3. 양성 시험 3: 판시 취지 왜곡에 대한 변론 재구성 권고 생성
    def test_actionable_guidance_holding_distortion_positive(self):
        guidance = generate_actionable_guidance(
            basis="CONTRADICTION",
            cited_authority="대법원 2015다77777 판결",
            claim_text="일방적 해고 권한 유보 약정은 무효이다.",
            distortion_type="CHANGED_PRECEDENT",
            grounded_evidence_quote="이 판결의 견해에 배치되는 범위 내에서 이를 변경하기로 한다.",
        )
        self.assertEqual(guidance["action_tier"], "HOLDING_DISTORTION")
        self.assertEqual(guidance["action_type"], "HOLDING_CORRECTION")
        self.assertIn("변경된 종전 판례", guidance["action_title"])
        self.assertIn("변경하기로 한다", guidance["guidance_summary"])
        self.assertIsNone(guidance["draft_motion_text"])  # 왜곡은 석명신청이 아닌 변론 수정
        self.assertTrue(any("대체 선례" in step or "교체" in step for step in guidance["recommended_steps"]))

    # 4. 대조 시험 1: 모든 요건사실이 충족된 정상 서면
    def test_cause_of_action_all_elements_present_control(self):
        text = (
            "청 구 원 인\n"
            "1. 피고의 불법행위 책임\n"
            "피고는 주의의무를 다하지 않은 과실 및 위법행위로 인하여 원고에게 상당한 재산상 손해를 입혔습니다.\n"
            "피고의 가해행위와 원고의 손해 발생 사이에는 상당인과관계가 명백하므로, "
            "피고는 민법 제750조 불법행위로 인한 손해배상금 50,000,000원을 지급할 의무가 있습니다."
        )
        doc = _make_doc(text)
        findings = check_cause_of_action_elements(doc)
        self.assertEqual(len(findings), 0)

    # 5. 대조 시험 2: 공식 원문 일치 판례의 사건 적용성 직접 검토 안내
    def test_actionable_guidance_official_confirmed_control(self):
        guidance = generate_actionable_guidance(
            basis="OFFICIAL_CONFIRMED",
            cited_authority="대법원 2020다12345 판결",
            claim_text="지체상금 배제 특약의 유효성에 관한 판단",
        )
        self.assertEqual(guidance["action_tier"], "OFFICIAL_CONFIRMED")
        self.assertEqual(guidance["action_type"], "APPLICATION_CHECK")
        self.assertIn("사건 적용성", guidance["guidance_summary"])
        self.assertIsNone(guidance["draft_motion_text"])

    # 6. 대조 시험 3: 하급심 출처 한계에 대한 판결서 열람 신청 안내
    def test_actionable_guidance_source_limit_control(self):
        guidance = generate_actionable_guidance(
            basis="UNCONFIRMED_SOURCE_LIMIT",
            cited_authority="서울고등법원 2020나55555 판결",
            claim_text="하급심 판결 원용",
        )
        self.assertEqual(guidance["action_tier"], "SOURCE_LIMIT_SUSPICIOUS")
        self.assertEqual(guidance["action_type"], "SOURCE_VERIFICATION")
        self.assertIn("판결서 인터넷 열람", guidance["action_title"])
        self.assertIn("scourt.go.kr", guidance["official_portal_url"])


if __name__ == "__main__":
    unittest.main()
