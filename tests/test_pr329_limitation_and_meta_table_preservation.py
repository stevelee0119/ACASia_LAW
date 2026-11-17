"""PR #329 보완 회귀 테스트: 소멸시효 왜곡 적용 범위 축소 & 체크리스트 부록 내 정상 표 보존.

모든 문장과 표 데이터는 합성 데이터이며 실제 사건 고유값을 포함하지 않는다.
"""
from __future__ import annotations

import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.claim_engine.evidence_consistency import exhibit_rows
from packages.claim_engine.extractor import extract_claims, extract_entities, extract_events
from packages.common.enums import CitationType, ClaimType
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.document_engine.meta_sections import is_meta_checklist_table_rows, meta_checklist_block_ids
from packages.legal_engine.citation_extractor import extract_citations
from packages.legal_engine.claim_review import classify_claims


# ===========================================================================
# 1. 소멸시효 기간 왜곡 규칙 적용 범위 축소 테스트
# ===========================================================================

def test_pr329_limitation_no_claim_scope_not_contradicted():
    """권리 유형이 특정되지 않은 '소멸시효는 25년이다'는 CONTRADICTED로 확정하지 않는다."""
    unspecified_sentences = [
        "이 사건에서 소멸시효는 25년이다.",
        "소멸시효 기간은 30년으로 보아야 한다.",
        "시효기간은 21년 이상 경과하여야 소멸한다.",
        "일반 소멸시효 기간은 25년으로 인정되어야 마땅하다.",
    ]
    for s in unspecified_sentences:
        matches = classify_claims(s)
        distortion_matches = [m for m in matches if m.claim_type == "LIMITATION_PERIOD_DISTORTION"]
        assert not distortion_matches, f"Should not classify unspecified sentence as distortion: {s}"


@pytest.mark.parametrize("sentence,expected_law", [
    ("원고의 일반 대여금 채권의 소멸시효는 25년이므로 아직 시효가 완성되지 않았다.", "민법 제162조"),
    ("피고에 대한 공사대금 계약상 채권의 소멸시효 기간은 20년으로 인정되어야 한다.", "민법 제162조"),
    ("피고에 대한 매매대금 반환 채권은 영구히 소멸하지 않으므로 청구가 타당하다.", "민법 제162조"),
    ("이 사건 불법행위 손해배상 청구권의 소멸시효 기간은 15년으로 보아야 한다.", "민법 제766조"),
    ("피고의 가해행위에 기한 위자료 손해배상청구권의 소멸시효 기간은 25년이다.", "민법 제766조"),
])
def test_pr329_limitation_positive_general_bonds_and_torts(sentence, expected_law):
    """일반 채권·손해배상청구권의 과도한 기간 및 영구 미완성 주장은 의도대로 탐지되고 조문이 일치한다."""
    matches = classify_claims(sentence)
    distortions = [m for m in matches if m.claim_type == "LIMITATION_PERIOD_DISTORTION"]
    assert len(distortions) == 1
    d = distortions[0]
    assert d.status == "CONTRADICTED"
    assert any(expected_law in b.get("name", "") for b in d.basis)
    assert expected_law in d.detail


@pytest.mark.parametrize("sentence", [
    "특별법에 규정된 손실보상 청구권의 소멸시효 기간은 25년으로 정해져 있다.",
    "상법상 상사 채권의 소멸시효는 25년으로 보아야 한다.",
    "국가배상법에 따른 국가배상청구권의 소멸시효는 25년이다.",
    "근로기준법상 임금 채권의 소멸시효는 25년으로 보아야 마땅하다.",
    "소유권 이외의 재산권에 대한 소멸시효는 20년이다.",
    "전세권 및 기타 제한물권의 소멸시효는 20년으로 보아야 한다.",
    "채권자의 재판상 청구 및 가압류로 인하여 소멸시효가 중단되어 25년이 지나도 시효가 완성되지 않았다.",
    "채무자의 채무 승인으로 소멸시효가 중단되어 15년이 경과하여도 청구권이 소멸하지 않는다.",
    "손해배상청구권의 소멸시효 기산점이 도래하지 않아 15년이 지나도 시효가 완성되지 않는다.",
])
def test_pr329_limitation_exclusions_not_contradicted(sentence):
    """특별법상 청구권, 소유권 이외 재산권, 시효 중단·정지·기산점 문맥은 확정 반박하지 않는다."""
    matches = classify_claims(sentence)
    distortions = [m for m in matches if m.claim_type == "LIMITATION_PERIOD_DISTORTION"]
    assert not distortions, f"Excluded context wrongly contradicted: {sentence}"


