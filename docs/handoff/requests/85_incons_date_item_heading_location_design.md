# 설계 메모: INCONS 한글병기 · DATE 하이픈날짜 항목명 위치 보강 설계

- **문서 번호:** `requests/85_incons_date_item_heading_location_design.md`
- **작성일:** 2026-10-17
- **작성자:** Antigravity (구현 에이전트)
- **대상 티켓:** TK-76 (개발 말뭉치 중점 6유형 1주기)
- **목표:** EVI-INCONS(한글병기 8건), EVI-DATE(하이픈날짜 8건)의 match_spec 토큰 불일치 (d) 해소

---

## 1. 배경 및 평가 측 모의 결과
- **현상 (d):** 기존 `AMOUNT.WORDS_MISMATCH`(A등급) 및 날짜 검증 규칙이 결함(한글-숫자 불일치, 날짜 불일치) 자체는 100% 정상 탐지하고 있으나, 채점기 match_spec이 요구하는 `[항목명]` 토큰이 Finding의 발췌/표시에 누락되어 점수 인정에서 제외됨.
- **줄 전체 확장의 위험성 (평가 측 실측):**
  - 발췌를 줄 전체로 확장할 경우 INCONS +4건, DATE +4건의 점수 상승이 있으나, **FP-TRAP 오탐이 0건에서 4건으로 증가**하여 게이트 통과가 불가능해짐.
- **해법:** 줄 전체를 확장하지 않고, 오직 결함이 위치한 행의 선행 항목 머리(`[항목명]`)만 정밀하게 추출하여 `[{item_heading}] ` 형태로 접두(prefix) 부가.

---

## 2. 항목 머리 추출 헬퍼 설계 (`_extract_item_heading`)

### (1) 항목 머리 정규식
- 법률/증빙 서면의 표 및 목록에서 흔히 쓰이는 항목 식별자 패턴:
```python
ITEM_HEADING_RE = re.compile(
    r"\[(?P<name>[^\]\n]{2,30})\]|"             # [검수대장 1차]
    r"【(?P<name>[^】\n]{2,30})】|"             # 【1차 납품】
    r"<\s*(?P<name>[^>\n]{2,30})\s*>|"          # <물품 목록>
    r"(?:^|\s)(?P<num>[0-9]{1,3}|[가-하])\s*[\.\)]\s*(?P<title>[^\n]{2,30})" # 1. 검수내역
)
```

### (2) 적용 위치 및 범위
1. **EVI-INCONS (`korean_amount.py`):**
   - `words_digits_mismatches`에서 금액 불일치 발생 시, 같은 블록/라인의 선행 텍스트에서 `_extract_item_heading`을 호출하여 `[{heading}] ` 접두.
2. **EVI-DATE (`evidence_consistency.py` 및 `date_verifier.py`):**
   - 하이픈 날짜 검증 시 선행 항목명이 식별되면 `[{heading}] ` 접두.
   - 단, 문맥 문장(`context_sentence`)은 일절 부가하지 않아 calendar_dates와의 간섭을 원천 차단.

---

## 3. 보고 및 점수 분리 방침
- 공통 제출 점검표 3항 및 5항 작성 시:
  - **'탐지 개선분'**과 **'표시 보강분(위치 보강)'**을 분리하여 명시.
  - dev 81.7 / holdout 79.2 / 은퇴 4세트 점수 유지 및 FP-TRAP 오탐 0건 유지 필수 검증.
