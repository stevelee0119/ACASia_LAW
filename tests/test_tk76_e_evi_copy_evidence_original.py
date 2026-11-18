"""TK-76 E항: EVI-COPY 원문 범위를 서술형 원본 서증으로 확장.

설계 메모: docs/handoff/requests/TK76_E_evi_copy_evidence_original_scope_design.md

과거 시안은 원문 범위를 '사실경위서가 아닌 문서'(음성 조건)로 넓혀 은퇴 1세트 53.3→49.3·오탐 0→2를
만들었다. 이번 설계는 원문이 서증 원본임을 표제로 적극 판별해야만 범위에 들어간다. 그래서
`PLEADING ↔ PLEADING`·`PLEADING ↔ OTHER`는 구조적으로 결과를 낼 수 없다.

모든 문서·문장·표제는 합성 값이다(평가 세트·은퇴 세트·사건 자료에서 가져오지 않았다).
"""
from __future__ import annotations

import pytest

from packages.claim_engine.evidence_consistency import (
    DOC_KIND_EVIDENCE_ORIGINAL,
    DOC_KIND_FACT_CONFIRMATION,
    DOC_KIND_OTHER,
    DOC_KIND_PLEADING,
    _document_title_kind,
    cross_document_copies,
)
from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page


def _make_doc(doc_id: str, text: str, filename: str = "doc.pdf") -> NormalizedDocument:
    block = Block(block_id="b1", text=text, page=1, visible=True,
                  source_layer="visible_text", block_type="paragraph")
    page = Page(page_number=1, blocks=[block], width=595.0, height=842.0)
    return NormalizedDocument(document_id=doc_id, filename=filename,
                              mime_type="application/pdf", sha256="0" * 64, pages=[page])


# 통복제될 본문. 소송서면과 원본 서증이 같은 문장을 갖는다(어미·조사까지 동일).
_COPIED_BODY = (
    "점검 당시 승강기 제어반 내부의 배선 피복이 벗겨져 있었고 접지선이 단자에서 분리되어 있었다. "
    "관리주체는 분기 점검 기록을 남기지 않았으며 경보장치는 작동하지 않는 상태로 방치되어 있었다. "
    "현장에서 확인한 결과 비상통화장치의 전원이 차단되어 있었고 수신실 호출도 연결되지 않았다."
)


def _copies(docs):
    return [f for f in cross_document_copies(docs) if f.type == FindingType.CROSS_DOC_COPY]


# ---------------------------------------------------------------------------
# 표제 판별: 새 종류가 생기고 기존 판정은 그대로다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("title", [
    "점 검 보 고 서",
    "사고보고서",
    "감 정 서",
    "감정평가서",
    "소 견 서",
    "상해진단서",
    "진료기록부",
    "시 말 서",
])
def test_tk76e_narrative_evidence_titles_are_classified_as_evidence_original(title):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n1. 확인 내용\n{_COPIED_BODY}"))
    assert kind == DOC_KIND_EVIDENCE_ORIGINAL


@pytest.mark.parametrize("title", [
    # 정형 서증: 문구를 서면에 옮기는 것이 정상 인용이므로 원문 범위에 들어가면 안 된다
    "계 약 서", "합의서", "각 서", "영 수 증", "거래명세서", "재직증명서",
    # 파생 문서명
    "점검보고서 사본 송부", "감정서 제출 안내",
    # 소송서면(의견서)과 원본 서증(소견서)을 섞지 않는다
    "의 견 서",
])
def test_tk76e_control_titles_are_not_evidence_original(title):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n1. 내용\n{_COPIED_BODY}"))
    assert kind != DOC_KIND_EVIDENCE_ORIGINAL


def test_tk76e_fact_confirmation_classification_unchanged():
    """사실경위서로 잡히던 문서의 판정은 바뀌지 않는다(검사 순서로 보장)."""
    kind, _ = _document_title_kind(_make_doc("d", "사 실 경 위 서\n1. 발생 일시 및 장소\n" + _COPIED_BODY))
    assert kind == DOC_KIND_FACT_CONFIRMATION


