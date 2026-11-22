# 0.26.0 릴리스 후보 오프라인 판정 (2026-11-22)

**판정: 오프라인 수용 (minor 0.25.0 → 0.26.0).** 평가 대상은 `Steve_ACASiaLAW`의 `40396ff6`이며, 기준은 운영 `main`의 `023fc33ced8c8080629c743a2e9fcb0e6b0b0850`(0.25.0)이다. #393(`TK-225`), #394(`TK-226`), #395(`TK-230`), #396(`TK-228`), #397(`TK-229`), #398(`TK-227`)의 6개 구현 PR을 모두 포함한다.

## 필수 게이트

| 게이트 | 확인 결과 |
|---|---|
| 점수·회귀 (CI `점수 하락 게이트`·`은퇴 세트 비교`) | PR #395(`TK-230`) 및 #398(`TK-227`) CI 기준: 고정 `dev` **83.9→84.8**(`+0.9`, RER 5.59%, v2 `43/56`), `holdout` **83.3→83.8**(`+0.5`, RER 2.99%, v2 `42/54`), 합산 RER **4.27%**(`(168.6 - 167.2) / (200 - 167.2) = 0.0427`), 확인 오탐·A등급 오탐 0, 인젝션 방어 유지. 은퇴 5세트(`sealed_20261008` 53.3 · `sealed_20261008b` 50.0 · `sealed_20261009` 56.9 · `sealed_20261010` 45.8 · `sealed_20261025` 34.1) 모두 오탐 0·A등급 0·항목 회귀 0. |
| 필수 CI (#393~#398) | 6개 구현 PR 모두 `점수 하락 게이트`·`은퇴 세트 비교`·`CodeQL`(새 경고 0건)·`Docker OCR readiness`·`SQLite`·`PostgreSQL`·`Redis` 전수 통과 (`#398` `pip-audit` 통과 포함). |
| 비공개·봉인 세트 | 격리 봉인 세트는 원격 평가 VM 미보유로 `NOT_MEASURED` (배포 후 온라인 점검 시행). |
| 열린 P1 회귀 | `TK-225`(`I-1` P1 regression) 포함 `TK-225`~`TK-230` 6건 모두 `merged` 전환, 열린 P1 회귀 `0`건. |

## 가치·버전·미측정

- **분류(`basis`):** `["added", "fixed", "performance_patch"]` → **0.26.0 (`minor`)**.
  - `added`: 한국어 RapidOCR 폴백 의존성(`requirements.in`/해시 고정/Docker) 및 `LV_OCR_FALLBACK_MODE` 제어 연동(`TK-227`, #398), 임베딩·재순위 HTTP 어댑터 및 청크 리비전 캐시·실요청 기반 `effective_mode`(`TK-228`, #396), 로컬 LLM 운영 안전 설정·헬스체크·스키마 검증·호출 계측(`TK-229`, #397).
  - `fixed`: `ReferenceLibrary` SQLite `interrupted` 구간별 축소 재시도·부분 보존·`UNVERIFIED`/`incomplete_reason` 노출(`TK-225`, #393), `Legal NLI Stage 2` 부정 활용형·반의어·다문장 정렬·짝수 패리티 누락 해소(`TK-226`, #394).
  - `performance_patch`: `TK-230`(#395) AI 문체 잔재 교차 보강 일반화로 `dev 83.9→84.8`, `holdout 83.3→83.8` (합산 RER 4.27%).
- **미측정(`NOT_MEASURED`):** 배포 후 운영 온라인 실측(`case9` 3회 연속 `5/5`·`6/6` 및 `TK-225` 안정성 검증, RapidOCR 저품질 `0.611`/Drive `16쪽` 실측, Dense/Reranker `ON/OFF` 실서버 대조, `LOCAL_ONLY` 로컬 모델 실호출 짝 비교, `Legal NLI assist` 반전 인용 재측정) 및 격리 봉인 세트. 새 기능 포함 릴리스(`RELEASE_PROCEDURE` 2-7)이므로 `main` 병합·배포 직후 온라인 점검을 시행한다.

Agent: evaluator
