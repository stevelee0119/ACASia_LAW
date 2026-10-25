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
    _QUANTITY_RE,
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


# ==============================================================================
# 6. B-3 4차 보완 Y1~Y6, Y8 단위 시험 (한국어 주석 포함)
# ==============================================================================

def test_y1_amount_definitive_and_partial_payment():
    """Y1: 대금 중 일부 지급 대조군 및 총액 확정 둘 충돌 양성 검증 (한국어 주석)."""
    # 1. 대조군: '대금 중 일부 지급'은 계약 총액 슬롯 제외 (오탐 0)
    text_ctrl = "원고는 피고에게 공사대금 중 500만 원을 지급하였습니다. 한편 피고는 공사대금 중 1,000만 원을 수령하였습니다."
    doc_ctrl = _make_doc(text_ctrl)
    findings_ctrl = [f for f in check_internal_inconsistency(doc_ctrl) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings_ctrl) == 0, f"Y1 일부 지급 오탐 발생: {findings_ctrl}"

    # 2. 양성: 총액 확정 둘이 충돌하는 경우
    text_pos = "이 사건 매매대금 총액은 3억 원으로 약정하였습니다. 그러나 다른 서면에서 위 매매대금 총액을 4억 원으로 정하였습니다."
    doc_pos = _make_doc(text_pos)
    findings_pos = [f for f in check_internal_inconsistency(doc_pos) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings_pos) == 1, f"Y1 총액 충돌 미탐지: {findings_pos}"


def test_y2_amount_deposit_and_rent_separation():
    """Y2: 임대차의 보증금과 월 차임 분리 대조군 및 동일 보증금 충돌 양성 검증 (한국어 주석)."""
    # 1. 대조군: 보증금 5,000만 원과 월 차임 200만 원은 별개 속성이므로 모순 아님
    text_ctrl = "이 사건 임대차계약의 보증금은 5,000만 원입니다. 한편 위 임대차계약의 월 차임은 200만 원으로 정하였습니다."
    doc_ctrl = _make_doc(text_ctrl)
    findings_ctrl = [f for f in check_internal_inconsistency(doc_ctrl) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings_ctrl) == 0, f"Y2 보증금-차임 오탐 발생: {findings_ctrl}"

    # 2. 양성: 동일 계약의 보증금을 서로 다르게 확정한 경우
    text_pos = "이 사건 임대차계약의 보증금은 5,000만 원입니다. 한편 다른 서면에서 위 임대차계약의 보증금을 7,000만 원으로 약정하였습니다."
    doc_pos = _make_doc(text_pos)
    findings_pos = [f for f in check_internal_inconsistency(doc_pos) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings_pos) == 1, f"Y2 동일 보증금 충돌 미탐지: {findings_pos}"


