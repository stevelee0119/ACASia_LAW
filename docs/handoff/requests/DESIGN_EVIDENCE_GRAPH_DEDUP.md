# 설계 메모: Legal Evidence Graph 기반 결함 분석 및 중복 경고 병합 (PR-13)

- **작성자**: `Agent: implementer`
- **관련 계획**: `docs/roadmap/NEXT_GEN_IMPLEMENTATION_PLAN.md` (P3 `PR-13`), `docs/architecture/NEXT_GEN_ARCHITECTURE.md` 2.8절
- **Feature Flag**: `LV_EVIDENCE_GRAPH_MODE=off | shadow | canary | default` (기본값 `shadow`)

---

## 1. 목적 및 4대 그래프 분석 규칙

`PR-12`에서 구축한 `LegalEvidenceGraph`(`LEGAL_CLAIM`, `REQUIREMENT_ELEMENT`, `FACT_ASSERTION`, `AUTHORITY_SOURCE`, `EXHIBIT_EVIDENCE`, `SOURCE_SPAN`)를 순회하여 다음 4가지 구조적 신호를 산출합니다.

1. **`BROKEN_AUTHORITY_CHAIN` (근거 결여 연쇄)**:
   - `LEGAL_CLAIM` 또는 `FACT_ASSERTION`이 `GROUNDED_IN_AUTHORITY`로 의존하는 `AUTHORITY_SOURCE`에 `UNDERMINES` / `CONTRADICTED` / `NOT_FOUND` / `OVERRULED` 상태가 존재하는 경우 탐지.
2. **`MISSING_PREREQUISITE_ELEMENT` (요건사실 누락)**:
   - `LEGAL_CLAIM`이 `REQUIRES_ELEMENT`로 요구하는 `REQUIREMENT_ELEMENT` 중 `ASSERTS_SATISFACTION` 인입 엣지가 0건인(`PENDING`) 요건 탐지.
3. **`UNSUPPORTED_FACT_ELEMENT` (사실-서증 단절/모순)**:
   - `FACT_ASSERTION`이 `PROVED_BY_EXHIBIT`로 연결한 `EXHIBIT_EVIDENCE`가 `UNATTACHED` / `MISSING` / `CONTRADICTED` 상태인 경우 탐지.
4. **`Alert Deduplication` (동일 원인 연결 컴포넌트 병합)**:
   - `SOURCE_SPAN` 허브를 제외한 무방향 연결 컴포넌트(`graph.connected_components()`) 내에서 **동일 `FindingType`이면서 `advisory_only=False`인 복수 `Finding`**을 `verdict_rank` 최상위 대표 1건으로 병합하고, 나머지 ID·요약은 `confidence_features["merged_findings"]` 및 `evidence`에 보존해 적중(`hits`) 손실 0건을 보장합니다.

---

## 2. 파이프라인 및 `ReviewItem` 통합 방식

- **`shadow` 모드 (기본값)**:
  - `pipeline.py`에서 그래프 빌드 및 `analyze_evidence_graph()` 결과를 `result.engine_data["evidence_graph"]`·`result.engine_data["evidence_graph_analysis"]`에 기록만 수행하고 `Finding`·`ReviewItem` 판정은 변경하지 않습니다.
- **`canary` / `default` 모드**:
  - `finalize_document_findings(..., evidence_graph=graph)`에서 연결 컴포넌트 단위 중복 병합을 수행합니다.
  - `review_items.py`의 `build_document_review_items()`에서 관련 `ReviewItem.reasoning_sections["prerequisite_checklist"]`에 누락 요건·단절 근거 점검표를 구조화해 첨부합니다.
