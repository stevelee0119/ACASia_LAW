"""TK-91 증거 과장(EVI-OVR) 구조적 탐지 및 확정 기준 검증 시험.

- 메모 보정본 128_tk91_evi_ovr_design_revision.md 및 조건부 승인 조건 전면 반영:
  1) 범주 사전에서 '현장', '감정서' 제외
  2) 7대 범주 × 4대 술어 능력 매트릭스 코드 상수화 및 전액·전부·모두 추가
  3) 증명 대상 절 한정
  4) 부정 술어, 상대방 주장, 가정·조건, 의문 제외 가드
  5) 증거목록·인용 괄호에서만 서증 추출
  6) 직접 증명 구조 B등급 및 진단상태/진술확인 C등급 상한, 따옴표 오타('r') 완전 수정
  7) 'r' 갈래 매칭 시험, 7대 범주 × 3변형(21문장), 대조 7개 이상, 부정/상대방 주장 대조
"""

import pytest
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import (
    check_evidence_overreach,
    check_exhibits,
    _DIRECT_PROOF_STRUCTURE_RE,
)


def _make_doc(*texts: str, doc_id: str = "doc_ovr_test_1") -> NormalizedDocument:
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


# --- 1. 조건 7 요구: 'r' 갈래 매칭 시험 ------------------------------------------------

def test_direct_proof_structure_first_branch_matching():
    """조건 7: 따옴표 오타가 수정된 _DIRECT_PROOF_STRUCTURE_RE 첫 번째 갈래의 정상 매칭을 검증한다 (한국어 주석)."""
    text_sample = "갑 제1호증에 의하면 피고의 채무 불이행 사실이 명백히 입증된다."
    m = _DIRECT_PROOF_STRUCTURE_RE.search(text_sample)
    assert m is not None, f"첫 번째 갈래 매칭 실패: {text_sample}"

    text_sample2 = "을 제3호증으로 피고의 귀책사유가 충분히 증명되었다."
    m2 = _DIRECT_PROOF_STRUCTURE_RE.search(text_sample2)
    assert m2 is not None, f"첫 번째 갈래 변형 매칭 실패: {text_sample2}"


# --- 2. 조건 7 요구: 7대 범주 × 3변형(어순, 연결어미, 동의어) 21문장 양성 시험 ----------

