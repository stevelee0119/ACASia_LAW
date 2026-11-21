# 차기 릴리스(0.25.0 목표) 구현 에이전트 지시 및 목표 총괄

- **기준 배포:** `v.0.24.0` (`684f3469028dc38e539345501191cc7c9832b13a`)
- **근거 문서:**
  - [0.24.0 온라인 평가 판정서](../../scorecards/online_0240_20261121.md) (5절·6절)
  - [0.24.0 온라인 재점검 결과](../online/0240_20261121/recheck_result.json) · [재점검 절차](../online/0240_20261121/recheck_procedure.md)
  - [차세대 평가 명세](../../scorecards/NEXT_GEN_EVALUATION.md) (2.3절 티켓 선별 기준)
  - [거버넌스 및 역할 분리](../../AGENT_ROLES.md)

## 1. 핵심 목표 (2대 트랙)

1. **객관적 오프라인 지표(`dev 82.6` · `holdout 81.9` · 은퇴 5세트 `53.3/48.6/56.9/45.8/34.1`) 상승:**
   - 0.21.0~0.24.0 정체(`RER 0`)를 깨기 위해 오프라인 도달 가능 미탐 축(`EVI-LOGIC`, `EVI-OVR`, `EVI-COPY`, `CIT-META`, `LAW-MIS`, `OVR/LAW-NX`, `AIGEN`)을 직접 개선하고, `REPLAY` 카세트 트랙으로 `EXTERNAL_SOURCE_REQUIRED`를 분리 측정한다.
2. **온라인 미해소(`RAGC-S3`) 해소 및 차세대 미측정 경로(`NOT_MEASURED`)의 시험 가능성 확보:**
   - `RAGC-S3` 청크 전달 후 지지 의견 미생성 해소, 저품질 OCR 16쪽 폴백/재색인 관측성, 진단 API의 유효 모드 노출(`Legal NLI`, `Hybrid RAG`, `Source 카세트`, `로컬 LLM`), 공식 Source 정확 조회 개선.

## 2. 발행된 계약 티켓 목록 (우선순위 순)

| 티켓 | 마일스톤 | 핵심 목표 | 선행 조건 / 주의사항 |
|---|---|---|---|
| [TK-221](TK-221.md) | `P1` | **오프라인 객관 지표(`dev`·`holdout`·은퇴 세트) 향상** (`EVI-LOGIC`/`OVR`/`COPY`, `CIT-META`, `LAW-MIS`, `AIGEN`) | 탐지 휴리스틱 변경 시 `docs/handoff/requests/` 설계 메모 선행, 확인/A등급 오탐 0 유지 |
| [TK-223](TK-223.md) | `P1` | **차세대 실행 경로 진단 가시성 및 `NLI`·`Hybrid RAG`·카세트·로컬 모델 시험 가능성 확보** | 비밀값·PII 노출 금지, 오프라인 vs 리플레이 점수 합산 금지 |
| [TK-220](TK-220.md) | `P2` | **RAG 지지 의견 미생성(`RAGC-S3`) 해소** (`TK-209` 후속) | `RAGC-N1`/`N2` 무관 대조군 오선택 0 유지 |
| [TK-222](TK-222.md) | `P2` | **저품질 스캔 OCR 폴백·재색인 실측 경로 및 채택 관측성** | 정상 스캔(`0.89`) 불필요 폴백 미채택 |
| [TK-224](TK-224.md) | `P2` | **공식 Source(`law_go_kr`) 정확 조회 일치 개선 및 학술 Source 원인 분리** | 다른 사건 오채택 0 (`Fail-Closed`) |

## 3. 구현 에이전트 작업 규칙
- 1티켓 = 1PR 단위로 `Steve_ACASiaLAW` 대상 PR을 생성한다.
- 각 티켓의 4절(구현 설계 요약)을 채우고, PR 코멘트 3줄(`바꾼 것`·`남은 것`·`검토 요청`)과 커밋 끝 `Agent: implementer`를 적는다.
- 보호 경로(`docs/scorecards/**`, `tests/acceptance/**`, `tests/fixtures/**` 등) 수정 금지, 사건 고유 값·서면 문구 하드코딩 금지(`scripts/check_case_literals.py`).
- 신규 규칙은 서로 다른 일반화 양성 3건 이상·대조군 3건 이상의 단위 시험을 포함한다.
