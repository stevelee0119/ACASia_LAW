# Codex 구현 전달문 (현행 통합본)

갱신: 2026-10-11 14:11 KST. 이전 전달문 전체를 대체한다. 미배포·보완 TK 완료와 릴리스에 집중한다. 구현은별도공개전용세션/clone, 평가대화·첨부·비공개·봉인·정답 접근/복사/요청금지. 보호경로/expectations/기준선/버전은평가측담당. 제품전설계메모·양방향합성대조·관련시험만·Agent: implementer·강제푸시/Steve/main직접푸시금지.

## 수용분·릴리스
- main9c1b218/0.12.0. Steve5dea의TK24/43/56/69/70/72/74/75 기술수용·병합·미배포. TK75 기본OFF·실제품질개선미측정.
- #78 c6e5437 TK44/49 직접SPACE보존·#81 0261ea0 TK57 연락처경계·#82 ce83355 TK55 first-party스키마/손실없는JSON·#86 ebd6b51 UNKNOWN진단메타데이터 내용수용. accepted제품통합8446107·remote기록69553cc exactCI38109108790/점수38109108770 SUCCESS. local기록b33d 미푸시.
- UNKNOWNprimary쪽폭/ActualText미구현·TK55legacy24/encoded불명역할잔여를완전해소로기록하지않는다. 수용·통합·운영배포·티켓전체해소구분.
- TK45/73 미수용제품미통합. 수용확정후평가측전체1회/동SHA통합CI/새봉인1쌍/버전/릴리스/온라인. 새봉인미채점. 원래제출14:21KST목표는최소보완검증으로조정: A설계14:25/제품관련14:40/CI후정식14:55 목표, 전체19:51/온라인17:51창 유지. CI/수용생략·기준완화없음.

## 경로 A: TK44/49 수용유지·TK45 최종 CI/평가 대기
- #78 c6e 실제PDF/DOCX/폭105 PASS·명시SPACE48/48·보호기대값유지. #86 ebd1452본문/2실제PDF·72비공개PDF/29기존출력불변 내용수용5481655173. ActualText/primary선택 추가배정없음.
- PR84 0c09885a557d879f50d21870111a27426bee9db3 불수용5481987480. 요청6105692046·exactCI38113014109/점수38113014100 SUCCESS 인용. 원래20 평가측 재실행 부정8/8·정상7/8·확장1/4, 실제TXT전체경로 동일. 정상8/8필수미달. 고정18 부정3/4·정상4/4·화자1/4·재반박1/2·확장4/4. 공개465·독립13 PASS는 대체불가. 미통합·미배포·원래기준/expectations/채점불변·새봉인미실행.
- 출력불변metadata: 실패정상1은 CHANGED_ARGUMENT/UNCERTAIN + ASSERTED_REQUIREMENT_REALIZATION/POSITIVE. configured requirement identity2이고 두 observation identity는서로다름. 신규same-identity resolution resolved0, qualifier abstention까지도달하지않음. 원문/IDs/spans공유0·다른POSITIVE로독립요건/직접부정/불확실면제금지. 같은정상지표정체뒤제품전새공개일반화설계필수.
- 기존정식1a/d11/268 불수용유지. 원래수용: 정상8/8하한·부정/확장각시작2/8·0/4보다증가/어느것도감소없음.6/8·3/4는목표/미달사유보고이지새하한아님. 고정18/공개시험/감사 대체불가.
- clause-first typed-effect와officialsense/applicationmapping구분 유지. same-identity context설계1c8/5203의공개P2 최소보완은통과했지만정상필수실패원인해소안됨. ea80 설계승인6105785316에 따라 서로다른configured요건의참조/검증/행위진술을 source논항·술어·actor·부정·화자·조건으로독립구별한다. 원래state/reason/identity 유지·supports_requirement_fulfillment=false, 별도POSITIVE가 첫요건을충족한다는인증금지. ANYPOSITIVE로다른요건면제금지·사실충족/법률충족인증금지·UNKNOWN확인요청.
- 기존465expects·R6-02/R7-03/R7-08·state/reason/source/grade 유지·newrule_id0·부분/계획/준비/타객체/독립절·주어/상대방인용/화자/재반박/정중체/유한lemma 보호.

## 경로 B: TK55/57 수용유지·버전대기
- #80 설계draft유지/중복구현없음. #81 PHONE누락0/54·RRN0/84·mockprovider0 필수. #82 4first-party스키마/system/output바인딩·PII우선·중복키거부/Unicode/encoded 모든값손실없는검사·providerpayload 유지. 보호144/결합244 PASS·정상차단6/28·faithfulrouter16/16·legacy24/불명역할잔여.
- 가격PR87 사용자명시폐기closed/unmerged. 가격조회/비용계산/증가율조건/후속제품PR재개금지. 기존프로그램예산보호/USD40상한 유지.
- 배포후ON분석JSON 기존실제Claude top-level model_executions만1회집계: input/output/total OFF/ON·차이·변화율·coverage·실행/해시바인딩. missingnull/OFF0percentnull·도큐먼트복사본중복합산금지·동일값인실제별도호출삭제금지. 통화변환/토큰기준없음.
- root최종수용integration SHA/측정판정서후새브랜치version-only1commit. 폐기가격브랜치재사용금지·현재추가제품변경없음.

## 경로 C: TK73 최종 CI/평가 대기
- #79 최신9ab6764/제품95e11e5·관련823PASS/원래817불변. 독립actualTXT/PDF/DOCX15 연속성 대조 PASS. 점수38114012021 SUCCESS; CI38114012034 attempt1의 TK71(PG)/TK24(SQLite) 시간시험 실패는 원본 보존하며, 원래제품/시험 start 대비diff0·각격리 start/candidate PASS 확인 후 같은SHA 실패job만1회 재실행중. 필수CI 성공 전 수용 아님. 원래formal30a AFP3/필수0 불수용5481848611 유지·새formalAFP미실행.
- 이전a357 호환보호독립actualTXT/PDF/DOCX30 PASS, ［］3 row-free는 A보존근거아님. 새74runtime최대.0025초/bool1296조합/원본rows15 불변이나연속성P2보류6105693708.
- c53ae13776c48d3c50d921ab5df0dc5bbfc7c66f 승인6105703232: original 모든item-origin reference순서를 witness view에보존, protected/불명origin/범위누락을UNKNOWNstop으로처리하고뒤항목건너뛰기금지. role key/exemption view만verified/unprotected filter. 원래817expects/source/rows·정확Boolean existinggrammar/runtime회복유지·parser/어휘/입력범위확장0.
- source-covered genericenumerated목록·≥2연속reference-colon·독립peer/ancestor 종료, 원래in_section/sticky/TK64 그대로. rawglyph/sourceproof로만인증·NFKC생성구문/합성join/unknownorigin/oneentry/unclosed/childonly fallback. ancestor narrative면제없음·sibling 다음heading까지만·exactparty/number/branch등록key만 제외. conflictinginventory/미등록key/no-listbody의A 유지. 인용/fullwidth/불릿absolute좌표/continuation/physical-source gap/날짜/amount/gap/listmissing 보호유지.
- inferred-table 진단3 expected0실패+12통과는별도잔여/제품보류·자동strictxfail없음. private어휘/경고삭제/기준완화금지.

## 제출
정확최종SHA의바꾼것·남은것·검토요청3줄을PR에등록한다. 같은SHA 필수CI완료와독립공개delta뒤원래기준으로정식판정. 구현verify_all미실행. 미측정/잔여는사실대로기록·공개green으로전체해소/배포주장금지.
