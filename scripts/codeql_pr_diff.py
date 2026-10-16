"""Steve 대상 PR의 CodeQL 새 경고 게이트 (.github/workflows/codeql-pr.yml에서 실행).

기준 커밋(base)과 PR 병합본(head)을 각각 분석한 SARIF를 비교해, PR이 새로 만든 결과만 센다.
같은 결과인지는 (규칙, 파일, 메시지)로 판단한다. 줄 번호는 PR이 위쪽 코드를 바꾸면 밀리므로 쓰지 않는다.

    python scripts/codeql_pr_diff.py --base sarif/base --head sarif/head

- 실패(종료 코드 1): 새 결과 중 보안 심각도 7.0(High) 이상, 또는 보안 심각도가 없는 error 수준이 있다.
  GitHub 코드 스캔 검사의 기본 실패 기준(보안 'High or higher', 그 밖 'Only errors')과 같다.
- 실패(종료 코드 2): base나 head 쪽 SARIF가 없다(분석이 돌지 않은 것을 통과로 보지 않는다).
- 그 밖의 새 결과(Medium 이하·warning)는 요약에 적기만 한다.
`GITHUB_STEP_SUMMARY`가 있으면 같은 요약을 실행 요약에도 남긴다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

HIGH = 7.0
Key = Tuple[str, str, str]


def _rules(run: dict) -> Dict[str, dict]:
    tool = run.get("tool") or {}
    out: Dict[str, dict] = {}
    for comp in [tool.get("driver") or {}] + list(tool.get("extensions") or []):
        for rule in comp.get("rules") or []:
            if rule.get("id"):
                out[rule["id"]] = rule
    return out


def _rule_id(result: dict, run: dict) -> str:
    if result.get("ruleId"):
        return result["ruleId"]
    rule = result.get("rule") or {}
    if rule.get("id"):
        return rule["id"]
    idx = result.get("ruleIndex", rule.get("index"))
    rules = ((run.get("tool") or {}).get("driver") or {}).get("rules") or []
    if isinstance(idx, int) and 0 <= idx < len(rules):
        return rules[idx].get("id", "?")
    return "?"


def _location(result: dict) -> Tuple[str, int]:
    for loc in result.get("locations") or []:
        phys = loc.get("physicalLocation") or {}
        uri = (phys.get("artifactLocation") or {}).get("uri") or "?"
        return uri, int((phys.get("region") or {}).get("startLine") or 0)
    return "?", 0


def load(paths: Iterable[Path]) -> Tuple[List[dict], int]:
    """SARIF 결과를 펼친다. 반환: (결과 목록, 읽은 SARIF 파일 수)."""
    rows, files = [], 0
    for path in paths:
        if not path.exists():
            continue
        for f in sorted(path.rglob("*.sarif")) if path.is_dir() else [path]:
            files += 1
            data = json.loads(f.read_text(encoding="utf-8"))
            for run in data.get("runs") or []:
                rules = _rules(run)
                for res in run.get("results") or []:
                    if (res.get("suppressions") or []) or res.get("baselineState") == "absent":
                        continue
                    rid = _rule_id(res, run)
                    rule = rules.get(rid, {})
                    props = rule.get("properties") or {}
                    try:
                        sev = float(props.get("security-severity"))
                    except (TypeError, ValueError):
                        sev = None
                    level = res.get("level") or (rule.get("defaultConfiguration") or {}).get("level") or "warning"
                    uri, line = _location(res)
                    message = " ".join(((res.get("message") or {}).get("text") or "").split())
                    rows.append({"rule": rid, "uri": uri, "line": line, "message": message,
                                 "severity": sev, "level": level,
                                 "name": (rule.get("shortDescription") or {}).get("text") or rid})
    return rows, files


def key(row: dict) -> Key:
    return row["rule"], row["uri"], row["message"]


def blocking(row: dict) -> bool:
    if row["severity"] is not None:
        return row["severity"] >= HIGH
    return row["level"] == "error"


def new_results(base: List[dict], head: List[dict]) -> List[dict]:
    """head에만 있는 결과. 같은 키가 여러 개면 개수 차이만큼 새것으로 본다."""
    remaining = Counter(key(r) for r in base)
    out = []
    for row in sorted(head, key=lambda r: (r["uri"], r["line"], r["rule"])):
        k = key(row)
        if remaining[k] > 0:
            remaining[k] -= 1
        else:
            out.append(row)
    return out


def render(new: List[dict], base_n: int, head_n: int) -> str:
    block = [r for r in new if blocking(r)]
    lines = ["## CodeQL 새 경고 (Steve 대상 PR)", "",
             f"- 기준 커밋 결과 {base_n}건, PR 병합본 결과 {head_n}건, **새 결과 {len(new)}건**"
             f"(그중 실패 기준 해당 {len(block)}건: 보안 심각도 {HIGH} 이상 또는 error)"]
    if new:
        lines += ["", "| 판정 | 규칙 | 심각도 | 위치 |", "|---|---|---|---|"]
        for r in new:
            sev = "-" if r["severity"] is None else f"{r['severity']:.1f}"
            lines.append(f"| {'실패' if blocking(r) else '참고'} | `{r['rule']}` {r['name']} | {sev} ({r['level']}) | "
                         f"`{r['uri']}:{r['line']}` |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", nargs="+", type=Path, required=True, help="기준 커밋 SARIF 파일 또는 폴더")
    ap.add_argument("--head", nargs="+", type=Path, required=True, help="PR 병합본 SARIF 파일 또는 폴더")
    a = ap.parse_args(argv)
    base, base_files = load(a.base)
    head, head_files = load(a.head)
    if not base_files or not head_files:
        print(f"SARIF 없음: 기준 {base_files}개, PR {head_files}개. 분석이 끝나지 않았다.", file=sys.stderr)
        return 2
    new = new_results(base, head)
    text = render(new, len(base), len(head))
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text)
    return 1 if any(blocking(r) for r in new) else 0


if __name__ == "__main__":
    sys.exit(main())
