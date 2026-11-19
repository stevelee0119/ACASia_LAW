# 0.23.0 릴리스 후보 전체 검증 기록 — `2b8b4bd` (2026-11-19)

평가 측이 릴리스 후보 SHA에서 `verify_all` 전체 모드를 한 번 돌린 결과다. [DAILY_TREND](DAILY_TREND.md)
2026-11-19 릴리스 후보 행의 근거이며, 그 행의 수치는 전부 여기에 있다.

## 1. 측정 조건

| 항목 | 값 |
|---|---|
| HEAD | `2b8b4bd` (`Steve_ACASiaLAW`) |
| 기준 | `v.0.22.0` |
| 명령 | `python scripts/verify_all.py --base v.0.22.0` (full 모드, 브라우저 시험 포함) |
| 측정일 | 2026-11-19 (한국 시각) |
| 측정 주체 | 평가 측 재실행. CI 결과 인용이 아니다 |
| 환경 | python 3.13.18, tesseract 5.3.4, Linux 6.18.44 |
| 네트워크 | 오프라인 |

**환경 불일치**: CI는 python 3.11이다. `verify_all`의 `environment` 단계가 이를 실패로 잡는다. 같은 단계를
CI가 3.11에서 모두 통과시켰으므로(아래 4절) 이 불일치는 기록하고 넘어간다. 숨기지 않는다.

## 2. 단계별 결과

| 단계 | 결과 | 수치 |
|---|---|---|
| environment | **실패** | python 3.13.18 — CI(3.11)와 다름 |
| acceptance | 통과 | 통과 1,276 · 실제 실패 0 · strict XPASS 0 (143.9초) |
| regression_ledger | 통과 | 통과 2,357 · 실제 실패 0 · strict XPASS 0 (31.9초) |
| score_gate | 통과 | 점수 게이트 통과(고정 세트 하락 없음) |
| regression_gate | 통과 | **회귀 없음** — 명세 전 항목 base=head |
| hardcoding_diff | 통과 | 추가된 줄 8,222개에 시험 입력의 값·낱말·조문 번호 없음 |
| test_edits | 통과 | 기존 시험의 삭제·표시 변경 없음 |
| protected_paths | 통과 | 바뀐 보호 경로 34개 모두 평가 측 커밋 또는 승인 |
| version_policy | 통과 | 위반 없음(버전 변경 없음 — 버전 커밋은 구현 측 몫) |
| full_tests | 통과 | 통과 **11,409** · 실제 실패 0 · strict XPASS 0 |
| browser_tests | 통과 | 통과 200 · 실제 실패 0 |

### 회귀 게이트 항목별

base → head, 전 항목 동일:

```
case6_military_secret/primary      · case6_military_secret/text
case7_suspension/primary           · case7_suspension/text        (22/22 → 22/22)
case8_delay_penalty/primary        · case8_delay_penalty/text     (22/22 → 22/22)
case9_state_compensation/primary   · case9_state_compensation/text (28/28 → 28/28)
variant1_discipline/primary        · variant1_discipline/text     (24/24 → 24/24)
variant2_food_license/primary      · variant2_food_license/text   (21/21 → 21/21)
```

**첫 실행에서는 이 단계가 exit 2('측정하지 못한 항목이 있다')로 끝났다.** 평가 측이 원인을 추적해
게이트 자산 결함(TK-219)으로 확정했고, CI 동등 조건(`HOME`이 저장소를 품는 조건)에서 다시 재
'회귀 없음'을 받아 **제품에 회귀가 없음을 분리 확인**했다. 결함과 고친 내용은
[TK-219 티켓](../handoff/TK-219_regression_gate_base_input_paths.md)에 있다.

## 3. 이 후보에 담긴 변경

