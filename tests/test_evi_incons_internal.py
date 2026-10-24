"""TK-90 문서 안 진술 불일치(EVI-INCONS) 단위 시험.

조건부 승인(129) 및 2-2 공통 수용 규약 반영:
1. 4속성(일시·장소·서명자·수량) 양성 각 1개 이상 × 3변형 (12문장 양성)
2. 기존 핵심 양성:
   - 양성 1: 동일 계약 총 매매대금 금액 모순 (3억 원 ↔ 3억 5,000만 원, C등급)
   - 양성 2: 동일 사고 발생일 일자 모순 (2023. 5. 12. ↔ 2023. 6. 12., C등급)
   - 양성 3: 당사자 역할 역전 모순 (원고가 임대인 ↔ 임차인인 원고, C등급)
   - 양성 4: 동일 서증 조항 원용 상반 단정 (갑 제1호증 제15조 면제 ↔ 부과, B등급)
3. 수식 파서 (사칙연산 불일치 C등급): 곱셈, 덧셈, 뺄셈 불일치 양성
4. 서증 명시 작성자 vs 본문 진술 불일치 (B등급)
5. 대조군 (7개 이상):
   - 대조 1: 총 대금과 미지급 잔대금 차이 (정상 분할 진술, 오탐 0)
   - 대조 2: 사고일과 치료일의 차이 (정상 후속 일자, 오탐 0)
   - 대조 3: 전대차 관계의 복수 지위 (정상 복수 지위, 오탐 0)
   - 대조 4: 정정 진술 (정정 필터, 오탐 0)
   - 대조 5: 주위적·예비적 청구금액 차이 (청구 취지 차이, 오탐 0)
   - 대조 6: 서로 다른 조항 원용 (제15조 면제 ↔ 제16조 손해배상금, 오탐 0)
   - 대조 7: 배타적 한정 없는 일반 장소 이동 서술 (정상 방문, 오탐 0)
   - 대조 8: 복수 공동 서명자 정상 서술 (오탐 0)
   - 대조 9: 상대방 주장 인용 (상대방 주장은 사실과 다르다, 오탐 0)
   - 대조 10: 수식 파서 정상 일치 계산식 (오탐 0)
6. A-4 중복 억제 대조 1건:
   - 사건 간 선후 관계(체결 후 해지, 발송 후 수령)가 포함된 문장에서 B-3 중복 발생 억제 (오탐 0)
7. 선형 성능 측정:
   - 길이 1배, 4배 텍스트 각 3회 측정, 최솟값 비 < 8, 4배 최솟값 < 1초 검증.
"""
from __future__ import annotations

import time
import pytest

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.claim_engine.internal_inconsistency import (
    check_internal_inconsistency,
    parse_arithmetic_expression,
)


def _make_doc(*texts: str, doc_id: str = "synth_doc") -> NormalizedDocument:
    """합성 테스트용 NormalizedDocument 생성 헬퍼."""
    blocks = [
        Block(block_id=f"b{i+1}", text=t, page=1, visible=True, source_layer="visible_text")
        for i, t in enumerate(texts)
    ]
    page = Page(page_number=1, blocks=blocks, width=595.0, height=842.0)
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


# ==============================================================================
# 1. 4속성(일시·장소·서명자·수량) 3변형 양성 시험 (조건부 승인 129 조건 7)
# ==============================================================================

