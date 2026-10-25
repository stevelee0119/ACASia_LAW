# TK-128 두 표의 엘박스/AI 검증 프롬프트 + 외부 AI 답변 붙여넣기로 표 갱신 (P1, 새 기능)
- 근거: 사용자 요구(2026-10-25 세 차례). 기준 SHA Steve `b68e70f`.
- 분류: `added`. **사용자 확인 뒤 수용.** 같은 PR: TK-126·127. 사전 검증 수정본: `docs/handoff/patches/TK-126-128_prevalidated_b68e70f.diff`.

## 사용자 원문
- (10-25) "엘박스에 현재 질의하는 프롬프트 생성 기능이 있는데, 엘박스 등의 답변을 다시 입력받아 표를 업데이트 할 수 있는 기능을 구현할 수 있는지 검토해줘."
- (10-25) "3번째탭 '법률상 무리한 주장' 부분에도 엘박스/AI 검증 프롬프트를 생성하는 기능을 추가하고, 엘박스 등의 답변을 다시 입력받아 표를 업데이트 할 수 있는 기능을 구현할 수 있는지 검토"
- (10-25, 사전 검증 화면을 본 뒤) "엘박스의 답변을 다시 받아 입력받는 기능과, 입력된 내용을 표에 반영하도록 하는 기능을 실행하는 버튼은 없는 것 같고 … 두번째 파일은 엘박스 프롬프트 생성 기능, 엘박스의 답변을 다시 입력받아 입력된 내용을 표에 반영하도록 하는 기능을 실행하는 버튼 등이 부재해."

## 원칙
- 외부 AI 답변은 공식 확인이 아니다. 표에는 '외부 AI 답변(공식 확인 아님)'으로만 붙이고, 판정 배지·공식 확인 상태·등급은 바꾸지 않는다(Source First, Human Final Decision).
- 자유 서식 답변은 안정적으로 읽을 수 없으므로, 프롬프트에 항목 번호(A1…·B1…)와 고정 결과 블록을 넣고 그 블록만 읽는다.

## 원문 대응표 (수용 기준)
| # | 원문 | 확인할 화면·동작 |
|---|---|---|
| 1 | 3번째 탭에도 프롬프트 생성 | '법률적으로 무리한 주장' 표 위 띠에 '📋 엘박스/AI 검증 프롬프트 만들기'. 항목 번호 B1…, [인용]·[주장](서버에서 정책대로 가린 문장). LOCAL_ONLY·대상 0건이면 띠 숨김 |
| 2 | 답변을 다시 입력받는 버튼 | 두 표 띠 모두 '📥 외부 AI 답변 붙여넣기'. 프롬프트를 아직 만들지 않았으면 안내만 한다 |
| 3 | 입력된 내용을 표에 반영하는 버튼 | 붙여넣기 → '저장' → 미리보기 대화상자('표에 반영할 답변 n건 확인': 번호 → 행, 판정·근거·요지, 표에 없는 번호 목록) → '표에 반영' |
| 4 | 표 갱신 | 해당 행 3열에 '외부 AI 답변 A1 (공식 확인 아님)' 상자(판정·근거·요지·반영 시각, '공식 DB 재조회 전까지 위 판정 배지는 바뀌지 않습니다'). 판정 배지는 그대로 |
| 5 | (평가 측 추가 — 사용자 결정 대기) 저장 위치 | 사전 검증본은 브라우저 저장(프로젝트·실행별 키). 다른 PC·다른 검토자와 공유하려면 서버 저장이 필요하다 |

## 고칠 것 (`b68e70f` 기준, 사전 검증 완료)
1. **2단 프롬프트 번호·결과 블록:** `app.js` 362행 `buildExternalAiPromptForUnverifiedAuthorities`에 4번째 인자 `prefix = "A"`, 목록 번호 `${prefix}${idx + 1}. `. 395행 '각 항목별 상세 확인 내용' 뒤에 결과 블록을 **함수 안 문자열로** 넣는다(시험이 이 함수만 떼어 node로 실행하므로 바깥 상수를 부르면 안 된다 — 사전 검증 중 실제로 깨짐):
   ```
   [결과 블록 — 답변 맨 끝에 반드시 아래 형식 그대로]
   항목마다 한 줄씩, 위 목록 번호(A1, A2 …)를 그대로 쓰고 칸은 | 로 나눕니다.
   <<<ACAS_RESULT
   A1 | 판정: 확인/부존재/불일치/불명 | 근거: 사건번호·선고일 또는 법령·조문 | 요지: 한두 문장
   ACAS_RESULT>>>
   ```
