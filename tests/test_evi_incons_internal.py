"""TK-90 문서 안 진술 불일치(EVI-INCONS) 단위 시험.

3차 보완 지시(T1~T8) 및 2-2 공통 수용 규약 반영:
1. 속성 6종(일시·장소·서명자·금액·지위·조항) 양성 각 3변형:
   - T3 지시어 접두 분리 꼴 포함 ('이 사건 사고' ↔ '위 사고')
   - T6 상대 날짜 꼴 포함 ('같은 날' 해소)
   - T7 호칭+이름 서명자 및 단독 표지 확장 ('만·만이·혼자·외에는')
   - T4 '총' 표지 없는 계약대금 명사 확정 진술 포착
   - T8 당사자 지위 역전 3항 구조 (임대인/임차인, 매도인/매수인, 도급인/수급인)
2. T5 한국어 금액 파서 단위 혼용 ('2억 5천만 원', '3천5백만 원', '1억2천만 원', '5,000만 원') 검증
3. 대조군 시험:
   - T2 상대방 주장 인용 3꼴 ('주장합니다', '다툽니다', '번복합니다') 오탐 0
   - 복수 공동 서명자 정상 서술 (오탐 0)
   - 서로 다른 계약 대조 (오탐 0)
   - 비배타적 일반 이동 서술 (오탐 0)
   - 부분 금액(잔금) 대조 (오탐 0)
   - 정정 필터 대조 (오탐 0)
   - 주위적·예비적 청구 대조 (오탐 0)
   - T1: B-3 내부 산식 검사 부존재 확인 (calculation.py 전담)
4. A-4 선후 관계 중복 억제 대조
5. 선형 성능 측정 (점검표 2항)
"""
from __future__ import annotations

