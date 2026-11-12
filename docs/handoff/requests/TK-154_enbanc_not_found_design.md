# TK-154 미발견 대법원 전원합의체 판결 '부존재 의심'(HIGH) 설계 메모

- **작성일**: 2026-11-12
- **작성자**: Antigravity (구현 에이전트)
- **대상 티켓**: TK-154(P1) 미발견 대법원 전원합의체 판결 '부존재 의심'(HIGH)
- **대상 모듈**: `packages/legal_engine/authority_status.py`, `packages/legal_engine/verifier.py`
- **시험 모듈**: `tests/test_tk154_enbanc_not_found.py`

---

## 1. 배경 및 문제 정의

0.18.0 온라인 case9 EX-1에서 서면이 인용한 실재하지 않는 대법원 전원합의체 판결이 `MEDIUM`(조회 범위 내에서 찾지 못한 판례)으로만 판정되어 이전 버전 대비 탐지 강도가 후퇴하는 문제가 발생하였다 (0.17.0 `CRITICAL` → 0.18.0 `MEDIUM`, 명세 기대 `HIGH` 이상).

### 원인 분석 및 법적 근거
1. **C1 (일률적 `MEDIUM` 처리)**: `verifier.py` 354~361행은 사건번호 형식이 유효한 미발견 판례에 대해 법원급이나 판결 성격과 무관하게 `severity = MEDIUM`, tags `["SOURCE_LIMIT"]`로 분류하며, `authority_status.py`의 `is_covered_precedent_scope`는 전수 수록 미증명으로 항상 `False`를 반환한다 (LV-03, X6 결정).
2. **C2 (전원합의체 판결의 공개성 및 공보 게재 대상)**: 법원도서관 조사심의관 지침('판례공보와 종합법률정보', 2017. 8. 4.)에 따르면 대법원 전원합의체 판결은 중요도 'A급'으로 판례공보 게재 및 종합법률정보 전수 등록 대상이다.
   - 따라서 선고 후 충분한 지연 기간이 경과하였음에도 공식 판례 DB에서 검색되지 않는 전원합의체 판결은 단순 수록 범위 제한을 넘어 판례 부존재(또는 중대한 오기)를 강력히 의심할 수 있다.
   - 단, 연계 조회 중인 국가법령정보 DB의 전수 수록 공식 증명이 없으므로 `CRITICAL`(확정 부존재) 대신 `HIGH`(부존재 의심)로 판정한다.

---

## 2. 설계 및 구현 계획

### F1. `authority_status.py`: 공보 지연 상수 및 의심 판정 함수
- `ENBANC_PUBLICATION_LAG_DAYS = 180`: 판례공보 게재(월 2회), 종합법률정보 등록, 국가법령정보 연계 지연을 여유 있게 포괄하는 기준 기간.
- `enbanc_absence_suspected(citation, current_date)`: 다음 세 조건이 모두 충족될 때만 `True`:
  1. `get_court_tier(citation) == "SUPREME"` (대법원)
  2. `case_kind` 또는 `raw_text`에 정규식 `r"전원\s*합의체"` 포함 (서면이 스스로 밝힌 전원합의체 표기)
  3. `decision_date`와 `current_date`가 유효한 날짜이고, `선고일 <= 기준일 - 180일`

### F2. `verifier.py`: 전원합의체 미발견 판례의 '부존재 의심' 분류
- `verify_case(self, citation, current_date=None)` 및 `verify_citations()`에서 `current_date` 인자 지원 (기본값: `today_korea()`).
- 미발견·형식 유효 판례 분기에서 `elif enbanc_absence_suspected(citation, current_date or today_korea()):` 분기 추가:
  - `status`: `VerificationStatus.NOT_FOUND`
  - `severity`: `Severity.HIGH`
  - `tags`: `["LEGAL", "CASE", "ENBANC_NOT_FOUND"]` (`SOURCE_LIMIT`, `FAKE_PRECEDENT` 태그 제외)
  - `title`: `공개 대상인 대법원 전원합의체 판결을 조회 범위에서 찾지 못함(부존재 의심): …`
  - `detail`: 공보 게재 대상, 180일 경과, 오기 또는 실재하지 않을 가능성이 높음, 전수 수록 미증명으로 확정하지 않음 안내.
  - `authority_status`: `SUSPICIOUS` ('존재의심'), features에 `suspicion_basis="ENBANC_PUBLICATION_EXPECTED"`, `publication_lag_days=180` 등록.

### F3. 비대상 판례의 기존 동작 유지
- 어댑터 조회 실패(`READY` 아님) 시 모든 결과 `UNVERIFIED` 유지.
- 헌재 사건번호, 하급심, 전원합의체 표기 부재, 선고일 누락, 선고 후 180일 이내의 미발견 판결은 기존대로 `Severity.MEDIUM`, `SOURCE_LIMIT` 유지.

---

## 3. 검증 및 수용 기준

1. **확인 시험 (`tests/test_tk154_enbanc_not_found.py`)**:
   - 180일 경과 대법원 전원합의체 미발견 시 `HIGH`·`NOT_FOUND`·`ENBANC_NOT_FOUND` 및 `SUSPICIOUS` 단언 (합성 사건번호/일자).
   - 대조군(표기 없음, 180일 이내, 선고일 없음, 하급심)은 `MEDIUM`·`SOURCE_LIMIT` 유지 단언.
   - 어댑터 에러(`ERROR`) 시 `UNVERIFIED` 유지 단언.
   - 180일 경계치(당일 참, 1일 전 거짓) 단언.
2. **보호 경로 및 하드코딩 준수**:
   - `check_protected_paths.py`, `check_case_literals.py`, `check_hardcoding_diff.py` 100% 통과.
3. **회귀 방지**:
   - 기존 권위도 판정 및 판례 검증 시험 단언 변경 0건.
   - 필수 CI(점수 하락 게이트, 은퇴 세트, 테스트, Docker OCR readiness) 전체 통과.
