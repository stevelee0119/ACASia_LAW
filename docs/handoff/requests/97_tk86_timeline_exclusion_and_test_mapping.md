# TK-86: 보고서 timeline 제외 해시 영향, events 처리 방침 및 시험 대응표

- 작성일: 2026-10-21
- 작성자: Antigravity (구현 에이전트)
- 관련 PR: [#154](https://github.com/stevelee0119/ACASia_LAW/pull/154)

---

## 1. 보고서 스냅숏 해시 영향 분석 (TK-86 요구 2)

### (1) 신규 생성 보고서 스냅숏의 해시 변화
- 신규로 생성되는 보고서 스냅숏은 `reports.py` 545~546행에 따라 `engine_result`에서 `timeline` 필드가 제외된 복사본으로 생성됩니다.
- 따라서 새로 발행되는 보고서의 `snapshot_hash`(`canonical_hash(snapshot)`, 559행)는 이전 버전(0.13.1) 대비 `timeline` 필드가 제거된 상태로 해시가 계산되어 데이터베이스에 기록됩니다.

### (2) 기존 저장 보고서에 대한 영향: 영향 없음 (0)
- 데이터베이스에 이미 저장되어 있는 기존 보고서 행(`ReportReview`)은 생성 당시 계산된 고유 해시(`review.snapshot_hash`)를 보유하고 있습니다.
- 저장된 보고서의 무결성 검증 로직(`reports.py` 596행):
  ```python
  snapshot = unpack_snapshot(get_storage(), copy.deepcopy(review.review_snapshot))
  if canonical_hash(snapshot) != review.snapshot_hash:
      raise HTTPException(409, "보고서 스냅샷 무결성을 확인할 수 없습니다")
  ```
  위 로직은 기저장된 스냅숏 blob을 풀어서 저장 당시의 `snapshot_hash`와 1:1 대조합니다.
- 본 PR의 변경 사항은 초안 생성 및 확정 시 신규 스냅숏을 구성하는 함수(`_snapshot`, 545행)에만 적용되며, 기저장된 blob 데이터를 소급 변조하지 않습니다.
- 따라서 기존 저장 보고서의 조회, preflight 확인, 무결성 검증(`_checked_snapshot`)에는 일체의 영향이 없으며 하위 호환성이 안전하게 유지됩니다.

---

## 2. `documents[].events` 처리 방침 (원자료 보존)

### (1) 처리 방침
- **유지 결정**: 보고서 JSON 상세 스냅숏의 개별 문서 원자료인 `documents[].events`(`exporters.py` 82행)는 그대로 보존합니다.

### (2) 유지 사유
1. **개념적 위계 구분 (종합 뷰 vs 원천 엔티티)**:
   - `timeline`은 복수 문서 전체의 날짜-사건을 시계열로 통합/재배열한 파생 종합 뷰(View)입니다. 사용자 결정(10-19)의 취지는 저사용 화면 탭인 '사건 일지'와 보고서 상의 '종합 사건 일지' 뷰를 제외하는 것입니다.
   - 반면 `documents[].events`는 개별 문서 파싱 단계에서 추출된 순수 원천 개체명(Entity/Date-Event) 데이터입니다(`citations`, `claims`, `entities`, `events`와 동일 위계).
2. **감사 추적(Audit Trail) 및 날짜 결함 재현성 보장**:
   - 보고서 상세 JSON은 검증 보조 자료로서 감사 추적용으로 보존됩니다.
   - 날짜 모순(`EVI-DATE`)이나 시효/기한 관련 법리 검토 시, 개별 문서의 어느 문맥에서 해당 날짜 사건이 파싱되었는지 역추적하기 위해 원천 `documents[].events`는 필수적인 근거 데이터입니다.
3. **하위 호환성 및 부수효과 방지**:
   - `documents[].events`는 문서 레벨 정규화 모델의 기본 필드이므로, 이를 임의 제거할 경우 감사 로깅이나 다운스트림 분석 파이프라인에서 필드 누락 오류를 야기할 수 있습니다.
- 따라서 사용자 결정(TK-86 요구 2)에 따라 종합 사건 일지인 `timeline`만을 보고서 산출물에서 철저히 제외하고, 원천 데이터인 `documents[].events`는 보존합니다.

---

## 3. 프론트엔드 시험 변경 대응표

화면 간소화(저사용 4개 탭 및 계산 워크벤치 스크립트 제거, 재시도 버튼 작업 기록 이동)에 따라 갱신된 기존 시험들의 세부 대응표입니다.

| 변경 시험 파일 | 기존 단언 / 기대값 | 변경 후 단언 / 기대값 | 변경 사유 및 요구사항 대응 |
|---|---|---|---|
| `tests/frontend_auth.test.cjs`<br/>(206~207행) | `scripts` 배열 검증:<br/>`["workflow.js", "admin.js", "operations.js", "report-workbench.js", "calculation-workbench.js"]` | `scripts` 배열 검증:<br/>`["workflow.js", "admin.js", "operations.js", "report-workbench.js"]` | **TK-86 요구 1**: 저사용 '금액 계산' 워크벤치 스크립트(`calculation-workbench.js`) 및 탭이 화면에서 제거됨에 따라 번들 스크립트 기대 목록 정비. |
| `tests/test_frontend_admin.py`<br/>(313~328행) | 관리자 작업 공간 탭 그룹 검증:<br/>`자료`: `documents`, `compare`<br/>`검증·검토`: `ai-verification`, `review`, `timeline`, `calculations`, `search`<br/>최종 활성 패널: `search` | 축소된 관리자 작업 공간 탭 그룹 검증:<br/>`자료`: `documents`<br/>`검증·검토`: `ai-verification`, `review`, `issues`<br/>최종 활성 패널: `issues` | **TK-86 요구 1**: 저사용 4개 탭(`compare`, `timeline`, `calculations`, `search`)이 제거되고 검토 탭 구성이 간소화됨에 따라 실제 렌더링되는 탭 목록 및 활성 패널 검증으로 정비. |
| `tests/test_frontend_retry.py`<br/>(48~65행) | 작업 공간 상단 도구줄 버튼 직접 클릭:<br/>`page.locator('#run-actions button:has-text("재시도")').click()` | 작업 기록 모달을 통한 재시도 흐름 검증:<br/>1. 상단 `작업 기록` 버튼 클릭<br/>2. 모달 내 `button:has-text("같은 입력으로 재시도")` 클릭 및 `POST /verification-runs/{id}/retry` 확인 | **TK-86 요구 3**: 상단 도구줄의 무조건적 재시도 버튼을 제거하고, 작업 기록 모달 내 실패/취소/부분완료 작업 행의 컨텍스트 액션으로 재시도 버튼을 이동한 UX 검증. |

---

## 4. 서버 측 검증 시험 추가 내역 (`tests/test_report_timeline_exclusion.py`)

1. `test_timeline_retained_in_execution_payload_but_excluded_from_reports`:
   - 실행 결과 `to_payload()`에는 `timeline`이 정상 유지됨을 단언 (채점기 및 엔진 데이터 무결성).
   - 보고서 payload(`to_payload` with `report_metadata`), Excel 기술부록(`to_xlsx`), 기술 스냅숏(`technical_payload`)에서 `timeline`이 배제됨을 단언.
2. `test_reports_api_snapshot_excludes_timeline` (평가 측 권고사항 반영):
   - `apps/api/routers/reports.py` 내부 `_snapshot` 함수 호출 시 반환되는 `engine_result`에 `timeline`이 없음을 단언.
   - 호출 후 원본 `engine` 객체의 `timeline` 데이터는 보존됨을 교차 단언.
