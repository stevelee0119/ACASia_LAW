"""A-4 EVI-DATE 위치(항목명) 보강 단위 및 진입점 시험.

- korean_amount._find_item_heading을 공용 재사용하여 날짜 판정에 항목명이 올바르게 반영되는지 검증
- 합성 양성 3건, 대조군 3건
"""

import pytest
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.date_verifier import verify_dates_in_document


def _make_doc(*texts: str, doc_id: str = "doc_date_test_1") -> NormalizedDocument:
    blocks = [
        Block(block_id=f"b{i+1}", text=t, page=1, visible=True, source_layer="visible_text")
        for i, t in enumerate(texts)
    ]
    page = Page(page_number=1, blocks=blocks, width=595.0, height=842.0)
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0000000000000000000000000000000000000000000000000000000000000000",
        pages=[page],
    )


def test_positive_date_weekday_with_bracket_heading():
    """양성 1: 괄호형 항목명([점검일정]) 뒤 요일 불일치에서 항목명 접두 반영 검증."""
    # 2026. 3. 20.은 금요일인데 (목)으로 기재
    doc = _make_doc(
        "준비서면\n[점검일정] 2026. 3. 20.(목) 현장 확인을 실시하기로 하였습니다."
    )
    findings = verify_dates_in_document(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("heading") == "[점검일정]"
    assert "[점검일정]" in f.detail
    assert "날짜와 요일 불일치" in f.title


def test_positive_date_invalid_hyphen_with_bracket_heading():
    """양성 2: 하이픈 표기 평년 2월 29일 앞에 항목명([계약체결일]) 접두 반영 검증."""
    # 2026년은 평년이므로 2026-02-29는 존재하지 않는 날짜
    doc = _make_doc(
        "준비서면\n[계약체결일] 2026-02-29 매매계약서를 작성하였습니다."
    )
    findings = verify_dates_in_document(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("heading") == "[계약체결일]"
    assert "[계약체결일]" in f.detail
    assert "달력상 존재하지 않는 날짜" in f.title


def test_positive_date_invalid_with_bullet_heading():
    """양성 3: 불릿 번호 뒤 항목명(1. 납품기한) 접두 반영 검증."""
    # 4월은 30일까지 있으므로 4. 31.은 존재하지 않음
    doc = _make_doc(
        "준비서면\n1. 납품기한 2026. 4. 31.까지 전량을 납품하기로 약정하였습니다."
    )
    findings = verify_dates_in_document(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("heading") == "1. 납품기한"
    assert "[1. 납품기한]" in f.detail


def test_control_narrative_sentence_no_false_heading():
    """대조군 1: 일반 서술문 중간의 날짜 결함은 무리한 항목명 없이 상위 소제목으로 폴백 검증."""
    # 2026. 3. 20.은 금요일인데 (목)으로 기재, 앞 문맥은 서술문
    doc = _make_doc(
        "제1항 청구원인 사실관계\n원고는 피고와 수차례 협의한 끝에 2026. 3. 20.(목)에 최종 합의에 이르렀습니다."
    )
    findings = verify_dates_in_document(doc)
    assert len(findings) == 1
    f = findings[0]
    # 서술문 일부가 항목명으로 오인되지 않고 블록/상위 소제목이 채택되어야 함
    assert f.confidence_features.get("heading") == "제1항 청구원인 사실관계"


def test_control_valid_date_and_weekday_no_findings():
    """대조군 2: 정상적인 요일 및 날짜 기재 시 오탐 0건 검증."""
    # 2026. 3. 20.은 실제 금요일
    doc = _make_doc(
        "[회의일정] 2026. 3. 20.(금) 오전 10시에 회의를 진행하였습니다.\n[납품완료] 2026. 4. 30. 전량을 정상 입고하였습니다."
    )
    findings = verify_dates_in_document(doc)
    assert len(findings) == 0, f"정상 날짜는 결함으로 잡히지 않아야 함: {findings}"


def test_control_valid_hyphen_date_no_findings():
    """대조군 3: 정상적인 하이픈 날짜 기재 시 오탐 0건 검증."""
    doc = _make_doc(
        "[체결일자] 2026-02-28 계약서를 정식 체결하였습니다.\n[발송일시] 2025-12-31 통지서를 우편 발송하였습니다."
    )
    findings = verify_dates_in_document(doc)
    assert len(findings) == 0, f"정상 하이픈 날짜는 결함으로 잡히지 않아야 함: {findings}"
