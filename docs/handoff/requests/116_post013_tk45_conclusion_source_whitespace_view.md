# TK45 직접부정 결론의 공백 view·원문 mapping 성능 설계

현재 제품b582e77은 source/norm 보완 후152 PASS이나 추가 성능 반례로 HOLD다. 직접부정 뒤 configured limited_conclusions의 연속 optional \s*에 malformed `채무에`+N 공백+불일치 명제를 적용하면 helper64/128/256/512자 .00021/.00045/.00168/.00575s로 초선형이다. 고정 R이면 전체 regex 내부 방문까지 O(R*N)이라는 docstring 주장은 철회한다. 기존selector·설정·기대값·timing 상한은 변경하지 않는다.

제품 변경 전 공개 spike59 PASS/0.45s: 현재 configured 결론5개 각각의 정상/불일치×공백없음/단일/다중/tab/NBSP·전각공백에서 원문 regex와 compact view의 입력 언어 일치 및 원문 match span 복원, 그리고 sensitive future pattern9개의 거절을 확인했다. 현재5개는 비공백 literal·그룹·선택·optional 및 \s*만 사용한다. literal whitespace, \s+/고정공백수량, lookaround, wildcard/characterclass/anchor, backreference·기타escape, lazy/possessive 공백수량은 인증하지 않는다. 그런 미래 설정이 들어오면 새 증명은 abstain하고 기존 규칙은 그대로 실행한다. 정의되지 않은 설정의 언어 동일성을 추정하지 않는다.

직접부정 경로에 들어간 경우에만 citation 뒤 local assertion 영역의 공백 run을 하나의 space로 표현하는 view를 한 번 lazy 생성한다. 비공백 codepoint는 변경/삭제하지 않고, 각 view codepoint는 원문 start/end를 가진다. 새로 만든 한 space는 원래 whitespace run 전체 span을 갖는다. newline이 있는 unit은 기존대로 새 proof 없음이며 원문 텍스트를 교체하거나 문서 전체 normalization을 추가하지 않는다. 같은 configured 결론 regex와 terminal을 view에 적용하고 match의 첫/끝 codepoint source span으로 원문 결론 좌표를 복원한다. 원래 argument/case/finite/predicate/부정/시제/span과 기존finding은 불변이다. 완료·이행·fact/legal certification이나 UNKNOWN 면제가 아니다.

region 시작은 citation end로 한 번 고정하고, 관측 denial.end는 source starts 이진조회로 view offset에 대응한다. 이진조회 O(log M) 비용을 별도 accounting하며 후보별 긴 suffix copy·후보별 view 재생성·문장별 whole-prefix 검색은 없다. 추가 view scan chars/빌드수/이진조회수/compact chars를 실제 수행 범위로 기록한다. current supported regex 언어의 공백에 의한 반복 backtracking을 줄이지만 전체pipeline 선형/≤2N을 주장하지 않는다.

승인 후 기존152+spike59 기대값 유지, 원래 32k malformed 중간공백 UNKNOWN/정상 장공백 source span 및 actual TXT 대조, literal/정량공백/lookaround가 있는 future configuration은 새 proof 없음의 양방향 제어를 추가한다. 제품·관련시험·성장 재측정/독립 좁은 감사·exactCI·3줄 요청 후 원래 정상8/8 및 부정/확장 각각 시작 대비 증가 조건으로 평가한다. 제품이 통과하지 못한 현재 HOLD와 이전CI 기록을 보존한다.
