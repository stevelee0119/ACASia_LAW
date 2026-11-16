"""P1-2 및 P2-1 단위·회귀 테스트.

모든 문장과 개체명은 일반 법률 도메인 기준의 합성 예문으로 작성되었다.
"""
from __future__ import annotations

import asyncio

import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.claim_engine.evidence_consistency import exhibit_rows
from packages.claim_engine.extractor import extract_claims, extract_entities, extract_events
from packages.common.enums import CitationType, ClaimType, EntityType, EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, Citation, NormalizedDocument, Page
from packages.document_engine.meta_sections import is_meta_checklist_table_rows, meta_checklist_block_ids
from packages.legal_engine.argument_validity_verifier import verify_argument_validity
from packages.legal_engine.citation_extractor import extract_citations, extract_from_text
from packages.legal_engine.claim_review import classify_claims, review_claims
from packages.legal_engine.normalize import canonical_law_name, law_name_suffix
from packages.verification_engine.pipeline import VerificationPipeline


def _doc(*texts: str) -> NormalizedDocument:
    blocks = [Block(f"b{i}", t, 1) for i, t in enumerate(texts)]
    return NormalizedDocument("doc-test", "brief.pdf", "application/pdf", "0" * 64,
                              pages=[Page(1, blocks=blocks)])


# ===========================================================================
# P1-2a: 현행 실정법 대조표 오염 차단 & 자동 기준일 승격
# ===========================================================================

def test_p1_2a_verified_statutes_and_admin_rules_excluded_from_hallucination_table():
    """full_text가 없는 공식 법령·행정규칙 VERIFIED/VERIFIED_PROVISION은 대조표에 올리지 않는다."""
    doc = _doc(
        "민법 제750조는 불법행위 손해배상 책임을 정한다.",
        "근로기준법 제36조는 금품 청산을 정한다.",
        "안전관리지침 제5조는 점검 의무를 정한다.",
    )
    c_law = Citation.create(CitationType.STATUTE, "민법 제750조", block_id="b0", page=1, law_name="민법", article="750")
    c_prov = Citation.create(CitationType.STATUTE, "근로기준법 제36조", block_id="b1", page=1, law_name="근로기준법", article="36")
    c_admin = Citation.create(CitationType.ADMIN_RULE, "안전관리지침 제5조", block_id="b2", page=1, law_name="안전관리지침", article="5")

    verdicts = [
        {
            "citation_id": c_law.citation_id,
            "type": "STATUTE",
            "status": "VERIFIED",
            "verification_label": "VERIFIED_PROVISION",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "NOT_ASSERTED", "temporal": "UNVERIFIED"},
            "official_record": {"law_name": "민법", "version_id": "100"},
            "review": {"quote_diff": {"status": "NO_QUOTE"}, "temporal_review_needed": False},
            "findings": [],
        },
        {
            "citation_id": c_prov.citation_id,
            "type": "STATUTE",
            "status": "PARTIALLY_VERIFIED",
            "verification_label": "VERIFIED_PROVISION",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "VERIFIED", "temporal": "UNVERIFIED"},
            "official_record": {"law_name": "근로기준법", "version_id": "200"},
            "review": {"quote_diff": {"status": "EXACT_MATCH"}, "temporal_review_needed": False},
            "findings": [],
        },
        {
            "citation_id": c_admin.citation_id,
            "type": "ADMIN_RULE",
            "status": "VERIFIED",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "NOT_ASSERTED"},
            "official_record": {"rule_name": "안전관리지침"},
            "review": {},
            "findings": [],
        },
    ]

    result = asyncio.run(verify_argument_validity(doc, [c_law, c_prov, c_admin], verdicts, []))
    assert result.rows == []


