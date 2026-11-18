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
    confirm_dlg = page.get_by_role("dialog", name="표에 반영할 답변 1건 확인")
    confirm_dlg.get_by_role("button", name="표에 반영").click()
    expect(confirm_dlg).to_have_count(0)


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


def test_reload_after_server_failure_preserves_unsynced_answer_and_warning_then_retries():
    """변별 ①·②: 서버 저장 실패 뒤 새로고침해도 로컬 답변과 미동기화 표시가 유지되고, 이후 재시도로 서버에 저장된다."""
    from frontend_helpers import select_first_project

    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=_RESULT, server_store=store)
        page.locator('.tabs [data-tab="review"]').click()
        bar = page.locator("#reviewTableActions")
        # 탐침 2 경로: 프롬프트 생성을 먼저 눌러도 빈 답변 스냅샷이 서버 판본(saved=true)이 되지 않아야 한다
        bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        assert store["saved"] is False

        page.route("**/external-ai-answers", _fail_put)
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dlg = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dlg.locator("textarea").fill(_ANSWER)
        dlg.get_by_role("button", name="저장").click()
        page.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()

        expect(page.locator(".external-sync-warning")).to_be_visible()
        assert store["saved"] is False

        # ① 새로고침 뒤에도 로컬 답변과 미동기화 경고가 그대로 남아 있어야 한다
        page.reload()
        select_first_project(page)
        page.locator('.tabs [data-tab="review"]').click()
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        warning = page.locator(".external-sync-warning")
        expect(warning).to_be_visible()
        expect(warning).to_contain_text("이 브라우저에만 저장됨")

        # ② 그 상태에서 서버 복구 뒤 '서버에 다시 저장'을 누르면 서버에 저장되고 경고가 사라진다
        page.unroute("**/external-ai-answers", _fail_put)
        warning.get_by_role("button", name="서버에 다시 저장").click()
        expect(page.locator(".external-sync-warning")).to_have_count(0)
        assert store["saved"] is True
        assert "A1" in (store["answers"] or {})
        browser.close()


