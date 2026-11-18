# 설계 메모: 261116 AegisLAW UI·리포트·검증 품질 개선 (항목 1~9)

- **작성일:** 2026-11-16 (`Agent: implementer`)
- **대상 범위:** 사용자 실사용 점검 `[261116 AegisLAW 개선 필요 사항 정리]` 1~9번 + 보고서(PDF/DOCX/XLSX/JSON) 동기 반영(7·7-1 확정 범위)

---

## 1. 항목별 원인 및 설계

| 구분 | 확인된 원인 | 설계 방안 |
|---|---|---|
| **1. 작성주체 범위 `0/35674자`** | `ai_document_detector.py`에서 LLM 전원이 프라이버시 게이트 등에서 실패(`used_llm=False`)하면 규칙 기반 검사를 수행하고도 `inspected_chars=0`으로 덮어씀 | 규칙 검사·모델 교차검토 범위를 분리 기록(`rule_inspected_chars`, `model_inspected_chars`)하고, 2번 해소로 LLM 호출 정상화 후 전체/표본 분모·분자 일치 표시 |
| **2. `INPUT_PRIVACY_BLOCKED` / `PII_INPUT_BLOCKED`** | `detect_ai_document` 입력(`document_sample_text`, `document_filename`, `_mask_direct_quotes` 후 문자열)에 대한 PII 마스킹 후 `privacy.verify_request` 재검사 불일치 | PR #328(`P0-2` 마스킹 멱등성·규칙 동기화) 병합 후 `detect_ai_document` 경로(파일명·인용마스크 구간·지시문 치환문) 잔여 미스매치 점검 및 Fail-Closed 유지 하 가림 완결 |
| **3. 모델별 판정 영문 코드 노출** | `llm_router/router.py`의 `INPUT_PRIVACY_BLOCKED [MASKING_PII_DETECTED:PII_INPUT_BLOCKED]` 원문 문자열을 `app.js` `modelOpinions()`가 그대로 출력 | 코드별 한글 사유 사전(`llm_router`·`app.js` 공용 매핑)으로 치환해 내부 enum 대신 이해 가능한 한글 안내만 노출 |
| **4. 프롬프트 인젝션 'AI 검토에서 제외' 표시** | 백엔드는 v6 P3(`pipeline.py`)로 지시문 구간만 제거 후 본문 AI·법리 검토를 이미 수행하나, `app.js:1449` 문구가 구버전('이 문서는 AI 검토에서 제외') 그대로 남음 | UI·진단 요약 문구를 "지시문 구간만 AI 입력·RAG 자동 등록에서 격리하고 나머지 본문 검토를 수행함"으로 교정하고, 격리 문서라도 내용 검토 결과·요약이 모두 표시되도록 정합화 |
| **5. `보안 및 파일 진단` 카드 폭** | `card1`·`injectionCard`는 `summary-card-wide`(`grid-column: 1 / -1`)이나 `securityCard`만 일반 `summary-card`라 좌측 1열만 점유 | `app.js` `securityCard()`에 `summary-card-wide` 클래스 부여 |
| **6. 외부 AI 답변 영속성·덮어쓰기** | `localStorage`에만 저장되어 재접속/타 브라우저 시 소실되며, 재붙여넣기 시 기존 접두사(`A`/`B`) 구답변이 잔존 | 서버 DB(`VerificationRun` 메타/전용 엔드포인트) 저장·재조회 동기화 추가, 새 답변 붙여넣기 반영 시 동일 접두사(`A` 또는 `B`) 기존 답변 초기화 후 신규 답변만 저장·표시 |
| **7·7-1. 모델명 표기 및 비공식/안내 문구 삭제** | 웹(`externalAnswerBlock` 등)과 보고서(`external_answers.py`, `pdf_report.py`, `docx_report.py`, `exporters.py`, `report-workbench.js`)에 `(공식 확인 아님)` 및 하단/시트 상단 당연 고지 반복 | 프롬프트 결과 블록·입력 모달에 `모델명` 필드 추가(`{모델명} 답변`, 예: `Gemini … 답변`, `엘박스 답변`). 웹 카드와 다운로드 보고서 **PDF·DOCX·XLSX·JSON** 모두에서 `(공식 확인 아님)` 및 하단/상단 설명 고지 문구 제외(기존 `test_tk126`/`127`/`129` 단언 동기 갱신) |
| **7-2. 중요도·근거 배지 좌측 정렬** | `styles.css:2989` `.claim-verdict { margin-left: 4px; }`로 데스크톱 2번째 줄 래핑 시 1줄(`매우 높음`)과 4px 어긋남 | 배지 묶음 컨테이너(`display: inline-flex; flex-wrap: wrap; gap: 4px 6px;`) 적용 및 `.claim-verdict`의 고정 `margin-left` 제거 |
| **8·8-1. 계산 비교 및 3열 논리 재구성** | `review_items.py` 비인용 행이 2열에 분석 `detail`을 넣고 3열에 짧은 제목만 두며 4열에 `detail`을 재노출 | **2열:** 서면 원 주장 문장·잘못된 계산식/액수 원문, **3열:** 정당한 계산식·정당 산정 액수·정당한 법리 결론+근거, **4열:** 결론 검증에 필요한 확인 항목(`counteraction`/증거/산식 변수)으로 역할 분리 |
| **9. Time-Table 사건 사실관계 집중** | `claim_engine/extractor.py` `extract_events()`가 판시(`CASE_HOLDING`)·법리(`LEGAL_RULE`)·판결 선고일/법령 시행일 날짜까지 모두 사건으로 추출 | `CASE_HOLDING`/`LEGAL_RULE`/`LEGAL_INTERPRETATION` 문장과 순수 판결 선고·법령 공포/시행일 맥락 날짜를 타임라인 추출에서 제외하고, 당사자 행위·계약·지급·사고 등 사건 사실관계 날짜만 반영 |

