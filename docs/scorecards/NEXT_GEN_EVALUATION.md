# AegisLAW (ACASia_LAW) 차세대 평가체계 및 품질 검증 명세서 (Next-Gen Evaluation Spec)

- **작성일**: 2026-11-19
- **관련 문서**:
  - [`docs/architecture/NEXT_GEN_BASELINE.md`](../architecture/NEXT_GEN_BASELINE.md)
  - [`docs/architecture/NEXT_GEN_ARCHITECTURE.md`](../architecture/NEXT_GEN_ARCHITECTURE.md)
  - [`docs/roadmap/NEXT_GEN_IMPLEMENTATION_PLAN.md`](../roadmap/NEXT_GEN_IMPLEMENTATION_PLAN.md)
- 이 명세는 평가 방법과 목표를 정의한다. 수치 기준선은 출처 명세에 기록된 값이다. 123개 항목의 도달 가능성 분류와 102건의 개별 경고 판정은 별도 측정 작업으로 기록한다.

---

## 1. 평가체계 개편의 핵심 원칙

1. **조건이 다른 점수의 합산·혼동 금지**:
   - **오프라인 회귀 시험(`LV_ALLOW_NETWORK=0`, 공식 DB·LLM 없음)** 과 **온라인/리플레이 통합 시험(공식 법령·판례 원문 및 Drive RAG 포함)** 은 서로 다른 능력을 측정하므로 절대 하나의 숫자로 합산하여 목표 달성 여부를 주장하지 않는다.
2. **오프라인 법률 결함(123항목)의 도달 가능성 3분류 분리**:
   - 오프라인 법률 재현율 `35.0% (43/123)`를 단일 분모로만 두면, 공식 원문 없이는 원천적으로 판정할 수 없는 항목(`UNVERIFIED`가 정답인 항목)과 알고리즘 미탐이 뒤섞인다. 이를 다음 3개 분모로 분리 측정한다:
     | 분류 코드 | 정의 | 오프라인 정상 기대 상태 | 목표 관리 지표 |
     | --- | --- | --- | --- |
     | `OFFLINE_VERIFIABLE` | 사건번호 형식 오류(`FMT.*`), 대역 밖 번호, 문서 내 자체 모순, 로컬 규칙표(`config/legal_rules/rules.json`) 수록 법리 | `POSITIVE` (`NOT_FOUND`, `CONTRADICTED`, `SUSPICIOUS`, `INVALID_FORMAT`) | **오프라인 결정론 재현율 80% 이상** |
     | `EXTERNAL_SOURCE_REQUIRED` | 실존 사건번호의 인용문 날조(`CIT-FAB-Q`), 판례 취지 왜곡(`CIT-MIS`), 미수록 법령·조문(`LAW-NX`) 등 외부 공식 원문 필수 항목 | 오프라인에서는 `UNVERIFIED` (무근거 허위 단정 금지), **카세트 리플레이/온라인에서 `POSITIVE`** | **온라인/리플레이 법률 재현율 75% 이상**, 오프라인 무근거 단정 **0건** |
     | `SOURCE_AVAILABLE_MISSED` | 로컬 규칙표나 스냅샷에 원문이 존재함에도 문장 변형·절 분리·인용 연결 실패로 놓친 항목 | `POSITIVE` (현재 미탐 → P1/P3로 해결할 핵심 타깃) | **미탐률 50% 이상 감축** |
3. **정밀도(Precision)와 검토 부담(Review Burden)의 실질 측정**:
   - `FP-TRAP`과 대조군 문서만의 오탐(0건)을 전체 정밀도로 간주하지 않는다.
   - 정답지 외 미판정 경고(**현행 102건**)를 전수 라벨링하여 **전체 경고 정밀도(Alert Precision)** 와 **문서당 평균 검토 경고 수 / 중복 경고율**을 함께 관리한다.

---

## 2. 102건 미판정 경고(Unadjudicated Alerts) 라벨링 프로토콜

### 2.1 추출 및 클러스터링 규격 (`packages/evaluation/adjudication.py`)
51개 벤치마크 문서(dev 36 + holdout 15)의 `unmatched_defect_findings` 102건에 대해 각 항목을 다음 필드로 추출한다:
- `alert_id`: 결정론적 해시 (`sha256(document_key | finding_type | page | span | normalized_title)[:16]`)
- `document_key`, `finding_type`, `status`, `severity`, `evidence_grade`, `engine`
- `page`, `block_id`, `span`, `excerpt`
- `cluster_id`: 동일 문서 내 `(finding_type, normalized_authority_or_entity)` 기준 중복 클러스터 ID (현행 동일 문서·유형 중복 후보 24건)

### 2.2 5분류 판정 기준 (`AdjudicationVerdict`)
법률가(또는 독립 평가 세션)가 각 경고를 다음 5가지 중 하나로 판정한다:

