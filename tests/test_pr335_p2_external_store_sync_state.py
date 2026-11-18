"""PR #335 보완 P2: 외부 AI 답변의 서버 저장 실패를 성공처럼 처리하지 않는다.

종전 `persistExternalStoreToServer()`는 저장 예외를 모두 삼키고 호출자에게 아무것도
돌려주지 않았다. 서버 저장이 실패해도 반영 흐름은 성공 toast를 띄워, 사용자는 다른
기기에서 복구되지 않는 상태를 저장 완료로 오해할 수 있었다.

이 시험은 (1) 서버 성공, (2) 서버 오류, (3) 복구 뒤 재시도 성공 세 경로를 구분해 본다.
프로젝트/실행이 없는 로컬 전용 화면 경로는 실패로 보지 않는다는 점도 함께 고정한다.

모든 자료는 합성 값이다.
"""
from __future__ import annotations

from playwright.sync_api import expect, sync_playwright

from test_aegislaw_261116_batch_a import _mount_page


_RESULT = {
    "status": "COMPLETED",
    "documents": [
        {
            "id": "d1",
            "filename": "합성서면.pdf",
            "quarantined": False,
            "review_items": [
                {
                    "item_id": "item_a1",
                    "kind": "CITATION",
                    "document_id": "d1",
                    "location": {"display": "2쪽"},
                    "claim_text": "판례 인용 주장",
                    "cited_authority": "대법원 2097다30001 판결",
                    "official_status": "OFFICIAL_NOT_FOUND",
                    "reference_status": "NOT_CHECKED",
                    "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
                    "severity": "HIGH",
                    "finding_ids": [],
                },
            ],
        }
    ],
}

_ANSWER = ("<<<ACAS_RESULT\n"
           "모델: 합성모델\n"
           "A1 | 판정: 불명 | 근거: 합성 근거 | 요지: 합성 요지\n"
           "ACAS_RESULT>>>")


def _apply_answer(page):
    """A표에서 프롬프트 번호를 만들고 답변 1건을 붙여넣어 반영한다."""
    page.locator('.tabs [data-tab="review"]').click()
    bar = page.locator("#reviewTableActions")
    bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
    bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
    dlg = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
    dlg.locator("textarea").fill(_ANSWER)
    dlg.get_by_role("button", name="저장").click()
    page.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()


def _fail_put(route):
    """external-ai-answers PUT만 서버 오류로 만든다(조회는 기본 처리로 넘긴다)."""
    if route.request.method.upper() == "PUT":
        return route.fulfill(status=500, json={"detail": "synthetic server error"})
    return route.fallback()


def test_server_success_shows_no_unsynced_warning():
    """대조군 1: 서버 저장이 되면 미동기화 표시가 없고 서버에 답변이 남는다."""
    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=_RESULT, server_store=store)
        _apply_answer(page)
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        expect(page.locator(".external-sync-warning")).to_have_count(0)
        assert store["saved"] is True
        assert "A1" in (store["answers"] or {})
        browser.close()


def test_server_error_marks_browser_only_and_keeps_answer():
    """양성 1: 서버 저장이 실패하면 '이 브라우저에만 저장됨'을 표시하고 답변은 로컬에 남긴다."""
    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=_RESULT, server_store=store)
        page.route("**/external-ai-answers", _fail_put)
        _apply_answer(page)

        # 답변은 현재 브라우저에 남아 화면에 보인다
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        # 서버 저장이 확인되지 않았음을 화면이 밝힌다
        warning = page.locator(".external-sync-warning")
        expect(warning).to_be_visible()
        expect(warning).to_contain_text("이 브라우저에만 저장됨")
        expect(warning.get_by_role("button", name="서버에 다시 저장")).to_be_visible()
        # 서버에는 저장되지 않았다
        assert store["saved"] is False
        browser.close()


def test_retry_after_recovery_clears_warning_and_saves_to_server():
    """양성 2: 네트워크가 복구된 뒤 재시도하면 서버에 저장되고 표시가 사라진다."""
    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=_RESULT, server_store=store)
        page.route("**/external-ai-answers", _fail_put)
        _apply_answer(page)
        expect(page.locator(".external-sync-warning")).to_be_visible()
        assert store["saved"] is False

        page.unroute("**/external-ai-answers", _fail_put)   # 서버 복구
        page.locator(".external-sync-warning").get_by_role("button", name="서버에 다시 저장").click()

        expect(page.locator(".external-sync-warning")).to_have_count(0)
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        assert store["saved"] is True
        assert "A1" in (store["answers"] or {})
        browser.close()


def test_local_only_screen_path_is_not_treated_as_failure():
    """대조군 2: 서버 저장 대상이 아닌 로컬 전용 화면(server_store 없음)은 실패로 보지 않는다."""
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=_RESULT, server_store=None)
        _apply_answer(page)
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        expect(page.locator(".external-sync-warning")).to_have_count(0)
        browser.close()
