# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-NUM 평가 측 시험(E1~E3). 평가 측 비공개 탐침과 다른 낱말로 새로 지은 합성예다."""
from __future__ import annotations

import unittest

from packages.claim_engine.evidence_consistency import check_document
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page

_NUM = {FindingType.EVIDENCE_NUMBERING_GAP, FindingType.EVIDENCE_LIST_MISMATCH, FindingType.EVIDENCE_REFERENCE_MISSING}


def _doc(lines):
    doc = NormalizedDocument(document_id="n", filename="n.pdf", mime_type="application/pdf", sha256="c" * 64)
    page = Page(page_number=1, width=595.0, height=842.0)
    for i, t in enumerate(lines):
        page.blocks.append(Block(block_id=f"b{i}", page=1, text=t, block_type="paragraph", source_layer="visible_text"))
    doc.pages.append(page)
    return doc


def _num(body, rows):
    lines = ["준 비 서 면", "원고 국○○", "피고 주식회사 솔길"] + body + ["입 증 방 법"] + rows + ["2025. 9. 30.", "원고 소송대리인 변호사 ○○○"]
    return [f for f in check_document(_doc(lines)) if f.type in _NUM
            and (f.confidence_features or {}).get("defect_code") != "EVIDENCE_NUMBER_DUPLICATE"]


class TestE1PriorAndFutureCitations(unittest.TestCase):
    def test_numbers_below_new_list_start_are_prior_submissions(self):
        found = _num(["앞 서면 갑 제3호증 납품서에서 보듯 물품은 인도되었고, 대금 청구는 새 자료로 뒷받침됩니다(갑 제8호증)."],
                     ["1. 갑 제8호증 미수금 원장", "2. 갑 제9호증 독촉장"])
        self.assertEqual(found, [])

    def test_future_submission_notice_is_not_missing(self):
        found = _num(["물품 단가는 거래처 확인서를 받아 갑 제3호증으로 추후 제출하겠습니다. 인도 사실은 갑 제1호증으로 증명됩니다."],
                     ["1. 갑 제1호증 납품서", "2. 갑 제2호증 세금계산서"])
        self.assertEqual(found, [])

    def test_genuine_missing_citation_still_found(self):
        found = _num(["피고는 물품을 받고도 대금을 주지 않았습니다(갑 제3호증 미수금 원장)."],
                     ["1. 갑 제1호증 납품서", "2. 갑 제2호증 세금계산서"])
        self.assertTrue(any("갑 제3호증" in f.title for f in found))


class TestE2BranchCitation(unittest.TestCase):
    def test_branch_beyond_listed_branches(self):
        found = _num(["물품 상태는 검수 사진으로 확인됩니다(갑 제4호증의 5)."], ["1. 갑 제4호증의 1 내지 4 각 검수사진"])
        self.assertTrue(any((f.confidence_features or {}).get("defect_code") == "BRANCH_REFERENCE_MISSING" for f in found))

    def test_branch_within_listed_range(self):
        found = _num(["물품 상태는 검수 사진으로 확인됩니다(갑 제4호증의 3)."], ["1. 갑 제4호증의 1 내지 4 각 검수사진"])
        self.assertEqual(found, [])


