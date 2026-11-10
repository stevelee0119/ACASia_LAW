"""TK-76 3주기 후속 C 묶음 — 산식 Q4('수+명사' 이름표)·Q5(분배형 곱셈) (평가 측 공개 합성 문장)."""
from __future__ import annotations

import pytest

from packages.claim_engine.calculation import _check_statement_formula


@pytest.mark.parametrize("text", [
    "가동 라인별로 보면 3라인 조립 수량 640개와 4라인 조립 수량 410개를 더하면 1,070개이다.",
    "7동 관리비 1,350,000원과 8동 관리비 1,150,000원을 합하면 2,600,000원이다.",
    "A구역 대신 2구역 면적 120㎡와 5구역 면적 85㎡를 합하면 215㎡이다.",
])
def test_q4_number_noun_label_before_quantity(text):
    r = _check_statement_formula(text)
    assert r is not None and r["stated"] != r["computed"], r


@pytest.mark.parametrize("text", [
    "가동 라인별로 보면 3라인 조립 수량 640개와 4라인 조립 수량 410개를 더하면 1,050개이다.",
    "7동 관리비 1,350,000원과 8동 관리비 1,150,000원을 합하면 2,500,000원이다.",
    "3명 × 70,000원 = 210,000원",
])
def test_q4_control_correct_sum_or_real_operand(text):
    assert _check_statement_formula(text) is None


@pytest.mark.parametrize("text", [
    "협력업체 6곳에 각각 250,000원씩 보내 모두 1,600,000원이다.",
    "참가자 9명에게 1인당 40,000원씩 합계 370,000원을 지급하였다.",
    "근로자 4명 각 65,000원씩 지급하면 합계 270,000원이다.",
])
def test_q5_distributive_multiplication(text):
    r = _check_statement_formula(text)
    assert r is not None and r["stated"] != r["computed"], r


@pytest.mark.parametrize("text", [
    "협력업체 6곳에 각각 250,000원씩 보내 모두 1,500,000원이다.",
    "기본급 2,400,000원과 수당 350,000원씩을 합계 2,750,000원으로 정하였다.",
    "하루 6시간씩 4일 일하면 모두 24시간이다.",
])
def test_q5_control(text):
    assert _check_statement_formula(text) is None
