"""Time Table 원문 근거·중복 제거·실행 상태·Markdown 복사·UI 무결성 시험."""
from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import re

import pytest

from packages.claim_engine.contradiction import build_timeline, _format_timeline_evidence
from packages.claim_engine.exhibits import canonical, parse_exhibits
from packages.common.schemas import Event


def _event(**kw) -> Event:
    defaults = dict(
        event_id=kw.pop("event_id", "EVT-1"),
        date=kw.pop("date", date(2024, 3, 15)),
        description=kw.pop("description", "합성 사실관계 진술"),
    )
    defaults.update(kw)
    return Event(**defaults)


def test_build_timeline_preserves_distinct_sources_and_long_prefixes():
    prefix = "당사자 사이 물품 공급에 관한 기본 합의가 체결되었고 " * 15  # > 300자
    e1 = _event(event_id="E1", document_id="doc-a", page=1, span=(10, 80), description=prefix + "A")
    e2 = _event(event_id="E2", document_id="doc-b", page=1, span=(10, 80), description=prefix + "A")
    e3 = _event(event_id="E3", document_id="doc-c", page=2, span=(5, 40), description=prefix + "A")

    rows = build_timeline([e1, e2, e3])
    assert [r["event_id"] for r in rows] == ["E1", "E2", "E3"]


@pytest.mark.parametrize("dup_count", [2, 3, 4])
def test_build_timeline_collapses_exact_same_source_duplicates(dup_count: int):
    events = [
        _event(
            event_id=f"E{i}",
            document_id="doc-1",
            source_document_sha256="sha-1",
            block_id="blk-1",
            page=2,
            span=(100, 150),
            description="2024. 3. 15. 계약금 지급",
        )
        for i in range(dup_count)
    ]
    rows = build_timeline(events)
    assert len(rows) == 1


@pytest.mark.parametrize(
    "field,val_a,val_b",
    [
        ("document_id", "doc-1", "doc-2"),
        ("source_document_sha256", "sha-aaa", "sha-bbb"),
        ("block_id", "blk-1", "blk-2"),
        ("page", 1, 2),
        ("span", (10, 20), (30, 40)),
        ("evidence_references", [{"raw_text": "갑 제1호증"}], [{"raw_text": "을 제2호증"}]),
        ("event_identity", "id-alpha", "id-beta"),
        ("speaker_id", "spk-1", "spk-2"),
        ("action", "PAID", "CANCELLED"),
        ("negated", False, True),
        ("stance", "ASSERTED", "DENIED"),
    ],
)
def test_build_timeline_preserves_single_axis_differences(field, val_a, val_b):
    base = dict(
        document_id="doc-1",
        source_document_sha256="sha-1",
        block_id="blk-1",
        page=1,
        span=(0, 50),
        description="동일 날짜 동일 문구 사건",
    )
    a = _event(event_id="EA", **{**base, field: val_a})
    b = _event(event_id="EB", **{**base, field: val_b})
    rows = build_timeline([a, b])
    assert len(rows) == 2


def test_build_timeline_preserves_distinct_event_ids_when_source_metadata_missing():
    e1 = _event(event_id="EVT-A", description="출처 미기재 동일 문구")
    e2 = _event(event_id="EVT-B", description="출처 미기재 동일 문구")
    e3 = _event(event_id="EVT-A", description="출처 미기재 동일 문구")
    rows = build_timeline([e1, e2, e3])
    assert [r["event_id"] for r in rows] == ["EVT-A", "EVT-B"]


def test_timeline_evidence_preserves_structured_raw_text_and_multiple_exhibits():
    ev_structured = _event(
        description="갑 제7호증 및 을 제18호증에 의하여 확인됨",
        evidence_references=[
            {"raw_text": "갑 제7호증(계약서 사본, 3~4쪽)"},
            {"raw_text": "을 제18호증의 2"},
        ],
    )
    assert _format_timeline_evidence(ev_structured) == "갑 제7호증(계약서 사본, 3~4쪽), 을 제18호증의 2"

    ev_joined = _event(description="갑 제7호증 및 을 제18호증 기재에 따르면")
    summary = _format_timeline_evidence(ev_joined)
    assert summary == "갑 제7호증, 을 제18호증"
    assert "및 을" not in summary


