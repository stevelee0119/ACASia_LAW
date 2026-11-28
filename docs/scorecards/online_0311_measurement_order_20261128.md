# 0.31.1 운영 재측정 지시 (Codex 대행, 2026-11-28)

사용자 원문: "운영재측정은 codex에서 하도록 지시문을 구체적으로 만들어줘"(2026-11-28). 아래 코드 블록이 Codex에 준 지시 전문이다.

```
[0.31.1 운영 재측정 — Codex 대행] 측정만 한다. 판정은 평가 측(Claude Code)이 한다.

0. 근거·범위
 - 사용자 지시(2026-11-28): 0.31.1 배포 뒤 운영 재측정을 Codex가 대행한다.
 - 대상 판: 운영 0.31.1, main 5626ecb7(#472). 릴리스 판정서: docs/scorecards/release_0311_candidate_20261128.md
 - 확인할 변경:
   · TK-253(#468): openai_review=gpt-6.2-sol, gemini=gemini-4-neon
   · TK-254(#469): Anthropic 캐시 지점을 system 블록으로 옮김. 사용자가 Render에 LV_LLM_PROMPT_CACHING=1을 설정함
   · TK-255(#469): 공급자 거절이 RAG 상한·예산을 소진하지 않음(운영 재현은 거절이 생길 때만 됨)
 - 범위: case9 3회, U2, 데이터셋 상태, 정리. 인용 대조군 N1~N5·다문서는 평가 측 비공개 입력이라 하지 않는다.
 - 하지 말 것:
   · 제품 코드·설정·시험·평가 도구 변경
   · main·Steve_ACASiaLAW push
   · 영구 삭제(purge)
   · Render 환경변수 변경
   · 토큰·키·비밀번호·문서 본문·당사자 정보 출력(존재 여부·길이만)
   · 병렬 실행(3회는 순서대로)

1. 선행 확인(하나라도 어긋나면 멈추고 그대로 보고)
 1-1 GET {BASE}/api/health → version "0.31.1", commit 앞 8자리 "5626ecb7", database ok
     BASE는 환경변수 AEGISLAW_TEST_BASE_URL. 출력할 때는 호스트를 가린다.
 1-2 로그인: POST {BASE}/api/auth/login, JSON {"email": $AEGISLAW_TEST_EMAIL, "password": $AEGISLAW_TEST_PASSWORD}
     → access_token을 파일(권한 600)에만 저장한다. role이 ADMIN인지 확인한다.
 1-3 GET {BASE}/api/settings/reference-dataset (Authorization: Bearer)
     → 저장할 값: configured, initialized, snapshot_hash, inventory_mode, files_cached, files_indexed, identifiers_cached, pending_low_quality_reprocess, failed_updates
     → 기대(0.31.0 2차와 같음): snapshot_hash 앞 8자리 11922706, files_indexed 41, pending_low_quality_reprocess 0
 1-4 처리 대기 작업이 없을 때 시작한다. 캐시 설정 전 대기 작업은 EXECUTION_SETTINGS_CHANGED로 다시 시도될 수 있다.

2. case9 3회(m1→m2→m3, 순서대로, 회차 사이 대기 없음)
 입력: tests/fixtures/case9_state_compensation_google_docs.pdf
       sha256 f79abba4abe4ffa4fecc273a8fc89ccbccc3a91f3e3259a92a5c4003a8d4df92를 먼저 확인한다
 회차마다:
 2-1 POST {BASE}/api/projects
     JSON {"name":"평가-0311-온라인-m<N>","purpose":"평가 측 온라인 실측","external_ai_policy":"MASKED"} → 201, project id
 2-2 POST {BASE}/api/projects/{pid}/documents (multipart)
     fields: document_kind=BRIEF, is_own_document=true, privacy_ack=true, file=<위 PDF; application/pdf> → 201
 2-3 POST {BASE}/api/projects/{pid}/verify, JSON {"profile":"STANDARD","force":true} → 202, run id
 2-4 GET {BASE}/api/verification-runs/{rid}을 15초 간격으로, 최대 50분 조회한다
     종료 상태: COMPLETED, PARTIAL_COMPLETED, FAILED, CANCELLED. PARTIAL_COMPLETED는 0.31.0에서도 정상이다
 2-5 GET {BASE}/api/verification-runs/{rid}/result(timeout 300초) → 저장소 밖 작업 폴더에 result_m<N>.json으로 저장하고 sha256을 기록한다
 2-6 채점(저장소 루트, 오프라인):
     LV_ALLOW_NETWORK=0 python scripts/score_report.py --report result_m<N>.json --spec tests/fixtures/probes/<명세>.json
     명세 3개: case9_state_compensation_online, case9_state_compensation_rag_controls_online, pipeline_health_online
     각 명세의 '통과' 줄 수와 통과가 아닌 항목의 ID·사유를 적는다

3. 회차별로 뽑을 값(result JSON에서)
 3-1 실행: state, 소요 초, run_manifest.model_execution_summary.calls
 3-2 model_executions 각 항목: purpose, provider, model, ok, cost_status, cost_usd, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, error(앞 120자)
     집계 기준(purpose, model, ok, cost_status):
     ① 건수
     ② 비용 합(REPORTED만)
     ③ drive_rag_advisory·claim_rag_advisory 비용 합
     ④ Sonnet RAG 호출의 cache_read_tokens 합과 cache_read>0 호출 수, cache_write_tokens 합
     ⑤ 실패 호출 목록
 3-3 모델 확인:
     · purpose argument_review_v1에 model gpt-6.2-sol ok=true가 있는가
     · Gemini 호출의 model이 gemini-4-neon이고 ok=true인가
     · Sonnet 5.5가 RAG를 처리하는가
 3-4 documents[0].engine_data.rag:
     · len(unreviewed_drive_sources)
     · claim_coverage.linked_claims
     · claim_coverage.budget의 halt_reason, spent_usd, uncertain_usd, provider_rejected_usd(0.31.1 새 필드)
 3-5 run_manifest.reference_library.diagnostics: elapsed_ms, inventory_mode, reprocess_failed, reprocess_deferred
 3-6 보고서 모델 표시명에 'Gemini 4 Neon', 'GPT-6.2 Sol'이 쓰였는가(문자열 검색, 해당 줄 앞 80자만)

4. U2
 - GitHub Actions 워크플로 live-source-check.yml을 ref main, with_llm=true, strict=true로 실행한다
 - 로그 '판정' 절과 LLM Provider 절을 요약한다(공급자별 모델·OK 여부)
 - U2는 효율 라우팅을 켜지 않으므로 gpt-6.2-sol은 여기서 불리지 않는다. 6.2 Sol 확인은 3-3에서 한다

5. 정리
 - 이 측정으로 만든 프로젝트(이름이 '평가-0311-온라인-'으로 시작)만 DELETE {BASE}/api/projects/{id} → 204
 - GET {BASE}/api/projects?deleted=true로 휴지통에 들어간 것을 확인한다. purge 금지
 - 토큰 파일을 지운다. 결과 JSON은 저장소 밖에 두고 커밋하지 않는다

6. 비교 기준(0.31.0 2차, 같은 입력·명세, docs/scorecards/online_0310_2nd_20261128.md)
 - 점수: 표준 23/23, RAG 5/5, 건강 6/6(3회 모두)
 - 모델 호출: 48~49건, 실패 0
 - 실행당 비용: $1.07~1.11. RAG $1.02~1.05
 - Sonnet cache_read 0
 - Drive 동기화: m1 130초, m2·m3 0.6초
 - 소요: 352~505초
 - 기대(판정 기준은 평가 측이 정함):
   · 점수 유지
   · gpt-6.2-sol·gemini-4-neon 실호출 성공
   · Sonnet RAG 호출 cache_read>0(Drive 대조 2번째 호출부터)
   · RAG 비용 감소(추정 실행당 $0.13~0.20)
   · halt_reason null
   · unreviewed_drive_sources 0

7. 제출(대화 응답으로, 코드 블록 하나)
 (가) 선행 확인 결과(health 판·커밋, 데이터셋 상태 값)
 (나) 회차별 표: 실행 ID, 상태, 소요, 호출/실패, 표준·RAG·건강 점수, 실행당 비용, RAG 비용, Sonnet cache_read 합·적중 호출 수, Drive 동기화 ms, 재처리 실패/연기, halt_reason, provider_rejected_usd
 (다) (purpose, model, ok, cost_status)별 건수·비용 표(3회 각각)
 (라) 모델 확인 3-3·3-6 결과, 실패 호출 목록
 (마) U2 요약과 run 링크
 (바) 정리 결과(DELETE 상태 코드, 휴지통 확인 수)
 (사) 측정하지 못한 것과 이유, 결과 JSON의 sha256 목록
 측정 조건(입력 sha256, 정책 MASKED, 명세 이름, 시각 UTC)을 맨 위에 적는다.
 판정·해석 문구("수용" 등)는 쓰지 않는다.
Agent: codex
```

Agent: evaluator