def test_y3_date_event_predicate_and_exclude_removal():
    """Y3: 체결일/이행일, 발생일/청구일/치료일 대조군 및 동일 사고일 충돌 양성 검증 (한국어 주석)."""
    # 1. 대조군 1: 체결일과 이행일은 별개 사건 술어이므로 모순 아님
    text_ctrl1 = "원고는 2023. 5. 1. 이 사건 매매계약을 체결하였습니다. 한편 피고는 2023. 6. 1. 위 계약에 따른 목적물을 인도하였습니다."
    doc_ctrl1 = _make_doc(text_ctrl1)
    findings_ctrl1 = [f for f in check_internal_inconsistency(doc_ctrl1) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_ctrl1) == 0, f"Y3 체결일-인도일 오탐 발생: {findings_ctrl1}"

    # 2. 대조군 2: 사고 발생일과 보험금 청구일은 별개 사건 술어이므로 모순 아님
    text_ctrl2 = "2023. 3. 10. 이 사건 교통사고가 발생하였습니다. 원고는 2023. 4. 1. 위 사고에 관하여 보험금을 청구하였습니다."
    doc_ctrl2 = _make_doc(text_ctrl2)
    findings_ctrl2 = [f for f in check_internal_inconsistency(doc_ctrl2) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_ctrl2) == 0, f"Y3 발생일-청구일 오탐 발생: {findings_ctrl2}"

    # 3. 대조군 3: 사고 발생일과 병원 치료일은 구조 규칙에 의해 슬롯 분리 (오탐 0)
    text_ctrl3 = "2023. 2. 1. 이 사건 사고가 발생하였습니다. 원고는 2023. 2. 15. 병원에서 치료를 받았습니다."
    doc_ctrl3 = _make_doc(text_ctrl3)
    findings_ctrl3 = [f for f in check_internal_inconsistency(doc_ctrl3) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_ctrl3) == 0, f"Y3 발생일-치료일 오탐 발생: {findings_ctrl3}"

    # 4. 양성: 동일 사고 발생일을 서로 다르게 진술한 경우 (지시어 다름)
    text_pos = "이 사건 교통사고는 2023. 5. 10. 발생하였습니다. 한편 다른 준비서면에서 위 사고는 2023. 5. 20. 일어났다고 기재하였습니다."
    doc_pos = _make_doc(text_pos)
    findings_pos = [f for f in check_internal_inconsistency(doc_pos) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_pos) == 1, f"Y3 동일 사고 발생일 충돌 미탐지: {findings_pos}"


