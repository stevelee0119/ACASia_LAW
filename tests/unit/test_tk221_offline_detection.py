"""TK-221 오프라인 탐지 개선(ClauseNormalizer 승격, CIT-META, EVI-LOGIC, EVI-OVR, AIGEN) 단위 시험."""
from __future__ import annotations

from types import SimpleNamespace
import asyncio

from packages.claim_engine.evidence_consistency import check_evidence_overreach, check_reasoning_structure
from packages.common.config import get_settings
from packages.common.enums import CitationType, EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Block, Citation, NormalizedDocument, Page
from packages.legal_engine.citation_format import format_violations
from packages.legal_engine.polarity import ASSERTED, CONDITIONAL, NEGATED, REPORTED, polarity
from packages.legal_engine.verifier import CitationVerdict, LegalVerifier
from packages.verification_engine.ai_document_detector import detect_ai_document
from packages.verification_engine.ai_residue import scan_residue


def _doc(text: str, *, doc_id: str = "doc-1", metadata: dict | None = None) -> NormalizedDocument:
    return NormalizedDocument(
        document_id=doc_id,
        filename="sample.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[Block(block_id="b1", page=1, text=text, block_type="paragraph")])],
        metadata=metadata or {},
    )


# 1. ClauseNormalizer default promotion
def test_clause_normalizer_promoted_to_default() -> None:
    settings = get_settings()
    assert settings.use_clause_normalizer == "default"
    # 양성 3건: 이중부정 단정, 상대방 주장 전달, 가정 조건
    assert polarity("피고가 채무를 변제하지 않은 것은 아니다.", (0, 9)) == ASSERTED
    assert polarity("원고는 계약이 무효라고 주장하나 이유 없다.", (4, 11)) == REPORTED
    assert polarity("가사 계약이 체결되었다고 가정하더라도 효력이 없다.", (3, 13)) == CONDITIONAL
    # 대조군 3건: 단일 부정, 단순 단정, 일반 과거 사실
    assert polarity("피고는 대금을 지급하지 않았다.", (0, 10)) == NEGATED
    assert polarity("원고는 약정일에 물품을 인도하였다.", (0, 18)) == ASSERTED
    assert polarity("계약서는 적법하게 작성되었다.", (0, 15)) == ASSERTED


# 2. CIT-META: 재판유형-부호 불일치 & 문서 내 동일 사건번호 메타 모순
def test_trial_kind_mismatch_positive_and_negative() -> None:
    positives = [
        Citation(citation_id="c1", type=CitationType.CONSTITUTIONAL, raw_text="헌법재판소 2020. 5. 14. 선고 2019헌마123 판결",
                 court="헌법재판소", case_number="2019헌마123", canonical_case_number="2019헌마123", case_kind="판결"),
        Citation(citation_id="c2", type=CitationType.CASE, raw_text="대법원 2021. 3. 11. 선고 2020마456 판결",
                 court="대법원", case_number="2020마456", canonical_case_number="2020마456", case_kind="판결"),
        Citation(citation_id="c3", type=CitationType.CASE, raw_text="대법원 2022. 1. 20. 자 2021다789 결정",
                 court="대법원", case_number="2021다789", canonical_case_number="2021다789", case_kind="결정"),
    ]
    for cit in positives:
        viols = format_violations(cit)
        assert any(v["rule_id"] == "FMT.TRIAL_KIND_MISMATCH" for v in viols), cit.raw_text

    negatives = [
        Citation(citation_id="n1", type=CitationType.CONSTITUTIONAL, raw_text="헌법재판소 2020. 5. 14. 자 2019헌마123 결정",
                 court="헌법재판소", case_number="2019헌마123", canonical_case_number="2019헌마123", case_kind="결정"),
        Citation(citation_id="n2", type=CitationType.CASE, raw_text="대법원 2022. 1. 20. 선고 2021다789 판결",
                 court="대법원", case_number="2021다789", canonical_case_number="2021다789", case_kind="판결"),
        Citation(citation_id="n3", type=CitationType.CASE, raw_text="서울중앙지방법원 2021. 7. 1. 선고 2020가합100 판결",
                 court="서울중앙지방법원", case_number="2020가합100", canonical_case_number="2020가합100", case_kind="판결"),
    ]
    for cit in negatives:
        viols = format_violations(cit)
        assert not any(v["rule_id"] == "FMT.TRIAL_KIND_MISMATCH" for v in viols), cit.raw_text


