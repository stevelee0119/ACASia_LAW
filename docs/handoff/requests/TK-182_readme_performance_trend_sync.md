# TK-182: README 성능 추이 그래프(`version_performance.csv`) 0.20+ 반영 요청

- **대상(보호 경로)**: `docs/scorecards/version_performance.csv`, `docs/assets/performance_trend.png`
- **배경**:
  - `README.md` 제목을 `ACAS AegisLAW`로 변경하고, `scripts/update_readme.py`가 릴리스마다 상단 운영 버전 배지·`현재 운영 버전:`·검토 화면 탭 구성·기본 모델명을 자동 갱신하도록 보완했습니다.
  - `scripts/render_performance_chart.py`에 `v0.10`을 시작으로 최신 릴리스 기준 1·2·3개월 전 마일스톤을 자동 선택하는 `select_milestone_rows()`를 추가했습니다.
- **평가 측 요청 사항**:
  1. `docs/scorecards/version_performance.csv`에 `v0.20`, `v0.21`(및 향후 `v0.22` 릴리스 시) 동일 오프라인 조건 재측정 행을 추가해 주세요.
  2. 갱신 후 `python scripts/render_performance_chart.py` 및 `python scripts/update_readme.py`로 `docs/assets/performance_trend.png`와 `README.md`를 최신화해 주세요.
