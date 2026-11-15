# 0.22.0 릴리스 후보 통합 판정 — 2026-11-15

**오프라인 통합 검증 수용. 버전은 0.21.0 → 0.22.0(minor). main 병합·배포는 보류.** 새 봉인의 동일 조건 비교, 구현 측 버전 커밋, 릴리스 PR 최종 CI 및 사용자 main 병합 승인이 남았다.

- 제품 후보: `fca75347c5612b3a5960005726b4a31f7143b38a`. 기준 main: `83d862e78ba3e4d489dcab3fdc5b1bcc7c5838ca`.
- 포함: #303 의존성/runtime, #304 Gemini, #305 Time Table, #306 README, #307 TK182/183/184/186, #308 TK185, #310 건수 표시, #312 모바일 동기화. #302의 온라인 판정은 담당 세션 기록을 인용하며 재판정하지 않았다.
- main 대비 30커밋/87파일(평가 기록 포함), 제품/설정 22파일. migrations 변경 없음. 프로그램 표시 버전은 구현 측 버전 커밋 전까지 0.21.0이다.

## 1. 최종 verify_all

평가 측 재실행: Linux/Ubuntu24.04, Python3.11.17, Tesseract5.3.4 eng/kor/osd, 잠긴 시험 의존성83개, Playwright1.63.0/Chromium153, 오프라인. 전체 모드 **종료0, 실패 단계0**.

| 단계 | 결과 |
|---|---:|
| 수용 시험 | 1278 passed |
| 회귀 원장 | 2357 passed |
| 전체 시험(수용/별도 UI 제외) | 10430 passed |
| 별도 브라우저 시험 | 200 passed |
| 환경·점수·항목회귀·하드코딩·시험편집·보호경로·버전 | 모두 통과 |

원장은 전체 시험에도 포함되므로 이 행들을 합산해 고유 시험 수로 표시하지 않는다. 실제 실패/strict XPASS는 0이며 기존 xfail은 해결로 계산하지 않는다.

최초 환경 실패도 보존했다. 최소 Ubuntu의 tzdata 누락은 API import/수용 fixture를 막았고, /workspace와 과거 worktree의 경로 허용 범위 차이는 일부 탐침 측정을 막았다. 다음 /tmp bind mount 환경에서는 내구성 시험4건의 기본 임시 디스크 가정과 충돌했다. 컨테이너 overlay에 독립 clone/TMPDIR을 두고 관련14건 통과를 확인한 후 전체를 다시 실행했다. 제품·시험·경로 검사·기준선 변경이나 환경 불일치 허용 옵션으로 통과시킨 것이 아니다. **최종 성공 실행만 이 표의 근거다.**

## 2. 동일 조건 비교와 가치

| 지표 | main 0.21.0 | 후보 | 판정 |
|---|---:|---:|---|
| 고정 dev / holdout | 82.6 / 81.9 | 82.6 / 81.9 | 유지 |
| v2 dev / holdout | 42/56 / 41/54 | 42/56 / 41/54 | 유지 |
| 은퇴5세트 | 53.3 / 48.6 / 56.9 / 45.8 / 34.1 | 동일 | 유형/항목 후퇴 없음 |
| 확인 오탐 / A | 0 / 0 | 0 / 0 | 유지 |
| 7세트365항목 v2 | 195/365 (53.4%) | 195/365 (53.4%) | RER 0 |

0.20.0도 같은 조건으로 7세트를 재실행해195/365를 확인했다. README/그래프는 실제 릴리스된0.20/0.21 행을 보충했다. v0.22 후보 행은 JSON에 보존하고 버전 커밋 수용 후 평가 측이 반영한다. 365항목 재현율·법률43/123은 재사용 회귀 자료의 오프라인 지표로 실무 정확도나 새 봉인 점수를 대신하지 않는다.

minor 근거는 Added/Changed(시간순 사건표, 모델 및 AI 관여/범위 정보)이며 점수 향상을 주장하지 않는다. #305 실제 진입점 시험 및 사용자 화면 확인, 각 PR의 수용 CI와 이번 합본 검증을 연결했다.

## 3. GitHub CI 인용