| 라벨 코드 | 의미 | 정밀도(Precision) 산식 반영 | 후속 엔지니어링 조치 |
| --- | --- | --- | --- |
| `TRUE_DEFECT_UNLISTED` | 문서에 실제로 존재하는 법률·사실·인용 결함을 정확히 짚었으나 기존 정답지에 등재되지 않은 항목 | **진양성 (TP)** 으로 산입 | 평가 에이전트가 정답지 v3 확장 후보로 검토 |
| `TRUE_DEFECT_TOKEN_MISMATCH` | 정답지에 있는 결함을 찾아냈으나 `match_spec.json`의 어휘 매칭 토큰과 표현이 달라 매칭에서 누락된 항목 | **진양성 (TP)** (매칭기 아티팩트) | 평가 에이전트가 `match_spec` 또는 스팬 기반 매칭으로 보정 |
| `DUPLICATE_FINDING` | 이미 적중한 결함과 동일한 원인을 중복 보고한 경고 (중복 후보는 개별 확인) | 고유 결함 정밀도와 **중복 포함 노출 정밀도**를 분리 계산 | P3 `LegalEvidenceGraph` 연결 컴포넌트 병합으로 제거 |
| `OVERREACH_FALSE_POSITIVE` | 부정문·가정문·상대방 주장 인용·적법한 법리 주장을 결함으로 잘못 판정한 실질 오탐 | **위양성 (FP)** 으로 산입 | P1 `KoreanLegalClauseNormalizer` 및 규칙 가드로 억제 |
| `ADVISORY_MISCLASSIFIED` | 참고 신호(`advisory_only=True`)로 안내해야 할 사안을 본문 확정 결함 경고로 노출한 항목 | 본문 확정 경고 기준 **위양성 (FP)** | `advisory_only=True` 및 근거 등급 하향 |

---

## 3. 계층별 핵심 성과 지표(KPI) 및 수용 기준

| 평가 계층 | 세부 지표 | 현행 기준선 (`v0.22.0` / `a7b13a3`) | 차세대 목표치 | 측정 방법 및 조건 |
| --- | --- | --- | --- | --- |
| **1. 회귀 및 전체 재현율** | 동일 조건 엄격 재현율 (`regression_v2.recall`) | **53.4%** (195 / 365) | **70.0% 이상** (도달 가능 항목 분석 병행) | `scripts/scorecard.py` (dev 36 + holdout 15) |
| **2. 법률 결함 검증** | 오프라인 결정론 법률 재현율 (`OFFLINE_VERIFIABLE`) | 전체 통합 35.0% (43 / 123) | **조건별 분리 측정 (결정론 80%+, 리플레이 75%+)** | 오프라인(`LV_ALLOW_NETWORK=0`) vs 카세트 리플레이(`LV_SOURCE_REPLAY_MODE=REPLAY`) 분리 채점 |
| **3. 경고 정밀도 및 피로도** | 라벨링 기반 전체 경고 정밀도 (`TP / (TP + FP)`) | `NOT_MEASURED` (미판정 102건) | **90.0% 이상** | `packages/evaluation/quality.py` + 102건 라벨링 데이터셋 |
| **3-보완. 중복 경고 억제** | 동일 문서·동일 유형 중복 경고 수 | **24건** / 51문서 | **5건 이하** (80% 이상 감축) | `duplicate_citation_verdicts` 및 그래프 병합 후 집계 |
| **4. 하이브리드 RAG 검색** | 법률 참고자료 검색 `Recall@10` / `MRR@10` | `NOT_MEASURED` | **Recall@10 ≥ 90.0%** | 정답 청크/조문 ID가 라벨링된 검색 벤치마크 세트 |
| **5. 근거 구간 및 NLI** | 공식 원문 근거 구간(`passage`) 연결 정확도 (Span IoU ≥ 0.5) | `NOT_MEASURED` (합성 계약 45/45) | **95.0% 이상** | 공식 판결문·조문 원문 구간 라벨 대조 |
| **5-보완. 무근거 단정 방지** | 원문 근거 구간 없는 `CONTRADICTED` / `FALSE_VERIFIED` 비율 | 합성 시험 0건 | **0.0% (0건 유지)** | `classify_claim()` 불변식 및 `false_verified_rate` |
| **6. 문서 지능 (OCR/표)** | Drive 참고자료 사전 색인 페이지 완독률 | `PARTIAL` 다수 발생 (5쪽 예산 제한) | **98.0% 이상** (`BUDGET_EXHAUSTED` 0건) | `reference_health.coverage_ledger` |
| **7. 보안 및 프라이버시** | 외부 전송 PII 유출 / 프롬프트 인젝션 방어 실패 / 심각한 회귀 | **0건** | **0건 절대 유지** | `score_gate.py` + `OutboundGuard` + 적대적 픽스처 시험 |

---

## 4. 평가·구현 독립성 거버넌스

1. **역할 분리 (`docs/AGENT_ROLES.md` 준수)**:
   - **구현 에이전트 (Antigravity, `Agent: implementer`)**: `packages/`, `apps/`, `workers/`, `config/`의 제품 코드와 `tests/unit/` 단위 시험만 수정한다. 채점 스크립트(`scripts/scorecard.py`, `scripts/evaluation_v2.py`)나 정답지(`tests/fixtures/**`)를 절대 수정하지 않는다.
   - **평가 에이전트 (`Agent: evaluator`)**: 보호 경로의 채점기·정답지·봉인 세트(`--sealed-dir`)를 관리하고, 구현 PR의 실제 일반화 성능을 독립 판정한다.
2. **봉인 시험(Sealed Set) 및 과적합 방지**:
   - 모든 신규 탐지·정규화 규칙은 벤치마크 문서의 문구를 따오지 않고 일반 문법·법리 구조로만 설계하며, `tests/acceptance/test_no_case_literals.py`와 `scripts/check_hardcoding_diff.py`로 자동 검증한다.
   - 개발 세트(`dev`) 점수가 상승하더라도 홀드아웃(`holdout`) 또는 저장소 외부 봉인 세트(`sealed`)에서 재현율이 하락하거나 오탐이 증가하면 해당 기능 플래그를 승격하지 않는다.
