# 티켓 지표

`python scripts/ticket_metrics.py`가 만든다. 손으로 고치지 않는다. 상태는 `ticket_registry.json`(평가 측 갱신)을 따른다.
티켓 번호는 발견한 문제 수다. 해소 여부·회귀(구현 수정이 새로 만든 결함)·재발은 아래처럼 따로 센다.

- 전체 75건 · 회귀 24건 · 미해결(open·accepted·merged·known_open) 5건
- 상태별: open 4 · accepted 0 · merged 0 · known_open 1 · deployed 70 · closed 0
- 해소일(deployed_on·closed_on)은 2026-10-10 이후 기록분만 있다. 그 전 해소 건은 날짜 미상이라 주간 해소 수에 들어가지 않는다.

## 주별
| 주(ISO) | 발견 | 그중 회귀 | 회귀 비율 | 재발 | 배포로 해소 | 배포 없이 닫힘 |
|---|---|---|---|---|---|---|
| 2026-W40 | 59 | 21 | 36% | 0 | 0 | 0 |
| 2026-W41 | 16 | 3 | 19% | 0 | 9 | 0 |

## 일별 발견
| 날짜 | 발견 | 그중 회귀 |
|---|---|---|
| 2026-09-30 | 12 | 0 |
| 2026-10-01 | 17 | 1 |
| 2026-10-03 | 24 | 16 |
| 2026-10-04 | 6 | 4 |
| 2026-10-05 | 2 | 1 |
| 2026-10-06 | 1 | 1 |
| 2026-10-07 | 1 | 0 |
| 2026-10-08 | 1 | 0 |
| 2026-10-09 | 7 | 1 |
| 2026-10-10 | 4 | 0 |

## 미해결 목록
| 티켓 | 상태 | 종류 | 발견일 | 메모 |
|---|---|---|---|---|
| TK-44 | open | regression | 2026-10-03 | 운영8280 부분배포·전체open 유지. #90 b1e inline에 이어 #95 5e6e859 named PAGE ActualText/capture 제한범위 수용5485088907. exactCI38144023479/score38144023440/Docker SUCCESS·독립PDF18 PASS·원래 경계/접합/법리 보호 유지. root full1회 exit0 수용1214/원장949/전체6914/브라우저197/실패0·fixed81.7/79.2/FP0. 미지원/Form/structure/untagged/UNKNOWN primary/floor/consumer 잔여·신규통합/배포 전. |
| TK-45 | open | regression | 2026-10-03 | 전체open·미배포. #93 f8f6e08 root5483280439 불수용 유지: 원래2/8·8/8·0/4 불변으로 두strictincrease 미달·정상8/8 보호. 최신 #96 8d237496f32868f339828bb6ab8cf7622f641263은 source reference/법적적용 구분 설계·공개65PASS 제출(구현측)/제품0·root 설계검토 대기. 승인 뒤 제품/원래수용 시험·불수용제품 통합금지. |
| TK-49 | open | regression | 2026-10-03 | 운영8280 부분배포·전체open 유지. #90 b1e inline에 이어 #95 5e6e859 named PAGE ActualText/capture 제한범위 수용5485088907. exactCI38144023479/score38144023440/Docker SUCCESS·독립PDF18 PASS·원래 경계/접합/법리 보호 유지. root full1회 exit0 수용1214/원장949/전체6914/브라우저197/실패0·fixed81.7/79.2/FP0. 미지원/Form/structure/untagged/UNKNOWN primary/floor/consumer 잔여·신규통합/배포 전. |
| TK-55 | known_open | regression | 2026-10-04 | 운영8280 부분배포·known_open 유지. #91 86e cascade에 이어 #97 2f4e798 두first-party 발췌 occurrence/source추가검사 제한수용5485136030. exactCI38143165314/score38143165365/Docker SUCCESS·독립27대조 PASS·원래privacy 필수/보호 충족. root full1회 exit0 수용1214/원장2357/전체8061/브라우저197/실패0·fixed81.7/79.2/FP0. 이전#91 첫full timing1FAIL 이력보존·현재결과와구분. legacy/opaque/unsupported/capture-budget 잔여·신규통합/배포 전. |
| TK-73 | open | existing | 2026-10-10 | 전체open·미배포. #92 최신545c917fd12f9fec40eb52bbccfffaf566bc9fdc 설계/공개시험·제품0. 별도 source-tree/native 안전성 제한PASS는 제품/기준승인과구분·구체 기준안 검토 HOLD. 원래111 날짜확대 진짜확인손실+9/false추가이득0·기존4종AFP3 불변. 사용자 확인필요분리 선택은 검토이며 승인0·원래A/finding/GLOBAL/UNKNOWN 보호 유지. |

## 읽는 법
- 회귀 비율이 줄면 수정 과정의 품질 관리가 나아지는 것이다. 성능(처음 보는 문서의 탐지율)은 고정 비공개 벤치마크로 따로 본다(`FIXED_BENCHMARK.md`).
- 종류는 티켓 머리의 유형 표기로 자동 분류한다(오차 가능). 틀리면 등록부의 `kind`로 바로잡는다.
