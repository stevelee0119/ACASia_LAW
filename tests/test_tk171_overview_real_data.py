"""TK-171 보완: 개요 화면은 실제 값만 보이고(D2~D4, D1 최근 작업 활동은 사용자 11-14 결정으로 화면에서 뺐다), 브랜드·글꼴(B1·F1), 넓은 화면 사이드바 접기(S1),
좁은 화면 표 카드화(M1)를 지킨다. 값은 모두 합성이다(서버는 Playwright route로 대신한다)."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "apps/web/static"
FILES = {f"/static/{p.relative_to(STATIC).as_posix()}": p for p in STATIC.rglob("*") if p.is_file()}
FILES["/"] = ROOT / "apps/web/index.html"

PROJECT = {"id": "p1", "name": "합성 사건", "case_number": "합성-1", "court": "합성법원", "can_delete": True,
           "document_count": 2, "external_ai_policy": "MASKED", "scope_revision": 0, "incident_date": "2024-05-01",
           "requested_issues": [], "verification_profile": "STANDARD", "created_at": "2026-11-10T01:00:00"}
DOCS = [{"id": "d1", "filename": "서면_합성.pdf", "included_in_verification": True, "size_bytes": 2048,
         "uploaded_at": "2026-11-10T01:05:00"},
        {"id": "d2", "filename": "참고_합성.hwpx", "included_in_verification": False, "size_bytes": 1024,
         "uploaded_at": "2026-11-11T02:00:00"}]
ITEMS = [{"item_id": "i1", "kind": "CITATION", "document_id": "d1", "location": {"display": "2쪽"},
          "claim_text": "합성 주장 문장", "cited_authority": "대법원 2099다1 판결", "official_status": "OFFICIAL_NOT_FOUND",
          "reference_status": "NOT_CHECKED", "verdict_label": "공식 DB 미확인 (원문 확인 필요)", "severity": "HIGH",
          "finding_ids": [], "citation_id": "c1"}]
RESULT = {"status": "COMPLETED", "run_manifest": {},
          "documents": [{"id": "d1", "filename": "서면_합성.pdf", "quarantined": False, "findings": [], "review_items": ITEMS,
                         "claims": [], "engine_data": {"rag": {"status": "NOT_RELEVANT", "observations": []}}}]}
RUN = {"id": "r1", "project_id": "p1", "state": "COMPLETED", "progress": 1, "stage_message": "", "document_ids": ["d1"],
       "scores": {}, "unverified_items": [], "errors": [], "unavailable_sources": [], "input_snapshot": {"scope_revision": 0},
       "started_at": "2026-11-12T03:00:00", "finished_at": "2026-11-12T03:04:00"}
REPORTS = [{"report_id": "rep1", "run_id": "r1", "state": "DRAFT", "label": "초안 · 내부 검토용",
            "created_at": "2026-11-12T04:00:00", "finalized_at": None, "artifacts": {}}]


def _handler(with_run: bool):
    fixed = {"/api/health": {"status": "ok", "version": "0.21.0"},
             "/api/auth/me": {"user_id": "u", "email": "t@example.test", "display_name": "검토자", "role": "ADMIN",
                              "authentication": "local"},
             "/api/verification-runs": {"active_count": 0, "runs": []}, "/api/projects": [PROJECT],
             "/api/projects/p1": PROJECT, "/api/projects/p1/documents": DOCS,
             "/api/projects/p1/runs": [RUN] if with_run else [], "/api/projects/p1/reports": REPORTS if with_run else [],
             "/api/privacy-notice": {"version": "v1", "bullets": [], "ack_label": "", "report_header": ""},
             "/api/finding-categories": {"categories": {}, "tabs": {}, "counts": {}}}

    def handler(route):
        path = urlsplit(route.request.url).path
        if path in FILES:
            return route.fulfill(path=str(FILES[path]))
        if with_run and path.endswith(("/result", "/results")):
            return route.fulfill(json=RESULT)
        if path.endswith(("/case-matrix", "/latest-run")):
            return route.fulfill(body="null", content_type="application/json")
        if path in fixed:
            return route.fulfill(json=fixed[path])
        return route.fulfill(json=[])
    return handler


@pytest.fixture
def browser():
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    with sync_playwright() as p:
        b = p.chromium.launch(**options)
        yield b
        b.close()


def _open(browser, width, height, with_run=True):
    page = browser.new_page(viewport={"width": width, "height": height})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/*", _handler(with_run))
    page.goto("http://tk171.test/")
    page.keyboard.press("Escape")
    if width <= 700:
        page.locator("#menuButton").click()  # 좁은 화면: 프로젝트 목록은 서랍 안에 있다
    page.locator("#projectList button").first.click()
    expect(page.locator("#projectView")).to_be_visible()
    return page, errors


def test_overview_has_no_activity_timeline_or_shortcut_cards(browser):
    """사용자 11-14: 최근 작업 활동·핵심 기능 바로가기는 현재 화면에 없는 기능·배치라 개요에 넣지 않는다."""
    page, errors = _open(browser, 1440, 900)
    overview = page.locator("#templateAOverview")
    expect(overview.locator(".overview-warning-card")).to_be_visible()
    expect(overview).not_to_contain_text("최근 작업 활동")
    expect(overview).not_to_contain_text("핵심 기능 바로가기")
    expect(page.locator(".overview-timeline, .overview-activity-card, .overview-shortcuts-section, .overview-sc-card")).to_have_count(0)
    # 개요는 결과가 올 때마다 다시 그려지므로, 그 시점의 요소를 새로 찾아 잰다. 사람 검토 패널이 개요 폭을 다 쓴다.
    page.wait_for_function("""() => { const c = document.querySelector('#templateAOverview .overview-warning-card');
        const g = document.querySelector('#templateAOverview .overview-mid-grid');
        return c && g && c.getBoundingClientRect().width > 0
            && Math.abs(c.getBoundingClientRect().width - g.getBoundingClientRect().width) < 2; }""")
    assert not errors


@pytest.mark.parametrize("width", [1440, 390])
def test_review_panel_is_a_low_band_with_reason_cards(browser, width):
    """사용자 11-14 배치안 A: 두 패널을 뺀 자리에 사람 검토 패널을 낮은 띠로 둔다(저울 그림 없음).
    넓은 화면은 제목 오른쪽에 사유 카드가 가로로, 좁은 화면은 세로로 쌓인다."""
    page, errors = _open(browser, width, 900, with_run=False)
    expect(page.locator("#templateAOverview .overview-reason-item")).to_have_count(2)
    expect(page.locator(".overview-warning-art")).to_have_count(0)
    # 개요는 결과가 올 때마다 다시 그려지므로, 그 시점의 요소를 새로 찾아 잰다.
    layout = page.wait_for_function("""() => {
        const card = document.querySelector('#templateAOverview .overview-warning-card');
        const head = card && card.querySelector('.overview-warning-head');
        const items = card ? [...card.querySelectorAll('.overview-reason-item')].map(e => e.getBoundingClientRect()) : [];
        if (!card || items.length !== 2 || !items[0].width) return null;
        const c = card.getBoundingClientRect(), h = head.getBoundingClientRect();
        return {cardH: c.height, sameRow: Math.abs(items[0].top - items[1].top) < 2,
                stacked: items[1].top >= items[0].bottom, besideHead: items[0].left >= h.right};
    }""").json_value()
    if width > 1050:
        assert layout["sameRow"] and layout["besideHead"], layout
        assert layout["cardH"] < 160, layout
    else:
        assert layout["stacked"] and not layout["besideHead"], layout
    assert not errors


def test_before_verification_nothing_is_shown_as_zero(browser):
    page, errors = _open(browser, 1440, 900, with_run=False)
    kpis = page.locator(".kpi-overview-row")
    expect(kpis).not_to_contain_text("성립 불가 인용")
    expect(kpis).not_to_contain_text("미확인 0건")
    expect(kpis).to_contain_text("검증 후 집계")
    expect(page.locator(".overview-warning-card")).to_contain_text("검토 안내")
    expect(page.locator(".overview-warning-card")).not_to_contain_text("사람 검토 필요")
    assert not errors


def test_document_card_counts_documents_only(browser):
    page, _ = _open(browser, 1440, 900)
    expect(page.locator("#overviewScopeCard")).to_contain_text("검토 포함 1건 · 제외 1건")
    expect(page.locator("#overviewScopeCard")).not_to_contain_text("인용")


def test_brand_text_and_self_hosted_pretendard():
    html = (ROOT / "apps/web/index.html").read_text(encoding="utf-8")
    assert "ACASia" not in html and "ACASia" not in (STATIC / "operations.js").read_text(encoding="utf-8")
    assert 'href="/static/fonts/pretendard/pretendard.css"' in html
    css = (STATIC / "fonts/pretendard/pretendard.css").read_text(encoding="utf-8")
    assert "font-family: 'Pretendard Variable'" in css and "http" not in css.split("*/", 1)[1]
    for name in __import__("re").findall(r"url\(\./([^)]+)\)", css):
        assert (STATIC / "fonts/pretendard" / name).is_file(), name
    assert (STATIC / "fonts/pretendard/OFL-Pretendard.txt").is_file()


def test_pretendard_is_actually_used(browser):
    page, _ = _open(browser, 1440, 900)
    # 글꼴 정의가 없으면 fonts.check도 참이 되므로, 자체 호스팅한 글꼴 면이 실제로 읽혔는지를 본다.
    page.wait_for_function("""() => [...document.fonts].some(
        f => f.family.replace(/['"]/g, '') === 'Pretendard Variable' && f.status === 'loaded')""", timeout=10000)


def test_wide_screen_sidebar_collapses_and_expands_with_the_menu_button(browser):
    page, errors = _open(browser, 1440, 900)
    button = page.locator("#menuButton")
    expect(button).to_be_visible()
    expect(button).to_have_attribute("aria-expanded", "true")
    button.click()
    expect(page.locator("#sidebar")).not_to_be_visible()
    expect(button).to_have_attribute("aria-expanded", "false")
    assert page.locator("main").evaluate("el => el.getBoundingClientRect().left") < 10
    button.click()
    expect(page.locator("#sidebar")).to_be_visible()
    expect(button).to_have_attribute("aria-expanded", "true")
    assert not errors


@pytest.mark.parametrize("width", [320, 390, 768])
def test_narrow_screen_review_table_becomes_cards(browser, width):
    page, errors = _open(browser, width, 844)
    page.evaluate("switchTab('review')")
    cell = page.locator("#reviewTable tbody td").first
    expect(cell).to_be_visible()
    if width <= 700:
        page.wait_for_function("""() => { const td = document.querySelector('#reviewTable tbody td');
            return td && td.isConnected && td.dataset.label === '위치' && getComputedStyle(td).display === 'block'; }""")
        assert page.locator("#reviewTable").evaluate("el => el.scrollWidth <= el.parentElement.clientWidth + 1")
        expect(page.locator("#reviewTable thead")).not_to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors
