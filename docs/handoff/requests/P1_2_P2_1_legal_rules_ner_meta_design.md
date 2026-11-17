# P1-2 & P2-1 설계 메모: 현행 기본 실정법 판정 정합화 · 무리한 법리 주장 4종 독립 탐지 · 인용 경계/NER/부록 메타표 격리

## 1. 목적 및 배경
- **대상 브랜치**: `feat/p1-2-p2-1-legal-rules-ner-meta` (기준: `origin/Steve_ACASiaLAW`)
- **과제 범위**: `P1-2`(기본 실정법 `temporal_pending` 과다 보류 및 `ai_hallucination_table` 오염 해소 + 무리한 법리 주장 4종 독립 탐지) 및 `P2-1`(법령/행정규칙 인용 경계 파싱, 한국어 법률 NER 불용어 연동, 부록/체크리스트 메타표 격리).

---

## 2. P1-2a: 현행 기본 실정법 `VERIFIED_PROVISION` 정합화 및 대조표 오염 방지

1. **판례 요약본 판정(`is_summary_only`) 범위 한정 (`packages/legal_engine/argument_validity_verifier.py`)**
   - 현행 코드에서 `has_official and not full_text`는 판례 전문(`full_text`) 여부를 기준으로 요약본 한계를 표시하나, 국가법령정보 법령·행정규칙 레코드는 본질적으로 `articles`/`provisions` 구조이며 `full_text` 키가 없다.
   - `CitationType.STATUTE` 및 `CitationType.ADMIN_RULE`에는 `is_summary_only`를 적용하지 않고, `has_official` 여부를 항목 dict에 명시해 루프 변수 누수를 차단한다.
   - `STATUTE`/`ADMIN_RULE` 인용이 `VERIFIED` 또는 `VERIFIED_PROVISION`이고 오류·불일치·취지 왜곡이 없으면 `ai_hallucination_table` 미확인 목록에 포함하지 않는다. `UNCONFIRMED_SOURCE_LIMIT` 문구도 법령/판례 유형별로 분기한다.

2. **자동 추정 기준일(`inferred_reference_applied`) 적용 실정법 승격 (`packages/verification_engine/pipeline.py`)**
   - `context.case_date`가 미입력인 상태에서 문서 날짜로 기준일을 자동 추정(`inferred_reference_applied=True`)한 경우, 대다수 현행 법령의 부칙·경과조치로 인해 `levels["temporal"] == "UNVERIFIED"`가 되고 `as_of`가 비어 있지 않아 `PARTIALLY_VERIFIED`에 머무른다.
   - `temporal_review` 단계가 완료된 뒤, 사용자가 `case_date`를 명시하지 않았고(`inferred_reference_applied=True`) 해당 조문이 존재(`existence="VERIFIED"`), 조문 일치(`article="VERIFIED"`), 본문 대조 완료(`content in ("VERIFIED", "NOT_ASSERTED")`)이며 `temporal_review` 또는 `TEMPORAL_LAW_MISMATCH`/`LAW_CITATION_ERROR`로 과거 시점 쟁점이 지적되지 않은 경우에 한해 `provision_label(..., as_of=None)` 규칙에 따라 `VERIFIED` / `VERIFIED_PROVISION` 및 `CURRENT_VERSION_ADVISORY`로 승격하고 `component_summary`를 재집계한다.
   - 직접 호출되는 `verify_statute(..., as_of=...)`, `verify_citations(...)`, `provision_label(..., as_of=...)`의 기존 계약은 변경하지 않는다.

---

## 3. P1-2b: 무리한 법리 주장 4종 독립 탐지 (`claim_review.py` + `config/legal_rules/rules.json`)

각 규칙은 **다중 문맥 신호 + 극성(`_CLAIM_SPANS` / `_author_asserts`) + 예외/단서 제외**를 결합하여 단정적 작성자 주장만 탐지하며, `rules.json`의 공식 조문 원문을 근거로 연결한다.

1. **`LIMITATION_PERIOD_DISTORTION` (소멸시효 기간 왜곡)**
   - 일반 채권·손해배상·계약 청구권의 소멸시효를 법정 기간(민법 제162조 10년·제766조 3년/10년)을 넘는 비정상 장기(11년 이상, 20년·30년 등, 소유권 이외 재산권 제외) 또는 영구 불완성으로 단정하는 주장을 탐지한다. 시효 중단·정지·취득시효·공소시효·징계시효 문맥은 제외한다.
