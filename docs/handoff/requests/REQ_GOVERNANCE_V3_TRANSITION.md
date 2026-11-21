# [요청 티켓] 평가·구현 거버넌스 v3 전환 (`docs/AGENT_ROLES.md` · `AGENTS.md` 개정 요청)

- **요청일**: 2026-11-19
- **요청자**: Antigravity (`Agent: implementer`) — **2026-11-19 사용자 지시("평가 체계를 권고대로 변경해줘") 반영**
- **수신자**: 평가 에이전트 (`Agent: evaluator`) 및 사용자
- **관련 문서**:
  - [`docs/architecture/EVALUATION_GOVERNANCE_V3.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/architecture/EVALUATION_GOVERNANCE_V3.md)
  - [`docs/handoff/tickets/_TEMPLATE.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/handoff/tickets/_TEMPLATE.md)

---

## 1. 요청 사유 (`AGENTS.md` 보호 경로 준수)

2026-11-19 사용자께서 평가·구현 에이전트 운영 체계의 권고안대로 변경할 것을 승인하셨습니다.
단, [`docs/AGENT_ROLES.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/AGENT_ROLES.md)와 [`AGENTS.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/AGENTS.md)는 [`scripts/check_protected_paths.py:33`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/check_protected_paths.py#L33)의 보호 경로이므로, 구현 에이전트가 직접 수정하지 않고 평가 에이전트(`Agent: evaluator`)가 검토·적용할 수 있도록 개정안을 제출합니다.

---

## 2. `docs/AGENT_ROLES.md` 및 `AGENTS.md` 개정 요청 항목

1. **계약 기반 역할 분리 (What vs. How 분리)**
   - 평가 에이전트는 지시서에 **문제 현상(What)·결함 범주·정량 수용 기준(Metric)·불변식**만 명시하며, **코드 줄 번호·정규식 목록·구현 패치(`How`)** 를 직접 지시하지 않는다.
   - 구현 에이전트는 공용 아키텍처(P0~P3)와 일반화 시험을 책임지고 설계·구현한다.
2. **거대 단일 전달문(`NEXT_FOR_ANTIGRAVITY.md`, 7,262줄) 아카이브 및 티켓 분리**
   - 현행 [`docs/handoff/NEXT_FOR_ANTIGRAVITY.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/handoff/NEXT_FOR_ANTIGRAVITY.md)를 `docs/handoff/archive/`로 동결 보존한다.
   - 신규 지시는 [`docs/handoff/tickets/_TEMPLATE.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/handoff/tickets/_TEMPLATE.md) 형식의 개별 티켓(`docs/handoff/tickets/TK-*.md`)으로만 발행하여 에이전트 컨텍스트 비대화와 사용자 수동 중계를 줄인다.
3. **마일스톤·CI 중심 게이트 일원화**
   - 일반 PR은 CI 게이트(`score_gate.py`, `check_case_literals.py`, `check_protected_paths.py`, SQLite/Postgres/Docker OCR/CodeQL)로 1차 판정한다.
   - 평가 에이전트(및 감사)의 비공개·봉인 세트 수동 실행은 **마일스톤(P0~P3) 완료 시점 또는 릴리스 후보 SHA**로 집중하고, 상시 업무를 **102건 미판정 경고 라벨링·3분류 도달 가능성 관리**로 전환한다.
4. **중복 기록 축소**
   - PR 코멘트 3줄 보고 + `HISTORY.md` 1행 기록을 원본으로 두고, 동일 판정의 다중 파일 중복 기재를 폐지한다.
