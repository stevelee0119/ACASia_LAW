"""TK-179: 모델 응답 JSON 추출이 설명 속 중괄호·여러 객체에서 실패하던 문제와, 형식 오류 원인을 알 수 없던 문제. 값은 합성이다.

운영 근거: 0.19.0 탐침 B 실행에서 anthropic 50건 중 3건 실패(INVALID_RESPONSE_SCHEMA 'JSON이 아님' 2건, 2500 토큰 잘림 1건).
'JSON이 아님' 2건의 실제 응답은 기록되지 않아 원인을 확정하지 못했다(미검증). 아래는 추출기의 확인된 약점과 진단 보강이다.
"""
import pytest

from packages.llm_router.providers import _extract_json, response_shape
from packages.llm_router import router


@pytest.mark.parametrize("text, expected", [
    ('{"status":"VERIFIED","confidence":0.8}', "VERIFIED"),
    ('```json\n{"status":"VERIFIED"}\n```', "VERIFIED"),
    ('```JSON\n{"status":"VERIFIED"}\n```', "VERIFIED"),
    ('다음은 판단입니다.\n{"status":"VERIFIED"}', "VERIFIED"),
    ('{"status":"VERIFIED"}\n위와 같이 판단합니다.', "VERIFIED"),
    ('설명 {예시} 이후 {"status":"VERIFIED","rationale":"a {b} c"}', "VERIFIED"),
    ('{"status":"VERIFIED"}\n{"note":"추가"}', "VERIFIED"),
    ('형식: {status, confidence}\n{"status":"CONTRADICTED"}', "CONTRADICTED"),
])
def test_extracts_the_first_json_object(text, expected):
    assert _extract_json(text)["status"] == expected


@pytest.mark.parametrize("text", ['{"status":"VERIFIED","rationale":"길게 이어지다 잘', "", "JSON 없음", "[1, 2]"])
def test_no_object_returns_none(text):
    assert _extract_json(text) is None


def test_response_shape_has_no_content():
    shape = response_shape('설명 {예시} 이후 {"status":"VERIFIED","rationale":"사건 내용 문장')
    assert "사건" not in shape and "VERIFIED" not in shape
    assert "길이" in shape and "끝" in shape


def test_verdict_output_limit_matches_other_review_paths():
    assert router._VERDICT_MAX_TOKENS >= 4096
