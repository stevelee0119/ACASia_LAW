# -*- coding: utf-8 -*-
"""A-4 EVI-DATE 동일 주체·동일 대상 결합 인과적 선후 관계 및 민법 기간 계산 검증 시험 (한국어 주석).

이 시험은 다음 사항을 검증한다:
1. 실제 진입점(VerificationPipeline)을 통한 선후 모순 검출 및 소제목 문맥 바인딩.
2. 동일 주체·동일 대상 결합 4대 구조(개시-종료, 선행신청-대상처분, 기간종료-최초작성, 상대일자·시각 역전)
   양성 시험 및 정상 대조군 시험.
3. 민법 제157조(초일 불산입 원칙)·제159조·제160조(역에 의한 월·년 계산, 말일 보정) 기간 만료일 산정 검증.
4. 앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 5종(처분 다툼, '~에 따라' 참조, 앞선 결정을 대상으로 함,
   앞선 회신 첨부, '~를 거쳐' 회고) 및 정정·장래·별개 주체 제외 대조군 검증 (오탐 0건).
5. 문장 길이 1배 및 4배 스케일링 성능비 < 8배 검증.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import time

import pytest

from packages.claim_engine.date_verifier import _add_civil_period, verify_dates_in_document
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
    """점검표 1항: 실제 진입점(VerificationPipeline)에서 동일 대상 결합 사건 선후 모순 검출 확인 (한국어 주석)."""
    doc_path = tmp_path / "temporal_test_brief.txt"
    doc_path.write_text(
        "2. 처분 발령 경위\n"
        "최초 변경신청 2024. 8. 20.에 대한 거부처분은 2024. 7. 15.에 발령되었습니다.\n",
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
    assert f.confidence_features.get("sub_rule") == "TARGET_BOUND_DISPOSITION"
    assert f.confidence_features.get("cause_date") == "2024-08-20"
    assert f.confidence_features.get("effect_date") == "2024-07-15"
    assert "2. 처분 발령 경위" in f.detail


@pytest.mark.parametrize(
    "heading,body_text,expected_sub_rule",
    [
        # 양성 1 (규칙 1-A1): 동일 주체의 개시일(입사일)-종료일(최종 퇴사일) 역전
        (
            "1. 근로관계 경위",
            "신청인의 입사일은 2024. 6. 10.이고 최종 퇴사일은 2024. 5. 15.입니다.",
            "SAME_SUBJECT_LIFECYCLE",
        ),
        # 양성 2 (규칙 1-A2): 입사일 후 N개월 근무 뒤 사직 통지 발송일 역전 (민법 제157조·제160조)
        (
            "가. 사직 경위",
            "피고는 입사일을 2024. 4. 10.로 적었습니다. 두 달 근무한 뒤 보냈다는 사직 통지의 발송일은 2024. 3. 25.입니다.",
            "LIFECYCLE_DURATION_INVERSION",
        ),
        # 양성 3 (규칙 1-B1): 선행 신청을 직접 대상으로 삼은('~에 대한') 후행 처분 발령일 역전
        (
            "2. 처분 경위",
            "최초 허가신청 2024. 9. 12.에 대한 불승인처분은 2024. 9. 5.에 발령되었습니다.",
            "TARGET_BOUND_DISPOSITION",
        ),
        # 양성 4 (규칙 1-B2): 선행 계약 후 지시어('그 계약에 대한')로 결합된 해제 통지일 역전
        (
            "3. 해제 통지",
            "원고는 2024. 7. 20. 공급계약을 체결하였고, 그 계약에 대한 해제 통지는 2024. 7. 10.에 발송되었습니다.",
            "ANAPHORIC_TARGET_INVERSION",
        ),
        # 양성 5 (규칙 2): 동일 행위 기간 종료('끝난 뒤') 후 최초 문서 작성일 역전
        (
            "4. 정산 내역",
            "실제 임대기간은 2024. 10. 1.부터 2024. 10. 31.까지이고, 임대가 끝난 뒤 처음 확인서를 작성한 날은 2024. 10. 20.입니다.",
            "PERIOD_END_WRITE_INVERSION",
        ),
        # 양성 6 (규칙 3): 동일 행위 명사 결합 상대 일자('다음 날인') 역산 모순 (민법 제157조)
        (
            "5. 통지 수령",
            "결정도달서를 2024-03-15 처음 수령했고 수령 다음 날인 2024-03-14에 재심청구했다.",
            "RELATIVE_NEXT_DAY_INVERSION",
        ),
        # 양성 7 (규칙 4-A): 동일 일자 내 지시어('그 <명사>보다 앞선') 결합 시각 역전
        (
            "6. 연락 시각",
            "결제 시각은 2024-05-10 14:20이고 그 결제보다 20분 앞선 안내는 같은 날 15:00이다.",
            "SAME_DAY_EARLIER_TIME_INVERSION",
        ),
        # 양성 8 (규칙 4-B): 동일 목적물 최초 확보 시각 vs 같은 날 이미 인계된 시각 역전
        (
            "7. 물품 인계",
            "2024. 8. 12. 16:30에 기록매체를 처음 확보하였습니다. 목록에는 그 매체가 같은 날 15:40에 이미 담당 부서에 인계되었다고 적었습니다.",
            "SAME_OBJECT_FIRST_ACQUIRE_TIME_INVERSION",
        ),
    ],
)
def test_temporal_event_inversion_positives(heading: str, body_text: str, expected_sub_rule: str):
    """동일 주체·동일 대상 결합 4대 구조 양성 시험 검증 (한국어 주석)."""
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
    assert f.confidence_features.get("sub_rule") == expected_sub_rule
    assert f"[{heading}]" in f.detail


@pytest.mark.parametrize(
    "heading,body_text",
    [
        # 정상 대조군 1: 입사일보다 최종 퇴사일이 나중인 정상 순서
        (
            "1. 근로관계 경위",
            "신청인의 입사일은 2024. 5. 15.이고 최종 퇴사일은 2024. 6. 10.입니다.",
        ),
        # 정상 대조군 2: 입사일로부터 두 달 근무한 뒤 민법 기간 만료일 이후에 사직 통지 발송
        (
            "가. 사직 경위",
            "피고는 입사일을 2024. 4. 10.로 적었습니다. 두 달 근무한 뒤 보냈다는 사직 통지의 발송일은 2024. 6. 15.입니다.",
        ),
        # 정상 대조군 3: 선행 신청일 이후에 거부처분이 발령된 정상 순서
        (
            "2. 처분 경위",
            "최초 허가신청 2024. 9. 5.에 대한 불승인처분은 2024. 9. 12.에 발령되었습니다.",
        ),
        # 정상 대조군 4: 임대기간 종료일 이후에 확인서를 처음 작성한 정상 순서
        (
            "4. 정산 내역",
            "실제 임대기간은 2024. 10. 1.부터 2024. 10. 31.까지이고, 임대가 끝난 뒤 처음 확인서를 작성한 날은 2024. 11. 2.입니다.",
        ),
        # 정상 대조군 5: 수령 다음 날(민법 제157조 초일 불산입 +1일)이 정확히 일치하는 정상 서술
        (
            "5. 통지 수령",
            "결정도달서를 2024-03-15 처음 수령했고 수령 다음 날인 2024-03-16에 재심청구했다.",
        ),
        # 정상 대조군 6: 동일 일자 내 앞선 안내 시각이 결제 시각보다 실제로 이른 정상 서술
        (
            "6. 연락 시각",
            "결제 시각은 2024-05-10 14:20이고 그 결제보다 20분 앞선 안내는 같은 날 14:00이다.",
        ),
        # 정상 대조군 7: 최초 확보 시각 이후에 같은 날 인계된 정상 서술
        (
            "7. 물품 인계",
            "2024. 8. 12. 15:40에 기록매체를 처음 확보하였습니다. 목록에는 그 매체가 같은 날 16:30에 이미 담당 부서에 인계되었다고 적었습니다.",
        ),
    ],
)
def test_temporal_event_normal_sequence_controls(heading: str, body_text: str):
    """인과관계 및 달력·시각 순서와 일치하는 정상 대조군 검증 (오탐 0건) (한국어 주석)."""
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
        # 회고 정상 대조군 1: 나중 서면이 앞선 처분을 다툼
        (
            "1. 소 제기 경위",
            "원고는 2024. 5. 10. 취소소장을 제출하여 2024. 3. 15.자 과징금부과처분의 취소를 구합니다.",
        ),
        # 회고 정상 대조군 2: '~에 따라' 앞선 문서를 참조·제출
        (
            "2. 서류 제출",
            "신청인은 2024. 6. 1. 보정명령에 따라 2024. 4. 10.자 결정문을 제출하였습니다.",
        ),
        # 회고 정상 대조군 3: 나중 청구의 대상이 앞선 결정
        (
            "3. 심판청구 대상",
            "2024. 7. 15. 제기된 이 사건 심판청구는 2024. 5. 20. 내려진 기각결정을 대상으로 한다.",
        ),
        # 회고 정상 대조군 4: 나중 서면에 앞선 회신을 첨부
        (
            "4. 입증 방법",
            "원고는 2024. 8. 10. 준비서면을 제출하면서 2024. 6. 5. 수신한 회신 공문을 별지로 첨부하였다.",
        ),
        # 회고 정상 대조군 5: '~를 거쳐' 앞선 처분을 회고 서술
        (
            "5. 전심 절차",
            "청구인은 2024. 9. 1. 이의신청을 거쳐 2024. 7. 1.자 처분의 위법성을 다투고자 합니다.",
        ),
        # 제외 꼴 6: 정정 서술 (~가 아니라 ~로 정정한다)
        (
            "6. 사실관계 정정",
            "입사일은 2024. 6. 10.이고 최종 퇴사일은 2024. 5. 15.이 아니라 2024. 8. 15.로 정정하여 기재합니다.",
        ),
        # 제외 꼴 7: 별개 주체의 대립 행위 (원고 vs 피고)
        (
            "7. 당사자 주장",
            "원고는 2024. 6. 10. 의견서를 제출하였고, 피고는 2024. 5. 15. 행정 조사를 완료하였습니다.",
        ),
    ],
)
def test_temporal_event_retrospective_and_exclusion_controls(heading: str, body_text: str):
    """앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 5종 및 정정·별개 주체 대조군 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) == 0


def test_civil_code_period_calculation_articles_157_159_160():
    """민법 제157조(초일 불산입)·제159조·제160조(역에 의한 월·년 계산, 말일 보정) 단위 검증 (한국어 주석)."""
    start = datetime.date(2024, 1, 31)
    # 2024년은 윤년이므로 1월 31일로부터 1개월(민법 제160조 제3항 말일 보정):
    # 초일 불산입 시 만료일은 2024-02-29, 초일 산입 시 최소 만료일은 2024-02-28
    assert _add_civil_period(start, 1, "개월", inclusive=False) == datetime.date(2024, 2, 29)
    assert _add_civil_period(start, 1, "개월", inclusive=True) == datetime.date(2024, 2, 28)

    # 일 단위 계산: 2024-03-07로부터 10일 -> 초일 불산입 2024-03-17, 초일 산입 2024-03-16
    d_base = datetime.date(2024, 3, 7)
    assert _add_civil_period(d_base, 10, "일", inclusive=False) == datetime.date(2024, 3, 17)
    assert _add_civil_period(d_base, 10, "일", inclusive=True) == datetime.date(2024, 3, 16)


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
