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
| TK-44 | open | regression | 2026-10-03 | #78 c6e 직접SPACE 보존·#86 ebd UNKNOWN lazy대안/진단 메타데이터 제한범위내용수용·844평가통합CI성공. 실제명시SPACE48/48·UNKNOWN24·legacy29출력동일9/29. primary폭의존/ActualText잔여유지·완전해소아님·최종full/봉인/운영배포전. 승인된 부분만 0.13.0 main8280a59 배포; 티켓 전체 잔여는 미완료 유지. |
| TK-45 | open | regression | 2026-10-03 | PR84 e21c40d442f521782cd7d85a18b8fb40655b403d 불수용5482338759(요청6106648755). exactCI38120377539/점수38120377556/Docker SUCCESS·공개815/독립26 PASS. 원래20 및actualTXT20 부인8/8·정상7/8·확장1/4로 정상8/8 필수미달; 고정18은3/4·4/4·1/4·1/2·4/4. 출력불변진단 새case/순서/공백 통과하나 regular/AUXILIARY attachment fullmatchfalse→proof없음·resolved0, 소비자LOCAL_SUBJECT 면제 미도달. 수용3389에서 제외·미통합/미배포. 기준/기대값 불변; 별도 공개 문법·논항 설계 승인 후 보완, 비공개 어휘/좌표 공유금지. 이전3736/258 시험 생성기·타이밍 실패는 역사기록으로 보존. |
| TK-49 | open | regression | 2026-10-03 | #78 c6e 직접SPACE 보존·#86 ebd UNKNOWN lazy대안/진단 메타데이터 제한범위내용수용·844평가통합CI성공. 실제명시SPACE48/48·UNKNOWN24·legacy29출력동일9/29. primary폭의존/ActualText잔여유지·완전해소아님·최종full/봉인/운영배포전. 승인된 부분만 0.13.0 main8280a59 배포; 티켓 전체 잔여는 미완료 유지. |
| TK-55 | known_open | regression | 2026-10-04 | #82 ce83355 first-party계약/손실없는JSON 제한범위 내용 수용. 기존개인정보/라우터 보호 유지·#81과 통합PHONE/RRN 도달0. 호환성 결정에 따라 legacy역할키24/encoded불명역할 잔여 유지·전체해소 아님·최종릴리스 대기. 승인된 부분만 0.13.0 main8280a59 배포; 티켓 전체 잔여는 미완료 유지. |
| TK-73 | open | existing | 2026-10-10 | PR79 214334ddb916a0a856e7a4a55d39cbd180c5ec1a 불수용5482229717. 요청6106394284·exactCI38118526548/점수38118526520/Docker 모두SUCCESS. 평가측 원래4 재실행19.0/29.6/36.2 FP0 유지;20261010 시작15.2/.302/FP3(control3/A3)→25.2/.302/FP1(control1/A1), 기존9ab와동일·필수AFP/control0 미달. 네세트 인젝션방어유지. 공개936/독립GLOBAL실제형식감사PASS는대체불가. 미통합·미배포·새봉인미실행·기준/채점/기대값불변. 출력불변214 진단: control7rows/scope1/excluded2/keys4·남은group1 inventorykindNone1/모든narrative종료뒤prose1. 새inventory_atom4회/PASS0·row정규화mapping/단일itemorigin/원래offset순서/definitionmarker4통과. wholeparagraphsource0·nativeatom0→eligible/certified/rowdomain0·latercitation원시함수호출0. 4paragraph모두multi-reading-segment(total16), source없음으로단정하지않음. row정규화일치와originalphysicalglyph proof는구별하며 UNKNOWNjoin을원문으로인증/가상whole-source span생성금지. 원문/어휘/IDs/좌표공유0·기존globalall-origin충돌/UNKNOWN 및interval/936expects 유지. 수용3389에서 제외·미통합/미배포. 기존 name-field+colon feasibility 0/4로 해당 공개 gap은 남은 AFP의 원인 증명이 아님. 제품214 동결·새 공개 wholecaption/source-role 설계 승인 전 제품추가 금지. |

## 읽는 법
- 회귀 비율이 줄면 수정 과정의 품질 관리가 나아지는 것이다. 성능(처음 보는 문서의 탐지율)은 고정 비공개 벤치마크로 따로 본다(`FIXED_BENCHMARK.md`).
- 종류는 티켓 머리의 유형 표기로 자동 분류한다(오차 가능). 틀리면 등록부의 `kind`로 바로잡는다.
