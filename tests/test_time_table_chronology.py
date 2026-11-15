"""v0.22.0 Time Table(사건일지) 탭 단위·브라우저 회귀 시험."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from frontend_helpers import select_first_project
from packages.claim_engine.contradiction import build_timeline
from packages.common.schemas import Event

ROOT = Path(__file__).resolve().parents[1]


def test_build_timeline_sorts_chronologically_and_formats_evidence() -> None:
    events = [
        Event(
            event_id="e3",
            date=date(2026, 10, 8),
            description="원고가 피고에게 잔금 독촉 문자 발송",
            document_id="doc-1",
            page=3,
            span=(120, 150),
            evidence_references=[],
        ),
        Event(
            event_id="e1",
            date=date(2026, 9, 30),
            description="피고가 원고로부터 5,000만 원을 차용함 (증제1호 26. 9. 30.자 차용증)",
            document_id="doc-1",
            page=1,
            span=(10, 60),
            evidence_references=[],
        ),
        Event(
            event_id="e1-dup",
            date=date(2026, 9, 30),
            description="피고가 원고로부터 5,000만 원을 차용함 (증제1호 26. 9. 30.자 차용증)",
            document_id="doc-1",
            page=1,
            span=(10, 60),
            evidence_references=[],
        ),
        Event(
            event_id="e2",
            date=date(2026, 10, 2),
            description="피고가 일부 변제금 입금",
            document_id="doc-1",
            page=2,
            span=(5, 40),
            evidence_references=[{"raw_text": "갑 제2호증 계좌이체내역"}],
        ),
    ]

    timeline = build_timeline(events)
    assert len(timeline) == 3
    assert [item["date"] for item in timeline] == ["2026-09-30", "2026-10-02", "2026-10-08"]
    assert timeline[0]["formatted_date"] == "26.9.30.(수)"
    assert timeline[1]["formatted_date"] == "26.10.2.(금)"
    assert timeline[2]["formatted_date"] == "26.10.8.(목)"
    assert "증제1호" in timeline[0]["evidence_summary"]
    assert timeline[1]["evidence_summary"] == "갑 제2호증 계좌이체내역"
    assert timeline[2]["evidence_summary"] == "[근거 미작성]"


@pytest.fixture
def timeline_browser_page():
    launch_kwargs = {"headless": True}
    channel = os.environ.get("LV_TEST_BROWSER_CHANNEL")
    if channel:
        launch_kwargs["channel"] = channel

    project_data = {
        "id": "p-time",
        "name": "Time Table UI 검증 프로젝트",
        "can_delete": True,
        "document_count": 1,
        "external_ai_policy": "MASKED",
        "scope_revision": 0,
        "requested_issues": ["대여금 반환"],
    }

    # 의도적으로 역순 배치하여 프론트엔드에서도 시간 순서 정렬이 보장되는지 검증
    run_data = {
        "id": "r-time",
        "project_id": "p-time",
        "state": "COMPLETED",
        "progress": 1,
        "stage_message": "",
        "document_ids": ["d1"],
        "scores": {},
        "unverified_items": [],
        "errors": [],
        "unavailable_sources": [],
        "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-11-15T00:00:00",
        "timeline": [
            {
                "date": "2026-10-15",
                "formatted_date": "26.10.15.(목)",
                "formatted_content": "원고가 내용증명 최고서 발송",
                "evidence_summary": "[근거 미작성]",
                "document_id": "d1",
                "page": 4,
            },
            {
                "date": "2026-09-30",
                "formatted_date": "26.9.30.(수)",
                "formatted_content": "계약 체결 및 금전 교부",
                "evidence_summary": "증제1호 26. 9. 30.자 차용증",
                "document_id": "d1",
                "page": 2,
            },
            {
                "date": "2026-10-05",
                "formatted_date": "26.10.5.(월)",
                "formatted_content": "피고의 변제기 도과",
                "evidence_summary": "갑 제2호증 통장사본",
                "document_id": "d1",
                "page": 3,
            },
        ],
    }

    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static_dir).as_posix()}": p for p in static_dir.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    def route_handler(route):
        path = urlsplit(route.request.url).path
        if path in files:
            route.fulfill(path=str(files[path]))
            return
        if path == "/api/health":
            route.fulfill(json={"status": "ok", "version": "0.22.0"})
            return
        if path in ("/api/auth/me", "/api/identity/me"):
            route.fulfill(json={"user_id": "u", "email": "tester@example.com", "display_name": "검토자", "role": "ADMIN", "authentication": "local"})
            return
        if path == "/api/verification-runs":
            route.fulfill(json={"active_count": 0, "runs": []})
            return
        if path == "/api/projects":
            route.fulfill(json=[project_data])
            return
        if path == "/api/projects/p-time":
            route.fulfill(json=project_data)
            return
        if path == "/api/projects/p-time/documents":
            route.fulfill(json=[{"id": "d1", "filename": "complaint.pdf", "included_in_verification": True}])
            return
        if path == "/api/projects/p-time/runs":
            route.fulfill(json=[run_data])
            return
        if path == "/api/projects/p-time/findings":
            route.fulfill(json=[])
            return
        if path == "/api/projects/p-time/reports":
            route.fulfill(json=[{
                "report_id": "rep-1",
                "project_id": "p-time",
                "run_id": "r-time-1234",
                "created_at": "2026-11-15T00:05:00",
                "state": "DRAFT",
                "audience": "INTERNAL",
                "snapshot_hash": "abcdef1234567890",
                "artifacts": {
                    "pdf": {"download": "/api/reports/rep-1/download?format=pdf"},
                    "docx": {"download": "/api/reports/rep-1/download?format=docx"},
                },
            }])
            return
        if path.endswith("/result") or path.endswith("/results"):
            route.fulfill(json={"summary": {}, "findings": []})
            return
        if path == "/api/projects/p-time/audit":
            route.fulfill(json={"events": []})
            return
        if path == "/api/privacy-notice":
            route.fulfill(json={"version": "v1.0", "bullets": [], "ack_label": "", "report_header": ""})
            return
        if path.endswith("/case-matrix"):
            route.fulfill(body="null", content_type="application/json")
            return
        if path == "/api/finding-categories":
            from packages.common.finding_category_map import CATEGORY_TO_TAB, FINDING_CATEGORY_MAP, get_category_counts
            route.fulfill(json={
                "categories": {ft.value: cat.value for ft, cat in FINDING_CATEGORY_MAP.items()},
                "tabs": {ft.value: CATEGORY_TO_TAB[cat].value for ft, cat in FINDING_CATEGORY_MAP.items()},
                "counts": get_category_counts(),
            })
            return
        route.fulfill(status=200, json=[])

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.route("**/*", route_handler)
        yield page
        browser.close()


def test_time_table_tab_order_chronology_and_responsive(timeline_browser_page) -> None:
    page = timeline_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    expect(page.locator(".brand-title")).to_have_text("법률문서 검증시스템")
    expect(page.locator(".brand-title")).not_to_contain_text("종합행정학교 법무교육단")

    # 스크롤을 내려도 상단 엠블럼 영역(.topbar)이 화면 최상단에 고정되는지 확인
    page.evaluate("() => { document.body.style.minHeight = '2000px'; window.scrollTo(0, 600); }")
    topbar_rect = page.locator(".topbar").evaluate("el => el.getBoundingClientRect().toJSON()")
    emblem_rect = page.locator(".brand-emblem").evaluate("el => el.getBoundingClientRect().toJSON()")
    assert 0 <= topbar_rect["top"] <= 1
    assert 0 <= emblem_rect["top"] < topbar_rect["bottom"]
    page.evaluate("() => { window.scrollTo(0, 0); document.body.style.minHeight = ''; }")

    metric_titles = page.locator("#summary .metric .metric-content span").all_inner_texts()
    assert metric_titles == [
        "AI 작성·보안 진단",
        "출처 미확인 인용",
        "법률적으로 무리한 주장",
        "Time Table",
    ]
    time_card = page.locator("#summary .metric", has_text="Time Table")
    expect(time_card).to_contain_text("완료")
    expect(time_card).to_contain_text("사실관계 정리 총 3건")
    expect(time_card.locator("svg")).to_be_visible()

    tabs = page.locator(".workspace-tabs button")
    assert tabs.count() == 6
    tab_names = [tabs.nth(i).get_attribute("data-tab") for i in range(6)]
    assert tab_names == [
        "documents",
        "ai-verification",
        "review",
        "legal-claims",
        "timeline",
        "reports",
    ]
    assert "Time Table" in (tabs.nth(4).inner_text() or "")

    time_card.click()
    panel = page.locator('section[data-panel="timeline"]')
    expect(panel).to_be_visible()

    headers = [panel.locator("#timelineTable thead th").nth(i).inner_text().strip() for i in range(3)]
    assert headers == ["일시", "내용", "관련근거"]

    rows = panel.locator("#timelineRows tr")
    assert rows.count() == 3

    dates = [rows.nth(i).locator(".timeline-date-text").inner_text().strip() for i in range(3)]
    assert dates == ["26.9.30.(수)", "26.10.5.(월)", "26.10.15.(목)"]

    ev0 = rows.nth(0).locator("td").nth(2).inner_text().strip()
    ev1 = rows.nth(1).locator("td").nth(2).inner_text().strip()
    ev2_badge = rows.nth(2).locator("td").nth(2).locator(".badge.evidence-missing")
    assert ev0 == "증제1호 26. 9. 30.자 차용증"
    assert ev1 == "갑 제2호증 통장사본"
    expect(ev2_badge).to_have_text("[근거 미작성]")

    # 보고서 탭: 점검 후 확정·고정본 무결성 제거 및 가로 일렬 배치 확인
    tabs.nth(5).click()
    reports_panel = page.locator('section[data-panel="reports"]')
    expect(reports_panel).to_be_visible()
    report_row = reports_panel.locator("#reportList .row-item").first
    expect(report_row).to_be_visible()
    expect(report_row).not_to_contain_text("점검 후 확정")
    expect(report_row).not_to_contain_text("고정본 무결성")
    expect(report_row.locator(".report-links a", has_text="PDF")).to_be_visible()
    expect(report_row.locator(".report-links a", has_text="DOCX")).to_be_visible()
    row_geom = report_row.evaluate("""el => {
        const info = el.querySelector('.report-row-info').getBoundingClientRect();
        const links = el.querySelector('.report-links').getBoundingClientRect();
        return { height: el.getBoundingClientRect().height, infoRight: info.right, linksLeft: links.left };
    }""")
    assert row_geom["linksLeft"] >= row_geom["infoRight"] - 1
    assert row_geom["height"] <= 80

    # 모바일 390px 카드 배치 및 가로 넘침 없음 확인
    tabs.nth(4).click()
    page.set_viewport_size({"width": 390, "height": 844})
    first_cell_display = rows.nth(0).locator("td").nth(0).evaluate("el => getComputedStyle(el).display")
    assert first_cell_display == "block"
    overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert not overflow