def test_internal_citation_meta_conflict_positive_and_negative() -> None:
    # 양성 3건: 선고일 불일치, 법원 불일치, 둘 다 불일치
    for case_no, (court1, date1), (court2, date2) in [
        ("2020다11111", ("대법원", "2020-05-14"), ("대법원", "2021-03-11")),
        ("2020나22222", ("서울고등법원", "2020-06-01"), ("부산고등법원", "2020-06-01")),
        ("2021도33333", ("대법원", "2021-08-12"), ("서울고등법원", "2022-01-10")),
    ]:
        v1 = CitationVerdict(
            Citation(citation_id="a1", document_id="d1", type=CitationType.CASE, raw_text=case_no,
                     case_number=case_no, canonical_case_number=case_no, court=court1, decision_date=date1),
            VerificationStatus.NOT_FOUND,
        )
        v2 = CitationVerdict(
            Citation(citation_id="a2", document_id="d1", type=CitationType.CASE, raw_text=case_no,
                     case_number=case_no, canonical_case_number=case_no, court=court2, decision_date=date2),
            VerificationStatus.NOT_FOUND,
        )
        LegalVerifier._check_internal_citation_meta_conflicts([v1, v2])
        findings = v1.findings + v2.findings
        assert any(f.type == FindingType.CASE_METADATA_MISMATCH for f in findings)

    # 대조군 3건: 동일 메타, 서로 다른 사건번호, 대법원 vs 대법원 전원합의체 부분문자열
    for (c1, n1, ct1, dt1), (c2, n2, ct2, dt2) in [
        (("k1", "2020다11111", "대법원", "2020-05-14"), ("k2", "2020다11111", "대법원", "2020-05-14")),
        (("k3", "2020다11111", "대법원", "2020-05-14"), ("k4", "2020나99999", "서울고등법원", "2020-01-10")),
        (("k5", "2020다11111", "대법원", "2020-05-14"), ("k6", "2020다11111", "대법원 전원합의체", "2020-05-14")),
    ]:
        v1 = CitationVerdict(
            Citation(citation_id=c1, document_id="d2", type=CitationType.CASE, raw_text=n1,
                     case_number=n1, canonical_case_number=n1, court=ct1, decision_date=dt1),
            VerificationStatus.NOT_FOUND,
        )
        v2 = CitationVerdict(
            Citation(citation_id=c2, document_id="d2", type=CitationType.CASE, raw_text=n2,
                     case_number=n2, canonical_case_number=n2, court=ct2, decision_date=dt2),
            VerificationStatus.NOT_FOUND,
        )
        LegalVerifier._check_internal_citation_meta_conflicts([v1, v2])
        assert not (v1.findings + v2.findings)


# 3. EVI-LOGIC: 명시적 부재/불능 표지 + 직접 지각 모순
def test_evi_logic_explicit_absence_positive_and_control() -> None:
    positives = [
        "당시 저는 현장에 없었습니다. 같은 시각 피고가 서명하는 것을 직접 보았습니다.",
        "그날 저는 해외 체류 중이었습니다. 당시 대화 내용을 현장에서 직접 들었습니다.",
        "사건 당일 저는 병원에 입원 중이었습니다. 같은 시간 상황을 두 눈으로 직접 목격했습니다.",
    ]
    for text in positives:
        findings = check_reasoning_structure(_doc(text))
        assert any(f.type == FindingType.STATEMENT_BEYOND_PERCEPTION for f in findings), text

    controls = [
        "당시 저는 편의점 앞에 있었습니다. 그때 두 사람이 다투는 장면을 직접 보았습니다.",
        "당시 저는 현장에 없었습니다. 이틀 뒤에 CCTV 영상을 통해 상황을 보았습니다.",
        "제 동생은 당시 현장에 없었습니다. 저는 같은 시각 현장에서 직접 보았습니다.",
    ]
    for text in controls:
        findings = check_reasoning_structure(_doc(text))
        assert not any(f.type == FindingType.STATEMENT_BEYOND_PERCEPTION for f in findings), text


