"""TK-240 unit tests: quote attribution guard against A-grade false positives on reported opponent quotes."""
from __future__ import annotations

from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Citation, CitationType
from packages.legal_engine.verifier import LegalVerifier
from packages.source_adapters.base import AdapterResponse, AdapterStatus
from packages.source_adapters.registry import SourceRegistry


def _make_verifier(official_text: str) -> LegalVerifier:
    class _StubLaw:
        name = "law_go_kr"
        def status(self):
            return AdapterStatus.READY
        def search_case(self, case_number, court=None):
            rec = {
                "case_number": case_number,
                "court": "대법원",
                "decision_date": "2020-01-15",
                "holding": official_text,
                "summary": official_text,
                "full_text": official_text,
            }
            return AdapterResponse(AdapterStatus.READY, [rec], None, "ok")
        def fetch_case(self, rec, constitutional=False):
            return AdapterResponse(AdapterStatus.READY, [rec], None, "ok")
        def search_law(self, *a, **kw):
            return AdapterResponse(AdapterStatus.READY, [], None, "")
        def search_ordinance(self, *a, **kw):
            return AdapterResponse(AdapterStatus.READY, [], None, "")

    reg = SourceRegistry()
    reg.legal = [_StubLaw()]
    return LegalVerifier(registry=reg)


def _verify_quote(context: str, quoted: str, official_text: str):
    verifier = _make_verifier(official_text)
    cit = Citation(
        citation_id="c1",
        type=CitationType.CASE,
        raw_text="대법원 2021다99001 판결",
        case_number="2021다99001",
        quoted_text=quoted,
        context=context,
        document_id="d1",
        block_id="b1",
        page=1,
        span=[0, len(quoted)],
    )
    return verifier.verify_case(cit)


def test_tk240_pos1_author_own_mismatched_quote_raises_a_grade():
    """양성 1: 작성자 본인의 직접 인용이 공식 원문과 다르면 A등급 CONTRADICTED 경고를 유지한다."""
    official = "매도인은 계약 해제 통지 후 원상회복 의무를 부담한다."
    ctx = '원고는 대법원 2021다99001 판결에서 "매도인은 계약 해제 통지 후 원상회복 의무를 부담하지 않는다."고 판시하였음을 근거로 청구합니다.'
    verdict = _verify_quote(ctx, "매도인은 계약 해제 통지 후 원상회복 의무를 부담하지 않는다.", official)
    assert verdict.status == VerificationStatus.CONTRADICTED
    qm = [f for f in verdict.findings if f.type == FindingType.CASE_QUOTE_MISMATCH]
    assert qm and qm[0].evidence_grade == EvidenceGrade.A and qm[0].advisory_only is False


def test_tk240_pos2_reported_then_adopted_by_author_raises_a_grade():
    """양성 2: 상대방 주장을 적고 결론에서 자기 주장으로 채택한 회피 문형은 A등급 확정 경고를 유지한다."""
    official = "임차인의 유익비 상환청구권은 임대차 종료 시에 발생한다."
    ctx = (
        '피고는 대법원 2021다99001 판결이 "임차인의 유익비 상환청구권은 임대차 종료 시에도 발생하지 않는다."고 주장한다. '
        "따라서 본 소송대리인도 같은 취지에서 피고의 주장이 타당하고 즉시 적용되어야 한다고 본다."
    )
    verdict = _verify_quote(ctx, "임차인의 유익비 상환청구권은 임대차 종료 시에도 발생하지 않는다.", official)
    assert verdict.status == VerificationStatus.CONTRADICTED
    qm = [f for f in verdict.findings if f.type == FindingType.CASE_QUOTE_MISMATCH]
    assert qm and qm[0].evidence_grade == EvidenceGrade.A and qm[0].advisory_only is False


def test_tk240_pos3_author_modified_quote_raises_a_grade():
    """양성 3: 작성자 본인 주장의 핵심 어절 변형(수치·정도 변경)도 A등급 경고를 유지한다."""
    official = "지연손해금은 연 5%의 비율로 산정함이 타당하다."
    ctx = '대법원 2021다99001 판결은 "지연손해금은 연 20%의 비율로 산정함이 타당하다."고 명시하였다.'
    verdict = _verify_quote(ctx, "지연손해금은 연 20%의 비율로 산정함이 타당하다.", official)
    assert verdict.status == VerificationStatus.CONTRADICTED
    qm = [f for f in verdict.findings if f.type == FindingType.CASE_QUOTE_MISMATCH]
    assert qm and qm[0].evidence_grade == EvidenceGrade.A


def test_tk240_ctrl1_opponent_reported_and_rebutted_no_a_grade():
    """대조 1: 상대방 주장을 전언하고 이어서 부인·반박한 인용은 A등급 확정 경고를 올리지 않는다."""
    official = "손해배상 책임의 범위는 상당인과관계 있는 손해에 한한다."
    ctx = (
        '피고는 대법원 2021다99001 판결이 "모든 간접 손해까지 무제한으로 배상하여야 한다."는 취지로 판시했다고 주장한다. '
        "그러나 이는 위 판결의 취지와 다릅니다."
    )
    verdict = _verify_quote(ctx, "모든 간접 손해까지 무제한으로 배상하여야 한다.", official)
    assert verdict.status != VerificationStatus.CONTRADICTED
    assert not any(
        f.type == FindingType.CASE_QUOTE_MISMATCH and f.evidence_grade == EvidenceGrade.A
        for f in verdict.findings
    )
    assert all(f.advisory_only for f in verdict.findings if f.type == FindingType.CASE_QUOTE_MISMATCH)


def test_tk240_ctrl2_concessive_opponent_report_no_a_grade():
    """대조 2: '~라고 주장하나' 양보형 전언 인용은 A등급 확정 경고를 올리지 않는다."""
    official = "법정대리인의 동의 없는 미성년자 법률행위는 취소할 수 있다."
    ctx = '상대방 측은 대법원 2021다99001 판결을 들어 "미성년자 법률행위라도 언제나 확정적으로 유효하다."라고 주장하나, 이유 없다.'
    verdict = _verify_quote(ctx, "미성년자 법률행위라도 언제나 확정적으로 유효하다.", official)
    assert verdict.status != VerificationStatus.CONTRADICTED
    assert not any(
        f.type == FindingType.CASE_QUOTE_MISMATCH and f.evidence_grade == EvidenceGrade.A
        for f in verdict.findings
    )


def test_tk240_ctrl3_exact_quote_verified_no_finding():
    """대조 3: 공식 원문과 일치하는 정확 인용은 VERIFIED이며 경고가 없다."""
    official = "채무불이행으로 인한 손해배상액은 통상손해를 한도로 한다."
    ctx = '대법원 2021다99001 판결은 "채무불이행으로 인한 손해배상액은 통상손해를 한도로 한다."고 판시하였다.'
    verdict = _verify_quote(ctx, "채무불이행으로 인한 손해배상액은 통상손해를 한도로 한다.", official)
    assert verdict.status == VerificationStatus.VERIFIED
    assert not any(f.type == FindingType.CASE_QUOTE_MISMATCH for f in verdict.findings)
