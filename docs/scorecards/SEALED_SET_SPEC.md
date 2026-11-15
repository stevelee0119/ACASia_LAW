# 봉인 세트 출제 사양 (U4, 2026-11-14 사용자 승인 'U-1~5 모두 반영')

출제는 저장소를 연결하지 않은 Codex 격리 세션이 한다(AGENT_ROLES). 이 문서는 무엇을 담아야 하는지(구성 요건)만 정한다. 문서 내용·정답은 저장소에 두지 않는다.

## 1. 형식
- 오프라인 채점(`scripts/scorecard.py --sealed-dir`)과 온라인 채점(`scripts/score_sealed_online.py`)이 같은 폴더를 쓴다: `ground_truth.json`, `match_spec.json`, 문서 PDF.
- `ground_truth.json` 문서 키는 파일 이름 앞부분(`SD-01_….pdf` → `SD-01`)과 같아야 한다. 온라인 실행 때 파일 이름을 바꾸지 않는다.
- 결함 항목의 `type`은 채점기 `scripts/eval_testset.py`의 `DEFECT_TYPE_MAP` 키를 쓴다(표에 없는 유형은 채점이 멈춘다).

## 2. 구성 요건(세트 하나 기준)
| 구분 | 요건 |
|---|---|
| 결함 유형 | `DEFECT_TYPE_MAP`의 유형 중 오프라인으로 재현 가능한 것을 각 1건 이상. 법률 인용(CIT-*·LAW-*·SRC-UNV), 문서 일관성(EVI-*), 인젝션(INJ-* 10종 중 4종 이상), AI 작성(AIGEN), 무리한 주장(OVR)은 각 2건 이상 |
| 이번에 더한 유형(2026-11-14) | FOR-META·FOR-HIDDEN·FOR-SIG·FOR-TRACK·RHET·CIT-INT·CALC-INV·DOC-QUAL을 각 1건 이상(평가 체계 감사 F4: 지금까지 어느 세트로도 재지 않던 탐지 유형) |
| 공식 DB 항목 | CIT-NX-DB·SRC-UNV처럼 공식 DB가 있어야 맞힐 수 있는 항목 3건 이상(온라인 봉인 실행에서만 채점) |
| 대조군 | 결함이 없는 대조 문서 1건 이상(정답지 expected PASS), 오탐 함정(FP-TRAP) 5건 이상(정상 인용·정상 법률 서술·정상 하이퍼링크·정상 문서 속성 포함) |
| 개인정보 | 문서마다 가려야 할 개인정보 종류를 `pii_kinds` 목록으로 적는다(예: PERSON·PHONE·ACCOUNT·ADDRESS·DOB·EMAIL). 채점은 종류 단위다 |
| 입력 형식 | 텍스트 PDF 외에 스캔 PDF(OCR) 1건 이상 |

## 3. 확인
- 출제 세션은 위 표의 충족 여부를 숫자로 적어 사용자에게 넘긴다(유형별 건수만, 문장 없음).
- 사용자는 `scorecard.py --sealed-dir` 성적표의 '결함 유형 N종(0건 유형: …)' 줄로 덮는 유형을 확인한다.
