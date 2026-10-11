# Codex 구현 전달문 (현행 통합본)

갱신: 2026-10-11 16:03 KST. 이전 전달문 전체를 대체한다. 미배포 TK 보완·수용·릴리스에 집중한다. 구현은별도공개전용세션/clone·봉인/비공개/정답/평가원문 접근·요청금지. 제품전설계/관련양방향합성대조·기존expects불변·Agent: implementer. 보호경로·버전판정은평가측·강제push/Steve/main직접push금지.

## 수용분과 릴리스
- 운영main9c1b218/0.12.0. Steve5dea의TK24/43/56/69/70/72/74/75 기술수용·병합·미배포. TK75 기본OFF·실제품질미측정.
- #78 c6e5437(TK44/49 SPACE)·#81 0261ea0(TK57)·#82 ce83355(TK55 first-party)·#86 ebd6b51(UNKNOWN진단) 제한범위 내용수용. accepted제품통합8446107·remote기록69553cc exactCI/점수성공. 후속평가기록은local이며최종수용품통합후push한다.
- TK44/49 UNKNOWNprimary폭의존/ActualText미구현 및 TK55 legacy24/encoded불명역할 잔여는완전해소아님. 수용scope·통합·실제배포·전체티켓해소구분.
- 최종TK45/73 미수용. 수용후최종통합SHA동결→full1회/동SHA필수CI→새봉인운영/후보최초1쌍→버전정책판정/필요버전-only1commit/CI→Steve/main릴리스·Render실제health/APIworkerOFF확인. 원래기준/상한/기준선완화없음. 온라인17:51–19:21KST·전체19:51KST목표.

## 경로 A
- TK44/49 직접SPACE48/48·UNKNOWN24불변·actualPDF/DOCX/width105 PASS·metadata1452본문/2PDF불변 내용수용유지. 추가primary/ActualText제품작업없음.
- PR84 bcea17c660f9cbd3055952b2ae0f1b26f2cfda49 불수용5482118915. 요청6106067158·동일SHA CI38116124746/점수38116124743/Docker SUCCESS 인용. 원래20 평가측 재실행 부인8/8·정상7/8·확장1/4, 실제TXT전체경로 동일. 정상8/8 필수조건 미달. 고정18 부인3/4·정상4/4·화자1/4·반박1/2·확장4/4. 공개537 및 독립 조건부 보호 감사 PASS는 원래 조건 대체불가. 미통합·미배포·새봉인 미실행·기대값/기준선 불변.
- 출력불변 진단: 남은 정상1의 독립요건 identity2와 UNCERTAIN/CHANGED_ARGUMENT·POSITIVE/ASSERTED_REQUIREMENT_REALIZATION 유지. reference_frame 호출0, immediate argument pattern 미일치·기존 event_frame case 존재·predicate_chain 없음. contextual_proposition 생성 전 거절되므로 기존 nominal-modifier/object-tail 설계가 해당 원인을 설명하지 못한다. 원문/식별자/좌표 전달0. 다른 POSITIVE를 이용한 요건 면제나 낱말목록 확장 대신 공개 source 논항·술어 결합 설계부터 재검토.
- bb68a009 공개 case-bound past-event attachment 설계 사전승인6106168162. root actualTXT22에서 기존 확인요청으로3FAIL/19PASS·제품diff0; 독립 NIKL -ㄴ/이후 출처검토 뜻풀이일치. 첫 source의 case→동적 개별lemma→관측 -한→상대적 이후 결합만 증명하며 original state/reason/identity/event_frame 불변·다른행위 비병합·조건/부분/계획/인용/보고/UNKNOWN 보호·원문에 없는 분해자모 source span 생성금지. 이후·형태조합만으로 사실/법적충족/과거발생 추정금지. 기존537 고정. 최소제품/형식대조/선형계측·최종독립감사·exactCI 및 원래필수판정 대기.
- PR84 3736c9ec971c40e85bf3e180a6d656d3185966d0 불수용5482209439. 요청6106331973·완료CI38118075725 양쪽DB FAIL(새PDF생성용 fitz누락4건), 점수38118075720/DockerSUCCESS 구분. 평가측 원래20 부인8/8·정상7/8·확장1/4, actualTXT전체경로동일; 정상8/8 필수미달. 고정18 부인3/4·정상4/4·화자1/4·반박1/2·확장4/4 불변. 공개594/독립actual22 PASS 대체불가. 원래기준/기대값/채점불변·미통합/미배포·새봉인미실행.
- 출력불변3736 진단: 새case_bound_event primitive호출1·원래case/argument순서/공백검사통과·interveningcase0·predicate_chain없음. 새attachment grammar_fullmatchfalse→proof없음·resolved0. 기존SOURCE_SENSES의 exactfinitepast/regularadnominal 인식0. generic -한/-했/-하였 rawshape0은punctuation/다른활용 미확인이라 nonpast판정근거아님. 두독립identity와 원래UNCERTAIN/POSITIVE 불변. 원문/어휘/식별자/좌표전달0. 새 source 논항/술어·closure 설계메모전 제품추가금지·다른POSITIVE로요건면제금지.
- 최종258907052d538192187cf4356338715e648b27fb은공개PDF fixture생성기만fitz→기존reportlab/CID로보완·폭/원문/6expects그대로·6PASS. 제품326diff0. 새CI38118978843/점수38118978817대기이며원래정상7/8 불수용을해소하지않음.
- f51abebe31395a2b2d0faa3371f854785db797a6 auxiliary source-composition 설계조건부승인6106464870. 평가측actualTXT37 오류/skip0·5genuineFAIL32PASS·제품diff0, 독립NIKL5source 뜻/동음구분일치. 자기case→독립dynamichead/observedconnective→resultativeauxiliary→rawpastadnominal→relativeclosure만최소구현중. bare하다 authored-direct-action을COMPLETION/전체fulfillment/facts/legal과분리하며false필드를명시시험으로고정. 기존594/조건guard/관찰identity불변·source자모가상좌표금지·다른act비병합. exact certified auxiliary와동일span의LOCAL_SUBJECT collision만local처리하고다른origin blocker는보존.
- 원래수용은정상8/8유지·부정/확장각시작2/8·0/4보다증가/어느것도감소없음.6/8·3/4는목표/미달사유보고이며새하한아님. 고정18/공개대조는원래20대체불가. 다른요건/주체/독립부정/계획/부분/quote/조건/UNKNOWN면제금지·newrule_id0.

