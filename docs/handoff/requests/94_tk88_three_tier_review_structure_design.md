# 설계 메모: TK-88 검토 화면 3단 체계 개편 및 법률적 검증 분류 설계

- **문서 번호:** `requests/94_tk88_three_tier_review_structure_design.md` (2026-10-21 2차 판정 피드백 3개 항목 반영 전면 개정)
- **작성일:** 2026-10-20 (1차), 2026-10-21 (2차 개정), 2026-10-21 (3차 전면 개정: 판정 문장 우선순위, 실제 보고서 모듈/형식/시험 매핑)
- **작성자:** Antigravity (구현 에이전트)
- **대상 티켓:** TK-88 (사용자 개선안 3다·4항: 검토 화면 3단 체계 재편)
- **수용 기준:** 탐지 diff 0, 채점기·match_spec 불변, 고정·은퇴 세트 점수 불변, 실제 보고서 7개 내보내기 형식 및 시험 계약 보존

---

## 1. 배경 및 문제 정의

- **현행 한계:**
  1. 출처 확인(공식 DB 판례·법령 조회 결과)과 법리 타당성(주장 내용의 무리함)이 '확인할 항목' 표 한 줄에 혼재되어, 사용자가 "출처가 허위/부존재한 것"인지 "출처는 실재하나 주장이 왜곡된 것"인지 직관적으로 구분하기 어려움.
  2. 주요 참고문헌(RAG) 결과가 표 아래 별도 구역에 접혀 있어 본문 대조 내용과 유기적으로 연결되지 못함.
  3. '주장·쟁점' 탭에 남아 있는 복잡한 워크플로우 입력(쟁점 편집, 인부, 지지 상태 등)은 프로그램 본래 목적인 "서면의 위험 요인 확인"과 괴리됨.

---

## 2. 3단 체계 구성 및 우선순위 기반 분류 매트릭스 (피드백 1·2 반영)

```
[1단] AI 작성·보안 진단 (기존 탭 유지)
  └─ AI 생성 의심 지표, 시스템 지시문/인젝션 채널 탐지

[2단] 판례·법령·주요참고문헌 인용 오류·미확인 검토 (AI 작성 여부 판단과 별개)
  └─ 인용한 판례·법령·참고문헌의 공식 DB 부존재, 서지 불일치, 원문-인용문 불일치, 시적 적용 오류, 성립 불가 사건번호

[3단] 법률적으로 무리한 주장 (기존 '주장·쟁점' 탭 자리 대체)
  └─ 가짜 출처 기반 주장(AI_HALLUCINATED_CONTENT), 출처 취지에 반하는 부당 주장, 사실관계 상이, 참고자료 모순(TK-70)
```

---

### (1) 법리 검토 판정 문장(`validity_verdict`)과 우선순위 분류 체계 (피드백 1 반영)

`packages/legal_engine/argument_validity_verifier.py`의 실제 코드 구현에 기반하여, 단순 부분 문자열 매칭의 왜곡을 방지하기 위한 **3단계 우선순위 분류 순서**를 확정합니다:

**분류 우선순위:**
1. **1순위: 결과 유형 (`FindingType` / `rule_id`):** 고유 보안/출처/참고자료 모순 규칙 우선.
2. **2순위: 공식 조회 및 출처 상태 (`basis` / `official_lookup_status` / `error_category`):** 출처 자체의 부존재·불성립 검증 우선.
3. **3순위: 법리 검토 판정 문장 (`validity_verdict`):** 실재하는 출처에 기초한 변론 타당성 당부 평가.

#### [표 1] 실제 판정 문장 및 결과 유형별 2단/3단 분류표

