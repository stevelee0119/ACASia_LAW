# 0.22.0 버전 커밋 전달문 — Antigravity

목적: 수용·병합된 제품 후보 `fca75347c5612b3a5960005726b4a31f7143b38a`를 0.22.0으로 표시하는 버전 커밋 1개를 만든다. 제품 기능을 추가로 수정하는 작업이 아니다.

## 착수 조건

평가 브랜치 `evaluator/release-022-records`의 PR이 CI를 통과해 `Steve_ACASiaLAW`에 통합된 뒤 시작한다. 최신 원격 Steve에서 아래 두 파일을 확인한다.

- `docs/scorecards/version_verdicts.json`: `from=0.21.0`, `version=0.22.0`, `level=minor`, `measured_commit=fca75347c5612b3a5960005726b4a31f7143b38a`.
- `docs/scorecards/release_022_candidate_20261115.md`: 최종 전체 검증 및 main 대비 동일 조건 비교. 최초 환경 오류 기록을 최종 검증 결과로 인용하지 않는다.

통합 전에는 대기 사유를 평가 PR 번호로 알린다. #303/#311 선행 통합을 다시 요구하지 않는다. 두 PR의 잠금·workflow 통합은 #303 병합으로 끝났다.

## 변경할 파일과 내용

1. 최신 `origin/Steve_ACASiaLAW`에서 새 브랜치를 만든다. `packages/common/config.py`의 버전만 `0.21.0`에서 `0.22.0`으로 바꾼다.
2. `docs/releases.json`에 0.22.0 항목을 기존 스키마대로 추가한다. 실제 작업일의 유효한 날짜를 먼저 넣는다. 날짜가 없으면 README 생성기가 중단한다.
3. 릴리스 노트는 다음 범위를 분류해 기재한다.
   - Added: Time Table 시간순 사건·증거표, 출처 연결, Markdown 복사(#305).
   - Changed: Gemini 4 Hydrogen 기본 모델·단가·요청 설정(#304), AI 관여/전체·일부 범위/이견/표본/근거 강도 정보 보존(#308).
   - Fixed: Drive PDF 읽기·빈 비밀번호·OCR·재개 진단, HWPX 셀 문단 경계, 비율 계산 근거 연결, 공식 Source 개인정보 차단 진단(#307), 미확인 건수 표시(#310), 모바일 프로젝트 목록 새로고침(#312).
   - 운영 재현성: 해시 잠금, 운영/시험 의존성 분리, runtime 기록, pip-audit, score-gate의 시험 잠금·Chromium 설치(#303). README 제목·6개 탭·모델·버전 자동 동기화(#306).
   - 평가 도구 보완: AI 반복 조건 증거 비교, 누락/복수 문서/중복 실행 거부. 모델 정확도 개선으로 설명하지 않는다.
4. `docs/release_highlights.json`은 기존 릴리스 계열 요약 형식에 필요한 경우만 갱신한다. `python scripts/update_readme.py`로 README와 `docs/RELEASE_HISTORY.md`를 재생성한다. 생성 결과에 0.22.0·Time Table 포함 6개 탭·Gemini 4 Hydrogen이 일치해야 한다.

## 수치와 제한

- 고정 dev/holdout 및 은퇴 세트 수치는 평가 판정서의 동일 조건 측정값을 그대로 사용한다. 점수가 오르지 않은 항목을 성능 향상으로 표기하지 않는다.
- 실제 Drive 원본, Gemini 새 모델 호출·비용·품질, AI 범위 정확도/반복, 공식 Source cascade 해소, 실기기 화면은 배포 후 재측정 대상이다. 오프라인 시험 통과를 운영 해소로 바꾸지 않는다.
- `docs/scorecards/version_performance.csv`·성능 그래프·판정서·기준선은 평가 측 소관이다. 구현 측은 추정 행을 넣지 않는다. 평가 JSON에 보존한 v0.22 후보 행은 버전 커밋 수용 후 평가 측이 반영한다.
- 봉인 시험 또는 이번 릴리스에 한정한 대체 승인은 배포 선행요건이다. 버전 커밋은 배포 승인이나 봉인 생략을 의미하지 않는다.

## 검증·제출

1. `python scripts/update_readme.py --check` 및 `pytest -q tests/test_update_readme.py`를 실행한다.
2. 단일 버전 커밋에 `Agent: implementer`를 넣고 `python scripts/check_version_policy.py --base origin/Steve_ACASiaLAW`를 실행한다.
3. Steve 대상 PR을 열고 최종 head의 CI·점수 게이트·CodeQL·pip-audit 결과를 확인한다. 제품 버전 필드 이외의 제품·설정·잠금·workflow diff가 생기면 제거하거나 평가 측에 이유를 설명한다. 전체 `verify_all`은 중복 실행하지 않는다.
4. PR 본문에 최종 SHA, 변경 파일, 버전 정책/문서 생성 검사 결과, 측정값 출처, 운영 미측정 항목, `검토 요청`을 적는다. 평가자는 버전 외 제품 diff 0을 확인한 뒤 main 대상 릴리스 PR을 준비한다.

main 직접 푸시·병합·태그·운영 배포는 이 전달문의 실행 범위에 포함되지 않는다. 최종 main 병합은 릴리스 선행요건 충족 및 사용자 승인 뒤 수행한다.
