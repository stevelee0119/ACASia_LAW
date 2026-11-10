"""TK-76 EVI-INCONS C 후속 T1 — 결과 제목의 대상 표시에 같은 낱말이 겹치지 않는다(평가 측 공개 합성 문장)."""
from __future__ import annotations

import re

import pytest

from packages.claim_engine.internal_inconsistency import check_internal_inconsistency
from packages.common.schemas import Block, NormalizedDocument, Page


def _titles(lines):
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(lines)]
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                             pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])
    return [f.title for f in check_internal_inconsistency(doc)
            if (f.confidence_features or {}).get("rule_id") == "EVI.INCONS_SAME_EVENT_DATETIME"]


def _target(title):
    m = re.search(r"동일 사건\(([^)]*)\)", title)
    return m.group(1) if m else ""


def test_no_repeated_word_when_head_nouns_differ():
    titles = _titles([
        "위원회는 2024. 3. 4. 처음이자 마지막으로 원고에 대한 해고를 의결하였습니다.",
        "위원회가 2024. 3. 18. 한 위 해고 의결은 정관상 정족수를 채우지 못하였습니다.",
    ])
    assert titles
    for t in titles:
        words = _target(t).split()
        assert len(words) == len(set(words)), t


def test_content_and_head_from_same_slot():
    titles = _titles([
        "원고는 2024. 5. 2. 단 한 차례 해지 통지를 발송하였습니다.",
        "원고는 2024. 5. 9. 위 해지 통지를 발송하였습니다.",
    ])
    assert titles and all(_target(t) == "해지 통지" for t in titles), titles


# --- 평가 측 후속 I1: 관형절에 날짜가 있는 '위 [사건 명사]에 대하여' 꼴 ---

def test_i1_dated_relative_clause_with_daehayeo_binds():
    titles = _titles([
        "원고는 2024. 6. 3. 단 한 차례 피고에게 손해배상 청구를 하였습니다.",
        "원고가 2024. 6. 17. 한 위 손해배상 청구에 대하여 피고는 아무런 답변을 하지 않았습니다.",
    ])
    assert titles, titles


def test_i1_control_no_relative_clause_daehayeo_not_bound():
    # 관형절 날짜 없이 '위 청구에 대하여 [다른 날짜] 답변서 제출' — 다른 사건(답변서 제출)의 날짜다
    titles = _titles([
        "원고는 2024. 6. 3. 단 한 차례 피고에게 손해배상 청구를 하였습니다.",
        "피고는 위 청구에 대하여 2024. 6. 17. 답변서를 제출하였습니다.",
    ])
    assert not titles, titles


# --- 평가 측 후속 I2: 전달 수단 명사(메일·문자·팩스 등)로 적은 같은 사건 ---

def test_i2_medium_noun_time_conflict():
    titles = _titles([
        "피고는 2024. 7. 1. 10:00 원고에게 단 한 번 해명 메일을 보냈습니다.",
        "피고가 위 해명 메일을 보낸 시각은 2024. 7. 1. 15:30입니다.",
    ])
    assert titles, titles


def test_i2_control_medium_as_instrument_not_event():
    # '팩스로'는 수단이다 — 다른 날짜의 팩스 도착을 같은 사건으로 묶지 않는다
    titles = _titles([
        "원고는 2024. 8. 5. 피고에게 계약 해지 통지를 발송하였습니다.",
        "원고는 2024. 8. 6. 같은 내용을 팩스로 다시 보냈습니다.",
    ])
    assert not titles, titles


def test_i2_control_idiom_munja_geudaero():
    titles = _titles([
        "피고는 2024. 9. 2. 계약서 조항을 문자 그대로 해석하였습니다.",
        "피고는 2024. 9. 9. 위 조항을 문자 그대로 다시 적용하였습니다.",
    ])
    assert not titles, titles


# --- 평가 측 후속 T2: 끝 음절이 조사와 같은 두 글자 내용 수식('이의·항의·사과' 등)이 제목에서 빠지지 않는다 ---

def test_t2_two_syllable_content_ending_like_particle_kept():
    titles = _titles([
        "원고는 2024. 10. 7. 단 한 차례 피고에게 항의 통지를 발송하였습니다.",
        "원고는 2024. 10. 14. 위 항의 통지를 피고에게 발송하였습니다.",
    ])
    assert titles and all(_target(t) == "항의 통지" for t in titles), titles


def test_t2_pronoun_genitive_not_content():
    from packages.claim_engine.internal_inconsistency import _clean_content_prefix
    assert _clean_content_prefix("그의") is None
    assert _clean_content_prefix("나도") is None
    assert _clean_content_prefix("이의") == "이의"


# --- 평가 측 후속 I3: '알리다·전하다'는 알림 단계 서술어다(결정과 그 통지를 같은 단계로 묶지 않는다) ---

def test_i3_control_decide_then_notify_by_allida():
    titles = _titles([
        "피고는 2024. 11. 4. 감봉 처분을 의결하였고, 2024. 11. 8. 위 감봉 처분을 원고에게 알렸습니다.",
    ])
    assert not titles, titles


def test_i3_control_decide_then_notify_by_jeonhada():
    titles = _titles([
        "피고는 2024. 11. 4. 전보 결정을 하였고, 2024. 11. 6. 위 전보 결정을 원고에게 전하였습니다.",
    ])
    assert not titles, titles


# --- 평가 측 후속 I4: 지시어 뒤 두 어절 내용 수식('위 [명사] [명사] [사건 명사]') ---

