"""기존 시험의 삭제·약화를 잡는다 (TK-49·TK-50: 7차 보완·7C가 원장 기대값을 바꾸고 시험 6개를 지웠으나 게이트가 보지 못했다).

`--base`부터 HEAD까지 `tests/` 아래 파이썬 파일의 시험 함수를 비교한다.
- 실패(종료 코드 1): 기존 시험 함수가 사라졌다(파일 삭제 포함). 시험을 지워서 통과시키는 것은 허용하지 않는다.
- 실패(종료 코드 1): 기존 시험에 `skip`·`skipif`·`xfail` 표시가 새로 붙었다(표시 변경은 평가 측 소관).
- 경고(종료 코드 0): 기존 시험의 `assert` 개수가 줄었다(약화 의심 — 사람이 본다).
- 이름만 바뀐 시험(같은 파일에 본문·표시·인자가 똑같은 새 이름 시험이 있음)은 삭제로 세지 않고 '이름 변경'으로 적는다
  (2026-10-05: PR 안에서 새로 만든 시험의 이름을 바꾸면 push 비교에서 거짓 '삭제'가 났다 — PR #17 b7dfb0a·5dca58c).
범위의 모든 커밋이 `Agent: evaluator` 꼬리표를 가지면(평가 측이 보호 시험을 고치는 경우) 점검을 건너뛴다.
평가 측이 표시를 지시하고 구현 측이 붙인 경우(예: 알려진 미해결 strict xfail)는 `docs/scorecards/approved_test_marks.json`에
적힌 시험·표시만 승인으로 본다. 평가 측이 지시한 시험 교체(삭제)는 `"mark": "delete"`로 적는다(2026-10-04).
그 파일을 마지막으로 바꾼 커밋이 `Agent: evaluator`일 때만 목록을 믿는다.

승인의 적용 범위 (TK-215, 2026-11-19): 승인 항목은 `"scope": {"body": "<16자리>"}`로
**그 시험의 본문 지문**에 한정한다. 이름만으로 걸면 같은 이름의 시험이 나중에 다시 만들어진 뒤
또 지워질 때 새 검토 없이 통과한다. 지문은 이름을 뺀 정의(표시·인자·본문)의 SHA-256 앞 16자리다.
`python scripts/check_test_edits.py --digest <경로> <시험이름> --ref <커밋>`으로 뽑는다.
경과 조치: `approved`가 2026-11-19 이전인 옛 항목은 범위 없이도 그대로 쓰되 경고로 센다.
그 날짜 이후 항목은 범위가 없으면 승인으로 보지 않는다.
사용: python scripts/check_test_edits.py --base <기준 커밋>
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

MARKS = ("skip", "skipif", "xfail")
APPROVALS = "docs/scorecards/approved_test_marks.json"
# 이 날짜(포함) 이후에 올린 승인은 적용 범위(`scope.body`)가 없으면 승인으로 보지 않는다.
SCOPE_REQUIRED_FROM = "2026-11-19"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def _show(ref: str, path: str) -> Optional[str]:
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, check=False)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def _marks(node: ast.AST) -> set:
    found = set()
    for dec in getattr(node, "decorator_list", []):
        text = ast.unparse(dec)
        for m in MARKS:
            if f"mark.{m}" in text or text.startswith(f"pytest.{m}"):
                found.add(m)
    return found


def collect(source: Optional[str]) -> Dict[str, Tuple[int, set]]:
    """시험 함수 이름 -> (assert 개수, 표시 집합). 클래스 안 시험은 `Class.name`."""
    if source is None:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out: Dict[str, Tuple[int, set]] = {}

    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                asserts = sum(isinstance(n, ast.Assert) for n in ast.walk(node))
                out[prefix + node.name] = (asserts, _marks(node))
            elif isinstance(node, ast.ClassDef):
                visit(node.body, prefix + node.name + ".")

    visit(tree.body)
    return out


def signatures(source: Optional[str]) -> Dict[str, str]:
    """시험 함수 이름 -> 이름을 뺀 정의(표시·인자·본문) 문자열. 이름만 바뀐 시험을 알아보는 데 쓴다."""
    if source is None:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out: Dict[str, str] = {}

    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                out[prefix + node.name] = ast.dump(ast.Module(body=[*node.decorator_list, node.args, *node.body], type_ignores=[]))
            elif isinstance(node, ast.ClassDef):
                visit(node.body, prefix + node.name + ".")

    visit(tree.body)
    return out


def body_digest(signature: Optional[str]) -> str:
    """시험 본문 지문. signatures()가 돌려준 정의 문자열의 SHA-256 앞 16자리."""
    if not signature:
        return ""
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]


def all_evaluator_commits(base: str) -> bool:
    log = _git("log", f"{base}..HEAD", "--format=%H%x00%B%x01")
    commits = [c for c in log.split("\x01") if c.strip()]
    if not commits:
        return False
    return all("Agent: evaluator" in c for c in commits)


def approved_marks() -> Dict[Tuple[str, str], List[dict]]:
    """평가 측이 승인한 (경로::시험, 표시) -> 항목 목록.

    파일을 마지막으로 바꾼 커밋이 평가 측일 때만 믿는다. 같은 (시험, 표시)에 항목이 여럿일 수
    있으므로(본문이 다른 시점의 승인) 집합이 아니라 목록으로 돌려준다.
    """
    out: Dict[Tuple[str, str], List[dict]] = {}
    source = _show("HEAD", APPROVALS)
    if source is None:
        return out
    last = _git("log", "-1", "--format=%B", "HEAD", "--", APPROVALS)
    if "Agent: evaluator" not in last:
        print(f"  [주의] {APPROVALS}를 마지막으로 바꾼 커밋이 평가 측이 아니라 승인 목록을 쓰지 않는다")
        return out
    try:
        entries = json.loads(source).get("approved", [])
    except (ValueError, AttributeError):
        return out
    for e in entries:
        if isinstance(e, dict):
            out.setdefault((e.get("test", ""), e.get("mark", "")), []).append(e)
    return out


def match_approval(
    entries: List[dict], digest: str, scope_required_from: str = SCOPE_REQUIRED_FROM
) -> Tuple[Optional[dict], str]:
    """(승인 항목 또는 None, 이유). 적용 범위를 대조한다 (TK-215).

    - `scope.body`가 있으면 그 지문과 같을 때만 승인이다
    - 범위가 없고 `approved`가 scope_required_from 이전이면 경과 조치로 승인한다(경고)
    - 범위가 없고 그 날짜 이후면 승인으로 보지 않는다
    """
    legacy: Optional[dict] = None
    for e in entries:
        scope = e.get("scope")
        want = (scope or {}).get("body") if isinstance(scope, dict) else None
        if want:
            if digest and want == digest:
                return e, "범위 일치"
            continue
        approved_on = str(e.get("approved", ""))
        if approved_on and approved_on >= scope_required_from:
            continue
        legacy = e
    if legacy is not None:
        return legacy, "범위 없는 옛 승인(경과 조치)"
    if entries:
        return None, "승인 항목이 있으나 적용 범위가 맞지 않는다"
    return None, "승인 항목 없음"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--digest", nargs=2, metavar=("경로", "시험이름"),
                    help="그 시험의 본문 지문을 출력한다(승인 항목의 scope.body에 넣는다)")
    ap.add_argument("--ref", default="HEAD", help="--digest가 읽을 커밋 (기본 HEAD)")
    args = ap.parse_args(argv)

    if args.digest:
        path, name = args.digest
        sigs = signatures(_show(args.ref, path))
        if name not in sigs:
            print(f"{args.ref}:{path}에 시험 {name}이 없다", file=sys.stderr)
            return 2
        print(body_digest(sigs[name]))
        return 0

    if not args.base:
        ap.error("--base 또는 --digest 가운데 하나가 필요하다")

    if all_evaluator_commits(args.base):
        print(f"시험 삭제·약화 점검 — 기준 {args.base}: 범위의 모든 커밋이 `Agent: evaluator`라 건너뜀")
        return 0

    changed = [p for p in _git("diff", "--name-only", args.base, "HEAD", "--", "tests").splitlines()
               if p.endswith(".py")]
    approvals = approved_marks()
    removed: List[str] = []
    newly_marked: List[str] = []
    approved_seen: List[str] = []
    weakened: List[str] = []
    renamed: List[str] = []
    legacy_scope: List[str] = []
    for path in changed:
        before_src, after_src = _show(args.base, path), _show("HEAD", path)
        before = collect(before_src)
        after = collect(after_src)
        before_sig, after_sig = signatures(before_src), signatures(after_src)
        new_names = [n for n in after if n not in before]
        for name, (asserts, marks) in before.items():
            if name not in after:
                twin = next((n for n in new_names if after_sig.get(n) == before_sig.get(name)), None)
                if twin is not None:
                    new_names.remove(twin)
                    renamed.append(f"{path}::{name} → {twin}")
                    continue
                digest = body_digest(before_sig.get(name))
                entry, why = match_approval(approvals.get((f"{path}::{name}", "delete"), []), digest)
                if entry is not None:
                    approved_seen.append(f"{path}::{name} (삭제, {why})")
                    if why.startswith("범위 없는"):
                        legacy_scope.append(f"{path}::{name} (삭제) — 지문 {digest}")
                else:
                    removed.append(f"{path}::{name}" + ("" if why == "승인 항목 없음" else f" — {why}, 지문 {digest}"))
                continue
            a_asserts, a_marks = after[name]
            added = a_marks - marks
            digest = body_digest(after_sig.get(name))
            unapproved = set()
            for m in added:
                entry, why = match_approval(approvals.get((f"{path}::{name}", m), []), digest)
                if entry is None:
                    unapproved.add(m)
                elif why.startswith("범위 없는"):
                    legacy_scope.append(f"{path}::{name} (+{m}) — 지문 {digest}")
            if added - unapproved:
                approved_seen.append(f"{path}::{name} (+{', '.join(sorted(added - unapproved))})")
            if unapproved:
                newly_marked.append(f"{path}::{name} (+{', '.join(sorted(unapproved))})")
            if a_asserts < asserts:
                weakened.append(f"{path}::{name} (assert {asserts} → {a_asserts})")

    print(f"시험 삭제·약화 점검 — 기준 {args.base}, 변경된 시험 파일 {len(changed)}개")
    for title, items in (("삭제된 시험", removed), ("새로 skip·xfail이 붙은 시험", newly_marked)):
        if items:
            print(f"  [실패] {title} {len(items)}개")
            for it in items:
                print(f"    - {it}")
    if renamed:
        print(f"  [이름 변경] 본문·표시가 같은 시험 {len(renamed)}개(삭제로 세지 않음)")
        for it in renamed:
            print(f"    - {it}")
    if approved_seen:
        print(f"  [승인] 평가 측 승인 목록({APPROVALS})에 있는 표시 {len(approved_seen)}개")
        for it in approved_seen:
            print(f"    - {it}")
    if legacy_scope:
        print(f"  [경고] 적용 범위 없는 옛 승인으로 통과한 항목 {len(legacy_scope)}개 (TK-215 경과 조치)")
        for it in legacy_scope:
            print(f"    - {it}")
        print(f"    범위를 넣으려면 {APPROVALS}의 해당 항목에 \"scope\": {{\"body\": \"<지문>\"}}를 적는다")
    if weakened:
        print(f"  [경고] assert가 줄어든 시험 {len(weakened)}개(약화 의심, 사람이 확인)")
        for it in weakened:
            print(f"    - {it}")
    if removed or newly_marked:
        print("기존 시험을 지우거나 표시를 바꾸려면 먼저 docs/handoff/requests/로 사유를 올리고 평가 측 승인을 받는다.")
        print(f"승인은 적용 범위에 한정된다(TK-215). 승인 항목에 \"scope\": {{\"body\": \"<지문>\"}}를 적고,")
        print("지문은 `python scripts/check_test_edits.py --digest <경로> <시험이름> --ref <기준 커밋>`으로 뽑는다.")
        return 1
    print("  기존 시험의 삭제·표시 변경 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
