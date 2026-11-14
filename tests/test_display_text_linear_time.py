"""괄호 속 코드 지우기가 긴 공백에서도 선형 시간에 끝나고 옛 규칙과 결과가 같다(CodeQL py/polynomial-redos #133).

옛 규칙: 정규식 '\\s*\\(([A-Z][A-Z0-9]*_[A-Z0-9_]+)\\)'을 빈 문자열로 치환. 값은 모두 합성이다.
"""
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from packages.common.display_text import _drop_paren_codes, readable
from tests.frontend_helpers import privacy_notice_mock_payload

ROOT = Path(__file__).resolve().parents[1]
OLD = re.compile(r"\s*\(([A-Z][A-Z0-9]*_[A-Z0-9_]+)\)")
CASES = [
    "", "(AB_CD)", "앞 문장 (AB_CD) 뒤", "앞\t\t(AB_CD)", "줄\n(AB_CD)\n다음", "(AB_CD)(EF_GH)", "a (AB_CD) b (EF_1) c",
    "(ab_cd) 소문자는 그대로", "(AB) 밑줄 없음", "( AB_CD ) 안쪽 공백", "　(AB_CD)", "x  (AB_CD)", "  (A1_B2_C3)",
    "끝 공백 없는 (AB_CD", "[PERSON_003] 가림 토큰", "\t" * 50,
]


@pytest.mark.parametrize("text", CASES)
def test_same_result_as_the_old_rule(text):
    assert _drop_paren_codes(text) == OLD.sub("", text)


def test_long_whitespace_without_parenthesis_is_linear():
    text = "\t" * 200_000 + "x"
    started = time.perf_counter()
    assert readable(text) == text
    assert time.perf_counter() - started < 1.0  # 옛 규칙은 길이 40,000에서 이미 1초를 넘는다(평가 측 측정)


@pytest.fixture
def browser():
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    with sync_playwright() as playwright:
        b = playwright.chromium.launch(**options)
        yield b
        b.close()


def test_screen_rule_matches_server_and_stays_linear(browser):
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        if path == "/api/health":
            return route.fulfill(json={"status": "ok", "version": "test"})
        if path == "/api/privacy-notice":
            return route.fulfill(json=privacy_notice_mock_payload())
        return route.fulfill(status=401, json={"detail": "Login required"})

    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/*", respond)
    page.goto("http://linear.test/")
    expect(page.get_by_role("dialog", name="작업 공간 로그인")).to_be_visible()
    screen = page.evaluate("cases => cases.map(dropParenCodes)", CASES)
    assert screen == [OLD.sub("", text) for text in CASES]
    elapsed = page.evaluate("""() => { const text = '\\t'.repeat(200000) + 'x';
        const started = performance.now(); const out = friendlyText(text);
        return [out === text, performance.now() - started]; }""")
    assert elapsed[0] and elapsed[1] < 1000
    assert errors == []
