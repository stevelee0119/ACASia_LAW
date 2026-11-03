# TK-134 자치법규(조례·규칙) 조회와 조례 판정 분기 (P2, 결함 수정, 평가 측 수정본)

- 결정: 2026-11-03 사용자 '다음 릴리스 범위'·'A1~A3 + B1 설계 메모 진행'. 배정 Antigravity.
- 기준: Steve `892bbd8`. 수정본 `patches/TK-134_ordinance_lookup_on_892bbd8.diff`(3개 파일 +365/−1, 11-03 2판).

## 1. 원인(`892bbd8`)

1. `source_adapters/law_go_kr.py`는 `target=law`(법령)만 조회한다. 자치법규(`target=ordin`) 조회가 없다.
2. `legal_engine/source_review.py` `_is_statute_form`(344행)이 '조례'를 일반 법령 꼴로 본다.
3. 그래서 법령 목록에 없는 조례(정상)는 `_law_absent` 3분기(489행~)로 가서 STATUTE_NONEXISTENT **CRITICAL**이 된다. 실재하는 조례도 같다.

## 2. 공식 API(법제처 공동활용 가이드, 2026-11-03 평가 측 확인)

- 목록: `https://www.law.go.kr/DRF/lawSearch.do?target=ordin&OC=…&type=JSON&query=…` — 필드 자치법규일련번호·자치법규명·자치법규ID·공포일자·시행일자·지자체기관명·자치법규종류 등.
  - 출처: <https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=ordinListGuide>
- 본문: `https://www.law.go.kr/DRF/lawService.do?target=ordin&ID=…`(또는 `MST=`) — 필드 조문번호·조문여부(조 Y, 편·장·절 N)·조제목·조내용 등.
  - 출처: <https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=ordinInfoGuide>
- **미검증**: JSON 최상위 키 이름과 조문번호 자릿수 형식. 이 세션에 OC 키가 없어 실제 응답을 받지 못했다. 수정본은 구조에 기대지 않고 '자치법규명'을 가진 항목을 재귀로 모으고, 조문번호는 '3'과 '000300'(조 4자리+가지 2자리) 둘 다 받는다.

## 3. 수정(수정본 내용)

1. `law_go_kr.py`
   - `search_ordinance(name)`: 목록 조회. 이름(공백·낫표 무시)이 정확히 같은 것만 `exact`. 없으면 이름 끝이 같은 것(6자 이상)을 `suffix`로 돌려준다(서면이 지자체 이름을 뺀 경우).
   - `fetch_ordinance_articles(record)`: 본문 조문번호 목록. 조문여부 N(편·장·절)은 뺀다. 실패하면 None.
   - 응답 형식이 맞지 않으면 ERROR(부존재로 보지 않음).
2. `source_review.py`
   - `_is_ordinance_form`: '조례'로 끝나거나, 첫 어절이 지자체 이름(…시·군·구·도·특별시·광역시·특별자치시·특별자치도)이고 '규칙'으로 끝나는 이름('시행규칙' 제외).
   - `_law_absent`에 2-1분기: 자치법규 꼴이면 `_ordinance_lookup`으로 판정하고 3분기(CRITICAL)로 가지 않는다.
   - `_ordinance_lookup`
     - 조회 실패: UNVERIFIED(`_unverified_finding`), 부존재 아님.
     - 정확 일치 1건: PARTIALLY_VERIFIED, existence `VERIFIED`(기존 어휘), `review.ordinance_lookup.source=ORDINANCE_LIST`. 조문이 있으면 본문 조문번호와 대조(있음 VERIFIED, 없음 LAW_CITATION_ERROR **HIGH** `ORDINANCE_ARTICLE_NOT_FOUND`, 본문 실패 UNVERIFIED).
     - 여러 건(지자체 미기재 등): PARTIALLY_VERIFIED, existence `PARTIALLY_VERIFIED`, `review.ordinance_lookup.ambiguous=True`, 결과 없음(사람이 고름).
     - 목록에 없음: STATUTE_NONEXISTENT **HIGH**(CRITICAL 아님), `NOT_FOUND_ORDINANCE`, '부존재 확정 아님'.
   - `verify_statute_source`: 자치법규 꼴은 TK-130b 약칭 추정(`_infer_abbreviation`)을 건너뛴다.
3. 새 시험 `tests/test_tk134_ordinance_lookup.py` 10건(가이드 필드 이름으로 만든 합성 응답).

### 2판 정정(11-03, 기존 코드와의 충돌 점검에서 발견)