def test_p1_2a_control_unconfirmed_statute_summary_case_and_modified_statute_keep_rows():
    """미확인 법령, 요약본 판례, 조문 변형 법령 인용은 여전히 대조표에 남는다."""
    doc = _doc(
        "가상특별법 제9조에 따른다.",
        "대법원 2021다12345 판결은 성립을 인정하였다.",
        "상법 제10조는 \"임의로 변경된 문구\"라고 규정한다.",
    )
    c_stat_nf = Citation.create(CitationType.STATUTE, "가상특별법 제9조", block_id="b0", page=1, law_name="가상특별법", article="9")
    c_case_sum = Citation.create(CitationType.CASE, "대법원 2021다12345 판결", block_id="b1", page=1,
                                 court="대법원", case_number="2021다12345", canonical_case_number="2021다12345",
                                 quoted_text="원문 판시 요약")
    c_stat_mod = Citation.create(CitationType.STATUTE, "상법 제10조", block_id="b2", page=1, law_name="상법", article="10",
                                 quoted_text="임의로 변경된 문구")

    verdicts = [
        {
            "citation_id": c_stat_nf.citation_id,
            "type": "STATUTE",
            "status": "NOT_FOUND",
            "levels": {"existence": "NOT_FOUND", "article": "UNVERIFIED", "content": "NOT_ASSERTED"},
            "official_record": None,
            "review": {},
            "findings": [],
        },
        {
            "citation_id": c_case_sum.citation_id,
            "type": "CASE",
            "status": "PARTIALLY_VERIFIED",
            "levels": {"existence": "VERIFIED", "content": "UNVERIFIED"},
            "official_record": {"case_number": "2021다12345", "summary": "요지 있음"},
            "review": {"quote_diff": {"status": "UNVERIFIED"}},
            "findings": [],
        },
        {
            "citation_id": c_stat_mod.citation_id,
            "type": "STATUTE",
            "status": "CONTRADICTED",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "MODIFIED"},
            "official_record": {"law_name": "상법"},
            "review": {"quote_diff": {"status": "MODIFIED_QUOTE", "categories": ["SUBSTITUTION"]}},
            "findings": [],
        },
    ]

    result = asyncio.run(verify_argument_validity(doc, [c_stat_nf, c_case_sum, c_stat_mod], verdicts, []))
    assert len(result.rows) == 3
    by_id = {r.citation_id: r for r in result.rows}
    assert "원문" in by_id[c_stat_nf.citation_id].validity_verdict
    assert by_id[c_case_sum.citation_id].verification_status == "UNCONFIRMED_SOURCE_LIMIT"
    assert by_id[c_stat_mod.citation_id].verification_status == "CONTRADICTED"


def test_p1_2a_promote_inferred_current_statutes_respects_temporal_disputes():
    """자동 추정 기준일 적용 시 시점 쟁점이 없는 현행 조문만 VERIFIED_PROVISION으로 승격하고 분쟁 조문은 유지한다."""
    c_clean1 = Citation.create(CitationType.STATUTE, "민법 제105조", law_name="민법", article="105")
    c_clean2 = Citation.create(CitationType.STATUTE, "상법 제42조", law_name="상법", article="42")
    c_clean3 = Citation.create(CitationType.STATUTE, "형법 제250조", law_name="형법", article="250")
    c_mismatch = Citation.create(CitationType.STATUTE, "근로기준법 제23조", law_name="근로기준법", article="23")
    c_need_rev = Citation.create(CitationType.STATUTE, "행정소송법 제20조", law_name="행정소송법", article="20")
    c_explicit = Citation.create(CitationType.STATUTE, "국가배상법 제2조", law_name="국가배상법", article="2")

    def _verdict(cit, *, inferred=True, temporal="UNVERIFIED", needed=False):
        return {
            "citation_id": cit.citation_id,
            "type": "STATUTE",
            "status": "PARTIALLY_VERIFIED",
            "inferred_reference_applied": inferred,
            "scope": "incident",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "NOT_ASSERTED", "temporal": temporal},
            "review": {"temporal_review_needed": needed},
            "findings": [],
        }

    verdicts = [
        _verdict(c_clean1),
        _verdict(c_clean2),
        _verdict(c_clean3),
        _verdict(c_mismatch),
        _verdict(c_need_rev, needed=True),
        _verdict(c_explicit, inferred=False),
    ]

    class _DummyResult:
        def __init__(self):
            self.findings = []
            self.unverified_items = [
                {"citation_id": c_clean1.citation_id, "scope": "PARTIAL", "kind": "verification"},
                {"citation_id": c_mismatch.citation_id, "scope": "PARTIAL", "kind": "verification"},
            ]
            self.engine_data = {
                "legal_verdicts": verdicts,
                "legal_reviews": [{"scope": "incident", "verdicts": [dict(v) for v in verdicts]}],
                "legal": {"component_summary": {}},
            }

    from packages.common.schemas import Evidence, Finding
    mismatch_finding = Finding.create(
        FindingType.TEMPORAL_LAW_MISMATCH, VerificationStatus.CONTRADICTED, Severity.HIGH, EvidenceGrade.A,
        "행위시법 불일치",
        evidence=[Evidence.create(description="시점", grade="A")],
        confidence_features={"citation_id": c_mismatch.citation_id, "law_name": "근로기준법", "article": "23"},
    )

    dummy = _DummyResult()
    VerificationPipeline._promote_inferred_current_statutes(
        dummy, [c_clean1, c_clean2, c_clean3, c_mismatch, c_need_rev, c_explicit], [mismatch_finding]
    )
    by_id = {v["citation_id"]: v for v in verdicts}
    for clean_c in (c_clean1, c_clean2, c_clean3):
        assert by_id[clean_c.citation_id]["status"] == "VERIFIED"
        assert by_id[clean_c.citation_id]["verification_label"] == "VERIFIED_PROVISION"
        assert by_id[clean_c.citation_id]["levels"].get("temporal_basis") == "CURRENT_VERSION"
        assert "현행 버전 기준 일치" in " ".join(by_id[clean_c.citation_id].get("advisories", []))
    assert by_id[c_mismatch.citation_id]["status"] == "PARTIALLY_VERIFIED"
    assert by_id[c_need_rev.citation_id]["status"] == "PARTIALLY_VERIFIED"
    assert by_id[c_explicit.citation_id]["status"] == "PARTIALLY_VERIFIED"
    assert dummy.engine_data["legal"]["verified_count"] == 3


