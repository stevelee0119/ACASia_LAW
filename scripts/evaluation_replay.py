"""Run historical PRODUCT code with the current evaluator and frozen input bytes."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import eval_testset, evaluation_v2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tree", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    os.environ["LV_ALLOW_NETWORK"] = "0"
    sys.path.insert(0, str(a.tree.resolve()))
    with tempfile.TemporaryDirectory(prefix="evaluation-replay-") as scratch:
        os.environ["LV_DATA_DIR"] = scratch
        result = eval_testset.run_pipeline(a.dataset.resolve())
        old = eval_testset.score(result, a.dataset, db_available=False)
        v2 = evaluation_v2.score(result, a.dataset, old)
        injection = old.get("injection_defense") or {}
        report = {"overall": old["overall"], "weighted_recall": old["weighted_recall"],
                  "false_positives": old["false_positives_total"], "a_grade_fp": old["a_grade_false_positives"],
                  "injection_defended": injection.get("defended"), "regression_v2": v2}
        from packages.common.config import get_settings
        report["product_version"] = get_settings().version
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
