"""LV-01: 날짜 역할 및 기산점·제소기간 계산 전제 보존 단위 및 합성 시험.

규칙:
1. 소제기일(또는 서면 작성일)이 명시되지 않은 경우 임의의 미래 날짜나 오늘로 폴백하지 않고 계산 보류로 표시.
2. 장래 일정(면담 예정일, 기일 등)이 본문에 있어도 이를 소제기일로 전용하지 않음.
3. 명시적 소제기일 또는 서면 작성일이 있을 때만 동적 일수를 계산.
"""
from __future__ import annotations

from packages.common.schemas import Block, Page, NormalizedDocument
from packages.legal_engine.legal_rules import _calculate_dynamic_deadline


def _make_doc(text: str, doc_id: str = "lv01_doc") -> NormalizedDocument:
    b = Block("b1", text, 1)
    p = Page(1, 100.0, 100.0, [b])
    return NormalizedDocument(doc_id, f"{doc_id}.txt", "text/plain", "sha256", [p])


# --- 1. 양성 예시 3종 (소제기일/작성일이 확인되어 동적 계산 정상 수행) ---

def test_lv01_positive_explicit_filing_date():
    """양성 1: 명시적 소제기일 기재 -> 90일 이내 정상 계산."""
    claim = "이의신청 결과를 통보받아 제소기간 90일이 진행하므로 기산점은 통보일이어야 합니다."
    text = (
        "청구원인\n"
        "원고는 2024. 1. 15. 처분을 고지받고 이에 불복하여 이의신청을 제기하였으며, "
        "2024. 2. 1. 결과를 통보받았습니다.\n"
        "소제기일: 2024. 4. 10.\n"
    )
    doc = _make_doc(text, "pos1")
    result = _calculate_dynamic_deadline(doc, claim)
    assert "[실제 일수 동적 계산]" in result
    assert "원처분일(2024. 1. 15.) 기준: 86일 경과" in result
    assert "이의신청 통보일(2024. 2. 1.) 기준: 69일 경과" in result
    assert "기간 준수" not in result and "각하 위험" not in result
    assert "소제기일: 2024. 4. 10." in result


def test_lv01_positive_document_drafting_date_over_deadline():
    """양성 2: 서면 말미 작성일자만 있고 소제기일 부재 -> 임의 만료 단정 방지 및 계산 보류."""
    claim = "이의신청 결과를 통보받아 제소기간 90일이 기산됩니다."
    text = (
        "청구원인\n"
        "원고는 2024. 1. 10. 영업정지처분을 고지받고 이의신청을 제기하여 "
        "2024. 1. 25. 결과를 통보받았습니다.\n"
        "2024. 6. 1.\n"
        "원고 대리인 변호사"
    )
    doc = _make_doc(text, "pos2")
    result = _calculate_dynamic_deadline(doc, claim)
    assert "[제소기간 계산 보류]" in result
    assert "소제기일이 문서에 명시되지 않거나 불명확하여 법적 만료일 판단이 보류되었습니다" in result
    assert "각하 위험" not in result
    assert "기간 준수" not in result


def test_lv01_positive_action_filing_phrase():
    """양성 3: 서술형 소제기 문장('본 소를 제기') 기재 -> 90일 이내 동적 계산."""
    claim = "이의신청 통지일 기준으로 제소기간 90일 계산을 하여야 합니다."
    text = (
        "청구원인\n"
        "피고는 2024. 2. 1. 원고에게 처분을 내렸고, 원고는 2024. 2. 15. 통지를 받았습니다. "
        "원고는 2024. 4. 5. 본 소를 제기하였습니다."
    )
    doc = _make_doc(text, "pos3")
    result = _calculate_dynamic_deadline(doc, claim)
    assert "[실제 일수 동적 계산]" in result
    assert "원처분일(2024. 2. 1.) 기준: 64일 경과" in result
    assert "이의신청 통보일(2024. 2. 15.) 기준: 50일 경과" in result
    assert "기간 준수" not in result and "각하 위험" not in result
    assert "소제기일: 2024. 4. 5." in result


# --- 2. 대조군 3종 (소제기일/작성일 부재 시 계산 보류 처리, 임의 폴백 방지) ---

