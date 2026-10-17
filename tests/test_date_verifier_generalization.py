# -*- coding: utf-8 -*-
"""날짜 검증기(date_verifier) 위치 문맥 보강 및 요일 조사 허용 일반화 시험.

이 시험은 다음 사항을 검증한다:
1. 실제 진입점(VerificationPipeline)을 통한 날짜 검증 및 소제목/문맥 반영 실행.
2. 요일 표기 뒤 조사(에, 은, 는, 이, 가, 부터 등)가 결합된 양성 3건 및 정상 대조군 3건.
3. 소제목/목차 번호(1. , 가. , [제목] 등) 문맥 및 32일 등 유효 범위를 벗어난 일자 양성 3건 및 정상 대조군 3건.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

import pytest

from packages.claim_engine.date_verifier import verify_dates_in_document
from packages.common.enums import FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def _make_doc(*texts: str, doc_id: str = "synth_doc") -> NormalizedDocument:
    """합성 테스트용 정규화 문서를 생성한다 (한국어 주석)."""
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


def test_pipeline_date_verifier_heading_context_execution(tmp_path: Path):
    """공통 점검표 1항: 실제 진입점(VerificationPipeline)에서 날짜 검증과 소제목 문맥 부여 실행."""
    # 소제목과 날짜 불일치가 포함된 합성 텍스트 문서 작성
    doc_path = tmp_path / "sample_brief_test.txt"
    doc_path.write_text(
        "1. 사전 업무 개요\n"
        "담당 직원은 2024. 5. 1. 목요일에 관련 업무 서류를 접수하였습니다.\n",
        encoding="utf-8",
    )

    pipeline = VerificationPipeline()
    context = ProjectContext(project_id="test_proj_date")
    inputs = [
        DocumentInput(
            document_id="doc_pipe_test",
            path=str(doc_path),
            filename="sample_brief_test.txt",
            mime_type="text/plain",
        )
    ]

    run_res = pipeline.run("run_date_eval", context, inputs)
    assert run_res is not None
    assert len(run_res.documents) == 1

    doc_res = run_res.documents[0]
    date_findings = [f for f in doc_res.findings if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(date_findings) >= 1

    # 소제목 문맥이 detail 및 confidence_features에 기록되었는지 확인
    f = date_findings[0]
    assert "1. 사전 업무 개요" in f.detail
    assert f.confidence_features.get("heading") == "1. 사전 업무 개요"
    assert "2024. 5. 1." in f.detail


@pytest.mark.parametrize(
    "text,expected_date,stated_weekday,actual_weekday",
    [
        # 양성 예시 1: '에' 조사가 결합된 경우 (2024. 5. 1.은 수요일)
        ("업무 일정에 따라 2024. 5. 1. 목요일에 서류를 발송했습니다.", "2024. 5. 1.", "목", "수"),
        # 양성 예시 2: '부터' 조사가 결합된 경우 (2024년 6월 7일은 금요일)
        ("해당 규정은 2024년 6월 7일 토요일부터 시행하기로 하였습니다.", "2024. 6. 7.", "토", "금"),
        # 양성 예시 3: '은' 조사가 결합된 경우 (2024. 7. 10.은 수요일)
        ("협약 체결일인 2024. 7. 10. 목요일은 공휴일이 아니었습니다.", "2024. 7. 10.", "목", "수"),
    ],
)
def test_weekday_particle_positive_cases(text: str, expected_date: str, stated_weekday: str, actual_weekday: str):
    """요일 단어 뒤 조사가 결합된 날짜-요일 불일치 양성 예시 3건 검증 (한국어 주석)."""
    doc = _make_doc(text)
    findings = verify_dates_in_document(doc)

    weekday_findings = [f for f in findings if f.type == FindingType.TIMELINE_CONTRADICTION and "요일" in f.title]
    assert len(weekday_findings) == 1

    f = weekday_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    assert f.confidence_features.get("stated_weekday") == stated_weekday
    assert f.confidence_features.get("actual_weekday") == actual_weekday


@pytest.mark.parametrize(
    "text",
    [
        # 대조군 1: 역법과 일치하는 수요일 표기 ('에' 결합)
        "업무 일정에 따라 2024. 5. 1. 수요일에 서류를 발송했습니다.",
        # 대조군 2: 역법과 일치하는 금요일 표기 ('부터' 결합)
        "해당 규정은 2024년 6월 7일 금요일부터 시행하기로 하였습니다.",
        # 대조군 3: 역법과 일치하는 수요일 표기 ('은' 결합)
        "협약 체결일인 2024. 7. 10. 수요일은 공휴일이 아니었습니다.",
    ],
)
def test_weekday_particle_control_cases(text: str):
    """역법상 일치하는 정상 요일 표기 대조군 3건 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(text)
    findings = verify_dates_in_document(doc)

    weekday_findings = [f for f in findings if f.type == FindingType.TIMELINE_CONTRADICTION and "요일" in f.title]
    assert len(weekday_findings) == 0


