# 0.31.1 릴리스 후보 오프라인 판정 (2026-11-28)

**판정: 오프라인 수용 (patch 0.31.0 → 0.31.1).**
- **평가 대상:** `Steve_ACASiaLAW` `c6a48c51`(`#469` 병합)
- **기준:** 운영 `main` `9b30e246`(0.31.0)
- **사용자 지시:** "후보 판정"(2026-11-28)

## 0. 포함 변경
| PR | 티켓 | 내용 | PR 판정 |
|---|---|---|---|
| `#468` | TK-253 | 모델 조정: OpenAI 검토 `gpt-6.2-sol`, Gemini `gemini-4-neon`, 단가 2종, temperature 생략 목록, 표시명 정규식 | [수용](pr_468_verdict_20261128.md) |
| `#469` | TK-254·TK-255 | Anthropic 캐시 지점을 system 블록으로 옮김 + Haiku 5.5 단가 등록. 공급자 거절이 RAG 호출 상한·비용 예산을 소진하던 결함 수정 | [수용](pr_469_verdict_20261128.md) |

- 제품 코드 변경: `config/llm_routing.json`·`providers.json`·`pricing.json`, `llm_router/providers.py`, `report_engine/model_opinions.py`, `rag_engine/review.py`, README.
- **근거 구분:**
  - 평가 측 재실행: `verify_all` 전체 모드(이 SHA에서 1회), 성적표, 은퇴 세트 비교
  - CI 결과 인용: 각 PR 필수 CI 11/11

## 1. 필수 게이트
| 게이트 | 결과 |
|---|---|
| `verify_all` 전체 모드(`c6a48c51`, 기준 `9b30e246`) | 모두 통과. 실패는 전체 시험 5건뿐이다(아래 행) |
| ↳ 시험 | 수용 1,284 통과·실패 0, 원장 2,357 통과·실패 0, 브라우저 200 통과 |
| ↳ 게이트 | 점수 게이트 통과, 회귀 게이트 회귀 없음 |
| ↳ 정적 점검 | 하드코딩 0, 시험 삭제·표시 변경 없음, 보호 경로 변경 없음, 버전 정책 위반 없음 |
| 전체 시험 | **11,712 통과**(0.31.0 후보 11,699 + 이번 신규 시험). 실패 5건은 0.31.0 후보와 같은 컨테이너 환경 요인이고 CI에서는 통과했다: `test_tk127_stage2_drive_pipeline::…[0·10·20]`, `test_tk88_three_tier_review::test_docx_and_pdf_reports_include_three_tier_subheadings`, `test_v5_ocr_dates::test_rotated_scan_page_impossible_date_is_found` |
| 점수(성적표) | `dev` **89.7**(v2 47/56) · `holdout` **87.5**(v2 45/54). 확인 오탐 0, A등급 오탐 0, 기존 방어 유지, 엔진 오류 0. 0.31.0과 같다 |
| 은퇴 5세트(기준 `9b30e246`) | 56.5 · 54.6 · 63.8 · 59.4 · 55.7, 평균 **58.00**. 전 세트 오탐 0, A 0, v2 동일, **후퇴 없음** |
| 열린 P1 이상 회귀 | 0건 |

**측정 조건:** 오프라인(`LV_ALLOW_NETWORK=0`), Linux, **Python 3.13.18**(CI는 3.11, `--allow-env-mismatch`로 실행), tesseract 5.3.4.

## 2. 버전 판정 (VERSION_POLICY 5절)
- **`fixed`(patch):** TK-255. 0.31.0 운영 1차 m3에서 재현된 운영 결함이다(참고자료 33/83 미대조, 주장 대조 COST 중단).
  - 수정본에서 같은 꼴의 합성 시험 3건이 통과한다. 원래 코드에서는 3건 모두 실패한다.
  - 탐침 4종도 기대대로였다.
- **분류 없음:**
  - TK-253(모델 설정): 새 기능이나 화면 변경이 아니다. 보고서의 모델 표시명이 'Gemini 4 Neon'으로 바뀌는 것은 설정값을 그대로 보여 주는 것이다.
  - TK-254(캐시 지점): 비용 개선이며 탐지 성능 변화는 없다(RER 0).
- 따라서 **patch 0.31.1**이다. `rer` 0.0.

## 3. 미측정·배포 뒤 확인
- 격리 봉인 세트: 원격 VM이 없어 NOT_MEASURED.
- 배포 뒤 운영:
  1. `gpt-6.2-sol` 실호출(`openai_review`), Neon 비용·지연
  2. 사용자가 `LV_LLM_PROMPT_CACHING=1`을 설정한 뒤 캐시 적중(`cache_read_tokens>0`)과 RAG 비용 감소(0.31.0 2차 m1~m3 $1.02~1.05 대비)
  3. case9 ×3 표준·RAG·건강 점수 유지
  4. Haiku 5.5 확인 실측([계획](haiku_rag_measurement_plan_20261128.md))
- 공급자 거절 운영 재현은 한도 소진 같은 상황에서만 생긴다(사후 확인).

Agent: evaluator
