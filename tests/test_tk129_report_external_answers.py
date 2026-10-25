# -*- coding: utf-8 -*-
"""TK-129 (2026-10-25 사용자 요구) 표에 반영한 외부 AI 답변을 보고서에 싣는다.

원문: "AI 검토내용이 표에 반영된 후 다시 보고서를 생성할때, 그 내용이 보고서 내용에 반영되도록 기능구현을 하면,
보고서가 브라우저 저장된 AI 답변을 담을 수 있지 않을까?"
"""
from __future__ import annotations

import copy
import io
import json
import zipfile
from urllib.parse import urlsplit

import openpyxl
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

from apps.api.schemas import ReportRequest
from apps.api.workspace import ReportReview
from apps.api.snapshot_store import unpack as unpack_snapshot
from test_report_completion import create, download, finalize, report_case  # noqa: F401
import test_tk126_flat_tabs_answer_import as screen

TITLE = "외부 AI 참고 의견 (사용자 입력, 공식 확인 아님)"


def _with_table_items(case):
    result = copy.deepcopy(case.run.result_json)
    doc = result["documents"][0]
    doc["review_items"] = [{"item_id": "d1_CITATION_cit_1", "kind": "CITATION", "cited_authority": "대법원 2022다99999 판결",
                            "claim_text": "청구권 행사 기한 주장"}]
    doc["engine_data"]["rag"] = {"observations": [{"claim_id": "c1", "claim_quote": "참고문헌과 다른 주장 문장",
                                                    "relationship": "CONTRADICTS"}]}
    case.run.result_json = result
    case.session.commit()


ANSWERS = [
    {"code": "A1", "item_id": "d1_CITATION_cit_1", "verdict": "부존재", "basis": "해당 사건번호 없음",
     "summary": "같은 쟁점의 실제 판례 확인 필요", "applied_at": "2026. 10. 25. 오후 1:00"},
    {"code": "B1", "item_id": "d1_REFERENCE_c1", "verdict": "불일치", "basis": "민법 제543조",
     "summary": "=HYPERLINK(\"https://invalid.example\") 해지 의사표시 필요", "applied_at": ""},
]


def _create(case, answers, formats, audience="INTERNAL"):
    response = case.client.post("/api/projects/p1/reports",
                                json={"audience": audience, "formats": formats, "external_ai_answers": answers})
    assert response.status_code == 201, response.text
    return response.json()


def test_answers_are_frozen_into_every_format_and_survive_finalize(report_case):  # noqa: F811
    case = report_case
    _with_table_items(case)
    draft = _create(case, ANSWERS, ["pdf", "docx", "xlsx", "json"])
    final = finalize(case, draft)
    assert final.status_code == 201, final.text
    for report in (draft, final.json()):
        pdf = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(download(case, report, "pdf"))).pages)
        xml = zipfile.ZipFile(io.BytesIO(download(case, report, "docx"))).read("word/document.xml").decode()
        workbook = openpyxl.load_workbook(io.BytesIO(download(case, report, "xlsx")))
        payload = json.loads(download(case, report, "json"))
        for text in (pdf, xml):
            assert "외부 AI 참고 의견" in text and "부존재" in text and "민법 제543조" in text
        sheet = workbook["외부AI참고의견"]
        rows = [[c.value for c in row] for row in sheet.iter_rows()]
        assert rows[0] == ["번호", "대상", "판정", "근거", "요지", "반영 시각"]
        # 대상 문구는 브라우저 값이 아니라 고정 결과의 표 항목에서 찾는다.
        assert rows[1][:3] == ["A1", "대법원 2022다99999 판결", "부존재"]
        assert rows[2][1] == "참고문헌과 다른 주장 문장"
        assert str(rows[2][4]).startswith("'=")  # 수식으로 실행되지 않게 막는다
        assert [a["code"] for a in payload["review_snapshot"]["external_ai_answers"]] == ["A1", "B1"]


def test_unknown_table_item_is_rejected_and_no_answers_keep_snapshot_unchanged(report_case):  # noqa: F811
    case = report_case
    _with_table_items(case)
    bad = case.client.post("/api/projects/p1/reports", json={"formats": ["json"], "external_ai_answers": [
        {**ANSWERS[0], "item_id": "other-run-item"}]})
    assert bad.status_code == 422 and "other-run-item" in bad.text
    assert case.client.post("/api/projects/p1/reports", json={"formats": ["json"], "external_ai_answers": [
        {**ANSWERS[0], "code": "C1"}]}).status_code == 422
    plain = create(case, ["json"])
    snapshot = unpack_snapshot(case.storage, case.session.get(ReportReview, plain["report_id"]).review_snapshot)
    assert "external_ai_answers" not in snapshot


def test_shareable_report_masks_personal_data_in_answers(report_case):  # noqa: F811
    case = report_case
    _with_table_items(case)
    answers = [{**ANSWERS[0], "summary": "원고 홍길동 user@example.com 관련 판례 없음"}]
    draft = _create(case, answers, ["json", "docx"], "SHAREABLE")
    output = download(case, draft, "json").decode()
    xml = zipfile.ZipFile(io.BytesIO(download(case, draft, "docx"))).read("word/document.xml").decode()
    for text in (output, xml):
        assert "관련 판례 없음" in text and "홍길동" not in text and "user@example.com" not in text


def test_report_job_request_round_trips_answers():
    request = ReportRequest(formats=["json"], external_ai_answers=ANSWERS)
    assert ReportRequest(**request.model_dump()).external_ai_answers == request.external_ai_answers


def test_report_dialog_sends_answers_reflected_in_table():
    bodies = []
    with sync_playwright() as p:
        browser, page = screen._page(p, [])
        page.on("request", lambda r: bodies.append(r.post_data_json) if r.url.endswith("/report-jobs") and r.method == "POST" else None)
        page.route("**/api/projects/p1/report-jobs", lambda route: route.fulfill(json={
            "job_id": "j1", "state": "FAILED", "stage": "", "percent": 0, "error": "시험 중단", "formats": ["json"]}))
        page.locator('.tabs [data-tab="review"]').click()
        bar = page.locator("#reviewTableActions")
        bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dialog = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dialog.locator("textarea").fill("<<<ACAS_RESULT\nA1 | 판정: 부존재 | 근거: 없음 | 요지: 확인 필요\nACAS_RESULT>>>")
        dialog.get_by_role("button", name="저장").click()
        page.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()
        page.locator("#reportBtn").click()
        report = page.get_by_role("dialog", name="검토 보고서 초안")
        checkbox = report.get_by_label("표에 반영한 외부 AI 답변 1건을 '외부 AI 참고 의견(공식 확인 아님)'으로 함께 싣기")
        expect(checkbox).to_be_checked()
        report.get_by_role("button", name="초안 생성").click()
        page.wait_for_timeout(500)
        assert bodies and bodies[-1]["external_ai_answers"][0]["code"] == "A1"
        assert bodies[-1]["external_ai_answers"][0]["item_id"] == "item_a"
        assert bodies[-1]["external_ai_answers"][0]["verdict"] == "부존재"
        browser.close()
