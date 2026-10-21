"""TK-90 문서 안 진술 불일치(EVI-INCONS) 단위 시험.

승인된 설계 메모 docs/handoff/requests/93_evi_incons_internal_inconsistency_design.md 기준:
1. 합성 양성 4건:
   - 양성 1: 동일 계약 총 매매대금 금액 모순 (3억 원 ↔ 3억 5,000만 원, C등급)
   - 양성 2: 동일 사고 발생일 일자 모순 (2023. 5. 12. ↔ 2023. 6. 12., C등급)
   - 양성 3: 당사자 역할 역전 모순 (원고가 임대인 ↔ 임차인인 원고, C등급)
   - 양성 4: 동일 서증 조항 원용 상반 단정 (갑 제1호증 제15조 면제 ↔ 부과, B등급 상향)
2. 합성 대조군 6건:
   - 대조 1: 총 대금과 미지급 잔대금 차이 (정상 분할 진술, 오탐 0)
   - 대조 2: 사고일과 치료일의 차이 (정상 후속 일자, 오탐 0)
   - 대조 3: 전대차 관계의 복수 지위 (정상 복수 지위, 오탐 0)
   - 대조 4: 정정 진술 (정정 필터, 오탐 0)
   - 대조 5: 주위적·예비적 청구금액 차이 (청구 취지 차이, 오탐 0)
   - 대조 6: 서로 다른 조항 원용 (제15조 면제 ↔ 제16조 손해배상금, 오탐 0 및 등급 통제)
3. 정규식 선형 성능 측정:
   - 길이 1배, 4배 텍스트 각 3회 측정, 최솟값 비 < 8, 4배 최솟값 < 1초 검증.
"""
import time
import pytest

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.claim_engine.internal_inconsistency import check_internal_inconsistency


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


# --- 1. 합성 양성 4건 시험 ---

