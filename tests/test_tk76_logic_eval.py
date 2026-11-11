# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-LOGIC 잔여 평가 측 시험(L1~L3). 평가 측 비공개 탐침과 다른 낱말로 새로 지은 합성예다."""
from __future__ import annotations

import os
import time
import unittest
from unittest import mock

from packages.claim_engine.evidence_consistency import check_reasoning_structure
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(lines):
    doc = NormalizedDocument(document_id="l", filename="l.pdf", mime_type="application/pdf", sha256="e" * 64)
    page = Page(page_number=1, width=595.0, height=842.0)
    for k, t in enumerate(lines):
        page.blocks.append(Block(block_id=f"b{k}", page=1, text=t, block_type="paragraph", source_layer="visible_text"))
    doc.pages.append(page)
    return doc


def _rules(lines):
    return [(f.confidence_features or {}).get("rule_id") for f in check_reasoning_structure(_doc(lines))]


class TestL1PreviousSentenceElsewhere(unittest.TestCase):
    # TK-151: L1은 기본으로 꺼져 있다(재설계 대기). 규칙 자체의 회귀는 스위치를 켜고 그대로 본다.
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"LV_ENABLE_PERCEPTION_STRUCTURE_L1": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_elsewhere_then_direct_sight(self):
        self.assertIn("EVI.BEYOND_PERCEPTION_STRUCTURE", _rules(
            ["그 시간에 저는 목포항 여객터미널 대합실에 있었습니다.", "저는 피고가 창고 열쇠를 숨기는 것을 똑똑히 보았습니다."]))

    def test_moved_before_seeing(self):
        self.assertEqual(_rules(["오전에 저는 목포항 여객터미널에 있었습니다.", "오후에 창고로 돌아와 피고가 열쇠를 숨기는 것을 직접 보았습니다."]), [])

    def test_l1_variations_word_order_endings_and_lexicon(self):
        # 어순 변형: 시간 표지가 둘째 문장 첫머리에 위치 / 첫 문장 중간('하루 종일', '내내')에 위치
        self.assertIn("EVI.BEYOND_PERCEPTION_STRUCTURE", _rules(
            ["저는 강릉 연수원 숙소에 머물렀습니다.", "같은 시각 저는 피고가 사무실 금고를 여는 모습을 직접 목격하였습니다."]))
        self.assertIn("EVI.BEYOND_PERCEPTION_STRUCTURE", _rules(
            ["진술인은 사건 당일 하루 종일 부산 지사 회의실에 지냈다.", "진술인은 원고가 본사 복도에서 서류를 찢는 장면을 두 눈으로 보았다."]))
        # 어미·체재 서술 변형 (-다, -음, 중이었다) 및 청각 직접 지각
        self.assertIn("EVI.BEYOND_PERCEPTION_STRUCTURE", _rules(
            ["당시 본인은 대전 물류센터에서 근무 중이었음.", "동시에 본인은 서울 매장 안에서 오간 폭언을 현장에서 직접 들었음."]))
        # 대조: 이동 표지('이동하여', '도착한 뒤에') 및 매개 지각('전해 들었다')
        self.assertEqual(_rules(["당시 저는 오전에 수원 지점에 있었습니다.", "그 뒤 본사로 이동하여 피고가 서류를 가져가는 것을 직접 보았습니다."]), [])
        self.assertEqual(_rules(["그때 저는 제주 공항 대합실에 머물렀습니다.", "저는 피고가 매장에서 소란을 피웠다고 동료에게 전해 들었습니다."]), [])


class TestL1DisabledByDefault(unittest.TestCase):
    """TK-151(사용자 11-11 결정 D4): 스위치가 없으면 L1 결과를 내지 않는다."""
    def test_l1_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LV_ENABLE_PERCEPTION_STRUCTURE_L1", None)
            self.assertNotIn("EVI.BEYOND_PERCEPTION_STRUCTURE", _rules(
                ["그 시간에 저는 목포항 여객터미널 대합실에 있었습니다.", "저는 피고가 창고 열쇠를 숨기는 것을 똑똑히 보았습니다."]))
            self.assertNotIn("EVI.BEYOND_PERCEPTION_STRUCTURE", _rules(
                ["당시 저는 목포 물류센터에 있었는데, 그때 피고가 원고의 차량을 긁는 장면을 직접 보았습니다."]))


class TestL2SingleToAlways(unittest.TestCase):
    def test_single_observation_to_habit(self):
        self.assertIn("EVI.SINGLE_TO_ALWAYS", _rules(["피고는 한 차례 정산서를 늦게 낸 적이 있으므로 피고는 언제나 정산을 미루는 사람입니다."]))

    def test_never_and_rule_text_and_rebuttal(self):
        self.assertEqual(_rules(["원고는 한 번도 결근한 적이 없으므로 항상 성실하였습니다."]), [])
        self.assertEqual(_rules(["규정은 1회 위반 시 경고로 정하므로 매번 횟수를 따져야 합니다."]), [])
        self.assertEqual(_rules(["피고가 한 번 늦었으므로 늘 늦는다는 원고의 주장은 근거가 없습니다."]), [])

    def test_l2_variations_connectives_word_order_and_lexicon(self):
        # 연결 어미·접속사 변형 (-기 때문에, -으니, -니까, 따라서, 그러므로) 및 다른 어휘(딱 한 번, 단 1회, 매번, 상습적, 번번이, 습관적)
        self.assertIn("EVI.SINGLE_TO_ALWAYS", _rules(
            ["원고가 지난달 딱 한 번 보고서를 지연 제출한 사실이 있기 때문에 원고는 매번 마감 기한을 어기는 직원입니다."]))
        self.assertIn("EVI.SINGLE_TO_ALWAYS", _rules(
            ["임차인이 작년에 단 1회 차임을 연체하였으니 임차인은 상습적으로 차임을 연체하고 있습니다."]))
        self.assertIn("EVI.SINGLE_TO_ALWAYS", _rules(
            ["피고는 현장에서 한 번 안전모를 벗었으니까 번번이 안전수칙을 무시하는 자입니다."]))
        self.assertIn("EVI.SINGLE_TO_ALWAYS", _rules(
            ["담당자가 한 차례 회계 전표를 잘못 입력한 일이 있었고, 따라서 담당자는 습관적으로 장부를 부실하게 관리한다."]))


