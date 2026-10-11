# Codex 구현 전달문 — 0.13.0 이후 잔여 5건 우선

갱신: 2026-10-11 20:32 KST. 이전 전달문 전체를 대체한다. 사용자 최신 지시: **TK-44·45·49·55·73 구현을 먼저**. 온라인 Claude 법률 지침 OFF/ON·독립 법률 채점은 후속으로 이연한다. 보호 기준과 원래 수용 조건을 유지한다.

## 시작점·역할

- 저장소 `stevelee0119/verify_ACAS_LAW`, 시작 SHA `2a85aa0e043cb6d13993742c2a053a8b048c48d5` (`Steve_ACASiaLAW`). 제품은 실제 운영 `8280a597db40b0905dbacf10c56fa3e9915cafd5`/`v.0.13.0`과 같다.
- 0.13.0 실제 배포 완료(17:11 KST Render Live·동일SHA health/database ok). TK24/43/56/57/69/70/72/74/75 기술 수용 범위 배포 완료. TK44/49/55 부분 보완은 전체 완료가 아니다. TK45 PR84 e21 및 TK73 PR79 214 불수용 제품은 미통합·미배포다.
- 공개 전용 별도 Codex 구현 세션/clone에서 한 세션 한 경로 A/B/C를 수행한다. Codex 평가 세션은 제품을 직접 수정하지 않고 측정·판정·수용 SHA 통합을 담당한다. 구현자의 비공개·봉인·정답·평가 원문 조회/요청 금지.
- 제품 전 설계·공개 양방향 대조·평가 승인. 같은 접근 두 번 실패 뒤 새 설계 없이 세 번째 시도 금지. 평가자는 원인·제약·수용 조건을 전달하고 구현 방법은 구현자가 정한다.
- 보호 경로·기존 기대값·기준선·CI·버전·원장·채점 변경 금지. 구현 커밋 `Agent: implementer`. 공개 제품/합성 시험/설계의 정상 브랜치 푸시·PR 등록은 승인됨. Steve/main 직접·강제 푸시 금지.

## 경로 A — TK44/49 → TK45

- TK44/49 PR90 정확 `b1e506f2eab2b830cb8fb7fd074d22dcdc3be589`: inline ActualText→원래 visible glyph의 유일한 대응에서 JOIN/SPACE를 전달하는 제품 구현 완료. exact CI38132618288/score38132618289/Docker SUCCESS, 정식 요청6108248291. root 관련 공개239 PASS 및 수용/회귀2163 PASS·기존24 xfail 유지. 최종 평가자 전체 verify_all 종료0: 수용1214/원장949/전체6723/브라우저197/실패0/strictXPASS0·고정81.7/79.2/FP0. root5483100719 제한범위 내용 수용, 신규 통합/배포 전이다.
- 초기 독립 감사의 invisible/unclosed/named-outer/nonSpan 반례와 제품 shading-after P2를 보완했다. shading-after UNKNOWN·prior-shading JOIN 대조를 독립 확인했다. MCID는 identity가 아니며 raw glyph/논리 text 매핑은 의미·진실성 인증이 아니다.
- 비태그·미해석 resource/Form/structure-tree·UNKNOWN primary·0.75 floor·consumer는 미보완 잔여. 낱말 사전/항상 JOIN·SPACE/기대값 교체 금지. 원래61 보호·7ad/고정 원장·TC06 0.357·PDF47/19/1·DOCX40/19/1·폭9·81.7/79.2/0 유지. 새 inline provider를 전체 TK44/49 완료로 쓰지 않는다.
- TK45 PR84 e21은 원래 정상8/8 필수 미달로 불수용·전체 이식 금지. 반복 attachment 확대 대신 별도 PR93 설계 `5a51dd35dcc8ffb3ccfbc6547d12d7dcf706369b`·메모112를 root5483024001 조건부 승인했다. 공개 actualTXT25는 baseline/fixture annotation의 독립 재현이며 자동 의미 증명기나 원래 수용 성공이 아니다.
- TK45 제품0dd4b8 제출 후 독립 actualTXT20 사전감사에서 문장간 인용/상대·보고·반박4건과 다른 법률 출처2건의 새 proof 오인증을 재현하여 HOLD6108540760. 양성2와 나머지 반대12는 유지했다. 화자/민사규범 보호 강화 보완 진행 중이며 exact CI·정식 요청 뒤 원래 판정한다. 기존 판정 보존 + 같은 문장 원문으로 확정된 직접 요건부정/개별 법적 효과 finding 추가만 허용. UNKNOWN·인용·상대 주장/반박·조건·계획·중첩 부정·타 논항·필요성·사실 수령·부분 충족·독립 요건은 새 인증 거절. 기존 finding 삭제/재분류·완료 인증·다른 POSITIVE 면제·sense/lemma만으로 효과 인증 금지.
- 원래 TK45 조건: 정상8/8, 부인·확장 각각 시작2/8·0/4보다 엄격 증가, 어느 지표도 감소 없음. 목표6/8·3/4는 새 하한이 아니다. 새 rule_id0·R6/R7 및 fixed score 보호. 제품 CI·정식 요청 뒤 원래 독립 판정.

## 경로 B — TK55

