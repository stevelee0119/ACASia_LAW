# TK-138 구현 PR 판정 기록

## #231 1차 판정: 보완 1회 (11-04, head `02b26e9`, 기준 Steve `996ba14`)
- CI 결과 인용: 필수 확인 전부 성공. 평가 측 재실행: 관련 시험 65개 파일(argument_validity·claim_review·search_case·_semantic_review·related_authorities·input_contract·inspect_request) 5,072건 통과·5 건너뜀(PR·사본 같음), 하드코딩·시험 약화 점검 통과. verify_all 전체는 수용 SHA에서(입력 계약 변경 포함).
- 실제 법제처 응답(평가 측, http, 값 미기록): org=400201 대법원 한정 근로기준법 제23조 379건·민법 제750조 215건·주택임대차보호법 제3조 264건 중 100건, 판결유형으로 전원합의체 식별, 본문 상세 요지 수신 동작. 두 질의 실행: PR 상세 6회·12.4초 → 사본 상세 3회·7.1초.
- 결함(평가 측 재현): H1 판례 제공 시 무리한 주장 AI 교차검토 요청이 입력 계약 위반으로 차단(`INPUT_CONTRACT_VIOLATION`), H2 의견 키 변경으로 AI 의견 근거 빈칸(회귀), H3 둘째 항목부터 자기 인용 사건번호를 목록 밖으로, H4 목록 없는 문서에도 목록 밖 판정, H5 목록 밖 사건번호가 화면 글에 남음, H7 상세 조회 문서당 최대 6건.
- 평가 측 사본 증분: [patches/TK-138_impl_fix_on_02b26e9.diff](patches/TK-138_impl_fix_on_02b26e9.diff)(평가 측 시험 5건: 02b26e9에서 5/5 실패, 사본 통과). 화면 캡처(사본, 1280·390px, 긴 사건명): [captures/TK-138/](captures/TK-138/).
- U5 문구(범위 표시 반복·괄호 겹침)는 사용자 확인 사항 — 사본 미적용(미검증).

## 보완 지시 전문

