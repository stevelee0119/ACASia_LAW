# Codex 구현 전달문 — 0.13.0 이후 잔여 5건

갱신: 2026-10-12 09:55 KST. 이전 전달문 전체를 대체한다. 사용자 최신 지시 순서에 따라 #95·#97 수용 SHA 통합·통합검증까지 완료했다. 전체 미완료 TK는 44·45·49·55·73이다.

## 역할·시작점

- 저장소 stevelee0119/verify_ACAS_LAW. 라운드 시작2a85aa0e043cb6d13993742c2a053a8b048c48d5, 실제 운영8280a597db40b0905dbacf10c56fa3e9915cafd5/v0.13.0.
- 평가 세션은 제품을 직접 고치지 않고 게이트·판정·수용 SHA 통합·릴리스 준비를 맡는다. 공개 구현 세션은 한 세션 한 경로 A/B/C. 비공개 세트/원문/봉인/정답 열람·요청 금지.
- 설계→공개 양방향 대조→설계 승인→제품→정확SHA CI/3줄 요청→원래 게이트 판정. 같은 접근 두 실패 후 새 설계 필수. 보호 경로·기존 기대값·기준선·CI·버전 변경 금지. 정상 구현브랜치 push/PR 승인됨·Steve/main 직접/강제 push 금지.

## 경로 A — TK44/49 및 TK45

- #90 b1e506f inline provider 제한 수용에 이어 #95 정확 5e6e85932a5579eedb84b7bc9ba8f75ec3c7d25d (제품88b0cfd) named PAGE ActualText/capture 제한 범위 최종 수용5485088907. 요청6109737405, CI38144023479/점수38144023440/Docker SUCCESS, 독립 실제PDF18파일 PASS. 평가자 full1회 종료0: 수용1214/원장949/전체6914/브라우저197·실패0/strictXPASS0. 원래 경계/UNKNOWN·접합/법리 결과 및 고정81.7/79.2/0 유지. Steve aa40019 통합·미배포.
- 현재 PAGE resources/direct string의 엄격한 경계증명만 추가하며 indirect는 inspection-only UNKNOWN. capture 상한·partial/unsupported/lifecycle 불완전 상태를 유지한다. 간접문자열 검사 수집과 경계 인증을 혼동하지 않는다. 전체 파서 선형/처리시간 보장을 주장하지 않는다.
- Form/structure-tree/미해석resource/비태그/UNKNOWN primary·0.75 floor·consumer 잔여로 TK44/49 전체open 유지. 낱말사전/항상JOIN/SPACE/기대값교체 금지. 원래61/7ad/TC06 .357/PDF47·19·1/DOCX40·19·1/폭9/fixed 보호 유지.
- TK45 #93 f8f6e0899f4e80a10ae73fa750fc26d5ecf3adbd 불수용 유지: 원래20/actualTXT20 시작과같은2/8·8/8·0/4, 부인·확장 strictincrease 모두미달. #96 최신8d237496f32868f339828bb6ab8cf7622f641263은 공개설계65 PASS 제출/제품0·root 설계검토 대기. reference availability와 법적적용/효과 인증을 구분한 설계부터 승인받는다. 불수용제품 이식금지.
- TK45 원래 정상8/8, 부인·확장 각각시작2/8·0/4보다엄격증가/어느지표도하락0. 기존 finding 삭제/등급완화/다른POSITIVE 요건면제/UNKNOWN·화자·규범·인용 오인증 금지. 목표6/8·3/4는 새하한아님. R6/R7·fixed 보호. 장문 전체pipeline 미완료 측정은 완료로 쓰지 않는다.

## 경로 B — TK55

- #91 86e75e3 cascade source 제한 수용에 이어 #97 정확 2f4e798a052ef2bd6b581d7e69c3738aa1c79eb2 발췌 PHONE/RRN 추가검사 최종 제한수용5485136030. 요청6109620195, CI38143165314/점수38143165365/Docker SUCCESS·독립 actual producer→router27대조 PASS. 원래 개인정보필수/보호 충족. 평가자 full1회 종료0: 수용1214/원장2357/전체8061/브라우저197·실패0/strictXPASS0·fixed81.7/79.2/0. Steve aa40019 통합·미배포.
- 실제 argument context1000자/claim post-mask exactslice의 once-render→cut→strip/mask surviving occurrence, 불변 request/consumer/batch/profile binding만 추가검사한다. malformed-present는 pre-budget 거절, opaque/지원한계/상한초과는 기존payload/예외 유지하며추가검사 ABSTAIN. 기존system/assembled/schema/metadata 검사와 PII 우선순위 유지·추가source는면책아님.
- 역사864 대조와 actual product3664 구현측결과를 구분한다. 승인된4개 역사helper는 inspection_source를 분리해 원래공개 기대값만 유지하며 실제product gate의typed capability는 제거하지 않는다. 기존기대/보호시험 변경0.
- 외부/legacy unknown-role·opaque/unsupported/capture-budget 잔여 known_open, 전체TK55 완료아님. 임의JSON전체폐쇄/키사전확대/value-only명사 추가차단/동일substring 재인증 금지. 성명330/330·60/60/stem16/16, 연락처/RRN 필수·정상≤6/28, TK43 가능≤10/100·8/80/불가≥30/40·24/32 유지. 시작누락이같다는이유로필수게이트 PASS 처리금지.
- 이전#91 최초full exit1/TK71 timing1 및 단독보완6946PASS 기록을 보존한다. 이번#97 full0과는다른SHA/다른실행이다.

