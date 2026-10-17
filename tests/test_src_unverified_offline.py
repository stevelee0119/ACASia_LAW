"""SRC-UNV 오프라인 외부 출처(간행물·보고서·통계) UNVERIFIED 식별 검증 시험.

실제 진입점(VerificationPipeline.run 및 LegalVerifier), 양성 3건, 대조군 3건,
서증 제목 오인 방지 대조군 3건, 정규식 성능비 검증 포함.
사건 고유 리터럴 하드코딩 금지 규칙 준수.
"""
from __future__ import annotations

import time
import pytest

from packages.common.config import reset_settings
from packages.common.enums import CitationType, FindingType, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.citation_extractor import (
    REPORT_CITATION_RE,
    INDICATOR_STAT_RE,
    extract_from_text,
)
from packages.legal_engine.verifier import LegalVerifier
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


# --- 1. 실제 진입점 시험 1: LegalVerifier.verify_citations ---
def test_src_unverified_entrypoint():
    """LegalVerifier 단위 진입점을 통해 외부 간행물/보고서 인용이 UNVERIFIED로 판정되는지 검증."""
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
    assert (
        "2024 물류운송 통계연보" in finding.title
        or "2024 물류운송 통계연보" in finding.detail
        or (finding.evidence and any("2024 물류운송 통계연보" in e.excerpt for e in finding.evidence))
    )


# --- 2. 실제 진입점 시험 2: VerificationPipeline.run 전체 파이프라인 ---
def test_pipeline_entrypoint_src_unverified_offline(tmp_path, monkeypatch):
    """실제 파이프라인 진입점(VerificationPipeline.run)을 통한 오프라인 서면의 SRC-UNV 검출 검증.

    오프라인 서면 1건을 실행하여 finding 개수, 유형, 상태, 제목, 발췌를 정확히 단언.
    """
    sample_text = (
        "원고는 피고의 관리 부실을 주장하며 한국물류정책학회의 「2024 물류운송 통계연보」 52쪽을 제출하였습니다.\n"
        "그러나 해당 연보에 따르면 반품률은 12.3%에 불과하여 원고의 주장과 상반됩니다."
    )
    doc_path = tmp_path / "brief_src_unv.txt"
    doc_path.write_text(sample_text, encoding="utf-8")

    with monkeypatch.context() as patch:
        patch.setenv("LV_ALLOW_NETWORK", "0")
        patch.setenv("LV_DATA_DIR", str(tmp_path / "data"))
        reset_settings()
        try:
            pipeline = VerificationPipeline()
            result = pipeline.run(
                "pipeline-src-unv-run",
                ProjectContext("pipeline-src-unv-project"),
                [DocumentInput("brief-doc-1", str(doc_path), doc_path.name)],
            )
        finally:
            reset_settings()

    assert not result.errors
    assert len(result.documents) == 1
    doc_result = result.documents[0]

    # ACADEMIC_CITATION_ERROR / UNVERIFIED finding 필터링
    src_findings = [
        f
        for f in doc_result.findings
        if f.type == FindingType.ACADEMIC_CITATION_ERROR
        and f.status == VerificationStatus.UNVERIFIED
    ]
    assert len(src_findings) == 1, f"SRC-UNV finding이 정확히 1건이어야 함: {len(src_findings)}"
    finding = src_findings[0]
    assert "2024 물류운송 통계연보" in finding.title
    assert len(finding.evidence) >= 1
    assert any("2024 물류운송 통계연보" in e.excerpt for e in finding.evidence)
    # 쪽수 보존 단언
    assert any("52쪽" in e.excerpt for e in finding.evidence)


# --- 3. 양성 예시 3건 (각기 다른 문헌 및 통계 수치) ---
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


# --- 4. 대조군 3건 (인용이 아니거나 법률 조문/일반 문장) ---
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
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) == 0, f"대조군에서 ACADEMIC 인용이 오탐되지 않아야 함: {control_text}"