class TestL3SilenceAsConsent(unittest.TestCase):
    def test_silence_to_consent(self):
        self.assertIn("EVI.SILENCE_AS_CONSENT", _rules(["피고는 원고의 임대료 인상 통지에 회신하지 않았으므로 인상에 동의한 것입니다."]))

    def test_deemed_clause_conduct_and_commercial(self):
        self.assertEqual(_rules(["임대차계약은 통지 후 10일 안에 이의가 없으면 동의한 것으로 본다고 정하였고 피고는 회신하지 않았으므로 인상에 합의가 되었습니다."]), [])
        self.assertEqual(_rules(["피고는 이의 없이 인상된 임대료를 석 달 동안 입금하였으므로 인상에 동의한 것입니다."]), [])
        self.assertEqual(_rules(["피고는 상시 거래관계에 있는 상인으로서 낙부통지를 하지 않았으므로 상법 제53조에 따라 승낙한 것으로 봅니다."]), [])

    def test_l3_variations_and_three_exclusion_categories(self):
        # 양성 변형 (어순·연결 어미·같은 꼴 다른 낱말: 이의 제기하지 않 / 답도 없 / 반대 의견 보내지 않 / 침묵 -> 승낙 / 수락 / 합의 / 승인)
        self.assertIn("EVI.SILENCE_AS_CONSENT", _rules(
            ["매수인은 계약 조건 변경 안내에 아무런 이의를 제기하지 않았기 때문에 변경안을 전적으로 승낙한 것입니다."]))
        self.assertIn("EVI.SILENCE_AS_CONSENT", _rules(
            ["원고가 정산 내역서를 보냈음에도 피고는 답도 없었으니 위 정산 금액에 합의한 것이다."]))
        self.assertIn("EVI.SILENCE_AS_CONSENT", _rules(
            ["피신청인은 해지 통고서에 반대 의견을 보내지 않았으므로 계약 해지를 수락하였습니다."]))
        self.assertIn("EVI.SILENCE_AS_CONSENT", _rules(
            ["상대방은 추가 공사비 청구에 끝내 침묵하였으므로 그러므로 추가 비용 지급을 승인한 것입니다."]))

        # 제외 1꼴: 간주 약정·법정 근거 (약정, 간주, 보기로, 상법 제53조, 상시 거래)
        self.assertEqual(_rules(
            ["특약사항에 따라 서면 통보 후 7일 내 회신이 없으면 변경에 동의한 것으로 간주하므로 피고가 답하지 않아 변경에 합의한 것입니다."]), [])
        self.assertEqual(_rules(
            ["양측은 이의가 없으면 연장하기로 약정하였고 임차인이 응답하지 않았으므로 갱신에 동의한 것입니다."]), [])

        # 제외 2꼴: 부정 서술 ('볼 수 없다', '아니다')
        self.assertEqual(_rules(
            ["피고가 원고의 최고서에 회신하지 않았으므로 이를 두고 곧바로 채무를 승인한 것이라고 볼 수는 없습니다."]), [])
        self.assertEqual(_rules(
            ["임차인이 인상 요구에 대답하지 않았기 때문에 인상에 동의한 것이 아니다."]), [])

        # 제외 3꼴: 행동으로 드러난 묵시 동의 ('없이 + 지급·수령·이행·사용·서명·날인·납부')
        self.assertEqual(_rules(
            ["피고는 별다른 이의 없이 변경된 단가로 납품 대금을 수령하였으므로 단가 조정에 합의한 것입니다."]), [])
        self.assertEqual(_rules(
            ["원고는 반대 없이 정산 합의서에 직접 서명하였으므로 정산 조건을 수락한 것입니다."]), [])

        # 공통 제외: 상대방 주장 인용·반박
        self.assertEqual(_rules(
            ["원고는 피고가 회신하지 않았으므로 계약 변경에 동의하였다는 주장을 하나 이는 부당합니다."]), [])

    def test_linear_time(self):
        start = time.time()
        check_reasoning_structure(_doc(["한 번 " * 5000 + "있으므로 " + "항상 " * 5000 + "."]))
        check_reasoning_structure(_doc(["에서 " + "가나 " * 8000 + "있었습니다.", "직접 " * 5000 + "보았습니다."]))
        self.assertLess(time.time() - start, 2.0)


if __name__ == "__main__":
    unittest.main()
