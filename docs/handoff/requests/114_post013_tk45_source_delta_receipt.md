# TK45 직접 원문 부정·효과 증분 제출 기록 (현재 HOLD)

현재 제품 b582e777b711823a4fb1ed548517993bba4a2697은 원문 heading 앞 UNKNOWN 보호까지 관련152 PASS/3.54s이나, 직접부정 뒤 configured conclusion의 malformed 장공백 초선형 반례로 **HOLD**다. 이전2d/ae 제출 기록은 아래 역사적 결과이며 최종 수용 가능한 tip이 아니다. 새 설계116/47e42d8은 제품diff0·공개 language/mapping59 PASS로 승인 대기다. 정확 최종 CI/3줄 요청은 이 차단 해소 이후 제출한다. source grammar O(R*N) 주장을 철회하고 전체 regex 내부 비용을 계측했다고 주장하지 않는다.

시작 `2a85aa0e043cb6d13993742c2a053a8b048c48d5`, 설계 `5a51dd35dcc8ffb3ccfbc6547d12d7dcf706369b`/PR93 review5483024001, 범위 보완 메모 `97c622d`. 최종 제품 `2d487ad15e2e010b9f81b8755fc0ae5889124b7b`. 이 보고서만 추가한 제출 tip의 제품 diff는 0이다. 최종 diff stat: 7 files, +563/-0. 보호 기대값/설정/의존성/CI/버전/기준선/new rule_id 변경 0.

## 변경과 증거

원래 legal_rules 선택·finding을 보존하고, 원문으로 닫힌 직접 독립 `하지 않았` 부정 또는 개별 법적 객체+유한 술어+명시 민사규범 연결의 효과 단정만 기존 rule finding으로 추가한다. 사전 뜻과 application role을 구분하며 원문 논항/격/술어/부정/시제/종료/민법 참조/규범 연결의 exact span/slice를 기록한다. 하다1:1/받다1:10/면하다1(免):1·2 개별 뜻의 NIKL 조회일은 2026-10-11이고 URL·개별sense/한자/정의는 제품 SOURCE_SENSES에 남긴다. 사전 조회 자체는 현재 문맥의 의미나 법적 충분성을 인증하지 않는다.

작성자 아닌 화자/UNKNOWN scope·조건·계획된 결론·중첩 부정·타논항·필요성·사실 수령·부분 범위·다른 요건은 새 증명 실패로 baseline 그대로 남긴다. 기존 verification/SUSPICIOUS/UNVERIFIED finding을 삭제·재분류하지 않는다. 전제 causal 술어는 원문 연결만 기록하고 의미/요건 충족 증거로 쓰지 않는다. 행위주체 entity identity, 행위 병합, 전제 실제 행위, 요건 이행/총완료/사실 진실성/법적 충분성은 모두 false다. 다른 POSITIVE의 존재는 증명·면제 조건이 아니다.

최초제품0dd에서 독립 actual TXT 감사6범주가 IMPLICIT_WRITER/civil_norm을 오인증하여 HOLD였다. 공개9 보호는 사전9 FAIL을 고정했고 최종제품에서 PASS했다. 새 증명은 BODY 첫 비어있지 않은 문장에만 허용하고, 앞 문장이 있으면 인용/보고/반박 종료를 추정하지 않는다. 뒤의 독립 작성자 실제 주장도 이번 증분의 증명 대상이 아니다. civil_norm은 실제 민법+configured 조문번호만이며 헌법/형법을 민사규범으로 기록하지 않는다. 독립 화자 reset·다음 문장 연결·기존 e21 attachment/선택 면제는 이식하지 않았다.

## 최종 관련 시험

제품2d487ad에서 **143 PASS/3.67s**: historical baseline25는 proof-disabled 입력/기대값 불변으로 별도 확인; 실제 enabled25는 미검출6 추가/정상·반대16 유지/기존 경고3 유지 및 다른 엔진 finding의 의미필드 보존을 확인한다. citation_id는 같은 원문을 다시 실행할 때 생성되는 nonce만 제외했고 status/grade/verdict는 제외하지 않는다. 추가37 opposite·실제 TXT/DOCX/PDF595·720 양방향12·정중체/개별sense3·focus2·화자/민사규범9·terminal5·32k UNKNOWN3와 기존 관련보호22를 포함한다. 자동 제품 proof는 fixture annotation을 읽지 않는다. source offset/span/slice·JSON·후속 중복판정 제외까지 검증한다.

