# 평가 v2 운영 규약

시행 근거: 2026-11-13 사용자 지시 **“권고대로 평가 방법을 전환해줘.”** 평가 도구·시험·CI·운영 규약의 전환이다. 제품 탐지 코드와 기존 정답·`baseline.json`은 변경하지 않는다.

## 1. 판정 방식

82.6/81.9 같은 종전 수치는 **구 산식 회귀 점수**로만 표기한다. 전체 법률 정확도 또는 전체 오탐률로 인용하지 않는다. 기존 회귀 하한과 개인정보·보안 수용 조건은 유지한다.

이제 `scorecard.py`는 같은 제품 실행 결과에서 기존 지표와 `regression_v2`를 함께 산출한다. `score_gate.py`는 기존 기준선과 `regression_v2_baseline.json`의 유형별 정답 인정 건수·분모·자료 해시·프로토콜을 모두 검사한다. 새 하한은 v0.19 제품의 dev **42/56**, holdout **41/54**다. 실무 품질 합격선을 75점 등으로 정한 것이 아니다.

새 점수는 non-advisory 강한 결함 판정에 이진 득점을 주고, CIT-NX-DB/SRC-UNV는 UNVERIFIED를 요구한다. 문서별 최대 이분 매칭으로 finding 하나를 정답 하나에만 사용한다. `confidence_features`·규칙 ID·유형 이름 자체는 검색 텍스트에서 제외한다. 내부 보조 데이터에 정답 단어가 나타난 것만으로 득점할 수 없다. 같은 finding ID를 문서/프로젝트 출력에서 다시 세지 않는다.

정답지의 위치를 법률적으로 재주석한 것은 아니므로 이 수치는 **어휘 기반 회귀 대리 지표**다. 하나의 경고가 복수 결함을 묶은 경우 보수적으로 손실될 수 있다. 문서 위치·근거 의미 검증과 법률 전문가의 새 정답을 대체하지 않는다. 이 한계와 프로토콜을 보고서에서 생략하지 않는다.

`known_false_positive_findings`(현재 정답지에서 확인된 오탐), `unadjudicated_alerts`(정답지 밖 경고), `advisory_findings`를 따로 기록한다. 미판정 경고를 모두 오탐으로 바꾸거나, 정답지 밖 경고가 있는 상태를 ‘전체 오탐 0’이라고 표기하지 않는다. 인젝션 탐지와 기존 프로젝트 BLOCK 대리값은 실제 공격 방어 성공률과 구분한다.

## 2. 다섯 평가 층과 미측정 처리

| 층 | 운영 도구/자료 | 현재 전환 상태 |
|---|---|---|
| 회귀·계약 | scorecard / score_gate / retired_compare | 필수 CI 연결, 구 기준+v2 유형별 하한 병행 |
| 출처 검색 | 공식 원문 ID·버전·근거 span·관련성 정답 | 실제 라벨 전에는 NOT_MEASURED |
| 허위·왜곡 검증 | 실제 제품 출력 → export_quality_predictions → packages/evaluation | 판례/법령 식별과 직접 인용의 차원을 분리한 export 연결. 독립 법률가 라벨이 없으면 NOT_MEASURED |
| 주장·법리 적용 | 사건 사실·시점·법률요건·반대 근거·판례 의견의 독립 정답 | 전체 추론을 identity/quote VERIFIED로 추정하지 않음. claim별 구조화 판정과 정답 확보 전에는 NOT_MEASURED |
| 실무 효과 | 무작위/순서 균형 검토 실험, 검토 시간·중대한 오류·비용 | 실제 실험 전에는 NOT_MEASURED |

`evaluation_dashboard.py`가 이 층들을 한 보고서에 구분한다. NOT_MEASURED의 값은 `null`이다. 도구가 정상 종료했거나 회귀 CI가 녹색이어도 `legal_quality_approval=NOT_ESTABLISHED`를 법률 품질 승인으로 바꾸지 않는다. 이 값은 기존 기능의 모든 릴리스를 금지한다는 뜻이 아니라, 실무 법률 정확도를 입증했다고 주장할 수 없다는 뜻이다. 기능별 수용 판정은 실제 측정한 범위와 미측정 항목을 명시한다.

평가 실패/시간 초과/문서 누락은 점수 0·변화 0·통과로 바꾸지 않는다. 파이프라인 `errors`가 있으면 측정 실패다. 악성 시험문서를 격리하는 정상 보안 동작 자체는 실행 실패가 아니다. 원문/정답/인증정보는 CI artifact에 넣지 않고 집계만 보존한다.

## 3. 은퇴 세트와 비교 재현성

`retired_manifest.json`은 **통합 브랜치 e57855f에 이미 존재하는 5세트 전체의 파일 묶음 해시**를 고정한다. 배포된 main v0.19에는 이 중 20261025 세트가 없었다. 앞으로 릴리스 통합에서 파일이 빠지면 CI가 실패한다. manifest를 줄여서 통과시키지 않는다. 새 자료 추가나 교체는 평가 측 검토·변경 이유·비교 가능성 기록을 요구한다.

`retired_compare.py`는 기준/후보 제품을 **같은 후보 측 고정 입력과 같은 현재 채점기**로 재실행한다. 기준 버전의 구 채점기와 후보 버전의 새 채점기를 비교하지 않는다. 전체 목록을 검사하므로 교집합으로 세트 누락을 감추지 못한다. 기준/후보 실행 실패, 분모/프로토콜/자료 해시 차이, 기존 점수 후퇴 또는 v2 유형별 인정 건수 감소는 실패다. 신설 세트는 같은 입력을 두 제품 모두에 공급해 비교한다.

제품·평가 도구·자료가 모두 그대로일 때만 `NOT_RUN_UNCHANGED`로 재실행을 생략한다. 목록·해시 검사는 이 경우에도 수행한다. 이를 ‘새로 전수 시험 통과’라고 보고하지 않는다. 로컬 캐시 키에는 기준 제품 SHA, 현재 평가 코드, 자료 해시, Python/플랫폼, 패키지 버전, OCR 버전/언어 자료 해시를 포함한다. CI는 캐시를 사용하지 않는다. 고정 하한은 운영 회귀 제약이며, 환경이 다른 두 실행을 과학적 성능 증감으로 비교할 때는 별도 동일 조건 replay가 필요하다.

## 4. 실제 예측과 독립 정답 연결

평가 inventory는 **정답을 읽지 않고** 실제 문서 SHA256, 인용문 원문 해시, 페이지·문자 범위, 판정 차원으로 안정된 항목 ID를 만든다. 매 실행 달라지는 citation UUID는 항목 ID에 사용하지 않는다. 동일 위치가 모호하게 겹치면 추측 매칭하지 않고 실패한다. 인용 추출이 사라지면 고정 inventory 항목을 삭제하지 않고 ABSTAIN으로 내보낸다. 평가 입력 문서 자체가 달라지거나 빠지면 실패한다.

```bash
python scripts/export_quality_predictions.py --result /private/result.json --make-inventory --out /private/items.json
python scripts/export_quality_predictions.py --result /private/result.json --inventory /private/items.json --system-version <정확한_제품_SHA> --out /private/predictions.jsonl
python scripts/evaluation_dashboard.py --scorecard artifacts/scorecard.json --labels /private/labels.jsonl --predictions /private/predictions.jsonl --origin ATTORNEY_LABELED --out /private/evaluation-v2.json
```

inventory는 개발 중 동결하고 새 버전에 재사용한다. 정답 라벨은 이 item ID에 연결하되 input_text, case_id, case_family_id, split, origin, gold_status, error_types, annotation을 `LabelRecord` 스키마로 작성한다. 독립 법률가 2인의 자격 확인·판정·불일치 조정, 근거 페이지/블록/문자 범위를 기록한다. 기존 모듈은 선언된 자격을 확인할 뿐 자격을 인증하지 않는다. 실제 확인 절차는 평가 책임자가 보관한다.

관련 사건·상하급심·개정 서면·요약·변형은 하나의 case_family_id로 묶어 development/validation/test 중 한쪽에만 둔다. 합성/실제 라벨 자료를 합산하지 않는다. 평가 중 정답을 보고 수정한 자료는 독립 시험에서 은퇴시킨다. 원문/정답의 공개 여부는 기존 봉인 자산 규약을 유지한다.

