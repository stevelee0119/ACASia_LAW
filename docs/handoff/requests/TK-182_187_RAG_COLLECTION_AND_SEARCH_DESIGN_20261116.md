# TK-182 · TK-187 구현 설계 메모: 참고자료 수집 분리·쪽별 상태 구분·주장 단위 다중 검색

작성: 2026-11-16 · 기준 브랜치: `Steve_ACASiaLAW` · 참조: `TK-182_drive_reference_coverage.md`, `TK-187_rag_claim_candidate_coverage.md`, `requests/RAG_REDESIGN_PROPOSAL_20261116.md`

---

## 1. 핵심 변경 요약

1. **수집·색인과 문서 질의의 분리 (TK-187 1단계)**
   - `VerificationPipeline.run()`은 `LV_RAG_DECOUPLED_COLLECTION`(기본 `1`)이 켜진 동안 `references._default_collect_all`을 활성화한 뒤 `references.sync(query=query)`를 호출해(기존 `sync(query=...)` 시그니처·테스트 호환 유지) **폴더 내 읽기 허용·지원 형식 자료 전체를 질의·파일명·폴더명과 무관하게 수집·색인**한다.
   - 질의(`query`)와 파일명/폴더명 일치 점수(`metadata_priority`)는 다운로드 우선순위와 검색 가점으로만 쓰고 `NOT_SELECTED_METADATA / NAME_PATH_NOT_RELATED` 탈락 조건으로 쓰지 않는다.
   - 기존 `ReferenceLibrary.sync(query=...)` 직접 호출 호환(`LV_RAG_METADATA_FIRST=1`, `collect_all=None`)은 유지하되, 제품 실행 경로(`collect_all=True`) 및 전역 `LV_RAG_METADATA_FIRST=0` 환경에서는 전량 수집(`FULL_CORPUS_INDEX`)이 동작한다.
   - 권한 철회·휴지통·폴더 이동(`access_problem`) 또는 목록에서 사라진 자료는 즉시 `eligible`·`chunks`·`case_rows`에서 제거하여 과거 스냅샷에서도 검색되지 않게 차단한다.

2. **쪽별 상태 분리·시각적 빈 쪽 확인·추출기 판 상향 (TK-182 후속)**
   - `packages/rag_engine/extract.py`:
     - **`extracted_text_pages`(`read_pages`)와 `completed_pages` 분리**: 본문 청크가 추출된 쪽 수(`NATIVE_TEXT`, `OCR_TEXT`)와 검사가 완결된 쪽 수(`NATIVE_TEXT`, `OCR_TEXT`, `VERIFIED_BLANK`)를 따로 집계한다.
     - **시각적 빈 쪽 검증 강화**: `pypdfium2` 객체 열거(`page.get_objects()`)가 성공하고 이미지·벡터 객체·스트림 그리기 연산이 전혀 없으며 `pypdf` 이미지도 없을 때만 `VERIFIED_BLANK`(`status="blank"`)로 확정한다. 객체 열거 실패, 미지원 벡터/이미지 존재, OCR 저품질(`OCR_LOW_QUALITY`)은 빈 쪽으로 숨기지 않고 `scanned` / `ocr_low_quality` / `error`로 남긴다.
     - **OCR 저품질 검출**: `_ocr_pdf_page()`는 `packages.document_engine.ocr.page_quality()`로 평균 신뢰도와 유효 문자를 검사해 `ocr_min_confidence` / `ocr_quality_min_confidence` 미달 시 `status="ocr_low_quality"`, `state="OCR_LOW_QUALITY"`로 기록하고 `partial=True`를 유지한다.
     - **`partial`(본문 미추출)과 `coverage_complete`(전 쪽 처리 완료) 분리**: `extract()`는 기존 `read_pages < total` 계약(`partial=True`)을 유지하면서 `coverage_complete=True`를 함께 반환하고, `ReferenceLibrary`는 `coverage_complete=True`이고 미완료·스캔·오류·저품질 쪽이 없는 빈 쪽 문서를 `INDEXED` / `READY`(`VERIFIED_BLANK_PAGES` / `VERIFIED_BLANK_DOCUMENT`)로 정상 완독 분류한다.
     - **추출기 판 상향**: `EXTRACTOR_VERSION = "drive-text-v9-tk182"`로 올려 구 캐시의 `partial`/빈 쪽 오분류를 리비전 유지 상태에서도 자동 재평가한다.

3. **주장·쟁점별 다중 경로 검색 및 범위 원장 분리 (TK-187)**
   - **다중 경로 검색 (`library.py`, `relevance.py`, `review.py`)**:
     - 경로 ① **식별자·법령·사건번호 정확 조회** (`search_citation`, 법령+조문·사건번호 정규화)
     - 경로 ② **한국어 조사 제거 어간 + 문자 2-gram FTS5 검색** (문서 앞 24,000자 절단 해제, 다쟁점 전 구간 윈도우 순회 + 주장 단위 절·어절 OR 결합 검색)
     - 경로 ③ **로컬 결정론적 의미 유사도(TF-IDF 코사인 + 문자 n-gram 유사도) 및 순위 융합(RRF)** (`LV_RAG_HYBRID_SEMANTIC=1`, 외부 임베딩 API 전송 없음). 파일명 점수가 0인 자료(영문·무관 파일명)도 본문 근거가 충분하면 통과하도록 파일명 0점 배제 규칙을 제거한다.
     - 동일 문헌 독점 방지(파일당 상한 + 다중 파일 다양성 보장) 및 인접 쪽/문단 문맥 복원(800자 주장 요청 한도 유지).
   - **전역 원장과 실행 범위 원장 분리**:
     - `summary["coverage_ledger"]`는 전체 드라이브 자료 상태(`global_library`: 완독/빈쪽/스캔/OCR저품질/오류/미처리)를 유지하고, `review["search_scope"]`는 해당 문서·주장별 검색 범위·예산·다중 경로 적중 수를 별도로 보고한다.

4. **보안·역할 경계 및 되돌림(Rollback)**
   - TK-180 역할 분리(`authority="USER_REFERENCE_NOT_OFFICIAL"`, 참고자료 본문을 `AdversarialScanner`에 넣지 않음)와 입력 문서 PII 마스킹(`pii.mask_text`)·인젝션 격리는 변경 없이 유지한다.
   - 환경변수 플래그(`LV_RAG_DECOUPLED_COLLECTION`, `LV_RAG_CLAIM_MULTISEARCH`, `LV_RAG_HYBRID_SEMANTIC`, 기본 `1`)로 운영 중 즉시 구 경로로 되돌리거나 동일 스냅샷 기준 A/B 비교가 가능하다.
