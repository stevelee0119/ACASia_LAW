"""B-2 EVI-COPY 비진술서(32건) 원본 서증 통복제 및 구조적 분별 단위 시험.

승인된 설계 메모 docs/handoff/requests/84_evi_copy_non_statement_author_design.md 기준:
1. 조건 3: 표제 판별 단위 시험 (_document_title_kind)
   - 사실경위서(FACT_CONFIRMATION), 진술서(STATEMENT), 증거설명서(EVIDENCE_EXPLANATION), 소송서면(PLEADING)
2. 조건 1: 민사소송규칙 제106조에 따른 증거설명서 통복제 예외 처리
   - 해당 호증 설명(입증취지) 항목 밖 통복제는 C등급 결함 검출, 항목 내 정상 기재는 제외
3. 조건 2: 5순위 비진술서(소송서면/증거설명서)의 사실경위서 통복제 C등급(SUSPICIOUS) 고정 검증
4. 합성 양성 4건 및 대조군 6건 완비.
"""
import pytest

from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import (
    DOC_KIND_EVIDENCE_EXPLANATION,
    DOC_KIND_FACT_CONFIRMATION,
    DOC_KIND_PLEADING,
    DOC_KIND_STATEMENT,
    _document_title_kind,
    cross_document_copies,
)


