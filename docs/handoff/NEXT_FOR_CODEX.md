# Codex 구현 전달문 (현행 통합본)

갱신: 2026-10-11 13:26 KST. 이전 전달문 전체를 대체한다. 미배포·보완 TK 완료와 릴리스에 집중한다. 구현은 공개전용별도세션/clone, 평가대화·첨부·비공개/봉인/정답 열람·복사·요청금지. 보호경로/기대값/기준선/버전은평가측담당. 설계먼저·양방향합성대조·관련시험만·Agent: implementer·강제푸시/Steve/main직접푸시금지.

## 수용분·릴리스
- 운영main9c1b218/0.12.0. Steve5dea에 TK24/43/56/69/70/72/74/75 기술수용·병합·미배포. TK75 기본OFF, 실제품질개선 미측정.
- #78 c6e5437 직접SPACE보존·#81 0261ea0 연락처국가코드경계·#82 ce83355 first-party스키마/손실없는JSON검사·#86 ebd6b51 출처정렬UNKNOWN진단메타데이터 제한범위내용수용. 제품통합8446107 및 기록전용69553cc exactCI/점수SUCCESS(695:38109108790/38109108770).
- UNKNOWNprimary쪽폭/ActualText미구현·TK55legacy24/encoded불명역할잔여를 완전해소로기록하지않는다. 내용수용/통합/운영배포/티켓완전해소를구분한다. 기존수용분추가제품배정없음.
- 미수용TK45/73제품은미통합. 최종수용범위확정후 평가측이full1회/동SHA통합CI/새봉인/버전/릴리스/온라인을수행한다. 새봉인미채점. 최종제출14:21KST목표·전체19:51KST·기준완화없음.

## 경로 A: TK44/49 수용 유지·TK45 정상오탐 원인보완
- #78 c6e 실제PDF/DOCX/폭105 PASS·보호문자열기대값유지·명시SPACE48/48. #86 ebd 독립1452본문/2실제PDF 호환성·72비공개PDF/기존29출력동일, 수용5481655173. ActualText/primary선택변경배정없음.
- #84 최신1a324c922a81e7481ca31b6a415829821fba2447/제품81657495309dc9634fe0648653d14cc0d179d100. f929dc8 clause-first typed-effect 승인설계, 기존363/417기대값불변·관련430 PASS 보고. 공개P2 정중체/lemma-prefix 최소보완후 독립actualTXT14·source/span/JSON/후속중복제외 PASS. 공식sense와application분류 구분·새차단점없음. PR84 1a324c922a81e7481ca31b6a415829821fba2447 불수용5481892889. 요청6105422572·exactCI38110886498/점수38110886552 SUCCESS 인용. 기존20 평가측재실행 부정8/8·정상7/8·확장1/4, actualTXT전체경로 동일. 시작2/8·8/8·0/4 대비 부정/확장증가이나 정상8/8 필수미달. 고정18 부정3/4·정상4/4·화자1/4·반박1/2·확장4/4. 공개430·독립actualTXT14 PASS는 대체불가. 원래기준/채점/expectations 유지·미통합/미배포·새봉인미채점. 출력불변metadata 원인: 정상실패1은 CHANGED_ARGUMENT/UNCERTAIN + ASSERTED_REQUIREMENT_REALIZATION/POSITIVE의 동시존재, CONFIGURED authored limited1·scope_uncertain false·typed0·uncertain_quote false. 새효과분기가 아닌 한정요건확인 선택분기. 원문/IDs/spans 전달0. 독립 실제행위 단언과 문맥참조의 관계를 공개일반화설계부터 보완하며 POSITIVE존재만으로 실제부정/다른요건/주체/미확정을면제하지 않는다.
- 이전d11은exactCI성공이나 기존20 부정8/8·정상7/8·확장0/4/실제TXT동일로불수용5481744949. 원래계약: 정상8/8하한·부정/타책임확장 각각시작보다증가/어느것도감소없음. 6/8·3/4는목표/미달사유보고이며새하한아님. 동결18/공개감사는이계약을대체하지않음.
- 새rule_id0·R6-02/R7-03/R7-08·기존210기대값/판정상태·severity·grade 유지. source논항/술어/actor·필요성/부정·다의sense를분리하고 UNKNOWN은확인요청. 낱말명사만으로sense·법률효과/전부이행인증금지. 부분/계획/준비/타객체/독립주어·절/상대방인용/화자/재반박/정중체/유한활용 보호유지. 불수용1a제품은미통합·아래승인설계만보완.