@pytest.mark.parametrize("sentence", [
    "일반 대여금 채권의 소멸시효 기간은 25년이 아니다.",
    "원고는 20년간 평온하게 점유하여 취득시효가 완성되었다고 주장한다.",
    "형사 공소시효는 25년으로 규정되어 있어 적법한 기소에 해당한다.",
    "민법 제162조 제1항에 따라 일반 채권의 소멸시효 기간은 10년이다.",
])
def test_pr329_limitation_controls_preserved(sentence):
    """취득시효, 공소시효, 부정문, 법정 기준 인용 대조군은 정상 유지된다."""
    matches = classify_claims(sentence)
    distortions = [m for m in matches if m.claim_type == "LIMITATION_PERIOD_DISTORTION"]
    assert not distortions


# ===========================================================================
# 2. 체크리스트 부록 내 정상 사실관계·서증·산정 표 보존 테스트
# ===========================================================================

def test_pr329_meta_checklist_with_following_facts_exhibits_and_calc_tables():
    """한 문서 내에 체크리스트 제목, 메타 체크리스트 표, 이어지는 정상 사실관계 표(일자|내용|법적 근거),

    서증 목록, 손해액 산정표, 사실관계 본문이 함께 존재할 때 메타 블록만 DOCUMENT_META로 격리되고
    정상 표 및 사실 서술의 인용·사건·계산·서증 추출은 온전히 보존된다.
    """
    b_body = Block(
        "b_body",
        "원고는 2024. 1. 5. 피고에게 계약상 채무불이행으로 인한 손해배상을 청구하였다.",
        1,
    )
    b_app_head = Block("b_app_head", "[부록] 기능 점검 체크리스트", 1)

    meta_cells = [
        ["검증 항목", "대상 기능", "기대 결과"],
        ["1", "가공 판례 탐지", "대법원 2099다99999 판결 탐지"],
        ["2", "허위 조문 탐지", "민법 제9999조 탐지"],
    ]
    b_tbl_meta = Block(
        "b_tbl_meta",
        "검증 항목 | 대상 기능 | 기대 결과\n1 | 가공 판례 탐지 | 대법원 2099다99999 판결 탐지\n2 | 허위 조문 탐지 | 민법 제9999조 탐지",
        1,
        block_type="table",
        attributes={"cells": meta_cells, "table_ref": "b_tbl_meta"},
    )
    b_app_row = Block(
        "b_app_row",
        "1. 가공 판례 방지 검증 대법원 2099다88888 판결 확인 및 가상부록법 제99조 점검.",
        1,
    )

    facts_cells = [
        ["일자", "내용", "법적 근거"],
        ["2024. 1. 10.", "피고의 계약 위반으로 채무불이행 책임 발생", "민법 제390조"],
        ["2024. 2. 15.", "원고는 피고에게 불법행위 손해배상을 청구함", "민법 제750조"],
    ]
    b_tbl_facts = Block(
        "b_tbl_facts",
        "일자 | 내용 | 법적 근거\n"
        "2024. 1. 10. | 피고의 계약 위반으로 채무불이행 책임 발생 | 민법 제390조\n"
        "2024. 2. 15. | 원고는 피고에게 불법행위 손해배상을 청구함 | 민법 제750조",
        1,
        block_type="table",
        attributes={"cells": facts_cells, "table_ref": "b_tbl_facts"},
    )

    exh_cells = [
        ["호증", "서증명", "입증취지"],
        ["갑 제1호증", "매매계약서", "계약 체결 및 이행기 사실"],
        ["갑 제2호증", "내용증명서", "이행 최고 및 계약 해제 통지"],
    ]
    b_tbl_exh = Block(
        "b_tbl_exh",
        "호증 | 서증명 | 입증취지\n"
        "갑 제1호증 | 매매계약서 | 계약 체결 및 이행기 사실\n"
        "갑 제2호증 | 내용증명서 | 이행 최고 및 계약 해제 통지",
        1,
        block_type="table",
        attributes={"cells": exh_cells, "table_ref": "b_tbl_exh"},
    )

    calc_cells = [
        ["항목", "산정내역", "금액"],
        ["원금", "계약대금 미지급분", "50,000,000원"],
        ["손해액", "지연배상금", "5,000,000원"],
        ["합계", "총 청구금액", "55,000,000원"],
    ]
    b_tbl_calc = Block(
        "b_tbl_calc",
        "항목 | 산정내역 | 금액\n"
        "원금 | 계약대금 미지급분 | 50,000,000원\n"
        "손해액 | 지연배상금 | 5,000,000원\n"
        "합계 | 총 청구금액 | 55,000,000원",
        1,
        block_type="table",
        attributes={"cells": calc_cells, "table_ref": "b_tbl_calc"},
    )

    b_fact_prose = Block(
        "b_fact_prose",
        "원고는 2024. 3. 20. 피고에게 위 정산 합계 금원의 지급을 최고하였다.",
        1,
    )
    b_sign = Block("b_sign", "서울중앙지방법원 귀중", 1)

    doc = NormalizedDocument(
        "doc-pr329-mixed",
        "brief_pr329.pdf",
        "application/pdf",
        "3" * 64,
        pages=[Page(1, blocks=[
            b_body,
            b_app_head,
            b_tbl_meta,
            b_app_row,
            b_tbl_facts,
            b_tbl_exh,
            b_tbl_calc,
            b_fact_prose,
            b_sign,
        ])],
        structure={"tables": [
            {"cells": meta_cells, "page": 1, "table_ref": "b_tbl_meta"},
            {"cells": facts_cells, "page": 1, "table_ref": "b_tbl_facts"},
            {"cells": exh_cells, "page": 1, "table_ref": "b_tbl_exh"},
            {"cells": calc_cells, "page": 1, "table_ref": "b_tbl_calc"},
        ]},
    )

    # 1) 메타 표 판정 확인
    assert is_meta_checklist_table_rows(meta_cells)
    assert not is_meta_checklist_table_rows(facts_cells)
    assert not is_meta_checklist_table_rows(exh_cells)
    assert not is_meta_checklist_table_rows(calc_cells)

    # 2) 메타 블록 격리 확인: b_app_head, b_tbl_meta, b_app_row 만 격리되어야 함
    meta_ids = meta_checklist_block_ids(doc)
    assert meta_ids == {"b_app_head", "b_tbl_meta", "b_app_row"}
    assert "b_tbl_facts" not in meta_ids
    assert "b_tbl_exh" not in meta_ids
    assert "b_tbl_calc" not in meta_ids
    assert "b_fact_prose" not in meta_ids
    assert "b_body" not in meta_ids
    assert "b_sign" not in meta_ids

    # 3) 인용 추출 확인: 메타 블록 인용(2099다99999, 민법 제9999조)은 배제되고 사실관계 표의 민법 조문은 정상 추출
    citations = extract_citations(doc)
    law_articles = {(c.law_name, c.article) for c in citations if c.type == CitationType.STATUTE}
    assert ("민법", "390") in law_articles
    assert ("민법", "750") in law_articles
    assert ("민법", "9999") not in law_articles
    assert not any(c.case_number in ("2099다99999", "2099다88888") for c in citations)

    # 4) 주장 추출 확인: 메타 블록은 DOCUMENT_META, 정상 서술 블록은 실체 주장으로 보존
    claims = extract_claims(doc, citations)
    meta_claims = [c for c in claims if c.block_id in meta_ids]
    assert all(c.type == ClaimType.DOCUMENT_META for c in meta_claims)
    prose_claims = [c for c in claims if c.block_id in ("b_body", "b_fact_prose")]
    assert len(prose_claims) >= 2
    assert not any(c.type == ClaimType.DOCUMENT_META for c in prose_claims)

    # 5) 서증 목록 추출 확인
    exhibits = exhibit_rows(doc)
    assert len(exhibits) == 2
    exhibit_names = [e["name"] for e in exhibits]
    assert "매매계약서" in exhibit_names
    assert "내용증명서" in exhibit_names

    # 6) 사건 추출 확인: 정상 서술의 날짜는 사건으로 추출되고 메타 날짜는 격리됨
    events = extract_events(doc)
    event_block_ids = {e.block_id for e in events}
    assert "b_body" in event_block_ids
    assert "b_fact_prose" in event_block_ids
    assert "b_app_row" not in event_block_ids

    # 7) 계산 검산 확인
    calc_findings = CalculationEngine().verify_document(doc)
    # 정산표가 정확하므로 ARITHMETIC_MISMATCH 오류는 없어야 함
    assert not any(f.type.name == "ARITHMETIC_MISMATCH" for f in calc_findings)