def _make_doc(doc_id: str, text: str, filename: str = "doc.pdf") -> NormalizedDocument:
    """합성 테스트용 NormalizedDocument 생성 헬퍼."""
    block = Block(
        block_id="b1",
        text=text,
        page=1,
        visible=True,
        source_layer="visible_text",
        block_type="paragraph",
    )
    page = Page(page_number=1, blocks=[block], width=595.0, height=842.0)
    return NormalizedDocument(
        document_id=doc_id,
        filename=filename,
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


# --- 1. 조건 3: 표제 판별 단위 시험 (_document_title_kind) ---

def test_document_title_kind_classification():
    """조건 3: 표제부 패턴을 통한 문서 종류 분류 정확성 검증."""
    # 1. 사실경위서
    doc_fact = _make_doc("d1", "사 실 경 위 서\n1. 발생 일시 및 장소...")
    kind, _ = _document_title_kind(doc_fact)
    assert kind == DOC_KIND_FACT_CONFIRMATION

    # 2. 진술서 / 사실확인서
    doc_stmt = _make_doc("d2", "진 술 서\n성명: 홍길동\n주민등록번호: ...")
    kind, _ = _document_title_kind(doc_stmt)
    assert kind == DOC_KIND_STATEMENT

    # 3. 증거설명서 (민사소송규칙 제106조 대상)
    doc_expl = _make_doc("d3", "증 거 설 명 서\n사건 2023가단12345\n원고 홍길동...")
    kind, _ = _document_title_kind(doc_expl)
    assert kind == DOC_KIND_EVIDENCE_EXPLANATION

    # 4. 소송 대리 서면 (준비서면, 소장, 답변서, 의견서)
    doc_prep = _make_doc("d4", "준 비 서 면\n사건 2023가단12345...")
    kind, _ = _document_title_kind(doc_prep)
    assert kind == DOC_KIND_PLEADING

    doc_complaint = _make_doc("d5", "소  장\n원고 홍길동\n피고 김철수...")
    kind, _ = _document_title_kind(doc_complaint)
    assert kind == DOC_KIND_PLEADING

    doc_opinion = _make_doc("d6", "의 견 서\n원고 소송대리인은 다음과 같이 의견을 개진합니다...")
    kind, _ = _document_title_kind(doc_opinion)
    assert kind == DOC_KIND_PLEADING


# --- 2. 합성 양성 예시 3건 시험 ---

def test_positive_1_fact_confirmation_copied_into_pleading_grade_c():
    """양성 1 (5순위, train 32건 대응): 사실경위서 원본 문단이 준비서면에 통복제된 경우 (조건 2 C등급 검증)."""
    shared_paragraph_1 = (
        "2023년 5월 10일 피고 회사 공장에서 기계 정비 작업을 수행하던 도중 안전장치가 제대로 작동하지 않아 "
        "작업자의 오른손이 롤러에 끼이는 중대한 사고가 발생하였습니다."
    )
    shared_paragraph_2 = (
        "사고 직후 공장 관리 책임자는 119에 즉시 신고하지 않고 자체적으로 수습하려 하였으며 "
        "이로 인해 응급 치료를 받을 수 있는 중요한 골든타임을 허비하게 되었습니다."
    )

    doc_fact = _make_doc(
        "d_fact",
        f"사 실 경 위 서\n작성인: 박○○\n\n{shared_paragraph_1}\n\n{shared_paragraph_2}",
        "사실경위서.pdf",
    )
    doc_prep = _make_doc(
        "d_prep",
        f"준 비 서 면\n원고 소송대리인 변호사\n\n3. 사고 발생 경위\n{shared_paragraph_1}\n\n{shared_paragraph_2}",
        "준비서면.pdf",
    )

    findings = cross_document_copies([doc_fact, doc_prep])

    # 준비서면(d_prep)을 owner로 하는 복사 Finding 검출
    assert len(findings) == 1
    f = findings[0]
    assert f.document_id == "d_prep"
    assert f.type == FindingType.CROSS_DOC_COPY
    assert f.evidence_grade == EvidenceGrade.C  # 조건 2: 5순위 서증 통복제 C등급 고정
    assert f.status == VerificationStatus.SUSPICIOUS
    assert "증거자료(사실경위서.pdf)의 본문과 같은 문장이" in f.title
    assert f.confidence_features.get("copy_category") == "FACT_CONFIRMATION_REPLICATION"


def test_positive_2_independent_third_party_statement_copied_grade_b():
    """양성 2 (4순위): 독립 제3자 확인서 문장이 소장 본문과 일치 시 대필 의심 (EvidenceGrade.B 검증)."""
    shared_text = (
        "당시 저는 현장에서 약 3미터 떨어진 곳에서 자재를 운반하고 있었는데 굉음과 함께 비명 소리가 들려 "
        "즉시 현장으로 달려가 상황을 목격하게 되었습니다."
    )

    doc_stmt = _make_doc(
        "d_stmt",
        f"진 술 서\n성명: 목격자 최○○\n\n{shared_text}",
        "진술서_목격자.pdf",
    )
    doc_complaint = _make_doc(
        "d_comp",
        f"소  장\n원고 홍길동\n\n{shared_text}",
        "소장.pdf",
    )

    findings = cross_document_copies([doc_stmt, doc_complaint])

    # 진술서(d_stmt)가 owner인 B등급 Finding 검출 (4순위)
    assert len(findings) == 1
    f = findings[0]
    assert f.document_id == "d_stmt"
    assert f.type == FindingType.CROSS_DOC_COPY
    assert f.evidence_grade == EvidenceGrade.B  # 4순위 진술서 대필 의심은 B등급
    assert f.status == VerificationStatus.SUSPICIOUS
    assert "진술 문서에 다른 서면(소장.pdf)과 같은 문장이" in f.title


def test_positive_3_fact_confirmation_copied_into_complaint_grade_c():
    """양성 3: 사실경위서 원본 문단이 소장에 그대로 복제된 경우 (C등급 검증)."""
    shared_body = (
        "해당 공사 현장은 설계도면과 다르게 기초 콘크리트 타설 두께가 기준치에 현저히 미달하였으며 "
        "철근 배근 간격도 불규칙하여 구조적 결함이 사전에 내재되어 있었습니다."
    )

    doc_fact = _make_doc(
        "d_fact2",
        f"사건경위서\n현장소장\n\n{shared_body}",
        "사건경위서.pdf",
    )
    doc_comp = _make_doc(
        "d_comp2",
        f"소  장\n원고 소송대리인\n\n{shared_body}",
        "소장.pdf",
    )

    findings = cross_document_copies([doc_fact, doc_comp])

    assert len(findings) == 1
    f = findings[0]
    assert f.document_id == "d_comp2"
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.SUSPICIOUS


def test_positive_4_evidence_explanation_outside_exhibit_entry_grade_c():
    """양성 4 (조건 1 준수): 증거설명서 내 해당 호증 설명 항목 밖(별도 항목)에 사실경위서가 통복제된 경우 (C등급 검출)."""
    copied_paragraph = (
        "2023년 5월 10일 피고 회사 공장에서 기계 정비 작업을 수행하던 도중 안전장치가 제대로 작동하지 않아 "
        "작업자의 오른손이 롤러에 끼이는 중대한 사고가 발생하였습니다."
    )

    doc_fact = _make_doc(
        "d_fact_out",
        f"사 실 경 위 서\n작성인: 박○○\n\n{copied_paragraph}",
        "사실경위서.pdf",
    )
    # 증거설명서 표제가 있으나 입증취지 항목 밖(별도 항목)에 복제된 형태
    doc_expl = _make_doc(
        "d_expl_out",
        f"증 거 설 명 서\n사건 2023가단12345\n\n[별도 참고사항]\n3. 현장 설명\n{copied_paragraph}",
        "증거설명서.pdf",
    )

    findings = cross_document_copies([doc_fact, doc_expl])
    assert len(findings) == 1
    f = findings[0]
    assert f.document_id == "d_expl_out"
    assert f.evidence_grade == EvidenceGrade.C  # 5순위 비진술서 통복제 C등급
    assert f.status == VerificationStatus.SUSPICIOUS
    assert f.confidence_features.get("copy_category") == "FACT_CONFIRMATION_REPLICATION"


# --- 3. 합성 대조군 5건 시험 ---

def test_negative_1_pleading_restatement_skip():
    """대조 1 (7순위): 동일 진영 소송서면 간 변론 요지 정상 재진술 (소장 ↔ 준비서면, 오탐 0)."""
    shared_argument = (
        "피고는 민법 제750조에 따른 불법행위 책임이 명백하므로 원고가 입은 재산상 손해 및 "
        "위자료를 포함한 손해배상금을 전액 지급할 의무가 있습니다."
    )

    doc_comp = _make_doc("d_c", f"소  장\n원고\n\n{shared_argument}", "소장.pdf")
    doc_prep = _make_doc("d_p", f"준 비 서 면\n원고\n\n{shared_argument}", "준비서면.pdf")

    findings = cross_document_copies([doc_comp, doc_prep])
    # 소송서면 간 재진술은 정상 변론 행위이므로 결함 판정 0건
    assert len(findings) == 0


def test_negative_2_evidence_explanation_rule106_exception():
    """대조 2 (조건 1 검증): 민사소송규칙 제106조에 따른 증거설명서 서증 요약/설명 예외 (오탐 0)."""
    shared_fact_text = (
        "2023년 5월 10일 피고 회사 공장에서 기계 정비 작업을 수행하던 도중 안전장치가 제대로 작동하지 않아 "
        "작업자의 오른손이 롤러에 끼이는 중대한 사고가 발생하였습니다."
    )

    doc_fact = _make_doc(
        "d_fact_106",
        f"사 실 경 위 서\n작성인: 박○○\n\n{shared_fact_text}",
        "사실경위서.pdf",
    )
    doc_expl = _make_doc(
        "d_expl_106",
        f"증 거 설 명 서\n원고 소송대리인\n\n갑 제1호증 사실경위서: {shared_fact_text}",
        "증거설명서.pdf",
    )

    findings = cross_document_copies([doc_fact, doc_expl])
    # 증거설명서는 민사소송규칙 제106조에 따른 서증 기재 요약이 법정 목적이므로 오탐 제외(SKIP)
    assert len(findings) == 0


def test_negative_3_explicit_evidence_reference_skip():
    """대조 3 (서증 정식 원용): 소송서면에서 서증 인용 부호를 밝혀 서술한 경우 (오탐 0)."""
    quote_text = (
        "갑 제1호증 사실경위서의 기재에 의하면 피고 회사 공장에서 기계 정비 작업을 수행하던 도중 "
        "안전장치가 제대로 작동하지 않아 사고가 발생한 사실이 입증됩니다."
    )

    doc_fact = _make_doc(
        "d_fact_ref",
        f"사 실 경 위 서\n{quote_text}",
        "사실경위서.pdf",
    )
    doc_prep = _make_doc(
        "d_prep_ref",
        f"준 비 서 면\n{quote_text}",
        "준비서면.pdf",
    )

    findings = cross_document_copies([doc_fact, doc_prep])
    assert len(findings) == 0


def test_negative_4_boilerplate_litigation_phrases():
    """대조 4 (소송 상투구 제외): 정형 서명·날인 확인 문구 (오탐 0)."""
    boilerplate = (
        "본인은 위 진술서 내용이 사실과 다름없음을 확인하고 자유로운 의사에 기하여 서명 날인합니다."
    )

    doc1 = _make_doc("d_b1", f"진 술 서\n{boilerplate}", "진술서1.pdf")
    doc2 = _make_doc("d_b2", f"진 술 서\n{boilerplate}", "진술서2.pdf")

    findings = cross_document_copies([doc1, doc2])
    assert len(findings) == 0


def test_negative_5_direct_quotation_of_opponent():
    """대조 5 (상대방 주장 인용): 따옴표 인용 부호 내 문장 (오탐 0)."""
    sentence = (
        "원고는 \"피고 회사의 중대한 과실로 인하여 안전사고가 발생하였으므로 전액 배상책임이 있다\"고 주장하나 "
        "이는 사실과 완전히 다릅니다."
    )

    doc_prep1 = _make_doc("d_p1", f"준 비 서 면\n{sentence}", "준비서면1.pdf")
    doc_prep2 = _make_doc("d_p2", f"준 비 서 면\n{sentence}", "준비서면2.pdf")

    findings = cross_document_copies([doc_prep1, doc_prep2])
    assert len(findings) == 0


def test_negative_6_evidence_explanation_inside_exhibit_entry_skip():
    """대조 6 (조건 1 준수): 증거설명서 내 정규 입증취지 항목(또는 표) 내부의 정상 서증 기재 (오탐 0)."""
    copied_paragraph = (
        "2023년 5월 10일 피고 회사 공장에서 기계 정비 작업을 수행하던 도중 안전장치가 제대로 작동하지 않아 "
        "작업자의 오른손이 롤러에 끼이는 중대한 사고가 발생하였습니다."
    )

    doc_fact = _make_doc(
        "d_fact_in",
        f"사 실 경 위 서\n작성인: 박○○\n\n{copied_paragraph}",
        "사실경위서.pdf",
    )
    # 증거설명서 내 '입증취지' 정규 설명 항목 내에 기재된 형태 (민사소송규칙 제106조 목적)
    doc_expl = _make_doc(
        "d_expl_in",
        f"증 거 설 명 서\n사건 2023가단12345\n\n1. 갑 제1호증\n입증취지: {copied_paragraph}",
        "증거설명서.pdf",
    )

    findings = cross_document_copies([doc_fact, doc_expl])
    # 정규 입증취지 항목 내 기재는 정상 실무이므로 제외(오탐 0)
    assert len(findings) == 0


def test_negative_7_list_item_and_police_rank_not_misclassified():
    """대조 7 (요구 ② 검증): 목록 줄, 경찰관 직위('경위'), 일반 명사 '경위'가 표제로 오인되지 않음."""
    # 1. 준비서면 첫머리 첨부목록에 '1. 사실경위서 1부'가 있는 경우 -> 준비서면(PLEADING)으로 정상 분류되어야 함
    doc_with_list = _make_doc(
        "d_list",
        "준 비 서 면\n사건 2023가합12345\n원고 홍길동\n첨부서류:\n1. 사실경위서 1부\n2. 영수증 1부\n\n본문...",
        "준비서면.pdf",
    )
    kind, _ = _document_title_kind(doc_with_list)
    assert kind == DOC_KIND_PLEADING

    # 2. 직위 낱말(경찰 계급 '경위')이 포함된 경우 -> 사실경위서(FACT_CONFIRMATION)로 오인되지 않아야 함
    doc_with_rank = _make_doc(
        "d_rank",
        "수 사 보 고\n담당: 사법경찰관 경위 김철수\n피의자 신문 결과 보고\n\n본문 내용...",
        "수사보고.pdf",
    )
    kind, _ = _document_title_kind(doc_with_rank)
    assert kind != DOC_KIND_FACT_CONFIRMATION

    # 3. 본문 중 일반 명사 '경위' 서술이 첫머리에 나타난 경우 -> 경위서로 오인되지 않아야 함
    doc_with_narrative = _make_doc(
        "d_narr",
        "의 견 서\n사건 발생 경위에 대하여 다음과 같이 설명드립니다.\n본문 내용...",
        "의견서.pdf",
    )
    kind, _ = _document_title_kind(doc_with_narrative)
    assert kind == DOC_KIND_PLEADING


def test_negative_8_evidence_explanation_vs_pleading_no_cross_copy():
    """대조 8 (요구 ③ 검증): 증거설명서와 준비서면 간 문장 일치는 원본이 서증이 아니므로 결함 미발생 (오탐 0)."""
    shared_text = (
        "원고는 피고 회사의 안전관리 소홀로 인하여 발생한 재해 사고에 대하여 "
        "사용자 책임에 따른 손해배상을 구하고자 이 사건 소송을 제기하였습니다."
    )

    doc_prep = _make_doc(
        "d_prep_common",
        f"준 비 서 면\n사건 2023가단12345\n\n1. 청구의 요지\n{shared_text}",
        "준비서면.pdf",
    )
    doc_expl = _make_doc(
        "d_expl_common",
        f"증 거 설 명 서\n사건 2023가단12345\n\n{shared_text}",
        "증거설명서.pdf",
    )

    findings = cross_document_copies([doc_prep, doc_expl])
    # 증거설명서와 소송서면 간 일치는 원본이 사실경위서(서증 원본)가 아니므로 결함 판정 0건
    assert len(findings) == 0


def test_statement_path_invariance_with_steve():
    """요구 ①·⑥ 검증: 진술서 경로(STATEMENT_HEADING_RE, _statement_start)가 Steve 원본과 동일하게 동작."""
    # 1. 단독 줄 진술서 제목 -> 정상 진술서 판정
    doc_stmt = _make_doc("d_st", "진 술 서\n성명: 홍길동\n본문 텍스트...")
    kind, offset = _document_title_kind(doc_stmt)
    assert kind == DOC_KIND_STATEMENT
    assert offset is not None

    # 2. 단독 줄 사실확인서 제목 -> 정상 진술서 판정
    doc_fact_stmt = _make_doc("d_fst", "사 실 확 인 서\n성명: 김철수\n본문 텍스트...")
    kind, offset = _document_title_kind(doc_fact_stmt)
    assert kind == DOC_KIND_STATEMENT
    assert offset is not None

    # 3. 본문 중 단어 '각 진술서'나 목록 속 문구는 진술서로 잡히지 않음 (Steve 원래 정규식 특성)
    doc_non_stmt = _make_doc("d_nst", "소  장\n증거목록 속 각 진술서의 기재를 참조하시기 바랍니다.")
    kind, _ = _document_title_kind(doc_non_stmt)
    assert kind == DOC_KIND_PLEADING

    # 4. 진술서(B등급) finding의 confidence_features에는 sources·differences가 없어야 함 (Steve와 100% 동일)
    shared = (
        "당시 저는 현장에서 약 3미터 떨어진 곳에서 자재를 운반하고 있었는데 굉음과 함께 비명 소리가 들려 "
        "즉시 현장으로 달려가 상황을 목격하게 되었습니다."
    )
    d_st = _make_doc("d_st2", f"진 술 서\n성명: 최○○\n\n{shared}", "진술서.pdf")
    d_cp = _make_doc("d_cp2", f"소  장\n원고 홍길동\n\n{shared}", "소장.pdf")
    stmt_findings = cross_document_copies([d_st, d_cp])
    assert len(stmt_findings) == 1
    assert stmt_findings[0].evidence_grade == EvidenceGrade.B
    assert "sources" not in stmt_findings[0].confidence_features
    assert "differences" not in stmt_findings[0].confidence_features


def test_c_grade_sources_preserve_multiple_owners_in_pipeline(tmp_path, monkeypatch):
    """요구 ① 검증: C등급(비진술서 통복제)에 문서별 sources가 있어야 파이프라인(_cross_check)에서
    서로 다른 owner 서면(소장, 준비서면 등)의 결함과 진술서(B등급) 결함이 하나로 합쳐져 소실되지 않음을 입증."""
    from packages.verification_engine.pipeline import DocumentInput, ProjectContext, VerificationPipeline
    from packages.pii_engine import PseudonymStore

    shared_fact = (
        "2023년 5월 10일 피고 회사 공장에서 기계 정비 작업을 수행하던 도중 안전장치가 제대로 작동하지 않아 "
        "작업자의 오른손이 롤러에 끼이는 중대한 사고가 발생하였습니다."
    )
    doc_fact = _make_doc("d_fact", f"사 실 경 위 서\n작성인: 박○○\n\n{shared_fact}", "사실경위서.pdf")
    doc_comp = _make_doc("d_comp", f"소  장\n원고 홍길동\n\n{shared_fact}", "소장.pdf")
    doc_prep = _make_doc("d_prep", f"준 비 서 면\n원고 대리인\n\n{shared_fact}", "준비서면.pdf")
    doc_stmt = _make_doc("d_stmt", f"진 술 서\n성명: 김○○\n\n{shared_fact}", "진술서.pdf")

    docs_map = {"d_fact": doc_fact, "d_comp": doc_comp, "d_prep": doc_prep, "d_stmt": doc_stmt}
    from packages.verification_engine import pipeline as pipeline_module
    monkeypatch.setattr(pipeline_module, "parse_document", lambda path, **kw: docs_map[kw["document_id"]])
    monkeypatch.setattr(pipeline_module, "PseudonymStore", lambda project_id, **kw: PseudonymStore(project_id, root=tmp_path))

    pipeline = VerificationPipeline()
    result = pipeline.run(
        "run-multi-owner-copy",
        ProjectContext("proj-multi-owner-copy"),
        [
            DocumentInput("d_fact", "사실경위서.pdf", "사실경위서.pdf"),
            DocumentInput("d_comp", "소장.pdf", "소장.pdf"),
            DocumentInput("d_prep", "준비서면.pdf", "준비서면.pdf"),
            DocumentInput("d_stmt", "진술서.pdf", "진술서.pdf"),
        ],
    )

    copy_findings = [f for f in result.project_findings if f.type == FindingType.CROSS_DOC_COPY.value]
    owners = {f.document_id: f.evidence_grade for f in copy_findings}
    # 진술서(B등급 1건)와 비진술서 소장·준비서면(각 C등급 1건)이 서로 충돌 없이 보존되어야 한다
    assert owners.get("d_stmt") == EvidenceGrade.B
    assert owners.get("d_comp") == EvidenceGrade.C
    assert owners.get("d_prep") == EvidenceGrade.C
    assert len(copy_findings) == 3


def test_running_head_and_subtitle_headings_classification():
    """요구 ② 검증: 1쪽 상단 running_head 블록에 위치한 표제 및 부제목/관리기호 병기 표제 정상 분류."""
    # 1. running_head에만 '사실경위서 ― 사건 부제목'이 있고 본문은 항목부터 시작하는 다쪽 서면
    doc_rh_fact = NormalizedDocument(
        document_id="rh_fact",
        filename="rh_fact.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block("rh1", "SD-07 | 사실경위서 ― 현장 설비 점검 사건", 1, block_type="running_head"),
                    Block("p1", "1. 작성 경위\n본 문서는 당시 상황을 기록한 것입니다.", 1, block_type="paragraph"),
                ],
            )
        ],
    )
    kind, _ = _document_title_kind(doc_rh_fact)
    assert kind == DOC_KIND_FACT_CONFIRMATION

    # 2. running_head에 '대금 청구 준비서면 관리번호 SD-03 / ...'가 있는 다쪽 서면
    doc_rh_plead = NormalizedDocument(
        document_id="rh_plead",
        filename="rh_plead.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block("rh2", "대금 청구 준비서면 관리번호 SD-03 / 2026년 검토 제출본 / 1쪽", 1, block_type="running_head"),
                    Block("p2", "1. 변론의 요지\n원고의 주장을 정리합니다.", 1, block_type="paragraph"),
                ],
            )
        ],
    )
    kind, _ = _document_title_kind(doc_rh_plead)
    assert kind == DOC_KIND_PLEADING

    # 3. '편철 확인서 ...' 또는 '제출자료 편철 및 표기 설명서 ...' 등 편철 안내 문서는 OTHER로 유지 (오탐 방지)
    doc_rh_cover = NormalizedDocument(
        document_id="rh_cover",
        filename="rh_cover.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block("rh3", "편철 확인서 관리번호 SD-01 / 2026년 검토 제출본 / 1쪽", 1, block_type="running_head"),
                    Block("p3", "1. 제출 취지\n이 자료는 서면 묶음에 편철하여 제출한다.", 1, block_type="paragraph"),
                ],
            )
        ],
    )
    kind, _ = _document_title_kind(doc_rh_cover)
    assert kind != DOC_KIND_STATEMENT
    assert kind != DOC_KIND_FACT_CONFIRMATION
    assert kind != DOC_KIND_PLEADING