@pytest.mark.parametrize(
    "cat_idx,variant,heading,body_text,exhibit_line,expected_grade",
    [
        # 1. 일방통지 (내용증명, 최고서 등)
        (1, "어순 역전", "1-1. 통지", "피고가 계약 해제에 동의한 사실은 최고서(갑 제3호증)에 의하여 입증됩니다.", "1. 갑 제3호증 최고서 (발신인: 원고)", EvidenceGrade.B),
        (1, "연결어미 변형", "1-2. 통지", "원고가 발송한 최고서에 따라 피고는 계약 해제에 동의하였는바(갑 제3호증), 원상회복을 구합니다.", "1. 갑 제3호증 내용증명우편(최고서) (발신인: 원고)", EvidenceGrade.B),
        (1, "동의어 변형", "1-3. 통지", "원고의 통고서(갑 제3호증)로써 피고가 채무 승인을 합의하였음이 확인됩니다.", "1. 갑 제3호증 통고서 (발신인: 원고)", EvidenceGrade.B),

        # 2. 견적계획 (견적서, 산출내역서 등)
        (2, "어순 역전", "2-1. 견적", "공사대금을 전액 완납한 사실은 공사 견적서(을 제2호증)로 직접 증명됩니다.", "1. 을 제2호증 공사 견적서", EvidenceGrade.B),
        (2, "연결어미 변형", "2-2. 견적", "피고는 공사비 산출내역서(을 제2호증)에 따라 공사대금을 전액 정산 완료하였으므로, 추가 청구는 부당합니다.", "1. 을 제2호증 공사비 산출내역서", EvidenceGrade.B),
        (2, "동의어 변형", "2-3. 견적", "원고는 공사예산서(을 제2호증)를 통해 시공이 최종 준공되었음을 입증합니다.", "1. 을 제2호증 공사예산서", EvidenceGrade.B),

        # 3. 명의식별 (통장표지, 사업자등록증 등)
        (3, "어순 역전", "3-1. 명의", "물품대금 전액을 완납한 사실은 통장 표지 사본(갑 제4호증)으로 확인됩니다.", "1. 갑 제4호증 통장 표지 사본", EvidenceGrade.B),
        (3, "연결어미 변형", "3-2. 명의", "원고는 사업자등록증(갑 제4호증)에 의해 납품대금을 전액 변제 완료한바, 이행의무를 다하였습니다.", "1. 갑 제4호증 사업자등록증", EvidenceGrade.B),
        (3, "동의어 변형", "3-3. 명의", "통장사본(갑 제4호증)으로써 차용원리금 전액이 모두 지급완료되었음이 입증됩니다.", "1. 갑 제4호증 통장사본", EvidenceGrade.B),

        # 4. 진단상태 (상해진단서, 소견서 등 - 조건 6: C등급 상한)
        (4, "어순 역전", "4-1. 진단", "피고가 원고에게 불법행위를 가한 사실은 상해진단서(갑 제5호증)로 직접 확인됩니다.", "1. 갑 제5호증 상해진단서", EvidenceGrade.C),
        (4, "연결어미 변형", "4-2. 진단", "원고에 대한 피고의 가해 행위는 의사의 소견서(갑 제5호증)에 따라 명백히 입증되는바, 손해배상 책임이 있습니다.", "1. 갑 제5호증 의사소견서", EvidenceGrade.C),
        (4, "동의어 변형", "4-3. 진단", "진료기록부(갑 제5호증)를 통하여 피고가 고의로 상해를 가한 사실이 직접 증명됩니다.", "1. 갑 제5호증 진료기록부", EvidenceGrade.C),

        # 5. 영상사진 (사진, 녹화영상 등)
        (5, "어순 역전", "5-1. 사진", "원고가 항상 근무지에 상주한 사실은 현장 사진(갑 제6호증)으로 직접 입증됩니다.", "1. 갑 제6호증 사진", EvidenceGrade.B),
        (5, "연결어미 변형", "5-2. 사진", "피고는 녹화영상(갑 제6호증)에 의해 전 기간 내내 공모하여 범행을 지속하였음이 확인됩니다.", "1. 갑 제6호증 녹화영상", EvidenceGrade.B),
        (5, "동의어 변형", "5-3. 사진", "화면캡처(갑 제6호증)를 통하여 상대방이 줄곧 악의로 일체를 거부하였음이 증명됩니다.", "1. 갑 제6호증 화면캡처", EvidenceGrade.B),

        # 6. 영수입금 (영수증, 입금증 등 - 전액·전부 등 전칭 결합 비약)
        (6, "어순 역전", "6-1. 영수", "피고는 모든 채무를 전액 완납하였음이 영수증(을 제4호증)으로 확인됩니다.", "1. 을 제4호증 영수증", EvidenceGrade.B),
        (6, "연결어미 변형", "6-2. 영수", "원고가 발행한 입금증(을 제4호증)에 따라 일체의 손해배상금이 전부 변제 완료되었는바, 더 이상의 청구는 부당합니다.", "1. 을 제4호증 입금증", EvidenceGrade.B),
        (6, "동의어 변형", "6-3. 영수", "계좌이체영수증(을 제4호증)을 통하여 상대방에 대한 모든 미지급 공사대금이 모두 정산 완료되었음이 입증됩니다.", "1. 을 제4호증 계좌이체영수증", EvidenceGrade.B),

        # 7. 진술확인 (제3자 확인서, 인우보증서 등 - 조건 6: C등급 상한)
        (7, "어순 역전", "7-1. 확인", "원고에게 소유권이 확정적으로 귀속된 사실은 확인서(갑 제7호증)로 명백히 입증됩니다.", "1. 갑 제7호증 확인서", EvidenceGrade.C),
        (7, "연결어미 변형", "7-2. 확인", "인우보증서(갑 제7호증)에 따라 당사자 간의 합의가 최종 확정되었는바, 권리관계가 명백합니다.", "1. 갑 제7호증 인우보증서", EvidenceGrade.C),
        (7, "동의어 변형", "7-3. 확인", "사실확인서(갑 제7호증)를 통하여 피고의 채무변제 의무가 완전히 확정되었음이 증명됩니다.", "1. 갑 제7호증 사실확인서", EvidenceGrade.C),
    ],
)
def test_positive_seven_categories_three_variants(
    cat_idx: int, variant: str, heading: str, body_text: str, exhibit_line: str, expected_grade: EvidenceGrade
):
    """조건 7: 7대 서증 범주 각각 양성 1개 이상 × 3대 변형(어순, 연결어미, 동의어) 21문장 검증 (한국어 주석)."""
    doc = _make_doc(heading, body_text, "입증방법", exhibit_line)
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) >= 1, f"검출 실패: 범주 {cat_idx} ({variant}) - {body_text}"
    f = ovr[0]
    assert f.evidence_grade == expected_grade, f"등급 불일치 ({f.evidence_grade} != {expected_grade}): {body_text}"


