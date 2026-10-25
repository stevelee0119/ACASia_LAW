# TK-129 보고서 생성 시 표에 반영한 외부 AI 답변을 보고서에 포함 (P2, 새 기능)
- 근거: 사용자 결정·요구(2026-10-25). 기준: Steve `b68e70f` + TK-126·127·128 수정본(`patches/TK-126-128_prevalidated_b68e70f.diff`). 줄 번호는 이 기준.
- 선행: TK-126·127·128 PR 병합.
- 분류: `added`. 보고서 엔진 변경(탐지·채점 엔진 아님). **사용자 확인 뒤 수용.**
- 사전 검증 수정본: `docs/handoff/patches/TK-129_prevalidated_after_TK126.diff`(9개 파일, 249줄 추가·14줄 삭제).

## 사용자 원문
- (10-25) "AI 답변 저장 위치는 브라우저에 저장. 타 사용자와는 AI 검토 내용을 표에 반영한 다음 보고서로 추출하여 공유가 가능할 것으로 예상됨."
- (10-25) "AI 검토내용이 표에 반영된 후 다시 보고서를 생성할때, 그 내용이 보고서 내용에 반영되도록 기능구현을 하면, 보고서가 브라우저 저장된 AI 답변을 담을 수 있지 않을까?"
- (10-25) "지시문 전달 TK-129 착수"

## 원인(평가 측 코드 확인)
1. 보고서는 서버가 실행 결과 고정본으로만 만든다. `report-workbench.js` 72행은 `run_id·formats·audience·detail_level`만 보내고, `ReportRequest`(`apps/api/schemas.py` 174~181행)에 답변 칸이 없다. `_build_draft`(`apps/api/routers/reports.py` 247행)가 만드는 고정본(`_snapshot`, 542행)에도 답변 자리가 없다.
2. 그래서 TK-128 답변(브라우저 저장)은 보고서에 들어갈 길이 없다.

## 원문 대응표 (수용 기준)
| # | 원문 | 확인할 화면·동작 |
|---|---|---|
| 1 | 표에 반영된 뒤 보고서를 생성하면 그 내용이 보고서에 반영 | 표에 답변을 반영한 뒤 '보고서 생성' 창에 "표에 반영한 외부 AI 답변 n건을 '외부 AI 참고 의견(공식 확인 아님)'으로 함께 싣기"(기본 선택)가 보인다. 만든 보고서: PDF·Word는 '3. 법률적으로 무리한 주장' 뒤 '외부 AI 참고 의견 (사용자 입력, 공식 확인 아님)' 절(안내문 + 표: 번호·대상·판정·근거·요지·반영 시각), Excel은 '외부AI참고의견' 시트, JSON은 `review_snapshot.external_ai_answers` |
| 2 | 보고서로 추출하여 타 사용자와 공유 | 초안·확정본·내려받기가 같은 답변을 싣는다(고정본 해시에 묶임). 공유용 보고서는 답변 문장의 실명·연락처를 가린다 |
| 3 | (TK-128 원칙) 공식 확인 아님 | 절 제목·안내문에 '공식 확인 아님'. 공식 판정·등급·점수·다른 절은 바뀌지 않는다. 답변이 없으면 절·시트가 없고 고정본도 전과 같다 |

## 평가 측 사전 검증 (TK-126 수정본 위 임시 사본, 저장소 밖)
- 새 시험 `tests/test_tk129_report_external_answers.py` 5건 통과. 기능을 끈 사본(행 함수가 빈 목록 반환)에서는 2건 실패, 확정에 답변을 넘기지 않은 사본에서는 확정본 시험 실패 — 시험이 기능을 실제로 잡는다.
- 보고서·화면·API 관련 시험 2,022건 실패 0, 건너뜀 25: 보고서를 다루는 기존 시험 전부(`test_report_completion`·`test_report_timeline_exclusion`·`test_source_objects`·`test_identity_security`·`test_operations_completion`·`test_improvements`·`test_evidence_hardening`·`test_efficient_llm_routing`·`test_tk78_opt_in_routing`·`test_auth_migration_merge`·`korean_law_profile/test_review_path`·`regression/test_post013_tk55…`) + TK-126 시험 묶음 + 새 시험.
- 전체 `tests` 결과는 HISTORY 10-25 'TK-129 사전 검증'에 적는다.
- `git apply --check`: `b68e70f` + TK-126 수정본 위에 통과.
- 미검증: 운영 보고서 실제 화면(긴 답변이 PDF 표에서 줄바꿈되는 모양), 실제 엘박스 답변 분량.