def test_y4_opponent_claim_with_date_and_conjugations():
    """Y4: 날짜 낀 상대방 다툼 및 반박 표지 제외와 작성자 자신 진술 충돌 양성 검증 (한국어 주석)."""
    # 1. 대조군 1: 날짜가 포함된 '…다고 다툽니다' 오탐 0
    text_ctrl1 = "원고는 대여금을 청구합니다. 피고는 2024. 3. 15. 대여금을 전액 변제하였다고 다툽니다."
    doc_ctrl1 = _make_doc(text_ctrl1)
    findings_ctrl1 = [f for f in check_internal_inconsistency(doc_ctrl1) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(findings_ctrl1) == 0, f"Y4 날짜 낀 다툼 오탐 발생: {findings_ctrl1}"

    # 2. 대조군 2: 원고 주장 인용 + '사실과 다릅니다' 오탐 0
    text_ctrl2 = "피고가 소송대리인을 통하여 제출합니다. 원고는 2024. 1. 10. 계약을 체결하였다고 주장하지만 이는 전혀 사실과 다릅니다."
    doc_ctrl2 = _make_doc(text_ctrl2)
    findings_ctrl2 = [f for f in check_internal_inconsistency(doc_ctrl2) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_ctrl2) == 0, f"Y4 상대방 주장 인용 반박 오탐 발생: {findings_ctrl2}"

    # 3. 대조군 3: '다퉜으나' 오탐 0
    text_ctrl3 = "피고는 2023. 8. 1. 사고가 발생하지 않았다고 다퉜으나 이유 없습니다."
    doc_ctrl3 = _make_doc(text_ctrl3)
    findings_ctrl3 = [f for f in check_internal_inconsistency(doc_ctrl3) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_ctrl3) == 0, f"Y4 다퉜으나 오탐 발생: {findings_ctrl3}"

    # 4. 양성: 작성자 자신의 두 진술 충돌 (원고의 체결일 충돌)
    text_pos = "원고는 2023. 5. 1. 이 사건 계약을 체결하였다고 진술합니다. 한편 원고는 위 계약을 2023. 6. 1. 체결하였다고 주장합니다."
    doc_pos = _make_doc(text_pos)
    findings_pos = [f for f in check_internal_inconsistency(doc_pos) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_pos) == 1, f"Y4 작성자 본인 진술 충돌 미탐지: {findings_pos}"


def test_y5_party_role_contract_word_order_variants():
    """Y5: 계약명 선행·후행·생략 3변형 양성 및 별개 계약 대조군 검증 (한국어 주석)."""
    # 1. 양성 변형 1: 계약명 선행 ('위 임대차계약에서 원고는 임대인으로서...')
    text_v1 = "위 임대차계약에서 원고는 임대인으로서 목적물을 인도하였습니다. 한편 다른 준비서면에서 원고는 위 계약의 임차인입니다."
    doc_v1 = _make_doc(text_v1)
    findings_v1 = [f for f in check_internal_inconsistency(doc_v1) if f.confidence_features.get("inconsistency_type") == "ROLE"]
    assert len(findings_v1) == 1, f"Y5 계약명 선행 지위 역전 미탐지: {findings_v1}"

    # 2. 양성 변형 2: 계약명 후행 ('원고는 이 사건 임대차계약의 임대인입니다...')
    text_v2 = "원고는 이 사건 임대차계약의 임대인입니다. 그러나 원고는 위 계약의 임차인으로서 차임을 지급하였습니다."
    doc_v2 = _make_doc(text_v2)
    findings_v2 = [f for f in check_internal_inconsistency(doc_v2) if f.confidence_features.get("inconsistency_type") == "ROLE"]
    assert len(findings_v2) == 1, f"Y5 계약명 후행 지위 역전 미탐지: {findings_v2}"

    # 3. 양성 변형 3: 계약명 생략 / 문장 내 종류 ('본건 임대차 관계에서 원고는 임대인이다...')
    text_v3 = "본건 임대차 관계에서 원고는 임대인이다. 한편 원고는 위 계약의 임차인으로서 보증금을 청구한다."
    doc_v3 = _make_doc(text_v3)
    findings_v3 = [f for f in check_internal_inconsistency(doc_v3) if f.confidence_features.get("inconsistency_type") == "ROLE"]
    assert len(findings_v3) == 1, f"Y5 계약명 생략 지위 역전 미탐지: {findings_v3}"

    # 4. 대조군: 별개 계약 (매매계약 매수인 vs 임대차계약 임대인)
    text_ctrl = "원고는 이 사건 매매계약의 매수인입니다. 한편 원고는 위 임대차계약의 임대인입니다."
    doc_ctrl = _make_doc(text_ctrl)
    findings_ctrl = [f for f in check_internal_inconsistency(doc_ctrl) if f.confidence_features.get("inconsistency_type") == "ROLE"]
    assert len(findings_ctrl) == 0, f"Y5 별개 계약 지위 오탐 발생: {findings_ctrl}"


def test_y6_quantity_inconsistency_and_controls():
    """Y6: 수량 속성 충돌 3변형(대, 톤, ㎡) 양성 및 부분 인도/추가 납품 대조군 검증 (한국어 주석)."""
    # 1. 양성 변형 1: 개수/대수 충돌 ('10대' ↔ '20대')
    text_v1 = "이 사건 기계의 납품 수량은 10대로 약정하였습니다. 한편 다른 준비서면에서 위 기계의 납품 수량은 20대로 기재하였습니다."
    doc_v1 = _make_doc(text_v1)
    findings_v1 = [f for f in check_internal_inconsistency(doc_v1) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(findings_v1) == 1, f"Y6 대수 수량 충돌 미탐지: {findings_v1}"

    # 2. 양성 변형 2: 중량 충돌 ('50톤' ↔ '80톤')
    text_v2 = "이 사건 자재의 총 수량은 50톤으로 정하였습니다. 그러나 다른 서면에서 위 자재의 총 수량은 80톤으로 합의하였습니다."
    doc_v2 = _make_doc(text_v2)
    findings_v2 = [f for f in check_internal_inconsistency(doc_v2) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(findings_v2) == 1, f"Y6 중량 수량 충돌 미탐지: {findings_v2}"

    # 3. 양성 변형 3: 면적 충돌 ('500㎡' ↔ '700㎡')
    text_v3 = "이 사건 토지의 면적은 500㎡입니다. 한편 다른 서면에서 위 토지의 면적은 700㎡로 명시하였습니다."
    doc_v3 = _make_doc(text_v3)
    findings_v3 = [f for f in check_internal_inconsistency(doc_v3) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(findings_v3) == 1, f"Y6 면적 수량 충돌 미탐지: {findings_v3}"

    # 4. 대조군: 부분 인도 및 추가 납품 (오탐 0)
    text_ctrl = "원고는 위 물품 중 일부인 10개를 1차로 납품하였습니다. 한편 피고는 추가로 20개를 인도받았습니다."
    doc_ctrl = _make_doc(text_ctrl)
    findings_ctrl = [f for f in check_internal_inconsistency(doc_ctrl) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(findings_ctrl) == 0, f"Y6 부분 인도/추가 납품 오탐 발생: {findings_ctrl}"


def test_y8_relative_date_cross_block_and_korean_numbers():
    """Y8: 단락 간 상대 날짜 승계 및 한글 수사(스물·서른, 삼천만 원) 검증 (한국어 주석)."""
    # 1. 단락 첫 문장 상대 날짜 승계 충돌
    b1 = "2023. 5. 10. 이 사건 교통사고가 발생하였습니다."
    b2 = "당일 위 교통사고가 다시 일어난 사실은 없으며, 다른 준비서면에서 위 사고는 2023. 5. 25. 발생하였다고 적었습니다."
    doc_date = _make_doc(b1, b2)
    findings_date = [f for f in check_internal_inconsistency(doc_date) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(findings_date) == 1, f"Y8 단락 간 상대 날짜 승계 충돌 미탐지: {findings_date}"

    # 2. 한글 수사 변환 ('삼천만 원' -> 30,000,000원)
    assert _parse_korean_amount("삼천만 원") == 30_000_000
    assert _parse_korean_amount("3천5백만 원") == 35_000_000
    assert _parse_korean_amount("2억 5천만 원") == 250_000_000


# ==============================================================================
# B-3 5차 보완 검증 테스트: Q1 ~ Q3 전용 검증 (한국어 주석)
# ==============================================================================


def test_q1_unlisted_quantity_units_and_excluded_units():
    """Q1: 목록 밖 단위(켤레, 리터) 구조적 추출 양성 및 제외 단위(조문·순번·비율) 슬롯 배제 검증 (한국어 주석)."""
    # 1. 목록 밖 단위 1: '켤레' ('50켤레' ↔ '30켤레' 충돌 = 양성)
    text_u1 = (
        "원고는 피고에게 신발 50켤레를 공급하기로 약정하였습니다. "
        "그러나 실제 인도된 위 신발은 30켤레였습니다."
    )
    doc_u1 = _make_doc(text_u1)
    f_u1 = [f for f in check_internal_inconsistency(doc_u1) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_u1) == 1, f"Q1 목록 밖 단위(켤레) 수량 충돌 미탐지: {f_u1}"

    # 2. 목록 밖 단위 2: '리터' ('300리터' ↔ '200리터' 충돌 = 양성)
    text_u2 = (
        "이 사건 원유의 납품 수량은 300리터로 정하였습니다. "
        "한편 다른 준비서면에서 위 원유의 납품 수량은 200리터로 기재하였습니다."
    )
    doc_u2 = _make_doc(text_u2)
    f_u2 = [f for f in check_internal_inconsistency(doc_u2) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_u2) == 1, f"Q1 목록 밖 단위(리터) 수량 충돌 미탐지: {f_u2}"

    # 3. 제외 단위 검증: 조문(조·항·호), 순번(차·번·회), 비율(%, 배) -> 수량 슬롯 배제 (오탐 0건)
    text_ex = (
        "원고는 민법 제100조 및 제2항 제3호에 따라 연 5%의 비율에 의한 지연손해금을 청구하며, "
        "손해배상금은 약정액의 2배에 달하고, 제3차에 걸친 5회 납품 과정에서 10번 확인하였습니다."
    )
    doc_ex = _make_doc(text_ex)
    f_ex = [f for f in check_internal_inconsistency(doc_ex) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_ex) == 0, f"Q1 조문·순번·비율 단위 슬롯 오탐 발생: {f_ex}"


def test_q2_unlisted_quantity_targets_and_controls():
    """Q2: 목록 밖 대상(노트북, 마스크) 구조적 추출 양성 및 서로 다른 대상 대조군 검증 (한국어 주석)."""
    # 1. 목록 밖 대상 1: '노트북' ('50대' ↔ '30대' 충돌 = 양성)
    text_t1 = (
        "원고는 피고에게 노트북 50대를 공급하기로 약정하였습니다. "
        "그러나 실제로 납품된 위 노트북은 30대였습니다."
    )
    doc_t1 = _make_doc(text_t1)
    f_t1 = [f for f in check_internal_inconsistency(doc_t1) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_t1) == 1, f"Q2 목록 밖 대상(노트북) 충돌 미탐지: {f_t1}"

    # 2. 목록 밖 대상 2: '마스크' 및 속성 머리 명사 해소('위 [X]의 인도 수량' -> X) ('5,000매' ↔ '3,000매' 충돌 = 양성)
    text_t2 = (
        "이 사건 마스크의 계약 수량은 5,000매로 약정하였습니다. "
        "한편 위 마스크의 실제 인도 수량은 3,000매였습니다."
    )
    doc_t2 = _make_doc(text_t2)
    f_t2 = [f for f in check_internal_inconsistency(doc_t2) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_t2) == 1, f"Q2 목록 밖 대상(마스크) 속성 수량 충돌 미탐지: {f_t2}"

    # 3. 대조군: 서로 다른 대상의 수량 서술 ('노트북 50대' vs '모니터 30대' -> 모순 아님, 대조군 오탐 0건)
    text_ctrl = (
        "원고는 피고에게 노트북 50대를 납품하였습니다. "
        "또한 피고에게 모니터 30대를 인도하였습니다."
    )
    doc_ctrl = _make_doc(text_ctrl)
    f_ctrl = [f for f in check_internal_inconsistency(doc_ctrl) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_ctrl) == 0, f"Q2 서로 다른 대상 대조군 오탐 발생: {f_ctrl}"


def test_q3_definitive_predicate_and_event_predicate_inflections():
    """Q3: 과거형 확정 서술('…원이었습니다', '…개였습니다') 및 사건 술어 받침 결합('일어난') 양성 검증 (한국어 주석)."""
    # 1. 금액 과거형 확정 서술 충돌 ('…원이었습니다')
    text_amt = (
        "이 사건 공사계약 총액은 50,000,000원이었습니다. "
        "그러나 다른 준비서면에서 위 공사계약 총액은 80,000,000원이었습니다."
    )
    doc_amt = _make_doc(text_amt)
    f_amt = [f for f in check_internal_inconsistency(doc_amt) if f.confidence_features.get("inconsistency_type") == "AMOUNT"]
    assert len(f_amt) == 1, f"Q3 과거형 금액 확정 서술('원이었습니다') 충돌 미탐지: {f_amt}"

    # 2. 수량 과거형 확정 서술 충돌 ('…개였습니다')
    text_qty = (
        "이 사건 부품의 납품 수량은 100개였습니다. "
        "한편 다른 준비서면에서 위 부품의 납품 수량은 80개였습니다."
    )
    doc_qty = _make_doc(text_qty)
    f_qty = [f for f in check_internal_inconsistency(doc_qty) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_qty) == 1, f"Q3 과거형 수량 확정 서술('개였습니다') 충돌 미탐지: {f_qty}"

    # 3. 일자 사건 술어 관형형 받침 결합 ('…가 일어난 [날짜]')
    text_date = (
        "이 사건 화재가 일어난 2023. 5. 10. 당시 건물에 상주하고 있었습니다. "
        "그러나 피고는 위 화재가 2023. 5. 25. 발생하였다고 적었습니다."
    )
    doc_date = _make_doc(text_date)
    f_date = [f for f in check_internal_inconsistency(doc_date) if f.confidence_features.get("inconsistency_type") == "DATE"]
    assert len(f_date) == 1, f"Q3 사건 술어 관형형('일어난') 일자 충돌 미탐지: {f_date}"


def test_qq1_to_qq3_quantity_unit_and_definitive_and_modifier():
    """QQ1~QQ3: 단위 조사 분리, 확정 서술 값 직후 매칭, 전칭 부사 건너뛰기 검증 (한국어 주석)."""
    # QQ1: '[N]명과', '[N]개를', '[N]대가' 꼴에서 단위가 한 글자로 잡히는지 검증
    # 5명과 -> 단위 '명', 10개를 -> 단위 '개', 20대가 -> 단위 '대'
    text_qq1 = (
        "인부 5명과 작업하였습니다. "
        "부품 10개를 납품하였습니다. "
        "차량 20대가 인도되었습니다."
    )
    matches_q = list(_QUANTITY_RE.finditer(text_qq1))
    assert len(matches_q) == 3
    units = []
    for m in matches_q:
        u = m.group("unit")
        if len(u) == 2 and u[1] in ("과", "와", "을", "를", "이", "가", "은", "는", "에", "의", "로", "도", "만"):
            u = u[0]
        units.append(u)
    assert units == ["명", "개", "대"], f"QQ1 단위 조사 축소 실패: {units}"

    # QQ2: '[N]명과 [다른 동사]하였습니다' = 확정 서술 없음 -> 슬롯 없음 (오탐 0)
    # 서로 다른 일의 인원 수 서술이 모순으로 오탐되지 않음
    text_qq2_ctrl = (
        "원고는 공사 현장에서 인부 5명과 함께 작업을 진행하였습니다. "
        "피고는 다른 현장에서 인부 8명과 함께 청소를 완료하였습니다."
    )
    doc_qq2_ctrl = _make_doc(text_qq2_ctrl)
    f_qq2_ctrl = [f for f in check_internal_inconsistency(doc_qq2_ctrl) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_qq2_ctrl) == 0, f"QQ2 다른 동사 결합 인원 수 오탐 발생: {f_qq2_ctrl}"

    # QQ2: '[N][단위]이었습니다·입니다', '[N][단위]를 납품하였다' = 값 직후 확정 서술 -> 슬롯 생성 및 모순 검출
    text_qq2_pos = (
        "원고가 피고에게 납품한 부품은 100개였습니다. "
        "그러나 피고는 위 부품을 80개만 납품받았다고 기재되어 실제로 공급된 부품은 80개입니다."
    )
    doc_qq2_pos = _make_doc(text_qq2_pos)
    f_qq2_pos = [f for f in check_internal_inconsistency(doc_qq2_pos) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_qq2_pos) == 1, f"QQ2 값 직후 확정 서술('개였습니다'/'개입니다') 충돌 미탐지: {f_qq2_pos}"

    # QQ3: '[대상]은 모두 [N][단위]입니다' + '위 [대상]의 [속성] 수량은 [M][단위]였습니다' = 전칭 부사 건너뛰고 대상 일치하여 양성 검출
    text_qq3 = (
        "이 사건 노트북은 모두 50대입니다. "
        "한편 위 노트북의 실제 납품 수량은 30대였습니다."
    )
    doc_qq3 = _make_doc(text_qq3)
    f_qq3 = [f for f in check_internal_inconsistency(doc_qq3) if f.confidence_features.get("inconsistency_type") == "QUANTITY"]
    assert len(f_qq3) == 1, f"QQ3 전칭 부사('모두') 건너뛰기 후 수량 충돌 미탐지: {f_qq3}"

