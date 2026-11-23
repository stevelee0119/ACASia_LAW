"""1단 오프라인 Source 카세트(REPLAY) 평가 트랙 (평가 에이전트 소관, 보호 경로).

네트워크를 끈 상태에서(LV_ALLOW_NETWORK=0) 공식 DB·법령 카세트(LV_SOURCE_REPLAY_MODE=REPLAY)를
재생해 CIT-*/LAW-* 검증 성능을 재현 가능하게 측정한다.
카세트 디렉터리가 없거나 비어 있으면 NOT_MEASURED로 기록하고 기존 게이트를 깨지 않는다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluation_v2

DEFAULT_CASSETTE_DIR = ROOT / "tests" / "fixtures" / "source_cassettes"
DEFAULT_TESTSET = ROOT / "tests" / "fixtures" / "legal_verifier_testset"


def _load_eval_testset():
    spec = importlib.util.spec_from_file_location("eval_testset", ROOT / "scripts" / "eval_testset.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("eval_testset", module)
    spec.loader.exec_module(module)
    return module


def has_cassettes(cassette_dir: Path) -> bool:
    return cassette_dir.is_dir() and any(cassette_dir.glob("*.json"))


def run_cassette_track(testset: Path, cassette_dir: Path) -> Dict[str, Any]:
    if not has_cassettes(cassette_dir):
        return {
            "track": "cassette_replay_v1",
            "status": "NOT_MEASURED",
            "reason": "NO_CASSETTE_FILES",
            "cassette_dir": str(cassette_dir),
            "testset": str(testset),
            "overall": None,
            "regression_v2": None,
        }

    prev_network = os.environ.get("LV_ALLOW_NETWORK")
    prev_mode = os.environ.get("LV_SOURCE_REPLAY_MODE")
    prev_dir = os.environ.get("LV_SOURCE_CASSETTE_DIR")
    os.environ["LV_ALLOW_NETWORK"] = "0"
    os.environ["LV_SOURCE_REPLAY_MODE"] = "REPLAY"
    os.environ["LV_SOURCE_CASSETTE_DIR"] = str(cassette_dir)
    try:
        evaluator = _load_eval_testset()
        result = evaluator.run_pipeline(testset)
        report = evaluator.score(result, testset, db_available=True)
        v2 = evaluation_v2.score(result, testset, report)
        return {
            "track": "cassette_replay_v1",
            "status": "MEASURED",
            "cassette_dir": str(cassette_dir),
            "testset": str(testset),
            "overall": report["overall"],
            "weighted_recall": report["weighted_recall"],
            "false_positives": report["false_positives_total"],
            "a_grade_fp": report["a_grade_false_positives"],
            "regression_v2": v2,
        }
    finally:
        for k, v in (("LV_ALLOW_NETWORK", prev_network), ("LV_SOURCE_REPLAY_MODE", prev_mode), ("LV_SOURCE_CASSETTE_DIR", prev_dir)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline Source Cassette REPLAY evaluation track.")
    parser.add_argument("--testset", type=Path, default=DEFAULT_TESTSET)
    parser.add_argument("--cassette-dir", type=Path, default=DEFAULT_CASSETTE_DIR)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    payload = run_cassette_track(args.testset, args.cassette_dir)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
