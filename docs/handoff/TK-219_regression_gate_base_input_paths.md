# TK-219 — 회귀 게이트가 기준 커밋 쪽에서 현재 저장소의 입력을 열지 못한다

- 발견: 2026-11-19, 평가 세션. 0.23.0 릴리스 후보 `2b8b4bd`의 `verify_all` 전체 실행.
- 분류: **평가 측 게이트 자산 결함**. 제품 결함이 아니고, 제품 회귀도 아니다.
- 우선순위: P2 (회귀 판정을 낼 수 없게 만든다).
- 담당: 평가 측(자산 소관). 구현 측에 넘기지 않는다.

## 1. 증상

`python scripts/regression_gate.py --base v.0.22.0`이 명세 전 항목에 대해

```
[측정 못 함] <명세>/<입력>: 점검하지 못했다: 허용 폴더 밖의 경로: <저장소>/tests/fixtures/...
측정하지 못한 항목이 있다 — 회귀 없음으로 볼 수 없다
```

로 끝난다(exit 2). `verify_all`의 `regression_gate` 단계가 그대로 실패한다.

## 2. 원인

1. `scripts/regression_gate.py`는 기준 커밋을 임시 worktree에 펴고(`worktree()`), **그 커밋의** 탐침
   도구를 하위 프로세스로 돌린다(`probe_run()`). 명세·입력 경로는 **현재 저장소**의 것을 넘긴다.
2. worktree 안에서 `scripts/path_guard.py`의 `ROOT`는 그 임시 폴더다. 따라서
   `INPUT_ROOTS = (worktree, 임시 폴더, 홈)`이 된다.
3. 현재 저장소가 홈 밖에 있으면(예: `HOME=/root`, 저장소 `/home/user/ACASia_LAW`) 그 입력은 셋 중
   어디에도 들지 않아 `contained_path()`가 `ValueError`를 낸다.
4. `probe_run()`은 `PROBE_DOC_ROOT`로 **위치는** 넘기지만 허용 목록에는 넣지 않는다. 위치를 아는 것과
   열어도 되는 것을 가르는 자리가 비어 있었다.

검출 여부가 `$HOME` 위치에 달려 있어, CI(저장소가 홈 아래)에서는 통과하고 저장소가 홈 밖인 환경에서는
매번 실패한다. 겉으로는 회귀가 있는 것처럼 보이지만 아니다.

## 3. 고친 것

1. `scripts/regression_gate.py` — 기준 커밋 쪽으로 보낼 명세와 그 입력(`input`, `text_input`)을 임시
   폴더에 **같은 상대 경로로** 복사하고 `PROBE_DOC_ROOT`를 그 폴더로 준다(`stage_spec()`).
   임시 폴더는 어느 커밋의 `path_guard`에서도 허용 폴더이므로, **기준 커밋 코드를 고치지 않고** 풀린다.
   이것이 핵심이다 — 기준 커밋은 과거의 태그이므로 거기에 고친 코드를 기대할 수 없다.
2. `scripts/path_guard.py` — 같은 저장소의 **주 작업 폴더**를 허용 폴더에 넣는다(`_main_checkout()`).
   환경변수가 아니라 `git rev-parse --git-common-dir`가 알려주는 공통 폴더에서 끌어내고, git을 쓸 수
   없으면 넓히지 않는다. worktree가 아닐 때 이미 `ROOT`로 허용되던 곳이라 범위가 넓어지지 않는다.

## 4. 확인

- `HOME=/root`(저장소가 홈 밖)에서 `regression_gate --base v.0.22.0` → **회귀 없음**(exit 0), 전 항목 측정.
  같은 조건에서 고치기 전에는 exit 2.
- 새 시험 `tests/test_tk219_path_guard_main_checkout.py` 4건: 주 작업 폴더 식별, 진짜 worktree 안에서
  주 작업 폴더의 입력 허용(홈이 저장소를 품지 않는 조건), 허용 폴더 밖 경로는 여전히 거부,
  git을 쓸 수 없으면 넓히지 않음.
- 기존 시험: `test_path_guard`·`test_regression_gate_tools`·`test_generalization_guards`·
  `test_layout_invariance`·`test_round5_regressions`·`test_ledger` 통과.

## 5. 남은 것

- 기준 커밋이 **버전마다 다른 옛 `path_guard`**를 들고 있다는 사실 자체는 그대로다. 이번 수정은 그에
  기대지 않는 쪽(입력을 임시 폴더로 옮기는 쪽)으로 풀었으므로 다음 릴리스에서도 유효하다.
- `scorecard_run()`이 기준 worktree에서 저장소 바깥 자료를 읽는 경로가 있는지는 이번 실행에서 실패가
  드러나지 않아 **미확인**이다. 드러나면 같은 방식으로 옮긴다.
