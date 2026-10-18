# TK-77 TK-43 정규식 시간 시험이 CI 러너에서 한 번 측정·GC 개입으로 간헐 실패한다 (P3, 시험 견고성, 기존 결함)
- 유형: 시험 견고성(CI 신뢰성), 기존 결함. 제품 코드 결함이 아니다. 대상 시험: `tests/test_tk43_particle_sentences.py::test_label_regex_repeated_sentence_input_time`.
- 발견: 평가 측, 2026-10-17. 같은 날 서로 무관한 PR 세 곳에서 같은 시험만 실패했다(아래 1절). 사용자 승인으로 Antigravity에 배정했다.
- 측정 조건: GitHub Actions ubuntu 러너(Python 3.11), CI 로그 인용. 로컬 재실행은 Linux에서 0.004~0.005초로 통과(Python 3.11·3.12).

## 1. 증상 (CI 결과 인용)
| PR·SHA | 실행 | 측정값 (상한 0.1초) | 비고 |
|---|---|---|---|
| #114 `5d3eeb2` | push run 39002592191 (SQLite) | 0.748초 | 진단 기록상 측정 구간 안 GC 2세대 0.746초. 같은 SHA PR 실행은 성공 |
| #117 `a9f90c2` | PR run 39018312135 attempt1 (SQLite) | 0.597초 | attempt2 성공 |
| #117 `59b62fc` | PR run 39024186676 attempt1 (PostgreSQL) | 0.840초 | 같은 SHA push 실행 성공 |

- 세 PR 모두 `packages/pii_engine/detector.py`와 이 시험 파일을 바꾸지 않았다(blob 동일).
- 시험은 `perf_counter()`로 **한 번만** 잰다. 그 사이 GC가 돌거나 러너가 잠시 멈추면 상한을 넘는다.

## 2. 요구
1. 측정 방법만 바꾼다. 상한(0.1초)·입력(2,000문장)·일치 개수 단언은 그대로 둔다.
   - 측정 구간에서 GC를 끄고(`gc.disable()` → 측정 → `finally: gc.enable()`), 같은 입력을 3회 재서 **최솟값**으로 판정한다. 저장소의 다른 시간 시험(예: `tests/regression/test_tk24_statutory_exclusion.py`)과 같은 방식이다.
   - 정규식 컴파일·입력 생성은 측정 구간 밖에 둔다.
2. 같은 파일과 같은 모양(한 번 측정·0.1초 이하 상한)의 다른 시간 시험이 있으면 함께 고친다. 목록을 PR에 적는다.
3. 시험 삭제·skip·xfail·상한 완화는 하지 않는다(시험 삭제·약화 점검 대상).

## 3. 수용
- 변경은 시험 파일뿐이다(제품 diff 0). CI 필수 4개 성공.
- 바꾼 시험이 같은 정규식을 그대로 재는지(측정 대상 함수·입력 불변) 평가 측이 diff로 확인한다.
- 이후 1주 동안 CI에서 이 시험의 시간 초과 실패가 다시 나오지 않는지 평가 측이 지켜본다.
