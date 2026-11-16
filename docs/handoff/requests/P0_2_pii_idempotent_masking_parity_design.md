# P0-2 설계 메모: PII 마스킹 멱등성·위조 가명 토큰 차단 및 1·2차 검사 동기화

- 작성일: 2026-11-16
- 대상 브랜치: `fix/p0-2-pii-idempotent-masking-parity`
- 관련 이슈:
  1. 2차 입력 프라이버시 검사(`payload-pii-v4`)에서 마스킹 완료 결과 및 법률 식별자가 재탐지되어 정상 LLM 호출이 차단되는 문제.
  2. 형태만 맞춘 위조 가명 토큰(`[PERSON_01024681357]`, `PERSON_01024681357`, 짝이 맞지 않는 괄호, 잘못된 접두사, 인접 숫자 PII 결합)이 2차 검사를 우회하지 않도록 fail-closed 방어를 강화하는 문제.

## 1. 원인 진단 및 보안 경계 분석
1. **가명 토큰 숫자 재결합**: `detector._normalise_contact_view`가 가명 토큰 내부 숫자를 구분자 앞뒤 숫자로 이어 붙여 뒤에 날짜·숫자가 오면 `PHONE_NORMALIZED_RE`로 재탐지한다.
2. **단일 패스 및 부분 중첩 누락**: `PIIEngine.mask_text`가 `detect()`를 1회만 호출하고 `match.start < cursor` 부분 중첩을 건너뛰어 마스킹 후 경계에 잔여 PII가 남을 수 있다.
3. **가명 문법 과허용 및 위조 토큰 우회**:
   - 숫자 접미사를 3자리 이상 무제한으로 허용하면 `[PERSON_01024681357]`처럼 실제 PII 숫자가 접미사에 포함된 문자열이 토큰 구간으로 오인되어 내부 숫자 탐지가 건너뛰어졌다.
   - `_MASKED_NAME_VALUE_RE`가 대괄호 여부·모든 접두사·3자리 이상 접미사를 구분 없이 허용해 성명/역할 필드에서 `[PHONE_001]`이나 `[PERSON_01024681357]` 같은 위조 값을 차단하지 못할 위험이 있었다.
   - 요청 내 실제 마스킹 단계에서 발급된 토큰 집합(`_TokenAttestation`)을 `inspect_request`까지 전달·검증하지 않으면 형태 일치만으로 위조 토큰이 신뢰될 수 있다.
4. **법률 식별자 화이트리스트 공백**: 하이픈 포함 법령·훈령·예규·호증 번호와 2자리 연도 구 사건부호 일부가 `LEGAL_IDENTIFIER_PATTERNS`에 빠져 `VEHICLE`/`MILITARY_ID`로 오탐된다.

## 2. 변경 설계 (Fail-Closed 원칙 유지)
### 2.1 가명 토큰 순번 상한 및 생성기 강제 (`packages/pii_engine/pseudonym.py`)
- `MAX_PSEUDONYM_SEQUENCE = 999`, `PSEUDONYM_SEQUENCE_PATTERN = r"(?!000)[0-9]{3}"`.
- `PSEUDONYM_TOKEN_RE`는 **대괄호 균형 + 3자리 순번(`001`~`999`)**(`\[(?:PREFIXES)_(?!000)[0-9]{3}\]`)만 인식한다.
- `PseudonymStore._pseudonym_for_unlocked`는 `next_seq > MAX_PSEUDONYM_SEQUENCE`이면 `ValueError`를 발생시켜 4자리 이상이나 PII형 숫자 접미사 발급을 원천 차단한다.
- `canonical_pseudonym_token` / `is_valid_pseudonym_token`으로 짝이 맞지 않는 괄호(`[`만 있거나 `]`만 있음), 범위 초과(`000`, `1000+`), 비허용 접두사를 거부한다.

### 2.2 토큰 경계·내부 PII fail-closed 탐지 (`packages/pii_engine/detector.py`)
- `_pseudonym_analysis` 및 `_cross_boundary_pii_match`:
  - 토큰 직전/직후의 숫자·구두점 결합(`010-[PERSON_246]-1357`, `[PHONE_010]-2468-1357`, `780512-[PERSON_123]4567`, `110-[ACCOUNT_234]-567890`)과 토큰 경계 차량번호 결합(`12가[PERSON_001]3456`)이 전화번호·주민번호·계좌·차량번호·군번 패턴과 일치하면(날짜 제외) 토큰을 면책하지 않고 해당 PII `PIIMatch`를 반환한다.
  - 요청 증명(`trusted_tokens`)이 제공된 경우 증명 집합에 없는 비증명 토큰(`not is_trusted`)은 안전 스팬으로 제외하지 않으며, 공백 뒤 한국 전화번호 패턴 결합(`[PHONE_010] 2468-1357`)까지 탐지한다.

