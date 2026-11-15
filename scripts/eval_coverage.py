"""평가 커버리지 표: 탐지 유형(FindingType)마다 어느 평가 층이 재는지 센다(평가 에이전트 소관, 보호 경로).

    python scripts/eval_coverage.py                  # 표(markdown) 출력
    python scripts/eval_coverage.py --json out.json  # 같은 내용을 JSON으로

층(2026-11-14 평가 체계 감사)
- offline_scorer : 고정·은퇴·봉인 세트 채점기(eval_testset.DEFECT_TYPE_MAP)가 점수를 줄 수 있는 유형
- online_spec    : 온라인 보고서 명세(tests/fixtures/probes/*_online*.json)의 finding·no_finding 항목이 지정한 유형
- dev_probe      : 개발 문서 명세(tests/fixtures/probes/*.json, 온라인 제외)가 지정한 유형
- ci_tests       : 시험 코드(tests/**/*.py)에 유형 이름이 나오는가(단위·회귀 시험이 그 유형을 직접 다루는지의 근사)
정답 자료(봉인·은퇴·고정 세트의 ground_truth)는 읽지 않는다. 채점기 표와 명세 파일, 시험 코드만 본다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def finding_types() -> List[str]:
    from packages.common.schemas import FindingType
    return sorted(f.value for f in FindingType)


def offline_scorable() -> Set[str]:
    source = (ROOT / "scripts" / "eval_testset.py").read_text(encoding="utf-8")
    block = source[source.index("_INJECTION = {"):source.index("def allowed_types")]
    namespace: Dict[str, Any] = {}
    exec(compile(block, "eval_testset.DEFECT_TYPE_MAP", "exec"), namespace)  # 상수 정의 블록만 실행
    return set().union(*namespace["DEFECT_TYPE_MAP"].values())


def spec_types(online: bool) -> Set[str]:
    out: Set[str] = set()
    for path in sorted((ROOT / "tests" / "fixtures" / "probes").glob("*.json")):
        if ("_online" in path.stem) != online:
            continue
        spec = json.loads(path.read_text(encoding="utf-8"))
        for check in spec.get("checks", []):
            if check.get("kind") in ("finding", "no_finding"):
                out.update(str(t).split(".")[-1] for t in check.get("types") or [])
    return out


def test_mentions(types: List[str]) -> Set[str]:
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in (ROOT / "tests").rglob("*.py"))
    return {t for t in types if re.search(rf"\b{re.escape(t)}\b", text)}


def build() -> Dict[str, Any]:
    types = finding_types()
    layers = {"offline_scorer": offline_scorable(), "online_spec": spec_types(True),
              "dev_probe": spec_types(False), "ci_tests": test_mentions(types)}
    rows = [{"type": t, **{name: t in members for name, members in layers.items()}} for t in types]
    summary = {name: sum(1 for r in rows if r[name]) for name in layers}
    summary["total"] = len(rows)
    summary["offline_and_online_none"] = sum(1 for r in rows if not r["offline_scorer"] and not r["online_spec"])
    summary["ci_only_or_none"] = sum(1 for r in rows if not (r["offline_scorer"] or r["online_spec"] or r["dev_probe"]))
    return {"summary": summary, "rows": rows}


def render(data: Dict[str, Any]) -> str:
    s = data["summary"]
    lines = [f"탐지 유형 {s['total']}개 — 채점기 {s['offline_scorer']}, 온라인 명세 {s['online_spec']}, 개발 문서 명세 {s['dev_probe']}, "
             f"시험 코드 언급 {s['ci_tests']}. 채점기·온라인 명세 어느 쪽에도 없는 유형 {s['offline_and_online_none']}, "
             f"시험 코드에만 있거나 아무 데도 없는 유형 {s['ci_only_or_none']}", "",
             "| 유형 | 채점기(고정·은퇴·봉인) | 온라인 명세 | 개발 문서 명세 | 시험 코드 |", "|---|---|---|---|---|"]
    mark = {True: "○", False: "—"}
    for r in data["rows"]:
        lines.append(f"| {r['type']} | {mark[r['offline_scorer']]} | {mark[r['online_spec']]} | {mark[r['dev_probe']]} | {mark[r['ci_tests']]} |")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    data = build()
    if args.json:
        args.json.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(render(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
