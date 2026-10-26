# TK-126 0.14.0 화면 오구현 보완 + 상단 평면 탭 5개 (P1, 사용자 요구 미이행 결함)
- 근거: 사용자 개선안(2026-10-19) 3나·3다(제목)·4항, 사용자 지적(2026-10-25 두 차례). 평가 측 원인 분석: HISTORY 2026-10-25 '0.14.0 화면 오구현 원인'.
- 기준 SHA: Steve `b68e70f`(= 운영 main `28d3397` 제품). 줄 번호는 이 SHA 기준.
- 분류: `fixed`(사용자 요구 미이행·표시 결함) + `changed`. **사용자 확인 뒤 수용**(AGENT_ROLES 2.1 '사용자 요구 원문 대조 수용').
- 같은 PR: TK-127(참고문헌 행 통합)·TK-128(프롬프트·답변 반영). 세 티켓이 같은 파일을 고치므로 평가 측이 한 사본에서 함께 사전 검증했다. 사전 검증한 수정 전체: `docs/handoff/patches/TK-126-128_prevalidated_b68e70f.diff`.

## 사용자 원문
- (10-19, 3나) "타당성에 대해 사용자에게 검토해서 검토상태, 의견, 담당자를 기재하도록 하지 말고, 확인이 필요한 내용이 어떤 것인지를 요약해서 설명해 주는게 좋을 것 같아. 이 프로그램의 목적은 … 사용자에게 서면과 관련해 어떤 점을 의심하고 재검증해야 하는지를 명확하게 인지시켜주는 거야."
- (10-19, 4) "'판례·법령·주요참고문헌 인용 오류·미확인 검토 탭에서 '법률상 무리한 주장'이라고 정리하고 있는 부분들을 분리해서 [주장, 쟁점] 탭으로 옮기는 것 … [AI 작성여부] - [출처가 확인되지 않는 판례, 법령 등] - [법률적으로 무리한 주장]의 체계"
- (10-25, 1) "확인대상과 의심 사유는 설명을 하되, … 엘박스에 입력해 실제 존재하는 판례, 법령인지 검증할 수 있도록 프롬프트를 생성 … 쓸데없는 '확인방법'만 각 항별로 유사하게 반복되어 있는 것은 불필요 … 엘박스/AI 검증 프롬프트 버튼은 너무 작아 눈에 잘 띄지 않아."
- (10-25, 2) "법리검토(법령 규정 적용 배제) 등과 관련된 부분이 표의 해당 셀을 넘어가서 다른 셀과 중복되어 읽을 수 없도록 되어 있어."
- (10-25, 4) "3번째 탭의 주장, 쟁점은 두번째 탭의 '법률적으로 무리한 주장' 부분을 별도 탭으로 옮기고, 현재 내용은 없애는 것으로 개편 …"
- (10-25, 사전 검증 화면을 본 뒤) "현재 최 상단 탭이 [자료][검증,검토][보고서] 형식으로 되어 있고, 각 주제별 세부 탭을 별도로 두고 있는데 [자료][AI작성, 보안진단][출처가 확인되지 않는 항목][법률적으로 무리한 주장][보고서] 로 통합해서 구성하는게 어떨까? 세부탭을 별도로 두지 않아도 되니 편의성이 높아질 것 같아."
- (10-25, 평가 측 확인) 배포 뒤 브라우저가 0.13.1 화면 파일을 계속 써서 사용자가 캐시를 지운 뒤에야 0.14.0 화면이 보였다.

