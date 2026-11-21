# [설계 메모] 공식 원문 슬라이딩 구간 정렬 + Stage 2 한국어 Legal NLI 보조 검증기 (PR-09)

- **작성일**: 2026-11-20 · **작성자**: Antigravity (`Agent: implementer`) · **대상 PR**: `PR-09`

## 1. 해결하려는 문제
현재 `evidence_basis.py`의 퍼지 정렬과 `quote_diff.py`의 어휘 차분은 직접 인용문에는 강건하나, 판례의 요지를 간접 인용하거나 어순·어휘를 바꾸어 취지를 왜곡하는 경우(`CIT-MIS`) 원문 대응 구간(`passage`) 특정에 실패해 `UNVERIFIED`로 남는다.

## 2. 일반화 설계 및 안전 불변식
1. **슬라이딩 윈도우 구간 정렬 (`sliding_window_passages`)**:
   - 공식 판결문(`판시사항`, `판결요지`, `이유`)을 1~3문장 슬라이딩 윈도우로 분할하고, 어휘 중첩(2-gram + 내용어)으로 최적 후보 구간(`passage`, `start`, `end`)을 추출한다.
2. **Stage 2 NLI 보조 신호 (`LegalNLIVerifier`)**:
   - **핵심 불변식**: NLI 모델은 **법률적 타당성의 최종 판정기가 아니다.**
   - `(Premise=공식 원문 구간, Hypothesis=서면 인용 요지)` 쌍에 대해 NLI 확률 $(P_{\text{entail}}, P_{\text{contradict}}, P_{\text{neutral}})$을 계산하되:
     - **원문 근거 구간(`passage`)이 특정되고 구조적 반전(부정·단서 누락·의무/허용 반전·주체 치환 등)이 동반될 때만** `CONTRADICTED` 후보로 제안한다.
     - NLI 점수만 높고 구조적 반전 근거가 모호하면 `SUSPICIOUS`/`PENDING_REVIEW`(전문가 확인 또는 Stage 3 LLM Critic 에스컬레이션)로 둔다.
     - 공식 원문 구간이 없으면 항상 `INSUFFICIENT`로 fail-closed 처리한다.

## 3. Rollout 및 시험 계획
- `LV_LEGAL_NLI_MODE=off | shadow | assist` (기본값 `shadow`)로 도입한다.
- **시험**: 직접/간접 인용 모순 3건+ 및 일치·중립·원문 미확보 대조군 3건+ 단위 시험을 동반한다.
