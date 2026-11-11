# -*- coding: utf-8 -*-
"""TK-76 3주기 PR3 서증 원용 범위 초과(EVI-OVR) 구조적 탐지 및 수용 검증 시험.

- 설계 메모 보정본 docs/handoff/requests/TK-76_cycle3_evi_ovr_design_memo.md 반영:
  1) V1 서술어 자리 검증: 명사구 언급('변제를 최고하였다', '확정판결', '승인 여부를 묻는') 대조군 오탐 배제
  2) V2 어순 구조 검증: 인용 토큰 문미 위치 시 앞 절 지배 범위 자동 포함
  3) V3 사전 갱신: 새 낱말 5개('배달증명', '계약체결', '약정성립', '체결되었', '성립되었') 정상 탐지
  4) R6 정당 변론 제외: 형성권(해제, 해지, 취소, 상계, 철회) 행사 통지 및 처분문서(계약서, 합의서) 원용 오탐 배제
  5) R7 상대방 주장 가드: 탄핵 문맥(C3) 엄격 배제 및 자기 측 서증 원용 완화 검증
  6) OVR-01~08 8대 범주 양성 3건 / 대조 3건 및 3대 변형(어순, 연결어미, 동의어) 검증
"""

import pytest
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import check_evidence_overreach


def _make_doc(*texts: str, doc_id: str = "doc_tk76_ovr") -> NormalizedDocument:
    """합성 검증용 정규화 문서를 생성한다 (한국어 주석)."""
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


# ==============================================================================
# 1. 2-2 다 필수 요구: 설계 메모 5.2 핵심 시나리오 (양성 3건, 대조 3건)
# ==============================================================================

def test_scenario_p1_positive_notice_agreement_overreach():
    """양성 P1: 일방통지로 계약 성립 단정 시 과장 검출 (한국어 주석)."""
    doc = _make_doc(
        "청구원인",
        "원고는 최고서(갑 제1호증)에 의하여 본건 매매계약이 유효하게 성립되었음이 직접 입증됩니다.",
        "입증방법",
        "1. 갑 제1호증 최고서 (발신인: 원고)",
    )
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 1, f"P1 검출 실패: {findings}"
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "상대방의사표시" in findings[0].confidence_features.get("uncovered_predicates", [])


def test_scenario_p2_positive_estimate_completion_overreach():
    """양성 P2: 견적서로 공사 최종 완료 단정 시 과장 검출 (한국어 주석)."""
    doc = _make_doc(
        "공사비 청구",
        "갑 제2호증(공사견적내역서)에 의하여 본건 인테리어 공사가 모두 완료되었음이 확인됩니다.",
        "입증방법",
        "1. 갑 제2호증 공사견적내역서",
    )
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 1, f"P2 검출 실패: {findings}"
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "완료_확정" in findings[0].confidence_features.get("uncovered_predicates", [])


def test_scenario_p3_positive_receipt_total_debt_overreach():
    """양성 P3: 단일 입금확인증으로 채무 전액 완제 단정 시 과장 검출 (한국어 주석)."""
    doc = _make_doc(
        "변제 항변",
        "피고는 을 제3호증(입금확인증)으로 원고에 대한 모든 채무를 전액 완납하였음이 입증됩니다.",
        "입증방법",
        "1. 을 제3호증 입금확인증",
    )
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 1, f"P3 검출 실패: {findings}"
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "전칭_전기간" in findings[0].confidence_features.get("uncovered_predicates", [])


def test_scenario_c1_control_formation_right_exercise():
    """대조 C1 (R6): 최고서로 계약 해제 의사표시 도달 및 해제 효력 주장은 정상 변론 (오탐 0, 한국어 주석)."""
    doc = _make_doc(
        "계약 해제",
        "원고는 최고서(갑 제1호증)로써 계약 해제의 의사표시를 통지하여 해제되었습니다.",
        "입증방법",
        "1. 갑 제1호증 최고서 (발신인: 원고)",
    )
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 0, f"C1 오탐 발생: {findings}"


def test_scenario_c2_control_disposition_document_proof():
    """대조 C2 (R6): 합의서(처분문서)에 의한 합의 성립 입증은 정상 원용 (오탐 0, 한국어 주석)."""
    doc = _make_doc(
        "합의 성립",
        "갑 제4호증(합의서)에 의하여 피고와 사이에 본건 합의가 성립되었습니다.",
        "입증방법",
        "1. 갑 제4호증 합의서",
    )
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 0, f"C2 오탐 발생: {findings}"


