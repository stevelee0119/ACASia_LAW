# AegisLAW 평가·구현 거버넌스 개편안 (Governance v3: 계약 기반 역할 분리)

- **작성일**: 2026-11-19
- **상태**: 사용자 권고 승인에 따른 개편 명세 (보호 경로 개정 반영 대기 — [`REQ_GOVERNANCE_V3_TRANSITION.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/handoff/requests/REQ_GOVERNANCE_V3_TRANSITION.md))
- **배경 분석 근거**:
  - [`docs/scorecards/process_review_2026-10-03.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/scorecards/process_review_2026-10-03.md)
  - [`docs/scorecards/process_review_2026-11-09_probe_rounds.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/scorecards/process_review_2026-11-09_probe_rounds.md)

---

## 1. 개편의 핵심 원칙: "분리는 유지하되, 코드 처방과 수동 핑퐁을 폐지한다"

1. **유지하는 불변식 (과적합·시험 약화 방지)**
   - 구현 에이전트(`Agent: implementer`)와 평가 에이전트(`Agent: evaluator`)의 독립성 유지
   - 보호 경로([`scripts/check_protected_paths.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/check_protected_paths.py)), 케이스 리터럴 차단([`scripts/check_case_literals.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/check_case_literals.py)), 비공개·봉인 시험 세트 분리 유지
2. **폐지·전환하는 관행 (비효율·역할 침범 제거)**
   - **평가 측의 코드·정규식 직접 처방 폐지**: 평가 에이전트가 고칠 줄 번호·정규식 값·패치 diff를 내려주고 구현 에이전트가 `diff 0`으로 적용하던 관행을 종료한다.
   - **거대 단일 전달문(`NEXT_FOR_ANTIGRAVITY.md`, 7,262줄 / 905KB) 폐지**: 신규 티켓은 `docs/handoff/tickets/TK-XXX.md` 개별 계약 티켓으로 분리하고, 기존 전달문은 `docs/handoff/archive/`로 동결한다.
   - **소규모 탐침 10차 보완 루프 폐지**: 개별 어미·어휘 몇 건씩을 쫓는 미세 루프 대신 **공용 아키텍처 마일스톤(P0~P3) + 정량 지표 계약** 단위로 수용한다.

---

## 2. 역할 경계 재정립 (What vs. How 분리)

| 역할 | 소유 영역 (**What / Why / Gate**) | 금지 영역 |
| --- | --- | --- |
| **평가 에이전트 (`Agent: evaluator`)** | 1. **문제 정의(What)** 및 **수용 기준(Acceptance Metric)** 명시<br>2. 비공개·봉인 시험 세트 실행 및 축 조합 커버리지 검증<br>3. **102건 미판정 경고 라벨링** 및 **오프라인 결함 3분류** 관리<br>4. 릴리스 후보 SHA 최종 판정 및 보호 경로 승인 | - 제품 코드 수정 및 구현 방법(`How`: 특정 정규식·함수명·알고리즘) 강제<br>- 매 푸시/증분마다 수동 재실행(CI로 갈음) |
| **구현 에이전트 (`Agent: implementer`)** | 1. **아키텍처·모듈·알고리즘 설계(How)** 및 구현<br>2. 공용 인프라(`ClauseNormalizer`, `Hybrid RAG`, `EvidenceGraph`) 우선 구축<br>3. 자체 일반화 단위 시험(양성 3건+ / 대조군 3건+) 및 PR 제출 | - 보호 경로(`docs/scorecards/**`, `scripts/scorecard.py`, `tests/fixtures/**` 등) 직접 수정<br>- 사건 고유 리터럴·평가 문구 하드코딩 |
| **CI 자동 게이트** | 1. 회귀 금지(`score_gate.py`)<br>2. 리터럴·하드코딩·시험 삭제·보호 경로 점검<br>3. SQLite + PostgreSQL/pgvector + Docker OCR + CodeQL | — |
| **사용자(변호사)** | 1. 마일스톤·릴리스 방향 및 우선순위 승인<br>2. 봉인 시험 실행 및 `main` 병합/배포 최종 승인 | - 에이전트 간 지시서·판정서 수동 복사/중계 역할 최소화 |

---

## 3. 마일스톤·티켓 운영 프로토콜

1. **계약 티켓 규격 ([`docs/handoff/tickets/_TEMPLATE.md`](file:///home/antigravity/stevelee0119/ACASia_LAW/docs/handoff/tickets/_TEMPLATE.md))**:
   - 모든 신규 티켓은 `문제 현상`, `결함 범주(축)`, `정량 수용 기준(Metric)`, `제약 조건(불변식)` 4가지만 기술한다.
   - 평가 측은 특정 정규식이나 코드 줄 수정을 지시하지 않는다.
2. **PR 크기 및 판정 주기**:
   - **일반 기능/아키텍처 PR**: CI 게이트 통과 + 단위/일반화 시험 확인만으로 1~2회 내 수용.
   - **탐지 규칙 변경 PR**: 1쪽 설계 메모(`docs/handoff/requests/`) 선검토 후 구현. 동일 접근 2회 실패 시 아키텍처 전환(정규식 추가 금지).
   - **비공개·봉인 평가**: 매 커밋이 아닌 **마일스톤(P0 → P1 → P2 → P3) 완료 또는 릴리스 후보 SHA**에서만 실행.
3. **문서 중복 기록 축소**:
   - 판정 원본은 PR 코멘트(3줄) + `docs/scorecards/HISTORY.md`(수치 1행)로 일원화하고, 동일 내용의 3~4중 복사를 중단한다.
