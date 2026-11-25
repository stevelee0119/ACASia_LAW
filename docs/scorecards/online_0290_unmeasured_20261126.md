# 0.29.0 온라인 실측 — 미측정 항목의 원인과 해소 조치 (2026-11-26 KST)

사용자 지시(2026-11-26 "측정하지 못한 항목이 있다면 그 원인을 정리해서 보고. 필요하면 환경변수 등을 수정·정리하여 측정하지 못한 항목이 없도록")에 따른 정리다. 대상 배포는 운영 `main` `9c63772f`(`0.29.0`)이다.

## 1. 결론 요약

| 구분 | 건수 | 항목 |
|---|---|---|
| **이번에 추가로 측정 완료** | 4 | OCR 폴백(정상·저품질), U5 AI 작성 판별 반복 일치율, 상용 임베딩 캐시 적중률, Legal NLI 공식 전문 확보·Stage 기록 |
| **앞선 보고에서 정정(실측 완료)** | 1 | Dense·Reranker 실호출(`TK-228`) |
| **환경 설정으로 해소 가능 — 사용자 조치 필요** | 2 | `LV_SEMANTIC_SCHOLAR_KEY` 미설정, 카세트 `RECORD`/`REPLAY` 운영 경로 |
| **제품에서 제거되어 측정 대상 아님** | 1 | 로컬 모델(`TK-229`) |
| **자원·설계 부재로 측정 불가 — 사용자 결정 필요** | 4 | 격리 봉인 세트, 실무 법률 정확도, 검색/주장 타당성, 검토 효율 |
| **관측 필드 부재로 측정 불가(티켓 발행)** | 1 | 임베딩·재순위 지연(ms) |
| **조건 비교 측정 추가 완료** | 1 | 고정 dev·holdout 오프라인 vs 네트워크 켬 |

환경변수만으로 해소되는 항목은 **`LV_SEMANTIC_SCHOLAR_KEY` 1건**이며, 그 값은 외부 발급 키라 평가 측이 만들 수 없다. 나머지 미측정은 환경변수 문제가 아니라 **자원 부재(격리 VM·로컬 추론 서버)**, **측정 설계 부재(독립 변호사 라벨·검토시간 연구)**, **제품의 관측 필드 부재**가 원인이다.

## 2. 항목별 원인과 조치

### 2.1 이번에 측정을 완료한 항목

| 항목 | 종전 상태 | 이번 측정 | 원인·조치 |
|---|---|---|---|
| OCR 폴백(정상 스캔) | `0.26.0` 이후 미측정 | `tesseract 5.5.0` 0.89, 폴백 시도 0·채택 0, `OCR_EXTRACTED`, 청구 4건 — **충족** | 고정 합성 입력(`clean_scanned.pdf` `4b062f82…`)이 저장소에 있어 바로 측정 가능했다. 종전 미측정은 자료 부족이 아니라 **실행 누락**이었다. |
| OCR 폴백(저품질 스캔) | 같음 | 1차 0.483 → `rapidocr 3.10.0` 채택 0.537, 최종 `UNVERIFIED`/`OCR_LOW_CONFIDENCE` — **미충족** | 같음. 결과는 미해소이며 `0.26.0`(선택 신뢰도 0.582) 대비 후퇴 관측 → [TK-239](../handoff/tickets/TK-239.md) 발행 |
| U5 AI 작성 판별 반복 일치율 | 미집계 | 3회 모두 `AI_PARTIAL_GENERATION`, **일치율 1.0**, 유보 0, 기대 판정 비율 1.0 (openai 0.78~0.82 / gemini 0.65~0.75) | `scripts/ai_repeat_summary.py`에 3회 보고서를 넣으면 되는데 **집계를 돌리지 않았다.** 이번에 돌려 해소했다. |
| 상용 임베딩 캐시 적중률 | 미측정 | `cache_hits 9 / cache_misses 0`(적중률 **100%**), 신규 임베딩 요청 1건 | 문서 단위 `search_diagnostics.retrieval`에 이미 있었다. **보고서의 다른 위치(run 매니페스트)만 보고 미측정으로 처리한 것이 원인**이다. |
| Legal NLI Stage 2 품질 | `case9`에서 `full_text_missing 1`·`INSUFFICIENT 3` | `2011모1839` 전문 **30,211자 확보**. 정확 인용 → `SUPPORTED`·`VERIFIED`·finding 0, 반전 인용 → `CONTRADICTED`·A등급 양성(변형 지점 지적), **상대방 전언 대조군 → A등급 오탐 1건** | `case9`가 인용한 판례(`2022다29841`)가 공개 DB 조회 범위에 없어 NLI가 입력 부족으로 돌지 못한 것이다. **전문이 확보되는 다른 사건번호로 전용 입력을 만들면 측정 가능**하며, 이번에 그렇게 해소했다. 결과로 새 결함 2건을 발견했다([TK-240](../handoff/tickets/TK-240.md)·[TK-241](../handoff/tickets/TK-241.md)). |

