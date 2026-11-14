"""TK-157b: '연결 상태' 창의 경고 유형별 검토 결정 집계(서버 /api/review-quality, TK-157a). 값은 모두 합성이다."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.frontend_helpers import privacy_notice_mock_payload

ROOT = Path(__file__).resolve().parents[1]
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")
QUALITY = {"min_decided": 5, "note": "합성 안내", "types": [
    {"type": "EVIDENCE_LIST_MISMATCH", "total": 12, "decided": 10, "NEEDS_REVIEW": 2, "ACCEPTED": 6, "FALSE_POSITIVE": 3,
     "RESOLVED": 1, "acceptance_rate": 0.7, "false_positive_rate": 0.3, "enough_samples": True},
    {"type": "CASE_NOT_FOUND", "total": 4, "decided": 2, "NEEDS_REVIEW": 2, "ACCEPTED": 1, "FALSE_POSITIVE": 1,
     "RESOLVED": 0, "acceptance_rate": None, "false_positive_rate": None, "enough_samples": False},
    {"type": "ARITHMETIC_MISMATCH", "total": 0, "decided": 0, "NEEDS_REVIEW": 0, "ACCEPTED": 0, "FALSE_POSITIVE": 0,
     "RESOLVED": 0, "acceptance_rate": None, "false_positive_rate": None, "enough_samples": False},
]}
NAMES = {"EVIDENCE_LIST_MISMATCH": "증거목록 불일치", "CASE_NOT_FOUND": "공식 DB 미발견 판례", "ARITHMETIC_MISMATCH": "계산 불일치"}
DIAGNOSTICS = {"verdict": "READY", "note": "합성", "capabilities": {"ocr": {"ready": True}, "rasterizer": {"available": True},
               "database": {"dialect": "sqlite"}, "worker_mode": "auto", "network_allowed": True, "source_keys_present": {}}}


def _open(page, quality_status=200, storage_status=200, quality=QUALITY):
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        replies = {"/api/health": {"status": "ok", "version": "0.20.0"}, "/api/privacy-notice": privacy_notice_mock_payload(),
                   "/api/diagnostics": DIAGNOSTICS,
                   "/api/finding-categories": {"names": NAMES, "categories": {}, "tabs": {}, "code_words": {}}}
        if path in replies:
            return route.fulfill(json=replies[path])
        if path == "/api/review-quality":
            return route.fulfill(status=quality_status, json=quality if quality_status == 200 else {"detail": "x"})
        if path == "/api/admin/storage":
            return route.fulfill(status=storage_status, json={"database_bytes": 1, "files": {"root_bytes": 1, "parts": {}}, "tables": []}
                                 if storage_status == 200 else {"detail": "x"})
        return route.fulfill(status=401, json={"detail": "Login required"})

    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/*", respond)
    page.goto("http://quality.test/")
    expect(page.get_by_role("dialog", name="작업 공간 로그인")).to_be_visible()
    page.keyboard.press("Escape")
    page.locator("#settingsButton").click()
    expect(page.locator("#settingsDialog")).to_be_visible()
    return errors


@pytest.fixture
def browser():
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    with sync_playwright() as playwright:
        b = playwright.chromium.launch(**options)
        yield b
        b.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_panel_lists_types_with_korean_names_rates_and_small_sample_marker(browser, width):
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors = _open(page)
    panel = page.locator(".review-quality-panel")
    expect(panel).to_contain_text("경고 유형별 검토 결정")
    expect(panel.locator(".badge")).to_have_text("결정 12건")
    rows = panel.locator("tbody tr")
    expect(rows).to_have_count(2)  # 전체 0건 유형은 보이지 않는다
    expect(rows.nth(0)).to_contain_text("증거목록 불일치")
    expect(rows.nth(0)).to_contain_text("10 / 12")
    expect(rows.nth(0)).to_contain_text("70%")
    expect(rows.nth(1)).to_contain_text("표본 부족")
    expect(panel).to_contain_text("결정이 5건 미만인 유형은 비율을 보이지 않습니다")
    assert CODE_RE.findall(panel.inner_text()) == [] and errors == []
    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert not overflow
    # 표가 창(상자) 안에 들어와 네 칸이 모두 보인다(전역 table min-width 760px에 잘리지 않는다)
    fits = page.evaluate("""() => { const p = document.querySelector('.review-quality-panel');
        const t = p.querySelector('table'); return t.getBoundingClientRect().right <= p.getBoundingClientRect().right + 1; }""")
    assert fits
    expect(panel.locator("th").nth(3)).to_be_in_viewport()
    # 숫자·비율 칸은 한 줄(낱말 중간 줄바꿈 없음)
    heights = page.evaluate("""() => [...document.querySelectorAll('.review-quality-panel td:not(:first-child)')]
        .map(td => td.getClientRects().length && td.firstChild ? (() => { const r = document.createRange();
          r.selectNodeContents(td); return r.getClientRects().length; })() : 1)""")
    assert set(heights) == {1}, heights
    if os.getenv("TK157B_SHOT") and width == 1440:
        panel.screenshot(path=os.environ["TK157B_SHOT"])


def test_panel_is_absent_without_permission_and_survives_storage_failure(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = _open(page, quality_status=401)
    expect(page.locator("#settingsDialog")).to_contain_text("연결 상태")
    expect(page.locator(".review-quality-panel")).to_have_count(0)
    assert errors == []
    page2 = browser.new_page(viewport={"width": 1440, "height": 900})
    _open(page2, storage_status=500)
    expect(page2.locator(".review-quality-panel")).to_contain_text("증거목록 불일치")


def test_panel_reports_load_failure_without_breaking_the_dialog(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = _open(page, quality_status=500)
    expect(page.locator(".review-quality-panel")).to_contain_text("집계를 불러오지 못했습니다")
    assert errors == []


def test_panel_without_decisions_explains_how_they_accumulate(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    empty = {**QUALITY, "types": [{**t, "total": 0, "decided": 0} for t in QUALITY["types"]]}
    errors = _open(page, quality=empty)
    panel = page.locator(".review-quality-panel")
    expect(panel).to_contain_text("아직 검토 결정이 없습니다")
    expect(panel.locator("table")).to_have_count(0)
    expect(panel.locator(".badge")).to_have_text("결정 0건")
    assert errors == []
