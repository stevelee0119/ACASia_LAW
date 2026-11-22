# 설계 메모 · TK-230 · 객관적 AI 잔재 다중 동반 시 문체 잔재 신호의 교차 보강(`SUSPICIOUS/B`)

- **대상 티켓:** `TK-230` (`P1` — 오프라인 객관지표 `dev > 83.9`, `holdout > 83.3` 일반화 상승)
- **대상 모듈:** `packages/verification_engine/ai_document_detector.py`
- **작성일:** 2026-11-22

## 1. 문제 정의
- `ai_document_detector.py`는 비객관적 문체 잔재(`영문 병기`, `AI 답변 상투 표현` 등 `objective=False`)를 항상 `UNVERIFIED/C`(가중치 `0.25`)로만 기록한다.
- 동일 문서에 이미 서로 다른 **객관적 AI 생성 흔적**(`objective=True`, 예: 대화형 서두·마크다운 문법 잔재·지식 기준일·면책문·미기재 자리표시 중 2개 이상)이 다수 동반된 경우에도, 함께 나타난 문체 잔재 신호가 `UNVERIFIED`로만 남아 오탐 위험이 없는 문서에서조차 `AIGEN` 재현율이 `0.786`으로 제한되었다.

## 2. 일반화 설계
- 동일 문서에서 `objective=True` 잔재 카테고리가 **2개 이상**(`len(objective_cats) >= 2`) 독립 확인된 경우에 한하여, 그 문서에 동반된 문체 잔재(`not r["objective"]`)를 **교차 보강된 의심 신호(`VerificationStatus.SUSPICIOUS`, `Severity.LOW`, `EvidenceGrade.B`)**로 승격한다.
- **오탐 방지 불변식:**
  - `objective=True` 카테고리가 `0`개 또는 `1`개인 일반 사람 작성 서면에서는 문체 표현(`결론적으로`, 영문 병기 등)이 기존과 동일하게 `UNVERIFIED/C`로 유지된다(확인 오탐 0 · A등급 오탐 0).
  - 승격 등급은 `B`(`advisory_only=True`)로 제한해 `A`등급 오탐을 만들지 않는다.
  - 특정 사건 문구·키워드를 추가하지 않는 구조적 교차 보강 규칙이다.

## 3. 검증 계획
- 양성 3건 이상(객관적 AI 흔적 2종+ 동반 문서의 문체/영문 병기 승격) 및 대조 3건 이상(사람 작성 서면의 상투어·영문 병기·단일 약한 신호 미승격) 단위 시험.
- `eval_testset.py`(`dev`), `score_gate.py`, `retired_compare.py`, `check_case_literals.py`, `check_train_phrase_overlap.py --eval-sets` 전수 통과.
