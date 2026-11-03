"""TK-76 3주기 1항 PR2: 앵커가 있는 대상·속성의 문서 간 대조(설계 메모 3.1·M6·M7, 승인 조건 N1).

같은 사건 묶음의 두 문서가 '이 사건/본건 [대상]의 [속성]' 또는 '갑·을 제N호증의 [속성]'을 서로 다른 값으로
확정 서술하면 CROSS_DOCUMENT_CONTRADICTION(SUSPICIOUS·B·HIGH)을 낸다. 앵커가 없으면 결과를 만들지 않는다.
합성 문장만 쓴다.
"""
from __future__ import annotations

import pytest

from packages.claim_engine.cross_document_entities import verify_cross_document_entities
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page

HEAD = "사건 2025가단30418 물품대금"


def _doc(i: int, text: str, head: str = HEAD) -> NormalizedDocument:
    blocks = [Block(block_id=f"d{i}-h", text=head, page=1), Block(block_id=f"d{i}-b", text=text, page=1)]
    return NormalizedDocument(document_id=f"d{i}", filename=f"d{i}.pdf", mime_type="application/pdf", sha256=str(i),
                              pages=[Page(page_number=1, height=800, blocks=blocks)])


def _anchored(a: str, b: str, head_b: str = HEAD):
    findings = verify_cross_document_entities([_doc(1, a), _doc(2, b, head_b)])
    return [f for f in findings if (f.confidence_features or {}).get("rule_id") == "XDOC.ANCHORED_ATTRIBUTE"]


@pytest.mark.parametrize("a,b", [
    ("이 사건 기계의 설치일은 2022. 2. 15.이다.", "이 사건 기계 설치일은 2022. 3. 15.로 기록되어 있다."),          # 날짜·'의' 유무
    ("이 사건 물품대금은 금 48,000,000원이다.", "이 사건 물품대금은 42,000,000원이다."),                          # 금액·복합 속성
    ("갑 제6호증(검수확인서)의 작성일은 2022. 4. 1.이다.", "갑 제6호증의 작성일자는 2022. 4. 11.이다."),          # 서증·일자
    ("본건 창고의 바닥면적은 640㎡이다.", "본건 창고 바닥면적은 460㎡이다."),                                       # 수량
    ("이 사건 행사의 참가인원은 120명이다.", "이 사건 행사 참가인원은 210명이다."),                                 # 인원
])
def test_anchored_attribute_conflict_is_reported(a, b):
    [f] = _anchored(a, b)
    assert f.type == FindingType.CROSS_DOCUMENT_CONTRADICTION
    assert f.status == VerificationStatus.SUSPICIOUS
    assert f.evidence_grade == EvidenceGrade.B and f.severity == Severity.HIGH
    assert len(f.evidence) == 2


@pytest.mark.parametrize("a,b", [
    ("이 사건 기계의 설치일은 2022. 2. 15.이다.", "이 사건 기계의 설치일은 2022년 2월 15일이다."),               # 표기만 다름
    ("이 사건 물품대금은 48,000,000원이다.", "이 사건 물품대금은 4,800만 원이다."),                               # 표기만 다름
    ("위 기계의 설치일은 2022. 2. 15.이다.", "해당 기계의 설치일은 2022. 3. 15.이다."),                           # 앵커 없음(위·해당)
    ("이 사건 기계의 설치일은 2022. 2. 15.이다.", "이 사건 설비의 설치일은 2022. 3. 15.이다."),                   # 다른 대상
    ("갑 제6호증의 작성일은 2022. 4. 1.이다.", "갑 제7호증의 작성일은 2022. 4. 11.이다."),                         # 다른 서증
    ("이 사건 물품대금은 48,000,000원이다.", "이 사건 물품대금 중 8,000,000원은 지급되었다."),                    # 부분 금액
    ("이 사건 물품대금은 48,000,000원이다.", "피고는 이 사건 물품대금이 42,000,000원이라고 주장한다."),            # 상대방 주장
    ("이 사건 물품대금은 48,000,000원이다.", "이 사건 물품대금은 착오로 42,000,000원으로 적었으므로 바로잡는다."),  # 정정
    ("이 사건 청구금액은 30,000,000원이다.", "이 사건 청구금액은 36,000,000원으로 확장한다."),                    # 청구 변경
    ("이 사건 변론기일은 2025. 3. 4.이다.", "이 사건 변론기일은 2025. 4. 8.이다."),                               # 절차 일정
    ("이 사건 기계의 설치일은 2022. 2. 15.이다.", "만약 이 사건 기계의 설치일이 2022. 3. 15.이라면 하자는 없다."),  # 가정
])
def test_anchored_attribute_controls_are_not_reported(a, b):
    assert _anchored(a, b) == []


def test_documents_of_different_cases_are_not_compared():
    a, b = "이 사건 물품대금은 48,000,000원이다.", "이 사건 물품대금은 42,000,000원이다."
    assert _anchored(a, b, head_b="사건 2024나61207 대여금") == []


def test_two_values_in_one_document_are_not_compared():
    a = "이 사건 기계의 설치일은 2022. 2. 15.이다. 다른 장부에는 이 사건 기계의 설치일은 2022. 3. 15.이다."
    assert _anchored(a, "이 사건 기계의 설치일은 2022. 3. 15.이다.") == []