2. **답변 읽기 `parseExternalAnswers(text)`:** 마지막 `<<<ACAS_RESULT`~`ACAS_RESULT>>>` 사이(없으면 전체)에서 줄마다 앞 `|` 제거 → `|`·`｜`로 나눔 → 첫 칸에서 `*`·`` ` ``·공백·`.` 제거 후 대문자 `^[AB]\d{1,3}$`만 받는다(마크다운 표 행도 읽힘). `판정:`·`근거:`·`요지:` 칸은 각 필드로, 이름 없는 칸은 요지에 덧붙인다. 필드마다 1,000자 상한. 같은 번호는 마지막 것.
3. **번호 ↔ 행 기억:** 프롬프트 버튼을 누를 때 `rememberPromptCodes(prefix, items)`로 `{A1: item_id…}`를 저장(같은 접두 번호는 지우고 새로). '붙여넣기'를 누를 **때** 저장된 번호로 행을 찾는다(버튼을 그릴 때 찾으면 프롬프트를 만든 뒤에도 비어 있다 — 사전 검증 중 실제로 깨짐).
4. **대화상자:** `workflowUI.modal`로 ①붙여넣기(텍스트 12줄, 결과 블록 안내) → 저장 시 해당 접두 번호가 0개면 오류 문구를 띄우고 닫지 않는다 → ②미리보기(표에 없는 번호는 '반영하지 않음' 경고, 반영할 것이 0이면 '표에 반영' 숨김) → '표에 반영' 시 저장하고 `renderFindings()`.
5. **행 표시:** `renderFindings`에서 행 수집 뒤 `applyStoredExternalAnswers(allReviewItems)`로 `item.external_ai_answer`를 붙이고, `renderReviewRow` 3열(참고문헌 상자 다음)에 `externalAnswerBlock`. 모든 값은 `node()`의 textContent로만 넣는다(HTML 해석 없음).
6. **3단 프롬프트:** `index.html` 3단 안내 뒤 `<div id="legalClaimsActions" class="review-table-actions review-prompt-bar" hidden></div>`. `renderFindings`의 2단 띠 처리(2415~2445행) 뒤, 2447행 `// 4. 하단 미확인 범위` 앞에 3단 띠: 정책 LOCAL_ONLY이거나 3단 행 0건이면 숨김. 버튼은 `action(async …)`으로 `POST /api/projects/{id}/external-ai/prompt-texts {texts:[행 claim_text…]}`를 불러 가린 문장을 받고, 인용 식별자는 MASKED일 때 `maskAuthorityIdentifier`. 번호 B1…, `buildExternalAiPromptForLegalClaims(entries, incident_date)`(역할·고지·'개인정보는 프로젝트 정책에 따라 가림'·기준 시점·[검토 대상 주장 목록]·[검토 요청 사항 1~3]·결과 블록 B).
7. **서버 가림 API:** `apps/api/routers/workspace.py` 끝에 `ExternalPromptTexts`(texts 최대 200개, 각 2,000자로 자름)와 `POST /projects/{project_id}/external-ai/prompt-texts`: 프로젝트 없음 404, `LOCAL_ONLY` 403, `ORIGINAL` 그대로, 그 밖(`MASKED`) `PIIEngine(PseudonymStore(project_id=…)).mask_text(t).masked_text`. 브라우저 정규식 가림에 맡기지 않는다(주장 문장에는 인명·연락처·주소가 섞인다).
8. **CSS:** `.reference-observations`·`.external-ai-answer`(왼쪽 선·배경 구분, `overflow-wrap:anywhere`), `.review-prompt-bar .external-ai-import-btn`(프롬프트 버튼과 같은 크기).

## 시험 (새 `tests/test_tk126_flat_tabs_answer_import.py`, 수정본에 포함)
- `test_answer_import_applies_to_row_without_changing_official_badge`: 2단 프롬프트에 'A1. 대법원 …'·`<<<ACAS_RESULT`, 붙여넣기(A1·표에 없는 A7) → 미리보기 'A1 → 대법원 …'·'A7' 경고 → 반영 → 행에 '외부 AI 답변 A1 (공식 확인 아님)'·'판정: 부존재', 판정 배지 불변.
- `test_legal_claims_tab_prompt_uses_server_masked_claims_and_imports_answers`: 3단 프롬프트가 서버 가림 API를 부르고 가린 문장만 담는다(전화번호·실명 0), B 번호 답변 반영.
- `test_prompt_texts_endpoint_follows_project_policy`: LOCAL_ONLY 403, MASKED 전화번호 제거, ORIGINAL 원문.
- 기존 `test_external_ai_prompt.py`는 고치지 않고 통과한다(번호 앞 접두가 붙어도 단언 문자열이 그대로 들어 있음).

## 미검증·사용자 결정
- 저장 위치(대응표 5): 사전 검증본은 브라우저 저장(`localStorage`, 읽기·쓰기 실패 시 안내). 서버 저장(실행별 표, 감사 기록, 보고서 반영)은 `migrations/`가 필요한 별도 단계이며 미검증.
- 인젝션 문구가 든 답변: 표시는 textContent라 실행되지 않지만, 답변 문장에 대한 인젝션 탐지 재사용은 미구현·미검증.
- 운영 엘박스 실제 답변이 결과 블록을 지키는 비율: 미검증(사용자 실사용으로 확인).
