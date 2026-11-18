"""TK-76 3주기 PR1: EVI-INCONS 계산식·수량·진술 불일치 탐지 일반화 단위 시험.

설계 메모(docs/handoff/requests/TK76_CYCLE3_EVI_INCONS_RESIDUAL_DESIGN_20261118.md) 4축 검증:
- 축 A (calculation.py): 배분 곱셈([수량][단위] [대상명사]에 [대상명사]당 [단가]씩 … 합계 [금액]) D6 회복 (양성 3건 + 대조군 3건)
- 축 B (cross_document_entities.py): 앵커 대상·속성 문서 간 대조(XDOC.ANCHORED_ATTRIBUTE) 비용·사용료·가액 및 소갑·소을 호증 확장 (양성 3건 + 대조군 3건)
- 축 C1 (internal_inconsistency.py): 문서 안 수량 불일치(EVI.INCONS_INTERNAL_QUANTITY) 능동·피동 이행 동사 및 단계 분리 (양성 4건 + 대조군 4건)
- 축 C2 (internal_inconsistency.py): 문서 안 서명자 불일치(EVI.INCONS_SIGNER_*) 문서 명사 확장 및 지시어 결속 (양성 4건 + 대조군 4건)
"""
from __future__ import annotations

import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.claim_engine.cross_document_entities import verify_cross_document_entities
from packages.claim_engine.internal_inconsistency import check_internal_inconsistency
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page

CASE_HEAD = "사건 2025가단71024 손해배상"


def _make_doc(*texts: str, doc_id: str = "synth_incons_pr1", head: str = "") -> NormalizedDocument:
    """합성 시험용 NormalizedDocument 생성 헬퍼."""
    blocks = []
    if head:
        blocks.append(Block(block_id=f"{doc_id}-h", text=head, page=1, visible=True, source_layer="visible_text"))
    for idx, t in enumerate(texts):
        blocks.append(Block(block_id=f"{doc_id}-b{idx + 1}", text=t, page=1, visible=True, source_layer="visible_text"))
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256=f"{doc_id}_sha256",
        pages=[Page(page_number=1, width=595.0, height=842.0, blocks=blocks)],
    )


# ==============================================================================
# 축 A: 배분 곱셈 피수식 명사-기준 명사 호응 복원 (D6 회복)
# ==============================================================================


@pytest.mark.parametrize("text", [
    # 양성 1: 수량 뒤 피수식 명사('5개 업체에 업체당 100만 원씩 … 합계 600만 원', 5 × 100만 = 500만 ≠ 600만)
    "원고는 5개 업체에 업체당 100만 원씩 지원금을 지급하여 합계 600만 원을 지출하였다.",
    # 양성 2: 수량 뒤 피수식 명사('3개 매장에 매장당 200만 원씩 … 총 700만 원', 3 × 200만 = 600만 ≠ 700만)
    "피고는 3개 매장에 매장당 200만 원씩 인테리어 비용을 배정하여 총 700만 원을 청구하였다.",
    # 양성 3: 수량 앞 피수식 명사('협력업체 4곳에 업체당 150만 원씩 … 도합 700만 원', 4 × 150만 = 600만 ≠ 700만)
    "원고는 협력업체 4곳에 업체당 150만 원씩 수수료를 송금하여 도합 700만 원을 부담하였다.",
])
def test_axis_a_distributive_counted_noun_positive(text: str):
    """축 A 양성 3건: 피수식 대상 명사와 '…당/마다' 기준 명사가 일치하는 배분 곱셈 불일치 탐지."""
    doc = _make_doc(text)
    findings = [
        f for f in CalculationEngine().verify_document(doc)
        if f.type == FindingType.ARITHMETIC_MISMATCH
    ]
    assert len(findings) == 1
    assert findings[0].status == VerificationStatus.CONTRADICTED


