"""TK-136: 외부 AI 검증 프롬프트의 엄격성 규칙(두 프롬프트 공통). 실제 app.js 함수를 node로 실행한다."""
import json
import re
import subprocess
from pathlib import Path

import pytest

APP = Path("apps/web/static/app.js").read_text(encoding="utf-8")


def js_function(name):
    start = APP.index(f"function {name}(")
    depth, index = 0, APP.index(") {", start) + 2
    while True:
        depth += {"{": 1, "}": -1}.get(APP[index], 0)
        index += 1
        if depth == 0:
            return APP[start:index]


def constants():
    return "\n".join(line for line in APP.splitlines()
                     if line.startswith(("const EXTERNAL_ANSWER_OPEN", "const EXTERNAL_ANSWER_CLOSE")))


def run(script):
    out = subprocess.run(["node"], input=script.encode("utf-8"), capture_output=True, check=True)
    return json.loads(out.stdout.decode("utf-8"))


def authority_prompt():
    script = "\n".join([js_function("maskAuthorityIdentifier"), js_function("buildExternalAiPromptForUnverifiedAuthorities")]) + """
const items = [{cited_authority: "대법원 2099다1 판결", claim_text: "원고 홍길동 주장", official_status: "OFFICIAL_NOT_FOUND"}];
process.stdout.write(JSON.stringify(buildExternalAiPromptForUnverifiedAuthorities(items, "2025-01-01", "MASKED")));"""
    return run(script)


def claims_prompt():
    script = "\n".join([constants(), js_function("externalAnswerFormat"), js_function("buildExternalAiPromptForLegalClaims")]) + """
const entries = [{code: "B1", authority: "대법원 2099다2 판결", claim: "합성 주장 문장"}];
process.stdout.write(JSON.stringify(buildExternalAiPromptForLegalClaims(entries, "2025-01-01")));"""
    return run(script)


RULE_MARKERS = [
    "[엄격성 규칙 — 반드시 지킬 것]",
    "지금 조회한 데이터베이스에서 원문을 직접 확인한 것만 인용",
    "하나라도 확인하지 못했으면 그 인용을 쓰지 말고 '확인 불가'",
    "원문을 글자 그대로 옮긴 문장에만",
    "다수의견·별개의견·반대의견",
    "검색한 방법",
    "최대 2건",
    "확인한 사실과 귀하의 법적 의견을 문단으로 나누어",
]


@pytest.mark.parametrize("build", [authority_prompt, claims_prompt])
def test_both_prompts_carry_all_strictness_rules(build):
    prompt = build()
    for marker in RULE_MARKERS:
        assert marker in prompt, marker
    assert prompt.index("[엄격성 규칙") < prompt.index("ACAS_RESULT")   # 규칙은 결과 블록 앞


def test_replacement_precedent_request_is_bounded_by_rules():
    prompt = authority_prompt()
    assert "가공(환각) 판례라면, 동일한 쟁점을 다룬 실제 대법원 판례 제시" not in prompt   # 무조건 새 인용 요구 삭제
    assert "존재하지 않는다고 확인된 경우에만" in prompt and "엄격성 규칙 6번" in prompt
    assert "엄격성 규칙 6번" in claims_prompt()


@pytest.mark.parametrize("build", [authority_prompt, claims_prompt])
def test_result_block_keeps_four_cells(build):
    prompt = build()
    line = next(l for l in prompt.splitlines() if re.match(r"^[AB]1 \| 판정:", l))
    assert len(line.split("|")) == 4                       # 붙여넣기 해석기와 칸 수가 같다
    assert "(확인 방법)" in line


def test_masked_prompt_still_excludes_claim_text_and_names():
    prompt = authority_prompt()
    assert "홍길동" not in prompt and "원고 홍길동 주장" not in prompt


def test_answer_parser_unchanged_for_rule_following_answer():
    script = "\n".join([constants(), js_function("parseExternalAnswers")]) + """
const text = "본문 …\\n<<<ACAS_RESULT\\nA1 | 판정: 불명 | 근거: 확인 불가(사건번호 검색 0건) | 요지: 수록 범위 밖\\nACAS_RESULT>>>";
process.stdout.write(JSON.stringify(parseExternalAnswers(text)));"""
    parsed = run(script)
    assert parsed == [{"code": "A1", "verdict": "불명", "basis": "확인 불가(사건번호 검색 0건)", "summary": "수록 범위 밖"}]
