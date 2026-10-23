# 설계 메모: EVI-COPY 비진술서(32건) 원본 서증 통복제 및 구조적 분별 설계

- **문서 번호:** `requests/84_evi_copy_non_statement_author_design.md` (2026-10-24 3차 불승인 피드백 반영 및 진단 건수 보완 개정)
- **작성일:** 2026-10-17 (1차), 2026-10-20 (2차 보강), 2026-10-21 (3·4차 개정), 2026-10-22 (5·6차 개정), 2026-10-24 (7차: 3차 불승인 요구 ①~④ 반영)
- **작성자:** Antigravity (구현 에이전트)
- **대상 티켓:** 2026-10-19 통합본 B-2 (EVI-COPY 나머지 32건 비진술서 복사 탐지)
- **근거 규정:** 민사소송법 제274조(준비서면의 기재사항), 제355조(문서제출의 방법 등), 민사소송규칙 제106조(증거설명서의 제출)

---

## 1. 불승인(3차, `6f13c6d`) 피드백 분석 및 해결 내역

### (1) 요구 ①: 진술서 경로(`DOC_KIND_STATEMENT`) 결과 Steve 원본과 100% 동일 보장
- **차단 원인 진단 (`sealed_20261008` 46.7 → 36.7, B등급 오탐 5건):**
  - `VerificationPipeline._cross_check`(`packages/verification_engine/pipeline.py` 1524~1533행)는 `confidence_features`의 `sources`와 `differences`로 중복 제거 키(`key = json.dumps([locations, features.get("differences")])`)를 생성한다.
  - Steve 원본에서는 `cross_document_copies`의 진술서(B등급) 결과에 `sources`와 `differences` 필드가 없어 `key = [[], null]`로 단일화되었으나, `7fcd6da`·`6f13c6d`에서 진술서 경로에 `sources`와 `differences`(`owner_other_...`)를 추가하면서 `sealed_20261008`의 `SD-06`(진술서)이 공통 서두 문장을 공유하는 6개 문서(`SD-01`~`SD-05`, `SD-07`)와 각각 별도의 B등급 Finding 6건을 생성하였다. 그중 `SD-03` 1건만 정답(TP)으로 인정되고 나머지 5건이 `SD-06`의 FP-TRAP과 겹쳐 B등급 오탐 5건(-10.0점)이 발생하였다.
- **해결 조치 및 C등급 전용 `sources` 부여 근거:**
  1. **진술서 경로(B등급) 완전 원복:** `owner_kind == DOC_KIND_STATEMENT` 분기에서 `sources`와 `differences` 두 필드를 모두 제거하여 Steve 원본과 100% 동일한 `Finding`을 생성하도록 복원하였다(`sealed_20261008` 46.7점, 오탐 0 즉시 복원 확인).
  2. **비진술서 경로(C등급)에만 `sources: [{"document_id": owner.document_id}]` 부여 (`differences` 미사용):**
     - 만약 C등급에서도 `sources`를 제거하면 모든 C등급 결과와 B등급 결과가 동일한 `key = [[], null]`을 갖게 되어, 한 사건 묶음 내에 여러 비진술서(`소장`, `준비서면`, `증거설명서`, `의견서`)와 `진술서`가 함께 있을 때 `_cross_check`에서 첫 번째 문서의 결과 1건만 남고 나머지 서면의 결과가 전부 소실된다.
     - 반대로 `differences`에 `other_id`나 문장을 넣으면 동일 `owner` 서면에서 다수 Finding이 발생할 위험이 있다.
     - 따라서 C등급에만 `"sources": [{"document_id": owner.document_id}]`를 두고 `"differences"`는 두지 않음으로써, **`owner` 서면당 최대 1건의 C등급 결과만 생성**되면서도 서로 다른 `owner` 서면(`SD-0x03T`~`SD-0x06T`)과 진술서(`B등급`)가 충돌 없이 공존하도록 하였다.
     - 이를 검증하는 실패 방지 시험 `test_c_grade_sources_preserve_multiple_owners_in_pipeline`을 `tests/test_evi_copy_non_statement.py`에 추가하였다.

---

### (2) 요구 ②: 첫머리 표제 조건별 train 32건 및 은퇴 09·10(3항목) 탈락 건수 진단
`6f13c6d`에서 `train EVI-COPY`가 `20 → 4/40`으로 떨어져 목표 효과가 0이 된 원인을 조건별로 분리 진단한 결과는 다음과 같다.

