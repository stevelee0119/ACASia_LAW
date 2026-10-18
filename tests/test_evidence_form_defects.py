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
    """양성 1 (축 2): 원본 미제출 자인 결함 검출 (CONTRADICTED · B)."""
    # 평가 측 탐침 표현 포섭: "원본은 아직 찾지 못해 내지 못하였습니다"
    doc = _make_doc([
        "원고는 다음과 같이 입증취지를 밝힙니다.",
        "갑 제1호증 계약서 원본은 아직 찾지 못해 내지 못하였습니다.",
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
    """양성 2 (축 3): 작성자 이름과 도장 누락 공란 양식 검출 (SUSPICIOUS · B)."""
    # 평가 측 탐침 표현 포섭: "작성자 이름과 도장이 들어가 있지 않습니다"
    doc = _make_doc([
        "원고는 입증자료를 제출합니다.",
        "갑 제2호증 확인서에 작성자 이름과 도장이 들어가 있지 않습니다.",
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
    """양성 3 (축 2): 녹음 원본 음성은 미제출하고 요지만 기재한 자인 검출 (CONTRADICTED · B)."""
    # 평가 측 탐침 표현 포섭: "녹음 원본 음성은 제출하지 않고 요지만"
    doc = _make_doc([
        "원고 주장 입증방법.",
        "갑 제3호증 녹음 원본 음성은 제출하지 않고 요지만 정리하여 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제3호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_unidentifiable_content_truncated():
    """양성 4 (축 4): 금액 칸이 흐려 숫자를 읽기 어려운 식별 불가 결함 검출 (CONTRADICTED · B)."""
    # 평가 측 탐침 표현 포섭: "금액 칸이 흐려 숫자를 읽기 어렵습니다"
    doc = _make_doc([
        "원고 변론.",
        "갑 제4호증 영수증은 금액 칸이 흐려 숫자를 읽기 어렵습니다.",
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
    """양성 5 (축 1): 서증 항목 내용 자리에 자리표시 마크업만 기재 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "원고의 입증방법.",
        "갑 제5호증 전산화면 [화면 이미지 준비중]",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.SUSPICIOUS
    assert findings[0].evidence_grade == EvidenceGrade.B
    assert "갑 제5호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "EXHIBIT_PLACEHOLDER_ONLY"


# === 3. 신규 대조군 시험 (정상 실무 및 상대방 탄핵, 물리 매체 별도 제출 정상 보호) ===
def test_control_future_submission_plan():
    """대조군 1: 추후 제출 예정 / 보완 예정 등 소송 실무상 정상 입증계획 오탐 0건."""
    # 평가 측 대조군: "갑 제7호증 감정서는 감정 결과가 나오는 대로 제출 예정입니다"
    #                 "번역문은 다음 기일 전까지 보완 예정입니다"
    doc = _make_doc([
        "준비서면",
        "갑 제7호증 감정서는 감정 결과가 나오는 대로 제출 예정입니다.",
        "갑 제8호증 번역문은 다음 기일 전까지 보완 예정입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"추후 제출/보완 예정 정상 입증 계획은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_evidence_signature_challenge():
    """대조군 2: 상대방 증거(피고 제출 을호증)의 서명 누락 지적·탄핵 문맥 오탐 0건."""
    doc = _make_doc([
        "준비서면",
        "원고는 피고의 주장을 반박합니다.",
        "피고가 제출한 을 제3호증은 작성자 서명이 누락되어 진정성립이 인정될 수 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 증거 탄핵은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_evidence_original_challenge():
    """대조군 3: 상대방 증거의 원본 미제출에 대한 주장 입증 부족 지적 오탐 0건."""
    doc = _make_doc([
        "답변서",
        "원고가 제출한 증거는 원본이 제출되지 않았다는 주장을 입증하기에 부족합니다.",
        "피고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 증거 비판은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_transcript_credibility_challenge():
    """대조군 4: 상대방 녹취서 신빙성 배척 주장 오탐 0건."""
    doc = _make_doc([
        "준비서면",
        "상대방이 제출한 녹취서는 신빙성이 없으므로 배척되어야 합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"신빙성 탄핵 주장은 결함으로 잡지 않아야 함: {findings}"


def test_control_physical_media_separate_submission_usb():
    """대조군 5: USB 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "갑 제3호증 통화녹음(USB 별도 제출)",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"USB 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_physical_media_cd_submission():
    """대조군 6: CD 추후 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "을 제5호증 현장 동영상(CD 추후 별도 제출)",
        "피고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"CD 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_normal_exhibits_with_originals():
    """대조군 7: 외국어 원본과 번역문이 모두 정상 제출된 경우 오탐 0건."""
    doc = _make_doc([
        "5. 해외계약 정산 및 확인",
        "갑 제301호증 해외계약 1차 원본 및 번역문을 첨부하여 제출한다.",
        "영문 원본 1부와 공증된 한국어 번역문 1부를 모두 제출 완료하였습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0


def test_control_signed_statement():
    """대조군 8: 작성자와 서명이 온전히 완료된 진술서 오탐 0건."""
    doc = _make_doc([
        "5. 현장확인 정산 및 확인",
        "갑 제302호증 현장확인 1차 확인서를 제출한다.",
        "작성자 김철수가 본인의 서명 날인을 마친 온전한 원본입니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0


def test_control_pleading_electronic_signature_omitted():
    """대조군 9: 본안 소송서류 말미의 전자소송 서명 생략 문맥 오탐 0건."""
    doc = _make_doc([
        "이 사건 청구원인에 관하여 위와 같이 변론합니다.",
        "2026. 1. 15.",
        "원고 여도겸 (서명 생략)",
        "해솔지방법원 귀중",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0


def test_control_defendant_answer_with_plaintiff_claim_dismissal():
    """대조군 10: 피고 답변서 끝에 '원고의 청구를 기각...' 주문 문맥이 있어도 피고 서면으로 올바르게 인식 (오탐 0건)."""
    doc = _make_doc([
        "답변서",
        "원고가 제출한 갑 제1호증은 그 작성 경위가 불분명합니다.",
        "2026. 2. 20.",
        "원고의 청구를 기각하여 주시기 바랍니다.",
        "피고 소송대리인 변호사 이몽룡",
        "서울서부지방법원 귀중",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"피고 답변서에서 원고 증거 탄핵은 결함으로 잡지 않아야 함: {findings}"
