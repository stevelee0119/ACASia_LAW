# 사유 문서: TK-87 검토 화면 개편에 따른 레거시 인라인 워크플로 조작 시험 삭제 및 단언 축소 사유

- **문서 번호:** `requests/98_tk87_test_deletion_rationale.md`
- **작성일:** 2026-10-21
- **작성자:** Antigravity (구현 에이전트)
- **대상 티켓:** TK-87 (검토 화면 행별 워크플로 상태·우선순위·담당자 입력 제거 및 실효 4열 '확인이 필요한 내용' 요약 전환)
- **관련 커밋:** `76f2feb`, `cdaaebc`, `a9e9f07` 및 후속 보완 커밋

---

## 1. 삭제된 시험 목록
1. `tests/test_f2_review_screen_browser.py::test_f2_inline_workflow_manipulation`
2. `tests/test_f2_review_screen_browser.py::test_f2_inline_workflow_agreed_manipulation`

---

## 2. 단언 감소 (Assertion Reduction) 시험 3건
1. `tests/test_f2_review_screen_browser.py::test_f2_checkboxes_and_batch_review` (2 → 0):
   - 일괄 검토 체크박스(`selectAllFindings`, 개별 행 체크박스) 및 일괄 상태 변경 액션 바 제거에 따라 해당 조작 단언 2건 제거.
2. `tests/test_f2_review_screen_browser.py::test_f2_derived_findings_bundle_and_multi_save` (4 → 0):
   - 행별 워크플로 저장 버튼(`saveWorkflow`) 및 다중 상태 저장 트리거 제거에 따라 관련 단언 4건 제거.
3. `tests/test_frontend_metric_explain.py::test_pending_and_status_metrics_explain_themselves` (3 → 2):
   - 기존의 검토상태 필터(`reviewFilter`) 값 단언을 4열 `#reviewTable` 보임 확인으로 변경 (검토상태 필터 DOM 제거에 따른 변경, 1건 감소).

---

## 3. 삭제 및 변경 사유 (기능적 근거)

### (1) 기능 삭제에 따른 시험 폐지 (TK-87 요구사항 1)
- **배경:** 기존 검토 화면(`review`)의 4열에 위치하던 행별 인라인 상태 변경 셀렉트박스(`inline-status-select`), 우선순위 셀렉트박스(`inline-priority-select`), 담당자 텍스트 입력창(`inline-assignee-input`), 일괄 변경 체크박스(`selectAllFindings`) 등 복잡한 워크플로 관리 UI가 실무적 활용도 저하로 인해 전면 제거되었습니다.
- **삭제 타당성:** 
  - 위 2개 시험은 브라우저에서 인라인 셀렉트박스를 조작하여 `review_status`를 `ACCEPTED`, `FALSE_POSITIVE`, `RESOLVED` 등으로 변경하고, 이를 일괄 제출하거나 담당자를 입력하는 '행별 인라인 워크플로 전이'를 검증하는 테스트였습니다.
  - 해당 UI 요소 및 관련 이벤트 핸들러가 제품 코드(`apps/web/static/app.js`, `apps/web/index.html`)에서 완전히 제거되고, 해당 자리가 판정 결과 기반의 '확인이 필요한 내용' 3대 요약(확인 대상, 의심 사유, 확인 방법)으로 대체되었으므로, 존재하지 않는 UI 컨트롤 조작 시험은 기능 삭제 원칙에 따라 제거되었습니다.

### (2) 대체 및 보존된 검증 체계
- **화면 검증 대체:** `tests/test_f2_review_screen_browser.py::test_f2_review_summary_content_elements` 및 `test_f2_review_summary_reason_truncation_and_location_display`에서 4열 요약 블록의 3대 필수 요소(확인 대상, 의심 사유 축약, 확인 방법 문구 조합) 렌더링 및 모의 데이터의 실제 필드값 반영 단언을 철저히 검증합니다.
- **보고서 사전 점검(preflight) 보존 및 강화:** 신규 서버 시험 `tests/test_review_items_preflight.py` (3건)을 신설하여:
  1) `test_unresolved_required_when_only_unavailable_sources_exist`: 조회 실패 출처 시 확인 요구 검증
  2) `test_unresolved_required_when_only_unverified_items_exist`: 미확인 항목 시 확인 요구 검증
  3) `test_unresolved_not_required_when_only_review_records_incomplete`: 검토 기록 미완료만으로는 확인이 요구되지 않음(TK-87 요구사항 3) 검증
  을 완벽하게 수행합니다.
