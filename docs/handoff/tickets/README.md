# 차기 릴리스(0.27.0 목표) 구현 에이전트 지시 및 목표 총괄

- **기준 배포:** `v.0.26.0` (`19efff6a4acb11a22b9e8311dc04680a984aa76b`)
  - 현재 오프라인 기준선: **`dev 84.8`** (v2 `43/56`), **`holdout 83.8`** (v2 `42/54`), 은퇴 5세트 **`53.3 / 50.0 / 56.9 / 45.8 / 34.1`**, 확인 오탐 `0` · A등급 오탐 `0`.
  - 현재 온라인 기준선: `case9` **3회 연속 23/23 · RAG 5/5 · 건강 6/6 · 중단 0/3**, U5 AI 반복 **3/3 일치**, `Legal NLI Stage 2` 반전 `CONTRADICTED` 해소, 저품질 스캔 `RapidOCR` 채택(`9자 → 25자`).
- **근거 문서:**
  - [0.26.0 온라인 평가 판정서](../../scorecards/online_0260_20261122.md) · [후속 관찰](../online/0260_20261122/issues.md)
  - [거버넌스 및 역할 분리](../../AGENT_ROLES.md)

---

## 1. 0.27.0 2단계 핵심 추진 전략 (사용자 결정 2026-11-22)

> **"불필요한(미운영) 코드는 삭제하고, 핵심 기능은 추가 인프라 없이 실전화하며, 하드코딩 없이 온라인·오프라인 점수가 모두 상승하도록 2단계로 추진한다."**

### 1단계 (트랙 1) — 불필요 코드 삭제 & 핵심 기능 실전화 (`TK-232`, `TK-231`)
1. **[TK-232](TK-232.md) (`P1`) — 미운영 코드(로컬 LLM·별도 Reranker 서버) 삭제, 진단 정합화 및 상용 API 임베딩 연결:**
   - Render 운영 환경에 존재하지 않는 로컬 LLM(`local_ollama` 등) 및 별도 HTTP Reranker 서버 어댑터 코드를 과감히 삭제/단일화한다.
   - `LV_RAG_RETRIEVAL_MODE=lexical_only` 설정 시 `/api/diagnostics`에 `configured_mode=HYBRID`로 잘못 표시되던 불일치를 수정한다.
   - 별도 임베딩 서버 구축 없이 기존 `OPENAI_API_KEY` / `GEMINI_API_KEY`를 재사용해 상용 임베딩 API로 청크 리비전 캐시 임베딩을 생성·재사용할 수 있도록 연결하고, `lexical_only` 또는 실패 시 즉시 `LEXICAL_ONLY`로 폴백한다.
2. **[TK-231](TK-231.md) (`P1`) — 한국어 RapidOCR 이미지 전처리 및 Drive 저품질(`OCR_LOW_QUALITY`) 16쪽 선택 재색인 완결:**
   - 저품질 스캔 페이지에 그레이스케일·대비/이진화·샤프닝 전처리 후 RapidOCR를 실행해 `low_quality_scanned.pdf`의 복구 품질을 `OCR_EXTRACTED` 수준으로 끌어올린다(정상 스캔 `0.89`는 불필요 재처리 `0`).
   - Drive 참고자료 `41/41` 전체 재다운로드 없이 캐시 내 `OCR_LOW_QUALITY` `16쪽`만 선택적으로 재OCR·재색인하고 전후 델타를 기록한다.

### 2단계 (트랙 2) — 하드코딩 0 오프라인·온라인 점수 동반 상승 (`TK-233`, `TK-234`)
1. **[TK-233](TK-233.md) (`P1`) — 한국 법제 형식 불변식(`CIT-META`·`LAW-NX`·`EVI-FAKECIT`) 및 `ClauseNormalizer` 법리 양태(`LAW-MIS`·`OVR`) 일반화 탐지:**
   - 법원급↔사건부호 정합성, 사건번호 연도↔선고일 연도 역전, 기본 법전 총 조문 수 상한 초과(`LAW-NX`), `ClauseNormalizer` 기반 "[복합·예외 법리 + 절대적 단정 양태(`ALWAYS`/`MUST`)]" 구문 대조를 일반화 구현한다.
