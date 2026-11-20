# 0.23.0 버전 커밋 전달문 — 구현 측

목적: 수용·병합된 제품 후보 `2633d91c65d529683b48a5997ca1368bfa0c90e2`를 0.23.0으로 표시하는 **버전 커밋 1개**를 만든다. 제품 기능을 더 고치는 작업이 아니다.

## 착수 조건

평가 브랜치 `eval/release-0230-final`의 PR이 CI를 통과해 `Steve_ACASiaLAW`에 통합된 뒤 시작한다. 최신 원격 Steve에서 아래 두 파일을 확인한다.

- `docs/scorecards/version_verdicts.json`: `from=0.22.0`, `version=0.23.0`, `level=minor`, `basis=[added, changed, fixed]`, `measured_commit=2633d91c65d529683b48a5997ca1368bfa0c90e2`, `release_status=CANDIDATE_VERIFIED_AWAITING_VERSION_COMMIT`.
- `docs/scorecards/release_023_candidate_verification_20261119.md`: 6절이 최종 후보 `2633d91`의 전체 검증이다. **2~5절은 첫 후보 `2b8b4bd`의 기록이므로 최종 검증 결과로 인용하지 않는다.**

통합 전에는 대기 사유를 평가 PR 번호로 알린다.

## 변경할 파일과 내용

1. 최신 `origin/Steve_ACASiaLAW`에서 새 브랜치를 만든다. `packages/common/config.py`의 `version`만 `0.22.0` → `0.23.0`으로 바꾼다.
2. `docs/releases.json`에 0.23.0 항목을 기존 스키마대로 추가한다. **실제 작업일의 유효한 날짜를 먼저 넣는다**(날짜가 없으면 README 생성기가 중단한다).
3. 릴리스 노트는 다음 범위를 분류해 적는다. 범위는 `v.0.22.0..2633d91`(PR #320~#352)이다.
   - **평가 측 minor 판정**(0.22.0 → 0.23.0, `2633d91` 기준, added·changed·fixed): verify_all 전체 모드에서 수용 1,276 · 회귀 원장 2,357 · 전체 11,416 · 브라우저 200, 실제 실패 0. 회귀 게이트 '회귀 없음'(명세 전 항목 base=head). 고정 dev 82.6 · holdout 81.9 · 확인 오탐 0 · A등급 오탐 0 · 엔진 오류 0, v2 일대일 42/56 · 41/54로 **0.21.0·0.22.0과 같은 값**이다.
   - **Added**: Time-Table 사실관계 중심 정리와 근거 연결, 참고자료 미독 안내 표시(화면·PDF·DOCX), 발췌 선택 관측성(#349·#351).
   - **Changed**: Drive 참고자료 완독 판정을 '읽을 수 있는 쪽 완독'과 '확인된 미독'으로 분리하고 미독 사유를 분류해 표시(#343·#349), RAG 실패를 파이프라인 건강 판정에 드러냄(#350).
   - **Fixed**: Time-Table에 재판행위 날짜가 올라오던 문제(#342), 지지 의견 진단 단계 분리(#344), Drive 쪽 단위 이어 읽기와 재시도 상한(#343·#349).
   - **평가·CI 자산**: CI 게이트 기준을 이벤트와 무관하게 고정하고 중복 실행 제거(#348), 절대 벽시계 시간 단언을 자가 보정 상대 한계로 교체, 시험 승인 범위 한정, 회귀 게이트 기준 입력 경로(#352). **모델 정확도 개선으로 적지 않는다.**
4. `docs/release_highlights.json`은 기존 릴리스 계열 요약 형식에 필요한 경우만 갱신한다. `python scripts/update_readme.py`로 README와 `docs/RELEASE_HISTORY.md`를 다시 만든다. 생성 결과에 0.23.0이 반영돼야 한다.

## 수치와 제한

- 고정 dev/holdout·은퇴 세트 수치는 **평가 판정서의 동일 조건 측정값을 그대로** 쓴다. 점수가 오르지 않은 항목을 성능 향상으로 적지 않는다. 이번 판의 고정 세트는 **움직이지 않았다**.
- `docs/scorecards/version_performance.csv`·성능 그래프·판정서·기준선은 **평가 측 소관**이다. 구현 측은 추정 행을 넣지 않는다. v0.23 행은 버전 커밋 수용 뒤 평가 측이 반영한다.
- **다음은 미측정이다. 오프라인 시험 통과를 운영 해소로 바꾸지 않는다.**
  - TK-208이 노린 'Drive 참고자료 라이브러리 READY 도달' — 배포 뒤 3회차 온라인 점검에서 실측한다.
  - 완독 스냅샷 기준 운영 표준 23항목 비교, `RAGC-S3`(모델 판단 축, 사용자 결정 대기).
  - 실무 법률 정확도·검색/주장 타당성·검토 효율, AI 작성 판별·공식 DB 대조·Drive 실연동.
- 봉인 시험은 2026-11-18 사용자 결정으로 이 릴리스에서 **면제**됐다. 면제는 통과가 아니며, 버전 커밋이 배포 승인이나 봉인 생략을 뜻하지도 않는다.
- 평가 환경과 CI의 python 판이 다르다(3.13.18 대 3.11). verify_all의 `environment` 단계가 이를 실패로 잡지만, 같은 단계를 CI가 3.11에서 모두 통과시켰다. 이 사실을 가리지 않는다.

## 검증·제출

1. `python scripts/update_readme.py --check`와 `pytest -q tests/test_update_readme.py`를 돌린다.
2. 단일 버전 커밋에 `Agent: implementer`를 넣고 `python scripts/check_version_policy.py --base origin/Steve_ACASiaLAW`를 돌린다.
3. Steve 대상 PR을 열고 최종 head의 필수 CI 5종·CodeQL 결과를 확인한다. 제품 버전 필드 이외의 제품·설정·잠금·workflow diff가 생기면 없애거나 평가 측에 이유를 적는다. **전체 `verify_all`은 다시 돌리지 않는다**(릴리스 후보에서 평가 측이 이미 한 번 돌렸다).
4. PR 본문에 최종 SHA, 바꾼 파일, 버전 정책·문서 생성 검사 결과, 측정값 출처, 운영 미측정 항목, `검토 요청`을 적는다.

`main` 직접 푸시·병합·태그·운영 배포는 이 전달문의 범위가 아니다. 최종 `main` 병합은 선행요건 충족과 사용자 승인 뒤에 한다.