# (1) 속성 1: 일시 모순 3변형 (동일 사건 복수 일자 기재)
@pytest.mark.parametrize("variant_text", [
    # 변형 1: 기본 어순 (원고 주장 및 재차 진술)
    "원고는 2023. 5. 12. 발생한 위 교통사고로 차량이 대파되었습니다. 한편 2023. 6. 12. 발생한 위 교통사고 당시 피고는 신호를 위반하였습니다.",
    # 변형 2: 수식어 및 접속어 변경
    "본건 화재는 2022년 3월 10일 발생하여 창고를 전소시켰습니다. 그러나 피고의 부주의로 2022년 4월 10일 발생한 본건 화재의 책임은 피고에게 있습니다.",
    # 변형 3: 도치 및 연결어미 변경
    "2021. 8. 15. 발생한 이 사건 사고에 대해 피고는 과실을 인정하였으나, 다른 준비서면에서는 2021. 9. 15. 발생한 이 사건 사고의 원인을 원고에게 돌리고 있습니다.",
])
def test_positive_date_inconsistency_3_variants(variant_text: str):
    """일시 속성 모순 3변형 양성 시험 (C등급, UNVERIFIED)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED


# (2) 속성 2: 장소 모순 3변형 (동일 일시 배타적 상이 장소 체류)
@pytest.mark.parametrize("variant_text", [
    # 변형 1: 동일 일시 '에만' 한정 표지
    "원고는 2023. 7. 10. 종로사무소에만 있었고 다른 곳에 가지 않았습니다. 그런데 원고는 2023. 7. 10. 강남지점에 체류하며 회의를 주재하였습니다.",
    # 변형 2: '내내' 한정 표지 + 머무름 술어 활용형
    "피고는 2022년 11월 5일 내내 인천공장에만 머물렀습니다. 그러나 피고는 2022년 11월 5일 수원연구소에 상주하여 근무하였습니다.",
    # 변형 3: '오직' 한정 표지 + 도치
    "이 사건 당일인 2023. 9. 1. 피고인은 오직 자택에만 머물렀다고 진술하였으나, 같은 2023. 9. 1. 피고인은 물류센터에 체류하였습니다.",
])
def test_positive_location_inconsistency_3_variants(variant_text: str):
    """장소 속성 모순 3변형 양성 시험 (C등급, SUSPICIOUS)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "LOCATION"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.SUSPICIOUS


