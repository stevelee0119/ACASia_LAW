"""README '버전별 성능 발전 추이' 그래프를 docs/scorecards/version_performance.csv에서 그린다.

- 입력: docs/scorecards/version_performance.csv(릴리스 SHA를 같은 조건으로 다시 잰 값. 출처·조건은 같은 폴더의
  benchmark_audit_2026-11-13.md). 새 릴리스를 같은 조건으로 재면 이 파일에 한 줄을 더한다.
- 출력: docs/assets/performance_trend.png(README가 이 그림을 싣는다. 그림 아래 벤치마크 설명은
  scripts/update_readme.py가 같은 CSV에서 만든다).
- 정본 규칙(TK-252): 로컬 OS·글꼴 차이로 인한 바이트 변동을 막기 위해 `.github/workflows/readme-sync.yml`이
  고정 환경(ubuntu-24.04, Noto Sans CJK KR, matplotlib==3.9.4)에서 렌더한 PNG만 정본으로 삼는다.
  로컬에서 실행한 PNG 결과는 미리보기 전용이며 커밋하지 않는다.

사용: python scripts/render_performance_chart.py [--canonical-ci]
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "scorecards" / "version_performance.csv"
RELEASES = ROOT / "docs" / "releases.json"
OUT = ROOT / "docs" / "assets" / "performance_trend.png"
CANONICAL_FONT = "Noto Sans CJK KR"
KOREAN_FONTS = (CANONICAL_FONT, "NanumGothic", "NanumBarunGothic", "Malgun Gothic", "AppleGothic")


def resolve_chart_font(installed: set[str], *, canonical_only: bool = False) -> str:
    """렌더에 사용할 한글 글꼴을 결정한다. canonical_only=True면 정본 글꼴만 허용한다."""
    if canonical_only:
        if CANONICAL_FONT not in installed:
            raise SystemExit(f"정본 렌더 글꼴이 없습니다: {CANONICAL_FONT}")
        return CANONICAL_FONT
    family = next((name for name in KOREAN_FONTS if name in installed), None)
    if family is None:
        raise SystemExit("한국어 글꼴이 없습니다: " + ", ".join(KOREAN_FONTS))
    return family


def load_rows(path: Path = DATA) -> list:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _release_dates(path: Path = RELEASES) -> dict[str, date]:
    if not path.is_file():
        return {}
    out: dict[str, date] = {}
    for item in json.loads(path.read_text(encoding="utf-8")):
        ver = str(item.get("version") or "")
        short = "v" + ".".join(ver.split(".")[:2])
        try:
            d = date.fromisoformat(str(item.get("date") or ""))
        except ValueError:
            continue
        out.setdefault(short, d)
        out[ver] = d
    return out


def select_milestone_rows(rows: list, release_dates: dict[str, date] | None = None) -> list:
    """v0.10을 시작으로 최신 릴리스 기준 1·2·3개월 전 커밋 마일스톤을 선택한다(기간이 60일 미만이거나 날짜 누락 시 전체 유지)."""
    if len(rows) <= 2:
        return rows
    dates = release_dates if release_dates is not None else _release_dates()
    dated = [(r, dates.get(r["version"])) for r in rows]
    if any(d is None for _, d in dated):
        return rows
    earliest_date = min(d for _, d in dated if d is not None)
    latest_date = max(d for _, d in dated if d is not None)
    if (latest_date - earliest_date).days < 60:
        return rows

    targets = [
        earliest_date,
        latest_date - timedelta(days=90),
        latest_date - timedelta(days=60),
        latest_date - timedelta(days=30),
        latest_date,
    ]
    chosen_indices: list[int] = []
    for target in targets:
        best_idx = min(range(len(dated)), key=lambda i: abs((dated[i][1] - target).days))
        if best_idx not in chosen_indices:
            chosen_indices.append(best_idx)
    chosen_indices.sort()
    return [rows[i] for i in chosen_indices]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-ci", action="store_true", help="고정 정본 글꼴(Noto Sans CJK KR)만 허용")
    parser.add_argument("--out", type=Path, default=None, help="출력 PNG 경로(기본: docs/assets/performance_trend.png)")
    args = parser.parse_args(argv)
    canonical_only = bool(args.canonical_ci or os.getenv("LV_CANONICAL_CHART") == "1")
    out_path = args.out if args.out is not None else OUT

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    family = resolve_chart_font(installed, canonical_only=canonical_only)
    plt.rcParams.update({"font.family": family, "axes.unicode_minus": False})

    rows = select_milestone_rows(load_rows())
    # Mark an unreleased candidate compactly so the rightmost tick remains readable.
    versions = ["v0.22*" if r["version"].endswith("-candidate") else r["version"] for r in rows]
    x = list(range(len(rows)))
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 4.8), dpi=150)

    series_left = (("strict_recall", "결함 항목 재현율(365항목)", "#1f6feb"),
                   ("strict_macro", "유형별 재현율 평균", "#2da44e"),
                   ("legal_recall", "법률 결함 재현율(123항목)", "#cf222e"))
    for key, label, color in series_left:
        values = [float(r[key]) for r in rows]
        left.plot(x, values, marker="o", color=color, linewidth=2, label=label)
        left.annotate(f"{values[-1]:.1f}", (x[-1], values[-1]), textcoords="offset points", xytext=(8, -3), color=color)
    left.set_title("같은 365항목 재채점 — 재현율(%)", loc="left", fontweight="bold")

    # 끝값 글자가 겹치지 않게 dev는 위, holdout은 아래로 비켜 쓴다.
    series_right = (("legacy_dev", "고정 개발 세트(dev)", "#57606a", 5),
                    ("legacy_holdout", "고정 홀드아웃(holdout)", "#bf8700", -12),
                    ("legacy_retired_mean", "은퇴 5세트 평균", "#8250df", -3))
    for key, label, color, dy in series_right:
        values = [float(r[key]) for r in rows]
        right.plot(x, values, marker="o", color=color, linewidth=2, label=label)
        right.annotate(f"{values[-1]:.1f}", (x[-1], values[-1]), textcoords="offset points", xytext=(8, dy), color=color)
    right.set_title("기존 산식 회귀 점수(/100)", loc="left", fontweight="bold")

    for axis in (left, right):
        axis.set_xticks(x, versions)
        axis.set_ylim(0, 100)
        axis.grid(axis="y", color="#d0d7de", linewidth=0.6)
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(loc="lower right", fontsize=9, frameon=False)
        axis.set_xlabel("릴리스")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, metadata={"Software": None, "Creation Time": None})
    plt.close(fig)
    display_path = out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path
    print(f"저장: {display_path} ({len(rows)}개 릴리스)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