| 순서 | 판정 문장 (`validity_verdict`) 또는 결과 유형 | 실제 생성 위치 및 속성 | 배치 단 | 분류 이유 및 처리 원칙 |
|---|---|---|---|---|
| **1** | `"근거 결여 (성립 불가한 사건번호)"` | `argument_validity_verifier.py` 78행<br>(`basis="FABRICATION_SUSPECTED"`, `error_category="LEGAL_CITATION_ERROR"`) | **2단** | **출처 불성립(2단 배정):** 문장에 '결여'가 포함되어 있으나 본질은 연도/사건부호가 존재할 수 없는 '성립 불가 사건번호'라는 객관적 출처 오류임. 2단계 출처 우선순위 원칙에 따라 2단에 배치. |
| **2** | `"공식 DB 미확인 (원문 확인 필요)"` | `argument_validity_verifier.py` 381행<br>(`basis="UNCONFIRMED"`) | **2단** | **출처 미확인(2단 배정):** 공식 DB에 수록되지 않은 판례/법령의 객관적 출처 확인 필요 항목. |
| **3** | `"인용문 변형 (원문과 어절 차이)"`<br>`"인용 내용 불일치 (원문 대조 필요)"` | `argument_validity_verifier.py` 367~368행<br>(`mismatch=True`, `error_category="LEGAL_CITATION_ERROR"`) | **2단** | **원문-인용문 불일치(2단 배정):** 판례는 실재하나 본문 인용문과 공식 원문 어절 간의 물리적 차이 검증. |
| **4** | `CASE_HOLDING_DISTORTION`<br>(판시 취지 왜곡) | `enums.py`<br>(판례 원문 판결요지와 서면 인용 취지 괴리) | **2단** | **인용문 왜곡(2단 배정):** 판례 원문과 서면 인용문 사이의 '객관적 인용 왜곡/불일치'이므로 출처 검증(2단)에 배치. (단, 아래 3단 부당 주장과 1:1 상호 참조 링크 제공) |
| **5** | `TEMPORAL_LAW_MISMATCH`<br>(시적 적용 오류) | `enums.py`<br>(행위시 미시행 구법령/폐지법령 인용) | **2단** | **조항 유효성 오류(2단 배정):** 법령 조항의 유효성 및 시적 적용 시점의 형식적/객관적 불일치. |
| **6** | `"판례 취지 왜곡 (판시사항과 상반 / 부당)"` | `argument_validity_verifier.py` 339행<br>(`contradiction=True`, `finding_status=CONTRADICTED`) | **3단** | **무리한 주장(3단 배정):** 대법원 판례의 명시적 판결 취지와 정반대로 주장하는 변론의 법리적 부당성. 2단의 `CASE_HOLDING_DISTORTION`과 상호 참조 연결. |
| **7** | `"적용 차이 (사실관계 상이 / 전문가 검토 필요)"` | `argument_validity_verifier.py` 347행<br>(`distinguishable=True`, `error_category="APPLICATION_DIFFERENCE"`) | **3단** | **무리한 유추적용(3단 배정):** 판례 사안과 본 사건의 사실관계가 달라 유추적용이 무리한 주장 검토. |
| **8** | `rule_id` = `RAG.REFERENCE_CONTRADICTION`<br>(참고자료 내용 모순, TK-70) | `packages/rag_engine`<br>(실무편람·업무지침 내용 정면 위반) | **3단** | **실무상 무리한 주장(3단 배정):** 주요 실무편람/지침에 반하는 법률적 무리 주장. |
| **9** | `AI_HALLUCINATED_CONTENT` | `enums.py` 381행<br>(가짜 판례·조문 기반 법률 주장) | **3단** | **허위 근거 기반 무리한 주장(3단 배정):** 상세 논거는 아래 (2) 참조. |
| **10** | `"공식 원문 일치 (사건 적용성 직접 검토 필요)"` | `argument_validity_verifier.py` 354행<br>(`basis="OFFICIAL_CONFIRMED"`) | **2단** | **공식 확인 완료 안내:** 별도 Finding 없이 공식 확인 상태 안내로 2단 하단에 표시. |

---

### (2) `AI_HALLUCINATED_CONTENT`의 3단 배치 이유 및 2단과의 상호 참조 관계 (피드백 2 반영)

1. **3단 배치 이유:**
   - `AI_HALLUCINATED_CONTENT`는 단순히 "사건번호를 찾지 못함"에 그치지 않고, 실재하지 않는 가공의 판례나 법률 조항을 전제로 변론을 구성한 **'허위 근거에 기반한 법률적으로 무리한 주장'**입니다.
   - 변호사가 법정에 제출해서는 안 되는 가장 심각한 수준의 법리적 위험 요인이므로, 검토자가 공격·방어 관점에서 해당 주장의 법률적 부당성을 즉각 식별할 수 있도록 3단에 배치합니다.
2. **2단과의 상호 참조(Cross-reference) 체계:**
   - **발생 원천과 변론 결과의 분리 및 연결:**
     - **2단:** 인용된 판례/법령의 물리적 부존재 및 형식 불성립 검증 (`CASE_NOT_FOUND`, `LAW_CITATION_ERROR`, `"근거 결여 (성립 불가한 사건번호)"`).
     - **3단:** 해당 허위 출처를 기반으로 구축된 법률 주장의 배척 필요성 경고 (`AI_HALLUCINATED_CONTENT`, `LEGAL_ARGUMENT_INVALID`).
   - **UI 앵커 링크:** 3단 표의 해당 항목에 `[2단 출처 부존재 확인 →]` 앵커를 제공하여, 사용자가 원천적인 출처 결함과 이를 바탕으로 한 법률적 무리 주장을 원클릭으로 상호 교차 확인할 수 있도록 합니다.

---

## 3. 법률적 측면의 참고문헌(RAG) 표시 조건

1. **법적 구속력 배제 명시:**
   - 업무편람, 실무제요 등은 행정·사법 실무 해설서일 뿐 법적 구속력이 없음.
   - 배지(`참고문헌(구속력 없음)`)를 명시하고, 위험 지수 산정 제외(`gate.py` 159·238행)를 엄격히 유지.