def test_scenario_c3_control_impeachment_context():
    """대조 C3 (R7): 상대방 주장을 인용하여 배척·탄핵하는 정상 변론은 배제 유지 (오탐 0, 한국어 주석)."""
    doc = _make_doc(
        "반박 서면",
        "원고는 채무를 완제하였다고 주장하나, 을 제1호증에 비추어 보면 이는 사실이 아닙니다.",
        "입증방법",
        "1. 을 제1호증 확인서",
        "피고 소송대리인 변호사 김변호",
    )
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 0, f"C3 오탐 발생: {findings}"


# ==============================================================================
# 2. V1: 술어 위치 검증 (명사 언급 꼴 배제 대조군)
# ==============================================================================

def test_v1_predicate_noun_mention_not_overreach():
    """V1: 명사구 언급('변제를 최고하였다', '확정판결', '승인 여부를 묻는') 대조군 오탐 배제 (한국어 주석)."""
    cases = [
        # 1) '변제를 최고하였다' (목적어 명사구 결합)
        (
            "원고는 내용증명우편(갑 제1호증)으로 피고에게 채무 변제를 최고하였습니다.",
            "1. 갑 제1호증 내용증명우편 (발신인: 원고)"
        ),
        # 2) '확정판결' (복합명사 언급)
        (
            "원고는 내용증명(갑 제1호증)을 통해 확정판결에 따른 이행을 촉구한 바 있습니다.",
            "1. 갑 제1호증 내용증명"
        ),
        # 3) '승인 여부를 묻는' (명사 수식)
        (
            "원고는 최고서(갑 제1호증)를 발송하여 상대방에게 계약 승인 여부를 문의하였습니다.",
            "1. 갑 제1호증 최고서"
        ),
        # 4) '승인을 촉구하는' (목적격 조사 + 촉구)
        (
            "피고에게 채무 승인을 촉구하는 통고서(갑 제1호증)를 발송하였습니다.",
            "1. 갑 제1호증 통고서"
        ),
    ]
    for body_text, exhibit_line in cases:
        doc = _make_doc(body_text, "입증방법", exhibit_line)
        findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
        assert len(findings) == 0, f"V1 명사구 오탐 발생: {body_text} -> {findings}"


# ==============================================================================
# 3. V2: 어순 구조 규칙 검증 (문미 인용 토큰 지배 범위 포함)
# ==============================================================================

def test_v2_sentence_final_citation_governs_preceding_clause():
    """V2: 서증 인용이 문장 마지막 절에 올 때 앞 절의 결론 술어를 지배 범위로 포섭 검증 (한국어 주석)."""
    cases = [
        # 1) '...한 사실은 갑 제1호증과 같다'
        (
            "피고가 본건 매매계약 체결을 승낙한 사실은 최고서(갑 제1호증)의 기재로써 명백히 입증됩니다.",
            "1. 갑 제1호증 최고서 (발신인: 원고)",
            EvidenceGrade.B,
        ),
        # 2) '...한 점은 갑 제1호증에서 알 수 있다'
        (
            "상대방이 계약 해제에 동의한 점은 배달증명(갑 제2호증)에 의하여 명백히 확인됩니다.",
            "1. 갑 제2호증 배달증명 (발신인: 원고)",
            EvidenceGrade.B,
        ),
        # 3) '...사실은 갑 제3호증에 나타나 있다'
        (
            "본건 공사대금이 전액 완납된 사실은 견적서(을 제1호증)로 직접 증명됩니다.",
            "1. 을 제1호증 견적서",
            EvidenceGrade.B,
        ),
    ]
    for body_text, exhibit_line, expected_grade in cases:
        doc = _make_doc("주장 사실", body_text, "입증방법", exhibit_line)
        findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
        assert len(findings) >= 1, f"V2 문미 인용 검출 실패: {body_text}"
        assert findings[0].evidence_grade == expected_grade


# ==============================================================================
# 4. V3 정정 사항: 새 낱말 5개 검증
# ==============================================================================

