"""batch-c 통합 보완: 당사자 행위 동사 누락으로 사실 날짜가 탈락하던 결함.

통합 검증에서 `tests/test_p1_2_p2_1_legal_rules_ner_meta.py::
test_p2_1c_meta_checklist_section_and_table_isolated`가 깨졌다. 원인은 batch-c의
`_PARTY_FACT_VERB_RE`에 당사자 행위 동사 '청구'가 없어, 법령을 근거로 들며 당사자가
행위한 문장이 '법리 문장'으로 걸러진 것이다. 설계 메모가 열거한 '지체'도 빠져 있었다.

이 시험은 보완한 동사들이 사실 날짜를 보존하는지(양성)와, 법원이 판단 주체인 날짜는
여전히 제외되는지(대조)를 본다. 모든 문서·문장은 합성 값이다.
"""
from __future__ import annotations

import pytest

from packages.claim_engine.extractor import extract_events
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(text: str) -> NormalizedDocument:
    block = Block(block_id="b1", text=text, page=1, visible=True,
                  source_layer="visible_text", block_type="paragraph")
    return NormalizedDocument(document_id="d1", filename="doc.pdf",
                              mime_type="application/pdf", sha256="0" * 64,
                              pages=[Page(page_number=1, blocks=[block], width=595.0, height=842.0)])


# 양성: 법령·판례를 근거로 들더라도 당사자가 행위한 날짜는 사건으로 남는다
_KEEP = [
    ("원고 박성민은 2024. 5. 10. 민법 제750조에 따라 배상을 청구하였다.", "청구"),
    ("피고는 2024. 6. 1.부터 약정 이자의 지급을 지체하였다.", "지체"),
    ("원고는 2024. 7. 15. 민법 제548조에 따라 원상회복 의무를 이행하였다.", "이행"),
    ("피고는 2024. 8. 20. 보증금의 반환을 거절하였고 원고는 반환을 요구하였다.", "반환"),
    ("원고는 2024. 9. 5. 상당한 기간을 정하여 이행을 최고하였다.", "최고"),
    ("원고는 2024. 10. 2. 내용증명으로 변제를 독촉하였다.", "독촉"),
    ("피고는 2024. 11. 8. 변제 목적물을 공탁하였다.", "공탁"),
]


@pytest.mark.parametrize("text, verb", _KEEP)
def test_party_act_date_is_kept_as_event(text, verb):
    events = extract_events(_doc(text))
    assert events, f"당사자 행위 '{verb}' 문장의 사실 날짜가 탈락했다: {text}"


# 대조: 판단 주체가 법원·입법인 날짜는 그대로 제외된다
_DROP = [
    "대법원 2021. 5. 13. 선고 2020다12345 판결의 법리에 따르면 손해배상책임이 인정된다.",
    "헌법재판소 2019. 7. 18. 선고 2018헌마100 결정은 같은 취지이다.",
    "민법 제750조는 1958. 2. 22. 제정되어 1960. 1. 1. 시행되었다.",
    "서울고등법원 2022. 3. 4. 선고 2021나5678 판결은 이행 지체를 인정하였다.",
]


@pytest.mark.parametrize("text", _DROP)
def test_adjudication_and_statute_dates_still_excluded(text):
    events = extract_events(_doc(text))
    assert events == [], f"법적 근거 날짜가 사건으로 잡혔다: {text}"


def test_added_verbs_do_not_rescue_pure_holding_sentence():
    """추가 동사가 들어 있어도 선고일은 판례 인용 날짜로 계속 걸러진다."""
    text = "대법원 2020. 4. 9. 선고 2019다33333 판결은 반환 청구권의 소멸시효를 판시하였다."
    assert extract_events(_doc(text)) == []
