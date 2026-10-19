# TK-86 활용도 낮은 화면 정리: 버전 비교·사건 일지·금액 계산·근거 찾기 탭 삭제, 재시도 버튼 이동 (P3, 사용성, 사용자 개선안 2·5·6)
- 근거: 사용자 개선안(2026-10-19) 2·5·6항, 평가 측 코드 검토 회신(HISTORY 10-19).

## 1. 대상과 판단 근거
| 대상 | 위치 | 엔진·보고서 의존 |
|---|---|---|
| 버전 비교 탭 | `apps/web/static/workflow.js` `renderCompare`(310행 부근), `addTab("compare")` | 없음(`document-relations`는 화면·API만 사용) |
| 근거 찾기 탭 | `workflow.js` `renderSearch`(361행 부근), `addTab("search")` | 없음 |
| 금액 계산 탭 | `index.html` 계산 패널, `calculation-workbench.js` | 없음. 서면 안 금액 산식 검사(엔진)와 별개 |
| 사건 일지 탭 | `index.html` 사건 일지 패널 | **엔진은 날짜 분석 결과를 탐지에 쓴다**(`pipeline.py` 549·896~897행). 결과 JSON(`to_payload`, `exporters.py` 58행)에 `timeline`이 있고, 보고서의 '검증 상세(JSON)'와 Excel '기술부록'(`exporters.py` 258행)이 그 결과 JSON을 싣는다. Word·PDF 본문에는 사건 일지가 없다 |
| '같은 입력으로 재시도' 버튼 | `operations.js` 291~294행(위쪽 작업 도구줄) | 재시도 API(`/verification-runs/{id}/retry`)는 당시 입력·비용 한도를 이어 쓰는 복구 경로 |

## 2. 요구
1. 버전 비교·근거 찾기·금액 계산·사건 일지 **탭**을 화면에서 없앤다. 탭 묶음(`workflow.js` `groups`)과 관련 스크립트 로드를 정리한다.
2. **보고서에서 사건 일지를 뺀다(사용자 결정 10-19).** 보고서로 내보내는 '검증 상세(JSON)'·Excel '기술부록'·보고서 스냅숏에서 `timeline`을 제외한다.
   - 날짜 분석 엔진과 실행 결과 JSON(`to_payload`, DB 저장·채점기 입력)의 `timeline`은 **그대로 둔다.** 날짜 모순 탐지와 채점이 이것을 쓴다. 제외는 보고서 내보내기 경로에서만 한다.
   - 보고서 확정 점검·보고서 해시 계산이 바뀌면 그 영향을 PR에 적는다.
3. API·DB 표(`document-relations`·`compare`·`search`·`calculations`)는 이번에 지우지 않는다(마이그레이션 위험). 화면에서 부르지 않게만 한다.
4. '같은 입력으로 재시도'는 위쪽 도구줄에서 빼고 '작업 기록' 창 안으로 옮긴다. 위쪽에는 '검증 시작'과 자료 변경 알림의 '다시 검증'만 남는다.

## 3. 시험
- 서버 시험은 바꾸지 않는다. 화면 시험(`tests/test_frontend_retry.py` 등)은 새 위치에 맞게 고치고 TK-85와 같은 대응표를 낸다.
- 탐지 diff 0, 고정·은퇴 점수 불변.
