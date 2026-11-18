# 0.23.0 릴리스 후보 판정 (2026-11-18)

- 후보 SHA: `d79d6b21eb8b7f4d89def04ce9269ae2a7adbe99` (`Steve_ACASiaLAW`, #335 병합 직후)
- 기준: `183f3d22791bb01d4c8a39ce842e193000c663b8` (`main`, 0.22.0 배포본)
- 판정: **CANDIDATE_VERIFIED_PENDING_VERSION_COMMIT** — 오프라인 검증 통과, 버전 커밋·태그·배포 미시행
- 판정 주체: Claude Code 평가 세션(2026-10-17 사용자 지시로 평가 업무 승계)
- 측정 조건: 오프라인(`LV_ALLOW_NETWORK=0`), Python 3.11.18, Tesseract 5.3.4 eng/kor/osd,
  fonts-nanum, Node 22.23.5, Playwright 1.63/Chromium, SQLite, `OMP_THREAD_LIMIT=1`,
  Ubuntu 24.04 컨테이너. `verify_all`의 환경 단계 `matches_ci=true`.

## 1. verify_all 전체 모드 (후보 SHA, 작업 트리 깨끗)

| 단계 | 결과 |
|---|---|
| environment | 통과 — python 3.11.18, tesseract 5.3.4 |
| acceptance | 통과 1,276 · 실제 실패 0 · strict XPASS 0 |
| regression_ledger | 통과 2,357 · 실제 실패 0 · strict XPASS 0 |
| score_gate | 통과 |
| regression_gate | 통과 — 12칸 전부 동일, 회귀 없음 |
| hardcoding_diff | 통과 |
| test_edits | 통과 |
| protected_paths | 통과 — 보호 경로 20개 모두 평가 측 커밋 또는 승인 |
| version_policy | 통과 — 버전 변경 없음 |
| full_tests | 통과 11,027 · 실제 실패 0 · strict XPASS 0 |
| browser_tests | 통과 200 · 실제 실패 0 · strict XPASS 0 |

**실패 단계 0.** 종료 코드 0.

### 1차 실행의 환경 실패와 처리

첫 실행에서 `regression_gate`와 `full_tests` 5건이 실패했다. 둘 다 평가 환경 결함이었다.

| 실패 | 원인 | 확인 |
|---|---|---|
| `full_tests` 5건 (`tk88` 3단 소제목, `tk127` 4형식 참고 의견 3건, `v5_ocr_dates` 회전 스캔) | `fonts-nanum` 미설치 → `pdf_report.py`가 임베드 TTF를 못 찾고 CID 대체 폰트(`HYSMyeongJo-Medium`)로 떨어져 보고서 절이 누락 | base `6e7bf01`(#335 이전)에서도 같은 5건 실패 → 제품 회귀 아님. 폰트 설치 후 5건 전부 통과 |
| `regression_gate` 13항목 '측정 못 함' | `scripts/path_guard.py`의 `INPUT_ROOTS`가 `Path.home()`에 의존. 이 컨테이너는 `HOME=/root`·저장소 `/home/user/ACASia_LAW`여서 기준 쪽 탐침이 전부 '허용 폴더 밖의 경로'로 거부 | `HOME=/home/user`로 맞춘 뒤 통과(12칸 동일, 회귀 없음) |

CI 설치 목록(`tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng fonts-nanum`)과 대조해 누락을 찾았고,
환경을 CI와 일치시킨 뒤 후보 SHA에서 전체를 다시 돌린 결과가 위 표다. 1차 기록은 원인과 함께 보존한다.

## 2. 고정 시험 (같은 실행에서 재측정)

| 세트 | 구 산식 | 부분점수율 | 확인 오탐 | A등급 | 인젝션 방어 대리값 | v2 일대일 | 미판정 경고 | 참고 경고 | 엔진 오류 | 결함 유형 |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | 82.6 | 0.826 | 0 | 0 | 방어 | 42/56 (75.0%) | 10 | 10 | 0 | 28종 |
| holdout | 81.9 | 0.819 | 0 | 0 | 방어 | 41/54 (75.9%) | 9 | 4 | 0 | 27종 |

0.21.0·0.22.0 기록과 **같은 값**이다. 점수 이동 없음. 점수 순증을 근거로 버전을 올리지 않는다.
법률 정확도·전체 정밀도·공개 벤치마크·실무 효율은 `NOT_MEASURED`(0점/통과가 아님).

## 3. 은퇴 세트 비교 (기준 채점 ↔ 후보, 동일 조건)

| 세트 | 기준 | 후보 | 확인 오탐 / A / 방어 |
|---|---|---|---|
| sealed_20261008 | 53.3 · v2 22/46 · 미판정 6 | 53.3 · v2 22/46 · 미판정 6 | 0 / 0 / 방어 |
| sealed_20261008b | 48.6 · v2 24/54 · 미판정 20 | 48.6 · v2 24/54 · 미판정 20 | 0 / 0 / 방어 |
| sealed_20261009 | 56.9 · v2 31/58 · 미판정 30 | 56.9 · v2 31/58 · 미판정 30 | 0 / 0 / 방어 |
| sealed_20261010 | 45.8 · v2 23/53 · 미판정 11 | 45.8 · v2 23/53 · 미판정 11 | 0 / 0 / 방어 |
| sealed_20261025 | 34.1 · v2 12/44 · 미판정 16 | 34.1 · v2 12/44 · 미판정 16 | 0 / 0 / 방어 |

**후퇴 없음.** 실무 법률 정확도가 아니다.

## 4. 회귀 게이트 (기준 → 후보)

12칸(6사건 × primary/text) 전부 동일: 20/20, 25/25, 22/22, 28/28, 24/24, 21/21. **회귀 없음.**

## 5. 버전 등급

`minor` (0.22.0 → 0.23.0). `basis`: added · changed · fixed.
`#320`~`#335` 16건 병합, 139파일 `+19,560/−1,334`. 신규 기능(RAG 분리 수집·쪽별 상태·주장 단위
검색, 외부 AI 답변 서버 영속, 검토 표 3열 역할 분리, Time-Table 사실관계 중심)과 결함 수정이
함께 들어갔다. 상세 목록은 `version_verdicts.json`의 `0.23.0` 항목 `M4`.

## 6. 사용자 원문 대조 (TK-198~206)

사용자 원문 `[261116 AegisLAW 개선 필요 사항 정리]` 1~9항을 TK-198~206으로 등록하고 원문 문장별
대응표로 판정했다. **11개 문장 중 10개 충족**, 2항은 오프라인 근거만 있고 운영 재현 미확인.
화면 캡처는 사용자 '이상없음' 확인 접수(2026-11-18). 티켓 파일은 `docs/handoff/TK-198_*`~`TK-206_*`.

## 7. 측정하지 못한 것 (합격으로 간주하지 않는다)

1. **봉인 세트 동일 조건 비교 — 2026-11-18 사용자 지시로 이번 판정에서 제외.** 봉인 시험문서·정답은
   저장소 밖 사용자 보관이고 출제·자체 점검은 저장소 미연결 격리 세션이 맡아 이 평가 세션에서 잴 수
   없다. 사용자가 '봉인세트비교 제외'를 지시해 0.23.0 판정은 봉인 비교 없이 확정한다. 0.22.0 판정서의
   `M2`에 해당하는 근거가 0.23.0에는 없으며, 제외가 통과를 뜻하지 않는다.
2. **온라인 실연동 전부.** 공식 DB 대조, Drive 대조·원본/암호화/HWPX, 실제 모델 호출·비용·품질,
   AI 작성 판별, 실기기 화면, 온라인 봉인. 특히 **TK-199(사용자 실제 문서 35,674자의 개인정보
   입력 차단 해소)**는 배포 후 확인해야 한다.
3. 실무 법률 정확도·검색/주장 타당성·검토 효율(EVALUATION_V2 기준 `NOT_MEASURED`).
4. main 병합·태그·운영 `/api/health` 확인(버전·SHA·DB)은 미시행.

## 8. 평가 도구 결함 (별도 보완 대상)

`scripts/path_guard.py`의 `INPUT_ROOTS`가 `Path.home()`에 의존해, 저장소가 사용자 홈 밖에 있는
환경에서는 `regression_gate`의 기준 쪽 탐침이 전부 거부된다. CI는 저장소가 러너 홈 아래에 있어
우연히 통과하므로 CI만으로는 드러나지 않는다. 이번 판정은 `HOME`을 맞춰 측정했고, 도구 보완은
이 릴리스 판정과 분리한다.

## 9. 다음 절차

1. 평가 기록(이 문서 · `version_verdicts.json` 0.23.0 · TK-198~206 · DAILY_TREND · HISTORY)을
   `Steve_ACASiaLAW`에 PR로 병합한다. `Steve_ACASiaLAW`는 보호 브랜치여서 직접 푸시가 거부된다
   (`GH013: 5 of 5 required status checks are expected`).
2. 구현 측이 `packages/common/config.py`의 `version`을 `0.23.0`으로 올리고 변경 기록을 갱신한다.
   `check_version_policy.py`는 이 문서의 판정서가 있어야 통과한다.
3. `Steve_ACASiaLAW → main` 릴리스 PR, 태그 `v.0.23.0`, 배포.
4. 배포 후 운영 `/api/health`로 버전·SHA·DB를 확인하고, 기능별 온라인 평가를 별도 세션에서 수행한다.
