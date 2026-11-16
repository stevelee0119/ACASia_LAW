# P0-2 설계 메모: PII 마스킹 멱등성 및 1·2차 검사 규칙 동기화

- 작성일: 2026-11-16
- 대상 브랜치: `fix/p0-2-pii-idempotent-masking-parity` (기준: `origin/Steve_ACASiaLAW` `167c695`)
- 관련 이슈: 2차 입력 프라이버시 검사(`payload-pii-v4`)에서 마스킹 완료 결과 및 법률 식별자가 재탐지되어 `INPUT_PRIVACY_BLOCKED [MASKING_PII_DETECTED:PII_INPUT_BLOCKED]`로 정상 LLM 호출(특히 `ai_detection`)이 차단되는 문제 해소.

## 1. 원인 진단
1. **가명 토큰 숫자 재결합**: `detector._normalise_contact_view`가 `[PERSON_001]` 내부 숫자 `001`을 유지하고 `_`/`]`/`(`를 구분자로 치환하여, 뒤에 날짜·숫자가 오면 `PHONE_NORMALIZED_RE`(`0\d{1,2}-\d{3,4}-\d{4}`)로 재탐지한다.
2. **단일 패스 및 부분 중첩 누락**: `PIIEngine.mask_text`가 `detect()`를 1회만 호출하고 `match.start < cursor` 부분 중첩을 건너뛰어, 마스킹 후 경계에 남거나 새로 노출된 패턴이 2차 `inspect_request`에서 차단된다.
3. **가명 접두사 불일치**: `privacy._MASKED_NAME_VALUE_RE`가 `PERSON|COMPANY`만 허용하여 `AFFIL`, `MILID`, `PHONE`, `RRN`, `BIZNO`, `PII` 등 다른 `KIND_PREFIX` 가명 토큰이 인명/역할 필드 불확실 값으로 차단된다.
4. **법률 식별자 화이트리스트 공백**: 하이픈 포함 법령·훈령·예규·호증 번호와 2자리 연도 구 사건부호 일부가 `LEGAL_IDENTIFIER_PATTERNS`에 빠져 `VEHICLE`/`MILITARY_ID`로 오탐된다.

## 2. 변경 설계 (Fail-Closed 원칙 유지)
- **`packages/pii_engine/pseudonym.py`**: `KIND_PREFIX`와 `PII`를 단일 출처로 하는 `PSEUDONYM_PREFIXES` 및 `PSEUDONYM_TOKEN_RE` 정의.
- **`packages/pii_engine/detector.py`**:
  1. `_normalise_contact_view`에서 `PSEUDONYM_TOKEN_RE` 토큰 내부 숫자를 비숫자 문자로 가려 토큰 숫자-인접 숫자 간 접촉 결합 차단.
  2. `detect()`가 기존 `PSEUDONYM_TOKEN_RE` 구간과 겹치는 후보를 $O(\log N)$으로 제외하여 가명 토큰 재탐지·재분할 방지.
  3. `LEGAL_IDENTIFIER_PATTERNS`에 하이픈 포함 법령·행정규칙·호증 번호 및 2자리 구 사건번호를 보강(차량번호 `12가 3456`형 오면책 방지).
- **`packages/pii_engine/engine.py`**: `PIIEngine.mask_text`를 최대 5회 유한 다중 패스 멱등 루프로 전환하고, 후속 패스 매치를 원문 좌표계(`MaskResult.matches`)로 역매핑하여 `evidence_pack.project_masked` 및 `source_trace._EditTrace` 호환성을 유지한다. (`mask_document`의 대리인·법원 주소 보존 동작은 유지.)
- **`packages/llm_router/privacy.py`**: `_MASKED_NAME_VALUE_RE`가 `PSEUDONYM_PREFIXES` 전부를 허용하도록 동기화한다. `inspect_request`와 `LLMRouter.run`의 fail-closed 차단 계약은 변경하지 않는다.

## 3. 검증 계획
- 양성: (1) 가명 토큰+날짜·숫자 인접 문자열, (2) 부분 중첩·연쇄 PII의 `mask_text` 멱등성 및 `project_masked` 좌표 정합성, (3) `detect_ai_document`의 모의 라우터 + 실 `inspect_request` 통과, (4) 모든 `KIND_PREFIX` 토큰의 구조화 필드 허용, (5) 하이픈 법령/구 사건번호 무마스킹.
- 대조(Fail-closed): (1) 미마스킹 PII JSON의 `LLMRouter.run` `NOT_SENT` 차단 유지, (2) `[PERSON_001]` 뒤 원문 성명 결합 우회(`inspect_request` `BLOCKED`), (3) 차량번호·연락처·주민번호 정상 탐지 유지, (4) `test_pii_redos_linear` 및 `test_no_case_literals` 통과.
