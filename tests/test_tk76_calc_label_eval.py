"""TK-76 3주기 EVI-INCONS 산식 후속 — 결과 이름표·달력 시점 이름표 평가 측 시험(공개 합성 문장, 평가 측 비공개 탐침 문장 아님).

- Q1: 연산 서술어 뒤 결과 이름표의 '고'로 끝나는 명사('출고·입고·신고·광고·재고·원고')를 연결 어미 '-고'로 읽지 않는다.
- Q2: 연산 서술어 뒤, 결과 앞의 수('2분기 처리 건수는'의 '2분기')는 피연산자가 아니다.
- Q3: 달력 시점('N월'·'N분기'·'N반기')은 이름표다. 'N개월'은 기간의 양이라 해당 없음.
"""
from __future__ import annotations

import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _hits(text: str):
    block = Block(block_id="b1", text=text, page=1, visible=True, source_layer="visible_text")
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                             pages=[Page(page_number=1, blocks=[block], width=595.0, height=842.0)])
    return [f for f in CalculationEngine().verify_document(doc) if f.type == FindingType.ARITHMETIC_MISMATCH]


@pytest.mark.parametrize("text", [
    # Q1
    "북문 반입 63대와 남문 반입 71대를 더하면 금일 입고 대수는 124대이다.",
    "견적 1,200,000원과 추가 견적 450,000원을 합하면 광고 집행 금액은 1,750,000원이다.",
    "가지점 18명과 나지점 23명을 합하면 원고 소속 인원은 31명이다.",
    # Q2
    "접수 140건과 이관 95건을 합하면 2분기 처리 건수는 245건이다.",
    # Q3
    "3월 판매 410개와 4월 판매 385개를 합하면 785개이다.",
    "1분기 수주 26건과 2분기 수주 31건을 더하면 47건이다.",
])
def test_positive(text):
    assert len(_hits(text)) == 1


@pytest.mark.parametrize("text", [
    # 맞게 계산한 문장
    "북문 반입 63대와 남문 반입 71대를 더하면 금일 입고 대수는 134대이다.",
    "접수 140건과 이관 95건을 합하면 2분기 처리 건수는 235건이다.",
    "3월 판매 410개와 4월 판매 385개를 합하면 795개이다.",
    # 연결 어미·쉼표 절 경계는 그대로
    "북문 반입 63대와 남문 반입 71대를 더하였고 남은 대수는 50대이다.",
    "견적 1,200,000원과 추가 견적 450,000원을 합하면, 별도로 청구한 광고 비용은 900,000원이다.",
    # 'N개월'은 기간의 양(이름표 아님) — 기존 곱셈 산식 그대로
    "월 250,000원씩 4개월이면 1,000,000원이다.",
])
def test_negative(text):
    assert _hits(text) == []


def test_variations_amount_and_quantity_word_order_connectives_and_lexicon():
    """2-2 다 변형 시험: 어순·연결 어미·같은 꼴 다른 낱말(금액·수량 각각)."""
    positive_variations = [
        # 수량 변형 1: Q1 다른 '고' 명사('재고') + Q3 달력 시점('1반기·2반기') + 다른 연산 서술어('합산하면')
        "1반기 반출 45상자와 2반기 반출 38상자를 합산하면 창고 재고 수량은 73상자이다.",
        # 수량 변형 2: Q1 다른 '고' 명사('신고') + Q2 결과 이름표 내 숫자('1분기') + 뺄셈('빼면')
        "배정 210건에서 취소 35건을 빼면 1분기 신고 건수는 165건이다.",
        # 수량 변형 3: Q3 달력 시점('5월·6월') + 어순·표기 변형('총 출고 물량은')
        "5월 납품 120포대와 6월 납품 150포대를 더하면 총 출고 물량은 260포대이다.",
        # 금액 변형 1: Q1 다른 '고' 명사('피고') + Q3 달력 시점('7월·8월')
        "7월 정산금 3,400,000원과 8월 정산금 2,100,000원을 더하면 피고 부담 액수는 5,400,000원이다.",
        # 금액 변형 2: Q2 결과 이름표 내 달력 시점('3분기') + Q1 다른 '고' 명사('출고')
        "본사 청구 1,500,000원과 지사 청구 800,000원을 합하면 3분기 출고 대금은 2,400,000원이다.",
        # 금액 변형 3: Q3 달력 시점('1반기·2반기') + 뺄셈('공제하면')
        "1반기 매출 9,000,000원에서 2반기 반품 1,500,000원을 빼면 신고 금액은 7,200,000원이다.",
    ]
    for s in positive_variations:
        assert len(_hits(s)) == 1, s

    control_variations = [
        # 수량 대조: 용언 연결 어미('-더하고', '-합산했으나') 절 경계
        "1반기 반출 45상자와 2반기 반출 38상자를 더하고, 창고 재고 수량은 20상자이다.",
        "5월 납품 120포대와 6월 납품 150포대를 합산했으나 재고 물량은 50포대이다.",
        # 금액 대조: 정산 일치 + 중위 산식('곱하기') 보존
        "7월 정산금 3,400,000원과 8월 정산금 2,100,000원을 더하면 피고 부담 액수는 5,500,000원이다.",
        "단가 8 곱하기 26,000은 208,000이다.",
    ]
    for s in control_variations:
        assert _hits(s) == [], s

