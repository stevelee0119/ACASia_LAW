"""은퇴 봉인 세트(`tests/fixtures/retired_sealed/`) 기준·후보 비교 (2026-10-17 사용자 승인, 평가 측 자산).

제품·평가 도구·자료 변경 시 기준 커밋과 현재 HEAD를 같은 입력과 현재 채점기로 비교한다.
- 실패(종료 코드 1): manifest 불일치, 실행 실패, 기존 회귀 또는 v2 유형별 재현율 후퇴.
- 건너뜀(종료 코드 0): 평가 관련 변경이 없다. 이 경우에도 자료 목록과 해시는 검사한다.
evaluation_replay.py가 현재 채점기와 고정 입력을 과거/현재 제품에 각각 적용한다.
출력은 세트별 집계뿐이다. 은퇴 세트는 공개 개발 자료라 상세 보고서는 작업 폴더 밖 임시 폴더에만 둔다.
기준 쪽 집계는 로컬에서만 `artifacts/retired_cache/`에 캐시한다(TK-125, 2026-10-24 사용자 승인). 키는 기준 SHA·세트 목록·
파이썬 버전·플랫폼·의존성·OCR 자료·평가 코드·자료 해시다. CI(`CI` 환경 변수)와 `--no-cache`에서는
캐시를 읽지도 쓰지도 않는다. 기준 채점이 하나라도 실패하면 저장하지 않는다.

사용: python scripts/retired_compare.py --base <기준 커밋> [--no-cache]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluation_v2 import compare_sets, dataset_identity
from scripts.path_guard import TESSDATA_ROOTS, contained_path
RETIRED = "tests/fixtures/retired_sealed"
PRODUCT_PATHS = ("packages", "apps", "workers", "config", "migrations", "docker")
CACHE_DIR = ROOT / "artifacts" / "retired_cache"
CACHE_FORMAT = 2
EVALUATION_PATHS = ("scripts/evaluation_v2.py", "scripts/evaluation_replay.py", "scripts/eval_testset.py",
                    "scripts/retired_compare.py", "docs/scorecards/retired_manifest.json", RETIRED)


def cache_file(base_sha: str, names: List[str]) -> Path:
    from scripts.scorecard import tesseract_info
    tess = tesseract_info()
    # Include language model bytes, not merely the binary's version or a local path.
    language_models = {}
    binary = shutil.which("tesseract")
    if binary:
        listing = subprocess.run([binary, "--list-langs"], capture_output=True, text=True, timeout=10).stdout
        match = re.search(r'in "([^"]+)"', listing)
        raw = os.environ.get("TESSDATA_PREFIX") or (match.group(1) if match else "/nonexistent")
        try:
            folder = contained_path(raw, *TESSDATA_ROOTS)
        except ValueError:
            folder = None  # 허용 위치 밖 tessdata는 읽지 않는다(캐시 열쇠에 UNTRUSTED_PATH로 남김)
        for lang in tess["langs"]:
            if folder is None or not re.fullmatch(r"[A-Za-z0-9_]+", str(lang)):
                language_models[lang] = "UNTRUSTED_PATH"
                continue
            model = contained_path(folder / f"{lang}.traineddata", folder)
            language_models[lang] = hashlib.sha256(model.read_bytes()).hexdigest() if model.exists() else "MISSING"
    key = json.dumps({"format": CACHE_FORMAT, "base": base_sha, "sets": names,
                      "datasets": {n: dataset_identity(ROOT / RETIRED / n) for n in names},
                      "evaluator": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                    for p in EVALUATION_PATHS if (ROOT / p).is_file()},
                      "dependencies": sorted((d.metadata.get("Name", ""), d.version) for d in importlib.metadata.distributions()),
                      "ocr": tess, "language_models": language_models,
                      "python": platform.python_version(), "platform": sys.platform}, sort_keys=True)
    # 기준 SHA 조각이 이름에 들어가므로 캐시 폴더 밖으로 나가지 않게 묶는다.
    return contained_path(CACHE_DIR / f"{base_sha[:12]}_{hashlib.sha256(key.encode()).hexdigest()[:12]}.json", CACHE_DIR)


def load_cached_base(path: Path, names: List[str]) -> Optional[Dict[str, Optional[Dict]]]:
    try:
        data = json.loads(contained_path(path, CACHE_DIR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or sorted(data) != sorted(names) or any(v is None for v in data.values()):
        return None
    return data


def save_cached_base(path: Path, data: Dict[str, Optional[Dict]]) -> None:
    if any(v is None for v in data.values()):
        return
    path = contained_path(path, CACHE_DIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def product_changed(base: str) -> List[str]:
    out = subprocess.run(["git", "diff", "--name-only", base, "HEAD", "--", *PRODUCT_PATHS, *EVALUATION_PATHS],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def sets_in(tree: Path) -> List[str]:
    folder = contained_path(Path(tree) / RETIRED)
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
    env = dict(os.environ, LV_ALLOW_NETWORK="0", PYTHONUTF8="1", OMP_THREAD_LIMIT="1")
    results: Dict[str, Optional[Dict]] = {}
    for name in names:
        out = work / f"{name}.json"
        try:
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/evaluation_replay.py"),
                                   "--tree", str(tree), "--dataset", str(ROOT / RETIRED / name),
                                   "--out", str(out)], cwd=tree, env=env, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=600)
        except subprocess.TimeoutExpired:
            proc = None
        if proc is None or proc.returncode != 0 or not out.is_file():
            print(f"  [오류] {name}: 채점 실패/시간 초과", file=sys.stderr)
            results[name] = None
            continue
        try:
            results[name] = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            results[name] = None
    return results


def compare(base: Dict[str, Optional[Dict]], head: Dict[str, Optional[Dict]]) -> List[str]:
    """Measurement failure is not an unchanged score. Compare the full inventory."""
    problems = []
    if not base or set(base) != set(head):
        problems.append("은퇴 세트 목록 불일치/비어 있음")
    for name, b in base.items():
        h = head.get(name)
        if b is None:
            problems.append(f"{name}: 기준 채점 실패")
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
        if "regression_v2" in b or "regression_v2" in h:
            problems += compare_sets({name: h.get("regression_v2")}, {name: b.get("regression_v2") or {}})
    return problems


def _row(name: str, b: Optional[Dict], h: Optional[Dict]) -> str:
    def cell(x: Optional[Dict]) -> str:
        if x is None:
            return "채점 실패"
        inj = "방어" if x["injection_defended"] else ("-" if x["injection_defended"] is None else "실패")
        v2 = x.get("regression_v2") or {}
        return (f"구 산식 {x['overall']} / 확인오탐 {x['false_positives']} / A {x['a_grade_fp']} / 기존 방어대리값 {inj}"
                f" / v2 {v2.get('hits')}/{v2.get('items')} / 미판정 {v2.get('unadjudicated_alerts')}")
    return f"  {name:<18} {cell(b)}  →  {cell(h)}"


def check_inventory(tree):
    manifest = json.loads((ROOT / "docs/scorecards/retired_manifest.json").read_text(encoding="utf-8"))["sets"]
    if not manifest or set(sets_in(tree)) != set(manifest):
        raise ValueError("은퇴 세트 목록이 고정 manifest와 다릅니다")
    for name, expected in manifest.items():
        if dataset_identity(contained_path(Path(tree) / RETIRED / name)) != expected:
            raise ValueError(f"{name}: 평가 자료 해시 불일치")
    return sorted(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="기준 커밋(PR이면 기준 브랜치 SHA)")
    parser.add_argument("--no-cache", action="store_true", help="기준 집계 캐시를 쓰지 않는다(CI에서는 항상 쓰지 않음)")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/retired_comparison.json")
    args = parser.parse_args()
    # 검사한 값은 지역 변수로만 쓴다. args 속성에 다시 넣으면 CodeQL이 args.out 읽기를 여전히 외부 입력으로 본다.
    out = contained_path(args.out)  # 저장소·임시 폴더 안에만 쓴다
    use_cache = not args.no_cache and not os.environ.get("CI")
    base_sha = subprocess.run(["git", "rev-parse", args.base], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    changed = product_changed(base_sha)
    try:
        names = check_inventory(ROOT)
    except (OSError, ValueError, KeyError) as exc:
        print(f"[실패] {exc}", file=sys.stderr)
        return 1
    if not changed:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"status": "NOT_RUN_UNCHANGED", "sets": names,
                                      "reason": "no product/evaluator/dataset change"}), encoding="utf-8")
        print(f"은퇴 세트 목록 {len(names)}개 확인 — 평가 관련 변경 없음, 재실행 생략 (새 측정 아님)")
        return 0
    cached = None
    path = cache_file(base_sha, names)
    if use_cache:
        cached = load_cached_base(path, names)
    with tempfile.TemporaryDirectory(prefix="retired_cmp_") as tmp:
        work = Path(tmp)
        if cached is not None:
            base = cached
        else:
            tree = work / "base_tree"
            subprocess.run(["git", "worktree", "add", "--detach", "-q", str(tree), base_sha], cwd=ROOT, check=True)
            try:
                base = score_tree(tree, names, work / "base")
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT, capture_output=True)
                subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
            if use_cache:
                save_cached_base(path, base)
        head = score_tree(ROOT, names, work / "head")
    source = "캐시" if cached is not None else "채점"
    print(f"은퇴 세트 비교 — 기준 {base_sha[:7]}({source}) → 현재 (오프라인, 평가 관련 파일 {len(changed)}개 변경, 세트 {len(names)}개)")
    for name in names:
        print(_row(name, base.get(name), head.get(name)))
    problems = compare(base, head)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"status": "FAILED" if problems else "MEASURED", "base_sha": base_sha,
                                  "head_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                  "evaluator_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                                       for p in EVALUATION_PATHS if (ROOT / p).is_file()},
                                  "evaluator": "current frozen scorer for both products",
                                  "base": base, "head": head, "problems": problems}, ensure_ascii=False, indent=2), encoding="utf-8")
    if problems:
        print("  [실패] 기준 대비 후퇴:")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("  후퇴 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
