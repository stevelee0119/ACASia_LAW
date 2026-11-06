# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-FORM #235 평가 측 보완 시험(D1~D5). 평가 측 비공개 탐침과 다른 낱말로 새로 지은 합성예다."""
from __future__ import annotations

import time
import unittest

from packages.claim_engine.evidence_consistency import _fold_blanks, _foreign_script_name, check_document
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(lines):
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="b" * 64)
    page = Page(page_number=1, width=595.0, height=842.0)
    for i, t in enumerate(lines):
        page.blocks.append(Block(block_id=f"b{i}", page=1, text=t, block_type="paragraph", source_layer="visible_text"))
    doc.pages.append(page)
    return doc


def _codes(lines):
    return [(f.confidence_features or {}).get("defect_code") for f in check_document(_doc(lines))
            if f.type == FindingType.EVIDENCE_FORM_DEFECT]


def _brief(body, rows, sign="원고 소송대리인 변호사 ○○○"):
    return ["준 비 서 면", "원고 하○○", "피고 주식회사 늘봄"] + body + ["입 증 방 법"] + rows + ["20○○. ○. ○.", sign]


class TestD1ParenAbbreviation(unittest.TestCase):
    """괄호 속 약어 풀이는 서증명 본체가 아니다."""

    def test_korean_name_with_english_expansion_is_not_foreign(self):
        self.assertFalse(_foreign_script_name("ERP(Enterprise Resource Planning) 매출 조회 화면"))
        self.assertNotIn("TRANSLATION_MISSING", _codes(_brief(["매출은 조회 화면으로 확인됩니다(갑 제1호증)."],
                                                              ["1. 갑 제1호증 ERP(Enterprise Resource Planning) 매출 조회 화면"])))

    def test_foreign_name_with_parenthetical_note_still_foreign(self):
        self.assertTrue(_foreign_script_name("Bill of Lading (선하증권)"))


class TestD2AddressToken(unittest.TestCase):
    def test_domain_and_email_are_not_language(self):
        self.assertFalse(_foreign_script_name("www.neulbom-shop.co.kr 주문 내역 출력물"))
        self.assertFalse(_foreign_script_name("order@neulbom-shop.com 수신 메일"))

    def test_address_check_is_linear(self):
        start = time.time()
        _foreign_script_name("a." * 20000 + "!")
        _foreign_script_name("a" * 40000 + ".")
        self.assertLess(time.time() - start, 1.0)


class TestD3ApplicantSignLine(unittest.TestCase):
    """공용 판별이 작성 측을 못 정하면 신청 사건 서명 줄(채권자·신청인 / 채무자·피신청인)로 정한다."""

    def test_creditor_sign_line_makes_sogap_own(self):
        lines = ["부동산가압류 신청서", "채권자 노○○", "채무자 주식회사 늘봄", "신 청 이 유",
                 "채무자는 싱가포르 법인과 거래하였습니다(소갑 제1호증).", "소 명 방 법",
                 "1. 소갑 제1호증 Master Purchase Agreement and Schedules", "20○○. ○. ○.", "채권자 노○○ (인)"]
        self.assertIn("TRANSLATION_MISSING", _codes(lines))

    def test_debtor_sign_line_does_not_flag_creditor_marks_as_own(self):
        lines = ["이의신청서", "채권자 노○○", "채무자 주식회사 늘봄", "이 의 이 유",
                 "채권자가 낸 소갑 제1호증은 사실과 다릅니다.", "소 명 방 법",
                 "1. 소을 제1호증 Payment Confirmation from Overseas Bank", "20○○. ○. ○.", "채무자 주식회사 늘봄 대표이사 ○○○"]
        codes = _codes(lines)
        self.assertNotIn("PARTY_MARK_MISMATCH", codes)


class TestD4OneFindingPerExhibit(unittest.TestCase):
    def test_g4_wins_over_g1_on_same_exhibit(self):
        lines = _brief(["갑 제2호증 Delivery Note and Receipt는 받은 사람의 서명을 확인할 수 없으나, 인도 사실이 증명됩니다."],
                       ["1. 갑 제2호증 Delivery Note and Receipt"])
        codes = _codes(lines)
        self.assertIn("FORM_ELEMENT_ADMITTED", codes)
        self.assertNotIn("TRANSLATION_MISSING", codes)


class TestD5FoldConsecutiveBlanks(unittest.TestCase):
    def test_spaces_and_underscores_fold_to_one_mark(self):
        self.assertEqual(_fold_blanks("작성자 :   ____   (인)"), "작성자 :□(인)")
        self.assertEqual(_fold_blanks("20  년   월   일"), "20□년□월□일")

    def test_mixed_blank_sign_line_and_partial_year(self):
        lines = ["경 위 서", "본인은 위 매장에서 근무하며 사고를 목격하였습니다.", "위 내용은 사실입니다.",
                 "20  년   월   일", "작성자 :   ____   (인)"]
        self.assertIn("SIGNATURE_DATE_BLANK", _codes(lines))

    def test_fold_is_linear(self):
        start = time.time()
        _fold_blanks("성명 :" + " _" * 20000 + "x")
        self.assertLess(time.time() - start, 1.0)


if __name__ == "__main__":
    unittest.main()