@pytest.mark.parametrize("text", [
    # 대조군 1: 계산 결과가 일치하는 배분 곱셈('5개 업체에 업체당 100만 원씩 … 합계 500만 원')
    "원고는 5개 업체에 업체당 100만 원씩 지원금을 지급하여 합계 500만 원을 지출하였다.",
    # 대조군 2: 피수식 명사('업체')와 다른 시간·기간 기준('월당')이 결합된 다변수 산식(기간 변수 누락 가능 -> 배제)
    "원고는 5개 업체에 월당 100만 원씩 지원금을 지급하여 합계 1,500만 원을 지출하였다.",
    # 대조군 3: 피수식 명사('매장')와 다른 대상 기준('인당')이 결합된 다변수 산식(인원 변수 누락 가능 -> 배제)
    "피고는 3개 매장에 인당 100만 원씩 교육비를 지급하여 합계 900만 원을 지출하였다.",
])
def test_axis_a_distributive_counted_noun_controls(text: str):
    """축 A 대조군 3건: 정합 산식 및 다변수(시간·타 기준) 배분 곱셈 오탐 0."""
    doc = _make_doc(text)
    findings = [
        f for f in CalculationEngine().verify_document(doc)
        if f.type == FindingType.ARITHMETIC_MISMATCH
    ]
    assert findings == []


# ==============================================================================
# 축 B: 문서 간 앵커 대상·속성 대조 (XDOC.ANCHORED_ATTRIBUTE) 확장
# ==============================================================================


@pytest.mark.parametrize("text_a, text_b", [
    # 양성 1: '이 사건 [대상]의 공사비' 문서 간 불일치
    ("이 사건 건물의 공사비는 5,000만 원이다.", "이 사건 건물의 공사비는 6,500만 원이다."),
    # 양성 2: '본건 [대상]의 임대료/관리비' 문서 간 불일치
    ("본건 상가의 월임대료는 300만 원이다.", "본건 상가 월임대료는 450만 원이다."),
    # 양성 3: '소갑 제N호증의 감정가액' 문서 간 불일치
    ("소갑 제3호증의 감정가액은 1억 2,000만 원이다.", "소갑 제3호증 감정가액은 1억 5,000만 원이다."),
])
def test_axis_b_anchored_attribute_fee_cost_positive(text_a: str, text_b: str):
    """축 B 양성 3건: 공사비·임대료·감정가액 및 소갑 호증 앵커의 문서 간 수치 불일치 탐지."""
    d1 = _make_doc(text_a, doc_id="xdoc_1", head=CASE_HEAD)
    d2 = _make_doc(text_b, doc_id="xdoc_2", head=CASE_HEAD)
    findings = [
        f for f in verify_cross_document_entities([d1, d2])
        if (f.confidence_features or {}).get("rule_id") == "XDOC.ANCHORED_ATTRIBUTE"
    ]
    assert len(findings) == 1
    f = findings[0]
    assert f.type == FindingType.CROSS_DOCUMENT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.B
    assert f.severity == Severity.HIGH
    assert f.status == VerificationStatus.SUSPICIOUS


@pytest.mark.parametrize("text_a, text_b", [
    # 대조군 1: 동일 대상이라도 서로 다른 비용 항목(공사비 vs 수리비) 비교 금지
    ("이 사건 건물의 공사비는 5,000만 원이다.", "이 사건 건물의 수리비는 1,200만 원이다."),
    # 대조군 2: 부분 금액('공사비 중 2,000만 원') 비교 금지
    ("이 사건 건물의 공사비는 5,000만 원이다.", "이 사건 건물의 공사비 중 2,000만 원은 지급되었다."),
    # 대조군 3: 상대방 주장 인용('피고는 …라고 주장한다') 및 다른 소갑 번호 비교 금지
    ("소갑 제3호증의 감정가액은 1억 2,000만 원이다.", "피고는 소갑 제3호증의 감정가액이 9,000만 원이라고 주장한다."),
])
def test_axis_b_anchored_attribute_fee_cost_controls(text_a: str, text_b: str):
    """축 B 대조군 3건: 상이 속성·부분 금액·상대방 주장 인용 오탐 0."""
    d1 = _make_doc(text_a, doc_id="xdoc_c1", head=CASE_HEAD)
    d2 = _make_doc(text_b, doc_id="xdoc_c2", head=CASE_HEAD)
    findings = [
        f for f in verify_cross_document_entities([d1, d2])
        if (f.confidence_features or {}).get("rule_id") == "XDOC.ANCHORED_ATTRIBUTE"
    ]
    assert findings == []


