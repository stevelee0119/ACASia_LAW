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
  - 요청 증명(`_trusted_spans: frozenset[(start, end, bare_token)]`)이 제공된 경우 `(ts, te, bare) in trusted_spans`로 정확히 증명된 출현만 신뢰하며, 비증명 출현(`not is_trusted`)은 안전 스팬으로 제외하지 않고 공백 뒤 한국 전화번호 패턴 결합(`[PERSON_010] 2468-1357`, `[PHONE_010] 2468-1357`, `[PERSON_010] 1234-5678`)까지 탐지한다.

### 2.3 필드·출현 위치 단위 불변 마스킹 증명 (`token_attestation.py`, 소비 경로·`cascade` 오프셋 매핑)
- **요청 수준 토큰 집합 폐기**: `bind_masked_tokens`는 평면 토큰 이름 집합을 거부하고, 각 필드 경로별 `(field_text, token_spans)` 또는 `MaskResult`만 받는다.
- `_TokenAttestation`은 불변 슬롯·capability(`_CAP`)·`repr`/`deepcopy` 마스킹 객체에 `field_path -> (sha256(field_text), frozenset[(start, end, bare_token)])`와 요청 `(sha256(user), system)`을 바인딩한다. 동일 토큰의 중복 출현도 각 출현 좌표를 모두 증명해야 신뢰한다.
- 마스킹기 산출 스팬: `MaskResult.token_spans`(다중 패스 좌표 이동 포함), `evidence_pack.projected_token_spans`, `_ModelInputRenderer.mask_attested`·`render_argument_context(..., spans_out=...)`가 실제 가림 위치만 수집한다.
- 소비 경로 연동: `detect_ai_document`, `argument_validity_verifier`(배치·단건 재시도·부분 에스컬레이션 `build_partial_argument_request` 항목 인덱스 재매핑), `rag_engine.review`(배치·구간 슬라이싱 `slice_token_spans`·검토 프로필 재바인딩), `pipeline._semantic_review` → `LLMRouter.cascade`(`req.user` 내 JSON/래퍼 오프셋 매핑 + `cascade_source.official.source_excerpt`·`cascade_source.document`).

### 2.4 구조화 필드 접두사·좌표 검증 및 999 상한 fail-closed (`privacy.py`, `pseudonym.py`, 런타임)
- 순수 인명 키(`성명` 등)는 `PERSON`, 역할 키(`원고`·`대표자` 등)는 `PERSON`·`COMPANY`·`AFFIL`만 허용한다. `_uncertain_person_value`는 증명 요청 시 원문 오프셋(`raw_matches`)과 대괄호 균형·좌표를 대조해 비증명 중복 출현·전각 변형을 차단한다.
- `PseudonymSequenceLimitError(ValueError)`: `MAX_PSEUDONYM_SEQUENCE(999)` 초과 시 부분 가림 반환·미처리 500·외부 LLM 호출 없이 안전하게 실패한다(`workspace.external_prompt_texts` HTTP 422, `rag_engine.review_document` 결과 초기화 후 `UNVERIFIED`, `VerificationPipeline` 단계 중단).

### 2.5 다중 패스 멱등성·증거 좌표 보존 (`packages/pii_engine/engine.py`)
- `PIIEngine.mask_text`는 일반 `str`에서 부분 중첩 잔여 후보가 있을 때만 최대 5회 유한 다중 패스를 돌며 후속 매치와 `token_spans`를 갱신한다. `TracedText` 단일 패스 `_mask_matches` 훅 계약과 대리인·법원 주소 보존은 유지한다.

## 3. 검증 계획
- 실 `PseudonymStore` + `_ModelInputRenderer`로 `PERSON_010`·`PHONE_010` 발급 후, 동일 유효 증명 요청의 별도 필드·중복 삽입에 `[PERSON_010] 2468-1357`, `[PHONE_010] 2468-1357`, `[PERSON_010] 1234-5678` 주입 시 모두 `BLOCKED`/`NOT_SENT`(provider 0회 호출) 검증(키·실명 비로깅).
- 정상 다중 출현·날짜 인접·`detect_ai_document`·`verify_argument_validity`(부분 에스컬레이션·단건 재시도)·`review_document`·`cascade`·`PseudonymSequenceLimitError` fail-closed 및 기존 위조·ReDoS·리터럴 회귀 검증.
