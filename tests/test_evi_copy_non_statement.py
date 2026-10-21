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

