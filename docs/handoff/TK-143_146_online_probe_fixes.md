# TK-143~146 — 0.17.0 온라인 탐침 결함 수정 (P1·P2, 평가 측 수정본)

- 근거: `docs/scorecards/online_probe_0170_20261103.md`(운영 0.17.0, 독립 작성 탐침 서면 4종). 11-03 사용자 결정 '전부 이번 릴리스에 포함'.
- 기준: Steve `7b41c7d`. 티켓마다 수정본 하나, 서로 다른 파일이라 각각·합쳐 적용 모두 된다(평가 측 확인).

## TK-143 (P1) 두 음절 비공식 약칭이 CRITICAL '존재하지 않는 법령'
- 수정본 `patches/TK-143_short_abbreviation_on_7b41c7d.diff`(5개 파일 +168/−6)
- 원인(`7b41c7d`)
  1. `source_adapters/official_legal.py` `infer_law_by_abbreviation` 190행: 어간(예 '노조')이 3자 미만이면 검색하지 않는다. 검색도 부분 문자열이라 '노조'는 '노동조합…'에 없다 → 'XX법' 꼴은 언제나 후보 없음.
  2. `legal_engine/source_review.py` `_law_absent` 3분기: 후보 없음·모호한 짧은 약칭도 STATUTE_NONEXISTENT CRITICAL.
  3. 약칭+시행령('근기법 시행령')은 별칭표(`normalize.LAW_ALIASES`)에 걸리지 않아 같은 CRITICAL.
- 수정
  1. 안전 장치 `_abbreviation_like`: 어간 2~3자·공백 없는 'XX법(시행령·시행규칙)'이 풀리지 않으면 LAW_CITATION_ERROR MEDIUM·UNVERIFIED `ABBREVIATION_UNRESOLVED`(후보 표시). 명세 판정 UNVERIFIABLE. 어간 4자 이상 미발견은 지금처럼 CRITICAL(가짜 법률 대조 유지).
  2. `canonical_law_name`: 별칭 + 시행령·시행규칙 → 정식 모법명 + 종류.
  3. 두 글자 어간: 첫 글자 초성의 현행 법령 사전식 목록(`target=law&gana=…`, 최대 20쪽)에서 글자 순서 일치(줄임말 글자는 정식명의 짝수 위치 = 말마디 첫 음절 근사)로 하나만 고른다. 모호·상한·실패는 1번으로.
  4. 새 시험 `tests/test_tk143_short_abbreviation.py` 8건(합성 법령명). 별칭표(닫힌 목록)는 늘리지 않는다(탐침 맞춤 방지).
- 미검증: 사전식 검색(`gana`)의 실제 응답 범위·쪽수(OC 키 없음). 실패해도 1번 안전 장치로 CRITICAL은 나지 않는다.

## TK-144 (P1) DOCX 표가 표 구조로 나오지 않음
- 수정본 `patches/TK-144_docx_tables_on_7b41c7d.diff`(2개 파일 +188/−1)
- 원인: `document_engine/docx_parser.py`가 표 칸 문단을 table 블록(`table_ref`)으로만 내고 `structure["tables"]`를 만들지 않는다 → 표 검산(`_verify_cell_tables`)·비율·사실 저장소가 DOCX 표에서 동작하지 않음(평가 측 재현).
- 수정: `_docx_table_structures` — w:tbl을 행·열 표로(gridSpan 가로 병합·vMerge 세로 병합, 앵커 칸만 값), 칸 글자는 그 칸에 직접 딸린 문단만, `line_block_ids`로 칸 블록 연결(LINES_WITH_STRUCTURE, 표 블록 새로 만들지 않음), 상한 행 2000·열 100·문서 200,000칸, 실패 시 경고·본문 유지. 새 시험 5건.

## TK-145 (P2) 같은 판례를 같은 문단에서 다시 인용하면 합쳐짐
- 수정본 `patches/TK-145_repeated_case_citation_on_7b41c7d.diff`(4개 파일 +89/−3)
- 원인
  1. `citation_extractor.extract_citations` `select_body`: (인용 식별, 블록) 키로 중복을 지워, 같은 블록의 같은 판례 두 번째 인용(다른 인용문)이 통째로 버려진다 → 지어낸 인용문을 대조하지 않음.
  2. `opinion_attribution.FINAL_NEGATION_RE`에 '…하여서는 안 된다'(안 되)가 없어 판시 방향 검사가 서면을 '적극'으로 읽음 → 정상 인용에 판시 방향 반대 오탐(운영 문단 글자로 재현).
  3. 상대방 주장 문장('원고는 … 원용하면서 … 주장한다')도 서면 주장으로 대조된다.
- 수정: 인용이 든 문장의 첫 직접 인용문(`_occurrence_quote`)이 새로우면 별도 인용으로 둔다(같은 인용문 반복은 지금처럼 하나) · 부정 표지에 '안 되/안 돼/안된' 추가 · `_OPPONENT_CLAIM_RE`(당사자 + 주장·원용)면 판시 방향 대조에서 뺀다. 새 시험 5건.

## TK-146 (P2) 표 비율 오류 진단
- 수정본 `patches/TK-146_table_percentage_on_7b41c7d.diff`(2개 파일 +49/−1)
- 원인(`claim_engine/calculation.py`): `_verify_percentages`가 단위 없는 금액 칸('1,200,000')과 % 기호 없는 비율 칸('25')을 읽지 못해 행 비율 검사가 돌지 않고, `_verify_cell_tables`가 비율 열을 금액 열로 더해 '차이 5원'을 낸다.
- 수정: 비율 머리글 열은 금액 합계 검산에서 뺀다 · 비율 머리글이면 기호 없는 수도 비율로 · 금액은 `parse_cell_amount`로 보완. 새 시험 4건.

## 평가 측 사전 검증(평가 측 재실행)
- 티켓별 새 시험: TK-143 8/8, TK-144 5/5(원래 4 실패), TK-145 5/5(원래 3 실패), TK-146 4/4(원래 2 실패).
- 관련 기존 시험: TK-143 19개 파일, TK-144 44개 파일, TK-145 39개 파일(TK-72 출력 호환 포함 — 1판에서 같은 인용문 반복이 2건으로 늘던 것을 고침), TK-146 산식 관련 파일 — 실패 0.
- 온라인 탐침 재현: B-P1 판시 방향 오탐이 운영 문단 글자로 기존 코드에서 재현되고 수정본에서 사라짐, B-C2 지어낸 인용문이 별도 인용으로 추출됨. D 표(병합 머리글·두 문단 칸) 꼴 합성 DOCX에서 합계 1건·오탐 0, 비율 오류 행 진단.
- 문구 대조·하드코딩·시험 수정·보호 경로 점검 통과(티켓별).
- 합본 verify_all·은퇴 비교: 아래 '검증 결과'.
- 범위 밖: 지각 범위 진술(EVI-LOGIC) 놓친 꼴은 TK-76 3주기 'EVI-LOGIC 잔여'. 반대의견 귀속 결정적 검사 미작동은 원인 미확인(실제 판결 의견 표지 꼴 확인 필요, TK-135 후속).
