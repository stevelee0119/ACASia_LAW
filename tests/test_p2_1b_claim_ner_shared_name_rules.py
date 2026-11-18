"""P2-1② 주장 엔진 NER이 개인정보 엔진의 이름·법인 공용 규칙을 쓰는지 본다.

설계 메모: docs/handoff/requests/P2_1_claim_ner_shared_name_rules_design.md

#329는 `MILITARY_NOUNS`만 공유해 일부 오탐만 막았다. 이 시험은 남은 세 규칙
(`LEGAL_MILITARY_STOPWORDS`·`COMPANY_STOPWORDS`·`is_valid_korean_name_structure`)이
주장 엔진에도 적용되는지 확인한다.

모든 문장·성명·법인명은 합성 값이다(평가 세트·사건 자료에서 가져오지 않았다).
"""
from __future__ import annotations

import pytest

from packages.claim_engine.extractor import extract_entities, is_person_name
from packages.common.enums import EntityType
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.pii_engine.detector import (
    COMPANY_STOPWORDS,
    LEGAL_MILITARY_STOPWORDS,
    is_valid_korean_name_structure,
)


def _doc(*texts: str) -> NormalizedDocument:
    blocks = [Block(f"b{i}", t, 1) for i, t in enumerate(texts)]
    return NormalizedDocument("doc-ner-shared", "brief.pdf", "application/pdf", "0" * 64,
                              pages=[Page(1, blocks=blocks)])


# ---------------------------------------------------------------------------
# 양성: 당사자 표기 뒤 직책·물건·검사 명사는 사람 엔티티가 되지 않는다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sentence, token", [
    # 성씨 체계에 있는 글자로 시작해 구조 검사만으로는 걸러지지 않는 직책·물건 명사
    ("피고 사단장은 징계처분을 의결하였다.", "사단장"),
    ("원고 목적물을 인수하였다고 주장한다.", "목적물"),
    ("피고 지휘관이 발령한 처분이다.", "지휘관"),
    ("피고 심사위원회에 자료를 제출하였다.", "심사위원회"),
    # 성씨 체계에 없어 구조 검사로 걸러지는 명사
    ("증인 검사원은 입고 수량을 확인하였다.", "검사원"),
])
def test_p2_1b_role_and_object_nouns_are_not_person_entities(sentence, token):
    people = {e.name for e in extract_entities(_doc(sentence)) if e.type == EntityType.PERSON}
    assert token not in people, f"{token}이 사람 엔티티로 올라왔다"


# ---------------------------------------------------------------------------
# 양성: 계약 용어는 법인 앞 수식어로 걸러지고, 뒤의 실제 법인명이 잡힌다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sentence, modifier, company", [
    ("원고는 대금조항 주식회사 감마물산과 계약을 체결하였다.", "대금조항", "감마물산"),
    ("피고는 계약조건 주식회사 델타중공업에 통지하였다.", "계약조건", "델타중공업"),
    ("원고는 특약사항 주식회사 엡실론상사로부터 수령하였다.", "특약사항", "엡실론상사"),
])
def test_p2_1b_contract_terms_are_not_company_entities(sentence, modifier, company):
    companies = {e.name for e in extract_entities(_doc(sentence)) if e.type == EntityType.COMPANY}
    assert modifier not in companies, f"{modifier}이 법인 엔티티로 올라왔다"
    assert company in companies, f"수식어 뒤의 실제 법인명 {company}이 빠졌다"


# ---------------------------------------------------------------------------
# 대조군: 정상 성명·법인명은 계속 추출된다
# ---------------------------------------------------------------------------

def test_p2_1b_control_real_person_names_still_extracted():
    doc = _doc(
        "원고 홍길동은 소를 제기하였다.",
        "피고 남궁민수에게 송달되었다.",
        "증인 최서윤이 출석하여 진술하였다.",
        "채무자 정하람과 소외 서지후가 합의하였다.",
    )
    people = {e.name for e in extract_entities(doc) if e.type == EntityType.PERSON}
    for name in ("홍길동", "남궁민수", "최서윤", "정하람", "서지후"):
        assert name in people, f"정상 성명 {name}이 빠졌다"


def test_p2_1b_control_real_company_names_still_extracted():
    doc = _doc(
        "원고는 주식회사 한빛물류와 운송계약을 체결하였다.",
        "피고 동아산업 주식회사가 대금을 지급하였다.",
        "제타테크 주식회사는 용역을 수행하였다.",
    )
    companies = {e.name for e in extract_entities(doc) if e.type == EntityType.COMPANY}
    for name in ("한빛물류", "동아산업", "제타테크"):
        assert any(found.startswith(name) for found in companies), f"정상 법인명 {name}이 빠졌다"


# ---------------------------------------------------------------------------
# 규칙 공유 자체를 못박는다(목록이 갈라지면 실패한다)
# ---------------------------------------------------------------------------

def test_p2_1b_shared_rule_objects_are_the_pii_engine_ones():
    from packages.claim_engine.extractor import _PERSON_STOPWORDS, COMPANY_MODIFIER_STOPWORDS

    assert LEGAL_MILITARY_STOPWORDS <= _PERSON_STOPWORDS
    assert COMPANY_STOPWORDS <= COMPANY_MODIFIER_STOPWORDS


def test_p2_1b_person_predicate_defers_to_name_structure_rule():
    """개인정보 엔진이 성명 구조로 배제하는 토큰은 주장 엔진도 배제한다."""
    assert not is_valid_korean_name_structure("검사원", "", True)
    assert not is_person_name("검사원", full_token="검사원은")
    assert is_valid_korean_name_structure("최서윤", "", True)
    assert is_person_name("최서윤", full_token="최서윤이")