# --- 3. 조건 7 요구: 대조군 시험 (7개 이상 및 부정/상대방 주장 대조) -------------------

def test_control_notice_proper_dispatch_proof():
    """대조 1: 통지·최고 발송 사실 자체를 입증하는 정상 서면 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "원고는 피고에게 채무 이행을 최고하는 내용증명을 발송하였습니다(갑 제2호증).",
        "입증방법",
        "1. 갑 제1호증 차용증",
        "2. 갑 제2호증 내용증명우편",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"오탐 발생: {findings}"


def test_control_diagnostic_result_indirect_proof():
    """대조 2: 진단서로 상해 발생 결과를 입증하는 통상 간접증거 인용 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "피고의 불법행위로 인해 원고는 전치 3주의 상해를 입었는바(갑 제4호증), 치료비 상당의 손해배상을 구합니다.",
        "입증방법",
        "1. 갑 제4호증 상해진단서",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"오탐 발생: {findings}"


def test_control_financial_receipt_proof():
    """대조 3: 입금확인증으로 기재된 공사대금 지급 사실을 입증하는 정상 서면 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "피고는 공사대금 3,000만 원을 정상 지급 완료하였습니다(을 제3호증).",
        "입증방법",
        "1. 을 제3호증 입금확인증",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"오탐 발생: {findings}"


def test_control_bundled_exhibits_with_proof():
    """대조 4: 복수 서증 결합 원용(견적서 + 입금확인증) 시 과장 판정 배제 (한국어 주석)."""
    doc = _make_doc(
        "원고는 공사대금을 정산 지급 완료하였습니다(을 제2호증, 을 제3호증).",
        "입증방법",
        "1. 을 제2호증 공사 견적서",
        "2. 을 제3호증 계좌거래내역 입금확인증",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"오탐 발생: {findings}"


def test_control_notice_unknown_sender_fixed_to_grade_c():
    """대조 5: 발신인 불명 내용증명으로 상대방 채무승인 주장 시 C등급(UNVERIFIED) 고정 (한국어 주석)."""
    doc = _make_doc(
        "피고는 자신의 채무를 명시적으로 승인하였습니다(갑 제6호증 내용증명).",
        "입증방법",
        "1. 갑 제6호증 내용증명우편",
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1, f"검출 실패: {ovr}"
    assert ovr[0].evidence_grade == EvidenceGrade.C
    assert ovr[0].status == VerificationStatus.UNVERIFIED


def test_control_opposite_party_notice_approval_claim():
    """대조 6: 상대방이 보낸 통지서로 상대방의 의무 승인/합의를 주장하는 정상 서면 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "소장",
        "원고 홍길동",
        "피고 주식회사 케이건설",
        "피고가 발송한 최고서에 피고의 채무 승인 사실이 기재되어 있습니다(갑 제2호증).",
        "원고 소송대리인 변호사 김변호",
        "입증방법",
        "1. 갑 제1호증 도급계약서",
        "2. 갑 제2호증 최고서 (발신인: 피고)",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"오탐 발생: {findings}"


def test_control_estimate_scope_specification():
    """대조 7: 견적서로 공사 범위를 특정하고 그 범위의 공사 완료를 서술한 정상 문장 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "피고는 견적서(을 제2호증)에 기재된 방수공사 범위를 시공 범위로 특정하고, 해당 범위의 공사를 정상적으로 완료하였습니다.",
        "입증방법",
        "1. 을 제1호증 도급계약서",
        "2. 을 제2호증 견적서",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"오탐 발생: {findings}"


def test_control_negated_predicate():
    """조건 7 대조 8: 부정된 술어 대조군 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "최고서(갑 제3호증)만으로 피고가 채무를 승인했다고 볼 수 없습니다.",
        "입증방법",
        "1. 갑 제3호증 최고서",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"부정된 술어에서 오탐 발생: {findings}"


