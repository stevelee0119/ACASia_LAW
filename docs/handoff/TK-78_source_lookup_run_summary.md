# TK-78 공식 DB 조회 결과가 실행 단위로 집계되지 않아 온라인 측정이 DB 기여·실패를 보고하지 못한다 (P3, 관측성, 기존 공백)
- 유형: 관측성(실행 기록). 탐지·채점 규칙 변경이 아니다.
- 발견: 평가 측, 2026-10-17 온라인 첫 측정([FIXED_BENCHMARK](../scorecards/FIXED_BENCHMARK.md) 10절). 사용자 승인(평가 측 개선 방안 4번)으로 Antigravity에 배정한다.
- 근거는 실행 기록·접속 점검의 집계뿐이다. 고정 벤치·ragbench의 문서별·항목별 결과는 쓰지 않았다(FIXED_BENCHMARK 4절).

## 1. 증상
- 모델 호출은 `run_manifest["model_execution_summary"]`와 예산 원장으로 실행 단위 집계가 된다. 공식 DB(법령·판례) 조회는 그런 집계가 없다.
  - 조회마다 남는 `LookupTrace.summary()`(`packages/source_adapters/transport.py`)와 문서별 `engine_data["source_lookup"]`(소요 시간·재시도 소진 수)만 있다.
- 그래서 온라인 측정에서 다음을 보고하지 못했다.
  - 공식 DB 조회 수·성공·실패(사유별)
  - 재시도 수와 소요 시간
- 평가 측 접속 점검에서 `www.law.go.kr`는 10회 중 1회 연결이 끊겼다(Linux, 같은 날). 이런 실패가 점수에 얼마나 영향을 주는지 지금은 알 수 없다.

## 2. 요구
1. `run_manifest`에 실행 단위 공식 DB 조회 집계를 추가한다(예: `source_lookup_summary`). 기존 조회 기록(`LookupTrace`, 판정별 `source_lookup`)을 모아 만든다. 새 네트워크 호출을 만들지 않는다.
   - 출처(adapter)별: 요청 수, HTTP 시도 수, 캐시 적중 수, 상태(`AdapterStatus`)별 건수, 재시도 가능 실패 수
   - 실행 전체: 위 항목 합계, 문서별 `spent_seconds` 합, 예산 소진(`recovery_used`) 문서 수
2. 질의어·URL·인용 원문·키(OC)는 넣지 않는다. 건수와 상태 이름만 넣는다.
3. 보고서 내보내기(`to_payload`)에 그대로 실린다. 기존 필드는 바꾸지 않는다.

## 3. 시험
- 실제 진입점(`VerificationPipeline.run`)에서 가짜 전송(transport)으로 성공 1·시간 초과 1·찾지 못함 1·캐시 적중 1을 만든다. 그 뒤 집계 건수가 정확히 맞는지 확인한다(`>= 1`만 보는 시험은 인정하지 않는다).
- 네트워크 끔(`LV_ALLOW_NETWORK=0`)에서 집계가 비어 있거나 0으로 나오고 오류가 나지 않는다.
- 집계에 질의어·URL 문자열이 들어가지 않는지 확인하는 시험 1개.

## 4. 수용
- CI 필수 검사 성공. 고정 81.7/79.2·오탐 0, 은퇴 4세트 점수 불변(탐지 변경 없음).
- 평가 측이 다음 온라인 측정에서 이 집계를 기록에 싣는다(FIXED_BENCHMARK 10절 형식).