현재 exporter는 **identity와 literal quote**만 지원한다. 판례가 실재한다는 VERIFIED를 인용문 또는 주장 전체의 VERIFIED로 옮기지 않는다. 법령의 existence/article/content도 해당 차원으로 분리한다. 정답 error_types는 각각 `CITATION_IDENTITY_ERROR`, `QUOTE_CONTENT_ERROR`를 사용한다. 이 두 유형은 구성요소 오류의 큰 분류이며 상세 법리 오류 분류를 대체하지 않는다. `legal_verdicts.findings`의 축약 참조는 문서/프로젝트의 실제 finding과 연결한다. LAW_CITATION_ERROR처럼 내용 오류에도 쓰이는 유형을 식별 오류로 단정하지 않는다. 알려지지 않은 상태, 같은 차원의 VERIFIED와 명확한 결함 finding 충돌은 실패한다. 새 버전에서 inventory 밖에 생긴 인용은 manifest의 unbound_candidate_items로 따로 표시하며 정밀도 분모에서 조용히 지우지 않는다. 비용·시간을 측정하지 않았으면 null이다. 기존 quality 모듈의 precision/recall/F1, false VERIFIED, coverage, 사건군 신뢰구간을 그대로 사용한다. 새 실무 합격선은 위험 예산과 독립 validation 자료로 사전에 정한 뒤 TEST를 열어야 한다. 임의 80점이나 0건 관측만으로 안전을 인증하지 않는다.

## 5. 공개 벤치마크 — 미적용 (2026-11-13 사용자 결정)

사용자 결정: "추가 벤치마크는 필요성이 높지 않아보이니 미적용 하자."(2026-11-13)

KBL·영어권 공개 벤치마크를 적용하지 않는다. 근거는 [벤치마크 재평가 r3](benchmark_adoption_review_2026-11-13_r3.md)의 제로베이스 검토와 계획 문서 6.15다.
- 제품 핵심 기능(한국어 서면의 판례·법령 실재, 인용문, 시점, 주장 근거)은 자체 한국법 평가가 직접 잰다.
- 영어권 자료는 제품 경로에 들어가지 못한다(영어 인용 추출 0건).
- KBL 선택형 과제는 제품에 선택형 응답 기능이 없어 모델 단독 시험이 된다. 일부 정답은 개정 전 법을 기준으로 한다.

조치:
- 이 규약 초판(#272)의 KBL 채택과 `evaluate_kbl.py`(statute_hallucination 75문항 채점기)를 철회·삭제했다.
- `evaluation_dashboard.py`의 `public_benchmark` 층과 성적표 `measurement_status.public_benchmarks`는 `NOT_APPLIED`(값 null)로 남는다.
  - 미측정(NOT_MEASURED)과 다르다. 적용하지 않기로 결정한 층이며, 통과·0점으로 읽지 않는다. 점수를 붙이는 입력 경로는 없다.
- 지표 정의는 자체 평가에 그대로 쓴다: 지지·모순·근거 부족 3분류, 근거 구간 정밀도·재현율, 실패를 분모에 남기는 규칙, 사건군 단위 구간.
- 외부 벤치마크를 다시 들이려면 r3 2절의 필요성 기준(측정 공백, 자체 수단 대비 이점, 쓰일 결정, 역효과)으로 새로 검토하고 사용자 결정을 받는다.

## 6. 기존 시험과 전환 검증

기존 `test_retired_compare_failed_head_and_new_set`는 기준 실행 실패와 세트 차이를 무시하도록 기대했다. 사용자가 승인한 실패 시 차단 원칙에 맞춰 그 기대값을 강화했다. 그 밖의 기존 기준선·정답은 유지한다. 새 계약 시험은 중복 득점, 메타데이터만의 득점, advisory/불확실성 상태, 미판정 경고, 오류/문서 누락, 세트 누락, 분모/해시 변경, 실제 출력 export, CI 연결을 다룬다. KBL 채점 시험은 5절 결정에 따라 '외부 벤치마크 미적용·입력 경로 없음' 시험으로 바꾸었다(2026-11-13).

새 평가 스크립트·규약·기준선은 보호 경로와 CODEOWNERS에 포함한다. 평가 측 변경도 독립 코드 검토와 같은 SHA CI를 거친다. 인용문 위치/법리 의미, 실제 법률가 라벨, 실무 시간 측정은 확보 전까지 미검증으로 남는다. 구현 에이전트가 합격시키기 위해 평가 자료·라벨·manifest·하한을 바꾸지 않는다.
