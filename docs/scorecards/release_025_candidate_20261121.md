# 0.25.0 릴리스 후보 오프라인 판정 (2026-11-21)

**판정: 오프라인 수용 (minor 0.24.0 → 0.25.0).** 평가 대상은 `Steve_ACASiaLAW`의 `02d3a5c0e312c5f8139bcf11e52ac1c9836c1f83`이며, 기준은 운영 `main`의 `684f3469028dc38e539345501191cc7c9832b13a`(0.24.0)이다. #383(`TK-221`), #384(`TK-223`), #385(`TK-220`), #386(`TK-222`), #387(`TK-224`)의 5개 구현 PR을 포함한다.

## 필수 게이트

| 게이트 | 확인 결과 |
|---|---|
| 점수·회귀 (CI `점수 하락 게이트`·`은퇴 세트 비교`) | PR #387(`02d3a5c0` 동일 트리) CI 기준: 고정 `dev` **82.6→83.9**(v2 `43/56`), `holdout` **81.9→83.3**(v2 `42/54`), 확인 오탐·A등급 오탐 0, 인젝션 방어 유지. 합산 오류 감소율(RER) **7.61%**(`(167.2 - 164.5) / (200 - 164.5) = 0.0761`, `dev` 7.47% · `holdout` 7.73%). 은퇴 5세트(`sealed_20261008` 53.3 v2 22/46 · `sealed_20261008b` **48.6→50.0** v2 25/54 · `sealed_20261009` 56.9 v2 31/58 · `sealed_20261010` 45.8 v2 23/53 · `sealed_20261025` 34.1 v2 12/44) 모두 오탐 0·A등급 0·항목 회귀 0. |
| 필수 CI (`02d3a5c0` / PR #387) | `점수 하락 게이트`·`은퇴 세트 비교`·`CodeQL`(새 경고 0건)·`Docker OCR readiness`·`테스트 (SQLite + 인프로세스 Worker)`·`테스트 (PostgreSQL/pgvector + Celery 브로커)`·`테스트 (SQLite + PostgreSQL/pgvector + Redis)` 전수 통과(총 11개 성공, `Sourcery review` skipping). |
| 비공개·봉인 세트 | 비공개 봉인 세트는 격리 저장소 밖 자산으로 이번 원격 평가 VM에서 별도 재실행하지 않음(`NOT_MEASURED`). `RELEASE_PROCEDURE` 2절 기준 오프라인 탐지 변경(`TK-221`)이 포함되어 있으나, 5개 구현 PR의 회귀 게이트·은퇴 5세트·고정 2세트·SQLite/PostgreSQL 전수 CI 통과를 근거로 릴리스 후보를 판정하며 배포 후 온라인 점검을 시행한다. |
| 열린 P1 회귀 | `ticket_registry.json`의 `open`+`priority=P1`+`kind=regression` 0건. `TK-220`~`TK-224` 5건 모두 `merged` 전환. |

## 가치·버전·미측정

- **분류(`basis`):** `["added", "fixed", "performance_patch"]` → **0.25.0 (`minor`)**.
  - `added`: 실행 경로 진단 가시성(`TK-223`, `next_gen_feature_diagnostics()`·`/api/diagnostics`·`run_manifest`), 적응형 OCR 폴백 텔레메트리 및 재색인 `searchable_pages_delta`(`TK-222`), 공식 Source 원응답/필터 일치 진단(`TK-224`), `ClauseNormalizer` 승격(`TK-221`).
  - `fixed`: 전달 청크 `SUPPORTS` 의견 생성·근거 연결 보강(`TK-220`, `RAGC-S3`), `law_go_kr` 구분자 변형·2자리 연도 사건번호 정규화 및 `AcademicSourceAdapter` 429 `RATE_LIMITED` 오류 원인 분리(`TK-224`).
  - `performance_patch`: `TK-221` 오프라인 `dev 82.6→83.9`, `holdout 81.9→83.3` (합산 RER 7.61%), 은퇴 `sealed_20261008b 48.6→50.0`.
- **미측정(`NOT_MEASURED`):** 배포 후 온라인 실측(Hybrid RAG Dense·Reranker, `Legal NLI Stage 2`, 운영 OCR 폴백 채택, 로컬 LLM·카세트 `RECORD/REPLAY`, `RAGC-S3` 운영 재현, 실무 법률 정확도) 및 격리 봉인 세트. 새 기능 포함 릴리스(`RELEASE_PROCEDURE` 2-7)이므로 `main` 병합·배포 직후 `/api/health` 확인 및 U2 실연동·온라인 점검을 시행한다.
- **참고(태그):** 원격 저장소에 기존 `v.0.25.0` 태그가 `684f3469`에 이미 존재하므로(`RELEASE_PROCEDURE` 3절 5: 태그 삭제·이동 금지), `main` 병합 후 태그 처리는 사용자 확인을 거쳐 결정한다.

Agent: evaluator
