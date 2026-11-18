"""TK-76 E 후속: 파생 문서명 가드를 기존 서증 종류 판별에도 적용.

설계 메모: docs/handoff/requests/TK76_E2_derived_title_guard_existing_kinds_design.md

#330은 새 `EVIDENCE_ORIGINAL`에만 가드를 넣었고, 기존 `FACT_CONFIRMATION`·`EVIDENCE_EXPLANATION`
판별은 괄호·대괄호 안의 파생 용어를 통과시켰다. 이 시험은 세 분기가 같은 가드를 쓰는지,
정상 양성이 유지되는지, 소송서면·진술서 판별은 그대로인지 본다.

모든 문서·문장·표제는 합성 값이다.
"""
from __future__ import annotations

import pytest

from packages.claim_engine.evidence_consistency import (
    DOC_KIND_EVIDENCE_EXPLANATION,
    DOC_KIND_EVIDENCE_ORIGINAL,
    DOC_KIND_FACT_CONFIRMATION,
    DOC_KIND_OTHER,
    DOC_KIND_PLEADING,
    DOC_KIND_STATEMENT,
    _document_title_kind,
    cross_document_copies,
)
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


_BODY = (
    "점검 당시 승강기 제어반 내부의 배선 피복이 벗겨져 있었고 접지선이 단자에서 분리되어 있었다. "
    "관리주체는 분기 점검 기록을 남기지 않았으며 경보장치는 작동하지 않는 상태로 방치되어 있었다. "
    "현장에서 확인한 결과 비상통화장치의 전원이 차단되어 있었고 수신실 호출도 연결되지 않았다."
)


def _make_doc(doc_id: str, text: str, filename: str = "doc.pdf") -> NormalizedDocument:
    block = Block(block_id="b1", text=text, page=1, visible=True,
                  source_layer="visible_text", block_type="paragraph")
    page = Page(page_number=1, blocks=[block], width=595.0, height=842.0)
    return NormalizedDocument(document_id=doc_id, filename=filename,
                              mime_type="application/pdf", sha256="0" * 64, pages=[page])


def _copies(docs):
    return [f for f in cross_document_copies(docs) if f.type == FindingType.CROSS_DOC_COPY]


# ---------------------------------------------------------------------------
# 사실경위서 경로: 괄호·대괄호 안 파생 용어 배제
# ---------------------------------------------------------------------------

_FACT_DERIVED = [
    ("사실경위서(사본)", "괄호"),
    ("사실경위서[송부]", "대괄호"),
    ("사실경위서(제출)", "괄호"),
    ("사고경위서(접수)", "괄호"),
    ("경위서(발급)", "괄호"),
    ("사건경위서(회신)", "괄호"),
    ("사실경위서 - 사본", "구분자"),
    ("사실경위서 사본", "공백 접미"),
    ("사본사실경위서", "붙여쓴 수식어"),
]


@pytest.mark.parametrize("title, axis", _FACT_DERIVED)
def test_tk76e2_fact_derived_titles_are_not_fact_confirmation(title, axis):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n\n1. 발생 경위\n{_BODY}"))
    assert kind != DOC_KIND_FACT_CONFIRMATION, f"{axis}: {title}이 사실경위서로 분류됐다"


@pytest.mark.parametrize("title, axis", _FACT_DERIVED)
def test_tk76e2_fact_derived_titles_produce_no_copy_finding(title, axis):
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _BODY, "brief.pdf")
    derived = _make_doc("f1", f"{title}\n\n1. 발생 경위\n{_BODY}", "derived.pdf")
    assert _copies([pleading, derived]) == [], f"{axis}: {title}에서 경고가 생겼다"


@pytest.mark.parametrize("title", [
    "사실경위서", "사 실 경 위 서", "사고경위서", "사건경위서", "경위서", "사실경위서(원본)",
])
def test_tk76e2_fact_normal_titles_still_classified(title):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n\n1. 발생 경위\n{_BODY}"))
    assert kind == DOC_KIND_FACT_CONFIRMATION, f"정상 양성 {title}이 배제됐다"


@pytest.mark.parametrize("title", ["사실경위서", "사고경위서", "사실경위서(원본)"])
def test_tk76e2_fact_normal_titles_still_produce_copy_finding(title):
    """기존 5순위 사실경위서 통복제 경로는 그대로 동작한다."""
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _BODY, "brief.pdf")
    fact = _make_doc("f1", f"{title}\n\n1. 발생 경위\n{_BODY}", "fact.pdf")
    findings = _copies([pleading, fact])
    assert findings, f"정상 양성 {title}의 통복제가 검출되지 않았다"
    assert findings[0].confidence_features["rule_id"] == "EVI.COPY_FACT_CONFIRMATION"


# ---------------------------------------------------------------------------
# 증거설명서 경로(구현 중 함께 확인한 같은 결함)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("title", ["증거설명서(사본)", "증거설명서[송부]", "증거설명서(접수)"])
def test_tk76e2_evidence_explanation_derived_titles_excluded(title):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n\n1. 호증 설명\n{_BODY}"))
    assert kind != DOC_KIND_EVIDENCE_EXPLANATION, f"{title}이 증거설명서로 분류됐다"


@pytest.mark.parametrize("title", ["증거설명서", "증 거 설 명 서"])
def test_tk76e2_evidence_explanation_normal_titles_still_classified(title):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n\n1. 호증 설명\n{_BODY}"))
    assert kind == DOC_KIND_EVIDENCE_EXPLANATION


# ---------------------------------------------------------------------------
# 범위 밖 경로는 그대로다
# ---------------------------------------------------------------------------

def test_tk76e2_pleading_with_derived_title_stays_pleading():
    """'소장(사본)'도 내용은 그 소송서면이므로 owner 자격을 유지한다(가드 적용 안 함)."""
    kind, _ = _document_title_kind(_make_doc("d", "소 장(사본)\n\n청구취지\n" + _BODY))
    assert kind == DOC_KIND_PLEADING


def test_tk76e2_statement_path_unchanged():
    """진술서 1순위 판별은 건드리지 않는다."""
    kind, _ = _document_title_kind(
        _make_doc("d", "진 술 서\n\n성명: 홍길동\n생년월일: 1980. 1. 1.\n\n" + _BODY))
    assert kind == DOC_KIND_STATEMENT


def test_tk76e2_evidence_original_guard_still_holds():
    """#330의 서술형 원본 서증 가드가 유지된다(같은 정규식을 공유한다)."""
    assert _document_title_kind(
        _make_doc("d", f"진단서(사본)\n\n1. 확인 내용\n{_BODY}"))[0] == DOC_KIND_OTHER
    assert _document_title_kind(
        _make_doc("d", f"상해진단서\n\n1. 확인 내용\n{_BODY}"))[0] == DOC_KIND_EVIDENCE_ORIGINAL
