
- 11-12 사용자 '#260병합' → Steve `18659a1`(expectedHeadSha `d5bca4c`, CI 전부 성공). 버전 0.18.0이 Steve에 들어감. 다음: 릴리스 PR(Steve → main).

### 2026-11-12 0.18.0 릴리스
- 사용자 '릴리스 PR 생성, 병합' → 평가 측이 main `deb387d`에 Steve `18659a1` 병합한 `release/0.18.0`(`5a7f6c7`, 충돌 없음, #189 결정대로 sealed_20261025 등 11개 파일 제외 — 0.17.0과 같은 목록)으로 #261 생성. 자체 점검: check_version_policy·check_protected_paths(바뀐 보호 경로 12개 모두 평가 측 커밋 또는 승인)·update_readme --check 통과, tests/acceptance 1,256건 실패 0(평가 측 재실행). CI(인용) SQLite·PostgreSQL 각 2벌·점수 하락 게이트·은퇴 세트 비교·CodeQL 전부 성공 → 병합 main `3c75071`(expectedHeadSha `5a7f6c7`).
- 태그: 0.14.0~0.17.0과 같이 달지 않았다(원격 최신 태그 v.0.13.1). 사용자 지시가 있으면 `v.0.18.0`을 `3c75071`에 단다.
- 다음: 배포 확인(`/api/health` version 0.18.0·commit `3c75071`) → 0.17.0 대 0.18.0 온라인 비교(online_compare_0170_0180_plan.md).