def test_control_opponent_claim():
    """조건 7 대조 9: 상대방 주장 인용 대조군 오탐 배제 (한국어 주석)."""
    doc = _make_doc(
        "피고는 내용증명(갑 제3호증)에 의해 합의가 성립되었다고 주장하나, 이는 사실과 다릅니다.",
        "입증방법",
        "1. 갑 제3호증 내용증명",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"상대방 주장 인용에서 오탐 발생: {findings}"


# --- 4. 실제 진입점 파이프라인 연계 시험 ----------------------------------------------

def test_pipeline_evidence_overreach_entrypoint():
    """실제 check_exhibits 진입점을 통한 EVI-OVR 검출 및 속성 완전성 검증 (한국어 주석)."""
    doc = _make_doc(
        "원고는 피고에게 공사비 산출내역서(을 제2호증)에 따라 공사대금을 전액 완납하였습니다.",
        "입증방법",
        "1. 을 제1호증 공사도급계약서",
        "2. 을 제2호증 공사비 산출내역서",
    )
    findings = check_exhibits(doc)
    ovr_findings = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr_findings) == 1
    f = ovr_findings[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.confidence_features.get("exhibit") == "을 제2호증"
    assert f.confidence_features.get("category") == "ESTIMATE_OVERREACH"
    assert "을 제2호증" in f.evidence[0].excerpt


# --- 5. B-1 4차 보완 S1~S8 검증 시험 ----------------------------------------------

def test_s1_predicate_word_boundary_and_non_intent_controls():
    """S1: '의사표시', 직업 '의사', '해지 의사', 복합어('합의서', '확정판결', '계속적 거래') 대조군 (오탐 0)."""
    # 1) 의사표시, 해지 의사 통지 대조
    doc1 = _make_doc(
        "원고는 계약 해제의 의사표시를 최고서(갑 제1호증)로써 피고에게 도달시켰습니다.",
        "입증방법", "1. 갑 제1호증 최고서 (발신인: 원고)"
    )
    assert len(check_evidence_overreach(doc1)) == 0

    # 2) 직업 의사 대조
    doc2 = _make_doc(
        "원고는 담당 의사의 진단에 따라 상해진단서(갑 제2호증)를 발급받았습니다.",
        "입증방법", "1. 갑 제2호증 상해진단서"
    )
    assert len(check_evidence_overreach(doc2)) == 0

    # 3) 낱말 경계 복합어 대조: 합의서, 확정판결, 계속적 거래
    doc3 = _make_doc(
        "당사자들은 합의서(을 제1호증)를 작성하였고, 확정판결 및 계속적 거래 관계를 유지하였습니다.",
        "입증방법", "1. 을 제1호증 합의서"
    )
    assert len(check_evidence_overreach(doc3)) == 0


def test_s2_notice_predicate_subject_controls_and_positive():
    """S2: 자기 측 통지로 자기 해제 의사표시 도달 증명은 오탐 0, 상대방 승낙 단정은 양성(B)."""
    # 1) 정상 대조군: 자기 측 통지로 자기 해제 의사표시의 도달을 증명
    doc_ctrl = _make_doc(
        "원고는 최고서(갑 제1호증)에 의하여 원고의 해제 의사가 피고에게 도달하였음을 확인합니다.",
        "입증방법", "1. 갑 제1호증 최고서 (발신인: 원고)"
    )
    assert len(check_evidence_overreach(doc_ctrl)) == 0

    # 2) 양성: 자기 측 통지로 피고(상대방)의 승낙을 단정
    doc_pos = _make_doc(
        "원고의 최고서(갑 제1호증)에 의하여 피고가 계약 해제를 승낙한 사실이 입증됩니다.",
        "입증방법", "1. 갑 제1호증 최고서 (발신인: 원고)"
    )
    findings = check_evidence_overreach(doc_pos)
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.B


def test_s3_sender_detection_from_exhibit_or_prep_clause():
    """S3: 발신인이 자기 측이고 술어 주체가 상대방인 문장 양성, 상대방 발신 통지는 제외 대조군."""
    # 1) 바로 앞 관형절로 발신인 특정 양성
    doc_pos = _make_doc(
        "원고가 발송한 최고서(갑 제1호증)에 따라 피고가 채무를 승인한 사실이 확인됩니다.",
        "입증방법", "1. 갑 제1호증 최고서"
    )
    findings = check_evidence_overreach(doc_pos)
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.B

    # 2) 상대방 발신 통지는 상대방 의무 입증에 정당하므로 제외 대조군
    doc_ctrl = _make_doc(
        "피고가 발송한 최고서(갑 제1호증)에 의하여 피고의 채무 승인 사실이 명백히 입증됩니다.",
        "입증방법", "1. 갑 제1호증 최고서"
    )
    assert len(check_evidence_overreach(doc_ctrl)) == 0


def test_s4_direct_proof_structure_five_surface_forms():
    """S4: 직접 증명 구조 5대 표면형((으)로, 에 의하여, 을/를 통해, 에 비추어, (으)로써) B등급 검증."""
    surface_cases = [
        ("(으)로", "최고서(갑 제1호증)로 피고가 승낙한 사실이 입증됩니다."),
        ("에 의하여", "갑 제1호증에 의하여 피고가 동의한 사실이 인정됩니다."),
        ("을/를 통해", "내용증명(갑 제1호증)을 통해 피고가 승인하였음이 확인됩니다."),
        ("에 비추어", "갑 제1호증에 비추어 피고가 합의한 사실이 분명히 밝혀집니다."),
        ("(으)로써", "갑 제1호증으로써 피고의 승낙 사실이 명백히 증명됩니다."),
    ]
    for surf_label, text in surface_cases:
        doc = _make_doc(text, "입증방법", "1. 갑 제1호증 내용증명우편(최고서) (발신인: 원고)")
        findings = check_evidence_overreach(doc)
        assert len(findings) == 1, f"표면형 {surf_label} 검출 실패: {text}"
        assert findings[0].evidence_grade == EvidenceGrade.B, f"표면형 {surf_label} B등급 실패: {findings[0]}"


def test_s5_no_proof_scope_clause_excluded():
    """S5: 증명 대상 절이 없는 단순 사실 언급 서면은 판정 제외 (오탐 0)."""
    doc = _make_doc(
        "원고는 피고에게 최고서(갑 제1호증)를 우체국을 통하여 발송한 사실이 있습니다.",
        "입증방법", "1. 갑 제1호증 최고서"
    )
    assert len(check_evidence_overreach(doc)) == 0


def test_s6_completion_and_total_amount_predicates():
    """S6: '지급을 마친', '갚았다', '납부를 끝마쳤다' 및 채무 명사 수식 전칭 양성 검증."""
    # 1) 지급을 마친
    doc1 = _make_doc(
        "공사대금 지급을 마친 사실은 공사비 산출내역서(을 제1호증)로 직접 입증됩니다.",
        "입증방법", "1. 을 제1호증 공사비 산출내역서"
    )
    assert len(check_evidence_overreach(doc1)) == 1

    # 2) 갚았다
    doc2 = _make_doc(
        "원고에 대한 차용금을 모두 갚았음이 견적서(을 제2호증)에 의하여 확인됩니다.",
        "입증방법", "1. 을 제2호증 견적서"
    )
    assert len(check_evidence_overreach(doc2)) == 1

    # 3) 납부를 끝마쳤다
    doc3 = _make_doc(
        "피고는 공사비 납부를 끝마쳤음을 산출내역서(을 제3호증)를 통해 증명합니다.",
        "입증방법", "1. 을 제3호증 산출내역서"
    )
    assert len(check_evidence_overreach(doc3)) == 1

    # 4) 채무 명사 수식 전칭('모든 채무를 전액') 영수증 양성
    doc4 = _make_doc(
        "피고는 모든 채무를 전액 완납하였음이 영수증(을 제4호증)으로 증명됩니다.",
        "입증방법", "1. 을 제4호증 영수증"
    )
    assert len(check_evidence_overreach(doc4)) == 1


def test_s7_clause_level_exclusion_guard():
    """S7: 다른 절에 부정 표현이 있어도 증명 대상 절의 과장은 정확히 잡히는 양성 검증."""
    doc = _make_doc(
        "원고의 청구는 이유가 없으나, 피고가 계약 해제를 승낙한 사실은 최고서(갑 제1호증)에 의하여 명백히 입증됩니다.",
        "입증방법", "1. 갑 제1호증 최고서 (발신인: 원고)"
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.B


def test_s8_severity_assertion_retained():
    """S8: 발신인 불명 통지는 C등급 및 Severity.MEDIUM 단언 검증."""
    doc = _make_doc(
        "피고는 자신의 채무를 명시적으로 승인하였습니다(갑 제6호증 내용증명).",
        "입증방법", "1. 갑 제6호증 내용증명우편"
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1
    assert ovr[0].evidence_grade == EvidenceGrade.C
    assert ovr[0].severity == Severity.MEDIUM

