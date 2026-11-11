# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-DATE 평가 측 시험(T1 기간 일수). 평가 측 비공개 탐침과 다른 낱말로 새로 지은 합성예다."""
from __future__ import annotations

import time
import unittest

from packages.claim_engine import date_verifier as dv
from packages.common.schemas import Block, NormalizedDocument, Page


def _run(sentence):
    doc = NormalizedDocument(document_id="t", filename="t.pdf", mime_type="application/pdf", sha256="d" * 64)
    page = Page(page_number=1, width=595.0, height=842.0)
    page.blocks.append(Block(block_id="b0", page=1, text=sentence, block_type="paragraph", source_layer="visible_text"))
    doc.pages.append(page)
    return [f for f in dv.verify_dates_in_document(doc)
            if (f.confidence_features or {}).get("rule_id") == "claim_engine.date_verifier:DAYS_RANGE_MISMATCH"]


class TestT1RangeDays(unittest.TestCase):
    def test_wrong_inclusive_count(self):
        self.assertTrue(_run("피고는 2025. 8. 4.부터 2025. 8. 29.까지 7일간 정비 작업을 하였다."))

    def test_korean_date_form_and_dongan(self):
        self.assertTrue(_run("원고는 2025년 10월 1일부터 2025년 10월 15일까지 40일 동안 입원하였다."))

    def test_correct_inclusive_and_exclusive_counts(self):
        self.assertEqual(_run("원고는 2025. 8. 4.부터 2025. 8. 29.까지 26일간 정비 작업을 하였다."), [])
        self.assertEqual(_run("원고는 2025. 8. 4.부터 2025. 8. 29.까지 25일간 정비 작업을 하였다."), [])

    def test_business_day_basis_is_skipped(self):
        self.assertEqual(_run("원고는 2025. 8. 4.부터 2025. 8. 29.까지 근무일 기준 20일간 정비 작업을 하였다."), [])

    def test_month_period_not_days(self):
        self.assertEqual(_run("원고는 2025. 8. 4.부터 2025. 10. 3.까지 2개월간 정비 작업을 하였다."), [])

    def test_linear_time(self):
        start = time.time()
        list(dv.DAYS_RANGE_RE.finditer("2025" + ". " * 20000))
        self.assertLess(time.time() - start, 1.0)


class TestT1RangeDaysVariations(unittest.TestCase):
    """2-2 다 규약 변형 시험: 어순·연결 어미·같은 꼴 다른 낱말 변형 및 제외 조건 대조."""

    def test_t1_word_order_and_connective_variations(self):
        # 어순(기간 구절 선행/중간/후행) 및 연결 어미(-으므로, -으나, -더라도) 변형 양성 3건
        pos_sentences = [
            "2025-03-10부터 2025-03-25까지 총 5일간 장비 임대가 이루어졌으므로, 피고는 사용료를 정산해야 합니다.",
            "원고가 주장하는 하자보수 기간은 2025. 5. 1.에서 2025. 5. 20.까지 모두 6일에 걸쳐 진행되었으나, 완료되지 못했습니다.",
            "설령 피고가 2025년 7월 10일에서 2025년 7월 30일까지 합계 9일 동안 현장에 상주하였더라도, 지체상금은 면제되지 않습니다.",
        ]
        for sent in pos_sentences:
            found = _run(sent)
            self.assertEqual(len(found), 1, f"Expected DAYS_RANGE_MISMATCH on: {sent}")

    def test_t1_lexical_and_format_variations(self):
        # 같은 꼴 다른 낱말(날짜 구분자 하이픈/슬래시/점/년월일, 조사 '부터'/'에서', 수식어 '총'/'모두'/'합계', 단위 '일간'/'일 동안'/'일에 걸쳐') 양성 3건
        cases = [
            ("신청인은 2025/04/01에서 2025/04/20까지 합계 8일간 직무 교육을 이수하였습니다.", 8, 20),
            ("이 사건 공사는 2025-06-05부터 2025-06-24까지 모두 45일 동안 중단되었습니다.", 45, 20),
            ("피고는 2025. 11. 1.부터 2025. 11. 18.까지 총 3일에 걸쳐 물품을 나누어 인도하였습니다.", 3, 18),
        ]
        for sent, stated, inclusive in cases:
            found = _run(sent)
            self.assertEqual(len(found), 1, f"Expected DAYS_RANGE_MISMATCH on: {sent}")
            feat = found[0].confidence_features or {}
            self.assertEqual(feat.get("stated_days"), stated)
            self.assertEqual(feat.get("inclusive_days"), inclusive)

    def test_t1_basis_exclusion_and_valid_controls(self):
        # 대조군: 영업일·평일·공휴일 제외 등 셈법 표지 및 정상 일수(양 끝 포함 / 초일 불산입 1일 차이)
        control_sentences = [
            "피고는 2025. 4. 1.부터 2025. 4. 20.까지 영업일 기준 14일간 납품을 진행하였습니다.",
            "원고는 2025년 5월 1일에서 2025년 5월 31일까지 공휴일 제외 21일 동안 출근하였습니다.",
            "신청인은 2025-09-01부터 2025-09-15까지 평일 11일에 걸쳐 감사를 실시하였습니다.",
            "계약 이행 기간은 2025. 6. 1.부터 2025. 6. 10.까지 총 10일간(초일 불산입 시 9일)입니다.",
        ]
        for sent in control_sentences:
            self.assertEqual(_run(sent), [], f"False positive on control: {sent}")


if __name__ == "__main__":
    unittest.main()
