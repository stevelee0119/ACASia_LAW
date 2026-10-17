# 온라인 전체 측정 실행 계획 (평가 측, 2026-10-17)

사용자 결정(2026-10-17): "온라인으로 데이터베이스, Drive 등을 모두 점검해야 정확한 성능 비교가 가능". 키를 넣은 **새 평가 세션**이 이 문서대로 실행한다. 실행 위치는 평가 환경이다. 운영 서버(Render)는 쓰지 않는다. 봉인 자료가 운영 DB에 남고, 판 비교도 할 수 없기 때문이다.

## 1. 대상 세트 (모두 저장소 밖, 평가 측 열람 금지·집계만)
| 세트 | 지문 (코드포인트 정렬) | zip SHA-256 | 채점 |
|---|---|---|---|
| 고정 벤치 2판 `fixed_bench_20261017` | `c078b250e6e61e9f` (Windows 구식 `8a07f5b6ad16e0dc`) | `ee35ad4a…0e9906` | `scripts/fixed_benchmark.py` 경로(오프라인과 같은 채점기) |
| Drive 대조 세트 `ragbench_20261017` | `5a2e489099b8a751` | `53b4d337…e06304` | 묶음마다 결과 JSON을 `scripts/score_report.py --spec <setNN/spec.json>`로 채점 |

- 사용자가 두 zip의 Drive 링크를 준다. 받은 zip은 해시와 지문을 대조한 뒤 쓴다.
- ragbench는 `drive_refs/`만 측정 전용 Drive 폴더(묶음별 하위 폴더)에 있다. 서면과 `spec.json`은 Drive에 올리지 않는다.