def test_pr329_checklist_header_with_generic_columns_isolated():
    """'항목 | 기대 결과 | 비고' 등 일반 열(항목·비고)과 결합된 체크리스트 헤더가 정상 법률표로 오인되어 메타 격리를 우회하지 않음을 검증한다."""
    checklist_generic_cells = [
        ["항목", "기대 결과", "비고"],
        ["1", "가공 판례 대법원 2099다99999 판결 탐지 확인", "성공"],
        ["2", "허위 조문 민법 제9999조 탐지 확인", "성공"],
    ]
    # 1) 헤더 행 수준 판정 검증
    assert is_meta_checklist_table_rows(checklist_generic_cells)

    # 2) 문서 레벨 격리 검증: 부록 제목 없이 표만 있어도 격리
    b_body = Block("b_body", "원고는 피고에게 대여금의 반환을 청구한다.", 1)
    b_tbl_meta = Block(
        "b_tbl_meta",
        "항목 | 기대 결과 | 비고\n1 | 가공 판례 대법원 2099다99999 판결 탐지 확인 | 성공\n2 | 허위 조문 민법 제9999조 탐지 확인 | 성공",
        1,
        block_type="table",
        attributes={"cells": checklist_generic_cells, "table_ref": "b_tbl_meta"},
    )
    doc = NormalizedDocument(
        "doc-meta-generic-cols",
        "brief_chk.pdf",
        "application/pdf",
        "4" * 64,
        pages=[Page(1, blocks=[b_body, b_tbl_meta])],
        structure={"tables": [{"cells": checklist_generic_cells, "page": 1, "table_ref": "b_tbl_meta"}]},
    )

    meta_ids = meta_checklist_block_ids(doc)
    assert "b_tbl_meta" in meta_ids
    assert "b_body" not in meta_ids

    # 3) 인용 격리 검증: 메타 표 안의 가공 판례·허위 조문은 인용으로 추출되지 않아야 함
    citations = extract_citations(doc)
    assert not any(c.case_number == "2099다99999" for c in citations)
    assert not any(c.law_name == "민법" and c.article == "9999" for c in citations)


@pytest.mark.parametrize("header_row", [
    ["항목", "기대 결과", "비고"],
    ["순번", "검증 내용", "비고"],
    ["번호", "테스트 항목", "결과", "비고"],
    ["구분", "점검 대상", "통과 기준", "비고"],
    ["항목", "오류 유형", "탐지 대상"],
])
def test_pr329_rubric_headers_with_generic_columns_identified_as_meta(header_row):
    """일반 컬럼(항목, 순번, 구분, 비고)이 섞여 있어도 루브릭 컬럼이 있으면 메타 체크리스트 표로 식별된다."""
    rows = [header_row, ["1", "내용", "값", "추가"]]
    assert is_meta_checklist_table_rows(rows)