## 고칠 것 (수정본이 하는 일)
1. **요청 모델** (`apps/api/schemas.py` 174행 앞): `ExternalAiAnswer`(code `^[AB]\d{1,3}$`, item_id 1~300자, verdict·basis·summary 각 ≤1000자, applied_at ≤60자). `ReportRequest`에 `external_ai_answers: List[ExternalAiAnswer]`(≤400개, 기본 빈 목록). 보고서 작업(`report-jobs`)은 `payload.model_dump()`를 저장했다가 다시 읽으므로 새 칸도 그대로 이어진다.
2. **새 모듈** `packages/report_engine/external_answers.py`: 제목·안내문·머리글 상수. `_targets(engine)`는 고정 결과의 `documents[].review_items`(item_id → 인용 표기 또는 주장 문장)와 화면이 만드는 참고문헌 행 id(`{문서 id}_REFERENCE_{claim_id}` → claim_quote)를 모은다. `unknown_items`, `checked_answers`(대상 문구는 **서버가 고정 결과에서 다시 찾는다** — 브라우저가 보낸 대상 문구는 받지 않는다. 번호순 정렬, 같은 번호는 마지막 것), `external_answer_rows(snapshot)`.
3. **검사·고정본** (`apps/api/routers/reports.py`):
   - 219행 `_resolve_run` 끝: 이 실행의 표에 없는 item_id가 있으면 422(`unknown_item_ids` 최대 20개). 보고서 작업 시작 때 바로 알린다.
   - 247행 `_build_draft`: `checked_answers(engine, …)`를 `_snapshot(..., external=…)`로 넘긴다.
   - 542행 `_snapshot`: 인자 `external=None`. 답변이 있을 때만 `frozen["external_ai_answers"]`를 넣는다. 없으면 키를 두지 않아 기존 고정본 해시가 바뀌지 않는다.
   - 640행 확정(`finalize_report`): `external=frozen.get("external_ai_answers")`를 넘긴다. **빠뜨리면 확정본에서 답변이 사라진다.** 확정은 고정 결과로 고정본을 새로 만들기 때문이다(누락 사본에서 시험 실패 확인).
   - 공유용 가림은 따로 짤 필요가 없다. `shareable_snapshot`이 고정본 전체 문자열을 가리므로 답변도 가려진다(시험으로 확인).
4. **보고서 형식**:
   - `pdf_report.py` 290행 뒤 / `docx_report.py` 226행 뒤: 답변이 있을 때만 h2 제목 + 안내문 + 표. PDF 열 너비 `[30, 120, 60, 110, 120, 50]`, Word `[0.5, 1.5, 0.9, 1.4, 1.9, 0.8]`.
   - `exporters.py` 236행 `create_sheet("쟁점")` 앞: 답변이 있을 때만 '외부AI참고의견' 시트. 셀은 기존 `safe_cell`을 지나므로 `=`로 시작하는 답변이 수식으로 실행되지 않는다(시험으로 확인).
   - JSON은 기존 `review_snapshot` 출력에 자동 포함. CSV(결과 목록)·manifest·highlight에는 넣지 않는다.
5. **화면**:
   - `app.js` 434~437행: `externalStoreKey(projectId, runId)`·`loadExternalStore(projectId, runId)`가 인자를 받게 한다(기본값은 현재 프로젝트·실행). `externalAnswersForReport(projectId, runId)`를 추가한다. 번호와 행이 모두 남은 답변만 `{code, item_id, verdict, basis, summary, applied_at}`로 돌려준다.
   - `report-workbench.js` 64행: 생성 창에 답변이 있을 때만 체크 상자(기본 선택). 72행 요청 본문에 `external_ai_answers`를 넣는다(체크를 풀면 빈 목록).

## 시험 (수정본에 포함)
- `test_answers_are_frozen_into_every_format_and_survive_finalize`: 초안·확정본의 PDF·Word·Excel·JSON에 절·시트·값. 대상 문구는 서버 값. 수식 방지.
- `test_unknown_table_item_is_rejected_and_no_answers_keep_snapshot_unchanged`: 표에 없는 item_id 422, 잘못된 번호 422, 답변 없으면 고정본에 키 없음.
- `test_shareable_report_masks_personal_data_in_answers`: 공유용 JSON·Word에서 실명·전자우편 가림.
- `test_report_job_request_round_trips_answers`: 작업 저장·복원.
- `test_report_dialog_sends_answers_reflected_in_table`(브라우저): 답변 반영 → 보고서 창 체크 상자(기본 선택) → 요청 본문에 A1·item_id·판정.
- 기존 시험 수정 없음.

## 하지 않을 것
- 답변의 서버 저장·DB 표·migrations(사용자 결정: 브라우저 저장).
- 답변으로 판정·등급·점수·요약·다른 절을 바꾸는 것.
- CSV·manifest·highlight에 답변 넣기, 보고서 다른 절의 순서·문구 변경.
