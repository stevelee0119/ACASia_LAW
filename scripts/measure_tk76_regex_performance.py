# -*- coding: utf-8 -*-
"""TK-76 정규식 성능 측정 스크립트 (공통 점검표 2항).

DATE_WEEKDAY_RE, HEADING_LINE_RE, LEADING_MULTIPLIER_RE, BRACKET_HEADING_RE,
_JOSA_PREDICATE_RE, REPORT_CITATION_RE, INDICATOR_STAT_RE,
_COMPLETE_DECLARATION_RE, _COUNT_DECLARATION_RE, _CONTINUOUS_KEYWORD_RE 및
EVI-FORM 4대 축 정규식(_EVI_FORM_PLACEHOLDER_RE, _EVI_FORM_UNSUBMITTED_RE,
_EVI_FORM_BLANK_RE, _EVI_FORM_UNIDENTIFIABLE_RE, _EVI_FORM_SEPARATE_MEDIA_RE,
_EVI_FORM_OPPONENT_CHALLENGE_RE)의
1배/4배 최솟값 비 < 8.0 및 4배 수행시간 < 1.0초 검증.
"""
from __future__ import annotations

import sys
import timeit
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.claim_engine.date_verifier import DATE_WEEKDAY_RE, HEADING_LINE_RE
from packages.claim_engine.calculation import LEADING_MULTIPLIER_RE
from packages.claim_engine.korean_amount import BRACKET_HEADING_RE, _JOSA_PREDICATE_RE
from packages.legal_engine.citation_extractor import REPORT_CITATION_RE, INDICATOR_STAT_RE
from packages.claim_engine.evidence_consistency import (
    _COMPLETE_DECLARATION_RE,
    _COUNT_DECLARATION_RE,
    _CONTINUOUS_KEYWORD_RE,
    _NORMAL_FUTURE_SUBMISSION_RE,
    _EVI_FORM_PLACEHOLDER_RE,
    _EVI_FORM_UNSUBMITTED_RE,
    _EVI_FORM_EXHIBIT_UNSUBMITTED_RE,
    _EVI_FORM_BLANK_RE,
    _EVI_FORM_UNIDENTIFIABLE_RE,
    _EVI_FORM_SEPARATE_MEDIA_RE,
    _EVI_FORM_NON_DEFECT_CONTEXT_RE,
    _EVI_FORM_PROCEDURAL_JUSTIFICATION_RE,
    _EVI_FORM_OPPONENT_CHALLENGE_RE,
)