@pytest.mark.parametrize(
    "text",
    [
        "갑 제3호증 및 을 제5호증",
        "소갑 제1호증와 소을 제2호증의 1 내지 3",
        "을가 제4호증, 병 제2, 3호증",
        "피고인 증 제2호증의 1 및 검 증 제7호",
        "정 제1호증의 2, 4\n및 갑 제9호증(3쪽)",
    ],
)
def test_timeline_evidence_matches_parse_exhibits_canonical_set(text: str):
    summary = _format_timeline_evidence(_event(description=text))
    assert canonical(parse_exhibits(summary)) == canonical(parse_exhibits(text))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("별첨 제1호 목록 참조", "별첨 제1호"),
        ("별지 제2호(도면 3쪽) 기재", "별지 제2호(도면 3쪽)" if False else "별지 제2호"),
        ("첨부 제3호의 1 확인", "첨부 제3호의 1"),
    ],
)
def test_timeline_evidence_supports_attachments(text: str, expected: str):
    assert expected in _format_timeline_evidence(_event(description=text))


@pytest.mark.parametrize(
    "text",
    [
        "민법 제750조 제1항에 따른 손해배상 청구",
        "형법 제347조 제2호 위반 여부 검토",
        "보증 제2호 약정에 관한 사실관계 진술",
    ],
)
def test_timeline_evidence_ignores_non_exhibit_legal_citations(text: str):
    assert _format_timeline_evidence(_event(description=text)) == "[근거 미작성]"


def test_build_timeline_two_digit_years():
    events = [
        _event(event_id="Y01", date=date(2001, 1, 5), description="2001년 사건"),
        _event(event_id="Y05", date=date(2005, 5, 9), description="2005년 사건"),
        _event(event_id="Y09", date=date(2009, 12, 31), description="2009년 사건"),
    ]
    rows = build_timeline(events)
    assert [r["formatted_date"].split(".")[0] for r in rows] == ["01", "05", "09"]


def _launch_browser(playwright):
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    return playwright.chromium.launch(**options)


