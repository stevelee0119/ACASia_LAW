# Antigravity 구현 전달문 — 2026-10-17 통합본

이 문서 하나가 Antigravity에 대한 현행 지시다. 이전 전달문 전체를 대체한다. 작성: 평가 에이전트(Claude Code).

## 1. 체제(2026-10-17 사용자 지시)
- **새 구현은 Antigravity가 맡는다.** 평가(측정·판정·통합·릴리스 준비)는 Claude Code 평가 세션이 맡는다.
- Codex는 전환 시점에 열린 TK-44·45·49·55·73만 마무리한다. 그 브랜치·PR(#63·#79·#80·#84·#85·#92·#93·#95·#96·#97)에 푸시하지 않는다.
- [AGENTS.md](../../AGENTS.md)와 [AGENT_ROLES](../AGENT_ROLES.md)의 구현 규칙을 따른다: 보호 경로 수정 금지, 사건 값·서면 문구 하드코딩 금지, 새 규칙마다 합성 양성 3건·대조 3건 이상, 커밋 끝 `Agent: implementer`, 새 브랜치 → PR, `Steve_ACASiaLAW`·`main` 직접 푸시·강제 푸시 금지.
- 비공개 세트·봉인 자료·고정 비공개 벤치·개발 말뭉치 `check/`는 요청·열람하지 않는다.

## 2. 시작점
- 운영: `main` b68cfee(0.13.0). 통합 브랜치: `Steve_ACASiaLAW`. 착수 때 최신 `origin/Steve_ACASiaLAW`를 받아 시작 SHA를 PR에 적는다.
- Steve 대상 PR의 필수 검사는 4개다: 점수 하락 게이트, 테스트(SQLite + PostgreSQL/pgvector + Redis), Docker OCR readiness, **CodeQL 새 경고 게이트**(2026-10-16 추가. PR이 새로 만든 보안 심각도 High 이상 경고가 있으면 실패).

## 3. 배정 — [TK-76](TK-76_focus_types_generalization_cycle1.md) 개발 말뭉치 중점 6유형 1주기
**목표:** 특정 서면이 아니라 결함 유형 자체를 잡도록 탐지를 넓힌다. 대상은 EVI-INCONS·SRC-UNV·EVI-NUM·EVI-FORM·EVI-DATE·EVI-COPY.

**자료:** 사용자가 train 전용 ZIP을 준다. 지문 `d058b04f03579336`을 확인하고 저장소 밖에 둔다(어떤 worktree에도 복사·symlink 금지).

**순서**
1. **진단 메모 먼저**(첫 커밋, `docs/handoff/requests/`): train의 6유형 항목을 실제 진입점으로 돌려, 놓친 항목을 원인 범주별로 센 유형별 표. 범주·작성 요령은 TK-76 3절. 평가 측 회신 뒤 2로 간다.
2. **유형별 PR:** 한 PR에 한 유형. 제안 순서는 EVI-COPY → SRC-UNV → EVI-INCONS → EVI-FORM → EVI-NUM → EVI-DATE(메모에서 바꿀 수 있다).

**현재 상태(2026-10-17):** 진단 메모 [#109](https://github.com/stevelee0119/verify_ACAS_LAW/pull/109)는 **조건부 승인**이다([판정](https://github.com/stevelee0119/verify_ACAS_LAW/pull/109#issuecomment-6229122189)). 2단계 순서(COPY → SRC-UNV → DATE → INCONS → FORM → NUM)는 승인했다. 다음 일은 아래와 같다.
- #109에 정정 커밋 1개를 올린다.
  - EVI-INCONS 한글병기 8건 재진단. 기존 `korean_amount.words_digits_mismatches`가 있으므로 '미지원'은 원인이 아니다.
  - EVI-COPY 40항목의 '복사 쪽 → 원문 쪽 문서 종류' 건수표(문서 종류 이름만).
  - EVI-FORM의 (d) 40건을 제품 탐지 공백으로 재분류하고 법적 근거를 정정(민사소송법 제277·355·358조).
  - EVI-NUM의 가지번호 중복·별지 구역을 TK-73 영역으로 표시.
- 그 뒤 '검토 요청 + SHA'를 남긴다. SHA는 `git rev-parse HEAD` 출력 그대로 쓴다.
- 기다리는 동안 EVI-DATE 위치 문맥 PR은 먼저 시작해도 된다. 위치 정보는 모든 날짜 finding에 '가장 가까운 소제목/문단 번호'로 일관되게 붙이고, 말뭉치 토큰에 맞춘 문구는 넣지 않는다.
- 유형별 금지사항:
  - 산식·병기 검사를 병렬로 새로 만들지 않고, 기존 `calculation.evaluate_expression`·`korean_amount`를 확장한다.
  - SRC-UNV에는 `.invalid` 도메인 규칙을 쓰지 않는다. PR에 새 UNVERIFIED finding 수(문서당)를 보고하고, 출처 결함으로 단정하지 않는다.
  - EVI-COPY의 제목 제한은 통째로 풀지 않는다. 대조군 문서의 B등급 SUSPICIOUS는 채점기가 대조군 오탐으로 센다.

**알려진 단서:** 문서 간 복사 탐지는 '진술서·사실확인서·확인서' 제목이 있는 문서만 비교한다(TK-76 2절). 넓힐 때는 같은 대리인 서면끼리의 정상 중복을 오탐하지 않도록 설계한다.

**제외:** 증거번호 중복 판정(`_exhibit_lines`·`_numbering`)은 Codex의 TK-73 영역이다. 건드려야 하면 먼저 평가 측에 알린다.

## 4. 공통 제출 점검표
2026-10-16 사용자 승인. 탐지를 바꾸는 PR은 1~5항, 그 밖은 해당 항목만 낸다. 해당 없으면 사유를 적는다.

| # | 조건 | PR에 첨부 |
|---|---|---|
| 1 | 실제 진입점(파이프라인·API)에서 새 동작을 실행하는 시험 1개 이상 | 시험 이름 |
| 2 | 새 정규식·분석 경로마다 길이 1배·4배 입력을 각 3회 재서 최솟값 비 < 8, 4배 최솟값 < 1초 | 경로·입력 길이·측정값·비·재현 명령 |
| 3 | 보고 수치는 재현 명령과 그 출력을 그대로 붙인다 | 명령·출력·최종 SHA·환경 |
| 4 | 은퇴 봉인 4세트(`tests/fixtures/retired_sealed/`)와 고정 dev·holdout의 전후 점수표 | 기준·후보 SHA, 점수·재현율·오탐·A등급 오탐 |
| 5 | train 해당 유형의 전후 재현율 | 유형·분모·전후 재현율 |

- 2항은 새 경로 자체의 처리 시간이다. 캐시를 비우거나 새 프로세스로 잰다(예: `tests/regression/test_tk24_statutory_exclusion.py`). 분모가 0.0001초보다 작으면 0.0001초로 보정하고 원값과 함께 적는다.
- 4항은 공개된 은퇴 4세트만 쓴다. 같은 SHA CI의 dev·holdout 결과를 인용해도 된다.
- 기존 시험 삭제·약화, 하드코딩, 보호 경로 변경은 CI(점수 하락 게이트)가 자동으로 막으므로 표에 따로 적지 않는다.

## 5. 보고와 판정
- 커밋 전에는 바꾼 파일과 관련 시험만 돌린다. 푸시 뒤 CI가 실패하면 job 로그 끝 '실패 시험 목록'으로 고친다.
- 보고는 PR 코멘트 3줄(바꾼 것·남은 것·'검토 요청' + SHA)과 위 표.
- 평가 측은 '검토 요청'이 있고 CI가 끝난 SHA만 판정한다. 수용 기준은 TK-76 5절: 고정 81.7/79.2·오탐 0 유지, 은퇴 4세트 점수 하락·오탐 증가 없음, train 해당 유형 재현율 상승. check는 평가 측이 집계만 잰다(주기 목표이며 PR 합격선이 아니다).
- 같은 접근이 두 번 실패하면 세 번째 전에 설계 메모를 다시 낸다.

## 6. 그 밖
- 사용자 PC·브라우저 실행을 따로 배정받은 경우에만 한다. 이 문서만으로 유료 호출, 운영 설정 ON/OFF 변경, 배포를 하지 않는다.
- 고정 비공개 벤치마크 결과로는 티켓을 만들지 않는다([FIXED_BENCHMARK](../scorecards/FIXED_BENCHMARK.md) 4절).
