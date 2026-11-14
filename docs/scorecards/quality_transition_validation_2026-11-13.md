# 평가 v2 전환 검증 — 2026-11-13 KST

사용자 요청: “권고대로 평가 방법을 전환해줘.”

기준 제품/통합 브랜치: `e57855f28cde65f2f515c3d26f958370fa6251c8` (0.19.0). 평가 변경 브랜치: `evaluator/quality-transition-20261113`. 제품·기존 정답·기존 baseline.json 변경 없음. 운영 규약은 [EVALUATION_V2](EVALUATION_V2.md), 집계는 [검증 JSON](quality_transition_validation_2026-11-13.json).

## 검증 결과

- `b9ef32aa`: 신규 평가 계약 + 기존 scorecard/retired/quality 관련 시험 **135 통과, 1 환경 조건 건너뜀**. 명령: `python -m pytest tests/acceptance/test_evaluation_v2.py tests/test_eval_metrics_tools.py tests/acceptance/test_scorecard_tools.py tests/test_analysis_completion.py --junitxml=artifacts/quality-transition-tests.xml -o addopts='' -q`.
- `09f18915`: 최종 상태/버전 연결 계약 **41 통과** (`tests/acceptance/test_evaluation_v2.py`). 앞 항목과 겹치므로 통과 건수를 합산하지 않는다. 실제/공개 평가 결과가 다른 제품 SHA에서 나온 경우 dashboard가 거부한다.
- 고정 시험 재실행: 구 산식 dev **82.6**, holdout **81.9**, 확인 오탐 **0**. v2는 **42/56**, **41/54**. `score_gate.py --strict-env` 통과. 구 baseline은 그대로다.
- `f58f14c5`: 현재 채점기+고정 입력으로 기준/후보 제품을 각각 실행한 은퇴 5세트 **10회 성공, 기존/v2 회귀 없음**. 이후 같은 비교의 숫자 출력 위치를 고쳤고, 집계 렌더링 계약 시험을 추가했다. 판정 계산/제품/정답 변경은 없다. 모든 비교를 마지막 문서 커밋에서 다시 돌렸다고 주장하지 않는다.
- 은퇴 구 산식: **53.3 / 48.6 / 56.9 / 45.8 / 34.1**, 기준과 후보 동일. v2: **22/46 / 24/54 / 31/58 / 23/53 / 12/44**. 이는 이 실행 환경의 회귀자료 관측값이다.
- 과거 제품 바인딩 검증: 현재 evaluation_replay에 v0.10 제품을 공급해 제품 버전 **0.10.0**, holdout 구 산식 **79.2**, v2 **39/54** 확인. 과거 제품 대신 현재 제품을 잘못 불러오는 경로가 아님을 확인했다.
- 실제 제품 결과에서 **47개** identity/quote 예측 export 성공, 같은 inventory 밖 추가 후보 **0**. 독립 정답이 없으므로 정확도는 계산하지 않았다. 축약 finding 참조를 실제 finding과 연결하고, 법령 내용 오류를 법령 식별 오류로 섞지 않는 회귀 시험을 추가했다.
- 실제 고정 KBL 파일의 해시와 **75문항** 로딩 확인. 답변 실행은 하지 않았으며 빈 응답은 **NOT_MEASURED/null**이다. 합성 채점기 시험 점수를 실제 KBL 점수로 표시하지 않는다.
- 보호 경로·시험 변경 규칙·버전 정책 점검 통과. NEXT/HISTORY/DAILY_TREND는 추가만 했고 삭제 줄 수 0이다. `git diff --check` 통과.

실행 환경: Python 3.12.14, Tesseract 5.5.0 + eng/kor/osd, OMP_THREAD_LIMIT=1, 네트워크/LLM 미사용. GitHub CI의 Python 3.11/OCR 환경 결과는 별도로 확인한다. 로컬 검증을 동일 SHA CI 결과로 부풀리지 않는다.

## 수용 범위와 남은 조건

평가 도구/규약 전환의 로컬 검증은 통과했다. 통합 적용은 새 평가 PR의 최종 SHA CI와 사용자 병합 절차를 따른다. 실무 법률 정확도, 실제 KBL 추론 점수, 근거 검색, 주장별 법리 타당성, 검토 시간 개선의 실증적 검증은 **NOT_MEASURED**다. 독립 법률가 정답·실제 응답·근거 span·실무 검토 자료가 필요하며, 이를 0점 또는 합격으로 대체하지 않는다.

기존 평가의 수치가 증명하는 범위를 제한하면서 새 측정을 실제 실행 경로에 연결한 변경이다. 제품 성능 개선 PR이나 전면적인 법률 품질 인증 판정이 아니다.