def test_job_title_sojang_negative_not_pleading():
    """요구 ① 및 ③ 검증: 직위(기관·부대·현장 수식, 뒤에 다른 명사) '소장'은 PLEADING으로 분류되지 않아야 함 (음성 시험)."""
    # 1. 음성 대조군 5건 (직위 '소장'이므로 PLEADING이 아니어야 함)
    negative_cases = [
        "관리사무소 소장 확인서\n1. 확인 내용: 입주민 시설 점검 내역입니다.",
        "연구소 소장 명의 업무보고\n본 보고서는 신규 장비 검토 결과입니다.",
        "공사현장 소장 결재문\n금일 안전점검 완료 사항을 결재 요청합니다.",
        "소장 보고\n당월 시설 관리 현황 보고서입니다.",
        "파출소 소장 통보문\n관내 순찰 및 특이사항 통보의 건입니다.",
    ]
    for idx, text in enumerate(negative_cases):
        doc = _make_doc(f"neg_job_{idx}", text)
        kind, _ = _document_title_kind(doc)
        assert kind != DOC_KIND_PLEADING, f"직위 표제가 PLEADING으로 오분류됨: {text.splitlines()[0]}"

    # 2. 양성 기준군 4건 (실제 소송 서면 표제 꼴은 정상적으로 PLEADING으로 분류되어야 함)
    positive_cases = [
        ("소  장\n원고 홍길동\n피고 주식회사", DOC_KIND_PLEADING),
        ("SD-01 | 소장 ― 손해배상(기) 청구의 소\n원고 대리인 변호사", DOC_KIND_PLEADING),
        ("소장 (청구취지 및 청구원인 변경)\n사건 2024가단12345", DOC_KIND_PLEADING),
        ("원고 소장\n당사자 표시 및 청구원인", DOC_KIND_PLEADING),
    ]
    for idx, (text, expected_kind) in enumerate(positive_cases):
        doc = _make_doc(f"pos_plead_{idx}", text)
        kind, _ = _document_title_kind(doc)
        assert kind == expected_kind, f"정상 소송서면 표제가 분류 실패함: {text.splitlines()[0]}"


