# Codex 인계 — 0.31.1 운영 재측정과 후속 업무 (2026-11-28)

- 사용자 원문: "운영 재측정 및 그 후 후속 업무까지 codex가 진행할께 클로드코드 토큰 소진이 임박해서 말이야."(2026-11-28)
- 인계자: 평가 에이전트(Claude Code). 평가 브랜치 `ccr-1433dc64-pcexuu`.
- 운영: 0.31.1(`5626ecb7`) 배포 확인. 사용자가 `LV_LLM_PROMPT_CACHING=1` 설정 완료.

## 1. 지금 할 일 (순서대로)
1. **운영 재측정:** [online_0311_measurement_order_20261128.md](../scorecards/online_0311_measurement_order_20261128.md)의 지시 전문을 그대로 따른다.
2. **판정 기록:** 결과를 `docs/scorecards/online_0311_<YYYYMMDD>.md`에 적는다. 형식은 [online_0310_2nd_20261128.md](../scorecards/online_0310_2nd_20261128.md)와 같게 하고, 다음을 지킨다.
   - 측정 조건과 근거 구분('평가 측 재실행' 대신 'Codex 대행 재실행')을 적는다.
   - 다른 조건의 점수와 증감을 비교하지 않는다.
   - 측정하지 못한 것은 못 했다고 적는다.
   - 판정 기준은 아래 '수용 기준'이다.
     - 3회 모두 표준 23/23·RAG 5/5·건강 6/6
     - 모델 호출 실패 0(공급자 장애는 원인과 함께 따로 적음)
     - `argument_review_v1`에 `gpt-6.2-sol` ok
     - Gemini `gemini-4-neon` ok
     - Sonnet RAG 호출 `cache_read_tokens>0`
     - RAG 비용이 0.31.0 2차($1.02~1.05)보다 낮음
     - `halt_reason` null, `unreviewed_drive_sources` 0
3. **기록 갱신:**
   - `DAILY_TREND.md`에 한 줄을 추가한다(머리의 작성 규칙을 따름).
   - `ticket_registry.json`의 TK-253·254·255 상태를 `deployed`(수용 시)로 바꾸고 `deployed_on`을 적는다.
   - `FEATURE_ONLINE_EVALUATION.md`에 온라인 결과를 연결한다.
4. **Haiku 5.5 확인 실측(구현 전):** 운영 재측정이 수용 기준을 채운 뒤에만 한다. [haiku_rag_measurement_plan_20261128.md](../scorecards/haiku_rag_measurement_plan_20261128.md)를 따른다.
   - Render 환경변수 `LV_ANTHROPIC_REVIEW_MODEL=claude-haiku-5-5`는 **사용자가** 설정하고 되돌린다. Codex는 바꾸지 않는다.
   - 측정 시간대는 사용자와 정한다.
   - 기준 Sonnet ×3은 1번 결과를 쓴다(같은 판·같은 캐시 설정).
   - 판정 기준(제안):
     - 강한 관계(`SUPPORTS`·`CONTRADICTS`) (source_id, relationship) 짝 일치 8/10 이상(Sonnet끼리 9/10)
     - 새 `CONTRADICTS` 오표시 0
     - RAG 5/5
   - 결과는 '확인된 개선' 여부와 비용 대비 효용 표로 사용자에게 권고한다(AGENT_ROLES 2.1).

## 2. 인계하지 못하는 것 (사용자 결정 또는 Claude Code 복귀 필요)
- **인용 대조군 N1~N5·다문서 회귀 → 인계로 변경(2026-11-28 사용자 지시 "인용 대조군 N1~N5·다문서 측정은 codex가 수행하도록 지시문 생성"):** 입력 8개는 사용자가 저장소 밖으로 Codex에 직접 전달한다(`codex_private_inputs_0311.zip`). 저장소 커밋, 보고서 인용, 문장 요약은 하지 않는다. 판정 기준은 0.30.1·0.31.0 2차 지적 구성과 같은지다. 지시 전문은 사용자에게 준 코드 블록이다.
  - 0.31.1 변경은 모델·캐시·RAG 상한이라 이 대조군의 지적 규칙과는 경로가 다르다. 다만 모델이 바뀌어 참고자료 관찰 건수는 달라질 수 있다.
- **TK-251(365항목 엄격 채점):** 방식 결정 대기(가: 빈 열 생략 그래프 / 나: 엄격 채점기 구축 / 다: 하지 않음). 채점기는 저장소에 없다.
- **E-1~E-3(평가 하네스):** 변형 시험 PDF 글자층·홀드아웃 경로, 인용 미탐 단계별 계측, 운영 건강 지표 분리. 계획은 [RELEASE_PLAN_0303_0310.md](RELEASE_PLAN_0303_0310.md) 2절.
- **브랜치 정리:** 세션 권한으로는 삭제할 수 없어(HTTP 403) 사용자가 GitHub Branches 화면에서 지운다.
  - 대상: `evaluator/021-postdeploy-check`, `evaluator/022-live-integration`, `online/024-integration-20261121`, `online/025-integration-20261121`, `claude/u2-diag-2015mo2524`, `stevelee0119-patch-1`, `chore/release-0.31.1`

## 3. 지켜야 할 규칙 (CLAUDE.md 요약)
- 제품 코드(`packages/`, `apps/`, `workers/`, `config/`, `migrations/`, `docker/`)는 바꾸지 않는다. 결함은 `docs/handoff/tickets/`에 티켓으로 쓴다.
- 결함 티켓에는 다음을 적는다.
  - 원인별 번호, 코드 위치(SHA 기준), 재현, 고칠 방법, 시험, 수용 기준
  - 저장소 밖 사본에서 미리 적용해 본 사전 검증 결과
- 기준선(`docs/scorecards/baseline.json`)은 사용자 승인 없이 낮추지 않는다.
- 운영 프로젝트는 휴지통까지만 옮긴다(purge 금지). 비밀값은 존재·길이만 적는다.
- 병합·배포·Render 설정은 사용자 권한이다. 다른 에이전트에 줄 지시는 코드 블록 하나로 쓴다.

Agent: evaluator
