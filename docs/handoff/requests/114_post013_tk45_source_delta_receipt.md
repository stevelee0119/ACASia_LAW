# TK45 직접 원문 부정·효과 증분 제출 기록

시작 `2a85aa0e043cb6d13993742c2a053a8b048c48d5`, 설계112 `5a51dd35dcc8ffb3ccfbc6547d12d7dcf706369b`/PR93 review5483024001 및 승인된 scope115·공백 view116 `47e42d8a603b96fd3f16684fdbc803a0d176672d`에 따른 최종 제품은 **`982e7b36aee1e8ede65790d57cc0da43c4a7869c`**다. 이 receipt만 추가한 제출 tip은 제품 diff0이며 정확 tip CI·독립 감사·원래 수용 판정은 대기다. 제품 diff는 시작 대비 2 files/+299/-0. 보호 기대값/설정/selector/의존성/CI/버전/기준선/new rule_id 변경0. 기존 finding 삭제·상태 전환0.

## 변경과 source 계약

원래 legal_rules 선택·finding을 보존하고, 닫힌 직접 독립 하지 않았 원문 부정 또는 개별 법적 객체+유한 술어+명시 민사규범 연결의 효과 단정만 기존 rule finding으로 추가한다. NIKL 하다1:1/받다1:10/면하다1(免):1·2 개별 뜻의 URL·sense·한자·정의·조회일2026-10-11과 application role을 분리한다. 사전 조회 자체는 현재 문맥이나 법적 충분성을 인증하지 않는다. 원문 논항/격/술어/부정/시제/종료/민법 참조/규범 연결의 exact span/slice를 남긴다.

새 증명은 BODY 첫 비어있지 않은 문장이고 원래 reading source 앞부분이 공백+정확 grounds heading만인 경우에 한정한다. preamble/다른 section/앞 인용·상대방·보고 도입/UNKNOWN source 또는 앞 BODY 문장이 있으면 증명하지 않는다. 후속 작성자 reset·문장간 연결을 추정하지 않는다. civil_norm은 실제 민법+configured 조문번호 결합만이며 헌법/형법을 민사규범으로 기록하지 않는다. 다른 주체/조건/계획/중첩 부정/타논항/필요성/사실 수령/부분 범위/별개 요건은 증명 실패로 baseline 그대로 남긴다.

전제 causal 술어는 원문 연결만 기록하며 의미/요건 충족을 인증하지 않는다. 행위주체 identity, 행위 병합, 전제 실제 행위, 요건 이행/총완료/사실 진실성/법적 충분성은 모두 false다. 다른 POSITIVE를 면제 조건으로 쓰지 않고 이전 e21 attachment/선택 경로를 이식하지 않았다. 기존 verification/SUSPICIOUS/UNVERIFIED 의미를 숨기지 않는다.

## 최종 관련 시험과 기록 정정

제품982e7b에서 **245 PASS/12.82s**: 기존152(관련보호22 포함) 기대값 불변, 공백 언어/mapping 독립 spike60 및 enabled view/원문 mapping/future configuration/실제32k TXT parser→legal 소비자33. historical actualTXT25는 proof-disabled로 원래 결과를 보존하고, 별도 enabled25는 미검출6 추가·정상/반대16 유지·기존 경고3 유지를 확인한다. 다른 엔진 finding은 실행마다 생성되는 citation_id nonce만 제외하고 status/grade/verdict 등 의미 필드를 전부 비교한다. 실제 전체 VerificationPipeline TXT/DOCX/PDF595·720 양방향12, 정중체/sense/focus/화자/민사규범/heading/terminal 및 source span·slice/JSON/후속 중복판정 제외도 포함한다. 제품 parser는 fixture annotation을 답으로 읽지 않는다.

