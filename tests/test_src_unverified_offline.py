"""SRC-UNV 오프라인 외부 출처(간행물·보고서·통계) UNVERIFIED 식별 검증 시험.

실제 진입점(LegalVerifier), 양성 3건, 대조군 3건, 정규식 성능비 검증 포함.
사건 고유 리터럴 하드코딩 금지 규칙 준수.
"""
from __future__ import annotations

import time
import pytest

from packages.common.enums import CitationType, FindingType, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.citation_extractor import (
    REPORT_CITATION_RE,
    INDICATOR_STAT_RE,
    extract_from_text,
)
from packages.legal_engine.verifier import LegalVerifier


# --- 1. 실제 진입점 시험 (LegalVerifier.verify_citations) ---
def test_src_unverified_entrypoint():
    """실제 진입점 LegalVerifier를 통해 외부 간행물/보고서 인용이 UNVERIFIED로 판정되는지 검증."""
    sample_text = (
        "원고는 한국물류정책학회의 「2024 물류운송 통계연보」 52쪽을 근거로 제시하나, "
        "해당 보고서의 원문 및 기초 통계는 확인할 수 없습니다."
    )
    citations = extract_from_text(sample_text)
    assert len(citations) >= 1, "인용이 추출되어야 한다"
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) >= 1, "ACADEMIC 인용으로 분류되어야 한다"

    verifier = LegalVerifier()
    result = verifier.verify_citations(academic_cits)
    assert len(result.findings) >= 1, "finding이 방출되어야 한다"
    finding = result.findings[0]
    assert finding.type == FindingType.ACADEMIC_CITATION_ERROR
    assert finding.status == VerificationStatus.UNVERIFIED
    assert "2024 물류운송 통계연보" in finding.title or "2024 물류운송 통계연보" in finding.detail or (finding.evidence and any("2024 물류운송 통계연보" in e.excerpt for e in finding.evidence))


# --- 2. 양성 예시 3건 (각기 다른 문헌 및 통계 수치) ---
@pytest.mark.parametrize(
    "text,expected_title,expected_token",
    [
        (
            "자료조사위원회의 「2025 유통환경 실태백서」 미공개 요약에 따르면 반품률은 68.5%에 이릅니다.",
            "2025 유통환경 실태백서",
            "68.5%",
        ),
        (
            "사단법인 복지조사센터의 「2023 근로환경 실태조사」 85쪽에는 평균 근속기간이 기재되어 있습니다.",
            "2023 근로환경 실태조사",
            "85쪽",
        ),
        (
            "통합데이터포럼의 「2024 시스템 안정성 연보」에 따르면 장애 복구율은 91.2%입니다.",
            "2024 시스템 안정성 연보",
            "91.2%",
        ),
    ],
)
def test_src_unverified_positive_cases(text: str, expected_title: str, expected_token: str):
    """양성 예시 3건: 백서/실태조사/연보 등 다양한 간행물 및 수치 표출 검증."""
    citations = extract_from_text(text)
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) >= 1, f"'{expected_title}' 인용이 추출되어야 함"
    cit = academic_cits[0]
    assert expected_title in cit.title or expected_title in cit.raw_text
    assert expected_token in cit.context

    verifier = LegalVerifier()
    result = verifier.verify_citations([cit])
    assert len(result.findings) >= 1
    f = result.findings[0]
    assert f.type == FindingType.ACADEMIC_CITATION_ERROR
    assert f.status == VerificationStatus.UNVERIFIED
    # evidence excerpt에 수치/쪽수 토큰이 보존되었는지 확인
    assert any(expected_token in e.excerpt for e in f.evidence)


