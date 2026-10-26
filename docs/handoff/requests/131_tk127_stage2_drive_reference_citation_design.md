# [설계 메모] TK-127 2단계: 인용 행(판례·법령)의 Google Drive 색인 대조

- **작성일**: 2026-10-26 (2차 개정)
- **작성자**: Antigravity (구현 에이전트)
- **대상 브랜치**: `Steve_ACASiaLAW` (기준 제품 코드 SHA: `3fee071`)
- **문서 성격**: 설계 제안 메모 (본 PR에서는 제품 코드 및 시험 수정 0줄 유지)
- **상태**: 평가 측(Codex) 재검토 및 사용자 승인 대기

---

## 1. 배경 및 목적

- **배경**: TK-127 1단계(#183, Steve `3fee071`)를 통해 주요 참고문헌(Google Drive) 대조 의견이 웹 검토 표의 행에 바인딩되었습니다. 2단계는 사용자 요구(2026-10-25) *"공식데이터베이스의 자료를 API로 검색하는 것에 추가로 구글 DRIVE의 자료를 활용"* 중 미이행분인 **인용 행(판례·법령)을 Google Drive 색인에서도 직접 찾아 근거로 연결**하는 기능을 다룹니다.
- **원칙**: 엔진 및 데이터 파이프라인의 확장이 수반되므로 제품 코드 수정에 앞서 본 설계 제안을 제출하여 평가 측(Codex) 검토와 사용자 승인을 득한 후 별도 구현 티켓으로 착수합니다.

---

## 2. 항목별 세부 설계 및 근거 코드 위치

### 1) 인용 행의 Drive 조회 및 매칭 메커니즘
*(근거 코드 위치: `packages/rag_engine/review.py:137-190`, `packages/rag_engine/review.py:326-371`, `packages/rag_engine/library.py:613-762`, `packages/rag_engine/library.py:905-919`)*
- **질의 생성 및 정규화 규칙**:
  - **판례 사건번호**:
    - 법원명 및 불필요한 공백 제거 후 연도·사건부호·일련번호 정규화.
    - 정규식 경계 매칭: `rf"(?<!\d){re.escape(canonical_case_no)}(?!\d)"` (사건번호 앞뒤 비숫자 경계 대조, `review.py:163-164`).
    - 색인 조회: `ReferenceLibrary` 내 전문 색인에서 정규화된 사건번호를 단일 질의어로 조회하거나, 표준 판례표가 존재할 경우 `ReferenceLibrary.match_case`(`library.py:905-919`)로 정확 일치 조회.
  - **법령명 및 조문**:
    - 법령명 내 특수기호(`「`, `」`, `『`, `』`) 및 공백 제거 (예: `민법`, `근로기준법`).
    - 조문 정규화 패턴: `rf"제\s*{re.escape(str(article))}\s*조"`
    - 근접 윈도우 대조: 조문 출현 위치 기준 앞뒤 100자 이내에 정규화된 법령명이 함께 출현하는지 대조 (`_match_citations_to_references`, `review.py:169-180`).
- **단계별 용량·처리 한도 구분 (기준 SHA `3fee071` 설정 대조)**:
  - **색인/동기화 단계 한도 (`ReferenceLibrary._sync_files`, `library.py:304-608`)**:
    - `rag_inventory_max_files`: Drive 폴더 내 인벤토리 수집 상한. 기본값 **20,000개 파일** (설정: `LV_RAG_INVENTORY_MAX_FILES`, `packages/common/config.py:114`).
    - `rag_max_files`: 1회 동기화 시 새로 색인(파싱/저장)할 파일 수 예산 한도. 기본값 **1,000개 파일** (설정: `LV_RAG_MAX_FILES`, `packages/common/config.py:113`, `library.py:372-373`).
    - `rag_download_mb`: 파일 다운로드 크기 한도. 기본값 **128MB** (설정: `LV_RAG_DOWNLOAD_MB`, `packages/common/config.py:116`).
    - `rag_sync_seconds`: 동기화 실행 타임아웃. 기본값 **120초** (설정: `LV_RAG_SYNC_SECONDS`, `packages/common/config.py:112`).
  - **검색/선택 단계 한도 (`ReferenceLibrary.select`, `library.py:613-762`)**:
    - `ReferenceLibrary.select(text, limit=12)`: 서면 본문 및 키워드 기반으로 색인 코퍼스에서 연관성이 높은 참고자료 발췌(`sources`)를 선택하는 함수. 기본값 **최대 12개 발췌** (`library.py:613, 741`).
    - `ReferenceLibrary.search_case_table(text, limit=5)`: 구조화 판례 사건표 대조 시 선택 개수. 기본값 **최대 5개 행** (`library.py:920, 953`).
  - **외부 모델 배치 단계 한도 (`review.py:_split_sources_into_batches`, `review.py:394-435`)**:
    - `max_items_limit = 6`: 배치당 최대 참고자료 개수 **6개**.
    - `max_chars_limit = 6000`: 배치당 최대 발췌 글자 수 합계 **6,000자**.
    - *(주의: 5~6개 파일은 색인 상한이 아니며, 외부 모델 호출 프롬프트에 실어 보낼 때의 단일 배치 묶음 한도임).*
  - **발췌 목표 길이 (향후 구현 설계 목표)**:
    - 판례 인용은 사건번호 출현 전후 200~400자, 법령 인용은 해당 조문 윈도우 200~500자(최대 1,000자 이내)로 한정하여 토큰 소비를 최소화하도록 구현 목표 설정.
- **로컬 전용(`LOCAL_ONLY`) 및 빠른 검토(`QUICK`) 원칙**:
  - `context.profile == VerificationProfile.QUICK` 또는 `context.external_ai_policy == ExternalAIPolicy.LOCAL_ONLY`인 경우(`review.py:377-390`), 외부 LLM 호출을 전면 배제하고 파이썬 정규식 및 텍스트 윈도우 기반의 결정론적 로컬 매칭(`_match_citations_to_references` 확장)만 수행.
- **공식 확인(`OFFICIAL_CONFIRMED`) 격상 불가 원칙 및 화면 표시**:
  - Google Drive 자료는 사설 참고문헌이므로, 공식 DB(대법원·국가법령정보) API 확인 없이 `OFFICIAL_CONFIRMED`로 격상하지 않음 (`official_status` 불변 유지).
  - 참고자료 지지 상태(`reference_status`)를 `SUPPORTED`로 갱신하거나 `evidence_sources`에 Drive 출처를 추가 (`review_items.py:196-229`).
  - 화면 표시 문구는 1단계와 동일하게 `참고문헌(구속력 없음, 공식 확인 아님)` 또는 `주요 참고문헌 대조(구속력 없음)`를 유지하여 사용자의 법적 효력 오인을 방지 (`app.js:2098`).

### 2) 서버 연결 및 대체 매칭 계약 (Server-Side `reference_observations` 동기화)
*(근거 코드 위치: `packages/verification_engine/review_items.py:87-140`, `packages/verification_engine/pipeline.py:488-525`, `packages/common/schemas.py:618-665`, `apps/web/static/app.js:2060-2086`)*
- **서버 생성 방식**:
  - 1단계에서는 클라이언트 브라우저(`app.js`)가 `attachReferenceObservations()`를 통해 렌더링 시점에 동적 바인딩하던 로직을 서버 파이프라인의 `packages/verification_engine/review_items.py`(`build_document_review_items`)로 이전.
  - `ReviewItem` 도메인 모델(`packages/common/schemas.py:618-641`)에 `reference_observations: List[Dict[str, Any]] = field(default_factory=list)` 필드를 추가하고 `to_dict()`(`schemas.py:642-665`)에 직렬화 포함.
- **매칭 계약 상세 (기준 SHA `3fee071`의 `app.js:2060-2086` 동작과 정밀 일치)**:
  1. **정규화 방식 (`compactText`)**:
     - 자바스크립트 `compactText(text)` = `String(text || "").replace(/\s+/g, "")` (`app.js:2062`).
     - 서버 구현은 `re.sub(r"\s+", "", str(text or ""))`로 연속 공백 문자를 완전히 제거하여 동일한 문자열로 정규화.
  2. **1순위: ID 기반 우선 매칭**:
     - 관찰의 `claim_id` $\rightarrow$ 문서 `claims[].citation_ids` 조회 $\rightarrow$ 검토 행의 `citation_id`가 해당 목록에 포함되면 즉시 매칭 (`app.js:2074-2075`).
  3. **2순위: 대체 매칭 (Fallback) 엄격 조건**:
     - 1순위 매칭 실패 시에만 시도.
     - 정규화된 관찰 인용문: `quote_compact = compactText(observation.claim_quote)`
     - **조건 A (인용문 길이)**: `len(quote_compact) >= 8` (8자 이상)
     - **조건 B (주장 텍스트 길이)**: 각 후보 행의 정규화된 주장 텍스트 `claim_compact = compactText(item.claim_text)`에 대해 `len(claim_compact) >= 8` (8자 이상)
     - **조건 C (상호 부분 포함)**: `(quote_compact in claim_compact) or (claim_compact in quote_compact)`
     - **반드시 조건 A, 조건 B, 조건 C가 모두 충족될 때만 대체 매칭 성공** (`app.js:2076-2080`).
  4. **실패 및 제외 조건**:
     - `len(quote_compact) < 8`인 경우 대체 매칭을 시도하지 않고 즉시 매칭 실패 처리.
     - 후보 행의 `len(claim_compact) < 8`인 경우 해당 행은 대체 매칭 대상에서 제외.
     - 양쪽 모두 8자 이상이라도 상호 부분 포함되지 않으면 매칭 실패.
     - 매칭 실패 시 관찰은 `unmatched`로 분류되어 독립된 `kind: "REFERENCE"` 행으로 생성됨 (`app.js:2082, 2087-2095`).
- **향후 구현 회귀 시험 계획**:
  - `tests/test_tk127_stage2_server_reference_observations_sync.py` (향후 티켓에서 구현):
    - 동일한 입력 검증 결과(문서 `claims`, `citations`, RAG `observations`)에 대해,
    - Python 서버 로직(`build_document_review_items`)이 생성한 `item.reference_observations` 할당 결과와,
    - 브라우저 JS 로직(`attachReferenceObservations`)의 실행 결과(매칭된 행 ID, 미매칭 건수, 할당된 관찰 내용)가 단 1건의 오차도 없이 100% 동일함을 단언하는 동등성 검증 시험 구축.
  - 클라이언트(`app.js`)는 서버에서 이미 채워진 `item.reference_observations`가 존재할 경우 이를 우선 채택하고, 구버전 API 응답 등 누락된 경우에만 브라우저 폴백을 수행하도록 호환성 유지.

### 3) 보고서 반영 계획
*(근거 코드 위치: `packages/report_engine/pdf_report.py:290-350`, `packages/report_engine/docx_report.py:226-280`, `packages/report_engine/exporters.py:91, 236-300`, `packages/report_engine/external_answers.py`)*
- **반영 대상 형식**: PDF, Word(docx), Excel(xlsx), JSON 내보내기.
- **배치 위치**:
  - 인용 검토 표의 '근거 자료 / 대조 결과' 열(3열)에 `[참고문헌 대조]` 소제목과 함께 출처 파일명 및 발췌 내용을 표시.
- **TK-129 '외부 AI 참고 의견' 절과의 명확한 분리**:
  - TK-129에서 추가된 섹션은 사용자가 브라우저에서 직접 외부 AI(ChatGPT, Claude 등)의 답변을 임포트하여 검토한 '외부 AI 질의 답변' 독립 절(`external_answers.py`, `doc_result.external_ai_answers`)임.
  - TK-127 2단계의 Drive 대조는 엔진 파이프라인이 로컬 Google Drive 문서를 색인/검색하여 인용 행에 자동 매칭한 사설 참고자료 대조 결과임.
  - 따라서 TK-129의 외부 AI 절과 완전히 분리하여, 인용 검토 표 내의 개별 행 근거 자료(3열)에 독립 표기.

### 4) 측정 방안 및 안정성 기준
*(근거 코드 위치: `scripts/score_gate.py`, `scripts/scorecard.py`, `scripts/check_case_literals.py`, `scripts/check_test_edits.py`)*
- **오프라인 세트의 한계와 실측 방안**:
  - 개발(dev), 홀드아웃(holdout), 은퇴(retired) 세트는 고정 오프라인 서면이며 Drive 연동이 비활성화(`RAG_DRIVE_FOLDER_ID=""`)되어 있어 점수 측정 도구로는 Drive 검색 효과를 직접 측정할 수 없음.
  - 따라서 오프라인 점수 게이트(`python scripts/score_gate.py`)는 **회귀 방지(Regression Gate)** 목적으로만 활용하며, dev 82.6 이상, holdout 81.9 이상 유지 및 오탐(False Positive) 0건 유지를 안정성 통과 기준으로 설정.
- **운영 Drive 환경 실측 방안 (향후 구현 검증 단계)**:
  - 실제 운영 Drive 폴더가 설정된 환경에서 실서면 1건 이상을 검증 파이프라인에 입력.
  - **보안 및 개인정보 보호 엄수**: PR 및 보고서 작성 시 실제 사건번호, 당사자명, 서면 원문, 구체적 문구의 노출을 엄격히 금지함 (`check_case_literals.py` 준수).
  - 검증 증빙 자료는 **비식별화된 집계 지표(인용 행 Drive 매칭 건수 Hit Count)** 및 개인정보/사건 식별정보가 완전 마스킹된 웹 화면 캡처 1건으로 한정.

### 5) 성능 및 개인정보 보호 (PII)
*(근거 코드 위치: `packages/rag_engine/review.py:391-430`, `packages/pii_engine/detector.py:880-920`, `packages/common/enums.py:ExternalAIPolicy`)*
- **성능 목표 (향후 구현 설계 목표)**:
  - 인용 행 다수 존재 시 인용별 개별 색인 호출을 지양하고, 서면 내 모든 인용(사건번호·법령조문)을 1회의 역색인/필터링 패스로 일괄 매핑하는 아키텍처 지향.
  - 인용 행 대조 단계 전체에 대해 타임아웃 상한(예: 3~5초 시간 예산 목표)을 두어 초과 시 안전하게 graceful degradation(로컬 매칭 결과까지만 반환)하도록 설계.
  - *(주의: 3~5초는 측정된 확정 한계가 아니라 향후 구현에서 충족해야 할 설계 목표 예산임).*
- **개인정보 보호 정책 준수**:
  - Drive 발췌문 및 서면 인용문을 외부 모델에 전송해야 할 경우 `context.external_ai_policy` 철저 준수:
    - `LOCAL_ONLY`: 외부 전송 원천 금지 (로컬 정규식 매칭만 수행).
    - `MASKED`: `PIIEngine.mask_text()`를 거쳐 개인식별정보를 비식별화 후 전송.
    - `ORIGINAL`: 사용자 명시적 허용 시에만 전송.

---

## 3. 사전에 확인할 기존 시험 및 코드 위치 요약표 (기준 SHA: `3fee071`)

본 PR에서는 제품 코드 및 시험을 전혀 수정하지 않으며, 향후 구현 착수 시 연계될 핵심 모듈과 시험은 다음과 같습니다. 기준 SHA `3fee071`의 실제 코드 위치와 전수 대조를 마쳤습니다.

| 구분 | 파일 경로 | 실제 함수 / 심볼 및 줄 번호 (기준 SHA `3fee071`) | 역할 및 검증 포인트 |
| :--- | :--- | :--- | :--- |
| **RAG 엔진** | `packages/rag_engine/review.py` | 137~190행: `_match_citations_to_references`<br>326~371행: `review_document` 인용 대조 부<br>377~390행: `QUICK` 및 `LOCAL_ONLY` 프로필 분기<br>394~435행: `_split_sources_into_batches` | 사건번호 경계 일치, 법령명+조 근접 대조<br>서면 인용 대조 및 `reference_matches` 생성<br>외부 모델 차단 및 결정론적 매칭 반환<br>모델 배치 분할 (최대 6개, 6,000자) |
| **Drive 라이브러리** | `packages/rag_engine/library.py` | 304~608행: `_sync_files` (372행 `rag_max_files`)<br>613~762행: `ReferenceLibrary.select`<br>764~765행: `ReferenceLibrary.search`<br>905~919행: `ReferenceLibrary.match_case`<br>920~967행: `ReferenceLibrary.search_case_table` | 파일 동기화 및 신규 색인 예산 (기본 1000개)<br>문서 연관 자료 선택 (기본 limit=12 발췌)<br>단순 검색 래퍼<br>구조화 판례표 정확 대조<br>사건표 행 단위 관련 검색 (기본 limit=5) |
| **검토 항목 생성** | `packages/verification_engine/review_items.py` | 87~140행: `build_document_review_items`<br>167~306행: 인용 검토 행(CITATION) 생성 루프<br>196~229행: `reference_status` 결정 부<br>268~285행: `evidence_sources` 출처 생성 부 | 단일 문서 검토 항목 생성 메인 함수<br>인용 행 생성 및 필드 바인딩<br>참고자료 지지 상태 결정<br>Drive 출처 링크 및 대조 결과 추가 |
| **파이프라인 단계** | `packages/verification_engine/pipeline.py` | 479~484행: `reference_sync` 매니페스트 스테이지<br>488~525행: `reference_review` 매니페스트 스테이지 | 참고자료 동기화 파이프라인 단계<br>문서별 Drive 대조 실행 파이프라인 단계 |
| **공통 스키마** | `packages/common/schemas.py` | 605~614행: `ReviewItemKind` Enum<br>618~641행: `ReviewItem` 데이터클래스<br>642~665행: `ReviewItem.to_dict()` | 검토 항목 종류 정의<br>`reference_observations` 필드 추가 대상<br>직렬화 사전 변환 |
| **웹 화면** | `apps/web/static/app.js` | 2062행: `compactText`<br>2063~2086행: `attachReferenceObservations`<br>2087~2095행: `referenceObservationRow`<br>2096~2113행: `referenceObservationBlock`<br>2114~2130행: `referenceStatusLine` | 공백 제거 정규화 함수<br>브라우저 측 행 연결 (1순위 ID, 2순위 양쪽 8자)<br>미매칭 관찰 행 생성<br>3열 참고문헌 대조 블록 렌더링<br>표 위 상태 줄 렌더링 |
| **보고서 엔진** | `packages/report_engine/pdf_report.py`<br>`packages/report_engine/docx_report.py`<br>`packages/report_engine/exporters.py`<br>`packages/report_engine/external_answers.py` | `pdf_report.py`: 290~350행<br>`docx_report.py`: 226~280행<br>`exporters.py`: 91행, 236~300행<br>`external_answers.py`: 1~90행 | PDF 검토 표 3열 렌더링<br>Word 검토 표 3열 렌더링<br>JSON/Excel `review_items` 내보내기<br>TK-129 외부 AI 답변 독립 절 (분리 유지) |
| **설정** | `packages/common/config.py` | 111~116행: `rag_*` 설정 필드 | `rag_max_files`(기본 1000), `rag_inventory_max_files`(기본 20000), `rag_download_mb`(기본 128), `rag_sync_seconds`(기본 120) |
| **관련 기존 시험** | `tests/test_drive_rag_relevance.py`<br>`tests/test_f2_review_screen_browser.py`<br>`tests/test_tk126_flat_tabs_answer_import.py`<br>`tests/test_tk129_report_external_answers.py` | 각 테스트 파일 전체 (기준 SHA `3fee071`) | Drive RAG 관련성 시험<br>검토 화면 통합 렌더링 시험<br>1단계 평면 탭 시험<br>외부 AI 답변 보고서 분리 시험 |

---

## 4. 향후 절차

1. 본 설계 메모 2차 개정안 제출 및 평가 측(Codex) 재검토, 사용자 승인.
2. 승인 완료 후 세부 구현 티켓 발행 및 제품 코드/시험 구현 착수.
3. 제품 코드 수정 전후 오프라인 회귀 게이트(`score_gate.py`) 및 운영 Drive 실측 검증 완료 후 병합.