# ==============================================================================
# 축 C1: 문서 안 수량 불일치 (EVI.INCONS_INTERNAL_QUANTITY) 이행 동사·피동형 확장
# ==============================================================================


@pytest.mark.parametrize("text", [
    # 양성 1: 설치·시공 동사 결합 수량 충돌 ('20대를 설치' ↔ '15대를 설치')
    "원고는 이 사건 현장에 냉방기 20대를 설치하였습니다. 그러나 다른 준비서면에서는 위 냉방기 15대를 설치하였다고 기재하였습니다.",
    # 양성 2: 주격 조사 + 피동 서술어 결합 수량 충돌 ('40개가 설치되었다' ↔ '25개가 설치되었다')
    "이 사건 건물에는 태양광모듈 40개가 설치되었습니다. 한편 후속 서면에서는 위 태양광모듈 25개가 설치되었다고 진술합니다.",
    # 양성 3: 수령·인도받음 동사 결합 수량 충돌 ('100상자를 수령' ↔ '70상자를 인도받았')
    "피고는 원고로부터 부품 100상자를 수령하였습니다. 그러나 다른 단락에서는 위 부품 70상자를 인도받았다고 주장합니다.",
    # 양성 4: 매수·구입 동사 결합 수량 충돌 ('50톤을 매수' ↔ '30톤을 구입')
    "원고는 철근 50톤을 매수하여 현장에 투입하였습니다. 그런데 다른 서면에서는 위 철근 30톤을 구입하였다고 진술하였습니다.",
])
def test_axis_c1_internal_quantity_fulfillment_verbs_positive(text: str):
    """축 C1 양성 4건: 설치·피동형·수령·매수 등 이행 동사 결합 동일 목적물 수량 충돌 탐지."""
    doc = _make_doc(text)
    findings = [
        f for f in check_internal_inconsistency(doc)
        if f.confidence_features.get("rule_id") == "EVI.INCONS_INTERNAL_QUANTITY"
    ]
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.C
    assert findings[0].status == VerificationStatus.UNVERIFIED


@pytest.mark.parametrize("text", [
    # 대조군 1: 서로 다른 거래·물류 단계(생산 vs 판매, 입고 vs 출고)는 정당한 차이이므로 비교 금지
    "원고는 창고에 자재 100톤을 입고하였습니다. 이후 원고는 위 자재 60톤을 출고하였습니다.",
    # 대조군 2: 반품·폐기·잔여 수량 진술은 전체 수량과 비교 금지
    "원고는 피고에게 의류 200벌을 납품하였습니다. 이후 불량이 발견된 위 의류 30벌을 반품받았습니다.",
    # 대조군 3: 어림 수량('약 50대', '50대 가량')은 확정 수량이 아니므로 비교 금지
    "원고는 이 사건 현장에 냉방기 약 20대를 설치하였습니다. 실제 검수 결과 위 냉방기 18대를 설치하였습니다.",
    # 대조군 4: 부정 서술('설치하지 않았다')은 확정 수량 슬롯에서 제외
    "원고는 이 사건 현장에 냉방기 20대를 설치하지 않았습니다. 원고는 위 냉방기 15대를 설치하였습니다.",
])
def test_axis_c1_internal_quantity_fulfillment_verbs_controls(text: str):
    """축 C1 대조군 4건: 이행 단계 상이(입고/출고)·반품·어림수·부정문 오탐 0."""
    doc = _make_doc(text)
    findings = [
        f for f in check_internal_inconsistency(doc)
        if f.confidence_features.get("rule_id") == "EVI.INCONS_INTERNAL_QUANTITY"
    ]
    assert findings == []


