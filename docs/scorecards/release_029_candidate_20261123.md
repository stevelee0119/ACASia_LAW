# 0.29.0 릴리스 후보 오프라인 판정 (2026-11-23)

**판정: 오프라인 수용 (minor 0.28.0 → 0.29.0).** 평가 대상은 `Steve_ACASiaLAW`의 `154a1297`이며, 기준은 운영 `main`의 `1ef3e4fe`(0.28.0)이다. `#423`(FactTriple 구조화 추출·결정론적 검증기), `#426`(2단 운영 구조·정보 격리·동적 변형 시험 하네스), `#425`(일반화 FactTriple·다중 AI잔재 승격·문서간 복제 EVI-COPY 탐지 보완)를 포함한다.

## 필수 게이트

| 게이트 | 확인 결과 |
|---|---|
| 점수·회귀 (CI `점수 하락 게이트`·`은퇴 세트 비교`) | PR #425(`2583f851` = `154a1297` 동일 제품 트리, `45263747281`) CI 기준: 고정 `dev` **86.2 → 89.7**(+3.5, v2 `44/56 → 47/56`, `83.93%`), `holdout` **86.6 → 87.5**(+0.9, v2 `44/54 → 45/54`, `83.33%`), 합산 RER **16.18%**, 확인 오탐·A등급 오탐 0, 인젝션 방어 유지(회귀 0). **은퇴 5세트 평균 53.22 → 58.00(+4.78%p)**: `sealed_20261008` 56.5 · `sealed_20261008b` 54.6 · `sealed_20261009` **56.9 → 63.8**(+6.9) · `sealed_20261010` **53.8 → 59.4**(+5.6) · `sealed_20261025` **44.3 → 55.7**(+11.4) — 전 세트 오탐 0·A등급 0·항목 회귀 0. |
| 필수 CI (#423·#425·#426) | 모든 포함 PR에서 `점수 하락 게이트`(평가 세트 문구 대조 포함)·`은퇴 세트 비교`·`CodeQL`(새 경고 0건)·`Docker OCR readiness`·`SQLite`·`PostgreSQL`·`Redis` 전수 통과. |
| 비공개·봉인 세트 | 격리 봉인 세트는 원격 평가 VM 미보유로 `NOT_MEASURED` (배포 후 온라인 점검 시행). |
| 열린 P1 회귀 | 0건. |

## 가치·버전·미측정

- **분류(`basis`):** `["added", "fixed", "changed"]` → **0.29.0 (`minor`)**.
  - `added`: 2단계 구조화 `FactTriple` 추출·결정론적 검증기(`packages/claim_engine/fact_triples.py`, `pipeline.py`, #423·#425), 2단 운영 구조·정보 격리·동적 변형 시험 하네스(`docs/scorecards/EVALUATION_GOVERNANCE_TWO_TIER.md`, `scripts/eval_perturbation.py`, `scripts/eval_cassette_track.py`, #426), 다중 AI 문체 잔재 클러스터 승격 및 문서간 복제(`EVI-COPY`)·증거 불일치 일반화 규칙(#425).
  - `fixed`: `FactTriple`·`EVI-COPY`·`EVI-OVR`·`ClauseNormalizer`·`exporters`·`scanner` 경계 오탐 및 직렬화 가드 보완(#425).
  - `changed`: 2단 운영 원칙에 따른 오프라인 게이트·온라인 실측 분리 운영(#426).
- **미측정(`NOT_MEASURED`):** 배포 후 운영 온라인 실측(U2 `live-source-check` `with_llm=true`, `0.27.0`~`0.29.0` Drive 저품질 16쪽 재색인·상용 임베딩 실호출·`case9` 3회 연속·4차원 출력 검증) 및 격리 봉인 세트.

Agent: evaluator
