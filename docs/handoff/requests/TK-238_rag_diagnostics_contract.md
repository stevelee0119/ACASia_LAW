# TK-238 RAG·OCR 폴백 실행 진단 계약 (F1 / `run_manifest` 진단 명세)

## 1. `rag_retrieval_diagnostics.actual_calls` 정의 (A-1)

- `actual_calls = embedding_requests + reranker_requests`의 합이며, 작업별 구분은 각 필드로 본다.
  - 임베딩 작업: `embedding_requests`, `embedding_successes`, `embedding_failures`, `embedding_ms`
  - 재순위 작업: `reranker_requests`, `reranker_successes`, `reranker_failures`, `reranker_ms`
  - 전체 검색·캐시: `retrieval_ms`, `cache_hits`, `cache_misses`
- 소비자는 합산값(`actual_calls`)만으로 Dense 임베딩과 재순위 호출을 역산·분리하지 않고, 작업별 개별 필드를 기준으로 해석한다.

## 2. 미측정 구분 (`measured`) (A-2)

- 실행 전 스냅샷(`next_gen_feature_diagnostics()`)과 측정 대상 문서가 0개인 실행(`len(documents) == 0`)에서는 `rag.measured = False`, `ocr_fallback.measured = False`로 남긴다.
- 문서는 있으나 검색 기록(`engine_data.rag.search_diagnostics.retrieval`)이 있는 문서가 0개(`measured_docs == 0`)이면 `rag.measured = False`로 남기고 `NO_RELEVANT_DOCUMENTS_OR_CHUNKS_FOR_DENSE` 사유를 단정하지 않는다. 검색 기록이 있는 문서가 1개 이상(`measured_docs > 0`)일 때만 `rag.measured = True`로 집계한다.

## 3. `effective_mode` 표기 정합성 (A-3)

- 실행 전 스냅샷은 기능 가용 여부 기준으로 `HYBRID` 또는 `LEXICAL_ONLY`를 기록한다.
- 실행 후 `aggregate_run_feature_diagnostics()`는 문서 단위 `search_diagnostics.retrieval.effective_mode`(`HYBRID_RERANK` > `HYBRID_DENSE` > `LEXICAL_RERANK`)가 관측되면 run 단위 `rag.effective_mode`를 해당 세부 표기로 통일해 문서 단위 기록과 일치시킨다.