# 4. EVI-OVR: 진단상태/진술확인 직접 증명 과장 시 SUSPICIOUS 판정 (발신인 불명 통지 제외)
def test_evi_ovr_direct_proof_suspicious_and_controls() -> None:
    positives = [
        ("상해진단서(갑 제1호증)에 의하여 피고가 고의로 상해를 가한 사실이 직접 입증됩니다.", "1. 갑 제1호증 상해진단서"),
        ("사실확인서(갑 제2호증)로써 원고에게 소유권이 확정적으로 귀속되었음이 직접 증명됩니다.", "1. 갑 제2호증 사실확인서"),
        ("진료기록부(갑 제3호증)에 따라 상대방의 가해 의도가 명백히 입증됩니다.", "1. 갑 제3호증 진료기록부"),
    ]
    for body, ev_line in positives:
        doc = _doc(f"증거목록\n{ev_line}\n\n{body}")
        ovr = [f for f in check_evidence_overreach(doc) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
        assert ovr, body
        assert ovr[0].evidence_grade == EvidenceGrade.C
        assert ovr[0].status == VerificationStatus.SUSPICIOUS

    # 대조군: 발신인 불명 내용증명은 기존 계약대로 UNVERIFIED 유지, 정당한 사실 입증은 오탐 0
    doc_notice = _doc("증거목록\n1. 갑 제4호증 내용증명\n\n내용증명(갑 제4호증)에 의하여 피고가 채무를 승인하였음이 입증됩니다.")
    ovr_notice = [f for f in check_evidence_overreach(doc_notice) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert ovr_notice and ovr_notice[0].status == VerificationStatus.UNVERIFIED

    for safe_body, safe_ev in [
        ("상해진단서(갑 제5호증)에 의하여 원고가 치료를 받은 사실이 확인됩니다.", "1. 갑 제5호증 상해진단서"),
        ("영수증(갑 제6호증)에 의하여 일부 금원을 지급한 사실이 인정됩니다.", "1. 갑 제6호증 영수증"),
    ]:
        doc_safe = _doc(f"증거목록\n{safe_ev}\n\n{safe_body}")
        assert not [f for f in check_evidence_overreach(doc_safe) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]


# 5. AIGEN: 미치환 플레이스홀더 및 복합 정황
def test_aigen_placeholder_and_control() -> None:
    # 양성: 서로 다른 2종 이상의 미치환 초안 입력 표기
    res = scan_residue("피고는 [성명 입력]에게 [날짜 기재]까지 금원을 지급하여야 합니다.")
    assert any(r.category == "PLACEHOLDER" and r.reportable for r in res)

    # 대조군: 단일 괄호 표기 또는 일반 법률 서면은 PLACEHOLDER 미탐지
    assert not any(r.category == "PLACEHOLDER" for r in scan_residue("별지 [목록] 기재 부동산에 관하여 청구합니다."))
    assert not any(r.category == "PLACEHOLDER" for r in scan_residue("원고는 피고와 매매계약을 체결하였습니다."))

    # 복합 정황(성립 불가능 사건번호 2건 + 문체 신호)
    doc = _doc(
        "요약하자면 본 사안은 중요합니다. 결론적으로 핵심은 다음과 같습니다. 단계적으로 살펴보겠습니다. "
        "원고는 대법원 2099다99999 판결 및 대법원 2098다88888 판결에 따라 주장합니다."
    )
    impossible_findings = [
        SimpleNamespace(
            type=FindingType.CASE_NOT_FOUND,
            status=VerificationStatus.NOT_FOUND,
            confidence_features={"case_number": "2099다99999"},
        ),
        SimpleNamespace(
            type=FindingType.CASE_NOT_FOUND,
            status=VerificationStatus.NOT_FOUND,
            confidence_features={"case_number": "2098다88888"},
        ),
    ]
    ai_res = asyncio.run(detect_ai_document(doc, impossible_findings, router=None))
    assert ai_res.verdict == "AI_PARTIAL_GENERATION"
