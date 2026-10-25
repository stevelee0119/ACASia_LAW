# TK-126 0.14.0 화면 오구현 보완: '확인 방법' 삭제·프롬프트 버튼 강조·셀 넘침·3단 독립 탭·배포 캐시 (P1, 사용자 요구 미이행 결함)
- 근거: 사용자 개선안(2026-10-19) 3나·3다(제목)·4항, 사용자 지적(2026-10-25). 평가 측 원인 분석: HISTORY 2026-10-25 '0.14.0 화면 오구현 원인'.
- 기준 SHA: Steve `b68e70f`(= 운영 main `28d3397` 제품). 줄 번호는 이 SHA 기준.
- 분류: `fixed`(사용자 요구 미이행·표시 결함) + `changed`. **사용자 확인 뒤 수용**(AGENT_ROLES 2.1 '사용자 요구 원문 대조 수용').

## 사용자 원문
- (10-19, 3나) "타당성에 대해 사용자에게 검토해서 검토상태, 의견, 담당자를 기재하도록 하지 말고, 확인이 필요한 내용이 어떤 것인지를 요약해서 설명해 주는게 좋을 것 같아. 이 프로그램의 목적은 … 사용자에게 서면과 관련해 어떤 점을 의심하고 재검증해야 하는지를 명확하게 인지시켜주는 거야."
- (10-19, 4) "'판례·법령·주요참고문헌 인용 오류·미확인 검토 탭에서 '법률상 무리한 주장'이라고 정리하고 있는 부분들을 분리해서 [주장, 쟁점] 탭으로 옮기는 것 … [AI 작성여부] - [출처가 확인되지 않는 판례, 법령 등] - [법률적으로 무리한 주장]의 체계"
- (10-25, 1) "확인대상과 의심 사유는 설명을 하되, … 엘박스에 입력해 실제 존재하는 판례, 법령인지 검증할 수 있도록 프롬프트를 생성 … 쓸데없는 '확인방법'만 각 항별로 유사하게 반복되어 있는 것은 불필요 … 엘박스/AI 검증 프롬프트 버튼은 너무 작아 눈에 잘 띄지 않아."
- (10-25, 2) "법리검토(법령 규정 적용 배제) 등과 관련된 부분이 표의 해당 셀을 넘어가서 다른 셀과 중복되어 읽을 수 없도록 되어 있어."
- (10-25, 4) "3번째 탭의 주장, 쟁점은 두번째 탭의 '법률적으로 무리한 주장' 부분을 별도 탭으로 옮기고, 현재 내용은 없애는 것으로 개편 …"
- (10-25, 평가 측 확인) 배포 뒤 브라우저가 0.13.1 화면 파일을 계속 써서 사용자가 캐시를 지운 뒤에야 0.14.0 화면이 보였다.

## 원문 대응표 (수용 기준)
| # | 원문 | 확인할 화면·동작 |
|---|---|---|
| 1 | 확인 대상·의심 사유만, '확인 방법' 반복 삭제 | 확인할 항목·법률적으로 무리한 주장 표 4열에 '확인 대상'·'의심 사유'(·'상세 법리 의견' 접힘)만 있고 '확인 방법' 줄이 없다 |
| 2 | 엘박스/AI 검증 프롬프트 버튼이 눈에 띄게 | 확인할 항목 탭에서 표 **위**의 띠에 큰 버튼('📋 엘박스/AI 검증 프롬프트 만들기')이 있다. LOCAL_ONLY·대상 0건이면 숨김(기존 규칙 유지) |
| 3 | 셀 넘침 없음 | 긴 판정 문구(예: '법리 검토(법정 규정 적용 배제): …')가 3열 안에서 줄바꿈되고 4열과 겹치지 않는다 |
| 4 | 3번째 탭 = 법률적으로 무리한 주장, 주장·쟁점 내용 삭제 | 검증·검토 아래 탭이 'AI 작성·보안 진단 / 확인할 항목 / 법률적으로 무리한 주장' 3개. 3번째 탭에 3단 표만 있고 쟁점·요건사실·당사자 주장·변호사 판단 표가 없다. 확인할 항목 탭에는 3단 표가 없다 |
| 5 | 배포 뒤 새 화면 | `/`·`/static/*` 응답에 `Cache-Control: no-cache`(ETag 재확인). 배포 뒤 일반 새로고침으로 새 화면이 보인다 |

