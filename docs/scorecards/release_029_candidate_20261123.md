# 0.29.0 릴리스 후보 오프라인 판정 (2026-11-23)

**판정: 오프라인 수용 (minor 0.28.0 → 0.29.0).** 평가 대상은 `Steve_ACASiaLAW`의 `e880f425`이며, 기준은 운영 `main`의 `1ef3e4fe877f83fba4d7936e790c7843c80e4603`(0.28.0)이다. `#423`(방안 A/C: 2단계 구조화 Fact Triple 파이프라인)을 포함한다.

## 필수 게이트

| 게이트 | 확인 결과 |
|---|---|
| 점수·회귀 (CI `점수 하락 게이트`·`은퇴 세트 비교`) | PR #423(`08e73c79` = `e880f425` 동일 트리) CI 기준: 고정 `dev` **86.2**(v2 `44/56`, `78.6%`), `holdout` **86.6**(v2 `44/54`, `81.5%`), 확인 오탐·A등급 오탐 0, 인젝션 방어 유지(합산 RER 0%, 회귀 0). 은퇴 5세트(`56.5 / 54.6 / 56.9 / 53.8 / 44.3`, 평균 `53.22`) 전 세트 오탐 0·A등급 0·항목 회귀 0. |
| 필수 CI (#423) | `점수 하락 게이트`(평가 세트 문구 대조 포함)·`은퇴 세트 비교`·`CodeQL`(새 경고 0건)·`Docker OCR readiness`·`SQLite`·`PostgreSQL`·`Redis` 전수 통과. |
| 비공개·봉인 세트 | 격리 봉인 세트는 원격 평가 VM 미보유로 `NOT_MEASURED` (배포 후 온라인 점검 시행). |
| 열린 P1 회귀 | 0건. |

## 가치·버전·미측정

- **분류(`basis`):** `["added"]` → **0.29.0 (`minor`)**.
  - `added`: 2단계 구조화 Fact Triple 추출·검산 엔진(`packages/claim_engine/fact_triples.py`, `extract_fact_triples`·`verify_fact_triples`·`verify_project_fact_triples`) 및 `pipeline.py` 연동(`engine_data["fact_triples"]` 배출, 단일/문서 간 동일 단계 값 충돌 `FACT_TRIPLE.VALUE_CONFLICT`/`CROSS_DOC_CONFLICT`, 인과 단계 선후 역전 `FACT_TRIPLE.STAGE_INVERSION`, #423).
- **평가 측 후속(보호 경로 요청 `0290_fact_triple_and_cassette_track.md`):**
  - 방안 B(Source 카세트 `REPLAY` 오프라인 평가 트랙) 및 방안 D(`EVALUATION_V2` 4차원 실측·독립 법률가 라벨링)는 보호 경로 변경 사항으로 별도 평가 트랙에서 검토한다.
- **미측정(`NOT_MEASURED`):** 배포 후 운영 온라인 실측(`fact_triples` 실서면 추출/충돌 관측, `2015모2524` 원응답 3건 확인, `0.28.0` 4차원 출력·Drive 16쪽 재색인·상용 임베딩 실호출·`case9`) 및 격리 봉인 세트.

Agent: evaluator
