# TK-132 HWPX 표 구조 미보존과 표 텍스트 중복 수집 (설계 메모 먼저)

- 등록: 2026-11-02, 평가 측. 출처: Astra 평가(11-02). 평가 측이 재현했다.
- 배정: Antigravity. 순서: TK-131과 함께 측정한 뒤 착수 순서를 정한다.

## 확인한 사실 (Steve `debbe83`)

1. `packages/document_engine/hwp_parser.py` `HwpxParser.parse`(22행~)
   - 모든 `p` 요소를 `root.iter()`로 돌면서, 각 `p`의 하위 `t`를 전부 이어 붙인다.
   - 표(`tbl/tr/tc`)·셀 주소·병합을 해석하지 않는다. `structure["tables"]`도 만들지 않는다.
   - 표 추출은 구형 HWP(`_extract_hwp_tables`, 245행)에만 있다.
2. **재현(합성 HWPX: 본문 1문단 + 2×2 표)**
   - 결과: 보이는 텍스트가 `'본문 앞 항목금액위자료1,000,000 항목 금액 위자료 1,000,000'`이다.
   - 원인: 표를 감싼 바깥 `p`가 셀 텍스트를 한 번 이어 붙이고, 셀 안 `p`가 다시 한 번씩 수집한다.
   - 결과적으로 금액이 두 번 들어가고 `tables`는 없다.
3. 계산·사실·증거 엔진은 이미 `doc.structure["tables"]`를 소비한다(`calculation.py:353·502`, `table_formulas.py:202`, `fact_store.py:247`, `evidence_consistency.py:302`). 그러나 HWPX 입력에서는 이 경로가 비어 있다.

## 요구(설계 메모의 항목)

- namespace·local-name 기준으로 `tbl/tr/tc`, `cellAddr`, `cellSpan`을 해석한다. 각 텍스트를 한 소유자(문단 또는 셀)에 한 번만 배정한다.
- 기존 `structure["tables"]` 계약(`cells` 2차원 배열, `table_ref`)에 병합 anchor와 covered 관계를 더한다. 병합 값을 복제하지 않는다.
- 섹션 순서: manifest/spine을 우선한다. fallback은 숫자 순으로 정렬한다(`section10`이 `section2` 앞에 오지 않게).
- 자원 상한: 행·열·span·중첩 깊이를 검증한 뒤 할당한다. 손상된 구조는 부분 파싱으로 처리하고 사유를 남긴다.
- 이 변경은 탐지 결과를 바꾼다(계산 엔진 소비). 점수 하락 게이트, 은퇴 세트 비교, 릴리스 후보의 verify_all 전체 실행이 필요하다.
- 고정 벤치마크에 HWPX 시료가 0건이다. 그래서 합성 시험(병합·빈 셀·중첩·숫자 섹션 순서·합계 정오·표 안 인용·숨은 지시문)이 수용 근거가 된다.

## 측정

- 운영 입력 중 HWPX 비율과 표 포함 비율을 센다.
- 평가 측은 운영 데이터에 접근할 수 없다. 측정값이 없는 상태다.

## 2판(11-02): 설계 메모 대신 평가 측 사전 검증 수정본

- **수정본:** `patches/TK-132_hwpx_tables_on_76f5fbb.diff` (2개 파일, +264/−4)
- **`HwpxParser.parse` 변경**
  - 섹션 순서는 manifest(content.hpf) spine을 먼저 따르고, 없으면 숫자 순으로 정렬한다.
  - 표 안에 있는 문단은 본문 문단에서 뺀다.
  - 문단 글자는 그 문단에 직접 딸린 글자만 모은다(사이에 표가 끼면 뺀다).
  - `_hwpx_tables`가 cellAddr·cellSpan으로 2차원 표를 만든다. 병합 값은 앵커 칸에만 두고 덮인 칸은 빈칸으로 둔다.
  - 표마다 `merges`·`covered`·`nested`·`parent_table_ref`·`complete`를 기록한다.
  - 상한: 행 2000·열 100·중첩 깊이 4. 범위 밖이거나 겹치는 셀은 빼고 `complete=False`와 경고를 남긴다.
  - `structure["tables"]`와 표 블록(block_type `table`, `table_ref`)을 PDF 표 계약과 같은 꼴로 만든다.
- **사전 검증(76f5fbb + 수정본, 평가 측 재실행)**
  - 새 시험 10건 통과. 원래 파서로 되돌리면 8건이 실패한다.
  - 표 합계 오류를 `parse_document` → `CalculationEngine` 실제 경로의 표 행 검산이 잡는다(`table_ref` `hwpx_s0t0`). 예전에는 중복된 줄 글자에서 우연히 잡혔다.
  - 관련 37개 파일 + acceptance + regression 4,503건 실패 0. 고정 점수 변화 0. 문구 대조 통과.
- **같은 결함 유형(후속 후보, 이번 범위 밖):** 구형 HWP 파서는 `_extract_hwp_tables`(245행)로 표를 뽑지만 `structure["tables"]`에 연결하지 않는다. 시험만 이 함수를 부른다.
