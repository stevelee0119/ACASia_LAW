# 배포 후 온라인 점검 후속 — 2026-10-13

평가 시작: 실제 운영 main b68cfeec2c5c168a3b9e6e2e92653ea6892521bf, 기록 통합 Steve11870b8. 제품 직접 수정0. 원문·실제 claim ID·Drive식별자·모델 응답·키는 전달하지 않는다.

**TK55 기존 내부ID 과차단.** 신규 사용자 실행의 PHONE2는 metadata.claim_id와 user.claim_id에만 보고됐고 API전송 전 차단됐다. 프로그램은 Claim.create에서 CLM_+UUID hex12자로 ID를 만든다. 문서의 내부ID1개가 PHONE과 겹치고 같은ID가 MODEL_UNAVAILABLE로 미대조 목록에 있다. 실제 전체 요청은 export에 없어 완전 재구성하지 않았다. 아래 공개 합성 요청은 이전운영8280과현재b68에서 같은 결과다.

- 전화번호와 겹치는 합성 ID: CLM_a0212345678b, CLM_a03123456789, CLM_b05123456789 — 양쪽3/3 BLOCKED, PHONE2·동일두경로.
- 안전대조: CLM_abcdefabcdef, CLM_fedcbafedcba, CLM_abcdef123abc — 양쪽3/3 PASSED.
- 합성 claim_review_v1 요청의 claim_text/reference_sources는 일반 합성 설명이고 schema=ENVELOPE_SCHEMA, system=RAG_REVIEW_SYSTEM_PROMPT, metadata.stage=claim_rag_advisory다. 사용자 자료에서 예시를 가져오지 않았다.

원인 유형은 기존 내부 식별자 과차단으로 TK55 후속이다. 이번 #95/#97이나 ON 때문에 새로 생긴 회귀로 단정하지 않는다. 사용자명/사건정보/실제ID 목록·기준선 맞춤으로 고치지 않는다. 설계 메모를 먼저 제출하고 근원 인증이 된 내부식별자와 외부 임의문자열을 어떻게 구분하는지 설명한다. claim_id 키나 UUID모양만으로 일괄 면제하지 않는다. 기존 연락처/RRN 필수·성명/정상/스키마/metadata·capability·source·request binding 게이트와 원래 기대값은 유지한다. 필요한 보호시험 변경은 평가측에 요청한다. 구현은 한 세션 한 경로B, 별도 구현 세션에서 진행한다.

**JSON 응답 거절.** Claude의 INVALID_RESPONSE_SCHEMA(JSON이 아님)1건, 사용량은 입력6184/출력2448 토큰이다. raw 응답은 export에 없으므로 정확한 포맷 원인을 확정하지 않는다. 정상응답 스키마·근거 인용 검증을 완화하거나 무제한 retry로 숨기지 않는다. 공개 응답 대역으로 엄격거절·안전복구 계약을 설계한다. TK75 품질/응답 안정성 후속으로 관리한다.

**참고자료 미완료.** reference_sync 오류1·가용하지 않은 자료1·색인2185/미완료1371행이다. PARTIAL·미대조와 부존재를 구별하며 전체검증으로 표시하지 않는다. TK74 후속 및 사용자 자체평가에 기록한다.

선택된 온라인 명세2판23/23 통과와 위 실행 실패/미완료를 구분한다. 같은배포OFF 자료가 없고 참고발췌·모델응답이 바뀌어 법률지침 단일변수 통제시험이 아니다. 기존사용자ON 설정은 유지하고 정식채택은 독립법률채점자1명 검토/HOLD다. 가격절차/유료호출/새배포/봉인재시험0. 기존미완료TK44·45·49·55·73의 상태와 우선순위를 임의로 종료하지 않는다.