2. **`CIVIL_CRIMINAL_STANDARD_CONFUSION` (민·형사 입증책임·무죄추정 혼동)**
   - 비형사 절차(`not criminal_doc`)에서 민사·배상·계약·징계 책임을 부정·기각하기 위해 형사절차 원칙인 무죄추정(헌법 제27조 제4항) 또는 합리적 의심 배제 기준을 적용해야 한다고 단정하는 주장을 탐지한다. 형사·민사 증명정도의 차이를 설명하는 대조 문맥은 제외한다.
3. **`LOWER_COURT_STATUTE_INVALIDATION` (하급심의 법률 효력 폐지 주장)**
   - 지방법원·고등법원·일반 하급심 법원이 법률·법조항을 위헌으로 직접 폐지·실효시켰거나 효력을 소멸시켰다고 주장하는 경우를 탐지한다(헌법 제107조·제111조). 위헌법률심판 제청·명령·규칙 심사·헌법재판소 결정 서술은 제외한다.
4. **`UNILATERAL_CONTRACT_MODIFICATION` (계약 일방 변경·증액 주장)**
   - 계약상 조정 조항·합의·법정 근거 없이 일방적 통보·통지만으로 또는 상대방 동의 없이 계약금액·조건·대금을 증액(예: 배수·백분율 인상)·변경할 효력이 있다고 단정하는 주장을 탐지한다(민법 제105조·제543조). 합의·특약·물가변동·법정 증감청구 근거가 동반된 경우는 제외한다.

---

## 4. P2-1: 인용 경계 파싱 · 한국어 법률 NER 불용어 · 부록/체크리스트 메타표 격리

1. **법령·행정규칙 인용 경계 보정 (`normalize.py`, `citation_extractor.py`)**
   - `citation_extractor.py`의 `ADMIN_RULE` 분기에서 `m.start()` 대신 계산된 `start`를 사용해 선행 부사·지시어 조각이 `raw_text`와 `span`에 포함되지 않도록 수정한다.
   - `LAW_NAME_PREFIX_NOISE`에 범위·정도 부사어(`최소한`, `적어도`, `단지`, `단순히`, `불과`, `결국`, `즉`, `가령`, `예컨대` 등)를 추가한다.
   - `law_name_suffix`에서 단일 어절 내 공백 없이 붙은 주격·목적격·보조사(`은/는/이/가/을/를`)를 분리하되, 사전에 등록된 정식/약칭 법령 및 복합명사(`국가배상법`, `지방계약법` 등)는 절대 분절하지 않고, (a) 뒷부분이 기등록 공식/주요 법령명이거나 (b) 앞부분이 명확한 주어·행위 명사 + 조사(`은/는/을/를`) 구조인 경우에만 분리한다.

2. **한국어 법률 NER 불용어 연동 (`packages/claim_engine/extractor.py`)**
   - `packages/pii_engine/detector.py` 및 `name_stopwords.py`의 `PARTY_HEADER_STOPWORDS`, `REPRESENTATIVE_NAME_STOPWORDS`, `PERSON_CATEGORY_STOPWORDS`, `MILITARY_NOUNS` 및 `_CATEGORY_JOSA_TAIL_RE`를 재사용하고, 당사자 접미 표현(`측에/측은/...`) 및 관형형·서술형 어미(`하는/되는/있는/없는/위해/위반/...`)가 붙은 비인명 토큰을 `is_person_name`에서 제외한다.
   - `COMPANY_CONTEXT_RE` 처리 시 법인명 앞 일반 수식어(`민간`, `공공`, `기존`, `신규`, `당해`, `해당`, `외국`, `국내`, `관련`, `특정` 등)를 건너뛰고 뒤쪽 실체 상호(`주식회사 OOO`)만 추출하도록 보완한다.

3. **부록/체크리스트 메타표 격리 (`packages/document_engine/meta_sections.py` + `claim_engine` + `citation_extractor.py`)**
   - 부록·체크리스트 제목 및 2개 이상 평가·검증 열 표지(`테스트 항목`, `검증 항목`, `기대 결과`, `합격 기준`, `체크리스트`, `오류 유형` 등)를 구조적으로 식별한다.
   - 메타표·부록 구간은 주장 분류에서 `ClaimType.DOCUMENT_META`(`verification_target=False`)로 격리하고, 인용 추출(`extract_citations`)·개체 추출(`extract_entities`)·사건 추출(`extract_events`) 대상에서 제외한다. 일반 서증 목록(`exhibit_rows`)과 사실·금액 계산표는 영향받지 않는다.
