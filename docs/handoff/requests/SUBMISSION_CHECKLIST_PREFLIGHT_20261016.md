# 2026-10-16 공통 제출 조건 사전점검

사용자 승인 전달문 `MSG_TO_CODEX_EVAL_20261016.md`의2·4항을 전달문에 넣기 전에 CLAUDE.md의 사전점검 규칙에 따라 실행했다. **제품 수용·새 봉인 시험·고정 비공개 벤치 측정이 아니다.**

## 확인한 시작점과 환경

원격 main `b68cfeec2c5c168a3b9e6e2e92653ea6892521bf`/0.13.0, Steve `a47fb6f849618463d54b0107c27bbd85e4921477`. 제품 경로 diff0. main의 clean detached worktree에서 실행했고 제품·시험·CI·채점기·기대값을 바꾸지 않았다. Linux/Python3.11.17/pdfplumber0.11.10/Tesseract5.5.0, OCR eng/kor/osd, `LV_ALLOW_NETWORK=0`, 모델 호출0. CI의Tesseract5.3.4와 다른 환경이며 strict-env CI를 대신하지 않는다. 시간/의존성 값도 과거 실행과 다를 수 있다.

기존 scorecard OCR 언어 메타데이터 helper가 tesseract 헤더의 공백 분할 때문에 경로/헤더 단어도 언어로 기록한 것을 확인했다. 원본 영수증은 보존하고 `tesseract --list-langs`의 헤더 다음 행으로 실제 eng/kor/osd를 별도 확인했다. 이 문서 작업에서 helper 코드나 OCR 자체를 수정하지 않았다.

## 2항: 새 정규식·분석 경로의 길이 비율

관련 기존시험16건 PASS, 실패/오류/skip0,3.462초:

```bash
LV_ALLOW_NETWORK=0 python -m pytest -q \
  tests/regression/test_tk24_statutory_exclusion.py::test_synthetic_long_sentence_and_repeated_prefixes_are_linear \
  tests/regression/test_tk24_statutory_exclusion.py::test_synthetic_repeated_input_finishes_within_tenth_second \
  tests/test_tk64_exhibit_prose_rows.py::test_tk66_exhibit_section_head_regex_redos_prevention \
  tests/test_tk64_exhibit_prose_rows.py::test_tk66_exhibit_section_head_regex_13_contrasts \
  tests/test_tk72_citation_extractor_linear.py
```

TK24 원래 시험은 캐시를 비운 각3회 최솟값·분모바닥0.0001초·비<8·큰입력<1초다. TK66의0.1초 및 TK72의 기존2회/32k·호환 조건을 새 조건 때문에 바꾸지 않는다. 새/변경 경로에는 사용자 승인3회 조건을 추가하며 기존 시험은 그대로 적용한다.

같은TK24 합성 family의 별도 공개 계측(원래pytest 재실행이 아니라3회 값 수집)을 수행했다. 고정 prefix28자와 반복본문1,125/4,500회, 실제24,778/99,028자다. 캐시는 매 표본 비우고 GC/clock 설정은 변경하지 않았다.

| 입력 | 3회 원값(초) | 최솟값(초) |
|---|---|---|
| 1배 | 0.030811653 / 0.028367066 / 0.030459125 | 0.028367066 |
| 4배 | 0.103167824 / 0.060567228 / 0.056937309 | 0.056937309 |

최솟값 비2.007162<8,4배최솟값0.056937309<1초 PASS. 실제 크기는 고정 prefix로 정확4배보다 약간 작으며 그 차이도 기록했다. 이것을 새 모든 경로의 실행 시간 보장이나 전체 파서 선형성 증명으로 일반화하지 않는다.

## 4항: 공개 은퇴4세트와 dev/holdout 전후 표

기존 `scripts/eval_testset.py`의 `run_pipeline`/`score` 및 `scorecard.summarize`로6세트를 한 번씩 오프라인 실행했다. 같은 도구의 CLI 재현 형식은 다음과 같다. 경로는 **이미 개발용으로 공개된 은퇴 세트**이며 현재 비공개 봉인/고정 벤치가 아니다.

```bash
LV_ALLOW_NETWORK=0 python scripts/eval_testset.py --testset tests/fixtures/retired_sealed/sealed_20261008 --out <외부출력폴더>
LV_ALLOW_NETWORK=0 python scripts/eval_testset.py --testset tests/fixtures/retired_sealed/sealed_20261008b --out <외부출력폴더>
LV_ALLOW_NETWORK=0 python scripts/eval_testset.py --testset tests/fixtures/retired_sealed/sealed_20261009 --out <외부출력폴더>
LV_ALLOW_NETWORK=0 python scripts/eval_testset.py --testset tests/fixtures/retired_sealed/sealed_20261010 --out <외부출력폴더>
```