# ==============================================================================
# 축 C2: 문서 안 서명자 불일치 (EVI.INCONS_SIGNER_*) 문서 명사 확장 및 지시어 결속
# ==============================================================================


@pytest.mark.parametrize("header_text, body_text, expected_grade", [
    # 양성 1: 차용증 단독 서명자 본문 내 상호 모순 (C등급)
    (
        "기초사실",
        "이 사건 차용증에는 채무자 김민수가 단독으로 서명하였습니다. 그러나 다른 단락에서는 위 차용증에 보증인 박지훈이 혼자 서명하였다고 진술합니다.",
        EvidenceGrade.C,
    ),
    # 양성 2: 위임장/보증서 단독 작성자 본문 내 상호 모순 (C등급)
    (
        "기초사실",
        "이 사건 위임장은 대표이사 최영호가 유일하게 작성하고 날인하였습니다. 한편 후속 진술에서는 위 위임장을 이사 정우성이 단독으로 작성하였다고 합니다.",
        EvidenceGrade.C,
    ),
    # 양성 3: 복합 문서명('이 사건 금전소비대차계약서')과 지시어 접미 문서명('위 계약서') 간 단독 서명자 모순 (C등급)
    (
        "기초사실",
        "이 사건 금전소비대차계약서는 원고 김민수가 단독으로 기명날인하였습니다. 그런데 후반부에서는 위 계약서를 피고 박지훈이 혼자 서명하였다고 기재하였습니다.",
        EvidenceGrade.C,
    ),
    # 양성 4: 서증 목록 괄호 문서명('갑 제4호증(영수증) 작성자: 김철수')과 본문 문서명('이 사건 영수증') 서명자 충돌 (B등급)
    (
        "갑 제4호증(영수증) 작성자: 김철수",
        "담당자 이영희가 직접 작성하고 서명한 이 사건 영수증을 교부받아 보관하고 있습니다.",
        EvidenceGrade.B,
    ),
])
def test_axis_c2_internal_signer_document_nouns_positive(
    header_text: str,
    body_text: str,
    expected_grade: EvidenceGrade,
):
    """축 C2 양성 4건: 차용증·위임장·영수증 및 복합 문서명 지시어 결속 서명자 모순 탐지."""
    doc = _make_doc(header_text, body_text)
    findings = [
        f for f in check_internal_inconsistency(doc)
        if f.confidence_features.get("inconsistency_type") == "SIGNER"
    ]
    assert len(findings) == 1
    assert findings[0].evidence_grade == expected_grade


@pytest.mark.parametrize("header_text, body_text", [
    # 대조군 1: 서로 다른 문서 종류(차용증 vs 영수증)의 단독 서명자 차이는 모순 아님
    (
        "기초사실",
        "이 사건 차용증에는 김민수가 단독으로 서명하였습니다. 한편 이 사건 영수증에는 박지훈이 단독으로 서명하였습니다.",
    ),
    # 대조군 2: 공동 서명(단독 표지 없음) 진술은 모순 아님
    (
        "기초사실",
        "이 사건 차용증에는 김민수가 서명하였습니다. 또한 위 차용증에는 연대보증인 박지훈이 함께 날인하였습니다.",
    ),
    # 대조군 3: 서명 부정 진술('서명하지 않았다')과 실제 서명자 진술은 모순 아님
    (
        "기초사실",
        "이 사건 위임장에는 김민수가 서명하지 않았습니다. 위 위임장에는 박지훈이 단독으로 서명하였습니다.",
    ),
    # 대조군 4: 선행 복합 계약서가 2종 이상('매매계약서', '도급계약서')일 때 '위 계약서' 모호 결속 금지
    (
        "기초사실",
        "이 사건 매매계약서는 김민수가 단독으로 작성하였고, 이 사건 도급계약서도 존재합니다. 한편 위 계약서는 박지훈이 단독으로 작성하였습니다.",
    ),
])
def test_axis_c2_internal_signer_document_nouns_controls(header_text: str, body_text: str):
    """축 C2 대조군 4건: 타 문서 종류·공동 서명·부정 서술·복수 선행 문서 모호 지시어 오탐 0."""
    doc = _make_doc(header_text, body_text)
    findings = [
        f for f in check_internal_inconsistency(doc)
        if f.confidence_features.get("inconsistency_type") == "SIGNER"
    ]
    assert findings == []


