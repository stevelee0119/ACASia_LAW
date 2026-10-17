"""진술서 제목 반복 머리글 제외 결함 수정 및 교차 문서 복사 탐지 일반화 시험."""
from datetime import date
from pathlib import Path
import pytest

from packages.common.enums import FindingType, VerificationStatus
from packages.common.schemas import BBox, Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import (
    _statement_start,
    cross_document_copies,
    PREAMBLE_HEADING_RE,
    _BOILERPLATE_RE,
)
from packages.document_engine.reading_text import build_reading_text
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)
from packages.pii_engine import PseudonymStore


def _make_doc(
    doc_id: str,
    blocks: list[Block],
    filename: str = "document.pdf",
) -> NormalizedDocument:
    """단일 쪽 블록 목록으로 NormalizedDocument 객체를 생성한다."""
    page = Page(1, blocks=blocks)
    return NormalizedDocument(
        document_id=doc_id,
        filename=filename,
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


# --- 1. _statement_start 단위 시험 (머리글 진술서 제목 및 표제부 제외) ---

def test_statement_start_in_running_head_with_preamble():
    """머리글에만 진술서 제목이 있고 송달장소/요청취지 표제부가 있는 경우 표제부 끝을 반환한다."""
    blocks = [
        Block("b0", "진술서", 1, block_type="running_head"),
        Block("b1", "송달장소 : 서울 서초구 서초대로 100\n요청 취지 : 사실관계를 확인합니다.\n", 1, block_type="paragraph"),
        Block("b2", "1. 당시 상황\n저는 현장에서 직접 보았습니다.", 1, block_type="paragraph"),
    ]
    doc = _make_doc("stmt1", blocks)
    text = build_reading_text(doc).text

    # build_reading_text에서는 running_head가 제외되므로 본문에는 '진술서'가 없다
    assert "진술서" not in text
    start = _statement_start(doc, text)
    assert start is not None
    assert start > 0
    # 진술 시작 지점 이후에 실제 진술 구역("1. 당시 상황")이 위치해야 한다
    assert text[start:].strip().startswith("1. 당시 상황")


def test_statement_start_in_body_text():
    """본문 문단에 진술서 제목이 직접 존재하는 경우 해당 제목 뒤 오프셋을 반환한다."""
    blocks = [
        Block("b1", "진술서\n1. 목격 내용\n현장에서 당시 상황을 정확하게 목격하였습니다.", 1, block_type="paragraph"),
    ]
    doc = _make_doc("stmt2", blocks)
    text = build_reading_text(doc).text
    start = _statement_start(doc, text)
    assert start is not None
    assert text[start:].strip().startswith("1. 목격 내용")


def test_statement_start_non_statement_returns_none():
    """진술서나 사실확인서가 아닌 일반 서면은 None을 반환한다."""
    blocks = [
        Block("b1", "준비서면\n원고 대리인은 다음과 같이 변론합니다.", 1, block_type="paragraph"),
    ]
    doc = _make_doc("prep1", blocks)
    text = build_reading_text(doc).text
    start = _statement_start(doc, text)
    assert start is None


# --- 2. 교차 서면 문장 복사(cross_document_copies) 양성 3건 ---

def test_copy_positive_case_1_running_head_and_preamble():
    """양성 1: 머리글에 진술서 제목이 있고 표제부 이후 본문 문장이 다른 서면과 동일한 경우 탐지."""
    shared_sentence = "당시 물품 보관 창고의 출입 기록은 담당 관리자의 서명 날인 후 내부 서가에 보관되었습니다."
    stmt_blocks = [
        Block("b0", "사실확인서", 1, block_type="running_head"),
        Block("b1", "송달장소 : 서울 서초구 서초동\n제출 경위 : 확인을 위해 제출합니다.\n", 1, block_type="paragraph"),
        Block("b2", f"1. 보관 사실\n{shared_sentence}\n이 점은 명백합니다.", 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "준비서면\n원고 대리인의 주장입니다.", 1, block_type="paragraph"),
        Block("ob2", f"{shared_sentence}\n따라서 피고의 주장은 이유 없습니다.", 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_pos1", stmt_blocks, "stmt_pos1.pdf")
    other_doc = _make_doc("other_pos1", other_blocks, "other_pos1.pdf")

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 1
    assert findings[0].document_id == "stmt_pos1"
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].type == FindingType.CROSS_DOC_COPY.value


def test_copy_positive_case_2_multiple_shared_sentences_aggregated():
    """양성 2: 한 진술서 내에 복사된 문장이 여러 개 있어도 해당 상대 서면에 대해 단일 Finding으로 집계."""
    copied_s1 = "첫 번째 확인 사항으로 작업 일정표는 현장 감독관의 확인을 거쳐 주간 단위로 작성되었습니다."
    copied_s2 = "두 번째 확인 사항으로 안전 점검 일지는 매일 작업 종료 직후 캐비닛에 보관되었습니다."

    stmt_blocks = [
        Block("b0", "진술서", 1, block_type="running_head"),
        Block("b1", "송달장소 : 대전 서구 둔산동\n요청 취지 : 업무 사실 확인.\n", 1, block_type="paragraph"),
        Block("b2", f"1. 일정표 작성 경위\n{copied_s1}\n이상입니다.", 1, block_type="paragraph"),
        Block("b3", f"2. 점검 일지 관리\n{copied_s2}\n틀림없습니다.", 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "답변서\n피고 대리인의 진술입니다.", 1, block_type="paragraph"),
        Block("ob2", f"{copied_s1}\n또한 {copied_s2}\n이와 같이 관리되었습니다.", 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_pos2", stmt_blocks, "stmt_pos2.pdf")
    other_doc = _make_doc("other_pos2", other_blocks, "other_pos2.pdf")

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 1
    assert "2건 있다" in findings[0].title


def test_copy_positive_case_3_body_statement_heading():
    """양성 3: 본문 문단에 확인서 제목이 있고 다른 서면과 24자 이상 복사 문장이 일치하는 경우 탐지."""
    shared_sentence = "현장 점검 당시 장비의 이상 유무를 육안으로 직접 확인하고 점검표에 기록을 남겼습니다."
    stmt_blocks = [
        Block("b1", "확인서\n[검토 결과]\n" + shared_sentence, 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "소장\n청구원인입니다.\n" + shared_sentence, 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_pos3", stmt_blocks, "stmt_pos3.pdf")
    other_doc = _make_doc("other_pos3", other_blocks, "other_pos3.pdf")

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 1
    assert findings[0].type == FindingType.CROSS_DOC_COPY.value


# --- 3. 교차 서면 문장 복사(cross_document_copies) 대조군(음성) 6건 ---

def test_copy_control_case_1_distinct_sentences():
    """대조군 1: 머리글에 진술서 제목이 있으나 다른 서면과 본문 문장이 전혀 겹치지 않는 정상 서면."""
    stmt_blocks = [
        Block("b0", "진술서", 1, block_type="running_head"),
        Block("b1", "송달장소 : 대구 중구 공평로\n요청 취지 : 사실 증언.\n", 1, block_type="paragraph"),
        Block("b2", "1. 진술 요지\n저는 해당 일자에 현장을 방문한 사실이 전혀 없으며 전해 들은 바도 없습니다.", 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "준비서면\n원고는 계약 체결 당시 상대방에게 모든 조건을 상세히 고지하였습니다.", 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_ctl1", stmt_blocks)
    other_doc = _make_doc("other_ctl1", other_blocks)

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 0


def test_copy_control_case_2_preamble_shared_only():
    """대조군 2: 서면 서두 표제부(송달장소, 제출경위 등)만 일치하고 본문 진술 내용은 완전히 다른 경우 오탐 없음."""
    common_preamble = "송달장소 : 부산 연제구 법원로 10\n제출 경위 : 본 사건에 대한 사실 확인 목적.\n"
    stmt_blocks = [
        Block("b0", "사실확인서", 1, block_type="running_head"),
        Block("b1", common_preamble, 1, block_type="paragraph"),
        Block("b2", "1. 확인 사항\n당일 회의에 참석하여 안건에 대해 찬성 의견을 표명한 바 있습니다.", 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "준비서면\n" + common_preamble, 1, block_type="paragraph"),
        Block("ob2", "피고는 원고에게 약정된 대금을 전액 변제하였으므로 청구의 기각을 구합니다.", 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_ctl2", stmt_blocks)
    other_doc = _make_doc("other_ctl2", other_blocks)

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 0


def test_copy_control_case_3_non_statements_overlap():
    """대조군 3: 준비서면과 소장 등 일반 서면끼리 문장이 동일해도 진술서가 아니면 대필 의심을 보고하지 않음."""
    shared_sentence = "원고와 피고 사이의 계약 제5조에 따른 의무 불이행이 발생하여 계약 해지를 통보하였습니다."
    doc1 = _make_doc("prep_ctl3", [Block("b1", f"준비서면\n{shared_sentence}", 1, block_type="paragraph")])
    doc2 = _make_doc("complaint_ctl3", [Block("b1", f"소장\n{shared_sentence}", 1, block_type="paragraph")])

    findings = cross_document_copies([doc1, doc2])
    assert len(findings) == 0


def test_copy_control_case_4_natural_intro_without_preamble_heading():
    """대조군 4: 송달장소 등 표제부 키워드가 없으나 사건·인적사항 서두만 같고 본문은 다른 진술서 오탐 없음."""
    common_intro = (
        "사건 : 2026가단 10001 손해배상\n"
        "진술인 : 홍길동 (1980. 1. 1.생)\n"
        "위 사건에 관하여 다음과 같이 진술합니다.\n"
    )
    stmt_blocks = [
        Block("b0", "진술서", 1, block_type="running_head"),
        Block("b1", f"{common_intro}\n당일 사건 현장에 있었으나 아무런 충돌도 목격하지 못하였습니다.", 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "답변서\n피고 대리인의 답변입니다.", 1, block_type="paragraph"),
        Block("ob2", f"{common_intro}\n피고는 원고의 청구를 전부 부인하며 청구의 기각을 구합니다.", 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_ctl4", stmt_blocks)
    other_doc = _make_doc("other_ctl4", other_blocks)

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 0


def test_copy_control_case_5_short_common_cliche_signature():
    """대조군 5 (24~29자 상투구): 서명·날인 확인 상투 문구가 서면 간 중복되어도 실질 본문이 다르면 오탐 없음."""
    cliche_sentence = "위 진술 내용은 사실과 다름없음을 확인하며 서명 날인합니다."  # 27자
    stmt_blocks = [
        Block("b0", "진술서", 1, block_type="running_head"),
        Block("b1", "1. 진술 요지\n사무실 내 집기 비품의 파손 경위를 직접 보지 못하였습니다.\n" + cliche_sentence, 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "준비서면\n원고 대리인은 피고의 주장을 일체 부인합니다.\n" + cliche_sentence, 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_ctl5", stmt_blocks)
    other_doc = _make_doc("other_ctl5", other_blocks)

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 0


def test_copy_control_case_6_short_common_cliche_submission():
    """대조군 6 (24~29자 상투구): 제출 목적 증명 상투 문구가 서면 간 중복되어도 실질 본문이 다르면 오탐 없음."""
    cliche_sentence = "위 사실관계를 증명하기 위하여 본 확인서를 작성하여 제출합니다."  # 28자
    stmt_blocks = [
        Block("b0", "사실확인서", 1, block_type="running_head"),
        Block("b1", "1. 당시 정황\n회의실에서 양측 대표자가 원만히 합의에 도달하였습니다.\n" + cliche_sentence, 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "답변서\n피고는 소장의 청구원인을 모두 다투는 바입니다.\n" + cliche_sentence, 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("stmt_ctl6", stmt_blocks)
    other_doc = _make_doc("other_ctl6", other_blocks)

    findings = cross_document_copies([stmt_doc, other_doc])
    assert len(findings) == 0


# --- 4. VerificationPipeline 실제 진입점 실행 시험 1건 (공통 점검표 1항) ---

def test_verification_pipeline_actual_entrypoint_cross_doc_copy(tmp_path, monkeypatch):
    """공통 점검표 1항: VerificationPipeline 실제 진입점(.run)을 실행하여 cross_document_copies가 동작하는지 검증."""
    shared_sentence = "확인인이 현장에서 직접 확인한 재고 실사표는 총 세 부가 인쇄되어 날인되었습니다."

    stmt_blocks = [
        Block("b0", "진술서", 1, block_type="running_head"),
        Block("b1", "송달장소 : 광주 동구 준법로\n요청 취지 : 현장 실사 확인.\n", 1, block_type="paragraph"),
        Block("b2", f"1. 실사 경위\n{shared_sentence}\n이상 틀림없습니다.", 1, block_type="paragraph"),
    ]
    other_blocks = [
        Block("ob1", "준비서면\n원고 대리인의 변론 요지서입니다.", 1, block_type="paragraph"),
        Block("ob2", f"{shared_sentence}\n이 점을 살펴 주시기 바랍니다.", 1, block_type="paragraph"),
    ]
    stmt_doc = _make_doc("doc_stmt", stmt_blocks, "stmt.pdf")
    other_doc = _make_doc("doc_other", other_blocks, "other.pdf")

    # 파이프라인 내부 파서 및 가명화 저장소 모킹
    docs_map = {"doc_stmt": stmt_doc, "doc_other": other_doc}
    from packages.verification_engine import pipeline as pipeline_module
    monkeypatch.setattr(pipeline_module, "parse_document", lambda path, **kw: docs_map.get(kw.get("document_id"), stmt_doc))
    monkeypatch.setattr(pipeline_module, "PseudonymStore", lambda project_id, **kw: PseudonymStore(project_id, root=tmp_path))

    pipeline = VerificationPipeline()
    result = pipeline.run(
        "run-copy-test",
        ProjectContext("proj-copy-test"),
        [
            DocumentInput("doc_stmt", "stmt.pdf", "stmt.pdf"),
            DocumentInput("doc_other", "other.pdf", "other.pdf"),
        ],
    )

    # 파이프라인 결과의 project_findings에서 CROSS_DOC_COPY 발견 사항이 포함되어 있는지 검증
    copy_findings = [f for f in result.project_findings if f.type == FindingType.CROSS_DOC_COPY.value]
    assert len(copy_findings) == 1
    assert copy_findings[0].document_id == "doc_stmt"


# --- 5. 공통 점검표 2항: 정규식 성능 1배/4배 최솟값 비 < 8 및 4배 < 1초 시험 ---

def test_regex_performance_ratio_under_8():
    """공통 점검표 2항: 새 정규식의 1배/4배 길이 최솟값 비가 8 미만이고 4배 수행시간이 1초 미만인지 검증."""
    import timeit
    text_1x = (
        "송달장소 : 서울 서초구 서초대로 100\n"
        "요청 취지 : 사실관계를 확인합니다.\n"
        "제출 경위 : 확인을 위해 제출합니다.\n"
        "1. 당시 상황\n"
        "위 사실관계를 증명하기 위하여 본 확인서를 작성하여 제출합니다.\n"
        "본 진술 내용은 본인의 자유로운 의사에 따라 작성되었으며 사실과 다름없음을 확인하고 서명 날인합니다.\n"
    ) * 10
    text_4x = text_1x * 4

    for name, regex in [("PREAMBLE_HEADING_RE", PREAMBLE_HEADING_RE), ("_BOILERPLATE_RE", _BOILERPLATE_RE)]:
        t1 = min(timeit.repeat(lambda: list(regex.finditer(text_1x)), number=100, repeat=3))
        t4 = min(timeit.repeat(lambda: list(regex.finditer(text_4x)), number=100, repeat=3))
        ratio = t4 / t1 if t1 > 0 else 0
        assert ratio < 8.0, f"{name} 비정상 성능 비: {ratio}"
        assert t4 < 1.0, f"{name} 4배 최솟값 1초 초과: {t4}s"

