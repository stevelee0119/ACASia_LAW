# -*- coding: utf-8 -*-
"""A-4 EVI-DATE 인과적 선후 관계 및 사건 일자 모순 검증 시험 (한국어 주석).

이 시험은 다음 사항을 검증한다:
1. 실제 진입점(VerificationPipeline)을 통한 선후 모순 검출 및 소제목 문맥 바인딩.
2. 동일 주체·동일 대상의 인과적 선후 역전(원인 행위일 > 결과 처분일) 양성 3건 및 정상 대조군 3건.
3. 정정 서술(~로 정정한다, ~가 아니라), 장래 예정/변제기(~할 예정, ~까지 지급하기로),
   별개 주체(원고 vs 피고 분리 행위) 등 제외 꼴 대조군 3건 (오탐 0건).
4. 문장 길이 1배 및 4배 스케일링 성능비 < 8배 검증.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import time
from typing import List

import pytest

from packages.claim_engine.date_verifier import verify_dates_in_document
from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def _make_doc(*texts: str, doc_id: str = "synth_date_doc") -> NormalizedDocument:
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


def test_pipeline_temporal_event_inversion_entrypoint(tmp_path: Path):
    """점검표 1항: 실제 진입점(VerificationPipeline)에서 사건 선후 모순 검출 및 결과 내용 확인 (한국어 주석)."""
    doc_path = tmp_path / "temporal_test_brief.txt"
    doc_path.write_text(
        "2. 계약 해제 통지 경위\n"
        "신청인은 2024. 8. 20. 해제 통지를 발송하였는데, 이는 2024. 7. 15. 통지 도달을 전제로 한 것이었습니다.\n",
        encoding="utf-8",
    )

    pipeline = VerificationPipeline()
    context = ProjectContext(project_id="test_proj_temporal")
    inputs = [
        DocumentInput(
            document_id="doc_temporal_entry",
            path=str(doc_path),
            filename="temporal_test_brief.txt",
            mime_type="text/plain",
        )
    ]

    run_res = pipeline.run("run_temporal_eval", context, inputs)
    assert run_res is not None
    assert len(run_res.documents) == 1

    doc_res = run_res.documents[0]
    inversion_findings = [
        f for f in doc_res.findings
        if f.type == FindingType.TIMELINE_CONTRADICTION and f.evidence_grade == EvidenceGrade.B
    ]
    assert len(inversion_findings) >= 1

    f = inversion_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    assert f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    assert f.confidence_features.get("cause_date") == "2024-08-20"
    assert f.confidence_features.get("effect_date") == "2024-07-15"
    assert "2. 계약 해제 통지 경위" in f.detail


@pytest.mark.parametrize(
    "heading,body_text,expected_cause,expected_effect",
    [
        # 양성 1: 신청일(원인)이 결정일(결과)보다 미래인 모순
        (
            "1. 처분 경위",
            "청구인은 2024. 6. 10. 재심을 신청하여 2024. 5. 15. 기각 결정을 통지받았습니다.",
            "2024-06-10",
            "2024-05-15",
        ),
        # 양성 2: 역순 서술 구조에서 인가 처분일보다 신청일이 미래인 모순
        (
            "가. 사업 인가 경위",
            "2024. 3. 10. 변경 인가 처분이 내려졌으나, 이는 2024. 4. 20. 제출된 서류에 따른 것입니다.",
            "2024-04-20",
            "2024-03-10",
        ),
        # 양성 3: 순차 경과 연결어(이후)로 연결되었으나 날짜가 역전된 모순
        (
            "(1) 물품 공급 내역",
            "공급업체는 2024. 9. 25. 물품을 인도한 이후 2024. 8. 10. 검수 완료 처분을 받았습니다.",
            "2024-09-25",
            "2024-08-10",
        ),
    ],
)
def test_temporal_event_inversion_positives(heading: str, body_text: str, expected_cause: str, expected_effect: str):
    """사건 일자 인과적 선후 역전 양성 3건 검증 (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) == 1

    f = inversion_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    assert f.evidence_grade == EvidenceGrade.B
    assert f.confidence_features.get("cause_date") == expected_cause
    assert f.confidence_features.get("effect_date") == expected_effect
    assert f"[{heading}]" in f.detail