def test_v3_new_words_detection():
    """V3: 새로 추가된 5개 낱말('배달증명', '계약체결', '약정성립', '체결되었', '성립되었') 정상 동작 검증 (한국어 주석)."""
    cases = [
        # 1) 배달증명 (일방통지)
        (
            "배달증명(갑 제1호증)에 의하여 피고가 계약 해제에 동의한 사실이 입증됩니다.",
            "1. 갑 제1호증 배달증명 (발신인: 원고)",
            "상대방의사표시",
        ),
        # 2) 계약체결 (상대방의사표시)
        (
            "원고의 최고서(갑 제2호증)로써 당사자 사이에 본건 계약체결이 확인됩니다.",
            "1. 갑 제2호증 최고서 (발신인: 원고)",
            "상대방의사표시",
        ),
        # 3) 약정성립 (상대방의사표시)
        (
            "통고서(갑 제3호증)에 의해 피고와의 물품공급 약정성립이 증명됩니다.",
            "1. 갑 제3호증 통고서 (발신인: 원고)",
            "상대방의사표시",
        ),
        # 4) 체결되었 (상대방의사표시)
        (
            "내용증명(갑 제4호증)에 따라 본건 매매계약이 유효하게 체결되었습니다.",
            "1. 갑 제4호증 내용증명 (발신인: 원고)",
            "상대방의사표시",
        ),
        # 5) 성립되었 (상대방의사표시)
        (
            "안내문(갑 제5호증)에 의하여 합의가 최종 성립되었습니다.",
            "1. 갑 제5호증 안내문 (발신인: 원고)",
            "상대방의사표시",
        ),
    ]
    for body_text, exhibit_line, expected_cat in cases:
        doc = _make_doc(body_text, "입증방법", exhibit_line)
        findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
        assert len(findings) == 1, f"새 낱말 검출 실패: {body_text}"
        assert expected_cat in findings[0].confidence_features.get("uncovered_predicates", [])


# ==============================================================================
# 5. R6: 정당한 형성권 행사 통지 대조군 3건 이상 (오탐 0)
# ==============================================================================

def test_r6_formation_rights_controls():
    """R6: 해제, 해지, 상계 등 형성권 행사 통지 및 효력 발생 정상 변론 오탐 배제 검증 (한국어 주석)."""
    cases = [
        # 1) 계약 해제 통지
        (
            "원고는 최고서(갑 제1호증)로써 계약 해제의 의사표시를 통지하여 적법하게 해제되었습니다.",
            "1. 갑 제1호증 최고서 (발신인: 원고)"
        ),
        # 2) 임대차계약 해지 통지
        (
            "피고에게 내용증명우편(갑 제2호증)을 발송하여 임대차계약 해지의 의사표시가 도달함으로써 해지되었습니다.",
            "1. 갑 제2호증 내용증명우편 (발신인: 원고)"
        ),
        # 3) 상계의 의사표시 통지
        (
            "원고는 통고서(갑 제3호증)로 상계의 의사표시를 통지하였는바, 채권채무가 대등액에서 소멸되었습니다.",
            "1. 갑 제3호증 통고서 (발신인: 원고)"
        ),
        # 4) 취소 의사표시 통지
        (
            "배달증명(갑 제4호증)에 의하여 사기 취소의 의사표시를 통지하여 본건 약정이 취소되었습니다.",
            "1. 갑 제4호증 배달증명 (발신인: 원고)"
        ),
    ]
    for body_text, exhibit_line in cases:
        doc = _make_doc(body_text, "입증방법", exhibit_line)
        findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
        assert len(findings) == 0, f"R6 형성권 오탐 발생: {body_text} -> {findings}"


# ==============================================================================
# 6. R7: 상대방 주장 탄핵 문맥 대조군 및 자기 측 서증 완화 검증
# ==============================================================================