def test_i4_two_word_content_after_demonstrative_binds():
    titles = _titles([
        "원고는 2024. 12. 2. 단 한 번 피고에게 자료 제출 요구 통지를 발송하였습니다.",
        "원고가 2024. 12. 9. 발송한 위 제출 요구 통지에 대하여 피고는 답하지 않았습니다.",
    ])
    assert titles, titles


def test_i4_control_demonstrative_modifies_other_noun():
    # '위 원고에게 보낸 통지' — 지시어가 '원고'를 꾸민다(사건 결속 아님)
    titles = _titles([
        "피고는 2024. 12. 2. 원고에게 단 한 번 해고 통지를 하였습니다.",
        "피고는 2024. 12. 16. 위 원고에게 보낸 통지와 별도로 인사 발령을 하였습니다.",
    ])
    assert not titles, titles


# --- 평가 측 후속 I5: 복합 명사구의 머리 명사를 일반 경로와 지시어 경로에서 같게 고른다(마지막 사건 명사) ---

def test_i5_compound_noun_phrase_with_mid_noun_binds():
    titles = _titles([
        "피고는 2024. 10. 1. 단 한 차례 원고에게 계약 해지 예정 통지를 하였습니다.",
        "피고는 2024. 10. 15. 위 해지 예정 통지를 하였습니다.",
    ])
    assert titles and all(_target(t) == "예정 통지" for t in titles), titles


def test_i5_medium_noun_after_event_noun_binds():
    titles = _titles([
        "원고는 2024. 10. 1. 오전 10시 단 한 번 피고에게 합의 권유 메일을 보냈습니다.",
        "원고가 위 합의 권유 메일을 보낸 시각은 같은 날 오후 4시입니다.",
    ])
    assert titles, titles


def test_i5_control_relational_noun_not_extended():
    # '위 해고 이후 신청' — 지시어는 '해고'를 가리키고 '신청'은 다른 사건이다
    from packages.claim_engine.internal_inconsistency import _extract_event_from_clause
    r = _extract_event_from_clause("위 해고 이후 신청을 하였습니다")
    assert r is not None and r[1] == "해고", r


# --- 평가 측 후속 I6: EVI.INCONS_INTERNAL_DATE — 명사로만 쓰인 '해지·해제'는 사건 서술이 아니다 ---

def test_i6_control_haeji_as_noun_modifier_not_event():
    from packages.claim_engine.internal_inconsistency import check_internal_inconsistency
    from packages.common.schemas import Block, NormalizedDocument, Page
    lines = ["피고는 2024. 11. 4. 해지 예정 안내를 결정하였고, 2024. 11. 7. 위 해지 예정 안내 결정을 원고에게 전하였습니다."]
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(lines)]
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                             pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])
    rids = [(f.confidence_features or {}).get("rule_id") for f in check_internal_inconsistency(doc)]
    assert "EVI.INCONS_INTERNAL_DATE" not in rids, rids


def test_i6_haeji_verbal_still_detected():
    from packages.claim_engine.internal_inconsistency import check_internal_inconsistency
    from packages.common.schemas import Block, NormalizedDocument, Page
    lines = ["원고는 2024. 3. 2. 이 사건 계약을 해지하였습니다.", "원고는 2024. 3. 9. 이 사건 계약을 해지하였습니다."]
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(lines)]
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                             pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])
    rids = [(f.confidence_features or {}).get("rule_id") for f in check_internal_inconsistency(doc)]
    assert "EVI.INCONS_INTERNAL_DATE" in rids, rids


# --- 평가 측 후속 I7: 가정('-였다면')·의문('-였는지')은 단정 진술이 아니다 ---

def test_i7_control_conditional_not_assertion():
    titles = _titles([
        "원고가 2024. 8. 1. 단 한 차례 정직 통지를 송부하였다면, 2024. 8. 20. 위 정직 통지를 다시 송부할 이유가 없습니다.",
    ])
    assert not titles, titles


def test_i7_control_interrogative_not_assertion():
    titles = _titles([
        "원고가 2024. 8. 1. 정직 통지를 송부하였는지, 아니면 2024. 8. 20. 위 정직 통지를 송부하였는지 기록상 불분명합니다.",
    ])
    assert not titles, titles


# --- 평가 측 후속 I8: 서법 축 전체(가정·의문·선택·추측·당위·예정)는 단정 진술이 아니다 ---

@pytest.mark.parametrize("e1,e2", [
    ("송부하였으면", "송부하였으면"),            # 가정
    ("송부하였을지", "송부하였을지"),            # 의문
    ("송부하였거나", "송부하였거나"),            # 선택
    ("송부하였을 것으로 보이고", "송부하였을 가능성도 있습니다"),  # 추측
    ("송부하였어야 했고", "송부하였어야 했습니다"),  # 당위
    ("송부하기로 하였고", "송부하기로 하였습니다"),  # 예정
])
def test_i8_control_non_assertive_moods(e1, e2):
    titles = _titles([f"피고가 2024. 9. 2. 감급 통지를 {e1}, 2024. 9. 16. 위 감급 통지를 {e2}."])
    assert not titles, titles


# --- 평가 측 후속 I9: 정정류 낱말이 사건 명사구의 수식어이면 정정 진술이 아니다 ---

def test_i9_correction_word_as_noun_modifier_binds():
    titles = _titles([
        "원고는 2024. 9. 2. 단 한 차례 피고에게 등기 정정 신청을 하였습니다.",
        "원고는 2024. 9. 23. 위 등기 정정 신청을 하였습니다.",
    ])
    assert titles, titles


def test_i9_control_real_correction_statement_excluded():
    titles = _titles([
        "원고는 2024. 9. 2. 단 한 차례 피고에게 등기 정정 신청을 하였습니다.",
        "위 신청일은 2024. 9. 23.로 정정합니다.",
    ])
    assert not titles, titles
