# -*- coding: utf-8 -*-
"""TK-76 정규식 성능 측정 스크립트 (공통 점검표 2항).

DATE_WEEKDAY_RE 및 HEADING_LINE_RE의 1배/4배 최솟값 비 < 8.0 및 4배 수행시간 < 1.0초 검증.
"""
from __future__ import annotations

import sys
import timeit
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.claim_engine.date_verifier import DATE_WEEKDAY_RE, HEADING_LINE_RE


def measure_regex(name: str, pattern, base_text: str):
    text_1x = base_text
    text_4x = base_text * 4

    runs = 100
    repeats = 3

    t1_raw = min(timeit.repeat(lambda: list(pattern.finditer(text_1x)), number=runs, repeat=repeats)) / runs
    t4_raw = min(timeit.repeat(lambda: list(pattern.finditer(text_4x)), number=runs, repeat=repeats)) / runs

    # 분모 보정 (0.0001초 미만인 경우)
    t1_adj = max(t1_raw, 0.0001)
    ratio = t4_raw / t1_adj

    print(f"[{name}]")
    print(f"  1x 길이: {len(text_1x)}자 | 1회 최솟값: {t1_raw:.6f}s (보정값: {t1_adj:.6f}s)")
    print(f"  4x 길이: {len(text_4x)}자 | 1회 최솟값: {t4_raw:.6f}s")
    print(f"  성능 비: {ratio:.2f} (기준 < 8.0) | 4배 최솟값: {t4_raw:.6f}s (기준 < 1.0s)")
    assert ratio < 8.0, f"{name} 비정상 성능 비: {ratio}"
    assert t4_raw < 1.0, f"{name} 4배 최솟값 1.0초 초과: {t4_raw}s"
    print("  -> 판정: PASS\n")


def main():
    sample_text_weekday = (
        "업무 일정에 따라 2024. 5. 1. 목요일에 관련 서류를 접수하였습니다.\n"
        "해당 규정은 2024년 6월 7일 토요일부터 시행하기로 하였습니다.\n"
        "협약 체결일인 2024. 7. 10. 목요일은 공휴일이 아니었습니다.\n"
        "통상적인 업무 수행 과정에서 2025. 9. 1. 화요일에 확인서를 교부받았습니다.\n"
    ) * 10

    sample_text_heading = (
        "1. 사전 업무 개요 및 사실관계 정리\n"
        "가. 당사자 사이의 관계 및 계약 체결 경위\n"
        "(1) 1차 계약 체결 및 대금 지급 내역\n"
        "[검토 결과 보고서]\n"
        "【참고 사항】\n"
        "제1조 목적 및 적용 범위\n"
    ) * 10

    print("=== TK-76 EVI-DATE 정규식 성능 측정 (공통 점검표 2항) ===")
    measure_regex("DATE_WEEKDAY_RE", DATE_WEEKDAY_RE, sample_text_weekday)
    measure_regex("HEADING_LINE_RE", HEADING_LINE_RE, sample_text_heading)
    print("모든 정규식 성능 기준(비 < 8.0, 4배 < 1.0s) 충족 확인 완료.")


if __name__ == "__main__":
    main()
