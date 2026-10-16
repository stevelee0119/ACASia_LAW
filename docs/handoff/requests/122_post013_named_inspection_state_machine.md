# Named inspection: 미시도와 완료를 구분하는 상태 계약 (제품 전)

PR95/8a의 ActualText 인증은 UNKNOWN이지만, PAGE Properties도 inline ActualText hint도 없는 페이지는 availability 단계에서 해석을 생략한다. 따라서 `inspection_complete=true`의 기본값은 수집0을 known absence처럼 오표시한다. 두 coverage 보완에서 같은 metadata 결함이 반복되어, 값 종류별 guard를 더 붙이는 대신 **페이지 해석 lifecycle과 source 수집 결과를 독립 상태로 관리**하는 접근으로 바꾼다. 제품 diff0·원래95 기대값·source/visibility/cap 보호는 유지한다.

## 계약

capture 생성 시 `NOT_ATTEMPTED`이며 complete=false다. 페이지별 availability에서 interpreter를 실행하지 않으면 `UNAVAILABLE_UNINSPECTED`와 그 수를 기록한다. resource가 없다는 사실만으로 content의 named source 부재를 인증하지 않는다. `/Span /Selected BDC`가 있었어도 해석하지 않았으면 missing counter0은 “미관측”이지 “없음 확인”이 아니다. 이번 단계는 activation 범위를 확대하거나 raw comment/byte hint로 named 관계를 인증하지 않는다.

interpreter 진입/정상 종료를 페이지별 한 번 기록하고 selected named BDC 수와 실제 supported inspection 여부를 함께 남긴다. 관측된 선택 source를 모두 처리하고 실패/overflow/truncation/미해석 페이지가 없을 때만 `INSPECTED_SUPPORTED` + complete=true다. 정상 interpreter 종료 후 selected PAGE named source가 없었다면 `INSPECTED_NO_SELECTED_PAGE_NAMED_SOURCE` + complete=true를 **PAGE selected Properties 범위에서만** 쓴다. 실제 dictionary의 ActualText keyabsence도 그 범위의 관측된 부재다. unsupported/missing/invalid/unresolved source 또는 불완전 종료는 `INSPECTED_INCOMPLETE` + complete=false다. 진행 중 `IN_PROGRESS`도 완료로 표시하지 않는다.

문서 집계는 미해석 페이지를 다른 페이지의 성공으로 덮지 않는다. lifecycle attempted/completed/unavailable/page-named-request counters와 기존 unsupported·absence·resolution·budget 이유를 분리한다. `inspection_complete`는 파생 결과이며 default optimistic truth가 아니다. no-source와 supported를 상태로 구분하므로 수집0만으로 전체 문서에 명령이 없다고 인증하지 않는다. Form-only source·unsupported stream의 검사 잔여를 계속 명시한다. 원문 보안 검사/strict source 인증은 별개이며 successful indirect inspection의 인증 UNKNOWN을 coverage 실패로 잘못 처리하지 않는다.

## 공개 대조·범위

실제 PDF noProperties+selected BDC, emptyProperties+selected BDC, noProperties+unused-noNamedSource, emptyProperties+unused-noNamedSource, 일반 supported 및 unavailable+supported 멀티페이지6건을 비교했다. 원래8a의 공개 capture 코드로 원래 PDF를 실행한 complete boolean 대조는 **3 FAIL/3 PASS**였다: noProperties selected/unused 및 mixed의 해석 생략이 true였고, 나머지3의 기존 완료/불완전 판정은 맞았다. 빈 Python dict를 생략하는 ReportLab 동작을 피하여 실제 `/Properties << >>`를 생성·검증했다. Lifecycle prototype actual6은 미해석을 false, empty selected를 incomplete, empty unused를 관측부재, supported를 완료로 분리한다. 초기/진행/실패 종료 unit2도 별도로 대조했다. 최종 관련 **103 PASS/2.35s**이며 기존95/JSON/reading/source/security 기대값은 변경하지 않았다. 기존 한 번의 page interpretation에 lifecycle 기록만 붙이며 별도 content 탐색·resource enumeration·새 decode·threshold/CI/full검증/제품 변화0다. 독립 좁은 대조 후 root의 제한 제품 승인 여부를 기다린다.