# ===========================================================================
# P1-2b: 무리한 법리 주장 4종 독립 탐지 (각 3+ 양성 / 3+ 대조군)
# ===========================================================================

@pytest.mark.parametrize("sentence", [
    "원고의 일반 대여금 채권의 소멸시효는 25년이므로 아직 시효가 완성되지 않았다.",
    "이 사건 불법행위 손해배상 청구권의 소멸시효 기간은 15년으로 보아야 한다.",
    "피고에 대한 구상금 채권은 영구히 소멸하지 않으므로 언제든 청구할 수 있다.",
])
def test_p1_2b_limitation_period_distortion_positive(sentence):
    matches = classify_claims(sentence)
    assert any(m.claim_type == "LIMITATION_PERIOD_DISTORTION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "일반 대여금 채권의 소멸시효 기간은 25년이 아니다.",
    "원고는 20년간 점유하여 취득시효가 완성되었다고 주장한다.",
    "채무자의 승인으로 소멸시효가 중단되어 15년이 경과하여도 소멸하지 않는다.",
    "형사 공소시효는 25년으로 규정되어 있어 기소가 가능하다.",
])
def test_p1_2b_limitation_period_distortion_control(sentence):
    matches = classify_claims(sentence)
    assert not any(m.claim_type == "LIMITATION_PERIOD_DISTORTION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "피고에게도 헌법상 무죄추정의 원칙이 적용되므로 민사상 손해배상 책임이 인정될 수 없다.",
    "민사 채무불이행 손해배상 사건이라도 합리적 의심이 없을 정도의 증명이 없다면 책임을 물을 수 없다.",
    "피고는 무죄추정의 원칙에 따라 민사상 배상 책임에서 면책되어야 한다.",
])
def test_p1_2b_civil_criminal_standard_confusion_positive(sentence):
    matches = classify_claims(sentence)
    assert any(m.claim_type == "CIVIL_CRIMINAL_STANDARD_CONFUSION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "공소장\n공소사실: 피고인은 절도 행위를 하였다. 무죄추정의 원칙이 문제되나 책임이 인정될 수 없다.",
    "형사상 무죄추정 원칙과 민사상 손해배상 책임은 별개의 판단 기준이므로 책임이 부정되는 것은 아니다.",
    "무죄추정의 원칙으로 민사 손해배상 책임이 면책되지 않는다.",
])
def test_p1_2b_civil_criminal_standard_confusion_control(sentence):
    matches = classify_claims(sentence)
    assert not any(m.claim_type == "CIVIL_CRIMINAL_STANDARD_CONFUSION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "지방법원이 해당 특별법 법률 조항을 위헌으로 판단하여 직접 폐지하였다.",
    "고등법원 판결로 민법 제750조의 효력이 전면 소멸되어 더 이상 적용할 수 없다.",
    "제1심 법원이 관련 세법 법률을 직접 실효시키고 무효로 선언하였다.",
])
def test_p1_2b_lower_court_statute_invalidation_positive(sentence):
    matches = classify_claims(sentence)
    assert any(m.claim_type == "LOWER_COURT_STATUTE_INVALIDATION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "지방법원은 해당 조항에 대해 헌법재판소에 위헌법률심판 제청을 결정하였다.",
    "지방법원은 시행령 조항에 대한 명령·규칙 심사 결과 위법하다고 판단하였다.",
    "헌법재판소의 위헌 결정으로 해당 법률 조항의 효력이 상실되었다.",
    "지방법원은 이 사건 약관 규정이 불공정하여 무효라고 판단하였다.",
])
def test_p1_2b_lower_court_statute_invalidation_control(sentence):
    matches = classify_claims(sentence)
    assert not any(m.claim_type == "LOWER_COURT_STATUTE_INVALIDATION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "원고의 일방적인 통지만으로 계약 대금을 2배로 인상하기로 변경한 것은 유효하다.",
    "피고의 동의 없이 일방적으로 계약 금액을 증액하더라도 그 효력이 인정된다.",
    "상대방의 합의 없이 일방적 통보만으로 임대료를 200% 상향 변경하여 지급할 의무가 발생한다.",
])
def test_p1_2b_unilateral_contract_modification_positive(sentence):
    matches = classify_claims(sentence)
    assert any(m.claim_type == "UNILATERAL_CONTRACT_MODIFICATION" for m in matches)


