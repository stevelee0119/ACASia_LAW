# TK-90 EVI-INCONS 단위 시험 이전 및 명칭 변경 승인 요청서 (Y9)

## 1. 개요 및 배경
- 지시 사항: B-3 4차 보완 지시 Y9 (push 실행 `check_test_edits` 실패 해소 절차).
- 원인: `cb21298`에서 `test_evi_incons_internal.py`의 옛 시험 15개(산식 양성 3, 지위·조항 양성 2, 대조 1~10)가 T1(병렬 산식 삭제) 및 3차 T2~T8 지시(속성별 3변형 확장 및 명칭 체계화)를 반영하는 과정에서 명칭이 변경되거나 전담 모듈(`calculation.py`)로 이전되었습니다.
- 목적: 본 요청서를 통해 옛 시험 15개의 이전 및 명칭 변경 사유와 대응 관계를 명시하고 평가 측의 사전 승인을 요청합니다.

## 2. 옛 시험 15개 → 새 시험 대응표

| 번호 | 옛 시험 이름 (`90f56b3`) | 새 시험 이름 (`cb21298` / 현행) | 새 파일 위치 | 변경 및 이전 사유 |
|:---:|:---|:---|:---|:---|
| 1 | `test_positive_arithmetic_multiplier_mismatch` | `test_calculation_comma_number_times_integer_mismatch` | `tests/test_calculation_leading_multiplier.py` | T1 지시: EVI-INCONS 내 병렬 산식 검사 삭제 및 `calculation.py` 전담 이전 |
| 2 | `test_positive_arithmetic_addition_mismatch` | `test_calculation_integer_times_comma_number_with_josa` | `tests/test_calculation_leading_multiplier.py` | T1 지시: EVI-INCONS 내 병렬 산식 검사 삭제 및 `calculation.py` 전담 이전 |
| 3 | `test_positive_arithmetic_subtraction_mismatch` | `test_calculation_unit_amount_times_count_with_predicate` | `tests/test_calculation_leading_multiplier.py` | T1 지시: EVI-INCONS 내 병렬 산식 검사 삭제 및 `calculation.py` 전담 이전 |
| 4 | `test_positive_party_role_inversion` | `test_positive_party_role_inconsistency_3_variants` | `tests/test_evi_incons_internal.py` | T8 지시: 당사자 지위 역전 3항 구조 3변형(임대인/임차인, 매도인/매수인, 도급인/수급인)으로 확장 |
| 5 | `test_positive_exhibit_clause_contradiction` | `test_positive_exhibit_clause_contradiction_3_variants` | `tests/test_evi_incons_internal.py` | 동일 서증 조항 상반 원용(면제 ↔ 부과) 3변형으로 확장 |
| 6 | `test_control_1_partial_amount_vs_total` | `test_control_partial_amount_vs_total` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (번호 접두어 제거) |
| 7 | `test_control_2_incident_date_vs_subsequent_date` | `test_control_incident_date_vs_subsequent_date` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화. Y3 구조 규칙(사건 술어 결합) 도입 후에도 정상 통과 |
| 8 | `test_control_3_sublease_multiple_roles` | `test_control_sublease_multiple_roles` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (전대차 정상 복수 지위 대조군) |
| 9 | `test_control_4_correction_filter` | `test_control_correction_filter` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (오기 정정 필터 대조군) |
| 10 | `test_control_5_primary_vs_alternative_claim` | `test_control_primary_vs_alternative_claim` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (주위적·예비적 청구 대조군) |
| 11 | `test_control_6_different_exhibit_clauses` | `test_control_different_exhibit_clauses` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (상이한 서증 조항 대조군) |
| 12 | `test_control_7_non_exclusive_location_movement` | `test_control_non_exclusive_location_movement` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (비배타적 일반 이동 대조군) |
| 13 | `test_control_8_joint_multiple_signers` | `test_control_joint_multiple_signers` | `tests/test_evi_incons_internal.py` | 대조군 명칭 정규화 (공동 서명자 정상 서술 대조군) |
| 14 | `test_control_9_opponent_claim_citation` | `test_control_t2_opponent_claim_citation_claims`, `test_control_t2_opponent_claim_citation_dispute`, `test_control_t2_opponent_claim_citation_retraction` | `tests/test_evi_incons_internal.py` | T2 지시: 상대방 주장 인용 3꼴('주장합니다', '다툽니다', '번복합니다')로 확장 분리 |
| 15 | `test_control_10_valid_arithmetic_formula` | `test_control_t1_no_internal_arithmetic_detection` | `tests/test_evi_incons_internal.py` | T1 지시: EVI-INCONS 모듈 내 산식 미검출 확인 대조군으로 전환 |

## 3. 검증 결과
- `tests/test_calculation_leading_multiplier.py`: 13 passed (100% 통과, 이전된 산식 시험 포함).
- `tests/test_evi_incons_internal.py`: 40 passed (100% 통과, 확장된 3변형 및 대조군 전체 통과).
- Y3 구조 규칙 전환에 따라 후속 사건 배제 목록(`_INCIDENT_DATE_EXCLUDE_RE`)을 삭제한 뒤에도 사고일-치료일 대조군 시험(`test_control_incident_date_vs_subsequent_date` 및 `test_y3_date_event_predicate_and_exclude_removal`)이 완벽하게 통과함을 확인하였습니다.

Agent: implementer