첫 terminal 추가 대조 중 외부 paragraph trailing whitespace가 reading_text에서 trim되는 테스트 입력 가정 하나가 실패했다(142 PASS/1 FAIL). 순수 source helper로 trailing space 계약을 별도 확인하고 actual pipeline 입력은 바깥 공백만 trim하여 같은 원문 내부 간격을 검증했다. 기존 제출/보호 기대값은 수정하지 않았다. 교정 뒤 exact 제품143 단일 실행이 위 최종 결과다.

## 성장 비용과 한계

고정 configuration 수 R의 prefix match와 원문 pos/endpos를 사용한다. BODY 문장별 전체 prefix 재검색/후보별 긴 suffix 복사는 없으며 첫 문장 scope는 이미 수행하는 sentence_bounds 순회와 상수 boolean으로 처리한다. 조건 regex는 token 시작에서 한 번 진입하고 terminal의 연속 whitespace 수량자를 내용이 있는 선택 그룹으로 분리했다. source_scope_scans와 prefix/suffix query 카운터는 **regex 내부 방문량의 실측이 아니다**. 새 grammar의 고정 R에 따른 비용과 전체 pipeline 비용을 구분하며 전체 선형 또는 ≤2N을 주장하지 않는다. 새로운 timing 상한/기준 변경 0.

동일환경 helper median5회(초), 공개 양성/UNKNOWN 각 2k→4k→8k→16k→약32k:

| shape | 2k | 4k | 8k | 16k | 약32k | 결과 |
|---|---:|---:|---:|---:|---:|---|
| 긴 양보절 | .000092 | .000112 | .000189 | .000342 | .000642 | proof1 |
| malformed trailing whitespace | .000184 | .000331 | .000627 | .001194 | .002326 | UNKNOWN |
| 단일 긴 한글 token | .000092 | .000143 | .000247 | .000464 | .000907 | UNKNOWN |
| 반복 다른 객체(최대28,868자) | .000086 | .000135 | .000234 | .000435 | .000827 | UNKNOWN |

실제 TXT 전체 pipeline 같은 source 8,000/15,994/31,996자: enabled .879/1.857/4.879s, proof-disabled .821/1.699/5.052s; 실행오류0, enabled proof1+기존 finding1, disabled 기존 finding1. 각각 다른 실행 시점의 단발 측정이므로 미세 overhead 차이를 인과량으로 해석하지 않는다. 전체 성장비 enabled2.11/2.63, disabled2.07/2.97로 전체 엄밀 선형성의 증거가 아니다. 32,000+자 malformed/token UNKNOWN helper는 관련시험으로 보호한다.

재현용 공개 helper 입력은 제품시험의 DIRECT에서 (1) 계약 앞에 `추가 조건과 `를 길이별 반복, (2) 마지막 점 제거 후 공백 N개와 x, (3) 직접 술어 앞에 한글 가 N개, (4) 요건 부정을 `변제공탁 서류를 ` 반복+확인한 뒤 독립 요건완료로 교체하여 생성한다. whole TXT는 첫 형식+청구원인 헤더를 기존 VerificationPipeline로 실행한다. raw corpus나 비공개 자료를 이용하지 않았다.

## 남은 판정·범위

원래 정상8/8 유지 및 부정/확장 각각 시작보다 증가는 평가자가 정확 최종 tip CI 완료+3줄 요청 이후 판단한다. 목표6/8·3/4는 새 하한이 아니다. 이 공개143/format/성장 검사는 원래 필수조건/전체 평가/봉인/릴리스 승인을 대신하지 않는다. 현재 정확 최종 CI 및 독립 수정 감사는 대기이며 TK45 완결을 주장하지 않는다. TK44/49 accepted inline ActualText/SPACE 범위와 비태그 UNKNOWN primary·0.75floor·alternative-aware consumer·resource/Form 전체 잔여는 별도 과제다.