1. 1판은 새 판정 이름(`VERIFIED_IN_ORDINANCE_LIST`·`AMBIGUOUS_IN_ORDINANCE_LIST`)을 만들었다. `spec_mapping.spec_source_verdict`와 `components._MEANING`에 등록되지 않아, 실재 조례가 명세 판정 NOT_FOUND·화면 '확인하지 못함'으로 나왔다(재현 확인). 기존 어휘로 바꾸고, 명세·구성요소 판정을 시험으로 고정했다(실재 PARTIAL·CONFIRMED, 여럿 UNVERIFIABLE·PARTIAL, 미발견 NOT_FOUND·NOT_FOUND_IN_SEARCHED_SCOPE).
2. 조례 이름이 TK-130b 약칭 추정 단계를 먼저 거쳐 국가 법령으로 추정될 수 있었다. 자치법규 꼴은 건너뛴다(시험 추가).

## 4. 평가 측 사전 검증(평가 측 재실행, 저장소 밖 사본)

- 새 시험 10/10 통과(2판).
- 관련 기존 시험(law_go_kr·source_review·NOT_FOUND_LAW·STATUTE_NONEXISTENT를 쓰는 시험 전부) 통과, 실패 0.
- 문구 대조 '의심 없음', 하드코딩·시험 수정·보호 경로 점검 통과.
- 국가 법령 꼴(…법) 미발견은 그대로 NOT_FOUND_LAW CRITICAL(시험으로 고정).
- verify_all 전체 모드는 TK-135와 같은 방식으로 '검증 결과'에 적는다.

## 5. 구현 측 추가 제출(필수)

- OC 키로 받은 **실제 응답 2건**(목록 1, 본문 1)의 구조 요약: 최상위 키, 항목 배열 키, 조문번호 예 형식. 개인정보·OC 값은 가린다.
- 실제 형식이 수정본 가정과 다르면 정규화만 고치고 시험에 실제 형식 사례를 하나 더한다. 판정 분기는 바꾸지 않는다.

## 6. 수용

- diff = 수정본(+ 5절 형식 보정).
- 필수 CI 전부 성공, 기존 시험 수정 0, 고정 변화 0, 은퇴 하락·오탐 증가 0.
- 실재 조례 CRITICAL 0, 조회 실패는 UNVERIFIED, 국가 법령 판정 불변.

### 검증 결과(11-03, 평가 측 재실행, 2판 사본)

- verify_all 전체 모드: 수용 1,237·회귀 장부 2,357·브라우저 197 통과, 고정 dev 82.6/holdout 81.9/오탐 0/A 0(변화 0), 점수·회귀·하드코딩·시험 수정·보호 경로·버전 정책 통과.
- 전체 시험 9,225 통과·2 실패(`test_tk88_three_tier_review` PDF 소제목, `test_v5_ocr_dates` 회전 스캔). 수정 전 기준 코드에서도 같은 실패였다. 원인: 컨테이너 재시작으로 한글 글꼴 `fonts-nanum`(CI 설치) 누락. 설치 뒤 기준·2판 모두 통과.
- 은퇴 5세트 비교(`retired_compare.py --base 892bbd8`): 53.3/46.8/53.4/45.8/29.5 → 같음, 오탐 0/A 0, 후퇴 없음. 오프라인에는 공식 원문·OC가 없어 새 분기가 실행되지 않는다. 효과는 온라인 탐침(F)으로 잰다.

### #212 판정 — 보완 1건(PR 본문 정정, 코드 변경 없음) (11-03, head `b3e6eae`)
- 코드 diff = 2판 수정본. 필수 CI 전부 성공(CI 결과 인용). 평가 측 재실행: 새 시험 10/10(PR head).
- **불승인 사유(본문)**: '구현 측 추가 제출: 실제 응답 구조 요약'이 실제 응답이 아니다.
  1. 예시 자치법규명이 평가 측 합성 시험 자료의 가상 지자체 이름과 같고, 일련번호·ID가 자리표시 값이다.
  2. 근거로 든 함수 `_collect_named_records`는 수정본에 없다(실제 이름 `_ordinance_items`).
  3. 따라서 최상위 키 `ordinSearch`·`ordinService`, 배열 키 `조문.조문단위` 주장도 근거가 없다.
- 평가 측 확인(11-03): 법제처 공개 샘플 URL(OC=test)은 '사용자 정보 검증에 실패' JSON(`result`·`msg` 키)을 돌려준다. 이 실제 거부 응답은 수정본에서 형식 불일치 → 조회 실패(UNVERIFIED)로 처리되어 부존재로 오판하지 않는다(PR head 재실행 확인). 실제 정상 응답 형식은 여전히 미검증.
- 요구: PR 본문 해당 절을 사실대로 고친다(실제 응답을 받았으면 원문 구조, 못 받았으면 '미확인'과 사유). 코드는 바꾸지 않는다. 실제 형식은 배포 뒤 온라인 점검 항목으로 둔다.