- 새설계1c8ebe8204b4861ded1f03ae776a63c94e877936 조건부승인6105481991·actualTXT15 사전3FAIL/12PASS. 같은configured requirement와관측case/절경계/국소주체·화자/source-supported later direct past assertion 증명시normal limited선택에서 contextual uncertainty만해소. 원래observation/state/source유지·ANY POSITIVE면제금지·중간주체/인용/조건/다른요건/부분/계획/legacy-only 반대보호. 관련430불변·14:21제출목표.

## 경로 B: TK55/57 수용 유지
- #80 설계draft유지·중복구현금지. #81 0261ea0 PHONE누락0/54·RRN0/84·mockprovider0·종류/임계값유지. #82 ce83355 first-party4스키마/system/output바인딩·PII우선차단·중복키거부/Unicode/인코딩 모든값손실없는검사·providerpayload호환성유지. 보호144/통합244 PASS·정상차단6/28·faithful라우터16/16, legacy24/불명역할잔여유지.
- 가격PR87은사용자명시결정으로미병합폐기closed·가격조회/비용계산/증가율조건/후속제품PR재개금지. 기존프로그램예산보호/USD40상한유지. 배포후ON 분석JSON에기존실제Claude model_executions input/output/total OFF/ON·차이·변화율·coverage를참고기록. 제품PR/배포선행조건추가없음.
- 버전작업은root 최종수용integration SHA와측정판정서후새브랜치에서version-only1커밋. 폐기가격브랜치재사용금지·현재추가제품변경없음.

## 경로 C: TK73 새구역역할설계 승인·구현
- #79 현재30a2029256585b8136e077ea3f3d44270aa3dbd6/제품471625d. 요청6105309164·exactCI38110044088/점수38110044065 SUCCESS. 원래은퇴4종19.0/29.6/36.2/15.2·FP0/0/0/3·마지막대조군/A3·필수0미달로불수용5481848611·미통합. 공개652/독립좁은PASS는대체불가. 원문/IDs/spans비공개·새봉인미채점.
- 출력불변계측: 3그룹6행·None3/prose3·mapping6·prefix인증6이나legacy offset변화0. proposed=anchor/양쪽proper-prefix/unknown구분자prefix와다른proposed완전일치0. source-prefix/단순구분자제거가현필수실패원인해소를입증하지못함. balanced outer wrapper만으로표시인증/일괄제거금지.
- 새접근5097af6e5fe5e8099f33dce948a957ec36f8eeb0 scoped-inventory 조건부승인6105395055. 공개actualTXT/PDF36 사전6fail/30pass, root 기존TK64 직접14 PASS. 관측generic목록+구조enumerator·≥2 reference-colon 항목·독립peer/ancestor 종료와원본source의완전범위증거를갖춘comparison-local rolemap만진행.
- 원본row/source/in_section/이전652기대값불변·기존sticky/TK64 의미론유지. exactparty/number/branch가해당proved inventory에있는bodymention만역할구분, 미등록party/branch·상이inventory제목·목록없는상이body양성A 유지. fake/one-entry/child-only/unclosed/가상join/NFKC/애매source는fallback. sibling narrative는다음독립heading경계까지만·이후caption/list임의면제금지. nested/repeatedscope·복수refs·순서변경·TXT/PDF/가능하면DOCX source-span/원본불변대조추가.
- 많은fake/child/미종결heading에도forward O(N)/새처리0.1budget·기존parser전체시간과분리. gap/date/amount/listmissing 모집단/규칙변경0·실질prose충돌/날짜/인용/괄호/Unicode/물리경계/가지별격리보호유지. inferred-table gap은별도잔여제품보류·진단3 expected0보존·자동strictxfail추가없음. private어휘/경고삭제/기준완화금지. 설계승인≠원인/정식수용증명.

## 제출
정확최종SHA의 바꾼것·남은것·검토요청3줄을PR에남긴다. 구현측verify_all미실행. 동일SHA필수CI끝난뒤평가측정식판정. 새실패/잔여/미측정은사실대로기록하며공개시험green으로전체해소/배포를주장하지않는다.