## 2. 환경 (사용자 설정, 새 세션 시작 전)
- **AI:** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`.
- **공식 DB:** `LV_LAW_GO_KR_OC`.
- **학술(선택):** `LV_KCI_KEY`, `LV_SEMANTIC_SCHOLAR_KEY`, `LV_CROSSREF_MAILTO`.
- **Drive:** `LV_DRIVE_API_KEY` 또는 `LV_DRIVE_SERVICE_ACCOUNT_FILE`, `LV_RAG_DRIVE_FOLDER_ID`(측정 전용 폴더).
- **허용 도메인:**
  - AI: `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com`
  - 공식 DB: `www.law.go.kr`, `open.law.go.kr`
  - Drive: `www.googleapis.com`
  - 학술(선택): `www.kci.go.kr`, `api.semanticscholar.org`, `api.crossref.org`
- **실행 시 고정값:**
  - `LV_ALLOW_NETWORK=1`.
  - 2판 측정에서는 `LV_RAG_DRIVE_FOLDER_ID`를 비운다(참고자료 없는 세트라 Drive를 쓰지 않는다).
  - 예산 상한 `LV_MONTHLY_BUDGET_USD`는 시험 실행 5, 본 측정은 사용자 승인값(USD40 이하)으로 둔다.
- **키 확인:** 키 값을 출력하거나 기록하지 않는다. 확인은 변수가 비어 있지 않은지(존재 여부)만 본다.

## 3. 순서
1. **환경 확인:** 각 도메인 접속(키 없이 연결만)과 변수 존재 여부를 본다. 실패하면 막힌 호스트·변수 이름을 사용자에게 알리고 멈춘다.
2. **시험 실행 (상한 $5):** 운영 `b68cfee`로 2판 set01 1회, ragbench set01 1회를 돌린다.
   - 프로그램 호출 원장(LLM ledger)으로 문서당 추정 비용·시간·호출 수·실패/재시도 수를 잰다.
   - 금액은 `config/pricing.json` 기준 추정치로 표시한다. 실제 청구는 공급자 콘솔 확인이 필요하다고 적는다.
3. **추산 보고:** 문서당 비용 × 문서 수(2판 42, ragbench 10) × 지점 수 × 2회를 계산한다. 지점 안별(최소: 운영·후보 / 권장: 0.10.0·0.12.0·운영·후보 / 전체 7지점) 합계를 보고하고 승인을 받는다.
4. **본 측정:** 승인된 지점마다 clean checkout(오프라인과 같은 worktree 방식, 미커밋 변경 0)에서 2회 반복한다.
   - 2판은 `fixed_benchmark.py`(저장소 밖 실행기, `--note "온라인"`)로 잰다.
   - ragbench는 묶음마다 `eval_testset.py --save-result`로 결과 JSON을 만들고 `score_report.py`로 채점한다.
5. **기록:**
   - `fixed_benchmark_log.jsonl`에 `role`·`note`로 '온라인'을 표기한다(오프라인 계열과 섞지 않음).
   - ragbench는 `FIXED_BENCHMARK.md` 10절에 집계표를 둔다: 양성 탐지율 = 통과 양성/48, 대조 오탐 = 실패 대조/40, 대조군 묶음 오탐.
   - 비용·시간·호출 실패는 함께 적는다.
   - DAILY_TREND와 HISTORY를 갱신한다.
6. **정리:** 세트 사본, `.sealed_out/`, 결과 JSON, 호출 원장 DB(요청 내용 포함 가능)를 지운다. 측정 전용 Drive 폴더는 사용자가 다음 측정까지 그대로 둔다.

## 4. 읽는 법
- **반복 변동:** 같은 조건 2회의 차이 안에 드는 판 사이 차이는 판정하지 않는다(모델 응답 변동).
- **비교 원칙:**
  - 온라인과 오프라인 점수는 다른 계열이다. 오프라인 대비 증가분은 'DB·AI·Drive 기여'로만 적는다.
  - 판 사이 비교는 같은 세트·같은 환경·같은 키 구성일 때만 한다.
- **오염 방지:** 문서별·항목별·유형별 결과는 기록하지 않는다. 결과로 구현 티켓을 만들지 않는다(FIXED_BENCHMARK 4절).

## 5. 실행 기록 — 환경 확인·시험 실행 (2026-10-17, 평가 측 재실행)
사용자 지시: 환경 확인과 시험 실행(상한 $5)까지만. Anthropic 키는 실행 때 `LV_ANTHROPIC_API_KEY`를 `ANTHROPIC_API_KEY`로 넘겼다. 키 값은 출력·기록하지 않았다.

### 5.1 세트 대조
- 2판 zip SHA-256 `ee35ad4a…0e9906` 일치, 지문 `c078b250e6e61e9f`(코드포인트 정렬) 일치, 묶음 6.
- ragbench zip SHA-256 `53b4d337…e06304` 일치, 작성 프롬프트 점검 스크립트로 지문 `5a2e489099b8a751`·오류 0·경고 0.

### 5.2 환경 확인
| 구분 | 결과 |
|---|---|
| AI 3종 | 도메인 접속 정상. 무료 모델 목록 조회로 키 3종 모두 인증 200 |
| 공식 DB | `open.law.go.kr` 정상. `www.law.go.kr`는 간헐적 연결 리셋(10회 중 1회 실패), `LV_LAW_GO_KR_OC` 조회 응답 정상 |
| 학술(선택) | `www.kci.go.kr`·`api.semanticscholar.org`·`api.crossref.org` 모두 프록시 403(허용 목록 밖). 키 변수 3개도 비어 있음 |
| **Drive** | **막힘.** ① `LV_DRIVE_API_KEY` 값이 `GEMINI_API_KEY`와 같고, Drive API가 401 "API keys are not supported by this API. Expected OAuth2 access token…"으로 거절. ② `LV_RAG_DRIVE_FOLDER_ID`가 폴더 ID가 아니라 폴더 주소 전체여서 제품의 ID 형식 검사(`valid_id`)에 걸린다 |

- **Drive 재확인 (같은 날, 사용자 수정 뒤):** 키 형식 정상(Gemini 키와 다름), 폴더 변수는 ID 형식. 폴더 조회 200.
  - `ragbench/set01~05` 하위 폴더마다 파일 2개, zip의 `drive_refs/`와 MD5가 모두 일치한다(내용 열람 없음).
  - 다만 지정 폴더는 측정 전용이 아니다. `ragbench` 말고 일반 참고자료 하위 폴더 5개와 낱개 문서 1개가 함께 있다. 계획 1절('측정 전용 폴더')에 맞추려면 `ragbench` 하위 폴더 ID를 써야 한다(사용자 결정).
  - API 키로 읽힌다는 것은 지정 폴더 전체가 링크 공개 상태라는 뜻이다.
- 계획 3절 1항에 따라 Drive가 필요한 ragbench 시험 실행은 하지 않았다. 2판은 계획 2절대로 Drive를 비우고 돌리므로 시험 실행을 했다.

### 5.3 시험 실행 — 2판 set01 1회
- 조건: 운영 `b68cfee` clean worktree(미커밋 변경 0), `LV_ALLOW_NETWORK=1`, `LV_RAG_DRIVE_FOLDER_ID` 비움, `LV_MONTHLY_BUDGET_USD=5`, 새 원장 DB. Linux, Python 3.11.17, pdfplumber 0.11.10, pypdf 6.21.0, tesseract 5.3.4(kor). 저장소 밖 실행기가 checkout의 `eval_testset.run_pipeline`·`score`를 불렀다(`scorecard.build`는 네트워크를 강제로 끄므로 온라인에 쓸 수 없다). 환경 지문 complete.
- 문서 7, 실행 452초(문서당 65초).
- 호출(원장 42건, 모두 SETTLED): 공급자마다 14건(문서당 2건), 성공 42·실패 0·재시도 소진 0.

  | 공급자 | 입력·출력 토큰 | 원장 추정 | 비고 |
  |---|---|---|---|
  | anthropic | 30,818 · 23,487 | $0.4448 | REPORTED |
  | openai | 18,865 · 10,140 | $0.0070 | REPORTED(모델 단가표 `gpt-6-luna` 적용) |
  | gemini | 19,722 · 5,420 | $2.8672 | ESTIMATED: 어댑터가 사고 토큰을 빼므로 예약액 전액을 과금으로 잡는다. 토큰 단가로는 $0.079(사고 토큰 제외) |
  | 합계 | | **$3.3189** (문서당 $0.474) | 토큰 단가 기준 약 $0.53(문서당 약 $0.076) |
- 금액은 `config/pricing.json` 기준 추정치다. 실제 청구는 공급자 콘솔 확인이 필요하다.
- 점수는 시험 실행용 한 묶음 값이라 기록·비교하지 않는다(오프라인 계열과 다른 조건).
- 측정하지 못한 것: ragbench 시험 실행(Drive 인증), 학술 DB 경로, 공식 DB 호출 수·실패 수(원장에 없음).

### 5.4 추산 (2판만, 42문서 × 2회 × 지점 수)
| 지점 안 | 원장 기준(예산 상한이 보는 값) | 토큰 단가 기준 | 시간(순차) |
|---|---|---|---|
| 최소 2지점 | $79.6 | 약 $12.8 | 약 3.0시간 |
| 권장 4지점 | $159.3 | 약 $25.6 | 약 6.0시간 |
| 전체 7지점 | $278.8 | 약 $44.7 | 약 10.5시간 |

- 원장은 Gemini 호출을 예약액 전액으로 잡는다. 그래서 `LV_MONTHLY_BUDGET_USD`=40이면 1지점 2회(원장 $39.8)도 끝까지 못 돌 수 있다. 본 측정 상한은 원장 기준으로 정해야 한다(사용자 결정).
- ragbench 추산은 시험 실행을 못 해 없다. Drive 대조 호출(주장 단위, `LV_RAG_CLAIM_BUDGET_USD` 기본 1.00)이 더해진다.
- 시험 실행 뒤 세트 사본·`.sealed_out/`·결과 JSON·원장 DB를 지웠다.
