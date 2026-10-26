# [설계 메모] TK-127 2단계: 인용 행(판례·법령)의 Google Drive 색인 대조

- **작성일**: 2026-10-26 (5차 개정)
- **작성자**: Antigravity (구현 에이전트)
- **대상 브랜치**: `Steve_ACASiaLAW` (기준 제품 코드 SHA: `3fee071c17921c9add11167250744f646903cee3`)
- **문서 성격**: 설계 제안 메모 (본 PR에서는 제품 코드 및 시험 수정 0줄 유지)
- **상태**: 평가 측(Codex) 재검토 대기

---

## 1. 배경 및 목적

- **배경**: TK-127 1단계(#183, Steve `3fee071c17921c9add11167250744f646903cee3`)를 통해 주요 참고문헌(Google Drive) 대조 의견이 웹 검토 표의 행에 바인딩되었습니다. 2단계는 사용자 요구(2026-10-25) *"공식데이터베이스의 자료를 API로 검색하는 것에 추가로 구글 DRIVE의 자료를 활용"* 중 미이행분인 **인용 행(판례·법령)을 Google Drive 색인에서도 직접 찾아 근거로 연결**하는 기능을 다룹니다.
- **원칙**: 엔진 및 데이터 파이프라인의 확장이 수반되므로 제품 코드 수정에 앞서 본 설계 제안을 제출하여 평가 측(Codex) 검토와 사용자 승인을 득한 후 별도 구현 티켓으로 착수합니다. 점수나 테스트 결과를 임의로 고정하거나 성능을 사전 단정하지 않으며, 코드 참조는 유동적인 행 번호 대신 파일 경로와 심볼명을 기준으로 관리합니다.

---

## 2. 항목별 세부 설계 및 근거 코드 심볼

### 1) 인용 행의 Drive 조회 및 매칭 메커니즘
*(근거 심볼: `packages/rag_engine/review.py` 내 `_match_citations_to_references`, `review_document`, `packages/rag_engine/library.py` 내 `ReferenceLibrary.select`, `ReferenceLibrary.match_case`)*
- **질의 생성 및 정규화 규칙**:
  - **판례 사건번호**:
    - 법원명 및 불필요한 공백 제거 후 연도·사건부호·일련번호 정규화.
    - 정규식 경계 매칭: `rf"(?<!\d){re.escape(canonical_case_no)}(?!\d)"` (사건번호 앞뒤 비숫자 경계 대조, `_match_citations_to_references`).
    - 색인 조회: `ReferenceLibrary` 내 전문 색인에서 정규화된 사건번호를 단일 질의어로 조회하거나, 표준 판례표가 존재할 경우 `ReferenceLibrary.match_case`로 정확 일치 조회.
  - **법령명 및 조문**:
    - 법령명 내 특수기호(`「`, `」`, `『`, `』`) 및 공백 제거 (예: `민법`, `근로기준법`).
    - 조문 정규화 패턴: `rf"제\s*{re.escape(str(article))}\s*조"`
    - 근접 윈도우 대조: 조문 출현 위치 기준 앞뒤 100자 이내에 정규화된 법령명이 함께 출현하는지 대조 (`_match_citations_to_references`).
- **단계별 용량·처리 한도 구분 (기준 SHA `3fee071c17921c9add11167250744f646903cee3` 설정 대조)**:
  - **색인/동기화 단계 한도 (`ReferenceLibrary._sync_files`)**:
    - `rag_inventory_max_files`: Drive 폴더 내 인벤토리 수집 상한. 기본값 **20,000개 파일** (설정: `LV_RAG_INVENTORY_MAX_FILES`, `packages/common/config.py`).
    - `rag_max_files`: 1회 동기화 시 새로 색인(파싱/저장)할 파일 수 예산 한도. 기본값 **1,000개 파일** (설정: `LV_RAG_MAX_FILES`, `packages/common/config.py`, `library.py`의 `_sync_files`).
    - `rag_download_mb`: 파일 다운로드 크기 한도. 기본값 **128MB** (설정: `LV_RAG_DOWNLOAD_MB`, `packages/common/config.py`).
    - `rag_sync_seconds`: 동기화 실행 타임아웃. 기본값 **120초** (설정: `LV_RAG_SYNC_SECONDS`, `packages/common/config.py`).
  - **검색/선택 단계 한도 (`ReferenceLibrary.select`)**:
    - `ReferenceLibrary.select(text, limit=12)`: 서면 본문 및 키워드 기반으로 색인 코퍼스에서 연관성이 높은 참고자료 발췌(`sources`)를 선택하는 함수. 기본값 **최대 12개 발췌** (`library.py`).
    - `ReferenceLibrary.search_case_table(text, limit=5)`: 구조화 판례 사건표 대조 시 선택 개수. 기본값 **최대 5개 행** (`library.py`).
  - **외부 모델 배치 단계 한도 (`review.py`의 `_split_sources_into_batches`)**:
    - `max_items_limit = 6`: 배치당 최대 참고자료 개수 **6개**.
    - `max_chars_limit = 6000`: 배치당 최대 발췌 글자 수 합계 **6,000자**.
    - *(주의: 5~6개 파일은 색인 상한이 아니며, 외부 모델 호출 프롬프트에 실어 보낼 때의 단일 배치 묶음 한도임).*
  - **발췌 목표 길이 (향후 구현 설계 목표)**:
    - 판례 인용은 사건번호 출현 전후 200~400자, 법령 인용은 해당 조문 윈도우 200~500자(최대 1,000자 이내)로 한정하여 토큰 소비를 최소화하도록 구현 목표 설정.
- **로컬 전용(`LOCAL_ONLY`) 및 빠른 검토(`QUICK`) 원칙**:
  - `context.profile == VerificationProfile.QUICK` 또는 `context.external_ai_policy == ExternalAIPolicy.LOCAL_ONLY`인 경우(`review.py`의 프로필 분기), 외부 LLM 호출을 전면 배제하고 파이썬 정규식 및 텍스트 윈도우 기반의 결정론적 로컬 매칭(`_match_citations_to_references` 확장)만 수행.
- **공식 확인(`OFFICIAL_CONFIRMED`) 격상 불가 원칙 및 화면 표시**:
  - Google Drive 자료는 사설 참고문헌이므로, 공식 DB(대법원·국가법령정보) API 확인 없이 `OFFICIAL_CONFIRMED`로 격상하지 않음 (`official_status` 불변 유지).
  - 참고자료 지지 상태(`reference_status`)를 `SUPPORTED`로 갱신하거나 `evidence_sources`에 Drive 출처를 추가 (`packages/verification_engine/review_items.py`).
  - 화면 표시 문구는 1단계와 동일하게 `참고문헌(구속력 없음, 공식 확인 아님)` 또는 `주요 참고문헌 대조(구속력 없음)`를 유지하여 사용자의 법적 효력 오인을 방지 (`apps/web/static/app.js`의 `referenceObservationBlock`).

### 2) 서버 연결 및 정규화·대체 매칭 계약
*(근거 심볼: `packages/verification_engine/review_items.py` 내 `build_document_review_items`, `packages/verification_engine/pipeline.py` 내 `reference_review`, `packages/common/schemas.py` 내 `ReviewItem`, `apps/web/static/app.js` 내 `attachReferenceObservations`)*

- **서버 생성 방식**:
  - 1단계에서는 클라이언트 브라우저(`app.js`)가 `attachReferenceObservations()`를 통해 렌더링 시점에 동적 바인딩하던 로직을 서버 파이프라인의 `packages/verification_engine/review_items.py`(`build_document_review_items`)로 이전.
  - `ReviewItem` 도메인 모델(`packages/common/schemas.py`)에 `reference_observations: List[Dict[str, Any]] = field(default_factory=list)` 필드를 추가하고 `to_dict()`에 직렬화 포함.

- **공백 정규화 계약 (Python과 JavaScript 간 명시적 문자 집합 규약)**:
  - **배경 및 원인**:
    - JavaScript 정규식 `\s`와 Python `re \s`는 매칭하는 유니코드 공백 집합이 다릅니다.
    - 예컨대 `U+FEFF`(BOM)는 JavaScript `\s`에서는 매칭되어 제거되나, Python `re \s`에서는 형식 문자(`Cf`)로 취급되어 제거되지 않고 남습니다.
    - 반대로 `U+001C~U+001F`(ASCII 제어 분리자 4종)의 경우도 정규식 엔진 환경에 따라 취급 차이가 존재합니다.
    - 따라서 언어별 메타문자 `\s`에 동작을 위임하면 서버와 브라우저 간 정규화 결과가 어긋나 매칭이 깨질 수 있습니다.
  - **권위 있는 공통 공백 문자 집합 (White-list of Whitespace) 확정**:
    두 구현은 언어별 `\s`를 직접 쓰지 않고, 아래 **명시적 문자 코드포인트 집합을 완전히 동일하게 제거 대상 공백으로 확정**합니다:
    1. **기본 ASCII 공백 및 제어문자**: `\u0020`(스페이스), `\u0009`(`\t`), `\u000A`(`\n`), `\u000D`(`\r`), `\u000B`(`\v`), `\u000C`(`\f`)
    2. **ASCII 정보 분리 제어문자 (명시적 포함 확정)**: `\u001C`(FS), `\u001D`(GS), `\u001E`(RS), `\u001F`(US) — 서면 파싱/OCR 텍스트에 포함될 수 있으므로 양쪽 모두 공백 제거 대상에 명시적으로 포함함.
    3. **유니코드 특수 공백**: `\u00A0`(NBSP), `\u1680`, `\u2000`~`\u200A`(En/Em Space 등), `\u2028`(Line Separator), `\u2029`(Paragraph Separator), `\u202F`(Narrow NBSP), `\u205F`(Math Space), `\u3000`(전각 공백)
    4. **무폭 제어/BOM 문자**: `\uFEFF`(BOM / Zero Width No-Break Space)
  - **명시적 구현 표현 (언어별 `\s` 사용 금지)**:
    - **공통 명시적 정규식 문자 클래스**:
      `[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]+`
    - **Python 예시 구현**:
      ```python
      EXPLICIT_WHITESPACE_RE = re.compile(
          r"[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]+"
      )
      def compact_text(text: str) -> str:
          return EXPLICIT_WHITESPACE_RE.sub("", str(text or ""))
      ```
    - **JavaScript 예시 구현**:
      ```javascript
      const EXPLICIT_WHITESPACE_RE = /[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]+/g;
      function compactText(text) {
        return String(text || "").replace(EXPLICIT_WHITESPACE_RE, "");
      }
      ```
    - *(주의: 실제 양 언어 정규화 모듈의 완전한 일치 여부는 향후 구현 티켓에서 동등성 시험을 통과하기 전까지 무조건적 일치로 사전 단정하지 않고 설계 제안 규약으로 관리함).*

- **매칭 계약 순서 및 엄격 조건**:
  1. **1순위: ID 기반 우선 매칭**:
     - 관찰의 `claim_id` $\rightarrow$ 문서 `claims[].citation_ids` 조회 $\rightarrow$ 검토 행의 `citation_id`가 해당 목록에 포함되면 즉시 매칭 (`app.js`의 `attachReferenceObservations`).
  2. **2순위: 대체 매칭 (Fallback) 엄격 조건**:
     - 1순위 매칭 실패 시에만 시도.
     - 정규화된 관찰 인용문: `quote_compact = compact_text(observation.claim_quote)`
     - **조건 A (인용문 길이)**: `len(quote_compact) >= 8` (8자 이상)
     - **조건 B (주장 텍스트 길이)**: 각 후보 행의 정규화된 주장 텍스트 `claim_compact = compact_text(item.claim_text)`에 대해 `len(claim_compact) >= 8` (8자 이상)
     - **조건 C (상호 부분 포함)**: `(quote_compact in claim_compact) or (claim_compact in quote_compact)`
     - **반드시 조건 A, 조건 B, 조건 C가 모두 충족될 때만 대체 매칭 성공** (`app.js`의 `attachReferenceObservations`).
  3. **실패 및 제외 조건**:
     - `len(quote_compact) < 8`인 경우 대체 매칭을 시도하지 않고 즉시 매칭 실패 처리.
     - 후보 행의 `len(claim_compact) < 8`인 경우 해당 행은 대체 매칭 대상에서 제외.
     - 양쪽 모두 8자 이상이라도 상호 부분 포함되지 않으면 매칭 실패.
     - 매칭 실패 시 관찰은 `unmatched`로 분류되어 독립된 `kind: "REFERENCE"` 행으로 생성됨 (`app.js`의 `referenceObservationRow`).

- **향후 구현 회귀 시험 계획 (구현 티켓 수용 조건)**:
  - `tests/test_tk127_stage2_server_reference_observations_sync.py`:
    1. **문자 집합 경계 테스트 케이스 (공통 집합 안팎의 경계 문자 포함)**:
       - `U+FEFF` (BOM / Zero Width No-Break Space) 포함 입력
       - `U+001C~U+001F` (ASCII 정보 분리 제어문자 4종) 포함 입력 — 공통 집합에 포함되어 정상 제거되는지 검증
       - 일반 공백 (`U+0020`), 탭 (`\t`, `U+0009`), 줄바꿈 (`\r`, `\n`)
       - `U+00A0` (NBSP)
       - `U+3000` (전각 공백)
    2. **길이 경계 조건 테스트**:
       - 7자: 공통 공백 제거 후 7자 이하 시 대체 매칭 배제 (미매칭 확인)
       - 8자: 공통 공백 제거 후 8자 이상 시 대체 매칭 진입 및 부분 포함 시 성공 확인
    3. **양방향 부분 포함 테스트**:
       - `quote`가 `claim`을 포함하는 경우
       - `claim`이 `quote`를 포함하는 경우
       - 상호 포함되지 않는 경우 (매칭 실패)
    4. **ID 우선 매칭 보장**:
       - 1순위 `claim_id` $\rightarrow$ `citation_id` 일치 시 대체 매칭 미실행 보장
    5. **1:1 결과 비교 단언**:
       - 동일 입력 데이터셋에 대해 Python `build_document_review_items`가 반환한 행 ID 및 `reference_observations` 할당 결과와, JS 브라우저 `attachReferenceObservations`의 실행 결과(매칭 행 ID, 미매칭 행, 할당 목록)를 1:1 비교하여 정규화 및 최종 매칭 결과의 일치 여부를 검증.

### 3) 보고서 반영 계획
*(근거 심볼: `packages/report_engine/pdf_report.py` 내 `build_report_pdf`, `packages/report_engine/docx_report.py` 내 `build_report_docx`, `packages/report_engine/exporters.py` 내 `to_payload`, `to_json`)*
- **반영 대상 형식**: PDF, Word(docx), Excel(xlsx), JSON 내보내기.
- **배치 위치**:
  - 인용 검토 표의 '근거 자료 / 대조 결과' 열(3열)에 `[참고문헌 대조]` 소제목과 함께 출처 파일명 및 발췌 내용을 표시.
- **TK-129 '외부 AI 참고 의견' 절과의 명확한 분리**:
  - 기준 SHA `3fee071c17921c9add11167250744f646903cee3` 시점에는 `external_answers.py`가 없으며, 향후 TK-129가 병합되면 들어올 '외부 AI 질의 답변' 독립 절(`external_answers.py`, `doc_result.external_ai_answers`)과 본 Drive 대조를 완전히 분리.
  - TK-127 2단계의 Drive 대조는 엔진 파이프라인이 로컬 Google Drive 문서를 색인/검색하여 인용 행에 자동 매칭한 사설 참고자료 대조 결과이므로, 인용 검토 표 내의 개별 행 근거 자료(3열)에 독립 표기.

### 4) 측정 방안 및 안정성 기준
*(근거 심볼: `scripts/score_gate.py`, `docs/scorecards/baseline.json`, `scripts/scorecard.py`, `scripts/check_case_literals.py`, `scripts/check_test_edits.py`)*
- **오프라인 점수 게이트의 역할 및 출처 (회귀 방지 전용)**:
  - 권위 있는 점수 판정은 CI에서 실행되는 `python scripts/score_gate.py`가 동일 SHA에서 권위 있는 기준선 파일(`docs/scorecards/baseline.json`)과 비교하여 점수 하락이 없음을 검증하는 것입니다.
  - 현재 기준선(`docs/scorecards/baseline.json`, 기준 SHA `3fee071c17921c9add11167250744f646903cee3`)에 기록된 관찰값은 다음과 같습니다:
    - 개발 세트 (`sets.dev`): 가중 재현율 `weighted_recall: 0.826` (82.6점), 오탐 `false_positives: 0`
    - 홀드아웃 세트 (`sets.holdout`): 가중 재현율 `weighted_recall: 0.819` (81.9점), 오탐 `false_positives: 0`
  - 위 수치는 기준선의 현재 관찰값이며, 별도의 독립된 임의 합격 기준선이 아닙니다. 향후 구현 시에도 별도 기준을 신설하지 않고 `score_gate.py`의 기준선 대조 판정을 단일 권위 기준으로 삼습니다.
- **오프라인 세트의 한계 및 Drive 실측 방안**:
  - 개발(dev), 홀드아웃(holdout), 은퇴(retired) 세트는 고정 오프라인 서면이며 Google Drive 연동이 비활성화(`RAG_DRIVE_FOLDER_ID=""`)되어 있으므로, 오프라인 점수 게이트로는 Google Drive 검색/대조의 실제 효과나 성능 향상을 입증할 수 없습니다. 오프라인 게이트 통과는 기존 검증 기능에 대한 '회귀 없음(No Regression)'만을 보증합니다.
  - Google Drive 연동 기능의 실제 효과는 향후 운영 Drive 환경에서 실제 서면을 입력하여 검증해야 합니다.
  - **보안 및 개인정보 보호 엄수**: 운영 Drive 실측 검증 시 실제 사건번호, 당사자명, 서면 원문, 구체적 문구의 노출을 엄격히 금지합니다 (`check_case_literals.py` 준수). 검증 증빙 자료는 **비식별화된 집계 지표(인용 행 Drive 매칭 건수 Hit Count)** 및 개인정보/사건 식별정보가 완전 마스킹된 웹 화면 캡처 1건으로 한정합니다.

### 5) 성능 및 개인정보 보호 (PII)
*(근거 심볼: `packages/rag_engine/review.py` 내 `_split_sources_into_batches`, `packages/pii_engine/detector.py` 내 `PIIEngine.mask_text`, `packages/common/enums.py` 내 `ExternalAIPolicy`)*
- **성능 목표 (향후 구현 설계 목표)**:
  - 인용 행 다수 존재 시 인용별 개별 색인 호출을 지양하고, 서면 내 모든 인용(사건번호·법령조문)을 1회의 역색인/필터링 패스로 일괄 매핑하는 아키텍처 지향.
  - 인용 행 대조 단계 전체에 대해 타임아웃 상한(예: 3~5초 시간 예산 목표)을 두어 초과 시 안전하게 graceful degradation(로컬 매칭 결과까지만 반환)하도록 설계.
  - *(주의: 3~5초는 측정된 확정 제약이 아니라 향후 구현에서 달성해야 할 설계 목표 예산임).*
- **개인정보 보호 정책 준수**:
  - Drive 발췌문 및 서면 인용문을 외부 모델에 전송해야 할 경우 `context.external_ai_policy` 철저 준수:
    - `LOCAL_ONLY`: 외부 전송 원천 금지 (로컬 정규식 매칭만 수행).
    - `MASKED`: `PIIEngine.mask_text()`를 거쳐 개인식별정보를 비식별화 후 전송.
    - `ORIGINAL`: 사용자 명시적 허용 시에만 전송.

---

## 3. 사전에 확인할 기존 시험 및 코드 위치 요약표 (기준 SHA: `3fee071c17921c9add11167250744f646903cee3`)

본 PR에서는 제품 코드 및 시험을 전혀 수정하지 않으며, 향후 구현 착수 시 연계될 핵심 모듈과 시험은 다음과 같습니다. 파일별 행 번호는 커밋 및 포맷팅에 따라 유동적일 수 있으므로 **파일 경로와 심볼명**을 기준으로 관리합니다.

| 구분 | 파일 경로 | 주요 함수 / 설정 심볼 (기준 SHA `3fee071c17921c9add11167250744f646903cee3`) | 역할 및 검증 포인트 |
| :--- | :--- | :--- | :--- |
| **RAG 엔진** | `packages/rag_engine/review.py` | `_match_citations_to_references`<br>`review_document`<br>`_split_sources_into_batches` | 사건번호 경계 일치, 법령명+조 근접 대조<br>서면 인용 대조 및 결과 수집, QUICK/LOCAL_ONLY 분기<br>모델 배치 분할 (최대 6개, 6,000자) |
| **Drive 라이브러리** | `packages/rag_engine/library.py` | `ReferenceLibrary._sync_files`<br>`ReferenceLibrary.select`<br>`ReferenceLibrary.search`<br>`ReferenceLibrary.has_case_tables`<br>`ReferenceLibrary.case_table_status`<br>`ReferenceLibrary.match_case`<br>`ReferenceLibrary.search_case_table` | 파일 동기화 및 신규 색인 예산 (`rag_max_files`)<br>문서 연관 자료 선택 (기본 `limit=12` 발췌)<br>단순 검색 래퍼<br>표 후보 존재 여부 확인<br>표 후보 색인 상태 반환<br>구조화 판례표 정확 대조<br>사건표 행 단위 관련 검색 (기본 `limit=5`) |
| **검토 항목 생성** | `packages/verification_engine/review_items.py` | `derive_item_severity`<br>`build_document_review_items` | Finding 심각도 순수 파생<br>단일 문서 검토 항목 생성 메인 함수 (인용 행 루프, `reference_status` 결정, `evidence_sources` 출처 생성, 미연결 Finding 루프) |
| **파이프라인 단계** | `packages/verification_engine/pipeline.py` | `manifest.stage("reference_sync")`<br>`manifest.stage("reference_review")` | 참고자료 동기화 파이프라인 단계<br>문서별 Drive 대조 실행 파이프라인 단계 |
| **공통 스키마** | `packages/common/schemas.py` | `ReviewItemKind` (Enum)<br>`ReviewItem` (dataclass)<br>`ReviewItem.to_dict()` | 검토 항목 종류 정의<br>`reference_observations` 필드 추가 대상<br>직렬화 사전 변환 |
| **웹 화면** | `apps/web/static/app.js` | `compactText`<br>`attachReferenceObservations`<br>`referenceObservationRow`<br>`referenceObservationBlock`<br>`referenceStatusLine` | 공백 제거 정규화 함수<br>브라우저 측 행 연결 (1순위 ID, 2순위 양쪽 8자)<br>미매칭 관찰 행 생성<br>3열 참고문헌 대조 블록 렌더링<br>표 위 상태 줄 렌더링 |
| **보고서 엔진** | `packages/report_engine/pdf_report.py`<br>`packages/report_engine/docx_report.py`<br>`packages/report_engine/exporters.py` | `build_report_pdf`<br>`build_report_docx`<br>`to_payload`, `to_json` | PDF 검토 표 렌더링<br>Word 검토 표 렌더링<br>JSON/Excel `review_items` 내보내기<br>*(참고: `external_answers.py`는 기준 SHA 시점 미존재)* |
| **설정** | `packages/common/config.py` | `Settings.rag_drive_folder_id`<br>`Settings.rag_sync_seconds`<br>`Settings.rag_max_files`<br>`Settings.rag_inventory_max_files`<br>`Settings.rag_download_mb` | Drive 폴더 ID<br>동기화 타임아웃 (기본 120초)<br>신규 색인 파일 상한 (기본 1,000개 파일)<br>인벤토리 수집 상한 (기본 20,000개 파일)<br>다운로드 한도 (기본 128MB) |
| **관련 기존 시험** | `tests/test_drive_rag_relevance.py`<br>`tests/test_f2_review_screen_browser.py`<br>`tests/test_tk126_flat_tabs_answer_import.py` | 파일 전체 | Drive RAG 관련성 시험<br>검토 화면 통합 렌더링 시험<br>1단계 평면 탭 시험 |

---

## 4. 향후 절차

1. 본 설계 메모 5차 개정안 제출 및 평가 측(Codex) 재검토, 사용자 승인.
2. 승인 완료 후 세부 구현 티켓 발행 및 제품 코드/시험 구현 착수.
3. 제품 코드 수정 전후 오프라인 회귀 게이트(`score_gate.py`) 및 운영 Drive 실측 검증 완료 후 병합.
