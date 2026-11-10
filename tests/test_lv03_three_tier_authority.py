"""LV-03: 판례·법령 존재 및 서지 판정의 3단 체계화 단위 시험 (Public Synthetic Tests).

규칙 요구사항:
- 양성 예시 3건 (대법원 부존재 확인 CONFIRMED_NONEXISTENT, 하급심 출처 한계 UNCONFIRMED_SOURCE_LIMIT, 성립불가 오기의심 SUSPICIOUS)
- 대조군 3건 (공식 DB 존재 확인 VERIFIED, HallucinationTableRow 직렬화 정합성, 기존 _basis_for 하위 호환성)
- 사건 고유 리터럴 미사용 (합성 사건번호 및 일반 법리 문장)
"""
from __future__ import annotations

from packages.common.enums import CitationType, EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Citation, NormalizedDocument, Page, Block
from packages.legal_engine.authority_status import (
    LegalVerificationStatus,
    classify_authority_status,
    get_court_tier,
    is_covered_precedent_scope,
    make_authority_id,
)
from packages.legal_engine.argument_validity_verifier import (
    HallucinationTableRow,
    _basis_for,
    _fabrication_row,
)


def _make_citation(raw_text: str, case_no: str, court: str = "", c_type: CitationType = CitationType.CASE) -> Citation:
    return Citation(
        citation_id="cit_test_1",
        type=c_type,
        raw_text=raw_text,
        court=court,
        case_number=case_no,
        canonical_case_number=case_no,
        page=1,
    )


def test_lv03_positive_supreme_court_confirmed_nonexistent():
    """양성 1: 대법원 판례라도 공식 DB 미발견만으로 부존재를 단정하지 않고 출처 한계로 분류 (UNCONFIRMED_SOURCE_LIMIT, MEDIUM)."""
    raw = "대법원 2021다88888 판결"
    c = _make_citation(raw, "2021다88888", court="대법원")
    assert get_court_tier(c) == "SUPREME"
    assert not is_covered_precedent_scope(c)
    # attestation이 명시된 경우에만 전수 수록 보장 인정
    c_attested = _make_citation(raw, "2021다88888", court="대법원")
    c_attested.attributes = {
        "coverage_attestation": {
            "exhaustive": True,
            "verified_adapter": True,
            "source": "scourt",
            "scope": "supreme_court",
            "checked_at": "2026-11-10",
        }
    }
    assert is_covered_precedent_scope(c_attested) is True

    # 공식 DB 미검색 (official_record=None, 형식 유효)
    info = classify_authority_status(c, official_record=None, format_valid=True)
    assert info["status"] == LegalVerificationStatus.UNCONFIRMED_SOURCE_LIMIT
    assert info["severity"] == Severity.MEDIUM
    assert info["tier"] == "SUPREME"
    assert info["authority_id"] == "KR_SC_2021다88888"
    assert "조회 범위 내에서 찾지 못한" in info["title"]


def test_lv03_positive_lower_court_unconfirmed_source_limit():
    """양성 2: 하급심 판결은 법원명을 포함한 식별자와 함께 출처 한계로 분류 (UNCONFIRMED_SOURCE_LIMIT, MEDIUM)."""
    raw = "서울고등법원 2020나55555 판결"
    c = _make_citation(raw, "2020나55555", court="서울고등법원")
    assert get_court_tier(c) == "LOWER"
    assert is_covered_precedent_scope(c) is False

    info = classify_authority_status(c, official_record=None, format_valid=True)
    assert info["status"] == LegalVerificationStatus.UNCONFIRMED_SOURCE_LIMIT
    assert info["severity"] == Severity.MEDIUM
    assert info["tier"] == "LOWER"
    assert info["authority_id"] == "KR_LOWER_서울고등법원_2020나55555"
    assert "조회 범위 내에서 찾지 못한" in info["title"]
    assert "존재하지 않는 판례'라고 단정하지 않습니다" in info["reason"]


