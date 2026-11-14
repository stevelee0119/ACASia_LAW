"""README '버전별 성능 발전 추이' 그래프를 docs/scorecards/version_performance.csv에서 그린다.

- 입력: docs/scorecards/version_performance.csv(릴리스 SHA를 같은 조건으로 다시 잰 값. 출처·조건은 같은 폴더의
  benchmark_audit_2026-11-13.md). 새 릴리스를 같은 조건으로 재면 이 파일에 한 줄을 더한다.
- 출력: docs/assets/performance_trend.png(README가 이 그림을 싣는다. 그림 아래 벤치마크 설명은
  scripts/update_readme.py가 같은 CSV에서 만든다).
- 문서 도구다. 제품 실행에는 필요 없고 matplotlib가 있어야 한다(pip install matplotlib).

사용: python scripts/render_performance_chart.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "scorecards" / "version_performance.csv"
OUT = ROOT / "docs" / "assets" / "performance_trend.png"
KOREAN_FONTS = ("Noto Sans CJK KR", "NanumGothic", "NanumBarunGothic", "Malgun Gothic", "AppleGothic")


def load_rows(path: Path = DATA) -> list:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    family = next((name for name in KOREAN_FONTS if name in installed), None)
    if family is None:
        raise SystemExit("한국어 글꼴이 없습니다: " + ", ".join(KOREAN_FONTS))
    plt.rcParams.update({"font.family": family, "axes.unicode_minus": False})

    rows = load_rows()
    versions = [r["version"] for r in rows]
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, metadata={"Software": None, "Creation Time": None})
    print(f"저장: {OUT.relative_to(ROOT)} ({len(rows)}개 릴리스)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
