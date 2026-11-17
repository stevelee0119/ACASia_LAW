"""TK-188: Time Table 사건 문장 뒤의 인접 호증 연결 및 경계 보존 시험."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from frontend_helpers import select_first_project
from packages.claim_engine.contradiction import build_timeline
from packages.claim_engine.exhibits import canonical, parse_exhibits
from packages.claim_engine.extractor import extract_events
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.document_engine.simple_parsers import TextParser
from packages.report_engine.exporters import to_payload

ROOT = Path(__file__).resolve().parents[1]


def _doc_from_text(text: str, document_id: str = "doc-tk188") -> NormalizedDocument:
    parser = TextParser()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    try:
        return parser.parse(
            str(tmp_path),
            document_id=document_id,
            filename=f"{document_id}.txt",
            mime_type="text/plain",
            sha256="a" * 64,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def _assert_all_ref_spans_exist(doc: NormalizedDocument, events) -> None:
    blocks = {b.block_id: b.text for b in doc.prose_blocks()}
    for event in events:
        block_text = blocks[event.block_id]
        assert event.span is not None
        assert event.description in block_text
        for ref in event.evidence_references:
            start, end = ref["span"]
            assert block_text[start:end] == ref["raw_text"]


@pytest.mark.parametrize(
    "body,expected_canonical,expected_substrings",
    [
        (
            "2025년 4월 11일 임차인이 임대인에게 보증금 반환 통지서를 발송하였다. 갑 제1호증 내용증명.",
            [("갑", 1, ())],
            ["갑 제1호증"],
        ),
        (
            "2025년 5월 2일 시공사가 수정 공정표를 교부하였다. 을 제4호증의 3 수정 공정표.",
            [("을", 4, (3,))],
            ["을 제4호증의 3"],
        ),
        (
            "2025년 6월 14일 위탁사가 검수 결과를 회신하였다. (갑 제7호증의 1, 2 검수결과서)",
            [("갑", 7, (1, 2))],
            ["갑 제7호증의 1, 2"],
        ),
        (
            "2025년 7월 9일 대리인이 합의안과 세금계산서를 함께 송부하였다. 소갑 제2호증 및 을 제5호증의 1 내지 3.",
            [("갑", 2, ()), ("을", 5, (1, 2, 3))],
            ["소갑 제2호증", "을 제5호증의 1 내지 3"],
        ),
        (
            "2025년 8월 20일 발주자가 현장 사진을 촬영하였다(병 제3호증). 을가 제1호증 촬영일지.",
            [("병", 3, ()), ("을가", 1, ())],
            ["병 제3호증", "을가 제1호증"],
        ),
    ],
)
def test_adjacent_evidence_binds_positive_axes_with_exact_spans(body, expected_canonical, expected_substrings):
    doc = _doc_from_text(body)
    events = extract_events(doc, project_id="P-188", source_run_id="run-188")
    assert len(events) == 1
    _assert_all_ref_spans_exist(doc, events)

    timeline = build_timeline(events)
    assert len(timeline) == 1
    summary = timeline[0]["evidence_summary"]
    for token in expected_substrings:
        assert token in summary
    assert canonical(parse_exhibits(summary)) == sorted(expected_canonical)


def test_attachment_adjacent_sentence_binds():
    doc = _doc_from_text("2025년 9월 3일 감정인이 측량 도면을 제출하였다. 별지 제2호 측량도면.")
    events = extract_events(doc, project_id="P-188")
    assert len(events) == 1
    _assert_all_ref_spans_exist(doc, events)
    timeline = build_timeline(events)
    assert timeline[0]["evidence_summary"] == "별지 제2호"


@pytest.mark.parametrize(
    "body,expected_row_count,expected_summaries",
    [
        # 1) 다음 문단의 별개 호증은 앞 사건에 붙지 않는다.
        (
            "2025년 3월 1일 매수인이 해약 통지를 하였다.\n\n갑 제9호증 해약통지서.",
            1,
            ["[근거 미작성]"],
        ),
        # 2) 같은 문단이라도 다음 날짜의 호증은 앞 날짜 사건에 붙지 않는다.
        (
            "2025년 3월 1일 원고가 견적을 문의하였다. 2025년 3월 5일 피고가 최종 단가를 통지하였다. 을 제8호증 단가표.",
            2,
            ["[근거 미작성]", "을 제8호증"],
        ),
        # 3) 일반 조문·법조문 번호·전화번호 등은 호증으로 연결하지 않는다.
        (
            "2025년 3월 1일 근로기준법 적용을 통보하였다. 민법 제750조 제1항 및 형법 제347조 제2호 참조.",
            1,
            ["[근거 미작성]"],
        ),
        # 4) 증거 존재 부정·미제출·위조 다툼 문장은 자동 연결하지 않는다.
        (
            "2025년 3월 1일 현금을 교부하였다. 그러나 갑 제1호증 영수증은 존재하지 않는다.",
            1,
            ["[근거 미작성]"],
        ),
        (
            "2025년 3월 1일 인수증을 작성하였다. 을 제2호증은 위조되었고 제출되지 않았다.",
            1,
            ["[근거 미작성]"],
        ),
        # 5) 한 문장 안의 복수 날짜 사건 또는 여러 사건 총칭 참조는 모호하므로 자동 연결하지 않는다.
        (
            "2025년 3월 1일 시안을 보내고 2025년 3월 4일 최종본을 수령하였다. 갑 제3호증.",
            2,
            ["[근거 미작성]", "[근거 미작성]"],
        ),
        (
            "2025년 3월 1일 회의를 소집하였다. 위 각 사건에 관하여 갑 제4호증.",
            1,
            ["[근거 미작성]"],
        ),
        # 6) 중간에 별도 비호증 문장이 끼어들면 건너뛰어 뒤 호증을 붙이지 않는다.
        (
            "2025년 3월 1일 정산서를 송부하였다. 이후 별도 협의가 이어졌다. 갑 제5호증 합의서.",
            1,
            ["[근거 미작성]"],
        ),
        # 7) 전언(REPORTED)·가정(CONDITIONAL)·부정(DENIED) 경계를 넘는 인접 호증은 자동 확정하지 않는다.
        (
            "피고는 2025년 3월 1일 변제하였다고 주장한다. 을 제6호증 주장서.",
            1,
            ["[근거 미작성]"],
        ),
        # 8) 콜론형 이름 표기·기업 소유/귀속·새 행위 서술(보관 등)이 포함된 구절은 앞 사건에 자동 결속하지 않는다.
        (
            "2025년 3월 1일 회의가 열렸다. 김철수: 갑 제1호증 계약서.",
            1,
            ["[근거 미작성]"],
        ),
        (
            "2025년 3월 1일 회의가 열렸다. 주식회사 한빛의 갑 제1호증 계약서.",
            1,
            ["[근거 미작성]"],
        ),
        (
            "2025년 3월 1일 회의가 열렸다. 증인 김철수 갑 제1호증 보관.",
            1,
            ["[근거 미작성]"],
        ),
    ],
)
def test_negative_controls_do_not_misbind_adjacent_evidence(body, expected_row_count, expected_summaries):
    doc = _doc_from_text(body)
    events = extract_events(doc, project_id="P-188")
    timeline = build_timeline(events)
    assert len(timeline) == expected_row_count
    assert [row["evidence_summary"] for row in timeline] == expected_summaries


@pytest.mark.parametrize(
    "body",
    [
        "2025년 3월 1일 회의가 열렸다. 김철수: 갑 제1호증 계약서.",
        "2025년 3월 1일 회의가 열렸다. 주식회사 한빛의 갑 제1호증 계약서.",
        "2025년 3월 1일 회의가 열렸다. 증인 김철수 갑 제1호증 보관.",
    ],
)
def test_adjacent_evidence_rejects_subject_attribution_and_action(body):
    doc = _doc_from_text(body)
    events = extract_events(doc, project_id="P-188")
    assert len(events) == 1
    _assert_all_ref_spans_exist(doc, events)
    timeline = build_timeline(events)
    assert len(timeline) == 1
    assert timeline[0]["evidence_summary"] == "[근거 미작성]"


def test_paired_documents_and_same_date_events_chronology_and_stance_preserved():
    from datetime import datetime

    base_text = "\n\n".join([
        "사건경위 테스트 문서",
        "2025년 11월 12일 갑 회사가 물품 발주서를 송부하였다. 갑 제10호증 발주서.",
        "2025년 10월 3일 을 회사가 단가 문의서를 보냈다. 갑 제11호증 문의서.",
        "2025년 11월 12일 을 회사가 대체 품목 제안서를 보냈다. 을 제12호증의 2 제안서.",
        "상대방은 2025년 11월 20일 잔금을 수령했다고 주장한다. 수령 여부는 다투고 있다.",
        "만약 2025년 12월 5일 위약벌이 발생한다면 공제 범위를 따진다. 이는 가정이다.",
    ])
    revised_text = (
        base_text
        .replace("2025년 10월 3일", "2025년 10월 4일")
        .replace("2025년 11월 20일", "2025년 11월 21일")
    )

    doc_a = _doc_from_text(base_text, document_id="doc-a")
    doc_b = _doc_from_text(revised_text, document_id="doc-b")
    events_a = extract_events(doc_a, project_id="P-188")
    events_b = extract_events(doc_b, project_id="P-188")
    _assert_all_ref_spans_exist(doc_a, events_a)
    _assert_all_ref_spans_exist(doc_b, events_b)

    tl_a = build_timeline(events_a)
    tl_b = build_timeline(events_b)

    # 3개 인접 호증 모두 연결(양 문서 합계 6/6), 같은 날 2사건 보존, 전언/가정 구분 유지
    assert [r["evidence_summary"] for r in tl_a] == [
        "갑 제11호증",
        "갑 제10호증",
        "을 제12호증의 2",
        "[근거 미작성]",
        "[근거 미작성]",
    ]
    assert [r["evidence_summary"] for r in tl_b] == [
        "갑 제11호증",
        "갑 제10호증",
        "을 제12호증의 2",
        "[근거 미작성]",
        "[근거 미작성]",
    ]
    assert [r["date"] for r in tl_a] == ["2025-10-03", "2025-11-12", "2025-11-12", "2025-11-20", "2025-12-05"]
    assert [r["stance"] for r in tl_a] == ["ASSERTED", "ASSERTED", "ASSERTED", "REPORTED", "CONDITIONAL"]

    # Report payload export와 동일한 timeline/events가 유지되는지 검증
    run_stub = SimpleNamespace(
        run_id="r-188",
        project_id="P-188",
        state="COMPLETED",
        verification_key="vk-188",
        started_at=datetime(2026, 11, 16, 0, 0, 0),
        finished_at=datetime(2026, 11, 16, 0, 1, 0),
        scores={},
        timeline=tl_a,
        unavailable_sources=[],
        unverified_items=[],
        errors=[],
        input_snapshot={},
        run_manifest={},
        documents=[
            SimpleNamespace(
                document_id="doc-a",
                filename="doc-a.txt",
                normalized=doc_a,
                quarantined=False,
                rag_indexable=True,
                warnings=[],
                authorship={},
                masked_preview="",
                citations=[],
                claims=[],
                entities=[],
                events=[e.to_dict() for e in events_a],
                engine_data={},
                source_records=[],
                findings=[],
            )
        ],
        project_findings=[],
        model_executions=[],
    )
    payload = to_payload(run_stub)
    assert [row["evidence_summary"] for row in payload["timeline"]] == [row["evidence_summary"] for row in tl_a]

    # UI 표 렌더링 및 Markdown 복사 결과가 엔진 출력과 일치하는지 검증
    static_dir = ROOT / "apps" / "web" / "static"
    files = {f"/static/{p.relative_to(static_dir).as_posix()}": p for p in static_dir.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps" / "web" / "index.html"
    run_obj = {
        "id": "r-188",
        "project_id": "P-188",
        "state": "COMPLETED",
        "progress": 1,
        "stage_message": "",
        "document_ids": ["doc-a"],
        "scores": {},
        "unverified_items": [],
        "errors": [],
        "unavailable_sources": [],
        "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-11-16T00:00:00",
        "timeline": tl_a,
        "findings": [],
    }
    proj = {"id": "P-188", "name": "TK188 검증", "can_delete": True, "document_count": 1}

    def route_handler(route):
        path = urlsplit(route.request.url).path
        if path in files:
            route.fulfill(path=str(files[path]))
            return
        if path == "/api/health":
            route.fulfill(json={"status": "ok", "version": "0.22.0"})
            return
        if path in ("/api/auth/me", "/api/identity/me"):
            route.fulfill(json={"user_id": "u", "role": "ADMIN", "authentication": "local"})
            return
        if path == "/api/verification-runs":
            route.fulfill(json={"active_count": 0, "runs": []})
            return
        if path == "/api/projects":
            route.fulfill(json=[proj])
            return
        if path == "/api/projects/P-188":
            route.fulfill(json=proj)
            return
        if path == "/api/projects/P-188/documents":
            route.fulfill(json=[{"id": "doc-a", "filename": "doc-a.txt", "included_in_verification": True}])
            return
        if path == "/api/projects/P-188/runs":
            route.fulfill(json=[run_obj])
            return
        if path == "/api/finding-categories":
            route.fulfill(json={"categories": {}, "tabs": {}, "counts": {}})
            return
        if path.endswith("/case-matrix"):
            route.fulfill(body="null", content_type="application/json")
            return
        route.fulfill(json=[])

    launch_kwargs = {"headless": True}
    if os.environ.get("LV_TEST_BROWSER_CHANNEL"):
        launch_kwargs["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.add_init_script(
                "window.__copiedMd = '';"
                "Object.defineProperty(navigator, 'clipboard', {"
                "  value: { writeText: async (t) => { window.__copiedMd = t; } }, configurable: true"
                "});"
            )
            page.route("**/*", route_handler)
            page.goto("http://tk188.test/")
            select_first_project(page)
            page.locator('.tabs button[data-tab="timeline"]').click()
            expect(page.locator("#timelineRows tr")).to_have_count(5)
            cells = [page.locator("#timelineRows tr").nth(i).locator("td").nth(2).inner_text().strip() for i in range(5)]
            assert cells == ["갑 제11호증", "갑 제10호증", "을 제12호증의 2", "[근거 미작성]", "[근거 미작성]"]

            page.locator("#copyTimelineMarkdown").click()
            md = page.evaluate("window.__copiedMd")
            for idx, expected_ev in enumerate(["갑 제11호증", "갑 제10호증", "을 제12호증의 2", "[근거 미작성]", "[근거 미작성]"]):
                assert md.splitlines()[2 + idx].endswith(f"| {expected_ev} |")
        finally:
            browser.close()