2. **'대조 안 함' vs '부합'의 엄격한 분별:**
   - 색인 범위 제한(운영 기준 31건 중 5건), 주장별 대조 상한, 문서 앞 12,000자 기준 등으로 인하여 대조 대상에 포함되지 않은 문헌/주장은 절대로 '부합'으로 표시하지 않음.
   - 반드시 **'대조 안 함(미대조)'** 상태로 명시.
3. **주장·쟁점 탭 정리:**
   - 기존의 불필요한 입력 도구(쟁점 편집, 인부, 지지 상태)를 제거하고 3단 전용 4열 요약 표로 전환.

---

## 4. 데이터 계약 및 실제 보고서 7개 내보내기 형식 영향 (피드백 3 반영)

- **백엔드 계약 불변:** `Finding` 스키마, 유형 코드, 등급(`EvidenceGrade`), 심각도(`Severity`), match_spec은 일절 변경하지 않음 (diff 0).
- **실제 내보내기 형식 7개(`MEDIA_TYPES`, `apps/api/routers/reports.py` 48~54·650~651행) 영향 및 기존 시험 대응표:**

| 내보내기 형식 (`MEDIA_TYPES`) | 담당 엔진 / 모듈 | 변경 사항 | 기존 시험 대응표 |
|---|---|---|---|
| **`json`** (`application/json`) | `packages/report_engine/snapshot.py`<br>`serialize.py` | **일절 변경 없음 (diff 0).** 스키마, 키(`findings`, `review_items`), enum 값 100% 보존. | `tests/test_report_completion.py`<br>`tests/test_report_timeline_exclusion.py` (해시 및 스냅숏 불변 검증 통과) |
| **`manifest`** (`application/json`) | `packages/report_engine/snapshot.py` | **일절 변경 없음 (diff 0).** 무결성 검증 레코드 및 해시 규격 보존. | `tests/test_report_completion.py` (manifest 일치 검증 통과) |
| **`csv`** (`text/csv`) | `packages/report_engine/exporters.py` | **열 구조 및 데이터 불변 (diff 0).** 기존 파이프라인 호환. | `tests/test_report_completion.py` (CSV 필드 검증 통과) |
| **`xlsx`** (`openxmlformats`) | `packages/report_engine/exporters.py` | **시트 구성 및 셀 데이터 불변 (diff 0).** 기존 엑셀 다운로드 호환. | `tests/test_report_completion.py` (엑셀 워크북 무결성 검증 통과) |
| **`highlight`** (`application/pdf`) | `packages/report_engine/pdf_report.py`<br>원문 주석 엔진 | **원문 하이라이트 레이어 불변 (diff 0).** 본문 위치 좌표 및 하이라이트 색상 보존. | `tests/test_report_completion.py` (하이라이트 PDF 생성 검증 통과) |
| **`docx`** (`wordprocessingml`) | `packages/report_engine/docx_report.py` | '확인할 항목' 표 섹션 내에 3단 그룹 헤더(소제목 단락: 1. AI·보안, 2. 출처·인용 미확인, 3. 법률적 무리 주장) 서식 추가 | `tests/test_report_completion.py` (Word 문서 표 렌더링 검증 통과) |
| **`pdf`** (`application/pdf`) | `packages/report_engine/pdf_report.py`<br>(**ReportLab 기반**, Playwright 아님) | `_build_flowables` 내에서 '확인할 항목' Table 렌더링 시 3단 섹션 헤더 단락 및 스타일 적용 | `tests/test_report_completion.py`<br>`tests/test_frontend_report_progress.py` (진행률 가중치 `pdf: 4` 불변 검증 통과) |

---

## 5. 시험 및 검증 계획

1. **실제 진입점 화면 시험 (`tests/test_three_tier_review_browser.py`):**
   - 2단 패널: `CASE_NOT_FOUND`, `CASE_METADATA_MISMATCH`, `CASE_HOLDING_DISTORTION`, `TEMPORAL_LAW_MISMATCH`, `"근거 결여 (성립 불가한 사건번호)"` 렌더링 검증.
   - 3단 패널: `AI_HALLUCINATED_CONTENT`, `LEGAL_ARGUMENT_INVALID`, `RAG.REFERENCE_CONTRADICTION`, `"판례 취지 왜곡 (판시사항과 상반 / 부당)"` 렌더링 검증.
   - 2단-3단 상호 참조 링크(앵커) 클릭 시 스크롤 이동 및 하이라이트 검증.
   - 참고문헌 행의 '구속력 없음' 및 '대조 안 함' 배지 가시성 확인.
2. **보고서 무결성 회귀 시험:**
   - `tests/test_report_completion.py`를 통해 7개 형식(`pdf`, `docx`, `highlight`, `xlsx`, `json`, `csv`, `manifest`) 정상 생성 및 JSON 스냅숏 해시 불변 검증.
3. **탐지 및 채점 점수 불변:**
   - 고정 dev·holdout 세트 및 은퇴 4세트 측정 시 탐지 결과 diff 0 및 점수 불변 검증.