import time
import pytest

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.claim_engine.internal_inconsistency import (
    check_internal_inconsistency,
    _parse_korean_amount,
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
# 1. 속성 6종 3변형 양성 시험
# ==============================================================================

# (1) 속성 1: 일시 모순 3변형 (T3: 지시어 다른 꼴 포함)
@pytest.mark.parametrize("variant_text", [
    # 변형 1 (T3 지시어 다른 꼴): '이 사건 사고' ↔ '위 사고'
    "원고는 2023. 5. 12. 발생한 이 사건 사고로 인하여 차량이 크게 파손되었습니다. 그러나 다른 서면에서 원고는 2023. 6. 12. 발생한 위 사고 당시 피고의 신호위반을 지적하고 있습니다.",
    # 변형 2: '본건 화재' ↔ '위 화재'
    "본건 화재는 2022년 3월 10일 발생하여 창고를 전소시켰습니다. 그러나 피고의 부주의로 2022년 4월 10일 발생한 위 화재의 책임은 피고에게 있습니다.",
    # 변형 3: '해당 계약' ↔ '이 사건 계약'
    "2021. 8. 15. 체결된 해당 계약에 관하여 분쟁이 발생하였으며, 다른 단락에서는 2021. 9. 15. 체결된 이 사건 계약의 효력을 주장합니다.",
])
def test_positive_date_inconsistency_3_variants(variant_text: str):
    """일시 속성 모순 3변형 양성 시험 (T3 지시어 해소 포함, C등급, UNVERIFIED)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED


# (2) 속성 2: 장소 모순 3변형 (T6: 상대 날짜 해소 포함)
@pytest.mark.parametrize("variant_text", [
    # 변형 1 (T6 상대 날짜 꼴): '2023. 7. 10.' ... '같은 날'
    "원고는 2023. 7. 10. 종로사무소에만 상주하였습니다. 그런데 원고는 같은 날 강남지점에 체류하며 회의를 주재하였습니다.",
    # 변형 2: '내내' 한정 표지 + 머무름 술어 활용형
    "피고는 2022년 11월 5일 내내 인천공장에만 머물렀습니다. 그러나 피고는 2022년 11월 5일 수원연구소에 상주하여 근무하였습니다.",
    # 변형 3 (T6 주어 승계 꼴): 당일 상대 날짜 및 주어 승계
    "이 사건 당일인 2023. 9. 1. 피고인은 오직 자택에만 머물렀습니다. 당일인 2023. 9. 1. 물류센터에 체류하며 근무하였습니다.",
])
def test_positive_location_inconsistency_3_variants(variant_text: str):
    """장소 속성 모순 3변형 양성 시험 (T6 상대 날짜 해소 포함, C등급, SUSPICIOUS)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "LOCATION"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.SUSPICIOUS


# (3) 속성 3: 서명자 모순 3변형 (T7: 호칭+이름 및 단독 표지 확장, T2: 작성자 본인 진술 충돌)
@pytest.mark.parametrize("header_text, body_text, expected_grade", [
    # 변형 1: 서증 목록 기재 작성자 vs 본문 서술 불일치 (B등급 상향)
    ("갑 제1호증(합의서) 작성자: 김철수", "대표이사 박영희가 직접 서명하고 날인한 갑 제1호증에 따라 합의가 성립되었습니다.", EvidenceGrade.B),
    # 변형 2: 서증 목록 발신인 vs 본문 서술 불일치 (B등급 상향)
    ("갑 제2호증(동의서) 발신인은 이민호", "팀장 정우성이 단독으로 작성하여 기명날인한 갑 제2호증을 교부하였습니다.", EvidenceGrade.B),
    # 변형 3 (T7 호칭+이름 및 '혼자' 단독 표지, T2 작성자 자체 모순):
    ("기초사실 기재", "이 사건 확인서의 유일한 작성인은 원고 김민수입니다. 한편 다른 준비서면에서 위 확인서는 피고 박지훈 혼자 작성하고 날인하였다고 번복하였습니다.", EvidenceGrade.C),
])
def test_positive_signer_inconsistency_3_variants(header_text: str, body_text: str, expected_grade: EvidenceGrade):
    """서명자 속성 모순 3변형 양성 시험 (B/C등급)."""
    doc = _make_doc(header_text, body_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "SIGNER"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == expected_grade


# (4) 속성 4: 수량·금액 모순 3변형 (T4: 계약대금 일반 확정 진술 매칭, T2: 작성자 자체 모순)
@pytest.mark.parametrize("variant_text", [
    # 변형 1 (T4 총 표지 없는 계약대금 일반 확정 진술):
    "이 사건 매매대금은 3억 원입니다. 그러나 원고는 다른 준비서면에서 위 매매대금을 3억 5,000만 원으로 정하였습니다.",
    # 변형 2: 공사계약 공사대금 확정 진술
    "이 사건 공사계약의 공사대금은 5억 원으로 약정되었습니다. 하지만 다른 서면에서 위 공사계약의 공사대금을 6억 원으로 기재하였습니다.",
    # 변형 3: 대여금 계약 금액 확정 진술
    "이 사건 대여금의 총액은 5,000만 원으로 약정되었습니다. 그런데 다른 준비서면에서는 본건 대여금 총액을 7,000만 원으로 기재하였습니다.",
])
def test_positive_amount_inconsistency_3_variants(variant_text: str):
    """수량/금액 속성 모순 3변형 양성 시험 (T4 일반 확정 서술 매칭, C등급, UNVERIFIED)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED


# (5) 속성 5: 당사자 지위 역전 모순 3변형 (T8: 3항 구조 및 닫힌 짝 사전)
@pytest.mark.parametrize("variant_text, expected_pair", [
    # 변형 1: 임대차계약 임대인 ↔ 임차인
    (
        "원고는 이 사건 임대차계약의 임대인입니다. 그러나 결론에 이르러 원고는 위 임대차계약의 임차인으로서 보증금 반환을 청구합니다.",
        ("임대인", "임차인"),
    ),
    # 변형 2: 매매계약 매도인 ↔ 매수인
    (
        "원고는 이 사건 매매계약의 매도인으로서 소유권이전등기 의무를 집행하였습니다. 한편 다른 준비서면에서 원고는 위 매매계약의 매수인으로서 잔금을 지급하였다고 진술합니다.",
        ("매도인", "매수인"),
    ),
    # 변형 3: 도급계약 도급인 ↔ 수급인
    (
        "피고는 이 사건 도급계약의 도급인에 해당합니다. 그런데 피고는 위 도급계약의 수급인으로서 목적물을 완성하였다고 기재하였습니다.",
        ("도급인", "수급인"),
    ),
])
def test_positive_party_role_inconsistency_3_variants(variant_text: str, expected_pair: tuple[str, str]):
    """당사자 지위 역전 3변형 양성 시험 (T8: 3항 구조 일반화, B등급, CONTRADICTED)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "ROLE"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.status == VerificationStatus.CONTRADICTED


# (6) 속성 6: 동일 서증 조항 상반 원용 3변형
@pytest.mark.parametrize("variant_text", [
    # 변형 1: 지체상금 면제 ↔ 부과
    "갑 제1호증 제15조에 의하여 지체상금이 전액 면제되었습니다. 그런데 후술하는 바와 같이 갑 제1호증 제15조에 따라 지체상금을 부과하여야 합니다.",
    # 변형 2: 계약 해제권 부존재 ↔ 유효한 행사
    "을 제2호증 제8조에 따라 손해배상 책임이 없다고 할 것이나, 한편 을 제2호증 제8조에 기하여 손해배상금을 청구하여야 합니다.",
    # 변형 3: 위약금 감면 ↔ 지급 청구
    "갑 제3호증 제10조에 의하여 위약금 채무가 면제되었음에도 불구하고, 갑 제3호증 제10조를 근거로 위약금을 지급하여야 한다고 모순되게 주장합니다.",
])
def test_positive_exhibit_clause_contradiction_3_variants(variant_text: str):
    """동일 서증 조항 원용 상반 단정 3변형 양성 시험 (B등급, CONTRADICTED)."""
    doc = _make_doc(variant_text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "CLAUSE_CONTRADICTION"]
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.status == VerificationStatus.CONTRADICTED


# ==============================================================================
# 2. T5: 한국어 금액 파서 단위 혼용 단위 시험
# ==============================================================================

def test_t5_korean_amount_unit_combinations():
    """T5 요구 시험: 억·만 아래 자리의 천·백·십 단위 및 아라비아 숫자 혼용 해석."""
    assert _parse_korean_amount("2억 5천만 원") == 250_000_000
    assert _parse_korean_amount("3천5백만 원") == 35_000_000
    assert _parse_korean_amount("1억2천만 원") == 120_000_000
    assert _parse_korean_amount("5,000만 원") == 50_000_000
    assert _parse_korean_amount("3억 원") == 300_000_000
    assert _parse_korean_amount("50만 원") == 500_000


# ==============================================================================
# 3. 합성 대조군 시험 (T2 상대방 주장 3꼴 포함)
# ==============================================================================

def test_control_t2_opponent_claim_citation_claims():
    """T2 대조 1: 상대방 주장 인용 ('피고는 ...라고 주장합니다', 오탐 0)."""
    text = "이 사건 총 매매대금은 3억 원입니다. 피고는 총 매매대금이 5억 원이라고 주장합니다."
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings) == 0


def test_control_t2_opponent_claim_citation_disputes():
    """T2 대조 2: 상대방 다툼 인용 ('피고는 ...라고 다툽니다', 오탐 0)."""
    text = "이 사건 확인서의 작성인은 김철수입니다. 피고는 위 확인서의 작성인이 박지훈이라고 다툽니다."
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "SIGNER"]
    assert len(findings) == 0


