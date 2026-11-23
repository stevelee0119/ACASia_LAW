# 설계 메모: `0.28.0` 과제 1 — 은퇴 5세트 미탐 분해 및 구조적 일반화 개선

- **관련 과제:** `0.28.0` 트랙 `[과제 1]`
- **작성일:** 2026-11-22
- **원칙:** 사건 고유 값·서면 문구 10자 이상·특정 세트 맞춤 정규식 0건, `dev`/`holdout` 회귀 0, 확인·A등급 오탐 0.

## 1. 은퇴 세트 결함 유형별 미탐·미판정 분포 (리터럴 배제 집계)
- **`sealed_20261025` (37.5):** `MISS` `EVI-NUM`(3), `CIT-FAB-Q`(2), `OVR`(2), `CIT-MIS`(2), `AIGEN`(2), `EVI-OVR`(2); `PARTIAL` `LAW-MIS`(3), `CIT-NX`(2), `LAW-NX`(2)
- **`sealed_20261010` (51.9):** `MISS` `EVI-INCONS`(5), `OVR`(4), `EVI-OVR`(3), `EVI-FORM`(3), `AIGEN`(2), `EVI-DATE`(2); `PARTIAL` `LAW-MIS`(2)
- **`sealed_20261008b` (54.6):** `MISS` `OVR`(4), `AIGEN`(3), `EVI-INCONS`(3), `CIT-MIS`(2), `EVI-NUM`(2), `EVI-OVR`(2), `EVI-COPY`(2); `PARTIAL` `LAW-MIS`(4)
- **`sealed_20261008` (56.5):** `MISS` `EVI-INCONS`(5), `OVR`(3), `EVI-OVR`(3), `CIT-FAB-Q`(1), `EVI-DATE`(1), `EVI-NUM`(1), `EVI-FORM`(1), `AIGEN`(1); `PARTIAL` `LAW-MIS`(3)

합계 상위 미탐·부분점수 축은 **`OVR`(13) + `LAW-MIS`(12 partial)**, **`EVI-INCONS`(13) + `EVI-NUM`(6)**, **`EVI-OVR`(10)**이다.

## 2. 구조적 일반화 개선안
1. **`OVR` / `LAW-MIS` (`packages/legal_engine/claim_review.py`):**
   - `ClauseNormalizer`의 조건절(`CONDITION`)·단서절(`EXCEPTION_PROVISO`)·양보절(`CONCESSION`) 부재 및 주절 절대 양태(`MANDATORY`/`무조건`/`당연히`/`자동으로`/`예외 없이`) 구조 검사에, 법리상 복수 요건·재량·비례성·절차가 필수인 일반 법리 범주(계약 해제·해지의 최고/귀책, 징계·해고의 정당한 이유/비례, 행정처분의 재량/이익형량/중대·명백, 신의칙·권리남용, 부당이득·원상회복, 시효중단)를 추가한다(인용 귀속 문맥 제외).
2. **`EVI-OVR` (`packages/claim_engine/evidence_consistency.py`):**
   - 일방 작성 문서·단편적 정황 자료(`진술서`, `사실확인서`, `견적서`, `내용증명`, `영수증`)만으로 다툼 있는 법적 요건(`인과관계`, `고의`, `과실`, `위법성`, `소유권`, `손해액`)이 곧바로/완전히 증명된다고 단정하는 입증취지 과장 구조를 `EVIDENCE_PURPOSE_MISMATCH`(`C등급`, 사람 확인)로 일반화한다(상대방 주장 인용 문맥 제외).
3. **`EVI-INCONS` (`packages/claim_engine/evidence_consistency.py`):**
   - 동일 문서 내 동일 주체/서증(`갑 제N호증`/`을 제N호증`)에 대해 서로 다른 금액·비율·일자가 충돌하는 경우 교차 검증을 보강한다.

## 3. 정량 목표
- `dev` ≥ `86.2`, `holdout` ≥ `86.6` (회귀 0)
- 은퇴 5세트 평균 `51.48 → 55.0+` (특히 `sealed_20261025` `37.5` 및 `sealed_20261010` `51.9` 상승)
- 확인 오탐 `0`, A등급 오탐 `0`, 하드코딩/문구 중복 `0`