# (3) 속성 3: 서명자 모순 3변형 (서증 기재 작성자 vs 본문 진술 불일치 또는 본문 상이 서명자)
@pytest.mark.parametrize("header_text, body_text, expected_grade", [
    # 변형 1: 서증 목록 기재 작성자 vs 본문 서술 불일치 (B등급 상향)
    ("갑 제1호증(합의서) 작성자: 김철수", "대표이사 박영희가 직접 서명하고 날인한 갑 제1호증에 따라 합의가 성립되었습니다.", EvidenceGrade.B),
    # 변형 2: 서증 목록 발신인 vs 본문 서술 불일치 (B등급 상향)
    ("갑 제2호증(동의서) 발신인은 이민호", "팀장 정우성이 단독으로 작성하여 기명날인한 갑 제2호증을 교부하였습니다.", EvidenceGrade.B),
    # 변형 3: 본문 내 동일 확인서에 대해 서로 다른 단독 서명자 진술 (C등급)
    ("기초사실 기재", "이 사건 확인서의 유일한 작성인은 대표이사 홍길동입니다. 반면 피고는 위 확인서의 작성인이 변호사 강감찬이라고 주장합니다.", EvidenceGrade.C),
])
def test_positive_signer_inconsistency_3_variants(header_text: str, body_text: str, expected_grade: EvidenceGrade):
    """서명자 속성 모순 3변형 양성 시험 (B/C등급)."""
    doc = _make_doc(header_text, body_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "SIGNER"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == expected_grade


# (4) 속성 4: 수량·금액 모순 3변형 (동일 계약 총액 진술 불일치)
@pytest.mark.parametrize("variant_text", [
    # 변형 1: 매매계약 총 매매대금
    "이 사건 총 매매대금은 3억 원으로 확정되었습니다. 그러나 피고는 본건 총 매매대금을 3억 5,000만 원으로 합의하였다고 번복합니다.",
    # 변형 2: 공사계약 총 공사대금
    "원고와 피고가 체결한 위 공사계약의 공사대금 총액은 5억 원입니다. 하지만 피고는 위 공사계약의 총 공사대금이 6억 원이라고 다툽니다.",
    # 변형 3: 대여금 계약 총액
    "이 사건 대여금의 총액은 5,000만 원으로 약정되었습니다. 그런데 다른 준비서면에서는 본건 대여금 총액을 7,000만 원으로 기재하였습니다.",
])
def test_positive_amount_inconsistency_3_variants(variant_text: str):
    """수량/금액 속성 모순 3변형 양성 시험 (C등급, UNVERIFIED)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED


# ==============================================================================
# 2. 수식 파서 (사칙연산 불일치 C등급) 시험 (조건부 승인 129 조건 5)
# ==============================================================================

def test_positive_arithmetic_multiplier_mismatch():
    """수식 파서: 곱셈 계산식 불일치 탐지 (C등급)."""
    text = "추가 노무비는 150,000 × 20 = 4,000,000원입니다."  # 실제: 3,000,000원
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.SUSPICIOUS
    assert "150,000 × 20 = 기재 4,000,000 (실제 3,000,000)" in f.title


def test_positive_arithmetic_addition_mismatch():
    """수식 파서: 덧셈 합산 불일치 탐지 (C등급)."""
    text = "총 손해액은 50,000,000원 + 30,000,000원 = 총 95,000,000원입니다."  # 실제: 80,000,000원
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert "50,000,000 + 30,000,000 = 기재 95,000,000 (실제 80,000,000)" in f.title


def test_positive_arithmetic_subtraction_mismatch():
    """수식 파서: 뺄셈 차감 불일치 탐지 (C등급)."""
    text = "미지급 잔액은 100,000,000원 - 40,000,000원 = 잔액 50,000,000원입니다."  # 실제: 60,000,000원
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert "100,000,000 - 40,000,000 = 기재 50,000,000 (실제 60,000,000)" in f.title


# ==============================================================================
# 3. 기존 승인된 당사자 역할 및 서증 조항 상반 원용 시험
# ==============================================================================

def test_positive_party_role_inversion():
    """당사자 역할 역전 모순 (원고가 임대인 ↔ 임차인인 원고, C등급)."""
    text = (
        "기초사실로서 원고가 임대인, 피고가 임차인으로서 이 사건 임대차계약을 체결하였습니다. "
        "그러나 결론에 이르러 임차인인 원고는 목적물을 적법하게 인도하였으므로 보증금 반환을 청구합니다."
    )
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "ROLE"]
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.C


def test_positive_exhibit_clause_contradiction():
    """동일 서증 조항 원용 상반 단정 (갑 제1호증 제15조 면제 ↔ 부과, B등급)."""
    text = (
        "갑 제1호증 제15조에 의하여 지체상금이 전액 면제되었습니다. "
        "그런데 후술하는 바와 같이 갑 제1호증 제15조에 따라 지체상금을 부과하여야 합니다."
    )
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "CLAUSE_CONTRADICTION"]
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert findings[0].status == VerificationStatus.CONTRADICTED


# ==============================================================================
# 4. 합성 대조군 시험 (7개 이상 필수 준수)
# ==============================================================================

def test_control_1_partial_amount_vs_total():
    """대조 1: 총 대금과 미지급 잔대금 차이 (정상 분할 진술, 오탐 0)."""
    text = "이 사건 총 매매대금은 3억 원이고, 원고가 지급하지 않은 잔금은 5,000만 원입니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_2_incident_date_vs_subsequent_date():
    """대조 2: 사고일과 치료일의 차이 (정상 후속 일자, 오탐 0)."""
    text = "2023. 5. 12. 이 사건 교통사고가 발생하였고, 원고는 2023. 5. 13. 병원에 입원하였습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_3_sublease_multiple_roles():
    """대조 3: 전대차 관계의 복수 지위 (정상 복수 지위, 오탐 0)."""
    text = "원고는 임대인이자 전대차 계약의 임차인으로서 이 사건 건물을 관리하였습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_4_correction_filter():
    """대조 4: 정정 진술 (정정 필터 가드, 오탐 0)."""
    text = "이 사건 총 매매대금 3억 원은 착오로 잘못 기재한 것이므로 3억 5,000만 원으로 바로잡습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_5_primary_vs_alternative_claim():
    """대조 5: 주위적·예비적 청구금액 차이 (청구 취지 차이, 오탐 0)."""
    text = "주위적으로 이 사건 총 매매대금 3억 원을 청구하고, 예비적으로 2억 원의 반환을 구합니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_6_different_exhibit_clauses():
    """대조 6: 서로 다른 조항 원용 (제15조 면제 ↔ 제16조 손해배상금, 오탐 0)."""
    text = "갑 제1호증 제15조에 의하여 면제되었고, 갑 제1호증 제16조에 의해 손해배상금을 청구합니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_7_non_exclusive_location_movement():
    """대조 7: 배타적 한정 없는 일반 장소 이동 서술 (정상 방문, 오탐 0)."""
    text = "원고는 2023. 7. 10. 종로사무소에 방문하였고, 같은 날 강남지점에도 들러 업무를 처리하였습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_8_joint_multiple_signers():
    """대조 8: 복수 공동 서명자 정상 서술 (오탐 0)."""
    text = "대표이사 김철수와 이사 박영희가 공동으로 작성하고 서명한 합의서를 체결하였습니다."
    doc = _make_doc(text)
    # 상반된 단독 서명자가 아니므로 오탐 0
    assert len([f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "SIGNER"]) == 0


def test_control_9_opponent_claim_citation():
    """대조 9: 상대방 주장 인용 (상대방 주장은 사실과 다르다 가드, 오탐 0)."""
    text = "피고는 이 사건 총 매매대금이 5억 원이라고 주장하나 상대방의 주장은 사실과 다릅니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_10_valid_arithmetic_formula():
    """대조 10: 수식 파서 정상 일치 계산식 (오탐 0)."""
    text = "추가 공사비는 100,000 × 50 = 5,000,000원이며, 자재비 2,000,000원 + 노무비 3,000,000원 = 총 5,000,000원입니다."
    doc = _make_doc(text)
    assert len([f for f in check_internal_inconsistency(doc) if f.type == FindingType.ARITHMETIC_MISMATCH]) == 0


# ==============================================================================
# 5. A-4 선후 관계 중복 억제 대조 시험 (조건부 승인 129 조건 1)
# ==============================================================================

def test_control_a4_temporal_sequence_suppression():
    """A-4 중복 억제: 사건 간 선후 관계(체결 후 해지, 발송 후 도달)가 포함된 문장에서 B-3 일시 모순 억제 (오탐 0)."""
    text = "원고는 2023. 5. 1. 이 사건 계약을 체결하였고, 이후 2023. 4. 20. 위 계약을 해지하겠다는 통지를 발송하였습니다."
    doc = _make_doc(text)
    # 사건 간 선후 역전(체결 후 해지)은 A-4의 고유 영역이므로 B-3 일시 모순 findings가 발생하지 않아야 함
    date_incons = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(date_incons) == 0


# ==============================================================================
# 6. 선형 성능 측정 시험 (점검표 2항)
# ==============================================================================

def test_internal_inconsistency_linear_performance():
    """정규식 및 파서 선형 성능 측정: 길이 1배/4배 최솟값 비 < 8, 4배 최솟값 < 1초 검증."""
    base_text = (
        "이 사건 총 매매대금은 3억 원으로 정하였고 원고는 계약금을 완납하였습니다. "
        "2023. 5. 12. 발생한 위 교통사고로 인하여 차량이 파손되었고 병원에서 치료를 받았습니다. "
        "원고는 임대인으로서 피고와 이 사건 임대차계약을 체결하였습니다. "
        "갑 제1호증 제15조에 의하여 지체상금이 면제되었습니다. "
        "노무비 합계는 100,000 × 10 = 1,000,000원입니다. "
    )
    text_1x = base_text * 10
    text_4x = base_text * 40

    doc_1x = _make_doc(text_1x)
    doc_4x = _make_doc(text_4x)

    timings_1x = []
    for _ in range(3):
        t0 = time.perf_counter()
        check_internal_inconsistency(doc_1x)
        timings_1x.append(time.perf_counter() - t0)

    timings_4x = []
    for _ in range(3):
        t0 = time.perf_counter()
        check_internal_inconsistency(doc_4x)
        timings_4x.append(time.perf_counter() - t0)

    min_1x = min(timings_1x)
    min_4x = min(timings_4x)

    ratio = min_4x / max(min_1x, 1e-6)
    assert min_4x < 1.0, f"4배 텍스트 실행 시간이 1초를 초과함: {min_4x:.4f}s"
    assert ratio < 8.0, f"4배/1배 성능 비가 8배를 초과함 (비선형 의심): {ratio:.2f}배"
