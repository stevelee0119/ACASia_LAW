# 0.26.0 온라인 관찰과 후속 확인

## 1. Drive 저품질 16쪽 그대로 (TK-227, P2)

- **재현:** 공개 `case9` 서면을 운영 API에서 3회 연속 검증한다. 각 결과의 `run_manifest.reference_library.coverage_ledger.global_library`를 확인한다.
- **기대:** RapidOCR 적용 후 기존 저품질 쪽의 재처리 건수와 읽을 수 있게 된 쪽 수가 관찰된다.
- **실제:** 41/41 자료가 캐시에서 재사용됐고 Drive OCR 폴백 시도·채택은 0쪽, `OCR_LOW_QUALITY` 미완독은 16쪽으로 유지됐다. 새 저품질 스캔 입력 1쪽에서는 폴백이 채택됐지만 최종 상태는 여전히 `OCR_LOW_QUALITY`였다.
- **원인 가설:** 기존 Drive 색인 리비전과 추출기 버전이 그대로라 저품질 쪽을 재추출하지 않았다. 운영 관찰로 캐시 재사용은 확인했으나 캐시 내부의 모든 판단 경로는 확인하지 못했다.
- **후속 검증:** 기존 16쪽만 재처리할 수 있는 명시적 색인 갱신 절차를 마련하고, 전후 원인별 쪽 수·다운로드 건수·검색 가능한 쪽 수·본문 정확도를 같은 스냅샷에서 비교한다. 품질 기준을 넘지 못한 쪽은 계속 미완독으로 남겨야 한다.

## 2. 검색 설정 표시와 실호출 불일치 (TK-228, P2)

- **재현:** 운영 `/api/diagnostics`와 `case9` 결과의 검색 진단을 비교한다.
- **실제:** 사용자는 `LV_RAG_RETRIEVAL_MODE=lexical_only`를 API·worker에 설정해 재배포했다고 보고했다. 진단의 `configured_mode`는 `HYBRID`, `reranker_enabled`는 `true`로 남지만 `effective_mode`는 `LEXICAL_ONLY`이고 실제 임베딩·재순위 요청은 각각 0건이다. `search_diagnostics.retrieval.fallback_reasons`에는 두 엔드포인트 미구성이 기록됐다.
- **영향:** 설정 표시만으로 ON 효과를 주장하면 오판한다. 실제 검색은 어휘 방식으로 동작했다.
- **후속 검증:** 배포된 프로세스의 유효 변수와 진단 산출 기준을 대조하고, 주소·모델·실호출 성공 여부를 분리해 표시한다. 서버가 구축되면 같은 자료·스냅샷에서 ON/OFF를 짝지어 실제 요청 수, `effective_mode`, 정답 자료 순위, 오탐·지연을 비교한다.

## 3. LOCAL_ONLY 운영 효과 미측정 (TK-229, P2)

- **실제:** 로컬 모델 서버가 아직 구축되지 않아 공급자 등록 0개다. `LOCAL_ONLY` 짝 비교와 실호출 수는 측정할 수 없다.
- **후속 검증:** `/models`·`/chat/completions`를 제공하는 서버를 구축하고 실제 모델 ID·접속 URL을 설정한 뒤, 같은 합성 입력을 `MASKED`와 `LOCAL_ONLY`로 실행한다. 로컬 호출 성공·실패 건수와 외부 공급자 호출 0건을 함께 확인한다. 서버가 없을 때 임의 주소나 모델명을 변수에 넣지 않는다.

## 4. 배포 전환 중 검색 중단 1건 (TK-225, 관찰)

- **재현:** 재배포와 겹친 별도 `case9` 실행의 `documents[0].engine_data.rag.search_diagnostics.document_select`를 본다.
- **실제:** `interrupted=true`, 중단 단계 `main_fts`, `window_fts`, 사유 `SQLITE_QUERY_INTERRUPTED`, 부분 결과 표시. 같은 실행의 표준·RAG·건강 점수는 모두 만점이었다. 안정된 배포의 후속 3회는 중단 0건이다.
- **후속 검증:** 배포 시점의 worker 교체·DB 경합·검색 제한 시간을 서버 로그와 대조한다. 장기 부하 및 재배포 중 시험에서 `interrupted`와 부분 커버리지 비율을 따로 집계한다. 이 1건만으로 안정된 배포의 회귀를 단정하지 않는다.
