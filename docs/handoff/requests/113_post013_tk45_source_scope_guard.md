# TK45 추가 원문 증명: 화자·민사규범 범위 보완

제품 `0dd4b88ccf8fdf55e12aaf99c1f7542d6b183492`의 관련126은 PASS이지만 독립 actual TXT 감사에서 문장간 인용/상대방 도입/보고/재반박 네 범주와 헌법 참조 두 범주가 잘못 IMPLICIT_WRITER/civil_norm으로 인증되었다. 기존 baseline finding은 0이며 새로운 증명만 1이었다. 원문 span 정확성은 화자·법률 역할의 정확성을 대신하지 않는다. 공개9 제어 사전검사는 기존 결과 보존을 요구하며 제품 보완 전에 FAIL을 고정한다.

평가자의 승인된 source-bound 화자/UNKNOWN 보호 강화로, 새 증명을 BODY 첫 비어있지 않은 문장에만 허용한다. 앞 문장이 하나라도 있으면 그 의미나 인용 종료를 새 어휘 목록으로 추정하지 않고 새 화자 증명은 UNKNOWN으로 남긴다. 뒤 문장이 독립 작성자의 실제 주장이더라도 이번 증분은 인증하지 않는다. 원래 규칙의 판정은 계속 적용하며 기존 finding/상태/등급/원문을 삭제하거나 변경하지 않는다. 문장별 prefix 재검색 없이 이미 순회하는 sentence bounds와 상수 boolean만 이용한다.

새 civil_norm은 실제 `민법`과 기존 configured 조문번호의 결합으로 한정한다. 다른 법의 같은 번호 및 실제 헌법 조문을 민사 규범으로 기록하지 않는다. 이는 조문의 현재 유효성/내용이나 법적 충분성 인증이 아니다. 효과의 앞 요건 causal 술어는 관측 연결만 기록하며 premise_assertion_verified/이행/완료/사실/법적 충분성은 false를 유지한다.

terminal 문법의 중복 인접 whitespace 수량자를 내용이 있는 선택 어미/부호 그룹으로 묶고, 조건 어미 검색은 한글 token 시작에만 진입하여 같은 token의 모든 suffix를 반복 검색하지 않는다. 입력 범위/극성/어미 기대값은 동일하며 32k malformed trailing whitespace/긴 한글 token 및 정상·반대 대조로 검증한다. 추가 grammar 비용은 고정 configuration 수 R에 의존하며 regex 내부 방문량과 전체 pipeline 선형성을 계측했다고 주장하지 않는다.

기존25 historical baseline/자동 enabled 6/기존3 경고/반대대조·관련 보호시험은 기대값 불변. 공개9 speaker/norm 제어와 실제 TXT/PDF/DOCX/폭595·720 대조, 32k helper 및 pipeline 성장 비용을 제출한다. 원래 정상8/8·부정과 확장 각각 시작 대비 증가 기준은 그대로이며 첫 문장 제한으로 목표를 못 달성하면 미달로 보고한다. TK44/49 비태그 UNKNOWN primary/floor/consumer 전체잔여는 별도 후속 설계다.