## 원문 대응표 (수용 기준)
| # | 원문 | 확인할 화면·동작 |
|---|---|---|
| 1 | 확인 대상·의심 사유만, '확인 방법' 반복 삭제 | 두 표의 4열에 '확인 대상'·'의심 사유'(·'상세 법리 의견' 접힘)만 있고 '확인 방법' 줄이 없다 |
| 2 | 엘박스/AI 검증 프롬프트 버튼이 눈에 띄게 | 표 **위** 띠에 큰 버튼('📋 엘박스/AI 검증 프롬프트 만들기'). LOCAL_ONLY·대상 0건이면 숨김 |
| 3 | 셀 넘침 없음 | 긴 판정 문구가 3열 안에서 줄바꿈되고 4열과 겹치지 않는다 |
| 4 | 3번째 탭 = 법률적으로 무리한 주장, 주장·쟁점 내용 삭제 | '법률적으로 무리한 주장' 탭에 3단 표만 있다. 쟁점·요건사실 표가 없다. '출처가 확인되지 않는 항목' 탭에는 3단 표가 없다 |
| 5 | 배포 뒤 새 화면 | `/`·`/static/*` 응답에 `Cache-Control: no-cache` |
| 6 | 상단 탭 5개, 세부 탭 없음 | 상단에 [자료][AI 작성·보안 진단][출처가 확인되지 않는 항목][법률적으로 무리한 주장][보고서] 다섯 개만 보이고 '검증·검토' 묶음 단추·하위 탭 줄이 없다. 탭 이름 '확인할 항목'은 모두 '출처가 확인되지 않는 항목'으로 바뀐다. 390px 폭에서 탭이 줄바꿈되어 가로 스크롤이 없다 |
| 7 | (10-25 사용자 결정) "활동 기록은 삭제(보고서 탭 하단에 다시 세부 탭이 생성되지 않도록), 현재 [보고서] 탭의 내용만 계속 활용 예정" | 활동 기록 탭·패널·버튼이 화면 어디에도 없다(`[data-panel="audit"]`·`[data-tab="audit"]` 0개). 서버의 감사 기록·`/projects/{id}/audit` API는 그대로 둔다. 상단 '작업 기록'(검증 작업 기록, operations.js)은 다른 기능이라 유지 |

