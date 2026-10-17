# 효율적 법률문서 검토 — TK-78 기본 OFF

Codex 전달문 (4)의 ①~⑤를 적용한다. 평가 담당은 **Claude Code 평가 세션**이며,
평가 측 수용은 그 세션의 PR 코멘트 링크로만 인용한다. 이 문서는 구현 설명이며 수용 판정이 아니다.
[기존 평가 코멘트](https://github.com/stevelee0119/ACASia_LAW/pull/128#issuecomment-6241878062)는 보류·보완 요청이며,
최신 사용자 전달문 (4)가 릴리스 포함·기본 OFF·배포 뒤 OFF/ON 비교 순서를 정했다.

## 기본값과 ON 비교 설정

환경변수 미설정은 0.13.0 운영 커밋 `b68cfeec2c5c168a3b9e6e2e92653ea6892521bf`의
모델·호출 구성을 사용한다. `config/providers.json`도 해당 커밋의 값으로 복원했다.

| 항목 | 미설정/OFF 기본 | 사용자 승인 뒤 ON 비교 |
|---|---|---|
| `LV_LLM_EFFICIENT_ROUTING` | `0` | `1` |
| `LV_LLM_CROSS_CHECK` | `all` | `auto` |
| 일반 Anthropic 검토 | Opus 5.5 | Sonnet 5.5 |
| OpenAI 검토 | Luna | 법리 Sol / 작성 정황 Luna |
| Gemini | Gemini 3.8 Flash | Gemini 3.8 Flash |
| 동일 요청 실행 내 재사용 | 꺼짐 | 성공·출력 검사 통과 결과만 재사용 |
| 주장별 RAG 공급자 실패 대체 | 0.13.0 단일 공급자 경로 | 다음 공급자로 대체 시도 |
| `LV_LLM_PROMPT_CACHING` | `0` | `0` 유지 권장; 별도 명시 opt-in |
| `LV_LLM_REVIEW_SAMPLE_PERCENT` | `10` (OFF에서 미사용) | `10` |

OFF에서도 명시한 공급자 모델과 기존 `all/auto/off` 교차검증 선택은 존중한다.
작업별 배치·선택적 추가 의견·중복 요청 재사용·추가 장애 대체는 효율 라우팅 ON에서만 적용한다.
ON만 지정하면 교차검증은 여전히 `all`이다. 호출을 줄이는 비교 구성은 ON과 `auto`를 함께 지정한다.
`auto`를 명시하되 효율 라우팅이 OFF면 0.13.0의 신뢰도·심도·중대도 조건을 유지한다.

ON + auto 법리 검토는 Sonnet과 독립 Sol, 불일치/실패 때 Gemini를 추가한다.
미해결 쟁점에 Opus 참고 의견을 추가하되 기존 충돌 판정이나 증거등급을 승격하지 않는다.
작성 정황은 Luna 우선이며 긍정 판단·메타데이터 신호·표본 대상에 독립 검토를 추가한다.
주장 타당성은 서로 다른 두 공급자의 항목별 완전한 응답을 요구하고 충돌·누락·실패 때 세 번째를 호출한다.

`LV_ANTHROPIC_MODEL`·`LV_OPENAI_MODEL` 등 전역 모델 지정과 관리자 모델 지정은 우선한다.
ON으로 바꿔도 기존 전역 지정이 있으면 작업별 기본 모델이 적용되지 않을 수 있다.
필요하면 `LV_ANTHROPIC_REVIEW_MODEL`, `LV_OPENAI_REVIEW_MODEL`, `LV_OPENAI_EXTRACTION_MODEL`,
`LV_ANTHROPIC_ESCALATION_MODEL`로 단계를 명시한다. 단계별 지정도 효율 라우팅 OFF에서는 사용하지 않는다.
API 키·기존 예산·한국법 프로필은 이 변경으로 수정하지 않는다.

## 기존 대기 작업과 보안 경계

라우팅 필드 7개가 전부 없는 0.13.0 대기 작업은 **실패·수동 재시도 없이 OFF + all**로 실행한다.
현재 worker가 ON이어도 이를 물려받지 않는다. 저장된 공급자·모델·단가·예산 한도·예산 식별자를
유지하며 원본 snapshot/hash를 다시 쓰지 않는다. 현재 네트워크 차단과 조직 정책 제한은 계속 적용한다.
일부 라우팅 필드만 빠진 새 snapshot이나 OCR 등 기존 파서 설정 불일치는 기존처럼 거절한다.

ON 재사용은 입력·모델·역할·정책·schema·출력 한도·metadata가 모두 같을 때만 적용한다.
적중 때도 개인정보/출처·조직 정책·작업 소유권을 검사한다. 실행 시작에 비우고 실패·격리 결과는 저장하지
않으며 최대 256건이다. 재사용은 `cost_status=CACHED`, 비용 0으로 기록한다.
요약의 `external_calls`는 논리 실행 수이며 실제 HTTP 재시도 수나 공급자 청구액과 같다는 뜻은 아니다.

## 단가 출처와 확인 범위

확인일: **2026-10-17 UTC (2026-10-18 한국 시각)**. 단위: USD / 1,000,000 tokens.
직접 Standard API이며 OpenAI는 **Short context** 열이다. Batch/Flex/Fast와 장문 요금은 섞지 않는다.

| 모델/구간 | 입력 | 출력 | 캐시 읽기 | 공시 출처·확인 결과 |
|---|---:|---:|---:|---|
| gpt-6.1-sol | 2.00 | 10.00 | 0.10 | [OpenAI Pricing, Standard / Short context](https://developers.openai.com/api/docs/pricing), 위 확인일 조회로 확인 |
| gpt-6-luna | 0.10 | 0.50 | 0.01 | [OpenAI Pricing, Standard / Short context](https://developers.openai.com/api/docs/pricing), 위 확인일 조회로 확인 |
| gemini-3.8-flash, 2026-12-31까지 | 0.75 | 3.75 | 0.075 | [Gemini 3.8 Flash Pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash), 위 확인일 조회로 확인 |
| gemini-3.8-flash, 2027-01-01부터 | 1.50 | 7.50 | 0.15 | [같은 공시](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash), 시작일 포함 확인 |

Gemini 공시는 `through December 31, 2026` / `starting January 1, 2027`을 명시한다.
출력 요금은 thinking tokens를 포함한다. 코드의 `after_2026-12-31` 전환과 일치한다.
명시 캐시 보관료는 읽기 요금과 별도이며, 이 앱은 Gemini 명시 캐시를 생성하지 않는다.

**Sonnet 캐시 읽기: 공식 0.10 반영(평가 측 지시 정정).**
`claude-sonnet-5-5.cache_read`는 **0.10**이다.
[평가 측 정정](https://github.com/stevelee0119/ACASia_LAW/pull/132#issuecomment-6242393439)에 따라
[Anthropic 공식 가격 페이지](https://platform.claude.com/docs/en/about-claude/pricing)의 입력 단가 2.00의
5%인 0.10을 반영했다. Opus 5.5의 캐시 읽기 단가 0.20과 구분한다.

Claude API prompt cache는 5분 쓰기 방식이며 기본 OFF다. 단발 요청마다 쓰기만 발생하면 비용이 늘 수 있다.
캐시·사고 토큰 정산 개선은 유지하되 사용량이 불완전하면 추정 상태를 유지한다.
장문 요금 적용 여부·공급자 실청구액 일치·실제 절감률은 **미확인/미측정**이다.

## 검증과 릴리스

추가 시험은 OFF의 0.13.0 모델·호출 수·payload, ON 선택, 단가 정산/기간 경계,
기존 대기 작업 완료·예산/설정 보존과 부분 snapshot 거절을 확인한다. 기존 시험은 삭제하지 않는다.
명시 기본 모델 고정성을 보는 기존 시험은 ON을 명시하고 복원된 기본 Luna에 맞춰 검토 작업을 사용하며,
서로 다른 모델 선택·환경 변경 뒤 고정성 검사는 유지한다.

CI 완료 뒤 PR 본문에 `검토 요청`과 head SHA를 적는다. Claude Code 평가 세션이 ①~⑤와 후보 SHA의
`verify_all` 전체 모드 1회를 확인한다. 구현 세션은 평가 측 수용을 기록하거나 Render 벤치마크를 실행하지 않는다.
배포 뒤 사용자가 같은 문서로 OFF/ON의 법리 판단 일치, AI 작성 판별 재현율, 호출 수·실비용,
`max_tokens` 잘림률을 비교한다. **ON 전환은 그 결과를 보고 사용자가 결정한다.**