class TestE3ParenBoundary(unittest.TestCase):
    def test_body_name_in_parentheses_points_to_other_number(self):
        found = _num(["당사자는 단가를 정하였습니다(갑 제1호증 단가합의서)."],
                     ["1. 갑 제1호증 납품서", "2. 갑 제2호증 단가합의서"])
        self.assertTrue(any((f.confidence_features or {}).get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH" for f in found))

    def test_matching_name_in_parentheses(self):
        found = _num(["당사자는 단가를 정하였습니다(갑 제2호증 단가합의서)."],
                     ["1. 갑 제1호증 납품서", "2. 갑 제2호증 단가합의서"])
        self.assertEqual(found, [])


class TestE1ToE3Variations(unittest.TestCase):
    """2-2 다 규약 변형 시험: 어순·연결 어미·같은 꼴 다른 낱말 변형 및 E1 앞 제출 3꼴·추후 제출 3꼴."""

    def test_e1_prior_submission_three_forms(self):
        # 앞 제출 표지 3꼴: (1) '이미 제출한', (2) '종전에 제출된', (3) '제1차 준비서면에서 제출한'
        prior_sentences = [
            "원고가 이미 제출한 갑 제3호증에 의하면 계약 체결 사실이 확인되며, 손해 액수는 갑 제1호증으로 입증됩니다.",
            "종전에 제출된 갑 제4호증에서 살핀 바와 같으나, 추가 정산 내역은 갑 제1호증으로 확인됩니다.",
            "갑 제5호증은 제1차 준비서면에서 제출한 자료이므로, 이번에는 갑 제1호증과 갑 제2호증을 제출합니다.",
        ]
        rows = ["1. 갑 제1호증 정산내역서", "2. 갑 제2호증 송금확인증"]
        for sent in prior_sentences:
            found = _num([sent], rows)
            self.assertEqual(found, [], f"Prior submission falsely flagged: {sent}")

    def test_e1_future_submission_three_forms(self):
        # 추후 제출 표지 3꼴: (1) '추후 ... 제출하겠습니다', (2) '다음 기일에 ... 제출할 예정', (3) '향후 ... 낼 예정'
        future_sentences = [
            "감정 결과서는 감정인 회신이 도착하는 대로 갑 제3호증으로 추후 제출하겠습니다. 기본 사실은 갑 제1호증으로 증명됩니다.",
            "원고는 세무사 확인서를 발급받아 다음 기일에 갑 제4호증으로 제출할 예정이며, 현재 내역은 갑 제1호증과 같습니다.",
            "운송장 사본은 향후 정리하여 갑 제5호증으로 낼 예정이고, 본건 인도 사실은 갑 제1호증으로 확인됩니다.",
        ]
        rows = ["1. 갑 제1호증 거래원장", "2. 갑 제2호증 입고확인서"]
        for sent in future_sentences:
            found = _num([sent], rows)
            self.assertEqual(found, [], f"Future submission falsely flagged: {sent}")

    def test_e1_genuine_missing_positives_and_word_order_variations(self):
        # 어순·연결 어미·낱말 변형에서도 앞/추후 제출 표지가 없는 실제 목록 누락 인용은 모두 검출
        missing_sentences = [
            "보증금 반환 기일이 도래하였으므로(갑 제3호증 임대차계약서), 피고는 지급 의무가 있습니다.",
            "피고는 지급 의무가 있으나, 이는 내용증명우편(갑 제4호증)을 보더라도 명백합니다.",
            "본건 공사 완료 사실은 준공검사조서(갑 제5호증)로 확인됨에도 피고는 대금을 지체하고 있습니다.",
        ]
        rows = ["1. 갑 제1호증 등기사항전부증명서", "2. 갑 제2호증 건축물대장"]
        for sent in missing_sentences:
            found = _num([sent], rows)
            self.assertTrue(any(f.type == FindingType.EVIDENCE_LIST_MISMATCH for f in found), f"Missed genuine missing: {sent}")

    def test_e2_branch_citation_positives_and_controls_variations(self):
        # 양성 3건: 다양한 어순·호증 부호·가지번호 범위 밖 인용
        pos_cases = [
            (["현장 균열 상태는 사진으로 입증됩니다(갑 제2호증의 6)."], ["1. 갑 제2호증의 1 내지 5 각 현장사진"], "갑 제2호증의 6"),
            (["피고는 대금 수령을 부인하나 영수증(갑 제3호증의 4)에 의하면 지급이 명백합니다."], ["1. 갑 제3호증의 1 내지 3 각 영수증"], "갑 제3호증의 4"),
            (["설계 변경 내역은 도면(갑 제1호증의 3)을 보더라도 분명합니다."], ["1. 갑 제1호증의 1 내지 2 각 설계도면"], "갑 제1호증의 3"),
        ]
        for body, rows, expected_lbl in pos_cases:
            found = _num(body, rows)
            branch_f = [f for f in found if (f.confidence_features or {}).get("defect_code") == "BRANCH_REFERENCE_MISSING"]
            self.assertEqual(len(branch_f), 1, f"Expected BRANCH_REFERENCE_MISSING for {expected_lbl}")
            self.assertIn(expected_lbl, branch_f[0].title)

        # 대조: 중간 결번(목록이 의 1, 의 3일 때 본문이 의 2 인용)은 기존 가지번호 결번 판정이 맡으므로 BRANCH_REFERENCE_MISSING을 중복 생성하지 않음
        mid_gap_found = _num(
            ["계약 조건은 부속합의서(갑 제2호증의 2)로 확인됩니다."],
            ["1. 갑 제2호증의 1 기본합의서", "2. 갑 제2호증의 3 특약사항"],
        )
        branch_ref_missing = [
            f for f in mid_gap_found if (f.confidence_features or {}).get("defect_code") == "BRANCH_REFERENCE_MISSING"
        ]
        self.assertEqual(branch_ref_missing, [])

    def test_e3_paren_and_bracket_boundary_variations(self):
        # 양성 3건: 반각 소괄호 ')', 전각 소괄호 '）', 대괄호 ']' 및 조사 결합 변형
        rows = ["1. 갑 제1호증 임대차계약서", "2. 갑 제2호증 내용증명우편", "3. 갑 제3호증 건물인도확인서"]
        pos_sentences = [
            "원고는 계약 해지를 통보하였습니다(갑 제1호증 내용증명우편).",
            "원고는 건물을 인도받았으나（갑 제1호증 건물인도확인서）, 피고는 정산을 미루고 있습니다.",
            "해지 통지 사실은 첨부 자료[갑 제3호증 내용증명우편에서]로 확인됩니다.",
        ]
        for sent in pos_sentences:
            found = _num([sent], rows)
            self.assertTrue(
                any((f.confidence_features or {}).get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH" for f in found),
                f"Expected EXHIBIT_NUMBER_NAME_MISMATCH on: {sent}",
            )


if __name__ == "__main__":
    unittest.main()
