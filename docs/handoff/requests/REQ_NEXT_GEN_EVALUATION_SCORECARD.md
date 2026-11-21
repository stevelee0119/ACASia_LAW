# [요청 티켓] 차세대 평가체계 명세서(`docs/scorecards/NEXT_GEN_EVALUATION.md`) 등재 및 P0 평가 확장 요청

- **요청일**: 2026-11-19
- **요청자**: Antigravity (`Agent: implementer`)
- **수신자**: 평가 에이전트 (`Agent: evaluator`)
- **관련 문서**:
  - [`docs/architecture/NEXT_GEN_EVALUATION.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/architecture/NEXT_GEN_EVALUATION.md)
  - [`docs/architecture/NEXT_GEN_BASELINE.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/architecture/NEXT_GEN_BASELINE.md)
  - [`docs/architecture/NEXT_GEN_ARCHITECTURE.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/architecture/NEXT_GEN_ARCHITECTURE.md)
  - [`docs/roadmap/NEXT_GEN_IMPLEMENTATION_PLAN.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/roadmap/NEXT_GEN_IMPLEMENTATION_PLAN.md)

## 1. 요청 배경 (`AGENTS.md` 보호 경로 준수)

사용자 지시서(2026-11-19 「AegisLAW 성능 고도화 전략 및 Antigravity 구현 지시서」 13절)에서 산출물 중 하나로 `docs/scorecards/NEXT_GEN_EVALUATION.md` 작성이 요청되었습니다.

그러나 [`AGENTS.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/AGENTS.md) 및 [`scripts/check_protected_paths.py:31`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/check_protected_paths.py#L31)에 따라 `docs/scorecards/**`는 **평가 에이전트 전용 보호 경로**이며, 구현 에이전트(`Agent: implementer`) 커밋이 해당 경로를 직접 생성·수정하면 CI의 `보호 경로 변경 점검`이 실패합니다.

이에 따라 구현 에이전트는 동일한 전체 명세서를 비보호 경로인 [`docs/architecture/NEXT_GEN_EVALUATION.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/architecture/NEXT_GEN_EVALUATION.md)에 작성하고, 평가 측의 검토·등재를 위해 본 요청 티켓을 남깁니다.

## 2. 평가 에이전트 협조 요청 사항

1. **명세서 등재**: [`docs/architecture/NEXT_GEN_EVALUATION.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/architecture/NEXT_GEN_EVALUATION.md)를 검토하신 후 `Agent: evaluator` 커밋으로 `docs/scorecards/NEXT_GEN_EVALUATION.md`에 반영(또는 심볼릭/복사 등재)해 주시기 바랍니다.
2. **오프라인 법률 결함 123개 항목의 도달 가능성 3분류 태그 부여**:
   - `OFFLINE_VERIFIABLE` (오프라인 결정론 검증 가능)
   - `EXTERNAL_SOURCE_REQUIRED` (공식 법령·판례 원문 조회 필수 — 오프라인에서는 `UNVERIFIED`가 정상)
   - `SOURCE_AVAILABLE_MISSED` (로컬 규칙·스냅샷 존재하나 미탐)
3. **51문서 미판정 경고 102건(`unadjudicated_alerts`)에 대한 판정 라벨링**:
   - PR-04에서 `packages/evaluation/adjudication.py`가 제공하는 추출 포맷을 활용해 102건의 미판정 경고를 5분류(`TRUE_DEFECT_UNLISTED`, `TRUE_DEFECT_TOKEN_MISMATCH`, `DUPLICATE_FINDING`, `OVERREACH_FALSE_POSITIVE`, `ADVISORY_MISCLASSIFIED`)로 판정해 주시면, 구현 에이전트가 `OVERREACH_FALSE_POSITIVE`와 `DUPLICATE_FINDING`을 P1(`ClauseNormalizer`) 및 P3(`LegalEvidenceGraph`)에서 정밀 타격하여 제거하겠습니다.
