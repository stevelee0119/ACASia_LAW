"""서증 형식 결함(EVI-FORM) 구조 기반 검출 및 오탐 방지 시험.

민사소송법 제277조, 제355조, 제358조 및 민사소송규칙 제121·122조에 따른
서증 형식 요건 흠결(파일명·자리표시만 존재, 부제출 자인, 작성자·서명 공란,
중요 기재사항 잘림/식별불가)에 대한 파이프라인 진입점, 구조적 양성 6건, 대조군 11건 검증을 수행한다.
"""
from pathlib import Path
import pytest

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import (
    check_evidence_form_defects,
    _EVI_FORM_PLACEHOLDER_RE,
    _EVI_FORM_UNSUBMITTED_RE,
    _EVI_FORM_BLANK_RE,
    _EVI_FORM_UNIDENTIFIABLE_RE,
)
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)
from packages.pii_engine import PseudonymStore


def _make_doc(text_paragraphs, doc_id="TEST-FORM-01"):
    """시험용 NormalizedDocument 생성 헬퍼 함수."""
    blocks = []
    for idx, text in enumerate(text_paragraphs):
        blocks.append(
            Block(
                block_id=f"b_{idx}",
                page=1,
                block_type="paragraph",
                text=text,
                source_layer="visible_text",
                visible=True,
            )
        )
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=blocks)],
    )


# === 1. 실제 파이프라인 진입점 시험 ===
def test_pipeline_entrypoint_evidence_form_defects(monkeypatch, tmp_path):
    """실제 VerificationPipeline 진입점을 통한 서증 형식 결함 검출 검증 (점검표 1항)."""
    from packages.verification_engine import pipeline as pipeline_module

    # 파이프라인 전체를 통과하는 서면 생성
    doc = _make_doc([
        "준비서면",
        "5. 물품대금 정산 및 확인",
        "원고는 갑 제101호증 물품대금 계약서의 영문 원본은 제출되지 않았으나 사본으로 입증을 시도합니다.",
        "6. 배송확인 자료 검토",
        "원고가 제출한 갑 제102호증 확인서 작성자의 성명과 날인이 전혀 없다.",
        "2026. 1. 15.",
        "원고 소송대리인 변호사 김변호",
        "서울중앙지방법원 귀중",
    ], doc_id="entry_form_doc")

    monkeypatch.setattr(pipeline_module, "parse_document", lambda path, **kw: doc)
    monkeypatch.setattr(pipeline_module, "PseudonymStore", lambda project_id, **kw: PseudonymStore(project_id, root=tmp_path))

    pipeline = VerificationPipeline()
    result = pipeline.run(
        "run-entry-form-test",
        ProjectContext("proj-form-test"),
        [DocumentInput("entry_form_doc", "dummy.pdf", "dummy.pdf")],
    )

    doc_result = result.documents[0]
    form_findings = [f for f in doc_result.findings if f.type == FindingType.EVIDENCE_FORM_DEFECT.value]

    # 두 결함 모두 검출되어야 함 (개수 및 상태 엄격 검증)
    assert len(form_findings) == 2, f"기대 2건, 실측 {len(form_findings)}건: {form_findings}"

    # 1) 부제출 자인 결함 확인 (축 a: CONTRADICTED · B)
    f1 = next((f for f in form_findings if "갑 제101호증" in f.title), None)
    assert f1 is not None
    assert f1.status == VerificationStatus.CONTRADICTED.value
    assert f1.evidence_grade == EvidenceGrade.B.value
    assert "서증 미제출 자인" in f1.title

    # 2) 작성자·서명 공란 결함 확인 (축 b: SUSPICIOUS · B)
    f2 = next((f for f in form_findings if "갑 제102호증" in f.title), None)
    assert f2 is not None
    assert f2.status == VerificationStatus.SUSPICIOUS.value
    assert f2.evidence_grade == EvidenceGrade.B.value
    assert "공란" in f2.title or "서명" in f2.title


