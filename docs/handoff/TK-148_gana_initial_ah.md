# TK-148 두 글자 약칭 추정의 ㅇ 초성 사전식 값 오류 (P2, TK-143 후속, 평가 측 수정본)

- 발견: 2026-11-03 평가 측 공식 API 실제 응답 확인(법제처 OC, http, 값은 기록하지 않음).
- 원인(`cf57cb7`, `packages/legal_engine/law_name_inference.py` 23행 `_GANA`): ㅇ을 `a`로 보낸다. 법제처 `lawSearch.do`(target=law)는 ㅇ을 `ah`로 받는다. 알 수 없는 값은 오류 없이 **필터 없는 전체 목록(5,631건)**을 돌려준다 → 20쪽 상한에 걸려 언제나 INCOMPLETE.
  - 초성별 건수(11-03): ga 1,433·na 220·da 297·ra 0·ma 174·ba 368·sa 712·**ah 578**(a는 5,631)·ja 836·cha 164·ka 11·ta 99·pa 48·ha 639. 나머지 값은 모두 2,000건 상한 안이다.
  - 영향: ㅇ으로 시작하는 두 글자 어간 약칭(예: 여객법·응급법)은 후보를 찾지 못한다. 안전 장치(ABBREVIATION_UNRESOLVED, MEDIUM)로 CRITICAL은 나지 않는다.
- 수정본 `patches/TK-148_gana_ah_on_cf57cb7.diff`(2개 파일 +4/−2): `_GANA`의 ㅇ 값 `a` → `ah`(주석에 근거).
  - **기존 시험 단언 1건 변경 — 사용자 승인 필요**: `tests/test_tk143_short_abbreviation.py::test_gana_code_follows_initial_consonant`가 잘못된 값 `"오" → "a"`를 단언한다(TK-143 평가 측 수정본의 시험). 이름은 두고 기대값만 `"ah"`로 바꾼다.
- 사전 검증(평가 측 재실행): TK-143·약칭 추정 관련 시험과 보호 수용 시험 `test_reference_match_guard` 136건 통과 · 평가 세트 문구·하드코딩 통과 · 실제 응답(평가 측 스크립트에서만 http로 바꿔 실행, 제품 코드 무변경): 기존 코드 여객법·영유법·응급법 모두 INCOMPLETE → 수정본 여객법 FOUND(여객자동차 운수사업법)·영유법 AMBIGUOUS(영유아보육법·영유아특별회계법)·응급법 FOUND(응급의료에 관한 법률). 'ㄴ' 대조(노조법 FOUND)는 변화 없음.
- 미검증: 운영(https) 경로의 같은 응답(이 환경은 https가 프록시에서 끊김). 배포 뒤 온라인 재측정.
- 수용: 사용자 승인 뒤, diff = 수정본, 필수 CI 성공.
