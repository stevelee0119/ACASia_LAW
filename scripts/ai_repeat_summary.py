"""AI 작성 판별 반복 측정 집계(U5, 평가 에이전트 소관, 보호 경로).

같은 문서를 같은 조건으로 여러 번 온라인 실행한 결과 JSON을 받아, 실행 사이 판정의 흔들림을 숫자로 낸다.
릴리스마다 case9를 3회 실행해 이 도구로 집계한다(RELEASE_PROCEDURE 4절, 사용자 승인 11-14).

    python scripts/ai_repeat_summary.py --reports r1.json r2.json r3.json [--expect AI_FULL_GENERATION_LIKELY AI_PARTIAL_GENERATION]

출력
- 실행별: 커밋, 문서 판정(축 점수), 모델별 의견(공급자·판정·점수), 유보(UNCERTAIN) 여부
- 요약: 판정 일치율(가장 흔한 판정의 비율), 유보 횟수, --expect 쪽 판정 비율, 공급자별 점수 범위(최소~최대)
- 전체 SHA·입력·정책·모델·기준일·참고자료를 비교한다. 누락은 UNKNOWN, 차이는 DIFFERENT다.
- 입력 문서는 하나여야 한다. 조건 원문 대신 항목 이름과 해시만 출력한다. 일치율은 정확도가 아니다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def conditions(report: Dict[str, Any]) -> tuple[Dict[str, str], List[str]]:
    """Compare recorded inputs; never infer missing evidence from the current environment."""
    manifest = report.get("run_manifest") or {}
    snapshot = report.get("input_snapshot") or {}
    values: Dict[str, str] = {}
    missing: List[str] = []

    def record(name, value, valid=True):
        if not valid:
            missing.append(name)
        else:
            values[name] = _digest(value)

    def mapping(name, value, required, nullable=()):
        record(name, value, isinstance(value, dict) and all(
            key in value and (key in nullable or value[key] is not None and value[key] != "") for key in required))

    commit = (manifest.get("implementation") or {}).get("git_commit")
    record("commit", commit, isinstance(commit, str) and bool(re.fullmatch(r"[0-9a-f]{40}", commit)))
    docs = report.get("documents") or []
    inputs = snapshot.get("documents") or []
    axis = (((report.get("scores") or {}).get("axes") or {}).get("ai_authorship") or {}).get("documents") or []
    if len(docs) != 1 or len(inputs) != 1 or len(axis) != 1:
        missing.append("single_document")
    else:
        doc, source, score = docs[0], inputs[0], axis[0]
        sha = source.get("sha256")
        valid = (isinstance(sha, str) and bool(re.fullmatch(r"[0-9a-f]{64}", sha))
                 and doc.get("sha256") == sha and bool(source.get("document_id"))
                 and source["document_id"] == doc.get("document_id") == score.get("document_id"))
        record("input", {k: v for k, v in source.items() if k not in {"document_id", "storage_key", "filename"}}, valid)
    context = snapshot.get("context")
    mapping("context", {k: v for k, v in context.items() if k != "project_id"} if isinstance(context, dict) else None,
            ("profile", "case_date", "external_ai_policy", "issue_dates", "requested_issues", "counterparty_document"),
            nullable=("case_date",))
    mapping("security", snapshot.get("security"), ("external_ai_policy", "blocked_providers", "block_sealed_reveal"))
    execution = snapshot.get("execution") or {}
    mapping("execution", execution, ("providers", "settings", "budget", "pricing"))
    mapping("execution.settings", execution.get("settings"),
            ("allow_network", "llm_cross_check", "llm_efficient_routing", "llm_routing", "llm_model_overrides",
             "llm_default_models", "rag_drive_folder_id", "korean_law_review_profile", "rule_version", "prompt_version"),
            nullable=("rag_drive_folder_id",))
    providers = execution.get("providers")
    record("execution.providers", providers, isinstance(providers, dict) and bool(providers)
           and all(isinstance(p, dict) and p.get("model") and "enabled" in p for p in providers.values()))
    for label, value in (("versions", manifest.get("versions")), ("input_versions", snapshot.get("versions"))):
        mapping(label, value, ("rule", "prompt", "model_config"))
    record("issues", snapshot.get("issues"), isinstance(snapshot.get("issues"), list))
    env = manifest.get("environment") or {}
    record("environment", env.get("fingerprint"), bool(env.get("fingerprint")))
    reference = manifest.get("reference_library") or {}
    disabled = (reference.get("status") == "DISABLED" and "folder_id" in reference
                and not reference["folder_id"] and "snapshot_hash" in reference
                and reference["snapshot_hash"] is None
                and (execution.get("settings") or {}).get("rag_drive_folder_id") == "")
    sha = reference.get("snapshot_hash")
    ready = (reference.get("status") in {"READY", "PARTIAL"} and bool(reference.get("folder_id"))
             and isinstance(sha, str) and bool(re.fullmatch(r"[0-9a-f]{64}", sha)))
    record("reference_library", {k: reference.get(k) for k in ("status", "folder_id", "snapshot_hash")}, disabled or ready)
    try:
        timestamp = report.get("started_at")
        started = datetime.fromisoformat(timestamp.replace("Z", "+00:00") if isinstance(timestamp, str) else "")
        # Native reports serialize datetime.utcnow() without an offset.
        day = started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started
        record("reference_date", day.astimezone(ZoneInfo("Asia/Seoul")).date().isoformat())
    except (TypeError, ValueError):
        missing.append("reference_date")
    return values, sorted(set(missing))


def observe(report: Dict[str, Any]) -> Dict[str, Any]:
    manifest = report.get("run_manifest") or {}
    axis = (((report.get("scores") or {}).get("axes") or {}).get("ai_authorship") or {}).get("documents") or []
    opinions = []
    for document in report.get("documents", []):
        for opinion in (document.get("ai_detector_result") or {}).get("model_opinions") or []:
            opinions.append({"provider": str(opinion.get("provider")), "verdict": str(opinion.get("verdict")),
                             "score": float(opinion.get("score") or 0)})
    condition_hashes, missing = conditions(report)
    return {"commit": str(((manifest.get("implementation") or {}).get("git_commit")) or ""),
            "condition_hashes": condition_hashes, "missing_conditions": missing,
            "document_count": len(report.get("documents") or []),
            "run_id": report.get("run_id"),
            "verdicts": [str(e.get("verdict")) for e in axis],
            "scores": [e.get("score") for e in axis],
            "opinions": opinions}


def summarize(runs: List[Dict[str, Any]], expect: Optional[List[str]] = None) -> Dict[str, Any]:
    if any(run.get("document_count") != 1 or len(run["verdicts"]) != 1 for run in runs):
        raise ValueError("각 보고서에는 입력 문서와 AI 문서 판정이 각각 하나여야 합니다. 문서별로 분리해 집계하세요.")
    verdicts = [run["verdicts"][0] if run["verdicts"] else "NONE" for run in runs]
    counts = Counter(verdicts)
    top, top_n = counts.most_common(1)[0] if counts else ("NONE", 0)
    ranges: Dict[str, List[float]] = defaultdict(list)
    for run in runs:
        for opinion in run["opinions"]:
            ranges[opinion["provider"]].append(opinion["score"])
    commits = {run["commit"] for run in runs}
    keys = sorted({key for run in runs for key in run.get("condition_hashes", {})})
    differences = [key for key in keys if len({run.get("condition_hashes", {}).get(key) for run in runs}) > 1]
    if len(commits) > 1 and "commit" not in differences:
        differences.append("commit")
    missing = sorted({key for run in runs for key in run.get("missing_conditions", ["condition_evidence"])})
    if len(runs) < 2:
        missing.append("repeat_runs")
    run_ids = [run.get("run_id") for run in runs]
    if not all(isinstance(value, str) and value for value in run_ids) or len(set(run_ids)) != len(runs):
        missing.append("distinct_run_ids")
    status = "DIFFERENT" if differences else "UNKNOWN" if missing else "SAME"
    return {"runs": len(runs), "commits": sorted(commits), "same_condition": status == "SAME",
            "condition_status": status, "different_conditions": sorted(differences), "missing_conditions": missing,
            "comparable_agreement": round(top_n / len(runs), 3) if status == "SAME" else None,
            "verdict_counts": dict(counts), "agreement": round(top_n / len(runs), 3) if runs else None,
            "modal_verdict": top, "uncertain_runs": counts.get("UNCERTAIN", 0),
            "expected_ratio": (round(sum(1 for v in verdicts if v in expect) / len(runs), 3) if expect and runs else None),
            "provider_score_range": {p: [min(v), max(v), len(v)] for p, v in sorted(ranges.items())}}


def render(runs: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    lines = [f"AI 작성 판별 반복 측정 — {summary['runs']}회"
             + f" (조건 {summary['condition_status']})"]
    if not summary["same_condition"]:
        lines.append(f"  동일 조건 비교 불가 — 차이 {summary['different_conditions']}, 누락 {summary['missing_conditions']}")
    for i, run in enumerate(runs, 1):
        ops = ", ".join(f"{o['provider']} {o['verdict']} {o['score']:.2f}" for o in run["opinions"]) or "모델 의견 없음"
        lines.append(f"  {i}회 커밋 {run['commit'] or '?'} 판정 {run['verdicts']} 점수 {run['scores']} — {ops}")
    lines.append(f"  관찰 판정 일치율 {summary['agreement']} (가장 흔한 판정 {summary['modal_verdict']}), 유보 {summary['uncertain_runs']}회"
                 + (f", 기대 판정 비율 {summary['expected_ratio']}" if summary["expected_ratio"] is not None else ""))
    for provider, (low, high, n) in summary["provider_score_range"].items():
        lines.append(f"  {provider}: 점수 {low:.2f}~{high:.2f} ({n}건)")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reports", nargs="+", required=True, type=Path)
    parser.add_argument("--expect", nargs="*")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        runs = [observe(json.loads(p.read_text(encoding="utf-8"))) for p in args.reports]
        summary = summarize(runs, args.expect)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"집계할 수 없음: {type(exc).__name__}")
        return 2
    print(json.dumps({"runs": runs, "summary": summary}, ensure_ascii=False) if args.json else render(runs, summary))
    return 0 if summary["same_condition"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