def test_control_t2_opponent_claim_citation_recants():
    """T2 대조 3: 상대방 번복 인용 ('피고는 ...라고 번복합니다', 오탐 0)."""
    text = "공사대금 총액은 5억 원으로 약정되었습니다. 피고는 위 공사대금이 6억 원이라고 번복합니다."
    doc = _make_doc(text)
    findings = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings) == 0


def test_control_partial_amount_vs_total():
    """대조: 총 대금과 미지급 잔대금 차이 (정상 분할 진술, 오탐 0)."""
    text = "이 사건 총 매매대금은 3억 원이고, 원고가 지급하지 않은 잔금은 5,000만 원입니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_incident_date_vs_subsequent_date():
    """대조: 사고일과 치료일의 차이 (정상 후속 일자, 오탐 0)."""
    text = "2023. 5. 12. 이 사건 교통사고가 발생하였고, 원고는 2023. 5. 13. 병원에 입원하였습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_sublease_multiple_roles():
    """대조: 전대차 관계의 복수 지위 (정상 복수 지위, 오탐 0)."""
    text = "원고는 임대인이자 전대차 계약의 임차인으로서 이 사건 건물을 관리하였습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_correction_filter():
    """대조: 정정 진술 (정정 필터 가드, 오탐 0)."""
    text = "이 사건 총 매매대금 3억 원은 착오로 잘못 기재한 것이므로 3억 5,000만 원으로 바로잡습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_primary_vs_alternative_claim():
    """대조: 주위적·예비적 청구금액 차이 (청구 취지 차이, 오탐 0)."""
    text = "주위적으로 이 사건 총 매매대금 3억 원을 청구하고, 예비적으로 2억 원의 반환을 구합니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_different_exhibit_clauses():
    """대조: 서로 다른 조항 원용 (제15조 면제 ↔ 제16조 손해배상금, 오탐 0)."""
    text = "갑 제1호증 제15조에 의하여 면제되었고, 갑 제1호증 제16조에 의해 손해배상금을 청구합니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_non_exclusive_location_movement():
    """대조: 배타적 한정 없는 일반 장소 이동 서술 (정상 방문, 오탐 0)."""
    text = "원고는 2023. 7. 10. 종로사무소에 방문하였고, 같은 날 강남지점에도 들러 업무를 처리하였습니다."
    doc = _make_doc(text)
    assert len(check_internal_inconsistency(doc)) == 0


