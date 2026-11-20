# 평가 측 요청: 릴리스 후 온라인 실측 + 카세트 리플레이 평가 정례화

- **작성자**: `Agent: implementer` (사용자 지시 반영)
- **요청 대상**: `Agent: evaluator` (Claude Code 평가 세션)
- **관련 문서**:
  - `docs/architecture/EVALUATION_GOVERNANCE_V3.md`
  - `docs/architecture/NEXT_GEN_EVALUATION.md`
  - `docs/roadmap/NEXT_GEN_IMPLEMENTATION_PLAN.md` (`PR-03`, `PR-07`, `PR-08`, `PR-11`, `PR-13`)

---

## 1. 요청 배경

차세대 고도화(`PR-01` ~ `PR-13`)에는 Drive RAG 사전 색인(`PR-02`), 카세트 스냅샷 리플레이(`PR-03`), 하이브리드 검색·적용성 필터(`PR-07`·`PR-08`), 적응형 OCR 폴백(`PR-11`) 등 **온라인·외부 원문·모델 연동 경로**에서만 효과가 측정되는 기능이 다수 포함되어 있습니다.
오프라인 `dev`/은퇴 세트만으로는 이러한 온라인 경로의 실제 개선 폭을 측정하기 어렵므로, 사용자 승인에 따라 **매 릴리스 단위 온라인 실측 및 결과 `main` 반영 절차**의 정례화를 요청합니다.

---

## 2. 제안 평가 파이프라인 (2단계)

1. **릴리스 전 게이트 (`Steve_ACASiaLAW → main` 릴리스 후보 SHA)**:
   - 기존 거버넌스 v3 원칙에 따라 오프라인 게이트 + 비공개/봉인 세트(및 고정 카세트 `REPLAY`)로 **점수 하락·회귀 0건**을 확인한 뒤 `main`에 병합·릴리스합니다.
2. **릴리스 직후 온라인 실측 및 기록 병합 (`main` 대상 평가 PR)**:
   - 배포된 릴리스 SHA 기준으로 실제 온라인 환경(Drive RAG + 공식 DB + 활성화된 Feature Flag)에서 평가를 실행합니다.
   - 실행 시 **`LV_SOURCE_REPLAY_MODE=RECORD`**로 비식별 스냅샷을 함께 확보하여 다음 릴리스와의 동일 조건(`REPLAY`) 비교 기준을 유지합니다.
   - 온라인 측정 성적표 및 추이 갱신(`docs/scorecards/HISTORY.md` 등 보호 경로)을 **평가 측 PR로 `main`(및 `Steve_ACASiaLAW`)에 추가 병합**합니다.

---

## 3. 시행 시점 제안

- 현재 진행 중인 `PR-12` (`#366`), `PR-11` (`#367`) 및 잔여 `PR-13` 병합과 주요 Feature Flag(`Canary → Default`) 전환이 완료되는 **차기 릴리스 후보 SHA**부터 본 절차를 첫 적용할 것을 권장합니다.