## 평가 측 사전 검증(임시 사본, 저장소 밖)
- '고칠 것' 전체(TK-127·128 포함)를 `b68e70f` 사본에 적용했다. 수정본: `docs/handoff/patches/TK-126-128_prevalidated_b68e70f.diff`(보호 시험 수정은 평가 PR #182에 있으므로 뺐다).
- 화면 캡처 5장(출처 미확인 탭·무리한 주장 탭·답변 붙여넣기·반영 미리보기·390px 탭)을 사용자에게 제시했다(10-25).
- 시험 1,410건 실패 0(건너뜀 25): `tests/acceptance`, `tests/test_frontend_*.py`, `test_external_ai_prompt*.py`, `test_f1_ai_security_tab_browser.py`, `test_f2_review_screen_browser.py`, `test_tk61_layout_browser.py`, `test_tk88_three_tier_review.py`, `test_upload_privacy_notice_browser.py`, 새 `test_tk126_flat_tabs_answer_import.py`, `test_workspace.py`, `test_api.py`.
- `check_test_edits --base b68e70f` 통과(시험 삭제·약화 없음).
- 미검증: 실제 운영 데이터(사용자 서면) 화면, 운영 Drive 대조 결과가 실제로 행에 붙는 비율.

## 고칠 것 (`b68e70f` 기준)
1. **'확인 방법' 삭제:** `apps/web/static/app.js` 2148~2167행(`// 3) 확인 방법` 블록 전체)을 지운다.
2. **프롬프트 버튼 강조·위치:** `index.html`의 `#reviewTableActions`를 `hallucinationSection` 뒤, `#reviewTable` 앞으로 옮기고 클래스를 `review-table-actions review-prompt-bar`로 한다. `app.js` 2429행 문구 `"📋 엘박스/AI 검증 프롬프트 만들기"`, 2434행 클래스 `"primary external-ai-prompt-btn"`. CSS는 수정본 `styles.css` 끝의 `.review-prompt-bar` 규칙.
3. **셀 넘침:** `.badge`(`styles.css` 483행~)의 `white-space: nowrap`이 3열 `span.badge.validity-verdict`에도 걸리는 것이 원인. `.review-items-table .validity-verdict, .tier3-table .validity-verdict`에 `white-space:normal; overflow-wrap:anywhere; word-break:keep-all; display:inline-block; max-width:100%`.
4. **3단 독립 탭:** `index.html` 11행 `issues` 탭 → `legal-claims`('법률적으로 무리한 주장'), review 패널의 `#tier3Section`을 새 `section[data-panel="legal-claims"]`로 옮긴다(id 유지). `workflow.js` 304행 `"issues"` → `"legal-claims"`, 307~313행 issues 툴바·`issueWorkbench` 생성 삭제. `app.js` 624행 `renderIssues();`·2583~2604행 `renderIssues`·2798행 `"editIssues"` 삭제. 상호 참조 단추 2071행 → `"법률적으로 무리한 주장 탭에서 확인 →"`/`switchTab("legal-claims")`, 2077행 → `"출처가 확인되지 않는 항목 탭에서 확인 →"`. 쟁점 API·DB는 지우지 않는다.
5. **배포 캐시:** `apps/api/main.py` 300행 `app.mount("/static", …)` 뒤에 `_web_revalidate` 미들웨어(`/`·`/static/*`에 `Cache-Control: no-cache`, 이미 있으면 두지 않음).
6. **평면 탭 5개(새 요구):**
   - 원인: `workflow.js` 6~33행이 상단 '묶음 단추'(`#workspaceGroups`: 자료·검증·검토·보고서)를 만들고, `syncNavigation`이 `.tabs` 줄에서 선택한 묶음의 탭만 보이게 한다. 그래서 탭이 두 줄(묶음 → 하위 탭)이다.
   - 고칠 것: `groups`·`lastTabs`·`syncNavigation`·`initNavigation`과 314행 `initNavigation();` 호출, 반환 객체의 `syncNavigation`을 지운다. `app.js` `switchTab`의 `workflowUI.syncNavigation(tab);` 줄도 지운다.
   - `index.html` 11행 `.tabs`를 `class="tabs workspace-tabs"`로 하고 단추를 아이콘+이름으로: `files` 자료 / `shield-check` AI 작성·보안 진단 / `search-x` 출처가 확인되지 않는 항목 / `scale` 법률적으로 무리한 주장 / `file-chart-column` 보고서. `audit` 단추는 지운다. 아이콘은 모두 `vendor/lucide.min.js`에 있다(평가 측 확인).
   - 활동 기록 화면 삭제(사용자 결정): `index.html` 17행 `section[data-panel="audit"]` 전체, `app.js` `switchTab`의 `if (tab === "audit") loadAudit()…` 줄, `loadAudit` 함수, `$("refreshAudit").onclick` 줄. 서버 감사 API는 그대로.
   - '확인할 항목' 문구를 모두 '출처가 확인되지 않는 항목'으로: `index.html` 11·13(배너 링크)·14(h2)·15(3단 안내)행, `app.js` 1240행(`button("확인할 항목에서 보기"…)`), 1779행 주석, 2077행 상호 참조, 2488행 오류 문구.
   - CSS: `.workspace-tabs`(아이콘 정렬, 최소 높이 44px), 700px 이하 `flex-wrap:wrap; white-space:normal`(가로 스크롤 금지).

## 시험 (구현 측이 고치고, PR에 '전 요구 → 새 확인 위치' 대응표를 낸다)
- 수정본의 시험 변경을 그대로 쓴다. 요지:
  - '검증·검토' 묶음 단추 클릭 줄 삭제(`test_external_ai_prompt_browser.py`·`test_f1_ai_security_tab_browser.py`·`test_f2_review_screen_browser.py`·`test_frontend_citation_groups.py`·`test_tk61_layout_browser.py`·`test_tk88_three_tier_review.py`). `.tabs button[data-tab=…]` 클릭은 그대로 동작한다.
  - `test_frontend_admin.py::test_grouped_workbench_preserves_all_tools_and_selected_case`: 묶음 3개 단언 → 평면 탭 5개·이름 순서·활동 기록 탭·패널 0개·390px에서 `.tabs` 넘침 없음.
  - `test_frontend_report_progress.py`: `#workspaceGroups` 보고서 클릭 줄 삭제.
  - 문구 변경 단언: `test_frontend_metric_explain.py`('출처가 확인되지 않는 항목에서 보기'), `test_f1_ai_security_tab_browser.py` 배너, `test_tk88_three_tier_review.py` 상호 참조.
  - 이전 사전 검증분(3단 탭·확인 방법·버튼 위치)은 이전 판과 같다.
- 시험 함수 삭제는 없다.

## 수용 기준
- 원문 대응표 1~7을 평가 측 화면 캡처로 확인한 뒤 **사용자 확인**을 받는다(10-25 사전 검증 화면 6장 사용자 확인 '그대로 진행').
- 탐지 diff 0, 고정·은퇴 점수 불변(화면·API만 바뀐다). 필수 CI 성공.
- 수정본 밖의 변경을 섞지 않는다.

## 10-25 보충 (전체 시험에서 발견)
- `tests/test_drive_rag_relevance.py::test_web_shows_drive_health_selection_and_duplicates`가 TK-127의 '참고문헌 처리 기록 → 표 위 접힘 상태 줄' 변경으로 실패했다(접힌 상세 안의 `.reference-section`이 보이지 않아 스크린샷 시간 초과). 옛 화면 단언이므로 평가 측이 고쳤다: `switchTab('review')` 뒤와 `renderFindings()` 재렌더 뒤에 `#referenceStatus summary`를 펼친다. 수정본에 포함(19개 파일). 그 파일 47건 실패 0.
- 전체 `tests`(TK-129까지 적용한 사본, 4묶음 병렬): 10,462건 중 실패 5 → 위 1건(수정) + 시간 시험 4건(병렬 실행 부하, 단독 재실행 통과).