@pytest.mark.parametrize(
    "heading,body_text",
    [
        # 정상 대조군 1: 신청일이 결정일보다 앞선 정상적인 순서
        (
            "1. 처분 경위",
            "청구인은 2024. 5. 15. 재심을 신청하여 2024. 6. 10. 기각 결정을 통지받았습니다.",
        ),
        # 정상 대조군 2: 제출일 이후에 변경 인가 처분이 내려진 정상 순서
        (
            "가. 사업 인가 경위",
            "2024. 4. 20. 변경 인가 처분이 내려졌으며, 이는 2024. 3. 10. 제출된 서류에 따른 것입니다.",
        ),
        # 정상 대조군 3: 인도 후 정상적으로 검수 완료된 순서
        (
            "(1) 물품 공급 내역",
            "공급업체는 2024. 8. 10. 물품을 인도한 이후 2024. 9. 25. 검수 완료 처분을 받았습니다.",
        ),
    ],
)
def test_temporal_event_normal_sequence_controls(heading: str, body_text: str):
    """인과관계와 일치하는 정상 선후 순서 대조군 3건 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) == 0


@pytest.mark.parametrize(
    "heading,body_text",
    [
        # 제외 꼴 1: 정정 서술 (~가 아니라 ~로 정정한다)
        (
            "1. 사실관계 정정",
            "신청서 접수일은 2024. 6. 10.이 아니라 2024. 5. 15.로 정정하여 기재합니다.",
        ),
        # 제외 꼴 2: 장래 이행기/변제기 약정 (~까지 변제하기로 약정)
        (
            "2. 대여금 약정",
            "피고는 2024. 8. 10. 차용증을 작성하며 기한을 2024. 7. 1.로 소급 변제하기로 약정한 사실이 없습니다.",
        ),
        # 제외 꼴 3: 별개 주체의 대립 행위 (원고의 신청 vs 피고의 별개 처분)
        (
            "3. 당사자 주장",
            "원고는 2024. 6. 10. 의견서를 제출하였고, 피고는 2024. 5. 15. 행정 조사를 완료하였습니다.",
        ),
    ],
)
def test_temporal_event_exclusion_controls(heading: str, body_text: str):
    """정정 서술, 장래 이행기 약정, 별개 주체 행위 등 제외 꼴 대조군 3건 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) == 0


def test_temporal_event_inversion_performance_scaling():
    """점검표 2항: 문장 길이 1배 및 4배 스케일링 성능비 < 8배 및 4배 최솟값 < 1초 검증 (한국어 주석)."""
    base_text = (
        "신청인은 2024. 5. 10. 업무 계획서를 제출하였고 관계 부서는 2024. 5. 20. 이를 승인하였습니다. "
        "이후 보완 서류를 준비하여 2024. 6. 1. 정식 접수를 마쳤습니다.\n"
    ) * 20  # 약 2,000자

    text_1x = base_text
    text_4x = base_text * 4

    doc_1x = _make_doc("1. 개요", text_1x)
    doc_4x = _make_doc("1. 개요", text_4x)

    times_1x = []
    for _ in range(3):
        t0 = time.perf_counter()
        verify_dates_in_document(doc_1x)
        times_1x.append(time.perf_counter() - t0)

    times_4x = []
    for _ in range(3):
        t0 = time.perf_counter()
        verify_dates_in_document(doc_4x)
        times_4x.append(time.perf_counter() - t0)

    min_1x = min(times_1x)
    min_4x = min(times_4x)

    # 1x가 너무 작을 경우(0.001초 미만) 분모 안정화
    ratio = min_4x / max(min_1x, 0.0005)

    assert min_4x < 1.0, f"4배 길이 최솟값이 1초 이상입니다: {min_4x:.4f}s"
    assert ratio < 8.0, f"4배/1배 최솟값 비율이 8배 이상입니다: {ratio:.2f}x (1x: {min_1x:.4f}s, 4x: {min_4x:.4f}s)"
