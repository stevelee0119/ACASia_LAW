# RELEASE_PROCEDURE 4절: 서면9 운영 점검

실제 절차 문서는 `docs/scorecards/RELEASE_PROCEDURE.md` 4절에 있다(지시문에 적힌 `docs/RELEASE_PROCEDURE.md` 경로에는 파일이 없다). 공개 개발 자료 `tests/fixtures/case9_state_compensation_google_docs.pdf`와 규칙 2판 `tests/fixtures/probes/case9_state_compensation_online.json`을 사용했다. 원본 사건 문구·식별자·개인정보가 있는 결과 JSON은 이 PR에 넣지 않는다.

| 실행 | 표준 23항목 | case9 건강 | RAG 대조 5항목 | 파이프라인 건강 6항목 | 결과 상태 |
|---|---:|---:|---:|---:|---|
| 1 | 23/23 | 1/1 | 4/5 (`RAGC-S3`) | 5/6 (`H-REF`) | `PARTIAL_COMPLETED` |
| 2 | 23/23 | 1/1 | 4/5 (`RAGC-S3`) | 5/6 (`H-REF`) | `PARTIAL_COMPLETED` |
| 3 | 23/23 | 1/1 | 4/5 (`RAGC-S3`) | 5/6 (`H-REF`) | `PARTIAL_COMPLETED` |

다음은 **규칙 2판의 23개 개별 항목**이다. 세 실행 모두 각 항목을 충족했다. 근거는 세 원본 보고서의 `documents[].findings`, `ai_detector_result`, `masked_preview.kinds`, `engine_data.rag.observations`와 명세를 읽기 전용 `scripts/score_report.py --json`으로 대조한 결과다. 구체적 사건 발췌는 비공개 보고서에만 보존한다. `충족`은 이 공개 개발 자료에서의 관찰이며 일반적 정확도 판정은 아니다.

각 행의 API 결과 기반 참·거짓 값과 원본 보고서 SHA-256은 식별자를 제거한 [파생 JSON](api_derived_sanitized.json)에 실행별로 담았다. 화면에 원본 사건 문구가 보이는 캡처는 공개하지 않았다.

| ID | 확인 대상 | 1 | 2 | 3 | 근거 종류 |
|---|---|---|---|---|---|
| AI-1 | 문서 AI 판정 | 충족 | 충족 | 충족 | 문서 판정 값 |
| AI-2 | AI 쪽 모델 의견 2개 이상 | 충족 | 충족 | 충족 | 모델 의견 수 |
| AI-3 | 전형 문구 발췌 | 충족 | 충족 | 충족 | 탐지 발췌 존재 |
| AI-4 | 문서 단위 경고 | 충족 | 충족 | 충족 | finding 등급 |
| EX-1 | 인용 판결 존재 대조 | 충족 | 충족 | 충족 | 판례 finding |
| EX-2 | 존재하지 않는 조문 대조 | 충족 | 충족 | 충족 | 법령 finding |
| EX-2s | 같은 조문의 높은 심각도 | 충족 | 충족 | 충족 | finding 등급 |
| TMP-1 | 행위시법 대조 | 충족 | 충족 | 충족 | 시간·법령 finding |
| LEG-1 | 무리한 손해배상 주장 | 충족 | 충족 | 충족 | 법리 finding |
| LEG-2 | 무리한 시효 주장 | 충족 | 충족 | 충족 | 법리 finding |
| INJ-1 | 입력 서면의 위장 지시문 | 충족 | 충족 | 충족 | 지시문 finding 등급 |
| FA-1 | 은닉 신호 오탐 없음 | 충족 | 충족 | 충족 | 해당 finding 부재 |
| FP-1 | 참고 규정의 비존재 오탐 없음 | 충족 | 충족 | 충족 | 해당 finding 부재 |
| RAG-1 | 관련 참고 규정의 모순 의견 | 충족 | 충족 | 충족 | RAG 의견 |
| RAG-2 | 모순이 finding에 표시 | 충족 | 충족 | 충족 | finding 포함 |
| PII-K1 | PERSON | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K2 | DOB | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K3 | ADDRESS | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K4 | PHONE | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K5 | EMAIL | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K6 | ACCOUNT | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K7 | DRIVER_LICENSE | 충족 | 충족 | 충족 | 마스킹 종류 |
| PII-K8 | MILITARY_ID | 충족 | 충족 | 충족 | 마스킹 종류 |

## 2026-10-10의 21/23과 다른 조건

- 이번 운영 배포는 TK75 프로필이 `ON`(`korean_law_review_profile=true`, prompt `v0.2+kr2`)이었다. 요청된 2026-10-10 기준은 `OFF`다. 프로젝트 설정의 해당 프로필을 이 측정에서 끄지 않았으며 별도 `OFF` 쌍을 만들지 않았다.
- 현재 모델은 Claude `claude-opus-5-5`, Gemini `gemini-4-hydrogen`, OpenAI `gpt-6-luna`이며 2026-10-10의 실제 모델 구성과 동일하다는 근거가 없다.
- Drive는 현재 41개 파일로 조회됐고 세 실행 모두 일부 페이지 미완독으로 `PARTIAL`이었다. 과거와 같은 참고자료 스냅샷이라고 확인할 수 없다. 1회는 색인 35/41, 2·3회는 41/41이었다. 7개 자료에서 총 2,636쪽 중 2,599쪽을 읽었다는 문제 기록이 반복됐다.
- 네트워크 사용은 `true`, 보고서 코드 SHA는 세 번 모두 `32d9c485bc04ef0487fc4c6a32a91c9d39d29948`로 같았다.

따라서 **이번 23/23과 2026-10-10의 21/23 사이에는 점수 증감을 판정하지 않는다.** 표준 항목은 현재 조건에서 모두 관찰됐지만 실행 건강은 별개다.

## 신규 온라인 건강 대조

- `H-REF`: 세 번 모두 미충족. 1회에는 Drive 읽기 시간 초과·동기화 예산 소진·보류 파일이 함께 있었고, 2·3회에는 41/41개 색인에도 자료 7개가 부분 읽기로 남았다.
- `RAGC-S3`: 세 번 모두 미충족. 관련 지지 자료는 선별됐으나 그 자료에 대한 지지 관계 의견이 나오지 않았다. 관련 자료에 거짓 모순을 달거나 무관 자료를 선별하는 문제는 이 대조에서 보이지 않았다.
- 공식 법령 DB 조회는 case9에서 매회 21건, 재시도 실패 0건이었다. 모델 호출 실패도 관찰되지 않았다.
- AI 반복(U5): 세 번 모두 `AI_PARTIAL_GENERATION`, 유보 0건, 외형상 일치 3/3이었다. 다만 `scripts/ai_repeat_summary.py`가 참고자료 라이브러리 해시 차이를 `DIFFERENT`로 검출해 `comparable_agreement=null`을 냈다. **동일 조건 반복 성능으로 판정하지 않는다.**

이 원본 결과와 입력/명세 해시, 실행 시각은 저장소 외부 증거 묶음에 보존하고 해시는 실행 개요에 기록한다.
