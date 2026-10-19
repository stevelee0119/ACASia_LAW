"""서증 형식 결함(EVI-FORM) 구조 기반 검출 및 오탐 방지 시험.

민사소송법 제277조, 제355조, 제358조 및 민사소송규칙 제121·122조에 따른
서증 형식 요건 흠결(파일명·자리표시만 존재, 부제출 자인, 작성자·서명 공란,
중요 기재사항 잘림/식별불가)에 대한 파이프라인 진입점, 구조적 양성 14건, 대조군 14건 검증을 수행한다.
"""
from pathlib import Path
import pytest

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import (
    check_evidence_form_defects,
    _EVI_FORM_PLACEHOLDER_RE,
    _EVI_FORM_UNSUBMITTED_RE,
    _EVI_FORM_EXHIBIT_UNSUBMITTED_RE,
    _EVI_FORM_BLANK_RE,
    _EVI_FORM_UNIDENTIFIABLE_RE,
    _EVI_FORM_PROCEDURAL_JUSTIFICATION_RE,
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


# === 2. 구조 기반 양성 예시 시험 14건 (전달문 15 확장 검증) ===
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
    """양성 5 (축 c): 영수증 스캔 하단 잘림 보이지 않음 결함 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제5호증 영수증 스캔 하단이 잘려 중요한 결제 일자가 보이지 않습니다.",
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


def test_positive_structural_exhibit_direct_unsubmitted():
    """양성 7 (피드백 2): 호증 자체가 주어인 미제출 자인 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제7호증은 아직 제출하지 못하였으나 거래 내역에 부합합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert findings[0].type == FindingType.EVIDENCE_FORM_DEFECT
    assert findings[0].status == VerificationStatus.CONTRADICTED
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_structural_adjacent_sentence_defect():
    """양성 8 (피드백 3): 앞 문장 호증 제시 + 인접 다음 문장 결함 진술 결속 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "원고는 계약 체결 경위에 대하여 설명합니다. 원고는 갑 제8호증 확인서를 제출합니다. "
        "그러나 위 확인서에는 작성자 서명이 누락되어 있습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제8호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_structural_blank_state_negation():
    """양성 9 (전달문 16): 대상 명사 + 상태 부정 일반형(~되어 있지 않/못) 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제8호증 확인서에 대해 당사자 서명날인이 되어 있지 않은 채로 제출되었습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제8호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_structural_recovery_failure():
    """양성 9-2 (전달문 16): 회수·복구·발급 실패 일반형 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제14호증 데이터 파일은 시스템 오류로 복구하지 못하여 출력하지 못했습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제14호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_structural_partial_pages_omitted():
    """양성 9-3 (전달문 16): 일부 장·면 누락 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제15호증 정산서 중 뒷면 일부 페이지가 누락되어 식별하기 어렵습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제15호증" in findings[0].title


def test_positive_structural_defendant_statement_unsigned():
    """양성 10 (피드백 5-1): 피고 서면에서 자기 진술서 서명 결손 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "답변서",
        "피고는 을 제1호증 진술서를 제출하나, 해당 진술서에는 작성자 서명날인이 빠져 있습니다.",
        "피고 소송대리인 변호사 이을수",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "을 제1호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_structural_audio_file_not_kept():
    """양성 11 (피드백 5-5): 음성 파일 미보관 자인 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제9호증 통화 녹음 파일은 현재 보관하고 있지 않아 요약서만 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제9호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_structural_original_missing_translation_only():
    """양성 12 (피드백 5-3): 외국어 원문 미제출 + 번역문만 제출 자인 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제10호증 해외 계약서 원문은 제출하지 못하여 번역본만 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제10호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_structural_list_row_parentheses_placeholder():
    """양성 13 (피드백 5-4): 증거목록 행 괄호 속 첨부 예정 자리표시 검출 (SUSPICIOUS · B)."""
    doc = _make_doc([
        "증거목록",
        "1. 갑 제11호증 전산화면 (화면 캡처 첨부 예정)",
        "2. 갑 제12호증 확인서",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제11호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "EXHIBIT_PLACEHOLDER_ONLY"


def test_positive_structural_smudge_unidentifiable():
    """양성 14 (피드백 5-6): 서증 번짐으로 판독 곤란 자인 검출 (CONTRADICTED · B)."""
    doc = _make_doc([
        "준비서면",
        "갑 제13호증 영수증은 잉크 번짐으로 인해 금액 판독이 곤란합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1
    assert "갑 제13호증" in findings[0].title
    assert findings[0].confidence_features.get("defect_code") == "UNIDENTIFIABLE_CONTENT_TRUNCATED"


# === 3. 신규 대조군 시험 14건 (정상 실무 및 보호 문맥 오탐 0건 검증) ===
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


def test_control_negation_of_defect_omission_none():
    """대조군 6 (피드백 1): 결손의 부존재(빠진 기재가 없다) 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제16호증 계약서에는 서명과 날인이 모두 되어 있고 빠진 기재가 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"결손 부존재 서술은 결함으로 잡지 않아야 함: {findings}"


def test_control_negation_of_defect_blank_none():
    """대조군 7 (피드백 1): 결손의 부존재(누락된 항목이나 공란이 없다) 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제17호증 확인서에 누락된 항목이나 공란은 전혀 존재하지 않습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"공란 부존재 서술은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_argument_refutation():
    """대조군 8: 상대방 주장 인용 및 반박 문맥 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "피고는 갑 제12호증에 서명이 없다고 주장하나 이는 사실과 다릅니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 주장 인용 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_evidence_challenge():
    """대조군 9: 상대방 증거 탄핵 배제 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "피고가 제출한 을 제1호증은 작성자 서명이 누락되어 진정성립이 없습니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 증거 탄핵 배제는 결함으로 잡지 않아야 함: {findings}"


def test_control_separate_media_usb():
    """대조군 10: USB 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "갑 제13호증 통화녹음(USB 별도 제출)",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"USB 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_separate_media_cd():
    """대조군 11: CD 추후 별도 제출 기재 정상 입증방법 보호 (오탐 0건)."""
    doc = _make_doc([
        "입증방법",
        "을 제14호증 현장영상(CD 추후 별도 제출)",
        "피고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"CD 별도 제출 정상 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_complete_document():
    """대조군 12: 작성자 서명 및 작성일자가 완비된 계약서 원본 정상 제출 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제15호증 작성자 서명 및 작성일자가 완비된 계약서 원본을 제출합니다.",
        "원고 소송대리인",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"서명 완비 정상 제출은 결함으로 잡지 않아야 함: {findings}"


def test_control_defendant_answer_claim_dismissal():
    """대조군 13: 피고 답변서 끝에 '원고의 청구를 기각...' 주문 문맥이 있어도 오탐 0건."""
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


def test_control_no_additional_evidence():
    """대조군 14 (전달문 16 가): 이 증거 외에 추가 증거를 내지 않겠다는 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제1호증 외에 추가로 제출할 증거 자료는 전혀 없습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"추가 증거 없음 정상 진술은 결함으로 잡지 않아야 함: {findings}"


def test_control_prior_submission_no_duplicate():
    """대조군 15 (전달문 16 나): 앞 서면에 이미 제출하여 중복 첨부하지 않는다는 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제2호증 영수증은 종전 소장에 이미 첨부하여 제출하였으므로 중복 제출을 피하기 위해 이번 서면에서는 별도로 첨부하지 않습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"기제출 중복 생략 진술은 결함으로 잡지 않아야 함: {findings}"


def test_control_public_system_accessible():
    """대조군 16 (전달문 16 다): 공적 전산망으로 확인 가능하여 첨부 생략하는 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제3호증 등기사항전부증명서는 대법원 전산망을 통해 즉시 확인 가능하므로 서면에 별도 첨부하지 아니합니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"공적 전산 확인 가능 진술은 결함으로 잡지 않아야 함: {findings}"


def test_control_court_order_request_reason():
    """대조군 17 (전달문 16 라): 문서제출명령/촉탁 신청 사유로 원본 미소지 기재한 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제4호증 금융거래내역은 해당 은행에 대한 문서제출명령을 신청할 예정이므로 원고가 원본을 직접 소지하고 있지 않습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"문서제출명령 신청 사유 기재는 결함으로 잡지 않아야 함: {findings}"


def test_control_no_other_evidence_variant_1():
    """대조군 18 (전달문 17 조건 1): '외에 다른 입증방법 제출 안 함' 변형 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제1호증 외에 다른 입증방법을 제출할 계획이 없습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"추가 증거 없음 변형 진술은 결함으로 잡지 않아야 함: {findings}"


def test_control_no_other_evidence_variant_2():
    """대조군 19 (전달문 17 조건 1, TK-81): '이 밖에 그 밖의 증거 내지 않음' 변형 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "본 서증 이 밖에 그 밖의 증거는 내지 않기로 하였습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"추가 증거 없음 변형 진술은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_quote_refutation_variant_1():
    """대조군 20 (전달문 17 조건 2): 상대방 주장 인용(-다고 하나) 뒤 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "피고는 갑 제2호증에 서명날인이 빠졌다고 하나, 문서 말미에 작성자 자필서명이 분명히 존재합니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 주장 인용 후 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_quote_refutation_variant_2():
    """대조군 21 (전달문 17 조건 2): 상대방 주장 인용(-다고 다투지만) 뒤 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "상대방은 갑 제3호증 계약서의 중요 부분이 잘려 있다고 다투지만, 이는 사실과 명백히 다릅니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 주장 인용 후 반박은 결함으로 잡지 않아야 함: {findings}"


# ====================================================================================
# TK-81 신규 검증 시험: EVI-FORM 제외 규칙 과잉 수정 검증
# ====================================================================================

def test_positive_defect_unquoted_concessive_clause_1():
    """양성 시험 17 (TK-81): 주어 없이 '~다고 하나/지만' 역접이 결손 기술에 사용된 경우 결함 정상 검출."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제1호증을 제출하나, 작성자 서명이 빠져 있다고 보이지만, 이를 입증방법으로 원용합니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1, f"주어 없는 역접 결손 서술은 결함으로 정상 검출되어야 함: {findings}"
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_positive_defect_unquoted_concessive_clause_2():
    """양성 시험 18 (TK-81): 주어 없이 판독 불가 서술에 '~다고 보이나' 등이 결합된 경우 결함 정상 검출."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제2호증 영수증 하단이 잘려 금액을 판독할 수 없다고 보이나, 실질적인 효력에는 변함이 없습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1, f"주어 없는 역접 판독 불가 서술은 결함으로 정상 검출되어야 함: {findings}"
    assert findings[0].confidence_features.get("defect_code") == "UNIDENTIFIABLE_CONTENT_TRUNCATED"


def test_positive_defect_standalone_bakke_1():
    """양성 시험 19 (TK-81): 단독 '밖에'가 사용된 미제출 자인 결함 정상 검출."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제3호증에 대하여 사본 밖에 소지하지 못하여 원본을 제출하지 못합니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1, f"단독 밖에로 표현된 미제출 자인은 결함으로 정상 검출되어야 함: {findings}"
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_defect_standalone_bakke_2():
    """양성 시험 20 (TK-81): 단독 '밖에'가 사용된 필수 기재 누락 결손 진술 결함 정상 검출."""
    doc = _make_doc([
        "준비서면",
        "갑 제4호증은 작성일자 밖에 기재되어 있지 않아 작성자 성명이 공란입니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1, f"단독 밖에와 결합된 필수 기재 누락은 결함으로 정상 검출되어야 함: {findings}"
    assert findings[0].confidence_features.get("defect_code") == "BLANK_FORM_DEFECT"


def test_control_opponent_adnominal_claim_refutation_1():
    """대조군 22 (TK-81): 상대방 주장 관형형('-다는 주장') + 부정 평가('사실과 다르다') 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제5호증 계약서의 서명날인이 위조되었다는 피고의 주장은 사실과 전혀 다릅니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 관형형 주장 인용 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_adnominal_claim_refutation_2():
    """대조군 23 (TK-81): 상대방 주장 관형형('-라는 지적') + 부정 평가('이유 없다') 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "을 제6호증 진술서가 작성자의 진정한 의사에 기하지 않았다는 상대방의 지적은 전혀 이유 없습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 관형형 지적 인용 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_adnominal_claim_refutation_3():
    """대조군 24 (TK-81 전달문 20): 관형형 반박 합쇼체('사실과 다릅니다') 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제7호증 차용증의 금액 기재가 변조되었다는 상대측 주장은 사실과 명백히 다릅니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 관형형 주장 합쇼체 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_adnominal_claim_refutation_4():
    """대조군 25 (TK-81 전달문 20): 관형형 반박 합쇼체('사실과 틀립니다') 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "을 제8호증 확인서의 작성일자가 소급 기재되었다는 원고의 지적은 실제 사실과 전혀 틀립니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 관형형 지적 합쇼체 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_opponent_adnominal_claim_refutation_5():
    """대조군 26 (TK-81 전달문 20): 관형형 반박 연결형('사실과 달라') 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "피고는 갑 제9호증 영수증의 중요 부분이 훼손되었다는 주장은 실체적 사실과 달라 근거가 없습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 관형형 주장 연결형 반박은 결함으로 잡지 않아야 함: {findings}"


# ====================================================================================
# TK-81 잔여 (전달문 26): 단독 '틀립니다·잘못입니다' 반박 오탐 방지 및 결함 보존 시험
# ====================================================================================

def test_control_standalone_wrong_refutation_1():
    """대조군 27 (TK-81 잔여): 상대방 지적 관형형 + 단독 '틀립니다' 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제10호증에 원본이 첨부되지 않았다는 피고의 지적은 명백히 틀립니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 지적 인용 후 단독 '틀립니다' 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_standalone_wrong_refutation_2():
    """대조군 28 (TK-81 잔여): 상대방 주장 관형형 + 단독 '틀렸습니다' 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "을 제11호증 확인서에 작성자 서명이 누락되었다는 원고의 주장은 전적으로 틀렸습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 주장 인용 후 단독 '틀렸습니다' 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_standalone_wrong_refutation_3():
    """대조군 29 (TK-81 잔여): 상대방 지적 관형형 + 단독 '잘못입니다' 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제12호증 계약서 작성일자가 공란이라는 상대방의 지적은 명백한 잘못입니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 지적 인용 후 단독 '잘못입니다' 반박은 결함으로 잡지 않아야 함: {findings}"


def test_control_standalone_wrong_refutation_4():
    """대조군 30 (TK-81 잔여): 상대방 주장 관형형 + 단독 '잘못된 판단' 반박 정상 진술 보호 (오탐 0건)."""
    doc = _make_doc([
        "준비서면",
        "갑 제13호증의 중요 내용이 식별 불가라는 상대측의 주장은 사실을 오인한 잘못된 판단입니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 0, f"상대방 주장 인용 후 단독 '잘못된' 반박은 결함으로 잡지 않아야 함: {findings}"


def test_positive_defect_retention_loss_admission():
    """양성 시험 21 (TK-81 잔여 요구 1 보존): 자기 측 원본 분실 자인은 결함으로 정상 검출 유지."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제14호증 약정서의 원본을 분실하여 제출하지 못하므로 사본으로 갈음합니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1, f"자기 측 원본 분실 자인은 결함으로 정상 검출되어야 함: {findings}"
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_positive_defect_retention_bakke_only_copy():
    """양성 시험 22 (TK-81 잔여 요구 2 보존): '사본 밖에 + 제출 불가' 자인은 결함으로 정상 검출 유지."""
    doc = _make_doc([
        "준비서면",
        "원고는 갑 제15호증 영수증에 대하여 사본 밖에 소지하지 못하여 원본을 제출할 수 없습니다.",
        "원고 소송대리인 변호사 홍길동",
    ])
    findings = check_evidence_form_defects(doc)
    assert len(findings) == 1, f"사본 밖에 없어 원본 미제출 자인은 결함으로 정상 검출되어야 함: {findings}"
    assert findings[0].confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


def test_pipeline_entrypoint_tk81_standalone_wrong_refutation(monkeypatch, tmp_path):
    """실제 VerificationPipeline 진입점 시험 (TK-81 잔여 점검표 1항): 단독 틀립니다 반박 제외 및 실제 결함 검출 검증."""
    from packages.verification_engine import pipeline as pipeline_module

    doc = _make_doc([
        "준비서면",
        "2. 상대방 주장에 대한 반박",
        "원고는 갑 제20호증에 원본이 첨부되지 않았다는 피고의 지적은 명백히 틀립니다.",
        "또한 갑 제21호증 계약서 작성일자가 공란이라는 상대방의 주장은 명백한 잘못입니다.",
        "3. 원본 제출에 관한 진술",
        "다만 원고는 갑 제22호증 약정서의 원본을 분실하여 법원에 제출하지 못하므로 사본으로 원용합니다.",
        "2026. 1. 20.",
        "원고 소송대리인 변호사 홍길동",
        "서울중앙지방법원 귀중",
    ], doc_id="entry_tk81_doc")

    monkeypatch.setattr(pipeline_module, "parse_document", lambda path, **kw: doc)
    monkeypatch.setattr(pipeline_module, "PseudonymStore", lambda project_id, **kw: PseudonymStore(project_id, root=tmp_path))

    pipeline = VerificationPipeline()
    result = pipeline.run(
        "run-entry-tk81-test",
        ProjectContext("proj-tk81-test"),
        [DocumentInput("entry_tk81_doc", "dummy.pdf", "dummy.pdf")],
    )

    doc_result = result.documents[0]
    form_findings = [f for f in doc_result.findings if f.type == FindingType.EVIDENCE_FORM_DEFECT.value]

    # 반박 문장(갑 20호증, 갑 21호증)은 제외되고 오직 실제 분실 자인(갑 22호증) 1건만 검출되어야 함
    assert len(form_findings) == 1, f"기대 1건(갑 제22호증 분실 자인), 실측 {len(form_findings)}건: {form_findings}"
    finding = form_findings[0]
    assert "갑 제22호증" in finding.title
    assert finding.status == VerificationStatus.CONTRADICTED.value
    assert finding.evidence_grade == EvidenceGrade.B.value
    assert finding.confidence_features.get("defect_code") == "UNSUBMITTED_EVIDENCE_ADMISSION"


