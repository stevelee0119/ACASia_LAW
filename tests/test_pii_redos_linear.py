# -*- coding: utf-8 -*-
"""개인정보 탐지 정규식의 ReDoS(겹치는 공백 반복) 회귀 시험 (2026-10-25 평가 측, #183 CodeQL py/polynomial-redos).

TK-128의 가림 API(`POST /projects/{id}/external-ai/prompt-texts`)와 TK-129 보고서 요청이 사용자 입력을
그대로 `detect()`에 넘긴다. 고치기 전에는 라벨 뒤 공백 200자에 9~13초, '처방' 뒤 공백 2,000자에 48초가 걸렸다.
절대 시간은 실행기 부하에 흔들리므로 증가 지수(선형 약 1, 제곱 약 2)와 넉넉한 상한을 함께 본다.
TK-142(2026-11-03 사용자 결정): 두 점 비율(2,000자 대 8,000자 < 8)이 CI에서 한 점 잡음으로 흔들려(9.3)
같은 엄격도(지수 < 1.5)를 네 길이·교차 측정·최소자승 기울기로 잰다.
"""
from __future__ import annotations

import gc
import math
from time import perf_counter

import pytest

from packages.pii_engine.detector import detect

LABELS = ["", "사업자번호", "계좌번호", "주민등록번호", "법인등록번호", "군번", "생년월일",
          "2020년 3월 2", "처방", "복용약", "진단", "의뢰인 홍길동 상병"]


SIZES = (2000, 4000, 8000, 16000)
ROUNDS = 5
# 길이 4배에 시간 비 8 = 증가 지수 log(8)/log(4) = 1.5. 선형이면 약 1, 제곱이면 약 2다(TK-142: 같은 엄격도를 두 점 대신 네 점으로 잰다).
MAX_EXPONENT = 1.5


def _timings(func, texts) -> list:
    """길이별 최솟값. 길이를 번갈아 재서(교차 측정) 실행기 부하가 한 길이에만 몰리지 않게 한다."""
    best = [float("inf")] * len(texts)
    gc.collect()
    gc.disable()
    try:
        for _ in range(ROUNDS):
            for i, text in enumerate(texts):
                started = perf_counter()
                func(text)
                best[i] = min(best[i], perf_counter() - started)
    finally:
        gc.enable()
    return best


def _growth_exponent(sizes, timings) -> float:
    """log(시간)-log(길이) 최소자승 기울기. 한 점의 잡음이 비율 하나를 크게 흔드는 것을 막는다."""
    xs = [math.log(n) for n in sizes]
    ys = [math.log(max(t, 1e-6)) for t in timings]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


@pytest.mark.parametrize("label", LABELS)
def test_label_followed_by_long_whitespace_is_linear(label):
    timings = _timings(detect, [label + " " * n for n in SIZES])
    assert timings[SIZES.index(8000)] < 2.0, (label, timings)   # 기존 절대 상한(8,000자 2초) 유지
    exponent = _growth_exponent(SIZES, timings)
    assert exponent < MAX_EXPONENT, (label, round(exponent, 3), timings)


def test_growth_measure_flags_quadratic_work():
    """측정 방법 자체의 시험: 제곱 시간 작업은 지수 1.5를 넘고, 선형 작업은 넘지 않아야 한다."""
    def quadratic(text):
        n = len(text) // 40
        return sum(1 for i in range(n) for _ in range(i))

    def linear(text):
        return sum(1 for _ in range(len(text) * 4))

    sizes = (1000, 2000, 4000, 8000)
    texts = [" " * n for n in sizes]
    assert _growth_exponent(sizes, _timings(quadratic, texts)) > MAX_EXPONENT
    assert _growth_exponent(sizes, _timings(linear, texts)) < MAX_EXPONENT


def test_rewritten_patterns_keep_known_detections():
    # 정규식을 겹침 없는 꼴로 바꿔도 탐지 결과는 같아야 한다(평가 측 비교: 시험 자료 문장 9,722개 차이 0).
    text = ("사업자번호: 123-45-67890 계좌번호 110-123-456789 주민등록번호 900101-1234567 "
            "생년월일: 1990. 1. 1 처방 내역: 타이레놀 500mg 진단 내과에서 당뇨병 치료")
    assert sorted((m.kind, m.text) for m in detect(text)) == [
        ("ACCOUNT", "110-123-456789"), ("BUSINESS_REGISTRATION", "123-45-67890"),
        ("DOB", "생년월일: 1990. 1. 1 "), ("MEDICAL", "당뇨"), ("RRN", "900101-1234567")]
    # 유일한 의도된 차이: 처방 표현 앞 공백은 위치에 넣지 않는다(문구는 같고 가림 범위만 공백 1자 줄어듦).
    [match] = detect("처방 5mg 타이레놀")
    assert (match.kind, match.start, match.end, match.text) == ("MEDICAL", 3, 11, "5mg 타이레놀")