이전 커밋589e30a 메시지의 **243 PASS는 잘못된 기록**이다. 해당 실제 출력은 **242 PASS/1 FAIL/11.92s**였고, 새 장문 시험이 기존 claim preview300과 full original span을 같다고 가정한 실패였다. 982e7b에서 새 장문만 preview300과 전체 BODY/span을 각각 확인하도록 교정했고 기존152/짧은 기대값은 변경하지 않았다. 원래 실패와 잘못된 메시지를 amend/삭제하지 않았으며 위245 단일 완료 결과와 구분한다. 앞선 terminal 대조142 PASS/1 FAIL은 외부 trailing whitespace trim 가정 오류였고 source helper와 actual parser 입력을 분리한 뒤 제품2d의143 PASS로 교정했다.

## 공백 view와 비용 범위

제품b582e77의 configured conclusion malformed 장공백에서 helper2k/4k/8k .08695/.36428/1.49223s 반례로 HOLD였고 O(R*N) regex 내부 비용 주장을 철회했다. 설계116 승인 후 직접 부정 경로 citation 뒤 local 영역을 한 번 lazy 공백 view로 만든다. 비공백 codepoint를 바꾸지 않고 공백 run 하나의 view space에 원래 run start/end를 붙인다. 현재5개 configured regex·terminal 언어를 그대로 적용하며 원래 conclusion 좌표를 복원한다. 미래 literal/정량 공백·lookaround·기타 미승인 문법, malformed/empty/zero-width 결론은 새 proof abstain이다. 원문 텍스트나 기존 regex 설정을 교체하지 않는다.

정확 제품982e7b에서 helper median5회(초), 중간 공백2k→4k→8k→16k→32k:

| source | 2k | 4k | 8k | 16k | 32k | 결과 |
|---|---:|---:|---:|---:|---:|---|
| 정상 한정 결론 | .000267 | .000518 | .000924 | .001758 | .003498 | proof1 |
| 결론 불일치 | .000249 | .000460 | .000868 | .001702 | .003597 | UNKNOWN/새 proof0 |

32,061자 정상 source에서 view build1, 실제 view scan32,036chars, join37chars, denial→view 이진조회1, requirement prefix query2/conclusion query1이다. 이진조회 O(log M) overhead를 scan accounting과 구분한다. source_scope_scans/query 카운터는 regex 내부 방문량을 계측하지 않으며 전체 pipeline 선형성·고정 상한 충족을 증명하지 않는다. timing 예산/threshold 변경0.

## 전체 pipeline 잔여와 판정

**중간 공백32k 전체 VerificationPipeline은 proof-disabled에서도 기존 classifier.find_pattern_hits 단계가 >60초여서 중단(exit130), 완료 결과 미측정이다.** 시작2a85와 현재 classifier blob은 모두 `86c0f239a58060d788b0ba3b352e38335ffbd5de`다. 같은 source byte라는 사실을 gate 통과로 처리하지 않는다. 새33 시험의 장문2건은 실제 TXT parse_document→review_legal_rules 소비자만 검증했고 이를 전체 앱 성능 보장으로 보고하지 않는다. 기존 whole pipeline25/format12/heading 대조는 그대로다.

이미 완료한 b582의 다른 공개 긴 양보절 wholeTXT8,000/15,994/31,996자 .8676/1.8504/5.3784s와 earlier2d enabled .879/1.857/4.879s·disabled .821/1.699/5.052s는 **역사적 별도 입력/측정**으로 보존한다. 이것은 최종 제품의 32k 공백 전체 pipeline 성공 또는 엄밀 선형성 근거가 아니다. b582 성능 HOLD/0dd 화자·norm HOLD/heading HOLD 및 이전 CI 서명도 보존한다.

원래 정상8/8 유지 및 부정/확장 각각 시작보다 엄격 증가는 평가자가 정확 제출 tip CI 완료+3줄 요청 후 판정한다. 목표6/8·3/4는 새 하한이 아니다. 공개245/format/성장 검사는 원래 필수조건·전체 평가·봉인·릴리스 승인을 대체하지 않는다. TK45 완결을 주장하지 않는다. TK44/49 수용 inline ActualText/SPACE와 비태그 UNKNOWN primary·0.75floor·alternative-aware consumer·resource/Form 전체 잔여는 별도 설계 과제다.
