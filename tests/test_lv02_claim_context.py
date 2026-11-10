"""LV-02: 주장 문맥 보존 및 평가 발췌-표시 분리 단위 및 합성 시험.

규칙:
1. 인용 판례와 직접 연결된 문장 뒤에 단서('다만'), 예외('특별한 사정이 없는 한'), 조건, 부정이 오면
   200자 강제 절단 없이 최대 1,000자까지 평가 문맥(evaluation_context)으로 온전히 보존.
2. UI 및 보고서 행의 표시용 claim_text는 200자 이내로 단어 경계를 존중하여 요약.
3. 무관한 후속 단락은 evaluation_context에 포함하지 않음.
"""
from __future__ import annotations

from packages.common.enums import CitationType
from packages.common.schemas import Block, Page, NormalizedDocument, Citation
from packages.legal_engine.argument_validity_verifier import _extract_linked_claim, HallucinationTableRow


def _make_doc(text: str, doc_id: str = "lv02_doc") -> NormalizedDocument:
    b = Block("b1", text, 1)
    p = Page(1, 100.0, 100.0, [b])
    return NormalizedDocument(doc_id, f"{doc_id}.txt", "text/plain", "sha256", [p])


def _make_citation(raw_text: str, context: str, case_no: str = "") -> Citation:
    return Citation(
        citation_id="cit_1",
        type=CitationType.CASE,
        raw_text=raw_text,
        context=context,
        case_number=case_no,
        page=1,
    )


# --- 1. 양성 예시 3종 (단서·예외·접속문 문맥 보존 및 200자 초과 보존) ---

def test_lv02_positive_proviso_daman_preserved():
    """양성 1: '다만'으로 시작하는 후속 단서 문장이 evaluation_context에 온전히 포함."""
    raw = "대법원 2021. 5. 13. 선고 2020다12345 판결"
    s1 = (
        f"{raw}에 의하면, 계약 체결 이후 발생한 채무불이행 사태에 있어서 "
        "채권자의 이행청구가 상당한 기간 내에 도달한 이상 손해배상청구권이 성립한다고 봄이 상당합니다."
    )
    s2 = (
        "다만 채무자가 예측할 수 없었던 특별손해에 관하여는 채권자에게도 손해의 확대를 방지할 "
        "주의의무가 인정되므로 과실상계가 적극적으로 참작되어야 마땅합니다."
    )
    full_context = f"{s1} {s2}"
    assert len(full_context) > 200, "테스트 문맥이 200자보다 길어야 함"

    c = _make_citation(raw, full_context, "2020다12345")
    doc = _make_doc(full_context)

    extracted = _extract_linked_claim(c, doc, max_chars=1000)
    # 단서 문장('다만 ... 과실상계가 ...')이 잘리지 않고 보존되어야 함
    assert "다만 채무자가 예측할 수 없었던 특별손해" in extracted
    assert "과실상계가 적극적으로 참작되어야 마땅합니다." in extracted
    assert len(extracted) == len(full_context)


def test_lv02_positive_exception_phrase_preserved():
    """양성 2: '특별한 사정이 없는 한' 예외 조건 문장이 evaluation_context에 보존."""
    raw = "대법원 2019. 11. 14. 선고 2018다54321 판결"
    s1 = f"{raw}의 취지에 비추어 볼 때, 당사자 사이의 약정은 강행법규에 위배되지 않는 범위에서 유효합니다."
    s2 = "특별한 사정이 없는 한 일방 당사자가 계약상의 주된 급부의무를 위반한 경우에는 상대방은 최고 없이 즉시 해제권을 행사할 수 있습니다."
    full_context = f"{s1} {s2}"

    c = _make_citation(raw, full_context, "2018다54321")
    doc = _make_doc(full_context)

    extracted = _extract_linked_claim(c, doc, max_chars=1000)
    assert "특별한 사정이 없는 한" in extracted
    assert "즉시 해제권을 행사할 수 있습니다." in extracted