## 평가 측 사전 검증(임시 사본, 저장소 밖)
- 아래 '고칠 것'을 `b68e70f` 사본에 그대로 적용했다.
- 화면 캡처 2장(확인할 항목·법률적으로 무리한 주장, 긴 판정 문구 주입)으로 대응표 1~4를 확인했다.
- 관련 시험 전체 통과: `tests/acceptance`, `tests/test_frontend_*.py`, `test_f1_*`, `test_f2_*`, `test_tk88_three_tier_review.py`, `test_external_ai_prompt*.py`, `test_tk61_layout_browser.py`, `test_upload_privacy_notice_browser.py`, `test_api.py`, `test_drive_rag_relevance.py`.
- 단, 아래 '시험' 절의 수정을 함께 적용한 상태에서의 결과다. 수정하지 않으면 옛 구조를 단언하는 10건이 실패한다(회귀가 아니라 옛 요구를 담은 단언).
- `check_test_edits --base origin/Steve_ACASiaLAW` 통과.
- 보호 시험 `tests/acceptance/test_f1_screen_protected.py`는 평가 측이 평가 PR로 먼저 고친다. 확인 탭에 `legal-claims`를 추가했고, 현재 코드에서도 통과한다.
- 미검증: 실제 운영 데이터, 모바일 폭(390px) 화면.

## 고칠 것 (`b68e70f` 기준)
1. **'확인 방법' 삭제:** `apps/web/static/app.js` 2148~2167행(`// 3) 확인 방법` 블록 전체)을 지운다. 확인 대상·의심 사유·상세 법리 의견은 그대로 둔다.
2. **프롬프트 버튼 강조·위치:** `apps/web/index.html`의 `<div id="reviewTableActions" class="review-table-actions" hidden></div>`를 표 아래에서 빼서 `hallucinationSection` 바로 뒤, `#reviewTable`의 `.table-wrap` 앞에 둔다. 클래스는 `review-table-actions review-prompt-bar`로 한다. `app.js` 2429행 버튼 문구를 `"📋 엘박스/AI 검증 프롬프트 만들기"`, 2434행 클래스를 `"primary external-ai-prompt-btn"`으로 바꾼다. `styles.css`에 다음을 더한다.
   ```css
   .review-prompt-bar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:12px 0 14px;padding:12px 14px;border:1px solid var(--line);border-radius:8px;background:#f3f8f6}
   .review-prompt-bar[hidden]{display:none}
   .review-prompt-bar .external-ai-prompt-btn{font-size:15px;font-weight:600;padding:10px 18px;min-height:44px}
   ```
3. **셀 넘침:** 원인은 `.badge`(`styles.css` 483행~)의 `white-space: nowrap`이 3열 `span.badge.validity-verdict`(app.js `renderReviewRow`)에도 걸리는 것이다. 다음을 더한다(짧은 등급 표시는 그대로 nowrap).
   ```css
   .review-items-table .validity-verdict,.tier3-table .validity-verdict{display:inline-block;max-width:100%;white-space:normal;overflow-wrap:anywhere;word-break:keep-all;line-height:1.45}
   .review-items-table td,.tier3-table td{overflow-wrap:anywhere}
   ```
