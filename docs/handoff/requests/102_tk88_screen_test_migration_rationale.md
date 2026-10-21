# TK-88: 기존 화면 시험(F2)의 3단 분리에 따른 검증 위치 변경 대응표

- **문서 번호:** `requests/102_tk88_screen_test_migration_rationale.md`
- **작성일:** 2026-10-22
- **작성자:** Antigravity (구현 에이전트)
- **대상 티켓:** TK-88 (검토 화면 3단 체계 개편)
- **관련 시험:** `tests/test_f2_review_screen_browser.py`

---

## 1. 개편 배경 및 시험 조정 사유

TK-88은 기존의 '검증·검토' 단일 표에 혼재되어 있던 항목들을:
- **[2단] 판례·법령·주요참고문헌 인용 오류·미확인 검토 (`#aiVerificationRows`)**: 출처 부존재, 불성립 사건번호, 원문 어절 불일치 등 객관적 출처 오류
- **[3단] 법률적으로 무리한 주장 (`#tier3Rows`)**: 출처 취지 왜곡/부당 원용, 사실관계 상이/일자 모순, 참고자료 모순, AI 환각 주장
으로 명확하게 2개의 분리된 4열 표로 개편합니다.
(평가 측 2차 판정 지침에 따라, 보호 시험 `test_t2r_every_finding_title_is_visible_in_ai_tab_or_review_tab`과의 완전한 정합성을 위해 3단 표를 검증·검토(`section[data-panel="review"]`) 탭 내부 하단 별도 구역으로 배치하여 정보 손실 0 및 화면 도달성을 확보하였습니다.)

기존 `tests/test_f2_review_screen_browser.py`는 단일 표 시절의 3개 합성 항목(`d1_CITATION_cit_1`: 인용 행, `d1_FINDING_f_fact_1`: 일자 선후 모순 행, `d1_CITATION_cit_pure`: 순수 인용 행)이 모두 `#aiVerificationRows` 하나에 노출될 것을 전제로 작성되었습니다.
TK-88 개편에 따라 인용 2건은 2단 표로, 사실관계 모순 1건은 3단 표로 정확히 분리 배치되므로, 시험의 검증 대상을 2단과 3단 각각의 위치로 정비합니다. 전체 3개 항목에 대한 요약 블록, 사유 축약, 필터링 등 원래 시험이 검증하던 모든 요구조건은 일절 약화 없이 온전히 보존됩니다.

---

## 2. '전에 확인하던 요구 → 새 확인 위치' 대응표

| 기존 시험 및 행 번호 | 전에 확인하던 요구 | 새 확인 위치 및 단언 방식 | 변경 사유 및 검증 동일성 보장 |
|---|---|---|---|
| `test_f2_review_table_renders_four_columns`<br>(371~380행) | `.review-items-table thead th` 4열 머리글 노출 확인 (`to_have_count(4)`) | 2단 표 `.review-items-table thead th` 4열 검증 및 3단 표 `.tier3-table thead th` 4열 별도 검증 | 동일 탭('검증·검토') 내에 2단 표와 3단 표가 함께 배치됨에 따라, 3단 표 클래스를 `.tier3-table`로 한정 분리하고 2단 표(4열) 및 3단 표(4열: 위치/주장/법리검토/확인필요) 각각의 머리글 구조를 독립 검증. |
| `test_f2_review_table_renders_four_columns`<br>(380~382행) | `#aiVerificationRows tr`에서 3개 행 전수 노출 확인 (`to_have_count(3)`) | 2단 `#aiVerificationRows tr`에서 2개 행(인용 행) 확인 + 3단 `#tier3Rows tr`에서 1개 행(사실관계 행) 확인, 총합 3개 행 누락 없음 검증 | 2단 표와 3단 표로 분리 배치됨에 따라 각 단의 행 수(2단 2행, 3단 1행) 및 전체 합계(3행)를 교차 검증하여 항목 유실 0 보장. |
| `test_f2_review_summary_box_renders_instead_of_inline_workflow`<br>(410~413행) | `#aiVerificationRows`의 3개 행 각각에 4열 확인 요약 박스(`.review-summary-box`) 노출 검증 | 2단 표의 2개 행 및 3단 표의 1개 행 각각에서 4열 확인 요약 박스(`.review-summary-box`)가 노출됨을 검증 | 2단뿐만 아니라 3단으로 분리된 사실관계 행에서도 동일한 4열 확인 요약 박스가 정상 렌더링됨을 전수 확인. |
| `test_f2_review_summary_reason_truncation_and_location_display`<br>(462~465행) | 3번째 행(`rows.nth(2)`)에서 '헌법 제10조' 확인 방법 텍스트("헌법 제10조 원문 대조 (1쪽)") 검증 | 2단 표 2번째 행(`rows.nth(1)`)에서 '헌법 제10조' 확인 방법 텍스트 검증 | 사실관계 행이 3단 표로 이동함에 따라 2단 표에는 인용 2건만 남게 되어 '헌법 제10조' 행의 인덱스가 2에서 1로 이동함. 동일한 텍스트 및 분기 검증 유지. |
| `test_f2_filters_search_severity_review_status`<br>(478~496행) | 2단 `#aiVerificationRows` 기준 3행 노출 및 '선후 모순' 검색 시 1행 매칭 확인 | 2단 표 2행 노출 확인, CRITICAL 필터 1행 확인, '선후 모순' 검색어는 해당 항목이 소속된 3단 표(`#tier3Rows`)에서 1행 매칭 확인 | '일자 선후 모순' 항목이 표 1 원칙에 따라 3단 표에 배치되었으므로 검색 대상 위치를 3단 표로 갱신하여 검색 기능 온전성 검증. |

---

## 3. 검증 결과
- `tests/test_f2_review_screen_browser.py`: 8/8 pass
- `tests/test_f1_ai_security_tab_browser.py`: pass
- `tests/test_tk88_three_tier_review.py`: 표 1 10개 행 브라우저 렌더링 검증 포함 전원 통과