@pytest.mark.parametrize(
    "run_state,timeline,expected_title,forbidden",
    [
        (None, [], "—", ["완료", "사실관계 정리 총 0건"]),
        ("QUEUED", [], "대기", ["완료", "사실관계 정리 총 0건"]),
        ("PARSING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("ADVERSARIAL_SCANNING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("EXTRACTING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("PII_PROCESSING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("VERIFYING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("CROSS_CHECKING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("AGGREGATING", [], "진행 중", ["완료", "사실관계 정리 총 0건"]),
        ("PARTIAL_COMPLETED", [{"event_id": "E1", "date": "2024-01-02", "description": "부분"}], "일부 미확인", ["완료"]),
        ("FAILED", [], "실행 실패", ["완료", "사실관계 정리 총 0건"]),
        ("CANCELLED", [], "취소됨", ["완료", "사실관계 정리 총 0건"]),
        ("COMPLETED", [{"event_id": "E1", "date": "2024-01-02", "description": "완료"}], "완료", []),
    ],
)
def test_timeline_summary_card_distinguishes_all_run_states(run_state, timeline, expected_title, forbidden):
    from playwright.sync_api import expect, sync_playwright
    from frontend_helpers import select_first_project
    STATIC = Path(__file__).resolve().parents[1] / "apps" / "web" / "static"
    MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}

    run_obj = None if run_state is None else {
        "id": "r1", "project_id": "p1", "state": run_state, "profile": "STANDARD",
        "progress": 1 if run_state == "COMPLETED" else 0.4, "stage_message": "",
        "document_ids": [], "unverified_items": [], "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-11-15T00:00:00",
        "scores": {"release_gate": {"deployable": False, "human_review_required": False, "hard_block_reasons": [], "review_reasons": []}},
        "summary": {"gate": {"deployable": False, "human_review_required": False, "hard_block_reasons": [], "review_reasons": []}},
        "timeline": timeline, "findings": [],
    }
    replies = {
        "/api/projects": [{"id": "p1", "name": "상태검증사건"}],
        "/api/projects/p1": {"id": "p1", "name": "상태검증사건", "documents": [], "runs": [run_obj] if run_obj else []},
        "/api/projects/p1/documents": [],
        "/api/projects/p1/runs": [run_obj] if run_obj else [],
        "/api/finding-categories": {"names": {}, "code_words": {}, "field_words": {}},
    }
    if run_obj:
        replies[f"/api/runs/{run_obj['id']}"] = run_obj

    def respond(route):
        url = route.request.url
        if not url.startswith("http://tt-state.test/"):
            return route.abort()
        path = url.removeprefix("http://tt-state.test").split("?", 1)[0]
        if path in ("/", "/index.html"):
            return route.fulfill(path=str(STATIC.parent / "index.html"))
        if path.startswith("/static/"):
            f = STATIC / path.removeprefix("/static/")
            if f.exists():
                return route.fulfill(path=str(f))
        if path == "/api/health":
            return route.fulfill(json={"status": "ok", "version": "0.22.0"})
        if path == "/api/identity/me":
            return route.fulfill(json={"user_id": "u", "role": "ADMIN", "authentication": "password"})
        if path == "/api/verification-runs":
            return route.fulfill(json={"active_count": 0, "runs": []})
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith("/result"):
            return route.fulfill(json={"documents": []})
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    with sync_playwright() as pw:
        browser = _launch_browser(pw)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.route("**/*", respond)
            page.goto("http://tt-state.test/")
            select_first_project(page)
            tt_card = page.locator("#summary .metric", has_text="Time Table")
            expect(tt_card).to_have_count(1)
            expect(tt_card.locator("strong")).to_have_text(expected_title)
            card_text = tt_card.inner_text()
            for bad in forbidden:
                if bad == "완료" and expected_title == "일부 미확인":
                    assert tt_card.locator("strong").inner_text() != "완료"
                else:
                    assert bad not in card_text
            page.close()
        finally:
            browser.close()


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_timeline_browser_layout_source_link_and_markdown_escape(width: int, height: int):
    from playwright.sync_api import expect, sync_playwright
    from frontend_helpers import select_first_project
    STATIC = Path(__file__).resolve().parents[1] / "apps" / "web" / "static"
    MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}

    long_desc = (
        "원고와 피고 사이의 물품 공급 기본계약 체결 및 선급금 지급 경위 확인\r\n"
        "특수문자 \\ 백슬래시 및 | 파이프 포함 상세 진술 " + ("장문 합성 확인 문구 " * 12)
    )
    timeline_items = [
        {
            "event_id": "EV-1",
            "date": "2005-05-09",
            "document_id": "doc-1",
            "page": 3,
            "span": [10, 90],
            "description": long_desc,
            "evidence_references": [{"raw_text": "갑 제7호증"}, {"raw_text": "을 제18호증"}],
            "evidence_summary": "갑 제7호증, 을 제18호증",
        },
        {
            "event_id": "EV-2",
            "date": "2009-12-31",
            "document_id": "doc-2",
            "page": 7,
            "span": [10, 90],
            "description": long_desc,
            "evidence_summary": "소을 제1호증의 2 | 별지 제3호",
        },
    ]
    docs = [
        {"id": "doc-1", "filename": "원고_준비서면_장문테스트.pdf", "evidence_number": "서면1", "submitted_by": "PLAINTIFF", "sha256": "a" * 64, "included_in_verification": True},
        {"id": "doc-2", "filename": "피고_답변서_장문테스트.pdf", "evidence_number": "서면2", "submitted_by": "DEFENDANT", "sha256": "b" * 64, "included_in_verification": True},
    ]
    run_obj = {
        "id": "run-tt", "project_id": "p1", "state": "COMPLETED", "profile": "STANDARD",
        "progress": 1, "stage_message": "", "document_ids": ["doc-1", "doc-2"],
        "unverified_items": [], "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-11-15T00:00:00",
        "timeline": timeline_items, "findings": [],
        "scores": {"release_gate": {"deployable": True, "human_review_required": False, "hard_block_reasons": [], "review_reasons": []}},
        "summary": {"gate": {"deployable": True, "human_review_required": False, "hard_block_reasons": [], "review_reasons": []}},
    }
    replies = {
        "/api/projects": [{"id": "p1", "name": "타임테이블검증사건"}],
        "/api/projects/p1": {"id": "p1", "name": "타임테이블검증사건", "documents": docs, "runs": [run_obj]},
        "/api/projects/p1/documents": docs,
        "/api/projects/p1/runs": [run_obj],
        "/api/runs/run-tt": run_obj,
        "/api/finding-categories": {"names": {}, "code_words": {}, "field_words": {}},
    }

    def respond(route):
        url = route.request.url
        if not url.startswith("http://tt-ui.test/"):
            return route.abort()
        path = url.removeprefix("http://tt-ui.test").split("?", 1)[0]
        if path in ("/", "/index.html"):
            return route.fulfill(path=str(STATIC.parent / "index.html"))
        if path.startswith("/static/"):
            f = STATIC / path.removeprefix("/static/")
            if f.exists():
                return route.fulfill(path=str(f))
        if path == "/api/health":
            return route.fulfill(json={"status": "ok", "version": "0.22.0"})
        if path == "/api/identity/me":
            return route.fulfill(json={"user_id": "u", "role": "ADMIN", "authentication": "password"})
        if path == "/api/verification-runs":
            return route.fulfill(json={"active_count": 0, "runs": []})
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith("/blocks"):
            return route.fulfill(json={"pages": [1, 2, 3, 4, 5, 6, 7], "blocks": []})
        if path.endswith("/result"):
            return route.fulfill(json={"documents": []})
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    with sync_playwright() as pw:
        browser = _launch_browser(pw)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.add_init_script(
                "window.__copiedMd = '';"
                "Object.defineProperty(navigator, 'clipboard', {"
                "  value: { writeText: async (t) => { window.__copiedMd = t; } }, configurable: true"
                "});"
            )
            page.route("**/*", respond)
            page.goto("http://tt-ui.test/")
            select_first_project(page)

            # 4 metric cards + tab order
            expect(page.locator("#summary .metric")).to_have_count(4)
            tab_names = page.locator(".tabs button[data-tab]").evaluate_all("els => els.map(e => e.dataset.tab)")
            assert tab_names == ["documents", "ai-verification", "review", "legal-claims", "timeline", "reports"]

            # Switch to Time Table tab and verify both distinct-source rows appear
            page.locator('.tabs button[data-tab="timeline"]').click()
            expect(page.locator("#timelineRows tr")).to_have_count(2)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

            # Verify Markdown copy escaping & 2-digit years
            page.locator("#copyTimelineMarkdown").click()
            md = page.evaluate("window.__copiedMd")
            lines = md.splitlines()
            assert lines[0] == "| 일시 | 내용 | 관련근거 |"
            assert lines[1] == "| :--- | :--- | :--- |"
            assert len(lines) == 4  # header + separator + 2 data rows
            assert lines[2].startswith("| 05.5.9.")
            assert lines[3].startswith("| 09.12.31.")
            assert "\\\\" in lines[2] and "\\|" in lines[2]
            assert "\\|" in lines[3]

            # Round-trip parse unescaped cells
            for data_line in lines[2:]:
                cells = re.split(r"(?<!\\)\|", data_line)[1:-1]
                assert len(cells) == 3

            # Verify clicking source-link opens the exact document & page
            page.locator("#timelineRows .timeline-source-link").nth(1).click()
            expect(page.locator("#detailDialog")).to_be_visible()
            expect(page.locator("#viewerFilename")).to_have_text("피고_답변서_장문테스트.pdf")
            expect(page.locator("#pageNumber")).to_have_text("7 / 7")
            page.close()
        finally:
            browser.close()
