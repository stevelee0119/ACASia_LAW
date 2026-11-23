"""동적 변형 시험(Perturbation Testing) 하네스 (평가 에이전트 소관, 보호 경로).

기존 평가 세트의 원본 파일을 훼손하지 않고 임시 사본에 의미 보존 변형
(문체 전환·날짜 표기 변형·당사자 지위 치환)을 적용해 재채점함으로써
특정 문구·표면 패턴에 과적합된 규칙을 적발한다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluation_v2

DEFAULT_TESTSET = ROOT / "tests" / "fixtures" / "legal_verifier_testset"
ALLOWED_TESTSETS: Dict[str, Path] = {
    "dev": ROOT / "tests" / "fixtures" / "legal_verifier_testset",
    "holdout": ROOT / "tests" / "fixtures" / "legal_verifier_testset_holdout",
}
TEXT_EXTS = {".txt", ".md"}

_REGISTER_SUBS = (
    (re.compile(r"하였습니다\."), "하였음."),
    (re.compile(r"했습니다\."), "했음."),
    (re.compile(r"합니다\."), "함."),
    (re.compile(r"됩니다\."), "됨."),
    (re.compile(r"입니다\."), "임."),
)

_DATE_DOT_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})\.\s*(\d{1,2})\.\s*(\d{1,2})\.")

_PARTY_SUBS = (
    (re.compile(r"피고는"), "피신청인은"),
    (re.compile(r"피고가"), "피신청인이"),
    (re.compile(r"피고를"), "피신청인을"),
    (re.compile(r"피고"), "피신청인"),
    (re.compile(r"원고는"), "신청인은"),
    (re.compile(r"원고가"), "신청인이"),
    (re.compile(r"원고를"), "신청인을"),
    (re.compile(r"원고"), "신청인"),
)


def _load_eval_testset():
    spec = importlib.util.spec_from_file_location("eval_testset", ROOT / "scripts" / "eval_testset.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("eval_testset", module)
    spec.loader.exec_module(module)
    return module


def perturb_text(text: str, modes: Sequence[str]) -> str:
    out = text
    if "register" in modes:
        for pat, repl in _REGISTER_SUBS:
            out = pat.sub(repl, out)
    if "date_format" in modes:
        out = _DATE_DOT_RE.sub(r"\1년 \2월 \3일", out)
    if "party_role" in modes:
        for pat, repl in _PARTY_SUBS:
            out = pat.sub(repl, out)
    return out


def _perturb_match_tokens(tokens_obj: Dict[str, Any], modes: Sequence[str]) -> Dict[str, Any]:
    if "party_role" not in modes:
        return tokens_obj
    raw = json.dumps(tokens_obj, ensure_ascii=False)
    for pat, repl in _PARTY_SUBS:
        raw = pat.sub(repl, raw)
    return json.loads(raw)


def build_perturbed_copy(src_dir: Path, dst_dir: Path, modes: Sequence[str]) -> Path:
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    for p in dst_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            original = p.read_text(encoding="utf-8")
            p.write_text(perturb_text(original, modes), encoding="utf-8")
    ms_path = dst_dir / "match_spec.json"
    if ms_path.is_file() and "party_role" in modes:
        ms = json.loads(ms_path.read_text(encoding="utf-8"))
        ms_path.write_text(json.dumps(_perturb_match_tokens(ms, modes), ensure_ascii=False, indent=2), encoding="utf-8")
    return dst_dir


def run_perturbation_eval(testset: Path, modes: Sequence[str] = ("register", "date_format")) -> Dict[str, Any]:
    evaluator = _load_eval_testset()
    base_res = evaluator.run_pipeline(testset)
    base_rep = evaluator.score(base_res, testset, db_available=False)
    base_v2 = evaluation_v2.score(base_res, testset, base_rep)

    with tempfile.TemporaryDirectory(prefix="acas_perturb_") as tmp:
        p_dir = build_perturbed_copy(testset, Path(tmp) / "perturbed_testset", modes)
        pert_res = evaluator.run_pipeline(p_dir)
        pert_rep = evaluator.score(pert_res, p_dir, db_available=False)
        pert_v2 = evaluation_v2.score(pert_res, p_dir, pert_rep)

    base_overall = float(base_rep["overall"])
    pert_overall = float(pert_rep["overall"])
    retention = round(pert_overall / base_overall, 4) if base_overall > 0 else 1.0
    base_hits = int(base_v2["hits"])
    pert_hits = int(pert_v2["hits"])
    v2_retention = round(pert_hits / base_hits, 4) if base_hits > 0 else 1.0

    return {
        "track": "perturbation_v1",
        "testset": str(testset),
        "modes": list(modes),
        "baseline": {
            "overall": base_overall,
            "v2_hits": base_hits,
            "v2_items": int(base_v2["items"]),
            "false_positives": int(base_rep["false_positives_total"]),
            "a_grade_fp": int(base_rep["a_grade_false_positives"]),
        },
        "perturbed": {
            "overall": pert_overall,
            "v2_hits": pert_hits,
            "v2_items": int(pert_v2["items"]),
            "false_positives": int(pert_rep["false_positives_total"]),
            "a_grade_fp": int(pert_rep["a_grade_false_positives"]),
        },
        "retention_ratio": retention,
        "v2_retention_ratio": v2_retention,
        "overfitting_warning": retention < 0.90 or int(pert_rep["false_positives_total"]) > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run dynamic perturbation evaluation on an existing testset.")
    parser.add_argument("--testset", choices=sorted(ALLOWED_TESTSETS.keys()), default="dev")
    parser.add_argument("--modes", nargs="+", default=["register", "date_format"], choices=["register", "date_format", "party_role"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    testset_path = ALLOWED_TESTSETS[args.testset]
    payload = run_perturbation_eval(testset_path, modes=args.modes)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