| 병합 SHA | 내용 |
|---|---|
| `2b8b4bd` | TK-208 Drive 미완독 3갈래 분류·`ocr_blocked` 분리·재시도 상한·화면/보고서 미독 표시 (#349) |
| `0244aee` | TK-218 발췌 선택 관측성 — 선택 결과 불변 (#351) |
| `a7b13a3` | TK-216 RAG 실패 건강 게이트 (#350) |
| `66b5b85` | TK-212 CI 기준 단일화·트리거 축소 (#348) |

## 4. CI 결과 (인용)

`2b8b4bd`의 직전 head `f9385cf`에 대한 PR #349 CI: 점수 하락 게이트 ✅, 테스트(SQLite + 인프로세스
Worker) ✅, 테스트(PostgreSQL/pgvector + Celery 브로커) ✅, Docker OCR readiness ✅, 은퇴 세트 비교 ✅,
CodeQL 새 경고 게이트 ✅, CodeQL 분석 4건 ✅, Sourcery ✅. python 3.11에서 돌았다.

## 5. 측정하지 못한 것

합격으로 간주하지 않는다.

- **TK-208이 노린 'Drive 라이브러리 READY 도달'** — 오프라인 합성 스텁으로는 확정할 수 없다. 배포 뒤
  3회차 온라인 점검에서 실측한다.
- **완독 스냅샷 기준 23항목 비교** — 두 회차 연속 불가했다(Drive `PARTIAL`). 같은 온라인 회차에서 본다.
- **`RAGC-S3`(TK-209 (가) 모델 판단 축)** — 사용자 범위 결정 대기.
- **봉인 세트 온라인·출제** — 2026-11-18 사용자 결정으로 이 릴리스에서 면제. 면제는 통과가 아니다.
- **실무 법률 정확도·검색/주장 타당성·검토 효율** — 이 세션의 측정 범위 밖이다.
- **AI 작성 판별·공식 DB 대조·Drive 실연동** — 오프라인 측정으로는 잴 수 없다.

---

## 6. 최종 후보 `2633d91` 재측정 (TK-219 수정 반영)

2~5절은 첫 후보 `2b8b4bd`의 기록이다. TK-219(회귀 게이트 자산 결함)를 고쳐 병합한 뒤 최종 후보에서
같은 명령을 다시 돌렸다.

| 단계 | `2b8b4bd` | `2633d91` |
|---|---|---|
| environment | 실패(python 3.13.18 ≠ CI 3.11) | 실패(같은 이유) |
| acceptance | 통과 1,276 | 통과 1,276 |
| regression_ledger | 통과 2,357 | 통과 2,357 |
| score_gate | 통과 | 통과 |
| **regression_gate** | **exit 2 — 측정하지 못한 항목이 있다** | **통과 — 회귀 없음** |
| hardcoding_diff | 통과 | 통과 |
| test_edits | 통과 | 통과 |
| protected_paths | 통과(보호 경로 34개) | 통과(보호 경로 36개) |
| version_policy | 통과(버전 변경 없음) | 통과(버전 변경 없음) |
| full_tests | 통과 11,409 | 통과 **11,416** |
| browser_tests | 통과 200 | 통과 200 |

회귀 게이트가 전 항목을 측정해 통과한 것이 TK-219 수정의 확인이다. 첫 실행에서는 같은 단계가 19초 만에
'측정 못 함'으로 끝났고, 최종 실행에서는 기준 커밋 worktree에서 탐침 12개를 모두 돌렸다.

전체 시험이 11,409 → 11,416으로 7건 는 것은 TK-219의 새 시험 4건과 #352 보완에서 더한 3건이다.
보호 경로가 34 → 36개로 는 것은 `scripts/path_guard.py`·`scripts/regression_gate.py`가 이번에 바뀐
것이며, 둘 다 평가 측 커밋이다.

**고정 세트**(`artifacts/scorecard.json`, SHA `2633d91`, dirty=false): dev 82.6(가중 재현율 0.826,
56항목) · holdout 81.9(0.819, 54항목), 확인 오탐 0 · A등급 오탐 0 · 대조 오탐 0 · 엔진 오류 0.
v2 일대일 dev 42/56(75.0%) · holdout 41/54(75.9%), 미판정 경고 9 · 8, 참고 경고 10 · 4.
0.21.0 · 0.22.0과 같은 값이다.

5절의 미측정 목록은 그대로 유효하다.
