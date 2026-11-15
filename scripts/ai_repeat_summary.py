"""AI 작성 판별 반복 측정 집계(U5, 평가 에이전트 소관, 보호 경로).

같은 문서를 같은 조건으로 여러 번 온라인 실행한 결과 JSON을 받아, 실행 사이 판정의 흔들림을 숫자로 낸다.
릴리스마다 case9를 3회 실행해 이 도구로 집계한다(RELEASE_PROCEDURE 4절, 사용자 승인 11-14).

    python scripts/ai_repeat_summary.py --reports r1.json r2.json r3.json [--expect AI_FULL_GENERATION_LIKELY AI_PARTIAL_GENERATION]

출력
- 실행별: 커밋, 문서 판정(축 점수), 모델별 의견(공급자·판정·점수), 유보(UNCERTAIN) 여부
- 요약: 판정 일치율(가장 흔한 판정의 비율), 유보 횟수, --expect 쪽 판정 비율, 공급자별 점수 범위(최소~최대)
- 커밋이 실행마다 다르면 '조건 불일치'로 표시하고 일치율을 비교 근거로 쓰지 않는다
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def observe(report: Dict[str, Any]) -> Dict[str, Any]:
    manifest = report.get("run_manifest") or {}
    axis = (((report.get("scores") or {}).get("axes") or {}).get("ai_authorship") or {}).get("documents") or []
    opinions = []
    for document in report.get("documents", []):
        for opinion in (document.get("ai_detector_result") or {}).get("model_opinions") or []:
            opinions.append({"provider": str(opinion.get("provider")), "verdict": str(opinion.get("verdict")),
                             "score": float(opinion.get("score") or 0)})
    return {"commit": str(((manifest.get("implementation") or {}).get("git_commit")) or "")[:12],
            "run_id": report.get("run_id"),
            "verdicts": [str(e.get("verdict")) for e in axis],
            "scores": [e.get("score") for e in axis],
            "opinions": opinions}


def summarize(runs: List[Dict[str, Any]], expect: Optional[List[str]] = None) -> Dict[str, Any]:
    verdicts = [run["verdicts"][0] if run["verdicts"] else "NONE" for run in runs]
    counts = Counter(verdicts)
    top, top_n = counts.most_common(1)[0] if counts else ("NONE", 0)
    ranges: Dict[str, List[float]] = defaultdict(list)
    for run in runs:
        for opinion in run["opinions"]:
            ranges[opinion["provider"]].append(opinion["score"])
    commits = {run["commit"] for run in runs}
    return {"runs": len(runs), "commits": sorted(commits), "same_condition": len(commits) == 1,
            "verdict_counts": dict(counts), "agreement": round(top_n / len(runs), 3) if runs else None,
            "modal_verdict": top, "uncertain_runs": counts.get("UNCERTAIN", 0),
            "expected_ratio": (round(sum(1 for v in verdicts if v in expect) / len(runs), 3) if expect and runs else None),
            "provider_score_range": {p: [min(v), max(v), len(v)] for p, v in sorted(ranges.items())}}


def render(runs: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    lines = [f"AI 작성 판별 반복 측정 — {summary['runs']}회"
             + ("" if summary["same_condition"] else f" (조건 불일치: 커밋 {', '.join(summary['commits'])})")]
    for i, run in enumerate(runs, 1):
        ops = ", ".join(f"{o['provider']} {o['verdict']} {o['score']:.2f}" for o in run["opinions"]) or "모델 의견 없음"
        lines.append(f"  {i}회 커밋 {run['commit'] or '?'} 판정 {run['verdicts']} 점수 {run['scores']} — {ops}")
    lines.append(f"  판정 일치율 {summary['agreement']} (가장 흔한 판정 {summary['modal_verdict']}), 유보 {summary['uncertain_runs']}회"
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
    runs = [observe(json.loads(p.read_text(encoding="utf-8"))) for p in args.reports]
    summary = summarize(runs, args.expect)
    print(json.dumps({"runs": runs, "summary": summary}, ensure_ascii=False) if args.json else render(runs, summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
