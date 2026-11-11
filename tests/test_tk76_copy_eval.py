# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-COPY 평가 측 시험(C1 어미·조사만 바꾼 복사). 평가 측 비공개 탐침과 다른 낱말로 새로 지은 합성예다."""
from __future__ import annotations

import unittest

from packages.claim_engine.evidence_consistency import _lcs_len, _stem_seq, cross_document_copies
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(i, lines):
    doc = NormalizedDocument(document_id=f"c{i}", filename=f"c{i}.pdf", mime_type="application/pdf", sha256=str(i) * 64)
    page = Page(page_number=1, width=595.0, height=842.0)
    for k, t in enumerate(lines):
        page.blocks.append(Block(block_id=f"c{i}b{k}", page=1, text=t, block_type="paragraph", source_layer="visible_text"))
    doc.pages.append(page)
    return doc


_PLEAD = ["준 비 서 면", "원고 탁○○", "피고 주식회사 한울농산",
          "피고는 2025. 5. 20. 원고 과수원에 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고 그 목재를 화물차에 실어 갔습니다.",
          "원고는 다음 날 아침 과수원을 둘러보다가 나무가 잘려 나간 자리를 발견하고 곧바로 관할 파출소에 신고하였습니다.",
          "2025. 9. 1.", "원고 소송대리인 변호사 ○○○"]


def _stmt(lines):
    return ["진 술 서", "성명 : 용○○"] + lines + ["2025. 8. 28.", "진술인 용○○ (서명)"]


def _copies(docs):
    return [f for f in cross_document_copies([_doc(i, d) for i, d in enumerate(docs)]) if f.type == FindingType.CROSS_DOC_COPY]