표의 원값은 scorecard와 같은 공개 채점 API를 실행한 평가측 summary JSON이다. 각 세트의 실제 runtime/settings·환경은 실행 때 함께 기록한다. 위 CLI 경로와 요약 API 경로의 조건을 맞추고, `--out`은 세트마다 다른 폴더를 사용하여 덮어쓰지 않는다.

| 세트 | 문서/결함 | 종합 | 가중 재현율 | 오탐/A등급 | 방어 |
|---|---|---|---|---|---|
| dev | 6/56 | 81.7 | 0.817 | 0/0 | 성공 |
| holdout | 6/54 | 79.2 | 0.792 | 0/0 | 성공 |
| 은퇴20261008 | 8/46 | 19.0 | 0.190 | 0/0 | 성공 |
| 은퇴20261008b | 8/54 | 29.6 | 0.296 | 0/0 | 성공 |
| 은퇴20261009 | 8/58 | 36.2 | 0.362 | 0/0 | 성공 |
| 은퇴20261010 | 8/53 | 15.2 | 0.302 | 3/3 | 성공 |

6세트 소요72.204731초, 그중 은퇴49.098860초. 전체CI/전체pytest 실행이 아니다. 기존CI는 dev/holdout과 관련 전체시험을 이미 포함하고, 새 제출표만으로 은퇴4세트 CI job을 추가하지 않는다. 따라서 이번에는 기존CI 상한(점수15분/각DB30분)을 변경하지 않으며 새시간/전체검증 중복 실행 의무를 만들지 않는다. 경로별 새 시험 수·실행기 부하까지 고려한 미래CI 소요 보장은 아니고 제출 때 실제 시간을 함께 확인한다.

기준 결과는 SHA·환경·scorer/입력/명세 지문이 같을 때 재사용한다. 같은후보SHA CI의dev/holdout은 인용 가능하다. 구현 측은 해당 표와 출처를 제출하고 실제 비교가 없으면 미측정으로 남긴다. 새 조건으로 비공개 세트 접근권을 주거나 원래 수용 기준을 낮추지 않는다.

## 은퇴 중점6유형: 전달받은 측정과 평가측 재실행

claude-code의10/16 보고는 main b68/Python3.11/오프라인/모델0·결함211의 **타 세션 측정**으로 먼저 접수했다. 아래는 별도로 실행한 **Codex 평가측**의 원점수다. 환경·반올림 정밀도 차이를 구분하며 전달값을 평가측 결과로 둔갑시키지 않는다.

| 유형 | 전달 재현율 | 평가측 획득점수/항목 | 평가측 재현율 |
|---|---|---|---|
| EVI-INCONS | 0.10 | 2/21 | 0.095238 |
| SRC-UNV | 0.00 | 0/11 | 0 |
| EVI-NUM | 0.30 | 4.25/14 | 0.303571 |
| EVI-FORM | 0.07 | 0.75/10 | 0.075000 |
| EVI-DATE | 0.50 | 7/14 | 0.500000 |
| EVI-COPY | 0.00 | 0/6 | 0 |

총76항목/점수14/미획득점수62로 집계가 일치한다. EVI-FORM의0.07과0.075는 표시 정밀도를 구분한다. 원점수는 기존 scorer의1/0.5/0.25/0 부분점수를 포함하므로 이 값은 이진 탐지율이 아니다. 은퇴세트는 약점 진단용 개발 자료이며 처음 보는 문서 성능이나 새`check/`의 기준값이 아니다.

OVR0/15·EVI-OVR0/12·EVI-LOGIC0/10도 이번 오프라인에서는0이다. 전달문의 ‘모델이 필요한 유형일 수 있음’은 원인 가설로만 보존한다. 현 제품에는 결정론 OVR 경로도 있으므로 모델 부재만으로 미탐 원인을 확정하지 않는다.

원값·입력지문·환경·목표의 기계 기록은 [development_targets_2026-10-16.json](../../scorecards/development_targets_2026-10-16.json). 원본stdout/JUnit과 재현 계측 스크립트는 평가측 외부artifact에 보존한다. 공개 전달문에는 비공개 원문·정답·실제 사용자 식별자를 붙이지 않는다. 이번 분석으로 제품 기능 수용·새버전·배포·전체TK종결은0건이다.
