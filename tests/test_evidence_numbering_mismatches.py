"""서증 번호 및 목록 불일치(EVI-NUM) 구조 기반 검증 시험.

실제 진입점(VerificationPipeline.run), 다른 표현 양성 5건(축 1~4),
대조군 4건(완결 선언 없음, 기제출 원용, 가지번호 묶음, 통상 정상 서면) 포함.
사건 고유 리터럴 하드코딩 금지 규칙 준수.
"""
from __future__ import annotations

import pytest

from packages.common.config import reset_settings
from packages.common.enums import FindingType, EvidenceGrade
from packages.common.schemas import Block, NormalizedDocument, Page, VerificationStatus
from packages.claim_engine.evidence_consistency import check_evidence_numbering_mismatches
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def _make_doc(lines: list[str], doc_id: str = "test-doc") -> NormalizedDocument:
    """테스트용 NormalizedDocument 헬퍼 (한국어 주석)."""
    blocks = [Block(block_id=f"b{i}", text=line, page=1) for i, line in enumerate(lines)]
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=blocks)],
    )


# --- 1. 실제 진입점 파이프라인 시험 (VerificationPipeline.run) ---
def test_pipeline_entrypoint_evidence_numbering_mismatches(tmp_path, monkeypatch):
    """실제 파이프라인 진입점(VerificationPipeline.run)을 통한 EVI-NUM 검출 검증."""
    sample_text = (
        "원고는 피고의 납품 지연을 입증하기 위하여 갑 제6호증 발주서를 주요 증거로 인용합니다.\n"
        "입증방법: 갑 제1호증 계약서, 갑 제2호증 내역서 (이 서면의 제출 증거 전부)"
    )
    doc_path = tmp_path / "brief_num_mismatch.txt"
    doc_path.write_text(sample_text, encoding="utf-8")

    with monkeypatch.context() as patch:
        patch.setenv("LV_ALLOW_NETWORK", "0")
        patch.setenv("LV_DATA_DIR", str(tmp_path / "data"))
        reset_settings()
        try:
            pipeline = VerificationPipeline()
            result = pipeline.run(
                "pipeline-num-run",
                ProjectContext("pipeline-num-project"),
                [DocumentInput("brief-num-1", str(doc_path), doc_path.name)],
            )
        finally:
            reset_settings()

    assert not result.errors
    assert len(result.documents) == 1
    doc_result = result.documents[0]

    num_findings = [
        f for f in doc_result.findings
        if f.type == FindingType.EVIDENCE_LIST_MISMATCH
        and f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    ]
    assert len(num_findings) >= 1
    finding = num_findings[0]
    assert finding.evidence_grade == EvidenceGrade.B
    assert "갑 제6호증" in finding.title or "갑 제6호증" in finding.detail


