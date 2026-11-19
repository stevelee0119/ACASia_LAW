# TK-210 실연동 점검이 은퇴 모델의 404를 strict 실패로 센다 (평가 측 점검 도구)

- 발견일: 2026-11-19 (평가 세션, PR #340 I-5 판정)
- 출처: PR #340 I-5. 배포 `32d9c485` run 44396919559, 그리고 **0.21.0 배포 기록에 같은 두 모델·같은 사유**
- 종류: **평가 측 점검 도구 결함.** 제품 결함이 아니다. 구현 측에 보내지 않았다
- 범위: 0.23.0 평가 자산 수정 (2026-11-19 사용자 결정 "I-5는 평가측에서 고치자")
- 상태: 수정 완료(평가 측)

## 문제

`외부 Source 실연동 점검`(`live-source-check.yml`, `--strict`)이 실패로 끝나는데, 실패 항목에
운영에 쓰지 않는 구형 Gemini 모델 2건이 들어 있었다. 그 때문에 **운영 기본 모델의 상태를
읽어내기 어려웠다.**

| 실행 | 실패로 집계된 항목 |
|---|---|
| 0.21.0 (`release_021_deployment_20261115.json`) | `gemini:gemini-2.5-flash`, `gemini:gemini-2.5-flash-lite` — "no longer available to new users" |
| 0.23.0 (run 44396919559) | **같은 두 항목·같은 사유** |

두 실행 모두 운영 기본 `gemini-4-hydrogen`은 OK였고, 같은 실행의 다른 후보
(`gemini-3-flash-preview`·`gemini-3.1-flash-lite`·`-preview`)도 호출 가능했다.

## 원인

`scripts/live_source_check.py` `check_gemini_models()`:

    names = [... /models 응답에서 generateContent 지원 모델 ...]
    usable = [n for n in names if n.startswith("gemini") and not any(...)]
    ordered = sorted(set(usable) - {current}, key=lambda n: ("flash" not in n, "pro" not in n, n))[:5]

후보를 공급자의 `/models` 목록에서 자동으로 고르고 `flash`를 앞에 세운다. 목록에는 남아 있으나
**신규 호출이 막힌 구형 모델**이 그 앞자리에 들어오고, 호출하면 404가 돌아온다.
`partition_failures()`는 `requires_key`가 참이면 그 404를 치명적 실패로 넣었고, strict가 1로 끝났다.

모델 ID를 목록으로 박아 두면 다시 낡는다. 그래서 **자동 선택은 유지하고 판정 쪽을 고쳤다.**

## 수정

1. `CheckResult`에 `advisory` 칸을 더했다. 운영에 쓰지 않는 대상의 호환성 알림을 뜻한다.
2. `_is_retired_model(status_code, detail)`을 더했다. 공급자가 '이 모델은 더 못 쓴다'고 답한
   **문구 축**을 받는다(낱말 하나가 아니다): `no longer available` · `not available to new users` ·
   `deprecat` · `has been retired/removed` · `is not supported` · `unsupported model` ·
   `not found for API version`. 4xx에만 적용한다 — 5xx는 서비스 장애이지 은퇴가 아니고,
   본문 없는 404는 경로 오류일 수 있다.
3. 후보 모델(현재 설정이 아닌 것)이 위 꼴로 실패하면 `advisory=True`로 둔다.
4. `partition_failures()`가 치명적 실패·경고·**호환성 알림** 셋으로 나눈다. strict는 알림을 세지 않는다.
5. 보고서에 알림을 별도 절로 적는다.

**운영 기본 모델의 실패는 알림으로 내리지 않는다.** 쿼터 초과·권한 오류·요청 오류도 그대로 실패다.

## 평가 측 검증

| 시험 | 결과 |
|---|---|
| 문구 축 (은퇴 8꼴 + 실패로 남아야 하는 7꼴) | **15/15** |
| 3분기 분리(운영 기본 실패는 치명적, 후보 은퇴는 알림, 공개 Source는 경고) | 통과 |
| 알림만 있을 때 strict 실패 없음 | 통과 |
| 보고서 표시 | 통과 |
| `tests/test_tk210_live_check_retired_model_advisory.py` | **19건 통과** |

0.21.0·0.23.0 기록에 남은 실제 응답 문구를 그대로 시험 입력으로 썼다.

## 남는 것

`law_go_kr:사건번호조회(2015모2524)` 정확 일치 0건과 `semantic_scholar` 속도 제한은 이 티켓과
별개이며 0.21.0 기록과 동일한 기존 조건이다. 전자는 공식 DB 색인 범위·검색 파라미터 문제일 수
있어 따로 측정해야 한다. 이 티켓으로 가리지 않는다.
