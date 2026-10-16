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

## TK45 제출 SHA·현재 HEAD·다음 푸시 동기화 (사용자 전달)

| PR | 본문에 고정된 제출·판정 대상 | 이번 확인 최신 HEAD | 원격 브랜치 |
|---|---|---|---|
| #93 | f8f6e0899f4e80a10ae73fa750fc26d5ecf3adbd | 9ebd28735949b8c5d4a7080b527b9444d0c0980a | codex/post013-track-a-tk45-design |
| #96 | 8d237496f32868f339828bb6ab8cf7622f641263 | bb9b7a4fd0b2aa94f3be5d3e5542ad9483f70027 | codex/post013-track-a-tk45-applicability |

두HEAD는각제출SHA와Steve93acef5의실제병합커밋이며제출SHA는이력에그대로남아있다. 제출SHA대비제품17파일이바뀌었으므로기존판정/CI를새HEAD의판정으로확장하지않는다. CI인용에는대상SHA·runID를붙이고, 실제체크아웃이PR병합ref이면그SHA도구분한다. 제출#93의기존불수용과#96의설계검토대기를이번동기화로승인으로바꾸지않는다. 조회시제출#93 f8f6e08의CI/점수는SUCCESS,제출#96 8d23749는CI failure/점수success이며최신HEAD검사는별도실행중/대기였다. 과거실패를지우거나새HEAD성공으로덮지않는다.

이브랜치에추가푸시하기전, 로컬작업을보존한뒤해당브랜치에서 `git pull --ff-only origin <위 원격브랜치>`로병합커밋을먼저받고HEAD를확인한다. 분기하면멈춰이력을정합시키며강제푸시·원격병합삭제금지다. 두PR은draft를유지하고새설계승인/검토요청/제품착수로해석하지않는다. 이번통지만으로전체시험·비공개재측정·새보완을시작하지않는다.

## 경로 A — TK44/49 및 TK45

- #90 b1e506f inline provider 제한 수용에 이어 #95 정확 5e6e85932a5579eedb84b7bc9ba8f75ec3c7d25d (제품88b0cfd) named PAGE ActualText/capture 제한 범위 최종 수용5485088907. 요청6109737405, CI38144023479/점수38144023440/Docker SUCCESS, 독립 실제PDF18파일 PASS. 평가자 full1회 종료0: 수용1214/원장949/전체6914/브라우저197·실패0/strictXPASS0. 원래 경계/UNKNOWN·접합/법리 결과 및 고정81.7/79.2/0 유지. #98 통합 후 #100/main b68cfee 제한 범위 배포 확인 완료.
- 현재 PAGE resources/direct string의 엄격한 경계증명만 추가하며 indirect는 inspection-only UNKNOWN. capture 상한·partial/unsupported/lifecycle 불완전 상태를 유지한다. 간접문자열 검사 수집과 경계 인증을 혼동하지 않는다. 전체 파서 선형/처리시간 보장을 주장하지 않는다.
- Form/structure-tree/미해석resource/비태그/UNKNOWN primary·0.75 floor·consumer 잔여로 TK44/49 전체open 유지. 낱말사전/항상JOIN/SPACE/기대값교체 금지. 원래61/7ad/TC06 .357/PDF47·19·1/DOCX40·19·1/폭9/fixed 보호 유지.
- TK45 #93 f8f6e0899f4e80a10ae73fa750fc26d5ecf3adbd 불수용 유지: 원래20/actualTXT20 시작과같은2/8·8/8·0/4, 부인·확장 strictincrease 모두미달. #96 최신8d237496f32868f339828bb6ab8cf7622f641263은 공개설계65 PASS 제출/제품0·root 설계검토 대기. reference availability와 법적적용/효과 인증을 구분한 설계부터 승인받는다. 불수용제품 이식금지.
- TK45 원래 정상8/8, 부인·확장 각각시작2/8·0/4보다엄격증가/어느지표도하락0. 기존 finding 삭제/등급완화/다른POSITIVE 요건면제/UNKNOWN·화자·규범·인용 오인증 금지. 목표6/8·3/4는 새하한아님. R6/R7·fixed 보호. 장문 전체pipeline 미완료 측정은 완료로 쓰지 않는다.

## 경로 B — TK55

- #91 86e75e3 cascade source 제한 수용에 이어 #97 정확 2f4e798a052ef2bd6b581d7e69c3738aa1c79eb2 발췌 PHONE/RRN 추가검사 최종 제한수용5485136030. 요청6109620195, CI38143165314/점수38143165365/Docker SUCCESS·독립 actual producer→router27대조 PASS. 원래 개인정보필수/보호 충족. 평가자 full1회 종료0: 수용1214/원장2357/전체8061/브라우저197·실패0/strictXPASS0·fixed81.7/79.2/0. #98 통합 후 #100/main b68cfee 제한 범위 배포 확인 완료.
- 실제 argument context1000자/claim post-mask exactslice의 once-render→cut→strip/mask surviving occurrence, 불변 request/consumer/batch/profile binding만 추가검사한다. malformed-present는 pre-budget 거절, opaque/지원한계/상한초과는 기존payload/예외 유지하며추가검사 ABSTAIN. 기존system/assembled/schema/metadata 검사와 PII 우선순위 유지·추가source는면책아님.
- 역사864 대조와 actual product3664 구현측결과를 구분한다. 승인된4개 역사helper는 inspection_source를 분리해 원래공개 기대값만 유지하며 실제product gate의typed capability는 제거하지 않는다. 기존기대/보호시험 변경0.
- 외부/legacy unknown-role·opaque/unsupported/capture-budget 잔여 known_open, 전체TK55 완료아님. 임의JSON전체폐쇄/키사전확대/value-only명사 추가차단/동일substring 재인증 금지. 성명330/330·60/60/stem16/16, 연락처/RRN 필수·정상≤6/28, TK43 가능≤10/100·8/80/불가≥30/40·24/32 유지. 시작누락이같다는이유로필수게이트 PASS 처리금지.
- 이전#91 최초full exit1/TK71 timing1 및 단독보완6946PASS 기록을 보존한다. 이번#97 full0과는다른SHA/다른실행이다.

- 2026-10-13 온라인 후속: 생성한 claim_id를 PHONE으로 오인한 1건을 확인했다. 공개합성3양성/3대조가 이전8280·현재b68에서 동일해 기존과차단으로 추적한다. actual사용자ID/원문은 전달하지 않는다. 키/UUID모양 일괄면제 금지·근원인증 설계 먼저·원래필수/보호 게이트 유지. 원인·공개대조·제약은 [통합 후속 메모](requests/POST_RELEASE_ONLINE_FOLLOWUP_20261013.md)를 따른다.

## 경로 C — TK73

- #92 최신545c917fd12f9fec40eb52bbccfffaf566bc9fdc은 설계·합성시험만/제품0. 독립 source-tree/native 안전성 제한PASS는 제품·등급·수용기준 승인과 다르다.
- 사용자의 확인필요분리 선택은 구체 기준안 검토다. 기준변경 승인0. 원래A/finding·GLOBAL·UNKNOWN 보호를 유지한다. native EOF는 의미상 제목·명제 역할의 증명이 아니다. 원래111 진짜확인손실+9·오탐추가분리0 및 기존4종AFP3 불변을숨기지않는다.
- 구체 기준/영향/보호 계약 및 승인대상을 검토한 뒤 사용자결정과제품구현. 날짜초기확대보류권고 유지. 원래은퇴4종 앞3 유지/마지막 대조·A FP0/재현≥.302/injection·936/fixed·GLOBAL/party/number/branch/parent/interval/date/amount/list/time 보호 유지.
