# TK-251: `docs/scorecards/version_performance.csv` v0.24~v0.30.2 반영 및 릴리스별 자동 갱신 연계 요청

- **요청 대상(보호 경로)**: `docs/scorecards/version_performance.csv`
- **배경**:
  - `README.md`의 `버전별 성능 발전 추이` 그래프(`docs/assets/performance_trend.png`)는 `docs/scorecards/version_performance.csv`를 읽어 생성됩니다.
  - 현재 `version_performance.csv`가 `v0.23`(2026-11-19)에서 멈춰 있어, 이후 릴리스(`v0.24`~`v0.30.2`)의 재채점 추이가 그래프에 반영되지 않고 있습니다.
  - 구현 측에서는 `readme-sync.yml`과 `scripts/update_readme.py`를 개선하여 푸시/릴리스마다 `render_performance_chart.py` + `update_readme.py`가 자동 실행되도록 구성했습니다(`README.md` 최근 릴리스 주요 변경·측정 범위 안내 포함).
- **요청 사항**:
  1. `docs/scorecards/version_performance.csv`에 `v0.24`~`v0.30.2` 동일 조건 재채점 행을 추가해 주세요.
  2. 향후 릴리스(0.31.0+) 평가 시에도 `version_performance.csv`에 해당 릴리스 행을 추가하면, `.github/workflows/readme-sync.yml`이 그래프(`performance_trend.png`)와 `README.md`를 자동으로 최신화합니다.
