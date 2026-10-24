# -*- coding: utf-8 -*-
"""A-4 EVI-DATE 동일 주체·동일 대상 결합 인과적 선후 관계 및 민법 기간 계산 검증 시험 (한국어 주석).

이 시험은 R1~R9 보완 사항을 포함하여 다음 사항을 검증한다:
1. 실제 진입점(VerificationPipeline)을 통한 선후 모순 검출 및 소제목 문맥 바인딩.
2. 동일 주체·동일 대상 결합 4대 구조 양성 시험 및 정상 대조군 시험.
3. 민법 제157조(초일 불산입 원칙)·제159조·제160조(역에 의한 월·년 계산, 말일 보정) 기간 만료일 산정 검증.
4. 앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 및 정정·장래·별개 주체 제외 대조군 검증 (오탐 0건).
5. 7대 선후 쌍 3변형(어순, 연결어미, 동의어) 21문장 양성 시험.
6. R1~R9 요구사항별 단위·통합 검증 시험:
   - R1: 사건 낱말 없는 절 슬롯 0개 검증 (날짜만, 다음 날만, N개월 근무만).
   - R2: 복수 사건 연결어미 및 관형절 양성 검증.
   - R3: 문서 명사 대상 추출 및 행위 사건 분리 검증 ('신청서를 제출했다').
   - R4: 엄격 대상 일치 대조군('1차 계약' vs '2차 계약', 'A 처분' vs 'B 처분') 및 지시어 해소 양성.
   - R5: 주체 분별 ('원고 신청 -> 법원 처분' 양성, '원고 신청 -> 원고 처분' 오탐 제외).
   - R6: 5대 제외 문맥 대조군 및 판결 언급 포함 진짜 역전 양성.
   - R7: 새 주기 정상 대조군('퇴사 후 다시 입사') 및 글쓴이가 밝힌 순서 역전 양성.
   - R8: 두 기간 병기 정상 대조군 및 한 기간 시작일>종료일 역전 양성.
   - R9: 규칙 8 삭제 확인 및 연도 생략 날짜 양성 2개 검증.
7. 문장 길이 1배 및 4배 스케일링 성능비 < 8배 검증.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import time

import pytest

from packages.claim_engine.date_verifier import (
    EVENT_ORDER_RULES,
    _add_civil_period,
    _extract_clause_slots,
    verify_dates_in_document,
)
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
    "heading,body_text,expected_sub_rule,expected_grade",
    [
        # 양성 1 (규칙 1-A1): 동일 주체의 입사일-퇴사일 역전
        (
            "1. 근로관계 경위",
            "신청인의 입사일은 2024. 6. 10.이고 최종 퇴사일은 2024. 5. 15.입니다.",
            "SAME_SUBJECT_LIFECYCLE",
            EvidenceGrade.B,
        ),
        # 양성 2 (R2): 관형절로 이어진 두 사건 선후 역전
        (
            "가. 처분 경위",
            "행정청이 2024. 8. 15. 내린 불승인처분은 원고가 2024. 8. 25. 낸 허가신청에 대한 것입니다.",
            "TARGET_BOUND_DISPOSITION",
            EvidenceGrade.B,
        ),
        # 양성 3: 선행 신청을 직접 대상으로 삼은('~에 대한') 후행 처분 발령일 역전
        (
            "2. 처분 경위",
            "최초 허가신청 2024. 9. 12.에 대한 불승인처분은 2024. 9. 5.에 발령되었습니다.",
            "TARGET_BOUND_DISPOSITION",
            EvidenceGrade.B,
        ),
        # 양성 4: 선행 계약 후 지시어('그 계약에 대한')로 결합된 해제 통지일 역전
        (
            "3. 해제 통지",
            "원고는 2024. 7. 20. 공급계약을 체결하였고, 그 계약에 대한 해제 통지는 2024. 7. 10.에 발송되었습니다.",
            "ANAPHORIC_TARGET_INVERSION",
            EvidenceGrade.B,
        ),
        # 양성 5: 동일 행위 명사 결합 상대 일자('다음 날인') 역산 모순 (C등급)
        (
            "4. 통지 수령",
            "결정도달서를 2024-03-15 처음 수령했고 수령 다음 날인 2024-03-14에 재심청구했다.",
            "RELATIVE_NEXT_DAY_INVERSION",
            EvidenceGrade.C,
        ),
        # 양성 6 (R9): 연도 생략 날짜 사건 역전 1
        (
            "5. 발송 및 도달",
            "2024년 최고서를 8월 15일에 발송하였으나, 상대방은 8월 10일에 이미 수령하였습니다.",
            "SEND_BEFORE_RECEIPT",
            EvidenceGrade.B,
        ),
        # 양성 7 (R9): 연도 생략 날짜 사건 역전 2
        (
            "6. 소송 접수",
            "2024년 소장을 4. 12. 법원에 접수하였는데 법원의 보정명령은 4. 5.에 발령되었습니다.",
            "RECEIPT_BEFORE_AMENDMENT",
            EvidenceGrade.B,
        ),
        # 양성 8 (R7): 글쓴이가 밝힌 순서 역전 ('그 후' 후속 사건 날짜가 앞섬)
        (
            "7. 순서 역전",
            "원고는 2024. 6. 10. 업무협약을 체결하였습니다. 그 후 입사한 날짜는 2024. 5. 20.입니다.",
            "NARRATIVE_TEMPORAL_ORDER_INVERSION",
            EvidenceGrade.B,
        ),
    ],
)
def test_temporal_event_inversion_positives(
    heading: str, body_text: str, expected_sub_rule: str, expected_grade: EvidenceGrade
):
    """동일 주체·동일 대상 결합 양성 시험 검증 (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) == 1, f"검출 결과 이상: {findings}"

    f = inversion_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    assert f.evidence_grade == expected_grade
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
        # 정상 대조군 2: 선행 신청일 이후에 거부처분이 발령된 정상 순서
        (
            "2. 처분 경위",
            "최초 허가신청 2024. 9. 5.에 대한 불승인처분은 2024. 9. 12.에 발령되었습니다.",
        ),
        # 정상 대조군 3: 수령 다음 날(민법 제157조 초일 불산입 +1일)이 정확히 일치하는 정상 서술
        (
            "3. 통지 수령",
            "결정도달서를 2024-03-15 처음 수령했고 수령 다음 날인 2024-03-16에 재심청구했다.",
        ),
    ],
)
def test_temporal_event_normal_sequence_controls(heading: str, body_text: str):
    """인과관계 및 달력 순서와 일치하는 정상 대조군 검증 (오탐 0건) (한국어 주석)."""
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
        # 1차 오탐 5꼴 × 2문장 대조군
        # 꼴 1: 나중 서면이 앞선 처분을 다툼 (2문장)
        (
            "1. 소 제기 경위",
            "원고는 2024. 5. 10. 취소소장을 제출하여 2024. 3. 15.자 과징금부과처분의 취소를 구합니다.",
        ),
        (
            "1-2. 이의신청 경위",
            "신청인은 2024. 6. 20. 이의신청서를 내면서 2024. 4. 10.자 영업정지처분의 위법함을 다투고자 합니다.",
        ),
        # 꼴 2: '~에 따라' 참조 (2문장)
        (
            "2. 서류 제출",
            "신청인은 2024. 6. 1. 보정명령에 따라 2024. 4. 10.자 결정문을 제출하였습니다.",
        ),
        (
            "2-2. 계획서 제출",
            "피고는 2024. 7. 15. 행정청의 처분에 따라 2024. 5. 2.자 조치계획서를 제출하였습니다.",
        ),
        # 꼴 3: 나중 청구 대상이 앞선 결정 (2문장)
        (
            "3. 심판청구 대상",
            "2024. 7. 15. 제기된 이 사건 심판청구는 2024. 5. 20. 내려진 기각결정을 대상으로 한다.",
        ),
        (
            "3-2. 재심청구 대상",
            "2024. 8. 1. 접수된 재심청구는 2024. 6. 10.자 초심결정을 대상으로 삼고 있습니다.",
        ),
        # 꼴 4: 앞선 회신 첨부 (2문장)
        (
            "4. 입증 방법",
            "원고는 2024. 8. 10. 준비서면을 제출하면서 2024. 6. 5. 수신한 회신 공문을 별지로 첨부하였다.",
        ),
        (
            "4-2. 소명자료 제출",
            "신청인은 2024. 9. 12. 소명자료를 내며 2024. 7. 20.자 질의회신 문서를 첨부하였습니다.",
        ),
        # 꼴 5: '~를 거쳐' 회고 (2문장)
        (
            "5. 전심 절차",
            "청구인은 2024. 9. 1. 이의신청을 거쳐 2024. 7. 1.자 처분의 위법성을 다투고자 합니다.",
        ),
        (
            "5-2. 소송 제기",
            "원고는 2024. 10. 5. 전심 절차를 거쳐 2024. 8. 15.자 불승인 결정을 다투는 소송을 제기했습니다.",
        ),
        # 정정 서술 (~가 아니라 ~로 정정한다)
        (
            "6. 사실관계 정정",
            "입사일은 2024. 6. 10.이고 최종 퇴사일은 2024. 5. 15.이 아니라 2024. 8. 15.로 정정하여 기재합니다.",
        ),
        # 별개 주체의 대립 행위 (원고 vs 피고)
        (
            "7. 당사자 주장",
            "원고는 2024. 6. 10. 의견서를 제출하였고, 피고는 2024. 5. 15. 행정 조사를 완료하였습니다.",
        ),
    ],
)
def test_temporal_event_retrospective_and_exclusion_controls(heading: str, body_text: str):
    """앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 및 정정·별개 주체 대조군 검증 (오탐 0건) (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) == 0


def test_temporal_event_exclusion_controls():
    """조건 8: 되살린 test_temporal_event_exclusion_controls 복구 검증 (한국어 주석)."""
    controls = [
        ("1. 처분 다툼", "원고는 2024. 5. 10. 취소소장을 제출하여 2024. 3. 15.자 과징금부과처분의 취소를 구합니다."),
        ("2. 명령 참조", "신청인은 2024. 6. 1. 보정명령에 따라 2024. 4. 10.자 결정문을 제출하였습니다."),
        ("3. 대상 지정", "2024. 7. 15. 제기된 이 사건 심판청구는 2024. 5. 20. 내려진 기각결정을 대상으로 한다."),
        ("4. 회신 첨부", "원고는 2024. 8. 10. 준비서면을 제출하면서 2024. 6. 5. 수신한 회신 공문을 별지로 첨부하였다."),
        ("5. 전심 회고", "청구인은 2024. 9. 1. 이의신청을 거쳐 2024. 7. 1.자 처분의 위법성을 다투고자 합니다."),
    ]
    for h, b in controls:
        doc = _make_doc(h, b)
        findings = verify_dates_in_document(doc)
        inversion_findings = [
            f for f in findings
            if f.type == FindingType.TIMELINE_CONTRADICTION
            and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
        ]
        assert len(inversion_findings) == 0, f"오탐 발생: {h} - {b}"


@pytest.mark.parametrize(
    "pair_idx,variant_name,heading,body_text",
    [
        # 1. 신청 -> 처분 (행정절차법 제17조)
        (1, "어순 역전", "1-1. 처분", "불승인처분은 2024. 9. 5.에 발령되었는데, 그 처분의 대상인 허가신청은 2024. 9. 12.에 있었습니다."),
        (1, "연결어미 변형", "1-2. 처분", "신청인은 2024. 9. 12. 변경신청을 한바, 관할청의 거부처분은 2024. 9. 5.에 이미 내려졌습니다."),
        (1, "동의어 변형", "1-3. 처분", "원고는 2024. 9. 12. 재심청구를 제출하였으나, 이에 대한 기각결정은 2024. 9. 5.에 발령되었습니다."),
        # 2. 발송 -> 도달 (민법 제111조)
        (2, "어순 역전", "2-1. 도달", "해당 서류를 수령한 날은 2024. 8. 10.인데, 우편물의 발송일은 2024. 8. 15.로 확인되었습니다."),
        (2, "연결어미 변형", "2-2. 도달", "피고가 2024. 8. 15. 최고서를 발송한 뒤, 원고는 2024. 8. 10.에 이를 수령하였습니다."),
        (2, "동의어 변형", "2-3. 도달", "원고가 2024. 8. 15. 통지서를 송부하였으나, 피고는 2024. 8. 10.에 이미 송달받았다고 주장합니다."),
        # 3. 체결 -> 해지/이행 (민법 제543조)
        (3, "어순 역전", "3-1. 계약", "공급계약에 대한 해제 통지는 2024. 7. 10.에 있었고, 원고와 피고 사이의 공급계약 체결일은 2024. 7. 20.입니다."),
        (3, "연결어미 변형", "3-2. 계약", "당사자들은 2024. 7. 20. 매매계약을 체결한바, 매매계약 해지 통지는 2024. 7. 10.에 발송되었습니다."),
        (3, "동의어 변형", "3-3. 계약", "원고는 2024. 7. 20. 업무협약을 약정하였으나, 그 협약의 해제 통지는 2024. 7. 10.에 도달하였습니다."),
        # 4. 입사 -> 퇴사 (근로기준법 제2조)
        (4, "어순 역전", "4-1. 근로", "근로자의 최종 퇴사일은 2024. 5. 15.인데, 회사의 입사일은 2024. 6. 10.로 적혀 있습니다."),
        (4, "연결어미 변형", "4-2. 근로", "신청인은 2024. 6. 10. 회사에 입사한 뒤, 2024. 5. 15.에 사직하였습니다."),
        (4, "동의어 변형", "4-3. 근로", "피고 회사는 2024. 6. 10. 원고를 채용하였으나, 원고에 대한 해고 통지는 2024. 5. 15.에 이루어졌습니다."),
        # 5. 접수 -> 보정 (민사소송법 제254조)
        (5, "어순 역전", "5-1. 소송", "소장에 대한 보정명령은 2024. 4. 5.에 내려졌으나, 법원에 소장을 접수한 날은 2024. 4. 12.입니다."),
        (5, "연결어미 변형", "5-2. 소송", "원고가 2024. 4. 12. 사건을 접수한바, 법원의 보정명령은 2024. 4. 5.에 발령되었습니다."),
        (5, "동의어 변형", "5-3. 소송", "신청서가 2024. 4. 12. 법원에 접수되었으나, 재판장의 보정권고는 2024. 4. 5.에 내려졌습니다."),
        # 6. 발생 -> 청구 (상법 제724조)
        (6, "어순 역전", "6-1. 보험", "피해자는 2024. 3. 10. 보험금을 청구하였고, 이 사건 사고발생일은 2024. 3. 20.입니다."),
        (6, "연결어미 변형", "6-2. 보험", "교통사고가 2024. 3. 20. 발생한바, 손해배상 청구는 2024. 3. 10.에 이미 제기되었습니다."),
        (6, "동의어 변형", "6-3. 보험", "손해는 2024. 3. 20. 발생하였으나, 그에 대한 손해배상금 지급청구는 2024. 3. 10.에 접수되었습니다."),
        # 7. 기간시작 -> 기간종료 (민법 제157조)
        (7, "어순 역전", "7-1. 임대", "임대차의 종료일은 2024. 10. 15.이고, 임대차 개시일은 2024. 11. 1.로 기재되었습니다."),
        (7, "연결어미 변형", "7-2. 임대", "근무기간은 2024. 11. 1.부터 시작하여, 그 기간의 종료는 2024. 10. 15.로 정하였습니다."),
        (7, "동의어 변형", "7-3. 임대", "계약의 기산일은 2024. 11. 1.이며, 계약의 만료일은 2024. 10. 15.입니다."),
    ],
)
def test_temporal_event_seven_pairs_three_variants(
    pair_idx: int, variant_name: str, heading: str, body_text: str
):
    """조건 8: 7대 선후 쌍 각각 양성 1개 이상 × 세 변형(어순, 연결어미, 동의어) 21문장 검증 (한국어 주석)."""
    doc = _make_doc(heading, body_text)
    findings = verify_dates_in_document(doc)

    inversion_findings = [
        f for f in findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversion_findings) >= 1, f"검출 실패: 쌍 {pair_idx} ({variant_name}) - {body_text}"
    f = inversion_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    assert f.evidence_grade == EvidenceGrade.B


# ==============================================================================
# R1~R9 원인별 보완 검증 전용 단위 시험
# ==============================================================================

def test_r1_empty_event_clause_no_slot():
    """R1: 사건 낱말이 없는 절은 슬롯을 생성하지 않는다 (날짜만, 다음 날만, N개월 근무만 각 슬롯 0개)."""
    # 1) 날짜만 있는 절
    slots_date_only = _extract_clause_slots("2024. 5. 10.에.")
    assert len(slots_date_only) == 0, f"날짜만 있는 절에 슬롯이 생성됨: {slots_date_only}"

    # 2) '다음 날'만 있는 절
    slots_next_only = _extract_clause_slots("다음 날에.")
    assert len(slots_next_only) == 0, f"'다음 날'만 있는 절에 슬롯이 생성됨: {slots_next_only}"

    # 3) 'N개월 근무'만 있는 절
    slots_dur_only = _extract_clause_slots("3개월간 근무.")
    assert len(slots_dur_only) == 0, f"'N개월 근무'만 있는 절에 슬롯이 생성됨: {slots_dur_only}"


def test_r2_multiple_events_and_adnominal_clause():
    """R2: 한 문장에 두 사건이 연결어미로 이어진 양성 및 관형절로 이어진 양성 검출 검증."""
    # 연결어미로 두 사건 결합
    t_conn = "신청서가 2024. 9. 20. 접수되었는데 관할청의 거부처분은 2024. 9. 10.에 내려졌습니다."
    doc_conn = _make_doc("1. 소송 경위", t_conn)
    f_conn = [f for f in verify_dates_in_document(doc_conn) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_conn) >= 1

    # 관형절로 두 사건 결합
    t_adnom = "행정청이 2024. 8. 15. 내린 불승인처분은 원고가 2024. 8. 25. 낸 허가신청에 대한 것입니다."
    doc_adnom = _make_doc("2. 처분 경위", t_adnom)
    f_adnom = [f for f in verify_dates_in_document(doc_adnom) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_adnom) >= 1


def test_r3_document_noun_as_object_not_event():
    """R3: '신청서를 제출했다'에서 사건 1개(제출), 대상 1개(신청서)로 바인딩되는지 검증."""
    slots = _extract_clause_slots("2024. 5. 10. 신청서를 제출했습니다.")
    assert len(slots) == 1, f"슬롯이 1개가 아님: {slots}"
    slot = slots[0]
    assert slot.kind == "신청"
    assert slot.surface_form in ("제출", "제출했")
    assert slot.target == "신청서"


def test_r4_strict_target_match_controls_and_positive():
    """R4: 수식어가 다른 대상('1차 계약' vs '2차 계약', 'A 처분' vs 'B 처분') 제외 대조 및 '위 처분' 양성 검증."""
    # 1) '1차 계약' 체결과 '2차 계약' 해제는 대상이 다르므로 비교 제외 대조군
    t_diff_contract = "당사자들은 2024. 7. 20. 1차 계약을 체결하였고, 2024. 7. 10. 2차 계약에 대한 해제 통지가 발송되었습니다."
    doc_diff_c = _make_doc("1. 별개 계약", t_diff_contract)
    assert len([f for f in verify_dates_in_document(doc_diff_c) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 2) 'A 처분'과 'B 처분'은 대상이 다르므로 비교 제외 대조군
    t_diff_disp = "원고는 2024. 9. 12. A 신청을 냈는데, 관할청은 2024. 9. 5. B 처분을 내렸습니다."
    doc_diff_d = _make_doc("2. 별개 처분", t_diff_disp)
    assert len([f for f in verify_dates_in_document(doc_diff_d) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 3) '위 처분'이 직전 '과징금 부과처분'과 묶이는 지시어 해소 양성
    t_anaphora = "원고는 2024. 9. 12. 과징금 부과처분에 대한 재심청구를 제출하였으나, 위 처분은 2024. 9. 5.에 이미 발령되었습니다."
    doc_ana = _make_doc("3. 지시어 결합", t_anaphora)
    f_ana = [f for f in verify_dates_in_document(doc_ana) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_ana) >= 1


def test_r5_subject_differentiation_controls_and_positive():
    """R5: '원고 신청 → 법원 처분' 정상 쌍 양성, '원고 신청 → 원고 처분' 오탐 제외 검증."""
    # 1) 원고 신청 -> 법원 처분: 주체가 다른 상대방 관계 양성
    t_pos = "원고가 2024. 9. 12. 허가신청을 하였으나, 법원의 처분은 2024. 9. 5.에 발령되었습니다."
    doc_pos = _make_doc("1. 정상 상대방 쌍", t_pos)
    f_pos = [f for f in verify_dates_in_document(doc_pos) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_pos) >= 1

    # 2) 원고 신청 -> 원고 처분: 신청과 처분의 주체가 동일인이면 정상 법률 행위가 아니므로 오탐 방지 제외
    t_ctrl = "원고가 2024. 9. 12. 허가신청을 하였고, 원고가 2024. 9. 5. 자체 처분을 내렸습니다."
    doc_ctrl = _make_doc("2. 동일 주체 상대방 오탐 방지", t_ctrl)
    f_ctrl = [f for f in verify_dates_in_document(doc_ctrl) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_ctrl) == 0


def test_r6_five_exclusions_and_real_inversion_with_verdict():
    """R6: 5개 제외 대상 각각 대조 1개(총 5개) 및 진짜 역전에 판결 언급이 있어도 잡히는 양성 검증."""
    # 1) 판례/법령 인용 문맥 대조군
    t_ex1 = "대법원 2024. 5. 10. 선고 판결에 따라 2024. 3. 15.자 처분의 효력이 인정됩니다."
    assert len([f for f in verify_dates_in_document(_make_doc("1. 판례", t_ex1)) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 2) 장래/예정 대조군
    t_ex2 = "원고는 2024. 7. 20. 계약을 체결하였고, 대금은 2024. 7. 10. 변제기 도래 시 지급하기로 예정되어 있었습니다."
    assert len([f for f in verify_dates_in_document(_make_doc("2. 예정", t_ex2)) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 3) 상대방 주장 인용 대조군
    t_ex3 = "피고는 2024. 8. 15. 최고서를 발송하여 2024. 8. 10. 도달했다고 주장하나 이는 이유 없습니다."
    assert len([f for f in verify_dates_in_document(_make_doc("3. 상대방주장", t_ex3)) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 4) 부정 대조군
    t_ex4 = "원고는 2024. 6. 10. 입사한 사실이 없으며, 2024. 5. 15. 퇴사하지도 않았습니다."
    assert len([f for f in verify_dates_in_document(_make_doc("4. 부정", t_ex4)) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 5) 정정 대조군
    t_ex5 = "입사일은 2024. 6. 10.이고 최종 퇴사일은 2024. 5. 15.의 착오로 기재된 것입니다."
    assert len([f for f in verify_dates_in_document(_make_doc("5. 정정", t_ex5)) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 6) 진짜 역전에 단순 판결 언급이 포함되어 있어도 정상 검출되는 양성
    t_real = "원고는 2024. 9. 12. 판결을 위해 허가신청을 냈으나, 관할청의 거부처분은 2024. 9. 5.에 이미 내려졌습니다."
    f_real = [f for f in verify_dates_in_document(_make_doc("6. 진짜 역전", t_real)) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_real) >= 1


def test_r7_new_cycle_control_and_narrative_order_inversion():
    """R7: '퇴사 후 다시 입사' 정상 대조군 및 '그 후 입사(날짜는 이전)' 역전 양성 검증."""
    # 1) 퇴사 후 다시 입사: 새 주기로 정상 대조군
    t_ctrl = "신청인은 2024. 3. 10. 퇴사한 후, 2024. 4. 1. 다시 입사하였습니다."
    doc_ctrl = _make_doc("1. 재입사 정상", t_ctrl)
    assert len([f for f in verify_dates_in_document(doc_ctrl) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 2) 그 후 입사하였으나 날짜가 이전인 역전 양성 (B등급)
    t_pos = "원고는 2024. 6. 10. 업무협약을 체결하였습니다. 그 후 입사한 날짜는 2024. 5. 20.입니다."
    doc_pos = _make_doc("2. 글과 날짜 역전", t_pos)
    f_pos = [f for f in verify_dates_in_document(doc_pos) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_pos) == 1
    assert f_pos[0].evidence_grade == EvidenceGrade.B
    assert f_pos[0].confidence_features.get("sub_rule") == "NARRATIVE_TEMPORAL_ORDER_INVERSION"


def test_r8_concurrent_periods_control_and_inversion():
    """R8: 두 기간 병기 정상 대조군 및 한 기간 안에서 시작일>종료일 역전 양성 검증."""
    # 1) 두 기간 병기: D1~D2와 D3~D4 병기 시 D1과 D4를 비교하지 않는 정상 대조군
    t_ctrl = "1차 임대기간은 2024. 1. 1.부터 2024. 6. 30.까지이고, 2차 임대기간은 2024. 7. 1.부터 2024. 12. 31.까지입니다."
    doc_ctrl = _make_doc("1. 두 기간 병기", t_ctrl)
    assert len([f for f in verify_dates_in_document(doc_ctrl) if f.type == FindingType.TIMELINE_CONTRADICTION]) == 0

    # 2) 한 기간 안에서 시작일 > 종료일 역전 양성
    t_pos = "임대기간은 2024. 10. 31.부터 2024. 10. 1.까지로 기재되었습니다."
    doc_pos = _make_doc("2. 동일 기간 내 시작>종료", t_pos)
    f_pos = [f for f in verify_dates_in_document(doc_pos) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_pos) == 1
    assert f_pos[0].confidence_features.get("sub_rule") == "PERIOD_START_BEFORE_END"


def test_r9_rule8_deleted_and_omitted_year_dates():
    """R9: 규칙 8(접수일 vs 송달일) 삭제 확인 및 연도 생략 날짜 양성 2개 검증."""
    # 1) 규칙 8 삭제 확인: EVENT_ORDER_RULES 에 PERIOD_END_WRITE_INVERSION 또는 RECEIPT_VS_DELIVERY 규칙이 없음
    rule_ids = [r["rule_id"] for r in EVENT_ORDER_RULES]
    assert "PERIOD_END_WRITE_INVERSION" not in rule_ids, "규칙 8(PERIOD_END_WRITE_INVERSION)이 삭제되지 않음"
    assert "RECEIPT_VS_DELIVERY" not in rule_ids, "규칙 8이 삭제되지 않음"

    # 2) 연도 생략 날짜 양성 1: 'M월 D일' 형태
    t_pos1 = "2024년 최고서를 8월 15일에 발송하였으나, 상대방은 8월 10일에 이미 수령하였습니다."
    doc_pos1 = _make_doc("1. 연도 생략 양성 1", t_pos1)
    f_pos1 = [f for f in verify_dates_in_document(doc_pos1) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_pos1) == 1
    assert f_pos1[0].confidence_features.get("cause_date") == "2024-08-15"
    assert f_pos1[0].confidence_features.get("effect_date") == "2024-08-10"

    # 3) 연도 생략 날짜 양성 2: 'M. D.' 형태
    t_pos2 = "2024년 소장을 4. 12. 법원에 접수하였는데 법원의 보정명령은 4. 5.에 발령되었습니다."
    doc_pos2 = _make_doc("2. 연도 생략 양성 2", t_pos2)
    f_pos2 = [f for f in verify_dates_in_document(doc_pos2) if f.type == FindingType.TIMELINE_CONTRADICTION]
    assert len(f_pos2) == 1
    assert f_pos2[0].confidence_features.get("cause_date") == "2024-04-12"
    assert f_pos2[0].confidence_features.get("effect_date") == "2024-04-05"


def test_civil_code_period_calculation_articles_157_159_160():
    """민법 제157조(초일 불산입)·제159조·제160조(역에 의한 월·년 계산, 말일 보정) 단위 검증 (한국어 주석)."""
    start = datetime.date(2024, 1, 31)
    assert _add_civil_period(start, 1, "개월", inclusive=False) == datetime.date(2024, 2, 29)
    assert _add_civil_period(start, 1, "개월", inclusive=True) == datetime.date(2024, 2, 28)

    d_base = datetime.date(2024, 3, 7)
    assert _add_civil_period(d_base, 10, "일", inclusive=False) == datetime.date(2024, 3, 17)
    assert _add_civil_period(d_base, 10, "일", inclusive=True) == datetime.date(2024, 3, 16)


def test_civil_code_period_article_161_holiday_adjustment():
    """민법 제161조(기간의 말일이 토요일 또는 공휴일에 해당하는 때에는 기간은 그 익일로 만료한다) 검증 (한국어 주석)."""
    start = datetime.date(2024, 8, 1)
    assert _add_civil_period(start, 2, "일", inclusive=False, adjust_holiday=False) == datetime.date(2024, 8, 3)
    assert _add_civil_period(start, 2, "일", inclusive=False, adjust_holiday=True) == datetime.date(2024, 8, 5)

    d_feb = datetime.date(2024, 2, 20)
    assert _add_civil_period(d_feb, 10, "일", inclusive=False, adjust_holiday=True) == datetime.date(2024, 3, 4)


def test_temporal_event_inversion_performance_scaling():
    """점검표 2항: 문장 길이 1배 및 4배 스케일링 성능비 < 8배 및 4배 최솟값 < 1초 검증 (한국어 주석)."""
    base_text = (
        "신청인은 2024. 5. 10. 업무 계획서를 제출하였고 관계 부서는 2024. 5. 20. 이를 승인하였습니다. "
        "이후 보완 서류를 준비하여 2024. 6. 1. 정식 접수를 마쳤습니다.\n"
    ) * 20

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

    ratio = min_4x / max(min_1x, 0.0005)

    assert min_4x < 1.0, f"4배 길이 최솟값이 1초 이상입니다: {min_4x:.4f}s"
    assert ratio < 8.0, f"4배/1배 최솟값 비율이 8배 이상입니다: {ratio:.2f}x (1x: {min_1x:.4f}s, 4x: {min_4x:.4f}s)"


# ==============================================================================
# A-4 5차 보완 검증 테스트: U1 ~ U3 전용 검증
# ==============================================================================


def test_u1_narrative_order_and_new_cycle():
    """U1: 글이 밝힌 순서(-ㄴ 뒤, -ㄴ 후, -ㄴ 다음, -다가)와 새 주기(새로, 다시) 검증 (한국어 주석)."""
    # 1. 정상 순서 대조군 (날짜 순서 일치: 오탐 0건)
    normal_cases = [
        "원고는 2020. 3. 1. 퇴직한 뒤 2021. 5. 1. 새로 입사하였습니다.",
        "피고는 2020. 1. 10. 계약을 해지한 다음 2020. 5. 1. 다시 체결하였습니다.",
        "원고는 2020. 2. 1. 퇴사하였다가 2020. 8. 1. 재입사하였습니다.",
    ]
    for text in normal_cases:
        doc = _make_doc("1. 사실관계", text)
        findings = verify_dates_in_document(doc)
        inversions = [
            f for f in findings
            if f.type == FindingType.TIMELINE_CONTRADICTION
            and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
        ]
        assert len(inversions) == 0, f"U1 정상 순서 오탐 발생: {text} -> {inversions}"

    # 2. 날짜 역전 양성군 (글의 순서와 반대 날짜 기재: NARRATIVE_TEMPORAL_ORDER_INVERSION 양성)
    reversed_cases = [
        ("원고는 2022. 3. 1. 퇴직한 뒤 2021. 5. 1. 입사하였습니다.", "2022. 3. 1.", "2021. 5. 1."),
        ("피고는 2022. 1. 10. 계약을 해지한 다음 2021. 5. 1. 체결하였습니다.", "2022. 1. 10.", "2021. 5. 1."),
        ("원고는 2022. 2. 1. 퇴사하였다가 2021. 8. 1. 입사하였습니다.", "2022. 2. 1.", "2021. 8. 1."),
    ]
    for text, d_cause, d_effect in reversed_cases:
        doc = _make_doc("1. 사실관계", text)
        findings = verify_dates_in_document(doc)
        inversions = [
            f for f in findings
            if f.type == FindingType.TIMELINE_CONTRADICTION
            and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
        ]
        assert len(inversions) == 1, f"U1 역전 미탐지: {text} -> {findings}"
        assert inversions[0].confidence_features.get("sub_rule") == "NARRATIVE_TEMPORAL_ORDER_INVERSION"
        assert inversions[0].evidence_grade == EvidenceGrade.B


def test_u2_correction_sentence_handling():
    """U2: 정정 문장('착오이므로', '오기이므로', '바로잡는다') 슬롯 정제 및 역전 검증 (한국어 주석)."""
    # 1. 정정 후 값이 정상 순서인 경우 (정정 후 입사 6. 1. -> 퇴사 7. 1.) -> 오탐 0건
    text_normal = (
        "원고가 2023. 5. 1. 입사하였다고 적은 것은 착오이므로 2023. 6. 1.로 바로잡는다; "
        "원고는 2023. 7. 1. 퇴사하였습니다."
    )
    doc_normal = _make_doc("2. 정정 사항", text_normal)
    findings_normal = verify_dates_in_document(doc_normal)
    inversions_normal = [
        f for f in findings_normal
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversions_normal) == 0, f"U2 정정 후 정상 순서 오탐 발생: {findings_normal}"

    # 2. 정정 후 값도 다른 절과 역전인 경우 (정정 후 입사 8. 1. -> 퇴사 7. 1.) -> 양성 탐지
    text_reversed = (
        "원고가 2023. 5. 1. 입사하였다고 적은 것은 착오이므로 2023. 8. 1.로 바로잡는다; "
        "원고는 2023. 7. 1. 퇴사하였습니다."
    )
    doc_reversed = _make_doc("2. 정정 사항", text_reversed)
    findings_reversed = verify_dates_in_document(doc_reversed)
    inversions_reversed = [
        f for f in findings_reversed
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversions_reversed) >= 1, f"U2 정정 후 역전 미탐지: {findings_reversed}"
    assert inversions_reversed[0].confidence_features.get("sub_rule") == "SAME_SUBJECT_LIFECYCLE"
    assert inversions_reversed[0].evidence_grade == EvidenceGrade.B


def test_u3_passive_intransitive_target_binding():
    """U3: 피동·자동사 사건의 주격/주제어 대상 바인딩 및 '에 관하여' 검증 (한국어 주석)."""
    # 1. '소장은 접수되었는데 … 위 소장에 관하여 보정명령' (접수일 > 보정명령일: 양성)
    text_reversed = "소장은 2024. 5. 10. 접수되었는데, 재판장은 위 소장에 관하여 2024. 4. 20. 보정명령을 발령하였습니다."
    doc_reversed = _make_doc("3. 소송 경과", text_reversed)
    findings_reversed = verify_dates_in_document(doc_reversed)
    inversions_reversed = [
        f for f in findings_reversed
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversions_reversed) == 1, f"U3 소장 접수-보정명령 역전 미탐지: {findings_reversed}"
    assert inversions_reversed[0].confidence_features.get("sub_rule") == "RECEIPT_BEFORE_AMENDMENT"
    assert inversions_reversed[0].evidence_grade == EvidenceGrade.B

    # 2. 같은 꼴 정상 순서 (접수일 <= 보정명령일: 오탐 0건)
    text_normal = "소장은 2024. 4. 20. 접수되었는데, 재판장은 위 소장에 관하여 2024. 5. 10. 보정명령을 발령하였습니다."
    doc_normal = _make_doc("3. 소송 경과", text_normal)
    findings_normal = verify_dates_in_document(doc_normal)
    inversions_normal = [
        f for f in findings_normal
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]
    assert len(inversions_normal) == 0, f"U3 정상 순서 오탐 발생: {findings_normal}"