def measure_regex(name: str, pattern, base_text: str):
    import gc
    text_1x = base_text
    text_4x = base_text * 4

    runs = 100
    repeats = 3

    gc_was_enabled = gc.isenabled()
    try:
        gc.disable()
        t1_raw = min(timeit.repeat(lambda: list(pattern.finditer(text_1x)), number=runs, repeat=repeats)) / runs
        t4_raw = min(timeit.repeat(lambda: list(pattern.finditer(text_4x)), number=runs, repeat=repeats)) / runs
    finally:
        if gc_was_enabled:
            gc.enable()

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

    sample_text_incons = (
        "창고정산 1차 14건 × 17,000원 = 269,000원 수량과 단가를 곱한 금액을 적는다.\n"
        "검수대장 2차 15건 * 17,000원 = 286,000원 수량과 단가를 곱한 금액을 적는다.\n"
        "일반적인 사실관계 서술 문장 안에서 3개월 × 1,000,000원의 용역 대금을 청구한다.\n"
    ) * 10

    sample_text_src_unv = (
        "원고는 여러 서증을 제출하며 주장을 이어갔습니다.\n"
        "한편 자료조사위원회의 「2025 유통환경 실태백서」 미공개 요약에 따르면 반품률은 68.5%에 이릅니다.\n"
        "피고는 이러한 조사의 신빙성을 다투고 있습니다.\n"
        "물가 및 거래 동향에 따르면 납품지수 94.73 및 정확도 99.8%를 기록하였습니다.\n"
    ) * 10

    sample_text_evi_num = (
        "원고는 피고의 불법행위에 대하여 다음과 같이 입증합니다.\n"
        "입증방법: 총 5개 서증을 제출합니다. 제출 증거는 모두 5개입니다.\n"
        "위 목록이 제출한 증거의 전부이며 추가 제출 목록은 없습니다.\n"
        "피고는 을 제1호증부터 을 제4호증까지 빠짐없이 연속 제출을 주장합니다.\n"
    ) * 10

    sample_text_evi_form = (
        "원고는 갑 제1호증 계약서 원본은 아직 찾지 못해 내지 못하였습니다.\n"
        "갑 제2호증 확인서 작성자 이름과 도장이 들어가 있지 않습니다.\n"
        "갑 제3호증 통화녹음 원본 음성은 제출하지 않고 요지만 정리하였습니다.\n"
        "갑 제4호증 영수증 금액 칸이 흐려 숫자를 읽기 어렵습니다.\n"
        "갑 제5호증 전산화면 [화면 이미지 준비중] 상태입니다.\n"
        "갑 제6호증 동영상(USB 별도 제출) 형태로 제출합니다.\n"
        "갑 제7호증 감정서는 감정 결과가 나오는 대로 제출 예정입니다.\n"
        "피고가 제출한 을 제1호증은 신빙성이 없어 배척되어야 합니다.\n"
    ) * 10

    print("=== TK-76 정규식 성능 측정 (공통 점검표 2항) ===")
    measure_regex("DATE_WEEKDAY_RE", DATE_WEEKDAY_RE, sample_text_weekday)
    measure_regex("HEADING_LINE_RE", HEADING_LINE_RE, sample_text_heading)
    measure_regex("LEADING_MULTIPLIER_RE", LEADING_MULTIPLIER_RE, sample_text_incons)
    measure_regex("BRACKET_HEADING_RE", BRACKET_HEADING_RE, sample_text_heading)
    measure_regex("_JOSA_PREDICATE_RE", _JOSA_PREDICATE_RE, sample_text_incons)
    measure_regex("REPORT_CITATION_RE", REPORT_CITATION_RE, sample_text_src_unv)
    measure_regex("INDICATOR_STAT_RE", INDICATOR_STAT_RE, sample_text_src_unv)
    measure_regex("_COMPLETE_DECLARATION_RE", _COMPLETE_DECLARATION_RE, sample_text_evi_num)
    measure_regex("_COUNT_DECLARATION_RE", _COUNT_DECLARATION_RE, sample_text_evi_num)
    measure_regex("_CONTINUOUS_KEYWORD_RE", _CONTINUOUS_KEYWORD_RE, sample_text_evi_num)
    measure_regex("_NORMAL_FUTURE_SUBMISSION_RE", _NORMAL_FUTURE_SUBMISSION_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_PLACEHOLDER_RE", _EVI_FORM_PLACEHOLDER_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_UNSUBMITTED_RE", _EVI_FORM_UNSUBMITTED_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_EXHIBIT_UNSUBMITTED_RE", _EVI_FORM_EXHIBIT_UNSUBMITTED_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_BLANK_RE", _EVI_FORM_BLANK_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_UNIDENTIFIABLE_RE", _EVI_FORM_UNIDENTIFIABLE_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_SEPARATE_MEDIA_RE", _EVI_FORM_SEPARATE_MEDIA_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_NON_DEFECT_CONTEXT_RE", _EVI_FORM_NON_DEFECT_CONTEXT_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_PROCEDURAL_JUSTIFICATION_RE", _EVI_FORM_PROCEDURAL_JUSTIFICATION_RE, sample_text_evi_form)
    measure_regex("_EVI_FORM_OPPONENT_CHALLENGE_RE", _EVI_FORM_OPPONENT_CHALLENGE_RE, sample_text_evi_form)
    print("모든 정규식 성능 기준(비 < 8.0, 4배 < 1.0s) 충족 확인 완료.")


if __name__ == "__main__":
    main()
