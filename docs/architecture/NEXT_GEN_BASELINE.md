# AegisLAW (ACASia_LAW) 차세대 고도화 1단계 — 현행 코드 및 평가 감사 보고서 (Step A)

- **작성일**: 2026-11-19
- **기준 브랜치 / 커밋**: `Steve_ACASiaLAW` @ `a7b13a370810d853811e4ffa8b171b8b77bb8feb` (코드 버전 `0.22.0`, `v0.23.0` 온라인 라운드 2·3 후보)
- **작성 주체**: Antigravity (`Agent: implementer`)
- **목적**: 차세대 아키텍처(`Legal Evidence Graph + Hybrid Retrieval + Structured Legal Reasoning`) 도입에 앞서, 평가 성적표(`docs/scorecards/`)와 실제 제품 코드(`packages/`, `apps/`, `migrations/`)를 교차 대조하여 **확인된 사실(Verified Facts)** 과 **검증이 필요한 가설(Hypotheses)** 을 엄격히 분리한다.

---

## 1. 감사 요약: 확인된 사실 vs 가설 분리

| 감사 항목 | 구분 | 핵심 결론 (근거 파일 및 라인) |
| --- | --- | --- |
| **1. 오프라인 법률 재현율 35.0% (43/123) 정체 원인** | **확인된 사실** | `scripts/scorecard.py:137`(`LV_ALLOW_NETWORK=0`) 및 `scripts/evaluation_v2.py:13,123` 확인 결과, 오프라인 채점은 공식 법령·판례 DB 및 LLM을 모두 차단한 상태에서 비참고(`not advisory_only`) 확정 상태(`NOT_FOUND`, `CONTRADICTED`, `SUSPICIOUS`, `INVALID_FORMAT`, `INVALID`, `MODIFIED`)만 정답으로 인정한다. 그 결과 123개 법률 결함 중 원문 대조가 필수인 `CIT-FAB-Q`(0/9), `CIT-MIS`(0/7), `LAW-NX`(0/15), `LAW-MIS`(4/22)에서 `UNVERIFIED` 또는 참고 신호로 빠져 구조적 상한(ceiling)에 도달해 있다(`docs/scorecards/benchmark_audit_2026-11-13.md:64-76`). |
| **1-보완. 오프라인 정체 중 순수 알고리즘 한계 비중** | **검증 필요 가설** | 80건의 오프라인 미탐(`123 - 43`) 중 몇 건이 `외부 원문 없이는 판정 불가능한 항목`이고 몇 건이 `로컬 규칙표(config/legal_rules/rules.json) 또는 로컬 스냅샷만으로 판정 가능했으나 놓친 항목`인지는 항목별 3분류 재집계(P0-1)를 통해 확정해야 한다. |
| **2. 미판정 경고 102건 발생 경로** | **확인된 사실** | `scripts/evaluation_v2.py:138`의 `unadjudicated_alerts`는 `scripts/eval_testset.py`의 `unmatched_defect_findings` 개수다. 51개 벤치마크 문서(dev 36 + holdout 15) 기준 102건(문서당 평균 2.00건)이며, 이 중 **동일 문서·동일 유형 중복이 24건**, **증거등급 A등급 경고가 72건**이다(`docs/scorecards/DAILY_TREND.md:135`, `docs/scorecards/benchmark_audit_2026-11-13.md:19,121`). |
| **2-보완. 102건 중 실질 오탐(FP) vs 타당 미등재 탐지 비율** | **검증 필요 가설** | 현재 `known_false_positive_findings`(0건)는 `FP-TRAP`과 대조군 문서만 계산한다. 102건이 실제 실무상 유용한 경고(정답지 미등재 진양성)인지, 과민 규칙에 의한 오탐인지, 동일 원인의 중복 경고인지는 전수 라벨링(P0-2) 전까지 미측정 상태다. |
| **3. 온라인 RAG `PARTIAL` 및 `BUDGET_EXHAUSTED` 발생 조건** | **확인된 사실** | `packages/rag_engine/extract.py:224-266, 369-375` 및 `packages/rag_engine/library.py:486-489` 확인 결과 세 가지 경로가 결합되어 발생한다: ① 호출당 OCR 예산 기본값 5페이지(`LV_REFERENCE_OCR_MAX_PAGES` → `5`) 도달 시 중단 및 `CAUSE_BUDGET_EXHAUSTED` 기록, ② `pypdfium2` 로드 실패(`native = None`) 시 시각 전용 페이지가 `ocr_available=True`로 기록되어 `continuation=None`인 채 `BUDGET_EXHAUSTED`로 오분류되는 결함(TK-208 D1), ③ `library.py:487`이 `prior.get("continuation")`이 있을 때만 재추출을 시도하여 `continuation=None`인 `PARTIAL` 파일이 SQLite 캐시에서 영구 재사용되는 결함(TK-208 D2). |
| **4. `LocalLLMProvider` 구현 수준** | **확인된 사실** | `packages/llm_router/providers.py:479-523` 확인 결과, OpenAI 호환 `/chat/completions`에 `model`, `messages`, `temperature`, `max_tokens` 4개 필드만 전송하는 최소 어댑터다. `request.schema`(JSON Schema 강제 출력)를 무시하고, `_checked()`(`finish_reason == "length"` 절단 검사)를 호출하지 않으며, `usage` 토큰 수(`input_tokens`, `output_tokens`)도 파싱하지 않는다(항상 `0`). |
| **5. 문장 분리·서법·부정·화자 귀속 중복 현황** | **확인된 사실** | `packages/claim_engine/`과 `packages/legal_engine/` 전반에 걸쳐 최소 4종의 독자적 문장 분리기와 15개 이상의 개별 부정·가정·전달·미래시제 정규식이 파편화되어 있다(아래 2.5절 상세 표 참조). 형태소 분석기(Kiwi 등)나 공용 Clause Normalizer 계층은 존재하지 않는다. |
| **6. 인용-원문 의미 비교, 근거 구간 연결 및 `pgvector` 현황** | **확인된 사실** | ① 인용-원문 정렬은 `packages/legal_engine/evidence_basis.py`의 문자 정규화 퍼지 매칭(`locate_fuzzy_normalized`, `SequenceMatcher`)과 `quote_diff.py`의 어휘 차분(`DEGREE`, `NEGATION`, `MODALITY`, `PARTY_SWAP`, `PROVISO_OMISSION`, `NUMERIC`)으로 동작한다. ② 주장 3분류(`SUPPORTED`/`CONTRADICTED`/`INSUFFICIENT`)가 `argument_validity_verifier.py:153-174`에 도입되었으나 NLI 모델이 아닌 규칙·기존 판정 매핑이다. ③ **`pgvector`는 스키마(`migrations/versions/20260906_98e07fd05c9e_initial_schema.py:100`, `apps/api/db.py:305`)와 설정(`config.py:118` `rag_hybrid_semantic=True`)에만 존재할 뿐, 실제 코드베이스 어디에서도 임베딩을 생성하거나 조회하지 않는다.** |