def test_derived_documents_negative_not_fact_confirmation():
    """요구 ② 및 ③ 검증: '사본·송부·안내·요청' 등 경위서 자체가 아닌 파생 문서는 FACT_CONFIRMATION으로 분류되지 않아야 함 (음성 시험)."""
    # 1. 음성 대조군 5건 (파생 문서명이므로 FACT_CONFIRMATION이 아니어야 함)
    negative_cases = [
        "사실경위서 사본 제출\n첨부자료 원본 대조필 사본 제출 목록입니다.",
        "사고경위서 송부의 건\n수신: 관련 부서\n참조: 인사팀",
        "경위서 발급 및 작성 안내문\n임직원 사고 발생 시 처리 절차 안내입니다.",
        "사건경위서 제출 요청서\n사건 관련 경위서 작성을 요청하오니 회신 바랍니다.",
        "경위서 ― 사본 일체\n관련 서류 사본 일체를 제출합니다.",
    ]
    for idx, text in enumerate(negative_cases):
        doc = _make_doc(f"neg_fact_{idx}", text)
        kind, _ = _document_title_kind(doc)
        assert kind != DOC_KIND_FACT_CONFIRMATION, f"파생 문서 표제가 FACT_CONFIRMATION으로 오분류됨: {text.splitlines()[0]}"

    # 2. 양성 기준군 4건 (실제 서증 원본 경위서 표제는 정상적으로 FACT_CONFIRMATION으로 분류되어야 함)
    positive_cases = [
        ("사 실 경 위 서\n1. 발생 경위: 당일 작업 현황입니다.", DOC_KIND_FACT_CONFIRMATION),
        ("SD-07 | 사실경위서 ― 현장 설비 점검 사건\n1. 일시 및 장소", DOC_KIND_FACT_CONFIRMATION),
        ("사고경위서 (작성자: 박○○)\n사고 발생 직후 조치 내역입니다.", DOC_KIND_FACT_CONFIRMATION),
        ("경위서 작성자: 홍길동\n당시 상황에 대한 육하원칙 진술입니다.", DOC_KIND_FACT_CONFIRMATION),
    ]
    for idx, (text, expected_kind) in enumerate(positive_cases):
        doc = _make_doc(f"pos_fact_{idx}", text)
        kind, _ = _document_title_kind(doc)
        assert kind == expected_kind, f"정상 사실경위서 표제가 분류 실패함: {text.splitlines()[0]}"




