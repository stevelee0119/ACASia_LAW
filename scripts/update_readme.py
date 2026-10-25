"""README의 '버전별 변경 내역' 표와 상세 변경 이력을 docs/releases.json에서 다시 만든다.

- README 표는 `<!-- RELEASES:START -->`와 `<!-- RELEASES:END -->` 사이에 쓴다. 릴리스 계열(주.부 버전)마다
  한 줄로 묶고(최신 계열이 위), 핵심 변경은 docs/release_highlights.json의 요약을 개조식으로 싣는다.
  요약이 없는 계열은 상세 기록 앞 두 항목을 줄여 쓴다.
- 버전별 상세 표는 docs/RELEASE_HISTORY.md에 쓴다(최신 버전이 위).
- 프로그램 버전(packages/common/config.py)이 releases.json에 없으면, 마지막 커밋 제목으로 항목을 추가한다.
  버전을 올리고 기록을 빠뜨려도 README 표가 비지 않게 하기 위해서다.
- `--check`: 바꿀 것이 있으면 종료 코드 1(파일은 고치지 않음).

사용: python scripts/update_readme.py [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
RELEASES = ROOT / "docs" / "releases.json"
HIGHLIGHTS = ROOT / "docs" / "release_highlights.json"
HISTORY = ROOT / "docs" / "RELEASE_HISTORY.md"
CONFIG = ROOT / "packages" / "common" / "config.py"
START, END = "<!-- RELEASES:START -->", "<!-- RELEASES:END -->"
TAG_RE = re.compile(r"\s*\[(?:run-eval|fetch-sources|skip ci)\]")


def current_version() -> str:
    match = re.search(r'^\s*version:\s*str\s*=\s*"([^"]+)"', CONFIG.read_text(encoding="utf-8"), re.M)
    if not match:
        raise SystemExit("packages/common/config.py에서 버전을 찾지 못했습니다")
    return match.group(1)


def _version_key(version: str):
    return tuple(int(part) if part.isdigit() else 0 for part in re.split(r"[.\-]", version))


def _last_commit_subject() -> str:
    try:
        subject = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "변경 내역 기록 없음"
    return TAG_RE.sub("", subject).strip() or "변경 내역 기록 없음"


def load_releases(add_missing: bool = True) -> list:
    releases = json.loads(RELEASES.read_text(encoding="utf-8"))
    version = current_version()
    if add_missing and version not in {item["version"] for item in releases}:
        releases.append({"version": version, "date": date.today().isoformat(), "changes": [_last_commit_subject()]})
    return sorted(releases, key=lambda item: _version_key(item["version"]))


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_table(releases: list) -> str:
    lines = ["| 버전 | 날짜 | 주요 변경 사항 |", "|---|---|---|"]
    for item in reversed(releases):
        changes = "<br>".join(f"• {_cell(change)}" for change in item["changes"])
        lines.append(f"| {item['version']} | {item['date']} | {changes} |")
    return "\n".join(lines)


def _line(version: str) -> str:
    return ".".join(re.split(r"[.\-]", version)[:2])


def load_highlights() -> dict:
    if not HIGHLIGHTS.exists():
        return {}
    data = json.loads(HIGHLIGHTS.read_text(encoding="utf-8"))
    return {key: value for key, value in data.items() if not key.startswith("_")}


def _short(text: str, limit: int = 70) -> str:
    text = re.split(r"[:(]", text, maxsplit=1)[0].strip() or text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_summary(releases: list, highlights: dict) -> str:
    """릴리스 계열별 한 줄. 버전 범위·기간·핵심 변경(개조식)."""
    groups: dict = {}
    for item in releases:
        groups.setdefault(_line(item["version"]), []).append(item)
    lines = ["| 릴리스 | 기간 | 핵심 변경 |", "|---|---|---|"]
    for key in sorted(groups, key=_version_key, reverse=True):
        items = sorted(groups[key], key=lambda r: _version_key(r["version"]))
        first, last = items[0]["version"], items[-1]["version"]
        label = f"**{key}**" + (f" ({first}–{last})" if first != last else f" ({first})")
        dates = sorted(r["date"] for r in items)
        period = dates[0] if dates[0] == dates[-1] else f"{dates[0]} ~ {dates[-1]}"
        points = highlights.get(key) or [_short(c) for c in items[-1]["changes"][:2]]
        lines.append(f"| {label} | {period} | " + "<br>".join(f"• {_cell(p)}" for p in points) + " |")
    return "\n".join(lines)


def history_text(releases: list) -> str:
    return ("# 버전별 상세 변경 이력\n\n"
            "> `docs/releases.json`에서 자동으로 만들어집니다(`python scripts/update_readme.py`). "
            "README에는 릴리스 계열별 요약만 싣습니다.\n\n" + render_table(releases) + "\n")


def updated_readme(releases: list) -> str:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"README에 {START}·{END} 표시가 없습니다")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    note = ("\n\n> 릴리스 계열별 핵심 요약입니다. 버전별 상세는 [변경 이력](docs/RELEASE_HISTORY.md)에 있습니다. "
            "이 표는 `docs/releases.json`·`docs/release_highlights.json`에서 자동으로 만들어집니다"
            "(`python scripts/update_readme.py`).\n\n")
    return f"{head}{START}{note}{render_summary(releases, load_highlights())}\n\n{END}{tail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="바꿀 것이 있으면 1로 끝낸다")
    args = parser.parse_args()
    releases = load_releases()
    readme = updated_readme(releases)
    releases_text = json.dumps(releases, ensure_ascii=False, indent=2) + "\n"
    outputs = ((README, readme), (RELEASES, releases_text), (HISTORY, history_text(releases)))
    changed = [path for path, content in outputs
               if not path.exists() or path.read_text(encoding="utf-8") != content]
    if args.check:
        for path in changed:
            print(f"갱신 필요: {path.relative_to(ROOT)}")
        return 1 if changed else 0
    for path, content in outputs:
        if path in changed:
            path.write_text(content, encoding="utf-8")
            print(f"갱신: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