# ==============================================================================
# F1 보완: 수량 슬롯 미래·예정 서법 가드 (동사 축 × 미래 4꼴 대조 및 약정↔실제 양성 보존)
# ==============================================================================


@pytest.mark.parametrize("verb", [
    "공급", "납품", "설치", "제작", "시공", "수령", "구입", "출고",
])
@pytest.mark.parametrize("future_tail", [
    "할 예정이다",
    "할 계획이다",
    "할 것이다",
    "될 예정이다",
])
def test_f1_quantity_future_modality_cross_verbs_controls(verb: str, future_tail: str):
    """F1 대조(8동사 × 미래·예정 4꼴 = 32칸): 확정 수량과 아직 이행하지 않은 예정·계획 수량은 모순 아님(head 51546edd에서는 32칸 실패)."""
    if future_tail.startswith("될"):
        second_sentence = f"향후 위 기계 25대가 {verb}{future_tail}."
    else:
        second_sentence = f"향후 위 기계 25대를 {verb}{future_tail}."
    text = f"원고는 현장에 기계 40대를 {verb}하였다. {second_sentence}"
    doc = _make_doc(text)
    findings = [
        f for f in check_internal_inconsistency(doc)
        if f.confidence_features.get("rule_id") == "EVI.INCONS_INTERNAL_QUANTITY"
    ]
    assert findings == []


@pytest.mark.parametrize("text", [
    # 양성 1: 공급 약정 수량 ↔ 실제 인도 수량 불일치
    "원고는 피고에게 운동화 50켤레를 공급하기로 약정하였습니다. 그러나 실제 인도된 위 운동화 30켤레를 수령하는 데 그쳤습니다.",
    # 양성 2: 설치 합의 수량 ↔ 실제 설치 수량 불일치
    "피고는 이 사건 건물에 냉방기 40대를 설치하기로 합의하였습니다. 그러나 실제로는 위 냉방기 25대를 설치하였습니다.",
    # 양성 3: 납품 약정 수량 ↔ 실제 납품 수량 불일치
    "원고는 피고에게 부품 100상자를 납품하기로 약정하였습니다. 한편 후속 단락에서는 위 부품 70상자를 납품하였다고 기재하였습니다.",
    # 양성 4: 제작 합의 수량 ↔ 실제 제작(피동) 수량 불일치
    "피고는 현장에 철골구조물 60개를 제작하기로 합의하였습니다. 그러나 실제로는 위 철골구조물 35개가 제작되었습니다.",
])
def test_f1_agreed_vs_actual_quantity_positive_preserved(text: str):
    """F1 양성 4건: '…하기로 약정/합의' 수량 대 실제 이행 수량 불일치는 계속 탐지됨."""
    doc = _make_doc(text)
    findings = [
        f for f in check_internal_inconsistency(doc)
        if f.confidence_features.get("rule_id") == "EVI.INCONS_INTERNAL_QUANTITY"
    ]
    assert len(findings) == 1
    assert findings[0].evidence_grade == EvidenceGrade.C
    assert findings[0].status == VerificationStatus.UNVERIFIED


# ==============================================================================
# F2 보완: 호증 앵커 키 접두 구분 (소갑 ≠ 갑, 소을 ≠ 을) 및 원문 라벨 보존
# ==============================================================================