def test_r7_impeachment_and_self_claim_relaxation():
    """R7: 탄핵 문맥(C3) 배제 유지 및 자기 측 서증 결론 단정 정상 탐지 검증 (한국어 주석)."""
    # 1. 탄핵 문맥 배제 (오탐 0건)
    impeachment_cases = [
        (
            "피고는 채무를 전부 변제하였다고 주장하지만, 갑 제1호증에 비추어 보면 전혀 사실이 아닙니다.",
            "1. 갑 제1호증 입금확인서"
        ),
        (
            "원고는 공사대금을 완납하였다고 다투나, 을 제1호증의 기재에 의하면 이유 없는 주장입니다.",
            "1. 을 제1호증 확인서"
        ),
        (
            "피고는 합의가 성립되었다고 번복하였으나, 갑 제2호증에 의하면 신빙성이 없는 주장입니다.",
            "1. 갑 제2호증 통지서"
        ),
    ]
    for body_text, exhibit_line in impeachment_cases:
        doc = _make_doc(body_text, "입증방법", exhibit_line, "원고 소송대리인 변호사 홍길동")
        findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
        assert len(findings) == 0, f"R7 탄핵 문맥 오탐 발생: {body_text} -> {findings}"

    # 2. 자기 측 서증 완화 (원고 측 서증으로 상대방 동의 단정 시 과장 정상 탐지)
    doc_self = _make_doc(
        "원고는 최고서(갑 제3호증)에 의하여 피고가 계약 해제에 동의하였음이 직접 확인됩니다.",
        "입증방법",
        "1. 갑 제3호증 최고서 (발신인: 원고)",
        "원고 소송대리인 변호사 홍길동",
    )
    findings_self = [f for f in check_evidence_overreach(doc_self) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings_self) == 1, f"R7 완화 미탐지: {findings_self}"
    assert findings_self[0].evidence_grade == EvidenceGrade.B


# ==============================================================================
# 7. 4.1 규칙별 득점 귀속표 (OVR-01 ~ OVR-08 양성/대조 검증)
# ==============================================================================

@pytest.mark.parametrize(
    "rule_id,cat_name,body_text,exhibit_line,expected_grade",
    [
        # OVR-01: 일방통지 × 상대방의사표시
        ("OVR-01", "일방통지", "최고서(갑 제1호증)에 의하여 피고가 계약 승낙을 하였음이 직접 입증됩니다.", "1. 갑 제1호증 최고서 (발신인: 원고)", EvidenceGrade.B),
        # OVR-02: 일방통지 × 완료_확정
        ("OVR-02", "일방통지", "통고서(갑 제2호증)에 의하여 대여금 채무가 전액 완납되었음이 확인됩니다.", "1. 갑 제2호증 통고서 (발신인: 원고)", EvidenceGrade.B),
        # OVR-03: 견적계획 × 완료_확정
        ("OVR-03", "견적계획", "공사 견적서(을 제1호증)로써 본건 인테리어 시공이 최종 완료되었음이 입증됩니다.", "1. 을 제1호증 공사 견적서", EvidenceGrade.B),
        # OVR-04: 명의식별 × 완료_확정
        ("OVR-04", "명의식별", "통장사본(갑 제3호증)에 의해 납품대금 전액이 모두 변제 완료되었음이 확인됩니다.", "1. 갑 제3호증 통장사본", EvidenceGrade.B),
        # OVR-05: 진단상태 × 내심의상태 (C등급 상한)
        ("OVR-05", "진단상태", "상해진단서(갑 제4호증)에 따라 피고가 고의로 가해 행위를 하였음이 입증됩니다.", "1. 갑 제4호증 상해진단서", EvidenceGrade.C),
        # OVR-06: 영상사진 × 전칭_전기간
        ("OVR-06", "영상사진", "현장사진(갑 제5호증)을 통해 피고가 전 기간 동안 계속 점유하였음이 증명됩니다.", "1. 갑 제5호증 사진", EvidenceGrade.B),
        # OVR-07: 영수입금 × 전칭_전기간
        ("OVR-07", "영수입금", "영수증(을 제2호증)으로 상대방에 대한 모든 채무가 전액 완제되었음이 확인됩니다.", "1. 을 제2호증 영수증", EvidenceGrade.B),
        # OVR-08: 진술확인 × 법률관계 확정 (C등급 상한)
        ("OVR-08", "진술확인", "확인서(갑 제6호증)에 의하여 본건 부동산의 소유권이 최종 확정되었음이 증명됩니다.", "1. 갑 제6호증 확인서", EvidenceGrade.C),
    ]
)
def test_rules_ovr_01_to_08_positive(rule_id, cat_name, body_text, exhibit_line, expected_grade):
    """4.1 득점 귀속표: OVR-01 ~ OVR-08 전 범주 양성 및 기대 등급 검증 (한국어 주석)."""
    doc = _make_doc(f"규칙 {rule_id}", body_text, "입증방법", exhibit_line)
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) == 1, f"규칙 {rule_id} ({cat_name}) 검출 실패: {body_text}"
    assert findings[0].evidence_grade == expected_grade, f"규칙 {rule_id} 등급 불일치: {findings[0]}"


