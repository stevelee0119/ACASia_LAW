# TK-127 주요참고문헌(Drive) 대조 결과를 상단 표의 근거로 통합 (P1, 사용자 요구 미이행)
- 근거: 사용자 개선안(2026-10-19) 3다, 사용자 지적(2026-10-25 두 차례). 기준 SHA Steve `b68e70f`.
- 분류: `changed`. **사용자 확인 뒤 수용.** 1단계(화면 통합)는 엔진을 바꾸지 않으므로 탐지 diff 0. 2단계(인용 행의 Drive 조회)는 엔진 변경이라 설계 메모 먼저.
- 같은 PR: TK-126·128. 사전 검증 수정본: `docs/handoff/patches/TK-126-128_prevalidated_b68e70f.diff`.

## 사용자 원문
- (10-19, 3다) "주요참고문헌 검토 결과는 현재 클릭을 해야만 상세하게 볼 수 있는데, 주요참고문헌을 검토하는 것은 공신력이 있고 검증된 자료를 제시하고 이를 기반으로 검색해 오류를 최소화하기 위해서야. 하단부에 따로 별도로 설명하지 말고, 위의 표에 각 서면의 내용을 판례, 법령등과 동일한 근거 자료로서 활용하고, 그 내용에 부합하거나 부합하지 않는 내용이 있다면 판례 인용 오류·미확인 검토 (AI 작성 여부 판단과 별개) 부분의 표에 함께 정리해줘."
- (10-25, 3) "주요참고문헌 검토 결과를 별도로 하단 부에 두지 말고, 같은 페이지 상단의 표에 있는 주요 내용들을 검증하는 자료로서 공식데이터베이스의 자료를 API로 검색하는 것에 추가로 구글 DRIVE의 자료를 활용하도록 한 다음 상단표와 통합해서 정리하도록 기능 개선을 요구했는데 구현되지 않았어."
- (10-25, 사전 검증 화면을 본 뒤) "주요참고문헌 검토결과는 데이터베이스로 활용하고 상단 표 내용작성시에 활용하도록 요구한 것과 달리 여전히 하단에 별도로 있는 것 같아."

## 원인(평가 측 코드 확인, `b68e70f`)
1. Drive 대조 결과는 문서별 `engine_data.rag.observations`(항목: `claim_id`·`claim_quote`·`source_id`·`source_quote`·`relationship`·`explanation`)에 있는데, 화면은 이것을 `app.js` `referenceSection`(1073~1195행)에서 문서별 접힘 목록으로만 그리고, `renderFindings` 2464행이 그 절을 표 **아래** `#reviewReferencesContainer`에 붙인다. 표의 행(`review_items`)과 잇는 코드가 없다.
2. 표에 올라가는 것은 CONTRADICTS 중 결과(finding)로 승격된 것(`RAG.REFERENCE_CONTRADICTION`, TK-70)뿐이다. 부합·맥락·근거 부족은 표에 없다.
3. TK-88이 '화면 배치만, 탐지 diff 0'으로 좁혀 발행되어 이 요구가 빠졌다(평가 측 원인).

## 원문 대응표 (수용 기준)
| # | 원문 | 확인할 화면·동작 |
|---|---|---|
| 1 | 하단부에 따로 두지 않음 | 표 아래 '주요 참고문헌 검토 결과(RAG)' 절이 없다. 표 **위** 한 줄 상태('주요 참고문헌 대조: 색인 n/m건 · 표의 행에 반영한 의견 k건 · 별도 행 j건')만 있고, 펼치면 처리 기록(동기화·색인·자료별 기록)이 나온다. 3번째 탭에는 같은 요약 한 줄만 있다 |
| 2 | 판례·법령과 같은 근거로 표 작성에 활용 | 대조 의견이 연결되는 행의 3열에 '주요 참고문헌 대조 (참고문헌·구속력 없음, 공식 확인 아님)' 상자: 부합/불부합/맥락 참고/근거 부족 배지 · 자료 이름 · 쪽 · AI 참고 의견 · 발췌(접힘) |
| 3 | 부합하거나 부합하지 않는 내용을 표에 정리 | 연결할 행이 없는 의견도 버리지 않는다: 불부합은 '법률적으로 무리한 주장' 표에 '참고문헌과 불부합' 행, 나머지는 '출처가 확인되지 않는 항목' 표에 '참고문헌 대조 의견' 행(배지 '참고문헌(구속력 없음)') |
| 4 | 공식 DB API 검색에 더해 Drive 자료로 인용 행 확인 | **2단계(엔진, 설계 메모 먼저)**: 인용 행의 사건번호·법령명·조문으로 Drive 색인을 찾아 발췌를 붙인다. 공식 확인으로 올리지 않는다 |

