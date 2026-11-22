"""TK-233: Korean legal format invariants (CIT-META, LAW-NX) and ClauseNormalizer modality overclaim (LAW-MIS/OVR) tests."""
from __future__ import annotations

from types import SimpleNamespace

from packages.common.enums import CitationType, FindingType
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.legal_engine.citation_extractor import Citation
from packages.legal_engine.citation_format import code_court_family, court_family, format_violations
from packages.legal_engine.claim_review import review_claims
from packages.legal_engine.statute_ranges import check_statute_article_range
from packages.legal_engine.verifier import LegalVerifier


# ---------------------------------------------------------------------------
# Positive tests (>= 3 across all 3 axes)
# ---------------------------------------------------------------------------


def test_tk233_pos1_court_code_and_year_date_invariants():
    """Court-level vs case-code mismatch, admin appeal mismatch, and impossible calendar dates are flagged."""
    # 1. 대법원 with 1심 부호 가합
    c1 = Citation(citation_id="c1", type=CitationType.CASE, raw_text="대법원 2022가합12345 판결", court="대법원", case_number="2022가합12345", canonical_case_number="2022가합12345", decision_date="2023-05-01")
    v1 = format_violations(c1)
    assert any(v["rule_id"] == "FMT.COURT_CODE_MISMATCH" for v in v1)

    # 2. 법원 with 행정심판 부호 행심
    assert court_family("중앙행정심판위원회") == "행정심판"
    assert code_court_family("행심") == "행정심판"
    c2 = Citation(citation_id="c2", type=CitationType.CASE, raw_text="서울지방법원 2023행심999", court="서울지방법원", case_number="2023행심999", canonical_case_number="2023행심999")
    v2 = format_violations(c2)
    assert any(v["rule_id"] == "FMT.COURT_CODE_MISMATCH" for v in v2)

    # 3. 선고일 연도 < 사건번호 연도 & 달력 성립 불가일 (13월 5일)
    c3 = Citation(citation_id="c3", type=CitationType.CASE, raw_text="대법원 2022다11111 2020. 5. 1. 선고", court="대법원", case_number="2022다11111", canonical_case_number="2022다11111", decision_date="2020-05-01")
    assert any(v["rule_id"] == "FMT.DECIDED_BEFORE_FILED" for v in format_violations(c3))

    c4 = Citation(citation_id="c4", type=CitationType.CASE, raw_text="대법원 2022다22222 2023. 13. 5. 선고", court="대법원", case_number="2022다22222", canonical_case_number="2022다22222", decision_date=None)
    assert any(v["rule_id"] == "FMT.DATE_NOT_ON_CALENDAR" for v in format_violations(c4))


def test_tk233_pos2_statute_range_exceeded_detected_deterministically_offline():
    """Core statutes exceeding max article or 제0조 emit LAW_CITATION_ERROR (LAW-NX) offline."""
    assert check_statute_article_range("민법", "1200")["defect_code"] == "LAW-NX"
    assert check_statute_article_range("근로기준법", "150")["defect_code"] == "LAW-NX"

    verifier = LegalVerifier()
    cit = Citation(
        citation_id="s1",
        type=CitationType.STATUTE,
        raw_text="민법 제1500조",
        law_name="민법",
        article="1500",
        document_id="doc1",
        page=1,
    )
    verdict = verifier.verify_statute(cit)
    assert any(f.type == FindingType.LAW_CITATION_ERROR for f in verdict.findings)


def test_tk233_pos3_clause_normalizer_detects_unconditional_legal_overclaim():
    """Unconditional mandatory assertions on multi-factor doctrines without conditions emit OVERCLAIM."""
    doc = NormalizedDocument(
        document_id="doc_tk233_pos",
        filename="brief.txt",
        mime_type="text/plain",
        sha256="tk233pos",
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block(
                        block_id="b1",
                        page=1,
                        text=(
                            "위법성 조각사유는 어떠한 경우에도 무조건 성립한다. "
                            "과실상계는 당사자의 사정과 무관하게 자동으로 적용된다. "
                            "입증책임은 상대방에게 전부 전가된다."
                        ),
                    )
                ],
            )
        ],
    )
    findings = review_claims(doc)
    overclaims = [f for f in findings if f.type == FindingType.OVERCLAIM]
    assert len(overclaims) >= 2


# ---------------------------------------------------------------------------
# Control tests (>= 3)
# ---------------------------------------------------------------------------


def test_tk233_ctrl1_valid_court_code_and_valid_date_pass_cleanly():
    """Valid 대법원 다-code and valid decision date >= filing year produce 0 format violations."""
    c = Citation(
        citation_id="ok1",
        type=CitationType.CASE,
        raw_text="대법원 2021다12345 2023. 4. 10. 선고",
        court="대법원",
        case_number="2021다12345",
        canonical_case_number="2021다12345",
        decision_date="2023-04-10",
    )
    assert format_violations(c) == []


def test_tk233_ctrl2_valid_statute_and_decree_not_flagged_as_law_nx():
    """Valid core statute articles and 시행령 articles are not flagged as LAW-NX."""
    assert check_statute_article_range("민법", "750") is None
    assert check_statute_article_range("근로기준법", "116") is None
    assert check_statute_article_range("민법 시행령", "2000") is None


def test_tk233_ctrl3_conditional_or_permissive_or_attributed_claims_not_flagged():
    """Nuanced claims with conditions, exceptions, permissive modality, or opponent attribution are not overclaims."""
    doc = NormalizedDocument(
        document_id="doc_tk233_ctrl",
        filename="brief_ok.txt",
        mime_type="text/plain",
        sha256="tk233ctrl",
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block(
                        block_id="b1",
                        page=1,
                        text=(
                            "정당한 사유가 인정되는 경우에 한하여 위법성이 조각될 수 있다. "
                            "원칙적으로 과실상계가 가능하나, 다만 예외적인 사정이 있으면 감경할 수 있다. "
                            "원고는 입증책임이 전부 피고에게 있다고 주장한다."
                        ),
                    )
                ],
            )
        ],
    )
    findings = review_claims(doc)
    overclaims = [f for f in findings if f.type == FindingType.OVERCLAIM]
    assert overclaims == []
