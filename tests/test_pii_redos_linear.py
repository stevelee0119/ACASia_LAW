# -*- coding: utf-8 -*-
"""개인정보 탐지 정규식의 ReDoS(겹치는 공백 반복) 회귀 시험 (2026-10-25 평가 측, #183 CodeQL py/polynomial-redos).

TK-128의 가림 API(`POST /projects/{id}/external-ai/prompt-texts`)와 TK-129 보고서 요청이 사용자 입력을
그대로 `detect()`에 넘긴다. 고치기 전에는 라벨 뒤 공백 200자에 9~13초, '처방' 뒤 공백 2,000자에 48초가 걸렸다.
절대 시간은 실행기 부하에 흔들리므로 길이 4배의 시간 비(선형이면 약 4, 제곱이면 약 16)와 넉넉한 상한을 함께 본다.
"""
from __future__ import annotations

import gc
from time import perf_counter

import pytest

from packages.pii_engine.detector import detect

LABELS = ["", "사업자번호", "계좌번호", "주민등록번호", "법인등록번호", "군번", "생년월일",
          "2020년 3월 2", "처방", "복용약", "진단", "의뢰인 홍길동 상병"]


def _best(text: str) -> float:
    best = float("inf")
    gc.collect()
    gc.disable()
    try:
        for _ in range(3):
            started = perf_counter()
            detect(text)
            best = min(best, perf_counter() - started)
    finally:
        gc.enable()
    return best


@pytest.mark.parametrize("label", LABELS)
def test_label_followed_by_long_whitespace_is_linear(label):
    short, long = _best(label + " " * 2000), _best(label + " " * 8000)
    assert long < 2.0, (label, long)
    assert long / max(short, 1e-3) < 8, (label, short, long)


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
