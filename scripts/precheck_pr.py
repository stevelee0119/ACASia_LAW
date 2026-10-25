"""구현 측이 PR을 올리기 전에 한 번에 돌리는 사전 점검(평가 측 도구, 2026-10-18 사용자 승인).

CI 필수 검사 가운데 오프라인으로 재현할 수 있는 것을 같은 순서로 돈다. 하나라도 실패하면 종료 코드 1.
  1. 고정 dev·holdout 성적표와 점수 하락 게이트(scorecard.py → score_gate.py)
  2. 은퇴 4세트 비교(retired_compare.py, 기준 브랜치 대비)
  3. 회귀 원장·수용 시험·TK-73 번호 시험(+ --tests로 준 시험)
  4. 평가 세트 정답 문구 대조(check_train_phrase_overlap.py --eval-sets)
train 원문 대조(점검표 7항)는 train이 저장소 밖에 있어 평가 측이 돌린다. 이 도구의 통과가 수용을 뜻하지는 않는다.
--quick(TK-125, 2026-10-24 사용자 승인): 1·4와 --tests 시험만 돈다. 은퇴 비교와 CORE_TESTS는 push 때 CI 필수 검사
('은퇴 세트 비교'·'테스트')가 같은 head에서 돈다. --quick 요약을 PR에 붙일 때는 그 두 CI 잡의 성공을 함께 적는다.

사용: python scripts/precheck_pr.py [--base origin/Steve_ACASiaLAW] [--tests tests/test_x.py ...] [--skip-retired | --quick]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_TESTS = ["tests/regression", "tests/acceptance", "tests/test_tk73_numbering_product.py"]


def run(title: str, cmd: list) -> bool:
    print(f"\n=== {title}\n$ {' '.join(cmd)}", flush=True)
    env = {**os.environ, "LV_ALLOW_NETWORK": "0", "PYTHONUTF8": "1"}
    env.setdefault("LV_PSEUDONYM_SECRET", "precheck-only-not-a-real-secret")
    code = subprocess.run(cmd, cwd=ROOT, env=env).returncode
    print(f"--- {title}: {'통과' if code == 0 else f'실패(종료 코드 {code})'}", flush=True)
    return code == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/Steve_ACASiaLAW")
    ap.add_argument("--tests", nargs="*", default=[], help="바꾼 기능의 시험 파일")
    ap.add_argument("--skip-retired", action="store_true", help="은퇴 4세트 비교를 건너뛴다(빠른 반복용, PR 전에는 쓰지 않는다)")
    ap.add_argument("--quick", action="store_true",
                    help="성적표·게이트·문구 대조·--tests만 돈다(은퇴 비교·CORE_TESTS는 CI 필수 검사에 맡김)")
    args = ap.parse_args(argv)
    if args.quick and not args.tests:
        ap.error("--quick에는 바꾼 기능의 시험을 --tests로 하나 이상 준다")
    skip_retired = args.skip_retired or args.quick
    py = sys.executable
    card = str(Path(tempfile.mkdtemp()) / "scorecard.json")
    results = {
        "성적표·점수 게이트": run("성적표", [py, "scripts/scorecard.py", "--out", card])
        and run("점수 하락 게이트", [py, "scripts/score_gate.py", "--current", card]),
    }
    if not skip_retired:
        results["은퇴 4세트 비교"] = run("은퇴 4세트 비교", [py, "scripts/retired_compare.py", "--base", args.base])
    core = [] if args.quick else CORE_TESTS
    results["회귀·수용·기능 시험" if core else "기능 시험(--tests)"] = run(
        "시험", [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", *core, *args.tests])
    results["평가 세트 문구 대조"] = run("평가 세트 문구 대조",
                                    [py, "scripts/check_train_phrase_overlap.py", "--base", args.base, "--eval-sets"])
    print("\n=== 요약 (PR 본문 점검표에 이 출력을 붙인다)")
    for name, ok in results.items():
        print(f"  {'통과' if ok else '실패'}  {name}")
    if args.quick:
        print("  건너뜀  은퇴 4세트 비교·회귀·수용·TK-73 시험(--quick, CI '은퇴 세트 비교'·'테스트' 성공을 함께 적는다)")
    elif args.skip_retired:
        print("  건너뜀  은퇴 4세트 비교(--skip-retired)")
    print(f"  기준 {args.base}, HEAD {subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