class TestC1LightEditCopy(unittest.TestCase):
    def test_endings_changed_two_sentences(self):
        stmt = _stmt(["피고는 2025. 5. 20. 원고 과수원에 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고 그 목재를 화물차에 실어 갔다.",
                      "원고는 다음 날 아침에 과수원을 둘러보다가 나무가 잘려 나간 자리를 발견하고 곧바로 관할 파출소에 신고했다."])
        self.assertTrue(_copies([_PLEAD, stmt]))

    def test_own_words_same_event(self):
        stmt = _stmt(["저는 그 무렵 옆 밭에서 일하다가 화물차 한 대가 과수원 쪽으로 들어가는 것을 봤고, 전기톱 소리가 한참 들렸습니다.",
                      "며칠 뒤 원고가 나무 여러 그루가 없어졌다며 속상해하는 이야기를 들었습니다."])
        self.assertEqual(_copies([_PLEAD, stmt]), [])

    def test_single_light_edit_sentence_is_not_enough(self):
        stmt = _stmt(["피고가 2025. 5. 20. 원고의 과수원에 들어와서 사전 동의도 없이 사과나무 열두 그루를 베어 냈고 그 목재를 화물차로 실어 갔다.",
                      "저는 그날 과수원 근처에 가지 않았습니다."])
        self.assertEqual(_copies([_PLEAD, stmt]), [])

    def test_stem_helpers(self):
        self.assertEqual(_stem_seq("원고는 과수원을 둘러보았다"), ["원고", "과수", "둘러"])
        self.assertEqual(_lcs_len(["가", "나", "다"], ["가", "다"]), 2)

    def test_ending_variations_three_forms(self):
        # 어미 변형 1꼴: -습니다/-하였습니다 -> -다/-하였다
        stmt_form1 = _stmt([
            "피고는 2025. 5. 20. 원고 과수원에 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고 그 목재를 화물차에 실어 갔다.",
            "원고는 다음 날 아침 과수원을 둘러보다가 나무가 잘려 나간 자리를 발견하고 곧바로 관할 파출소에 신고하였다.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_form1])), 1)

        # 어미 변형 2꼴: 연결 어미(-고 -> -며, -다가 -> -던 중) 및 종결 어미(-습니다 -> -었습니다)
        stmt_form2 = _stmt([
            "피고는 2025. 5. 20. 원고 과수원에 들어와서 사전 동의 없이 사과나무 열두 그루를 베어 내며 그 목재를 화물차에 실어 갔었습니다.",
            "원고는 다음 날 아침 과수원을 둘러보던 중 나무가 잘려 나간 자리를 발견하며 곧바로 관할 파출소에 신고했었습니다.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_form2])), 1)

        # 어미 변형 3꼴: 명사형 종결(-음/-함) 및 연결 어미(-고 -> -고서) 변형
        stmt_form3 = _stmt([
            "피고는 2025. 5. 20. 원고 과수원에 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고서 그 목재를 화물차에 실어 갔음.",
            "원고는 다음 날 아침 과수원을 둘러보다가 나무가 잘려 나간 자리를 발견하고서 곧바로 관할 파출소에 신고함.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_form3])), 1)

    def test_particle_variations_three_forms(self):
        # 조사 변형 1꼴: 주격/보조사 교체(피고는 -> 피고가, 원고는 -> 원고가)
        stmt_part1 = _stmt([
            "피고가 2025. 5. 20. 원고 과수원에 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고 그 목재를 화물차에 실어 갔습니다.",
            "원고가 다음 날 아침 과수원을 둘러보다가 나무가 잘려 나간 자리를 발견하고 곧바로 관할 파출소에 신고하였습니다.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_part1])), 1)

        # 조사 변형 2꼴: 속격·부사격 교체(원고 -> 원고의, 화물차에 -> 화물차로, 파출소에 -> 파출소로)
        stmt_part2 = _stmt([
            "피고는 2025. 5. 20. 원고의 과수원으로 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고 그 목재를 화물차로 실어 갔다.",
            "원고는 다음 날 아침에 과수원을 둘러보다가 나무들이 잘려 나간 자리를 발견하고 곧바로 관할 파출소로 신고했다.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_part2])), 1)

        # 조사 변형 3꼴: 보조사 결합(동의도, 목재마저, 자리까지, 파출소에는)
        stmt_part3 = _stmt([
            "피고는 2025. 5. 20. 원고 과수원에는 들어와 사전 동의도 없이 사과나무 열두 그루만 베어 내고 그 목재마저 화물차에 실어 갔다.",
            "원고는 다음 날 아침에는 과수원을 둘러보다가 나무가 잘려 나간 자리까지 발견하고 곧바로 관할 파출소에는 신고하였다.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_part3])), 1)

    def test_word_order_preserved_mixed_exact_and_light_edit(self):
        # 어절 순서 유지 변형: 1문장 정확 일치 + 1문장 어미·조사 변형 조합 및 진술서 간 어미·조사 변형 복사
        stmt_mixed = _stmt([
            "피고는 2025. 5. 20. 원고 과수원에 들어와 사전 동의 없이 사과나무 열두 그루를 베어 내고 그 목재를 화물차에 실어 갔습니다.",
            "원고가 다음 날 아침에 과수원을 둘러보던 중 나무가 잘려 나간 자리를 발견하고서 곧바로 관할 파출소로 신고했다.",
        ])
        self.assertEqual(len(_copies([_PLEAD, stmt_mixed])), 1)

        stmt_other_witness = [
            "진 술 서",
            "성명 : 강○○",
            "피고가 2025. 5. 20. 원고의 과수원에 들어와 사전 동의도 없이 사과나무 열두 그루를 베어 내며 그 목재를 화물차로 실어 갔다.",
            "원고는 다음 날 아침 과수원을 둘러보다가 나무가 잘려 나간 자리를 발견하고 곧바로 관할 파출소에 신고하였다.",
            "2025. 8. 29.",
            "진술인 강○○ (인)",
        ]
        self.assertTrue(_copies([stmt_mixed, stmt_other_witness]))

    def test_three_own_words_controls_same_events(self):
        # 같은 사건 자기 말 진술 대조 1: 과수원 벌목 사건을 이웃 주민이 자기 말로 서술
        ctrl1 = _stmt([
            "저는 5월 하순경 과수원 옆 농로에서 트럭이 서 있는 것을 보았고 인부들이 베어 낸 나무 기둥을 적재하고 있었습니다.",
            "이튿날 오전에 과수원 주인이 찾아와 허락도 없이 과일나무를 베어 갔다며 경찰관을 불렀다고 말했습니다.",
        ])
        self.assertEqual(_copies([_PLEAD, ctrl1]), [])

        # 같은 사건 자기 말 진술 대조 2: 물류창고 설비 파손 경위를 현장 근무자가 자기 말로 서술
        plead_warehouse = [
            "준 비 서 면",
            "원고 주식회사 청해물류",
            "피고 주식회사 동방기계",
            "피고 소속 기사들은 2025. 4. 10. 냉동창고 내부로 지게차를 몰고 들어가다가 출입문 철제 프레임을 강하게 들이받아 변형시켰습니다.",
            "원고 현장관리자는 사고 직후 냉기가 외부로 새어 나오는 것을 확인하고 임시 천막으로 틈새를 막은 뒤 수리 업체를 호출하였습니다.",
            "2025. 7. 1.",
        ]
        ctrl2 = _stmt([
            "그날 오후 지게차가 창고 입구를 통과할 때 쿵 하는 큰 소리가 났고 문짝 기둥이 휘어져 문이 제대로 닫히지 않았습니다.",
            "관리팀 직원이 급히 비닐 덮개로 입구를 가리고 수리 기사를 부르는 모습을 옆에서 지켜보았습니다.",
        ])
        self.assertEqual(_copies([plead_warehouse, ctrl2]), [])

        # 같은 사건 자기 말 진술 대조 3: 점포 원상복구 협의를 동석자가 자기 말로 서술
        plead_lease = [
            "준 비 서 면",
            "원고 박○○",
            "피고 최○○",
            "원고와 피고는 2025. 3. 15. 상가건물 1층 점포에서 만나 내부 칸막이 철거 비용을 절반씩 부담하기로 구두로 합의하였습니다.",
            "그러나 피고는 약정한 기일이 지나도록 분담금을 송금하지 아니한 채 철거 업체의 연락마저 일방적으로 피하였습니다.",
            "2025. 6. 10.",
        ]
        ctrl3 = _stmt([
            "3월 중순 점포 안에서 두 사람이 마주 앉아 인테리어 철거비를 반반씩 내기로 약속하는 자리에 함께 있었습니다.",
            "나중에 임대인으로부터 세입자가 돈을 보내지 않고 철거업자 전화도 받지 않는다는 이야기를 전해 들었습니다.",
        ])
        self.assertEqual(_copies([plead_lease, ctrl3]), [])


if __name__ == "__main__":
    unittest.main()