def test_reload_after_partial_server_save_and_subsequent_failure_keeps_latest_local():
    """탐침 1 경로: A1 서버 저장 성공 뒤 PUT 차단 중 A1·A2를 반영하고 새로고침해도 최신 로컬(A1·A2)이 서버 구판본(A1)에 덮이지 않는다."""
    from frontend_helpers import select_first_project

    result_two = {
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
                        "claim_text": "판례 인용 주장 1",
                        "cited_authority": "대법원 2097다30001 판결",
                        "official_status": "OFFICIAL_NOT_FOUND",
                        "reference_status": "NOT_CHECKED",
                        "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
                        "severity": "HIGH",
                        "finding_ids": [],
                    },
                    {
                        "item_id": "item_a2",
                        "kind": "CITATION",
                        "document_id": "d1",
                        "location": {"display": "3쪽"},
                        "claim_text": "판례 인용 주장 2",
                        "cited_authority": "대법원 2097다30002 판결",
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
    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=result_two, server_store=store)
        _apply_answer(page)
        assert store["saved"] is True
        assert list(store["answers"].keys()) == ["A1"]

        # PUT 차단 상태에서 A1 + A2 반영
        page.route("**/external-ai-answers", _fail_put)
        bar = page.locator("#reviewTableActions")
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dlg = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dlg.locator("textarea").fill(
            "<<<ACAS_RESULT\n"
            "모델: 합성모델\n"
            "A1 | 판정: 불명 | 근거: 합성 근거 1 | 요지: 합성 요지 1\n"
            "A2 | 판정: 부존재 | 근거: 합성 근거 2 | 요지: 합성 요지 2\n"
            "ACAS_RESULT>>>"
        )
        dlg.get_by_role("button", name="저장").click()
        page.get_by_role("dialog", name="표에 반영할 답변 2건 확인").get_by_role("button", name="표에 반영").click()
        expect(page.locator(".external-sync-warning")).to_be_visible()

        # 새로고침 뒤에도 A2가 서버 구판본(A1)에 의해 소실되지 않아야 한다
        page.reload()
        select_first_project(page)
        page.locator('.tabs [data-tab="review"]').click()
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        expect(page.locator("#aiVerificationRows tr", has_text="2097다30002")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A2")
        expect(page.locator(".external-sync-warning")).to_be_visible()
        browser.close()


def test_reload_and_fresh_context_restore_synced_server_snapshot():
    """대조군 ③·④: 서버 저장이 성공하면 새로고침 및 새 브라우저 문맥(빈 localStorage)에서 서버 판본이 경고 없이 복원된다."""
    from frontend_helpers import select_first_project

    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser1, _ctx1, page1 = _mount_page(p, result_data=_RESULT, server_store=store)
        _apply_answer(page1)
        assert store["saved"] is True

        # ③ 같은 브라우저에서 새로고침
        page1.reload()
        select_first_project(page1)
        page1.locator('.tabs [data-tab="review"]').click()
        expect(page1.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        expect(page1.locator(".external-sync-warning")).to_have_count(0)
        browser1.close()

        # ④ 다른 브라우저 문맥(새 context, 로컬 저장소 비움)에서 서버 판본 복원
        browser2, _ctx2, page2 = _mount_page(p, result_data=_RESULT, server_store=store)
        page2.locator('.tabs [data-tab="review"]').click()
        expect(page2.locator("#aiVerificationRows tr", has_text="2097다30001")
               .locator(".external-ai-answer")).to_contain_text("합성모델 답변 A1")
        expect(page2.locator(".external-sync-warning")).to_have_count(0)
        browser2.close()


def test_code_reassignment_deletes_last_answer_from_local_and_server_without_resurrection():
    """R1 변별: 코드 재할당으로 마지막 답변이 삭제되면 로컬과 서버 모두에서 삭제되어 새로고침·새 문맥에서도 되살아나지 않는다."""
    from frontend_helpers import select_first_project

    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser1, _ctx1, page1 = _mount_page(p, result_data=_RESULT, server_store=store)
        page1.locator('.tabs [data-tab="review"]').click()
        bar = page1.locator("#reviewTableActions")

        # ③ 대조군: 답변이 한 번도 없던 상태에서 프롬프트 번호만 생성할 때는 서버에 빈 스냅샷을 저장하지 않는다
        bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        assert store["saved"] is False

        # 답변 1건 반영(대화상자 클릭 직후 비행 중 바로 코드 재할당이 일어나는 경합 경로 포함)
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dlg = page1.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dlg.locator("textarea").fill(_ANSWER)
        dlg.get_by_role("button", name="저장").click()
        page1.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()

        # ① 반영 클릭 직후 코드가 다른 항목(item_other)으로 재할당되어 마지막 답변 삭제
        page1.evaluate("() => { rememberPromptCodes('A', [{item_id: 'item_other'}]); renderFindings(); }")
        expect(page1.locator("#aiVerificationRows .external-ai-answer")).to_have_count(0)
        page1.wait_for_function("() => !loadExternalStore().pendingSync")
        assert page1.evaluate("() => externalAnswersForReport().length") == 0
        assert store["saved"] is True
        assert store["answers"] == {}
        assert store["codes"] == {"A1": "item_other"}

        # ② 새로고침 뒤에도 옛 답변이 되살아나지 않는다
        page1.reload()
        select_first_project(page1)
        page1.locator('.tabs [data-tab="review"]').click()
        expect(page1.locator("#aiVerificationRows .external-ai-answer")).to_have_count(0)
        expect(page1.locator(".external-sync-warning")).to_have_count(0)
        assert page1.evaluate("() => externalAnswersForReport().length") == 0
        browser1.close()

        # ② 새 브라우저 문맥(빈 localStorage)에서도 서버 판본이 비어 있어 옛 답변이 되살아나지 않는다
        browser2, _ctx2, page2 = _mount_page(p, result_data=_RESULT, server_store=store)
        page2.locator('.tabs [data-tab="review"]').click()
        expect(page2.locator("#aiVerificationRows .external-ai-answer")).to_have_count(0)
        expect(page2.locator(".external-sync-warning")).to_have_count(0)
        assert page2.evaluate("() => externalAnswersForReport().length") == 0
        browser2.close()


def test_server_save_and_reload_repeated_ten_times_never_shows_false_unsynced_warning():
    """R2 변별: 서버 저장 성공 직후 새로고침을 10회 연속 반복해도 미동기화 경고가 뜨지 않고 unsynced가 남지 않는다."""
    from frontend_helpers import select_first_project

    store: dict = {"saved": False, "codes": {}, "answers": {}}
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=_RESULT, server_store=store)
        for i in range(10):
            page.locator('.tabs [data-tab="review"]').click()
            bar = page.locator("#reviewTableActions")
            bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
            bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
            dlg = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
            dlg.locator("textarea").fill(
                f"<<<ACAS_RESULT\n모델: 합성모델\nA1 | 판정: 불명 | 근거: 합성 근거 {i} | 요지: 합성 요지 {i}\nACAS_RESULT>>>"
            )
            dlg.get_by_role("button", name="저장").click()
            confirm_dlg = page.get_by_role("dialog", name="표에 반영할 답변 1건 확인")
            confirm_dlg.get_by_role("button", name="표에 반영").click()
            if i % 2 == 0:
                expect(confirm_dlg).to_have_count(0)
            page.reload()
            select_first_project(page)
            page.locator('.tabs [data-tab="review"]').click()
            expect(page.locator("#aiVerificationRows tr", has_text="2097다30001")
                   .locator(".external-ai-answer")).to_contain_text(f"합성 요지 {i}")
            expect(page.locator(".external-sync-warning")).to_have_count(0)
            assert page.evaluate("() => Boolean(loadExternalStore().unsynced)") is False
            assert store["saved"] is True
        browser.close()