# === 2. 구조 기반 양성 예시 시험 6건 (메모 91 매트릭스 4대 축 검증) ===
def test_positive_structural_evidence_lost():
    """양성 1 (축 a): 원본 분실로 인한 미제출 자인 결함 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제1호증 계약서 원본은 보관 중 분실하여 제출하지 못하였습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제1호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_structural_media_not_attached():
    """양성 2 (축 a): 동영상 파일 미첨부 요약보고서만 제출 결함 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제2호증 동영상 파일이 첨부되지 않은 채 요약 보고서만 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제2호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_structural_author_name_omitted():
    """양성 3 (축 b): 사실확인서 작성자 성명란 공란 결함 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제3호증 사실확인서에 작성자 성명란이 공란으로 비어 있습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제3호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_structural_date_field_missing():
    """양성 4 (축 b): 동의서 작성일자 기재 누락 결함 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제4호증 동의서는 작성일자 기재가 빠져 있는 미완성 양식입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제4호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_structural_scan_truncated():
    """양성 5 (축 c): 영수증 스캔 하단 잘림 식별불가 결함 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제5호증 영수증 스캔 하단이 잘려 중요한 결제 내역을 식별할 수 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제5호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNIDENTIFIABLE_CONTENT_TRUNCATED"


def test_positive_structural_bracket_placeholder():
    """양성 6 (축 d): 현장사진 자리표시 마크업만 기재된 결함 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제6호증 현장사진 [증빙 이미지 첨부 예정]",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제6호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "EXHIBIT_PLACEHOLDER_ONLY"


# === 3. 신규 대조군 시험 11건 (정상 실무 및 보호 문맥 오탐 0건 검증) ===
def test_control_future_submission_plan():
    """대조군 1: 추후 제출 예정 정상 입증 계획 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제7호증 감정평가서는 결과 회신 후 제출할 예정입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"추후 제출 예정은 결함으로 잡지 않아야 함: {findings}"


def test_control_future_supplement_plan():
    """대조군 2: 추후 보완 예정 정상 입증 계획 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제8호증 번역 공증서는 다음 변론기일까지 보완할 계획입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"추후 보완 계획은 결함으로 잡지 않아야 함: {findings}"


def test_control_bring_original_to_court():
    """대조군 3: 원본 기일 지참 제시 계획 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제9호증 원본은 기일에 지참하여 제시할 예정입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"원본 기일 지참 계획은 결함으로 잡지 않아야 함: {findings}"


def test_control_remedy_omitted_signature():
    """대조군 4: 결함 해소 및 추완 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제10호증에 누락된 서명은 보완하여 금일 다시 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"누락 보완 재제출 진술은 결함으로 잡지 않아야 함: {findings}"


def test_control_double_negation_defense():
    """대조군 5: 이중 부정 반박 문맥 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제11호증의 원본을 확보하지 못하였다고 볼 수 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"이중 부정 반박 문맥은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_argument_refutation():
    """대조군 6: 상대방 주장 인용 및 반박 문맥 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "피고는 갑 제12호증에 서명이 없다고 주장하나 이는 사실과 다릅니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 주장 인용 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_evidence_challenge():
    """대조군 7: 상대방 증거 탄핵 배제 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "피고가 제출한 을 제1호증은 작성자 서명이 누락되어 진정성립이 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 증거 탄핵 배제는 결함으로 잡지 않아야 함: {findings}"


def test_control_separate_media_usb():
    """대조군 8: USB 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "갑 제13호증 통화녹음(USB 별도 제출)",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"USB 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_separate_media_cd():
    """대조군 9: CD 추후 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "을 제14호증 현장영상(CD 추후 별도 제출)",
        "피고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"CD 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_complete_document():
    """대조군 10: 작성자 서명 및 작성일자가 완비된 계약서 원본 정상 제출 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제15호증 작성자 서명 및 작성일자가 완비된 계약서 원본을 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"서명 완비 정상 제출은 결함으로 잡지 않아야 함: {findings}"


def test_control_defendant_answer_claim_dismissal():
    """대조군 11: 피고 답변서 끝에 '원고의 청구를 기각...' 주문 문맥이 있어도 오탐 0건."""
    doc = _make_doc([
        "답변서",
        "원고가 제출한 갑 제1호증은 작성자 서명이 없어 그 진정성립을 인정할 수 없습니다.",
        "2026. 2. 20.",
        "원고의 청구를 기각하여 주시기 바랍니다.",
        "피고 소송대리인 변호사 이몽룡",
        "서울서부지방법원 귀중",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"피고 답변서에서 원고 증거 탄핵은 결함으로 잡지 않아야 함: {findings}"