---

## 2. 검출 휴리스틱 및 시험 기준 (양성 3+ / 대조 3+)
- **개인정보(2번):** Fail-Closed 원칙(`verify_request` 비식별 검사 통과 필수)은 절대 완화하지 않고, 2중 마스킹·인용 공백 마스킹·파일명 경로의 미동기화만 해소한다.
- **Time-Table 필터(9번):** 판결 선고일·재판례 날짜(대조군 3건: 대법원 선고일 인용, 하급심 판시 날짜 인용, 법률 개정·시행일 인용)는 제외하고, 실제 사건 사실(양성 3건: 계약 체결일, 대금 지급·지체일, 해지 통지·사고 발생일 — 단 당사자가 다투는 원심 처분일/소장 제출일 등 사실 사건은 유지)만 추출하도록 분리 시험한다.
- **하드코딩 금지:** 모든 시험 데이터는 합성 문구만 사용하며 `tests/acceptance/test_no_case_literals.py` 및 `scripts/check_hardcoding_diff.py` 통과를 전제로 한다.

---

## 3. 작업 묶음 및 선행 PR 병합 권고
미병합 PR 10건(#320~#329)이 `app.js`, `privacy.py`, `router.py`, `pipeline.py`, `extractor.py`, `legal_engine` 전반과 직접 겹치므로 선행 PR 정리 후 아래 순서로 착수한다.
1. **Batch A (UI·표현·영속성 + 보고서 문구):** 항목 **5 · 7-2 · 3 · 4 · 7 · 7-1 · 6** (`apps/web/`, `packages/report_engine/`, `apps/api/`)
2. **Batch B (입력 차단·검토 범위):** 항목 **2 · 1** (`packages/verification_engine/ai_document_detector.py`, `packages/llm_router/privacy.py`, `packages/pii_engine/`) — #328·#324 병합 기반 위에서 수행
3. **Batch C (사실관계·법리 3열 구조):** 항목 **9 · 8 · 8-1** (`packages/claim_engine/extractor.py`, `packages/claim_engine/calculation.py`, `packages/verification_engine/review_items.py`, `packages/legal_engine/`) — #321·#326·#329 병합 기반 위에서 수행
