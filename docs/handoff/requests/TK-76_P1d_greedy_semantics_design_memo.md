# [설계 메모] TK-76 3주기 D 묶음 후속 P1d — 순서 연결어 탐욕적 일치 의미 보존 및 선형 스캔 최적화

- **작성일**: 2026-11-10 | **작성자**: Antigravity (구현 에이전트)
- **기준 브랜치/커밋**: `antigravity/tk76-cycle3-d-bundle` (`5c85c02`)
- **대상 모듈**: `packages/claim_engine/date_verifier.py` (`CONJUGATED_ORDER_RE`, `_has_narrative_order_connective`)
- **수칙 준수**: 본 메모는 독립 평가 지시(2026-11-10)의 P1d 품질 기준에 따른 설계 보완 메모이다.

---

## 1. 원인 분석 및 앞선 지시의 누락 축
- **원인**: P1a에서 `CONJUGATED_ORDER_RE`의 동사 패턴을 `[가-힣]+`에서 `[가-힣]{1,10}`으로 임의 제한했다.
- **누락 축**: 
  - 기준 패턴 `[가-힣]+`는 같은 한글 run 안에서 뒤쪽 연결어까지 탐욕적으로 소비하는 좌측 우선 탐색 의미를 갖는다.
  - 길이 제한({1,10})은 앞 연결어에서 먼저 일치하여 기준 동작과 다른 매칭 경계를 형성, 기준 3d54f77에는 없던 `TEMPORAL_EVENT_INVERSION` 오탐을 유발했다.
  - 단순한 `(?<![가-힣])` lookbehind 역시 앞선 일치가 공백 뒤 연결어까지 소비한 후 동일 run 중간에서 시작하는 유효 일치를 탈락시키는 문제가 있다.

## 2. 변경 경로 및 범위
- **`packages/claim_engine/date_verifier.py`**:
  1. `CONJUGATED_ORDER_RE` 패턴을 기준 원본인 `r"(?P<verb>[가-힣]+)\s*(?P<conn>뒤|후|다음)|다가"`로 완전 복원.
  2. `_has_narrative_order_connective(text)`의 순회 방식을 한글 run 단위 선형 스캔으로 재설계:
     - 한글 run의 시작 또는 직전 일치 종료 위치(`m.end()`)에서 `.match(text, pos)` 수행 (문자열 슬라이싱 배제, 인덱스 직접 전달).
     - 매칭 성공 시: `다가` 또는 유효 어미/받침 충족 시 즉시 `True` 반환, 비유효 시 `pos = m.end()`로 전진.
     - 매칭 실패 시: 해당 한글 run 내에서는 `[가-힣]+`가 `뒤|후|다음`에 도달할 수 없음이 수학적으로 증명되므로, run 내 `다가` 존재 여부만 `text.find("다가", pos, run_end)`로 $O(L)$ 확인 후 run 끝(`run_end`)으로 단번에 점프.
  3. P1b(`_TARGET_WINDOW = 400`) 및 P1c(`_POST_TARGET_TAIL_RE`)의 대상 추출 최적화는 100% 보존.

## 3. 보존 계약 및 복잡도
- **보존 계약**:
  - 기준 3d54f77과 `_has_narrative_order_connective`의 모든 합성 및 문서 출력 판정 의미 100% 동일 (차이 0).
  - 공백을 사이에 둔 일치 이후 동일 run 중간에서 시작하는 후속 양성 보존 (`가 뒤검토한후` 등).
  - 긴 run 내부 복수 연결어의 기준 탐욕 소비 동작 보존.
- **복잡도**: 띄어쓰기 없는 2만 자 한글열에서도 $O(N)$ 선형 시간 복잡도로 0.002초 이내 완료 (기준 5초 대비 2,500배 이상 단축).

## 4. 시험 계획 및 결과
- **공개 시험**: `tests/test_codex_p1d_greedy_semantics_eval.py` (9/9 통과)
- **기존 날짜 검증 시험군**: `tests/test_tk76_date_perf_p1_eval.py`, `tests/test_tk76_date_t2_t3_eval.py`, `tests/test_tk76_date_t2_target_eval.py`, `tests/test_tk76_date_range_eval.py`, `tests/test_date_verifier_generalization.py`, `tests/test_a4_evi_date_temporal.py` (총 121/121 통과)
