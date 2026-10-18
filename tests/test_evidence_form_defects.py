"""서증 형식 결함(EVI-FORM) 구조 기반 검출 및 오탐 방지 시험.

민사소송법 제277조, 제355조, 제358조 및 민사소송규칙 제121·122조에 따른
서증 형식 요건 흠결(파일명·자리표시만 존재, 부제출 자인, 작성자·서명 공란,
중요 기재사항 잘림/식별불가)에 대한 진입점, 양성 5건, 대조군 5건 검증을 수행한다.
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
    """시험용 NormalizedDocument 생성 헬퍼."""
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

    doc = _make_doc([
        "준비서면",
        "5. 물품대금 정산 및 확인",
        "원고는 갑 제101호증 물품대금 계약서의 영문 원본은 제출되지 않았으나 사본으로 입증을 시도합니다.",
        "6. 배송확인 자료 검토",
        "원고가 제출한 갑 제102호증 확인서 작성자의 성명과 날인이 전혀 없다.",
        "2026. 1. 15.",
        "원고 소송대리인 변호사 홍길동",
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

    # 두 결함 모두 검출되어야 함 (개수 및 내용 엄격 검증)
    assert len(form_findings) == 2, f"기대 2건, 실측 {len(form_findings)}건: {form_findings}"

    # 1) 부제출 자인 결함 확인 (축 2: CONTRADICTED · B)
    f1 = next((f for f in form_findings if "갑 제101호증" in f.title), None)
    assert f1 is not None
    assert f1.status == VerificationStatus.CONTRADICTED.value
    assert f1.evidence_grade == EvidenceGrade.B.value
    assert "서증 미제출 자인" in f1.title
    assert "제출되지 않았으나" in f1.evidence[0].excerpt

    # 2) 작성자·서명 공란 결함 확인 (축 3: SUSPICIOUS · B)
    f2 = next((f for f in form_findings if "갑 제102호증" in f.title), None)
    assert f2 is not None
    assert f2.status == VerificationStatus.SUSPICIOUS.value
    assert f2.evidence_grade == EvidenceGrade.B.value
    assert "공란" in f2.title or "서명" in f2.title
    assert "성명과 날인이 전혀 없다" in f2.evidence[0].excerpt


# === 2. 신규 양성 예시 5건 시험 (4대 축 검증) ===
def test_positive_unsubmitted_admission():
    """양성 1 (축 2): 영문 원본 미제출 자인 결함 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "원고는 다음과 같이 입증취지를 밝힙니다.",
        "갑 제1호증 계약서 영문 원본은 제출되지 않았으나 국문 요약본을 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제1호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_blank_signature_form():
    """양성 2 (축 3): 작성자의 성명과 날인 부존재 공란 양식 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "원고는 입증자료를 제출합니다.",
        "갑 제2호증 확인서 작성자의 성명과 날인이 전혀 없다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제2호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_summary_memo_without_audio():
    """양성 3 (축 1): 녹음 파일 없이 요지만 정리한 메모뿐 소리 데이터 부존재 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "원고 주장 입증방법.",
        "갑 제3호증 통화 녹음 파일 없이 요지만 정리한 메모뿐 소리 데이터는 없다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제3호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "EXHIBIT_PLACEHOLDER_ONLY"


def test_positive_unidentifiable_content_truncated():
    """양성 4 (축 4): 하단이 복사되지 않아 합계 금액을 알 수 없는 식별 불가 결함 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "원고 변론.",
        "갑 제4호증 영수증 하단이 복사되지 않아 금액을 알 수 없다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제4호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNIDENTIFIABLE_CONTENT_TRUNCATED"


def test_positive_media_filename_unsubmitted():
    """양성 5 (축 1): 파일명만 기재되고 파일 자체 미제출 자인 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "원고의 입증방법.",
        "갑 제5호증 녹음파일 VOICE-01.wav 파일 자체는 제출되지 않았다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제5호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "EXHIBIT_PLACEHOLDER_ONLY"


# === 3. 신규 대조군 5건 시험 (상대방 탄핵 및 물리 매체 별도 제출 정상 보호) ===
def test_control_opponent_evidence_signature_challenge():
    """대조군 1: 상대방 증거(피고 제출 을호증)의 서명 누락 지적·탄핵 문맥 오탐 0건."""
    doc = _make_doc([
        "준비서면",
        "원고는 피고의 주장을 반박합니다.",
        "피고가 제출한 을 제3호증은 작성자 서명이 누락되어 진정성립이 인정될 수 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 증거 탄핵은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_evidence_original_challenge():
    """대조군 2: 상대방 증거의 원본 미제출에 대한 주장 입증 부족 지적 오탐 0건."""
    doc = _make_doc([
        "답변서",
        "원고가 제출한 증거는 원본이 제출되지 않았다는 주장을 입증하기에 부족합니다.",
        "피고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 증거 비판은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_transcript_credibility_challenge():
    """대조군 3: 상대방 녹취서 신빙성 배척 주장 오탐 0건."""
    doc = _make_doc([
        "준비서면",
        "상대방이 제출한 녹취서는 신빙성이 없으므로 배척되어야 합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"신빙성 탄핵 주장은 결함으로 잡지 않아야 함: {findings}"


def test_control_physical_media_separate_submission_usb():
    """대조군 4: USB 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "갑 제3호증 통화녹음(USB 별도 제출)",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"USB 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_physical_media_cd_submission():
    """대조군 5: CD 추후 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "을 제5호증 현장 동영상(CD 추후 별도 제출)",
        "피고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"CD 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


# === 4. 기존 대조군 유지 시험 (정상 문서 및 전자서명 생략) ===
def test_control_normal_exhibits_with_originals():
    """대조군 6: 외국어 원본과 번역문이 모두 정상 제출된 경우 오탐 0건."""
    doc = _make_doc([
        "5. 해외계약 정산 및 확인",
        "갑 제301호증 해외계약 1차 원본 및 번역문을 첨부하여 제출한다.",
        "영문 원본 1부와 공증된 한국어 번역문 1부를 모두 제출 완료하였습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0


def test_control_signed_statement():
    """대조군 7: 작성자와 서명이 온전히 완료된 진술서 오탐 0건."""
    doc = _make_doc([
        "5. 현장확인 정산 및 확인",
        "갑 제302호증 현장확인 1차 확인서를 제출한다.",
        "작성자 김철수가 본인의 서명 날인을 마친 온전한 원본입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0


def test_control_pleading_electronic_signature_omitted():
    """대조군 8: 본안 소송서류 말미의 전자소송 서명 생략 문맥 오탐 0건."""
    doc = _make_doc([
        "이 사건 청구원인에 관하여 위와 같이 변론합니다.",
        "2026. 1. 15.",
        "원고 여도겸 (서명 생략)",
        "해솔지방법원 귀중",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0
