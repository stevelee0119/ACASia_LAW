"""평가 측 공개 시험 — LV-01~06 보완(11-11). 평가 측 탐침과 다른 공개 합성 문장이다.
기준 d8af690(#257 head)에서 실패, 평가 측 사본에서 통과(변별 확인)."""
import time

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.legal_engine.legal_rules import _calculate_dynamic_deadline
from packages.legal_engine.quote_diff import categorize_quote_diff
from packages.legal_engine import opinion_attribution as oa
from packages.legal_engine.actionable_guidance import CAUSE_OF_ACTION_RULES


def _doc(text):
    return NormalizedDocument("d", "d.txt", "text/plain", "0", [Page(1, 100.0, 100.0, [Block("b1", text, 1)])])


CLAIM = "이의신청 결과를 통보받아 제소기간 90일이 진행하므로 기산점은 통보일이어야 합니다."


# E1 LV-01: '처분이 있은 날'(행정소송법 제20조 제2항)과 '처분이 있음을 안 날'(같은 조 제1항)은 다른 역할이다
def test_e1_disposition_and_awareness_are_separate_roles():
    text = ("처분이 있은 날: 2023. 9. 4.\n처분이 있음을 안 날: 2023. 9. 11.\n"
            "원고는 2023. 10. 2. 결과를 통보받았습니다.\n소제기일: 2023. 12. 1.\n")
    out = _calculate_dynamic_deadline(_doc(text), CLAIM)
    assert "상충" not in out
    assert "처분을 안 날(2023. 9. 11.) 기준: 81일 경과" in out


# E2 LV-01: 재결서 정본 송달일(같은 조 제1항 단서)을 '이의신청 통보일'로 표시하지 않는다
def test_e2_adjudication_service_label():
    text = "원고는 2023. 6. 1. 처분을 받고 행정심판을 청구하여 2023. 8. 7. 재결서 정본을 송달받았습니다.\n소제기일: 2023. 9. 20.\n"
    out = _calculate_dynamic_deadline(_doc(text), "재결서 송달일부터 제소기간 90일이 진행합니다.")
    assert "재결서 송달일(2023. 8. 7.)" in out


# E3 LV-01: 서술형 소제기('이 사건 소를 제기하였습니다')도 소제기일이다
def test_e3_narrative_filing_sentence():
    text = "원고는 2023. 3. 6. 처분을 고지받고 2023. 3. 27. 결과를 통보받았습니다.\n원고는 2023. 5. 2. 이 사건 소를 제기하였습니다.\n"
    out = _calculate_dynamic_deadline(_doc(text), CLAIM)
    assert "[실제 일수 동적 계산]" in out and "(소제기일: 2023. 5. 2.)" in out


OFFICIAL = ("임대인은 임차인이 차임을 두 번 연체한 때에는 계약을 해지할 수 있다. "
            "그러나 임차인이 연체 차임을 모두 지급한 경우에는 해지권을 행사할 수 없다.")


# E4 LV-04: 창 끝 어절의 조사 차이를 주어·객체 바뀜으로, 부정 활용 차이를 부정어 변경으로 보지 않는다
def test_e4_boundary_particle_and_negation_inflection_are_not_meaningful():
    r1 = categorize_quote_diff("임대인이 임차인이 차임을 두 번 연체한 때에는 계약을 해지할 수 있다", OFFICIAL)
    assert "PARTY_SWAP" not in r1["diff_categories"]
    r2 = categorize_quote_diff("임차인이 연체 차임을 모두 지급한 경우에는 해지권을 행사할 수 없는 것이다", OFFICIAL)
    assert "NEGATION" not in r2["diff_categories"]


# E5 LV-04: 끝 어절의 부정 반전('없다'→'있다')은 부정어 변경이다
def test_e5_final_negation_flip_is_negation():
    r = categorize_quote_diff("임차인이 연체 차임을 모두 지급한 경우에는 해지권을 행사할 수 있다", OFFICIAL)
    assert r["status"] == "MODIFIED_QUOTE" and "NEGATION" in r["diff_categories"]


# E6 LV-04: 생략 표시로 나눈 구간이 모두 원문과 같으면 변경이 아니다
def test_e6_ellipsis_quote_matching_segments_is_exact():
    r = categorize_quote_diff("임대인은 임차인이 차임을 … 연체한 때에는 계약을 해지할 수 있다", OFFICIAL)
    assert r["status"] == "EXACT_MATCH", r


NEW = ("보증채무의 소멸시효는 주채무가 확정된 때가 아니라 보증인이 이행청구를 받은 때부터 진행한다. "
       "이와 달리 보증채무의 소멸시효는 주채무가 확정된 때부터 진행한다고 판단한 대법원 1999. 3. 9. 선고 98다77777 판결 등은 "
       "이 판결의 견해에 배치되는 범위에서 이를 변경하기로 한다.")


