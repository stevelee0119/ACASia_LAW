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

## 5. 2판 (11-02, Astra 재검증 반영) — 1판 수정본은 쓰지 않는다

교차 검증에서 1판의 결함 4개가 지적됐다. 평가 측이 코드로 모두 확인했다.

| # | 1판 결함 | 2판 수정 |
|---|---|---|
| ① | 후보 없음·모호·목록 조회 실패·상세 조회 실패가 모두 `(None, None)`이 되어 구분되지 않는다 | `infer_law_by_abbreviation`의 결과를 `FOUND / NO_CANDIDATE / AMBIGUOUS / LOOKUP_FAILED / INCOMPLETE`로 나누고 `review.law_alias.outcome`·notes에 기록한다. 후보를 골랐으나 상세 조회 실패·ID 불일치(`CANDIDATE_LOOKUP_FAILED`)이면 **UNVERIFIED**로 둔다. 같은 함수의 문서 근거 약칭 미해소(66~69행)와 같은 처리다 |
| ② | 조항이 DELETED·UNVERIFIED여도 '인용 조문이 그 법령에 있어 대조했다'는 LOW 설명이 붙는다 | 조항 상태별 설명을 쓴다. VERIFIED이면 조문 확인, DELETED이면 '법령명 후보만 추정, 지정 조문은 삭제', UNVERIFIED이면 '법령명 후보만 추정, 지정 조항 미확인'. `provision_status`를 기록한다 |
| ③ | 후보 law_id가 후속 조회에 고정되지 않는다. 동명 법령이 여럿이면 최신 ID가 선택될 수 있다 | `resolve_statute(..., law_id=)`와 `search_law_history(..., law_id=)`를 추가해 고정한다. 정확 이름 목록에 그 ID가 없으면 ERROR다. 반환 기록의 law_id가 후보와 다르면 `CANDIDATE_LOOKUP_FAILED`로 처리한다 |
| ④ | '최대 2회'는 HTTP 요청 수 상한이 아니다(`_legal_list`가 최대 100쪽을 순회한다) | `_legal_list(max_pages=)`를 추가했다(기본 100, 기존 동작 불변). 후보 탐색은 검색어 최대 2개 × 각 `INFERENCE_MAX_PAGES=3`쪽(300건)까지다. 상한에 걸리면 `INCOMPLETE`이고 후보를 고르지 않는다. 후보를 고른 뒤의 연혁·전문 조회는 기존 경로와 같다 |
| 표현 | '후보가 하나뿐' | '조회한 후보 N개 중 우선 후보'로 고치고 `candidate_count`를 기록한다 |

- **심각도 정책(평가 측 결정, 사용자 변경 가능)**
  - `NO_CANDIDATE`·`AMBIGUOUS`·`LOOKUP_FAILED`·`INCOMPLETE`·`ARTICLE_NOT_IN_CANDIDATE`는 TK-130 이전 판정(STATUTE_NONEXISTENT CRITICAL)을 그대로 둔다. 결과 구분만 기록에 남긴다.
  - 이유: 정확 이름 조회가 정상적으로 0건을 돌려준 상태에서, 추가 탐색이 실패한 것은 새 증거가 아니다. 이 기능으로 기존 진양성(가짜 법령)이 약해지면 안 된다.
- **분리**
  - 원숫자(㉑~㊿)는 결함이 명확하고 작으므로 별도 PR로 먼저 처리한다(TK-130a).
  - 약칭 추정은 TK-130b다.
  - 수정본: `patches/TK-130a_circled_paragraphs_on_debbe83.diff`, `patches/TK-130b_abbreviation_inference_v2_on_debbe83.diff`.
