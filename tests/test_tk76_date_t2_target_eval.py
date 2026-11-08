"""TK-76 3주기 EVI-DATE T2 후속 — 처분 → 통지 대상 맞추기(F1~F3)와 차수 가드 평가 측 시험.

공개 합성 문장만 쓴다(평가 측 비공개 탐침 문장 아님).
- F1: 관형 수식('…에 대한 ○○처분') 대상과 사건 꼬리('처분·의결·통지서')를 떼고 핵심 명사로 비교
- F2: 같은 처분을 다른 꼴('감봉 2개월 징계' ↔ '감봉 징계', '직위해제의결' ↔ '직위해제 통지서')로 적어도 같은 대상
- F3: 통지 절의 목적어로 쓰인 처분 명사('그 ○○처분을 통지')는 처분 사건이 아님
- 차수: '1차'·'2차'처럼 차수가 서로 다르면 다른 대상
- F4: 사건 낱말 없이 날짜만 있는 절('…일 ○○을 검토하여')의 날짜를 같은 문장 다음 절 사건에 넘김('…일자 문서'는 넘기지 않음)
- F5: 처분 사건 낱말에 '결의' 계열 추가
- F6: 통지 쪽 대상이 비거나 사건 낱말뿐('통지서')이면 사건 낱말 바로 앞 명사를 대상으로 씀
"""

from __future__ import annotations

import pytest

from packages.claim_engine.date_verifier import verify_dates_in_document
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(text: str) -> NormalizedDocument:
    block = Block(block_id="b1", text=text, page=1, visible=True, source_layer="visible_text")
    page = Page(page_number=1, blocks=[block], width=595.0, height=842.0)
    return NormalizedDocument(
        document_id="doc-tk76-t2-target",
        filename="doc-tk76-t2-target.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


def _dbn(text: str):
    return [
        f
        for f in verify_dates_in_document(_doc(text))
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("sub_rule") == "DISPOSITION_BEFORE_NOTICE"
    ]


@pytest.mark.parametrize(
    "text",
    [
        # F1·F3: 관형 수식 대상 + 통지 목적어 처분 명사
        "피고는 2024. 6. 20. 감사 결과를 근거로 원고에 대한 과징금부과처분을 결정하였다. "
        "그런데 피고는 2024. 6. 12. 원고에게 그 과징금부과처분을 통지하였다.",
        # F2: 의결 ↔ 통지서
        "학교법인은 2023. 9. 14. 이사회에서 교수 갑에 대한 직위해제의결을 하였는데, "
        "직위해제 통지서는 2023. 9. 5. 갑에게 도달하였다.",
        # F2: 기간 수식 유무
        "회사는 2025. 2. 27. 원고에 대한 감봉 2개월 징계를 결정하였으나, "
        "2025. 2. 18. 원고에게 감봉 징계를 통보하였다.",
        # F4: 날짜만 있는 절 다음 절의 처분
        "피고는 2024. 10. 8. 민원 내용을 검토하여 원고에 대한 사용정지처분을 결정하였다. "
        "그런데 피고는 2024. 10. 2. 원고에게 그 사용정지처분을 통지하였다.",
        # F5: 결의
        "총회는 2024. 5. 30. 원고에 대한 제적 결의를 하였는데, 제적 통지서는 2024. 5. 22. 원고에게 발송되었다.",
        # F6: 주제어 꼴 통지('○○ 취소 통지는')
        "피고는 2024. 2. 16. 원고의 약국개설등록취소를 결정하였으나, 등록 취소 통지는 2024. 2. 9. 원고에게 도달하였다.",
    ],
)
def test_same_disposition_written_differently_is_matched(text: str):
    assert len(_dbn(text)) == 1


@pytest.mark.parametrize(
    "text",
    [
        # 차수가 다르면 다른 처분
        "피고는 2024. 3. 2. 원고에게 1차 경고처분을 통지하였고, 2024. 3. 10. 원고에 대한 2차 경고처분을 결정하였다.",
        # 다른 사람·다른 처분
        "회사는 2025. 5. 20. 직원 을에 대한 견책 징계를 결정하였고, 2025. 5. 12. 직원 병에게 감봉 징계를 통보하였다.",
        # 사전통지
        "피고는 2024. 7. 1. 원고에게 처분 사전통지를 하였고, 2024. 7. 15. 원고에 대한 영업정지처분을 결정하였다.",
        # 정상 순서
        "피고는 2024. 8. 9. 원고에 대한 과태료 부과처분을 결정하고, 2024. 8. 13. 원고에게 그 과태료 부과처분을 통지하였다.",
        # F4 제외: '…일자 문서'의 날짜는 처분일이 아니다
        "피고는 2024. 10. 1.자 감사보고서에 기초하여 원고에 대한 사용정지처분을 결정하였다. "
        "피고는 2024. 9. 30. 원고에게 그 사용정지처분을 통지하였다.",
        # F4 정상 순서
        "피고는 2024. 10. 1. 감사보고서에 기초하여 원고에 대한 사용정지처분을 결정하였다. "
        "피고는 2024. 10. 6. 원고에게 그 사용정지처분을 통지하였다.",
    ],
)
def test_different_or_ordered_dispositions_are_not_flagged(text: str):
    assert _dbn(text) == []


def test_variations_word_order_connectives_and_lexicon():
    """2-2 다 변형 시험: 어순(통지 선행·처분 후행), 연결 어미, 같은 꼴 다른 낱말 변형."""
    positive_variations = [
        # 어순 변형(통지 문장 선행, 처분 문장 후행) + F1·F3 다른 낱말(보조금환수명령)
        "피신청인은 2024년 11월 4일 신청인에게 그 보조금환수명령을 통보하였다. "
        "그러나 피신청인은 2024년 11월 12일에야 현장점검 결과를 바탕으로 신청인에 대한 보조금환수명령을 결정하였다.",
        # 연결 어미 변형('-였는바') + F2 기간 수식 유무 다른 낱말(정직 3개월 처분 ↔ 정직 처분)
        "징계위원회는 2024년 4월 19일 근로자 갑에 대한 정직 3개월 처분을 의결하였는바, "
        "2024년 4월 11일 갑에게 정직 처분을 통지하였다.",
        # F4 연결 어미('-하고서') + F5 결의 + F6 주제어 통지 다른 낱말(회원제명)
        "이사회는 2024. 7. 25. 소명자료를 심의하고서 원고에 대한 회원제명 결의를 하였으나, "
        "회원제명 통보서는 2024. 7. 17. 원고에게 발송되었다.",
    ]
    for s in positive_variations:
        assert len(_dbn(s)) == 1, s

    control_variations = [
        # F4 '…일자 문서' 변형 대조 ('…자 회의록을 참고하여')
        "피신청인은 2024. 11. 15.자 회의록을 참고하여 신청인에 대한 업무정지명령을 결정하였다. "
        "피신청인은 2024. 11. 10. 신청인에게 그 업무정지명령을 통보하였다.",
        # 차수 다른 변형(1차 vs 2차, 어순 반대)
        "회사는 2024. 9. 20. 원고에 대한 1차 감봉처분을 의결하였고, 이에 앞서 2024. 9. 10. 원고에게 2차 감봉처분을 통보하였다.",
    ]
    for s in control_variations:
        assert _dbn(s) == [], s

