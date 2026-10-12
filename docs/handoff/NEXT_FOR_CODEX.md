# Codex 구현 전달문 — 0.13.0 이후 잔여 5건

갱신: 2026-10-12 22:31 KST. 이전 전달문 전체를 대체한다. 사용자 최신 지시 순서에 따라 #95·#97 수용 SHA 통합·통합 검증·새 봉인·릴리스·health 확인까지 완료했다. 전체 미완료 TK는 44·45·49·55·73이다.

## 역할·시작점

- 저장소 stevelee0119/verify_ACAS_LAW. 라운드 시작2a85aa0e043cb6d13993742c2a053a8b048c48d5, 실제 운영 b68cfeec2c5c168a3b9e6e2e92653ea6892521bf/0.13.0. 새 작업은 최신 origin/Steve_ACASiaLAW를 확인하고 시작한다. 배포 제품과 동일한 시작점은 main b68cfeec2c5c168a3b9e6e2e92653ea6892521bf.
- 평가 세션은 제품을 직접 고치지 않고 게이트·판정·수용 SHA 통합·릴리스 준비를 맡는다. 공개 구현 세션은 한 세션 한 경로 A/B/C. 비공개 세트/원문/봉인/정답 열람·요청 금지.
- 설계→공개 양방향 대조→설계 승인→제품→정확SHA CI/3줄 요청→원래 게이트 판정. 같은 접근 두 실패 후 새 설계 필수. 보호 경로·기존 기대값·기준선·CI·버전 변경 금지. 정상 구현브랜치 push/PR 승인됨·Steve/main 직접/강제 push 금지.

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

## 경로 C — TK73

- #92 최신545c917fd12f9fec40eb52bbccfffaf566bc9fdc은 설계·합성시험만/제품0. 독립 source-tree/native 안전성 제한PASS는 제품·등급·수용기준 승인과 다르다.
- 사용자의 확인필요분리 선택은 구체 기준안 검토다. 기준변경 승인0. 원래A/finding·GLOBAL·UNKNOWN 보호를 유지한다. native EOF는 의미상 제목·명제 역할의 증명이 아니다. 원래111 진짜확인손실+9·오탐추가분리0 및 기존4종AFP3 불변을숨기지않는다.
- 구체 기준/영향/보호 계약 및 승인대상을 검토한 뒤 사용자결정과제품구현. 날짜초기확대보류권고 유지. 원래은퇴4종 앞3 유지/마지막 대조·A FP0/재현≥.302/injection·936/fixed·GLOBAL/party/number/branch/parent/interval/date/amount/list/time 보호 유지.

## 릴리스 완료 및 후속 순서

1. 수용 #90→#95와 #91→#97을 통합한 후보 0702386의 원래 필수·보호 게이트, full 1회(1214/2357/8322/197, 실제실패0), 동일 SHA CI를 통과했다. 불수용 TK45와 미승인 TK73 제품은 제외했다.
2. 새 봉인 bd746c475dd2cdab의 최초 운영/후보 비교는 회귀 기준 PASS다. 8문서·54결함에서 양쪽15.7/재현율15.7%/오탐0·대조0·A0·인젝션 방어 유지. 형식오류0·끝문장부호 경고16, 자료·정답·토큰 변경0. 소비 완료이며 새 봉인으로 재사용하지 않는다. 출제 독립성이나 온라인 법률 품질을 별도 입증한 결과는 아니다.
3. #99 관찰 전용 기록 head525a0b5의 원본 CI·점수·Docker와 #100 release head0847109의 필수 CI38253829678/점수38253829611 모두 성공했다. main b68cfeec2c5c168a3b9e6e2e92653ea6892521bf와 검증 릴리스 트리가 같다. Render dep-db6dvjnavr4c73fvnopg Live, 실제 health 동일commit/0.13.0/database ok 확인 완료. 버전 유지·새 태그 없음.
4. TK44·49·55의 수용 부분만 deployed_scope_sha를 갱신한다. 전체 티켓은 open/known_open이고 TK45·73도 미완료다. 전체 미해결5건, 이번 완결 판정0건이다. 원래 10시간 목표의 미달 기록은 보존한다.
5. f64 시간 시험 실패2건(.625568/.748032초, 원래.1초 상한)의 원인·해결은 미확정이다. clock/GC 설정/assert/입력/순서/상한 변경과 node 분리는 없다. 관찰 코드 독립 감사 적합, 이후 원본 CI 통과와 과거 실패를 구별해 CI 신뢰성 잔여로 추적한다. 새 실패를 면제하거나 상한을 낮추지 않는다.
6. 사용자가 요청한 법률 검토 지침 운영ON 설정은 변경하지 않았다. 기본OFF·다른 모델/fallback은 유지한다. 배포 후 사용자가 실제 온라인1회 실행하고 JSON을 제공하면 배포SHA·입력/모델·참고 snapshot 조건과 Claude input/output/total 토큰 변화를 확인해 기존 결과와 비교한다.
7. 독립 법률 채점자1명의 조건가림 품질 검토·정식 채택 판정은 별도 후속/HOLD다. 사용자 단일 OFF/ON 쌍의 참고자료 조건 차이를 통제품질 개선으로 처리하지 않는다. 가격PR87 폐기·가격/비용조회 절차 재개0·기존USD40 보호 유지. 2~3일 사용자 자체평가 뒤 잔여 보완 순서를 조정한다.

최신 판정·실제 배포 기록은 f1_gate_verdict/HISTORY/DAILY_TREND/TICKET_METRICS 및 release_post013_verdict_2026-10-12.json을 따른다. 봉인 원문·정답·항목 상세는 구현 세션에 전달하지 않는다.