# --- 3. 대조군 3건 (인용이 아니거나 법률 조문/일반 문장) ---
@pytest.mark.parametrize(
    "control_text",
    [
        "원고는 피고에게 계약서 제3조에 따라 대금을 청구하였으나 피고는 이를 거절하였습니다.",
        "민법 제750조에 따른 불법행위 손해배상 책임을 묻고자 합니다.",
        "피고는 매월 약 50%의 확률로 기기 결함이 발생할 수 있다고 구두로만 설명하였습니다.",
    ],
)
def test_src_unverified_control_cases(control_text: str):
    """대조군 3건: 일반 서면 문장, 법률 조항, 단순 일상 수치 표현에서 허위 보고서 인용이 발생하지 않아야 함."""
    citations = extract_from_text(control_text)
    # 일반 보고서/간행물 인용(REPORT_CITATION_RE)으로 인한 ACADEMIC 인용이 없어야 함
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) == 0, f"대조군에서 ACADEMIC 인용이 오탐되지 않아야 함: {control_text}"


# --- 4. 정규식 성능비 검증 (1배 vs 4배 < 8비, 4배 최솟값 < 1초) ---
def test_report_citation_regex_performance():
    """REPORT_CITATION_RE 정규식의 선형 복잡도 검증."""
    import gc
    base_text = (
        "원고는 여러 서증을 제출하며 주장을 이어갔습니다. "
        "한편 자료조사위원회의 「2025 유통환경 실태백서」 미공개 요약에 따르면 반품률은 68.5%에 이릅니다. "
        "피고는 이러한 조사의 신빙성을 다투고 있습니다. "
    )
    text_1x = base_text * 10
    text_4x = base_text * 40

    times_1x = []
    times_4x = []
    gc_was_enabled = gc.isenabled()
    try:
        gc.disable()
        for _ in range(3):
            t0 = time.perf_counter()
            list(REPORT_CITATION_RE.finditer(text_1x))
            times_1x.append(time.perf_counter() - t0)

        for _ in range(3):
            t0 = time.perf_counter()
            list(REPORT_CITATION_RE.finditer(text_4x))
            times_4x.append(time.perf_counter() - t0)
    finally:
        if gc_was_enabled:
            gc.enable()

    min_1x = max(min(times_1x), 0.0001)
    min_4x = min(times_4x)
    ratio = min_4x / min_1x

    assert min_4x < 1.0, f"4배 입력 처리시간 1초 미만이어야 함: {min_4x:.6f}s"
    assert ratio < 8.0, f"1배 대비 4배 처리시간 비 8배 미만이어야 함: {ratio:.2f}배 (1x: {min_1x:.6f}s, 4x: {min_4x:.6f}s)"


def test_indicator_stat_regex_performance():
    """INDICATOR_STAT_RE 정규식의 선형 복잡도 검증."""
    import gc
    base_text = (
        "물가 및 거래 동향에 따르면 납품지수 94.73 및 정확도 99.8%를 기록하였습니다. "
        "피고는 손상률 12.5%에 대한 추가 조사를 요구합니다. "
    )
    text_1x = base_text * 10
    text_4x = base_text * 40

    times_1x = []
    times_4x = []
    gc_was_enabled = gc.isenabled()
    try:
        gc.disable()
        for _ in range(3):
            t0 = time.perf_counter()
            list(INDICATOR_STAT_RE.finditer(text_1x))
            times_1x.append(time.perf_counter() - t0)

        for _ in range(3):
            t0 = time.perf_counter()
            list(INDICATOR_STAT_RE.finditer(text_4x))
            times_4x.append(time.perf_counter() - t0)
    finally:
        if gc_was_enabled:
            gc.enable()

    min_1x = max(min(times_1x), 0.0001)
    min_4x = min(times_4x)
    ratio = min_4x / min_1x

    assert min_4x < 1.0, f"4배 입력 처리시간 1초 미만이어야 함: {min_4x:.6f}s"
    assert ratio < 8.0, f"1배 대비 4배 처리시간 비 8배 미만이어야 함: {ratio:.2f}배 (1x: {min_1x:.6f}s, 4x: {min_4x:.6f}s)"