def test_lv02_positive_multiline_adversative_connective():
    """양성 3: 줄바꿈으로 이어진 다음 줄이 '그러나'로 시작할 때 결합 보존."""
    raw = "대법원 2016. 3. 24. 선고 2015다9876 판결"
    line1 = f"{raw}에 따르면 처분문서의 진정성립이 인정되면 그 기재 내용대로 의사표시의 존재가 증명됩니다."
    line2 = "그러나 반증이 있거나 문서 기재와 다른 명시적 합의가 입증된 경우에는 기재 내용과 다른 사실을 인정할 수 있습니다."
    context = f"{line1}\n{line2}"

    c = _make_citation(raw, context, "2015다9876")
    doc = _make_doc(context)

    extracted = _extract_linked_claim(c, doc, max_chars=1000)
    assert "그러나 반증이 있거나" in extracted
    assert "기재 내용과 다른 사실을 인정할 수 있습니다." in extracted


# --- 2. 대조군 3종 (무관한 문단 제외, 1000자 상한, UI 표시 분리) ---

def test_lv02_contrast_unrelated_next_paragraph_excluded():
    """대조군 1: 단서나 예외가 아닌 무관한 사실관계 다음 줄은 포함하지 않음."""
    raw = "대법원 2022. 1. 13. 선고 2021다11111 판결"
    line1 = f"{raw}에 따라 원고의 소유권 확인 청구는 이유 있습니다."
    line2 = "피고는 2023. 5. 10. 서울에 주소지를 두고 자동차를 운전하였습니다."
    context = f"{line1}\n{line2}"

    c = _make_citation(raw, context, "2021다11111")
    doc = _make_doc(context)

    extracted = _extract_linked_claim(c, doc, max_chars=1000)
    assert "원고의 소유권 확인 청구는 이유 있습니다." in extracted
    assert "자동차를 운전하였습니다" not in extracted


def test_lv02_contrast_max_chars_cap():
    """대조군 2: 1,000자를 넘는 극단적 장문은 max_chars(1000)에 맞추어 상한 제한."""
    raw = "대법원 2020. 2. 6. 선고 2019다22222 판결"
    long_tail = " 피고의 주장은 타당하지 않습니다." * 100  # 약 2,000자
    full_context = f"{raw}에 의하면 다음과 같습니다.{long_tail}"

    c = _make_citation(raw, full_context, "2019다22222")
    doc = _make_doc(full_context)

    extracted = _extract_linked_claim(c, doc, max_chars=1000)
    assert len(extracted) <= 1000


def test_lv02_contrast_display_summary_vs_evaluation_context():
    """대조군 3: HallucinationTableRow에서 claim_text는 200자 이내, evaluation_context는 전문 보존."""
    raw = "대법원 2023. 4. 27. 선고 2022다33333 판결"
    s1 = f"{raw}의 법리에 비추어 살펴보면, 원고의 청구는 계약상 의무 위반에 따른 손해배상책임의 성립요건을 모두 충족하고 있으므로 피고의 채무불이행에 기한 손해배상 의무가 전부 인정된다고 보아야 할 것입니다."
    s2 = "다만 피고는 천재지변에 준하는 불가항력적 사유로 인하여 일시적 이행지체가 발생하였음을 입증하였으므로 신의칙상 지연손해금의 상당한 감경을 구하는 바입니다."
    full_claim = f"{s1} {s2}"
    assert len(full_claim) > 200

    display_claim = full_claim if len(full_claim) <= 200 else (full_claim[:197] + "...")
    row = HallucinationTableRow(
        location="1면",
        claim_text=display_claim,
        cited_authority=raw,
        authority_exists=True,
        ai_generation_basis="",
        validity_verdict="타당",
        legal_reasoning="검토",
        recommended_counteraction="조치",
        evaluation_context=full_claim,
    )
    d = row.to_dict()
    # claim_text는 200자 이내 축약본
    assert len(d["claim_text"]) <= 200
    assert d["claim_text"].endswith("...")
    # evaluation_context는 단서가 온전히 보존된 전문
    assert "다만 피고는 천재지변에 준하는 불가항력적 사유" in d["evaluation_context"]
    assert len(d["evaluation_context"]) > 200