def test_lv01_contrast_scheduled_interview_date_not_used():
    """대조군 1: 면담 예정일 등 장래 일정이 본문에 있어도 소제기일로 전용하지 않고 계산 보류."""
    claim = "이의신청 결과 통보를 받아 제소기간 90일이 진행합니다."
    text = (
        "청구원인\n"
        "원고는 2024. 3. 1. 처분을 고지받고 이에 불복하여 이의신청을 제기하였으며, "
        "2024. 3. 20. 결과를 통보받아 제소기간 90일이 진행하므로 기산점은 통보일이어야 합니다.\n"
        "한편 원고는 2024. 11. 15. 피고 담당자와 면담이 예정되어 있습니다."
    )
    doc = _make_doc(text, "con1")
    result = _calculate_dynamic_deadline(doc, claim)
    # 2024. 11. 15.를 소제기일로 오인하여 90일 도과 각하 위험을 경고하지 않아야 함
    assert "2024. 11. 15." not in result
    assert "90일 도과" not in result
    assert "[제소기간 계산 보류]" in result
    assert "소제기일이 문서에 명시되지 않거나 불명확하여 법적 만료일 판단이 보류되었습니다" in result
    assert "원처분일 2024. 3. 1." in result
    assert "2024. 3. 20." in result


def test_lv01_contrast_no_other_dates_not_falling_back_to_notification():
    """대조군 2: 문서 내 다른 날짜가 없어도 통보일 자체를 소제기일로 전용하거나 오늘로 폴백하지 않음."""
    claim = "이의신청 결과를 통보받아 제소기간 90일이 기산됩니다."
    text = (
        "청구원인\n"
        "원고는 2024. 5. 1. 처분을 받고, 2024. 5. 20. 결과 통보를 받았습니다."
    )
    doc = _make_doc(text, "con2")
    result = _calculate_dynamic_deadline(doc, claim)
    assert "0일 경과" not in result
    assert "[제소기간 계산 보류]" in result
    assert "원처분일 2024. 5. 1." in result
    assert "이의신청 통보일 2024. 5. 20." in result


def test_lv01_contrast_future_completion_date_not_used():
    """대조군 3: 사업 완공 예정일 등 미래 일정이 있어도 소제기일로 쓰지 않음."""
    claim = "이의신청 통보일 기준으로 제소기간 90일이 진행됩니다."
    text = (
        "청구원인\n"
        "2024. 4. 1. 과징금 부과 처분이 있은 날이며, 2024. 4. 20. 송달받았습니다. "
        "당해 시설의 공사는 2025. 12. 31. 완공 예정입니다."
    )
    doc = _make_doc(text, "con3")
    result = _calculate_dynamic_deadline(doc, claim)
    assert "2025. 12. 31." not in result
    assert "90일 도과" not in result
    assert "[제소기간 계산 보류]" in result
    assert "원처분일 2024. 4. 1." in result
    assert "이의신청 통보일 2024. 4. 20." in result


# --- 3. 평가 에이전트 계약 점검 (주장 어휘 미확정 및 서법/사건역할 보류) ---

import pytest


@pytest.mark.parametrize("claim", ["제소기간을 검토한다.", "90일 기간을 주장한다.", "기간 준수 여부가 쟁점이다."])
def test_lv01_claim_words_do_not_establish_legal_deadline(claim: str):
    doc = _make_doc("원처분일: 2025. 3. 1.\n소제기일: 2025. 4. 9.", "claim_words")
    result = _calculate_dynamic_deadline(doc, claim)
    assert "39일" in result
    assert "기간 준수" not in result and "각하 위험" not in result


@pytest.mark.parametrize("tail", ["소제기일: 2025. 4. 9. 예정", "2025. 4. 9. 본 소를 제기할 경우", "심판청구일: 2025. 4. 9."])
def test_lv01_event_role_and_modality_are_not_actual_filing(tail: str):
    doc = _make_doc("원처분일: 2025. 3. 1.\n" + tail, "event_role")
    result = _calculate_dynamic_deadline(doc, "제소기간 검토")
    assert "보류" in result
    assert "기간 준수" not in result and "각하 위험" not in result