# --- 5. 서증 제목 오인 방지 대조군 3건 ---
@pytest.mark.parametrize(
    "exhibit_text",
    [
        "갑 제5호증 「감정보고서」에 의하면 피고의 과실이 명백하다.",
        "을 제3호증 「사고조사보고서」 12쪽을 보면 당시 현장 상황이 나와 있다.",
        "원고가 제출한 증거인 「현장 확인 보고서」를 보면 하자가 발생하였다.",
    ],
)
def test_control_exhibit_titles_not_academic(exhibit_text: str):
    """서증 제목 오인 방지 대조군 3건: 호증 표지나 제출/첨부 기재가 선행하는 서증 제목은 외부 학술 인용(ACADEMIC)으로 추출되지 않아야 함."""
    citations = extract_from_text(exhibit_text)
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) == 0, f"서증 제목은 ACADEMIC 인용으로 분류되지 않아야 함: {exhibit_text}"


# --- 5-1. 법령명 오인 방지 대조군 ---
@pytest.mark.parametrize(
    "statute_text",
    [
        "「근로기준법」 조사 결과에 의하면 원고의 청구는 부당합니다.",
        "피고는 「산업안전보건법」 통계에 따른 기준을 준수하였습니다.",
    ],
)
def test_control_statute_names_not_academic(statute_text: str):
    """법령명 오인 방지 대조군: 법령명 따옴표 뒤에 조사나 통계가 오더라도 외부 학술 인용(ACADEMIC)으로 추출되지 않아야 함."""
    citations = extract_from_text(statute_text)
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) == 0, f"법령명은 ACADEMIC 인용으로 분류되지 않아야 함: {statute_text}"


# --- 6. 단독 지표(통계 수치) 추출 및 동일 문장 중복 방지 검증 ---
def test_positive_indicator_statistic_only():
    """따옴표 없는 지표 수치 단독 인용 추출 및 보고서 인용과 동일 문장 시 중복 스킵 검증."""
    # 단독 지표 추출 케이스
    text_stat_only = "최근 발표된 물가 및 거래 동향에 따르면 납품지수 94.73을 기록하였습니다."
    cits_stat = extract_from_text(text_stat_only)
    academic_stats = [c for c in cits_stat if c.type == CitationType.ACADEMIC]
    assert len(academic_stats) == 1, "단독 지표는 ACADEMIC 인용으로 추출되어야 함"
    assert "납품지수 94.73" in academic_stats[0].title or "납품지수 94.73" in academic_stats[0].raw_text

    # 보고서 인용과 동일 문장에 지표가 함께 있는 경우 보고서 인용만 추출되고 지표는 중복 방출되지 않음
    text_combined = "위원회는 「2024 공정거래백서」에서 납품지수 94.73 및 만족도 조사를 발표하였습니다."
    cits_combined = extract_from_text(text_combined)
    academic_combined = [c for c in cits_combined if c.type == CitationType.ACADEMIC]
    assert len(academic_combined) == 1, "동일 문장 보고서와 지표가 있는 경우 중복 생성 없이 1건만 추출되어야 함"
    assert "2024 공정거래백서" in academic_combined[0].title


# --- 7. 조사 분리 및 한정어 수식어 검증 ---
def test_extra_modifier_and_postposition():
    """따옴표 뒤에 조사가 바로 붙은 경우 조사가 제목이나 수식어에 유입되지 않는지 검증."""
    text_with_postposition = "연구팀의 「2024 산업재해통계」의 내용을 살펴보면 재해율이 감소하였습니다."
    citations = extract_from_text(text_with_postposition)
    academic_cits = [c for c in citations if c.type == CitationType.ACADEMIC]
    assert len(academic_cits) == 1
    cit = academic_cits[0]
    assert cit.title == "2024 산업재해통계", f"제목에 조사가 포함되지 않아야 함: {cit.title}"

    # 한정어 수식어가 있는 경우
    text_with_modifier = "연구팀의 「2024 산업재해통계」 비공개 요약에 따르면 재해율이 감소하였습니다."
    cits_mod = extract_from_text(text_with_modifier)
    academic_mod = [c for c in cits_mod if c.type == CitationType.ACADEMIC]
    assert len(academic_mod) == 1
    assert "2024 산업재해통계" in academic_mod[0].title


# --- 8. 정규식 성능비 검증 (1배 vs 4배 < 8비, 4배 최솟값 < 1초) ---
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