---

## 2. 6대 핵심 병목 상세 코드 감사

### 2.1 오프라인 법률 결함 재현율(43 / 123, 35.0%) 정체 메커니즘

1. **채점기 엄격 매칭 규칙 (`scripts/evaluation_v2.py`)**
   - [`evaluation_v2.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/evaluation_v2.py#L13-L14)는 확정 양성 상태 집합을 `POSITIVE = {"NOT_FOUND", "CONTRADICTED", "SUSPICIOUS", "INVALID_FORMAT", "INVALID", "MODIFIED"}`로 정의한다.
   - [`evaluation_v2.py:121-125`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/evaluation_v2.py#L121-L125)에서 `UNCERTAIN = {"CIT-NX-DB", "SRC-UNV"}`에 해당하는 9개 항목만 `status == "UNVERIFIED"`를 정답으로 인정하고, 나머지 모든 법률 결함(123개 항목)은 **`not findings[j].get("advisory_only")` 이면서 `status in POSITIVE`** 여야만 적중(`hit`)으로 인정하고 이분 매칭(`maximum_matching`)을 수행한다.
2. **오프라인 실행 시 공식 원문 부재와 Fail-Closed 설계의 충돌**
   - [`packages/legal_engine/verifier.py:9-11`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/verifier.py#L9-L11) 주석에 명시된 바와 같이 *"공식 Source가 없으면 UNVERIFIED로 남기고 LLM 답변만으로 VERIFIED 처리하지 않는다(부록 C 제3항)"*.
   - 오프라인 평가(`LV_ALLOW_NETWORK=0`)에서는 국가법령정보센터 API 조회가 차단된다. 따라서 사건번호 형식 자체에 달력 불가능 날짜(`FMT.DATE_NOT_ON_CALENDAR`), 미래 연도(`FMT.FUTURE_CASE_YEAR`), 법원-사건부호 불일치(`FMT.COURT_CODE_MISMATCH`), 대법원·헌재 사건부호 대역 밖 번호 등 **결정론적 형식 위반**이 있거나 로컬 규칙표([`config/legal_rules/rules.json`](file:///home/antigravity/stevelee0119/ACASia_LAW/config/legal_rules/rules.json))에 수록된 조문·법리만 `POSITIVE` 판정을 내릴 수 있다.
3. **유형별 오프라인 적중 현황 (`docs/scorecards/benchmark_audit_2026-11-13.md:64-76`)**
   - `CIT-FAB-Q` (판례 직접 인용문 날조): **0 / 9 (0.0%)** — 공식 판결문 본문이 없으면 직접 인용문이 날조되었는지 대조 불가(`UNVERIFIED`).
   - `CIT-MIS` (판례 취지 왜곡): **0 / 7 (0.0%)** — 공식 판시사항·판결요지가 없으면 판례 취지 왜곡 판정 불가(`UNVERIFIED`).
   - `LAW-NX` (존재하지 않는 법령·조문): **0 / 15 (0.0%)** — 로컬 조문 범위표(`packages/legal_engine/statute_ranges.py`)에 없는 법령이나 비참고 확정 판정 요건 미충족 시 미탐.
   - `LAW-MIS` (법령 조문 왜곡·오적용): **4 / 22 (18.2%)** — `claim_review.py` 및 `legal_rules.py`에 등록된 일반 법리 패턴만 탐지.
   - `CIT-META` (선고일·법원 메타 불일치): **6 / 12 (50.0%)** — 연도 역전 등 형식상 모순만 오프라인 탐지 가능.
   - `CIT-NX` (허위 사건번호): **11 / 14 (78.6%)** — 사건부호·연도·번호 대역 규칙으로 탐지.
   - `EVI-FAKECIT` (존재하지 않는 증거·인용 결합): **5 / 9 (55.6%)**.
   - `OVR` / `OVR / LAW-NX` (변경된 판례·위헌 조문 원용): **17 / 35 (48.6%)**.
4. **결론**: 오프라인 법률 재현율 35.0%는 단일 지표로 묶여 있으나 실제로는 **(A) 오프라인 검증 가능 항목(형식·로컬 규칙·문서 내 모순)** 과 **(B) 외부 공식 원문(또는 고정 스냅샷)이 필수인 항목** 이 혼재된 결과다.

---

### 2.2 정답지 외 미판정 경고(Unadjudicated Alerts) 102건의 발생 경로

1. **집계 코드 경로**
   - `scripts/eval_testset.py`는 각 문서의 `findings` 중 `advisory_only=False`이고 결함 상태(`POSITIVE`)인 Finding을 정답지 항목과 매칭한 뒤, 매칭되지 않고 남은 Finding 리스트를 `unmatched_defect_findings`에 담는다.
   - [`scripts/evaluation_v2.py:138`](file:///home/antigravity/stevelee0119/ACASia_LAW/scripts/evaluation_v2.py#L138)은 `len(old["unmatched_defect_findings"])`를 `unadjudicated_alerts`로 기록한다.
2. **현재 분포 특성 (`docs/scorecards/DAILY_TREND.md:135`)**
   - 51개 문서(dev 36 + holdout 15)에서 총 **102건** 발생 (문서당 2.00건).
   - **동일 문서·동일 결함 유형 중복**: **24건** (하나의 사실관계·인용 불일치가 여러 문장 또는 하위 엔진에서 반복 보고됨).
   - **증거등급 A등급 경고**: **72건** (높은 확신도로 보고되었으나 정답지에 항목이 없거나 매칭 토큰이 어긋난 경고).
3. **구조적 문제점**
   - 정답지(`ground_truth.json` / `match_spec.json`)는 문서당 주요 결함 위주로 작성되어 있어, 엔진이 문서 내 부수적 날짜·금액·인용·형식 결함을 정당하게 찾아내도 `unadjudicated_alerts`로 분류된다.
   - 반대로, 매칭 토큰(`match_spec.json`)과 Finding의 텍스트 표현이 달라 정답 항목을 맞혔음에도 매칭에 실패해 `미탐(FN) + 미판정 경고(Unadjudicated)`로 이중 불이익을 받는 사례(`EVAL_ARTIFACT`)와 실제 과민 탐지(`TRUE_FP`)가 구분되지 않고 있다.

---

### 2.3 온라인 RAG `PARTIAL` 및 `BUDGET_EXHAUSTED` 발생 경로

[`packages/rag_engine/extract.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L180-L390) 및 [`packages/rag_engine/library.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/library.py#L480-L590) 감사 결과:

1. **호출당 고정 OCR 페이지 예산 (`max_ocr_pages = 5`)**
   - [`extract.py:397-402`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L397-L402)의 `_reference_ocr_budget()`는 `LV_REFERENCE_OCR_MAX_PAGES` → `LV_OCR_MAX_PAGES` → 기본값 `"5"`를 읽는다.
   - 스캔 PDF(예: 12쪽 판결문·법령집 사본) 추출 시 [`extract.py:252-259`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L252-L259)에서 5쪽까지만 OCR을 수행한 뒤 `next_continuation = {"next_page": page_no, ...}`를 남기고 루프를 중단(`break`)하며, 나머지 6~12쪽은 [`extract.py:372`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L372)에서 일괄 `CAUSE_BUDGET_EXHAUSTED`로 마킹된다.
2. **시각 전용 페이지의 `BUDGET_EXHAUSTED` 오분류 (TK-208 D1)**
   - [`extract.py:190-194`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L190-L194)에서 `pypdfium2.PdfDocument(path)` 초기화가 실패해 `native = None`이 되면, 텍스트 레이어가 없는 페이지는 [`extract.py:266`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L266)으로 내려가 `_page_diag("scanned", ocr_available=max_ocr_pages > 0)`를 기록한다.
   - 이때 `max_ocr_pages`가 5이므로 `ocr_available=True`가 되어 [`extract.py:373`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/extract.py#L373)에서 `CAUSE_BUDGET_EXHAUSTED`로 분류되지만, 실제로는 `next_continuation`이 생성되지 않아 `continuation=None`이 된다.
3. **캐시 재사용 루프에서 영구 `PARTIAL` 고착 (TK-208 D2)**
   - [`library.py:486-489`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/library.py#L486-L489):
     ```python
     prior = existing.get(fid)
     continuing = bool(prior and prior["md5"] == md5 and prior["extraction_version"] == EXTRACTION_VERSION
                       and prior["status"] == STATUS_PARTIAL and prior.get("continuation"))
     if prior and prior["md5"] == md5 and prior["extraction_version"] == EXTRACTION_VERSION and not continuing:
         ...
         files_reused += 1
         continue
     ```
   - `prior["status"] == STATUS_PARTIAL`이더라도 `prior.get("continuation")`이 `None`이면 `continuing = False`가 되어 재추출을 건너뛰고 캐시된 `PARTIAL` 상태를 영구 재사용한다.
   - 또한 `continuing = True`인 경우에도 한 번의 검증 실행(`sync_drive_folder`)마다 최대 5쪽씩만 전진하므로, 25쪽 스캔 문서는 검증을 5회 반복 실행해야만 `COMPLETE`에 도달한다.

---

### 2.4 `LocalLLMProvider` 구현 수준 감사

[`packages/llm_router/providers.py:479-523`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/llm_router/providers.py#L479-L523) 감사 결과:

```python
class LocalLLMProvider(LLMProvider):
    """vLLM / Ollama OpenAI 호환 엔드포인트."""
    name = "local"
    ...
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
```

- **결함 1 (구조화 스키마 미전달)**: `OpenAIProvider`(`providers.py:194-205`), `AnthropicProvider`(`providers.py:293-305`), `GeminiProvider`(`providers.py:390-398`), `PerplexityProvider`(`providers.py:446-455`)는 모두 `request.schema`가 있을 때 `response_format={"type": "json_schema", ...}` 또는 `tool_choice`를 사용해 JSON 스키마 출력을 강제한다. 반면 `LocalLLMProvider`는 `request.schema`를 전혀 참조하지 않는다.
- **결함 2 (출력 절단 미검출)**: 다른 4개 공급자는 모두 응답 수신 후 `_checked(text, stop_reason, self.name, model)`(`providers.py:114-120`)을 호출해 토큰 상한 절단(`finish_reason == "length"`) 시 `LLMTruncatedResponseError`를 발생시키고 JSON 파싱 오염을 차단한다. `LocalLLMProvider`는 `_checked()`를 호출하지 않는다.
- **결함 3 (토큰 사용량 및 관측성 누락)**: OpenAI 호환 응답의 `data.get("usage", {})`에서 `prompt_tokens`/`completion_tokens`를 추출하지 않아 `LLMResponse.input_tokens`와 `output_tokens`가 항상 `0`으로 기록된다.
- **결함 4 (역할별 타임아웃·재시도·헬스체크 부재)**: 로컬 GPU/CPU 추론 지연 특성을 고려한 엔드포인트 헬스 프로브(`/v1/models`), Guided Decoding 백엔드(vLLM `guided_json` vs Ollama `format`), 폴백 체인이 없다.

---

### 2.5 한국어 문장 분리·서법·부정·화자 귀속 중복 감사

현재 코드베이스에서 동일하거나 유사한 한국어 문법 판별 로직이 아래 모듈들에 각각 독립된 정규식으로 중복 구현되어 있다:

| 기능 영역 | 중복 구현된 파일 및 심볼 | 파편화로 인한 문제점 |
| --- | --- | --- |
| **문장 경계 분리** | - [`packages/document_engine/reading_text.py:295`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/document_engine/reading_text.py#L295) (`sentence_bounds`)<br>- [`packages/claim_engine/assertion.py:74`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/assertion.py#L74) (`_sentences`)<br>- [`packages/claim_engine/attachments.py:213`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/attachments.py#L213) (`_sentences`)<br>- [`packages/claim_engine/evidence_consistency.py:3124`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/evidence_consistency.py#L3124) (`_sentences_for_copy`) | 판례 날짜(`2023. 5. 12.`), 조문 약어, 괄호 안 마침표 처리에서 모듈마다 문장 경계와 `(start, end)` 오프셋이 달라짐 |
| **부정 및 이중부정 (Negation)** | - [`packages/legal_engine/polarity.py:25`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/polarity.py#L25) (`NEGATION_RE`, 홀짝 카운트)<br>- [`packages/claim_engine/structure.py:23`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/structure.py#L23) (`NEGATION_RE`)<br>- [`packages/claim_engine/date_verifier.py:171`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/date_verifier.py#L171) (`EXCLUDE_NEGATION_RE`)<br>- [`packages/claim_engine/evidence_consistency.py:690`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/evidence_consistency.py#L690) (`UNIVERSAL_NEGATION_RE`)<br>- [`packages/claim_engine/internal_inconsistency.py:175,271,1385`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/internal_inconsistency.py#L175) (`_SIGNER_NEGATION_RE`, `_QUANTITY_NEGATION_RE`, `_CLAUSE_NEGATION_FUTURE_RE`)<br>- [`packages/legal_engine/legal_rules.py:342,398`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/legal_rules.py#L342) (`NEGATION_WORDS_RE`, `_REQUIREMENT_NEGATION_RE`) | `polarity.py`는 절 단위 홀짝(이중부정=긍정)을 계산하지만, `date_verifier.py`나 `structure.py`는 단순 키워드 매칭을 사용하여 이중부정(`~않다고 볼 수 없다`)에서 서로 반대 판정을 냄 |
| **화자 귀속·상대방 주장 인용·판례 전달 (Attribution / Hearsay)** | - [`packages/legal_engine/polarity.py:30-38`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/polarity.py#L30-L38) (`COURT_SUBJECT_RE`, `REPORT_VERB_RE`, `OPPONENT_REPORT_RE`)<br>- [`packages/legal_engine/verifier.py:79`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/verifier.py#L79) (`_OPPONENT_CLAIM_RE`)<br>- [`packages/claim_engine/classification.py:116`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/classification.py#L116) (`assertion_mode` → `QUOTED_OTHER`)<br>- [`packages/claim_engine/date_verifier.py:167`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/date_verifier.py#L167) (`EXCLUDE_OPPONENT_CLAIM_RE`)<br>- [`packages/claim_engine/evidence_consistency.py:339,916`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/evidence_consistency.py#L339) (`_EVI_FORM_OPPONENT_CHALLENGE_RE`, `_OPPONENT_CLAIM_VERBS_PAT`) | 한 모듈에서 상대방 주장 인용 오탐을 막는 패턴을 패치해도 다른 모듈에는 반영되지 않아 유사 문형에서 오탐이 재발함 |
| **가정·예비적 주장·미래 시제 (Modality / Temporal)** | - [`packages/legal_engine/polarity.py:39-40`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/polarity.py#L39-L40) (`CONDITIONAL_LEAD_RE`, `CONDITIONAL_TAIL_RE`)<br>- [`packages/claim_engine/classification.py:55`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/classification.py#L55) (`HYPOTHETICAL`, `ALTERNATIVE`)<br>- [`packages/claim_engine/date_verifier.py:68,164,692`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/date_verifier.py#L68) (`FUTURE_EXCLUDE_RE`, `EXCLUDE_FUTURE_RE`, `_CAUSAL_FUTURE_EXCLUDE_RE`)<br>- [`packages/claim_engine/evidence_consistency.py:189-190`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/claim_engine/evidence_consistency.py#L189-L190) (`_FUTURE_SUBMISSION_RE`) | 예정 표현(`제출할 예정`, `지급하기로 한다`), 가정(`설령 ~라 하더라도`), 예비적 주장이 모듈마다 다르게 필터링됨 |

---

### 2.6 인용-원문 의미 비교, 근거 구간 연결 및 `pgvector` 감사

1. **근거 구간 정렬 (`packages/legal_engine/evidence_basis.py`)**
   - [`quote_span()`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/evidence_basis.py#L60-L120) 및 [`align_quote()`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/evidence_basis.py#L140-L195)는 공백·문장부호를 정규화한 문자열에서 `locate_fuzzy_normalized()`와 `difflib.SequenceMatcher`를 사용해 공식 원문 내 대응 구간 `(start, end)`와 어절 정렬(`alignment`), 위치 신뢰도(`location_confidence`)를 계산한다.
   - **한계**: 어휘·어순이 유사한 직접 인용문 변형에는 강건하나, 간접 인용(paraphrase)이나 복수 문단에 걸친 요지 압축 인용에서는 문자 유사도가 낮아 근거 구간 특정에 실패한다.
2. **차분 분류 (`packages/legal_engine/quote_diff.py`)**
   - [`quote_changes()`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/quote_diff.py#L75-L190)는 정렬된 두 구간 사이의 치환·삭제·삽입 토큰을 검사하여 `DEGREE`(정도 부사), `NEGATION`(부정), `MODALITY`(할 수 있다 ↔ 하여야 한다), `PARTY_SWAP`(원고 ↔ 피고), `PROVISION_QUALIFIER`(요건 한정어), `PROVISO_OMISSION`(단서 누락), `NUMERIC`(수치 변경)을 결정론적으로 분류한다.
   - **한계**: 어휘 치환 사전과 정규식에 의존하므로, 동의어 반전이나 문맥적 함의 모순(예: 예외 요건이 충족되었음을 전제로 본문 원칙을 뒤집는 서술)은 포착하지 못한다.
3. **검색 엔진 및 `pgvector` 미사용 실태 (`packages/rag_engine/relevance.py`, `apps/api/db.py`)**
   - [`migrations/versions/20260906_98e07fd05c9e_initial_schema.py:100`](file:///home/antigravity/stevelee0119/ACASia_LAW/migrations/versions/20260906_98e07fd05c9e_initial_schema.py#L100)에 `document_blocks.embedding` (`vector(1536)`) 및 HNSW 인덱스(`ix_document_blocks_embedding_hnsw`)가 선언되어 있고, [`packages/common/config.py:118`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/common/config.py#L118)에 `rag_hybrid_semantic: bool = True`가 존재한다.
   - 그러나 `packages/rag_engine/`의 실제 검색 구현([`relevance.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/relevance.py#L1-L240), [`library.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/rag_engine/library.py#L600-L780))은 SQLite `chunks` 테이블에서 **한국어 음절 바이그램(`tokens()`) + 어휘 IDF 가중치 매칭**만 수행하며, Dense 임베딩이나 Cross-Encoder Reranker, `pgvector` 질의는 단 한 줄도 연결되어 있지 않다.
   - 또한 법률 적용성 검증([`packages/legal_engine/source_review.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/source_review.py), [`temporal_review.py`](file:///home/antigravity/stevelee0119/ACASia_LAW/packages/legal_engine/temporal_review.py))은 공식 API로 단건 조회된 법령·판례에만 작동하고, RAG로 검색된 청크에는 시간적 유효성(시행일)·판례 변경 여부 필터가 결합되어 있지 않다.