## 경로 B
- TK57 제한 M4 평가측 actual54파일(TXT/PDF/DOCX·물리폭240/600): 동일공개6국제번호의전체원문contact span 운영9c0/36→수용84436/36. contact mockprovider0/144 양쪽동일, 법적번호대조18파일 numericFP0·정상mockprovider72/72 양쪽동일, kind/route/coverage 불변. 같은 fixture SHA256 07ab9c519e5c0f5ae551b5dc0cee8b3eb23b442a8e1b1ee966a3aa63fc32538b. 실제유료호출0/network0; 공개좁은형식증거이고 비공개M2/전체bench/새봉인 결과로쓰지않음.
- TK55/57 수용내용유지·추가제품작업없음. PHONE0/54·RRN0/84·mockprovider0·보호144/결합244·faithfulrouter16/16·JSON손실없는PII우선·legacy잔여구분.
- 가격PR87 명시폐기closed/unmerged. 재개/후속가격작업/계정조회/비용계산/비용증가율기준없음. 기존프로그램예산보호/USD40상한유지.
- 최종측정/버전판정후root확정SHA에서새version-only브랜치/3파일/1commit; 폐기가격branch재사용금지.

## 경로 C
- PR79 214334ddb916a0a856e7a4a55d39cbd180c5ec1a 불수용5482229717. 요청6106394284·exactCI38118526548/점수38118526520/Docker 모두SUCCESS. 평가측 원래4 재실행19.0/29.6/36.2 FP0 유지;20261010 시작15.2/.302/FP3(control3/A3)→25.2/.302/FP1(control1/A1), 기존9ab와동일·필수AFP/control0 미달. 네세트 인젝션방어유지. 공개936/독립GLOBAL실제형식감사PASS는대체불가. 미통합·미배포·새봉인미실행·기준/채점/기대값불변.
- 출력불변214 진단: control7rows/scope1/excluded2/keys4·남은group1 inventorykindNone1/모든narrative종료뒤prose1. 새inventory_atom4회/PASS0·row정규화mapping/단일itemorigin/원래offset순서/definitionmarker4통과. wholeparagraphsource0·nativeatom0→eligible/certified/rowdomain0·latercitation원시함수호출0. 4paragraph모두multi-reading-segment(total16), source없음으로단정하지않음. row정규화일치와originalphysicalglyph proof는구별하며 UNKNOWNjoin을원문으로인증/가상whole-source span생성금지. 원문/어휘/IDs/좌표공유0·기존globalall-origin충돌/UNKNOWN 및interval/936expects 유지.
- 전역guard214는공개독립PASS/936불변이나원래AFP0미달. 원래item/refsource조각을보존하는whole-caption 비교local proof 새설계만검토중·제품은동결. paired-native-title없음을이유로잘라내거나전체registeredkey를면제하지않음.
- TK73 #79 최신9ab6764/95e11e5·관련823·독립actualTXT/PDF/DOCX15 PASS. 요청6105908060 후정식불수용5482055280: 원래4 세트19.0/29.6/36.2 FP0유지·20261010 15.2/.302/FP3→25.2/.302/FP1(control1/A1), 필수0미달·모두injection유지.
- exactCI38114012034 attempt2 completedFAIL TK24 timing.216606/기존.1; PG/Docker/점수38114012021SUCCESS 구분. 최초실패및1회retry보존·같은9ab추가blindretry/시험/상한완화금지. 新정당한제품보완의exactCI는새SHA에서시행.
- 출력불변metadata: scope1/excludedrows2/registeredkeys4, 남은group1 두rows의원래itemorigin/reference_span·등록key유지. inventory內kindNone1 vs모든narrative interval종료뒤kindprose1. 원문/IDs/좌표공유0.
- TK73 bb4d300 설계 전용 사전승인6106093910: 평가측 actualTXT/PDF/DOCX90에서 동일관계9 duplicate1/목표0, 반대·불확실81 duplicate1 유지·원래rows/source 불변. 독립설계감사 조건부 진행 권고. 모든 inventory 대안의 충돌 검사 선행·source parent/exact party/number/branch별 anchor·native 균형제목/조사결합/완결명제 전체source proof·실제 occurrence/선형성·기존interval/prose multiplicity 유지. 비공개AFP 해결/제품수용 근거 아님.
- 현재inventory/narrative interval닫힘불변, 승인설계의 최소source proposition/citation identity 보완만 수행. 등록key+heading+predicate suffix만으로면제금지·문서전역scope확장금지·fullcaption/title충돌·날짜/amount/gap/listmissing/branch/party/quote/UNKNOWN/source/TK64/sticky/원래823expects 보호.
- publiccounter3 inferred-table진단실패는별도잔여/제품보류·자동strictxfail 없음. 원래AFP0 수용조건유지.

