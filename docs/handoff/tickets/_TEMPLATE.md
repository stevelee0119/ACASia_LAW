# [TK-XXX] <티켓 제목: 근본 원인 또는 마일스톤 단위>

- **상태**: `OPEN` | `IN_PROGRESS` | `IN_REVIEW` | `DONE`
- **마일스톤**: `P0` | `P1` | `P2` | `P3`
- **작성자**: `Agent: evaluator` (또는 사용자)
- **담당자**: `Agent: implementer`

---

## 1. 문제 현상 및 결함 범주 (What — 구현 방법 미지정)
- **현상 요약**: (어떤 실무/평가 결함이 관찰되는지 3줄 이내로 기술)
- **대상 결함 범주 / 축**: (예: `CIT-MIS`, `OVERREACH_FALSE_POSITIVE` 등 — 비공개 탐침 문장 복사 금지)

## 2. 정량 수용 기준 (Acceptance Criteria — 측정 도구 출력 기준)
- [ ] (예: `packages/evaluation/adjudication.py` 기준 중복 경고 24건 → 5건 이하)
- [ ] (예: `scripts/score_gate.py` 회귀 0건, 대조군/FP-TRAP 오탐 0건)
- [ ] (예: 신규 규칙당 독립 합성 양성 3건+ 및 대조군 3건+ 단위 시험 통과)

## 3. 제약 및 불변식 (Constraints)
- 보호 경로(`docs/scorecards/**`, `scripts/scorecard.py`, `tests/fixtures/**` 등) 수정 금지
- 사건 고유 값·서면 문구 하드코딩 금지 (`scripts/check_case_literals.py` 통과)
- `Fail-Closed` 원칙 유지: 공식 원문/근거 구간 없이 `VERIFIED` 또는 `CONTRADICTED` 단정 금지

---

## 4. 구현 설계 요약 (구현 에이전트 작성)
- **선택한 아키텍처/모듈(How)**:
- **PR 번호 / 대상 SHA**:
- **CI 및 자체 시험 결과**:
