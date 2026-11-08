"""TK-76 EVI-INCONS C 후속 T1 — 결과 제목의 대상 표시에 같은 낱말이 겹치지 않는다(평가 측 공개 합성 문장)."""
from __future__ import annotations

import re

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
