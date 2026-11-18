"""PR #335 보완 P1: 라벨이 붙은 생년월일이 날짜 가드에 막히지 않는지 확인한다.

batch-b가 `LEGAL_IDENTIFIER_PATTERNS`에 ISO 날짜/기간 정규식을 더해, 날짜 구간이 공통
가드가 되었다. 생년월일 라벨이 붙은 날짜는 DOB 일치 구간이 라벨까지 포함해 가드 구간보다
넓으므로 `_covered_by_span`에 걸리지 않는다. 이 시험은 그 성질을 탐지·마스킹·요청 검사
세 경로에서 고정하고, 비개인 날짜는 계속 식별자로 오인하지 않는지 함께 본다.

같은 보완에서 라벨과 날짜 사이의 조사·괄호 표기도 탐지되도록 넓혔다.

모든 입력은 합성 값이다.
"""
from __future__ import annotations

import json

import pytest

from packages.llm_router.privacy import inspect_request
from packages.llm_router.providers import LLMRequest
from packages.pii_engine.detector import detect
from packages.pii_engine.engine import PIIEngine
from packages.pii_engine.pseudonym import PseudonymStore


# 양성: 라벨이 붙은 생년월일 — 표기·구분자·문맥을 달리한다
_DOB_POSITIVE = [
    ("생년월일: 1985-11-24", "콜론 + ISO"),
    ("생년월일 1990-01-05", "공백 + ISO"),
    ("생년월일은 2001-12-31", "조사 '은' + ISO"),
    ("생년월일(1978-02-17)", "괄호 + ISO"),
    ("출생일: 1972-03-09", "출생일 라벨 + ISO"),
    ("원고 홍길동(생년월일 1985-11-24)은 당사자이다", "문장 안 괄호 문맥"),
    ("피고 생년월일 1990-01-05, 연락처 010-1111-2222", "다른 개인정보와 같은 줄"),
    ("생년월일: 1985. 11. 24.", "점 구분 표기"),
]

# 대조: 개인정보가 아닌 날짜·기간 — 탐지되면 안 된다
_DATE_CONTROL = [
    ("이행 기간: 2024-01-01 ~ 2024-12-31", "계약 기간"),
    ("정산 기준일 2024-06-30", "기준일"),
    ("공사기간 2023-03-01~2023-09-30 이다", "공사 기간"),
    ("은행 2024-12-24 거래내역을 확인하였다", "거래일"),
]


@pytest.mark.parametrize("text, axis", _DOB_POSITIVE)
def test_labelled_dob_is_detected(text, axis):
    hits = [m for m in detect(text) if m.kind == "DOB"]
    assert hits, f"{axis}: 라벨이 붙은 생년월일이 탐지되지 않았다 — {text}"


@pytest.mark.parametrize("text, axis", _DOB_POSITIVE)
def test_labelled_dob_is_masked(tmp_path, text, axis):
    engine = PIIEngine(PseudonymStore("pr335_dob", root=tmp_path))
    result = engine.mask_text(text)
    date_part = text.split("생년월일")[-1].split("출생일")[-1]
    digits = [t for t in date_part.replace(".", "-").split("-") if t.strip().isdigit()]
    assert digits, text
    assert digits[0].strip() not in result.masked_text, f"{axis}: 생년월일이 가려지지 않았다 — {result.masked_text}"


@pytest.mark.parametrize("text, axis", _DOB_POSITIVE)
def test_unmasked_labelled_dob_is_blocked_by_request_inspection(text, axis):
    """fail-closed: 가리지 않은 생년월일이 든 요청은 외부 모델로 나가지 못한다."""
    req = LLMRequest(system="검토 시스템", user=json.dumps({"본문": text}, ensure_ascii=False))
    verdict = inspect_request(req)
    assert verdict["status"] != "PASSED", f"{axis}: 가리지 않은 생년월일이 통과했다 — {verdict}"


@pytest.mark.parametrize("text, axis", _DOB_POSITIVE)
def test_masked_labelled_dob_passes_request_inspection(tmp_path, text, axis):
    """가린 뒤에는 같은 문장이 통과한다(과차단이 아님을 확인)."""
    engine = PIIEngine(PseudonymStore("pr335_dob_pass", root=tmp_path))
    masked = engine.mask_text(text).masked_text
    req = LLMRequest(system="검토 시스템", user=json.dumps({"본문": masked}, ensure_ascii=False))
    assert inspect_request(req)["status"] == "PASSED", f"{axis}: 가린 문장이 막혔다 — {masked}"


@pytest.mark.parametrize("text, axis", _DATE_CONTROL)
def test_non_personal_dates_are_not_detected(text, axis):
    assert detect(text) == [], f"{axis}: 비개인 날짜가 개인정보로 탐지됐다 — {text}"


def test_masking_is_idempotent_for_labelled_dob(tmp_path):
    engine = PIIEngine(PseudonymStore("pr335_dob_idem", root=tmp_path))
    text = "원고 생년월일은 2001-12-31, 피고 출생일: 1972-03-09"
    first = engine.mask_text(text).masked_text
    second = engine.mask_text(first).masked_text
    assert first == second
    assert "2001" not in second and "1972" not in second
