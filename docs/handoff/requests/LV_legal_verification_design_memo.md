# ACASia_LAW 법률 검증 고도화 (LV-01~LV-06) 통합 설계 메모

**문서 번호**: docs/handoff/requests/LV_legal_verification_design_memo.md  
**작성자**: Antigravity (구현 에이전트)  
**기준 커밋(BASE)**: `Steve_ACASiaLAW` `3d54f77` (2026-11-10 승인 통합 최신 SHA)  
**상태**: 선행 구현 착수 (평가 에이전트 부재 중 사용자 지시에 따른 선행 구현)  

---

## 1. 개요 및 배경

본 설계 메모는 판례·법령 인용의 허위 또는 오류와 법적 주장상의 문제를 근거에 따라 체계적으로 발견하고, 정상 인용에 대한 강한 오탐(False Positive)과 변호사의 확인 시간을 획기적으로 줄이기 위한 **ACASia_LAW 법률 검증 고도화(LV-01~LV-06)**의 전체 의존 관계, 공용 계약 및 구현 사양을 정의한다.

평가 측 제안(`c63160e:docs/scorecards/proposal_legal_verification_2026-11-10.md`, P0~P6) 및 기술 검토를 바탕으로, 세트 득점 중심의 미시 수정을 지양하고 근거 추적 가능성, 판단 가능 범위와 보류의 적절성, 실무 활용성을 확보한다.

---

## 2. LV-01 ~ LV-06 의존 관계 및 구현 범위 표

