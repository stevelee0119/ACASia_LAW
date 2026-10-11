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
| TK-44 | open | regression | 2026-10-03 | 0.13.0 운영8280의 SPACE/UNKNOWN 진단 부분은 배포됨. PR90 b1e506f exact CI38132618288/점수38132618289/Docker 성공·요청6108248291. root 공개239·수용/회귀2163 PASS/기존24 xfail 및 전체verify_all 종료0(수용1214/원장949/전체6723/브라우저197/실패0), 고정81.7/79.2/FP0 유지. root5483100719 inline ActualText provider 제한범위 내용 수용·신규 통합/배포 전. 비태그/resource/Form/structure-tree/UNKNOWN primary/floor/consumer 잔여·전체 open 유지. |
| TK-45 | open | regression | 2026-10-03 | 이전 PR84 e21 정상8/8 필수 미달 불수용·미통합/미배포 유지. PR93 5a51dd3 설계112 root5483024001 조건부 승인, 제품0dd4b8 제출. 독립 actualTXT20 사전감사에서 문장간 인용/상대·보고·반박4와 다른 법률 출처2의 새 proof 오인증으로 HOLD6108540760. 화자/민사규범 보호 보완 중, CI·정식3줄 요청 후 원래 정상8/8·부정/확장 시작2/8·0/4 대비 엄격 증가로 판정. 기존finding·UNKNOWN 보호와 기대값 유지·전체 open. |
| TK-49 | open | regression | 2026-10-03 | 0.13.0 운영8280의 SPACE/UNKNOWN 진단 부분은 배포됨. PR90 b1e506f exact CI38132618288/점수38132618289/Docker 성공·요청6108248291. root 공개239·수용/회귀2163 PASS/기존24 xfail 및 전체verify_all 종료0(수용1214/원장949/전체6723/브라우저197/실패0), 고정81.7/79.2/FP0 유지. root5483100719 inline ActualText provider 제한범위 내용 수용·신규 통합/배포 전. 비태그/resource/Form/structure-tree/UNKNOWN primary/floor/consumer 잔여·전체 open 유지. |
| TK-55 | known_open | regression | 2026-10-04 | 0.13.0 운영8280의 first-party closed/lossless JSON 부분은 배포됨. PR91 86e75e3 exact CI38132924102/점수38132924186/Docker 성공·요청6108286856. root 공개101/독립24/4adapter mockwire PASS·원래 privacy 게이트 충족. 최초전체exit1(전체6945 PASS/기존TK71 시간검사1FAIL)은 보존, 시작/후보 동일검사 각PASS 및 원래full_tests 단계만 단독1회 보완6946 PASS/실패0/290.3초, 코드/시험/임계값 변경0·첫원인미확정. root5483126695 요청별cascade source 추가검사 제한범위 내용 수용·신규통합/배포 전. arbitrary legacy unknown-role은 기존 호환성 계약에 따라 known_open·전체 완료 아님. |
| TK-73 | open | existing | 2026-10-10 | 이전 PR79 214 필수AFP0 미달 불수용·미통합/미배포 유지. PR92 ab5378e는 설계/진단/기준안 검토 메모만·제품diff0. root5483050614 source-role5822 제품 HOLD. public bounded108은 원래 대상 적용 증명 없음, root source-role27 재현·DOCX native rows0 별도 coverage잔여. 사용자가 확인 필요 분리 설계·기준안 검토를 선택하여 구체안 작성·평가 진행, 제품/등급/원래 시험/수용기준 변경 승인0. A/confirmed/pending 및 진짜양성 이동을 별도 기록하며 단순AFP0 수치 이동 금지·open. |

## 읽는 법
- 회귀 비율이 줄면 수정 과정의 품질 관리가 나아지는 것이다. 성능(처음 보는 문서의 탐지율)은 고정 비공개 벤치마크로 따로 본다(`FIXED_BENCHMARK.md`).
- 종류는 티켓 머리의 유형 표기로 자동 분류한다(오차 가능). 틀리면 등록부의 `kind`로 바로잡는다.
