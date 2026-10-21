# 사유 문서: TK-87 검토 화면 개편에 따른 레거시 인라인 워크플로 조작 시험 삭제 사유

- **문서 번호:** `requests/96_tk87_test_deletion_rationale.md`
- **작성일:** 2026-10-21
- **작성자:** Antigravity (구현 에이전트)
- **대상 티켓:** TK-87 (검토 화면 행별 워크플로 상태·우선순위·담당자 입력 제거 및 실효 4열 '확인이 필요한 내용' 요약 전환)
- **관련 커밋:** `76f2feb` 및 후속 보완 커밋

---

## 1. 삭제된 시험 목록
1. `tests/acceptance/test_f2_review_screen_browser.py::test_f2_inline_workflow_manipulation`
2. `tests/acceptance/test_f2_review_screen_browser.py::test_f2_inline_workflow_agreed_manipulation`

---

## 2. 삭제 사유 및 기능적 근거

### (1) 기능 삭제에 따른 시험 폐지 (TK-87 요구사항 1)
- **배경:** 기존 검토 화면(`review`)의 4열에 위치하던 행별 인라인 상태 변경 셀렉트박스(`inline-status-select`), 우선순위 셀렉트박스(`inline-priority-select`), 담당자 텍스트 입력창(`inline-assignee-input`), 일괄 변경 체크박스(`selectAllFindings`) 등 복잡한 워크플로 관리 UI가 실무적 활용도 저하로 인해 전면 제거되었습니다.
- **삭제 타당성:** 
  - 위 2개 시험은 브라우저에서 인라인 셀렉트박스를 조작하여 `review_status`를 `ACCEPTED`, `FALSE_POSITIVE`, `RESOLVED` 등으로 변경하고, 이를 일괄 제출하거나 담당자를 입력하는 '행별 인라인 워크플로 전이'를 검증하는 테스트였습니다.
  - 해당 UI 요소 및 관련 이벤트 핸들러가 제품 코드(`apps/web/static/app.js`, `apps/web/index.html`)에서 완전히 제거되고, 해당 자리가 판정 결과 기반의 '확인이 필요한 내용' 3대 요약(확인 대상, 의심 사유, 확인 방법)으로 대체되었으므로, 존재하지 않는 UI 컨트롤 조작 시험은 기능 삭제 원칙에 따라 제거되었습니다.

### (2) 대체 및 보존된 검증 체계
- **검토 상태 보존:** 백엔드의 finding workflow 데이터 모델 및 검증 완료 판정 기준은 그대로 유지되며, 신규 시험 `tests/test_review_summary_screen.py` 및 보완된 서버 시험 `tests/test_review_items_preflight.py`에서 기존 필드 기반 요약 렌더링 및 확인 필요 조건 검증을 완전하게 대체 수행합니다.