def test_positive_1_total_amount_contradiction():
    """양성 1: 동일 계약의 총 매매대금 금액 모순 (3억 원 ↔ 3억 5,000만 원, C등급)."""
    text = (
        "이 사건 총 매매대금은 3억 원으로 정하였고 원고는 계약금을 완납하였습니다. "
        "그러나 피고는 위 매매계약 당시 총 매매대금을 3억 5,000만 원으로 약정하였으며 일방적으로 증액을 요구합니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)

    assert len(findings) == 1
    f = findings[0]
    assert f.type == FindingType.FACT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED
    assert "300,000,000원 ↔ 350,000,000원" in f.title
    assert f.confidence_features.get("inconsistency_type") == "AMOUNT"


def test_positive_2_incident_date_contradiction():
    """양성 2: 동일 사고 발생일 일자 모순 (2023. 5. 12. ↔ 2023. 6. 12., C등급)."""
    text = (
        "청구원인으로서 2023. 5. 12. 발생한 위 교통사고로 인하여 원고의 차량이 파손되었습니다. "
        "나아가 2023. 6. 12. 발생한 위 교통사고 당시 피고는 신호를 위반하여 진입하였습니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)

    assert len(findings) == 1
    f = findings[0]
    assert f.type == FindingType.FACT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED
    assert "2023. 5. 12. ↔ 2023. 6. 12." in f.title
    assert f.confidence_features.get("inconsistency_type") == "DATE"


def test_positive_3_party_role_inversion_contradiction():
    """양성 3: 동일 계약상 당사자 역할 역전 모순 (원고가 임대인 ↔ 임차인인 원고, C등급)."""
    text = (
        "기초사실로서 원고가 임대인, 피고가 임차인으로서 이 사건 임대차계약을 체결하였습니다. "
        "그러나 결론에 이르러 임차인인 원고는 목적물을 적법하게 인도하였으므로 보증금 반환을 청구합니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)

    assert len(findings) == 1
    f = findings[0]
    assert f.type == FindingType.FACT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.UNVERIFIED
    assert "임대인 ↔ 임차인" in f.title
    assert f.confidence_features.get("inconsistency_type") == "ROLE"


def test_positive_4_exhibit_clause_contradiction_grade_b():
    """양성 4: 동일 서증 동일 조항 원용 상반 단정 (갑 제1호증 제15조 면제 ↔ 부과, B등급 상향)."""
    text = (
        "원고는 갑 제1호증(도급계약서) 제15조에 따라 지체상금이 전액 면제되었고 귀책이 없다고 진술하였습니다. "
        "반면 후문에서는 갑 제1호증 제15조에 의하여 피고에게 지체상금이 전액 부과되므로 배상책임이 있다고 주장합니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)

    assert len(findings) == 1
    f = findings[0]
    assert f.type == FindingType.FACT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.B  # 객관적 서증 조항 원용 상반 단정은 B등급으로 상향
    assert f.status == VerificationStatus.CONTRADICTED
    assert "동일 서증 조항 원용 상반 단정" in f.title
    assert f.confidence_features.get("inconsistency_type") == "CLAUSE_CONTRADICTION"


# --- 2. 합성 대조군 6건 시험 ---

def test_negative_1_total_and_balance_amount():
    """대조 1: 총 대금과 미지급 잔대금의 정상 분할 진술 (오탐 0)."""
    text = (
        "위 매매계약의 매매대금을 3억 원으로 정하였으나, 피고가 잔금 5,000만 원을 지급하지 않았습니다. "
        "따라서 원고는 미지급 잔액 5000만원의 지급을 구합니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)
    assert len(findings) == 0


def test_negative_2_incident_date_and_treatment_date():
    """대조 2: 사고 발생일과 치료/입원일 등 정상 후속 일자 (오탐 0)."""
    text = (
        "2023. 5. 12. 발생한 위 교통사고로 인하여 원고는 2023. 6. 12.까지 병원에서 치료를 받았습니다. "
        "이후 2023. 7. 10. 진단서를 발급받아 피고에게 제출하였습니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)
    assert len(findings) == 0


def test_negative_3_sublease_dual_capacity():
    """대조 3: 전대차 관계의 정상적 복수 지위 양립 (오탐 0)."""
    text = (
        "원고는 소외인의 임차인이자 피고의 전대인으로서 이 사건 임대차 및 전대차 관계를 체결하였습니다. "
        "따라서 원고의 지위는 복합적이며 이에 따른 권리를 행사합니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)
    assert len(findings) == 0


def test_negative_4_explicit_clerical_correction():
    """대조 4: 오기 정정 진술 (정정 필터, 오탐 0)."""
    text = (
        "이 사건 총 매매대금은 3억 원으로 정하였습니다. "
        "다만 소장 제2면에 위 매매계약 대금을 3억 5,000만 원으로 기재한 것은 단순 오기이므로 3억 원으로 바로잡습니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)
    assert len(findings) == 0


def test_negative_5_primary_and_alternative_claims():
    """대조 5: 주위적·예비적 청구금액 차이 (청구취지 차이, 오탐 0)."""
    text = (
        "주위적으로 위 매매계약 해제에 따른 원상회복으로 3억 원을 구하고, "
        "예비적으로 손해배상금 1억 원을 청구합니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)
    assert len(findings) == 0


def test_negative_6_different_clauses_no_conflict():
    """대조 6: 서로 다른 조항 원용 (제15조 면제 ↔ 제16조 손해배상, 오탐 0 및 등급 상향 통제)."""
    text = (
        "갑 제1호증(도급계약서) 제15조에 따라 지체상금이 면제되며, "
        "동 계약서 갑 제1호증 제16조에 의해 손해배상금이 청구됩니다."
    )
    doc = _make_doc(text)
    findings = check_internal_inconsistency(doc)
    assert len(findings) == 0


# --- 3. 정규식 선형 시간 복잡도 검증 시험 ---

def test_regex_linear_performance():
    """설계 메모 6절: 길이 1배·4배 텍스트 각 3회 측정, 최솟값 비 < 8, 4배 최솟값 < 1초 검증."""
    sample_text = (
        "이 사건 총 매매대금은 3억 원으로 정하였고 원고는 계약금을 완납하였습니다. "
        "2023. 5. 12. 발생한 위 교통사고로 인하여 원고의 차량이 파손되었습니다. "
        "원고가 임대인, 피고가 임차인으로서 이 사건 임대차계약을 체결하였습니다. "
        "갑 제1호증(도급계약서) 제15조에 따라 지체상금이 전액 면제되었습니다. "
    )
    text_1x = sample_text * 10
    text_4x = sample_text * 40

    doc_1x = _make_doc(text_1x)
    doc_4x = _make_doc(text_4x)

    times_1x = []
    for _ in range(3):
        t0 = time.perf_counter()
        check_internal_inconsistency(doc_1x)
        times_1x.append(time.perf_counter() - t0)

    times_4x = []
    for _ in range(3):
        t0 = time.perf_counter()
        check_internal_inconsistency(doc_4x)
        times_4x.append(time.perf_counter() - t0)

    min_1x = min(times_1x)
    min_4x = min(times_4x)

    # 4배 최솟값은 1초 미만이어야 함
    assert min_4x < 1.0, f"4배 텍스트 파싱 시간 초과: {min_4x:.4f}s >= 1.0s"

    # 1배 대비 4배의 비는 8 미만이어야 함 (선형 시간 보장)
    if min_1x > 0.0001:
        ratio = min_4x / min_1x
        assert ratio < 8.0, f"선형 복잡도 초과 (ReDoS 의심): ratio={ratio:.2f} >= 8.0"


def test_check_document_integration():
    """check_document 전체 진입점을 통해 내부 진술 모순 검사가 정상 수행됨을 검증."""
    from packages.claim_engine.evidence_consistency import check_document

    text = (
        "이 사건 총 매매대금은 3억 원으로 정하였고 원고는 계약금을 완납하였습니다. "
        "그러나 피고는 위 매매계약 당시 총 매매대금을 3억 5,000만 원으로 약정하였으며 일방적으로 증액을 요구합니다."
    )
    doc = _make_doc(text)
    findings = check_document(doc)

    incons_findings = [
        f for f in findings
        if f.confidence_features.get("rule_id") == "EVI.INCONS_INTERNAL_AMOUNT"
    ]
    assert len(incons_findings) == 1
    assert incons_findings[0].type == FindingType.FACT_CONTRADICTION