```
[평가 측 보완 지시 — #231 TK-138 관련 판례·권위 가중 (head 02b26e9, 기준 Steve 996ba14), 11-04]

판정: 보완 1회. U1·U2·U3(추출 규칙)·U4 반영은 확인. 실제 법제처 응답(평가 측, http)에서 org=400201 대법원 한정(근로기준법 제23조 379건·민법 제750조 215건·주택임대차보호법 제3조 264건 중 100건), 판결유형으로 전원합의체 식별, 본문 상세 요지 수신 모두 동작한다. 그러나 이 기능의 유일한 소비 경로(무리한 주장 AI 교차검토)가 막히고 기존 화면이 회귀한다. CI 결과 인용: 필수 확인 전부 성공. 평가 측 재실행: 관련 시험 65개 파일 5,072건 통과(PR·사본 같음) — 아래 결함은 기존 시험이 잡지 못한다.

원인과 고칠 것 (줄 번호는 02b26e9 기준)

H1 [치명] 판례를 주면 AI 교차검토 요청이 입력 계약 위반으로 차단 — argument_validity_verifier.py 634행, llm_router/input_contracts.py 50행
- 원인: 항목에 새 키 "관련 권위 판례(참고)"를 넣었지만 argument_review_v1의 _ARGUMENT_ITEM은 닫힌 객체라 모르는 키가 있으면 valid_input_contract가 거짓이다. 평가 측 재현: 판례 1건 제공 시 inspect_request = BLOCKED, failure_code INPUT_CONTRACT_VIOLATION, retryable False. 판례가 있는 문서는 모델에 아무것도 가지 않고 기존 AI 의견도 사라진다.
- 고칠 것: _ARGUMENT_ITEM에 "관련 권위 판례(참고)": str를 넣고 optional에 추가한다. 값은 지금처럼 hide()를 거친다.

H2 [회귀] AI 의견 근거가 화면·DOCX·PDF에서 빈칸 — 703행
- 원인: 의견 dict 키를 "reasoning"에서 "legal_reasoning"으로 바꿨다. reasoning_format.py 47행과 app.js 2952행은 "reasoning"을 읽는다. TK-138과 무관한 모든 문서의 AI 의견 근거가 사라진다(평가 측 재현).
- 고칠 것: 키 "reasoning" 유지.

H3 [오탐] 둘째 항목부터 서면 자신의 인용 사건번호를 '목록 밖'으로 판정 — 685~686행
- 원인: item_match = next(첫 항목)이라 모든 항목이 첫 항목의 사건번호만 제외한다. 평가 측 재현: 항목 2의 모델 답이 항목 2의 인용 판례를 말하면 '판단 불가'로 바뀐다.
- 고칠 것: item_id(1부터, enumerate 순서)로 unverified_cases[item_id-1]을 고르고, 그 인용 raw_text에서 extract_all_case_numbers로 뽑은 사건번호 전부를 제외 집합으로 쓴다.

H4 [범위] 판례 목록을 주지 않은 문서에도 '목록 밖' 판정 — 679~696행
- 원인: precedents가 없으면(오프라인·QUICK·법령 인용 없음·검색 0건) 제공 집합이 비어 모델 답의 다른 사건번호가 모두 '목록 밖'이 되어 기존 온라인 판정이 바뀐다. P5의 OFF/ON 측정에서 TK-138 효과를 분리할 수 없다.
- 고칠 것: provided_case_numbers가 비어 있지 않을 때만 대조한다.

H5 [메모 2.4 '제거' 미이행] 목록 밖 사건번호가 화면 근거 글에 그대로 남음 — 693~694행
- 고칠 것: 목록 밖 사건번호를 claim_text·reasoning·check에서 '[제공 목록 밖 사건번호 제거]'로 바꾼다(공백 낀 꼴 포함: rf"{y}\s*{c}\s*0*{n}(?!\d)"). 머리표 '[UNVERIFIED_INVENTED_IN_RESPONSE] 제공 목록 밖 사건번호 N건 인용 배제.'와 감사용 unprovided_case_numbers는 남긴다. verdict '판단 불가' 유지.

H7 [메모 2.5 초과] 본문 상세 조회가 문서당 최대 6건 — related_authorities.py 579~593행
- 원인: 질의 2개 × 상위 3건마다 상세 조회. 실제 응답 재현: 근로기준법 제23조·민법 제750조 두 질의에서 상세 6회·12.4초(메모 '최대 2~3건').
- 고칠 것: 문서당 상세 조회 횟수 카운터(상한 3)를 두고 예산 가드와 함께 본다. 평가 측 사본 실측: 상세 3회·7.1초, 판례 6건(요지 3건).

P4 정정(PR 본문에 적는다): 메모 2.3의 _excerpt_budget_chars는 _semantic_review 경로 함수라 무리한 주장 경로에는 없다. 판례 블록 상한(3건 × 요지 150자)으로 대체한다고 적는다.

U5 화면 문구(사용자 확인 사항): 범위 표시가 판례 줄마다 반복되고 괄호가 겹친다 — '…(검색 379건 중 100건 (대법원 한정))'. 범위는 판례 묶음 머리에 한 번만 적는 쪽을 권고한다(예: '[관련 판례] 대법원 본문검색 379건 중 100건을 권위 순 정렬한 상위 3건 · 검토 자료'). 이 항목은 평가 측 사본에 적용하지 않았다(미검증). 최종 문구는 사용자 화면 확인으로 정한다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-138_impl_fix_on_02b26e9.diff(evaluator/round8-promotion) — H1~H5·H7과 평가 측 시험 5건(TestTK138EvaluatorSupplement). 이 시험은 02b26e9에서 5/5 실패, 사본에서 통과(TK-137·138 시험 33건 통과).
- 기존 관련 시험(argument_validity·claim_review·search_case·_semantic_review·related_authorities·input_contract·inspect_request를 쓰는 65개 파일) 통과.
- 화면 캡처(1280·390px, 긴 사건명 포함) 다시 제출 → 사용자 확인 뒤 수용.
- 수용 SHA에서 평가 측 verify_all 전체(입력 계약 변경 포함)·오프라인 고정·은퇴 변화 0, 온라인 OFF/ON: 제공 목록 밖 인용 0(화면 근거 글 기준)·지어낸 인용 0.
```