# ---------------------------------------------------------------------------
# 양성: 소송서면이 서술형 원본 서증 본문을 통복제하면 C등급 결함
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("evidence_title, evidence_file", [
    ("점 검 보 고 서", "report.pdf"),
    ("감 정 서", "appraisal.pdf"),
    ("상해진단서", "diagnosis.pdf"),
])
def test_tk76e_pleading_copying_evidence_original_is_flagged(evidence_title, evidence_file):
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    evidence = _make_doc("e1", f"{evidence_title}\n\n1. 확인 내용\n{_COPIED_BODY}", evidence_file)

    findings = _copies([pleading, evidence])
    assert findings, f"{evidence_title} 통복제가 검출되지 않았다"
    hit = findings[0]
    assert hit.evidence_grade == EvidenceGrade.C
    assert hit.status == VerificationStatus.SUSPICIOUS
    assert hit.confidence_features["copy_category"] == "EVIDENCE_ORIGINAL_REPLICATION"
    assert hit.confidence_features["rule_id"] == "EVI.COPY_EVIDENCE_ORIGINAL"
    assert hit.confidence_features["human_review"] is True
    assert hit.confidence_features["other_document_id"] == "e1"


def test_tk76e_evidence_explanation_copying_evidence_original_is_flagged():
    explanation = _make_doc("x1", "증 거 설 명 서\n\n위 주장과 관련하여 다음과 같다.\n" + _COPIED_BODY,
                            "explanation.pdf")
    evidence = _make_doc("e1", "사고보고서\n\n1. 확인 내용\n" + _COPIED_BODY, "report.pdf")

    findings = _copies([explanation, evidence])
    assert findings
    assert findings[0].confidence_features["copy_category"] == "EVIDENCE_ORIGINAL_REPLICATION"


def test_tk76e_fact_confirmation_path_keeps_its_existing_values():
    """기존 사실경위서 경로의 분류 값·규칙 이름은 바뀌지 않는다."""
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    fact = _make_doc("f1", "사 실 경 위 서\n\n1. 발생 경위\n" + _COPIED_BODY, "fact.pdf")

    findings = _copies([pleading, fact])
    assert findings
    assert findings[0].confidence_features["copy_category"] == "FACT_CONFIRMATION_REPLICATION"
    assert findings[0].confidence_features["rule_id"] == "EVI.COPY_FACT_CONFIRMATION"


# ---------------------------------------------------------------------------
# 대조군: 과거 시안이 만든 오탐 꼴은 구조적으로 나오지 않는다
# ---------------------------------------------------------------------------

def test_tk76e_control_pleading_to_pleading_restatement_is_not_flagged():
    """소송서면 사이의 정상적인 변론 요지 재진술(7순위 보호)은 그대로 보호된다."""
    first = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief1.pdf")
    second = _make_doc("p2", "답 변 서\n\n1. 답변의 요지\n" + _COPIED_BODY, "answer.pdf")
    assert _copies([first, second]) == []


def test_tk76e_control_unclassified_source_is_not_flagged():
    """표제를 판별하지 못한 문서(OTHER)는 원문 자리에 들어오지 않는다(과거 시안의 오탐 원인)."""
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    other = _make_doc("o1", "2026. 3. 4. 회의 메모\n\n" + _COPIED_BODY, "memo.pdf")

    kind, _ = _document_title_kind(other)
    assert kind == DOC_KIND_OTHER
    assert _copies([pleading, other]) == []


@pytest.mark.parametrize("title", ["계 약 서", "영 수 증", "거래명세서"])
def test_tk76e_control_formal_evidence_quotation_is_not_flagged(title):
    """처분문서·정형 서증의 문구를 서면에 옮기는 것은 정상 인용이다."""
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    formal = _make_doc("c1", f"{title}\n\n제1조 목적\n{_COPIED_BODY}", "formal.pdf")
    assert _copies([pleading, formal]) == []


def test_tk76e_control_derived_document_name_is_not_flagged():
    """'… 사본 송부'처럼 원본 서증 자체가 아닌 파생 문서명은 원문 범위 밖이다."""
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    derived = _make_doc("d1", "점검보고서 사본 송부\n\n아래와 같이 송부합니다.\n" + _COPIED_BODY, "sent.pdf")
    assert _copies([pleading, derived]) == []


@pytest.mark.parametrize("line", [
    "1. 점검보고서",                 # 목록 줄
    "갑 제3호증 감정서",             # 호증 목록 줄
    "첨부서류: 진단서",              # 첨부 목록 줄
    "사법경찰관 경위 김도윤",        # 직위 낱말
])
def test_tk76e_control_list_lines_and_job_titles_are_not_evidence_original(line):
    kind, _ = _document_title_kind(_make_doc("d", f"{line}\n\n{_COPIED_BODY}"))
    assert kind != DOC_KIND_EVIDENCE_ORIGINAL


