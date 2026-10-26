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
from packages.report_engine.external_answers import (
    EXTERNAL_AI_HEADERS,
    EXTERNAL_AI_NOTICE,
    EXTERNAL_AI_STATUS_LABEL,
    EXTERNAL_AI_TITLE,
)
from test_report_completion import create, download, finalize, report_case  # noqa: F401
import test_tk126_flat_tabs_answer_import as screen

# 사건번호 형태(2022다99999 등) 리터럴 의존을 방지하기 위해 일반 합성 인용구 사용
SYNTHETIC_CITATION = "예시 판례 인용구"

ANSWERS = [
    {"code": "A1", "item_id": "d1_CITATION_cit_1", "verdict": "부존재", "basis": "해당 판례 없음",
     "summary": "같은 쟁점의 실제 판례 확인 필요", "applied_at": "2026. 10. 25. 오후 1:00"},
    {"code": "B1", "item_id": "d1_REFERENCE_c1", "verdict": "불일치", "basis": "민법 제543조",
     "summary": "=HYPERLINK(\"https://invalid.example\") 해지 의사표시 필요", "applied_at": ""},
]


def _with_table_items(case):
    result = copy.deepcopy(case.run.result_json)
    doc = result["documents"][0]
    doc["review_items"] = [{"item_id": "d1_CITATION_cit_1", "kind": "CITATION", "cited_authority": SYNTHETIC_CITATION,
                            "claim_text": "청구권 행사 기한 주장"}]
    doc["engine_data"]["rag"] = {"observations": [{"claim_id": "c1", "claim_quote": "참고문헌과 다른 주장 문장",
                                                    "relationship": "CONTRADICTS"}]}
    case.run.result_json = result
    case.session.commit()


def _create(case, answers, formats, audience="INTERNAL"):
    response = case.client.post("/api/projects/p1/reports",
                                json={"audience": audience, "formats": formats, "external_ai_answers": answers})
    assert response.status_code == 201, response.text
    return response.json()


def test_answers_are_frozen_into_every_format_and_survive_finalize(report_case):  # noqa: F811
    """모든 지원 포맷(PDF, Word, Excel, JSON)에 비공식성 표시가 일관되게 포함되는지 검증."""
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

        # PDF 및 DOCX 비공식성 표시 검증
        for text in (pdf, xml):
            assert EXTERNAL_AI_TITLE in text and "부존재" in text and "민법 제543조" in text
            assert EXTERNAL_AI_NOTICE in text or "공식 확인 아님" in text

        # XLSX 안내 행 및 안내 열 검증
        sheet = workbook["외부AI참고의견"]
        rows = [[c.value for c in row] for row in sheet.iter_rows()]
        # 1행: 비공식성 안내 행
        assert rows[0][0] == f"[안내] {EXTERNAL_AI_TITLE}: {EXTERNAL_AI_NOTICE}"
        # 2행: 헤더 (공식 여부 안내 열 포함)
        assert rows[1] == EXTERNAL_AI_HEADERS
        # 3행: 첫 번째 데이터 행
        assert rows[2][:3] == ["A1", SYNTHETIC_CITATION, "부존재"]
        assert rows[2][6] == EXTERNAL_AI_STATUS_LABEL
        assert rows[3][1] == "참고문헌과 다른 주장 문장"
        assert str(rows[3][4]).startswith("'=")  # 수식 인젝션 방지
        assert rows[3][6] == EXTERNAL_AI_STATUS_LABEL

        # JSON official=false 메타데이터 및 안내문 검증
        snapshot = payload["review_snapshot"]
        assert snapshot["external_ai_metadata"]["official"] is False
        assert snapshot["external_ai_metadata"]["notice"] == EXTERNAL_AI_NOTICE
        answers = snapshot["external_ai_answers"]
        assert len(answers) == 2
        for a in answers:
            assert a["official"] is False
            assert a["source"] == "external_ai"
            assert a["notice"] == EXTERNAL_AI_NOTICE


def test_csv_scope_and_notice_included_in_metadata(report_case):  # noqa: F811
    """CSV 지원 범위(단일 표 특성상 제외됨) 및 비공식성 안내가 메타데이터에 명시되는지 검증."""
    case = report_case
    _with_table_items(case)
    draft = _create(case, ANSWERS, ["csv"])
    csv_bytes = download(case, draft, "csv")
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "external_ai_scope" in csv_text
    assert "공식 확인 아님" in csv_text