### 2.3 요청 바인딩 기반 불변 마스킹 증명 (`packages/llm_router/token_attestation.py`, 소비 경로 연동)
- `_TokenAttestation`: capability 보호(`_CAP`)·불변 슬롯·`repr`/`deepcopy` 마스킹 객체로, 해당 요청의 `(sha256(user), system)` 및 실제 마스킹 단계(`_ModelInputRenderer.mask_tracked`, `pii.mask_text().replacements`)에서 발급된 정식 토큰 집합(`frozenset[str]`)을 바인딩한다.
- 소비 경로 연동: `ai_document_detector.detect_ai_document`, `rag_engine.review`, `argument_validity_verifier._attach_ai_opinions`, `pipeline._semantic_review` (`cascade` / `build_cascade_request`).
- 1차 내부 재조립(`_rebind_review_profile`, `build_partial_argument_request`, `LLMRouter.run`의 `SYSTEM_BASE` 조립)에 한해 증명 재바인딩 및 `original_system` 대조를 수행한다. 다른 요청으로 복제하거나 본문/시스템을 임의 수정하면 `valid_token_attestation`이 `False`로 fail-closed(`INPUT_CONTRACT_VIOLATION` / `BLOCKED`) 처리된다.

### 2.4 구조화 필드 종류별 허용 접두사 구분 (`packages/llm_router/privacy.py`)
- 순수 인명 키(`성명`, `이름`, `fullName` 등): `_STRICT_PERSON_NAME_PREFIXES = ("PERSON",)`만 허용(`PHONE`, `RRN`, `ACCOUNT`, `BIZNO`, `COMPANY` 등 거부).
- 법인/기관 겸용 당사자·역할 키(`원고`, `피고`, `대표자`, `담당자` 등): `_ROLE_PARTY_PREFIXES = ("PERSON", "COMPANY", "AFFIL")`만 허용.
- `trusted_tokens`가 존재하는 증명 요청에서는 `_uncertain_person_value`와 `detect(..., _trusted_tokens=...)` 모두 해당 요청에 증명된 토큰만 신뢰한다. `000`, 4자리 이상, 짝이 맞지 않는 괄호, 추가 문자(`_extra`, ` extra`)는 항상 차단된다.

### 2.5 다중 패스 멱등성·증거 좌표 보존 (`packages/pii_engine/engine.py`)
- `PIIEngine.mask_text`는 일반 `str`(및 `_EditTrace`)에서 부분 중첩 잔여 후보가 있을 때만 최대 5회 유한 다중 패스를 돌며 후속 매치를 원문 좌표계(`MaskResult.matches`)로 역매핑한다.
- `TracedText`(`type(text) is not str`) 호출 경로(`_mask_matches` 단일 패스 훅 계약)는 기존 단일 패스 동작을 보존한다. `mask_document`의 대리인·법원 주소 보존도 유지한다.

## 3. 검증 계획
- 위조 토큰 재현군(`[PERSON_01024681357]`, `[PHONE_01024681357]`, `[RRN_7805121234567]`, `PERSON_01024681357`, `[PERSON_001`, `PERSON_001]`, `[PERSON_001_extra]`, `PERSON_001 extra`, `[PHONE_010]-2468-1357`, `[PHONE_010] 2468-1357`, `010-[PERSON_246]-1357`, `780512-[PERSON_123]4567`, `110-[ACCOUNT_234]-567890`)의 `detect()`, `inspect_request()`, `LLMRouter.run`(`NOT_SENT`) 차단 검증.
- `PseudonymStore` 999건 한계 초과 시 `ValueError` 발생 및 `000`·`1000` 차단 검증.
- `_TokenAttestation` 연동 요청 통과, 타 요청 복사·변조 시 `INPUT_CONTRACT_VIOLATION` 차단, 비증명 토큰 주입 차단 검증.
- 기존 양성(날짜 인접 가명, 필드별 정식 접두사, 하이픈 법령/구 사건번호, `detect_ai_document` + `_ModelInputRenderer`) 및 `_EditTrace` 다중 패스/`project_masked`/`test_pii_redos_linear`/`test_no_case_literals` 통과 검증.
