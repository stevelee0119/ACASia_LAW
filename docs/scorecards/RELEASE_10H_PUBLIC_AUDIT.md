# 10시간 릴리스 공개 독립 감사

2026-10-11 한국 시각. 구현·평가와 다른 모델 계열의 독립 감사. 비공개/봉인 자료 접근·전체 verify_all·CI 재실행 없이 공개 코드와 생성 입력만 검토했다. 공식 수용/최종통합/신규봉인/배포와 구분한다.

- TK45 268: 실제 TXT pipeline14건. 티켓 기존 정상3건 유지, 다른 부수부정+최종이행2건에서 새 DENIED 재현. 효과후보가 설정표현에 한정되고 연결된 다음문장 결론을 놓침. 평가측 기존 정상7/8·확장0/4 불승인과 별개의 공개 일반원인이다. 새설계a307 승인·구현중.
- TK73 7e24ba0: 기존 제목충돌/어휘접두사/실제줄 경계 및 Cf 누락 보완 확인. TXT ZWJ/ZWNJ/WORD JOINER/BOM4종 실제원문·A중복1 유지, 공백/쉼표0. PDF에서Cf글리프가 실제 유지된 것으로 확대하지 않음. 날짜·출처span·TK64·결번 대조 유지. 새처리1천/2천/4천 행0.014/0.026/0.054초(기존parser 제외). 구분자 없는unit-wrap은 중복1잔여이며 필수AFP0 정식평가 전이다.
- TK44/49 ebd6b51: c6e 대비1452 join호출 본문 동일, 실제PDF2종 양쪽pipeline 본문·판정·등급·상태·경고·미검증·모델입력·검증키 동일(생성findingID는 별도). NFKC/줄간합성coarse표시·대안선택원본불변·동일길이마스킹원문복원거부·JSON왕복·이전cache·숨김블록 제외 확인. 저장량선형/대안미검증 표시. 메타데이터 한정 수용 권고, 정확CI/평가측보호·비공개호환성 대기. ActualText 미구현·UNKNOWNprimary폭의존·대안별법리미검증 유지.
- TK45 의미설계53631f8: NIKL 공개6페이지 뜻/동음sense를 독립 확인. 제품6범주는 공식분류와 분리해야 하며 REALIZATION≠전체완료, 부분/계획/준비/타행위/보고·모달·독립부정의 보수계약이 조건이다. 설계 진행 가능 의견이며 제품/비공개 수용 판정이 아니다. 기존 정상기대값을 유지하는 신규 사슬 인증 범위로 후속 좁힘 승인.
- TK73 b321370: 독립 actualTXT/PDF 각8개에서 상반된 완전서술은 중복0→1, 정확반복0→0, 다른날짜1→1. 그러나 동일명제의 단일종결 '.'↔'!' 및 '。'↔'.' 변형은0→1 신규 정상경고를 확인해 공식수용 전 보완. 원본rows(생성block_id 제외)·출처slice·실행중 불변 통과. 새projection+번호검사1k/2k/4k 0.0091/0.0184/0.0375초, 기존parser 제외. 별도 공유원본block의 반복leading-strip 최악경로는 구현측 공개counterbenchmark로 발견해 cache보완 중.
- 운영9c1b218→평가통합8446107 읽기전용 배포점검: migrations/requirements/Docker/render.yaml/start_server/config/worker 변경 없음. API설정 snapshot→inprocess worker 설정 유지/drift거부 경로 및 법률profile defaultOFF 확인. 필수신규환경변수 없음. 실제Render 설정 조회·배포·시험을 수행한 증거는 아니며 최종후속45/73 포함후 다시 변경범위만 확인한다. 폐기 #87 가격변경 미포함.
- TK45 0078572: 독립actualTXT20건 오류0. 계획/타객체/다의어/모달/보고/독립부정·정상한정재진술/새주어/인용효과 표본 보존, source/sense/범주와국소span 확인. 그러나 요건앞/부수부정앞의 부분extent가 새완료인증에서 누락돼 POSITIVE·경고0으로 바뀌는 P2를 확인해 공식요청 전 보류. 별도c70b2de 메모85·제품변경전4fail/7pass 제어 승인, 같은event의국소extent 위치보존 보완중. 비법률적 비과거부정도 효과확인요청을 만드는 보수후보 잔여 명시.
- TK73 2f1424d 좁은delta 감사: 독립actualTXT/PDF28개에서 단일종결부호 등가반복1→0 복구, 실질명제/부정/한정/날짜/내부부호/물음표/복수끝부호1→1 유지. 원본rows(생성ID 제외)·출처slice·실행중불변 확인, row별투영1회·가지별anchor격리 유지. shared-block1k/2k/4k 0.0009/0.0018/0.0034초·branch-reference0.0087/0.0175/0.0358초(기존parser 제외). 이번공개delta 차단점없음; 정확CI·검토요청·정식AFP0/최종통합/봉인/배포 별도.
- TK45 d11ae3e 좁은extent 후속감사: 독립actualTXT11개 오류0, argument앞/사슬앞뒤 및연속한정 모두UNCERTAIN/확인요청·supports/total_completion=false. 다른독립절/주어/목적어 extent전파없음, 일부러·무한정 정상경고0 보호, ARGUMENT_PREFIX/PREDICATE_CHAIN 및원문span 일치. 이전007 P2는이범위해소·새차단점없음. 전체/비공개/봉인/CI 재실행하지않았으며 정식판정은별도.


TK45 새clause-first설계f929dc8 공개사전감사: 공식NIKL10query HTTP200·개별면하다/면제하다/소멸하다/받다/제재/책임/징계/우편/소포 sense구분 확인. application role은별도이며사전조회가현문맥법적sense인증을대체하지않음. 새22actualTXT의known-categorical vsUNKNOWNverification 최종판정/source논항·술어·actor·필요성부정근거까지대조하도록조건부승인·제품미감사.