def test_legacy_fallback_items_and_observation_without_claim_id_are_accepted(report_case):  # noqa: F811
    """review_items가 없는 레거시 fallback 행 및 claim_id 없는 관찰 행도 422 없이 성공적으로 고정되는지 검증."""
    case = report_case
    result = copy.deepcopy(case.run.result_json)
    doc = result["documents"][0]
    # review_items를 완전히 비움 (레거시 환경 재현)
    doc["review_items"] = []
    doc["ai_hallucination_table"] = [
        {"citation_id": "fb_cit_1", "cited_authority": "폴백 판례 인용구", "claim_text": "폴백 주장", "validity_verdict": "미확인"}
    ]
    # claim_id가 없는 참고문헌 관찰
    doc["engine_data"]["rag"] = {
        "observations": [
            {"claim_quote": "claim_id 없는 관찰 문장", "relationship": "INSUFFICIENT"}
        ]
    }
    case.run.result_json = result
    case.session.commit()

    doc_id = doc.get("id") or doc.get("document_id")
    fallback_answers = [
        {"code": "A1", "item_id": f"{doc_id}_CITATION_fb_cit_1", "verdict": "확인", "basis": "근거", "summary": "요약", "applied_at": ""},
        {"code": "B1", "item_id": f"{doc_id}_REFERENCE_0", "verdict": "참고", "basis": "법령", "summary": "관찰 답변", "applied_at": ""},
    ]

    draft = _create(case, fallback_answers, ["json"])
    assert draft["report_id"] is not None
    payload = json.loads(download(case, draft, "json"))
    answers = payload["review_snapshot"]["external_ai_answers"]
    assert len(answers) == 2
    assert answers[0]["code"] == "A1" and answers[0]["target"] == "폴백 판례 인용구"
    assert answers[1]["code"] == "B1" and answers[1]["target"] == "claim_id 없는 관찰 문장"


def test_unknown_table_item_and_code_conflicts_are_rejected(report_case):  # noqa: F811
    """존재하지 않는 항목이나 코드 충돌이 422로 거부되는지 검증."""
    case = report_case
    _with_table_items(case)
    # 1) 존재하지 않는 항목 ID
    bad_item = case.client.post("/api/projects/p1/reports", json={"formats": ["json"], "external_ai_answers": [
        {**ANSWERS[0], "item_id": "other-run-item"}]})
    assert bad_item.status_code == 422 and "other-run-item" in bad_item.text

    # 2) 유효하지 않은 코드 형식
    bad_code = case.client.post("/api/projects/p1/reports", json={"formats": ["json"], "external_ai_answers": [
        {**ANSWERS[0], "code": "INVALID_CODE"}]})
    assert bad_code.status_code == 422

    # 3) 동일 코드에 서로 다른 item_id 바인딩 시도
    conflict = case.client.post("/api/projects/p1/reports", json={"formats": ["json"], "external_ai_answers": [
        ANSWERS[0],
        {**ANSWERS[1], "code": "A1", "item_id": "d1_REFERENCE_c1"}
    ]})
    assert conflict.status_code == 422

    # 답변 없는 요청은 external_ai_answers 키를 생성하지 않음
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


