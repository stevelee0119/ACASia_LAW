# v0.22.0 개선 구현 지시문 — 요구 문장별 구현 위치 대응표

- 작성일: 2026-11-18
- 작성: 구현 에이전트(Claude Code)
- 원문: [V0_22_0_IMPROVEMENT_INSTRUCTIONS_20261116.md](V0_22_0_IMPROVEMENT_INSTRUCTIONS_20261116.md)
  (SHA-256 `c6480f9e9c0defb3c881f5041b368df739c77196b2ec80bb6f88424428a3481c`, 재작성 없이 보존)
- 기준 실행: `run_68f603656dec475f` (v0.22.0, 운영 SHA `183f3d22791bb01d4c8a39ce842e193000c663b8`)
- 대조 기준 코드: Steve `8b760d2`(PR #330 병합) + PR #332(`3dd12f7`, 판정 대기)

**이 문서는 구현 측의 자기 보고다.** 수용 판정은 평가 측(Codex)이 한다. 줄 번호는 위 SHA 기준이다.

## 1. 구현 과제(3절) 대응

### [P0-1] `ai_hallucination_table` 매핑 어긋남 — 구현됨 (#326)

| 원문 요구 | 구현 위치 | 비고 |
|---|---|---|
| "리스트 인덱스 기반 병합(`zip`)을 제거하고 `citation_id` 키 기반 딕셔너리 조인으로 고정할 것" | `packages/legal_engine/argument_validity_verifier.py:598` `item["item_id"] = index`, `:787` `row.item_id = index`, `:1063-1064` `items_by_id[item_id]` 직접 키 조인 | 인덱스 재넘버링 제거. `cases_for_ai` 필터 뒤에도 원래 `item_id` 유지 |
| "`actionable_guidance`를 인용 유형(`STATUTE`, `ADMIN_RULE`, `CASE`)별로 분기해 법령·행정규칙에는 국가법령정보센터/소관 규정 원문 확인 가이드를 출력할 것" | `packages/legal_engine/actionable_guidance.py:154` `_authority_kind()`, `:173·177` `citation_type` 인자·분기 | 법령·행정규칙에 '판결서 사본 요구'가 나가지 않도록 분기 |
| (현상 서술) "법령·지침 행에도 일괄적으로 판결서 사본 요구가 출력됨" | 위와 같음 | — |

**추가로 드러난 원인**: 확인된 정상 법령이 미확인 표로 유입된 주원인은 `is_summary_only`가
`STATUTE`/`ADMIN_RULE`에도 적용된 것이었다 → `argument_validity_verifier.py:474-478`에서
`CASE`/`CONSTITUTIONAL`로 한정. 원문 P1-2 전반부와 같은 뿌리다(3절 참조).

### [P0-2] `INPUT_PRIVACY_BLOCKED`로 인한 `ai_detection` 실패 — 일부 구현, 일부 **설계상 미채택** (#328)

| 원문 요구 | 처리 | 비고 |
|---|---|---|
| "마스킹 완료 토큰, 법령 조문 번호, 판례 사건번호가 PII로 재탐지되지 않도록 1차 마스킹 규칙과 2차 검사 정규식을 동기화하고 화이트리스트를 적용할 것" | **구현**: `pii_engine/detector.py` `_normalise_contact_view`의 가명 토큰 숫자 재결합 차단, `LEGAL_IDENTIFIER_PATTERNS:21-38`(하이픈 법령·훈령·예규·호증, 2자리 연도 구 사건부호 포함), `pii_engine/engine.py` `MAX_MASK_PASSES` 유한 재패스 멱등화, `pseudonym.py:46` `PSEUDONYM_PREFIXES` 정합, `llm_router/privacy.py:105` `_build_masked_value_re` | 1·2차 규칙을 같은 토큰 문법으로 묶음 |
| "2차 검사 차단 시 즉시 실패 처리하지 말고 추가 마스킹 패스 1회 후 재시도하는 복구 경로를 추가할 것" | **미채택(설계 판단)** — `llm_router/privacy.py` `inspect_request`의 fail-closed 원칙에 반한다. 대신 **상류**(`PIIEngine.mask_text`)에서 유한 재패스로 멱등성을 확보해 2차 검사가 애초에 걸리지 않게 했다 | 라우터에서 재마스킹·재시도를 하면 개인정보 보호 경계가 느슨해진다. **원문과 다르게 처리한 유일한 항목이므로 평가 측 판단이 필요하다** |

**원문 현상 서술의 오진 정정**: "`inspected_chars: 0 / 35,674`"는 0자를 보낸 것이 아니라,
모델 전량 실패 뒤 보고용 값을 0으로 덮어쓴 결과다(`verification_engine/ai_document_detector.py:359·386·393`).
`:336` `requested_chars`와 `:391` `model_executed`가 추가돼 이제 둘을 구분할 수 있다.

### [P1-1] 구 사건부호 오탐 및 판례 DB ID 매칭 오류 — 구현됨 (#326)

| 원문 요구 | 구현 위치 |
|---|---|
| "사건번호 유효성 사전에 구 사건부호(`다카`, `나카` 등)를 반영할 것" | `packages/legal_engine/normalize.py:40-42` `HISTORICAL_CASE_CODE_MEANING`, `:174-175` 조회 통합. 공식 DB 일치 시 `verifier.py:519-520`에서 `number_format` `IMPOSSIBLE`→`VALID` 복원 |
| "외부 판례 DB 조회 결과를 `claim_evidence`에 결합할 때 사건번호·법원명·선고일 일치 검증 가드를 추가해 불일치 매칭을 차단할 것" | `packages/legal_engine/verifier.py:103` `_official_provider_linking_key`, `:131` `_detail_matches_official_case`, `:537` 적용. 파싱 불가·누락 시 fail-closed 차단 |
| (현상) 헌재 결정이 `prec`로 조회되던 문제 | `citation_extractor.py:716·770` 헌재 `CONSTITUTIONAL` 분류, `verifier.py:528` `constitutional=True` 라우팅 |

### [P1-2] 실정법 `temporal_pending` 과다 + 무리한 법리 주장 독립 탐지 — 구현됨 (#326·#329)

| 원문 요구 | 처리 |
|---|---|
| "과거 시점이 쟁점화되지 않은 기본 실정법은 최신 시행일 기준으로 `VERIFIED` 처리" | `legal_engine/source_review.py:197-202`가 **이미** 기준일 미지정 시 현행 기준 `VERIFIED`(`APPLICABILITY_UNREVIEWED`)로 판정하고 있었다. 미확인 표 유입의 실제 원인은 P0-1의 `is_summary_only` 버그 → #326으로 해소. 자동 추정 기준일(`inferred_reference_applied`) 승격은 `verification_engine/pipeline.py`에 반영(#329) |
| "`VERIFIED` 법령은 `ai_hallucination_table` 미확인 목록에서 제외할 것" | `argument_validity_verifier.py:474-478`·`:524` |
| "대표적 법리 오류 패턴(소멸시효 기간 왜곡, 민·형사 입증책임/무죄추정 혼동, 하급심의 법률 효력 폐지 주장, 계약 일방 변경)을 인용 오류와 분리해 독립 플래그로 보고" | `legal_engine/claim_review.py` `_unreasonable_argument`(+214줄) 4종: `LIMITATION_PERIOD_DISTORTION`·`CIVIL_CRIMINAL_STANDARD_CONFUSION`·`LOWER_COURT_STATUTE_INVALIDATION`·`UNILATERAL_CONTRACT_MODIFICATION`. 근거 조문은 `config/legal_rules/rules.json`에 민사소송법 제202조, 헌법 제27조 제4항·제107조, 민법 제105조·제543조 추가 |

### [P2-1] 인용 경계 파싱, NER 불용어, 부속서 메타표 — 구현됨 (#329 + #330)

| 원문 요구 | 구현 위치 |
|---|---|
| "법령 추출기 선행 부사·후행 조사 스트리핑" | `legal_engine/citation_extractor.py:834` `start = _law_name_start(m)`, `:1337` 함수 신설. `normalize.py` `law_name_suffix` 조사 경계 |
| "한국어 법률 NER 불용어 필터" | **#329는 `MILITARY_NOUNS`만 공유해 부분 구현이었다.** #330에서 완성: `claim_engine/extractor.py`가 `is_valid_korean_name_structure`·`LEGAL_MILITARY_STOPWORDS`(낱말 100개)·`COMPANY_STOPWORDS`(25개)를 개인정보 엔진과 공유. 원문의 오탐 예(`부대`·`측에`·`영위하는`·`대한민국` PERSON, `민간` COMPANY)를 합성 문장으로 재현·배제 |
| "부속서/체크리스트 메타표 제외 휴리스틱" | 신규 `packages/document_engine/meta_sections.py`(`is_meta_checklist_table_rows`, `meta_checklist_block_ids`), `citation_extractor.py:1618`·`claim_engine/extractor.py:319·380·631`에서 배선 |

### [P2-2] RAG 12,000자 절단, 지침 매칭, 실행 속도 — 구현됨 (#325·#327), 캐싱은 **미채택**

| 원문 요구 | 처리 |
|---|---|
| "`reference_review`를 청크 분할 대조로 전환해 전체 본문을 커버" | `rag_engine/review.py:306`이 `analysis_text(result.normalized, result.findings)`를 limit 없이 호출 → `document_engine/analysis_text.py:12·59` 기본 `limit=None`으로 **12,000자 절단 제거** |
| "약칭 `지침`에 문서 내 정의문·Drive 규정 제목을 결합한 쿼리 확장" | `citation_extractor.py:1658` 약칭 후보를 `STATUTE`+`ADMIN_RULE`로 확장(`지침`·`훈령`·`예규`·`규정`). RAG 쪽은 `library.select` 질의 확대·다중 경로 `search_claim`·분리 수집(#325) |
| "청크 병렬 처리로 속도를 개선" | `rag_engine/review.py:646·765` `asyncio.Semaphore(rag_concurrency)`, `argument_validity_verifier.py:1091` `Semaphore(4)` |
| "`llm_prompt_caching` 활성화" | **미채택(설계 판단)** — `common/config.py:169-171`의 `False`는 무상태 주장 프롬프트에서 캐시 쓰기 과금(+25%)을 막는 의도된 기본값이다. 17분 20초 지연의 주원인은 P0-1로 부풀려진 행 수와 순차 LLM 대기였고 그 둘을 고쳤다. **원문과 다르게 처리했으므로 평가 측 판단이 필요하다** |

## 2. 회귀 테스트 완료 기준(4절) 대조

| # | 원문 기준 | 현재 상태 |
|---|---|---|
| 1 | "`state`가 `PARTIAL_COMPLETED`가 아닌 정상 완료 상태로 종료" | **운영 재실행으로만 확인 가능** — 배포 후 온라인 평가 항목 |
| 2 | "`INPUT_PRIVACY_BLOCKED` 0건, `model_executed == true`, `inspected_chars > 0`" | **운영 재실행 필요.** 코드상 상류 멱등 마스킹(#328)으로 재탐지 원인을 제거하고 `requested_chars`·`model_executed`로 구분 가능하게 함 |
| 3 | "`ai_hallucination_table` 전 행에서 `citation_id`와 `ai_opinions`·`actionable_guidance` 유형이 100% 일치" | 코드로 충족(#326). 합성 시험으로 확인, 운영 보고서 재확인 필요 |
| 4 | "`88다카2813` 오탐 제거 및 `2021헌바86` 근거 내 타 사건 미혼입" | 코드로 충족(#326, 구 부호 사전 + fail-closed 결합 가드). 운영 보고서 재확인 필요 |
| 5 | "`reference_review`가 문서 후반부 전체를 대조해 Drive 규정과 본문 `지침`을 매칭하고, 무리한 법리 주장 4종이 독립 리스크로 탐지" | 절단 제거·약칭 확장·4종 규칙은 코드로 충족(#325·#327·#329). **Drive 실제 매칭은 운영 재실행 필요** |

## 3. 원문과 다르게 처리한 항목(평가 측 판단 필요) — 2건

1. **P0-2의 "2차 검사 차단 시 추가 마스킹 패스 후 재시도"** → 라우터 fail-closed 유지, 상류 멱등화로 대체
2. **P2-2의 "`llm_prompt_caching` 활성화"** → 의도된 기본값이라 유지, 지연 원인은 행 수·순차 대기로 귀속해 수정

두 항목은 개인정보 보호 경계와 과금에 직접 닿아 구현 측이 임의로 바꾸지 않았다. 원문 그대로 적용할지는
사용자·평가 측 결정 사항이다.

## 4. 측정하지 못한 것

원문 1절의 수치(총 탐지 64건, 17분 20초, LLM 97회 중 17회 차단, Drive 41건 중 36건 색인 등)는
**운영 실행 기록**이다. 구현 측은 그 실행을 재현할 수 없고, 오프라인 고정·은퇴 세트로는 AI 작성 판별·
공식 DB 대조·Drive 대조를 재지 못한다. 배포 후 온라인 재평가에서만 확인된다.
