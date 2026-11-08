"""TK-76 3주기 EVI-OVR 잔여 5꼴(O1~O5) 평가 측 시험 — 공개 합성 문장(평가 측 비공개 탐침 문장 아님).

- O1: 주체 판정은 주격을 소유격보다 먼저 보고, 당사자 뒤 동격 명사 한 어절('피고 회사가')을 받는다.
- O2: '소갑/소을 제N호증' 목록 줄을 이 검사 안에서 보충 행으로 읽는다(공용 exhibit_rows 불변).
- O3: 맨 '이행하였다/이행했다/이행한'도 완료 단정(의문·가정 어미 제외).
- O4: 'X임을/사실을 (…) 알고 있었다/알았다/알면서'는 내심 상태(앎) 단정.
- O5: 전칭 부정('한 번도/한 차례도/전혀 … 적이·일이·바가 없다')은 전 기간 단정.
"""
from __future__ import annotations

import pytest

from packages.claim_engine.evidence_consistency import check_evidence_overreach, exhibit_rows
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(body: str, ev: str) -> NormalizedDocument:
    texts = ["청구원인", body, "입증방법", ev]
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(texts)]
    return NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                              pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])


def _hit(body: str, ev: str) -> bool:
    return any(f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH for f in check_evidence_overreach(_doc(body, ev)))


@pytest.mark.parametrize("body,ev", [
    ("피고 조합이 위 정산안을 승낙하였다는 점은 갑 제1호증 최고서로 증명됩니다.", "1. 갑 제1호증 최고서 (발신인: 원고)"),
    ("피고가 원고의 연장 요청에 동의하였다는 점은 갑 제2호증 안내문으로 증명됩니다.", "1. 갑 제2호증 안내문 (발신인: 원고)"),
    ("피신청인이 위 보증금 반환 일정에 합의하였다는 사실은 소갑 제3호증 내용증명으로 소명됩니다.", "1. 소갑 제3호증 내용증명 (발신인: 신청인)"),
    ("을 제4호증 견적서에 의하면 원고는 위 배관 교체 의무를 이행하였습니다.", "1. 을 제4호증 견적서"),
    ("갑 제5호증 동영상으로 보아 피고는 위 제품이 반품 대상임을 처음부터 알고 있었습니다.", "1. 갑 제5호증 동영상"),
    ("피고는 한 번도 정기 점검을 빠뜨린 적이 없다는 사실이 을 제6호증 통장사본으로 증명됩니다.", "1. 을 제6호증 통장사본"),
])
def test_positive(body, ev):
    assert _hit(body, ev)


@pytest.mark.parametrize("body,ev", [
    ("원고 조합은 갑 제1호증 최고서로 피고에게 정산안을 제시하였습니다.", "1. 갑 제1호증 최고서 (발신인: 원고)"),
    ("피신청인이 위 반환 일정에 합의하였다는 사실은 소을 제3호증 내용증명으로 소명됩니다.", "1. 소을 제3호증 내용증명 (발신인: 피신청인)"),
    ("원고가 위 배관 교체 의무를 이행하였는지는 을 제4호증 견적서만으로 알 수 없습니다.", "1. 을 제4호증 견적서"),
    ("갑 제5호증 동영상만으로는 피고가 반품 대상임을 알았는지 확인할 수 없습니다.", "1. 갑 제5호증 동영상"),
    ("피고가 정기 점검을 빠뜨린 적이 한 번도 없다는 점은 원고도 다투지 않습니다.", "1. 을 제6호증 통장사본"),
    ("갑 제7호증 영수증에 의하면 피고는 2025. 3. 4. 원고에게 잔금 1,500,000원을 지급하였습니다.", "1. 갑 제7호증 영수증 (금 1,500,000원)"),
])
def test_negative(body, ev):
    assert not _hit(body, ev)


def test_shared_exhibit_rows_unchanged_for_so_lines():
    # O2는 공용 입력을 바꾸지 않는다: exhibit_rows는 '소갑' 목록 줄을 여전히 행으로 만들지 않는다
    assert exhibit_rows(_doc("본문", "1. 소갑 제3호증 내용증명 (발신인: 신청인)")) == []


def test_variations_o1_to_o5_word_order_connectives_and_question_negation_controls():
    """2-2 다 변형 시험: 어순·연결 어미·같은 꼴 다른 낱말 및 O3·O4 의문·부정 대조."""
    positive_variations = [
        # O1 변형: 동격 주체 다른 낱말('피고 회사는') + 소유격('원고의') + 어순(호증 선행)
        ("갑 제1호증 통고서에 비추어 볼 때 피고 회사는 원고의 납기 변경 요청을 수락하였습니다.", "1. 갑 제1호증 통고서 (발신인: 원고)"),
        # O2 변형: '소갑' 불릿 목록 줄 + 다른 의사표시('승인하였다')
        ("소갑 제2호증 독촉장에 의하면 피신청인은 위 지체상금 감면에 승인하였다고 할 것입니다.", "- 소갑 제2호증 독촉장 (발신인: 신청인)"),
        # O3 변형: '이행했다' 축약 어미 + 어순(주장 선행·호증 후행)
        ("원고가 위 하자보수 약정을 이행했다는 점은 을 제3호증 요청서로 입증됩니다.", "1. 을 제3호증 요청서"),
        # O4 변형: '사실을 … 알면서' 연결 어미 + 다른 서증('사진')
        ("갑 제4호증 현장사진을 보면 피고는 위 구조물에 균열이 발생하였다는 사실을 당초부터 알면서 방치하였습니다.", "1. 갑 제4호증 현장사진"),
        # O5 변형: '전혀 … 바가 없다' + 어순 변형
        ("을 제5호증 거래내역서에 의하면 피고는 전혀 안전교육을 누락한 바가 없습니다.", "1. 을 제5호증 거래내역서"),
    ]
    for body, ev in positive_variations:
        assert _hit(body, ev), body

    control_variations = [
        # O3 의문·가정 대조('이행했는지', '이행하였다면')
        ("원고가 위 하자보수 약정을 이행했는지는 을 제3호증 요청서만으로 단정하기 어렵습니다.", "1. 을 제3호증 요청서"),
        ("설령 원고가 위 의무를 이행하였다면 을 제3호증 요청서가 발송되었을 리 없습니다.", "1. 을 제3호증 요청서"),
        # O4 의문·부정 대조('알고 있었는지', '알지 못하였다')
        ("갑 제4호증 현장사진만으로는 피고가 균열 사실을 알고 있었는지 단정할 수 없습니다.", "1. 갑 제4호증 현장사진"),
    ]
    for body, ev in control_variations:
        assert not _hit(body, ev), body

