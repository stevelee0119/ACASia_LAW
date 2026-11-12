"""TK-153: 판결 전문의 번호 붙은 의견 머리말과 쟁점 한정 판결요지 표지.

공식 판결 전문은 '…의 반대의견은 다음과 같다' 대신 '8. …의 점에 관한 대법관 …의 반대의견'처럼 머리말만 두고
본문을 잇는 꼴이 많다(국가법령정보 응답의 <br/>은 공백으로 바뀐다). 판결 문장은 모두 합성이다.
"""
from __future__ import annotations

from packages.common.enums import CitationType, EvidenceGrade, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.opinion_attribution import opinion_ranges, quote_opinion, split_opinions

MAJ = "임대인은 임차인이 지출한 필요비를 지체 없이 상환하여야 한다."
DIS = "임차인이 미리 알리지 않고 지출한 비용은 상환 대상이 아니라고 보아야 한다."
CON = "필요비 상환의무의 근거는 신의칙이 아니라 계약의 해석에서 찾아야 한다."
SUP = "다수의견의 논거를 보충한다."
DSUP = "반대의견의 논거를 보충한다."

# 판결 끝 일치 문장(문장 속 언급) 뒤에 번호 붙은 머리말이 공백만 두고 이어진다.
FULL = (f"【이유】 상고이유를 판단한다. 1. {MAJ} 그러므로 상고를 기각한다. 이 판결에는 갑 부분에 관한 대법관 갑의 "
        f"별개의견, 을 부분에 관한 대법관 을, 대법관 병의 반대의견이 있는 외에는 관여 법관의 의견이 일치하였고, "
        f"다수의견에 대한 대법관 정의 보충의견이 있다.   "
        f"7. 대법관 갑의 별개의견   가. {CON}   "
        f"8. 피고인 1에 대한 무고의 점에 관한 대법관 을, 대법관 병의 반대의견   {DIS}   "
        f"9. 대법관 을의 반대의견에 대한 대법관 병의 보충의견   {DSUP}   "
        f"10. 다수의견에 대한 대법관 정의 보충의견   {SUP}  대법원장 무(재판장)")

SUMMARY = (f"[1] [다수의견] {MAJ}   [피고인 갑에 대한 무고의 점에 관한 대법관 을, 대법관 병의 반대의견] {DIS}")


def test_numbered_headings_split_sections():
    parts = split_opinions(FULL)
    assert MAJ in parts["MAJORITY"] and "의견이 일치하였고" in parts["MAJORITY"]
    assert len(parts["CONCURRING"]) == 1 and CON in parts["CONCURRING"][0]
    assert len(parts["DISSENT"]) == 2 and DIS in parts["DISSENT"][0] and DSUP in parts["DISSENT"][1]
    assert len(parts["SUPPLEMENTARY"]) == 1 and SUP in parts["SUPPLEMENTARY"][0]
    assert [k for _, _, k in opinion_ranges(FULL)] == ["MAJORITY", "CONCURRING", "DISSENT", "DISSENT", "MAJORITY"]


def test_mentions_inside_sentences_are_not_headings():
    for text in (
        "이 판결에는 갑 부분에 관한 대법관 갑의 반대의견이 있는 외에는 관여 법관의 의견이 일치하였다.",
        "이 판결에는 대법관 갑의 별개의견, 대법관 을의 반대의견과 대법관 병의 보충의견이 있다.",
        "3. 대법관 갑의 반대의견에 대하여 본다. 반대의견은 받아들일 수 없다.",
        "(대법원 2011. 4. 28. 선고 2010도1 판결 등 참조) 2. 반대의견 등에 대한 판단",
    ):
        assert opinion_ranges("【이유】 " + text) == [(0, len("【이유】 " + text), "MAJORITY")], text


def test_scoped_summary_bracket_is_a_dissent_marker():
    parts = split_opinions(SUMMARY)
    assert MAJ in parts["MAJORITY"] and len(parts["DISSENT"]) == 1 and DIS in parts["DISSENT"][0]


def test_quote_opinion_uses_numbered_headings():
    assert quote_opinion(MAJ, FULL) == "MAJORITY"
    assert quote_opinion(DIS, FULL) == "DISSENT"
    assert quote_opinion(CON, FULL) == "CONCURRING"
    assert quote_opinion(SUP, FULL) == "MAJORITY"


def citation(quoted):
    c = Citation.create(type=CitationType.CASE, raw_text="대법원 2099. 1. 1. 선고 2099도1 전원합의체 판결",
                        document_id="d1", quoted_text=quoted)
    c.context = f"위 판결의 다수의견은 '{quoted}'라고 설시하였다."
    c.attributes["case_claim"] = c.context
    return c


def _mis(quoted, record):
    from packages.legal_engine.verifier import LegalVerifier
    return [f for f in LegalVerifier._opinion_findings(citation(quoted), record)
            if f.confidence_features["verdict_label"] == "MISATTRIBUTED_OPINION"]


def test_dissent_quote_under_numbered_heading_is_misattributed_grade_a():
    [mis] = _mis(DIS, {"full_text": FULL})
    assert mis.status == VerificationStatus.CONTRADICTED and mis.evidence_grade == EvidenceGrade.A


def test_majority_quote_under_numbered_headings_is_not_flagged():
    assert not _mis(MAJ, {"full_text": FULL, "summary": SUMMARY})
    assert not _mis(SUP, {"full_text": FULL})
