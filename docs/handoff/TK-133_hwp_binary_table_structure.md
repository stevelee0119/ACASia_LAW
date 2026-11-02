# TK-133 구형 HWP(바이너리) 표 구조 연결

- 등록: 2026-11-02, 평가 측
- 근거: TK-132 후속(사용자 결정 11-02 'lexdiff 관련 반영까지 구현 뒤 한 번에 릴리스'), TK-132 티켓의 후속 후보 항목
- 배정: Codex 별도 세션(구현 한시 대행 2차, 11-02 사용자 지시)
- 분류: 입력 계층(표 구조 미제공) · 계산·사실 엔진 입력 정확도

## 1. 문제 (Steve `c180db9` 기준)

1. `packages/document_engine/hwp_parser.py`의 `HwpParser.parse`는 `_extract_hwp_text`로 문단 블록만 만든다.
   - `structure["tables"]`를 만들지 않는다.
   - 표를 셀 단위로 복원하는 `_extract_hwp_tables`(`_section_tables`)가 있지만 시험에서만 쓰이고 parse에 연결되어 있지 않다.
2. 그래서 표 소비자(`calculation._verify_cell_tables`·`_verify_percentages`, `table_formulas`, `fact_store`, `claim_amounts`, `attachments`, `evidence_consistency.exhibit_rows`)가 구형 HWP에서는 동작하지 않는다.
3. 셀 문단은 `paragraph_reconstruction`에서 한 문단으로 합쳐진다(평가 측 재현: 표 셀 8개와 표 뒤 문단이 한 블록이 됨). 합계 검산은 그 줄 글자에서 우연히 맞을 때만 동작한다.

## 2. 해결 (평가 측 수정본 `patches/TK-133_hwp_binary_tables_on_c180db9.diff`, 2개 파일 +330/−3)

- 새 함수 `_extract_hwp_table_structures` / `_section_table_structures`
  - 기존 `_extract_hwp_tables`·`_section_tables`는 그대로 둔다(기존 시험 보호).
  - 셀 머리(LIST_HEADER) 주소·병합(colSpan·rowSpan)으로 2차원 표를 만든다. 병합 값은 앵커 칸에만 두고, 덮인 칸은 빈칸이다. `merges`·`covered`를 기록한다.
  - 불완전한 표는 `structure["partial_tables"]`에 넣고 cells는 싣지 않는다. 불완전 조건: 범위 밖 주소·병합, 겹치는 셀, 짧은 셀 머리, 표 안의 표.
  - 상한: 표당 행 2000·열 100, 문서 전체 200,000칸(섹션 사이 누적). 넘으면 경고('상한')를 남기고 표를 만들지 않는다.
- 연결 방식: PDF `LINES_WITH_STRUCTURE`와 같은 계약
  - 표 블록을 새로 만들지 않는다. 셀 글자가 이미 본문 블록에 있으므로, 새로 만들면 중복 표시가 된다.
  - 셀 문단 블록에 `attributes["table_ref"]`를 붙이고, 표에 `line_block_ids`를 기록한다.
  - 그 결과는 다음과 같다.
    - 문단 복원이 셀 문단을 본문과 합치지 않는다.
    - 줄 단위 산식 검산은 그 블록을 건너뛴다(`calculation.py:277·438`).
    - 표 검산(`_verify_cell_tables`)이 한 번만 잡는다. 평가 측 재현으로, 연결하지 않으면 같은 합계 오류가 2건으로 중복된다.
  - 문단 순서 대응(비어 있지 않은 PARA_TEXT 순서)이 본문 문단 수와 다르면 표를 내지 않는다(경고).
  - 표 복원이 예외를 내면 경고만 남기고 본문은 유지한다.
- table_ref는 `hwp_s{섹션}t{순번}`이다. page는 1이다(구형 HWP는 쪽 번호를 신뢰하지 않음, 기존 `page_numbers_reliable=False`).

## 3. 수용 기준

- 새 시험 `tests/test_tk133_hwp_tables.py` 17건이 통과해야 한다. 원래 파서에서는 13건이 실패하고, 대조 4건은 통과한다.
  - 양성: 구조 노출·중복 없음, 셀 문단 연결·표 뒤 문단 분리, 합계 오류 1건(중복 없음), 병합 앵커, 두 섹션 ref
  - 대조: 올바른 합계 무발견, 범위 밖 span, 겹침, 중첩 표, 불완전 표 합계 무발견, 과대·빈 표, 문서 칸 누적 상한, 복원 실패 시 본문 유지, 문단 순서 불일치 시 표 미제공, 표 없는 문서 불변
- 기존 시험(`test_hwp_parser.py` 등)을 수정하지 않는다.
- 고정 점수 변화 0. 고정·은퇴 세트에 HWP 문서가 0건이므로 오프라인 점수 기여도 0이다.
- CI 필수 검사가 모두 성공해야 한다.

## 4. 평가 측 사전 검증 (평가 측 재실행, 저장소 밖 사본)

- `78c9bfd` + 수정본
  - 관련 49개 파일(hwp·계산·표 소비자) 1,510건 통과, 실패 0
  - 고정 dev 82.6 / holdout 81.9 / 오탐 0 / A 0, 점수 게이트 통과
  - 문구 대조 '의심 없음', 하드코딩·시험 수정 점검 통과
- `c180db9`(TK-131·132 병합 뒤)에 그대로 적용(충돌 없음)
  - TK-133·TK-132·HWP·document_engine 시험 통과
  - 문구 대조·하드코딩·시험 수정 점검 통과
- 미검증
  - 실제 한글 프로그램이 만든 HWP의 레코드 수준 분포. 셀 머리가 TABLE과 같은 수준인지 한 수준 아래인지 두 경우 모두 받지만, 실파일로는 확인하지 못했다.
  - 운영 입력 중 구형 HWP 표 비율

## 5. 후속(이번 범위 밖)

- 중첩 표의 안쪽 표 구조 제공. 지금은 바깥 표를 불완전으로 두고 표를 내지 않는다.
- 셀 문단과 본문 문단의 대응을 순서 대신 레코드 위치로 하는 방식