- PR91 정확 `86e75e34c213548c307e71b273b3933f3614bfec`: cascade Primary/Critic/Grounder의 실제 렌더 원문을 요청별 불변 source로 보존하여 기존 lossless 검사를 추가하는 제품 완료. exact CI38132924102/score38132924186/Docker SUCCESS·정식 요청6108286856.
- root 공개 제품101 PASS, 독립 감사 새 합성24 PASS·4adapter mockwire 내부source노출0. 원래 독립 privacy 게이트 충족. 최초 verify_all 종료1: 수용1214/원장1242/전체6945 PASS·기존TK71 시간검사1FAIL/브라우저197. 시작/후보 단독 동일검사 각PASS, 변경 없는 full_tests 단계만 단독1회 보완6946 PASS/실패0/290.3초. 원본exit1 보존·첫 실패 원인 미확정·제품/시험/0.1초 임계값 변경0. root5483126695 제한범위 내용 수용, 신규통합/배포 전. 제출 관련3527 PASS/기존24 xfail은 구현자 측정과 구분한다.
- 원래 system/assembled/schema/metadata 검사는 유지하고 source는 추가 검사일 뿐 면책이 아니다. 실제 stage/system/schema/user binding·removed/forged/mutated source의 pre-budget 거절·PII 우선순위·asdict/repr/wire/log 비노출 보호. 사용자 marker/전역registry로 인증 금지.
- first-party closed builders/lossless duplicate·encoded 검사 유지. value-only 키무관 이름 추정 spike는 정상 명사 추가 차단으로 불승인 유지. 정상JSON 일괄 폐쇄/역할 키 사전 확대/기존 residual PASSED 기대값 교체 금지. 외부·legacy unknown-role은 known_open으로 남으며 전체 TK55 해소가 아니다.
- 원래 정상 과차단≤6/28, PHONE54/RRN84 필수 게이트·성명330/330 및60/60·stem16/16·TK43 구별 가능≤10/100·8/80/구별 불가≥30/40·24/32 유지. 같은 시작 누락을 필수 게이트 통과 이유로 쓰지 않는다.

## 경로 C — TK73

- PR92 정확 `ab5378e4dcf90cd5eba251171490cc570bb794c0`는 설계/공개 진단 및 선택 기준안 검토 메모만이며 제품diff0. root5483050614 제품 승인 HOLD는 source-role 진단5822에 대한 판정이다. 최신 ab5378e 제안은 별도 기준안 검토 대기이며 불수용 PR79 214 전체 이식 금지.
- complete-caption/source-only198, bounded equality/coordinate108의 자체 계약은 원래 수용 대상을 해소하지 못했다. 정의/범위/원문 출처·negative/epistemic/qualifier/quote/완전 제목/global 대조를 분리한다. 공개green을 원래 AFP0 충족으로 쓰지 않는다.
- root 실제 공개 source-role27 독립 재현: 원래 PDF TITLE/PURPOSE·완전 명제 제목 양성·날짜 및 untyped UNKNOWN/A fallback 유지. DOCX native table rows0는 별도 coverage 잔여, 양성 통과가 아니다.
- 제목 인증 부재는 NON_TITLE의 증명이 아니다. 현재 UNKNOWN fallback·GLOBAL·진짜 A 양성을 유지하면서 원래 실패를 해소하는 독립 원문 역할 증명은 확보되지 않았다. 첫 구두점 제목 자르기·키전체 면제·유한 종결/cue 목록·원문 조각 합성 인증·등급 완화 금지.
- 사용자가 ‘확인 필요 분리 설계·기준안 검토’를 선택했다. 구체 기준안을 먼저 검토하며 선택만으로 제품/등급/기존 시험·수용 기준 변경은 승인되지 않았다. 원래 A·확정 중복·확인 필요 및 진짜양성의 확인 필요 이동을 각각 보고하여 단순 AFP0 수치 이동을 막고, 충돌 조항과 이후 승인 대상을 명시한다. 현재 제품/기존 시험/등급/기준은 유지한다.
- 원래 수용: 은퇴4종의 앞3 점수/FP 유지, 마지막 대조/A 오탐0·재현율≥0.302·인젝션, fixed81.7/79.2/0·936/GLOBAL/UNKNOWN/party/number/branch/parent/interval/prose multiplicity·TK64/date/amount/list 보호 및 시간0.1초. 구현 세션 비공개 조회0.

## 수용·통합·릴리스·온라인

1. 공개 설계→사전 승인→제품/양방향 대조→정확 SHA 필수CI와3줄 요청→원래 독립 게이트/필수 전체검증으로 판정.
2. 수용된 정확 SHA만 통합·통합최종 검증. 제한 범위 수용과 티켓 전체 완료를 구분한다. 5건 전체 미완료 상태를 시각이나 green으로 완료 처리하지 않는다.
3. 새 제품 릴리스는 새 봉인 운영/후보 비교가 필요하다. 0.13.0 최초 봉인은 이미 소비했으며 재사용하지 않는다. 봉인 준비는 현재 구현의 선행조건이 아니다. 버전정책·릴리스·실제배포 SHA/DB 확인 후 해당 수용 범위만 deployed로 반영한다.
4. 온라인6쌍/독립변호사1명 조건가림 채점은 사용자 최신 지시에 따라 이연. actualOFF/ON·끝OFF·ON JSON의 actualClaude input/output/total·OFF차이/증감률·실행hash/cache/fallback/실패 기록을 후속 검토한다. 미상null·OFF0percentnull·중복합산/실제호출 삭제 금지.
5. 가격PR87 폐기·가격/계정/쿼터/비용 절차 재개0. 기존 앱 예산 보호/USD40 상한 유지. 최초10시간 목표19:51 KST는 경과했으며 구현/판정 미완료를 숨기지 않는다. 온라인 평가와48–72h 자체평가 기간은 완료로 간주하지 않는다.