def test_prompt_refresh_code_reuse_regression():
    """프롬프트 갱신으로 코드가 다른 행에 재할당되었을 때 이전 답변이 오염 전송되지 않는 브라우저 로직 회귀 시험."""
    bodies = []
    with sync_playwright() as p:
        browser, page = screen._page(p, [])
        page.on("request", lambda r: bodies.append(r.post_data_json) if r.url.endswith("/report-jobs") and r.method == "POST" else None)
        page.route("**/api/projects/p1/report-jobs", lambda route: route.fulfill(json={
            "job_id": "j1", "state": "FAILED", "stage": "", "percent": 0, "error": "시험 중단", "formats": ["json"]}))
        page.locator('.tabs [data-tab="review"]').click()
        bar = page.locator("#reviewTableActions")

        # 1. 초기 프롬프트 생성 (A1 = item_a 매핑)
        bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()

        # 2. 답변 붙여넣기 (A1에 대한 답변 입력 및 저장)
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dialog = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dialog.locator("textarea").fill("<<<ACAS_RESULT\nA1 | 판정: 부존재 | 근거: 없음 | 요지: 원래의견\nACAS_RESULT>>>")
        dialog.get_by_role("button", name="저장").click()
        page.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()

        # 3. 프롬프트 갱신 시뮬레이션: 코드가 다른 항목(item_other)으로 재할당됨
        # 브라우저 컨텍스트에서 rememberPromptCodes('A', [{item_id: 'item_other'}]) 호출
        page.evaluate("""() => {
            rememberPromptCodes('A', [{item_id: 'item_other'}]);
        }""")

        # 4. 보고서 생성 다이얼로그 열기
        page.locator("#reportBtn").click()
        report = page.get_by_role("dialog", name="검토 보고서 초안")
        report.get_by_role("button", name="초안 생성").click()
        page.wait_for_timeout(500)

        # 5. 검증: 코드가 재할당되었으므로 이전 A1 답변이 새 행(item_other)의 의견으로 전송되지 않아야 함
        assert bodies, "요청이 전송되어야 함"
        sent_answers = bodies[-1].get("external_ai_answers", [])
        # 이전 답변은 삭제되거나 item_other로 잘못 전송되지 않음
        assert len(sent_answers) == 0, f"재할당된 코드의 이전 답변이 전송되지 않아야 함: {sent_answers}"
        browser.close()


def test_legacy_stored_answers_without_item_id_are_excluded_regression():
    """item_id가 없는 이전 버전 localStorage 답변은 표에도 보고서 요청에도 나오지 않는 회귀 시험."""
    bodies = []
    with sync_playwright() as p:
        browser, page = screen._page(p, [])
        page.on("request", lambda r: bodies.append(r.post_data_json) if r.url.endswith("/report-jobs") and r.method == "POST" else None)
        page.route("**/api/projects/p1/report-jobs", lambda route: route.fulfill(json={
            "job_id": "j1", "state": "FAILED", "stage": "", "percent": 0, "error": "시험 중단", "formats": ["json"]}))
        page.locator('.tabs [data-tab="review"]').click()

        # 1. item_id가 없는 이전 버전 구형 답변 및 코드 재사용 매핑을 localStorage에 주입
        page.evaluate("""() => {
            const key = externalStoreKey();
            const legacyStore = {
                codes: {"A1": "item_a"},
                answers: {
                    "A1": {code: "A1", verdict: "부존재", basis: "구형근거", summary: "구형답변요약"} // item_id 없음!
                }
            };
            localStorage.setItem(key, JSON.stringify(legacyStore));
            // 표를 다시 렌더링하여 적용 시도
            renderFindings();
        }""")
        page.wait_for_timeout(300)

        # 2. UI 검증: item_id가 없으므로 표의 행에 외부 AI 답변 박스가 표시되지 않아야 함
        answers_in_table = page.locator("#aiVerificationRows .external-ai-answer")
        expect(answers_in_table).to_have_count(0)

        # 3. 프롬프트 코드를 다른 항목(item_other)에 재할당 시뮬레이션
        page.evaluate("""() => {
            rememberPromptCodes('A', [{item_id: 'item_other'}]);
            renderFindings();
        }""")
        page.wait_for_timeout(300)

        # 재할당 후에도 여전히 표에 표시되지 않아야 함
        expect(answers_in_table).to_have_count(0)

        # 4. 보고서 생성 시뮬레이션
        page.locator("#reportBtn").click()
        report = page.get_by_role("dialog", name="검토 보고서 초안")
        report.get_by_role("button", name="초안 생성").click()
        page.wait_for_timeout(500)

        # 5. API 요청 본문 검증: 구형 답변은 보고서 전송 대상에서 완전히 제외되어야 함
        assert bodies, "보고서 생성 요청이 전송되어야 함"
        sent_answers = bodies[-1].get("external_ai_answers", [])
        assert len(sent_answers) == 0, f"item_id 없는 구형 답변은 보고서 요청에 포함되지 않아야 함: {sent_answers}"
        browser.close()


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