| LV ID | 구현 범위 | 대상 파일 | Draft PR | 의존 관계 | 미확인 가정 및 영향 범위 | 자체 시험 상태 | 병합 대기 조건 |
|---|---|---|---|---|---|---|---|
| **LV-01** | **날짜 역할 및 기산점·제소기간 계산 전제 보존**<br>- 날짜 추출 시 역할 메타데이터 보존<br>- 소제기일 부재 시 `max(valid_dates)`/`today` 폴백 차단<br>- 기산점/소제기일 결여 시 '계산 보류' 명시 | `packages/legal_engine/legal_rules.py`<br>`packages/legal_engine/reference_dates.py` | [PR #252](https://github.com/stevelee0119/ACASia_LAW/pull/252) | 독립 (공용 날짜 역할 스키마 제공) | **가정**: 본문 내 면담 예정일 등 장래 일정은 소제기일로 전용하지 않음.<br>**영향**: 행정소송 제소기간 부당 도과 경고 대폭 제거. | 공개 합성 6건 통과 (`test_lv01`) | CI 통과, 평가 측 독립 평가 |
| **LV-02** | **주장 문맥 보존 및 평가 발췌-표시 분리**<br>- `_extract_linked_claim` 200자 강제 절단 해소<br>- 단서('다만')·예외·조건·부정어 문맥 보존<br>- 평가 컨텍스트와 UI 표시 요약 분리<br>- 마스킹 오프셋 역추적 매핑 | `packages/legal_engine/argument_validity_verifier.py`<br>`packages/common/schemas.py` | [PR #253](https://github.com/stevelee0119/ACASia_LAW/pull/253) | LV-01과 병렬 가능, LV-04~06의 입력 문맥 | **가정**: 평가 컨텍스트는 문장 경계 기준 최대 1,000자까지 확장.<br>**영향**: 예외 조항 탈락으로 인한 법리 오인 방지. | 공개 합성 6건 통과 (`test_lv02`) | CI 통과, 평가 측 검토 |
| **LV-03** | **판례·법령 존재 및 서지 판정 3단 체계화**<br>- 3단화: 확인됨 / 부존재 확인 / 확인 불가<br>- 수록 범위 확실한 출처만 부존재 확정<br>- 사건번호 구조(연도·부호·일자) 결정적 검사<br>- 법령 약칭·개정 이력 정규화 | `packages/legal_engine/citation_extractor.py`<br>`packages/legal_engine/citation_format.py`<br>`packages/legal_engine/source_review.py`<br>`packages/legal_engine/verifier.py` | [PR #254](https://github.com/stevelee0119/ACASia_LAW/pull/254) | LV-01 날짜 정규화 및 공용 열거형 활용 | **가정**: 하급심 판례 및 비공식 약칭은 공식 DB 미수록 가능성 인정.<br>**영향**: 실재 판례/법령의 부존재 단정 CRITICAL 오탐 0 달성. | 공개 합성 6건 통과 (`test_lv03`) | CI 통과, 평가 측 독립 평가 |
| **LV-04** | **인용문 진위 정렬 및 차이 유형 구조화 (CIT-FAB-Q)**<br>- 공식 원문과 서면 인용문 근사 정렬<br>- 차이 5종 분류(부정어, 주어·객체, 수치, 단서 탈락, 자구)<br>- 본문 미확보 시 '인용 대조 불가' 명시 | `packages/legal_engine/quote_diff.py`<br>`packages/legal_engine/quotation.py`<br>`packages/legal_engine/provision_content.py` | [PR #255](https://github.com/stevelee0119/ACASia_LAW/pull/255) | LV-03 판례/법령 본문 확보 결과에 의존 | **가정**: 요지만 확보되고 본문이 없으면 일치 단정을 유보함.<br>**영향**: 지어낸 인용문(CIT-FAB-Q 0.0) 정확 탐지. | 공개 합성 6건 통과 (`test_lv04`) | CI 통과, 평가 측 검토 |
| **LV-05** | **판시 취지 및 명제 왜곡 탐지 (CIT-MIS)**<br>- 판결요지 요건·효과·예외 명제 분리 대조<br>- 결정적 왜곡 3규칙(변경된 판례, 파기환송 원심 판단 오인, 반대의견 오인)<br>- 원문 근거 문장 검증(grounded evidence quote) | `packages/legal_engine/semantic_consensus.py`<br>`packages/legal_engine/opinion_attribution.py`<br>`packages/legal_engine/statute_ranges.py` | [PR #256](https://github.com/stevelee0119/ACASia_LAW/pull/256) | LV-02 문맥 보존 및 LV-03/04 서지/원문 정렬 활용 | **가정**: 전원합의체 변경 문구 사전 및 결정적 신호로 1차 탐지.<br>**영향**: 판시 취지 왜곡(CIT-MIS 0.0) 해소. | 공개 합성 6건 통과 (`test_lv05`) | CI 통과, 평가 측 독립 평가 |
| **LV-06** | **청구원인 요건사실 점검 및 실무 조치 안내**<br>- 청구원인별(민법 750, 741, 390 등) 요건사실 주장 누락 점검<br>- 확정오류/의심/확인불가 3분 조치 가이드(정정 후보, 확인 URL, 석명 신청 안)<br>- 로컬 미러 캐시 및 관측성 강화 | `packages/legal_engine/actionable_guidance.py`<br>`packages/legal_engine/pleading_structure.py`<br>`packages/verification_engine/pipeline.py` | [PR #257](https://github.com/stevelee0119/ACASia_LAW/pull/257) | 전체 LV 결과를 종합하여 요건 점검 및 실무 조치 표출 | **가정**: 본 진단은 변호사의 최종 판단을 대체하지 않는 보조 도구임.<br>**영향**: 검토 시간 단축 및 실무 활용도 극대화. | 공개 합성 6건 통과 (`test_lv06`) | CI 통과, 평가 측 독립 평가 |

---

## 3. 공용 계약 (Common Contracts)

### 3.1. 인용 출현 식별자 vs 법원·공식 ID 구분
- **출현 식별자 (`occurrence_id`)**: 서면 내에서 특정 인용이 발생한 개별 위치를 식별.
  - 형식: `{doc_id}_cit_{index}` (인용문) 또는 `{doc_id}_claim_{index}` (법률 주장).
  - 서면 본문에서同一 판례를 3번 인용하더라도 각각 고유한 `occurrence_id`가 부여되어 위치별 오류(특정 문맥에서의 왜곡 등)를 개별 추적함.
- **공식/정규 기관 ID (`authority_id`)**: 법원 또는 정부 공식 시스템의 표준 식별자.
  - 판례: `KR_SC_{사건번호}` (예: 대법원 2020다12345), `KR_CC_{사건번호}` (헌법재판소).
  - 법령: `KR_ACT_{법령ID}_{조문번호}` (예: 민법 제750조).
- 모든 결과 스키마는 `occurrence_id`와 `authority_id`를 명확히 분리 기록한다.

### 3.2. 인용/주장 본문 발췌 범위 vs 마스킹 범위 규약
- `raw_text`: 서면에 기재된 원형 표기 (예: "대법원 2021. 1. 1. 선고 2020다12345 판결").
- `claim_evaluation_context`: 법리 평가를 위한 원문 문맥. 단서('다만'), 예외, 조건, 부정어가 잘리지 않도록 문장 경계를 존중하여 최대 1,000자까지 확보.
- `claim_display_summary`: UI 및 보고서 표시용 축약문. 주어와 술어의 결합 관계를 보존한 최대 150~200자 요약.
- `masked_evaluation_context`: 외부 AI 및 모델 전달용 PII 가림 텍스트. 가림 전 원문과의 1:1 문자 위치 역추적 매핑(`char_map: List[Tuple[int, int]]`)을 반드시 보존.

### 3.3. 공용 판정 상태 열거형 (`LegalVerificationStatus`)
기존 2분법(확인/불일치)의 한계를 극복하기 위해 아래의 공용 상태 체계를 표준화한다:
```python
class LegalVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"                       # 확인됨: 공식 원문과 존재·서지·내용 완전 일치
    CONTRADICTED = "CONTRADICTED"               # 불일치/모순: 공식 원문 또는 확립된 법리와 명백히 충돌
    CONFIRMED_NONEXISTENT = "CONFIRMED_NONEXISTENT" # 부존재 확인: 수록 범위 확실한 출처에서 부존재 확정 (CRITICAL)
    SUSPICIOUS = "SUSPICIOUS"                   # 존재의심/오기: 성립 불가능한 사건번호/조문 표기
    CONTEXT_CAUTION = "CONTEXT_CAUTION"         # 맥락주의: 판례는 실재하나 취지 왜곡(변경된 판례, 반대의견 오인 등)
    UNCONFIRMED_SOURCE_LIMIT = "UNCONFIRMED_SOURCE_LIMIT" # 확인 불가: 하급심·약칭 등 출처 미수록 가능성 (CRITICAL 아님)
    SUSPENDED = "SUSPENDED"                     # 판단/계산 보류: 소제기일/기산점 등 필수 전제 결여
    UNVERIFIED = "UNVERIFIED"                   # 미검증: 검증 미실시
```

### 3.4. 날짜 역할(Date Role) 스키마
행정소송 제소기간, 민사 소멸시효 등의 법정 기간 계산 오류를 원천 차단하기 위해 날짜 역할 스키마를 정립한다:
```python
class LegalDateRole(StrEnum):
    DISPOSITION = "DISPOSITION"             # 처분일 (행정처분, 원처분일)
    NOTICE_RECEIVED = "NOTICE_RECEIVED"     # 인지일/통지일 (처분이 있음을 안 날)
    SERVICE = "SERVICE"                     # 송달일 (처분서 송달일)
    FILING = "FILING"                       # 소제기일/심판청구접수일 (법원/위원회 접수일)
    DRAFTING = "DRAFTING"                   # 서면 작성일 (문서 말미 작성 일자)
    INCIDENT = "INCIDENT"                   # 불법행위/사고 발생일
    SCHEDULED = "SCHEDULED"                 # 출석/면담 예정일 (장래 일정)
    UNKNOWN = "UNKNOWN"                     # 역할 불명

class DatePremiseStatus(StrEnum):
    CONFIRMED = "CONFIRMED"                 # 명시적 기재로 확인됨
    INFERRED = "INFERRED"                   # 문맥상 합리적 추론
    HYPOTHETICAL = "HYPOTHETICAL"           # 가정적 진술
    UNVERIFIED = "UNVERIFIED"               # 미확인
```
- **계산 전제 규칙**: `FILING` 또는 `DRAFTING` 날짜가 명시되지 않은 경우, 문서 내 다른 날짜의 최댓값(`max(valid_dates)`)이나 오늘 날짜(`date.today()`)로 대체하지 않고 반드시 `SUSPENDED`("계산 보류: 소제기일 또는 기산점 미기재")로 처리한다.

### 3.5. 응답 스키마 버전 (`schema_version`)
- 응답 스키마 버전: `"2.0.0"`
- 하위 호환성 원칙: 기존 `Finding`, `ReviewItem`, `HallucinationTableRow` 필드를 100% 유지하며, 신규 고도화 필드(`authority_id`, `occurrence_id`, `date_premises`, `diff_categories`, `actionable_guidance`)는 선택적(Optional) 속성으로 확장하여 기존 API 소비자 및 테스트의 회귀를 방지한다.

---

## 4. 미결정 사항 및 제안 범위 한정

1. **외부 유료 API 연동 및 온라인 모델 확장**:
   - 본 구현은 오프라인 및 로컬 결정론적 규칙, 기존 어댑터를 최우선으로 정비한다.
   - 대규모 외부 전송이나 유료 법률 DB API 계약 확장은 별도 제안으로 분리한다.
2. **독립 평가 권한 존중**:
   - 구현 측의 자체 단위/합성 시험 통과는 제품 수용이나 독립 평가 통과를 의미하지 않으며, 최종 병합 및 배포는 평가 측 및 사용자의 절차에 따른다.