@pytest.mark.parametrize(
    "heading,body_text,invalid_date_str",
    [
        # 양성 예시 1: 숫자형 소제목 및 4월 31일 (4월은 30일까지)
        ("1. 물품 검수 및 출고 경위", "검수 완료 후 2025-04-31 출고 전표를 발행했습니다.", "2025-04-31"),
        # 양성 예시 2: 한글 번호형 소제목 및 6월 31일 (6월은 30일까지, 1~31 범위 내 부존재 일자)
        ("가. 2차 물품 반입 확인", "반입 일자는 2025-06-31 기재되어 확인을 요청했습니다.", "2025-06-31"),
        # 양성 예시 3: 괄호형 소제목 및 평년 2월 29일 (2025년은 평년)
        ("(1) 계약 체결 일정", "계약 체결일은 2025. 2. 29. 체결된 사실이 확인됩니다.", "2025. 2. 29."),
    ],
)
def test_invalid_date_and_heading_context_positive(heading: str, body_text: str, invalid_date_str: str):
    """달력상 부존재 날짜(4월 31일, 6월 31일, 평년 2월 29일) 및 소제목 문맥 반영 양성 3건 검증 (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inv_findings = [f for f in findings if f.type == FindingType.EVIDENCE_DATE_INVALID]
    assert len(inv_findings) == 1

    f = inv_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    # 소제목 문맥이 detail과 confidence_features에 정확히 보존되는지 확인 (문맥 문장은 제외)
    assert f"[{heading}]" in f.detail
    assert f.confidence_features.get("heading") == heading
    assert invalid_date_str.rstrip(".") in f.title or invalid_date_str.rstrip(".") in f.detail


@pytest.mark.parametrize(
    "heading,body_text",
    [
        # 대조군 1: 4월 30일 (달력상 정상 일자)
        ("1. 물품 검수 및 출고 경위", "검수 완료 후 2025-04-30 출고 전표를 발행했습니다."),
        # 대조군 2: 3월 31일 (달력상 정상 일자)
        ("가. 2차 물품 반입 확인", "반입 일자는 2025-03-31 기재되어 확인을 요청했습니다."),
        # 대조군 3: 윤년 2월 29일 (2024년은 윤년으로 2월 29일 존재)
        ("(1) 계약 체결 일정", "계약 체결일은 2024. 2. 29. 체결된 사실이 확인됩니다."),
    ],
)
def test_valid_date_and_heading_control_cases(heading: str, body_text: str):
    """달력상 존재하는 정상 날짜 대조군 3건 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inv_findings = [f for f in findings if f.type == FindingType.EVIDENCE_DATE_INVALID]
    assert len(inv_findings) == 0


@pytest.mark.parametrize(
    "text",
    [
        # 비날짜 숫자열 1: 문서 번호 형식 (끝자리가 32인 일련번호)
        "관련 문서 접수 번호는 제2025-04-32호로 등록되어 보관 중입니다.",
        # 비날짜 숫자열 2: 코드 번호 형식 (끝자리가 35인 관리코드)
        "자재 식별 관리 코드는 2026.05.35 규격에 맞춰 분류되었습니다.",
        # 비날짜 숫자열 3: 수량·도면 번호 형식 (끝자리가 33인 식별번호)
        "도면 식별 번호 2024.11.33 사양을 기준으로 현장 시공을 진행하였습니다.",
    ],
)
def test_non_date_number_sequence_32_to_35_control_cases(text: str):
    """날짜 모양이지만 날짜가 아닌 숫자열(마지막 자리가 32~35인 번호·수량 등) 대조군 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(text)
    findings = verify_dates_in_document(doc)

    inv_findings = [f for f in findings if f.type == FindingType.EVIDENCE_DATE_INVALID]
    assert len(inv_findings) == 0


def test_heading_line_regex_defects_fixed_validation():
    """HEADING_LINE_RE 결함 3가지(교대 우선순위 묶음, [가-하] 음절 범위, [조항조] 중복) 수정 검증 (한국어 주석)."""
    from packages.claim_engine.date_verifier import HEADING_LINE_RE

    # 1. 교대 우선순위 묶음: (1), (가)는 매칭되나, 닫는 괄호 없는 '(1 제목'은 매칭되지 않아야 함
    assert HEADING_LINE_RE.match("(1) 계약 체결") is not None
    assert HEADING_LINE_RE.match("(가) 사실관계 요약") is not None
    assert HEADING_LINE_RE.match("(1 계약 체결") is None

    # 2. 목차 기호 [가나다라마바사아자차카타파하]: 목차 기호는 매칭되고, 일반 단어로 시작하는 줄은 매칭되지 않아야 함
    assert HEADING_LINE_RE.match("가. 당사자 관계") is not None
    assert HEADING_LINE_RE.match("하. 결론 및 요청사항") is not None
    assert HEADING_LINE_RE.match("가방을 들고 사무실에 출근하였습니다.") is None
    assert HEADING_LINE_RE.match("가족들과 함께 식사를 하였습니다.") is None

    # 3. [조항] 중복 제거: 제1조, 제2항 정상 매칭 확인
    assert HEADING_LINE_RE.match("제1조 목적") is not None
    assert HEADING_LINE_RE.match("제2항 적용 범위") is not None

