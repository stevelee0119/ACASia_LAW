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


# --- Q6: 단가의 기준이 앞의 개수와 다르면(시간당·매월·1주당, 사이의 다른 수량) 인원 × 단가로 검산하지 않는다 ---
@pytest.mark.parametrize("text", [
    "강사 6명에게 시간당 30,000원씩 합계 1,440,000원을 지급하였다.",
    "임차인 4명에게 매월 200,000원씩 합계 9,600,000원을 반환하였다.",
    "주주 7인에게 1주당 500원씩 배당하여 합계 3,500,000원을 지급하였다.",
    "일용직 5명에게 3일간 일당 120,000원씩 합계 1,800,000원을 지급하였다.",
])
def test_q6_control_other_rate_basis(text):
    assert _check_statement_formula(text) is None


@pytest.mark.parametrize("text", [
    "수급 대상 11가구에 가구당 80,000원씩 지원하여 모두 900,000원을 집행하였다.",
    "직원 6명에게 각 수당 70,000원씩 합계 430,000원을 지급하였다.",
])
def test_q6_matching_basis_or_non_rate_word_still_checked(text):
    r = _check_statement_formula(text)
    assert r is not None and r["stated"] != r["computed"], r