| 탈락 조건 (6f13c6d의 `_document_title_kind` 제약) | train 비진술서 32건 중 탈락 건수 | 은퇴 09·10 (3항목) 중 탈락 건수 | 원인 상세 |
|---|:---:|:---:|---|
| **조건 A: `build_reading_text(doc).text`만 검사 (`1쪽 running_head` 누락)** | **32 / 32건**<br>(4세트 × 8항목 전수) | **2 / 3건**<br>(은퇴 09 `SD-06`, `SD-07`) | 다쪽 PDF의 1쪽 최상단 제목 줄은 `mark_running_heads`에 의해 `block_type="running_head"`로 분류되어 `build_reading_text(doc).text`에서 제외됨. `text[:600]`만 검사하면 1쪽 머리글에 위치한 문서 제목(`사실경위서`, `소장`, `준비서면`, `증거설명서`, `의견서`)을 전혀 볼 수 없어 전부 `OTHER`로 탈락함. |
| **조건 B: 행 길이 `len(stripped) > 30` 일괄 배제 및 줄 끝(`$`) 단독 일치 강제** | **32 / 32건**<br>(관리번호·부제목 병기 시) | **3 / 3건**<br>(은퇴 09 2건 + 은퇴 10 1건) | 머리글/첫 줄에 `SD-0x \| 제목 ― 사건명/부제목` 또는 `제목 관리번호 SD-0x / ...` 형태로 부제목(길이 35~55자)이 함께 적힌 경우 `len > 30` 및 `$` 종단 조건에서 전부 탈락함. |
| **조건 C: 은퇴 09·10의 3항목 문서 성격 분석 (진술서 확장 vs 비진술서 서증 복제)** | 해당 없음 (train 32건은 모두 원본이 `사실경위서`) | **3 / 3건** | - **은퇴 09 `SD-06` (1항목):** `진술서 ― 현장 관찰 경위...` ↔ `SD-02`(`소장`). 원본이 `사실경위서`가 아니라 `소장`이며, `SD-06`은 부제목이 붙은 **진술서**임.<br>- **은퇴 09 `SD-07` (1항목):** `증거설명서 ― ...` ↔ `SD-03`(`답변서`). 원본이 서증(`사실경위서`)이 아니라 **소송서면(`답변서`)**임.<br>- **은퇴 10 `SD-06` (1항목):** `SD-06 \| 현장 진술서 및 증거설명서` ↔ `SD-04`(`고소장`). 원본이 `고소장`이며 `SD-06`은 복합 표제 문서임.<br>→ 2차 판정 요구 ①(`STATEMENT_HEADING_RE` 원복)과 요구 ③(증거설명서는 원본이 서증일 때만)을 엄격히 준수하면 은퇴 09·10의 위 3항목은 B-2(원본이 `사실경위서`인 비진술서 복제) 대상이 아니므로 건드리지 않는 것이 맞음(억지로 포함하려다 `7fcd6da`에서 은퇴 08 오탐 17건 발생). |

- **개선 조치:**
  - `_document_title_kind`에서 **`doc.pages[0].blocks[:5]`(1쪽 상단 `running_head` 및 첫 문단 블록)의 줄들을 함께 검사**하도록 복원하여 조건 A로 인한 train 32건 탈락을 해소하였다.
  - 표제 정규식(`_EVIDENCE_EXPLANATION_TITLE_RE`, `_FACT_CONFIRMATION_TITLE_RE`, `_PLEADING_TITLE_RE`)에서 앞쪽의 문서 관리기호(`SD-0x |`)와 뒤쪽의 구분자·부제목(`― ...`, `/ ...`, `관리번호 ...`)을 허용하되, 목록 줄(`_HEADING_LIST_ITEM_RE`), 경찰 계급 직위(`_HEADING_JOB_TITLE_RE`), 복합 편철 안내문(`편철 확인서`, `제출자료 편철 및 표기 설명서`)은 철저히 배제하여 조건 B 탈락을 해소하면서 오탐 0건을 유지하였다.

---

