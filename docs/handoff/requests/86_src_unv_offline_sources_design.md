# 설계 메모: SRC-UNV 오프라인 외부 출처(문헌·통계·보고서) 미검증(UNVERIFIED) 식별 규칙

- **작성일:** 2026-10-17
- **작성자:** Antigravity (구현 에이전트)
- **문서 번호:** 86
- **대상 티켓:** TK-76 4절 과업 (SRC-UNV)
- **참조 지침:** 전달문 v5 4절, `docs/handoff/TK-76_focus_types_generalization_cycle1.md`, AGENTS.md

---

## 1. 배경 및 문제 진단

- **현상:** 오프라인 환경(`LV_ALLOW_NETWORK=0`)에서 외부 문헌·통계·보고서 인용에 대한 확인 불가(`UNVERIFIED`) 판정이 방출되지 않아 train 0/40, 은퇴 봉인 4세트 0/11 재현율을 기록함.
- **원인 분석:**
  1. `packages/legal_engine/citation_extractor.py`의 `ACADEMIC_RE`가 저자명(`_author_start`) 필수 구조로 되어 있어, 저자 없이 `「... 연보」`, `「... 백서」`, `「... 조사」`, `「... 보고서」` 형태로 인용되는 비학술 간행물 및 통계 자료를 추출하지 못함.
  2. `packages/legal_engine/verifier.py`의 `_unverified_finding`이 `CitationType.ACADEMIC`에 대해 `LAW_CITATION_ERROR`를 방출하거나 원문 문맥(수치·비율·쪽수)을 충분히 담지 못함.

---

## 2. 기본 원칙 및 금지사항 준수

1. **`.invalid` 규칙 금지:** `.invalid` TLD나 특정 도메인을 결함 근거로 삼는 정규식을 일절 사용하지 않는다.
2. **결함 단정 금지:** 오프라인 환경에서 외부 출처는 존재 여부를 확정할 수 없으므로 `CONTRADICTED`나 `NOT_FOUND` 등 결함으로 단정하지 않고, 오직 `UNVERIFIED` (등급 `U`, `advisory_only=True`, `Severity.INFO`)로만 처리한다.
3. **하드코딩 배제:** 특정 사건의 문헌명, 수치, 당사자명을 정규식에 일절 넣지 않고, 일반적인 간행물·통계 지시어 패턴으로 일반화한다.
4. **오탐 방지:** 방출되는 finding이 결함 판정이 아닌 `UNVERIFIED` (INFO 등급)이므로 대조군 문서(PASS) 및 FP-TRAP에서 오탐이 0건으로 유지된다.

---

## 3. 세부 설계

### A. 간행물·보고서·통계 인용 추출 (`citation_extractor.py`)
- **패턴 인식:**
  - 따옴표 표기(`「...」`, `『...』` 등) 내부 또는 직후에 일반적 서지·통계 지시어(`연보|백서|보고서|연감|실태조사|조사|지수|공통표|원표|통계|연행|편람|총람|요람|통람`)가 포함된 인용.
  - 인용 부호 직후 쪽수(`\d+쪽|\d+면`) 또는 통계 수치(`\d+(?:\.\d+)?%|\d+명|\d+(?:\.\d+)?일`)가 뒤따르는 패턴.
  - 따옴표 없는 경우에도 명백한 통계 지표 결합(`(?:\b[가-힣]{2,12}(?:지수|연감|조사|공통표)\s*\d+)`) 인식.
- **인용 생성:** `CitationType.ACADEMIC`으로 등록하고, 문맥(`context`)에 해당 문장(앞뒤 120자)을 보존한다.

### B. 오프라인 미검증 판정 방출 (`verifier.py`)
- 학술 Source 어댑터 미설정/오프라인 시 `verify_academic`에서:
  - `FindingType.ACADEMIC_CITATION_ERROR`, `status=VerificationStatus.UNVERIFIED`, `severity=Severity.INFO`, `evidence_grade=EvidenceGrade.U` 생성.
  - `evidence`에 인용된 원문 발췌(`excerpt=citation.context or citation.raw_text`)를 포함하여 세부 수치·비율 토큰이 채점기에 전달되도록 함.
  - 문서당 새 UNVERIFIED 건수를 기록하여 보고함.

---

## 4. 검증 계획

1. **실제 진입점 시험:** `pipeline.verify_document` 및 `LegalVerifier.verify_citations` 실행 검증.
2. **양성 예시 3건 & 대조군 3건:**
   - 양성: 백서 통계 인용(`「... 백서」 ... %`), 연보 쪽수 인용(`「... 연보」 ... 쪽`), 비공개 조사 수치 인용(`「... 조사」 ... 명`).
   - 대조군: 일반 사실 진술 문장, 법률 조항 인용(`민법 제750조`), 단순 일상적 비율 표현(`약 50%의 확률`).
3. **정규식 성능비 검증:** 1배/4배 길이 입력 3회 측정, 최솟값 비 < 8, 4배 최솟값 < 1초 충족.
4. **성적표 게이트:** dev 81.7 / holdout 79.2 / 은퇴 봉인 4세트 점수 유지 및 오탐 0건 확인.