### 2.2 정정 — 실측 완료였던 항목

**Dense·Reranker 실호출(`TK-228`)**: 문서 단위 기록에 `HYBRID_RERANK`·`embedding 1/1`·`reranker 1/1`이 3회 모두 남아 있었다. 매니페스트 `actual_calls=0`을 보고 미측정으로 분류한 것이 잘못이다. 원인은 `packages/verification_engine/environment.py:230,241`의 상수 하드코딩이며 [TK-238](../handoff/tickets/TK-238.md)로 발행했다.

### 2.3 환경 설정으로 해소 가능 — 사용자 조치가 필요한 항목

| 항목 | 원인 | 필요한 조치 | 평가 측이 할 수 없는 이유 |
|---|---|---|---|
| 학술 Source `semantic_scholar` | `LV_SEMANTIC_SCHOLAR_KEY`가 **빈 값**(U2 로그 `⚪ 없음`). 키 없이 공용 러너 IP로 호출해 `RATE_LIMITED`로 떨어진다. 다른 학술 Source(`kci`·`openalex`·`crossref`)는 정상이라 학술 성공률이 3/4에 머문다. | Semantic Scholar API 키를 발급받아 저장소 Secret `LV_SEMANTIC_SCHOLAR_KEY`에 등록 | 외부 서비스 발급 키이고 Secret 등록은 저장소 관리자 권한이다 |
| Source 카세트 `RECORD`/`REPLAY` 운영 경로 | 운영 기본값이 `LIVE`(`source_cassette.mode=LIVE`, `evaluation_only=true`). 모드 변경(`LV_SOURCE_REPLAY_MODE`)은 **운영 서비스 사용자에게 영향**을 주므로 평가 측이 임의로 바꾸지 않는다(`recheck_procedure` 4항). | 별도 시험 배포를 두거나 명시된 운영 변경 창을 지정 | 운영 환경변수 변경은 사용자 승인 사항이다. 컴포넌트 수준 `RECORD`/`REPLAY`는 `0.24.0`에서 이미 확인됐다(HTTP 200·본문 해시 일치·미스 차단). |

### 2.4 제품에서 제거되어 측정 대상이 아닌 항목

**로컬 모델(`TK-229`)**: `0.26.0`에서 `NOT_MEASURED`로 남았으나, `TK-232`(0.27.0 병합)가 미운영 로컬 공급자 코드를 제거했다. 운영 진단은 `local_llm.status=REMOVED_NOT_OPERATIONAL`, `provider_count 0`, `operational false`다. 즉 **측정할 기능이 더 이상 제품에 없다.** `NOT_MEASURED`(측정 못 함)가 아니라 **범위 밖(기능 제거)** 으로 분류해야 한다. `TK-229`의 존치 여부는 사용자 결정이 필요하다. 로컬 추론 서버를 다시 도입할 계획이 없다면 `TK-229`를 닫는 것이 기록상 정확하다.

### 2.5 자원·설계 부재로 측정 불가 — 사용자 결정이 필요한 항목

