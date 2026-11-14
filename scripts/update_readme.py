"""README의 '버전별 성능 발전 추이'와 상세 변경 이력을 다시 만든다.

- README에는 `<!-- RELEASES:START -->`와 `<!-- RELEASES:END -->` 사이에 성능 추이 그래프(docs/assets/performance_trend.png)와
  그래프 아래 벤치마크 설명을 쓴다(2026-11-13 사용자 지시: 버전별 변경내역 표를 성능 추이 그래프로). 설명의 측정일·항목 수·
  버전 범위는 docs/scorecards/version_performance.csv에서 읽는다. 그림은 scripts/render_performance_chart.py가 같은 CSV로 그린다.
- 릴리스 계열 요약 표(render_summary)는 함수로 남긴다(docs/release_highlights.json 요약).
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
PERFORMANCE = ROOT / "docs" / "scorecards" / "version_performance.csv"
CHART = "docs/assets/performance_trend.png"
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


def load_performance(path: Path = PERFORMANCE) -> list:
    import csv

    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def render_performance(rows: list) -> str:
    """성능 추이 그림과 그 아래 벤치마크 설명. 숫자는 모두 CSV에서 읽는다."""
    first, last = rows[0], rows[-1]
    dates = sorted({r["measured_on"] for r in rows})
    measured = dates[0] if len(dates) == 1 else f"{dates[0]}~{dates[-1]}"
    return (f"![버전별 성능 발전 추이]({CHART})\n\n"
            f"> **벤치마크 기준** — ACASia_LAW 내부 회귀 벤치마크(공개 벤치마크 아님). 고정 7세트(개발 dev·홀드아웃 holdout·"
            f"은퇴 봉인 5세트) 51문서의 결함·확인불가 **{last['items']}항목**(그중 법률 결함 {last['legal_items']}항목)을 "
            f"{first['version']}~{last['version']} 각 릴리스 코드에 같은 조건(오프라인, 공식 DB·LLM 호출 없음, 한국어 OCR 포함)으로 "
            f"공급해 {measured}에 다시 측정했다.<br>\n"
            "> **왼쪽** 같은 항목을 같은 규칙으로 일대일 재채점한 재현율(%) · **오른쪽** 기존 산식 회귀 점수(/100). "
            "두 패널은 분모·산식이 달라 서로 합산·비교하지 않는다.<br>\n"
            "> 실무 법률 정확도나 KBL 등 공개 벤치마크 점수가 아니다. 공식 DB를 조회하지 않으므로 법률 결함 재현율은 "
            "원문 대조 성능을 대표하지 않는다. "
            "측정 방법: [평가 기준 감사](docs/scorecards/benchmark_audit_2026-11-13.md) · "
            "[평가 v2 규약](docs/scorecards/EVALUATION_V2.md) · 자료: [version_performance.csv](docs/scorecards/version_performance.csv)")


def updated_readme(releases: list) -> str:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"README에 {START}·{END} 표시가 없습니다")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    note = ("\n\n버전별 변경 내역은 [변경 이력](docs/RELEASE_HISTORY.md)에 있습니다(`docs/releases.json`에서 자동 생성). "
            "아래 그래프와 설명은 `python scripts/render_performance_chart.py`·`python scripts/update_readme.py`가 "
            "`docs/scorecards/version_performance.csv`로 만듭니다.\n\n")
    return f"{head}{START}{note}{render_performance(load_performance())}\n\n{END}{tail}"


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
