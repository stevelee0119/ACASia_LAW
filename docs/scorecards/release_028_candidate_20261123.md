# 0.28.0 릴리스 후보 오프라인 판정 (2026-11-23)

**판정: 오프라인 수용 (minor 0.27.0 → 0.28.0).** 평가 대상은 `Steve_ACASiaLAW`의 `d5241370`이며, 기준은 운영 `main`의 `12be4fa58650bf59aacf30d9f21b87c1249582d5`(0.27.0)이다. `#418`(과제 2), `#419`(과제 4), `#417`(과제 3), `#420`(과제 1)의 4개 구현 PR을 모두 포함한다.

## 필수 게이트

| 게이트 | 확인 결과 |
|---|---|
| 점수·회귀 (CI `점수 하락 게이트`·`은퇴 세트 비교`) | PR #420(`12f492d5` = `d5241370` 동일 트리) CI 기준: 고정 `dev` **86.2**(v2 `44/56`, `78.6%`), `holdout` **86.6**(v2 `44/54`, `81.5%`), 확인 오탐·A등급 오탐 0, 인젝션 방어 유지(합산 RER 0%, 회귀 0). **은퇴 5세트 평균 51.48 → 53.22(+1.74)**: `sealed_20261008` 56.5(v2 `24/46`, 미판정 `6→5`) · `sealed_20261008b` 54.6(v2 `28/54`, 미판정 `20→19`) · `sealed_20261009` 56.9(v2 `31/58→32/58`, 미판정 `30→27`) · `sealed_20261010` **51.9→53.8**(+1.9, v2 `27/53→28/53`, 미판정 `13→12`) · `sealed_20261025` **37.5→44.3**(+6.8, v2 `14/44→17/44`) — 전 세트 오탐 0·A등급 0·항목 회귀 0. |
| 필수 CI (#417~#420) | 4개 구현 PR 모두 `점수 하락 게이트`(평가 세트 문구 대조 포함)·`은퇴 세트 비교`·`CodeQL`(새 경고 0건)·`Docker OCR readiness`·`SQLite`·`PostgreSQL`·`Redis` 전수 통과. |
| 비공개·봉인 세트 | 격리 봉인 세트는 원격 평가 VM 미보유로 `NOT_MEASURED` (배포 후 온라인 점검 시행). |
| 열린 P1 회귀 | 0건. |

## 가치·버전·미측정

- **분류(`basis`):** `["added", "fixed", "changed"]` → **0.28.0 (`minor`)**.
  - `added`: `EVALUATION_V2` 4차원(`identity`, `quote`, `claim_applicability`, `source_retrieval`) PII-free 구조화 출력 계약(`eval_contract.py`, `pipeline.py`, 과제 4 #419), 은퇴 세트 구조적 일반화 규칙(초안/AI 메모 `DRAFT_ARTIFACT`·내심 단정 `EVI-LOGIC`·서증명-호증번호 불일치 `EVI-NUM`·다중 줄 합계 내역·앵커 스칼라 불일치 `EVI-INCONS`·법리 과장 단언 `OVR`·메타데이터 지시어/ZWSP, 과제 1 #420).
  - `fixed`: `law_go_kr` NFKC/제로폭 정규화·사건명 fallback 매칭(완전 튜플 일치만 허용) 및 학술 Source(`SemanticScholarAdapter`) 키 미설정 시 429 백오프 단축(과제 3 #417), 선고일 기준일 오분류 배제(`temporal_review`, #420).
  - `changed`: 미운영 `HttpEmbeddingAdapter`/`LV_RAG_EMBEDDING_ENDPOINT` 분기 제거 및 `next_gen_feature_diagnostics()` `configured_mode`/`effective_mode`/`actual_calls` 3중 일치 계약 강제(과제 2 #418).
- **미측정(`NOT_MEASURED`):** 배포 후 운영 온라인 실측(U2 `live-source-check` `2015모2524` `ok: true` 해소 확인, `0.27.0`~`0.28.0` Drive 저품질 16쪽 재색인·상용 임베딩 실호출·`case9` 3회 연속·4차원 출력 검증) 및 격리 봉인 세트.

Agent: evaluator
