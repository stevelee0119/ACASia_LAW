"""Aggregate-only measurement of the four explicitly authorized public sets.

Uses unchanged scripts/eval_testset.py and scorecard.py. The guarded function
is temporarily installed only in this measurement process, never in product.
No fixed/private/sealed corpus, test asset or scorer is modified.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SETS = ("sealed_20261008", "sealed_20261008b", "sealed_20261009", "sealed_20261010")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def measure(mode):
    os.environ["LV_ALLOW_NETWORK"] = "0"
    from packages.common.config import reset_settings
    reset_settings()
    from packages.claim_engine import evidence_consistency as engine
    from packages.document_engine.ocr import get_ocr_adapter
    audit = load("tk73_retired_candidate", Path(__file__).with_name("TK73_minimal_comparison_audit.py"))
    scorecard = load("tk73_existing_scorecard", ROOT / "scripts/scorecard.py")
    directories = {name: ROOT / "tests/fixtures/retired_sealed" / name for name in SETS}
    if any(not (path / "ground_truth.json").is_file() for path in directories.values()):
        raise SystemExit("Exactly the four public retired fixture directories are required.")
    original = engine._numbering
    if mode == "guarded":
        engine._numbering = audit.minimal_numbering(guarded=True)
    try:
        # Do not dump row-level findings or documents into a review transcript.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            card = scorecard.build(directories, None)
        assert card["environment"]["network"] is False
        aggregates = {name: {key: value for key, value in result.items() if key != "per_document"}
                      for name, result in card["sets"].items()}
        adapter = get_ocr_adapter()
        return {"mode": mode, "product_installed": False, "public_retired_only": True,
                "ocr_probe": {"adapter": adapter.name, "available": adapter.available,
                              "diagnostics": adapter.diagnostics},
                "git": card["git"], "environment": card["environment"], "sets": aggregates}
    finally:
        engine._numbering = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "guarded"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = measure(args.mode)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
