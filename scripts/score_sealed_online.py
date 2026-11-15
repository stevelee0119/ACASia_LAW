"""온라인 봉인 실행 채점(U1, 사용자 전용, 보호 경로).

봉인 세트를 배포 서비스에서 한 프로젝트로 돌린 결과 JSON을, 오프라인 성적표와 같은 채점기(eval_testset)로 채점한다.
오프라인 채점(`scorecard.py --sealed-dir`)과 달리 공식 DB·모델·Drive가 켜진 상태라 `db_available=True`로 채점한다.
그래서 CIT-NX-DB·SRC-UNV처럼 공식 DB가 있어야 맞힐 수 있는 항목까지 잰다.
실행 상태(엔진 오류·공식 DB·모델·Drive 동기화)도 함께 적는다.

    python scripts/score_sealed_online.py --report <결과.json> --sealed-dir <저장소 밖 봉인 폴더>

- 출력은 집계 숫자만 싣는다(종합·재현율·오탐·결함 유형별 항목 수·재현율·개인정보 종류·실행 상태). 문서별·항목별 상세는
  봉인 폴더 안 `.sealed_out/`에만 쓴다(사용자만 본다).
- 결과 JSON의 문서 파일 이름은 정답지의 파일 이름과 같아야 한다(파일 이름 앞부분으로 문서를 맞춘다). 이름을 바꿔 올리지 않는다.
- 오프라인 봉인 점수와 조건이 달라(네트워크·모델) 서로 증감을 비교하지 않는다. 같은 봉인 세트의 운영본·후보 온라인 점수끼리만 비교한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import score_report, scorecard  # noqa: E402

HEALTH_CHECKS = ("commit_present", "engine_errors", "law_db_ready", "source_lookups", "models_ok", "reference_sync")


def score(report: Dict[str, Any], sealed_dir: Path) -> Dict[str, Any]:
    evaluator = scorecard.load_evaluator()
    graded = evaluator.score(report, sealed_dir, db_available=True)
    documents = len(json.loads((sealed_dir / "ground_truth.json").read_text(encoding="utf-8"))["documents"])
    summary = scorecard.summarize(graded, documents=documents, sealed=True)
    summary["engine_errors"] = scorecard.engine_errors(report)
    manifest = report.get("run_manifest") or {}
    health = {}
    for which in HEALTH_CHECKS:
        passed, detail = score_report.run_health({"check": which, "min_requests": 1, "allow": ["reference_sync"]}, manifest)
        health[which] = {"passed": bool(passed), "detail": detail}
    summary["run_health"] = health
    network = bool((manifest.get("environment") or {}).get("network"))
    summary["condition"] = ("online(배포 서비스: 네트워크·공식 DB·모델·Drive), db_available=True" if network
                            else "경고: 결과 JSON이 네트워크 끔 실행이다 — 온라인 봉인 점수로 쓰지 않는다")
    summary["commit"] = str(((manifest.get("implementation") or {}).get("git_commit")) or "")[:12]
    detail_dir = sealed_dir / ".sealed_out"
    detail_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (detail_dir / f"online_{stamp}.json").write_text(json.dumps(graded, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def render(summary: Dict[str, Any]) -> str:
    lines = [f"온라인 봉인 실행 — 커밋 {summary['commit'] or '?'}, 문서 {summary['documents']}건 ({summary['condition']})",
             f"  종합 {summary['overall']}, 부분점수율 {summary['weighted_recall']}, 결함 항목 {summary['defect_items']}, "
             f"확인 오탐 {summary['false_positives']}, A등급 오탐 {summary['a_grade_fp']}"]
    for kind, value in (summary.get("per_type") or {}).items():
        lines.append(f"  {kind:<12} 항목 {value['items']:>3}, 재현율 {value['recall']}")
    if summary.get("pii_kinds"):
        lines.append(f"  개인정보 종류 {summary['pii_kinds']['found_kinds']}/{summary['pii_kinds']['expected_kinds']}")
    for which, row in summary["run_health"].items():
        lines.append(f"  실행 상태 {which:<15} {'통과' if row['passed'] else '실패'} — {row['detail']}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sealed-dir", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    sealed_dir = args.sealed_dir.resolve()
    if sealed_dir == ROOT or ROOT in sealed_dir.parents:
        print("봉인 폴더는 저장소 밖에 있어야 한다", file=sys.stderr)
        return 2
    if not (sealed_dir / "ground_truth.json").is_file() or not (sealed_dir / "match_spec.json").is_file():
        print(f"봉인 폴더에 ground_truth.json·match_spec.json이 없다: {sealed_dir}", file=sys.stderr)
        return 2
    report = json.loads(args.report.read_text(encoding="utf-8"))
    summary = score(report, sealed_dir)
    print(json.dumps(summary, ensure_ascii=False) if args.json else render(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
