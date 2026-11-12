# TK-152 두 음절 어간 약칭 추정 설계 메모

2026-11-12 구현 에이전트 Antigravity
기준: main 3c75071 (v0.18.0), 사용자 결정 X7 승인 반영

## 1. 배경 및 원인
0.18.0 온라인 탐침 A에서 두 음절 비공식 약칭 중 실재 법률이 부존재(STATUTE_NONEXISTENT·CRITICAL) 또는 미확정(MEDIUM)으로 분류되는 문제가 발견되었다.
- **C1 (공식 약칭 가산 왜곡)**: 공식 약칭 기본점(800)이 정식명 기본점(600)보다 높아, 낱글자가 멀리 떨어져 맞는 타 법령 약칭(794점)이 첫 두 말마디가 온전히 일치하는 정답 정식명(596점)을 이김.
- **C2 (조문 부존재 시 CRITICAL 전락)**: 우선 후보 법령에 인용 조문이 없을 때 `ARTICLE_NOT_IN_CANDIDATE`로 설정되나, `UNDECIDED_INFERENCE`에 누락되어 CRITICAL(부존재)로 잘못 분기.
- **C3 (어간 전두 일치 가산 부재)**: 정답 공식 약칭(어간이 전두에 온전히 연속)과 타 법령 약칭(둘째 글자가 둘째 말마디)이 점수 차가 적어 AMBIGUOUS 처리.
- **C4 (앞 낱말 생략 약칭의 NO_CANDIDATE)**: 앞 낱말이 생략된 공식 약칭은 첫 글자 초성 목록에 없어 NO_CANDIDATE(CRITICAL)가 됨.

## 2. 해결 방안 (F1 · F2 · F3)

### F1 (C1 · C3). 두 음절 어간 전용 점수 함수 `_short_score()` 도입
- `min_stem == SHORT_STEM and len(stem(q)) == SHORT_STEM`인 경우 `_short_score(q, record)` 호출.
- 대조 대상은 공식 약칭(있으면 우선), 없으면 정식명. 약칭 가산 없음.
- 법령 종류 및 첫 글자 일치 필수. `…법`으로 끝나는 질의는 대상 이름 및 정식명이 `법`·`법률`로 끝나야 함(`…에 관한 규칙` 배제).
- 등급 기준:
  1. 어간이 대상 어간 맨 앞에 그대로 이어 나옴 (`target_stem.startswith(q_stem)`): 1000점
  2. 둘째 글자가 대상 어간 셋째 글자 (`len(target_stem) >= 3 and target_stem[2] == q_stem[1]`): 850점
  3. 그 밖의 말마디 첫 음절 정렬 (`_initials_subsequence(q_stem, target_stem)`): 700점
  4. 해당 없음: 0점
- 점수 산출: `등급 - min(max(len(target_stem) - 2, 0), 100)`. THRESHOLD 500, MARGIN 100 유지.
- 기존 96~99행의 두 음절 조건은 제거. 3자 이상 어간 규칙은 그대로 유지.

### F2 (C2). 후보 조문 부존재 시 미결 처리
- `UNDECIDED_INFERENCE`에 `"ARTICLE_NOT_IN_CANDIDATE"` 추가.
- 조문 부존재 시 `candidates=[inferred["candidate"]["law_name"]]` 보존.
- 513행 미결 분기 시 `ARTICLE_NOT_IN_CANDIDATE`인 경우 전용 detail 생성:
  `약칭 추정 후보 법령의 조회 버전에 인용 조문이 없어 그 후보로 확정하지 못했다(후보: …)`.
- `INFERENCE_NOTES`에 해당 항목 추가.
- 어간 4자 이상(약칭 꼴 아님)은 기존 CRITICAL 판정 유지.

### F3 (C4). 사용자 결정 X7 반영: 두 음절 NO_CANDIDATE 미결 완화
- 513행 조건을 `_undecided_inference(law_name, alias)`로 캡슐화.
  - `outcome in UNDECIDED_INFERENCE`이거나,
  - `outcome == "NO_CANDIDATE"`이면서 어간이 2자인 경우 참.
- `NO_CANDIDATE` detail: `첫 글자 목록에 글자 순서가 맞는 후보가 없으나, 앞 낱말을 생략한 공식 약칭일 수 있다`.
- 어간 3자 약칭 꼴의 NO_CANDIDATE 및 4자 이상은 CRITICAL 유지.
- `tests/test_tk143_short_abbreviation.py`의 `test_short_name_with_no_candidate_in_complete_list_keeps_not_found_law` 입력을 3자 어간 `가나다법`으로 조정하고, 2자 어간 `가나법`은 신규 시험에서 `ABBREVIATION_UNRESOLVED`로 검증.

## 3. 검증 계획
- `tests/test_tk152_short_abbreviation_ranking.py` 작성 (합성 법령명 사용).
- C1(정식명 우선순위 회복), C3(전두 일치 가산), 규칙 배제, C2(조문 부존재 미결), C4(2자 NO_CANDIDATE 미결) 및 대조군 검증.
- 하드코딩 방지 점검 및 기존 시험 회귀 점검.
