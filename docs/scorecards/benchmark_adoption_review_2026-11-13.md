# 법률 벤치마크 도입안 독립 검토 (2026-11-13, 평가 측)

- 요청: 사용자 첨부 지시문 「ACASia_LAW 상업적 이용 가능 법률 벤치마크 도입안」 평가.
  - 사용자 원문: "첨부한 지시문에 따라 ACASia_LAW의 법률 벤치마크 도입안을 독립적으로 평가해줘."
- 검토 SHA:
  - Steve_ACASiaLAW `b94750ba3a236aad8e1dcbe5b9137d96bd574d96`(원격 확인, #274·#275 병합 뒤)
  - main `5b878a1`(0.19.0)
  - 지시문 작성 시점 SHA `bf93d3c`는 이 검토 SHA보다 앞선다.
  - 검토 중 열린 PR: #271(head `87a5563`, 보완 3 반영 추정 — 별도 판정), #276(미확인 — 별도 판정).
- 범위: 도입안 평가와 실행 계획 확정. 제품 구현·CI·기준선 변경·병합·배포는 하지 않았다.
  - 사전 검증용 사본(저장소 밖)에서만 탐침과 구현 시험을 했다.
- 사용자 결정 반영:
  - KBL 미사용(11-13 "KBL은 사용하지 않는 것으로", 계획 문서 6.10).
  - ACASia_LAW는 상업적 이익 목적으로 쓰지 않을 예정이고, 유료 법률 업무에도 쓰지 않는다(11-13).
  - 다만 사용자가 '향후 확장 가능성'을 이유로 KBL을 제외했다. 그래서 이 검토는 **상업적 이용까지 허용되는 근거**를 기준으로 판정한다(지시문 목표 1).
- 이 문서는 법률 자문이 아니다. 라이선스 판단은 공식 원문 문구와 그 해석이며, 최종 판단은 사용자 또는 자문 변호사가 한다.

## 1. 핵심 판정

**전체: 일부 채택.**
- ACASia_LAW의 핵심 기능(한국어 서면의 판례·법령 인용 실재·인용문·시점·주장 근거 검증)은 공개 영어 벤치마크로 측정할 수 없다.
  - 재현: 영어 판례·법령 인용 문장 3건을 제품 인용 추출기에 넣으면 추출 0건이다(한국어 대조 문장은 추출됨, 6절 V4).
- 공개 영어 벤치마크는 **구성요소 시험**으로만 의미가 있다.
- 지금 근거가 서는 것은 ContractNLI 하나다. 제품의 '참고자료 대조 판정'(지지·모순·맥락·근거 부족)과 과제 구조가 같다.
- 한국법 인용 진위의 측정은 v1.0 단계의 독립 법률가 라벨(TK-166)이 여전히 유일한 경로다.

| 후보 | 판정 | 핵심 이유 |
|---|---|---|
| ContractNLI | **조건부 채택**(구성요소 시험) | CC BY 4.0(공식 사이트 원문). 제품의 참고자료 대조 판정과 과제가 대응한다. 조건: 구성요소 진입점(BM-2)·3분류 채점기(BM-1) 구현, 배포본 고정(SHA-256), 모델 호출 비용 승인. 결과는 '영문 계약 NLI 구성요소 성적'으로만 표기한다 |
| LegalBench-RAG | **보류** | 코드 MIT, 원천 4종도 허용 근거 확인. 그러나 배포 데이터(LLM 생성 질의)의 자체 이용조건 표기가 없고, 제품 검색기는 근거 문자 구간을 내지 않아 핵심 지표(구간 P/R/F1)를 잴 수 없다(UNSUPPORTED) |
| CUAD v1 | **보류(참고용)** | CC BY 4.0(Zenodo 레코드 `license: cc-by-4.0`). 계약 조항 추출은 제품 기능이 아니다 |
| MAUD | **보류(참고용)** | CC BY 4.0(Hugging Face README `license: cc-by-4.0`). 제품 기능 불일치는 CUAD와 같다 |
| LegalBench | **보류**(과제 허용 목록만 작성) | 과제별 라이선스. hearsay·overruling은 CC BY 4.0 확인, cuad 계열 과제 README에는 라이선스 문구 없음. 제품에 영문 법률 질의응답 기능이 없어 모델 단독 시험만 가능하며, 그것은 제품 성적이 아니다 |
| Harvey LAB | **보류** | 루트 LICENSE MIT 확인. 과제·자료별 이용조건은 미확인(전체 트리 미확인). 영문 에이전트 과제는 제품 기능과 맞지 않는다 |
| KBL | **제외** | 사용자 결정(11-13). CC BY-NC 4.0. 평가 자산에 남은 KBL 경로는 평가 측이 정리한다(5절 P0) |

## 2. 라이선스·데이터 계보 표

- 판정 수준: '허용 근거 확인'(공식 원문에 상업 이용을 막지 않는 라이선스가 명시) / '조건부'(근거는 있으나 원천·파생 자료 확인 필요) / '근거 미확인'.
- 모든 CC BY 4.0 자료의 공통 의무: 저작자 표시, 라이선스 고지·링크, 변경 표시(legalcode 3(a)). 보증·후원 암시 금지(2(a)(6)).
- 파일 SHA-256은 이번에 내려받지 않아 계산하지 않았다(CUAD만 공식 md5). **배포본 고정 단계(P1)에서 평가 측이 계산해 manifest에 적는다.**

| asset_id | 제공자 | 원본 URL | revision/release | 파일 해시 | 라이선스 근거 위치 | 원천·예외 | 이용 목적별(내부 회귀·외부 API 전송·집계 공개·재배포·번역/학습) | 표시 의무 | 미해결 쟁점 | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|
| contractnli-data | Stanford NLP | https://stanfordnlp.github.io/contract-nli/ | 미고정 | 미계산 | 사이트 'License' 절: "Our dataset is released under CC BY 4.0" | 문서 출처: 검색 PDF·SEC 공시(사이트 document_type 설명) | CC BY 4.0은 상업 포함 이용·변형을 허용. 외부 API 전송·집계 공개·번역 모두 표시 조건 아래 가능. 재배포는 가능하나 평가 오염 방지를 위해 저장소에 넣지 않는다 | 저자·라이선스·변경 표시 | 원문 문서(제3자 계약서) 자체의 권리는 라이선서가 가진 범위만큼만 허락됨(legalcode 'Considerations for the public') | 허용 근거 확인 |
| cuad-v1 | The Atticus Project | https://zenodo.org/records/4595826 | Zenodo v1(2021-03-11), DOI 10.5281/zenodo.4595826 | CUAD_v1.zip md5 c38f490a984420b8a62600db401fafd5(공식) | Zenodo API 레코드 `"license": {"id": "cc-by-4.0"}` | 510 계약(SEC EDGAR) | 위와 같음 | 같음 | SHA-256 미계산 | 허용 근거 확인 |
| maud | The Atticus Project | https://huggingface.co/datasets/theatticusproject/maud | main(미고정) | 미계산 | README 머리말 `license: cc-by-4.0` | 합병계약 | 위와 같음 | 같음 | revision 고정 필요. 논문 부록 A.1은 이번에 대조하지 않음 | 허용 근거 확인(revision 고정 전) |
| legalbench-code·과제 | HazyResearch | https://github.com/HazyResearch/legalbench | 미고정 | 미계산 | README: "We ask that you follow the license of the dataset creator", 과제 페이지 참조 | 과제마다 원천 다름 | 과제별 | 과제별 | Hugging Face `nguha/legalbench` 카드의 단일 `license: cc-by-4.0` 표기가 GitHub README(과제별)와 충돌 → 보수적으로 과제 README를 기준으로 삼는다 | 조건부(과제 허용 목록 필요) |
| legalbench/hearsay | 같음 | tasks/hearsay/README.md | 미고정 | 미계산 | "License: CC By 4.0"(직접 작성 자료) | 저자 직접 작성 | 허용 | 같음 | — | 허용 근거 확인 |
| legalbench/overruling | 같음 | tasks/overruling/README.md | 미고정 | 미계산 | "License: CC By 4.0" | CaseHOLD(Zheng et al. 2021) 계열 | 허용(과제 README 기준) | 같음 | 원천 CaseHOLD 자료의 이용조건은 이번에 확인하지 않음 | 조건부 |
| legalbench/cuad_affiliate_license-licensee | 같음 | tasks/cuad_affiliate_license-licensee/README.md | 미고정 | 미계산 | README에 "Source: Atticus Project"만 있고 **라이선스 문구 없음** | CUAD(CC BY 4.0) | — | — | 지시문의 'CC BY 4.0 확인'은 이번 원문 확인과 다르다. 원천 CUAD는 CC BY 4.0이지만 과제 파생물의 표기는 미확인 | 근거 미확인 |
| legalbenchrag-code | ZeroEntropy | https://github.com/zeroentropy-ai/legalbenchrag | master(미고정) | 미계산 | LICENSE "The MIT License (MIT) Copyright (c) 2025 ZeroEntropy" | — | 코드 허용 | MIT 고지 | — | 허용 근거 확인(코드만) |
| legalbenchrag-data | ZeroEntropy(Dropbox 배포) | README의 Dropbox 링크 | 미고정 | 미계산 | README: "Please ensure you agree to the usage policies of ContractNLI, CUAD, MAUD, and PrivacyQA", "LLMs are used in the process of creating the LegalBench-RAG benchmark" | 원천 4종 + LLM 생성 질의 | 생성 질의·정답 묶음 자체의 라이선스 표기 없음 | — | 배포 데이터의 이용조건 미표기. 코드로 원천에서 재생성하면 원천 조건만 남는다(재생성 비용 별도) | 근거 미확인(배포본) / 조건부(재생성) |
| privacyqa | Ravichander 외 | https://github.com/AbhilashaRavichander/PrivacyQA_EMNLP | 미고정 | 미계산 | 저장소 LICENSE: MIT("Adding License (MIT)") | 앱 개인정보처리방침 원문 | 저장소 기준 허용 | MIT 고지 | 원문 정책 문서의 권리 범위는 미확인 | 조건부 |
| harvey-labs | Harvey AI | https://github.com/harveyai/harvey-labs | main(미고정) | 미계산 | 루트 LICENSE "MIT License Copyright (c) 2026 Harvey AI" | 과제·자료 개별 | 루트 MIT만 확인 | MIT 고지 | 하위 자료·과제별 다른 조건 여부 미확인(전체 트리 미확인) | 근거 미확인(자료) |
| kbl | LBox | https://huggingface.co/datasets/lbox/kbl | 695653ba… | (#272 고정) | README `license: cc-by-nc-4.0` | — | — | — | 사용자 결정으로 제외 | 제외 |

- 별도 허락 권고:
  - 이번 채택 대상(ContractNLI)에는 별도 허락이 **법률상 필요하다는 결론이 아니다.** CC BY 4.0이 상업 이용을 허용한다.
  - 다만 원문 계약서는 제3자 문서다. 저장소·컨테이너에 넣지 않고 평가 시 내려받는 운영 원칙은 오염 방지와 불확실성 감소를 위한 **운영 권고**다.
- 모델 학습:
  - CC BY 4.0은 변형·학습을 막지 않는다.
  - 그러나 평가 자료를 학습·규칙 작성에 쓰면 측정이 무효가 된다. **평가 자료는 학습에 쓰지 않는다**(평가 규약).

## 3. 평가 대응표

| 평가 층 | 후보·지표 | 제품 진입점(b94750b) | 입력 | 실제 출력 | 정답 | 주장 가능한 결론 | 미측정·과장 금지 |
|---|---|---|---|---|---|---|---|
| 근거 검색 | LegalBench-RAG 구간 P/R/F1 | `packages/rag_engine/relevance.py`(파일 선정 어휘 문턱), `library.py` 614행 `select` | Drive 참고자료 색인 | 선정 파일·발췌(문자 구간 없음) | 근거 문자 구간 | 없음 | 제품이 구간을 내지 않아 **UNSUPPORTED**. TK-159는 공식 원문 구간만 다루고 참고자료 검색은 다루지 않는다 |
| 주장–문서 관계 | ContractNLI 3분류 macro-F1·혼동행렬·근거 구간 F1 | `packages/rag_engine/review.py` 판정(지지·모순·맥락·근거 부족). 지금은 `review_document`(문서 전체 실행)에만 묶여 있어 단독 호출 불가 | 가설 1문장 + NDA 원문 | observations(relationship·source_quote) | Entailment/Contradiction/NotMentioned + 구간 | '참고자료 대조 판정 구성요소의 영문 계약 NLI 성적' | 한국법 성적 아님. NotMentioned를 '거짓·부존재'로 바꾸지 않음. 검색 단계(파일 선정)는 제외된 성적 |
| 계약 조항 추출·해석 | CUAD·MAUD 원 지표 | 해당 기능 없음 | — | — | — | 없음 | UNSUPPORTED. 모델 단독 점수로 채우지 않음 |
| 법률 규칙 적용 | LegalBench 허용 과제 | 해당 기능 없음(영문 법률 질의응답 없음) | — | — | — | 모델 단독이면 '모델 성적' | 제품 성적으로 표기 금지 |
| 한국법 인용 진위·왜곡 | 독립 법률가 라벨(TK-166) | 인용 추출 → `legal_engine/verifier.py` → `scripts/export_quality_predictions.py`(identity·quote 2차원) | 한국어 서면 | 판정·근거(TK-159)·3분류(TK-160) | 법률가 2인 판정 | 해당 라벨 집단의 정확도 | v1.0 단계까지 NOT_MEASURED. 시점(temporal)·법리 적용(application)은 exporter 미지원 |
| 실무 효용 | 검토 시간·중대 누락 | — | — | — | — | — | NOT_MEASURED |

**다섯 구분(지시문 4절)의 현재 대응**
1. identity: exporter identity 차원.
2. quote/context: exporter quote 차원. 문맥 왜곡은 TK-160 3분류(병합 전).
3. temporal/authority: verifier levels에는 있으나 exporter 차원이 없다(공백).
4. application: TK-160 claim_verdict(병합 전). 법률가 라벨이 없으면 NOT_MEASURED.
5. unknown/abstention: exporter ABSTAIN, TK-159 basis_status LOOKUP_FAILED.

## 4. 기술 검토 결과

| # | 위치(b94750b) | 관측(재현 여부) | 원인 | 영향 | 개선 | 담당 |
|---|---|---|---|---|---|---|
| T1 | 제품 인용 추출(`packages/legal_engine` extract_from_text) | **재현**: 영어 판례·법령 인용 문장 3건 추출 0, 한국어 대조 1건 추출 | 한국 인용 형식 전용 추출기 | 영어 공개 벤치마크로 종단간 측정 불가 | 종단간 대신 구성요소 시험으로 한정. 종단간 성적 표기 금지 | 평가 측(규약) |
| T2 | `packages/rag_engine/review.py` 257행 `review_document` | **재현**(코드 확인): 판정 요청 생성이 문서 실행 루프 안(442~448행)에 있고, 단독 진입점이 없다 | 구성요소 분리 부재 | 어댑터가 프롬프트·스키마·근거 검증을 복제해야 해 '어댑터에 판단 숨김' 위험 | BM-2: 요청 생성 단일화 + 단독 진입점 | 구현 측 |
| T3 | `packages/evaluation`(quality.py) | **재현**: 오류 유형 다중 라벨 지표만 있고 3분류 혼동행렬·근거 구간 지표가 없다 | 설계 범위 | ContractNLI 공식 지표 재현 불가 | BM-1: nli.py | 구현 측(packages/ 경로) |
| T4 | `packages/evaluation/quality.py` 77~110행 `_metrics` | **재현**(탐침 P1): 정답 UNVERIFIED + 예측 VERIFIED → false_verified 1, rate 0.5 | 정답 'UNVERIFIED/ABSTAIN'(법률가도 판단 유보)도 '정답이 VERIFIED 아님'으로 센다 | false VERIFIED 정의가 정답 유보 항목을 포함하는지 명시되지 않음 | 정의 명시: 정답 ABSTAIN은 분모·분자에서 따로 보고(라벨 확보 전에 정한다) | 평가 측(규약)+구현 측(코드, TK-166 단계) |
| T5 | `scripts/evaluation_dashboard.py` 41·46행 | 확인: 예측의 system_version이 성적표 SHA와 같아야 한다(법률가 라벨) | 동일 SHA 계약 | 공개 벤치마크 실행은 제품 SHA와 평가기 SHA가 다를 수 있다 | 구성요소 벤치마크 층은 `product_sha`·`evaluator_sha`를 분리해 기록하되, 기존 법률가 라벨 층의 동일 SHA 요구는 유지 | 평가 측 |
| T6 | `scripts/evaluate_kbl.py`, dashboard 13·52~60행, EVALUATION_V2 5절, score-gate.yml 67행(dashboard 실행) | 확인: KBL 채택 문구·채점 경로가 남아 있다 | #272 시점 결정 | 사용자 결정(KBL 미사용)과 불일치 | KBL 경로 제거 또는 '사용하지 않음' 표시(계획 문서 6.10) | 평가 측 |
| T7 | PredictionRecord(schemas.py 74~96행) | 확인: 실행 manifest 항목 중 prompt_hash·model/provider·benchmark_revision·corpus_hash·legal_as_of·network_mode·execution_status가 없다 | 설계 범위 | 버전 오귀속·캐시 누락 차단 불가 | 구성요소 벤치마크는 BM-1의 NLIPrediction(revision·execution_status)과 별도 실행 manifest(평가 측 스크립트)로 기록 | 평가 측 + BM-1 |
| T8 | 지시문 2절 'LegalBench 일부 CUAD 과제 CC BY 4.0 확인' | **불일치**: 해당 과제 README에 라이선스 문구 없음 | 원천 라이선스와 과제 표기 혼동 | 허용 목록 오류 위험 | 과제 README 원문 기준 허용 목록, 문구 없는 과제는 '근거 미확인' | 평가 측 |
| T9 | LegalBench Hugging Face 카드 | 단일 `cc-by-4.0` 표기가 GitHub README(과제별)와 충돌 | 배포처별 표기 차이 | 일괄 허용으로 오판 위험 | 과제 README를 기준으로 삼는다 | 평가 측 |

## 5. 단계별 도입 계획

| 단계 | 내용 | 담당 | 선행 | 산출·수용 기준 | 비용·시간 근거 |
|---|---|---|---|---|---|
| P0 | KBL 경로 정리(T6), EVALUATION_V2 5절 개정(공개 벤치마크 층 = '구성요소 벤치마크', KBL 제외 사유), 허용 목록 문서 | 평가 측(평가 PR, 보호 경로라 사용자 병합 승인) | 없음 | dashboard·CI 녹색, KBL 문자열 제거, 보호 시험 변경은 사용자께 먼저 보임 | 오프라인 |
| P1 | 자산 고정: ContractNLI 배포본 revision·SHA-256·라이선스 문구 사본(저장소 밖) | 평가 측 | 없음 | `docs/scorecards/benchmark_assets.json`(URL·revision·SHA-256·라이선스 근거 위치·고지 문구) | 내려받기 1회 |
| P2 | BM-1(채점기)·BM-2(구성요소 진입점) | 구현 측(아래 전달문) | 없음(P0과 병렬) | 사전 검증 시험 통과, 기존 참고자료 대조 동작 불변 | 오프라인 |
| P3 | ContractNLI 어댑터 `scripts/benchmarks/contractnli_adapter.py` | 평가 측 | P1·P2 | 입력 변환(가설→claim_text, NDA 전문→source R1), 정규화표(SUPPORTS→ENTAILMENT, CONTRADICTS→CONTRADICTION, CONTEXT·INSUFFICIENT·관측 없음→NOT_MENTIONED, MODEL_FAILED·NO_PROVIDER·REJECTED→실행 실패로 분모 유지), source_quote→원문 문자 구간, 실행 manifest. 정답을 읽어 출력을 고치지 않는다 | 오프라인(가짜 라우터 시험) |
| P4 | 시범 실행(dev 분할 일부) | 평가 측(사용자 비용 승인) | P3 | 호출 수·비용·지연·반복 변동성 실측 → 전체 실행 횟수·예산 결정 | **미정: 비용 근거 없음 → 시범 실행으로 정한다** |
| P5 | 공식 test 분할 실행·보고 | 평가 측 | P4 | macro-F1·혼동행렬·구간 F1·문서군 부트스트랩 구간·실행 실패율. 대시보드 별도 층 '구성요소 벤치마크(영문)'. 공식 원형 리더보드와 순위 비교 금지 | P4 결과로 산정 |
| P6 | 한국어 독립 시험(TK-166) | v1.0 단계 | 사용자 결정 | 제품 핵심 기능의 측정 | — |

- 배치:
  - PR 회귀 게이트(결정적·오프라인)는 지금 그대로 둔다.
  - P5 실행은 릴리스 후보에서만 돈다(모든 PR에서 반복하지 않는다).
  - 외부 API 실패는 '측정 미완료' 상태로 남기고, 통과나 제품 회귀로 바꾸지 않는다.
- 되돌리기: BM-2는 요청 생성을 한 곳으로 옮기는 변경이다. 운영 동작이 바뀌면 시험이 잡는다(아래 수용 기준). 문제가 생기면 PR을 되돌리면 된다.

## 6. 검증 기록(모두 평가 측 재실행, 검토 SHA b94750b, Python 3.11.18, 오프라인 LV_ALLOW_NETWORK=0)

| # | 확인 | 명령·방법 | 관측 |
|---|---|---|---|
| V1 | 기존 평가 계약 시험 | `pytest tests/acceptance/test_evaluation_v2.py` | 31건 통과 |
| V2 | 실패 사례 탐침(평가 라이브러리) | 저장소 밖 탐침 스크립트 | 중복 예측 거절, 모르는 ID 거절, 사건군 분할 누출 거절, 누락 → 분모 유지(3건 중 2건 누락 → coverage 0.333), 출처 섞임은 origin 선택으로 분리, **정답 UNVERIFIED + 예측 VERIFIED → false VERIFIED 1(T4)**, 라이브러리는 버전 섞임 허용·dashboard에서 거절 |
| V3 | 라이선스 원문 | 공식 페이지·원문 파일 조회(2절 근거 위치) | 2절 표와 같다. 확인하지 못한 것은 '미확인'으로 표기 |
| V4 | 영어 입력 종단간 가능성 | `extract_from_text` | 영어 판례·법령·NDA 가설 3건 추출 0, 한국어 대조 1 |
| V5 | BM-1·BM-2 사본 구현 | 사본 `tbm`(b94750b + BM 패치), 새 시험 19건 | 19건 통과 |
| V6 | BM 사본 사전 점검 | `precheck_pr.py`(전체 모드, 관련 기존 시험 포함), 사본 a28a66f | 종료 0: 고정 82.6/81.9/오탐 0 변화 0, 은퇴 5세트 후퇴 없음, 평가 세트 문구 대조 통과. 게이트 3종 통과 |

- 실행하지 못한 것:
  - 실제 모델 호출(비용 범위 미승인)
  - 배포본 내려받기와 SHA-256 계산
  - ContractNLI 공식 분할별 문서 수의 원문 확인
  - Harvey LAB 전체 트리
  - 논문 부록(MAUD A.1) 대조
  - LegalBench 전체 과제 허용 목록
- 라이선스 확인(V3)과 기술 시험(V1·V2·V4~V6)은 서로 다른 근거다.

## 7. 사용자 결정 사항

1. **ContractNLI 시범 실행 비용 승인(P4).**
   - 호출 수: dev 분할 일부 문서 × 가설 17개 = 판정 호출 수.
   - 비용 근거가 없어 시범 실행으로 정한다.
   - 추천: 문서 10개(170호출) 시범 → 실측 비용·변동성 보고 → 전체 승인 여부를 다시 결정.
2. **P0 평가 PR 병합 승인**: 보호 경로이고, KBL 시험 단언을 바꾸게 된다.
3. 이 밖의 후보(LegalBench-RAG·CUAD·MAUD·LegalBench·Harvey LAB)는 보류다. 지금 결정할 것은 없다.
EOF
echo written