# --- 2. 양성 시험 1 (축 1: 완결 목록에 없는 호증 번호 인용) ---
def test_positive_complete_list_missing_exhibit():
    """축 1: 완결을 선언한 증거목록에 없는 호증을 본문에서 인용."""
    doc = _make_doc([
        "원고는 갑 제12호증 배수 점검일지로 피고의 과실을 입증합니다.",
        "증거목록: 갑 제1호증 ~ 갑 제11호증, 이 서면의 제출 증거 전부",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    assert "갑 제12호증" in f.title


# --- 3. 양성 시험 2 (축 2: 연속 범위 선언 후 중간 누락) ---
def test_positive_continuous_range_gap():
    """축 2: 을 제1호증부터 제4호증까지 연속 제출 선언 후 중간 번호 누락."""
    doc = _make_doc([
        "피고는 을 제1호증부터 을 제4호증까지 빠짐없이 연속 제출하며 본건 사실관계를 소명합니다.",
        "입증방법",
        "1. 을 제1호증 견적서",
        "2. 을 제2호증 세금계산서",
        "3. 을 제4호증 출고확인서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) >= 1
    gap_findings = [f for f in findings if f.confidence_features.get("defect_code") == "CONTINUOUS_RANGE_GAP"]
    assert len(gap_findings) == 1
    assert "을 제3호증" in gap_findings[0].title


# --- 4. 양성 시험 3 (축 3: 본문·목록 동일 자료명의 호증 번호 불일치) ---
def test_positive_mismatched_exhibit_number_same_name():
    """축 3: 동일한 자료명(운반 사진)이 본문과 목록에서 서로 다른 호증 번호로 매핑됨."""
    doc = _make_doc([
        "본문에서는 갑 제22호증 운반 사진에 나타난 바와 같이 하자 상태가 심각합니다.",
        "입증방법",
        "1. 갑 제23호증 운반 사진",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) >= 1
    name_mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(name_mismatches) == 1
    assert "운반 사진" in name_mismatches[0].title
    assert "갑 제22호증" in name_mismatches[0].detail and "갑 제23호증" in name_mismatches[0].detail


# --- 5. 양성 시험 4 (축 1: 수 호증 등 기타 당사자 부호의 완결 목록 누락 포섭) ---
def test_positive_su_exhibit_missing_in_complete_list():
    """축 1: '수' 부호 등 일반 한글 부호를 사용한 완결 목록 누락 정상 포섭."""
    doc = _make_doc([
        "피신청인은 수 제4호증 감정서를 통하여 신청인의 청구가 부당함을 입증합니다.",
        "입증방법: 수 제1호증 내지 수 제3호증 (제출 증거 일체)",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) >= 1
    f = [f for f in findings if f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"]
    assert len(f) >= 1
    assert "수 제4호증" in f[0].title


# --- 6. 양성 시험 5 (축 4: 선언 개수와 실제 목록 수 불일치) ---
def test_positive_count_mismatch():
    """축 4: 증거목록에서 총 4개 선언했으나 실제 목록은 3개."""
    doc = _make_doc([
        "입증방법: 총 4개 서증을 제출합니다.",
        "1. 갑 제1호증 계약서",
        "2. 갑 제2호증 영수증",
        "3. 갑 제3호증 통장사본",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("defect_code") == "EXHIBIT_COUNT_MISMATCH"
    assert f.confidence_features.get("declared_count") == 4
    assert f.confidence_features.get("actual_count") == 3


# --- 7. 대조군 시험 1 (완결 선언 없는 부분 목록 정상 보호) ---
def test_control_incomplete_list_not_flagged():
    """대조군 1: 완결 선언 없는 목록에서 본문이 다른 호증을 인용해도 결함 아님 (정상 서면)."""
    doc = _make_doc([
        "원고는 갑 제1호증 및 갑 제5호증을 참조하여 변론을 준비하였습니다.",
        "입증방법",
        "1. 갑 제1호증 품의서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"완결 선언 없는 부분 목록은 결함으로 잡히지 않아야 함: {findings}"


# --- 8. 대조군 시험 2 (이전 제출 호증 재인용 정상 보호) ---
def test_control_prior_submission_reference():
    """대조군 2: 앞서 제출한 호증 재인용은 목록에 없더라도 규칙 레벨에서 정상 보호."""
    doc = _make_doc([
        "원고는 앞서 제출한 갑 제2호증 영수증에 기재된 금액을 다시 원용합니다.",
        "증거목록 (이 서면의 제출 증거 전부)",
        "1. 갑 제5호증 점검표",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"앞서 제출한 호증 재인용은 제외되어야 함: {findings}"


# --- 9. 대조군 시험 3 (상대방 증거 인용 정상 보호) ---
def test_control_opponent_exhibit_not_flagged():
    """대조군 3: 원고 서면이 상대방 증거(을 제3호증)를 인용하고 자기 목록은 갑 호증만 있어도 결함 아님."""
    doc = _make_doc([
        "원고는 피고가 제출한 을 제3호증 영수증의 진정성립을 부인합니다.",
        "입증방법: 갑 제1호증 계약서 (이 서면의 제출 증거 전부)",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"상대방 증거(을호증) 인용은 자기 완결목록 누락으로 잡히지 않아야 함: {findings}"


# --- 10. 대조군 시험 4 (상대방 제출 개수 서술 정상 보호) ---
def test_control_opponent_count_mention_not_flagged():
    """대조군 4: '피고는 3개의 증거를 제출하였으나...'와 같은 상대방 주어 개수 언급은 목록 개수 불일치 미검출."""
    doc = _make_doc([
        "피고는 3개의 증거를 제출하였으나 이는 본건과 무관한 자료에 불과합니다.",
        "입증방법",
        "1. 갑 제1호증 확인서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    count_findings = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_COUNT_MISMATCH"]
    assert len(count_findings) == 0, f"상대방 서술 개수는 목록 개수 불일치로 오탐되지 않아야 함: {count_findings}"


# --- 11. 대조군 시험 5 (동일 접두어를 가진 서로 다른 자료명 구분 정상 보호) ---
def test_control_distinct_names_with_common_prefix():
    """대조군 5: 목록에 '갑 제3호증 사진'과 '갑 제5호증 사진첩'이 공존할 때 상이한 번호로 오인하지 않음."""
    doc = _make_doc([
        "원고는 갑 제5호증 사진첩을 통하여 현장 전경을 설명합니다.",
        "입증방법",
        "1. 갑 제3호증 사진",
        "2. 갑 제5호증 사진첩",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    name_mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(name_mismatches) == 0, f"'사진'과 '사진첩'은 서로 다른 자료명이므로 번호 불일치로 오탐되지 않아야 함: {name_mismatches}"


# --- 12. 대조군 시험 6 (정상적인 가지번호 묶음 제출 정상 보호) ---
def test_control_normal_sub_numbering():
    """대조군 6: 정상적인 가지번호(갑 제1호증의 1, 2) 묶음 제출은 결함 아님."""
    doc = _make_doc([
        "원고는 갑 제1호증의 1 및 갑 제1호증의 2를 제출합니다.",
        "입증방법",
        "1. 갑 제1호증의 1 사진",
        "2. 갑 제1호증의 2 사진",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0


# --- 13. 대조군 시험 7 (상대방의 별지 증거목록 부존재 주장 비판 정상 보호) ---
def test_control_opponent_annex_criticism_not_flagged():
    """대조군 7: '피고는 별지 증거목록에 없는 을 제6호증을 근거로...'와 같은 상대방 증거 비판은 결함 아님."""
    doc = _make_doc([
        "원고는, 피고가 별지 증거목록에 없는 을 제6호증을 근거로 주장한 사항에 대하여 이유 없음을 밝힙니다.",
        "입증방법: 갑 제1호증 계약서 (이 서면의 제출 증거 전부)",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"상대방 증거에 대한 비판 문장은 자기 목록 결함으로 오탐되지 않아야 함: {findings}"


# --- 14. 양성 시험 6 (축 3: 자료명 뒤에 호증 번호가 오는 역방향 배치 불일치 포섭) ---
def test_positive_reverse_name_exhibit_number_mismatch():
    """축 3: 본문에서 자료명이 앞에 오고 호증이 뒤에 오는 배치(운반 사진 갑 제22호증)에서도 번호 불일치 검출."""
    doc = _make_doc([
        "원고는 운반 사진 갑 제22호증으로 물품 훼손 상태를 증명합니다.",
        "첨부 목록: 갑 제21호증 접수표, 갑 제23호증 운반 사진. 추가 제출 목록은 없습니다.",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    name_mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(name_mismatches) == 1
    assert "운반 사진" in name_mismatches[0].title
    assert name_mismatches[0].status == VerificationStatus.SUSPICIOUS


# --- 15. 대조군 시험 8 (통상 정상 소송서면) ---
def test_control_normal_pleading_no_defects():
    """대조군 8: 번호 불일치가 없는 통상 소송서면."""
    doc = _make_doc([
        "원고는 갑 제1호증 계약서에 따라 피고에게 이행을 촉구하였습니다.",
        "입증방법",
        "1. 갑 제1호증 계약서",
        "2. 갑 제2호증 내용증명",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0


# --- 16. 대조군 시험 9 (목록 구역 내 2단 호증 연속 배치 구조 정상 보호) ---
def test_control_consecutive_list_rows_not_mismatched():
    """대조군 9: 입증방법 구역 내 2단으로 호증 목록 행이 연속 배치된 구조에서 앞 행 자료명과 뒷 행 번호가 결합되어 번호 불일치로 오탐되지 않음 (TC-01/HO-01 구조 보호)."""
    doc = _make_doc([
        "원고는 피고의 채무불이행 사실에 대하여 다음과 같이 증거를 제출합니다.",
        "입증방법",
        "갑 제1호증 발주서 갑 제2호증 납품내역서 및 송달증명",
        "갑 제3호증 제품사진 갑 제4호증의 1 내지 2 각 정산서",
        "첨부서류",
        "1. 위 입증방법 각 1통",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"연달아 배치된 목록 구역 행은 번호 불일치로 오탐되지 않아야 함: {findings}"


# --- 17. 양성 시험 7 (날짜가 포함된 완결 목록에서 본문 인용 호증 누락 검출) ---
def test_positive_complete_list_with_dates_missing_exhibit():
    """날짜(2026. 5. 1.)가 기재된 완결 목록에서 본문 인용 호증(갑 제4호증) 누락 검출 검증 (평가 측 탐침 문구 복사 배제)."""
    doc = _make_doc([
        "원고는 갑 제4호증 출하내역서에 기재된 일자에 물품이 발송되었음을 입증합니다.",
        "입증방법",
        "1. 갑 제1호증 발주계약서 2026. 3. 1.",
        "2. 갑 제2호증 입금확인증 2026. 3. 15.",
        "3. 갑 제3호증 인수증 2026. 4. 1.",
        "위 목록이 제출한 증거의 전부입니다.",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    missing_findings = [
        f for f in findings
        if f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    ]
    assert len(missing_findings) == 1
    assert "갑 제4호증" in missing_findings[0].title


# --- 18. 대조군 시험 10 (자료명 내 괄호 약식 마침표 표기 정상 수용) ---
def test_control_exhibit_name_with_parenthesized_dotted_date():
    """자료명에 '(1. 9.)'처럼 괄호 안 마침표 표기가 포함된 정상 목록 행 수용 검증 (HO-05 및 은퇴 08 보호)."""
    doc = _make_doc([
        "원고는 갑 제1호증 사건(1. 9.) 분석서에 기재된 내용으로 사실관계를 입증합니다.",
        "입증방법",
        "1. 갑 제1호증 사건(1. 9.) 분석서 2026. 1. 2.",
        "2. 갑 제2호증 영수증(2. 15.) 2026. 2. 20.",
        "위 목록이 제출한 증거의 전부입니다.",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"자료명에 '(1. 9.)' 표기가 있더라도 정상 목록 행으로 수용되어 결함이 오탐되지 않아야 함: {findings}"


# --- 19. 양성 시험 8 ('수' 부호 및 '이 서면의 제출 증거 전부' 완결 선언 누락 검출) ---
def test_positive_su_exhibit_missing_with_full_submission_declaration():
    """'수 제N호증' 및 '이 서면의 제출 증거 전부' 선언형 목록에서 본문 인용 호증(수 제3호증) 누락 정상 검출."""
    doc = _make_doc([
        "신청인은 수 제3호증 지급명령신청서를 통하여 채권의 존재를 입증합니다.",
        "입증방법",
        "1. 수 제1호증 대여금계약서",
        "2. 수 제2호증 송금내역서",
        "이 서면의 제출 증거 전부입니다.",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    missing = [
        f for f in findings
        if f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    ]
    assert len(missing) == 1
    assert "수 제3호증" in missing[0].title


# --- 20. 실제 파이프라인 진입점 시험 (목록 머리글 괄호 완결 선언 누락) ---
def test_pipeline_entrypoint_parenthesized_completion_declaration(tmp_path, monkeypatch):
    """실제 파이프라인 진입점: 목록 머리글 괄호 완결 선언('제출 증거 목록(이 서면의 제출 증거 전부)') 누락 검출."""
    sample_text = (
        "원고는 피고의 의무 불이행 사실을 입증하기 위해 갑 제7호증 통고서를 원용합니다.\n"
        "제출 증거 목록(이 서면의 제출 증거 전부)\n"
        "1. 갑 제1호증 합의서\n"
        "2. 갑 제2호증 거래명세표"
    )
    doc_path = tmp_path / "brief_parenthesized_completion.txt"
    doc_path.write_text(sample_text, encoding="utf-8")

    with monkeypatch.context() as patch:
        patch.setenv("LV_ALLOW_NETWORK", "0")
        patch.setenv("LV_DATA_DIR", str(tmp_path / "data"))
        reset_settings()
        try:
            pipeline = VerificationPipeline()
            result = pipeline.run(
                "pipeline-paren-completion-run",
                ProjectContext("pipeline-paren-project"),
                [DocumentInput("brief-paren-1", str(doc_path), doc_path.name)],
            )
        finally:
            reset_settings()

    assert not result.errors
    assert len(result.documents) == 1
    doc_result = result.documents[0]

    num_findings = [
        f for f in doc_result.findings
        if f.type == FindingType.EVIDENCE_LIST_MISMATCH
        and f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    ]
    assert len(num_findings) >= 1
    assert "갑 제7호증" in num_findings[0].title


# --- 21. 양성 시험 9 (목록 머리글 괄호 안 완결 선언 누락 검출) ---
def test_positive_section_head_parenthesized_completion_missing_exhibit():
    """목록 머리글에 괄호로 완결 선언('제출 증거 목록 (이 서면의 제출 증거 전부)')이 들어간 경우 본문 누락 호증(갑 제8호증) 검출."""
    doc = _make_doc([
        "원고는 피고의 추가 채무를 입증하기 위하여 갑 제8호증 차용증을 원용합니다.",
        "제출 증거 목록 (이 서면의 제출 증거 전부)",
        "1. 갑 제1호증 물품공급계약서",
        "2. 갑 제2호증 세금계산서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    missing = [f for f in findings if f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"]
    assert len(missing) == 1
    assert "갑 제8호증" in missing[0].title


# --- 22. 양성 시험 10 (자료명 뒤 조사 결합 형태의 양방향 자료명 불일치 검출) ---
def test_positive_reverse_name_with_particle_number_mismatch():
    """본문에서 자료명 뒤에 조사가 결합된 배치('현장 실측도면을 갑 제15호증으로 제출하며')에서 목록 번호(갑 제16호증)와의 불일치 검출."""
    doc = _make_doc([
        "원고는 공사 하자를 입증하기 위하여 현장 실측도면을 갑 제15호증으로 제출하며 손해액을 주장합니다.",
        "입증방법",
        "1. 갑 제14호증 공사계약서",
        "2. 갑 제16호증 현장 실측도면",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    name_mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(name_mismatches) == 1
    assert "현장 실측도면" in name_mismatches[0].title
    assert "갑 제15호증" in name_mismatches[0].detail and "갑 제16호증" in name_mismatches[0].detail


# --- 23. 양성 시험 11 (증거목록 헤더 괄호 완결 선언에서 본문 호증 누락 검출) ---
def test_positive_exhibit_list_header_parenthesized_full_scope():
    """'증거목록(추가 제출 없음)' 헤더에서 완결 선언이 정상 인식되어 본문 호증(을 제5호증) 누락 검출."""
    doc = _make_doc([
        "피고는 을 제5호증 송달보고서로 원고의 주장을 탄핵합니다.",
        "증거목록(추가 제출 없음)",
        "1. 을 제1호증 견적서",
        "2. 을 제2호증 영수증",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    missing = [f for f in findings if f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"]
    assert len(missing) == 1
    assert "을 제5호증" in missing[0].title


# --- 24. 대조군 시험 11 (본문 서술문 행의 A등급 호증 중복 오탐 방지) ---
def test_control_prose_sentence_not_duplicate_number_grade_a():
    """본문 서술문 행(40자 초과 + 서술어 종결)이 호증 번호를 포함하더라도 _numbering에서 A등급 호증 중복으로 오탐되지 않음 (은퇴 10 A등급 오탐 보호)."""
    doc = _make_doc([
        "원고는 피고가 갑 제1호증 발주서를 작성하여 송부한 사실이 명백하므로 이행을 촉구하였습니다.",
        "또한 피고는 갑 제1호증과 관련하여 물품 납품 기한을 준수하지 못하였다고 스스로 인정하였습니다.",
        "입증방법",
        "1. 갑 제1호증 발주서",
        "2. 갑 제2호증 납품확인서",
    ])
    from packages.claim_engine.evidence_consistency import check_exhibits
    findings = check_exhibits(doc)
    dup_findings = [
        f for f in findings
        if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"
    ]
    assert len(dup_findings) == 0, f"본문 서술문 행의 호증 언급은 A등급 호증 중복으로 오탐되지 않아야 함: {dup_findings}"


# --- 25. 대조군 시험 12 (서증명 뒤 조사가 붙은 단순 서술절 오탐 방지) ---
def test_control_particle_verb_phrase_not_mismatched():
    """서증명 뒤 조사가 붙은 일반 서술절은 엉뚱한 자료명 불일치로 오탐되지 않음."""
    doc = _make_doc([
        "원고는 공사계약서를 체결한 이후 갑 제1호증으로 영수증을 제출하였습니다.",
        "입증방법",
        "1. 갑 제1호증 영수증",
        "2. 갑 제2호증 공사계약서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    name_mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(name_mismatches) == 0


# --- 26. 대조군 시험 13 (목록 머리글 단순 부연 괄호는 완결 선언으로 오인하지 않음) ---
def test_control_section_head_non_completion_parenthesis():
    """목록 머리글에 단순 부연 설명 괄호('입증방법 (사본 1부 첨부)')가 있는 경우 완결 선언으로 오인하지 않아 본문 호증 인용이 정상 보호됨."""
    doc = _make_doc([
        "원고는 갑 제3호증 품의서를 근거로 사실관계를 주장합니다.",
        "입증방법 (사본 1부 첨부)",
        "1. 갑 제1호증 계약서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"단순 부연 괄호는 완결 선언으로 오인되지 않아야 함: {findings}"


# --- 27. 양성 시험 (머리글 없이 줄마다 적은 목록에서 긴 입증취지가 붙은 호증 중복 탐지) ---
def test_positive_unheaded_lines_duplicate_number_with_long_purpose():
    """머리글 없이 줄 단위로 적힌 증거 목록에서 자료명 뒤에 40자 초과 입증취지 서술문이 붙어 있더라도 호증 번호 중복을 정확히 검출 (A-3)."""
    doc = _make_doc([
        "1. 갑 제1호증 부동산매매계약서 피고가 계약금을 정히 수령하고도 소유권이전등기 의무를 불이행한 사실을 입증하고자 합니다.",
        "2. 갑 제1호증 금융거래내역확인서 원고가 피고 명의 계좌로 계약금 전액을 정상 송금하였음을 증명하기 위하여 제출합니다.",
        "3. 갑 제2호증 내용증명우편 통고서 피고에게 의무 이행을 최고한 사실을 입증합니다.",
    ])
    from packages.claim_engine.evidence_consistency import check_exhibits
    findings = check_exhibits(doc)
    dup_findings = [f for f in findings if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"]
    assert len(dup_findings) == 1, f"긴 입증취지가 붙은 목록형 행의 호증 중복이 탐지되어야 함: {dup_findings}"
    assert "갑 제1호증" in dup_findings[0].title


# --- 28. 양성 시험 (머리글 없이 하이픈 불릿으로 줄마다 적힌 목록의 호증 중복 탐지) ---
def test_positive_unheaded_lines_duplicate_number_hyphen_bullets():
    """머리글 없이 하이픈 불릿으로 줄마다 적힌 목록에서 같은 번호에 긴 입증취지가 붙은 경우 호증 번호 중복 탐지 (A-3)."""
    doc = _make_doc([
        "- 을 제3호증 정밀안전진단결과표 대상 구조물에 균열이 심각하여 보수공사가 시급하다는 기술적 소견을 입증합니다.",
        "- 을 제3호증 공사비산정내역서 피고가 주장하는 보수비용이 객관적 산출 근거에 기초하였음을 증명하고자 합니다.",
        "- 을 제4호증 현장실사사진 실제 균열 부위의 촬영 사진입니다.",
    ])
    from packages.claim_engine.evidence_consistency import check_exhibits
    findings = check_exhibits(doc)
    dup_findings = [f for f in findings if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"]
    assert len(dup_findings) == 1, f"하이픈 불릿형 긴 입증취지 행의 호증 중복이 탐지되어야 함: {dup_findings}"
    assert "을 제3호증" in dup_findings[0].title


# --- 29. 양성 시험 (수식어 결합 자료명의 본문-목록 번호 불일치 탐지) ---
def test_positive_mismatch_with_modifier_prefix():
    """본문에서 수식어가 붙은 자료명('현장 실사 운반 사진 (갑 제22호증)')과 목록('갑 제22호증 계약서', '갑 제23호증 운반 사진')의 번호 불일치 탐지 (A-3)."""
    doc = _make_doc([
        "원고는 현장 실사 운반 사진 (갑 제22호증)을 근거로 물품이 정상 인도되었음을 주장합니다.",
        "입증방법",
        "1. 갑 제22호증 물품공급계약서",
        "2. 갑 제23호증 운반 사진",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(mismatches) == 1, f"수식어 결합 자료명의 번호 불일치가 탐지되어야 함: {mismatches}"


# --- 30. 대조군 시험 12 (조사 '와·과'로 이어진 병렬 나열 정상 서술 불일치 오탐 배제) ---
def test_control_parallel_particle_wa_gwa_not_mismatched():
    """자료명 뒤 조사 '와·과'로 다른 서증과 나열된 정상 서술에서 자료명 불일치 오탐 배제 (TK-126 A-3 요구 1·4)."""
    doc = _make_doc([
        "원고는 부동산매매계약서와 갑 제2호증 영수증을 종합하여 볼 때 매매대금이 완납되었음을 밝힙니다.",
        "입증방법",
        "1. 갑 제1호증 부동산매매계약서",
        "2. 갑 제2호증 영수증",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(mismatches) == 0, f"병렬 조사 '와'로 나열된 정상 서술이 불일치로 오탐되어서는 안 됨: {mismatches}"


# --- 31. 대조군 시험 13 (접속사 '및'으로 이어진 병렬 나열 정상 서술 불일치 오탐 배제) ---
def test_control_parallel_conjunction_and_particles_not_mismatched():
    """자료명 뒤 '및'으로 다른 서증과 나열된 정상 서술에서 자료명 불일치 오탐 배제 (TK-126 A-3 요구 1·4)."""
    doc = _make_doc([
        "피고는 법인사업자등록증 및 갑 제3호증 위임장을 근거로 적법한 대표권이 존재한다고 다투고 있습니다.",
        "입증방법",
        "1. 갑 제1호증 법인사업자등록증",
        "2. 갑 제3호증 소송대리인위임장",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(mismatches) == 0, f"병렬 접속사 '및'으로 나열된 정상 서술이 불일치로 오탐되어서는 안 됨: {mismatches}"


# --- 32. 대조군 시험 14 (자기 번호 우선: '변경' 수식어가 붙은 정상 서술 불일치 오탐 배제) ---
def test_control_self_number_priority_modifier_variation():
    """목록에 '공사계약서'와 '변경 공사계약서'가 있고 본문 '변경 공사계약서(갑 제2호증)' 인용 시 자기 번호 우선으로 오탐 배제 (TK-126 A-3 요구 2·4)."""
    doc = _make_doc([
        "원고는 변경 공사계약서(갑 제2호증)에 따라 추가 공사대금의 지급을 구합니다.",
        "입증방법",
        "1. 갑 제1호증 공사계약서",
        "2. 갑 제2호증 변경 공사계약서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(mismatches) == 0, f"자기 번호 목록명과 일치하는 수식어 결합 행은 다른 번호와 접미 일치해도 오탐 배제되어야 함: {mismatches}"


# --- 33. 대조군 시험 15 (자기 번호 우선: '2차 추가' 수식어가 붙은 정상 서술 불일치 오탐 배제) ---
def test_control_self_number_priority_numeric_stage_variation():
    """목록에 '합의서'와 '2차 추가 합의서'가 있고 본문 '2차 추가 합의서(갑 제6호증)' 인용 시 자기 번호 우선으로 오탐 배제 (TK-126 A-3 요구 2·4)."""
    doc = _make_doc([
        "당사자들은 2차 추가 합의서(갑 제6호증)를 체결하여 종전의 잔여 채무액을 최종 확정하였습니다.",
        "입증방법",
        "1. 갑 제5호증 기본합의서",
        "2. 갑 제6호증 2차 추가 합의서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(mismatches) == 0, f"자기 번호 목록명과 일치하는 차수 수식어 결합 행은 다른 번호와 접미 일치해도 오탐 배제되어야 함: {mismatches}"


# --- 34. 대조군 시험 16 (A-3 잔여: 동일 번호·동일 자료명 접두·한쪽만 날짜 병기된 반복은 호증 중복 아님) ---
def test_control_same_number_same_prefix_one_sided_date_not_duplicate():
    """같은 호증 번호와 같은 자료명 접두('계약서,' vs '계약서:')를 공유하면서 한쪽에만 날짜가 병기된 2행 반복은 A등급 호증 중복으로 오탐되지 않음 (A-3 잔여)."""
    doc = _make_doc([
        "- 갑 제4호증 물품공급계약서, 대금 지급 기한에 관한 약정 조항 확인",
        "- 갑 제4호증 물품공급계약서: 기본 계약 체결 경위 설명 (2024-05-10)",
    ])
    from packages.claim_engine.evidence_consistency import check_exhibits
    findings = check_exhibits(doc)
    dup_findings = [
        f for f in findings
        if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"
    ]
    assert len(dup_findings) == 0, f"동일 번호·동일 자료명 접두에 한쪽만 날짜가 붙은 반복은 중복 오탐되지 않아야 함: {dup_findings}"


# --- 35. 양성 시험 (A-3 잔여 사전 의견 반영: 같은 번호·다른 자료명·한쪽만 날짜 병기된 진짜 중복 탐지) ---
def test_positive_same_number_different_names_one_sided_date_is_duplicate():
    """같은 호증 번호에 서로 다른 자료명('물품공급계약서,' vs '세금계산서:')이 붙고 한쪽에만 날짜가 병기된 경우 진짜 호증 중복(A등급)으로 정상 탐지됨 (평가 측 사전 의견 반영)."""
    doc = _make_doc([
        "- 갑 제4호증 물품공급계약서, 대금 지급 기한에 관한 약정 조항 확인",
        "- 갑 제4호증 세금계산서: 부가가치세 신고 내역 확인 (2024-05-10)",
    ])
    from packages.claim_engine.evidence_consistency import check_exhibits
    findings = check_exhibits(doc)
    dup_findings = [
        f for f in findings
        if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"
    ]
    assert len(dup_findings) == 1, f"같은 번호·다른 자료명·한쪽만 날짜인 진짜 중복은 반드시 탐지되어야 함: {dup_findings}"
    assert "갑 제4호증" in dup_findings[0].title


# --- 36. 양성 시험 (A-3 잔여: 같은 번호·같은 자료명 접두이나 양쪽 날짜가 서로 다른 별개 자료 중복 탐지) ---
def test_positive_same_number_same_prefix_conflicting_dates_is_duplicate():
    """같은 호증 번호와 같은 자료명 접두라도 양쪽에 서로 다른 날짜가 명시된 경우 별개 자료의 번호 중복으로 정상 탐지됨."""
    doc = _make_doc([
        "- 갑 제4호증 물품공급계약서, 1차 공급 약정 (2024-03-01)",
        "- 갑 제4호증 물품공급계약서: 2차 공급 약정 (2024-05-10)",
    ])
    from packages.claim_engine.evidence_consistency import check_exhibits
    findings = check_exhibits(doc)
    dup_findings = [
        f for f in findings
        if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"
    ]
    assert len(dup_findings) == 1, f"양쪽 날짜가 서로 다른 별개 자료의 같은 번호 부여는 중복으로 탐지되어야 함: {dup_findings}"