TK73 prefix제품dbda376/기록6570e91 공개사전감사: source경계/어휘각/인용/fullwidth/continuation/내부부제/날짜/locator48개PASS 및총64개원본rows생성block_id제외불변, parser제외12.5k/249·25k/499·50k/999prefix/가지0.0021/0.0041/0.0081초. 그러나무공백실질제목선두부호와명칭차이가TXT/PDF×섹션유무8개모두중복1→0으로합쳐지는새P2를확인해사전수용보류·좁은경계보완요청. 관측공백분리표기대조는1→0으로의도대로였음. 필수비공개/새봉인/full평가대체아님. 비공개자료접근없음.

TK73 최종30a2029/제품471625d 좁은후속감사: 무공백literal8 중복1·관측공백대조8 중복0 구분, 추가actualTXT/PDF12에서continuation/가상공백 인증거부 및 실제원본block 관측공백 긍정대조 PASS. PDF dash/quantifier뒤합성공백 중복1·동일원본block실제공백0. 재구성 physical-line 복사본 prefix인증거부·NFKC raw/global/normalized좌표와원본제목 유지. literal16 원본rows 생성ID제외동일·최종보고SHA의제품차이0. 새차단점없음·기존전체/비공개/봉인/게이트미재실행; exactCI와원래AFP0 정식판정 별도.

TK45 247f64c/보고f71186f 공개actualTXT20 좁은감사: 정중체 필요/권리 frame categorical누락 및면제신청→면제하다 source-prefix오인 두P2 확인·사전보류. 나머지known/UNKNOWN·사실수령/법적객체·화자/과거/부분/직접부정 반대 유지. source근거10 span/JSON/후속중복제외와8k/16k/32k 국소순회0.0069/0.0108/0.0248초 통과. 추가공식6자료 뜻풀이일치·행정처분 SANCTION_DECISION은제품매핑임 명시.

TK45 최소보완8165749 좁은후속actualTXT14 감사PASS: 필요/권리 정중체categorical복구·다른lemma/신청행위면제sense인증없음·능동/피동sense분리·직접/중첩부정/새actor/인용보존·모호책임은확인요청유지. source/span/JSON/후속중복제외PASS·새차단점없음. 최종1a324c9 exactCI/정식20+18은별도. 비공개/봉인/전체미재실행.


## TK45 context / TK73 scoped-role 후속 공개 감사

- TK45 cfec/보고32a: 공개 same-finite-endpoint250/500/1000/2000 contexts의 새resolution단계만0.0122/0.0725/0.3346/1.6852초(이전observation생성제외). 반복긴suffix문자열/words순회초선형 P2. 실제TXT 다른사건/소유자3개도원래1a경고1→0으로same-event증명 P2. 나머지10 반대보존. 설계5203 source-index/actualscan accounting 및양쪽argument-prefix unknown qualification abstention 조건부승인6105568141, 관련456불변. 정식20+18 미재측정.
- TK73 f16: 독립actualTXT/PDF/DOCX42+소수source검사에서 multiline quote 및단일item내인용ref를독립entry로인증하는P2. automatic-number-only DOCX·virtual-peer-gap PDF는UNKNOWN/A유지, glyph-coveredDOCX proof slicing 일치. 보완a393는기존인용P2를복구했지만 numbereditemprefix에서cand-relative line_group 좌표를원문paragraph mask에적용하는P2로세형식 A1→0; unprefixed대조A1 유지. 설계250318 absolute first-item reference span의원문paragraph 투영/완전unprotectedcoverage 조건부승인6105568716. 기존786기대값/원본row/source/TK64경로불변. 정식AFP미실행·비공개/봉인/whole/CI 재실행없음.


## 14:02 KST 최종 공개 보완 점검

- TK45 제품5b998ee/보고0c09885: 독립 actualTXT13 PASS. 다른사건/소유자3 경고 유지, 같은 미확정 수식도 일치만으로 인증하지 않음. 직접부정/다른요건/새주체/인용/조건/부분 보호 및 원래 state/reason/source/JSON 유지. 같은 finite endpoint 250/500/1000/2000 새 source-index 단계0.0011/0.0024/0.0075/0.0092초(기존 observation 생성 제외). 명시 pattern scan7N 및 index lookup O(KlogN); 전체 pipeline 선형 주장 아님. 관련465 PASS, exactCI38113014109 진행중/점수38113014100 SUCCESS. 정식20+18 및 actualTXT20 미실행·미수용.
- TK73 제품e387df1/보고a357716: 독립 actualTXT/PDF/DOCX30 좁은 호환 보호 PASS. 전각 quote/parenthesis 보호 복구, balanced title·정상 괄호형 목록 유지, 전각 heading 새 구문 인증없음, multi-char fold 이후 독립 목록 유지, 이전 bullet 좌표 반례 경고 유지. 생성block_id 제외 원본rows/source 동일·raw glyph/proof slicing 확인. ［］3개 기존reader row-free는 A보존 근거에서 제외. 관련815 PASS; 비공개AFP/whole/봉인 미실행.
- TK73 추가 runtime 사전반례: 원래parser row1/UNKNOWN 그대로이나 새helper가 long reference label을 다시 생성. actualTXT2에서 기존parser 제외0.604/0.571초. 기존TK64 14 PASS. 설계f01c876 조건부승인6105661781: 정확 기존문법 bool existence·원래 eligible first item absolute reference_span 재사용·보호prefix계수만 최소보완. 원래815expects/source/rows 불변·최종SHA CI/3줄 뒤 정식AFP0 판정. a357 호환 보호 PASS는 이 추가 runtime 보완 수용을 대체하지 않는다.