4. **3단 독립 탭:**
   - `index.html` 11행: `<button data-tab="issues">주장·쟁점</button>` → `<button data-tab="legal-claims">법률적으로 무리한 주장</button>`.
   - `index.html` 14행 review 패널 안의 `<section id="tier3Section" …>…</section>`을 빼고, 15행 issues 패널 전체를 다음으로 바꾼다: `<section data-panel="legal-claims" hidden><div class="toolbar"><h2>법률적으로 무리한 주장</h2></div>` + 옮긴 `tier3Section`(제목 h4는 안내 문장 `<p id="tier3Title" class="muted">출처는 확인되나 판례·법령 취지와 맞지 않거나 참고자료와 모순되는 주장입니다. 인용 자체가 확인되지 않는 항목은 '확인할 항목' 탭에 있습니다.</p>`로) + `</section>`. `#tier3Table`·`#tier3Rows`·`#tier3Empty` id는 유지한다.
   - `workflow.js` 8행 탭 목록 `"issues"` → `"legal-claims"`, 304행 `tab === "issues"` → `tab === "legal-claims"`, 307~313행 issues 패널 툴바·`issueWorkbench` 생성 코드를 지운다(`renderMatrix`는 `issueWorkbench`가 없으면 바로 돌아간다, 141행).
   - `app.js` 624행 `renderIssues();`와 2583~2604행 `renderIssues` 함수를 지운다. 2798행 `["editProject", "editIssues"]` → `["editProject"]`.
   - 상호 참조 단추: 2071행 `"3단 무리한 주장 확인 →"`·`switchTab("review")` → `"법률적으로 무리한 주장 탭에서 확인 →"`·`switchTab("legal-claims")`. 2077행 `"2단 출처 부존재 확인 →"` → `"확인할 항목 탭에서 출처 확인 →"`(이동 탭 `review` 유지).
   - 쟁점·주장 API·DB(`/issues`, `case-matrix`, `review-workflows`)와 보고서의 3단 소제목은 이번에 지우지 않는다(화면에서만 제거).
5. **배포 캐시:** `apps/api/main.py` 300행 `app.mount("/static", …)` 바로 뒤에 다음 미들웨어를 둔다.
   ```python
   @app.middleware("http")
   async def _web_revalidate(request, call_next):
       response = await call_next(request)
       path = request.url.path
       if (path == "/" or path.startswith("/static/")) and "cache-control" not in response.headers:
           response.headers["Cache-Control"] = "no-cache"
       return response
   ```

## 시험 (구현 측이 고치고, 대응표 '전 요구 → 새 확인 위치'를 PR에 낸다)
- `tests/test_frontend_admin.py` 314·323·328행: `"issues"` → `"legal-claims"`.
- `tests/test_f2_review_screen_browser.py`:
  - 3단 표 단언(381~393·425·512행 부근)은 `legal-claims` 탭을 연 뒤 `section[data-panel="legal-claims"]`에서 확인한다. 확인할 항목 패널에는 `.tier3-table`이 0개임을 단언한다.
  - '확인 방법' 단언(400·447~448·478~479행)은 `.summary-action` 0개 단언으로 바꾼다.
- `tests/test_tk88_three_tier_review.py`: 497행 앞에서 `legal-claims` 탭을 클릭한다. 525~526행 상호 참조 문구를 새 문구로 바꾼다.
- `tests/test_external_ai_prompt.py`: 50행 클래스 접두 단언과 '표 위' 위치 단언(`index('id="reviewTableActions"') < index('id="reviewTable"')`), 215행 새 버튼 문구.
- 새 시험(구현 측):
  - `/`·`/static/app.js` 응답의 `Cache-Control: no-cache`(TestClient).
  - 긴 판정 문구 행에서 `.validity-verdict`의 `getBoundingClientRect().right`가 자기 `td`의 right를 넘지 않음(브라우저).
- 시험 함수 삭제는 없다. 단언을 옮기거나 반대로 바꾸는 것뿐이다(평가 측 사전 검증에서 `check_test_edits` 통과).

## 수용 기준
- 원문 대응표 1~5를 평가 측 화면 캡처로 확인한 뒤 **사용자 확인**을 받는다.
- 탐지 diff 0, 고정·은퇴 점수 불변. 필수 CI 성공.
- 위 '고칠 것' 밖의 변경을 섞지 않는다(TK-127·128은 별도 PR).