## 제출·배포후
최종제품SHA/관련시험·독립공개delta·필수CI후3줄검토요청. root원래조건평가·수용품만통합. 공개green/기존같은문제만으로수용/배포/전체해소주장금지.
배포후법률profile6쌍 actualOFF/ON·독립변호사1명조건가림채점·끝OFF. ON분석JSON 실제Claude top-level model_executions만1회집계 input/output/total·차이/증감률·IDs/hash/coverage(cache/fallback/실패). 미상null·OFF0percentnull·도큐먼트복사본중복합산/동일값실제호출삭제금지. 통화환산/토큰의무기준없음.

최신 사용자: “우선 배포부터”. 온라인 대표6개 사전준비 회신은배포후로이연·배포선행요건추가없음. 실제유료OFFON전에는기존입력/변호사검증/조건고정절차를지킨다.

### 배포 우선 최종 평가 기록 — 2026-10-11 16:34 KST

수용 엔진 3389e9e(제품8446107)는 전체 검증 exit0: acceptance1214·ledger949·full6653·browser197, 실제 실패0/strictXPASS0. 동일 SHA CI38120524487·점수38120524471·Docker 모두 성공했다. 최초 기본 sandbox 실행의 Chromium IPC 실패와 인증 대기는 보존했고, 코드·시험·기준·상한 변경 없이 필요한 로컬 IPC 권한으로 운영/후보 동일 시험과 전체 검증을 통과했다.

첫 봉인 비교(8문서57결함, 지문1abd74597ec4b25a)는 운영9c1b218과 후보3389e9e 모두28.1/.281/FP0·대조군0·A등급0·인젝션방어 성공이다. 별도 깨끗한 작업트리와 Python 프로세스로 실행했고 재측정하지 않는다. 봉인 점수 상승은 없으며 온라인 품질은 미측정이다. 이후 문서·버전 메타데이터만 달라지는 릴리스는 엔진 동등성을 확인한다.

기존8TK+TK57 완료범위와 TK44/49/55 부분보완만 포함한다. TK45(e21, 정상7/8)·TK73(214, AFP1)은 불수용·제외, TK44/49/55의 잔여도 미완료다. 0.13.0 minor 판정은 완결 TK57와 공개 실제54파일 M4 개선에 근거하며 고정/봉인 점수 불변을 성능상승으로 기록하지 않는다. 버전 전용3파일1커밋·최종 SHA 필수CI·병합·Render 실제 SHA/health 확인 후 배포 완료를 기록한다. 온라인 OFF/ON과 독립 법률 채점은 배포 후 진행한다.

구현 담당 B는 평가 기록 커밋을 정확한 시작 SHA로 삼아 새 codex/10h-version-only 브랜치에서 config 버전·docs/releases.json·생성 README만 0.13.0으로 바꾼다. 가격 PR87·제품·시험·CI·평가 기준은 변경하지 않는다. A/C 제품은 이번 릴리스에 추가하지 않는다.