| 항목 | 원인 | 해소에 필요한 것 |
|---|---|---|
| 격리 봉인 세트 | 봉인 문서·정답은 저장소 밖에 있고, 격리 실행용 원격 평가 VM이 없다. 평가 세션은 봉인 문서를 열람·복사할 수 없으므로 이 컨테이너에서 대체할 수 없다. | 격리 실행 환경 제공, 또는 저장소를 연결하지 않은 격리 세션의 출제·채점 재개 |
| 실무 법률 정확도 | 독립 변호사 라벨과 제품 예측의 대조 설계가 없다(`scripts/scorecard.py`의 `measurement_status.legal_accuracy`에 `NOT_MEASURED` 사유로 명시돼 있다). | 라벨 작성 주체·표본·채점 규칙 승인 |
| 검색/주장 타당성 | 공식 출처·근거 구간(span) 라벨이 없다(`retrieval_quality`). | 라벨 설계 승인 |
| 검토 효율 | 독립 검토시간 연구가 없다(`practice_utility`). | 연구 설계·대상자 승인 |

이 네 항목은 `EVALUATION_V2`가 요구하는 대로 **합격으로 간주하지 않고** 미측정으로 명시한다.

### 2.6 관측 필드 부재로 측정 불가 — 티켓으로 처리

**임베딩·재순위 지연(ms)**: `search_diagnostics.retrieval`에 요청·성공·캐시 수는 있으나 **소요 시간이 없다**(`document_select 333ms`·`claim_search 5,123ms`는 있고 `retrieval`은 `null`). 제품이 기록하지 않으므로 평가 측이 잴 수 없다. [TK-238](../handoff/tickets/TK-238.md) 3항에 지연 기록 요구를 포함했다(같은 성격의 관측 결함이므로 같은 회차에서 처리, 2026-11-13 사용자 지시).

## 3. 환경 정리 내역 (평가 측이 실제로 바꾼 것)

| 변경 | 내용 | 사유 |
|---|---|---|
| 네트워크 허용목록 | `verify-acas-law.onrender.com`·`www.law.go.kr`·`www.data.go.kr` 추가(사용자 승인) | 허용목록에 와일드카드(`*.verify-acas-law.onrender.com`)만 있어 apex 도메인이 403으로 막혀 있었다 |
| 측정 조건 명시 | 온라인 측정 절차에 `external_ai_policy=MASKED`를 필수 조건으로 기재 | `POST /api/projects`의 기본값이 `LOCAL_ONLY`이고 운영에 로컬 공급자가 0개여서, 지정하지 않으면 모델 호출이 0건이 된다 |
| 평가 측 의존성 | 평가 컨테이너에 `httpx`·`filelock`·`sqlalchemy` 설치 | 저장소 모듈을 직접 불러 입력 사전 검증(EVI-COPY·FactTriple)을 돌리기 위함. 제품 코드는 고치지 않았다 |

`www.law.go.kr`는 허용목록 추가 후에도 평가 컨테이너에서 **원격 TLS 연결 초기화**(정책 거부 아님)로 직접 호출이 되지 않는다. 공식 DB 직접 조회가 필요한 측정은 이그레스가 열린 러너에서 수행했다.

## 4. 이번 측정으로 새로 발행한 티켓

| 티켓 | 등급 | 내용 |
|---|---|---|
| [TK-239](../handoff/tickets/TK-239.md) | `P1` | 저품질 스캔 OCR 복구 미달·폴백 신뢰도 후퇴(`TK-231` 축① 미해소) |
| [TK-240](../handoff/tickets/TK-240.md) | `P1` | 상대방 전언 인용에 `CASE_QUOTE_MISMATCH` **A등급 확정 경고**(확인 오탐) |
| [TK-241](../handoff/tickets/TK-241.md) | `P1` | 참고자료 대조 안내가 `FACT_CONTRADICTION` 확정 경고로 자료마다 **중복 노출**(서면 1장에 19건) |

앞서 발행한 `TK-235`~`TK-238`과 합해 열린 티켓은 **7건**이다.

## 5. 조건 비교 측정 결과 요약

고정 dev·holdout을 같은 SHA·같은 채점기·같은 OCR에서 네트워크만 바꿔 쟀다: dev **89.7 → 98.2**, holdout **87.5 → 95.4**, 오탐은 양 조건 모두 전부 0. 상세·해석·한계는 [online_0290_offline_online_compare_20261126.md](online_0290_offline_online_compare_20261126.md)에 있다.

Agent: evaluator
