# Codex 구현 전달문 — 2026-10-17 잔여 티켓 전용

이 문서 하나가 Codex 구현 세션에 대한 현행 지시다. 이전 전달문 전체를 대체한다. 작성: 평가 에이전트(Claude Code).

## 1. 체제와 현재 판정(2026-10-17)
- 사용자 지시: "이제 프로그램 개발에 codex 미사용, antigravity 구현, claude code 평가 체제로 전환". **Codex는 열린 TK-44·49·55·73만 마무리한다**(TK-45는 10-17 known_open 전환). 새 티켓·새 기능은 배정하지 않는다(새 구현은 Antigravity).
- 평가 측 검토는 한때 멈췄다가 같은 날 사용자 '전체검토' 지시로 **재개**했다. 평가는 Claude Code 평가 세션이 한다.
- **출제 역할은 그대로다:** 봉인 세트·고정 비공개 벤치마크·개발 말뭉치는 저장소를 연결하지 않은 Codex **격리 세션**이 작성·자체 점검한다. 이 구현 세션은 출제·채점에 쓰지 않는다.

| 경로 | 티켓 | PR·SHA | 판정(2026-10-17) | 다음 일 |
|---|---|---|---|---|
| B | TK-55 | #106 `2936764` | **수용**, 평가 측이 통합 | 이 브랜치에 더 푸시하지 않는다. 남은 잔여(기존 저장 16진수 ID, unknown-role·opaque·capture-budget)는 새 설계 메모부터 |
| A | TK-44·49 | #108 `86b7fa5` | **설계 조건부 승인** | 제품 구현 PR 1개. 기존 잔여 시험은 처음 두 단언만 반전, `inspection_complete=false` 유지. 제출 점검표 1~4항. 잔여 종결 계획 1쪽 동봉 |
| A | TK-45 | #96 `5c69062` | **known_open 전환(사용자 결정 10-17), 작업 중지** | 더 푸시하지 않는다. #84·#93·#96은 이력으로 남기고 닫는다(PR 코멘트에 'TK-45 known_open 전환'을 적는다). 재개는 사용자 결정 |
| C | TK-73 | #92 `401d098` | **보류, 최소 수정 먼저** | 서증명을 첫 `,`·`:` 앞까지로 비교하는 최소 수정을 공개 111·330 자료에 적용해 진짜 중복 손실 건수를 보고한다. 0이면 구현, 0보다 크면 좁은 보조 조건 설계. 새 검토 상태는 범위 밖 |

- 판정 원문: [#106](https://github.com/stevelee0119/verify_ACAS_LAW/pull/106#issuecomment-6226441530) · [#108](https://github.com/stevelee0119/verify_ACAS_LAW/pull/108#issuecomment-6226443498) · [#96](https://github.com/stevelee0119/verify_ACAS_LAW/pull/96#issuecomment-6226445169) · [#92](https://github.com/stevelee0119/verify_ACAS_LAW/pull/92#issuecomment-6226447328). 기록: [판정서](../scorecards/f1_gate_verdict.md) 「2026-10-17 Codex 잔여 PR 전체 검토」.
- 이전 PR #63·#79·#80·#84·#85(닫힘)·#93·#95·#97은 위 판정으로 대체된 이력이다. 새 작업은 최신 `origin/Steve_ACASiaLAW`에서 새 브랜치로 시작한다.

## 2. 공통 규칙
- [AGENTS.md](../../AGENTS.md)·[AGENT_ROLES](../AGENT_ROLES.md)의 구현 규칙과 [공통 제출 점검표](NEXT_FOR_ANTIGRAVITY.md#4-공통-제출-점검표)를 따른다.
- Steve 대상 PR의 필수 검사는 4개다(점수 하락 게이트·테스트·Docker OCR readiness·CodeQL 새 경고 게이트).
- **충돌 조정:** Antigravity가 [TK-76](TK-76_focus_types_generalization_cycle1.md)(개발 말뭉치 중점 6유형)으로 `packages/claim_engine/evidence_consistency.py` 등을 고친다. TK-73 작업이 같은 파일을 바꾸면 푸시 전에 최신 `origin/Steve_ACASiaLAW`를 받아 충돌을 해소한다. 증거번호 중복 판정(`_exhibit_lines`·`_numbering`)은 TK-73 영역으로 남긴다.
- 비공개 세트·봉인·고정 비공개 벤치·개발 말뭉치는 요청·열람하지 않는다.

## 3. 티켓별 유지 조건(이전 수용 범위와 보호 기준)
위 1절 판정표가 다음 일을 정한다. 아래는 그 일을 할 때 깨면 안 되는 조건만 남긴 요약이다. 상세 이력은 각 티켓 문서와 [판정서](../scorecards/f1_gate_verdict.md)에 있다.

- **TK-44·49**([TK-44](TK-44_line_join_word_lists_and_ledger_regression.md)·[TK-49](TK-49_ledger_expectations_rewritten_and_join_default.md)): #90·#95 제한 수용 범위(inline provider, named PAGE ActualText·capture 상한)를 유지한다. indirect는 inspection-only UNKNOWN, partial·unsupported·lifecycle 불완전 상태 유지. 낱말 사전·항상 JOIN/SPACE·기대값 교체 금지. 원래 61·7ad·TC06 .357, PDF 47·19·1, DOCX 40·19·1, 폭 9, 고정 81.7/79.2/0 보호. 전체 파서 처리시간 보장은 주장하지 않는다. Form·structure-tree·미해석 resource·비태그·UNKNOWN primary·0.75 floor 잔여로 티켓은 open이다.
- **TK-55**([티켓](TK-55_round8d_overblock_and_key_head_regression.md)): #91·#97·#106 수용 범위를 유지한다. 키·UUID 모양 일괄 면제, 임의 JSON 전체 폐쇄, 키 사전 확대, value-only 명사 추가 차단 금지. 성명 330/330·60/60·stem 16/16, 연락처·주민번호 필수, 정상 ≤6/28, TK43 가능 ≤10/100·8/80·불가 ≥30/40·24/32 유지. 외부·legacy unknown-role, opaque·unsupported·capture-budget, 기존 저장 16진수 ID는 known_open 잔여다([온라인 후속 메모](requests/POST_RELEASE_ONLINE_FOLLOWUP_20261013.md)).
- **TK-73**([티켓](TK-73_exhibit_duplicate_full_tail_as_title.md)): 원래 A등급·finding·GLOBAL·UNKNOWN 보호 유지. 은퇴 4세트 앞 3세트 점수 유지, 마지막 세트 A등급 오탐 0·재현율 ≥.302, injection·936·고정 대조군과 party·number·branch·parent·interval·date·amount·list·time 보호 유지. 날짜 쪽 초기 확대는 보류.
- **TK-45**([티켓](TK-45_defense_negation_by_word_match.md)): known_open(사용자 결정 10-17). 작업하지 않는다. #93·#96의 미수용 제품 코드를 다른 PR로 옮기지 않는다.
- 공통: 제출 SHA와 PR 최신 HEAD가 다르면 판정·CI 인용에 대상 SHA·run ID를 함께 적는다. 다른 SHA의 성공으로 과거 실패를 덮지 않는다. 기존 브랜치에 푸시하기 전 `git pull --ff-only`로 원격을 먼저 받고, 강제 푸시하지 않는다.
