# 0.29.0 설계 메모: 구조화 Fact Triple 2단계 파이프라인(방안 A/C) 및 Source 카세트 평가 트랙(방안 B/D) 요청

## 1. 배경
- `0.28.0`(PR #420)에서 문장 단위 정규식 확장이 대조군(`작성일≠발송일≠도착일`, `입금확인증 전액 지급`)과 기존 양성 시험 간 충돌을 반복 유발함을 확인하였다.
- 오프라인(`LV_ALLOW_NETWORK=0`) 환경에서는 `LAW-MIS`·`CIT-FAB-Q`·`CIT-MIS`가 원문 부재로 `PARTIAL`/`MISS`에 머문다.

## 2. 구현 설계 (제품 코드)
### 2-1. 방안 A: `packages/claim_engine/fact_triples.py` (2단계 구조화 Fact Triple 파이프라인)
1. **1단계 — 구조화 추출 (`extract_fact_triples`):**
   - 문서의 각 문장/절에서 `(subject, action_stage, target_object, date_iso, amount_krw, exhibit_ref, attribution, modality, page, excerpt)` 트리플을 추출한다.
   - `action_stage`를 `DRAFT(작성)` · `SEND(발송·발신·통지)` · `RECEIVE(도달·수신·접수·수령)` · `CONTRACT(체결·계약·약정)` · `PAY(지급·입금·변제·송금)` · `DELIVER(인도·납품)` · `TERMINATE(해지·해제·해고)`로 엄격히 분리한다.
   - `attribution` (`SELF` / `OPPONENT` / `QUOTED`) 및 `modality` (`ASSERTED` / `PLANNED` / `HYPOTHETICAL` / `NEGATED`)를 태깅하여, 오직 `SELF + ASSERTED` 트리플만 충돌/역전 검산에 사용한다.
2. **2단계 — 결정론 검산 (`verify_fact_triples`, `verify_project_fact_triples`):**
   - **동일 `(subject, action_stage, target_object)` 값 충돌 (`FACT_TRIPLE.VALUE_CONFLICT`):** 같은 단계·같은 대상에 대해 서로 다른 `date_iso` 또는 `amount_krw`가 진술되면 `FACT_CONTRADICTION` (Grade C, `SUSPICIOUS`)을 생성한다. `작성` vs `발송` vs `도착`은 `action_stage`가 다르므로 구조적으로 충돌하지 않는다.
   - **인과 단계 선후 역전 (`FACT_TRIPLE.STAGE_INVERSION`):** 동일 대상에 대해 `RECEIVE < SEND`, `TERMINATE < CONTRACT`인 경우 `EVIDENCE_TIMELINE_INVERSION` (Grade B, `SUSPICIOUS`)을 생성한다.
   - **문서 간 교차 충돌 (`FACT_TRIPLE.CROSS_DOC_CONFLICT`):** 프로젝트 내 동일 사건 문서들에서 동일 `(action_stage, target_object)`의 `date_iso` 또는 `amount_krw`가 다르면 `FACT_CONTRADICTION` (Grade C, `SUSPICIOUS`)을 생성한다.
3. **방안 C 연동 (`pipeline.py`):**
   - 추출된 `fact_triples` 요약을 `result.engine_data["fact_triples"]`에 기록하여 Stage 2 LLM 의미 검증(`OVR`·`CIT-MIS`·문맥 모순) 및 감사 추적에 활용한다.

## 3. 평가 측 요청 사항 (보호 경로 — 방안 B · 방안 D)
- **방안 B (Source 카세트 `REPLAY` 오프라인 평가 트랙):** `packages/source_adapters/cassette.py`의 `LV_SOURCE_REPLAY_MODE=REPLAY` + `LV_SOURCE_CASSETTE_DIR`가 이미 구현되어 있으므로, 평가 세션에서 `tests/fixtures/`용 PII-free 공식 판례·법령 카세트를 녹화하고 `scripts/eval_testset.py` / `scripts/scorecard.py`에 카세트 재생 트랙 추가를 검토 요청한다.
- **방안 D (`EVALUATION_V2` 실측):** PR #419에서 추가된 `result.engine_data["evaluation_dimensions"]` 4차원 출력을 기반으로 `scripts/export_quality_predictions.py` 확장 및 독립 법률가 라벨링 50~100건 실측 착수를 요청한다.
