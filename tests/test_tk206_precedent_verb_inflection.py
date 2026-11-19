"""TK-206 보완: 재판행위 어간 활용형(법원 × 어간 × 활용 3축 조합) 타임라인 배제 및 오적용 보존 시험.

- 제외 축: 법원(4) × 재판행위 어간(5: 선고·판시·설시·판단·결정) × 활용(5: 관형·연결·종결·명사형+조사·의존명사 결합) = 100칸
- 오적용 축(반드시 포함):
  1) 당해 사건 경과(이 사건 원심/제1심/항소심/상고심) 선고·변론종결 날짜
  2) 앞 35자에 법원 표지가 있으나 당사자 사실인 꼴(소장·위임장 제출, 법원 판례 언급 뒤 당사자 행위)
  3) 법령 조문 인용을 동반한 당사자 처분·통지 날짜 (TK-206 1차 보완분)

모든 문장은 합성이고 실제 사건과 무관하다.
"""
from __future__ import annotations

from datetime import date

import pytest

from packages.claim_engine.extractor import extract_events
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(text: str) -> NormalizedDocument:
    block = Block(
        block_id="b1",
        text=text,
        page=1,
        visible=True,
        source_layer="visible_text",
        block_type="paragraph",
    )
    return NormalizedDocument(
        document_id="tk206_inflection_doc",
        filename="synthetic_tk206_verb_inflection.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[block], width=595.0, height=842.0)],
    )


_COURTS = (
    "대법원은",
    "헌법재판소는",
    "서울고등법원은",
    "전원합의체는",
)

_JUDICIAL_VERBS = (
    "선고",
    "판시",
    "설시",
    "판단",
    "결정",
)

_INFLECTIONS = (
    ("관형형", "한 판결에서 관련 법리를 설명하였다."),
    ("연결형", "하면서 같은 기준을 제시하였다."),
    ("종결형", "하였다."),
    ("명사형+조사", "함으로써 판단 기준을 확립하였다."),
    ("의존명사결합", "한 바 있다."),
)


@pytest.mark.parametrize("court", _COURTS)
@pytest.mark.parametrize("verb", _JUDICIAL_VERBS)
@pytest.mark.parametrize("inflection_kind, tail", _INFLECTIONS)
def test_precedent_verb_inflection_matrix_excluded(court: str, verb: str, inflection_kind: str, tail: str):
    """[TK-206 제외 100칸] 법원 × 재판행위 어간 × 활용형 3축 전 조합이 Time-Table에서 제외된다."""
    text = f"{court} 2018. 5. 2. {verb}{tail}"
    events = extract_events(_doc(text))
    assert events == [], f"[{inflection_kind}] 제외 누락: {text}"


@pytest.mark.parametrize(
    "text, expected_date",
    [
        # 1) 당해 사건 경과 (이 사건 원심/제1심/항소심/상고심)
        ("이 사건 원심은 2024. 3. 14. 원고의 청구를 기각하는 판결을 선고하였다.", date(2024, 3, 14)),
        ("이 사건 제1심 법원은 2023. 11. 20. 변론을 종결하였다.", date(2023, 11, 20)),
        ("이 사건 항소심 법원은 2024. 6. 18. 원고의 항소를 기각하는 판결을 선고하였다.", date(2024, 6, 18)),
        ("이 사건 상고심은 2024. 9. 5. 파기환송 판결을 선고하였다.", date(2024, 9, 5)),
        # 2) 앞 35자에 법원 표지가 있으나 당사자 사실인 꼴
        ("원고는 서울중앙지방법원에 2024. 1. 12. 소장을 제출하였다.", date(2024, 1, 12)),
        ("피고는 서울고등법원에 2024. 2. 8. 소송위임장을 접수하였다.", date(2024, 2, 8)),
        ("대법원 법리를 근거로 원고는 2024. 4. 22. 피고에게 계약 해제를 통지하였다.", date(2024, 4, 22)),
        # 3) 법령 조문 인용을 동반한 당사자 처분·통지 날짜 (TK-206 1차 보완분)
        ("피고는 2024. 5. 10. 행정절차법 제21조에 따라 원고에게 영업정지 처분을 하였다.", date(2024, 5, 10)),
        ("원고는 2024. 7. 3. 민법 제544조에 따라 피고에게 이행 최고를 통보하였다.", date(2024, 7, 3)),
        # 4) 어간과 글자가 겹치는 복합명사로 시작하는 당사자 사실 (TK-206 2차 보완분: 선고·판단·결정)
        ("대법원 사건을 참고한 원고는 2024. 8. 12. 선고기일 통지서를 수령하였다.", date(2024, 8, 12)),
        ("대법원 판결을 검토한 피고는 2024. 8. 19. 판단자료 목록을 제출하였다.", date(2024, 8, 19)),
        ("서울고등법원 심리와 관련하여 원고는 2024. 8. 25. 결정문 사본을 교부받았다.", date(2024, 8, 25)),
        # 5) 법원 표지와 날짜 사이에 당사자 주격이 있는 꼴 (법원은 수식어, 행위 주체는 당사자)
        ("대법원 판례를 검토한 원고는 2024. 9. 12. 판단한 내용을 통보하였다.", date(2024, 9, 12)),
        ("헌법재판소 결정을 참고한 원고는 2024. 9. 18. 판단하였고 이후 소를 제기하였다.", date(2024, 9, 18)),
        ("서울고등법원 사건과 별도로 피고는 2024. 9. 24. 결정한 금액을 지급하였다.", date(2024, 9, 24)),
    ],
)
def test_party_facts_and_instant_case_history_preserved(text: str, expected_date: date):
    """[TK-206 오적용 방지] 당해 사건 경과, 법원 표지 인접 당사자 사실, 조문 인용, 복합명사·당사자 주격 꼴은 Time-Table에 보존된다."""
    events = extract_events(_doc(text))
    assert [e.date for e in events] == [expected_date], f"사건 날짜 누락: {text}"


@pytest.mark.parametrize(
    "text",
    [
        # 수식어 없는 법원 이름 (특허법원·군사법원·행정법원)
        "특허법원은 2019. 4. 11. 선고한 판결에서 등록무효 사유를 설시하였다.",
        "군사법원은 2020. 6. 18. 판단하면서 징계 기준을 제시하였다.",
        "행정법원은 2021. 2. 25. 결정하였다.",
        # 날짜 뒤 '자' 표기
        "대법원은 2018. 5. 2.자 결정으로 재항고를 기각하였다.",
        "특허법원은 2022. 10. 7.자 판결에서 같은 취지로 판시하였다.",
    ],
)
def test_unprefixed_courts_and_ja_suffix_excluded(text: str):
    """[TK-206 2차 제외 보완] 수식어 없는 법원 이름과 날짜 뒤 '자' 표기 판례 날짜는 제외된다."""
    events = extract_events(_doc(text))
    assert events == [], f"제외 누락: {text}"