# ==============================================================================
# 8. 4.2 3대 변형(어순, 연결어미, 동의어) 확장 검증
# ==============================================================================

@pytest.mark.parametrize(
    "variant_type,body_text,exhibit_line",
    [
        # 어순 1: 문두 인용
        ("어순-문두", "내용증명우편(갑 제1호증)에 의하여 피고와의 계약체결 사실이 인정됩니다.", "1. 갑 제1호증 내용증명우편 (발신인: 원고)"),
        # 어순 2: 문중 인용
        ("어순-문중", "원고는 최고서(갑 제1호증)에 따라 피고가 본건 합의에 승낙한 사실을 입증합니다.", "1. 갑 제1호증 최고서 (발신인: 원고)"),
        # 어순 3: 문미 인용 (V2)
        ("어순-문미", "피고가 본건 매매계약 체결을 승인한 사실은 배달증명(갑 제1호증)에서 명백히 확인됩니다.", "1. 갑 제1호증 배달증명 (발신인: 원고)"),

        # 연결어미 1: 종속 (-하므로)
        ("연결어미-종속", "갑 제2호증(견적서)에 의하여 공사가 모두 완료되었으므로 공사대금을 청구합니다.", "1. 갑 제2호증 견적서"),
        # 연결어미 2: 이유 (-하여)
        ("연결어미-이유", "산출내역서(갑 제2호증)를 제출하여 공사 준공이 완료되었음을 밝힙니다.", "1. 갑 제2호증 산출내역서"),
        # 연결어미 3: 단순 병렬 (-한바)
        ("연결어미-병렬", "공사계획서(갑 제2호증)에 따라 시공완료가 모두 마쳐진바, 잔금을 구합니다.", "1. 갑 제2호증 공사계획서"),

        # 동의어 1: 일방통지(통지서 vs 내용증명 vs 배달증명)
        ("동의어-통지서", "통지서(갑 제3호증)에 의해 피고가 계약 성립에 동의한 사실이 확인됩니다.", "1. 갑 제3호증 통지서 (발신인: 원고)"),
        # 동의어 2: 영수입금(입금증 vs 계좌이체영수증)
        ("동의어-입금증", "입금증(을 제1호증)으로 본건 미지급 공사비 전액이 전부 정산완료되었습니다.", "1. 을 제1호증 입금증"),
        # 동의어 3: 술어(변제 vs 완납 vs 정산완료)
        ("동의어-술어", "영수증(을 제1호증)에 의하여 일체의 대여금 채무가 모두 완제되었습니다.", "1. 을 제1호증 영수증"),
    ]
)
def test_three_variants_robustness(variant_type, body_text, exhibit_line):
    """4.2 3대 변형: 어순, 연결어미, 동의어 변형에 대한 견고성 검증 (한국어 주석)."""
    doc = _make_doc(f"변형 {variant_type}", body_text, "입증방법", exhibit_line)
    findings = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(findings) >= 1, f"3대 변형 검출 실패: {variant_type} - {body_text}"


# ==============================================================================
# 9. 평가 측 보완 F1~F4 단위 시험 (양성·대조, 평가 측 탐침 문장 배제)
# ==============================================================================

def test_f1_inner_intent_adverb_positive_and_negative():
    """F1: 내심의상태 부사/동사 연결 꼴 검출(양성) 및 명사 수식(여부 등) 배제(대조) 검증."""
    # 양성: 부사 꼴('악의로')로 다른 행위를 꾸미는 경우
    doc_pos = _make_doc(
        "F1 양성",
        "상해진단서(갑 제1호증)에 의하여 피고가 악의로 손해를 가하였음이 명백합니다.",
        "입증방법",
        "1. 갑 제1호증 상해진단서",
    )
    f_pos = [f for f in check_evidence_overreach(doc_pos) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_pos) == 1, "F1 내심 부사 꼴 양성 검출 실패"

    # 대조: 명사 수식(_NOUN_FOLLOWERS_PAT)으로 '악의 여부'를 논하는 경우
    doc_neg = _make_doc(
        "F1 대조",
        "상해진단서(갑 제1호증)만으로는 피고의 악의 여부를 단정할 수 없습니다.",
        "입증방법",
        "1. 갑 제1호증 상해진단서",
    )
    f_neg = [f for f in check_evidence_overreach(doc_neg) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_neg) == 0, "F1 명사 수식 대조 오탐 발생"