@pytest.mark.parametrize("sentence", [
    "물가변동에 따른 계약상 조정 조항에 따라 계약 대금을 증액할 수 있다.",
    "당사자 간의 합의에 따라 계약 금액을 20% 인상 변경한 것은 유효하다.",
    "상대방의 동의 없이 일방적 통지로 계약 대금을 증액할 수는 없으므로 효력이 없다.",
    "법정 해제 사유에 따라 계약을 적법하게 해제하였다.",
])
def test_p1_2b_unilateral_contract_modification_control(sentence):
    matches = classify_claims(sentence)
    assert not any(m.claim_type == "UNILATERAL_CONTRACT_MODIFICATION" for m in matches)


def test_p1_2b_review_claims_attaches_official_sources_from_rules_json():
    doc = _doc(
        "일반 채권의 소멸시효는 30년이므로 완성되지 않았다.",
        "민사 배상 사건에서도 무죄추정 원칙에 따라 손해배상 책임이 인정될 수 없다.",
    )
    findings = review_claims(doc)
    by_type = {f.confidence_features["claim_type"]: f for f in findings}
    assert "LIMITATION_PERIOD_DISTORTION" in by_type
    assert "CIVIL_CRIMINAL_STANDARD_CONFUSION" in by_type
    lim_basis = by_type["LIMITATION_PERIOD_DISTORTION"].confidence_features["basis"]
    assert any("민법 제162조" in b["name"] and b.get("text") for b in lim_basis)
    civ_basis = by_type["CIVIL_CRIMINAL_STANDARD_CONFUSION"].confidence_features["basis"]
    assert any("민사소송법 제202조" in b["name"] and b.get("text") for b in civ_basis)


# ===========================================================================
# P2-1a: 법령·행정규칙 인용 경계 및 조사 분리 (복합 법령 보존)
# ===========================================================================

@pytest.mark.parametrize("text,expected_type,expected_law,prefix", [
    ("한편 사내보안지침 제4조를 본다.", CitationType.ADMIN_RULE, "사내보안지침", "한편"),
    ("적어도 사내보안예규 제2조에 따른다.", CitationType.ADMIN_RULE, "사내보안예규", "적어도"),
    ("예컨대 행정규칙지침 제7조를 든다.", CitationType.ADMIN_RULE, "행정규칙지침", "예컨대"),
    ("적어도 내부관리규정 제2조에 따른다.", CitationType.STATUTE, "내부관리규정", "적어도"),
    ("최소한 민법 제750조는 적용된다.", CitationType.STATUTE, "민법", "최소한"),
    ("사실상 상법 제42조의 문제다.", CitationType.STATUTE, "상법", "사실상"),
    ("피고의행위는민법 제750조에 반한다.", CitationType.STATUTE, "민법", "행위는"),
    ("원고는테스트특별법 제3조를 주장한다.", CitationType.STATUTE, "테스트특별법", "원고는"),
    ("당해사건은국배법 제2조에 해당한다.", CitationType.STATUTE, "국가배상법", "사건은"),
])
def test_p2_1a_law_and_admin_rule_boundaries_clean(text, expected_type, expected_law, prefix):
    citations = extract_from_text(text)
    matches = [c for c in citations if c.type == expected_type]
    assert matches, f"No citation extracted from {text!r}"
    c = matches[0]
    assert c.law_name == expected_law
    assert not c.raw_text.startswith(prefix)
    assert text[c.span[0]:c.span[1]].strip() == c.raw_text