def test_lv03_positive_impossible_case_number_suspicious():
    """양성 3: 성립 불가능한 연도 또는 사건부호는 오기 의심 (SUSPICIOUS, HIGH)."""
    raw = "대법원 2099다11111 판결"
    c = _make_citation(raw, "2099다11111", court="대법원")

    # format_valid=False (미래 연도)
    info = classify_authority_status(c, official_record=None, format_valid=False)
    assert info["status"] == LegalVerificationStatus.SUSPICIOUS
    assert info["severity"] == Severity.HIGH
    assert info["authority_id"] == "KR_SC_2099다11111"
    assert "오기 의심" in info["title"]


def test_lv03_contrast_official_confirmed_verified():
    """대조군 1: 공식 DB에 존재하는 판례는 존재 확인 (VERIFIED, INFO)."""
    raw = "대법원 2020다12345 판결"
    c = _make_citation(raw, "2020다12345", court="대법원")
    mock_official = {"case_number": "2020다12345", "court": "대법원", "full_text": "판결 전문..."}

    info = classify_authority_status(c, official_record=mock_official, format_valid=True)
    assert info["status"] == LegalVerificationStatus.VERIFIED
    assert info["authority_id"] == "KR_SC_2020다12345"
    assert "일치 확인" in info["title"]


def test_lv03_contrast_hallucination_table_row_contract():
    """대조군 2: HallucinationTableRow에서 authority_id와 verification_status 직렬화 정합성."""
    row = HallucinationTableRow(
        location="1면",
        claim_text="피고는 부당이득 반환 의무가 있습니다.",
        cited_authority="대법원 2021다88888 판결",
        authority_exists=False,
        ai_generation_basis="대법원 판례 DB 부존재",
        validity_verdict="대법원 판례 부존재 (가짜 판례 의심)",
        legal_reasoning="대법원 공식 DB에서 확인되지 않는 판례입니다.",
        recommended_counteraction="원문 사본 확인 요청",
        basis="CONFIRMED_NONEXISTENT",
        authority_id="KR_SC_2021다88888",
        verification_status=LegalVerificationStatus.CONFIRMED_NONEXISTENT.value,
        evaluation_context="피고는 부당이득 반환 의무가 있습니다.",
    )
    d = row.to_dict()
    assert d["authority_id"] == "KR_SC_2021다88888"
    assert d["verification_status"] == "CONFIRMED_NONEXISTENT"
    assert d["basis"] == "CONFIRMED_NONEXISTENT"
    assert d["validity_verdict"] == "대법원 판례 부존재 (가짜 판례 의심)"


def test_lv03_contrast_backwards_compatibility_basis_for():
    """대조군 3: 기존 _basis_for 함수의 하위 호환성 유지 검증."""
    class _MockCitation:
        def __init__(self, num: str):
            self.case_number = num
            self.canonical_case_number = num

    # 1. 일반 미확인 -> UNCONFIRMED
    assert _basis_for(_MockCitation("2020다12345"), "NOT_FOUND") == "UNCONFIRMED"
    # 2. 내용 불일치 -> CONTENT_MISMATCH
    assert _basis_for(_MockCitation("2020다12345"), "CONTRADICTED") == "CONTENT_MISMATCH"
    # 3. 불가능한 미래 연도 -> FABRICATION_SUSPECTED
    assert _basis_for(_MockCitation("2099다99999"), "NOT_FOUND") == "FABRICATION_SUSPECTED"


import pytest

@pytest.mark.parametrize("court,number", [("대법원", "2021다67283"), ("헌법재판소", "2021헌바672"), ("서울중앙지방법원", "2021가단67283")])
def test_lv03_court_level_does_not_attest_exhaustive_coverage(court: str, number: str):
    c = _make_citation(f"{court} {number} 판결", number, court=court)
    assert not is_covered_precedent_scope(c)