def test_f2_receive_predicate_money_object_positive_and_negative():
    """F2: 일반 동사 '받다'의 목적어가 금전일 때만 완료 술어로 인정(양성), 비금전 목적어 배제(대조)."""
    # 양성: 목적어가 금전('물품대금을 모두 받았다')
    doc_pos = _make_doc(
        "F2 양성",
        "통고서(갑 제1호증)에 의하여 원고가 미지급 물품대금을 모두 받았음이 확인됩니다.",
        "입증방법",
        "1. 갑 제1호증 통고서 (발신인: 피고)",
    )
    f_pos = [f for f in check_evidence_overreach(doc_pos) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_pos) == 1, "F2 금전 목적어 수령 양성 검출 실패"

    # 대조: 목적어가 비금전('정밀 검진을 받았다')인 경우 완료 술어로 세지 않음
    doc_neg = _make_doc(
        "F2 대조",
        "진단서(갑 제1호증)를 통해 원고가 종합병원에서 정밀 검진을 받았음이 증명됩니다.",
        "입증방법",
        "1. 갑 제1호증 진단서",
    )
    f_neg = [f for f in check_evidence_overreach(doc_neg) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_neg) == 0, "F2 비금전 목적어 수령 대조 오탐 발생"


def test_f3_composite_predicate_prefix_and_chain():
    """F3: 합성 술어 앞 수식 명사 허용(양성1) 및 '이루어지다' 연쇄 완료 인정(양성2)."""
    # 양성 1: 앞 수식 명사 결합('임대차계약체결')
    doc_pos1 = _make_doc(
        "F3 양성1",
        "최고서(갑 제1호증)에 의하여 피고와 사이에 본건 임대차계약체결 사실이 증명됩니다.",
        "입증방법",
        "1. 갑 제1호증 최고서 (발신인: 원고)",
    )
    f_pos1 = [f for f in check_evidence_overreach(doc_pos1) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_pos1) == 1, "F3 앞 수식 명사 결합 계약체결 양성 검출 실패"

    # 양성 2: '이루어지다' 연쇄('변제가 이루어졌음')
    doc_pos2 = _make_doc(
        "F3 양성2",
        "견적서(갑 제2호증)에 의하여 본건 변제가 이루어졌음이 입증됩니다.",
        "입증방법",
        "1. 갑 제2호증 견적서",
    )
    f_pos2 = [f for f in check_evidence_overreach(doc_pos2) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_pos2) == 1, "F3 '이루어지다' 연쇄 완료 양성 검출 실패"


def test_f4_omitted_subject_not_counted_as_opponent_intent():
    """F4: 주체 생략 절을 상대방의사표시로 세지 않음(대조), '상대방' 주체 명시 시 인정(양성)."""
    # 대조: 주체 생략 절은 작성자(발신인) 본인의 조건부 승인/통지이므로 상대방의사표시 배제
    doc_neg = _make_doc(
        "F4 대조",
        "최고서(갑 제1호증)를 보내어 본건 분할변제안에 대하여 승인하였습니다.",
        "입증방법",
        "1. 갑 제1호증 최고서 (발신인: 원고)",
    )
    f_neg = [f for f in check_evidence_overreach(doc_neg) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_neg) == 0, "F4 주체 생략 절 작성자 행위 대조 오탐 발생"

    # 양성: 주체로 '상대방이' 또는 '상대방 측이'가 명시된 경우
    doc_pos = _make_doc(
        "F4 양성",
        "최고서(갑 제1호증)에 의하여 상대방 측이 본건 화해안을 승인하였음이 인정됩니다.",
        "입증방법",
        "1. 갑 제1호증 최고서 (발신인: 원고)",
    )
    f_pos = [f for f in check_evidence_overreach(doc_pos) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(f_pos) == 1, "F4 상대방 주체 명시 양성 검출 실패"