def test_control_joint_multiple_signers():
    """대조: 복수 공동 서명자 정상 서술 (오탐 0)."""
    text = "대표이사 김철수와 이사 박영희가 공동으로 작성하고 서명한 합의서를 체결하였습니다."
    doc = _make_doc(text)
    assert len([f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "SIGNER"]) == 0


def test_control_t1_no_arithmetic_mismatch_in_b3():
    """T1 대조: B-3 모듈에서는 산식 불일치를 발생시키지 않음 (calculation.py 전담)."""
    text = "추가 노무비는 150,000 × 20 = 4,000,000원입니다."
    doc = _make_doc(text)
    # B-3 internal_inconsistency에서는 ARITHMETIC_MISMATCH를 발생시키지 않아야 함
    findings = [f for f in check_internal_inconsistency(doc) if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(findings) == 0


# ==============================================================================
# 4. A-4 선후 관계 중복 억제 대조 시험
# ==============================================================================

def test_control_a4_temporal_sequence_suppression():
    """A-4 중복 억제: 사건 간 선후 관계가 포함된 문장에서 B-3 일시 모순 억제 (오탐 0)."""
    text = "원고는 2023. 5. 1. 이 사건 계약을 체결하였고, 이후 2023. 4. 20. 위 계약을 해지하겠다는 통지를 발송하였습니다."
    doc = _make_doc(text)
    date_incons = [f for f in check_internal_inconsistency(doc) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(date_incons) == 0


# ==============================================================================
# 5. 선형 성능 측정 시험 (점검표 2항)
# ==============================================================================

def test_internal_inconsistency_linear_performance():
    """정규식 및 슬롯 추출 선형 성능 측정: 길이 1배/4배 최솟값 비 < 8, 4배 최솟값 < 1초 검증."""
    base_text = (
        "이 사건 매매대금은 3억 원으로 정하였고 원고는 계약금을 완납하였습니다. "
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
