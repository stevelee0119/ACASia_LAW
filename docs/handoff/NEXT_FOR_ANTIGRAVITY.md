

### 2-33-8. LV 보완본 2차 보충 — CI 실패 2종 원인(F12 실제 결함, 문구 의심 허용 등록) (11-11, 평가 측 재실행)
- PostgreSQL 벌 API 시험 2건 실패를 로컬 PostgreSQL 16 + pgvector로 재현: Finding 객체가 결과 데이터 JSON에 들어감(LV-05 4327e02) → F12. **1차 판정에서 '일시 실패'로 본 것은 평가 측 오판**.
- 점수 하락 게이트 실패는 평가 세트 문구 의심 11건(설명·안내 문안) → 평가 측 허용 등록 커밋 `22d3fd7`(구현 측이 #252에 체리픽).
- 증분 [patches/LV_F11_F12_on_b128126.diff](patches/LV_F11_F12_on_b128126.diff)(F11 단독 증분은 대체), 공개 시험 16건.

```
[평가 측 판정 보충 — LV 보완본 2차(#252~#257, 끝 head b128126): CI 실패 2종 원인 확인, F12 추가 + 허용 문구 등록, 11-11]

앞 코멘트(#255, F11)에 더해 아래를 함께 반영한다. 증분은 F11·F12를 합친 docs/handoff/patches/LV_F11_F12_on_b128126.diff로 교체했다(제품 2파일 + 공개 시험 16건).

1) CI '테스트 (PostgreSQL/pgvector + Celery 브로커)' 실패 2건 — 실제 결함(F12, #256 LV-05에서 들어옴, 커밋 4327e02)
- 증상(CI 결과 인용): tests/test_api.py::test_vertical_slice_end_to_end(실행 상태 FAILED), ::test_run_listings_and_status_polls_never_read_the_stored_result(KeyError 'documents').
  1차 판정 때 'CI 일시 실패'로 본 것은 평가 측 오판이었다 — SQLite에서는 통과하고 PostgreSQL에서만 난다.
- 재현(평가 측, 로컬 PostgreSQL 16 + pgvector): Steve 649a162 통과, b128126 실패. verification_runs.errors = "Object of type Finding is not JSON serializable"(3회 재시도 모두).
- 원인: packages/legal_engine/verifier.py 229행 result.data["verdicts"][*]["findings"] = list(v.findings) — Finding 객체가 결과 데이터(JSON 칸)에 그대로 들어간다.
  PostgreSQL JSON 칸은 객체를 직렬화하지 못해 실행 전체가 실패한다.
- 고칠 것(#256 브랜치): 그 줄을
  [{"finding_id": f.finding_id, "type": str(f.type), "tags": list(f.tags or []), "confidence_features": dict(f.confidence_features or {})} for f in v.findings]
  로 바꾼다. 읽는 쪽(argument_validity_verifier.py 452행 v_findings)은 이미 dict를 처리한다(type·tags·confidence_features). 다른 소비처 없음(평가 측 grep).
- 공개 시험 E16(tests/test_lv_eval_fix.py): 결과 데이터 json.dumps 통과·findings가 dict인지. b128126에서 실패, 사본 통과.

2) CI '점수 하락 게이트' 실패 — 결함 아님(평가 세트 문구 의심 11건, 실패 시험 0건)
- check_train_phrase_overlap.py --eval-sets가 결과 설명·안내 문안·주석의 일반 표현 11건을 '의심'으로 표시해 종료 코드 1. 평가 측이 위치를 하나씩 확인했다 — 모두 탐지 조건(정규식·판정 분기)이 아니다.
- 평가 측 허용 등록 커밋: 평가 브랜치 evaluator/round8-promotion 22d3fd7(docs/scorecards/approved_eval_phrases.json만, 평가 측 저자).
  #252 브랜치에 git cherry-pick 22d3fd7 하고 연쇄로 전파한다(평가 측 커밋은 그대로 옮기고 고치지 않는다). 평가 측 확인: 체리픽 뒤 '평가 세트 문구 의심 없음'.

평가 측 재실행(사본 2fded7c = b128126 + F11 + F12)
- 공개 시험 16건 통과(b128126에서 E15·E16 실패). PostgreSQL로 tests/test_api.py 31건 통과(b128126은 2건 실패).
- SQLite 전체: F11 사본 9e9924a 11,442건 통과(F12는 그 위 한 줄 변경). PostgreSQL 16 + pgvector 전체: 사본 2fded7c 11,443건 통과(실패 0, 건너뜀 32).
- 은퇴 5세트·고정 82.6/81.9/0 변화 0(9e9924a 기준).

수용 기준
- F11(#255)·F12(#256)·허용 문구 체리픽(#252) 반영 후 연쇄 전파, 공개 시험 16건 통과, CI 전부 성공(두 시험 벌·점수 하락 게이트 포함) → #252~#257 연쇄 수용.
- 평가 측 교훈(기록): CI의 PostgreSQL 벌에서만 나는 실패는 일시 실패로 넘기지 않고 로컬 PostgreSQL로 재현한다(AGENT_ROLES 2.1 (10)).
```
- 11-11 #258(TK-151) 사용자 병합 → Steve `c89e191`. LV 보완 커밋은 새 Steve 기준으로 병합해도 충돌 없음(평가 측 확인).