@pytest.mark.parametrize("text_a, text_b, expected_label", [
    # 양성 1: 갑 제3호증 ↔ 갑 제3호증 가액 불일치
    ("갑 제3호증의 감정가액은 1억 2,000만 원이다.", "갑 제3호증의 감정가액은 1억 5,000만 원이다.", "갑 제3호증"),
    # 양성 2: 소갑 제3호증 ↔ 소갑 제3호증 가액 불일치
    ("소갑 제3호증의 감정가액은 1억 2,000만 원이다.", "소갑 제3호증의 감정가액은 1억 5,000만 원이다.", "소갑 제3호증"),
    # 양성 3: 소을 제2호증 ↔ 소을 제2호증 공사비 불일치
    ("소을 제2호증의 공사비는 5,000만 원이다.", "소을 제2호증의 공사비는 7,000만 원이다.", "소을 제2호증"),
    # 양성 4: 병 제1호증 ↔ 병 제1호증 수수료 불일치
    ("병 제1호증의 수수료는 800만 원이다.", "병 제1호증의 수수료는 1,200만 원이다.", "병 제1호증"),
])
def test_f2_same_exhibit_prefix_and_number_positive(text_a: str, text_b: str, expected_label: str):
    """F2 양성 4건: 같은 종류·같은 번호 호증(갑↔갑, 소갑↔소갑, 소을↔소을, 병↔병) 값 불일치 탐지 및 원문 라벨 일치."""
    d1 = _make_doc(text_a, doc_id="f2_pos_1", head=CASE_HEAD)
    d2 = _make_doc(text_b, doc_id="f2_pos_2", head=CASE_HEAD)
    findings = [
        f for f in verify_cross_document_entities([d1, d2])
        if (f.confidence_features or {}).get("rule_id") == "XDOC.ANCHORED_ATTRIBUTE"
    ]
    assert len(findings) == 1
    assert findings[0].confidence_features["anchor"] == expected_label
    assert f"'{expected_label}'" in findings[0].title


@pytest.mark.parametrize("text_a, text_b, expected_label_a, expected_label_b", [
    # 대조 1: 갑 제3호증 ↔ 소갑 제3호증 (head 51546edd에서는 같은 키 '갑3-'로 묶여 오탐 1건 발생)
    ("갑 제3호증의 감정가액은 1억 2,000만 원이다.", "소갑 제3호증의 감정가액은 1억 5,000만 원이다.", "갑 제3호증", "소갑 제3호증"),
    # 대조 2: 을 제2호증 ↔ 소을 제2호증 (head 51546edd에서는 같은 키 '을2-'로 묶여 오탐 1건 발생)
    ("을 제2호증의 감정가액은 8,000만 원이다.", "소을 제2호증의 감정가액은 9,500만 원이다.", "을 제2호증", "소을 제2호증"),
    # 대조 3: 병 제1호증 ↔ 갑 제1호증
    ("병 제1호증의 공사비는 4,000만 원이다.", "갑 제1호증의 공사비는 6,000만 원이다.", "병 제1호증", "갑 제1호증"),
    # 대조 4: 소갑 제3호증 ↔ 소갑 제4호증
    ("소갑 제3호증의 감정가액은 1억 2,000만 원이다.", "소갑 제4호증의 감정가액은 1억 5,000만 원이다.", "소갑 제3호증", "소갑 제4호증"),
])
def test_f2_different_exhibit_prefix_same_number_controls(
    text_a: str,
    text_b: str,
    expected_label_a: str,
    expected_label_b: str,
):
    """F2 대조 4건: 종류가 다른 같은 번호(갑↔소갑, 을↔소을, 병↔갑) 및 다른 번호(소갑3↔소갑4) 오탐 0, 원문 라벨 보존."""
    from packages.claim_engine.cross_document_entities import _anchored_items

    d1 = _make_doc(text_a, doc_id="f2_ctrl_1", head=CASE_HEAD)
    d2 = _make_doc(text_b, doc_id="f2_ctrl_2", head=CASE_HEAD)
    items_1 = _anchored_items(d1)
    items_2 = _anchored_items(d2)
    assert len(items_1) == 1 and items_1[0]["label"] == expected_label_a
    assert len(items_2) == 1 and items_2[0]["label"] == expected_label_b
    assert items_1[0]["key"] != items_2[0]["key"]

    findings = [
        f for f in verify_cross_document_entities([d1, d2])
        if (f.confidence_features or {}).get("rule_id") == "XDOC.ANCHORED_ATTRIBUTE"
    ]
    assert findings == []