@pytest.mark.parametrize("raw,expected", [
    ("국가배상법", "국가배상법"),
    ("지방계약법", "지방자치단체를 당사자로 하는 계약에 관한 법률"),
    ("국가계약법", "국가를 당사자로 하는 계약에 관한 법률"),
    ("대한민국헌법", "대한민국헌법"),
    ("어린이안전법", "어린이안전법"),
    ("새마을금고법", "새마을금고법"),
    ("보은군법", "보은군법"),
])
def test_p2_1a_control_compound_statute_names_never_split(raw, expected):
    assert law_name_suffix(raw) in (raw, expected)
    assert canonical_law_name(raw) == expected


# ===========================================================================
# P2-1b: 한국어 법률 NER 불용어 및 법인 앞 수식어 배제
# ===========================================================================

def test_p2_1b_person_and_company_ner_filters_false_positives_and_keeps_real_entities():
    doc = _doc(
        "원고 측에 서류를 송부하였고 피고 측을 상대로 청구하였다.",
        "피고 영위하는 영업과 관련하여 참고인 부대 소속 진술이 제출되었다.",
        "원고 박성민과 피고인 이지영은 증인 한상우와 채무자 정민준 앞에서 합의하였다.",
        "원고는 민간 주식회사 알파테스트와 계약을 체결하였고 주식회사 베타상사에 지급하였다.",
        "피고는 기존 유한회사 형태로 운영하였다.",
    )
    entities = extract_entities(doc)
    people = {e.name for e in entities if e.type == EntityType.PERSON}
    companies = {e.name for e in entities if e.type == EntityType.COMPANY}

    # False positives must be rejected
    for bad_person in ("측에", "측을", "영위하는", "영위하", "부대", "진술", "계약", "관련"):
        assert bad_person not in people
    for bad_company in ("민간", "원고는", "피고는", "기존"):
        assert bad_company not in companies

    # Real person and corporate names must remain extracted
    for good_person in ("박성민", "이지영", "한상우", "정민준"):
        assert good_person in people
    assert "알파테스트" in companies
    assert any(name.startswith("베타상사") for name in companies)


# ===========================================================================
# P2-1c: 부록·체크리스트 메타표 격리 (서증 목록·일시표·계산표 비훼손)
# ===========================================================================

def test_p2_1c_meta_checklist_section_and_table_isolated():
    rubric_table = Block(
        "b_tbl_meta",
        "테스트 항목 | 오류 유형 | 기대 결과\n1. 가상 판례 | 대법원 2099다99999 판결 | 허위 판례 탐지",
        1,
        block_type="table",
        attributes={"cells": [
            ["테스트 항목", "오류 유형", "기대 결과"],
            ["1. 가상 판례", "대법원 2099다99999 판결", "허위 판례 탐지"],
        ]},
    )
    doc = NormalizedDocument(
        "doc-meta",
        "brief.pdf",
        "application/pdf",
        "1" * 64,
        pages=[Page(1, blocks=[
            Block("b_body", "원고 박성민은 2024. 5. 10. 민법 제750조에 따라 배상을 청구하였다.", 1),
            rubric_table,
            Block("b_app_head", "[부록] 기능 검증 체크리스트", 1),
            Block("b_app_row1", "1. 원고 홍테스트는 2099. 1. 1. 대법원 2099다88888 판결 및 가상부록법 제99조를 주장한다.", 1),
            Block("b_app_row2", "2. 민간 주식회사 메타상사 사건에서 소멸시효 30년 무효이다.", 1),
            Block("b_sign", "서울중앙지방법원 귀중", 1),
        ])],
    )

    meta_ids = meta_checklist_block_ids(doc)
    assert "b_tbl_meta" in meta_ids
    assert "b_app_head" in meta_ids
    assert "b_app_row1" in meta_ids
    assert "b_app_row2" in meta_ids
    assert "b_body" not in meta_ids
    assert "b_sign" not in meta_ids

    citations = extract_citations(doc)
    assert [c.law_name for c in citations if c.type == CitationType.STATUTE] == ["민법"]
    assert not any(c.case_number in ("2099다99999", "2099다88888") for c in citations)

    claims = extract_claims(doc, citations)
    meta_claims = [c for c in claims if c.block_id in meta_ids]
    assert meta_claims and all(c.type == ClaimType.DOCUMENT_META and not c.attributes["verification_target"] for c in meta_claims)
    assert any(c.block_id == "b_body" and c.attributes["verification_target"] for c in claims)

    entities = extract_entities(doc)
    assert "박성민" in {e.name for e in entities if e.type == EntityType.PERSON}
    assert "홍테스트" not in {e.name for e in entities if e.type == EntityType.PERSON}
    assert "메타상사" not in {e.name for e in entities if e.type == EntityType.COMPANY}

    events = extract_events(doc)
    assert len(events) == 1 and events[0].block_id == "b_body"


