# 설계 메모 및 평가 측 요청: `EVALUATION_V2` 4차원 구조화 출력 계약 (`0.28.0` 과제 4)

- **관련 과제:** `0.28.0` 트랙 `[과제 4]`
- **작성일:** 2026-11-22
- **구현 측 범위:** 제품 엔진(`packages/verification_engine/eval_contract.py`, `pipeline.py`)
- **평가 측 변경 요청:** 보호 경로인 `scripts/export_quality_predictions.py` 확장 요청

## 1. 제품 출력 4차원 계약 (`engine_data["evaluation_dimensions"]`)
기존 `legal_verdicts`·`citations`·`findings` 하위 호환을 100% 유지하면서 `DocumentResult.engine_data["evaluation_dimensions"]`에 아래 4개 독립 차원을 기록한다(원문 PII·당사자명 미포함, SHA-256 기반 `item_id`):

1. **`identity`**: 인용 실존/형식 판정 (`item_id = "identity-" + sha256(doc_sha256, page, span, text_sha256)`, `status`, `errors`)
2. **`quote`**: 직접 인용문 일치 판정 (`item_id = "quote-" + sha256(...)`, `status`, `errors`)
3. **`claim_applicability`**: 주장 단위 적용/타당성 판정 (`item_id = "claim-" + sha256(doc_sha256, page, span, claim_sha256)`, `judgment ∈ {"SUPPORTS", "CONTRADICTS", "INSUFFICIENT"}`, `evidence_spans: [{"document_id", "page", "span", "length"}]`)
4. **`source_retrieval`**: 출처 검색 메타데이터 (`item_id = "source-" + sha256(...)`, `source_name`, `status`, `matched_count`, `cause`, `official_span`)

## 2. 평가 측(`scripts/export_quality_predictions.py`) 변경 요청
- 현재 `export_quality_predictions.py`는 `DIMENSIONS = {"identity", "quote"}`만 지원한다.
- 평가 측에서 `doc["engine_data"]["evaluation_dimensions"]["claim_applicability"]` 및 `["source_retrieval"]`을 읽어 `EVALUATION_V2.md`의 주장/법리 적용 및 출처 검색 `NOT_MEASURED`를 해소하도록 `export_quality_predictions.py` 확장을 요청한다.
