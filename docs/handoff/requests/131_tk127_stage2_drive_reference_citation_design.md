# [설계 메모] TK-127 2단계: 인용 행(판례·법령)의 Google Drive 색인 대조

- **작성일**: 2026-10-26
- **작성자**: Antigravity (구현 에이전트)
- **대상 브랜치**: `Steve_ACASiaLAW` (기준 SHA: `3fee071`)
- **상태**: 평가 측 검토 및 사용자 승인 대기 (제품 코드 및 시험 수정 0줄)

---

## 1. 배경 및 목적

- **배경**: TK-127 1단계(#183, Steve `3fee071`)를 통해 주요 참고문헌(Google Drive) 대조 의견이 화면 검토 표의 행에 바인딩되었습니다. 2단계는 사용자 원문(2026-10-25) *"공식데이터베이스의 자료를 API로 검색하는 것에 추가로 구글 DRIVE의 자료를 활용"* 요구 중 미이행분인 **인용 행(판례·법령)을 Google Drive 색인에서도 직접 찾아 근거로 연결**하는 기능을 다룹니다.
- **원칙**: 엔진 및 데이터 파이프라인의 확장이 수반되므로 제품 코드 수정에 앞서 본 설계 메모를 제출하여 평가 측 검토와 사용자 승인을 득한 후 구현에 착수합니다.

---

## 2. 항목별 세부 설계 및 근거 코드 위치

### 1) 인용 행의 Drive 조회 및 매칭 메커니즘
*(근거 코드 위치: `packages/rag_engine/review.py:137-190`, `packages/rag_engine/review.py:315-370`, `packages/rag_engine/library.py:330-380`)*
- **질의 생성 및 정규화 규칙**:
  - **판례 사건번호**:
    - 법원명 및 불필요한 공백 제거 후 연도·사건부호·일련번호 정규화.
    - 정규식 경계 매칭: `rf"(?<!\d){re.escape(canonical_case_no)}(?!\d)"` (예: `2021다12345` 앞뒤 비숫자 경계 대조).
    - 색인 조회: `ReferenceLibrary` 내 전문 색인에서 정규화된 사건번호를 단일 질의어로 조회.
  - **법령명 및 조문**:
    - 법령명 내 특수기호(`「`, `」`, `『`, `』`) 및 공백 제거(예: `민법`, `근로기준법`).
    - 조문 정규화 패턴: `rf"제\s*{re.escape(str(article))}\s*조"`
    - 근접 윈도우 대조: 조문 출현 위치 기준 앞뒤 100자 이내에 정규화된 법령명이 함께 출현하는지 대조 (`_match_citations_to_references`).
- **색인 범위 한계 및 발췌 길이**:
  - 색인 상한: `ReferenceLibrary`의 파일 수 상한(`MAX_SOURCES`, 기본 5~6개 파일) 및 대용량 문서 색인 페이지 한도 준수.
  - 발췌 길이: 판례 인용은 사건번호 출현 전후 문맥 200~400자, 법령 인용은 해당 조문 윈도우 200~500자(`EXCERPT_CHARS` 최대 1,000자 이내)로 한정하여 과도한 토큰 소비 방지.
- **로컬 전용(`LOCAL_ONLY`) 및 빠른 검토(`QUICK`) 원칙**:
  - `context.profile == VerificationProfile.QUICK` 또는 `context.external_ai_policy == ExternalAIPolicy.LOCAL_ONLY`인 경우(`review.py:377-390`), 외부 LLM 호출을 원천 배제하고 파이썬 정규식 및 텍스트 윈도우 기반의 결정론적 로컬 매칭(`_match_citations_to_references` 확장)만 수행.
- **공식 확인(`OFFICIAL_CONFIRMED`) 격상 불가 원칙 및 화면 표시**:
  - Google Drive 자료는 사설 참고문헌이므로, 공식 DB(대법원·국가법령정보) API 확인 없이 `OFFICIAL_CONFIRMED`로 격상하지 않음 (`official_status` 불변 유지).
  - 참고자료 지지 상태(`reference_status`)를 `SUPPORTED`로 갱신하거나 `evidence_sources`에 Drive 출처를 추가 (`review_items.py:196-229`).
  - 화면 표시 문구는 1단계와 동일하게 `참고문헌(구속력 없음, 공식 확인 아님)` 또는 `주요 참고문헌 대조(구속력 없음)`를 유지하여 사용자의 법적 효력 오인을 방지.

### 2) 서버 연결 (Server-Side `reference_observations` 동기화)
*(근거 코드 위치: `packages/verification_engine/review_items.py:87-140`, `packages/verification_engine/pipeline.py:488-520`, `packages/common/schemas.py:618-665`, `apps/web/static/app.js:2060-2086`)*
- **서버 생성 방식**:
  - 기존 1단계에서는 클라이언트 브라우저(`app.js`)가 `attachReferenceObservations()`를 통해 동적 바인딩하던 로직을 서버 파이프라인의 `packages/verification_engine/review_items.py`(`build_document_review_items`)로 이전.
  - `ReviewItem` 도메인 모델(`packages/common/schemas.py`)에 `reference_observations: List[Dict[str, Any]] = field(default_factory=list)` 필드를 공식 추가하고 `to_dict()`에 직렬화 포함.
- **매칭 계약 (1단계 화면 규칙과 100% 동일)**:
  1. `observation.claim_id` $\rightarrow$ 문서 `claims[].citation_ids` $\rightarrow$ 검토 행의 `citation_id` 일치 시 매칭.
  2. 1번 실패 시, 공백 제거 후 8자 이상인 `observation.claim_quote`와 `item.claim_text` 간의 상호 부분 포함 관계(`claim.includes(quote) || quote.includes(claim)`) 검사 (`app.js:2076-2080`).
- **검증 시험 설계**:
  - `tests/test_tk127_stage2_server_reference_observations_sync.py`: 서버에서 생성된 `review_items[*].reference_observations`의 매칭 결과가 기존 클라이언트 `attachReferenceObservations`의 결과와 정확히 일치함을 보장하는 회귀 시험 구축.
  - 클라이언트(`app.js`)는 서버가 이미 바인딩한 `reference_observations`가 있을 경우 재연산 없이 이를 우선 렌더링하고, 구버전 API 응답에 대해서만 폴백 바인딩을 수행하도록 구성.

### 3) 보고서 반영 계획
*(근거 코드 위치: `packages/report_engine/pdf_report.py:290+`, `packages/report_engine/docx_report.py:226+`, `packages/report_engine/exporters.py:91, 236+`, `packages/report_engine/external_answers.py`)*
- **반영 대상 형식**: PDF, Word(docx), Excel(xlsx), JSON 내보내기.
- **배치 위치**:
  - 인용 검토 표의 '근거 자료 / 대조 결과' 열(3열)에 `[참고문헌 대조]` 소제목과 함께 출처 파일명 및 발췌 내용을 표시.
- **TK-129 '외부 AI 참고 의견' 절과의 중복 방지**:
  - TK-129에서 추가된 섹션은 사용자가 외부 AI(ChatGPT, Claude 등)의 답변을 브라우저에 임포트하여 검토한 '외부 AI 질의 답변' 독립 절(`external_answers.py`)임.
  - TK-127 2단계의 Drive 대조는 엔진 파이프라인이 내부 Google Drive 문서를 색인/검색하여 인용 행에 자동 매칭한 것임.
  - 따라서 TK-129의 외부 AI 절과 완전히 분리하여, 인용 검토 표 내의 개별 행 근거 자료(3열)에 독립 표기.

### 4) 측정 방안 및 안정성 기준
*(근거 코드 위치: `scripts/score_gate.py`, `scripts/scorecard.py`, `scripts/check_case_literals.py`, `scripts/check_test_edits.py`)*
- **오프라인 세트의 한계와 실측 방안**:
  - 개발(dev), 홀드아웃(holdout), 은퇴(retired) 세트는 고정 오프라인 서면이며 Drive 연동이 비활성화(`RAG_DRIVE_FOLDER_ID=""`)되어 있어 점수 도구로 효과 측정이 불가함.
  - 따라서 운영 Drive 폴더가 설정된 실제 운영 환경에서 실서면 1건 이상을 입력하여:
    1. **인용 행 Drive 매칭 수(Hit Count)** 측정.
    2. 검토 화면 표에서 인용 행 3열에 Drive 참고문헌 블록이 정상 렌더링된 화면 캡처 1건 이상 증빙.
- **안정성 게이트 통과 기준**:
  - 오프라인 점수 게이트(`python scripts/score_gate.py`): dev 82.6 이상, holdout 81.9 이상 유지 (점수 하락 0).
  - 오탐(False Positive) 0건 유지.
  - 사건 고유값 방지(`check_case_literals.py`) 및 시험 편집 보호(`check_test_edits.py`) 통과.

### 5) 성능 및 개인정보 보호 (PII)
*(근거 코드 위치: `packages/rag_engine/review.py:391-430`, `packages/pii_engine/detector.py:880-920`, `packages/common/enums.py:ExternalAIPolicy`)*
- **성능 상한 (시간 예산)**:
  - 인용 행 다수 존재 시 인용별 개별 색인 호출을 지양하고, 서면 내 모든 인용(사건번호·법령조문)을 1회의 역색인/필터링 패스로 일괄 매핑.
  - 인용 행 대조 단계 전체에 최대 3~5초의 타임아웃 상한을 적용하여 초과 시 로컬 매칭 결과까지만 안전하게 반환.
- **개인정보 보호 정책 준수**:
  - Drive 발췌문 및 서면 인용문을 외부 모델에 전송해야 할 경우 `context.external_ai_policy` 철저 준수:
    - `LOCAL_ONLY`: 외부 전송 금지.
    - `MASKED`: `PIIEngine.mask_text()`를 거쳐 식별정보를 비식별화 후 전송.
    - `ORIGINAL`: 사용자 명시적 허용 시에만 전송.

---

## 3. 사전에 확인할 기존 시험 및 코드 위치 요약표 (기준 SHA: `3fee071`)

본 PR에서는 제품 코드 및 시험을 전혀 수정하지 않으며, 향후 구현 착수 시 연계될 핵심 모듈과 시험은 다음과 같습니다.

| 구분 | 파일 경로 | 관련 함수 / 위치 및 역할 |
| :--- | :--- | :--- |
| **RAG 엔진** | `packages/rag_engine/review.py` | 137~190행: `_match_citations_to_references` (사건번호 경계 일치, 법령명+조 근접 대조)<br>315~370행: `review_document` 인용 행 대조 메인 로직<br>377~390행: `QUICK` 및 `LOCAL_ONLY` 프로필 분기<br>391~430행: `_split_sources_into_batches` 배치 분할 |
| **Drive 라이브러리** | `packages/rag_engine/library.py` | 330~380행: `ReferenceLibrary.match_case`, `ReferenceLibrary.select` |
| **검토 항목 생성** | `packages/verification_engine/review_items.py` | 87~140행: `build_document_review_items`<br>196~229행: `reference_status` 결정부<br>269~285행: `evidence_sources` 생성부 |
| **파이프라인 단계** | `packages/verification_engine/pipeline.py` | 488~520행: `reference_review` 스테이지 및 RAG 대조 실행부 |
| **공통 스키마** | `packages/common/schemas.py` | 618~665행: `ReviewItem` 데이터클래스 정의 및 `to_dict` 직렬화 |
| **웹 화면** | `apps/web/static/app.js` | 2060~2086행: `attachReferenceObservations` (클라이언트 매칭 규칙)<br>2096~2113행: `referenceObservationBlock` (3열 대조 블록 렌더링) |
| **보고서 엔진** | `packages/report_engine/pdf_report.py`<br>`packages/report_engine/docx_report.py`<br>`packages/report_engine/exporters.py` | PDF/Word/JSON 검토 표 3열 렌더링 및 `ReviewItem` 내보내기 |
| **관련 기존 시험** | `tests/test_drive_rag_relevance.py`<br>`tests/test_f2_review_screen_browser.py`<br>`tests/test_tk126_flat_tabs_answer_import.py`<br>`tests/test_tk129_report_external_answers.py` | Drive RAG 관련성 시험, 검토 화면 통합 렌더링 시험, 1단계 평면 탭 시험, 외부 AI 답변 분리 시험 |

---

## 4. 향후 절차

1. 본 설계 메모 PR 제출 및 평가 측(Codex) 검토, 사용자 승인.
2. 승인 완료 후 세부 구현 티켓(PR) 발행 및 구현 착수.
3. 제품 코드 수정 전후 회귀 게이트 및 운영 Drive 실측 검증 완료 후 병합.
