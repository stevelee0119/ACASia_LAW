"""은퇴 봉인 세트(`tests/fixtures/retired_sealed/`) 기준·후보 비교 (2026-10-17 사용자 승인, 평가 측 자산).

제품 경로가 바뀐 PR에서 기준 커밋과 현재 HEAD를 같은 은퇴 세트로 오프라인 채점해 집계만 비교한다.
- 실패(종료 코드 1): 어느 세트든 종합점수 하락, 오탐 증가, A등급 오탐 증가, 인젝션 방어 실패 전환.
- 건너뜀(종료 코드 0): 기준~HEAD 사이에 제품 경로 변경이 없다.
각 쪽은 그 커밋의 `scripts/eval_testset.py`로 채점한다(채점기는 보호 경로라 두 쪽이 같다고 본다).
출력은 세트별 집계뿐이다. 은퇴 세트는 공개 개발 자료라 상세 보고서는 작업 폴더 밖 임시 폴더에만 둔다.

사용: python scripts/retired_compare.py --base <기준 커밋>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
RETIRED = "tests/fixtures/retired_sealed"
PRODUCT_PATHS = ("packages", "apps", "workers", "config", "migrations", "docker")


def product_changed(base: str) -> List[str]:
    out = subprocess.run(["git", "diff", "--name-only", base, "HEAD", "--", *PRODUCT_PATHS],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def sets_in(tree: Path) -> List[str]:
    folder = tree / RETIRED
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if (p / "ground_truth.json").is_file())


def summarize(report: Dict) -> Dict:
    injection = report.get("injection_defense") or {}
    return {"overall": report.get("overall"), "weighted_recall": report.get("weighted_recall"),
            "false_positives": report.get("false_positives_total"),
            "a_grade_fp": report.get("a_grade_false_positives"),
            "injection_defended": injection.get("defended") if injection else None}


def score_tree(tree: Path, names: List[str], work: Path) -> Dict[str, Optional[Dict]]:
    env = dict(os.environ, LV_ALLOW_NETWORK="0")
    results: Dict[str, Optional[Dict]] = {}
    for name in names:
        out = work / name
        proc = subprocess.run([sys.executable, "scripts/eval_testset.py", "--testset", str(tree / RETIRED / name),
                               "--out", str(out)], cwd=tree, env=env, capture_output=True, text=True)
        reports = sorted(out.glob("eval_*.json")) if out.is_dir() else []
        if proc.returncode != 0 or not reports:
            print(f"  [오류] {name}: 채점 실패(종료 코드 {proc.returncode})", file=sys.stderr)
            results[name] = None
            continue
        results[name] = summarize(json.loads(reports[-1].read_text(encoding="utf-8")))
    return results


def compare(base: Dict[str, Optional[Dict]], head: Dict[str, Optional[Dict]]) -> List[str]:
    """기준 대비 후퇴 목록. 기준에 없는 세트는 비교하지 않는다(새로 추가된 은퇴 세트)."""
    problems = []
    for name, b in base.items():
        h = head.get(name)
        if b is None:
            continue
        if h is None:
            problems.append(f"{name}: 후보 채점 실패")
            continue
        if (h["overall"] or 0) < (b["overall"] or 0):
            problems.append(f"{name}: 종합점수 {b['overall']} → {h['overall']}")
        if (h["false_positives"] or 0) > (b["false_positives"] or 0):
            problems.append(f"{name}: 오탐 {b['false_positives']} → {h['false_positives']}")
        if (h["a_grade_fp"] or 0) > (b["a_grade_fp"] or 0):
            problems.append(f"{name}: A등급 오탐 {b['a_grade_fp']} → {h['a_grade_fp']}")
        if b["injection_defended"] is True and h["injection_defended"] is not True:
            problems.append(f"{name}: 인젝션 방어 실패")
    return problems


def _row(name: str, b: Optional[Dict], h: Optional[Dict]) -> str:
    def cell(x: Optional[Dict]) -> str:
        if x is None:
            return "채점 실패"
        inj = "방어" if x["injection_defended"] else ("-" if x["injection_defended"] is None else "실패")
        return f"{x['overall']} / 오탐 {x['false_positives']} / A {x['a_grade_fp']} / 인젝션 {inj}"
    return f"  {name:<18} {cell(b)}  →  {cell(h)}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="기준 커밋(PR이면 기준 브랜치 SHA)")
    args = parser.parse_args()
    base_sha = subprocess.run(["git", "rev-parse", args.base], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    changed = product_changed(base_sha)
    if not changed:
        print(f"은퇴 세트 비교 — 기준 {base_sha[:7]} 이후 제품 경로 변경 없음, 건너뜀")
        return 0
    head_sets = sets_in(ROOT)
    with tempfile.TemporaryDirectory(prefix="retired_cmp_") as tmp:
        work = Path(tmp)
        tree = work / "base_tree"
        subprocess.run(["git", "worktree", "add", "--detach", "-q", str(tree), base_sha], cwd=ROOT, check=True)
        try:
            names = [n for n in sets_in(tree) if n in head_sets]
            base = score_tree(tree, names, work / "base")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT, capture_output=True)
            subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
        head = score_tree(ROOT, names, work / "head")
    print(f"은퇴 세트 비교 — 기준 {base_sha[:7]} → 현재 (오프라인, 제품 파일 {len(changed)}개 변경, 세트 {len(names)}개)")
    for name in names:
        print(_row(name, base.get(name), head.get(name)))
    problems = compare(base, head)
    if problems:
        print("  [실패] 기준 대비 후퇴:")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("  후퇴 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
