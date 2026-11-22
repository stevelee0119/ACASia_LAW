# 설계 메모: TK-234 증거 모순·복제(`EVI-*`), 인젝션(`INJ-*`), AI 잔재(`AIGEN`) 일반화

- **관련 티켓:** `TK-234` (`P1`)
- **작성일:** 2026-11-22
- **원칙:** 사건 고유 값·서면 문구·특정 문구 맞춤 정규식 0건, 대조군·정상 조판 오탐 0건, `dev`/`holdout`/은퇴 세트 동반 개선.

## 1. `EVI-COPY` · `EVI-LOGIC` · `EVI-INCONS` · `EVI-OVR` (`packages/claim_engine/evidence_consistency.py`)
1. **내용어 n-gram(shingle) 및 종결어미 정규화(`EVI-COPY`):**
   - 기존 `_stem_seq` 종결어미·조사 정규화 LCS 비교는 `owner_kind == DOC_KIND_STATEMENT`에만 적용되고, `PLEADING`/`EVIDENCE_EXPLANATION` ↔ `FACT_CONFIRMATION`/`EVIDENCE_ORIGINAL` 복제나 `~했습니다` ↔ `~하였다` 어미 변환, 어절 내 조사 변화가 있을 때 3-shingle 겹침이 누락될 수 있다.
   - 한국어 조사(`은/는/이/가/을/를/에/에서/로/으로/와/과/도/만/의`)와 종결·연결어미(`했습니다/하였습니다/했다/하였다/입니다/이다` 등)를 정규화한 내용어 토큰 열 기반 3-shingle 및 LCS 보조 검사를 `PLEADING`/`EVIDENCE_EXPLANATION` ↔ `FACT_CONFIRMATION`/`EVIDENCE_ORIGINAL` 및 `STATEMENT` 교차 복제에 일반화 적용한다(소송서면 간 정상 재진술 제외, 인용문 제외 유지).
2. **시공간·인지 양립 불가 및 내심 단정(`EVI-LOGIC`, `EVI-OVR`):**
   - `check_statements`에서 단일 문장 내 `LIMITATION_RE + CERTAINTY_RE`뿐 아니라, **인접 문장(전제-결론 창)** 또는 동일 문장 내에서 부재·비지각 조건(`보지 못했`, `그 자리에 없었`, `해외에 있었`, `수면/입원 중`)과 직접 지각·단정(`직접 보았`, `목격`, `분명히`, `틀림없이`)이 양립 불가능하게 충돌하는 경우를 `STATEMENT_BEYOND_PERCEPTION`(C등급)으로 탐지한다.
   - 진술서/일방 작성 문서(`DOC_KIND_STATEMENT`, `DOC_KIND_FACT_CONFIRMATION`)가 객관적 외형·언행 근거 없이 상대방의 내심·동기(`고의로 속이려`, `악의로`, `알면서도 일부러` 등)를 사실처럼 단정하는 경우를 `EVIDENCE_PURPOSE_MISMATCH`/`OVERCLAIM`(C등급, 사람 확인) 참고·의심 신호로 일반화한다(상대방 주장 인용 문맥 제외).
3. **앵커 튜플 충돌(`EVI-INCONS`):**
   - 동일 날짜·주체·항목 앵커에서 금액·수량·장소가 상충할 때 기존 `fact_checks` / `evidence_consistency`의 정규화 누락이 없도록 숫자·단위 정규화를 보강한다.

## 2. `INJ-ZWSP` · `INJ-META` · `INJ-OFFPAGE` (`packages/adversarial_engine/scanner.py`)
- 파서가 감지한 `actual_text_zero_width`, `raw_layers`의 `ZERO_WIDTH`, `OFF_PAGE`, 메타데이터 인젝션 신호가 `Finding`의 `document_id`, `page`, `span`/`evidence.excerpt`, `tags`에 누락 없이 매핑되도록 정규화한다.
- 정상 조판용 단일 ZWSP(`len <= 1`이고 숨겨진 지시문이 복원되지 않은 경우)는 오탐 0건을 유지한다.

## 3. `AIGEN` (`packages/verification_engine/ai_document_detector.py`)
- `len(objective_cats) >= 2`인 복수의 객관적 AI 잔재 동반 문서에서 `verdict`가 `AI_FULL_GENERATION_SUSPECTED` / `AI_PARTIAL_GENERATION` / `UNCERTAIN` 중 어느 것이든, 상위 기여 `suspicious_excerpts` 문단 클러스터의 스팬/발췌와 객관적 잔재 근거 토큰이 `AI_AUTHORSHIP_LIKELY`(`SUSPICIOUS`, `EvidenceGrade.B`) `evidence` 목록에 누락 없이 배출되도록 정밀화한다.
- 객관적 잔재가 0~1종인 사람 작성 대조군에서는 기존 승격 금지(`advisory_only=True`, `UNVERIFIED`)를 유지해 오탐 0건을 보장한다.

## 4. 검증 계획
- 축별 양성 3건 이상·대조군 3건 이상 단위 시험(`tests/unit/test_tk234_evi_inj_aigen_generalization.py`)
- `check_case_literals.py`, `check_hardcoding_diff.py`, `check_train_phrase_overlap.py --eval-sets`, `scorecard.py`, `score_gate.py`, `retired_compare.py`
