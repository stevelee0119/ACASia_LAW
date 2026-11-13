"""Produce a multi-layer evaluation report; unmeasured quality is never a pass."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.evaluation import LabelRecord, PredictionRecord, evaluate_quality, load_jsonl
from scripts.evaluation_v2 import compare_sets
from scripts.evaluate_kbl import evaluate as evaluate_kbl


def unmeasured(reason):
    return {"status": "NOT_MEASURED", "value": None, "reason": reason}


def build(card, labels=None, predictions=None, origin=None, kbl_dataset=None, kbl_predictions=None):
    if (labels is None) != (predictions is None) or (kbl_dataset is None) != (kbl_predictions is None):
        raise ValueError("Supply both labels and predictions, and both KBL dataset and predictions")
    baseline = json.loads((ROOT / "docs/scorecards/regression_v2_baseline.json").read_text(encoding="utf-8"))
    current = {k: card.get("sets", {}).get(k, {}).get("regression_v2") for k in baseline["sets"]}
    failures = compare_sets(current, baseline["sets"])
    report = {"schema": 2, "policy": "legal-quality-v2", "product_git": card.get("git"),
              "environment": card.get("environment"), "legal_quality_approval": "NOT_ESTABLISHED",
              "regression": {"status": "FAILED" if failures else "MEASURED", "failures": failures, "sets": current},
              "labeled_quality": unmeasured("Independent labels and bound actual product predictions required"),
              "public_benchmark": unmeasured("No KBL prediction run supplied"),
              "retrieval": unmeasured("Official source-span relevance labels required"),
              "legal_argument_validity": unmeasured("Independent legal application labels and claim-level outputs required"),
              "practice_utility": unmeasured("Independent lawyer review-time study required")}
    if labels is not None:
        gold = load_jsonl(labels, LabelRecord)
        pred = load_jsonl(predictions, PredictionRecord)
        # The library schema permits this; the new evaluation contract rejects contradictory assertions.
        if any(p.status == "VERIFIED" and p.error_types for p in pred):
            raise ValueError("VERIFIED prediction cannot simultaneously assert an error")
        if len({(p.run_id, p.system_version) for p in pred}) > 1:
            raise ValueError("Do not pool different product runs or versions")
        quality = evaluate_quality(gold, pred, origin=origin, seed=7)
        if quality["origin"] == "ATTORNEY_LABELED" and pred:
            sha = (card.get("git") or {}).get("sha")
            if not sha or {p.system_version for p in pred} != {sha}:
                raise ValueError("Attorney-labeled predictions must belong to this exact scorecard product SHA")
        report["labeled_quality"] = {"status": "MEASURED" if pred else "NOT_MEASURED", "report": quality,
                                     "scope": "ONLY_THE_SUPPLIED_LABEL_COHORT_AND_DIMENSIONS"}
        manifest = Path(predictions).with_suffix(Path(predictions).suffix + ".manifest.json")
        if manifest.exists():
            provenance = json.loads(manifest.read_text(encoding="utf-8"))
            if provenance.get("output_sha256") != hashlib.sha256(Path(predictions).read_bytes()).hexdigest():
                raise ValueError("Prediction export hash differs from its manifest")
            report["labeled_quality"]["export_provenance"] = provenance
    if kbl_dataset is not None:
        report["public_benchmark"] = evaluate_kbl(kbl_dataset, kbl_predictions)
        benchmark = report["public_benchmark"]
        if benchmark["status"] == "MEASURED" and benchmark["system_version"] != (card.get("git") or {}).get("sha"):
            raise ValueError("KBL predictions belong to a different product SHA")
    return report


def render(report):
    lines = ["# 평가 v2 — 다층 측정", "", "법률 품질 승인: NOT_ESTABLISHED. 미측정은 0점 또는 통과가 아닙니다.", "",
             "| 평가 층 | 상태 |", "|---|---|"]
    for key in ("regression", "labeled_quality", "public_benchmark", "retrieval", "legal_argument_validity", "practice_utility"):
        lines.append(f"| {key} | {report[key]['status']} |")
    lines += ["", "## 회귀자료 (실무 정확도 아님)", "", "| 세트 | 일대일 재현율 | 확인 오탐 | 미판정 경고 |", "|---|---|---|---|"]
    for name, row in report["regression"]["sets"].items():
        if row:
            lines.append(f"| {name} | {row['hits']}/{row['items']} | {row['known_false_positive_findings']} | {row['unadjudicated_alerts']} |")
    lines += ["", "미판정 경고는 독립 라벨링 전에는 오탐으로 확정하지 않습니다. 원문·정답·인증정보를 CI 산출물에 넣지 않습니다."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scorecard", type=Path, required=True)
    p.add_argument("--labels", type=Path)
    p.add_argument("--predictions", type=Path)
    p.add_argument("--origin", choices=["SYNTHETIC", "ATTORNEY_LABELED"])
    p.add_argument("--kbl-dataset", type=Path)
    p.add_argument("--kbl-predictions", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        report = build(json.loads(a.scorecard.read_text(encoding="utf-8")), a.labels, a.predictions,
                       a.origin, a.kbl_dataset, a.kbl_predictions)
        report["scorecard_sha256"] = hashlib.sha256(a.scorecard.read_bytes()).hexdigest()
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        a.out.with_suffix(".md").write_text(render(report), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.error(str(exc))
    return 1 if report["regression"]["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
