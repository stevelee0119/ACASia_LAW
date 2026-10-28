# TK-127 2단계 착수 전 기존 시험 계약 충돌

2026-10-28 · 구현 에이전트 · 기준 `efc9c9c035fb2d28c96da498321987311a9fef3d`

> **해결 / 구현 재개 (2026-10-28 사용자 결정)**: 아래는 당시 충돌 기록이다. 사용자는 구조적 claim_id→citation_id 연결은 식별자 유무·충돌과 관계없이 비구속 참고로 허용하고, SUPPORTS 관계·전체 식별자 일치·충돌 없음일 때만 SUPPORTED 승격하도록 결정했다. 비구조 연결은 식별자 부재·충돌 시 연결과 승격을 모두 차단한다. 기존 시험은 수정하지 않는다. 근거: 평가 브랜치 `NEXT_FOR_ANTIGRAVITY.md` 2-5절 및 #190 사용자 결정. 이 결정으로 아래 중단 사유가 해소되어 같은 브랜치에서 구현을 재개했다.

## 요구와 확인한 충돌

사용자 원문: “공식데이터베이스의 자료를 API로 검색하는 것에 추가로 구글 DRIVE의 자료를 활용”. 이슈 #190 구현 범위 4항과 2026-10-28 사용자 지시는 인용 행 또는 후보 자료 어느 쪽이든 법률 식별자가 없으면 **자동 연결과 SUPPORTED 승격을 모두 금지**한다.

기존 `tests/test_tk126_flat_tabs_answer_import.py`의 `_result()`는 `claim_id → claims[].citation_ids → citation_id` 연결을 제공하지만, 후보 `sources[].text`와 `source_quote`에는 법률 식별자가 없다. `test_rag_observations_attach_to_rows_and_bottom_section_is_gone`은 이 관찰이 인용 행의 `.reference-observations`에 붙기를 단언한다. 현재 `apps/web/static/app.js::attachReferenceObservations`를 Node로 실행한 결과는 인용 행 연결 1건·미연결 1건이다. 새 요구를 지키면 그 인용 행 연결을 금지해야 하므로 기존 단언과 충돌한다.

승인 설계 2절 2)의 1순위에는 구조 ID 일치 시 “즉시 매칭”이라고 적혀 있지만, 같은 절의 식별자 부재 금지와 최신 사용자 지시가 더 엄격하다. 구현자가 ID 연결에 예외를 두어 기존 시험을 통과시키지 않는다.

## 코드 위치 사전 대조와 기준 시험

- `review.py::_match_citations_to_references`·`review_document`, `review_items.py::build_document_review_items`, `schemas.py::ReviewItem/to_dict`, 파이프라인의 `reference_review`와 후행 review_items 재생성 경로를 확인했다. 현재 스키마에는 `reference_observations`가 없으며, 화면은 구조 ID 연결 뒤 8자 포함 fallback을 쓴다. 이는 예정된 수정 대상이다.
- 최신 Steve와 지정 작업 브랜치는 모두 위 기준 SHA다. 사전 확인 당시 #185는 미병합이며, 후속 구현은 TK-129의 `_REFERENCE_O{n}` 규칙을 보존해야 한다.
- 관련 7개 파일 기준 시험은 **122 통과·5 실패**(Windows Python 3.14.6, Edge, 외부 네트워크 비활성). Drive RAG·TK-126·citation_groups·F2 화면·RAG 검토·보고서 범위다. 누락된 체크아웃 의존 모듈을 복원한 뒤 해당 1건만 재실행하여 통과했다. 남은 4건은 Chromium 미설치로 실행 불가한 TK-126 화면 3건, `test_web_shows_drive_health_selection_and_duplicates`의 숨겨진 요소 캡처 시간 초과 1건이다. Chromium 설치도 배포 CDN 시간 초과로 실패했다. 따라서 기준 시험 전체 통과를 주장하지 않는다. 제품 코드·기존 시험 변경은 없다.

## 평가 측에 요청하는 처리와 중단 범위

기존 시험의 목적(관찰이 올바른 행에 보이고 하단 중복 절이 없어짐)은 유지하되, 평가 측에서 구조 ID 연결 양성 입력에 **동일한 전체 법률 식별자**를 양쪽에 넣는 최소 보정을 승인·반영해 주기 바란다. 식별자 부재·충돌 입력은 구조 ID가 연결되어 있어도 미연결이며 SUPPORTED가 아님을 확인하는 별도 대조로 유지하는 방안을 제안한다. 구현 측은 기존 시험을 수정하지 않았다.

사용자 중단 규칙에 따라 **작업 B의 제품 구현을 중단**한다. 시험 계약 정리가 끝나면 승인된 범위에서 서버·브라우저 연결, 보고서 4종, 동적 통제 집계를 구현한다. 통제 벤치마크는 미실행, 운영 Drive는 미측정이다. 이 메모는 수용·통과·병합 요청이 아니다.