def test_p2_1c_flattened_rubric_header_block_isolated_without_appendix_heading():
    doc = _doc(
        "테스트 항목 | 검증 대상 | 기대 결과",
        "1. 가공 판례 인용 검증 대법원 2098다77777 판결 탐지 확인",
        "위 원고 소송대리인 변호사 김변호",
    )
    meta_ids = meta_checklist_block_ids(doc)
    assert meta_ids == {"b0", "b1"}
    assert extract_citations(doc) == []


def test_p2_1c_control_real_exhibit_chronology_and_calc_tables_untouched():
    exhibit_cells = [
        ["호증", "서증명", "작성일", "입증취지"],
        ["갑 제1호증", "매매계약서", "2024. 1. 5.", "계약 체결 사실"],
    ]
    exhibit_table = Block(
        "t_exh",
        "호증 | 서증명 | 작성일 | 입증취지\n갑 제1호증 | 매매계약서 | 2024. 1. 5. | 계약 체결 사실",
        1,
        block_type="table",
        attributes={"cells": exhibit_cells, "table_ref": "t_exh"},
    )
    chrono_cells = [
        ["일시", "내용", "근거"],
        ["2024. 2. 1.", "민법 제390조 이행청구", "갑 제2호증"],
    ]
    chrono_table = Block(
        "t_chr",
        "일시 | 내용 | 근거\n2024. 2. 1. | 민법 제390조 이행청구 | 갑 제2호증",
        1,
        block_type="table",
        attributes={"cells": chrono_cells, "table_ref": "t_chr"},
    )
    calc_cells = [
        ["항목", "산정기준", "금액"],
        ["원금", "계약대금", "1,000,000원"],
        ["합계", "총액", "1,000,000원"],
    ]
    calc_table = Block(
        "t_calc",
        "항목 | 산정기준 | 금액\n원금 | 계약대금 | 1,000,000원\n합계 | 총액 | 1,000,000원",
        1,
        block_type="table",
        attributes={"cells": calc_cells, "table_ref": "t_calc"},
    )
    doc = NormalizedDocument(
        "doc-real-tables",
        "real.pdf",
        "application/pdf",
        "2" * 64,
        pages=[Page(1, blocks=[exhibit_table, chrono_table, calc_table])],
        structure={"tables": [
            {"cells": exhibit_cells, "page": 1, "table_ref": "t_exh"},
            {"cells": chrono_cells, "page": 1, "table_ref": "t_chr"},
            {"cells": calc_cells, "page": 1, "table_ref": "t_calc"},
        ]},
    )

    assert meta_checklist_block_ids(doc) == set()
    assert not is_meta_checklist_table_rows(exhibit_cells)
    assert not is_meta_checklist_table_rows(chrono_cells)
    assert not is_meta_checklist_table_rows(calc_cells)
    rows = exhibit_rows(doc)
    assert len(rows) == 1 and rows[0]["name"] == "매매계약서"
    citations = extract_citations(doc)
    assert any(c.type == CitationType.STATUTE and c.law_name == "민법" and c.article == "390" for c in citations)
    assert CalculationEngine().verify_document(doc) == []