- [CI43709116501](https://github.com/stevelee0119/ACASia_LAW/actions/runs/43709116501): SQLite11906 passed/13skipped/24xfail, PostgreSQL11910 passed/9skipped/24xfail, Docker OCR 성공.
- [점수43709116513](https://github.com/stevelee0119/ACASia_LAW/actions/runs/43709116513): 성공, 수용1278·원장2357. 이 push의 은퇴 job은 skipped이므로 본문2절은 평가 측 main 비교 실행을 근거로 한다.
- [pip-audit43709116539](https://github.com/stevelee0119/ACASia_LAW/actions/runs/43709116539): 성공. 구현 PR의 CodeQL은 병합 전 확인했으며, 최종 릴리스 PR의 새 head에서도 확인한다.
- GitHub runner는 Ubuntu26.04/Python3.11.18/Tesseract5.5.0이었다. 위 CI는 인용 근거이며, 1·2절은 고정된 평가 환경에서 재실행한 결과다. 서로 같은 환경이라고 쓰지 않는다.

## 4. 새 봉인 제출 결과 — 판정 보류

사용자 텍스트 요약: 후보 prefix fca7534, 8문서/62항목, 구23.0·v2 13/62(21.0%)·개인정보 종류13/26, 확인오탐/A0, 미판정13·참고1. 보안탐지0/10. **원본 집계 JSON·전체SHA/자료지문 검증·한국어OCR·동일 조건 main 결과가 없다.** Python3.11.2/Tesseract5.3.0 eng/osd만으로 실행됐으므로 한국어OCR를 보완한 쌍 비교가 필요하다. 낮은 점수를 OCR 때문이라고 단정하지 않는다.

구 `injection_defended`는 release_gate가 PASS가 아니며 집계 점수에 payload 표지가 재출력되지 않았는지를 보는 제한된 대리값이다. 보안10항목 탐지와 같은 뜻이 아니다. 0/10을 별도로 유지한다. 임의 절대 합격선이나 이전0.21 봉인 생략 승인을 적용하지 않는다.

[봉인 재측정 전달문](../handoff/RELEASE_022_sealed_remeasurement_instructions_2026-11-15.md)과 [제출 집계 기록](release_022_sealed_submitted_20261115.json)을 따른다. 원문·정답·비공개 Drive ID·상세 finding은 이 PR에 넣지 않았다.

## 5. 평가자 잔여 조치와 운영 한계

AI 반복 도구는 full SHA/입력 및 문서 대응/프로젝트·정책·모델·날짜·Drive 증거를 해시로 비교한다. 누락은 UNKNOWN, 차이는 DIFFERENT, 복수 문서는 거부한다. 중복 run ID는 독립 반복으로 계산하지 않는다. 실제 참여 모델 수의 차이만으로 auto라우팅 조건 불일치로 처리하지 않는다. 조건 원문은 출력하지 않는다. 관련43시험과 README12시험(합55) 통과.

TK182~186은 코드 병합 상태를 반영하되 운영 해소 완료로 바꾸지 않았다. 기존 P1 Drive 읽기/공식 Source cascade의 실제 해소, Gemini 실제 호출/품질/비용, AI 범위 정확도, 실기기 화면은 NOT_RUN/보류다. 이번 시험에서 새 제품 P1 회귀는 확인되지 않았다. [기능별 온라인 표](FEATURE_ONLINE_EVALUATION.md)의 REL022 항목과 [배포 후 비교 계획](online_compare_0210_0220_plan.md)을 유지한다.

## 6. 다음 순서와 가능 여부

1. 평가 PR: 이 문서·버전 판정·도구/그래프 보완을 Steve에 통합. **해당 PR 최종 head CI 성공 뒤 병합 가능**.
2. 구현 버전 커밋: 평가 PR 통합 뒤 [전달문](../handoff/RELEASE_022_version_commit_instructions_2026-11-15.md)대로 0.22.0 단일 커밋. 기능 추가/전체 verify_all 재실행 불필요. 평가 측은 버전 외 제품 diff0 및 CI 확인.
3. 봉인 쌍 비교: 담당자는 지금 재측정 가능. 집계 두 파일 수신·동일 조건/회귀 판정 전 **봉인 통과 아님**.
4. main 릴리스 PR: 버전 커밋·봉인 판정·최종CI 완료 후 준비/병합 안내. **지금 main 병합/배포 불가**. main은 Render 자동 배포이므로 사용자 승인 뒤 수행.
5. 배포 뒤 exact SHA/version/DB health·태그·온라인0.21→0.22 비교·전용 시험 프로젝트 정리. 미실행을 통과로 계산하지 않는다.

근거: [전체 검증 JSON](release_022_verification_20261115.json), [7세트 재측정 JSON](release_022_performance_20261115.json), `version_verdicts.json`의0.22.0 항목.
