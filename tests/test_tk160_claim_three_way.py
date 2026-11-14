"""TK-160(B2): 주장 판정 3분류(근거 일치·근거와 모순·근거 부족)와 근거 의무(합성 값)."""
import pytest

from packages.legal_engine.argument_validity_verifier import (CLAIM_VERDICT_LABELS, HallucinationTableRow,
                                                              classify_claim)

OFFICIAL = {"basis_status": "SOURCE_MISMATCHED", "source": {"kind": "OFFICIAL_CASE", "id": "1"},
            "passage": {"start": 0, "end": 5, "text_sha256": "0" * 64}}
NO_PASSAGE = {"basis_status": "SOURCE_MISMATCHED", "source": {"kind": "OFFICIAL_CASE", "id": "1"}, "passage": None}
MATCHED = {"basis_status": "SOURCE_MATCHED", "source": {"kind": "OFFICIAL_CASE", "id": "1"}, "passage": None}
RULE = {"basis_status": "RULE_BASED", "source": {"kind": "DETERMINISTIC_RULE", "rules": ["FMT"]}, "passage": None}
LOOKUP = {"basis_status": "LOOKUP_FAILED", "source": None, "passage": None}


@pytest.mark.parametrize("basis,evidence,quote,expected", [
    ("CONTENT_MISMATCH", OFFICIAL, "", "CONTRADICTED"),          # 원문 구간이 있는 인용 불일치
    ("CONTRADICTION", NO_PASSAGE, "판시 근거 발췌", "CONTRADICTED"),  # 판시 근거 발췌가 있는 취지 왜곡
    ("CONTRADICTION", NO_PASSAGE, "", "INSUFFICIENT"),           # 근거 구간 없는 '모순'은 낮춘다
    ("CONTENT_MISMATCH", LOOKUP, "", "INSUFFICIENT"),            # 원문을 못 찾았다
    ("CONTENT_MISMATCH", RULE, "", "INSUFFICIENT"),              # 형식 규칙 위반
    ("OFFICIAL_CONFIRMED", MATCHED, "", "SUPPORTED"),
    ("OFFICIAL_CONFIRMED", LOOKUP, "", "INSUFFICIENT"),
    ("UNCONFIRMED", MATCHED, "", "INSUFFICIENT"),
    ("DISTINGUISHABLE", MATCHED, "", "INSUFFICIENT"),
    ("FABRICATION_SUSPECTED", RULE, "", "INSUFFICIENT"),
])
def test_classify_claim(basis, evidence, quote, expected):
    verdict, note = classify_claim(basis, evidence, quote)
    assert verdict == expected
    if basis in ("CONTENT_MISMATCH", "CONTRADICTION") and expected == "INSUFFICIENT":
        assert note  # 낮춘 사유를 밝힌다


def test_no_contradicted_without_located_official_evidence():
    for evidence in (NO_PASSAGE, LOOKUP, RULE, {}, None):
        assert classify_claim("CONTENT_MISMATCH", evidence, "")[0] != "CONTRADICTED"


def test_row_dict_carries_three_way_fields_and_keeps_existing_ones():
    row = HallucinationTableRow(location="1면", claim_text="합성 주장", cited_authority="합성 판례", authority_exists=True,
                                ai_generation_basis="", validity_verdict="인용 내용 불일치 (원문 대조 필요)", legal_reasoning="",
                                recommended_counteraction="", basis="CONTENT_MISMATCH", evidence_basis=OFFICIAL)
    data = row.to_dict()
    assert data["claim_verdict"] == "CONTRADICTED" and data["claim_verdict_label"] == CLAIM_VERDICT_LABELS["CONTRADICTED"]
    assert data["claim_evidence"]["passage"]["end"] == 5
    assert data["basis"] == "CONTENT_MISMATCH" and data["validity_verdict"] == "인용 내용 불일치 (원문 대조 필요)"
