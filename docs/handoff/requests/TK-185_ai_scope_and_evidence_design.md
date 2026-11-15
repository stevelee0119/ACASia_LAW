# TK-185 설계 메모: AI 관여·범위 분리 및 근거 강도·표본 범위 보존

## 1. 구현/평가 역할 분리
- **평가 측 도구 (`scripts/ai_repeat_summary.py`)**: 문서 문자열에 명시된 평가 에이전트 소관 보호 도구이므로 구현 PR에서 직접 수정하지 않는다. 전체 SHA·입력 SHA·정책/모델/Drive 스냅샷·복수 문서 비교는 평가 측 수정 및 사본 검증으로 처리한다.
- **구현 측 제품 코드 (`packages/verification_engine/ai_document_detector.py`, `packages/verification_engine/scoring.py`)**: TK-185의 '품질 설계(구현/평가 분리)' 항목을 구현한다.

## 2. 제품 설계 원칙 (임계값 고정 금지)
1. **고정 라벨/점수 임계값 비변경**: 특정 사례(`case9` 등)에 맞춰 `verdict` 다수결 규칙·점수 임계값·`evidence_grade` 기준을 바꾸지 않는다.
2. **AI 관여 여부와 전체/일부 범위 분리**:
   - `involvement`와 `scope`(`WHOLE_DOCUMENT` / `PART_OF_DOCUMENT` / `NOT_APPLICABLE` / `UNDETERMINED`)를 `signals`, `confidence_features`, `scores.axes.ai_authorship`에 함께 보존한다.
3. **모델 간 범위 이견·관찰 구간·표본 범위·근거 강도 보존**:
   - `model_scope_opinions`(`provider -> scope`)와 `scope_disagreement`(`bool`)를 기록해, 과반이 AI 작성을 지목하더라도 `WHOLE_DOCUMENT`와 `PART_OF_DOCUMENT` 간 이견이 사라지지 않도록 한다.
   - `coverage`(`total_chars`, `inspected_chars`, `sampling_mode`, `is_full_coverage`, `omitted_chars`)를 `confidence_features`와 `scoring.py` 축 결과까지 전달해 관찰 구간과 표본 범위를 유지한다.
   - `evidence_strength`(`OBJECTIVE_TRACES` / `HEURISTIC_ONLY` / `NONE`)를 기록하고, 객관적 흔적(`objective_traces == 0`) 없이 문체·모델 추정만으로 다수결 AI 판정이 내려질 때는 설명 문구에 객관적 생성 흔적 미확인 사실을 명시한다.

## 3. 시험 계획
- 양성 예시 3건 이상:
  1. 모델 간 범위 이견(`FULL` vs `PARTIAL`) 시 `scope_disagreement=True`, `model_scope_opinions` 및 detail 표기 확인
  2. 객관적 흔적 없는 문체/모델 추정만 있을 때 `evidence_strength="HEURISTIC_ONLY"` 및 미확인 안내 문구 확인
  3. 긴 문서(`head_middle_tail` 샘플링) 시 `coverage`가 `signals` → `confidence_features` → `scoring.py` 축까지 보존되는지 확인
- 대조군 3건 이상:
  1. 모든 AI 모델이 동일 범위(`WHOLE_DOCUMENT` 일치)일 때 `scope_disagreement=False`
  2. 객관적 흔적(`objective_traces > 0`)이 있을 때 `evidence_strength="OBJECTIVE_TRACES"`
  3. 모델 의견이 갈려 `UNCERTAIN`일 때 `scope="NOT_APPLICABLE"` 및 기존 회귀 유지