# E7 LV-05: 실제 판결의 날짜 표기('1999. 3. 9. 선고')가 있어도 변경 판례 문장을 읽는다
def test_e7_changed_precedent_with_dated_case():
    r = oa.detect_changed_precedent_distortion("보증채무의 소멸시효는 주채무가 확정된 때부터 진행한다(대법원 2024다88888 전원합의체 판결).",
                                               NEW, "", "2024다88888")
    assert r and r["verdict"] == "CHANGED_PRECEDENT"


# E8 LV-05: 변경한 판결의 새 법리를 정확히 인용하면 왜곡이 아니다(극성이 같은 기산점 변경)
def test_e8_new_holding_is_not_changed_precedent():
    assert oa.detect_changed_precedent_distortion("보증채무의 소멸시효는 보증인이 이행청구를 받은 때부터 진행한다(대법원 2024다88888 전원합의체 판결).",
                                                  NEW, "", "2024다88888") is None


LOWER = ("원심은 이 사건 합의서가 피고를 구속하지 않는다고 판단하였다. "
         "그러나 이러한 원심의 판단에는 처분문서의 해석에 관한 법리를 오해한 위법이 있다.")


# E9 LV-05: 부정 명제인 원심 판단을 대법원 판시로 인용(끝에 괄호 인용 표시)해도 잡는다
def test_e9_reversed_remand_with_negated_holding_and_paren_citation():
    r = oa.detect_reversed_remand_confusion("대법원은 이 사건 합의서가 피고를 구속하지 않는다고 판단하였다(대법원 2022다99999 판결).", LOWER, "")
    assert r and r["verdict"] == "REVERSED_REMAND_CONFUSION"


# E10 LV-05: 원심 오인 정규식이 긴 한 줄 전문에서 이차 시간이 들지 않는다
def test_e10_reversed_remand_linear_time():
    big = "원심은 피고가 원고에게 대금을 지급할 의무가 있다고 판단하였다 " * 2000
    t = time.time()
    oa.detect_reversed_remand_confusion("대법원은 피고가 원고에게 대금을 지급할 의무가 있다고 판단하였다.", big, "")
    assert time.time() - t < 3.0


# E11 LV-06: 채무불이행 손해배상의 귀책사유는 원고의 요건사실이 아니다(민법 제390조 단서 — 채무자 항변)
def test_e11_fault_is_not_plaintiff_element_for_390():
    rule = next(r for r in CAUSE_OF_ACTION_RULES if "390" in r["trigger"].pattern)
    assert "귀책사유" not in [name for name, _ in rule["elements"]]


# E12~E14 TK-150(F10): 행정기본법 제36조 제4항·부칙 제6조 — 2023. 3. 24. 이후 처분은 이의신청 결과 통지일부터 90일이 가능하다
def _deadline_findings(text):
    from packages.legal_engine.legal_rules import review_legal_rules
    return [f for f in review_legal_rules(_doc(text))
            if (f.confidence_features or {}).get("rule_id") == "ADMIN.DEADLINE_CALCULATION_SCENARIOS"]


def test_e12_post_2023_disposition_is_not_contradicted():
    fs = _deadline_findings("청 구 원 인\n원고는 2025. 2. 10. 시정명령 처분을 받고 이의신청을 하여 2025. 2. 27. 결과를 통보받았습니다. " + CLAIM + "\n")
    assert fs and all(f.status.value == "SUSPICIOUS" and f.evidence_grade.value == "C" for f in fs)
    assert "행정기본법 제36조 제4항" in fs[0].detail


def test_e13_pre_2023_disposition_keeps_contradiction():
    fs = _deadline_findings("청 구 원 인\n원고는 2021. 7. 5. 시정명령 처분을 받고 이의신청을 하여 2021. 7. 22. 결과를 통보받았습니다. " + CLAIM + "\n")
    assert fs and fs[0].status.value == "CONTRADICTED" and fs[0].evidence_grade.value == "A"


def test_e14_unknown_disposition_date_asks_for_confirmation():
    fs = _deadline_findings("청 구 원 인\n원고는 시정명령 처분에 이의신청을 하여 결과를 통보받았습니다. " + CLAIM + "\n")
    assert fs and fs[0].status.value == "SUSPICIOUS" and "처분일을 문서에서 특정하지 못했다" in fs[0].detail


# E15 LV-04(F11): 당사자 맞바꿈은 같은 낱말 집합이라도 순서가 바뀐 것이다 — 순서로 견준다(문장 처음·중간)
def test_e15_party_swap_is_order_sensitive():
    off = "임차인은 임대인에게 차임을 지급할 의무가 있고 임대인은 임차인에게 목적물을 사용하게 할 의무가 있다."
    r1 = categorize_quote_diff("임대인은 임차인에게 차임을 지급할 의무가 있고 임대인은 임차인에게 목적물을 사용하게 할 의무가 있다", off)
    assert "PARTY_SWAP" in r1["diff_categories"], r1
    r2 = categorize_quote_diff("임차인은 임대인에게 차임을 지급할 의무가 있고 임대인은 임차인에게 목적물을 사용하게 할 의무가 있다", off)
    assert r2["status"] == "EXACT_MATCH", r2