## 고칠 것 — 1단계(화면, 사전 검증 완료, `b68e70f` 기준)
1. **행 연결 함수** `attachReferenceObservations(items, docs)`를 `classifyReviewItemTier`(1927행) 앞에 둔다. 연결 순서:
   ① 의견의 `claim_id` → 문서 `claims[]`의 `citation_ids` → 행의 `citation_id`(같은 문서 안에서만).
   ② 실패하면 `claim_quote`와 행 `claim_text`를 공백 제거 후 포함 관계로 비교(둘 다 8자 이상일 때만; 짧은 문장끼리 우연 일치 방지).
   연결된 의견은 `item.reference_observations`에 넣고, 못 붙인 것은 돌려준다.
2. **연결 못 한 의견 행** `referenceObservationRow`: `kind:"REFERENCE"`, `reference_library:true`, `tier`를 직접 준다(CONTRADICTS → 3, 그 밖 → 2). `classifyReviewItemTier`는 `item.tier`를 먼저 본다(1929행).
3. **행 표시** `referenceObservationBlock`: `renderReviewRow`의 3열, `context_review` 블록(2103행) 앞에 붙인다. 배지 대응 SUPPORTS=부합, CONTRADICTS=불부합, CONTEXT=맥락 참고, INSUFFICIENT=근거 부족. 자료 쪽 표기는 `page_numbers_reliable === false`이면 '텍스트 구간 n'.
4. **renderFindings**: 2336행(`// 판례 통계 요약 갱신`) 앞에서 연결·행 추가를 하고(필터·정렬 전), 2464~2465행 `referenceSection(docs)` 붙이기를 지운다. 대신 `referenceStatusLine(docs, 별도행수, withDetails)`를 `#referenceStatus`(review 패널 `hallucinationSection` 뒤)와 `#legalReferenceStatus`(3단 안내 뒤, 요약 한 줄만 — 같은 상세를 두 번 그리면 id·문구가 겹친다)에 그린다. `referenceSection` 함수 본문은 그대로 두고 상세 안에서 재사용한다(정보 손실 0). '추가 관련 법조문 검토'(`related_authorities`)는 이번 범위가 아니라 그 자리에 남긴다.
5. 서버 쪽 정식 연결(`review_items` 생성 시 `reference_observations` 필드)로 옮기는 것은 2단계 설계 메모에 포함한다(화면 연결과 결과가 같아야 한다).

## 시험
- 새 `tests/test_tk126_flat_tabs_answer_import.py::test_rag_observations_attach_to_rows_and_bottom_section_is_gone`: claim_id 연결 행에 '불부합'·'표준판례집 · 12쪽', 하단 `.reference-section` 0개, 상태 줄 '표의 행에 반영한 의견 1건', 연결 못 한 불부합 의견이 3번째 탭 행으로.
- 기존 단언 이동(평가 측 개정, 수정본에 포함): `test_frontend_citation_groups.py`·`test_frontend_summary_compact.py`·`test_f2_review_screen_browser.py`·`test_drive_rag_relevance.py`(10-25 보충)는 `#referenceStatus summary`를 먼저 펼친다.

## 2단계 설계 메모에 담을 것 (승인 전 구현 금지)
1. 인용 행의 Drive 조회: 질의(사건번호·법령명·조문 정규화), 색인 범위 한계, 발췌 길이, 외부 모델 미사용 시 로컬 검색만.
2. `review_items`에 `reference_observations` 필드를 서버에서 채우는 방식(1단계 화면 연결 규칙과 동일).
3. 보고서 7형식에 같은 칸을 넣을지.
4. 측정: 오프라인 세트로는 Drive 효과를 잴 수 없다. 운영 Drive로 사용자 실제 서면 1건 이상의 화면 캡처로 확인.

## 수용 기준
- 원문 대응표 1~3을 평가 측 화면 캡처로 확인한 뒤 **사용자 확인**. 탐지 diff 0. 4는 2단계.
