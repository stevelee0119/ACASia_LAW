# TK-86 활용도 낮은 화면 정리: 버전 비교·사건 일지·금액 계산·근거 찾기 탭 삭제, 재시도 버튼 이동 (P3, 사용성, 사용자 개선안 2·5·6)
- 근거: 사용자 개선안(2026-10-19) 2·5·6항, 평가 측 코드 검토 회신(HISTORY 10-19).

## 1. 대상과 판단 근거
| 대상 | 위치 | 엔진·보고서 의존 |
|---|---|---|
| 버전 비교 탭 | `apps/web/static/workflow.js` `renderCompare`(310행 부근), `addTab("compare")` | 없음(`document-relations`는 화면·API만 사용) |
| 근거 찾기 탭 | `workflow.js` `renderSearch`(361행 부근), `addTab("search")` | 없음 |
| 금액 계산 탭 | `index.html` 계산 패널, `calculation-workbench.js` | 없음. 서면 안 금액 산식 검사(엔진)와 별개 |
| 사건 일지 탭 | `index.html` 사건 일지 패널 | **엔진은 날짜 분석 결과를 탐지에 쓴다**(`pipeline.py` 549·896~897행). 보고서도 사건 일지를 내보낸다(`report_engine/exporters.py` 58행) |
| '같은 입력으로 재시도' 버튼 | `operations.js` 291~294행(위쪽 작업 도구줄) | 재시도 API(`/verification-runs/{id}/retry`)는 당시 입력·비용 한도를 이어 쓰는 복구 경로 |

## 2. 요구
1. 버전 비교·근거 찾기·금액 계산·사건 일지 **탭**을 화면에서 없앤다. 탭 묶음(`workflow.js` `groups`)과 관련 스크립트 로드를 정리한다.
2. 날짜 분석 엔진·결과 JSON의 `timeline`·보고서의 사건 일지 출력은 **그대로 둔다**(사용자 별도 결정 전까지 기본값).
3. API·DB 표(`document-relations`·`compare`·`search`·`calculations`)는 이번에 지우지 않는다(마이그레이션 위험). 화면에서 부르지 않게만 한다.
4. '같은 입력으로 재시도'는 위쪽 도구줄에서 빼고 '작업 기록' 창 안으로 옮긴다. 위쪽에는 '검증 시작'과 자료 변경 알림의 '다시 검증'만 남는다.

## 3. 시험
- 서버 시험은 바꾸지 않는다. 화면 시험(`tests/test_frontend_retry.py` 등)은 새 위치에 맞게 고치고 TK-85와 같은 대응표를 낸다.
- 탐지 diff 0, 고정·은퇴 점수 불변.