2. **[TK-234](TK-234.md) (`P1`) — 문서 구조 일반화(`EVI-COPY`·`EVI-LOGIC`·`EVI-INCONS`·`EVI-OVR`), 인젝션 스팬 매핑(`INJ-*`) 및 `AIGEN` 클러스터 배출 정밀화:**
   - 내용어 n-gram(shingle) 유사도 및 종결 어미 변환 기반 복제 탐지(`EVI-COPY`), 전제-결론 인지 양립 불가(`EVI-LOGIC`), 개체 튜플 충돌(`EVI-INCONS`/`OVR`), 파서 인젝션 신호(`INJ-ZWSP`/`META`/`OFFPAGE`)의 finding 스팬 정규화, `AIGEN` 상위 기여 문단 클러스터 배출을 완결한다.

---

## 2. 발행된 계약 티켓 및 실행 순서

| 순서 | 티켓 | 트랙 / 우선순위 | 핵심 목표 | 정량 합격 기준 / 선행 조건 |
|---:|---|---|---|---|
| 1 | [TK-232](TK-232.md) | 트랙 1 · `P1` | **로컬 LLM·원격 Reranker 삭제, 진단 정합화, 상용 API 임베딩 연결** | `lexical_only` 진단 일치, CodeQL 0, 회귀 0 |
| 2 | [TK-231](TK-231.md) | 트랙 1 · `P1` | **RapidOCR 이미지 전처리 및 Drive 저품질 16쪽 선택 재색인** | 정상 스캔 재처리 0, 저품질 복구 향상, 전후 델타 기록 |
| 3 | [TK-233](TK-233.md) | 트랙 2 · `P1` | **법제 형식 불변식(`CIT-META`·`LAW-NX`) & `ClauseNormalizer` 법리 양태(`LAW-MIS`·`OVR`)** | `docs/handoff/requests/` 설계 메모 선행 필수, 오탐 0 |
| 4 | [TK-234](TK-234.md) | 트랙 2 · `P1` | **문서 구조(`EVI-*`)·인젝션 스팬(`INJ-*`)·`AIGEN` 클러스터 일반화** | 설계 메모 선행 필수, `TK-233`+`234` 합산 **`dev > 84.8` · `holdout > 83.8` · 은퇴 2세트+ 상승** |

---

## 3. 구현 에이전트 작업 규칙 (필수 엄수)

1. **회귀 0 및 하드코딩 0 (절대 원칙):**
   - 기존 기능, 고정 세트(`dev 84.8` / `holdout 83.8`), 은퇴 5세트(`53.3/50.0/56.9/45.8/34.1`), 확인 오탐 `0` · A등급 오탐 `0`에서 **단 1건의 회귀도 허용하지 않는다**(`scripts/score_gate.py`, `scripts/regression_gate.py`, `scripts/retired_compare.py`).
   - 사건 고유 값(당사자명·사건번호·금액·수치), 서면 문구(한글 10자 이상), 영문 대문자 식별자(12자 이상), 특정 문구 맞춤 정규식을 **절대 코드에 넣지 않는다**(`scripts/check_case_literals.py`, `scripts/check_hardcoding_diff.py`, `scripts/check_train_phrase_overlap.py --eval-sets`).
   - 모든 새 규칙은 서로 다른 일반화 양성 3건 이상과 대조군(적법 주장·정상 인용·사람 작성 서면 등) 3건 이상의 단위 시험을 함께 제출한다.
2. **티켓 범위 완결성 (부분 구현·잔여 이월 금지):**
   - 각 티켓에 명시된 삭제·실전화·탐지 일반화 요구사항 전체를 해당 PR 안에서 100% 완결한다. 일부만 구현하고 후속 과제로 미루지 않는다.
   - `TK-232`에서 죽은 코드를 삭제할 때 `docs/scorecards/approved_test_marks.json`이 감시하는 기존 보호 수용 시험은 삭제/약화하지 않는다(`scripts/check_test_edits.py` 통과 필수).
3. **자율 상호작용 및 제출 절차 (`/aegis-autonomous-releasing` 연동):**
   - 1티켓 = 1PR 단위로 `Steve_ACASiaLAW` 대상 PR을 생성한다.
   - 각 티켓의 4절(구현 설계 요약)을 채우고, 커밋 메시지에 `Agent: implementer`, PR 코멘트 3줄(`바꾼 것` · `남은 것` · `검토 요청`)을 남긴다.
   - 보호 경로(`docs/scorecards/**`, `tests/acceptance/**`, `tests/fixtures/**` 등)는 수정하지 않는다.
