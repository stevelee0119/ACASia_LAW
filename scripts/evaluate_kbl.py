"""Score the pinned KBL statute-hallucination task from actual supplied predictions.

No inference, no answer generation, no claim of product certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REVISION = "695653ba87affa2c3113896013179c81fc16786a"
DATA_SHA256 = "910048e2860251ea371aa5efc3037bb570bb53fe4685c702b1488418bf03639e"
DATA_URL = f"https://huggingface.co/datasets/lbox/kbl/resolve/{REVISION}/knowledge/kbl_statute_hallucination_qa_v0.1.json"


def evaluate(dataset, response):
    data_bytes = Path(dataset).read_bytes()
    if hashlib.sha256(data_bytes).hexdigest() != DATA_SHA256:
        raise ValueError("KBL dataset hash mismatch; do not silently change dataset revision")
    data = json.loads(data_bytes)
    if len(data) != 75:
        raise ValueError("Unexpected pinned benchmark denominator")
    gold = {str(r["doc-id"]): r["label"] for r in data}
    if len(gold) != 75 or any(v not in "ABCD" or len(v) != 1 for v in gold.values()):
        raise ValueError("Invalid benchmark labels")
    supplied = json.loads(Path(response).read_text(encoding="utf-8"))
    if not supplied.get("run_id") or not supplied.get("system_version") or not isinstance(supplied.get("predictions"), list):
        raise ValueError("Response requires run_id, system_version, predictions")
    predictions = {}
    for row in supplied["predictions"]:
        key = str(row["item_id"])
        if key not in gold or key in predictions:
            raise ValueError("Unknown or duplicate KBL prediction ID")
        predictions[key] = row.get("choice")
    valid = {k: v for k, v in predictions.items() if isinstance(v, str) and v in {"A", "B", "C", "D"}}
    correct = sum(valid.get(k) == answer for k, answer in gold.items())
    return {"status": "MEASURED" if predictions else "NOT_MEASURED", "benchmark": "KBL_STATUTE_HALLUCINATION_QA", "dataset_revision": REVISION,
            "dataset_sha256": DATA_SHA256, "dataset_url": DATA_URL, "license": "CC-BY-NC-4.0",
            "items": 75, "correct": correct if predictions else None,
            "accuracy": correct / 75 if predictions else None, "coverage": len(valid) / 75 if predictions else None,
            "missing": 75-len(predictions), "invalid_answers": len(predictions)-len(valid),
            "run_id": supplied["run_id"], "system_version": supplied["system_version"],
            "predictions_sha256": hashlib.sha256(Path(response).read_bytes()).hexdigest(),
            "notice": "Multiple-choice task accuracy; not end-to-end document verification or current-law certification"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        report = evaluate(a.dataset, a.predictions)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