## 경로 C — TK73

- #92 최신545c917fd12f9fec40eb52bbccfffaf566bc9fdc은 설계·합성시험만/제품0. 독립 source-tree/native 안전성 제한PASS는 제품·등급·수용기준 승인과 다르다.
- 사용자의 확인필요분리 선택은 구체 기준안 검토다. 기준변경 승인0. 원래A/finding·GLOBAL·UNKNOWN 보호를 유지한다. native EOF는 의미상 제목·명제 역할의 증명이 아니다. 원래111 진짜확인손실+9·오탐추가분리0 및 기존4종AFP3 불변을숨기지않는다.
- 구체 기준/영향/보호 계약 및 승인대상을 검토한 뒤 사용자결정과제품구현. 날짜초기확대보류권고 유지. 원래은퇴4종 앞3 유지/마지막 대조·A FP0/재현≥.302/injection·936/fixed·GLOBAL/party/number/branch/parent/interval/date/amount/list/time 보호 유지.

## 통합·릴리스·온라인

1. 수용된 #90→#95 및 #91→#97 정확 SHA 의존 범위를 #98/Steve aa40019에 통합 완료했다. 검증0702386과전체tree동일·full1214/2357/8322/197/실패0 및동일SHA CI38188744443/score38188744440/Docker 모두SUCCESS. 불수용 TK45와 미승인 TK73 제품은 제외한다.
2. 통합최종 CI/전체검증·보호/버전 정책→새 봉인 운영/후보 비교→릴리스 PR/승인→배포SHA·health/DB 확인. 첫0.13봉인 재사용금지. 새봉인은 현재 개별판정의 선행조건이 아니다.
3. 실제배포 범위만 등록하고 잔여5건 상태를 전체완료로바꾸지 않는다. 최초10시간 목표는 경과했으며 미완료를숨기지 않는다.
4. 기존 운영 동일SHA의 Claude 법률지침은 사용자 요청으로 ON 유지(Render dep-db5otjdckfvc73aur76g Live). 제품기본OFF·기존시험불변·사용자 재지시 없이 운영OFF자동복원금지.
5. 사용자 단일OFF/ON JSON 대조는 완료했으나 참고자료범위가달라 통제품질평가/정식채택 HOLD. 세부원문·평가자료는 저장소밖/구현전달0. 독립법률채점자1명 후속·토큰 input/output/total 변화JSON 참고. 가격PR87 폐기·가격/비용조회 절차재개0·기존USD40 보호유지.

최신 판정과 측정은 f1_gate_verdict/HISTORY/DAILY_TREND/TICKET_METRICS에 기록한다. 새 봉인 bd746c475dd2cdab은 사용자 제공 후 최초 비교를 완료했다. 기존/신규 소비세트 모두 새봉인으로 재사용하지 않는다. 원문/정답은 구현자에게 전달하지 않는다. 현재 단계는 버전0.13.0유지로 릴리스 최종CI/병합/실제배포 확인이다.

## 2026-10-12 20:53 KST 새 봉인 판정·릴리스 진행

사용자 Drive로 받은 새세트 bd746c475dd2cdab 최초비교 PASS: 운영8280=후보070 15.7/.157/FP0·대조0·A0·인젝션유지. 문서8/결함54·형식오류0/끝문장부호경고16·원문일치확인·문서/정답/토큰수정0. 소비완료·다시새봉인으로사용금지. 버전상향없음/0.13.0유지·태그추가없음. 새봉인입력요청단계는완료했으며 현재는기록PR최종CI→Steve→main릴리스CI→병합/RenderSHA·DB확인이다. 사용자지시운영ON 유지. 미완료5TK와법률품질채택HOLD는유지한다.
