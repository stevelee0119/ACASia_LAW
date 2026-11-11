# [설계 메모] TK-76 3주기 C 묶음 후속 Q7 — 분배형 곱셈 단가 기준 탐색 범위 및 차원 보정

- **작성일**: 2026-11-10 | **작성자**: Antigravity (구현 에이전트)
- **기준 브랜치/커밋**: `antigravity/tk76-cycle3-c-bundle` (`d159949`)
- **대상 모듈**: `packages/claim_engine/calculation.py` (`_other_rate_basis`, `_evaluate_formula_operands`)
- **수칙 준수**: 본 메모는 독립 평가 지시(2026-11-10)의 Q7 품질 기준에 따른 설계 보완 메모이다.

---

## 1. 원인 분석 및 앞선 지시의 누락 축
- **원인**: 기존 `_other_rate_basis`(:491)는 인원(`ops[0]`)과 단가(`ops[1]`) 사이의 `between` 문자열만 검사했다.
- **누락 축**: 
  1. 단가 뒤~결과 앞(`after_ops`, 예: `각 25,000원씩 매일 사흘 동안 지급하여 합계...`, `각 45,000원씩 시간당 지급하여 합계...`)
  2. 절 시작~인원 앞(`before_ops`, 예: `매일 사흘 동안 상담원 4명에게 각 25,000원씩...`, `시간당 강사 8명에게...`)
  이 두 위치에 존재하는 기간·주기·차원 표지가 누락되어, 일회 지급액과 여러 회차/시간 총액을 잘못 단순 비교하는 `ARITHMETIC_MISMATCH` 오탐이 발생했다.

## 2. 변경 경로 및 범위
- **`packages/claim_engine/calculation.py`**:
  1. **구조적 기간/단가 정규식 확장**:
     - `_DURATION_BASIS_RE`: 한글 기간(`하루·사흘·석 달·보름` 등) + `(동안|간)`
     - `_DIGIT_DURATION_RE`: 숫자 결합 기간(`\d+\s*(?:일|월|달|년|주|시간|회|기|개월)` 등)
     - `_PERIOD_BASIS_RE` 및 `_PER_BASIS_RE`: 기존 주기 및 `-당` 기준 재사용
  2. **구간별 단가 기준 공통 검사기 `_check_segment_rate_basis`**:
     - 피연산자 앞(`before_ops`), 사이(`between`), 뒤(`after_ops`)에 대해 일관된 단가·기간 기준 검사.
     - `_is_other_per_basis` 판정 시 인원 단위(`_PERSON_BASIS`)와 첫 피연산자 단위(`ops[0]["unit"]`) 일치 여부를 대조하여, 동일 기준(`1인당`, `1명당`)은 정상 일회 지급으로 유지하고 이종 기준(`시간당`, `일당`)만 분배형 곱셈 제외.
  3. **산식 절 결속 및 호출자 연계**:
     - `_evaluate_formula_operands(ops, text, after_ops, cs=cs)`로 현재 절 시작점(`cs`)을 전달하여 `before_ops = text[cs:ops[0]["start"]]` 계산.
     - `_TOTAL_MARK_RE` 결합 분배형 곱셈에서 `_other_rate_basis` 참일 때 fallback 덧셈으로 빠지지 않고 `None, None`을 즉시 반환하여 보류.
     - 무관한 앞 절/앞 문장(`작성하지만`, `작성하고`, `.` 분할)의 기간 표지는 `_operand_clause_start`에 의해 `before_ops` 범위 밖으로 분리.

## 3. 보존 계약 및 복잡도
- **보존 계약**:
  - 단일 지급 합계(`4명에게 각 25,000원씩 지급하여 합계 100,000원이다`) 정상 검산 유지.
  - 단일 지급 불일치(`합계 110,000원이다`) 오차 탐지 유지.
  - 무관한 앞 문장/앞 절의 기간(`매월 보고서를 작성하지만 4명에게 각 25,000원씩...`)은 현재 절 산식 검산을 비활성화하지 않음.
  - 기존 덧셈/뺄셈/선행 계수 산식 호환성 유지.
- **복잡도**: 문자열 분할 및 1회 정규식 검색으로 $O(N)$ 선형 시간 복잡도 유지.

## 4. 시험 계획 및 결과
- **공개 시험**: `tests/test_codex_q7_rate_scope_eval.py` (15/15 통과)
- **기존 산식 시험군**: `tests/test_tk76_calc_q4q5_eval.py`, `tests/test_tk76_calc_label_eval.py`, `tests/test_tk76_cycle3_calculation.py`, `tests/test_calculation_leading_multiplier.py`, `tests/test_tk76_num_eval.py` (총 106/106 통과)