### (3) 요구 ③: 경위서 한정 어휘(`FACT_CONFIRMATION`)가 덮는 train 건수 진단
- **설정된 `FACT_CONFIRMATION` 어휘 범위:** `사실경위서`, `사건경위서`, `사고경위서`, `경위서` (자간 공백 허용).
- **train 커버리지 진단:**
  - TK-76 진단 메모(`requests/82_tk76_focus_types_diagnosis.md` 4절) 및 B-2 전수 매핑에서 확인된 바와 같이, train 말뭉치 4개 세트(`SD-01`~`SD-04`)의 EVI-COPY 총 40건은 다음과 같이 구성된다:
    - 진술서(`SD-0x02T`) ← 사실경위서(`SD-0x07T`): **8건** (#118 진술서 경로 관할)
    - 소장(`SD-0x03T`) ← 사실경위서(`SD-0x07T`): **8건**
    - 준비서면(`SD-0x04T`) ← 사실경위서(`SD-0x07T`): **8건**
    - 증거설명서(`SD-0x05T`) ← 사실경위서(`SD-0x07T`): **8건**
    - 의견서(`SD-0x06T`) ← 사실경위서(`SD-0x07T`): **8건**
  - 즉, 비진술서 대상 **32건 전수(32/32건, 100%)**에서 복사 원본(Source) 서증은 **`사실경위서`(`SD-0107T`, `SD-0207T`, `SD-0307T`, `SD-0407T`)**이다.
  - 다만 각 비진술서 문서(`SD-0x03T`~`SD-0x06T`, 총 16개 문서) 안에는 `#7` 항목과 `#8` 항목 **2개씩**의 EVI-COPY 정답 항목이 존재한다. `cross_document_copies`는 문서 쌍(`owner` ↔ `other`) 단위로 1개의 `Finding`을 생성하고 `matched[:5]`에 일치 문장들을 담으므로, 한 비진술서 문서당 1개의 C등급 `Finding`이 생성되어 각 문서의 두 항목 중 대표 항목을 맞추게 된다(`7fcd6da` 실측 기준: 진술서 4건 + 비진술서 16개 문서 × 1건 = **20/40건**, 즉 비진술서 16개 대상 문서 전수에서 누락 없이 탐지 작동).

---

## 2. 핵심 설계 및 구조적 분별 기준 요약

1. **공용 `STATEMENT_HEADING_RE` 및 진술서 경로 완전 불변 (요구 ①):**
   - `STATEMENT_HEADING_RE = re.compile(r"(?:^|\n)\s*(?:진\s*술\s*서|사\s*실\s*확\s*인\s*서|확\s*인\s*서)\s*(?:\n|$)")` 유지.
   - `owner_kind == DOC_KIND_STATEMENT` 결과에서 `sources`·`differences` 필드를 제거하여 Steve와 100% 동일 출력 보장.
2. **첫머리 표제 판별 (`_document_title_kind`, 요구 ②):**
   - 1순위: `_statement_start(doc, text)` (Steve 원본 100% 동일).
   - 2순위: 1쪽 상단 블록 5개(`doc.pages[0].blocks[:5]`, `running_head` 포함) 및 `text[:600]` 상단 15줄에서 목록 줄(`_HEADING_LIST_ITEM_RE`), 직위 낱말(`_HEADING_JOB_TITLE_RE`), 일반 서술문(80자 초과 또는 종결 어미/구두점)을 배제한 뒤 전용 표제 정규식(`_EVIDENCE_EXPLANATION_TITLE_RE`, `_FACT_CONFIRMATION_TITLE_RE`, `_PLEADING_TITLE_RE`)으로 분류.
3. **증거설명서 및 소송서면 판정 요건 (요구 ③):**
   - `owner_kind in (DOC_KIND_PLEADING, DOC_KIND_EVIDENCE_EXPLANATION)`이고 **`other_kind == DOC_KIND_FACT_CONFIRMATION`일 때만** C등급(`SUSPICIOUS`)으로 판정.
   - 증거설명서는 `_is_in_corresponding_exhibit_entry`를 통해 표 셀 내부 또는 250자 내 호증 설명 표지(`입증취지`, `서증의 표시`, `갑/을 제X호증`) 안의 정상 기재를 제외하고 **호증 항목 밖**만 판정.

---

## 3. 시험 및 수용 기준 검증 결과 (요구 ④)

1. **단위 시험 (`tests/test_evi_copy_non_statement.py`, `tests/test_copy_statement_heading.py`):**
   - 표제 분류(1쪽 `running_head` 및 부제목 포함), 합성 양성 4건, 대조군 음성 8건, 진술서 경로 Steve 불변 시험(`sources`·`differences` 미포함 검증), C등급 전용 `sources` 다중 문서 보존 시험(`test_c_grade_sources_preserve_multiple_owners_in_pipeline`) 등 총 29개 시험 전수 통과.
2. **은퇴 4세트 및 고정 세트 검증:**
   - `sealed_20261008`: **46.7점, 오탐 0, EVI-COPY 1.0 (1/1)** (Steve 기준 완벽 복원, B등급 오탐 5건 완전 해소).
   - `sealed_20261008b`: **40.7점, 오탐 0** (회귀 0).
   - `sealed_20261009`: **48.3점, 오탐 0** (회귀 0).
   - `sealed_20261010`: **38.9점, 오탐 1(기존 A등급 1)** (회귀 0).
   - `dev` (82.6, 오탐 0) · `holdout` (81.9, 오탐 0) 기준선 완벽 유지.
