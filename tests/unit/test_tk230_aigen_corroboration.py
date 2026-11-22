"""TK-230: Objective AI residue corroboration for co-occurring style residue signals."""
from __future__ import annotations

from types import SimpleNamespace

from packages.common.enums import EvidenceGrade, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.verification_engine.ai_document_detector import create_ai_detector_findings, detect_ai_document


def _doc(text: str, doc_id: str = "D1") -> NormalizedDocument:
    return NormalizedDocument(
        document_id=doc_id,
        filename="brief.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        parser_name="test",
        pages=[Page(page_number=1, blocks=[Block(block_id="B1", text=text, page=1)])],
    )


def _offline_router():
    return SimpleNamespace(has_available_provider=lambda **_kw: False)


def _run_findings(text: str):
    import asyncio
    doc = _doc(text)
    res = asyncio.run(detect_ai_document(doc, [], router=_offline_router()))
    return create_ai_detector_findings(doc, res)


# ---------------------------------------------------------------------------
# Positive cases (>= 3): >= 2 objective AI residues corroborate style signals
# ---------------------------------------------------------------------------


def test_tk230_pos1_preface_and_cutoff_corroborate_disclaimer_and_english_gloss() -> None:
    """Conversational preface + knowledge cutoff (>=2 objective) elevate disclaimer & English gloss to SUSPICIOUS/B."""
    text = (
        "물론입니다! 요청하신 내용을 바탕으로 소장을 작성해 드리겠습니다.\n"
        "제 지식 기준일 현재 신의성실의 원칙(good faith principle)과 비례원칙(proportionality principle)이 적용됩니다.\n"
        "본 답변은 법률 자문을 대체하지 않습니다.\n"
    )
    findings = _run_findings(text)
    style = [f for f in findings if (f.confidence_features or {}).get("objective") is False]
    assert len(style) >= 2
    for f in style:
        assert f.status == VerificationStatus.SUSPICIOUS
        assert f.evidence_grade == EvidenceGrade.B
        assert f.confidence_features["corroborated_by_objective_residue"] is True


def test_tk230_pos2_preface_and_cutoff_corroborate_boilerplate() -> None:
    """Conversational preface + knowledge cutoff (>=2 objective) elevate co-occurring AI boilerplate to SUSPICIOUS/B."""
    text = (
        "물론입니다! 요청하신 내용을 바탕으로 준비서면을 작성해 드리겠습니다.\n"
        "제 지식 기준일 현재 결론적으로, 중요한 점은 종합적으로 볼 때 피고의 주의의무 위반이 인정된다고 할 수 있습니다.\n"
    )
    findings = _run_findings(text)
    style = [f for f in findings if (f.confidence_features or {}).get("objective") is False]
    assert style
    assert all(f.status == VerificationStatus.SUSPICIOUS for f in style)
    assert all(f.evidence_grade == EvidenceGrade.B for f in style)


def test_tk230_pos3_preface_and_cutoff_corroborate_english_parenthetical() -> None:
    """Conversational preface + knowledge cutoff (>=2 objective) elevate English parenthetical to SUSPICIOUS/B."""
    text = (
        "물론입니다! 요청하신 내용을 바탕으로 검토서를 작성해 드리겠습니다.\n"
        "제 지식 기준일 현재 해당 쟁점은 적법절차(due process) 및 재량권 남용(abuse of discretion) 여부가 핵심입니다.\n"
    )
    findings = _run_findings(text)
    style = [f for f in findings if (f.confidence_features or {}).get("objective") is False]
    assert style
    assert all(f.status == VerificationStatus.SUSPICIOUS for f in style)
    assert all(f.evidence_grade == EvidenceGrade.B for f in style)


# ---------------------------------------------------------------------------
# Control cases (>= 3): human briefs with 0 or 1 objective residue stay UNVERIFIED/C
# ---------------------------------------------------------------------------


def test_tk230_ctrl1_human_brief_with_boilerplate_only_stays_unverified() -> None:
    """Human-written brief with transitional phrases and 0 objective AI residues stays UNVERIFIED/C."""
    text = (
        "1. 사실관계\n"
        "원고는 피고와 매매계약을 체결하였습니다.\n"
        "종합적으로 볼 때, 결론적으로 피고의 채무불이행 책임이 인정됩니다.\n"
    )
    findings = _run_findings(text)
    style = [f for f in findings if (f.confidence_features or {}).get("objective") is False]
    assert all(f.status == VerificationStatus.UNVERIFIED for f in style)
    assert all(f.evidence_grade == EvidenceGrade.C for f in style)
    assert all(f.confidence_features["corroborated_by_objective_residue"] is False for f in style)


def test_tk230_ctrl2_human_brief_with_english_legal_term_stays_unverified() -> None:
    """Human-written brief citing an English legal term in parentheses without objective residues stays UNVERIFIED."""
    text = (
        "계약 해석에 있어 사정변경의 원칙(rebus sic stantibus)과 신의칙(good faith)이 적용되어야 합니다.\n"
    )
    findings = _run_findings(text)
    style = [f for f in findings if (f.confidence_features or {}).get("objective") is False]
    assert all(f.status == VerificationStatus.UNVERIFIED for f in style)
    assert all(f.evidence_grade == EvidenceGrade.C for f in style)


def test_tk230_ctrl3_single_objective_residue_does_not_elevate_style_signals() -> None:
    """A single objective residue (e.g. one placeholder) is insufficient to elevate style signals."""
    text = (
        "원고는 [날짜] 체결된 계약에 기하여 청구를 유지합니다.\n"
        "결론적으로 원고의 청구는 이유 있습니다.\n"
    )
    findings = _run_findings(text)
    style = [f for f in findings if (f.confidence_features or {}).get("objective") is False]
    assert all(f.status == VerificationStatus.UNVERIFIED for f in style)
    assert all(f.confidence_features["corroborated_by_objective_residue"] is False for f in style)
