# Codex 구현 전달문 — 0.13.0 이후 잔여 5건 우선

갱신: 2026-10-11 19:20 KST. 이전 전달문 전체를 대체한다. 사용자 최신 지시: **TK-44·45·49·55·73 구현을 먼저**. 온라인 Claude 법률 지침 OFF/ON·독립 법률 채점은 후속으로 이연한다. 보호 기준과 원래 수용 조건은 유지한다.

## 시작점·역할

- 저장소 `stevelee0119/verify_ACAS_LAW`, 시작 SHA `2a85aa0e043cb6d13993742c2a053a8b048c48d5` (`Steve_ACASiaLAW`). 제품은 실제 운영 `8280a597db40b0905dbacf10c56fa3e9915cafd5`/`v.0.13.0`과 동일하다.
- 0.13.0 배포 완료(17:11 KST Render Live·동일SHA health/database ok). TK24/43/56/57/69/70/72/74/75 기술 수용 범위 배포 완료. TK44/49/55는 부분 보완만 배포·전체 미완료. TK45 PR84 e21 및 TK73 PR79 214 불수용 제품은 미통합·미배포다.
- 별도 공개 전용 Codex 구현 세션/clone에서 한 세션 한 경로 A/B/C를 맡는다. 평가는 Codex 평가 세션이 담당한다. 구현자의 비공개·봉인·정답·평가 원문 열람/요청 금지. 공개 출처와 독립 합성 입력만 사용한다.
- 제품 전 설계 메모·양성/반대 대조·평가 승인. 같은 접근으로 두 번 실패하면 새 설계 전 세 번째 제품 시도 금지. 평가자는 원인/제약/조건을 전달하고 구현 방법은 구현자가 정한다. 평가자는 제품을 직접 수정하지 않는다.
- 보호 경로·원래 기대값·기준선·CI·버전·채점 기준 수정 금지. 구현 커밋 `Agent: implementer`. 정상 브랜치 푸시·PR 등록 승인됨. Steve/main 직접·강제 푸시 금지.

## 경로 A — TK44/49 → TK45

브랜치 `codex/post013-track-a`. 기존 SPACE 및 UNKNOWN 메타데이터 수용 범위는 유지하되 전체 해소로 쓰지 않는다.

- TK44/49: 낱말 사전·항상 JOIN/SPACE·원장 기대값을 잘못된 공백으로 변경 금지. 현재 UNKNOWN primary·0.75 floor 변경은 별도 계약 승인 필요. 원래 7ad 원장/고정 사본·TC06 0.357·PDF47/19/1·DOCX40/19/1·폭9·61 보호 계약 유지.
- 설계110/PR90 e99159f는 design/spike이며 제품diff0. 실제 inline ActualText→원래 glyph의 유일하고 정확한 대응 범위만 첫 제품 후보로 검토한다. MCID는 identity가 아니다. 비태그·미해석 resource/Form·겹침/충돌/회전/hidden/OCR·불명 decoding은 UNKNOWN. source 없는 같은 glyph 입력의 의도를 알아냈다고 주장하지 않는다. consumer는 별도 설계 전 보류.
- 독립 공개 감사에서 invisible render mode3·미닫힌 BDC·unresolved named outer scope·nonSpan Div를 spike가 인증한 반례 발견. balanced invocation 종료·상위 UNKNOWN 전파·가시성/Span 제한 집행을 제품 전 음성 계약에 추가한다. 제품 결함 판정은 아니다.
- TK45 PR84 `e21c40d442f521782cd7d85a18b8fb40655b403d` 불수용5482338759. exactCI/점수/Docker 및 공개815/독립actual26 성공과 별개로 원래20 부인8/8·정상7/8·확장1/4, 실제TXT 전체경로 동일. 정상8/8 필수 미달. 고정18은3/4·4/4·1/4·1/2·4/4. 제품 전체 이식 금지.
- 출력 불변 진단: 독립identity2와 UNCERTAIN/CHANGED_ARGUMENT·POSITIVE/ASSERTED_REQUIREMENT_REALIZATION 유지. case_bound_event 호출1·원래case/order/gap 통과·interveningcase0·predicate_chain 없음. regular/AUX attachment fullmatch false→proof/resolved0. 반복 attachment 확대 대신 새 clause/argument closure 공개 설계부터 제출한다. 원문/어휘/IDs/좌표 전달0.
- 원래 조건: 정상8/8, 부인·확장 각각 시작2/8·0/4보다 증가·어느 지표도 감소 없음. 목표6/8·3/4는 새 하한이 아니다. 다른 요건/행위/주체, 독립 부정·변경·조건·계획·부분·quote·UNKNOWN 면제 금지.

## 경로 B — TK55

