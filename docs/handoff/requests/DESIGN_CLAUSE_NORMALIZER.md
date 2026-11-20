# [설계 메모] `packages/korean_nlp` 공용 Korean Legal Clause Normalizer (PR-05)

- **작성일**: 2026-11-19 · **작성자**: Antigravity (`Agent: implementer`) · **대상 PR**: `PR-05`

## 1. 해결하려는 문제
현재 `legal_engine/polarity.py`, `legal_engine/claim_review.py`, `claim_engine/classification.py`, `date_verifier.py`, `structure.py`, `evidence_consistency.py`, `internal_inconsistency.py` 등 15곳 이상에 문장 분리·부정·이중부정·가정·미래시제·화자 귀속 정규식이 중복·파편화되어 있다. 한쪽에서 수정한 오탐 가드가 다른 엔진에 반영되지 않아 동일 문형에서 오탐·미탐이 반복된다.

## 2. 일반화 설계 (사건 비의존 문법 구조)
1. **형태소/어절 계층 (`packages/korean_nlp/tokenizer.py`)**:
   - `kiwipiepy` 설치 환경에서는 지연 로딩 싱글턴으로 형태소·품사(`NNG`, `NNP`, `VV`, `VA`, `VX`, `EC`, `EF`, `JKS`, `JX`)를 추출한다.
   - 미설치·경량 환경에서는 결정론적 어절·조사·어미 분리기(`RegexFallbackTokenizer`)로 자동 폴백하여 예외 없이 동일 인터페이스를 제공한다.
2. **절 단위 정규화기 (`packages/korean_nlp/clause_normalizer.py`)**:
   - 문장을 연결 어미(`~으나`, `~지만`, `~면`, `~더라도`, `~므로`) 및 인용절(`~라고 주장하나`, `~라고 판시하였다`) 기준으로 `NormalizedClause`로 분해한다.
   - 각 절마다 **화자 역할(`speaker_role`)**, **귀속 유형(`attribution_type`)**, **극성(`polarity`, 이중부정 홀짝 처리)**, **서법(`modality`: 단정/가정/예비/의문/당위/허용)**, **시제(`temporal_aspect`)**, **원문 오프셋(`reading_span`)**, **불확실성(`parse_confidence`, `uncertainty_reasons`)** 을 산출한다.
   - 주어가 생략되었거나 다중 내포절인 경우 무리하게 작성자 단정으로 귀속하지 않고 `uncertainty_reasons`에 기록해 하위 검증기의 A등급 과확신을 방지한다.

## 3. Rollout 및 위험 통제
- **Shadow Mode 우선**: `LV_CLAUSE_NORMALIZER_MODE=shadow`(기본값)로 도입하여 기존 판정 결과와 회귀 점수(`score_gate.py`)에는 **영향 0건**을 보장하고, 후속 `PR-06`에서 단계적으로 위임한다.
- **시험 계획**: 이중부정, 상대방 주장 요약·반박, 판례 전달, 가정·예비적 주장, 미래 예정, 주어 생략 등 축별 **양성 3건+ / 대조군 3건+** 독립 합성 문장으로 검증한다.
