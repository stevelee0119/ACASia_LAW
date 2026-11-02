# TK-130 비공식 약칭 법령명의 공식 법령 추정 (+ 제21항 이상 원숫자)

- 등록: 2026-11-02, 평가 측
- 근거: 사용자 지시(2026-11-02) — lexdiff 저장소의 기술 노하우 분석, ACASia_LAW와의 우열 비교, 성능 향상 요소의 구현 지시
- 배정: Antigravity(2026-10-31부터 구현 에이전트 복귀). 착수 시점은 사용자 결정
- 분류: 오탐(법령 부존재 CRITICAL) 감소 · 정확도. 원인 유형 = 법령명 해소의 사전(辭典) 의존

## 1. 문제

- 서면은 공식 약칭이 아닌 줄임말을 자주 쓴다. 이 문서에서는 이를 '비공식 약칭'이라 부른다.
- ACASia_LAW는 이런 이름을 다음 순서로 해소한다.
  1. 하드코딩 별칭 표 `LAW_ALIASES`(20여 개, `packages/legal_engine/normalize.py:136`)
  2. 문서 안의 정식 법령명이나 약칭 정의(`citation_extractor._attach_law_alias_candidates`, 1499행)
  3. 공식 목록의 '법령약칭명'과 완전히 일치하는 경우(`official_legal.search_law_history`, 130~135행)
- 세 경로가 모두 실패하면 결과는 `_law_absent` 3번 분기(`source_review.py:467`)의 **STATUTE_NONEXISTENT CRITICAL**('법령 목록에서 찾지 못한 법령')이다.
- 실제 법령을 줄여 쓴 서면에 '존재하지 않는 법령' 최고 심각도가 붙는다. 이는 오탐이다.
- 국가법령정보 목록 검색은 비공식 약칭에 0건을 돌려준다. 이 사실은 이 저장소 `normalize.py:147~148` 주석('국가계약법' 0건)과 lexdiff `lib/law-name-match.ts` 주석에서 같은 관찰로 적혀 있다.

## 2. 참고한 외부 노하우 (lexdiff, BSL 1.1)

- `lib/law-name-match.ts`의 방식:
  - 어미('법'·'시행령' 등)를 뗀 몸통으로 다시 검색한다.
  - 후보의 공식 약칭이나 정식명 안에 적힌 이름의 글자가 순서대로 나오는지(부분수열)를 보고, 0~1000점을 매긴다.
- lexdiff는 **BSL 1.1(운영 사용 금지, 2030-04-14 Apache 2.0 전환)**이다. 코드·데이터(`query-expansion-data.ts` 등)는 복사하지 않는다.
- 평가 측 수정본은 아이디어만 참고했고, ACASia 판정 규약에 맞춰 새로 작성했다. lexdiff에 없는 차이점은 다음과 같다.
  - 종류 일치 검사
  - 약칭이 있으면 약칭과만 대조
  - 첫 글자 일치
  - 단일 후보 또는 점수 차이 조건
  - 조문 실존 조건
  - '확인됨' 승격 금지

## 3. 해결 (평가 측 수정본 `patches/TK-130_abbreviation_inference_on_debbe83.diff`, Steve `debbe83` 기준)

1. `packages/legal_engine/law_name_inference.py`(새 파일): `stem`·`law_kind`·`is_subsequence`·`score`·`pick`
2. `OfficialLegalMixin.infer_law_by_abbreviation(law_name)`(`official_legal.py`, `resolve_statute` 앞)
   - 검색어는 어간이고, 결과가 없으면 어간 앞 4자로 한 번 더 검색한다. 검색은 최대 2회다.
   - `pick`이 하나로 좁힐 때만 후보를 돌려준다.
3. `verify_statute_source`(`source_review.py`)
   - 다음 두 조건이 모두 맞을 때만 추정을 시도한다.
     - 응답이 `EXACT_LAW_NOT_FOUND`이다.
     - 문서 근거 약칭 후보(`law_alias_candidate`)가 없다.
   - 추정 법령을 `resolve_statute`로 조회해 조문을 대조한다.
   - 결과 표시
     - existence는 `INFERRED_FROM_ABBREVIATION`으로 둔다.
     - 상태가 VERIFIED이면 PARTIALLY_VERIFIED로 낮춘다.
     - LOW finding `ABBREVIATION_INFERRED`를 남긴다.
   - 추정 법령에 인용 조문이 없으면 추정을 버리고, 원래 응답으로 `_law_absent`를 실행한다. 원래 판정 CRITICAL이 그대로 유지된다.
4. 제21항 이상 원숫자
   - `temporal_review.CIRCLED`의 범위를 ①~⑳에서 ①~㊿로 넓힌다.
   - `provision_content.CLAUSE_SPLIT_RE`에 `㉑-㉟㊱-㊿`를 추가한다.
   - ㉑(U+3251)은 ⑳(U+2473)와 코드 범위가 이어지지 않는다. 그래서 지금은 제20항 추출이 제21항 이후까지 함께 잘려 나오고, 제21항 이상은 추출되지 않는다.
   - 주 경로 `legal_history.py:131`은 이미 ㊿까지 처리한다.

## 4. 수용 기준

- 새 시험 `tests/test_tk130_abbreviation_inference.py`
  - 양성: 약칭 3꼴, 제20~22항
  - 대조: 조문 부재, 근접 후보 2개, 종류·첫 글자·짧은 어간, 정식명 무시, 문서 근거 경로 불변, 제1·2·19항
- 기존 `tests/test_v096_statute_names.py` 등 관련 시험을 수정하지 않고 통과한다.
- 고정 벤치마크 dev·holdout과 오탐 수가 변하지 않는다.
- CI 필수 검사가 모두 성공한다.
- 온라인 효과(실제 국가법령정보 목록에서의 추정 정확도·호출 수)는 배포 뒤 온라인 점검에서 확인한다. 사전 검증에서는 측정하지 못했다.