def test_tk76e_control_no_evidence_original_means_no_work():
    """원본 서증·진술서가 없으면 기존처럼 즉시 종료한다(소송서면만 있는 경우)."""
    first = _make_doc("p1", "준 비 서 면\n\n1. 주장\n" + _COPIED_BODY, "brief1.pdf")
    second = _make_doc("p2", "준 비 서 면\n\n2. 주장\n" + _COPIED_BODY, "brief2.pdf")
    assert _document_title_kind(first)[0] == DOC_KIND_PLEADING
    assert _copies([first, second]) == []


# ---------------------------------------------------------------------------
# 보완(평가 측 1차 판정): 파생 문서명은 축을 가리지 않고 모두 배제된다
# 공백·붙여쓰기·괄호·대괄호·구분자 네 축을 양성/음성으로 함께 본다.
# ---------------------------------------------------------------------------

_DERIVED_TITLE_AXES = [
    # (표제, 축)
    ("사본진단서", "붙여쓴 수식어"),
    ("송부진단서", "붙여쓴 수식어"),
    ("사 본 진단서", "띄어쓴 수식어"),
    ("진단서 사본", "공백 접미"),
    ("점검보고서 사본 송부", "공백 접미 2낱말"),
    ("진단서(사본)", "괄호"),
    ("진단서(송부)", "괄호"),
    ("진단서(발급)", "괄호"),
    ("감정서[회신]", "대괄호"),
    ("진단서[송부]", "대괄호"),
    ("진단서 - 사본", "구분자"),
    ("감정서 / 제출", "구분자"),
    ("소견서: 안내", "구분자"),
    ("사고보고서(접수)", "괄호"),
    ("시말서(요청)", "괄호"),
]


@pytest.mark.parametrize("title, axis", _DERIVED_TITLE_AXES)
def test_tk76e_derived_titles_are_excluded_on_every_axis(title, axis):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n\n1. 내용\n{_COPIED_BODY}"))
    assert kind != DOC_KIND_EVIDENCE_ORIGINAL, f"{axis}: {title}이 원본 서증으로 분류됐다"


@pytest.mark.parametrize("title, axis", _DERIVED_TITLE_AXES)
def test_tk76e_derived_titles_produce_no_copy_finding(title, axis):
    """분류만이 아니라 실제 cross_document_copies 결과도 0건이어야 한다."""
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    derived = _make_doc("d1", f"{title}\n\n1. 내용\n{_COPIED_BODY}", "derived.pdf")
    assert _copies([pleading, derived]) == [], f"{axis}: {title}에서 경고가 생겼다"


_NORMAL_TITLE_AXES = [
    ("상해진단서", "붙여쓴 수식어"),
    ("후유장해진단서", "붙여쓴 수식어"),
    ("상해 진단서", "띄어쓴 수식어"),
    ("진단서(원본)", "괄호"),
    ("감정서(부동산)", "괄호"),
    ("사고보고서", "붙여쓴 수식어"),
    ("점 검 보 고 서", "자간"),
    ("시 말 서", "자간"),
]


@pytest.mark.parametrize("title, axis", _NORMAL_TITLE_AXES)
def test_tk76e_normal_titles_survive_the_derived_filter(title, axis):
    kind, _ = _document_title_kind(_make_doc("d", f"{title}\n\n1. 확인 내용\n{_COPIED_BODY}"))
    assert kind == DOC_KIND_EVIDENCE_ORIGINAL, f"{axis}: 정상 양성 {title}이 배제됐다"


@pytest.mark.parametrize("title", ["상해진단서", "진단서(원본)", "사고보고서"])
def test_tk76e_normal_titles_still_produce_copy_finding(title):
    pleading = _make_doc("p1", "준 비 서 면\n\n1. 주장의 요지\n" + _COPIED_BODY, "brief.pdf")
    evidence = _make_doc("e1", f"{title}\n\n1. 확인 내용\n{_COPIED_BODY}", "ev.pdf")
    findings = _copies([pleading, evidence])
    assert findings, f"정상 양성 {title}의 통복제가 검출되지 않았다"
    assert findings[0].confidence_features["rule_id"] == "EVI.COPY_EVIDENCE_ORIGINAL"