브랜치 `codex/post013-track-b`. first-party closed contracts·lossless JSON duplicate/encoded 검사·필수 숫자 보호는 이미 배포됐다. 외부/legacy unknown-role은 known_open이다.

- 키 사전 확대·사용자 JSON/metadata marker 면책·정상JSON 일괄 차단 금지. 원본 system·assembled request·중복/list/escaped evidence를 예산 예약/provider 전 검사하는 보호 유지.
- 설계 `post013_TK55_source_boundary_design.md`, c758e81 공개spike는 비교 실험. 일반 명사6/6 추가 차단을 노출하여 value-only 제품 적용 불승인. 기존 residual-PASSED 시험2개 기대값 유지. typed source 없이 성명과 일반 명사를 구별했다고 주장하지 않는다.
- 공개 코드에서 기존4builder 외 cascade Primary/Critic/Grounder의 실제 source→prompt 경계도 새 설계/spike로 조사한다. immutable consumer-bound 계약·실제 요청/예산/provider 순서·Retry/정상호환을 먼저 검증한다. UNTRUSTED/사용자 marker는 개인정보 면책이 아니다. 제품 전 평가 승인 필요.
- 기존 정상 과차단≤6/28·legacy 잔여 측정 유지. PHONE54/RRN84 필수 게이트·성명330/330 및60/60·stem16/16·TK43 구별 가능 과마스킹≤10/100·8/80, 구별 불가 가림≥30/40·24/32와 명사+조사 성명 형식 유지. 시작SHA에서도 같은 누락이라는 이유로 필수 게이트 통과 처리 금지.

## 경로 C — TK73

브랜치 `codex/post013-track-c`. PR79 `214334ddb916a0a856e7a4a55d39cbd180c5ec1a` 불수용5482229717·전체 이식 금지.

- 원래4 세트19.0/29.6/36.2 FP0 유지, 마지막15.2→25.2지만 FP3→1(control1/A1)이라 필수0 미달. 원래재현율0.302·인젝션 유지. 공개936 및 실제형식 GLOBAL 감사 성공은 대체 근거가 아니다.
- 출력 불변 진단: 남은group1 inventory kind None와 narrative 종료 뒤 prose. inventory_atom4회/PASS0; row 정규화 대응·item origin·offset 순서·definition marker 통과, whole-paragraph source/native quoted atom proof0. source 자체가 없다는 뜻이 아니다. 물리 reading 조각을 합성한 UNKNOWN whole-source로 인증 금지. 원문/어휘/IDs/좌표 전달0.
- 기존name-field/다른역할 colon/separator 확대 설계는 남은 항목 적용0/4 확인됨. 새 complete-caption/source-role/original-piece provenance 설계·실제TXT/PDF/DOCX 양성/반대 대조부터 제출한다.
- original identity/party/number/branch/parent/interval/prose multiplicity·all-origin GLOBAL collision/UNKNOWN guard·936 기대값 유지. 첫 구두점 제목 절단·등록key 전체 면제·문서 전역scope 확장 금지. 날짜/금액/목록누락/인용/TK64/sticky 양성 보호.

## 제출·통합·다음 릴리스

1. 공개 설계/spike → 평가 사전 점검/승인 → 최소 제품/관련 양방향 시험.
2. 최종SHA·관련 결과·동일SHA 필수CI/점수/Docker 완료 후 3줄 검토 요청. CI 인용과 평가 재실행 구분.
3. 평가자는 원래 조건/보호시험으로 판정하고 수용된 정확한 SHA만 통합한다. 공개green/기존같은결함으로 전체 완료를 선언하지 않는다.
4. 통합최종 검증·새봉인 비교·버전정책·릴리스·실제배포 확인 뒤 온라인6쌍. 0.13.0 최초봉인28.1/.281/FP0 운영/후보 기록은 이미 소비했으며 새 제품 릴리스에 재사용하지 않는다. 봉인 준비를 현재 구현의 선행 조건으로 추가하지 않는다.
5. 온라인 actualOFF/ON·독립변호사1명 조건가림 채점·끝OFF. ON분석JSON actualClaude top-level model_executions input/output/total·OFF차이/증감률·hash/coverage/cache/fallback/실패 기록. 미상null·OFF0percentnull·복사본 중복합산/동일값 실제호출 삭제 금지. 가격PR87 폐기·비용/계정/쿼터 조사 재개 없음. 기존 앱 예산 보호/USD40 실행 상한 유지.

19:51 KST는 기존10시간 목표다. 남은5건 전체 완료가 검증되지 않은 상태에서 시각만으로 수용/배포 선언하지 않는다. 이전 상세 결과는 f1_gate_verdict·HISTORY·실제 배포 완료 기록을 참고한다.
