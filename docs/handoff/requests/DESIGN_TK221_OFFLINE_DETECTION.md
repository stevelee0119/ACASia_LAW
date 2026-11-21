# [설계 메모] TK-221 오프라인 논리·증거 모순, 메타 교차검증 및 AI 작성 신호 개선

- **작성일**: 2026-11-21 · **작성자**: `Agent: implementer` · **대상 티켓**: `TK-221` (P1)

## 1. 목적 및 대상 축
`dev 82.6` · `holdout 81.9` · 은퇴 5세트(`53.3/48.6/56.9/45.8/34.1`)의 정체를 해소하기 위해, 외부 네트워크 조회 없이(`LV_ALLOW_NETWORK=0`) 결정론적으로 검증 가능한 다음 5개 축을 일반화 설계로 개선한다(`EXTERNAL_SOURCE_REQUIRED` 항목은 제외).

1. **`ClauseNormalizer` 기본 승격**: `LV_CLAUSE_NORMALIZER_MODE` / `LV_USE_CLAUSE_NORMALIZER` 기본값을 `shadow` → `default`로 승격(사전 측정: `dev 82.6`, `holdout 81.9`, 오탐 0, 회귀 0 확인).
2. **`CIT-META` 결정론적 메타 교차검증 보강 (`packages/legal_engine/citation_format.py`, `verifier.py`)**:
   - **문서 내 동일 사건번호 자기모순**: 같은 문서에서 동일 정규화 사건번호(`canonical_case_number`)를 2회 이상 인용하면서 서로 다른 선고일 또는 서로 다른 법원 계열을 기재한 경우 `CASE_METADATA_MISMATCH`(Grade B)로 탐지(단, 원심·항소심·환송전 병기 문맥 제외).
   - **재판유형–사건부호 불일치(`FMT.TRIAL_KIND_MISMATCH`)**: 결정 전용 부호(`헌가·헌나·헌마·헌바·마·모·라·로·카합·카단` 등)에 `판결`/`선고`를 붙이거나 본안 판결 전용 부호(`다·도·두·누·나·노·가합·가단·고합·고단` 등)에 `결정`을 붙인 경우 형식 위반으로 탐지.
3. **`EVI-LOGIC` 정밀화 (`packages/claim_engine/evidence_consistency.py`)**:
   - TK-151에서 일반 목격 진술 오탐으로 비활성화된 L1(`_l1_enabled`)을 대체하여, **명시적 부재·불능 표지**(현장 부재·불참·입원·해외 체류·출국·수감·구금)와 같은 시점의 직접 지각(`직접 목격/청취`)이 결합된 경우만 `STATEMENT_BEYOND_PERCEPTION`으로 탐지(일반 체재 진술 제외).
   - `Legal Evidence Graph`(`analyzer.py`)의 `broken_authority_chains` / `unsupported_fact_elements` 구조 신호와 연계.
4. **`EVI-OVR` / `EVI-COPY` 구조적 보강 (`packages/claim_engine/evidence_consistency.py`)**:
   - `EVI-OVR`: 직접 증명 구조(`is_direct_proof`)에서 객관적 한계를 초과한 단정(자기 측 진술확인서로 상대방 내심·고의 또는 자기 측 의무 이행을 직접 입증한다고 단정하는 등)의 등급·상태 정합성 보강.
   - `EVI-COPY`: 문서 유형 분류(`DOC_KIND_*`)에서 표제/본문 신호 보완 및 동일 문단 복제 탐지 누락 구간 점검.
5. **`AIGEN` 오프라인 복합 신호 보강 (`packages/verification_engine/ai_document_detector.py`, `packages/forensic_engine/residual.py`)**:
   - 미치환 플레이스홀더·AI 응답 잔재 패턴 보강 및 `stylometry_alert` + `heavy_listing` + 다수 문체 신호(`style_hits >= 2`) + 메타데이터/인용 클러스터 복합 정황 시 `AI_PARTIAL_GENERATION` 판정 보강.

## 2. 과탐 통제 및 시험 계획
- **불변식**: 확인 오탐 0건, A등급 오탐 0건, 대조군/FP-TRAP 오탐 0건 유지, 은퇴 5세트 후퇴 0건, 사건 고유 값·서면 문구 하드코딩 0건.
- **단위 시험**: 개선 축마다 서로 다른 일반화 양성 3건 이상 + 대조군(정상 목격 진술, 원심·상고심 병기, 상대방 작성 서증, 정상 법률 서면 등) 3건 이상 작성 및 `score_gate.py` 통과 확인.
