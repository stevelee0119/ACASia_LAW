# Antigravity 구현 전달문 — 2026-10-19 통합본 (26), 10-21 판정 반영

이 문서 하나가 Antigravity에 대한 현행 지시다. 이전 전달문 전체를 대체한다. 작성: 평가 에이전트(Claude Code).

전달 기록: 2026-10-21 사용자가 Antigravity에 전달 완료(`a491318` 판, TK-95 우선 처리 포함).
추가 전달: 2026-10-22 D-4(#171) 3차 판정 행 전달 완료(`8860fa4` 판). 2026-10-24 B-2(#168) 4차 판정 행 전달 완료(`91374bb` 판). 2026-10-24 B-2 5차·TK-93·TK-94 판정 행 전달 완료(`a413a47` 판). 2026-10-24 B-2 6차 판정 행 전달 완료(`0b257ea` 판). 2026-10-24 B-2(병합)·TK-94 5차 판정 행 전달 완료(`a170e75` 판). 2026-10-24 2-1절(0.14.0 릴리스 순서) 전달 완료(`577cfe2` 판). 2026-10-24 A-4(#175 불승인) 판정 행·A-3 사전 의견 전달 완료(`5331abd` 판). 2026-10-24 2-2절(탐지 PR 공통 수용 규약)·#175·#176·#165·#167 PR별 보완 지시 전달 완료(`d0f40df` 판). 2026-10-24 메모 보정본 3건(#175·#165·#167) 조건부 승인 지시·#177 닫기·TK-125 반영 안내 전달 완료(`cc9c7d4` 판). 2026-10-24 #176 수용·병합 안내 전달 완료(`cb83414` 판). 2026-10-24 #175 4차 보완 지시(R1~R9)·A-4 범위 유지 안내 전달 완료(`04de460` 판). 2026-10-24 버전·릴리스 정책 개정 안내·#165 4차 보완 지시(S1~S9) 전달 완료(`4c5045e` 판). 2026-10-24 #167 3차 보완 지시(T1~T9)·#178 병합 안내 전달 완료(`b8319b5` 판). 2026-10-24 #175 5차 보완 지시(U1~U4) 전달 완료(`2ede86e` 판). 2026-10-24 #165 5차 보완 지시(V1~V4) 전달 완료(`7e9d176` 판). 2026-10-24 #165 6차 보완 지시(X1~X3) 전달 완료(`8b19ae2` 판). 2026-10-24 #175 6차 보완 지시(W1~W3) 전달 완료(`18eb446` 판). 2026-10-24 #167 4차 보완 지시(Y1~Y9) 전달 완료(`ba29ae8` 판). 2026-10-25 #175 7차(Z1~Z4)·#165 7차(V1~V5)·#167 5차(Q1~Q3) 보완 지시 전달 완료(`357d87f` 판). 2026-10-25 #175 8차(AA1~AA6)·#165 8차(BB1~BB4)·#167 6차(QQ1~QQ3) 보완 지시 전달 완료(`f7754e3` 판). 2026-10-25 #165 9차 판정(CC1 조건부 승인) 전달 완료(`120c95e` 판). 2026-10-25 #167·#175 사전 검증 부록 전달 완료(`73c351d` 판). 2026-10-25 #165 CC1·#175 DD1 판정 전달 완료. 2026-10-25 2-1-1절(0.14.0 버전 커밋 지시) 전달 완료(`d5c111f` 판, #179 병합 `988c678` 뒤).

## 0. 가장 중요한 것: 말뭉치·평가 세트 문장을 규칙에 옮기지 않는다
- **train 문장 틀 금지(10-17 사용자 지시)는 그대로다.** #125·#126 1차는 train 결함 문장을 정규식으로 옮겨 불승인됐다(train 40/40·32/40, 같은 유형 은퇴 항목 득점 0, 다른 표현 0/5·0/4).
- **평가 세트 문장도 금지한다(10-18 추가).** #125 `a536a02`는 은퇴 세트 정답 문장(`별도 삽입 예정`·`지워진 빈 화면 사본`·`원본 접근 불가`)을 규칙에 넣어 불승인됐다.
  - 유일한 점수 상승(은퇴 08b SD-06)이 그 문구 일치에서 나왔다. train EVI-FORM 개선은 0이었다.
  - 은퇴·고정(dev·holdout) 세트는 **일반화를 재는 평가 세트**다. 그 정답지·문서 문장을 규칙이나 시험에 넣지 않는다.
  - **정규식 선택(`|`)으로 쪼개 넣어도 같다.** #125 `4391de4`는 은퇴 10 정답 3항목의 자료 종류·자료명 꼴·결함 어휘를 첨부 경로 대안으로 나눠 넣어 불승인됐다(은퇴 10 +5.7이 그 3항목뿐, 같은 구조를 다른 어휘로 쓴 탐침 0/6). 문구 대조 도구 통과는 수용을 뜻하지 않는다.
  - 평가 측 탐침 문장(판정 코멘트에 적힌 예)도 규칙·시험에 복사하지 않는다. #125 `133ec92`는 공개된 탐침 문장 4건의 표현을 정규식에 넣어, 공개 탐침 4/4·비공개 새 문장 0/8로 불승인됐다. 평가 측은 판정에 공개하지 않은 새 탐침으로 일반화를 잰다.
- 규칙은 결함의 **구조**로 쓴다. 예: 목록 구역과 본문 인용의 비교, 문서 안 진술끼리의 모순, 서증 항목의 내용 자리가 비어 있음. 양성 시험은 train·평가 세트와 **다른 표현**으로 쓴다.

## 1. 체제와 규칙
- 새 구현은 Antigravity, 평가(측정·판정·통합·릴리스 준비)는 Claude Code가 맡는다(사용자 확인 10-17). Codex는 잔여 티켓을 마쳤다.
- [AGENTS.md](../../AGENTS.md)·[AGENT_ROLES](../AGENT_ROLES.md) 구현 규칙을 따른다.
  - 보호 경로 수정 금지. 사건 값·서면 문구·말뭉치 문장·평가 세트 문장 하드코딩 금지.
  - 새 규칙마다 합성 양성 3건·대조 3건 이상.
  - 커밋 끝 `Agent: implementer`. 새 브랜치 → PR. `Steve_ACASiaLAW`·`main` 직접 푸시·강제 푸시·리베이스 금지(병합 커밋으로 받는다).
- 비공개 세트·봉인 자료·고정 비공개 벤치·개발 말뭉치 `check/`는 요청·열람하지 않는다.
- **PR을 내기 전 평가 세트 문구 대조는 `--base origin/main`으로도 돌린다.** Steve 기준만 돌리면 이미 병합된 코드의 문구가 릴리스 PR에서 처음 드러난다(0.13.1 #141 → #142).
- Steve 대상 PR의 필수 검사 5개: 점수 하락 게이트, 테스트(SQLite + PostgreSQL/pgvector + Redis), Docker OCR readiness, CodeQL 새 경고 게이트, 은퇴 세트 비교.
- **공용 입력을 바꾸지 않는다.** `exhibit_rows()`·`_exhibit_lines`·`_numbering`(TK-73)처럼 다른 검사가 쓰는 결과는 그대로 둔다. 걸러야 하면 새 검사 안에서 복사본으로 거른다. #126은 이 문제로 두 번 회귀했다(holdout HO-05 날짜 결함 소실, TK-73 시험 3건 실패).

## 2. 이번 주기 — 다음 릴리스: 편의성과 기능을 함께 올린다 (2026-10-19 사용자 지시)
- **현재 운영:** 0.13.1(main `c512462`, 10-19 배포). Drive 서비스 계정 전환 완료(TK-80). 효율 라우팅은 운영 환경변수로 ON(`LV_LLM_EFFICIENT_ROUTING=1`·`LV_LLM_CROSS_CHECK=auto`)이며 **코드 기본값 OFF는 바꾸지 않는다.**
- **릴리스 기준(예외 없음, [RELEASE_PROCEDURE 2-4](../scorecards/RELEASE_PROCEDURE.md)):** 평가 측이 0.13.1과 후보를 같은 조건으로 함께 잰다.
  - 고정 dev·holdout이 각각 0.13.1 이상이고, 두 세트 득점 합계가 0.13.1보다 높아야 한다(탐지 개선만 셈, 표시 보강 제외).
  - 오탐 0·A등급 오탐 0·인젝션 방어 유지, 은퇴 4세트 각각 0.13.1 이상·항목 단위 회귀 0.
  - **화면 개편만으로는 릴리스하지 않는다.** 시험·채점 기준이 바뀌면 바뀐 기준으로 0.13.1과 후보를 둘 다 다시 잰다.
- **0.13.1 손실 지도(평가 측 10-19 오프라인 측정, 집계만):**
  - 고정 dev·holdout에서 오프라인으로 올릴 수 있는 항목: 인젝션 폭 0 문자 채널 1(TK-89), EVI-COPY 1(B-2), EVI-OVR 2항목 부분 점수(TK-91). 나머지 손실(법령·판례 공식 대조, AI 작성 판별)은 오프라인 게이트로 재지 못한다.
  - 은퇴 4세트에서 큰 손실: EVI-INCONS 18, 인젝션 채널 약 17, EVI-OVR 12, EVI-FORM 8.5, EVI-DATE 7, EVI-COPY 5, EVI-NUM 4.
- **PR 원칙:** 항목마다 새 PR 1개. 서로 섞지 않는다. 'A·C·D-1~3'은 바로 구현하고, 'B·D-4·E'는 **설계 메모 PR부터** 낸다. 화면(D) PR은 탐지 diff 0이어야 한다.

| 순서 | 항목 | 종류 | 근거 |
|---|---|---|---|
| A-1 | **TK-89 인젝션 채널별 탐지 일반화 (신규, 최우선)** | 탐지 | [TK-89](TK-89_injection_channel_generalization.md) |
| A-2 | TK-81 잔여: 단독 '-다는 (상대방) 지적은 틀립니다' 반박 오탐 | 탐지(오탐) | [TK-81](TK-81_evi_form_exclusion_overreach.md) |
| A-2b | **TK-92 정상 서술을 '문서 속 지시문'으로 잡는 기존 오탐 (신규)** | 탐지(오탐) | [TK-92](TK-92_meta_instruction_fp_on_narrated_requests.md) |
| A-2c | **TK-93 문장 부호 없는 긴 본문에서 classify() 제곱 증가 (신규, 기존 결함)** | 성능·견고성 | [TK-93](TK-93_classifier_quadratic_long_unbroken_text.md) |
| A-3 | #126 잔여 3건 (은퇴 10 A등급 오탐 1 포함) | 탐지 | 3절 A-3 |
| A-4 | EVI-DATE 위치 보강 | 탐지 | 3절 A-4 |
| B-1 | **TK-91 EVI-OVR 증거 과장 (신규)** | 탐지, 설계 메모 먼저 | [TK-91](TK-91_evi_ovr_evidence_overreach.md) |
| B-2 | EVI-COPY 나머지 32건(준비서면·소장 등 비진술서) | 탐지, 설계 메모 먼저 | 작성명의인 기준 |
| B-3 | **TK-90 EVI-INCONS 문서 안 진술 불일치 (신규)** | 탐지, 설계 메모 먼저 | [TK-90](TK-90_evi_incons_internal_inconsistency.md) |
| C-1 | **TK-84 참고자료 대조 문장 잘림 (신규)** | 표시 결함 | [TK-84](TK-84_reference_contradiction_text_truncation.md) |
| C-2 | TK-78 공식 DB 조회 실행 단위 집계 | 관측성 | [TK-78](TK-78_source_lookup_run_summary.md) |
| C-3 | TK-82 Drive 내려받기 네트워크 오류 원인 구분·1회 재시도 | 견고성·관측성 | [TK-82](TK-82_drive_download_network_error.md) |
| D-1 | **TK-85 개인정보 안내를 업로드 시점 확인으로 (신규)** | 화면 | [TK-85](TK-85_privacy_ack_at_upload.md) |
| D-2 | **TK-86 버전 비교·사건 일지·금액 계산·근거 찾기 탭 삭제, 재시도 버튼 이동 (신규)** | 화면 | [TK-86](TK-86_remove_low_use_panels.md) |
| D-3 | **TK-87 검토 상태·담당자 입력 → '확인이 필요한 내용' 요약 (신규)** | 화면·보고서 점검 | [TK-87](TK-87_review_items_summary_instead_of_workflow.md) |
| D-4 | **TK-88 3단 체계: AI 작성 → 판례·법령·주요참고문헌 인용 오류·미확인 → 법률적으로 무리한 주장 (신규)** | 화면 구조, 설계 메모 먼저 | [TK-88](TK-88_three_tier_review_structure.md) |
| E-1 | TK-83 auto 법리 검토의 엇갈린 항목만 세 번째 공급자로 | 효율, 설계 메모 먼저 | [TK-83](TK-83_argument_review_auto_partial_escalation.md) |

## 2-1. 0.14.0 릴리스 순서 (2026-10-24 사용자 결정, 평가 측 정정 반영)
- 범위: A-4(#169 구현) → A-3 잔여(은퇴 10 A등급 오탐 1) → B-1 TK-91(#165) → B-3 TK-90(#167) → 종합 측정 → 릴리스 PR.
- **A-4 범위 유지(2026-10-24 사용자 결정):** #175가 탐침 기준에 못 미쳐 평가 측이 범위 제외를 건의했으나, 사용자가 범위에 포함하도록 결정했다. 수용 기준은 그대로이며 릴리스 PR은 A-4 수용·병합 뒤에 만든다. A-3은 #176 병합(`de91c55`)으로 끝났다.
- **D-4 TK-88(#171)은 이미 끝났다.** 4차 `ef47063` 수용, Steve `ccf0773` 병합(10-22). 두 시험(`.tier3-table` 분리, 표 1 브라우저 시험)도 그때 해소됐다. 다시 작업하지 않는다.
- A-4 구현 PR은 메모 조건부 승인(#169 `061581f`)의 다섯 조건을 따른다: ① 미득점 7항목별 진단표(특정 못 하는 규칙은 제외), ② 같은 주체·같은 대상일 때만 사건 쌍 비교·별개 주체·정정 서술 제외, ③ 기간 오차는 민법 제157조(초일 불산입)·제159조·제160조, ④ train +6 근거 또는 삭제, ⑤ 점검표 1~7항.
- A-3 잔여: 은퇴 10 A등급 오탐 1건은 0.13.1에도 있다. 발생 행·구조를 건수로 진단하고, 다른 항목을 잃지 않는 범위에서 단독 PR로 낸다.
- B-1·B-3은 3절 상태표의 불수용 사유를 그대로 해소한다(B-1: 자기 측 발신·증명 근거 구조·은퇴 12항목 진단, B-3: 같은 대상 결합 조건·은퇴 18항목 진단·4배당 성능 비 < 8).
- **릴리스·버전 기준 개정(2026-10-24 사용자 채택):** 릴리스는 게이트(회귀 금지) + 가치(점수 순증·새 기능·결함 감소·보안 중 하나)로 판단한다(RELEASE_PROCEDURE 2-5). 버전 자리는 변경 분류(VERSION_POLICY 5절: 새 기능·기능 변경·합산 오류 감소율 10% 이상 = 첫째 자리, 결함·보안 수정·작은 성능 개선 = 둘째 자리)로 정한다. 구현 측은 PR 본문에 변경 분류(Added·Changed·Fixed·Security 등)를 적는다.
- 릴리스 전제(평가 측, 2-5로 개정): 0.13.1(`c512462` 제품)과 같은 조건 비교에서 고정 dev·holdout 각각 이상(합계 상승은 가치 조건 중 하나), 고정 오탐 0·A등급 0, 은퇴 4세트 항목 후퇴 0, 릴리스 후보 SHA에서 `verify_all` 전체 모드 1회, 필수 CI 5종(점수 하락 게이트·테스트·Docker OCR readiness·CodeQL 새 경고 게이트·은퇴 세트 비교) 성공, 버전 판정서(`docs/scorecards/version_verdicts.json`, 평가 측 작성) 뒤에만 버전 상향, holdout 기준선 상향은 사용자 승인. 구현 측은 버전을 올리지 않는다.

## 2-1-1. 0.14.0 버전 커밋 지시 (10-25, 판정서 `docs/scorecards/version_verdicts.json` 0.14.0)
평가 측이 릴리스 후보 Steve `907c2fa`를 종합 측정하고 0.14.0(minor) 판정서를 썼다. VERSION_POLICY 6절 3항대로 **버전 커밋 1개**만 만든다.

**선행요건**: 평가 PR #179(판정서 포함)가 Steve에 병합된 뒤 시작한다. 새 브랜치는 그 병합 뒤 Steve에서 딴다.

**바꿀 것(이 셋만, 다른 변경 섞지 않음)**
1. `packages/common/config.py`: `version: str = "0.13.1"` → `"0.14.0"`.
2. `docs/releases.json` 끝에 아래 항목을 그대로 추가한다(날짜는 커밋일로 바꿔도 된다).
3. `docs/release_highlights.json`에 아래 "0.14" 키를 `_설명` 바로 뒤에 넣고 `python scripts/update_readme.py`를 실행해 README 변경표·`docs/RELEASE_HISTORY.md`를 갱신한다. README 다른 줄은 손대지 않는다('현재 운영 버전' 줄은 배포 뒤 평가 측이 바꾼다).

releases.json 항목:
```json
{
  "version": "0.14.0",
  "date": "2026-10-25",
  "changes": [
    "평가 측 minor 판정(0.13.1 → 0.14.0, 907c2fa 기준, 분류 added·changed·removed·fixed·performance_patch, 합산 RER 4.8%): 0.13.1(c512462)과 같은 오프라인 조건에서 고정 개발 82.6 유지, 홀드아웃 80.1 → 81.9(+1.8), 오탐 0건·A등급 0건, 하락 항목 0. verify_all 전체 모드 종료 0(전체 시험 8989·브라우저 197 통과)",
    "새 구조 탐지: #175 사건 순서 역전(EVI-DATE), #167(TK-90) 문서 안 장소·서명자·수량 불일치(EVI-INCONS), #168 소송서면·증거설명서의 경위서 원문 통째 복제(EVI-COPY), #165(TK-91) 서증 원용 범위 초과(EVI-OVR, 세트 득점 없음·일반 표현 탐침으로만 검증). 은퇴 세트 27.2/40.7/48.3/35.1 → 48.9/42.6/50.0/43.9, 개발 말뭉치 train 26.5×4 → 37.5/37.5/37.5/36.5",
    "포함 PR 및 티켓: #146(TK-89)·#147(TK-92) 인젝션, #149(TK-81)·#163·#176(A-3) 증거 목록 오탐, #150(TK-84)·#151(TK-78)·#152(TK-82)·#153(TK-85)·#154(TK-86)·#155(TK-87)·#171(TK-88)·#164(TK-94) 화면·보고서, #166(TK-83) auto 법리 검토 부분 에스컬레이션, #170(TK-95)·#173(TK-93) 시험·성능",
    "알려진 미해결: 관형절로 엮인 두 사건·대상 생략 응답 사건 일부(EVI-DATE), 7범주 밖 서증·자기 측 통지서로 상대방 내심 단정(EVI-OVR), 기존 이행 동사 밖 수량 서술·서명 대상 문서 명사 한정(EVI-INCONS). 온라인 모델·공식 DB·Drive 대조와 봉인 세트는 측정 못 함"
  ]
}
```

release_highlights.json "0.14":
```json
"0.14": [
  "구조 탐지 추가: 사건 순서 역전(EVI-DATE), 문서 안 장소·서명자·수량 불일치(EVI-INCONS), 경위서 원문 통째 복제(EVI-COPY), 서증 원용 범위 초과(EVI-OVR, 세트 득점 없음)",
  "고정 시험 개발 82.6 유지, 홀드아웃 80.1→81.9, 오탐 0건(0.13.1과 같은 조건)",
  "인젝션 채널별 구조 탐지(TK-89), 정상 서술 지시문 오탐 방지(TK-92)",
  "검토 화면 3단 개편·'확인이 필요한 내용' 요약, 저활용 탭 정리, 미확인 판례·법령 외부 AI 검증 프롬프트(TK-94)"
]
```

**확인(커밋 전 직접 실행, PR 본문에 결과)**
- `python scripts/check_version_policy.py --base origin/Steve_ACASiaLAW` 종료 0(평가 측이 같은 변경을 임시 사본에서 돌려 통과 확인).
- `python scripts/update_readme.py --check` 종료 0, `pytest -q tests/test_update_readme.py` 통과.
- 커밋 제목 `chore(release): 버전 0.14.0 판정서 반영`, 끝에 `Agent: implementer`. PR 대상 `Steve_ACASiaLAW`.

**수용 기준**: diff가 위 세 파일과 생성물(README 변경표·RELEASE_HISTORY)뿐, 필수 CI 성공, 판정서와 버전 일치. 평가 측은 diff와 CI만 확인하고 수용한다(탐지 변경 없음, 재측정 없음).

> **상태(10-28 평가 측 확인):** 0.15.0 버전 커밋 #187 병합(`fdf11b1`), 릴리스 #189 main 병합(`08d40ff`, 10-26). **운영 배포 확인(health 0.15.0·`08d40ff`, 10-28)** — TK-126·128 deployed, TK-127 1단계 배포. #186 TK-127 2단계 메모 Steve 병합(`efc9c9c`), 평가 측 검토 전. #185 TK-129 1차 보완 2건(2-4-1) → 2차 보완 1건(2-4-2) → 3차 `89cf414` 코드 수용·사용자 화면 확인 대기(2-4-3). #191 TK-127 2단계 1차 보완 2건(2-6) → `4891f4e` 코드 수용 → 사용자 결정(빈 괄호 제거·영문 코드 유지) 반영 보완 1건(2-6-1) → `cfd80c3` 수용, 사용자 병합 대기(10-28). #185 Steve 병합 `5d03247`.

## 2-1-4. 0.17.0 버전 커밋 지시 (11-02, 일반 경로)

- 판정서: `docs/scorecards/version_verdicts.json` 0.17.0. minor, basis added·changed·fixed, 측정 커밋 Steve `b14d7d9`.
- 근거
  - verify_all 전체 종료 0
  - 고정 82.6/81.9/FP0/A0 불변
  - 봉인 sealed_20261102: 운영본·후보 40.2로 같음, 오탐 0
  - 은퇴 5세트 상승(EVI-LOGIC만), 오탐 0
- 선행: 판정서가 든 평가 PR이 Steve에 병합된 뒤 시작한다.
- 수정본: `patches/v0.17.0_version_commit.diff`(5개 파일 +19/−1).
  - `config.py` version
  - `docs/releases.json` 0.17.0 항목
  - `docs/release_highlights.json` 0.17 요약
  - `update_readme.py`가 만든 README·RELEASE_HISTORY 줄
- 평가 측 사전 검증(b14d7d9 + 판정서 + 수정본): `check_version_policy --base 2f06f9a` 위반 없음(상향 1건 0.16.0 → 0.17.0), `update_readme --check` 통과, 버전·릴리스 관련 시험 3개 파일 49건 실패 0.
- 11-02 갱신: #205가 먼저 병합되어(Steve `d836a8b`), 수정본을 `d836a8b` 기준으로 다시 만들었다. 같은 검증을 다시 통과했다: check_version_policy 위반 없음, update_readme --check 통과, 시험 실패 0. 그대로 적용한다.

## 2-1-3. 0.16.0 버전 커밋 지시 (10-29, 일반 경로, 구현 한시 대행)

```
[Codex(구현 대행) 지시 — 0.16.0 버전 커밋 (평가 측 판정서 version_verdicts.json 0.16.0, 2026-10-29)]

■ 배경
- 릴리스 후보 Steve d2aa19a(TK-129 #185 + TK-127 2단계 #191)에서 평가 측 verify_all 전체 모드가 종료 0으로 끝났다.
  · 환경은 CI와 같다(Python 3.11.15, tesseract 5.3.4).
  · 수용 1238·회귀 장부 2357·전체 9094·브라우저 197 통과, 실제 실패 0.
  · score_gate·regression_gate(기준 0.15.0 main 08d40ff)·hardcoding_diff·test_edits·protected_paths·version_policy 통과.
- 점수: dev 82.6 / holdout 81.9 / 오탐 0 / A 0(0.15.0과 같음).
- 판정: minor(0.15.0 → 0.16.0), 분류 added·changed·fixed. 봉인 시험은 변경 범위 밖이라 생략한다(RELEASE_PROCEDURE 2절 2).
- 이 커밋은 구현 한시 대행 범위('이번 기능 구현 및 릴리스까지', 사용자 지시 10-28) 안이다.

■ 선행
- 평가 측 판정서가 담긴 평가 PR이 Steve_ACASiaLAW에 병합된 뒤 시작한다. check_version_policy가 판정서를 읽는다.

■ 할 것 — 평가 측 수정본 그대로 (5개 파일, +19/−1)
- 새 브랜치(예: codex/version-0.16.0, base Steve_ACASiaLAW)에서:
  `git fetch origin evaluator/round8-promotion && git show origin/evaluator/round8-promotion:docs/handoff/patches/v0.16.0_version_commit.diff | git apply --3way`
- 대상 파일:
  · packages/common/config.py: version 0.16.0(주석 포함)
  · docs/releases.json: 0.16.0 항목
  · docs/release_highlights.json: 0.16 요약 4줄
  · README.md·docs/RELEASE_HISTORY.md: scripts/update_readme.py가 생성한 줄
- 날짜 2026-10-29는 버전 기록일이다. 배포일이 다르면 배포 뒤 평가 측이 README '현재 운영 버전'에 실제 배포일을 적는다(이 커밋에서 바꾸지 않는다).

■ 평가 측 사전 검증 (d2aa19a + 수정본 + 판정서, 저장소 밖 사본)
- check_version_policy --base 08d40ff: '위반 없음(상향 2건: 0.14.0 → 0.15.0, 0.15.0 → 0.16.0)'.
- update_readme.py --check 통과.
- 버전·릴리스 관련 시험 4개 파일 65건 실패 0.

■ 하지 않을 것
- 다른 파일·코드 변경, 판정서(docs/scorecards/**) 수정, README '현재 운영 버전' 줄 수정.

■ 제출물·수용 기준
- 커밋 1개(`chore(release): 버전 0.16.0 판정서 반영`, 끝에 `Agent: implementer`), PR 대상 Steve_ACASiaLAW.
- 필수 CI 5종이 같은 SHA에서 성공해야 한다. PR 코멘트 3줄('검토 요청'은 CI 완료 뒤).
- 평가 측 확인: diff = 수정본. 맞으면 평가 측은 CI·check_version_policy만으로 수용한다 → 사용자 병합 → 릴리스 PR(Steve → main).
- main과 Steve의 이력이 갈라져 있다(#189가 은퇴 세트·메모를 빼고 main에 올라감). 릴리스 PR 구성은 평가 측이 따로 안내한다.
```

## 2-1-2. 0.15.0 버전 커밋 지시 (10-25, 간소 경로 RELEASE_PROCEDURE 2-6)
평가 PR(판정서 0.15.0 포함)이 Steve에 병합된 뒤, 새 브랜치에서 `git apply docs/handoff/patches/v0.15.0_version_commit.diff` 하나로 커밋한다(5개 파일: config.py 버전, releases.json, release_highlights.json, README 변경표, RELEASE_HISTORY — 평가 측 사전 검증: check_version_policy 통과, update_readme --check 0). 커밋 제목 `chore(release): 버전 0.15.0 판정서 반영`, 끝 `Agent: implementer`. 다른 변경 금지. 평가 측은 diff와 CI만 확인한다.

## 2-3. 0.14.0 화면 오구현 보완 + 평면 탭·참고문헌 행 통합·외부 AI 답변 반영 (10-25 개정, 사용자 지시 '잘못 구현된 기능을 즉각 원래 구현하고자 했던 방향대로 변경')
0.14.0에서 사용자 개선안(10-19) 3·4항이 다르게 구현됐다. 원인은 평가 측 티켓·판정에 있었다. 이번부터 사용자 요구 티켓은 **사용자 원문과 원문 대응표**를 수용 기준으로 하고, **화면 캡처를 사용자에게 확인받은 뒤** 수용한다(AGENT_ROLES 2.1). 10-25 첫 사전 검증 화면을 본 사용자 추가 요구(평면 탭 5개·답변 붙여넣기·3번째 탭 프롬프트·참고문헌 표 통합)를 반영해 TK-126·127(1단계)·128을 **PR 1개**로 묶었다(같은 파일, 한 사본에서 함께 사전 검증). 같은 날 사용자 결정으로 '공식 DB로 다시 조회' 버튼(평가 측 추가안)을 철회하고, 반복을 줄이도록 '수정본 그대로 적용·하지 않을 것·평가 측 수용 절차 고정'으로 지시를 다시 썼다(3차 개정). 이어 사용자가 화면 6장 확인('그대로 진행'), 답변 브라우저 저장, 활동 기록 화면 삭제를 결정해 4차 개정했다. 아래가 사용자에게 낸 지시문 전문이다.

[Antigravity 지시 — TK-126·127(1단계)·128 화면 개편, PR 1개. 2026-10-25 4차 개정. 앞선 TK-126 지시 세 판은 모두 이 지시로 대체한다]

■ 이 지시의 목적: 한 번에 수용
평가 측이 아래 수정 전체를 Steve `b68e70f` 사본에 먼저 적용해 시험·화면을 확인했고, 사용자가 화면 6장을 보고 '그대로 진행'으로 확정했다(활동 기록 화면 삭제·답변 브라우저 저장 결정 포함). 구현 측은 **검증된 수정본을 그대로 적용**하고 아래 '제출 전 확인'만 돌린다. 새 설계·추가 개선·리팩터링을 하지 않는다. 그래야 보완 왕복 없이 한 번에 수용된다.

■ 1. 작업 절차 (이 순서 그대로)
1) 평가 PR #182가 Steve_ACASiaLAW에 병합된 뒤 시작한다(보호 시험 `tests/acceptance/test_f1_screen_protected.py` 수정이 #182에 있다). 현재 Steve = `b68e70f`이고 #182는 문서·보호 시험만 바꾸므로 아래 패치는 충돌 없이 적용된다(평가 측 `git apply --check` 확인).
2) 새 브랜치에서: `git apply --3way docs/handoff/patches/TK-126-128_prevalidated_b68e70f.diff` (19개 파일, 539줄 추가·187줄 삭제 — 10-25 보충으로 tests/test_drive_rag_relevance.py 포함: apps/api/main.py, apps/api/routers/workspace.py, apps/web/index.html, apps/web/static/{app.js,styles.css,workflow.js}, tests 12개).
3) 충돌이 나면(그 사이 Steve가 같은 줄을 바꾼 경우만) 양쪽을 모두 살려 합치고, PR 본문에 파일·줄과 처리 내용을 적는다. 충돌이 없으면 패치 외 변경을 하지 않는다.
4) '제출 전 확인'을 돌리고 결과를 PR 본문에 붙인다. 커밋 끝 `Agent: implementer`. PR 대상 Steve_ACASiaLAW, 제목 `fix(ui): TK-126·127·128 화면 개편 — 평면 탭·참고문헌 행 통합·외부 AI 답변 반영`.

■ 2. 수정본이 하는 일 (원인 → 고친 것, 줄 번호는 b68e70f)
1. '확인 방법' 반복: app.js 2148~2167행 블록 삭제.
2. 프롬프트 버튼이 작고 표 아래: #reviewTableActions를 표 위 띠(review-prompt-bar)로, 큰 버튼 "📋 엘박스/AI 검증 프롬프트 만들기".
3. 셀 넘침: .badge(styles.css 483행~) nowrap이 .validity-verdict에도 걸림 → 두 표의 .validity-verdict만 줄바꿈 허용.
4. 3번째 탭 '주장·쟁점' → '법률적으로 무리한 주장'(legal-claims). index.html 11·15행, workflow.js 304·307~313행, app.js 624·2583~2604·2798행. 쟁점 API·DB는 남김.
5. 배포 뒤 옛 화면: main.py 300행 뒤 미들웨어, /·/static/*에 Cache-Control: no-cache.
6. 탭 두 줄(묶음 → 하위 탭): workflow.js 6~33행 groups·syncNavigation·initNavigation·314행 호출 삭제(app.js switchTab의 syncNavigation 호출 줄도). 상단 탭 5개 [자료][AI 작성·보안 진단][출처가 확인되지 않는 항목][법률적으로 무리한 주장][보고서]. 활동 기록 화면 삭제(사용자 결정): index.html 17행 audit 패널·audit 탭 단추, app.js switchTab의 loadAudit 줄·loadAudit 함수·refreshAudit 처리 줄. 서버 감사 기록·/audit API는 그대로. '확인할 항목' 문구 전부 교체(index.html 11·13·14·15행, app.js 1240·1779·2077·2488행). 700px 이하 줄바꿈.
7. 참고문헌 결과가 표 아래 별도 절(renderFindings 2464행): 의견(engine_data.rag.observations)을 claim_id → claims[].citation_ids → 행 citation_id로, 실패 시 문장 포함 비교(양쪽 8자 이상)로 표 행 3열에 붙임. 못 붙인 의견은 별도 행(불부합은 3번째 탭). 하단 절 삭제, 표 위 #referenceStatus 한 줄 상태(펼치면 기존 처리 기록), 3번째 탭 #legalReferenceStatus는 한 줄만.
8. 답변을 다시 넣을 버튼 없음: 프롬프트 번호(A1·B1)와 결과 블록(<<<ACAS_RESULT … ACAS_RESULT>>>), '📥 외부 AI 답변 붙여넣기' → 미리보기 → '표에 반영'. 행 3열에 '외부 AI 답변 A1 (공식 확인 아님)'. 판정 배지·공식 상태·등급 불변. 답변은 브라우저 저장(localStorage, 사용자 결정).
9. 3번째 탭 프롬프트 없음: 주장 문장은 서버가 정책대로 가린다 — POST /projects/{id}/external-ai/prompt-texts (LOCAL_ONLY 403, MASKED는 PIIEngine 가림, ORIGINAL 원문). #legalClaimsActions 띠에 프롬프트·붙여넣기 버튼.

■ 3. 하지 않을 것 (넣으면 범위 밖으로 되돌린다)
- '공식 DB로 다시 조회' 버튼·자동 재조회: 만들지 않는다(사용자 결정 10-25 — 공식 DB는 검증 실행 때 law_go_kr 어댑터로 이미 조회하고, 재검증은 엘박스 프롬프트로 충분. 공식 재조회가 필요하면 기존 '다시 검증').
- 외부 AI 답변으로 판정 배지·official_status·등급·점수를 바꾸는 것.
- 답변의 서버 저장·DB 표·migrations: 하지 않는다(사용자 결정 — 브라우저 저장).
- 보고서에 답변 넣기: 이 PR에 넣지 않는다. 별도 TK-129로 평가 측이 사전 검증 뒤 따로 지시한다.
- 활동 기록 화면·버튼을 다른 곳(보고서 탭 하위 탭 등)에 다시 만드는 것.
- TK-127 2단계(인용 행의 Drive 색인 조회, review_items 서버 필드), 탐지·채점·RAG 엔진 변경.
- 수정본에 없는 문구·색·배치 변경, 함수 이름 변경, 리팩터링.
- 시험 삭제·약화(수정본의 시험 변경은 옛 구조 단언을 새 위치로 옮긴 것뿐이고 check_test_edits 통과 확인됨).

■ 4. 사전 검증 중 실제로 깨졌던 곳 (손으로 옮겨 적을 때 같은 실수 금지)
- 결과 블록은 buildExternalAiPromptForUnverifiedAuthorities 함수 **안의 문자열**로 둔다. test_external_ai_prompt.py가 이 함수만 떼어 node로 실행하므로 바깥 상수·함수를 부르면 실패한다.
- 붙여넣기 버튼의 번호↔행 연결은 **버튼을 누를 때** 저장소에서 읽는다. 버튼을 그릴 때 읽으면 프롬프트를 만든 뒤에도 비어 있다.
- 참고문헌 처리 기록(referenceSection)을 두 탭에 모두 그리면 같은 문구가 두 번 생겨 기존 시험(test_frontend_citation_groups·test_frontend_summary_compact)이 strict mode로 실패한다. 상세는 #referenceStatus 하나에만.

■ 5. 제출 전 확인 (PR 본문에 결과 붙이기)
- pytest -q tests/acceptance tests/test_frontend_*.py tests/test_external_ai_prompt.py tests/test_external_ai_prompt_browser.py tests/test_f1_ai_security_tab_browser.py tests/test_f2_review_screen_browser.py tests/test_tk61_layout_browser.py tests/test_tk88_three_tier_review.py tests/test_upload_privacy_notice_browser.py tests/test_tk126_flat_tabs_answer_import.py tests/test_workspace.py tests/test_api.py
  → 평가 측 사전 검증: 1,410건 실패 0, 건너뜀 25(같은 수가 나와야 한다).
- (10-25 보충) pytest -q tests/test_drive_rag_relevance.py → 47건 실패 0.
- python scripts/check_test_edits.py --base origin/Steve_ACASiaLAW → '기존 시험의 삭제·표시 변경 없음'.
- git diff --stat origin/Steve_ACASiaLAW → 위 19개 파일만(충돌 처리 파일은 본문에 따로 적음).

■ 6. 평가 측 수용 절차 (이것만 본다 — 추가 요구 없음)
1) 필수 CI 성공(인용). 2) PR diff = 수정본(충돌 처리분 제외 차이 0). 3) 위 시험 묶음 평가 측 재실행 실패 0. 4) 탐지 diff 0·고정·은퇴 점수 불변(엔진 미변경 확인). 5) 실제 화면 캡처(긴 판정 문구 포함)를 원문 대응표(TK-126 1~7, TK-127 1~3, TK-128 1~5)와 함께 사용자에게 제시 → 사용자 확인 뒤 수용.
- 2)~4)가 맞으면 평가 측은 코드 보완 지시를 내지 않는다. 화면에서 사용자가 새로 요구하는 것은 새 티켓으로 따로 낸다(이 PR을 다시 열지 않는다).

■ 7. 미검증 (평가 측이 사용자 실사용으로 확인, 구현 측 조치 불필요)
- 운영 데이터 화면, 운영 Drive 의견이 행에 붙는 비율, 실제 엘박스 답변의 결과 블록 준수율, 붙여넣은 답변 문장의 인젝션 탐지(미구현 — 표시는 textContent라 실행되지 않음).

■ 참고 문서
- docs/handoff/TK-126_v014_screen_rework.md, TK-127_drive_reference_row_integration.md, TK-128_external_ai_prompt_tier3_and_answer_import.md (사용자 원문·원문 대응표·원인 상세).


## 2-3-1. #183 1차 판정 — 보완 1건 (10-25, 사용자 지시 '126~128 평가')

[Antigravity 보완 지시 — PR #183(head 7946aaf) 1차 판정: 보완 1건(CodeQL 새 경고 게이트 실패). 2026-10-25]

■ 판정 요약
- PR diff = 평가 측 수정본(주석 1줄 차이뿐), 필수 시험 CI 전부 성공, 평가 측 재실행 시험 실패 0, 탐지 점수 불변(dev 82.6 / holdout 81.9 / 오탐 0, 회귀 게이트 '회귀 없음'). 화면은 사전 검증 화면과 같다.
- 실패 1건: 'CodeQL 새 경고 게이트' — py/polynomial-redos 5건(심각도 7.5). 이것만 고치면 수용 절차 5)(사용자 화면 확인)로 넘어간다. 원인은 평가 측 수정본에 있었다(사전 검증에서 CodeQL을 돌리지 않음).

■ 원인 (줄 번호는 7946aaf의 packages/pii_engine/detector.py)
1. 이번 PR의 가림 API(POST /projects/{id}/external-ai/prompt-texts)가 사용자 입력을 PIIEngine.mask_text → detect()에 그대로 넘긴다. CodeQL이 이 경로를 '외부 입력 → 다항 시간 정규식'으로 잡았다: 43행 CORP/RRN_LABEL_PREFIX_RE(885행 사용, 2건), 112행 ACCOUNT_LABELLED_RE(905행), 38행 BUSINESS_REG_LABELLED_RE(912행), 1024행 re.search(r"\s*군$", …).
2. 공통 원인: `\s*[:：]?\s*`처럼 공백을 먹는 부분이 선택 요소를 사이에 두고 연달아 있어, 같은 공백을 여러 방식으로 나눠 맞추며 되짚는다(겹치는 \s*).
3. 경고 목록 밖이지만 실제로 가장 느린 것: 505행 MEDICAL_DIAGNOSIS_RE(`(…)?\s*(…)?\s*(?:에서)?\s*` — 공백 150자에 2.8초)와 511행 MEDICAL_PRESCRIPTION_RE(앞 `\s*…\s*` + 묶음 안의 \s — '처방' 뒤 공백 2,000자에 48초). 평가 측 재현: 라벨 뒤 공백 200자 9~13초, 400자 40초 초과(고치기 전).

■ 고칠 것 — 평가 측 수정본을 그대로 적용
- PR 브랜치에서: git apply --3way docs/handoff/patches/TK-128_pii_redos_fix_on_183.diff (평가 브랜치 커밋, 7946aaf 기준; 2개 파일: packages/pii_engine/detector.py 18줄 추가·14줄 삭제, tests/test_pii_redos_linear.py 새 파일 51줄)
- 수정 원리: 의미가 같은 겹침 없는 꼴로 바꾼다. `X\s*[:：]?\s*` → `X\s*(?:[:：]\s*)?`, `A\s*(?:B)?\s*` → `A(?:\s*B)?\s*`, `(?:P)?\s*(?:Q)?\s*(?:R)?\s*` → `(?:P\s*)?(?:Q\s*)?(?:R\s*)?`, `\s*군$` → `군$`. 대상: 31·38·42·43·70·79·86·98·112·411·412·506·512행, 1024행.
- 처방(512행)은 앞 \s*를 없애고 묶음 클래스가 공백을 함께 읽게 했다. 그래서 1034행 뒤에서 위치(start·end)를 묶음 앞뒤 공백만큼 줄인다(문구 med_text는 원래도 strip).

■ 평가 측 사전 검증 결과 (7946aaf + 수정본)
- 시간: 모든 라벨 + 공백 2,000자 ≤0.01초, 8,000자 ≤0.03초. 가림 API 최대 입력(200개 × 2,000자, 최악 라벨) 전체 0.84초.
- 탐지 동등성: 시험 자료의 한국어 문장 9,722개에서 고치기 전후 detect() 결과(종류·시작·끝·문구) 차이 0. 의도된 차이 1꼴: '처방 5mg …'처럼 처방어 바로 뒤에 용량이 오면 위치가 앞 공백 1자를 빼고 잡힌다(문구 동일, 가림 범위만 공백 1자 줄어듦).
- 점수: scorecard dev 82.6 / holdout 81.9 / 오탐 0 / 인젝션 방어(불변), score_gate 통과, regression_gate(기준 e980640) 회귀 없음.
- 시험: 새 tests/test_pii_redos_linear.py 13건 통과(라벨별 길이 4배 시간 비 < 8, 상한 2초, 탐지 결과 고정). 개인정보·보고서·작업공간·TK-126 시험 119건 실패 0. check_test_edits 통과.
- 미검증: CodeQL 재분석 결과(평가 측에서 CodeQL을 돌릴 수 없음 — 이 PR CI의 'CodeQL 새 경고 게이트'로 확인).

■ 하지 않을 것
- 가림 API를 없애거나 입력을 줄이는 것으로 경고를 피하지 않는다(사용자 요구 기능). 정규식의 탐지 범위(무엇을 잡는지)를 바꾸지 않는다. 수정본 밖의 변경을 섞지 않는다.

■ 제출물·수용 기준
- 같은 PR에 커밋 1개(끝 `Agent: implementer`). 본문에 'CodeQL 새 경고 게이트' 결과와 pytest -q tests/test_pii_redos_linear.py tests/test_pii_and_claims.py tests/test_tk126_flat_tabs_answer_import.py 결과를 붙인다.
- 평가 측 확인: CodeQL 새 경고 게이트 성공 + 필수 CI 성공 + diff = 수정본. 맞으면 코드 보완 지시 없이 사용자 화면 확인 단계로 간다.
- 개인정보 엔진 변경이므로 평가 측이 수용 SHA에서 verify_all 1회를 돈다(AGENT_ROLES 2.1).


## 2-4. TK-129 보고서에 외부 AI 답변 포함 (10-25, 사용자 지시 'TK-129 착수')
TK-126·127·128 PR 병합 뒤 착수. 평가 측이 그 수정본 위 사본에서 사전 검증했다. 아래가 사용자에게 낸 지시문 전문이다.

[Antigravity 지시 — TK-129 보고서에 외부 AI 답변 포함, PR 1개. 2026-10-25]

■ 이 지시의 목적: 한 번에 수용
사용자 요구: "AI 검토내용이 표에 반영된 후 다시 보고서를 생성할때, 그 내용이 보고서 내용에 반영되도록" (답변은 브라우저에 저장하고, 공유는 보고서로 한다 — 사용자 결정). 평가 측이 TK-126·127·128 수정본 위 사본에 아래 수정을 먼저 적용해 시험으로 확인했다. 구현 측은 **검증된 수정본을 그대로 적용**하고 '제출 전 확인'만 돌린다. 새 설계·추가 개선·리팩터링을 하지 않는다.

■ 1. 작업 절차 (이 순서 그대로)
1) TK-126·127·128 PR이 Steve_ACASiaLAW에 병합된 뒤 시작한다(이 수정본은 그 수정본 위에서 만들었다).
2) 새 브랜치에서: `git apply --3way docs/handoff/patches/TK-129_prevalidated_after_TK126.diff` (9개 파일, 249줄 추가·14줄 삭제: apps/api/schemas.py, apps/api/routers/reports.py, apps/web/static/{app.js,report-workbench.js}, packages/report_engine/{external_answers.py(새),pdf_report.py,docx_report.py,exporters.py}, tests/test_tk129_report_external_answers.py(새)). 평가 측 확인: b68e70f + TK-126 수정본 위에 그대로 적용된다.
3) 충돌이 나면(TK-126 PR이 수정본과 다르게 병합된 곳만) 양쪽을 살려 합치고 PR 본문에 파일·줄·처리를 적는다. 충돌이 없으면 패치 외 변경을 하지 않는다.
4) '제출 전 확인' 결과를 PR 본문에 붙인다. 커밋 끝 `Agent: implementer`. PR 대상 Steve_ACASiaLAW, 제목 `feat(report): TK-129 표에 반영한 외부 AI 답변을 보고서에 포함`.

■ 2. 원인과 수정본이 하는 일 (줄 번호는 b68e70f + TK-126 수정본 기준)
원인: 보고서는 서버가 실행 결과 고정본으로만 만든다. 화면 요청(report-workbench.js 72행)과 요청 모델(ReportRequest, schemas.py 174~181행)에 답변 칸이 없고, 고정본(_snapshot, reports.py 542행)에도 자리가 없어서, 브라우저에 저장된 답변이 보고서로 갈 길이 없다.
1. 요청 모델: ExternalAiAnswer(code ^[AB]\d{1,3}$, item_id ≤300, verdict·basis·summary ≤1000, applied_at ≤60). ReportRequest.external_ai_answers(≤400, 기본 []). report-jobs는 model_dump()를 저장·복원하므로 그대로 이어진다.
2. 새 모듈 packages/report_engine/external_answers.py: 제목 "외부 AI 참고 의견 (사용자 입력, 공식 확인 아님)", 안내문, 머리글 [번호, 대상, 판정, 근거, 요지, 반영 시각]. 대상 문구는 서버가 고정 결과에서 다시 찾는다(documents[].review_items의 item_id → 인용 표기/주장 문장, 참고문헌 행 id `{문서 id}_REFERENCE_{claim_id}` → claim_quote). 브라우저가 보낸 대상 문구는 받지 않는다.
3. reports.py: (a) 219행 _resolve_run 끝 — 표에 없는 item_id면 422(unknown_item_ids). (b) 247행 _build_draft — checked_answers 결과를 _snapshot(external=…)으로. (c) 542행 _snapshot — external이 있을 때만 frozen["external_ai_answers"](없으면 키 없음 → 기존 고정본 해시 불변). (d) 640행 확정 — external=frozen.get("external_ai_answers")를 반드시 넘긴다(확정은 고정본을 새로 만들므로 빠뜨리면 확정본에서 답변이 사라진다).
4. 형식: PDF(pdf_report.py 290행 뒤)·Word(docx_report.py 226행 뒤)에 '3. 법률적으로 무리한 주장' 다음 절, Excel(exporters.py 236행 앞) '외부AI참고의견' 시트 — 모두 답변이 있을 때만. JSON은 review_snapshot에 자동 포함. CSV·manifest·highlight 제외. 공유용 가림은 shareable_snapshot이 고정본 전체를 가리므로 추가 코드 없음. Excel 수식 방지는 기존 safe_cell.
5. 화면: app.js externalStoreKey·loadExternalStore에 (projectId, runId) 인자(기본 현재 값), externalAnswersForReport(projectId, runId) 추가(번호·행이 모두 남은 답변만). report-workbench.js 생성 창에 답변이 있을 때만 체크 상자 "표에 반영한 외부 AI 답변 n건을 '외부 AI 참고 의견(공식 확인 아님)'으로 함께 싣기"(기본 선택), 요청 본문 external_ai_answers(체크 해제 시 []).

■ 3. 하지 않을 것 (넣으면 범위 밖으로 되돌린다)
- 답변의 서버 저장·DB 표·migrations(사용자 결정: 브라우저 저장).
- 답변으로 판정·등급·점수·요약·다른 절을 바꾸는 것. 보고서 다른 절의 순서·문구 변경.
- CSV·manifest·highlight에 답변 넣기.
- 브라우저가 보낸 대상 문구를 보고서에 쓰는 것(대상은 서버가 고정 결과에서 찾는다).
- 기존 시험 수정·삭제(이 수정본은 기존 시험을 고치지 않는다).

■ 4. 사전 검증 결과 (평가 측 재실행)
- 새 시험 tests/test_tk129_report_external_answers.py 5건 통과. 기능을 끈 사본(보고서 행 함수가 빈 목록)에서는 2건 실패 — 시험이 기능을 실제로 잡는다.
- 보고서·화면·API 관련 시험 2,022건 실패 0, 건너뜀 25(보고서를 다루는 기존 시험 전부 + TK-126 시험 묶음 + 새 시험).
- 확정(finalize)에 답변을 넘기지 않은 사본에서는 확정본 시험이 실패 — 3(d) 누락을 시험이 잡는다.
- 전체 tests(TK-126+129 적용 사본): 10,462건 중 TK-129 변경에 따른 실패 0(실패 5건은 TK-126 보충으로 고친 옛 단언 1건과 병렬 부하 시간 시험 4건 — 단독 재실행 통과).
- 미검증: 운영 보고서 실제 모양(긴 답변의 PDF 줄바꿈), 실제 엘박스 답변 분량.

■ 5. 제출 전 확인 (PR 본문에 결과 붙이기)
- pytest -q tests/test_tk129_report_external_answers.py tests/test_report_completion.py tests/test_report_timeline_exclusion.py tests/test_source_objects.py tests/test_identity_security.py tests/test_operations_completion.py tests/test_improvements.py tests/test_evidence_hardening.py tests/test_tk126_flat_tabs_answer_import.py tests/test_frontend_report_button.py tests/test_frontend_report_progress.py tests/test_api.py → 실패 0.
- python scripts/check_test_edits.py --base origin/Steve_ACASiaLAW → '기존 시험의 삭제·표시 변경 없음'.
- git diff --stat origin/Steve_ACASiaLAW → 위 9개 파일만.

■ 6. 평가 측 수용 절차 (이것만 본다 — 추가 요구 없음)
1) 필수 CI 성공(인용). 2) PR diff = 수정본(충돌 처리분 제외 차이 0). 3) 위 시험 평가 측 재실행 실패 0. 4) 탐지 diff 0·고정·은퇴 점수 불변(보고서 엔진만 변경). 5) 답변을 반영한 실제 보고서(PDF·Word·Excel) 캡처를 원문 대응표(TK-129 1~3)와 함께 사용자에게 제시 → 사용자 확인 뒤 수용.
- 2)~4)가 맞으면 평가 측은 코드 보완 지시를 내지 않는다. 새 요구는 새 티켓으로 따로 낸다.

■ 참고 문서
- docs/handoff/TK-129_report_includes_external_ai_answers.md (사용자 원문·원문 대응표·원인·줄 번호 상세).



## 2-4-1. #185 1차 판정 — 보완 2건 (10-28, 인계 지시 '#185 상태 확인·독립 평가')

```
[Antigravity 보완 지시 — PR #185(TK-129, head 9ed54c5) 1차 판정: 보완 2건. 2026-10-28]

■ 판정 요약
- 같은 SHA CI(인용): 테스트 3종·Docker OCR readiness·CodeQL 새 경고 게이트·점수 하락 게이트·은퇴 세트 비교 모두 성공.
- 평가 측 재실행: 제출 전 확인 시험 묶음 실패 0, check_test_edits '기존 시험의 삭제·표시 변경 없음'.
- 사전 검증 수정본 밖 변경(item_id 고정, 오염 답변 삭제, 비공식 표시 강화, 422 검증 강화)은 방향을 수용한다. 0.15.0(TK-128)에서는 프롬프트를 다시 만들면 번호가 다른 행에 재할당되어, 저장된 답변이 엉뚱한 행에 붙을 수 있었다. 이번 PR이 이를 막는다(분류 fixed).
- 결함 1건: 참고문헌 별도 행 id가 서버와 화면에서 서로 다르다. 그 결과 보고서에 다른 문장이 대상으로 실리거나, 보고서 생성 전체가 422로 막힌다.
- 수용 절차 5)의 화면 자료가 부족하다: 캡처 04에 답변 상자가 보이지 않고, 실제 보고서(PDF·Word·Excel) 캡처가 없다.

■ 원인 1 — 참고문헌 별도 행 id 불일치 (줄 번호는 9ed54c5 기준)
- 화면: app.js 2562~2563행 `unmatchedReferences.forEach((entry, index) => … referenceObservationRow(entry, index))`. 2133행 id는 `${문서}_REFERENCE_${observation.claim_id || index}`이다.
  · index는 '행에 붙지 못한 관찰 목록'의 순번이다. 그 목록은 모든 문서를 통틀어 매겨진다.
- 서버: external_answers.py `_targets` 4)는 `targets.setdefault(f"{doc_id}_REFERENCE_{idx}", quote)`로 등록한다.
  · idx는 '그 문서 observations 배열 전체'의 순번이다. 행에 붙은 관찰도 세고, 문서마다 0부터 다시 센다.
- claim_id가 없는 관찰은 실제로 생긴다.
  · rag_engine/provision_quotes.py의 결정론 관찰(QUICK·LOCAL_ONLY 경로, review.py 387·707행)은 claim_id를 넣지 않는다.
  · 모델 관찰 스키마(review.py 20~29행)에도 claim_id가 없다(문장별 경로 690행에서만 채운다).
- 평가 측 재현(합성 입력, external_answers._targets·validate_answers 직접 호출):
  P1. 한 문서의 관찰 [o0(claim_id 있음, 인용 행에 붙음), o1(claim_id 없음)].
      · 화면 별도 행: o1, id `d1_REFERENCE_0`.
      · 서버가 `d1_REFERENCE_0`으로 찾는 문장: o0의 claim_quote.
      · 결과: 보고서 '외부 AI 참고 의견' 표의 대상 칸에 다른 관찰 문장이 실린다(잘못된 귀속).
  P2. 두 문서가 각각 claim_id 없는 미연결 관찰 1개.
      · 화면 id: `d1_REFERENCE_0`, `d2_REFERENCE_1`.
      · 서버: `d2_REFERENCE_1`이 없다 → 422('표에 없는 항목'). 답변이 실린 보고서 전체를 만들 수 없다.
- 기존 새 시험(test_legacy_fallback_items_and_observation_without_claim_id_are_accepted)은 문서 1개·관찰 1개라 두 순번이 우연히 같아 이 결함을 잡지 못한다.

■ 고칠 것 1 — 평가 측 수정본을 그대로 적용
- 수정본: docs/handoff/patches/TK-129_reference_row_id_fix_on_185.diff(9ed54c5 기준, 3개 파일).
  적용: PR 브랜치에서 `git fetch origin evaluator/round8-promotion && git show origin/evaluator/round8-promotion:docs/handoff/patches/TK-129_reference_row_id_fix_on_185.diff | git apply --3way` (평가 브랜치 커밋 fcef610).
- 원리: 별도 행 id를 '매칭 결과에 따라 달라지는 순번'이 아니라 '문서 안 관찰 순번'으로 고정한다. claim_id가 없을 때 id는 `{문서}_REFERENCE_O{n}`이다. 화면과 서버가 같은 규칙을 쓰므로, 서버가 화면의 매칭 알고리즘을 복제할 필요가 없다.
  · app.js `attachReferenceObservations`: `observations.forEach((observation, observationIndex) => …)`로 바꾸고, entry에 `observation_index`를 싣는다.
  · `referenceObservationRow`: index 인자를 없애고 id에 `observation.claim_id || \`O${observation.observation_index}\``를 쓴다. 2563행 호출부도 맞춘다.
  · external_answers.py `_targets` 4): `targets.setdefault(f"{doc_id}_REFERENCE_{obs.get('claim_id') or f'O{idx}'}", quote)` 한 줄로 바꾼다. 옛 `_REFERENCE_{idx}` 등록은 지운다. docstring도 맞춘다.
- 시험(같은 파일에 추가, 기존 시험 수정 없음):
  · 기존 새 시험의 B1 item_id를 `_REFERENCE_O0`으로 바꾼다. 이 PR에서 새로 만든 시험이므로 기존 시험 변경이 아니다.
  · test_reference_rows_without_claim_id_resolve_to_their_own_observation: 양성 3꼴과 대조 3건.
    - 양성 3꼴: 앞 관찰이 행에 붙은 경우, 문서 2개, 한 문서에 관찰 2개.
    - 대조 3건: 옛 순번 꼴 id는 422.
  · test_browser_reference_row_ids_match_server_targets: node로 app.js의 함수 3개를 실제 실행한다. 화면 행 id·문장이 서버 `_targets`의 키·문장과 같은지 교차 확인한다.
- 이미 브라우저에 저장된 `_REFERENCE_<숫자>` 답변은 새 id와 맞지 않아 표·보고서에 붙지 않는다. 번호는 프롬프트를 다시 만들 때 정리된다(rememberPromptCodes). 이는 이 PR의 구형 답변 배제 원칙과 같다. 이전 처리 코드를 따로 넣지 않는다.

■ 원인 2 — 사용자 확인 자료 부족 (수용 절차 5)
- 캡처 04('표 행에 렌더링된 외부 AI 답변 박스')는 표 머리글까지만 보이고 알림창이 가리고 있다. 답변 상자가 화면에 없다. 캡처 01과 사실상 같은 화면이다.
- 지시서 2-4절 6) 5)가 요구한 '답변을 반영한 실제 보고서(PDF·Word·Excel) 캡처'가 없다.

■ 고칠 것 2 — 캡처 교체·추가 (docs/handoff/screens/tk129/)
- 04 교체: 답변을 반영한 행까지 스크롤하고 알림이 사라진 뒤 찍는다. '외부 AI 답변 A1 (공식 확인 아님)' 상자와 판정·근거·요지가 다 보여야 한다. 긴 문구 1건(근거 200자 이상)을 포함한다.
- 새로 06~08: 초안 보고서의 실제 산출물을 찍는다.
  · PDF: '외부 AI 참고 의견 (사용자 입력, 공식 확인 아님)' 절 쪽. 긴 답변의 줄바꿈이 보여야 한다.
  · Word: 같은 절.
  · Excel: '외부AI참고의견' 시트의 안내 행·머리글·'공식 여부' 열.
- 09(선택): 참고문헌 별도 행(claim_id 없는 관찰)에 답변을 반영한 경우의 보고서 표 대상 칸. 고칠 것 1 확인용.
- PR 본문 대응표 '구현 위치' 칸의 캡처 번호를 위에 맞게 고친다.

■ 평가 측 사전 검증 결과 (9ed54c5 + 수정본, 저장소 밖 임시 사본, 평가 측 재실행)
- tests/test_tk129_report_external_answers.py 11건 통과.
- 수정본에서 제품 코드만 9ed54c5로 되돌린 사본에서는 새 시험 3건이 실패한다. 시험이 결함을 실제로 잡는다.
- 관련 묶음 17개 파일(제출 전 확인 목록 + TK-126·citation_groups·summary_compact·f2 화면·drive_rag_relevance·external_ai_prompt) 356건 실패 0.
- check_test_edits(기준 3fee071): '기존 시험의 삭제·표시 변경 없음'. check_hardcoding_diff(기준 3fee071) 새 줄에 시험 입력 값·낱말 없음.
- 탐지 엔진 변경 없음(보고서·화면만). 점수 재측정 대상 아님. 같은 SHA CI로 확인한다.
- 미검증:
  · 운영 데이터의 claim_id 없는 관찰 빈도.
  · 레거시 fallback(review_items가 없는 옛 실행) 경로에서 화면·서버의 finding 묶음 차이. document_id 없는 finding은 화면에만 FINDING 행이 생길 수 있다. 옛 실행 한정이라 이번 보완 범위 밖이다.
  · 실제 보고서 화면(캡처는 구현 측 제출물).

■ 하지 않을 것
- 화면의 매칭 알고리즘을 서버에 복제하지 않는다(수정본의 고정 id로 충분).
- 다른 행 종류(CITATION·FINDING·review_items)의 id 규칙을 바꾸지 않는다. 보고서 다른 절, 판정·점수를 바꾸지 않는다.
- 기존 시험을 수정하거나 지우지 않는다. 수정본 밖 변경을 섞지 않는다.

■ 제출물·수용 기준
- 같은 PR에 커밋 1~2개(끝 `Agent: implementer`): 수정본 적용 1개, 캡처 교체·추가 1개.
- PR 본문에 다음을 붙인다:
  · pytest -q tests/test_tk129_report_external_answers.py tests/test_tk126_flat_tabs_answer_import.py tests/test_report_completion.py 결과.
  · check_test_edits 결과.
  · 새 head의 CI 결과.
- 평가 측이 확인할 것:
  · 필수 CI 5종이 새 head와 같은 SHA에서 성공.
  · diff = 기존 9ed54c5 + 수정본(+캡처).
  · 캡처 04·06~08이 위 조건을 충족.
- 맞으면 코드 보완 지시 없이 캡처와 원문 대응표를 사용자에게 제시한다 → 사용자 확인 → "#185병합".
```



## 2-4-2. #185 2차 판정 — 보완 1건(작음) (10-28, 사용자 지시 '#185 보완 커밋 확인')

```
[Codex(구현 대행) 보완 지시 — PR #185(TK-129, head bdc242c) 2차 판정: 보완 1건(작음). 2026-10-28]

■ 판정 요약
- 같은 SHA CI(인용): 테스트 3종·Docker OCR readiness·CodeQL 새 경고 게이트·점수 하락 게이트·은퇴 세트 비교 모두 성공.
- 1차 보완 1(참고문헌 행 id): 이행. 평가 측 확인: 코드·시험 diff(aee705d)가 평가 측 수정본과 +/− 줄 단위로 같다(101줄).
- 1차 보완 2(캡처): 이행. 04에 긴 답변 상자가 보이고, 06 PDF·07 Word·08 Excel 캡처가 추가되었다.
- 평가 측 재실행(bdc242c): 관련 17개 파일 356건 실패 0. check_test_edits '기존 시험의 삭제·표시 변경 없음'.
- 새 결함 1건(캡처 06·07에서 발견): '외부 AI 참고 의견' 표의 열 너비 개수가 머리글 개수와 맞지 않는다.

■ 원인 (bdc242c 기준)
- 538958a에서 EXTERNAL_AI_HEADERS에 7번째 열 '공식 여부'를 추가했다(external_answers.py). 그런데 너비 목록은 6개 그대로다.
  · docx_report.py 233행: table(EXTERNAL_AI_HEADERS, external_rows, [0.5, 1.5, 0.9, 1.4, 1.9, 0.8])
  · pdf_report.py 298행: table([EXTERNAL_AI_HEADERS, *external_rows], [30, 120, 60, 110, 120, 50])
- Word: table 헬퍼(docx_report.py 64~96행)가 zip(row.cells, widths)로 너비·세로 정렬·셀 여백을 준다. 그래서 7번째 열은 서식이 빠진다. 캡처 07에서 '공식 여부' 열이 표 테두리 밖에 따로 놓였다. PR 본문은 이를 'LibreOffice 배치 차이'로 적었지만, 원인은 너비 목록 누락이다(렌더러 문제가 아님).
- PDF: 7번째 열 너비가 자동이 되어 표가 본문 폭(A4 − 좌우 18mm ≈ 493pt)을 넘는다. 캡처 06에서 이 표만 다른 표보다 좌우로 튀어나와 있다.

■ 고칠 것 — 평가 측 수정본 그대로 적용
- 적용(PR 브랜치에서):
  `git fetch origin evaluator/round8-promotion && git show origin/evaluator/round8-promotion:docs/handoff/patches/TK-129_external_table_widths_fix_on_185.diff | git apply --3way`
  4개 파일, 34줄 추가·4줄 삭제.
- external_answers.py: 머리글 옆에 너비 상수를 둔다.
  · EXTERNAL_AI_PDF_WIDTHS = [28, 100, 55, 125, 95, 47, 40] (합 490pt)
  · EXTERNAL_AI_DOCX_WIDTHS = [0.4, 1.3, 0.8, 1.6, 1.4, 0.8, 0.7] (합 7.0in = Letter 본문 폭)
  · 머리글과 너비를 한곳에서 함께 바꾸게 한다.
- docx_report.py·pdf_report.py: 위 상수를 쓴다.
- 시험 test_external_section_columns_have_widths_inside_page_in_docx_and_pdf:
  · 상수 개수 = 머리글 개수.
  · 합이 본문 폭 이하.
  · 실제 생성한 Word 표의 모든 행·7열에 지정 너비와 셀 여백(w:tcMar)이 있다.
  · PDF에 '공식 여부' 열이 있다.
- 캡처 06·07을 다시 찍는다. 표가 본문 폭 안에 있고, '공식 여부' 열이 표 안에 있어야 한다. PR 본문의 'LibreOffice 배치 차이' 문구는 원인 설명으로 고친다.

■ 평가 측 사전 검증 (bdc242c + 수정본, 저장소 밖 사본, 평가 측 재실행)
- 새 시험 통과. 너비를 6개로 되돌린 사본에서는 새 시험이 실패한다(7번째 셀 너비 불일치). 시험이 결함을 실제로 잡는다.
- 관련 17개 파일 357건 실패 0. check_test_edits·check_hardcoding_diff 통과.
- PDF 실제 생성: 표가 다른 표와 같은 본문 폭 안에 들어오고, 긴 근거 줄바꿈이 정상이다(평가 측 렌더링 확인).
- 미검증: Word 실제 화면. 평가 측 환경의 LibreOffice가 docx를 열지 못했다. 구조는 시험으로 확인했다. Microsoft Word·Excel 직접 표시도 미확인이다.

■ 하지 않을 것
- 머리글·열 순서·문구, 다른 표의 너비, 보고서 다른 절은 바꾸지 않는다.
- 수정본 밖 변경을 섞지 않는다. 기존 시험을 수정하지 않는다.

■ 제출물·수용 기준
- 커밋 1~2개(수정본 적용, 캡처 06·07 교체). 끝에 `Agent: implementer`.
- 필수 CI 5종이 새 head와 같은 SHA에서 성공해야 한다. PR 코멘트 3줄('검토 요청'은 CI 완료 뒤).
- 평가 측 확인: diff = bdc242c + 수정본(+캡처), 캡처 06·07 확인.
- 맞으면 평가 측이 캡처 01~08과 원문 대응표를 사용자에게 제시한다 → 사용자 화면 확인 → "#185병합".
```

## 2-5. #190 TK-127 2단계 — 구조 ID 연결과 식별자 부재 규칙 결정 (10-28, 사용자 결정 '연결 허용·승격만 금지')

- 계기: 구현 측(Codex 대행) 메모 `docs/handoff/requests/TK-127_stage2_existing_test_conflict_20261028.md`(브랜치 `antigravity/tk127-stage2-drive-citation` `572e442`). 이슈 #190·인계문의 '식별자 부재 시 자동 연결과 SUPPORTED 승격 모두 금지'를 구조 ID 연결에도 적용하면 기존 시험 `test_rag_observations_attach_to_rows_and_bottom_section_is_gone`(TK-126·127 1단계, 사용자 확인·0.15.0 배포 동작)과 충돌한다.
- 사용자 결정(10-28): **연결 허용·승격만 금지.** 승인 설계 메모(#186 10차) 2절 2)의 순서를 그대로 따른다.
  1. 1순위 구조 연결(관찰 `claim_id` → `claims[].citation_ids` → 행 `citation_id`, 같은 문서)은 식별자 유무와 관계없이 그 행에 '참고(비구속·공식 확인 아님)'로 붙인다. 근거: 그 관찰은 RAG 검토가 바로 그 주장에 대해 만든 것이라 텍스트 추측 연결이 아니다.
  2. `reference_status=SUPPORTED` 승격은 관계가 SUPPORTS이고, 행의 전체 식별자(사건번호 전체 또는 법령명+조문 전체)가 후보 발췌에 온전히 있고 충돌이 없을 때만 한다. 구조 연결이어도 식별자 부재·충돌이면 승격하지 않고 설계 5항의 미확정 상태로 둔다. 화면 배지(부합/불부합/맥락 참고/근거 부족)는 관계 표시라 그대로 둔다.
  3. 구조 연결이 없을 때(2·3순위)는 설계 그대로: 전체 식별자 일치 필수. 충돌은 Hard Stop, 부재는 Fallback 금지 → 행에 붙이지 않고 별도 '참고문헌 대조 의견' 행(TK-129 id 규칙 `{문서}_REFERENCE_{claim_id 또는 O순번}` 유지).
  4. `official_status`는 어느 경우에도 바꾸지 않는다.
- 기존 시험: 수정하지 않는다(위 1이 기존 단언을 그대로 만족). 평가 측 확인: Linux에서 `tests/test_tk126_flat_tabs_answer_import.py` 통과(10-28 #185 사본 재실행 356건 실패 0에 포함). 구현 측 Windows의 화면 시험 4건 실패는 Chromium 미설치 환경 문제로 판단하고, 판정은 같은 SHA CI로 한다.
- 새 시험(규칙마다 양성 3·대조 3 이상): ① 구조 연결 + 발췌 식별자 부재 → 행에 붙음·SUPPORTED 아님(서로 다른 3꼴) ② 구조 연결 + 식별자 충돌 → 행에 붙음·SUPPORTED 아님 ③ 구조 연결 + 전체 식별자 일치 + SUPPORTS → SUPPORTED(양성 3) ④ 구조 연결 없음 + 식별자 부재·충돌 → 별도 행·승격 없음. 서버·브라우저 결과가 같음을 node 교차 시험으로 확인한다.
- 통제 벤치마크: 설계 4) 그대로. 유형 N3·N4(식별자 부재)는 '구조 연결 없음' 사례로 구성한다. 구조 연결 사례는 '연결 정확도'와 'SUPPORTED 승격 정확도'를 따로 집계한다(구조 연결로 붙었는데 승격된 부재 사례 = FP).
- 이슈 #190 수용 기준 1항('식별자 부재 반례에서 연결과 SUPPORTED 승격이 모두 차단')은 '구조 연결이 없는 경우'로 읽고, 구조 연결 사례는 '승격 차단'만 본다.


## 2-4-3. #185 3차 확인 — 코드 수용, 사용자 화면 확인 대기 (10-28, 사용자 지시 '#185,#191 평가')

- head `89cf414`: `c23bc00` 코드·시험 diff = 평가 측 수정본(줄 단위 일치), 캡처 06·07 교체(표가 본문 폭 안, '공식 여부' 열이 표 안 — 평가 측 열람). 같은 SHA CI 전부 성공(인용, 두 테스트 실행 모두). 평가 측 사전 검증 사본과 코드 동일(357건 실패 0).
- 남은 것: 사용자 화면 확인(캡처 01~08·원문 대응표) → "#185병합". 병합 순서는 #185 먼저(2-6절).

## 2-6. #191 TK-127 2단계 1차 판정 — 보완 2건 + 병합 순서 (10-28, 사용자 지시 '#185,#191 평가')

```
[Codex(구현 대행) 보완 지시 — PR #191(TK-127 2단계, head faafb5e) 1차 판정: 보완 2건 + 병합 순서 1건. 2026-10-28]

■ 판정 요약
- 같은 SHA CI(인용): 점수 하락 게이트·은퇴 세트 비교·Docker OCR·CodeQL 새 경고 게이트 성공. 테스트는 같은 SHA의 두 실행 중 하나(run 40696157071)는 3종 성공, 다른 하나(run 40696164483)는 'SQLite + 인프로세스 Worker'에서 기존 시험 1건 실패(아래 '관찰' 참조).
- 구조·계약: 사용자 결정(10-28 '연결 허용·승격만 금지')과 승인 설계 #186을 지킨다(평가 측 코드 검토).
  · 1순위 구조 연결은 식별자와 무관하게 붙이고, SUPPORTED는 SUPPORTS·전체 식별자·충돌 없음일 때만 준다. 그 밖은 PENDING_REVIEW.
  · 비구조 연결은 근접 식별자 → 제한 fallback(전체 식별자·15자·고유 단일 후보) 순서로만 한다.
  · official_status를 보존하고, 화면·보고서 4종에 비공식 표시를 한다. TK-129 id 규칙 `_REFERENCE_O{n}`을 유지한다.
- 평가 측 재실행(faafb5e): TK-127 새 시험 2개 파일 통과. check_test_edits·check_hardcoding_diff·평가 세트 문구 대조·보호 경로 점검 통과.
- 결함 2건(평가 측 재현):
  · ① Drive 인용 검색이 색인 크기에 비례해 매우 느리다.
  · ② 법령 인용의 조문 식별자가 실제 추출기 출력과 맞지 않는다.

■ 원인 ① — search_citation 성능 (packages/rag_engine/library.py 767~792행, reference_binding.py 77~95행)
- review.py 283행이 문서의 인용마다 lib.search_citation(citation)을 부른다.
- search_citation은 적격 파일마다 FTS5 표를 `WHERE file_id=? AND revision=?`로 읽는다. UNINDEXED 열이라 파일마다 전체 표를 훑는다.
- 그렇게 읽은 모든 청크에 citation_excerpt를 부른다. citation_excerpt(83행)는 식별자가 있는지 보기 전에 글자마다 정규식(authority_text)을 돌린다.
- 평가 측 측정(합성 색인, 청크 1,000자, 인용 10개):
  · 1,000청크 9.1초 · 2,000청크 16.7초 · 4,000청크 34.8초 · 8,000청크 73.5초.
  · 청크 1개·인용 1개당 약 0.9ms다. 인용 30개인 서면이면 8,000청크 색인에서 3분 넘게 늘어난다.
  · 운영 색인 크기는 미측정이다.

■ 원인 ② — 조문 식별자 (reference_binding.py identifier 28~47행·identifier_match 68~73행, app.js referenceIdentifier 2066행·referenceIdentifierMatch 2102행)
- (a) 실제 추출기(packages/legal_engine/citation_extractor.py)는 '민법 제103조의2'를 article '103의2'로 남긴다.
  · identifier는 이것을 '제103의2조'로 만든다. ARTICLE_RE에 맞지 않아 None이 된다.
  · 결과: '조의N' 인용은 Drive 대조·승격 대상에서 모두 빠진다(평가 측 재현: extract_from_text 출력으로 identifier None).
  · article '7' + sub '3' 꼴도 sub를 무시한다.
- (b) 항을 든 인용('근로기준법 제23조 제1항' → '제23조제1항')을 그 조의 본문 발췌('근로기준법 제23조(해고 등의 제한) ① 사용자는…')와 대조하면 문제가 생긴다.
  · 발췌의 '제23조'를 다른 조문으로 보아 conflict=True가 된다.
  · 같은 조문을 '충돌'로 판정해, 구조 연결은 PENDING_REVIEW, 비구조 연결은 Hard Stop이 된다.
  · 평가 측 재현: identifier_match → {'full': False, 'conflict': True}. 같은 조 제1항 표기 발췌는 full, 제2항 발췌는 conflict.

■ 고칠 것 — 평가 측 수정본 그대로 적용 (①②, 4개 파일, +127/−34)
- 적용(PR 브랜치에서, rebase·force-push 없이 새 커밋):
  `git fetch origin evaluator/round8-promotion && git show origin/evaluator/round8-promotion:docs/handoff/patches/TK-127_stage2_fixes_on_191.diff | git apply --3way`
- ① library.search_citation:
  · 색인을 한 번만 `SELECT file_id, revision, page, start, text FROM chunks WHERE instr(text, ?) > 0`으로 훑는다. 인자는 식별자 앵커의 가장 긴 숫자열이다.
  · 적격·현재 revision·사례표 제외를 Python에서 거른다.
  · 정렬(file_id, page, start)과 limit은 그대로다.
  · reference_binding.citation_excerpt: `anchor not in authority_text(text)`로 먼저 거르고, 있을 때만 원문 위치를 계산한다(IGNORED_CHAR_RE 한 번).
- ② identifier: article을 `제?N조?(의M)?`로 읽어 '제N조의M'으로 만든다(sub 열 포함). 항·호는 이전처럼 덧붙인다.
- ② identifier_match: 발췌의 조문 표기를 가장 길게 읽는다. 뒤에 숫자가 이어지면 잘린 표기라 무효다.
  · article_compatible(같은 조·조의N이고 항·호가 서로 접두 관계)이면 같은 조문으로 본다.
  · 다른 조·다른 항·조의N 차이는 충돌로 유지한다.
  · app.js referenceIdentifier·referenceIdentifierMatch·referenceArticleCompatible도 같은 규칙이다(서버·브라우저 동일).
- 시험(새 시험만 추가, 기존 시험 수정 없음):
  · test_paragraph_and_sub_article_citations_match_their_own_article: 양성 3꼴 — 항 인용 대 ①표기 조문 본문, article '103의2', article+sub. 서버·Node 모두 연결과 SUPPORTED.
  · test_different_article_paragraph_or_sub_article_is_conflict: 대조 3꼴 — 다른 항, 조의N 인용 대 본조, 본조 인용 대 조의N. 연결은 유지, 승격은 없고 conflict.

■ 평가 측 사전 검증 (faafb5e + 수정본, 저장소 밖 사본, 평가 측 재실행)
- 성능: 같은 합성 색인에서 1,000청크 0.05초 · 8,000청크 0.36초(인용 10개). 1,800청크·인용 14개 혼합 색인에서 10.72초 → 0.19초.
- 동등성: 검색 결과가 원래 구현과 완전히 같다(162건, 결과 해시 일치). 식별자 변형 11꼴을 넣었다: 공백·전각 공백·괄호·판결 표기·다른 사건번호 병기·조의N·제1030조 등. 다른 revision과 사례표 파일도 섞었다.
- 새 조문 시험 6건 통과. 원래 faafb5e 코드에서는 6건 중 4건 실패한다(결함을 잡음). 기존 test_complete_article_boundary(제8조제2항0 등 잘린 표기) 통과 유지.
- TK-127 시험 2개 파일 전부 통과. check_test_edits·check_hardcoding_diff·평가 세트 문구 대조 통과.
- 병합 사전 검증: #185(89cf414) + #191 + 이 수정본 + 아래 병합 보정을 합친 사본에서 관련 13개 파일 255건 실패 0. 넓힌 22개 파일 묶음은 465건 실패 0(조문 수정 전 사본).
- 미검증: 운영 Drive 색인 크기·검색 시간, Microsoft Word·Excel 직접 표시.

■ 병합 순서 — #185 먼저, 그 뒤 #191 (평가 측 병합 시험으로 확인)
- 두 PR이 app.js attachReferenceObservations·referenceObservationRow에서 충돌한다. 충돌 구간은 #191 쪽을 택한다(같은 `_REFERENCE_O{n}` 규칙, #191이 상위 집합). 주의: 파일 전체를 한쪽으로 덮어쓰면 #185의 applyStoredExternalAnswers 변경이 사라진다. 평가 측이 이것으로 TK-129 회귀 시험 실패를 재현했다. 충돌 구간만 고른다.
- 병합 뒤 #185의 test_browser_reference_row_ids_match_server_targets가 실패한다. 이 시험은 app.js에서 함수 3개만 뽑아 node로 돌리는데, 병합 뒤 attachReferenceObservations가 새 보조 함수를 쓰기 때문이다(ReferenceError).
- 보정: #185 병합 뒤 #191 브랜치에 Steve를 병합 커밋으로 들이고 다음을 적용한다.
  `git show origin/evaluator/round8-promotion:docs/handoff/patches/TK-127_integration_tk129_test_helper.diff | git apply --3way`
  · 상수 EXPLICIT_WHITESPACE_RE와 보조 함수 5개를 함께 뽑는다. 단언은 바꾸지 않는다.

■ 관찰 (판정 보류, 새 head CI로 다시 확인)
- 실패 시험: test_frontend_citation_groups.py::test_findings_from_one_citation_are_grouped(run 40696164483, 하위 summary 클릭 시간 초과 '보이지 않음').
- 평가 측 재현: 같은 시험을 단독으로 12회씩 돌렸다. Steve 기준 0/12 실패, faafb5e 0/12 실패. 병합 사본 묶음 실행에서도 통과했다.
- #191의 app.js 변경은 상태 줄·처리 기록 렌더 경로를 바꾸지 않는다.
- 새 head의 두 테스트 실행이 모두 성공하면 닫는다. 다시 실패하면 재렌더 경쟁(처리 기록 details가 다시 닫힘)을 원인 후보로 별도 티켓을 낸다. 시험을 약화하거나 건너뛰지 않는다.

■ 하지 않을 것
- 매칭 계약(1·2·3순위, 승격 조건, 15자·고유 단일 후보)과 화면·보고서 문구는 바꾸지 않는다.
- 기존 시험을 수정하지 않는다(병합 보정의 함수 목록 추가는 예외로 위에 명시). 수정본 밖 변경을 섞지 않는다.

■ 제출물·수용 기준
- 커밋: 수정본 적용 1개(`Agent: implementer`). #185 병합 뒤 Steve 병합 커밋 + 병합 보정 1개.
- 필수 CI 5종이 같은 SHA에서 성공해야 하고, 두 테스트 실행 모두 성공해야 한다. PR 코멘트 3줄('검토 요청'은 CI 완료 뒤).
- 평가 측 확인: diff = faafb5e + 수정본(+ 병합·보정). 통제 파일럿 집계 재산출(유형별 표 갱신).
- 맞으면 평가 측이 화면 캡처 01~06과 원문 대응표를 사용자에게 제시한다 → 사용자 확인 → 병합.
- 탐지·RAG 엔진 변경이므로 릴리스 후보 수용 SHA에서 평가 측이 verify_all 전체 1회를 돈다(AGENT_ROLES 2.1).
```


## 2-6-1. #191 3차 — 사용자 결정 반영(빈 괄호 제거, 영문 코드 유지) (10-28)

```
[Codex(구현 대행) 보완 지시 — PR #191(TK-127 2단계, head 4891f4e) 3차: 사용자 결정 반영 1건(작음). 2026-10-28]

■ 판정 요약
- 코드는 수용했다(평가 측 2차 확인).
  · 같은 SHA CI 전부 성공, 두 테스트 실행 모두 성공(인용).
  · 평가 측 재실행 관련 22개 파일 471건 실패 0.
- 사용자 화면 확인 결과(10-28):
  · '문서 주장/인용' 칸의 빈 괄호는 제거한다.
  · 보고서의 영문 상태 코드(SUPPORTS·PENDING_REVIEW) 표기는 현재 상태를 유지한다(바꾸지 않는다).

■ 원인 (4891f4e 기준, TK-88부터 있던 코드)
- packages/report_engine/pdf_report.py 264행: `cell_claim = claim[:120] + "\n(" + str(row.get("cited_authority", "")) + ")"`
- packages/report_engine/docx_report.py 203행: `cell_claim = claim + f"\n({row.get('cited_authority', '')})"`
- 인용 표기(cited_authority)가 없는 행에도 괄호를 붙인다. 그래서 '()'가 남는다. 값이 None이면 '(None)'이 된다.
- 캡처 03(PDF) 1행에서 확인했다. Word도 같은 코드다.

■ 고칠 것 — 평가 측 수정본 그대로 적용 (3개 파일, +40/−2)
- 적용(PR 브랜치에서 새 커밋):
  `git fetch origin evaluator/round8-promotion && git show origin/evaluator/round8-promotion:docs/handoff/patches/TK-127_claim_cell_parentheses_fix_on_191.diff | git apply --3way`
- 두 줄 모두 `authority = str(row.get("cited_authority") or "").strip()`로 읽는다. 값이 있을 때만 `\n(표기)`를 붙인다.
- 시험 test_claim_cell_has_no_empty_parentheses_without_authority(tests/test_tk127_stage2_drive_pipeline.py에 추가):
  · 대조 3건(키 없음·빈 문자열·공백): Word 칸에 괄호가 없고, PDF에 '()'·'(None)'이 없다.
  · 양성 3건(판례·법령·사건번호 표기): 괄호 안에 그대로 싣는다.
- 캡처 03(PDF)·04(Word)를 다시 찍는다. 1행 '문서 주장/인용' 칸에 빈 괄호가 없어야 한다.

■ 평가 측 사전 검증 (4891f4e + 수정본, 저장소 밖 사본, 평가 측 재실행)
- 새 시험 6건 통과. 원래 코드에서는 대조 3건이 실패한다(결함을 잡음).
- cited_authority를 다루는 시험 전부와 TK-127·TK-129·보고서 시험을 함께 돌렸다: 20개 파일 294건 실패 0. 보호 시험 tests/acceptance/test_f3_protected.py도 포함된다.
- check_test_edits(기준 5d03247) '기존 시험의 삭제·표시 변경 없음', check_hardcoding_diff 통과.
- 미검증: Microsoft Word 앱 직접 표시.

■ 하지 않을 것
- 보고서의 영문 상태·관계 코드는 바꾸지 않는다(사용자 결정: 현재 상태 유지).
- 다른 칸·표·문구, 매칭 규칙은 바꾸지 않는다. 기존 시험은 수정하지 않는다.

■ 제출물·수용 기준
- 커밋 1~2개(수정본 적용, 캡처 03·04 교체). 끝에 `Agent: implementer`.
- 필수 CI 5종이 같은 SHA에서 성공해야 하고, 두 테스트 실행 모두 성공해야 한다. PR 코멘트 3줄('검토 요청'은 CI 완료 뒤).
- PR의 draft 상태를 해제한다(Ready for review).
- 평가 측 확인: diff = 4891f4e + 수정본(+캡처). 맞으면 사용자 "#191병합" 대상이다.
```

## 2-7. lexdiff 비교 후속 개선 4건 (11-02 개정, Claude Code·Astra 교차 검증 반영 — 1판 TK-130 지시 폐기)
- 비교 문서: `requests/LEXDIFF_COMPARISON_20261102.md`(4절 교차 검증).
- 순서: ① [TK-130a](TK-130_informal_law_abbreviation_inference.md) 원숫자 ㉑~㊿ → ② TK-130b 약칭 추정 2판 → ③ [TK-131](TK-131_precedent_evidence_excerpt.md) 판례 근거 발췌(설계 메모 먼저) → ④ [TK-132](TK-132_hwpx_table_structure.md) HWPX 표 구조(설계 메모 먼저). PR은 하나씩 따로 낸다.
- 수정본(평가 측 사전 검증 완료, Steve `debbe83` 기준):
  - `patches/TK-130a_circled_paragraphs_on_debbe83.diff`(3개 파일)
  - `patches/TK-130b_abbreviation_inference_v2_on_debbe83.diff`(4개 파일)
  - 1판 `TK-130_abbreviation_inference_on_debbe83.diff`·`_v2.diff`(통합본)는 쓰지 않는다.
- 2판 수정점: 결과 구분(FOUND/NO_CANDIDATE/AMBIGUOUS/LOOKUP_FAILED/INCOMPLETE·CANDIDATE_LOOKUP_FAILED→UNVERIFIED), 조항 상태별 설명, law_id 고정, 후보 탐색 쪽 상한(검색어 2 × 3쪽).
- 심각도 정책(평가 측 결정): 후보 없음·모호·조회 실패·상한·조문 부재는 기존 CRITICAL을 유지하고 결과 구분만 기록한다.
- 지시문 전문은 사용자에게 전달한 코드 블록과 같다.
- **#197 TK-130a 1차 판정(11-02): 보완 1회.** CI 전부 성공, diff = 수정본. Sourcery 지적 4건 모두 유효: `rag_engine/provision_quotes.py:15` CIRCLED 20자(같은 결함 세 번째 위치), 시험 경계 약점, 문장 다양성, 주석. 보완본 `patches/TK-130a_supplement_on_5ababa4.diff`(사전 검증 완료)를 같은 PR에 커밋 1개로 적용한다.
- **#197 2차(`cd31262`): 수용.** 보완본과 줄 일치, 같은 SHA CI 전부 성공. 사용자 '#197병합' 뒤 TK-130b 착수.
- **#198 TK-130b 1차(`f4fc0c8`): 보완 1회.** 원인: 평가 측 수정본 설명 문구가 평가 세트 문구 대조에 걸림, spec_verdict가 추정 성공을 NOT_FOUND로 판정, 재시도 소진 뒤 STATUTE_NONEXISTENT 잔존, 시험 보강. 보완본 `patches/TK-130b_supplement_on_f4fc0c8.diff`(사전 검증 완료)를 같은 PR에 커밋 1개로 적용한다.
- **#198 2차(`4b8bf01`): 수용.** 보완본과 줄 일치, 같은 SHA CI 전부 성공. 사용자 '#198병합' 뒤 TK-131·132 설계 메모 착수.

## 2-8. TK-76 2주기 1항 — EVI-LOGIC 지각 범위 구조 (11-02, 사용자 결정 '이번 릴리스 포함, Antigravity 구현')

- 이번 릴리스 범위: TK-133(Codex, 구형 HWP 표 구조)과 TK-76 EVI-LOGIC(Antigravity) 두 건이다.
- 지시문 전달 완료(11-02, 사용자 전달). 원문 내용은 [TK-76 티켓 '2주기 1항'](TK-76_focus_types_generalization_cycle1.md)과 수정본 `patches/TK-76_evi_logic_perception_on_c180db9.diff`(기준 Steve `c180db9`)에 있다.
- 수용 기준
  - diff = 수정본
  - 필수 CI 전부 성공, 기존 시험 수정 0, 고정 변화 0, 은퇴 하락·오탐 증가 0
  - train EVI-LOGIC·오탐 보고
  - 평가 측 새 비공개 탐침: 양성 ≥ 2/3, 대조 오탐 0
- **11-02 정정(2판):** 평가 측 1판 수정본에 일반화 결함 5개가 있었다(새 탐침 5/9). 2판 수정본 `patches/TK-76_evi_logic_perception_v2_on_c180db9.diff`로 바꾼다. 상세는 티켓 '2주기 1항 2판'에 있다. 1판 수정본은 쓰지 않는다.
- **#204 `6abf2bc` 1차 판정(11-02): 보완 1회.** 4차 탐침 대조 오탐 1/12(평가 측 수정본의 부사 예외 끝 글자 비교 결함). 보완본 `patches/TK-76_supplement_on_6abf2bc.diff`를 적용하고, 그 전에 `origin/Steve_ACASiaLAW`(`160e6bb`)를 병합한다. 상세는 티켓 '#204 1차 판정' 절에 있다.
- **#204 `0e97f2e` 2차 판정(11-02): 수용.** 5차 탐침 8/8·대조 0/10, CI 성공. 사용자 병합 대기.
- 상태: 수용.

## 2-9. 다음 릴리스 범위 (11-03 사용자 결정)

- 범위
  - TK-134~142
  - TK-76 3주기(EVI-INCONS → EVI-OVR → 나머지 EVI 잔여)
- 상세·순서: [requests/NEXT_RELEASE_SCOPE_20261103.md](requests/NEXT_RELEASE_SCOPE_20261103.md)
- 진행 방식
  - 평가 측이 티켓마다 사전 검증한 지시문을 따로 낸다. 지시문이 오기 전에는 착수하지 않는다.
  - 설계 메모가 필요한 항목(TK-76 각 유형, TK-137·138·139)은 메모부터 낸다.

## 2-10. 다음 릴리스 1차 지시 — TK-134·135·136 (11-03, 사용자 지시 'antigravity 구현')

| 티켓 | 수정본(기준 Steve `892bbd8`) | 티켓 | PR | 상태 |
|---|---|---|---|---|
| TK-136 외부 AI 프롬프트 엄격성 | `patches/TK-136_external_prompt_strictness_on_892bbd8.diff` | [TK-136](TK-136_external_ai_prompt_strictness.md) | #211 `ea951b2` | **Steve 병합 `5007073`**(11-03) |
| TK-135 판례 의견 귀속 | `patches/TK-135_opinion_attribution_on_892bbd8.diff`(2판) | [TK-135](TK-135_precedent_opinion_attribution.md) | #210 `1e1c637` | **Steve 병합 `46e0d72`**(11-03) |
| TK-134 자치법규 조회 | `patches/TK-134_ordinance_lookup_on_892bbd8.diff`(2판) | [TK-134](TK-134_local_ordinance_lookup.md) | #212 `b3e6eae` | **Steve 병합 `ed789cb`**(11-03) |
| TK-76 3주기 1항 EVI-INCONS | 설계 메모만(코드 금지) | [TK-76 '3주기 1항'](TK-76_focus_types_generalization_cycle1.md) | #213 `31bf218` | **메모 승인·Steve 병합 `7b41c7d`**(11-03) → PR1(A 산식) 착수(N2·N3 반영), PR2에서 N1 |

- 세 수정본은 서로 겹치지 않는다(평가 측 확인: 각각·연달아 적용 모두 성공).
- 한 PR에 한 티켓. 검토 요청은 필수 CI가 끝난 head SHA로 한다.
- 11-03 사용자가 4건(TK-134 2판·TK-135 2판·TK-136·EVI-INCONS 메모)을 Antigravity에 전달했다.

## 2-11. 다음 릴리스 2차 지시 — TK-140~146·#214 보완 (11-03)

| 티켓 | 수정본(`docs/handoff/patches/`) | 티켓 문서 | PR | 상태 |
|---|---|---|---|---|
| TK-140 문서 파서 후속(A+B-1+B-2) | `TK-140_parser_followups_AB1_on_7b41c7d`, `TK-140_hwp_nested_tables_B2_on_AB1` | [TK-140](TK-140_document_parser_followups.md) | #217 `078f854` | **수용·Steve 병합 `ea2c81f`(11-03)** |
| TK-141 발췌 입력 예산·해시 | `TK-141_input_budget_hash_on_7b41c7d` | [TK-141](TK-141_evidence_input_budget_hash.md) | #216 `7c37154` | **수용·Steve 병합 `7823cbf`(11-03)** |
| TK-142 ReDoS 시간 시험 안정화 | `TK-142_redos_timing_stability_on_7b41c7d` | [TK-142](TK-142_redos_timing_test_stability.md) | #215 `c1c5994` | **수용·Steve 병합 `0d7051b`(11-03)**(1회차 CI 실패는 무관한 TK-56 시간 시험 → TK-147) |
| TK-76 3주기 1항 PR1 보완(F1~F8·G1~G4) | `TK-76_cycle3_pr1_fix_on_0437219`, `TK-76_cycle3_pr1_fix2_on_a9f6ee3` | [TK-76 '#214 1~3차 판정'](TK-76_focus_types_generalization_cycle1.md) | #214 `0437219`→`a9f6ee3`→`4074ebb` | **3차 판정 수용·Steve 병합 `9cb9a96`(11-03)** — 새 6차 탐침 8/9·대조 0/12 |
| TK-143 짧은 약칭 추정 | `TK-143_short_abbreviation_on_7b41c7d`(2판) | [TK-143~146](TK-143_146_online_probe_fixes.md) | #218 `235db42` | **수용·Steve 병합 `831b325`(11-03)** |
| TK-144 DOCX 표 구조 | `TK-144_docx_tables_on_7b41c7d` | 같음 | #219 `b0c017c` | **수용·Steve 병합 `631b509`(11-03)** |
| TK-145 같은 판례 반복 인용 | `TK-145_repeated_case_citation_on_7b41c7d` | 같음 | #220 `9656317` | **수용·Steve 병합 `269432b`(11-03)** |
| TK-146 표 비율 행 진단 | `TK-146_table_percentage_on_7b41c7d` | 같음 | #221 `a484deb` | **수용·Steve 병합 `cf57cb7`(11-03)** |

- TK-143~146 합본(2판) 평가 측 사전 검증: verify_all 전체 종료 0(시험 9,269·브라우저 197), 고정 82.6/81.9 FP0, 은퇴 5세트 변화 0(평가 측 재실행, `eb4d5ea` 기록).
- 한 PR에 한 티켓. 검토: diff = 수정본, 필수 CI 성공, 2-2 규약 게이트.
- 11-03 평가 세션 교대 뒤 판정: #215·#216·#217 수용, #214 2차 보완(원인·수정본·사전 검증은 [TK-76 '#214 2차 판정'](TK-76_focus_types_generalization_cycle1.md)).
- 11-03 2차 제출 판정: #214 `4074ebb`·#218~#221 수용. 합본 후보(Steve `ea2c81f` + 5개 PR, 사본 `fab489d`) verify_all 전체 종료 0·고정 변화 0·은퇴 후퇴 없음(평가 측 재실행).

## 2-12. 다음 릴리스 3차 지시 — TK-76 PR2·TK-137 메모·TK-147 (11-03, 사용자 지시 '1,2순위대로 지시를 시작, TK147 포함, 릴리스는 현재 계획된 티켓 전체 구현후')

| 티켓 | 수정본·요청서 | 티켓 문서 | PR | 상태 |
|---|---|---|---|---|
| TK-76 3주기 1항 PR2 문서 간 대조(B) | `patches/TK-76_cycle3_pr2_xdoc_anchored_on_cf57cb7.diff` → 2판 `TK-76_cycle3_pr2_fix2_on_1d6f567` | [TK-76 'PR2'·'#224 1·2차 판정'](TK-76_focus_types_generalization_cycle1.md) | #224 `1d6f567`→`51e86f2` | **2차 판정 수용·Steve 병합 `5ffc405`(11-03)** — 8차 탐침 5/6·대조 0/10. 후속 S1(입금일 꼴) 다음 PR |
| TK-137 제한형 관련 근거 탐색 | 설계 메모 → 구현 | [TK-137 메모 요청·판정](TK-137_related_basis_memo_request.md) | #225 `9d561d9`→`9a5846b` | **메모 보정본 승인·Steve 병합 `c503d11`(11-03)** — 구현 PR에서 N1~N6 반영 · **구현 #226 `4ba891a` 1차 보완(R1~R5, 수정본 `TK-137_impl_fix_on_4ba891a`)** |
| TK-147 TK-56 시간 시험 안정화 | `patches/TK-147_tk56_timing_stability_on_cf57cb7.diff` | [TK-147](TK-147_tk56_timing_test_stability.md) | #222 `0890cb3` | **수용·Steve 병합 `200db94`(11-03)** |
| TK-148 ㅇ 초성 사전식 값 | `patches/TK-148_gana_ah_on_cf57cb7.diff` | [TK-148](TK-148_gana_initial_ah.md) | #223 `f1e3969` | **수용·Steve 병합 `f6aba23`(11-03)**(시험 주석 1줄 승인 전 판 — 비차단, 다음 해당 파일 PR에서 정정) |

- 기준 Steve `cf57cb7`. 세 수정본은 서로 겹치지 않는다(PR2·TK-147 합본 verify_all 전체 종료 0, TK-148 관련 시험 136건 통과 — 평가 측 재실행).
- 릴리스: 사용자 결정(11-03) — 현재 계획된 티켓 전체(TK-76 3주기 나머지·TK-137~139·TK-147·TK-148) 구현 뒤 한 번에.
- 한 PR에 한 티켓. 검토 요청은 필수 CI가 끝난 head SHA로 한다.

## 2-13. 설계 메모 3건 판정 (11-04)

| 티켓 | PR | 판정 | 상세 |
|---|---|---|---|
| TK-138 관련 판례·권위 가중 | #227 `c8cf902`→`5b45176` | **보정본 승인·Steve 병합 `ce4eea8`(11-04)** — 구현 PR에서 U1~U5 | [메모 판정](requests/MEMO_REVIEW_20261104_TK138_139_76OVR.md) |
| TK-139 처분기준 별표 1유형 | #228 `b81a52c`→`12af4b3` | **보정본 승인·Steve 병합 `c2ba9d2`(11-04)** — 구현 PR에서 W1~W5 | 같음 |
| TK-76 3주기 PR3 EVI-OVR | #229 `56738c7`→`2699f18` | **재작성본 조건부 승인·Steve 병합 `7533efd`(11-04)** — 구현 PR에서 V1~V4. EVI-INCONS 후속(S1·N월분)은 별도 | 같음 |
| TK-137 구현 | #226 `4ba891a`→`857ce01` | **수용·Steve 병합 `996ba14`(11-04)** | [TK-137 6절](TK-137_related_basis_memo_request.md) |

## 2-14. 구현 지시 — TK-138·TK-139·TK-76 PR3 EVI-OVR (11-04, 사용자 지시 'TK-138·TK-139·TK-76 PR3 구현 지시')

| 티켓 | 근거 메모(Steve) | 착수 기준 | 구현 조건 | 상태 |
|---|---|---|---|---|
| TK-138 관련 판례·권위 가중 | `requests/TK-138_related_precedents_design_memo.md`(`ce4eea8`) | **Steve `996ba14`**(#226 병합, U4: TK-137 예산 조정 포함) | U1~U5([판정서](requests/MEMO_REVIEW_20261104_TK138_139_76OVR.md)) | **전달 완료(11-04, 사용자)** |
| TK-139 처분기준 별표 1유형 | `requests/TK-139_disposition_criteria_design_memo.md`(`c2ba9d2`) | **Steve `996ba14`**(#226 병합, 같은 `related_authorities.py` 확장) | W1~W5 | **전달 완료(11-04, 사용자)** |
| TK-76 3주기 PR3 EVI-OVR | `requests/TK-76_cycle3_evi_ovr_design_memo.md`(`7533efd`) | Steve `7533efd`(지금) | V1~V4. V3 정정: 새 낱말은 '배달증명'·'계약체결'·'약정성립'·'체결되었'·'성립되었' 5개뿐(공문·세금계산서·확인증은 기존 사전), 기존 '확정적으로' 유지 | **전달 완료(11-04, 사용자)** |

- 평가 측 기준선(Steve `7533efd`, 평가 측 재실행): EVI-OVR 관련 시험 18개 파일 599건, HWP 시험 4개 파일 61건, 판례·무리한 주장 관련 47개 파일 1,924건 통과(5 건너뜀).
- 세 PR 모두 2-2 규약(탐지)·화면 PR 규칙(TK-138·139: 캡처·사용자 확인)을 적용한다. 한 PR에 한 티켓.

## 2-15. 구현 PR 판정 — #230 TK-76 PR3 EVI-OVR · #231 TK-138 (11-04, 사용자 '제출완료')

| PR | head | 판정 | 요지 | 상태 |
|---|---|---|---|---|
| #230 TK-76 3주기 PR3 EVI-OVR | `e481f3f`→`4e7c6ea` | **2차 수용(11-04)** | 보완본 제품 코드 = 평가 측 사본(diff 0). 새 5차 탐침 5/6·0/8, 누적 21/27·0/32 | **Steve 병합 `349a30b`(11-04)** |
| #231 TK-138 관련 판례·권위 가중 | `02b26e9`→`17f6e73` | **2차 조건부 수용(11-04)** | H1~H5·H7 = 평가 측 사본. K1(머리 줄 범위가 첫 질의 것뿐) 보완 + 화면 캡처 1280·390 → 사용자 화면 확인 | **3차 수용(11-04, head `022db04`, 사용자 화면 확인)** — **Steve 병합 `ae2c6e8`(11-04)** |
| #232 TK-139 처분기준 별표 | `d834190` | **보완 1회** | J1 다운로드 서명 오류·J2 실제 파서 merges 꼴·J3 차수 열 오연결(치명), J4~J10. 탐침 PR 판정 0(예외 25) → 사본 26/28·잘못된 확정 0 | **2차 보완 1회 더(11-04, head `bd2de2f`)** — J12·J13(평가 측 누락분), #231 병합 뒤 rebase, J11 별도 10초·문구 권고안(사용자 결정) | **4차 수용(11-04, head `b25caf6`, 사용자 화면 확인, CodeQL 게이트 성공, verify_all 전체 종료 0)** — **Steve 병합 `4323721`(11-05)** |

### #230 보완 지시
```
[평가 측 보완 지시 — #230 TK-76 3주기 PR3 EVI-OVR (head e481f3f, 기준 Steve 996ba14), 11-04]

판정: 보완 1회. V4 수용 기준 미달.
- 평가 측이 새로 지은 비공개 탐침 4세트(합 양성 21·대조 24, 문장은 공개하지 않음)
  · 기준 Steve 996ba14: 양성 12/21, 대조 오탐 4/24
  · 이 PR e481f3f: 양성 11/21, 대조 오탐 4/24  ← 2/3 미달·오탐 남음
  · 아래 F1~F4를 적용한 평가 측 사본: 양성 16/21(76%), 대조 오탐 0/24
- CI 결과 인용: 필수 확인 전부 성공. 평가 측 재실행: 은퇴 5세트 변화 0·오탐 0(PR·사본 같음), 평가 세트 문구 대조·하드코딩·시험 약화 점검 통과, 평가 측 사본 a2d624f verify_all --base 996ba14 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,387·브라우저 197), 고정 dev 82.6·holdout 81.9·FP 0 변화 0.

원인과 고칠 것 (줄 번호는 e481f3f의 packages/claim_engine/evidence_consistency.py)

F1 [회귀] 내심의상태 부사·동사 꼴 미탐 — 721~725행
- 원인: 이번 PR이 _match_predicate_word를 '서술어 자리' 판별로 바꾸면서 전칭_전기간만 경계 일치로 남기고, 내심의상태도 일반 경로(마지막 서술 판별)로 보냈다. 내심 낱말은 '…로'(부사)·'…하여'(동사 연결)로 쓰여 다른 동사를 꾸미는 것이 보통이라 서술어 자리에 오지 않는다. 평가 측 재현: 내심 꼴 탐침 기준 5/5 → PR 3/5.
- 고칠 것: cat이 "전칭_전기간" 또는 "내심의상태"면 경계 일치로 판정하되, 낱말 바로 뒤에 '하'·'적'이 붙는 꼴도 허용하고(뒤 경계 예견에 하|적 추가), 낱말 뒤 공백 다음이 _NOUN_FOLLOWERS_PAT(여부·취지 등 명사 수식)인 일치만 뺀다. 모든 일치를 finditer로 보며 하나라도 명사 수식이 아니면 참.

F2 [오탐, 기존 결함] 금전 아닌 목적어의 '받다'를 완료 술어로 셈 — 1206~1207행
- 원인: COMPLETION_PREDICATE_RE의 둘째 갈래 중 맨 '받았…|받은'은 목적어를 보지 않는다. 진단·상태류 서증에서 금전이 아닌 목적어 + '받았다' 꼴 서술이 완료_확정으로 잡혀 매트릭스 '못 덮음'으로 결과가 난다(평가 측 대조 2건 중 기준 2·PR 1 오탐).
- 고칠 것: 1206행의 COMPLETION_PREDICATE_RE.search(scope_text)를 함수 _completion_structure_found(text)로 바꾼다. finditer로 모든 일치를 보고, 일치가 '받았'·'받은'으로 시작하는 맨 갈래면 바로 앞 어절(조사 을/를, 부사 모두·전부·전액·이미·다 건너뜀)이 금전 명사 꼴일 때만 참: 정규식 (?:\d[\d,]*\s*원|돈|[가-힣]{0,8}(?:대금|금|비|채무)|차임|원리금)$. 다른 갈래 일치는 그대로 참. 장면 명사 목록을 쓰지 않는다(2-2).

F3 [미탐] 합성 술어 명사 앞 수식 명사·'이루어지다' 연쇄 — 725행, 760행
- 원인 (가): 상대방의사표시 새 낱말 '계약체결'·'약정성립'은 앞 경계가 공백·조사여야 해서 '(종류명)계약체결'처럼 앞에 명사가 붙으면 안 맞는다. (나): 760행 완료 연쇄 어간 목록에 '이루'만 있어 '이루어졌'의 '어'에서 끊긴다.
- 고칠 것 (가): cat == "상대방의사표시"이고 낱말 길이 ≥ 4이며 '었'으로 끝나지 않으면 앞 경계에 [가-힣]도 허용한다(725행 matches의 앞 경계). (나): 760행 어간 목록에 '이루어'를 '이루'보다 앞에 넣는다.

F4 [지시 밖 확장, 오탐] 주체 생략 절을 상대방 의사표시로 셈 — 1249~1250행
- 원인: 'elif not opp_subj and sender:' 갈래는 메모·지시에 없던 확장이며 B-1 S2(통지류 술어 주체 확인, 주체 미정 제외)를 뒤집는다. 한국어 서면에서 주체를 생략한 절은 대개 작성자 측 행위다. 평가 측 재현: 자기 측 발신 통지서로 주체 없이 승인·동의를 서술한 대조 2/2 오탐.
- 고칠 것: 이 갈래를 '주체가 상대방으로 명시된 때'로 좁힌다: not opp_subj and sender and re.search(r"(?<![가-힣])상대방(?:\s*측)?[이가은는]", scope_text[:opp_pos] if opp_pos is not None else scope_text). 이 PR의 시험 test_v2_sentence_final_citation_governs_preceding_clause는 그대로 통과한다.

2-2 다 제출물 (규약 위반 — 다시 낸다)
- 득점 귀속표: 단위 시험 건수가 아니라 고정·은퇴·train 세트 점수 변화를 규칙별로(규칙 끄기 재측정) 적는다. 이번 변화는 은퇴·고정 0이므로 '세트 득점 0'으로 적는다. 판정 코드는 코드에 실제 있는 값만 적는다(PR 본문의 NOTICE_AGREEMENT_OVERREACH 등은 코드에 없다 — 실제는 범주별 태그 ESTIMATE_OVERREACH·DIAGNOSTIC_ASSERTION 등).
- train 미득점 원인표: debug_counters(no_cat·no_row·no_scope·no_pred·covered·excluded·pos_emitted)로 train EVI-OVR 미득점 항목마다 멈춘 단계를 ①~⑦ 단계별 **건수**로 낸다(NEXT 3절 B-1 S9 형식, 문장 인용 금지). 서술형 원인 A~D만으로는 안 된다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_pr3_fix_on_e481f3f.diff(evaluator/round8-promotion). 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- F1~F4 각각 양성·대조 단위 시험(평가 측 탐침 문장 사용 금지, 다른 낱말·어순으로 새로 짓는다). 기존 EVI-OVR 관련 시험 19개 파일 627건 통과(평가 측 사본에서 확인).
- 수용: 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 은퇴·고정 하락·오탐 0, 평가 세트 문구 대조 통과, 귀속표·train 원인표(건수).
- 이번 PR 범위 밖(후속, 이번 수용 조건 아님): 소갑 호증의 입증방법 행 연결, 맨 '이행하였다' 완료 꼴, '알다' 꼴 인식, 전칭 부정 꼴.
```

### #231 보완 지시
```
[평가 측 보완 지시 — #231 TK-138 관련 판례·권위 가중 (head 02b26e9, 기준 Steve 996ba14), 11-04]

판정: 보완 1회. U1·U2·U3(추출 규칙)·U4 반영은 확인. 실제 법제처 응답(평가 측, http)에서 org=400201 대법원 한정(근로기준법 제23조 379건·민법 제750조 215건·주택임대차보호법 제3조 264건 중 100건), 판결유형으로 전원합의체 식별, 본문 상세 요지 수신 모두 동작한다. 그러나 이 기능의 유일한 소비 경로(무리한 주장 AI 교차검토)가 막히고 기존 화면이 회귀한다. CI 결과 인용: 필수 확인 전부 성공. 평가 측 재실행: 관련 시험 65개 파일 5,072건 통과(PR·사본 같음) — 아래 결함은 기존 시험이 잡지 못한다.

원인과 고칠 것 (줄 번호는 02b26e9 기준)

H1 [치명] 판례를 주면 AI 교차검토 요청이 입력 계약 위반으로 차단 — argument_validity_verifier.py 634행, llm_router/input_contracts.py 50행
- 원인: 항목에 새 키 "관련 권위 판례(참고)"를 넣었지만 argument_review_v1의 _ARGUMENT_ITEM은 닫힌 객체라 모르는 키가 있으면 valid_input_contract가 거짓이다. 평가 측 재현: 판례 1건 제공 시 inspect_request = BLOCKED, failure_code INPUT_CONTRACT_VIOLATION, retryable False. 판례가 있는 문서는 모델에 아무것도 가지 않고 기존 AI 의견도 사라진다.
- 고칠 것: _ARGUMENT_ITEM에 "관련 권위 판례(참고)": str를 넣고 optional에 추가한다. 값은 지금처럼 hide()를 거친다.

H2 [회귀] AI 의견 근거가 화면·DOCX·PDF에서 빈칸 — 703행
- 원인: 의견 dict 키를 "reasoning"에서 "legal_reasoning"으로 바꿨다. reasoning_format.py 47행과 app.js 2952행은 "reasoning"을 읽는다. TK-138과 무관한 모든 문서의 AI 의견 근거가 사라진다(평가 측 재현).
- 고칠 것: 키 "reasoning" 유지.

H3 [오탐] 둘째 항목부터 서면 자신의 인용 사건번호를 '목록 밖'으로 판정 — 685~686행
- 원인: item_match = next(첫 항목)이라 모든 항목이 첫 항목의 사건번호만 제외한다. 평가 측 재현: 항목 2의 모델 답이 항목 2의 인용 판례를 말하면 '판단 불가'로 바뀐다.
- 고칠 것: item_id(1부터, enumerate 순서)로 unverified_cases[item_id-1]을 고르고, 그 인용 raw_text에서 extract_all_case_numbers로 뽑은 사건번호 전부를 제외 집합으로 쓴다.

H4 [범위] 판례 목록을 주지 않은 문서에도 '목록 밖' 판정 — 679~696행
- 원인: precedents가 없으면(오프라인·QUICK·법령 인용 없음·검색 0건) 제공 집합이 비어 모델 답의 다른 사건번호가 모두 '목록 밖'이 되어 기존 온라인 판정이 바뀐다. P5의 OFF/ON 측정에서 TK-138 효과를 분리할 수 없다.
- 고칠 것: provided_case_numbers가 비어 있지 않을 때만 대조한다.

H5 [메모 2.4 '제거' 미이행] 목록 밖 사건번호가 화면 근거 글에 그대로 남음 — 693~694행
- 고칠 것: 목록 밖 사건번호를 claim_text·reasoning·check에서 '[제공 목록 밖 사건번호 제거]'로 바꾼다(공백 낀 꼴 포함: rf"{y}\s*{c}\s*0*{n}(?!\d)"). 머리표 '[UNVERIFIED_INVENTED_IN_RESPONSE] 제공 목록 밖 사건번호 N건 인용 배제.'와 감사용 unprovided_case_numbers는 남긴다. verdict '판단 불가' 유지.

H7 [메모 2.5 초과] 본문 상세 조회가 문서당 최대 6건 — related_authorities.py 579~593행
- 원인: 질의 2개 × 상위 3건마다 상세 조회. 실제 응답 재현: 근로기준법 제23조·민법 제750조 두 질의에서 상세 6회·12.4초(메모 '최대 2~3건').
- 고칠 것: 문서당 상세 조회 횟수 카운터(상한 3)를 두고 예산 가드와 함께 본다. 평가 측 사본 실측: 상세 3회·7.1초, 판례 6건(요지 3건).

P4 정정(PR 본문에 적는다): 메모 2.3의 _excerpt_budget_chars는 _semantic_review 경로 함수라 무리한 주장 경로에는 없다. 판례 블록 상한(3건 × 요지 150자)으로 대체한다고 적는다.

U5 화면 문구(사용자 확인 사항): 범위 표시가 판례 줄마다 반복되고 괄호가 겹친다 — '…(검색 379건 중 100건 (대법원 한정))'. 범위는 판례 묶음 머리에 한 번만 적는 쪽을 권고한다(예: '[관련 판례] 대법원 본문검색 379건 중 100건을 권위 순 정렬한 상위 3건 · 검토 자료'). 이 항목은 평가 측 사본에 적용하지 않았다(미검증). 최종 문구는 사용자 화면 확인으로 정한다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-138_impl_fix_on_02b26e9.diff(evaluator/round8-promotion) — H1~H5·H7과 평가 측 시험 5건(TestTK138EvaluatorSupplement). 이 시험은 02b26e9에서 5/5 실패, 사본에서 통과(TK-137·138 시험 33건 통과).
- 기존 관련 시험(argument_validity·claim_review·search_case·_semantic_review·related_authorities·input_contract·inspect_request를 쓰는 65개 파일) 통과.
- 화면 캡처(1280·390px, 긴 사건명 포함) 다시 제출 → 사용자 확인 뒤 수용.
- 수용 SHA에서 평가 측 verify_all 전체(입력 계약 변경 포함)·오프라인 고정·은퇴 변화 0, 온라인 OFF/ON: 제공 목록 밖 인용 0(화면 근거 글 기준)·지어낸 인용 0.
```

### #232 보완 지시
```
[평가 측 보완 지시 — #232 TK-139 처분기준 별표 대조 1유형 (head d834190, 기준 Steve 996ba14), 11-04]

판정: 보완 1회. 이 PR 그대로는 실제 환경에서 한 건도 판정하지 못한다. 실제 법제처 응답(식품위생법 시행규칙 MST 289161, 별표 135개)과 실제 [별표 23] HWP(164,352바이트)로 평가 측이 끝에서 끝까지 돌린 결과: PR은 다운로드 단계에서 늘 실패(J1)하고, 다운로드를 우회해도 표 파싱에서 예외가 난다(J2). 평가 측 사본(아래 J1~J10 적용)은 같은 입력에서 '일치'와 감경 규정 병기까지 정상 동작한다. 단위 시험이 실제 파서 출력이 아니라 가짜 꼴(merges dict, _http_get 모의)을 써서 CI가 모두 통과했다.
- CI 결과 인용: 필수 확인 전부 성공. 평가 측 재실행 결과는 아래 각 항목과 '제출물'에 적었다.
- 평가 측 비공개 탐침 2세트(서면 문장 28개, 실제 별표 23. 기대값은 실제 별표 칸 값 기준이며 2건은 별표 확인 뒤 평가 측 기대값을 정정했다):
  · PR d834190: 판정 0 — 25건 표 파싱 예외(J2), 3건은 업종 미특정으로 파싱 전 보류
  · 평가 측 사본: 1차 12/12, 2차 14/16 정답, 잘못된 확정(틀린 일치·불일치) 0. 보류 2건은 같은 위반사항 문구가 두 세부 절에 있고 3차 값이 달라 유일성 가드가 막은 것으로, 안전한 보류다.

원인과 고칠 것 (줄 번호는 d834190 기준)

J1 [치명] 별표 다운로드가 늘 실패 — law_go_kr.py 461행
- 원인: self._http_get(url, timeout=5.0)인데 SourceAdapter._http_get(base.py 109행)에는 timeout 인자가 없다. TypeError가 나고 except에서 None을 돌려줘 늘 'HWP 다운로드 실패'가 된다(평가 측 재현). 시험은 _http_get을 MagicMock으로 바꿔 서명 오류를 숨긴다.
- 고칠 것: base.py _http_get에 timeout: Optional[float]=None을 더하고, 설정값보다 짧게만 줄인다(min(timeout, settings.http_timeout)). 시험은 모의 함수에서 inspect.signature(SourceAdapter._http_get).bind(...)로 실제 서명을 검사한다.

J2 [치명] 실제 HWP 파서의 merges 꼴과 다름 — disposition_criteria.py 201~202행
- 원인: 실제 _extract_hwp_table_structures의 merges는 [{"row","col","row_span","col_span"}, ...] 목록이고 covered는 [[r,c], ...] 목록이다(별표 23 실측: merges 36·covered 79). 코드는 dict로 보고 .items()를 불러 AttributeError가 난다. 시험 test_w3는 {(3,0):(2,1)}이라는 실제와 다른 꼴을 쓴다.
- 고칠 것: 목록 꼴을 읽어 전파하고(dict 꼴도 허용 가능), 시험 표는 실제 파서 출력 꼴로 만든다.

J3 [치명, 행 오연결] 차수 열을 잘못 잡음 — 216~240행
- 원인: 머리글을 0~3행에서만 찾는데 실제 별표 23의 머리글은 4행('위반사항|근거 법령|행정처분기준')·5행('1차 위반|2차 위반|3차 위반')이다. 그 대신 2행 일반기준 문단(5열 병합, 전파 뒤 모든 칸에 같은 글자)에 '1차' 낱말이 들어 있어 order_cols[1]이 마지막 열(4열 = 3차 칸)이 되고 2·3차는 못 찾는다. 결과: 1차 주장을 3차 기준과 비교한다(G1 위반).
- 고칠 것: 전파 전 원본 칸에서, 덮인 칸(covered)을 빼고, 칸 전체(공백 제거)가 머리글인 것만 본다: '위반사항|위반행위|위반내용' → 위반 열, '근거법령' → 근거 열, 정규식 ([123])차(위반)? 전체 일치 → 차수 열. 앞 15행 안에서 찾고, 위반 열이나 1~3차 열 중 하나라도 못 찾으면 UNVERIFIED(G4). 머리글 행과 그 앞 행은 자료 행에서 뺀다.

J4 [오판 위험] 차수 미기재를 1차로 가정 — 21·81~87행
- 원인: claimed_order 기본값 1. 차수를 적지 않은 서면이 2차 기준값을 주장하면 '불일치'로 잘못 확정된다. VIOLATION_ORDER_RE의 '이|일|세' 한 글자 갈래는 '이 차량'·'세차' 같은 낱말에도 걸린다.
- 고칠 것: 처분 문장 안의 (?<![0-9가-힣])([123])\s*차 꼴, 또는 '(첫|두|세) 번째 (위반|처분)'에서만 차수를 정한다. 없으면 None → UNVERIFIED('서면의 위반 차수 미기재').

J5 [미판정] 위반 사실 구간에 행정청·날짜·차수가 섞임 — 103~154행, 351행
- 원인: 처분 문구 앞 전체를 쓰고 끝부분만 다듬어 처분 주체·날짜·상대방 낱말이 섞인 구간이 Jaccard에 들어간다. 별표 쪽은 '1. 법 제N조를 위반한 경우 가. …' 상위 항목과 번호가 붙은 채 비교된다. 평가 측 사본에서 J1~J4만 고치면 1차 탐침 6/12, J5까지 고치면 12/12.
- 고칠 것 (구조 규칙, 낱말 사전 아님):
  (가) 서면: 처분 문구 앞에서 마지막 처분 주체 절('…피고|행정청|처분청|청장|시장|군수|구청장' + 은/는/이/가 + 공백) 뒤에서 시작해, 그 뒤 첫 이유 연결어(정규식 (?:다는|였다는|했다는|라는|다고)?\s*(?:이유|사유|까닭)(?:로|에서)|(?:다|였다|했다)고\s*하여|(?:다|이라)며|함에\s*따라) 앞까지를 위반 사실로 잡는다. 그 안에서 마지막 당사자 주격('원고|신청인|청구인' + 가/는/은/이) 뒤만 남긴다. 이유 연결어가 없으면 지금 방식으로 돌아간다.
  (나) 별표: 위반사항 칸을 번호 표지((?:^|\s)(?:\d+(?:의\d+)?\.|[가-하]\.|\d+\)|[가-하]\))\s)로 나눠 마지막 세목만 쓴다.
  (다) 양쪽 끝의 형식어를 같은 규칙으로 뗀다: \s*(?:하는\s*)?(?:행위를\s*)?(?:한|하는|된)?\s*(?:것|경우)?(?:로서)?$
  Jaccard 0.60·격차 0.20 기준은 그대로 둔다.

J6 [W1 위반] 업종 절을 못 찾으면 전체 행에서 매칭 — 343~345행
- 고칠 것: 다른 업종 행과 맞추지 않고 UNVERIFIED('별표에서 해당 업종 절 미확인').

J7 [오판] 처분 종류가 달라도 숫자만 비교 — 284행
- 원인: 실제 별표 23 식품제조·가공업 칸에는 '품목류 제조정지 1개월'·'시정명령'이 있다. 첫 숫자+단위만 읽어 '영업정지 1개월' 주장과 '일치'로 볼 수 있다.
- 고칠 것: 칸에서 '영업정지\s*(\d+)\s*(일|월|개월)'만 읽는다. 없으면 UNVERIFIED.

J8 [선택 오류] 별표 번호 비교 — related_authorities.py 477행
- 원인: 실제 응답의 별표번호는 '0023'인데 서면의 '[별표 23]'에서 뽑은 '23'과 문자열로 비교한다. 지금은 제목 '행정처분' 대체 경로로 우연히 맞는다.
- 고칠 것: 앞의 0을 떼고 비교하며 가지번호가 있는 별표(예: 별표 23의2)는 따로 본다.

J9 [하드코딩] verify_disposition_criteria의 기본값 law_name="식품위생법 시행규칙", table_title="[별표 23] …" — 298~299행. 평가 측 check_hardcoding_diff가 '[검토] 명세 낱말'로 잡는다. 기본값을 빈 문자열로 하고 호출자가 넘긴 값만 쓴다.

J10 [보고서 빈칸] 저장 뒤 차수 키가 문자열이 됨 — related_authorities.py 624행, disposition_criteria.py 384행
- 원인: criteria_raw의 정수 키(1·2·3)가 JSON 저장 뒤 "1"·"2"·"3"이 되어 report_lines가 '기준  vs 서면 …'으로 빈칸을 낸다(평가 측 재현).
- 고칠 것: 정수·문자열 키를 모두 읽는다(raw.get(order) or raw.get(str(order))). JSON 왕복 시험을 더한다.

J11 [예산, 미검증] 실제 실행 12.3초·외부 호출 7회(법령 해석·target=law 별표 목록·HWP 다운로드). TK-137(8초)·TK-138과 같은 문서 15초 예산 밖에서 돈다. #231(TK-138)이 공용 예산 객체 AuthorityBudget을 들인다 — 두 PR이 related_authorities.py의 같은 자리를 고치므로 먼저 병합되는 쪽 위로 rebase하고, TK-139 단계도 그 예산을 쓴다(외부 호출 전 잔여 ≥ 3초, 모자라면 UNVERIFIED '시간 예산 소진'). 평가 측 사본에는 적용하지 않았다.

화면·보고서 문구(사용자 확인 사항, 미검증): 지금 줄은 '[처분기준] (법령명) (별표 제목): (위반사항 세목) → 기준 영업정지 N일 vs 서면 영업정지 M일 (DISCREPANCY_DETECTED) (…감경 가능…) · 검토 자료' 꼴이다(평가 측 캡처 docs/handoff/captures/TK-139/). 권고: 내부 코드(DISCREPANCY_DETECTED·MATCHED)를 '불일치(확인 필요)'·'일치'로 바꾸고, 차수('1차 위반')·별표 번호('[별표 23]')·업종을 적는다. 메모 5절의 영역 이름 '[처분기준 검토]'와 맞춘다. 최종 문구는 사용자 화면 확인으로 정한다.

알려진 한계(이번 수용 조건 아님): 한 업종 절이 여러 영업을 묶는 경우(예: '식품제조·가공업 등' 절의 즉석판매제조·가공업)는 업종 이름이 달라 UNVERIFIED로 보류된다. 별표 안 다른 절(조리사 등)이 앞 업종 이름을 이어받는다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-139_impl_fix_on_d834190.diff(evaluator/round8-promotion) — J1~J10과 평가 측 시험 7건(TestTK139EvaluatorSupplement 6·TestTK139ReportRoundTrip 1). 이 가운데 6건은 d834190에서 실패한다. 이 PR의 test_w2_unit_mismatch는 서면에 차수를 넣도록 고쳤다(J4).
- 단위 시험의 표는 실제 파서 출력 꼴(merges·covered 목록, 머리글 4·5행, 일반기준 병합 문단)로 만든다. 가능하면 실제 별표 HWP 하나를 시험 자료로 넣는다(공공 자료, 크기 확인).
- 관련 기존 시험(related_authorities·law_go_kr·_http_get·source_get·hwp_parser를 쓰는 43개 파일) 통과, TK-137·139 시험 통과.
- 화면 캡처(1280·390px, 불일치·일치 각 1건) → 사용자 확인 뒤 수용.
- 수용 SHA에서 평가 측이 실제 법제처 응답·실제 별표로 끝에서 끝까지 재확인, 새 비공개 탐침에서 잘못된 확정 0·판정 가능 문장의 정답률 2/3 이상, 오프라인 고정·은퇴 변화 0.
```

### #231 2차 — K1 보완 지시
```
[평가 측 2차 판정 — #231 TK-138 보완본 (head 17f6e73, 기준 Steve 996ba14), 11-04]

판정: 조건부 수용 — K1 한 가지 보완과 사용자 화면 확인 뒤 수용.
- H1~H5·H7: 제품 코드가 평가 측 사본과 같다(평가 측 대조 diff 0). 평가 측 시험 5건 포함 TK-137·138 시험 통과.
- CI 결과 인용: 필수 확인 성공(기록 시점에 pull_request 실행의 테스트 2개는 진행 중이었다 — 병합 전 완료·성공 확인). 평가 측 재실행: 관련 65개 파일 5,077건 통과·5 건너뜀(1차 5,072 + 평가 측 시험 5).
- U5 머리 줄 단일 표기 반영 확인.

K1 [화면·보고서 사실 오류] 머리 줄 검색 범위가 첫 판례의 질의 것뿐 — app.js 2848행(const firstScope), related_authorities.py 723행
- 원인: 판례는 인용 조문 최대 2개 질의에서 모인다(질의별 검색 건수가 다르다). 머리 줄이 precedents[0].search_scope만 써서, 평가 측 재현(근로기준법 제23조 2건 + 민법 제750조 1건)에서 '[관련 판례] 검색 379건 중 100건 (대법원 한정) 권위 순 정렬 상위 3건'으로 민법 질의(215건 중 100건)가 빠진다. 보고서(report_lines)는 아직 판례 줄마다 범위를 반복해 화면과 구조가 다르다.
- 고칠 것: 판례의 search_query·search_scope로 질의별 범위를 중복 없이 모아 '질의: 범위'를 ' · '로 이어 머리 줄에 한 번 적는다(예: '[관련 판례] 근로기준법 제23조: 검색 379건 중 100건 (대법원 한정) · 민법 제750조: 검색 215건 중 100건 (대법원 한정) — 권위 순 정렬 3건 · 검토 자료'). '상위'는 뺀다(질의별 상위 3건을 합친 수다). report_lines도 같은 구조(머리 줄 1개 + 판례 줄)로 바꾼다.
- 평가 측 사본 증분: docs/handoff/patches/TK-138_k1_on_17f6e73.diff — app.js·related_authorities.py, 이 PR의 test_report_lines_and_presentation을 머리 줄+판례 줄 구조로 고침, 시험 1건 추가(TestTK138ScopeHeaderK1). TK-137·138·F2 화면 시험 42건 통과. 캡처: docs/handoff/captures/TK-138/k1_*.png.

제출물: K1 반영 커밋, 화면 캡처 1280px·390px 각 1장(질의 2개·긴 사건명 포함 — 지금 제출본 1장은 5.7KB 1280×390 한 장뿐이라 판독이 어렵다). 그 뒤 사용자 화면 확인 → 수용.
```

### #232 2차 — 보완 지시
```
[평가 측 2차 판정 — #232 TK-139 보완본 (head bd2de2f, 기준 Steve 996ba14), 11-04]

판정: 보완 1회 더(마지막 통합 단계). J1~J10은 평가 측 사본과 같다(제품 코드 diff 0). 아래 J12·J13은 평가 측이 1차 판정 때 놓친 결함이다 — 평가 측 사본에서 발견·수정·검증했다. #231 병합 뒤 rebase(충돌 해소)와 사용자 결정 2건(시간 예산·문구)을 이번에 함께 반영한다.
- CI 결과 인용: 필수 확인 전부 성공. 평가 측 재실행: 최종 사본(Steve+#231 위 #232) TK-137·138·139·F2 화면 시험 60건, 관련 70개 파일 2,785건 통과.
- 평가 측 비공개 탐침(실제 별표 23, 문장 비공개). 3차(이번 판정용 새 세트, 10문장): PR 6/10·잘못된 확정 0 → 사본 10/10. 4차(J12·J13 적용 뒤 새로 지은 독립 세트, 12문장): PR 7/12, 사본 8/12(J13 보강 전)·9/12(보강 후), 잘못된 확정 모두 0. 1·2차 세트 26/28 유지. 3차 세트 기대값 1건은 영업 종류가 속한 절을 법령으로 확인한 뒤 평가 측이 정정했다.

원인과 고칠 것 (줄 번호는 bd2de2f 기준)

J12 [행 오연결, 평가 측 누락분] 업종 절 경계가 위반사항 문장 속 낱말로 바뀜 — disposition_criteria.py 294~310행
- 원인: 어느 행이든 업종 낱말과 '1.'·'2.' 같은 번호가 있으면 절을 바꾼다. 실제 별표 23의 124행('다. 식품소분업 및 유통전문판매업자의 준수사항 위반은 2. 식품판매업 등의 제9호가목에 따른다.')에서 절이 '식품소분·판매업'으로 바뀌어 1절(식품제조·가공업 등) 124~144행이 다른 업종으로 붙는다. 또 고정 목록 이름 '식품소분·판매업'은 1절의 식품소분업과 2절의 식품판매업을 한데 묶는다(별표 23 1절 머리: '영 제21조제1호의 식품제조·가공업, … 제5호가목의 식품소분업, … 나목3)의 유통전문판매업 …', 2절 머리: '제4호의 식품운반업, 제5호나목의 식품판매업(유통전문판매업은 제외한다) 및 제6호나목의 식품냉동·냉장업').
- 고칠 것:
  (가) 절 머리는 표 전체 폭 병합 행(merges에서 col=0, col_span=열 수)이고 '^(Ⅱ. 개별기준 )?N. ' 꼴인 행만 본다. 그 머리 글자 전체를 행의 industry로 둔다. 'Ⅲ'으로 시작하는 전체 폭 행에서 개별기준이 끝난다(그 뒤 행은 버림).
  (나) 서면 업종 → 절: 절 머리 글자에서 영업 이름을 뽑는다(정규식 의\s*([가-힣][가-힣·ㆍ\s]*?업)(?=[\s,(.]|및|을|를|이|은|$) + 절 제목 첫 '…업'). 공백·가운뎃점(·ㆍ)을 지운 뒤 서면 업종 낱말과 같거나 서로 포함되면 그 절로 본다. 맞는 절이 정확히 하나일 때만 그 절 행에서 맞추고, 0개·2개 이상이면 UNVERIFIED.
  (다) 서면에 INDUSTRY_PATTERNS 업종이 둘 이상 나오고 처분 문장 주변에서도 하나로 좁혀지지 않으면 UNVERIFIED. 패턴 업종이 하나도 없을 때만, 절 머리 영업 이름(4자 이상) 가운데 서면에 나오는 것을 서면 업종으로 쓴다(예: '식품소분업', '식품첨가물제조업'이 고정 목록에 없어도 판정).

J13 [미판정] 별표 위반사항 앞의 조문 인용구 — 91행(_row_core), 405행
- 원인: '법 제48조제2항에 따른 …', '법 제49조제1항 단서에 따른 …'처럼 인용구가 붙은 행은 서면 서술과 Jaccard가 0.52~0.58에 머물러 0.60을 넘지 못한다.
- 고칠 것: 양쪽(서면 위반 사실·별표 세목)에서 앞머리 인용구를 같은 규칙으로 뗀다: ^(?:「[^」]+」\s*|[가-힣]*법(?:\s*시행령|\s*시행규칙)?\s*|영\s*|규칙\s*)?제\d+조(?:의\d+)?(?:제\d+항)?(?:제\d+호)?(?:[가-하]목)?(?:\s*(?:및|또는|ㆍ|·|,)\s*(?:제\d+조(?:의\d+)?)?(?:제?\d+[항호])?(?:[가-하]목)?)*(?:\s*(?:단서|본문|전단|후단))?\s*(?:에\s*따른|에\s*의한|에\s*규정된)\s*

R1 [통합] #231 병합 뒤 rebase — related_authorities.py·app.js 충돌
- #231(TK-138)과 같은 자리를 고친다. #231이 Steve에 병합되면 그 위로 rebase하고 둘 다 남긴다: review_related_authorities는 TK-137 → TK-138 → TK-139 순서, 빈 결과 조건은 'not related and not delegations and not explicit_refs and not precedents and not disp_criteria', out에 precedent_status·precedents·disposition_criteria 모두, report_lines·app.js에 [관련 판례] 묶음 다음 [처분기준 검토] 줄. app.js는 K1 블록의 닫는 중괄호를 잃지 않게 한다(평가 측 사본에서 그 자리 누락으로 문법 오류가 났다).

J11 [사용자 결정 11-04 'TK-139 별도 상한'] — related_authorities.py _discover_tk139_disposition_criteria(387행~)
- 문서 15초 공용 예산(TK-137·138)과 별도로 TK-139 상한 10초(TK139_MAX_SECONDS), 외부 호출(resolve_statute·get_law_appendices·download_appendix_hwp) 직전마다 잔여 3초 이상(TK139_MIN_CALL_SECONDS), 모자라면 {"status": "UNVERIFIED (시간 예산 소진)", "comparison_result": "UNVERIFIED", "advisory_only": True}·상태 "BUDGET_EXHAUSTED". TK-139는 지금처럼 '영업정지'와 시행규칙이 있는 서면에서만 외부 호출을 한다.
- 평가 측 실측(이 환경, http, 운영 https 미측정): 서면이 시행규칙 조문을 인용해 앞 단계 검증이 판(MST)을 확정한 경우 호출 2회·3.7초로 '일치'+감경 병기. 조문 인용 없이 판을 직접 찾으면 resolve_statute 9.5초(1.8MB 본문 포함)로 10초 안에서 '시간 예산 소진'(알려진 한계).

U [사용자 결정 11-04 '권고안 적용'] 화면·보고서 문구 — report_lines 617행, app.js 2847행
- 한 함수(disposition_line)로 화면·보고서 같은 문구: '[처분기준 검토] {법령명} {[별표 N](의M)} · {업종 절 제목('…영 제21조' 앞)} · {N}차 위반 '{위반사항}': 별표 {기준 칸} / 서면 {처분} → {일치|불일치(확인 필요)} · {감경 규정} · 검토 자료'. 내부 코드(MATCHED·DISCREPANCY_DETECTED)는 화면·보고서에 내지 않는다. 별표 번호는 _discover_tk139에서 chosen_appendix의 번호(앞 0 제거)·가지번호로 result["appendix_label"]에 넣는다.

제출물·수용 기준
- 평가 측 사본 증분 두 개(evaluator/round8-promotion, docs/handoff/patches/):
  · TK-139_j12_j13_on_bd2de2f.diff — 지금 head 위 J12·J13과 시험(test_w3를 실제 파서 꼴로, TestTK139SectionJ12 추가).
  · TK-139_on_231_eval.diff — Steve+#231 위 최종 상태(R1·J11·U 포함, 시험 TestTK139BudgetJ11 추가, 보고서 시험 새 문구). #231 병합 뒤 rebase한 브랜치에 맞춘다.
- 시험: TK-137·138·139·F2 화면 60건, 관련 70개 파일(related_authorities·law_go_kr·_http_get·source_get·hwp_parser·disposition·argument_validity·input_contract) 2,785건 통과(평가 측 사본).
- 화면 캡처 1280·390px(평가 측 캡처를 다시 내지 말고 구현 측이 이 PR 코드로 직접 찍는다 — 지난 제출본 캡처는 평가 측 파일과 바이트가 같았다), 사용자 확인 뒤 수용.
- 수용 SHA에서 평가 측 verify_all 전체, 실제 법제처 응답·별표 23 끝에서 끝까지, 새 비공개 탐침 잘못된 확정 0·판정 가능 문장 2/3 이상.
```

### #232 3차 — 작은 보완 지시
```
[평가 측 3차 판정 — #232 TK-139 2차 보완본 (head 3bbaf34, 기준 Steve ae2c6e8), 11-04]

판정: 작은 보완 1회(J14·J15) + 화면 캡처 다시. 제품·시험 코드는 평가 측 최종 사본 ad46936과 같다(diff 0). 아래 J15는 평가 측이 2차 지시로 준 정규식(J13 인용구·J5 형식어)의 결함이다 — 평가 측 책임이며 고칠 코드를 그대로 준다.
- 평가 측 재실행(이 head): verify_all --base ae2c6e8 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,425·브라우저 197), 고정 dev 82.6·holdout 81.9·FP 0, 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0 — 변화 0. 실제 법제처 응답·별표 23(판 확정 경로) 3회 3.4~3.9초 '일치'+감경 병기.
- CI 결과 인용: 'CodeQL 새 경고 게이트' 실패 — py/redos(심각도 7.5) 2건, disposition_criteria.py 84행(_CITE_PREFIX_RE). 나머지 필수 확인 성공.
- 평가 측 비공개 탐침 5차(이번 판정용 새 세트, 10문장): 이 head 결과 10/10이나, 확정 판정을 연결된 행으로 전수 점검하니 1건이 다른 행에 붙었다(결과 꼴은 맞았으나 화면의 위반사항·기준값이 틀림). 6차(J14 뒤 새로 지은 독립 세트, 6문장): 이 head 2/6(다른 행 연결 1건), 사본 4/6, 사본의 확정 판정은 모두 바른 행.

원인과 고칠 것 (줄 번호는 3bbaf34 기준, packages/legal_engine/disposition_criteria.py)

J14 [행 오연결] 괄호 속 부연 때문에 더 짧은 다른 행에 붙음
- 원인: 실제 별표 23의 '사. 급수시설기준을 위반한 경우(수질검사결과 부적합 판정을 받은 경우를 포함한다)'(269행)는 괄호 부연 때문에 서면 '급수시설기준을 위반'과의 Jaccard가 낮아, 같은 절의 '1) 시설기준을 위반한 경우'(271행)에 붙는다. 2절(177·180행)에서도 같다.
- 고칠 것: 양쪽(서면 위반 사실·별표 세목)에서 괄호 부연 \([^()]{0,200}\)을 지운 뒤 비교한다(_strip_cite 안에서).

J15 [CodeQL py/redos, 평가 측 지시 결함] 인용구·형식어 정규식의 역추적 폭증 — 80~83행(_CITE_PREFIX_RE), 79·95행(_TAIL_RE)
- 원인: _CITE_PREFIX_RE는 '\s*(및|또는|·|,)\s*(…)?(…)?(…)?' 반복 안에 빈 매칭이 가능한 조각과 \s*가 이어져 있어, 평가 측 재현에서 '제1조' 뒤 ' ,'를 2,000번 이은 입력이 10초를 넘긴다. _TAIL_RE는 \s* 두 개가 모두 생략 가능한 조각을 사이에 두고 붙어 있어 공백 2,000칸에서 10초를 넘긴다(이번 CodeQL 경고에는 없었지만 같은 꼴).
- 고칠 것(평가 측 사본 그대로):
  · _CITE_PREFIX_RE를 지우고 _CITE_END_RE = r"에 ?(?:따른|의한|규정된)", _CITE_TOKEN_RE = r"「[^」]{1,60}」|[가-힣]{0,20}법|시행령|시행규칙|영|규칙|제\d{1,4}조(?:의\d{1,3})?|제?\d{1,3}[항호]|[가-하]목|단서|본문|전단|후단|및|또는|[ㆍ·, ]", _PAREN_RE = r"\([^()]{0,200}\)"로 둔다.
  · _strip_cite: 괄호 부연 제거 → 공백 한 칸으로 정리 → 앞 120자 안에서 _CITE_END_RE를 찾고, 그 앞부분에 '제+숫자'가 있고 _CITE_TOKEN_RE로 전부 지워지면(인용 토큰만으로 이루어졌으면) 그 뒤부터 쓴다.
  · _TAIL_RE = r" ?(?:하는 ?)?(?:행위를 ?)?(?:한|하는|된)? ?(?:것|경우)?(?:로서)?$", _strip_tail은 " ".join(text.split())에 적용한다.
- 평가 측 재현(사본): 함수 4개(_strip_cite·_row_core·_strip_tail·extract_document_claim) × 악성 입력 5종(인용 반복·쉼표 반복·긴 한글·괄호 반복·공백 반복) × 길이 2,000·20,000 = 40회 모두 0.04초 이하. 탐침 1~6차 결과는 정규식 판과 같다.

화면 캡처: 제출본 4장(docs/handoff/captures/TK-139/01·02_*, docs/handoff/screens/tk139/01·02_*)은 제목과 빈 상자뿐이고 [처분기준 검토] 줄이 없다. 처분기준 결과가 든 화면(관련 판례와 함께)으로 다시 찍어 바꾼다. 평가 측이 이 head로 찍은 화면(docs/handoff/captures/TK-139/head_3bbaf34_*.png)과 같은 내용이면 된다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-139_j14_j15_on_3bbaf34.diff(evaluator/round8-promotion) — 제품 1파일, 시험 3건(TestTK139ParenJ14·TestTK139RedosJ15 2건).
- 'CodeQL 새 경고 게이트'를 포함한 필수 CI 전부 성공.
- 시험: TK-137·138·139·F2 화면 63건, 관련 70개 파일 2,788건 통과(평가 측 사본).
- 화면 캡처 교체 → 사용자 화면 확인 → 수용.
```

## 2-16. 진행 현황(11-05)과 구현 지시 — TK-76 3주기 EVI-INCONS 후속(S1·N1~N3) (사용자 '구현 계획 중 현재 진행 상황 정리, TK-76 다음 지시')

다음 릴리스 범위(11-03 사용자 결정: 계획 티켓 전체 구현 뒤 릴리스) 진행 현황 — Steve `4323721`:

| 티켓 | 내용 | 상태 |
|---|---|---|
| TK-137 | 관련 근거 탐색(위임·명시 참조) | Steve 병합 `996ba14` |
| TK-138 | 관련 판례 권위 가중 | Steve 병합 `ae2c6e8` |
| TK-139 | 처분기준 별표 대조 1유형 | Steve 병합 `4323721` |
| TK-140~148 | 문서 처리·성능·화면 등 9건 | Steve 병합(11-03~04) |
| TK-76 3주기 EVI-INCONS | A 산식(#214)·B 문서 간(#224) 병합 / 후속 S1·N1~N3 **#233 `b827a2f` 수용·Steve 병합 `90cc681`(11-05)** / C 발신 시각(메모 필요) | 진행 중 |
| TK-76 3주기 EVI-OVR | #230 병합 `349a30b` | 잔여 5꼴 이번 릴리스 포함(11-08 사용자 결정) — 구현 지시 2-24절 |
| TK-76 3주기 EVI-FORM·EVI-NUM·EVI-DATE·EVI-COPY 잔여, EVI-LOGIC 잔여 | 유형마다 설계 메모 → 구현(순서: FORM → NUM → DATE → COPY → LOGIC → INCONS C) | **EVI-FORM 메모 #234 Steve 병합 `00e668a`, 구현 #235 Steve 병합 `13641e0`(11-06)**, **EVI-NUM #236 Steve 병합 `77b8d07`(11-08)**, **EVI-DATE: T1 병합 `c977c0b`·T2·T3 메모 병합 `900502a`, T2·T3 #239 Steve 병합 `bb46bce`(11-08), T2 대상 맞추기 후속 #243 수용(2-19-5절)** · **EVI-COPY C1 #240 Steve 병합 `2969d8c`(11-08)** · **EVI-LOGIC 잔여 L1~L3 #241 수용(11-08, 2-21-1절)** · **EVI-INCONS C 메모 #242 Steve 병합 `a89311c`, 구현 요청(2-22-3절, 조건 C1)** · **산식 후속 #244 Steve 병합 `a836bba`(11-09)** · **EVI-OVR 잔여 #245 Steve 병합 `a356d76`(11-09)** · **EVI-INCONS C #246 Steve 병합 `3d54f77`(11-09), 후속 A 묶음(T1·T2·I1·I2) 지시(2-27절, 2-25절 대체), #247 `8171fc2` I3·I4 반영 확인, 판정용 새 10차 미달 — I5(복합 명사구 머리 통일, I2 회귀)·I6(INTERNAL_DATE 해지·해제 접미)·I7(가정·의문 제외) 보완(2-27-3절), #247 `a21ddb3` I5~I7 반영 확인, 판정용 12차 오탐 2(서법 축 — 평가 측 I7 지시 결함)·미탐 1(제외 낱말 축) → I8·I9 보완(2-27-4절)** |

```
[평가 측 구현 지시 — TK-76 3주기 EVI-INCONS 후속 PR(S1·N1~N3), 기준 Steve 4323721, 11-05]

목적: 3주기 1항 PR1(A 산식, #214)·PR2(B 문서 간 대조, #224)에서 남긴 미탐과, 이번 평가 측 탐침에서 새로 드러난 산식 오탐을 고친다. 한 PR(EVI-INCONS 후속)로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료).

평가 측 사전 검증(사본, Steve 4323721 위, 저장소 밖 비공개 탐침 — 문장 비공개):
- S1 문서 간 탐침 1차(이번에 새로 지음): 기준 2/6·오탐 0/6 → 사본 6/6·0/6. 2차(수정 뒤 새로 지음, 독립): 기준 4/5 → 사본 5/5·0/6. 지난 PR2 탐침 5~8차: 하락 0·오탐 0(8차 1건 새로 잡힘).
- 산식 탐침 1차: 기준 2/5·오탐 1/6 → 사본 5/5·0/6. 2차(독립): 기준 3/4·0/6 → 사본 3/4·0/6(남은 1건은 단위 '대' 기존 한계, 이번 범위 밖). 지난 PR1 탐침 3~6차: 하락 0·오탐 0(6차 1건 새로 잡힘).
- verify_all --base 4323721 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,432·브라우저 197), 고정 dev 82.6·holdout 81.9·FP 0, 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0 — 변화 0(세트 득점 0). 산식·문서 간 관련 31개 파일 784건 통과. 하드코딩·시험 약화·평가 세트 문구 점검 통과.

원인과 고칠 것 (줄 번호는 Steve 4323721 기준)

S1 [미탐] 문서 간 앵커 속성 '…금일·…금액'을 앞부분 '…금'으로 먼저 잡음 — packages/claim_engine/cross_document_entities.py 315~319행(_ANCHOR_RE)
- 원인: 속성 꼴 [가-힣]{1,4}?(?:일자|일|금)이 게으른 반복이라 '입금일'의 '입금'을 먼저 '…금'(금액) 속성으로 잡는다. 뒤 값이 날짜라 금액으로 읽히지 않아 버려지고, finditer가 그 뒤로 넘어가 '입금일'로 다시 시도하지 않는다(입금일·송금일·출금일·입금액 모두 미탐).
- 고칠 것: attr 그룹 바로 뒤에 경계 예견 (?=\s|[은는이가을를의에도과와으로:：]|$)를 둔다. 한글이 이어지면 더 긴 속성으로 되짚는다.

N1 [미탐·오탐] 기간 몫 이름표('N월분'·'N분기분'·'N년분')가 피연산자로 들어감 — packages/claim_engine/calculation.py 152행 근처, 307~310행(unit_is_ordinal_label)
- 원인: 차수 표지(_ORDINAL_UNITS: 차·번째·회차·순위)만 이름표로 보고, 수 + 달력 기간 + '분' 꼴은 수량으로 읽어 산식에 넣는다. 그래서 'N월분 a개 + M월분 b개 …'의 N·M이 피연산자로 더해져 산식이 깨진다.
- 고칠 것: _PERIOD_LABEL_RE = re.compile(r"(?:월|분기|반기|년|연)분")을 두고, unit_is_ordinal_label 첫머리에서 unit_part가 이 꼴로 시작하면 True(이름표). 'N개월분'(기간의 양)·'N일분'은 수량이므로 넣지 않는다.

N2 [오탐, 기존 결함] 뺄셈 서술을 합계로 덧셈 검산 — calculation.py 802~826행(_verify_block)
- 원인: TOTAL_LABEL_RE에 '실지급액'·'차인지급액' 등이 있어 '○○ A원에서 ○○ B원을 빼면 실지급액은 C원' 꼴 문장을 A+B=C 합계로 검산한다. 맞게 계산한 문장도 '합계가 세부 금액 합산값과 다르다'가 난다.
- 고칠 것: section_before 판정 뒤, text[section_start:total_match.start()]에 뺄셈·곱셈 서술(_SUB_PRED·_MUL_PRED)이 있으면 return []. 그 문장은 산식 검산(서술형 산식 경로)이 맡는다(평가 측 확인: 틀린 뺄셈은 그 경로가 잡는다).

N3 [N1의 부작용 방지] 나열 쉼표를 절 경계로 봄 — calculation.py 150행(_OPERAND_CLAUSE_BREAK_RE)
- 원인: ',(?!\d)'는 'A원, N월분 B원'처럼 쉼표 뒤 공백 다음에 숫자가 오는 나열을 절 경계로 자른다. N1로 'N월분' 이름표가 빠지면 마지막 두 항목만 더해 맞는 합계를 틀렸다고 낸다(평가 측 사본에서 재현·확인).
- 고칠 것: ',(?! ?\d)'로 바꾼다(쉼표 뒤 공백 한 칸을 건너 숫자가 오면 나열).

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_incons_followup_on_4323721.diff(evaluator/round8-promotion) — 제품 2파일(10줄 남짓), 평가 측 시험 tests/test_tk76_followup_s1_n.py 4건(기준에서 3건 실패, 1건은 N3 부작용 방지). 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2 규약: 닫힌 장면 낱말 사전·고정 문장 틀 금지(이번 수정은 꼴 규칙뿐), 평가 측 탐침 문장 사용 금지. 2-2 다 제출물: 귀속표(규칙별 고정·은퇴·train 득점 — 이번 은퇴·고정 변화 0이면 '세트 득점 0'), 변형 시험(어순·연결 어미·같은 꼴 다른 낱말), train EVI-INCONS 미득점 원인 건수표(문장 인용 금지).
- 수용: 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침 하락 0, 고정·은퇴 하락·오탐 0, verify_all 전체 종료 0, 필수 CI(CodeQL 게이트 포함) 성공.
- 이번 범위 밖(후속): 단위 '대' 수량 산식 미탐, EVI-INCONS C(문서 안 같은 회신의 발신 시각 — internal_inconsistency.py, 설계 메모 필요).
```

## 2-2. 탐지 PR 공통 수용 규약 — 하드코딩 금지 (2026-10-24 사용자 지시 '평가기준을 엄격히 적용하되 하드코딩으로 충족하지 못하게 제한')
10-24 검토(#175 `618130c`·#165 `94c645f`·#167 `af28269`/`0731277`)에서 세 PR이 같은 방식으로 실패했다. 은퇴 세트 항목만 정확히 오르고(EVI-DATE 7·EVI-OVR 5·EVI-INCONS 3) train 같은 유형은 0이다. 평가 측의 비공개 다른 표현 탐침도 0이다(#175 0/4·#165 0/2·#167 장소·서명자 규칙 0). 새 정규식은 고정 낱말 여러 개를 순서대로 이은 문장 틀이다. 그 낱말은 은퇴 항목 위치 소제목 낱말과 8~9개씩 겹친다. **아래 규약은 A-4·B-1·B-3과 이후 모든 탐지 PR에 적용한다. 하나라도 어기면 점수와 무관하게 불승인한다.**

**가. 규칙을 만들 때 쓸 수 있는 것과 없는 것**
- 쓸 수 있다: 법령·판례의 개념, 티켓·메모의 유형 정의, 직접 지어낸 합성 예문.
- 쓸 수 없다: 은퇴·고정(dev·holdout) 세트의 문서·정답지·위치 소제목, `retired_compare` 출력의 위치 문자열, train 문장, 평가 측 판정 코멘트·탐침의 예문.
- `retired_compare` 출력은 결과 확인용이다. 출력에 나온 위치 문자열을 보고 규칙을 고치면 그 규칙은 무효다.

**나. 규칙 형식 — 기계적으로 판정한다**
1. **문장 틀 금지.** 한 정규식에 한글 고정 낱말(2자 이상) 3개 이상이 순서 고정으로 이어지면 문장 틀로 본다(사이에 `[^.\n]{0,N}`·`.*?`가 있어도 같다). 이런 정규식은 삭제한다.
   - 허용하는 형식: 닫힌 범주 사전 하나와 구조 슬롯(주체·대상·술어·날짜·값)의 결합.
   - 범주 사전은 한 정규식에 대안(`|`)으로 넣을 수 있다. 사전 전체 목록과 범주 이름은 설계 메모에 적는다.
2. **장면 명사 금지.** 특정 사건 장면을 가리키는 사물·장소·행위 명사를 사전에 넣지 않는다(사건마다 달라지는 물건·장소·행위 이름. 법률 개념 범주에 속하지 않는 낱말은 모두 여기에 든다).
   - 허용하는 사전: 법률 개념 범주다. 문서 종류(통지·견적·식별·진단·사진·영수·확인서), 법률상 사건 종류(신청·처분·발송·도달·체결·해지·입사·퇴사·접수·보정), 속성 종류(금액·수량·일시·장소·서명자·횟수·지위), 문법 표지(전칭·한정·시상 부사)가 이에 해당한다.
3. **낱말 겹침 대조.** 평가 측은 `packages/`에 새로 들어온 한글 낱말을 은퇴 항목 위치 소제목 낱말과 기계 대조한다(일반어 제외).
   - 겹치는 장면 낱말이 들어 있는 규칙은 삭제 대상이다. 그 규칙이 낸 득점은 세지 않는다.
   - 평가 측은 겹친 낱말 목록을 공개하지 않는다(공개하면 그 자체가 정답 누설이다).
   - 예외: 설계 메모에서 승인된 법률 개념 사전(문서 종류·법률상 사건 종류·속성 종류·문법 표지)의 낱말은 겹쳐도 무효로 보지 않는다. 대신 그 규칙은 라-2 탐침 기준을 넘어야 득점을 인정받는다.
4. **한 항목 전용 규칙 금지.** 규칙 하나가 은퇴 항목 하나에만 반응하고, 합성 다른 표현 3개 중 2개 이상을 못 잡으면 그 규칙은 무효다.
5. **병렬 검사 신설 금지(4절 기존 금지 재확인).** 산식·날짜 병기처럼 기존 모듈(`calculation.py`·`date_verifier.py`)이 하는 검사를 새 모듈에 다시 만들지 않는다. 부족한 꼴은 기존 모듈을 고치고 그 모듈의 시험을 늘린다.

**다. PR에 반드시 낼 것 — 빠지면 평가 측은 측정하지 않고 돌려보낸다**
1. **요구 대응표**: 판정 코멘트의 요구 번호 → 바꾼 파일·함수 → 확인 시험 이름. 1건이라도 비면 검토하지 않는다.
2. **규칙별 득점 귀속표**: 은퇴·train·고정 세트에서 오른 항목마다 그 득점을 낸 규칙 상수·함수 이름을 적는다(위치 문자열은 유형·문서 번호까지만).
   - 평가 측은 규칙을 하나씩 끄고 다시 재서 귀속이 맞는지 확인한다.
3. **변형 시험**: 규칙마다 합성 양성 3개 이상, 정상 대조 3개 이상을 둔다.
   - 양성 각각에 어순 바꿈, 연결어미 바꿈, 같은 범주의 다른 낱말 바꿈의 세 변형을 붙인다. 변형도 모두 잡혀야 한다.
   - 대조에는 1차 판정에서 오탐이 난 꼴을 **자기 말로 다시 지은 문장**으로 넣는다.
4. **train 같은 유형의 미득점 원인표**: 세트별로 건수와 원인 분류만 적는다(문장 인용 금지). 규칙이 train에서 0이면 이유를 적는다.
5. 점검표 1~7항(5절)과 `precheck_pr.py` 요약.

**라. 수용 기준 — 미리 공개하고 바꾸지 않는다**
1. 고정 dev·holdout 항목 하락 0, 오탐·A등급 증가 0, 은퇴 4세트 항목 하락 0. 필수 CI 5종이 성공해야 한다.
2. **평가 측 비공개 탐침**(이번 판정 뒤 새로 짓는다. 이전 탐침과 판정 코멘트 예문은 쓰지 않는다).
   - 유형별 양성 재현 2/3 이상이어야 한다.
   - 정상 대조 오탐은 0이어야 한다. 1차·2차 판정에서 오탐이 났던 꼴의 새 표현도 여기에 넣는다.
3. **은퇴 득점 > 0이면서 train 같은 유형 0이면 과적합으로 추정한다.** 이 경우 2항 탐침 기준을 모두 넘어야만 은퇴 득점을 인정한다.
4. 시험 삭제·약화(assert 감소·대조 시험 삭제·표시 추가)는 `docs/handoff/requests/` 사유 문서와 평가 측 승인 없이는 불승인이다.
5. PR 본문 수치는 그 head의 재현 출력이어야 한다. 본문이 실측과 다르면 돌려보낸다.

**마. 반복을 줄이는 절차**
- 구현 전에 **설계 메모 보정본**(반 쪽~한 쪽)을 먼저 낸다. 담을 것: 범주 사전 전체 목록과 각 낱말의 범주 근거, 슬롯 구조, 제외 구조, 위 '다'의 시험 목록 초안. 평가 측은 이 단계에서 나·라 위반을 미리 걸러 승인한다. 메모 승인 전에는 구현 커밋을 올리지 않는다.
- 한 PR 안에서 관계없는 변경(예: #167의 TK-125 문서)을 섞지 않는다. 별도 PR로 낸다.
- **이번 보완에서도 라-2 탐침 기준에 못 미치면, 평가 측은 그 티켓을 0.14.0 범위에서 빼자고 사용자께 건의한다.** 릴리스는 나머지로 진행한다.

## 3. 할 일

### 10-21 판정 현황 (#150~#163, 사용자 지시 'PR #150 ~ #163 검토'; 설계 메모 #156~#160은 같은 날 2차 판정)
각 PR의 평가 측 판정 코멘트가 요구의 원문이다. 아래는 요약이다. 보완한 head마다 '검토 요청' 코멘트(head SHA·점검표)를 남긴다.

| 항목 | PR | 판정 | 다음 할 일 |
|---|---|---|---|
| A-2 TK-81 잔여 | #149 `997d9f7` | **수용·병합** | Steve `74d45a3`(10-21). 완료. #161은 닫힘. |
| A-2c TK-93 | #173 `cc5aa91`(2차) | **수용·병합** | Steve `9b96e17`(10-24). 완료. |
| A-3 #126 잔여 | 1·2항 #163 `a2103c5` 병합 / 3항 #176 `42d36f4`→`95262a4` | **3항 수용·병합** | 은퇴 10 38.9→43.9·오탐·A등급 1→0, 다른 세트·train 변화 0(평가 측 재측정), CI 전부 성공. TK-73 한쪽 날짜 잔여 해제 승인(사유 문서 126). 남는 위험(같은 이름·다른 문서·한쪽만 날짜)은 TK-73 known_open. Steve `de91c55`(10-24) 병합. 완료. |
| A-4 EVI-DATE | 메모 #169 `061581f` 조건부 승인 / 구현 #175 `ed5e5d3`→`618130c` | **2차 불승인(하드코딩)** | 은퇴 EVI-DATE 미득점 7건이 정확히 모두 오르고(08 46.7→51.1·08b 40.7→42.6·09 48.3→51.7·10 38.9→42.6), train EVI-DATE 0, 고정 0. 평가 측 탐침: 자연 양성 0/3, 같은 사건 다른 표현 0/4, 틀 맞춤 1/4. 원인: 새 정규식 8개(`SAME_SUBJECT_LIFECYCLE_RE`·`LIFECYCLE_DURATION_INVERSION_RE`·`TARGET_BOUND_DISPOSITION_RE`·`ANAPHORIC_TARGET_INVERSION_RE`·`PERIOD_END_WRITE_INVERSION_RE`·`RELATIVE_NEXT_DAY_INVERSION_RE`·`SAME_DAY_EARLIER_TIME_INVERSION_RE`·`SAME_OBJECT_FIRST_ACQUIRE_TIME_INVERSION_RE`)가 모두 2-2 나-1 문장 틀이다. 은퇴 위치 소제목과 겹치는 낱말 9개. 1차 제외 대조 시험 `test_temporal_event_exclusion_controls` 삭제, 양성 assert 6→5(시험 약화, push 실행 `check_test_edits` 실패). 본문 '은퇴 점수 유지'는 실측과 다르다. **요구**: 3절 A-4 '2차 보완 지시'. **10-24 메모 보정본 `c0cc686`(127) 조건부 승인**: 메모 재제출 없이 구현. 조건 8개(결정적 절 단위 추출·외부 의존성 금지, 표면형 사전 전체, 신청→통지 등 위험 쌍 대상 결합 필수·근거 조문, 민법 제157조 단서·제161조, B 조건, 기관 접미 규칙, O(n)·옛 정규식 완전 삭제, 귀속표·train 원인표·시험)은 PR #175 판정 코멘트 원문대로. **10-24 구현 `ba62858` 불승인(탐침 미달)**: 은퇴 +1(08)·train·고정 0. 새 탐침 양성 6/10·대조 오탐 5/12. 원인: 대상 결합이 절 문자열 포함·사건 종류명 대체로 사실상 꺼짐, 접수→처분 대상 결합 누락·체결→통지/도달 확장, 승인 밖 기간종료→작성·시각 역전·목적물 인계 분기(옛 틀 이식), 장면 낱말('매체'·'인계'·'정산'·'수임'), 기관명 열거 잔존. 원인별 4차 보완 지시(3절 'A-4 4차 보완 지시', R1~R9) 발행. **사용자 결정(10-24): A-4는 0.14.0 범위 유지, 릴리스는 A-4 수용까지 대기.** **10-24 4차 `b1e5cad` 보완(수용 직전)**: CI 5종 성공. 은퇴 08·08b +1씩(일반 규칙 귀속), 하락 0, train·고정 0. 새 탐침 양성 9/10·대조 오탐 2/12. 남은 원인 U1~U4(새 주기 구조 규칙·'새로', 정정 문장 처리, 피동 사건 대상·'에 관하여', 미사용 '작성' 사전) — 3절 'A-4 5차 보완 지시'. **10-24 5차 `e0315f2` 보완**: U1~U4 반영(4차 세트 10/10·0/12). CI 5종 성공, 은퇴 +2 유지·하락 0. 새 5차 세트 8/10·오탐 1/12, 3차 세트 재실행 오탐 1/12. 원인 W1~W3(4차부터 있던 대상 결합 우회 분기 — 평가 측 지난 판정 누락, 상대방 주장 표면형, 발생→신고·대상 정규화) — 3절 'A-4 6차 보완 지시'. **10-25 6차 `27f5277` 보완(W1 미이행)**: W2 일부·W3 반영, CI 성공. 은퇴 +2 유지·하락 0. 탐침 3차 10/10·4차 9/10·5차 9/10(오탐 1)·새 6차 9/10·**오탐 6/12**. 우회 분기가 '3) 규칙별 결합'으로 남고 '2) 지시어 바인딩'(낱말 존재로 일치) 신설. 평가 측 '엄격 일치만' 변형: 오탐 0~1, 은퇴 +2 유지(분기 득점 기여 0). 원인 Z1~Z4(분기 삭제, 대상 추출 4결함, 종결형 상대방 주장, 접미 일치) — 3절 'A-4 7차 보완 지시'. **10-25 7차 `76c5895` 보완**: Z1(우회 분기 삭제)·Z3·Z4 이행, CI 성공. 은퇴 +2 유지·하락 0. 탐침 3차 6/10(직전 10/10)·4차 9/10·5차 7/10(오탐 1)·6차 7/10(오탐 3)·새 7차 6/10(오탐 1/11). 원인 AA1~AA6(넓은 대상 승계 단계, 조사 붙은 토큰을 삼키는 대상 창, 지시어 접두 판정, 기관 접미 비고정, 블록 단위 '소를 제기' 제외, 표면형 의존 피동 판정). 승계만 끈 변형은 오탐 0 — 3절 'A-4 8차 보완 지시'. **10-25 8차 `2f7627d` 조건부 승인**: AA1~AA8 반영, 기존 시험 전부 통과, CI 성공, 은퇴 +2·하락 0. 탐침 3~8차 양성 7~9/10, 오탐 5·8차 각 1(다른 계약 주제 승계). DD1(U3 주제 대상 판정을 정규화 전 이름으로, 처분 종류 낱말 제외) 조건 — 평가 측 사본 검증: 6세트 오탐 0·기존 시험 통과·세트 동일 — 3절 'A-4 9차 판정'. **10-25 `5396f5a` 수용**: DD1만 반영, 사전 검증 사본과 같은 결과(탐침 3~8차 오탐 0, 기존 시험 통과, 은퇴 +2 유지), CI 성공. Steve `5031b5f`(#165 병합)과 충돌 없음. — 3절 'A-4 판정 — 수용'. **Steve 병합 `907c2fa`(10-25).** |
| B-1 TK-91 | 메모 #156 `1c821b8` 승인 / 구현 #165 `a9bc8c7`→`94c645f` | **3차 불승인(하드코딩)** — 메모 보정본 먼저 | 은퇴 EVI-OVR 5건 상승(08 48.9·08b 42.6·09 51.7·10 40.8), train 0, 고정 0. 탐침: 다른 표현 0/2, 틀 맞춤 1/2. 원인: `_STRUCT_OVERREACH_SUBJ_RE`·`_STRUCT_OVERREACH_PRED_RE`에 장면 명사·고정 구절이 들어 있다(은퇴 소제목과 겹치는 낱말 8개). `_DIRECT_PROOF_STRUCTURE_RE` 첫 대안이 `r"(?:'r'"`로 시작해(따옴표 오타) 그 갈래는 절대 맞지 않는다. 메모 승인 조건 '증명 근거 구조'가 그만큼 꺼져 있다. **요구**: 3절 B-1 '3차 보완 지시'. **10-24 메모 보정본 `124ca75`(128) 조건부 승인**: '현장'·'감정서' 삭제, 능력 매트릭스(7×4) 상수, 술어는 증명 대상 절에만, 부정·상대방 주장 제외, 범주는 서증 명칭에서만, B/C 등급 규칙, 귀속표·시험. PR #165 판정 코멘트 원문대로. **10-24 구현 `2c2a903` 보완**: 하드코딩 해소(장면 정규식 삭제·겹침은 법률 범주어뿐). 고정·은퇴·train 변화 0. 새 탐침 양성 4/6·대조 오탐 3/12. 원인 S1~S9(술어 부분 문자열 일치·'의사', 통지 술어 주체 미확인, 발신인 문장 전체 추정, 직접 증명 표면형 누락('에 의하여'·'로'), 대상 절 없으면 문장 전체, 완료 활용형 나열, 문장 단위 제외, 등급 분기, 득점 0 원인 진단) — 3절 'B-1 4차 보완 지시'. **10-24 5차 `9806494` 보완**: CI 5종 성공. 오탐 3/12→0(S1~S8 반영). 세트 득점 0. 탐침 양성 3차 4/6·4차 3/6(합 7/12 < 2/3). 원인 V1~V4(명사 뒤 수량 전칭, 완료 술어 활용형, 범주 접미 일치, S9 진단표 미제출) — 3절 'B-1 5차 보완 지시'. **10-24 6차 `2b985e6` 보완**: CI 5종 성공, 세트 득점 0·하락 0. 재현 합계 14/18(기준 충족), 3·4차 세트 오탐 0 유지, 새 5차 세트 오탐 2/12(상대방 발신 동사 연쇄, '다투지만'). S9 표 제출(미득점 18 중 범주 미식별 7). 원인 X1~X3 — 3절 'B-1 6차 보완 지시'. 득점 0이면 Added 포함 여부 사용자 결정 예정. **10-25 7차 `0daf35b` 보완**: X1~X3 반영, CI 성공, 세트 득점 0. 재현 3~5차 6/6. 금전 전칭이 잡히며 판정 결함 노출: 4·5차 세트 새 오탐 2·2, 새 6차 오탐 8/12. 원인 V1~V5(금전 전칭의 범주 분류·결합 합집합, '-기 어렵' 부정, 상대방 종결형(평가 측 X3 지시 누락), '-였다면' 가정, 부사 낀 발신 동사) — 3절 'B-1 7차 보완 지시'. **10-25 8차 `17f7734` 보완**: V1~V5 반영, CI 성공, 세트 득점 0. 6차 세트 오탐 8/12→1/12. 평가 측 V1 결함 정정(특정 대금 전액 ↔ 채무 전체 구분, 지난 세트 양성 2문장 대조로 재분류). 탐침 3차 5/6·1/12, 4차 5/5·1/13, 5차 3/5·1/13, 6차 4/6·1/12. 원인 BB1~BB4(금전 전칭 2분, 지급 술어 목록, 결합 합집합의 거래내역 범주 누락, 상대방 작성 확인서 제외 범위) — 3절 'B-1 8차 보완 지시'. **10-25 9차 `fb92a19` 조건부 승인**: BB1~BB4 반영, CI 성공, 세트 득점 0·하락 0. 탐침 3~6차 21/22·오탐 0/50, 새 7차 5/6·오탐 2/12(합의서를 '진술확인'으로 옮긴 탓). CC1(합의서류 6낱말 범주에서 삭제) 한 줄 조건 — 평가 측 사본 검증: 5세트 26/28·오탐 0/62·기존 시험 통과. **사용자 결정(10-25): B-1은 수용 뒤 'Added(새 탐지 기능, 세트 득점 없음)'로 0.14.0에 포함.** — 3절 'B-1 9차 판정'. **10-25 `02a30b6` 수용**: CC1만 반영, 사전 검증 사본과 같은 결과(5세트 26/28·오탐 0/62, 기존 시험 통과), 세트 변화 0, CI 성공. Steve `c88c208`과 충돌 없음. — 3절 'B-1 판정 — 수용'. **Steve 병합 `5031b5f`(10-25).** |
| B-2 EVI-COPY | 메모 #157 조건부 승인 / 구현 #168 `9b5374e`(7차) | **수용·병합** | Steve `0a180e1`(10-24). train EVI-COPY 4→19/40·오탐 0. known_open: set04 `SD-0402T`(첫머리 소장 구성 표지 없음 — 후속에서 다른 구조 근거 진단). |
| B-3 TK-90 | 메모 #158 승인 / 구현 #167 `accaf19`→`af28269`(`0731277`은 문서만) | **2차 불승인(하드코딩·CI 실패)** | 은퇴 EVI-INCONS 3건 상승(08b 40.7→42.6, 09 48.3→51.7), 10 0, train 0, 고정 0. CI 점수 하락 게이트 실패: 평가 세트 정답지 문구 2건(0절 위반). 테스트 실패: `tests/test_calculation_leading_multiplier.py::test_pipeline_entrypoint_leading_multiplier_calculation`이 `ARITHMETIC_MISMATCH` 2건(기존 `calculation.py`와 새 `_ARITH_*` 중복, 4절 병렬 검사 금지 위반). 탐침: 장소·서명자 규칙은 틀 맞춤·다른 표현 모두 0. `_EXCLUSIVE_LOC_RE`·`_SIGNER_DENIAL_RE`·`_DISPATCH_DENY_RE`·`_RECEIPT_STMT_RE`·`_ARITH_NET_DESC_RE`는 문장 틀, 은퇴 소제목 겹침 8개. TK-125 문서 커밋이 섞였다. **요구**: 3절 B-3 '2차 보완 지시'. **10-24 메모 보정본 `0396ed4`(129) 조건부 승인**: 결재>송달 선후는 A-4 범위라 제외(같은 사건 복수 날짜만)·중복 억제, 결정적 추출, 장소=처소 조사+머무름 술어+한정 표지, 서명자 이름은 당사자 표시·정의·호칭에서만, 수량 단위 열거 금지·합계는 calculation.py, 서증 조항 B 유지 여부 명시, 등급 C(조항만 B). #177은 #167 코드 포함이라 병합 불가·닫기(TK-125는 평가 측 `d0f40df` 반영). **10-24 구현 `90f56b3` 불승인**: 평가 세트 문구 0·옛 틀 삭제 확인. 은퇴 +3 중 2는 병렬 산식(T1, B-3 득점 불인정)·1은 장소 규칙, train 0. 새 탐침 양성 0/6·대조 0/10. 기존 산식 시험 실패 지속. 원인 T1~T9(병렬 산식, 상대방 주장을 모순으로 판정, 대상 키에 지시어 접두, 총액 표지 필수, '천' 단위 금액 오해석, 상대 날짜 미해석, 서명자 이름 추출 한정, 지위 틀 고정, 귀속·원인표) — 3절 'B-3 3차 보완 지시'. **10-24 4차 `cb21298` 보완(수용 불가)**: T1·T3·T5·T6·T7 반영, 기존 산식 시험 통과, PR 실행 CI 5종 성공·push 실행 게이트 실패(시험 이름 15개 삭제, 승인 절차 미이행). 은퇴 09 +1(장소)·10 +0.25(금액), 하락 0, train·고정 0. 3차 세트 양성 3/6·오탐 0/10, 새 4차 세트 양성 4/6·**오탐 6/12**. 원인 Y1~Y9(금액 확정 서술 조건 꺼짐, 금액 키에 속성 없음, 날짜가 사건 술어와 미결합·목록 의존, 상대방 주장 제외가 날짜 마침표·'다툽'·원고 주어에서 깨짐, 지위 키 불일치·계약 선행 어순, 수량 미구현, 통화 없는 산식 확장, 단락 경계 상대 날짜·한글 수사, 시험 삭제 승인 절차) — 3절 'B-3 4차 보완 지시'. **10-25 5차 `ae5c060` 보완(수용 직전)**: Y1~Y5·Y7~Y9 반영, CI 성공. 은퇴 09 +1(장소)·하락 0. 탐침 3차 4/6·4차 4/6·새 5차 5/6, **오탐 0/34**(탐침 기준 첫 충족). 남은 원인 Q1~Q3(수량 단위·대상 명사 닫힌 목록 — 메모 129·Y6 위반, 과거형 확정 서술·관형형 사건 술어). requests/130 승인(이름 오기 정정 조건) — 3절 'B-3 5차 보완 지시'. **10-25 6차 `853ad02` 보완(수용 직전)**: Q1~Q3 구조화·사유서 130 정정 확인, CI 성공. 은퇴 09 +1(장소)·10 +0.25(수량 — 결함 위 득점이라 불인정)·하락 0. 탐침 3차 5/6·4차 6/6·5차 6/6(오탐 0/34), 새 6차 7/8·**오탐 1/12**. 원인 QQ1~QQ3(단위가 조사를 삼킴, 확정 서술 과대 — 평가 측 Q3 지시 결함, 전칭 부사를 대상으로 잡음) — 3절 'B-3 6차 보완 지시'. **10-25 7차 `a444e51` 수용**: QQ1~QQ3 반영(사전 검증 결과와 일치), CI 성공. 은퇴 09 +1(장소)·하락 0, train·고정 0. 탐침 3~7차 31/34·오탐 0/58. known_open 2(서명 대상 문서 명사 한정, 수량 목적어 동사 밖) — 3절 'B-3 판정 — 수용'. **Steve 병합 `c88c208`(10-25).** |
| C-1 TK-84 | #150 `05c0dee` | **수용·병합** | Steve `b9bfa34`(10-21). 완료. |
| C-2 TK-78 | #151 `f8b886a` | **수용·병합** | Steve `610fc1c`(10-21). 완료. 열린 PR은 보완 때 최신 Steve를 병합 커밋으로 받는다. |
| C-3 TK-82 | #152 `0a6d6c5` | **수용·병합** | Steve `ea97fce`(10-21). 완료. |
| D-1 TK-85 | #153 `a7f6099` | **수용·병합** | Steve `7448838`(10-21). 후속(작은 것): 대기 대상을 두 번째 파일 행으로. |
| TK-95 TK-71 시간 상한 시험 CI 불안정 | #170 `686a809` | **수용·병합** | Steve `7bde77d`(10-21). 후속(TK-95 2차): 사유서 5~51번 같은 방식 정리, 1x가 수 ms 이상 되게. |
| D-2 TK-86 | #154 `b00a179` | **수용·병합** | Steve `2b7c97b`(10-21). 후속: 대응표 admin·retry 두 칸 정정, `source_run_hash` 한 줄. |
| D-3 TK-87 | #155 `c6ca7f7` | **수용·병합** | Steve `b4237ba`(10-21). 완료. |
| D-4 TK-88 | 메모 #159 `1be8cdd` 조건부 승인(닫음) / 구현 #171 `ef47063` | **수용·병합** | Steve `ccf0773`(10-22). 완료. 참고: 3단 표 글자·줄 간격이 2단과 같은지 다음 손질 때 확인. |
| E-1 TK-83 | 메모 #160 승인 / 구현 #166 `3bf5439` | **수용·병합** | Steve `34d8b18`(10-21). 완료. |
| (사용자 지시) TK-94 외부 AI 검증 프롬프트 | #164 `bbc5a4a`(6차) | **수용·병합** | Steve `ce323c7`(10-24). 비차단 후속: '…및…에 관한 법률' 꼴 긴 법령명 일부 잘림(정확도). |
| TK-126 0.14.0 화면 오구현 보완·평면 탭 5개 | #183 | **Steve 병합 `3fee071`(10-25) — 배포 대기** | '확인 방법' 삭제·프롬프트 버튼 표 위 강조·셀 넘침·3단 독립 탭·배포 캐시·상단 평면 탭 5개. 2-3절, 수정본 `patches/TK-126-128_prevalidated_b68e70f.diff` |
| TK-127 Drive 근거 상단 표 통합 | #183 | **1단계 Steve 병합(0.15.0 배포 대상)·2단계 설계 메모 먼저 — 0.15.0 다음 릴리스 범위(사용자 결정 10-25)** | 1단계: 대조 의견을 표 행에 연결, 하단 절 → 표 위 상태 줄. 2단계: 인용 행 Drive 조회. 2-3절, `TK-127_…md` |
| TK-129 보고서에 외부 AI 답변 포함 | — | **지시(10-25), 평가 측 사전 검증 완료, 착수 가능 — 0.15.0 다음 릴리스 범위(사용자 결정 10-25)** | 보고서 요청에 브라우저 답변 동봉 → 서버 고정본(해시)·PDF·Word·Excel·JSON. 선행 TK-126 PR. 2-4절, 수정본 `patches/TK-129_prevalidated_after_TK126.diff` |
| TK-128 두 표 프롬프트·외부 AI 답변 붙여넣기 | — | **지시(10-25 개정, 사전 검증 완료)** | 번호·결과 블록, 붙여넣기→미리보기→표에 반영, 3단 서버 가림 API. 서버 저장은 사용자 결정 대기. 2-3절, `TK-128_…md` |

- 공통: 화면 PR(D)의 기존 시험 수정은 대응표가 승인 조건이다. 시험을 지우면 CI '점수 하락 게이트'의 `check_test_edits.py`가 실패한다. 그때는 사유 문서를 `docs/handoff/requests/`에 둔다.

### A-1 TK-89 — 인젝션 채널별 탐지 일반화 (신규, 최우선)
- 문서 단위 차단은 모든 인젝션 문서에서 되지만, 채널별 결과는 문서마다 10/10·10/10·9/10·6/10·0/10이다.
- 채널마다 PDF 구조(렌더링 모드, 글자 크기·색 대비, 덮인 영역, 쪽 밖 좌표, 폭 0·서식 문자, 주석·첨부·문서 정보)로 판정하고, 쪽·위치·채널 종류를 담은 채널별 결과를 낸다.
- 채널마다 생성 방식이 다른 합성 PDF 3개 이상과 대조군 3개 이상을 시험으로 둔다. 정상 서면의 작은 각주·회색 머리글·서명 이미지는 오탐이 되면 안 된다. **은퇴·고정 세트 문서를 시험 입력으로 쓰지 않는다.**
- 탐지 변경이므로 점검표 1~7항을 모두 낸다.
- **완료: #146 `3aa43a4` 수용·Steve 병합 `fb6592c`(10-19).** 아래는 1차 판정 기록이다.
- **1차 판정(#146 `8db1237`, 10-19): 불승인(보완 필요).** 판정 코멘트를 따른다.
  - 유지: `pdf_parser.py` 페이지 레이어 보존. holdout 폭 0 문자 +1이 이것에서 나왔다(구조 개선).
  - 고칠 것: ① 근거 발췌 봉인(`sealed=True`)을 복원하고, `confidence_features`에서 은닉 원문을 뺀다. ② 평가 세트 어휘에 맞춘 패턴(메타데이터·첨부 우선 2개, `ignore` 대상 확장)을 삭제한다. ③ 숨김 채널에서 나온 명령형·AI 수신자 문장은 동사 목록과 무관하게 채널 의심으로 판정한다(구조). ④ 채널별 합성 3개 이상·대조군(정상 서면의 인용·서술 문장 포함)·실제 진입점 시험을 둔다. ⑤ 점검표 4~6항 표에 오른 항목별 원인(파서·구조·패턴)을 적는다.

### A-2b TK-92 — 정상 서술을 '문서 속 지시문'으로 잡는 기존 오탐 (신규)
- 상대방의 절차 중단 요청을 인용하거나 절차를 생략한 처분이 위법하다고 서술하는 정상 문장이 `META_INSTRUCTION` 의심으로 잡힌다(0.13.1에서도 재현).
- 인용·과거 서술·관형형·법률 판단 문장은 지시문으로 보지 않는다. 보이는 본문에만 적용하고, 숨김 채널은 그대로 둔다. 점검표 1~7항.
- **#147 `7bfd8e8` 수용·Steve 병합 `c211778`(10-19).** 잔여 1꼴('절차를 건너뛰고 … 하였음')은 다음에 손댈 때 함께 정리한다.

### A-2c TK-93 — classify() 긴 본문 성능 (신규)
- 문장 경계를 hit마다 다시 찾지 말고 한 번 계산하거나 문장 길이에 상한을 둔다. 탐지 결과는 바꾸지 않는다.
- 점검표 2항을 문장 부호 없는 입력으로도 측정해 낸다. 탐지 diff 0.

### A-2 TK-81 잔여 — 단독 '틀립니다' 반박 오탐
- 상대방 주장을 '-다는 (상대방의) 지적·주장'으로 받고 '사실과' 없이 '틀립니다·잘못입니다'로 반박하는 문장이 있다. 이를 자기 호증 기재 누락(EVI-FORM)으로 잡는다.
- 상대방 주어·관형형 반박 구조로 제외한다. 진짜 결함(자기 측 원본 분실 자인, 'X밖에 + 제출 부정')을 다시 놓치지 않아야 한다(TK-81 요구 1·2 유지).
- 평가 측은 공개하지 않은 새 탐침으로 잰다. 판정 코멘트의 예문을 규칙·시험에 복사하지 않는다. 점검표 1~7항.

### A-3 #126 잔여 3건
- 목록 머리글 괄호 안에 적은 완결 선언이 괄호 제거로 사라지는 문제가 있다. 괄호를 지우기 전에 완결 선언을 먼저 판정한다.
- '같은 번호, 다른 자료명' 검출은 `83ddb07`에서만 됐다. 공용 목록 행은 바꾸지 않는다.
- 은퇴 10의 A등급 오탐 1건이 0.13.1에도 남아 있다(10-19 재측정). `9cd3843`·`53740a2`에서는 0이었다. 어떤 변경이 제거했는지 찾아, 다른 항목을 잃지 않는 범위에서 반영한다.
- 점검표 1~7항. **은퇴·고정 세트 문장을 규칙·시험에 넣지 않는다(0절).**

### A-4 EVI-DATE 위치 보강
- 대상은 요일 병기 8건과 하이픈 날짜다. #120의 `_find_item_heading`을 공용으로 써서 날짜 판정에 적용한다. **새 함수를 따로 만들지 않는다.** 점검표 1~7항.

### B-1 TK-91 / B-2 EVI-COPY 나머지 32건 / B-3 TK-90 (설계 메모 먼저)
- 각 티켓의 '설계 메모에 담을 것'을 반 쪽~한 쪽 메모로 낸다. 메모가 승인되기 전에는 구현 PR을 내지 않는다.
- B-2는 준비서면·소장 등 비진술서가 대상이고, 작성명의인 기준이다.
- 세 항목 모두 은퇴 세트·말뭉치의 같은 유형 항목이 함께 올라야 수용한다. 고정 세트 항목만 오르면 불수용이다.

### A-4 2차 보완 지시 (#175 `618130c` 불승인, 10-24) — 메모 보정본 먼저, 2-2 규약 전부 적용
**문제(원인)**
1. 득점이 은퇴 7항목에만 일대일로 나고 train·탐침은 0이다. 규칙이 '사건 선후'라는 개념이 아니라 특정 문장 틀을 잡는다.
2. 새 정규식 8개(상태표 A-4 행)는 각각 고정 낱말 3개 이상을 순서대로 이었다(2-2 나-1 위반).
3. 같은 주체·같은 대상의 결합(메모 조건 ②)은 정규식 안 고정 구절로 흉내 냈을 뿐이다. 일반 결합 절차가 없다.
4. 1차 제외 대조 시험을 지우고 양성 assert를 줄였다(2-2 라-4 위반).
5. `_add_civil_period`는 추가됐지만 상대 기간 판정이 틀 정규식에 묶여 있어 다른 표현에서는 쓰이지 않는다.

**고칠 것(전부)**
1. **삭제**: 위 8개 정규식, 그리고 이 정규식에만 딸린 제외 상수.
2. **사건 틀 추출 함수 하나**: 문장·절마다 `(주체, 사건 종류, 대상, 날짜·시각)`을 뽑는다.
   - 주체: 당사자 호칭과 기관명 범주.
   - 사건 종류: 아래 닫힌 사전에서 고른다.
   - 대상: 사건 낱말 앞뒤의 명사구. 지시어(그·위·해당·같은·동일)는 앞의 같은 범주 명사로 푼다. 기존 `_same_object_noun`을 쓴다.
3. **선후 사전(닫힌 목록, 메모에 전체 기재)**: 법률상 앞뒤가 정해진 쌍만 넣는다. 신청→처분·결정·통지, 발송→도달·수령, 체결→이행·해지·해제, 입사·채용→퇴사·해고, 접수→보정·결정, 발생→신고·청구, 기간 시작→기간 종료. 각 쌍의 근거(법령 조문 또는 개념 정의)를 메모에 적는다.
4. **비교 조건**: 같은 주체 또는 같은 대상으로 결합된 쌍만 비교한다. 문서 전체에서 (대상, 사건 종류)로 묶어 비교한다(이웃 문장만 보지 않는다, 반복 안의 반복 금지).
5. **상대 기간**: '다음 날·N일 뒤·N개월 후·N년간'을 기준일과 함께 민법 제157조(초일 불산입)·제159조(말일 종료)·제160조(역에 의한 계산)로 계산한다. 적힌 날짜와 다를 때만 낸다. 기간 꼴 3개 이상(일·월·년)을 시험한다.
6. **제외(구조로)**:
   - 정정·오기 서술, 장래·예정·이행기, 상대방 주장의 인용.
   - 앞선 사건을 대상·근거로 삼는 꼴: '~에 따라', '~를 거쳐', '~에 대한 불복·이의', '~를 첨부'처럼 조사·연결 구조로 판정한다.
   - 별개 대상, 증거목록 구역.
7. **시험**: 삭제한 `test_temporal_event_exclusion_controls`를 되살린다. 1차 판정의 정상 대조 5꼴(나중 서면이 앞선 처분을 다툼, '~에 따라' 참조, 나중 청구의 대상이 앞선 결정, 앞선 회신 첨부, '~를 거쳐' 회고)을 자기 말로 각 2문장씩 대조로 넣는다. 양성은 선후 쌍 3종 이상 × 2-2 다-3 세 변형.
8. 메모 #169 조건 ④(train +6 근거 또는 삭제)를 2-2 다-4 원인표로 이행한다. train 미득점이 요일 병기·하이픈 날짜(원래 A-4 범위) 꼴이면 그 꼴은 기존 `date_verifier.py`의 날짜 해석을 고쳐 다룬다.

**수용**: 2-2 라 전부. 은퇴 EVI-DATE 득점은 규칙 귀속이 확인되고 탐침 기준을 넘을 때만 센다.

### A-4 4차 보완 지시 (#175 `ba62858` 불승인, 10-24) — 원인별 해결 방안
**A-4는 0.14.0 릴리스 범위에 남는다(2026-10-24 사용자 결정).** 2-2 마의 범위 제외 건의는 적용하지 않는다. 릴리스는 A-4 수용까지 기다리므로, 아래 원인 R1~R9를 **모두, 한 번에** 고친다. 줄 번호는 `ba62858`의 `packages/claim_engine/date_verifier.py` 기준이다. 메모를 다시 내지 않는다. 고친 결과는 PR 본문의 'R번호 → 바꾼 함수 → 시험 이름' 대응표로 낸다.

**측정 요약**
- 은퇴 EVI-DATE +1(08 한 항목). train·고정 변화 0.
- 평가 측 새 탐침: 양성 6/10, 정상 대조 오탐 5/12(B).
- 놓친 양성: 한 절 안에 사건 두 개가 있는 문장, 문서 명사가 사건 낱말로 잡힌 문장, 연도가 생략된 날짜.
- 오탐 대조: 두 기간 병기, 대상이 다른 두 서면, '다시' 입사, 서로 다른 두 계약, 상대방 주장 인용.

**R1. 사건 낱말이 없는 절에 사건 종류를 지어낸다 (`_extract_clause_slots` 646~660행)**
- 원인: 사건 낱말이 없는데 '다음 날'이 있으면 `신청`, 기간 표현이 있으면 `퇴사`, 시각만 있으면 `시각`, 날짜만 있으면 `사건`으로 종류를 붙인다. 근거 없는 슬롯이 비교에 들어가 오탐과 틀 맞춤 득점을 만든다.
- 해결: 이 기본값 분기를 **삭제**한다. 사건 낱말이 없는 절은 슬롯을 만들지 않는다. 상대 일자·기간 표현은 같은 절에 사건 낱말이 있을 때만 그 슬롯의 속성으로 붙인다.
- 시험: 날짜만 있는 절, '다음 날'만 있는 절, 'N개월 근무'만 있는 절이 각각 슬롯 0개인지 확인한다.

**R2. 한 절에 사건 하나·날짜 하나만 잡는다 (594~633행)**
- 원인: 절마다 가장 긴 표면형 하나와 첫 날짜 하나만 쓴다. 한 절에 두 사건이 있으면(관형절 '…가 내린 처분은 …가 낸 신청에 대한 것', 연결어미 '-다가') 하나를 버린다. 그래서 양성을 놓친다.
- 해결:
  - 절 안의 **모든** 사건 낱말 출현을 위치와 함께 모은다.
  - 각 사건 낱말에 '같은 절 안에서 그 낱말 앞의 가장 가까운 날짜'를 붙인다. 앞에 없으면 뒤의 가장 가까운 날짜를 붙이되, 다른 사건 낱말을 건너지 않는다.
  - 절 분리에 `-다가`, 관형형 `-ㄴ/-은/-던 + 명사 + 은/는`도 경계로 넣는다.
- 시험: 관형절 두 사건, '-다가' 두 사건 양성을 각 3변형으로 둔다.

**R3. 문서 명사를 사건 낱말로 쓴다 (`EVENT_KIND_SURFACE_FORMS` 136~229행)**
- 원인: '최고서·통지서·신청서·청구서·확인서·소장' 같은 **문서 명사**가 사건 사전에 들어 있다. 가장 긴 일치가 이기므로 '최고서를 발송'이 발송이 아니라 통지로 분류된다.
- 해결:
  - 사건 사전에는 **행위를 나타내는 낱말과 그 활용형**만 둔다(신청하·발송하·도달하·수령하·체결하·해지하·입사하·퇴직하·접수되·보정명령을 하 등).
  - 문서 명사는 별도 상수 `OBJECT_NOUNS`(문서 종류·계약 종류 범주)로 옮겨 **대상** 추출에만 쓴다.
  - 사건 낱말이 명사형으로만 나오면('신청', '도달') 바로 뒤에 `하/했/한/되/된/받/일/일시` 중 하나가 있을 때만 사건으로 본다.
- 삭제할 표면형: '수임'(도달 아님), '받았/받은/교부/인계'(지나치게 넓거나 장면 낱말), '정산'(장면 낱말), '안내·공지'(통지와 법적 성질이 다름).
- 시험: '최고서를 발송하였고 … 위 최고서를 수령' 꼴이 발송→도달로 잡히는지 3변형으로 확인한다.

**R4. 대상 결합이 사실상 꺼져 있다 (대상 추출 665~717행, 비교 1312~1340행)**
- 원인:
  - ① 대상이 없으면 사건 종류명(`cause_slot.kind`)으로 대체한다.
  - ② `c_target in effect_slot.clause_text`처럼 **절 문자열 포함**만으로 일치로 본다.
  - ③ 대상이 없으면 696~700행이 '계약·신청·매체…' 목록에서 절에 들어 있는 낱말을 대상으로 붙인다. 그래서 서로 다른 계약도 둘 다 '계약'이 된다.
  - ④ 지시어 해소(726~737행)의 else 분기가 일치하지 않아도 직전 대상을 붙인다.
  - ⑤ '에 대한' 자동 결합(720~724행)이 절 번호와 슬롯 번호를 섞어 쓴다. 슬롯은 절마다 생기지 않으므로 엉뚱한 슬롯이 묶인다.
- 해결(엄격 일치 하나로 통일):
  - 대상 = 사건 낱말 바로 앞의 `~의/~에 대한/~에 관한/~을·를` 명사구. 그 명사구의 **핵심 명사(마지막 명사) + 수식어**를 정규화해 저장한다(예: '이 사건 매매계약' → 핵심 '매매계약').
  - 지시어(그·위·해당·같은·동·이 사건)는 **앞선 슬롯 가운데 핵심 명사가 같은 범주인 가장 가까운 것**으로만 푼다. 없으면 대상 없음으로 둔다.
  - 일치 판정 = 두 대상의 핵심 명사가 같을 것(`_same_object_noun`의 완전 일치 또는 '수식어+핵심'이 '핵심'을 포함하는 경우만). 절 문자열 포함, 종류명 대체, 목록 대체는 모두 **삭제**한다.
  - '에 대한' 결합은 같은 절 안에서 `[A 명사구]에 대한 [B 사건]`일 때 B의 대상을 A로 두는 것으로만 구현한다.
  - **모든 쌍에서 대상이 한쪽이라도 없으면 비교하지 않는다**(`require_target_match`를 전 규칙 True로).
- 시험: 서로 다른 두 계약(매매·임대차)의 체결·해지, 대상이 다른 두 서면(답변서·준비서면)의 발송·수령, 지시어가 다른 범주를 가리키는 경우 = 오탐 0. 같은 계약을 '위 계약'으로 받는 경우 = 양성.

**R5. 주체 결합도 빈칸이면 통과한다 (541~547행, 1307~1310행)**
- 원인: 주체가 없는 절은 직전 주체를 물려받는다(`last_subject`). 비교 때는 한쪽 주체가 비면 같은 주체로 통과시킨다.
- 해결:
  - 물려받기는 같은 문장 안에서만 하고, 문장이 바뀌면 지운다.
  - 입사→퇴사처럼 `require_same_subject`인 규칙은 두 주체가 모두 있고 같을 때만 비교한다.
  - 주체 추출은 `SUBJECT_RE`의 기관명 열거를 지우고 접미 규칙 `[가-힣]{1,15}(?:법원|위원회|청|서)`(+ '서'는 경찰서·세무서 같은 2자 이상 앞말일 때만)으로 바꾼다(조건 6).

**R6. 제외 장치를 블록 전체에 낱말 목록으로 건다 (1177~1185행)**
- 원인: 블록 안 어디에든 '판결·법률·시행·선고·추후·향후·첨부…'가 있으면 **블록 전체를 건너뛴다.** 실제 서면은 거의 모든 단락에 판결·법률 인용이 있어 train에서 0이 된다. 반대로 목록에 없는 표현('다시 입사', '주장하나')은 막지 못한다.
- 해결(구조 단위로):
  - 제외는 **해당 문장만**, 표지가 직접 걸린 슬롯만 뺀다.
  - 판례·법령은 사건 낱말이 선고·공포·시행인 슬롯만 뺀다(블록 제외 삭제).
  - 장래·예정은 그 절의 서술어가 `-기로/-ㄹ 예정/-할/까지 …하여야`인 슬롯만 뺀다.
  - **상대방 주장 인용**은 문장의 주절이 `[상대 당사자]는/가 … -다고/라고 (주장|진술|다투)하(나|지만|는데|였으나)` 꼴이면 그 인용절 안의 슬롯 전부를 뺀다.
  - **부정**은 사건 서술어가 부정(`-지 않|아니|없`)이거나 '사실과 다르다'가 그 절을 받으면 뺀다.
  - 정정은 '착오·오기·바로잡' 문장의 슬롯만 뺀다.

**R7. 글이 스스로 밝힌 순서를 무시한다**
- 원인: '퇴사한 **후 다시** 입사', '…를 **마친 다음**'처럼 글이 사건 순서를 직접 밝힌 경우에도 법률상 선후 사전만으로 역전을 판정한다.
- 해결: 두 슬롯 사이에 순서 연결어(`-한 후/뒤/다음`, `-다가`, `이후`, `다시·재차·새로`)가 있으면 **글이 밝힌 순서**를 기준으로 삼는다.
  - 글이 '결과 사건 → 원인 사건' 순서를 명시했고 날짜도 그 순서와 맞으면 → 새 주기(재입사·재계약)로 보고 내지 않는다.
  - 글이 '원인 → 결과'를 명시했는데 날짜가 반대면 → 역전으로 낸다(B, 대상 일치 조건 충족 시).
  - `SEPARATE_PERIOD_EXCLUDE_RE`의 '재입사' 같은 낱말 목록은 이 구조 규칙으로 대체하고 삭제한다.

**R8. 기간 비교를 서로 다른 기간끼리 한다 (550~593행, 규칙 7)**
- 원인: 'D1부터 D2까지'마다 시작·종료 슬롯 두 개를 만들고, 대상을 '임대·근로·계약·재직' 중 절에 있는 낱말로 붙인다. 그래서 한 문장의 **두 번째 기간 시작일과 첫 번째 기간 종료일**이 서로 비교된다.
- 해결: 기간 시작·종료 비교는 **같은 'D1부터 D2까지' 표현 안에서만** 한다(그 표현 하나에서 D2 < D1이면 낸다). 다른 기간 표현과는 비교하지 않는다. 기간 슬롯은 다른 규칙의 비교에 쓰지 않는다.

**R9. 승인 범위 밖 규칙과 옛 틀 이식분을 지운다**
- 규칙 8 `기간종료→작성`(315~325행)과 사전 `작성` 종류(222행~)를 삭제한다. 메모 127의 7쌍에 없고 근거 조문도 맞지 않는다.
- '같은 날 시각 역전'·'상대 시각(앞선·이른)'·'동일 목적물 최초 확보 후 인계·전달' 분기(1376행 이후)를 삭제한다. 2차에서 지운 틀을 옮긴 것이다.
- '상대 기간 근무 후 사직·퇴사' 분기(1227~1290행)는 R1의 기본값(`퇴사`)에 기대므로 삭제한다. 상대 기간 계산(민법 제157·160·161조)은 '기준 사건 슬롯 + 같은 절의 N일/월/년 + 같은 절의 만료 사건 슬롯과 날짜'가 모두 있을 때만 C로 낸다.
- 조건 3대로 접수→처분 규칙은 `require_target_match=True`로 바꾼다. 체결 규칙의 결과 종류는 이행·해지(해제 포함)만 둔다(통지·도달 삭제).
- 지시어·대상 목록의 '그 매체·기록매체·매체·그 결제·확인서'를 삭제한다(R4로 대체).
- 날짜 해석에 '같은 해·동년' 같은 연도 생략 날짜를 같은 문장의 앞 날짜 연도로 채우는 처리를 넣는다(놓친 양성의 원인).

**시험 (전부 자기 문장, 평가 측 예문 복사 금지)**
- 양성: 7쌍 × 3변형(어순·연결어미·같은 범주 낱말), 그리고 R2 두 꼴 × 3변형.
- 대조:
  - R4·R5·R6·R7·R8 각 원인마다 2문장 이상: 서로 다른 대상, 주체 다름·빈칸, 판례 인용 단락 안의 진짜 역전(양성으로 남아야 함), 상대방 주장, 부정, 글이 밝힌 새 주기, 두 기간 병기.
  - 1차 5꼴 × 2문장 유지.
- 회귀: 기존 `tests/test_a4_evi_date_temporal.py` 단언을 줄이지 않는다.

**PR에 낼 것**
- R1~R9 대응표.
- 규칙별 득점 귀속표: 오른 은퇴·train 항목마다 유형·문서 번호 + 그 득점을 낸 규칙 ID.
- train EVI-DATE 원인표: 세트별 건수. '해결 완료'가 아니라 **이 head에서 실제로 오른 수**로 적는다.
- 점검표 1~7항, precheck 요약(`--quick`이면 CI '은퇴 세트 비교'·'테스트' 성공 병기).
- holdout은 **현재 Steve(81.9)와 비교**해 적는다(baseline.json 옛 값 비교 금지).

**수용 기준(변경 없음)**
- 고정·은퇴 항목 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 다시 새로 짓는 비공개 탐침에서 양성 2/3 이상, 정상 대조 오탐 0.
- 미달이면 범위에서 빼지 않고 다시 보완한다. 다만 릴리스가 그만큼 늦어지므로 R1~R9 대응표와 자체 대조 시험으로 먼저 확인한 뒤 검토를 요청한다.
- 점수 하락 게이트의 '행정절차법 제' 문구는 일반 법령 표현이므로 평가 측이 허용 목록에 올린다. 구현 측은 조문 표기를 그대로 둔다.

### A-4 5차 보완 지시 (#175 `b1e5cad` 보완 — 수용 직전, 10-24) — 원인별 해결 방안
4차 지시 R1~R9는 대체로 반영됐다. 하드코딩 낱말(매체·인계·정산·수임)과 옛 틀·규칙 8·시각 역전 분기가 지워졌고, 대상·주체 결합이 엄격해졌다. 일반 표현 탐침이 6/10·오탐 5/12에서 **9/10·오탐 2/12**로 좋아졌다. 은퇴 득점 2항목도 일반 규칙에서 나왔다. 남은 것은 아래 U1~U4뿐이다. **이것만 고치면 평가 측 새 탐침 확인 뒤 수용한다.** 줄 번호는 `b1e5cad`의 `packages/claim_engine/date_verifier.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, 새 Steve `3b017eb`와 같은 탐지 조건(#176 포함, 은퇴 10 기준 43.9), 항목 단위, train 포함.
- 고정 82.6/81.9 불변. 은퇴 08 46.7→48.9, 08b 40.7→42.6, 09·10 불변, 하락 0. train 변화 0.
- 득점 귀속(평가 측 확인, 결과 메시지 유형만):
  - 08 1항목: `RELATIVE_NEXT_DAY_INVERSION`(C).
  - 08b 1항목: 입사→퇴사 생애주기 규칙(B).
  - 둘 다 일반 규칙이다.
- 평가 측 새 탐침(4차, 문장 비공개): 양성 9/10, **정상 대조 오탐 2/12**(기준 0 미달).
  - 오탐 꼴: ① '퇴직한 뒤 **새로** 입사', ② 착오 정정 문장('…로 적은 것은 착오이므로 …로 바로잡는다; …').
  - 놓친 꼴: ③ '소장은 …에 접수되었는데, 재판장은 위 소장에 **관하여** 보정명령'.
- CI(인용): 필수 5종 모두 성공. 은퇴 소제목 겹침은 법률 범주어뿐(장면 낱말 0).

**U1. '새 주기' 판정이 낱말 목록이고 '새로'가 빠져 있다 (721행, 비교 1322~1324행)**
- 원인: `is_new_cycle = re.search(r"(?:다시|재차|새로운)")`라서 부사 '새로'를 놓친다. 또 4차 R7이 요구한 **구조 규칙**(글이 밝힌 순서와 날짜가 맞으면 새 주기)이 생애주기 규칙보다 먼저 적용되지 않는다. 그래서 '퇴직한 뒤 … 입사'(날짜도 그 순서)가 입사→퇴사 역전으로 잡힌다.
- 해결:
  - 두 슬롯 사이에 순서 연결어(`-ㄴ 뒤|-ㄴ 후|-ㄴ 다음|-다가|이후|그 후`)가 있으면, **글이 밝힌 순서(앞 절 → 뒤 절)**를 먼저 판정한다.
    - 날짜가 그 순서와 맞으면, 법률상 선후 사전의 역방향(결과→원인)이라도 **새 주기로 보고 내지 않는다.**
    - 날짜가 그 순서와 반대면 `NARRATIVE_TEMPORAL_ORDER_INVERSION`으로 낸다(현행 유지).
  - 낱말 목록에 '새로'를 더하는 것만으로 끝내지 않는다(같은 꼴의 다른 표현에서 다시 깨진다).
- 시험: '…퇴직한 뒤 …입사', '…해지한 다음 …다시 체결', '…퇴사하였다가 …재입사'(날짜 순서 맞음) = 오탐 0. 같은 꼴에서 날짜가 반대 = 양성.

**U2. 정정 문장의 처리가 좁고 문장 단위가 아니다 (`EXCLUDE_CORRECTION_RE` 161~162행, 600행)**
- 원인: 표지가 '이 아니라·의 오기이다·의 착오로·으로 정정'뿐이라 '착오이므로·오기이므로·바로잡는다'를 놓친다. 그래서 정정 전 값(잘못 적었다는 값)이 슬롯으로 남아 다른 절과 비교된다. 옛 `CORRECTION_EXCLUDE_RE`(59~60행)는 남아 있지만 쓰이지 않는다.
- 해결:
  - 정정 표지를 `(착오|오기)(이므로|이다|로|였)|바로잡|정정(한다|합니다|하여)|이 아니라`로 넓힌다. 두 정규식을 하나로 합치고 안 쓰는 쪽은 지운다.
  - 정정 문장 안에서는 **정정 전 값(표지 앞 값)의 슬롯을 지우고**, 정정 후 값(`…로 바로잡/정정`)만 남겨 다른 절과 비교한다.
- 시험: 정정 후 값이 다른 절과 정상 순서 = 오탐 0. 정정 후 값도 역전 = 양성.

**U3. 피동·자동사 사건의 대상을 못 잡고 '에 관하여'가 없다 (`TARGET_PRE_RE` 579~580행, 대상 추출부)**
- 원인:
  - 대상을 사건 낱말 **앞의 `~의/~에 대한/~에 관한/~을·를`**에서만 찾는다. '접수되·발생하·도달하·송달되·해지되·체결되' 같은 피동·자동사 사건은 대상이 **주제·주어 자리**(`소장은`, `화재가`)에 온다. 그래서 대상이 비고, 대상 일치 규칙 때문에 비교가 안 된다.
  - '위 소장에 **관하여**'는 '에 관한'만 있어 놓친다.
- 해결:
  - 피동·자동사 사건 낱말(사전에 표시)일 때, 같은 절의 `X(은|는|이|가)`에서 X가 **문서·계약·사건 명사(`DOCUMENT_OBJECT_NOUNS`·계약 종류·사건 종류)**이면 X를 대상으로 쓴다. 당사자 호칭은 대상이 아니다.
  - `TARGET_PRE_RE`에 `에\s*관하여`, `에\s*대하여`를 더한다.
- 시험: '소장은 접수되었는데 … 위 소장에 관하여 보정명령'(역전) = 양성. 같은 꼴 정상 순서 = 오탐 0.

**U4. 정리**
- 4차 R9대로 사전의 `"작성"` 종류(267행~)를 지운다. 규칙이 없어 쓰이지 않는 사전이다.
- PR 본문에 아래를 낸다(커밋 메시지에는 없었다):
  - R1~R9·U1~U4 대응표;
  - 규칙별 득점 귀속표(위 2항목 포함);
  - train EVI-DATE 미득점 원인표(세트별 건수·원인, 문장 인용 금지).

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 **다시 새로 짓는** 비공개 탐침에서 양성 2/3 이상, 정상 대조 오탐 0.
- 위 넷 외에 새 규칙·새 낱말을 더하지 않는다(범위 고정).

### A-4 6차 보완 지시 (#175 `e0315f2` 보완, 10-24) — 원인별 해결 방안
U1~U4는 반영됐다. 4차 탐침 세트가 **양성 10/10, 오탐 0/12**로 바뀌었다(새 주기·정정·피동 대상·'에 관하여' 해소). 그러나 이번에 새로 지은 5차 탐침에서 오탐 1건이 나왔고, 3차 탐침 세트를 다시 돌리자 1건이 새로 오탐으로 바뀌었다. 원인을 추적한 결과, **대상 결합을 우회하는 낱말 목록 분기**가 있다. 이 분기는 4차 `b1e5cad`부터 있었는데, 평가 측이 지난 판정에서 놓쳤다(평가 측 누락을 바로잡는다). 아래 W1~W3만 고친다. 줄 번호는 `e0315f2`의 `packages/claim_engine/date_verifier.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9 불변. 은퇴 08 48.9·08b 42.6(+2, 일반 규칙 귀속, 4차와 같음), 09·10 불변, 하락 0. train 변화 0.
- 탐침(문장 비공개):
  - 3차 세트: 양성 10/10, 오탐 1/12 — '해고 통지 뒤 구제 신청'(정상 순서)이 신청→통지 역전으로 잡힘. 이전에는 0이었다.
  - 4차 세트: 양성 10/10, 오탐 0/12.
  - 새 5차 세트: 양성 8/10, 오탐 1/12 — '피고는 …라고 **다투지만**'(상대방 주장)이 잡힘.
  - 놓친 꼴: '…사고를 보험회사에 **신고**', '사업 인가를 신청 … 위 인가 신청에 대하여 결정'.
- CI(인용): 필수 5종 모두 성공.

**W1. 대상 결합 우회 분기를 지운다 (1566~1595행)**
- 원인: `require_target_match` 규칙인데도, 대상이 일치하지 않으면 아래 분기가 절 문자열의 낱말만 보고 일치로 바꾼다. 4차 R4('절 문자열 포함·목록 대체는 모두 삭제')와 메모 조건 3('신청→통지는 통지의 대상이 그 신청일 때만')을 정면으로 어긴다.
  - 1568~1574행: 발생→청구 — `acc_words`·`claim_words`가 두 절 어디에든 있으면 일치.
  - 1578~1581행: 접수→보정 — '소장·신청서·사건·신청'과 '보정·명령·권고'가 절에 있으면 일치.
  - 1583~1590행: 신청→처분·통지 — '신청·청구'가 앞 절에, '처분·결정·통지·명령·불승인·기각·거부'가 뒤 절에 있으면 일치. 3차 세트 오탐의 원인이다(해고 통지와 구제 신청은 대상이 다르다).
  - 1593~1594행: 발송→도달 — **무조건** `matched_target = True`.
- 해결:
  - 네 분기를 모두 **삭제**한다. 대상 일치는 R4의 엄격 일치(핵심 명사 같음 또는 풀린 지시어) 하나로만 판정한다.
  - 이 분기 없이 놓치는 꼴은 대상 추출을 고쳐 잡는다(U3 방식).
    - 예: '보정명령'의 대상은 '위 소장에 관하여'에서 온다.
    - 예: '그 신청에 대한 처분'은 R4의 '[A]에 대한 [B]' 결합으로 잡는다.
- 시험: 해고 통지 뒤 구제 신청(정상), 다른 서면의 발송·수령, 다른 사고의 발생·청구 = 오탐 0. 같은 대상으로 묶인 역전 = 양성. 삭제 뒤 기존 시험·4차 세트 꼴이 유지되는지 확인한다.

**W2. 상대방 주장 제외 표면형이 좁다 (`EXCLUDE_OPPONENT_CLAIM_RE` 149~152행)**
- 원인: '라고/다고 + 주장하나/주장한바/주장하지만/주장하므로/주장하며'와 '…라는 주장은'뿐이다. '다투지만·다투나·진술하나·항변하나·번복하였으나'를 놓친다(4차 R6이 요구한 범위).
- 해결: `(라고|다고|라며|다며)\s*(주장|진술|항변|번복)(하|했|하였)(나|지만|는데|으나|으므로|며)|(라고|다고)\s*다투(나|지만|는데|었으나|며)`로 넓힌다. 적용은 현행대로 인용절 안 슬롯만 뺀다.
- 시험: 주장·다투·진술·항변·번복 다섯 꼴 = 오탐 0.

**W3. 발생→신고와 대상 정규화 (규칙 339~346행, 대상 추출부)**
- 원인:
  - 메모 127 쌍 6은 '발생→신고·청구'인데, 결과 종류에 '신고'가 없다.
  - '사업 인가를 신청'의 대상은 '사업 인가', '위 인가 신청에 대하여'의 대상은 '인가 신청'으로 핵심 명사가 달라 묶이지 않는다.
- 해결:
  - 사건 사전에 '신고(하|했|한|되)'를 넣고, 발생 규칙의 결과 종류에 포함한다.
  - 대상 명사구 끝에 붙은 **사건 낱말 자체(신청·청구·처분·통지·계약 등)는 대상 정규화에서 떼고** 핵심 명사를 비교한다('인가 신청' → '인가', '사업 인가' → 핵심 '인가').
- 시험: 위 두 꼴 각 양성 1 + 같은 꼴 정상 순서 대조 1.

**제출물**
- W1~W3 대응표, 득점 귀속표, train EVI-DATE 원인표(아직 PR 본문에 없다), precheck 요약.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 다시 새로 짓는 비공개 탐침과 지난 3~5차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- W1~W3 외에 새 규칙·새 낱말 목록·새 우회 분기를 더하지 않는다.

### A-4 7차 보완 지시 (#175 `27f5277` 보완, 10-25) — 원인별 해결 방안
W2(상대방 주장 표면형 일부)·W3(신고 사건, 대상 끝 사건 낱말 분리)는 반영됐다. 그러나 **W1이 이행되지 않았다.** 지우라고 한 네 우회 분기가 '3) 규칙별 종속적 행위 결합'으로 이름만 바뀌어 남았고, 그보다 넓은 '2) 지시어 바인딩' 분기가 새로 생겼다. 그 결과 새 6차 탐침의 **정상 대조 오탐이 6/12**다. 평가 측이 두 분기를 끄고(엄격 일치만) 같은 탐침을 돌리면 오탐은 0~1로 떨어지고 놓침은 세트당 1~4건 늘었다. 그 놓침은 모두 **대상 추출**의 결함에서 나온다(Z2). 아래 Z1~Z4만 고친다. 줄 번호는 `27f5277`의 `packages/claim_engine/date_verifier.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9 불변. 은퇴 08 48.9·08b 42.6(+2, 일반 규칙 귀속, 지난번과 같음), 09·10 불변, 하락 0. train 변화 0.
- 탐침(문장 비공개). 오른쪽 두 칸은 평가 측이 1624~1672행 두 분기를 끈 '엄격 일치만' 변형 값이다.
  | 세트 | 현행 양성 | 현행 오탐 | 엄격 일치만 양성 | 엄격 일치만 오탐 |
  |---|---|---|---|---|
  | 3차 | 10/10 | 0/12 | 9/10 | 0/12 |
  | 4차 | 9/10 | 0/12 | 7/10 | 0/12 |
  | 5차 | 9/10 | 1/12 | 9/10 | 0/12 |
  | 새 6차 | 9/10 | **6/12** | 6/10 | 1/12 |
  - 현행 오탐 꼴: 다른 대상인데 문장에 '위'가 있음, 해고 통지 뒤 구제 신청을 역순으로 서술, 다른 사고의 발생·청구, '해당'이 다른 대상을 가리킴, 소 제기와 그보다 앞선 처분, 상대방 주장('…다고 주장합니다').
  - 엄격 일치만 변형의 놓침 꼴: '위 [X] 신청에 대하여' 꼴의 처분·결정, '[X]로 인한 [Y]를 청구', '위 [X]를 [기관]에 신고', 피동 주제 '[문서]는 송부되었고 … 도달'.
- 득점 귀속: '엄격 일치만' 변형으로 은퇴 4세트를 다시 재도 08·08b +2가 그대로다. **두 분기의 득점 기여는 0이다.**
- CI(인용): PR·push 실행 필수 검사 모두 성공.

**Z1. 대상 결합 우회 분기를 실제로 지운다 (1624~1672행)**
- 원인:
  - 1624~1631행 '2) 지시어 바인딩': `effect_slot.has_anaphora`이거나, 두 절 어디에든 '에 대한·에 대하여·해당·위 ' 낱말이 있으면 대상 일치로 본다. 지시어가 **무엇을** 가리키는지 보지 않는다. 서면에는 '위'·'해당'이 거의 모든 문단에 있어 사실상 결합 조건이 꺼진다.
  - 1633~1672행 '3) 규칙별 결합': W1이 지우라고 한 낱말 목록 분기(발생→청구 `acc_words`·`claim_words`, 접수→보정 '소장·신청서'·'보정·명령', 발송→도달 무조건)가 그대로다. 신청→처분은 오히려 넓어졌다. 1661~1662행은 두 대상의 핵심 명사가 같거나 **비어 있으면** 일치로 본다. 통지 판정 1651행은 '위'·'그' 한 글자로 일치를 준다.
- 해결:
  - 1624~1672행을 **통째로 삭제**한다. 대상 일치는 1621~1622행 `_same_object_noun`(엄격 일치) 하나로만 정한다.
  - 지시어는 '일치를 주는 낱말'이 아니다. 지시어는 **슬롯 추출 단계에서 직전 대상으로 풀어** `target`에 넣는다(현행 `last_target` 치환을 쓴다). 풀리지 않은 지시어는 대상이 없는 것으로 본다(일치 아님).
  - 대상이 빈 슬롯끼리는 비교하지 않는다.
- 시험: 위 현행 오탐 6꼴 = 오탐 0. 삭제 뒤 3~5차 세트 꼴이 유지되는지는 Z2와 함께 확인한다.

**Z2. 대상 추출을 고친다 (`TARGET_PRE_RE` 591~594행, 대상 추출부 910~960행)**
- 원인(평가 측이 `_extract_clause_slots`로 확인):
  - ① `TARGET_PRE_RE`의 대상이 공백 없는 한 낱말(`[가-힣0-9]{1,15}`)이다. '위 [X] 신청에 대하여'에서 대상이 '신청'(사건 낱말 자체)이 된다. W3의 끝 사건 낱말 분리는 대상 문자열에 핵심 명사가 남아 있어야 작동하므로 여기서는 소용이 없다.
  - ② 대상과 사건 낱말 사이에 날짜만 허용한다. '위 [X]를 [날짜] [기관]에 신고'처럼 처소·상대 부사어(`X에`·`X에게`)가 끼면 대상이 비어 결합이 안 된다.
  - ③ '[X]로 인한 [Y]를 청구'에서 청구 대상이 Y(보험금·손해배상)로만 잡혀, 원인 사건 X(사고·화재)와 묶이지 않는다.
  - ④ 피동 주제 대상(U3)이 송부되·발송되 뒤 주어가 생략된 '도달하였다' 절로 이어지지 않는다.
- 해결:
  - ① 대상 명사구를 공백으로 이어진 명사 최대 3개(`(?:[가-힣0-9]{1,15}\s+){0,2}[가-힣0-9]{1,15}`)로 잡고, 그다음에 W3의 끝 사건 낱말 분리를 한다('위 [X] 신청' → 'X').
  - ② 대상 뒤 날짜와 함께 처소·상대 부사어 1개(`[가-힣]{1,10}(?:에|에게|으로|로)`)를 허용한다.
  - ③ 청구·신고 사건의 대상 명사구에 '[X](으)로 인한·에 따른·에 관한'이 붙으면 X를 그 사건의 **원인 대상**으로 함께 기록한다. 발생→청구 규칙은 발생 대상과 청구의 원인 대상을 `_same_object_noun`으로 비교한다(낱말 목록 대신).
  - ④ 같은 문장에서 주어가 생략된 다음 절은 앞 절의 주제 대상을 잇는다(U3 대상의 절 간 승계, 한 문장 안).
- 시험: 위 놓침 4꼴 각 양성 1 + 같은 꼴 정상 순서 대조 1.

**Z3. 상대방 주장 표면형에 종결형이 없다 (`EXCLUDE_OPPONENT_CLAIM_RE` 149~152행)**
- 원인: 술어 뒤가 연결어미(-나·-지만·-는데·-으나·-으므로·-며)뿐이다. '주장합니다·주장한다·주장하고 있습니다·다툽니다·다퉜다' 같은 **종결형**을 놓친다(평가 측 확인: 두 꼴 모두 불일치). 평가 측 W2 지시문도 종결형을 빠뜨렸다(평가 측 지시 보완).
- 해결: `(라고|다고|라며|다며)\s*(?:(?:주장|진술|항변|번복)(?:하|합|했|하였|한)|다(?:투|툽|퉜|퉈))`로 바꾼다(어미 제한 없음). 적용은 현행대로 그 문장의 슬롯을 뺀다(1033~1044행).
- 시험: '…다고 주장합니다', '…다고 다툽니다', '…다고 주장하고 있습니다' = 오탐 0.

**Z4. 접미 일치가 넓다 (`_same_object_noun` 524~526행)**
- 원인: `a.endswith(b) or b.endswith(a)`라서 짧은 핵심 명사 하나가 그것으로 끝나는 모든 긴 대상('…[핵심]' 꼴)과 일치한다. W3가 요구한 것은 '[수식어] [핵심]'과 '위 [핵심]'처럼 **지시어로 다시 가리킨 짧은 꼴**의 결합이다.
- 해결: 접미 일치는 짧은 쪽이 지시어로 해소된 대상(`has_anaphora`)이고, 긴 쪽이 바로 앞 대상일 때만 허용한다. 그 밖에는 핵심 명사 완전 일치만 본다.
- 시험: 핵심 명사가 같고 수식어가 다른 두 대상('[A][핵심]'·'[B][핵심]') = 대조. '[수식어] [핵심] 신청'과 '위 [핵심] 신청에 대한 결정' = 양성.

**제출물**
- Z1~Z4 대응표, 삭제한 줄 범위, 득점 귀속표, train EVI-DATE 원인표, precheck 요약.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 비공개 탐침과 지난 3~6차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- Z1~Z4 외에 새 규칙·새 낱말 목록·새 우회 분기를 더하지 않는다. **대상 일치를 낱말 존재로 주는 분기는 어떤 이름으로도 두지 않는다.**

### A-4 8차 보완 지시 (#175 `76c5895` 보완, 10-25) — 원인별 해결 방안
**Z1은 이행됐다.** 우회 분기 두 개가 지워지고 대상 일치가 `_same_object_noun` 하나로 정해졌다. Z3(종결형)·Z4(접미 일치 제한)도 반영됐다. 그러나 Z2에서 두 가지가 새로 생겼다. ① 대상이 없는 절에 앞 절 대상을 넓게 물려주는 **승계 단계**가 다시 오탐을 만든다(사실상 새 우회 분기). ② 대상 명사구 창을 넓히면서 **조사가 붙은 낱말까지 대상에 들어가** 대상이 깨진다. 그래서 지난 3차 세트 양성이 10/10에서 6/10으로 후퇴했다. 아래 AA1~AA6만 고친다. 줄 번호는 `76c5895`의 `packages/claim_engine/date_verifier.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9 불변. 은퇴 08 48.9·08b 42.6(+2, 일반 규칙, 지난번과 같음), 09·10 불변, 하락 0. train 변화 0.
- 탐침(문장 비공개). 오른쪽 두 칸은 평가 측이 1026~1035행 승계 단계만 끈 변형 값이다.
  | 세트 | 현행 양성 | 현행 오탐 | 승계 끈 양성 | 승계 끈 오탐 |
  |---|---|---|---|---|
  | 3차 | **6/10**(직전 10/10) | 0/12 | 6/10 | 0/12 |
  | 4차 | 9/10 | 0/12 | 8/10 | 0/12 |
  | 5차 | 7/10 | 1/12 | 7/10 | 0/12 |
  | 6차 | 7/10 | 3/12 | 7/10 | 0/12 |
  | 새 7차 | 6/10 | 1/11 | 6/10 | 0/11 |
  - 7차 대조 1문장은 평가 측 문장 오류로 집계에서 뺐다('그 뒤'로 순서를 밝혀 실제 서술 순서 역전이었다).
  - 현행 오탐 꼴: 다른 처분에 앞 절 대상이 승계됨, 해고 통지 뒤 구제 신청, '해당'이 다른 대상, '그와 무관한' 다른 계약.
  - 놓친 꼴: '[당사자]는 그 [X]에 대하여' 꼴 처분, 관형절 두 사건, '[X]로 인한 [Y] 청구'의 발생 대상, '공사…계약'처럼 기관 접미가 든 계약명, 피동 체결·해제, 통지 → 도달.
- CI(인용): PR·push 실행 필수 검사 모두 성공.

**AA1. 승계 단계를 Z2-④ 범위로 줄인다 (1026~1035행)**
- 원인: 대상이 없으면 앞 절 대상(`last_topic_target`)을 물려주는 조건이 '피동·자동사이거나, 사건이 도달·보정·처분이거나, 앞 구분자에 연결어미가 있거나, **마침표만 아니면**'이다. 사실상 같은 문장의 모든 절이 앞 대상을 받고 `has_anaphora=True`가 된다. 대상 추출에 실패한 절(자기 목적어가 있는데 못 잡은 절)도 앞 대상을 받아 엄격 일치를 통과한다(평가 측 확인: 다른 처분·구제 신청 절이 앞 절 대상을 받음). 승계 단계만 끄면 오탐이 5세트 모두 0이 되고 양성은 4차 1건만 줄었다.
- 해결: 승계는 아래 **셋을 모두** 만족할 때만 한다.
  - 같은 문장 안이다(현행).
  - 그 절의 사건이 피동·자동사(`_is_passive_or_intransitive_event`)다.
  - 그 절에 자기 목적어·대상 표지(`X을/를`, `X에 대하여/대한/관하여`, `X의`)가 **없다**. 목적어 표지가 있는데 대상을 못 잡았으면 승계하지 않고 대상 없음으로 둔다.
- 연결어미·구분자 조건과 '도달·보정·처분' 종류 조건은 지운다.
- 시험: 위 현행 오탐 꼴 = 오탐 0. 피동 주제 '[문서]는 발송되었고, … 도달하였다' = 양성(유지).

**AA2. 대상 명사구 창이 조사 붙은 낱말을 삼킨다 (`TARGET_PRE_RE` 602~609행, 원인 대상 1056~1067행)**
- 원인: Z2 ①의 '명사 최대 3개'를 `[가-힣0-9]{1,15}` 토큰으로 구현해, 조사가 붙은 토큰('[당사자]는'·'[당사자]에게'·'[X]에 관한'·'[X]로 인한')도 명사로 센다. 평가 측이 `_extract_clause_slots`로 본 대상: '[당사자]는그', '[당사자]에게[X]', '[X]에관한[Y]', '[X]로인한[Y]' 꼴로 조사째 붙어 있다. 이렇게 깨진 대상은 엄격 일치에 실패하거나(놓침), 뒤 절로 승계돼 오탐을 낸다. 3차 세트 후퇴의 주원인이다.
- 해결:
  - 창의 앞쪽 토큰은 **조사로 끝나지 않는 토큰**만 허용한다: 토큰 끝이 `은|는|이|가|을|를|에|에게|에서|으로|로|와|과|의|도|만`이면 창을 거기서 끊는다. '관한·대한·인한·따른' 같은 관형 연결도 끊는 자리다.
  - 당사자 호칭(`PARTY_TITLES`)과 지시어 단독 토큰('그'·'위')은 대상 명사가 아니다. 지시어는 접두로만 떼고 지시 해소에 쓴다.
  - 원인 대상(`cause_target`, 1056~1067행) 추출도 같은 토큰 규칙을 쓴다.
- 시험: '[당사자]는 그 [X]에 대하여 [날짜] [처분]', '[당사자]에게 [X]를 통지', '[X]로 인한 [Y]를 청구' 꼴에서 대상이 각각 X로 잡히는지 단위 시험으로 확인한다.

**AA3. 지시어 판정이 '그와·그런' 같은 낱말까지 잡는다 (954·997·1060행 `startswith`)**
- 원인(코드 점검): `t_raw.startswith(ana) for ana in ("그", "위", "해당", …)`라서 '그와 무관한 [X]'·'그런 [X]'·'위반'·'해당 [기관]'도 지시어로 본다. '그와 무관한'은 오히려 **다른 대상**이라는 표시인데 앞 대상으로 풀릴 수 있다. 이번 '다른 계약' 오탐은 AA1 승계에서 났지만, AA2로 창이 바로잡히면 이 판정이 같은 꼴의 다음 원인이 된다.
- 해결: 지시어는 **독립 토큰**일 때만 인정한다: `^(?:그|위|해당|동|본건|이\s*사건)\s+(?=[가-힣])`. '그와·그런·그러한'은 지시어가 아니다. '해당'은 뒤 명사가 대상 명사(문서·계약·사건)일 때만 지시어로 본다(기관·장소 앞 '해당'은 제외).
- 시험: '그와 무관한 [다른 계약]'·'해당 [기관]에' = 지시 해소 안 함(대조).

**AA4. 기관 접미 판정이 계약명 안의 '공사'를 잡는다 (`ORGAN_SUFFIX_RE` 108~110행, 사용 950행)**
- 원인: `ORGAN_SUFFIX_RE.search(t_raw)`가 끝 고정이 아니라서, '공사'로 시작하는 계약·대금 명사처럼 '공사'가 든 대상을 기관(행위 주체)으로 보고 버린다(평가 측 확인: '[공사…]계약을 체결'의 대상이 `None`, '공사'가 없는 같은 꼴 계약명은 정상).
- 해결: 기관 판정은 대상 명사구가 기관 접미로 **끝날 때만** 한다(`…(?:법원|…|공사)$`, 끝 고정, `fullmatch`). 계약·문서 명사로 끝나면 기관이 아니다.
- 시험: '[공사…]계약을 체결'·'[공사…]계약을 해지' 꼴 역전 = 양성. '[기관명]공사가 처분' = 행위 주체(대상 아님).

**AA5. 블록 단위 '소를 제기' 제외를 지운다 (1719행)**
- 원인: 1719행 정규식에 `소를\s*제기|소송을\s*제기`를 더해, 블록에 이 말이 **어디든 있으면** 신청→처분·접수→보정 규칙 전체를 건너뛴다. 낱말 존재로 판정을 끄는 분기다(7차 수용 기준 위반). 원래 의도는 '[처분]의 취소를 구한다' 꼴의 회고 서술인데, 그 경우는 바로 아래 줄(소·소송 대상 슬롯 제외)과 '취소를 구하' 꼴로 처리된다. 기존 '구하'는 '구한다·구합니다' 활용형을 못 잡는다.
- 해결: `소를\s*제기|소송을\s*제기`를 지운다. 기존 표면형을 `(?:취소|위법|무효)[를을]?\s*(?:구하|구한|구합|다투|다툽|다퉜)`로 활용형까지 넓힌다. 제외는 그 문장 안의 쌍에만 적용한다(블록 전체 아님).
- 시험: '[날짜] 소를 제기하여 [더 앞 날짜]에 한 [처분]의 취소를 구한다' = 오탐 0. 같은 블록의 다른 문장에 있는 진짜 신청→처분 역전 = 양성.

**AA6. 피동 판정이 일치한 표면형에 의존한다 (`_is_passive_or_intransitive_event` 639~643행)**
- 원인: 피동 여부를 `surf`(일치한 사건 표면형)에 '해지되·체결되'가 들어 있는지로 본다. 사전에서 더 짧은 표면형('해지'·'해제'·'체결')이 먼저 일치하면 뒤의 '되었다'를 보지 못해 피동이 아니게 되고, U3 주제 대상('[계약]은 … 해지되었다')이 붙지 않는다(평가 측 확인: '[계약]은 [날짜] 해지되었다'의 대상 `None`, 해제는 목록에도 없음).
- 해결: 피동은 표면형 목록이 아니라 **사건 낱말 바로 뒤 어미**로 판정한다: 일치 끝 위치 뒤 `\s*(?:되|돼|됐|되었|받|당하)`가 오면 피동이다. 자동사 종류(접수·발생·도달)는 현행 유지.
- 시험: '[계약]은 [날짜] 체결되었는데, 위 [계약]은 [더 앞 날짜] 해제되었다' = 양성. 같은 꼴 정상 순서 = 대조.

**제출물**
- AA1~AA6 대응표, 득점 귀속표, train EVI-DATE 원인표, precheck 요약.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 비공개 탐침과 지난 3~7차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- AA1~AA6 외에 새 규칙·새 낱말 목록·새 우회 분기를 더하지 않는다. 대상이 없는 슬롯에 대상을 주는 경로는 AA1의 좁은 승계 하나뿐이다.

### A-4 8차 보완 지시 부록 — 평가 측 사전 검증 결과와 지시 정정 (#175, 10-25)
평가 측이 8차 지시 AA1~AA6를 `76c5895` 사본에 적용해 검증했다. **오탐은 모두 없어지고 탐침 양성도 기준(2/3)을 넘지만, 지시문 그대로는 구현이 막히는 곳이 셋 있었고(AA2·AA6 정정), 원인 하나가 더 있었다(AA7). 구현 측 기존 시험 3개와의 충돌(AA8)은 평가 측도 아직 풀지 못했다(미검증).**

**검증 결과(평가 측 사본, AA1~AA7 적용)**
- 탐침 3~7차: 양성 7/10·8/10·7/10·9/10·8/10, 정상 대조 오탐 0(7차의 1건은 평가 측 대조 문장 오류로 제외).
- 세트: 고정 불변, 은퇴 08·08b +1씩 유지, 하락 0.
- 기존 시험: `tests/test_a4_evi_date_temporal.py` 중 3개 실패 — `test_r5_subject_differentiation_controls_and_positive`, `test_r6_five_exclusions_and_real_inversion_with_verdict`, `test_r9_rule8_deleted_and_omitted_year_dates`(AA8).

**AA2 정정 — 조사 판정 토큰**
- 지시대로 토큰 끝 '이·가·의·에·로·도·만'까지 조사로 보면, '허가·인가·평가'처럼 **'가'로 끝나는 명사**를 조사로 오인해 대상이 비거나 사건 낱말만 남는다(평가 측 사본에서 3차 세트 양성 6/10으로 확인).
- 정정: (1) 창의 **마지막 토큰은 끊지 않는다**(마지막 조사는 이미 `TARGET_PRE_RE` 바깥에서 맞는다). (2) 앞쪽 토큰은 뜻이 하나인 조사 `은|는|을|를|에게|에서|으로|와|과|에는|에도`로 끝날 때만 끊는다. (3) '이·가·의·에'는 토큰에서 그 글자를 뗀 나머지가 당사자 호칭(`PARTY_TITLES`)일 때만 끊는다('원고가'·'피고의'). (4) 날짜 토큰(`[\d.\-년월일]+`)에서도 끊는다. (5) '이 사건'의 '이'는 끊지 않는다.

**AA6 정정 — 피동 판정 위치**
- '[처분]은 [날짜]에 발령되었다'처럼 피동 어미가 사건 낱말 바로 뒤가 아니라 **같은 절 뒤쪽 술어**에 온다. 일치 끝 바로 뒤만 보면 놓친다.
- 정정: 일치 끝부터 절 끝까지에서 `(?:되었|되어|되고|되는|된|돼|됐|받았|당하|내려지|내려졌)`가 술어로 나오면 피동이다.

**AA7(추가) — 사후 지시 해소가 명시된 대상을 덮어쓴다 (1124~1130행)**
- 원인: 슬롯을 다 만든 뒤 `has_anaphora`인 슬롯의 대상을 **무조건** 앞 슬롯 대상으로 바꾼다. '해당 [다른 계약]'처럼 지시어 뒤에 대상이 명시돼 있어도 앞 계약으로 덮여, 구현 측 시험 `test_z1_…` 오탐 4가 깨진다(평가 측 사본 확인).
- 해결: 그 반복은 **대상이 비어 있을 때만** 채운다(`if slots[i].has_anaphora and not slots[i].target`).

**AA8(미검증) — 대상이 생략된 응답형 사건**
- 충돌하는 시험 3개는 모두 '[신청·접수]한 뒤 [기관]의 [처분·보정명령]은 [날짜]에 발령되었다' 꼴이다. 응답 사건(처분·보정명령·결정)이 **행위 주체의 소유격만 있고 자기 대상이 없다**. 예전에는 넓은 승계로 잡혔고, AA1로 승계를 좁히면 빠진다.
- 방향: AA1 승계 조건의 '대상 표지 없음'에서 **행위 주체 소유격('[기관·당사자]의')은 대상 표지로 보지 않는다**(평가 측 사본에 반영함). 그래도 남는 원인은 그 절의 대상이 사건 낱말 자체('처분'·'보정명령')로 채워지는 경로다. 대상 정규화 뒤 빈 문자열이 되는 대상(사건 낱말뿐)은 '대상 없음'으로 보고 AA1 승계를 받게 한다. 이 수정은 평가 측이 아직 검증하지 못했다. 구현 뒤 세 시험과 탐침 3~7차를 함께 돌려 결과를 PR 본문에 낸다.

**수용 기준(변경 없음)**: 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공(기존 시험 포함), 평가 측 새 탐침과 지난 3~7차 세트 모두 양성 2/3 이상·오탐 0.

### A-4 9차 판정 — 조건부 승인 (#175 `2f7627d`, 10-25) — 한 곳 수정 조건
AA1~AA8이 반영됐다. 구현 측 기존 시험이 전부 통과하고(AA8의 충돌 3개 해소), 탐침 양성이 모든 세트에서 기준을 넘는다. 남은 오탐은 한 꼴뿐이고 원인은 한 곳이다(DD1). **DD1만 고치면 수용한다.** 평가 측이 그 수정을 `2f7627d` 사본에 적용해 미리 검증했다(아래). 줄 번호는 `2f7627d`의 `packages/claim_engine/date_verifier.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9 불변. 은퇴 08 48.9·08b 42.6(+2, 일반 규칙), 09·10 불변, 하락 0. train 변화 0.
  - DD1 적용 사본도 같은 값이다(득점 영향 없음).
- 탐침(문장 비공개):
  | 세트 | 현행 양성 | 현행 오탐 | DD1 사본 양성 | DD1 사본 오탐 |
  |---|---|---|---|---|
  | 3차 | 8/10 | 0/12 | 8/10 | 0/12 |
  | 4차 | 8/10 | 0/12 | 8/10 | 0/12 |
  | 5차 | 7/10 | **1/12** | 7/10 | 0/12 |
  | 6차 | 9/10 | 0/12 | 9/10 | 0/12 |
  | 7차 | 8/10 | 0/11 | 8/10 | 0/11 |
  | 새 8차 | 7/10 | **1/12** | 7/10 | 0/12 |
  - 7차의 대조 1문장은 평가 측 문장 오류로 계속 제외한다.
  - 현행 오탐 꼴(5·8차 공통): '그와 무관한 [다른 계약]은 [날짜] 해지되었다'처럼 피동 절의 주제가 **다른 계약**인데, 앞 절 계약을 물려받아 역전으로 잡힌다.
  - 놓친 꼴(기준 안, 고치지 않아도 됨): 관형절로 엮인 두 사건, 응답형 사건 일부, 피동 체결·해제의 일부 어순.
- 시험: `tests/test_a4_evi_date_temporal.py` 전부 통과(현행·DD1 사본 모두, 평가 측 재실행). CI(인용): PR·push 실행 필수 검사 모두 성공.

**DD1. 피동 주제 대상 판정이 정규화한 뒤의 이름으로 계약·문서 여부를 본다 (U3 단계 1114~1145행)**
- 원인: 1129행에서 `cand_clean = _normalize_target(...)`로 끝의 사건 낱말('계약' 등)을 떼어낸 뒤, 1131~1134행이 그 **뗀 이름**으로 '…계약·…협약' 끝맺음을 검사한다. '[다른]계약'은 '[다른]'만 남아 계약 명사로 인정되지 않는다. 그래서 주제 대상이 비고, AA1 승계가 앞 절 계약을 물려준다(평가 측 사본에서 확인).
- 해결(두 군데):
  1. 대상 여부 검사는 **정규화 전 이름**(지시어만 뗀 핵심, 공백 제거)으로 한다: `_cand_full = re.sub(r"\s+", "", cand_core if cand_has_ana else cand_raw)`, `is_valid_object = cand_clean in DOCUMENT_OBJECT_NOUNS or _cand_full in DOCUMENT_OBJECT_NOUNS or any(_cand_full.endswith(k) for k in (…기존 끝맺음…))`. 채택하는 대상 값은 지금처럼 `cand_clean`(정규화 값)을 쓴다.
  2. 1129행의 '사건 낱말뿐인 주제' 제외 목록에 **처분 종류 낱말**(거부·불승인·기각·각하·승인·인용·불허·불허가·반려)을 더한다. 1을 하면 '[관할청]의 거부처분은'의 '거부처분'이 대상으로 채택되어 '[신청서]가 접수되었는데 [관할청]의 거부처분은 …' 꼴(구현 측 시험 `test_r2_…`·`test_r6_…`)이 깨진다. 처분 종류만 남는 주제는 자기 대상이 없는 응답 사건이므로 AA1 승계를 받아야 한다.
- 시험: '그와 무관한 [다른 계약]은 [더 앞 날짜] 해지되었다' = 대조(오탐 0). 기존 시험 전부 통과(평가 측 사본에서 확인).

**수용 조건**
- DD1만 고친다. 다른 변경을 더하지 않는다.
- 필수 CI 성공. 평가 측은 DD1 커밋을 받으면 3~8차 세트·기존 시험·세트 점수를 다시 돌려 위 사본 결과와 같은지만 확인하고 수용한다.
- 수용 뒤 새 Steve(`c88c208`, #167 병합)와의 충돌은 없음을 확인했다(로컬 병합 시험).

### A-4 판정 — 수용 (#175 `5396f5a`, 10-25)
DD1이 지시대로 반영됐다(대상 여부 검사를 정규화 전 이름으로, 처분 종류 낱말 제외, 대조 시험 추가, 다른 변경 없음). 평가 측 사전 검증 사본과 동작이 같다(주석·줄바꿈만 다름). **수용한다.** 남은 보완 지시는 없다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9 불변. 은퇴 08 46.7→48.9·08b 40.7→42.6(`EVI-DATE` 각 1항목, 일반 규칙), 09·10 불변, 하락 0, 오탐·A등급 0. train 변화 0.
- 탐침(문장 비공개): 3차 8/10·0/12, 4차 8/10·0/12, 5차 7/10·0/12, 6차 9/10·0/12, 7차 8/10·0/11(평가 측 대조 문장 오류 1건 제외), 8차 7/10·0/12. 사전 검증 사본 결과와 같다.
- 시험: `tests/test_a4_evi_date_temporal.py` 전부 통과(평가 측 재실행). CI(인용): PR·push 실행 필수 검사 모두 성공.
- Steve `5031b5f`(#167·#165 병합)과 로컬 병합: 충돌 없음, 병합 트리에서 A-4·B-1·B-3 시험 통과.

**알려진 미해결(known_open, 후속)**
- 관형절로 엮인 두 사건, 응답형 사건 일부, 피동 체결·해제의 일부 어순을 놓친다.
- 커밋 제목의 티켓 번호(TK-92)는 기존 다른 티켓과 겹친다. 다음 커밋부터 A-4 표기로 바로잡는다(코드 영향 없음).

**병합**: 10-25 사용자 지시 뒤 병합 커밋 `907c2fa`로 Steve에 넣었다(head `5396f5a`).

### B-1 3차 보완 지시 (#165 `94c645f` 불승인, 10-24) — 메모 보정본 먼저, 2-2 규약 전부 적용
**문제(원인)**
1. 은퇴 5항목만 오르고 train·다른 표현 탐침은 0이다. 득점은 `_STRUCT_OVERREACH_SUBJ_RE`·`_PRED_RE`의 장면 명사·고정 구절에서 나온다(2-2 나-1·나-2 위반).
2. 메모 #156에서 승인한 축('서증 종류가 증명할 수 있는 범위' 대 '주장 술어')은 통지·견적·식별·진단 4범주만 구현됐다. 나머지는 장면 낱말로 메웠다.
3. `_DIRECT_PROOF_STRUCTURE_RE` 첫 대안이 `r"(?:'r'"`로 시작한다. 따옴표 오타로 그 갈래는 맞지 않는다.
4. 3차 불승인이다. 같은 방식으로 다시 내면 2-2 마의 범위 제외 건의 대상이다.

**고칠 것(전부)**
1. **삭제**: `_STRUCT_OVERREACH_SUBJ_RE`·`_STRUCT_OVERREACH_PRED_RE`, 그리고 이것만 쓰는 함수 갈래.
2. **메모 보정본**: 아래 두 표와 판정식을 적어 먼저 승인받는다.
   - **서증 능력표**(문서 종류 범주 → 증명할 수 있는 것 / 단독으로는 증명할 수 없는 것):
     - 통지·최고·내용증명 → 발송·도달·통지 내용의 존재 / 상대방 승낙·채무 승인·통지 내용의 진실.
     - 견적·계획·산출내역 → 제시 금액·예정 내용 / 지급 완료·이행 완료.
     - 식별(통장 표지·사업자등록증·신분증) → 명의·계좌의 존재 / 거래·지급.
     - 진단서·소견서 → 진단 당시 신체 상태 / 가해자·가해 행위·고의.
     - 사진·영상 캡처 → 촬영 시점의 상태 / 그 전후의 지속·전 기간·행위자의 의사.
     - 영수증·입금 확인 → 그 금액의 수령 / 다른 채무의 전액 변제.
     - 제3자 확인서·진술서 → 진술의 존재 / 확정 사실(C 등급만).
   - **주장 술어 범주**:
     - 전칭·전 기간: 항상·매번·모든·계속·내내·줄곧 같은 문법 부사. 명사는 넣지 않는다.
     - 내심: 의사·고의·인식.
     - 완료·확정: 완납·완료·변제.
     - 상대방 의사표시: 승낙·승인·동의.
     - 각 범주의 사전 전체를 적는다.
   - 판정식: 인용 서증들의 능력 합집합이 주장 술어 범주를 덮지 못할 때만 낸다. 함께 인용된 서증 하나라도 덮으면 내지 않는다(현행 결합 원칙 유지).
3. **유지**: 메모 승인 조건(자기 측 발신일 때만 B, 상대방 발신 통지는 판정 안 함, 증명 근거로 놓인 구조에서만 B). `'r'` 오타를 고치고, 그 갈래가 실제로 맞는지 보는 시험을 더한다.
4. **시험**: 능력표 7범주 × 양성 1개 이상(서로 다른 술어 범주), 대조 7개 이상. 대조는 적정 원용, 결합 원용, 상대방 발신, 간접증거 원용이다. 양성마다 2-2 다-3 세 변형을 붙인다.

**수용**: 2-2 라 전부. 메모 보정본 승인 전 구현 커밋은 검토하지 않는다.

### B-1 4차 보완 지시 (#165 `2c2a903` 보완, 10-24) — 원인별 해결 방안
하드코딩은 해소됐다(장면 정규식 삭제, 은퇴 소제목 겹침은 법률 범주 낱말뿐). 남은 것은 정상 문장 오탐과 놓침, 그리고 세트 득점 0이다. 아래 S1~S9를 **모두, 한 번에** 고친다. 줄 번호는 `2c2a903`의 `packages/claim_engine/evidence_consistency.py` 기준이다. 메모를 다시 내지 않는다. 결과는 PR 본문의 'S번호 → 바꾼 함수 → 시험 이름' 대응표로 낸다.

**측정 요약**
- 평가 측 재실행(오프라인, Steve `0887d49` 같은 탐지 조건, 항목 단위, train 포함): 고정 82.6/81.9, 은퇴 46.7/40.7/48.3/38.9, train 37.5/37.5/37.5/36.5, **모두 변화 0**(은퇴 EVI-OVR 득점 0, 하락 0).
- 커밋 메시지의 'holdout 80.1→81.9'는 baseline.json 옛 값과의 비교다. 현재 Steve도 81.9라 향상 0이다.
- 평가 측 새 탐침: 양성 4/6(기준 2/3 충족), **정상 대조 오탐 3/12**(기준 0 미달).
  - 오탐 꼴: 통지로 자기 측 의사표시의 존재를 증명, '의사'가 직업 명사로 쓰인 문장, 통지에 담긴 해지 의사의 도달.
  - 놓친 꼴: 원고 발신 통지로 피고 승낙을 단정, '지급을 마친' 꼴의 완료 단정.
  - 양성 4건이 모두 C였다. B가 나와야 할 '…에 의하여 인정된다' 꼴이 직접 증명 구조로 잡히지 않는다.
- CI 점수 하락 게이트 실패: '알 수 있습니다' 1건(일반 표현). 평가 측이 허용 목록에 올린다(평가 브랜치, 평가 PR #178로 Steve 반영).

**S1. 술어 사전을 부분 문자열로 찾는다 (743행, 사전 538~556행)**
- 원인: `pw in scope_text`로 찾는다. '의사'가 '의사표시', 직업 명사 '의사', '해지 의사'에 모두 걸린다. '모든·계속·확정·인식·과실·합의'도 다른 낱말 속에서 걸린다.
- 해결:
  - 술어는 **낱말 경계**로 찾는다(앞은 문장 처음·공백·조사, 뒤는 조사·어미·공백).
  - '의사'는 사전에서 지운다. 내심은 '고의·악의·인식·공모·통모'와 구조 `-(려는|할|ㄹ) 의사(로|를 가지고|가 있었)`로만 잡는다. '의사표시'는 내심이 아니다.
  - '과실·불법행위'는 내심이 아니라 법률 평가다. 내심 범주에서 뺀다.
- 시험: '의사표시', 직업 '의사', '해지 의사를 통지' 각 대조. 낱말 경계(합의서·계속적 거래·확정판결) 대조.

**S2. 통지류에서 술어의 주체를 보지 않는다 (매트릭스 558행~)**
- 원인: 통지·최고서는 **발신인 자신의 의사표시와 그 도달**을 증명한다. 그런데 술어의 주체가 발신인 자신이어도 '내심·의사표시 못 덮음'으로 판정한다.
- 해결: 내심·상대방 의사표시 술어는 그 술어의 주체(같은 절의 `은/는/이/가` 당사자)가 **서증 작성자(발신인)와 다른 당사자일 때만** 센다. 주체를 못 정하면 세지 않는다.
- 시험: 자기 측 통지로 자기 해제 의사표시의 도달을 증명 = 오탐 0. 자기 측 통지로 상대방의 승낙을 단정 = 양성.

**S3. 발신인을 문장 전체에서 추정한다 (776~790행)**
- 원인: 문장 어디에든 '피고가'가 있으면 통지 발신인을 피고(상대방)로 본다. 그래서 '원고가 보낸 최고서로 피고가 승낙한 사실이 확인된다'가 상대방 발신으로 판정돼 빠진다.
- 해결: 발신인은 다음 둘에서만 정한다. 둘 다 없으면 '발신인 불명'(C 상한)이다.
  - (가) 증거목록 행의 작성자·발신인 칸.
  - (나) 그 서증 인용 바로 앞의 관형절 `[당사자](가|이) (보낸|발송한|작성한) [서증]`.
- 시험: 술어 주체가 상대방이고 발신인이 자기 측인 문장 = 양성. 그 반대 = 제외.

**S4. 직접 증명 구조의 표면형이 빠져 있다 (604행)**
- 원인: '에 의하여', 받침 없는 서증명 뒤의 '로'(예: '최고서로')가 없다. 그래서 정상적인 직접 증명 문장이 C로 떨어진다.
- 해결: 조사를 정규화한다. 아래 표면형을 모두 넣고 표면형마다 시험 1개를 둔다.
  - `(으)로`
  - `에 의(하여|해|하면|한)`
  - `을/를 통(해|하여)`
  - `에 비추어`
  - `(으)로써`

**S5. 증명 대상 절을 못 찾으면 문장 전체를 쓴다 (715행)**
- 원인: `if target_clauses else sent_clean` 때문에 대상 절이 없을 때 문장 전체가 범위가 된다. 상대방 주장·별개 사실 절의 술어까지 센다(조건 3 위반).
- 해결: 대상 절이 없으면 그 서증은 **판정하지 않는다**.

**S6. 완료 술어를 활용형 나열로만 잡는다 (546~549행)**
- 원인: '지급하였·변제했' 같은 활용형만 있어 '지급을 마친·갚았다·끝냈다·납부를 끝마쳤다'를 놓친다.
- 해결: '(지급|변제|납부|이행|시공|공사|인도)(을|를)? (마치|끝내|끝마치|완료하)' 구조와 어간 '갚'으로 잡는다. 수량 전칭(전액·전부·모두)은 채무·대금 명사를 꾸밀 때만 전칭으로 센다.

**S7. 제외 가드를 문장 전체에 건다 (667행)**
- 원인: '아니다·않았다·볼 수 없' 등이 문장 어디에 있든 문장 전체를 건너뛴다. 진짜 과장 문장에 다른 부정 절이 있으면 놓친다.
- 해결: 부정·가정·의문은 **술어가 있는 그 절**에 걸렸을 때만 제외한다. 상대방 주장 인용은 인용절 안 술어만 제외한다.

**S8. 등급 규칙을 하나로 맞춘다 (750행)**
- 진단·견적만 증명 표지를 따로 요구하는 분기를 지운다.
- 모든 범주에 'S5의 증명 대상 절 + S4의 직접 증명 구조 + 매트릭스 못 덮음'을 공통으로 적용한다. 이를 충족하면 B, 증명 표지만 있고 직접 구조가 없으면 C다.
- 진단·진술확인은 C 상한, 통지는 자기 측 발신일 때만 B(승인 조건 6 그대로).

**S9. 세트 득점 0의 원인을 진단한다 (평가 세트 문장 열람·인용 금지)**
- 은퇴 4세트 EVI-OVR 미득점 항목과 train EVI-OVR 미득점 항목마다, 이 코드가 어느 단계에서 멈췄는지 **건수로만** 표로 낸다. 문서 번호·유형까지만 적고 문장은 적지 않는다.
- 단계: ① 서증 범주 미식별, ② 인용 행 미연결, ③ 증명 대상 절 없음, ④ 술어 범주 없음, ⑤ 매트릭스 덮음, ⑥ 결합·제외 가드로 제외, ⑦ 결과는 냈으나 채점 위치 불일치.
- 계측은 함수 안 디버그 카운터(시험 전용 인자)로 하고, 제품 출력은 바꾸지 않는다.
- 이 표를 보고 일반 규칙으로 고칠 수 있는 단계만 고친다. 특정 항목에 맞춘 낱말 추가는 2-2 규약 위반이다.

**제출물** (2c2a903 PR 본문에 없던 것 포함)
- S1~S9 대응표, 규칙별 득점 귀속표, train EVI-OVR 원인표(S9).
- `_DIRECT_PROOF_STRUCTURE_RE` 표면형 전체 목록.
- `test_control_notice_unknown_sender_fixed_to_grade_c`에서 뺀 severity 단언을 되살린다.
- 점검표 1~7항, precheck 요약(`--quick`이면 CI '은퇴 세트 비교'·'테스트' 성공 병기).
- holdout은 현재 Steve(81.9)와 비교해 적는다.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 비공개 탐침에서 양성 2/3 이상, 정상 대조 오탐 0.
- 3절 B 공통 조건: 은퇴·train 같은 유형 항목이 함께 올라야 한다. 그래도 0이면 평가 측은 S9 표와 함께 'Added(새 탐지 기능)로 득점 없이 포함할지'를 사용자께 올린다.

### B-1 5차 보완 지시 (#165 `9806494` 보완, 10-24) — 원인별 해결 방안
4차 지시 S1~S8은 반영됐다. **정상 대조 오탐이 3/12에서 0으로 줄었다.** 의사표시·직업 '의사'·자기 통지·발신인 추정·부정 절·낱말 경계 꼴이 모두 해소됐다. 남은 것은 **놓침(재현율)**과 **S9 미제출**이다. 아래 V1~V4만 고친다. 줄 번호는 `9806494`의 `packages/claim_engine/evidence_consistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, 새 Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9, 은퇴 46.7/40.7/48.3/43.9, train 37.5/37.5/37.5/36.5: **모두 변화 0**(EVI-OVR 득점 0, 하락 0).
- 평가 측 탐침(문장 비공개):
  - 3차 세트: 양성 4/6, 오탐 0/12.
  - 새 4차 세트: 양성 3/6, 오탐 0/12.
  - **합계 양성 7/12(58%)로 기준 2/3에 못 미친다.** 오탐 기준은 충족했다.
- 놓친 꼴(평가 측이 정규식으로 직접 확인):
  - '대여금 **전액을 갚은**', '물품대금을 **모두** 지급한', '공사가 **전부 끝마쳐졌다**' — 수량 전칭이 명사 **뒤**에 오는 꼴과 완료 술어의 활용형.
  - 사업자등록증·산출내역서로 지급·완료를 단정하는 꼴.
- CI(인용): PR 실행 필수 5종 모두 성공.

**V1. 수량 전칭을 '전칭 + 명사' 어순에서만 잡는다 (`TOTAL_AMOUNT_MODIFIER_RE` 567~569행)**
- 원인: `(전액|전부|모두)(의|\s+)(채무|대금|…)`라서 '전액 대금'만 잡는다. 한국어에서 흔한 **명사 뒤 전칭**('대여금 전액을', '물품대금을 모두', '공사가 전부')을 놓친다. 명사 목록도 '대금' 등 고정 낱말이라 '대여금·물품대금·공사비'를 놓친다.
- 해결:
  - 두 어순을 모두 잡는다: `(전액|전부|모두|일체)(의)?\s*N`과 `N(을|를|이|가|의)?\s*(전액|전부|모두)`.
  - N은 금전·채무 명사 **접미 규칙**(`…대금|…금|…비|…채무|차임|원리금`)과 '공사·용역·업무'(완료 대상)로 정한다. 낱말을 열거하지 않는다.
  - 4차의 '채무·대금 명사를 꾸밀 때만' 조건은 유지한다. 위 N 범위 밖('모두 출석')은 전칭이 아니다.
- 시험: 위 세 꼴 각 1개 + 어순 바꿈 1개 = 양성. '모두 출석하였다'·'전부 기각' = 대조.

**V2. 완료 술어가 활용형 나열이라 '끝마쳐졌·갚은·끝났'을 놓친다 (`COMPLETION_PREDICATE_RE` 561~564행)**
- 원인: '마치|마쳤|마친|끝내|끝냈|끝낸|끝마치|끝마쳤|끝마친'과 '갚았'만 있다. '끝마쳐(졌)·마쳐(졌)·끝났·끝난·갚은·갚아·갚고'를 놓친다.
- 해결: **어간 + 어미 결합**으로 바꾼다.
  - 어간: `마치|마쳐|끝마치|끝마쳐|끝내|끝나|끝났|끝난|갚`.
  - 뒤에 `[가-힣]*`(어미)와 피동 `지|졌`을 허용한다.
  - 앞의 대상은 '(지급|변제|납부|이행|시공|공사|인도|대금|채무)(을|를|이|가)?'로 결합한다(대상 없는 '끝났다'는 세지 않는다).
- 시험: '공사가 끝마쳐졌다', '채무를 갚은', '납부가 끝났다', '지급을 마쳐' = 양성 근거. '회의가 끝났다' = 대조(대상이 금전·이행 아님).

**V3. 범주 식별 표면형을 점검한다 (`EVIDENCE_KIND_CATEGORIES`)**
- 원인 후보: '공사비 산출내역서'처럼 수식어가 붙은 서증명이 범주에 걸리는지 평가 측 탐침에서 확인되지 않았다(V1·V2 때문에 막혔는지 범주 문제인지 구분해야 한다).
- 해결: V1·V2 수정 뒤 서증명 앞 수식어(공사비·용역·물품 등)가 붙어도 범주가 잡히는지 시험으로 확인한다. 범주어를 **접미 일치**(…산출내역서·…견적서·…등록증)로 바꾼다.

**V4. S9 진단표를 낸다 (4차 지시 그대로, 이번 PR에 없음)**
- 은퇴 4세트·train EVI-OVR 미득점 항목마다 멈춘 단계를 **건수로만** 표로 낸다(문장 인용 금지): ① 범주 미식별, ② 인용 행 미연결, ③ 증명 대상 절 없음, ④ 술어 범주 없음, ⑤ 매트릭스 덮음, ⑥ 결합·제외로 제외, ⑦ 결과는 냈으나 채점 위치 불일치.
- V1·V2 뒤에도 득점이 0이면 이 표가 득점 없이 포함할지 판단하는 근거가 된다.

**제출물**
- V1~V4 대응표, 득점 귀속표, S9 진단표, 점검표 1~7항, precheck 요약.
- holdout은 현재 Steve(81.9)와 비교해 적는다.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 비공개 탐침에서 양성 2/3 이상, 정상 대조 오탐 0(이번에 충족한 오탐 0을 유지).
- 3절 B 공통 조건: 은퇴·train 같은 유형 득점. 0이면 평가 측은 S9 표와 함께 'Added(새 탐지 기능)로 득점 없이 포함할지'를 사용자께 올린다.
- V1~V3 외에 새 규칙·새 낱말 목록을 더하지 않는다(범위 고정).

### B-1 6차 보완 지시 (#165 `2b985e6` 보완, 10-24) — 원인별 해결 방안
V1~V3가 반영돼 **재현이 기준을 넘었다**(3차 세트 5/6, 4차 세트 5/6, 새 5차 세트 4/6, 합계 14/18 = 78%). 3·4차 세트의 오탐 0도 유지됐다. S9 진단표도 제출됐다. 남은 것은 새 5차 세트의 **상대방 관련 오탐 2건**과 놓침 2건이다. 아래 X1~X3만 고친다. 줄 번호는 `2b985e6`의 `packages/claim_engine/evidence_consistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정·은퇴·train 모두 변화 0(EVI-OVR 득점 0, 하락 0).
- 새 5차 탐침(문장 비공개): 양성 4/6, **정상 대조 오탐 2/12**.
  - 오탐 ①: 상대방이 '작성하여 보낸' 서증(상대방 발신)이 C로 잡힘.
  - 오탐 ②: 상대방이 '…라고 다투지만'(상대방 주장)이 B로 잡힘.
  - 놓침: 금전 명사 뒤 전칭에 조사가 붙은 꼴 2건.
- CI(인용): 필수 5종 모두 성공.
- S9 진단표(구현 측 제출, 은퇴 12·train 6): ① 범주 미식별 5·2, ② 인용 행 미연결 2·1, ③ 증명 대상 절 없음 2·1, ④ 술어 범주 없음 2·1, ⑥ 결합·제외 1·1, ⑤·⑦ 0.

**X1. 명사 뒤 전칭에 조사가 붙으면 놓친다 (`TOTAL_AMOUNT_MODIFIER_RE` 580행~)**
- 원인: 뒤 어순 `N … (전액|전부|모두|일체)(?![가-힣])`가 전칭 바로 뒤 한글을 금지한다. 그래서 '모두를·전부를·전액을·전부가'처럼 **조사가 붙은 전칭**을 놓친다(평가 측 확인).
- 해결: 전칭 뒤 `(을|를|이|가|은|는|의|으로|로)?`를 허용한 다음 `(?![가-힣])`로 끝낸다. 앞 어순도 같은 방식으로 맞춘다.
- 시험: 금전·채무 명사 + 전칭 + 조사(을·를·이·가) 3변형(구현 측이 자기 문장으로 짓는다) = 양성 근거. '모두를 위하여'처럼 금전 명사가 없는 꼴 = 대조.

**X2. 발신인 관형절이 '동사 연쇄'를 못 읽는다 (`_detect_exhibit_sender` 693행~, 관형절 정규식 705~707행)**
- 원인: `[당사자](가|이)\s*(보낸|발송한|작성한|통지한)`라서 '작성하여 보낸·작성·발송한·직접 보낸'처럼 동사가 둘 이상 이어지면 발신인을 못 정한다. 그래서 상대방 발신인데 '발신인 불명(C)'으로 판정된다.
- 해결: `[당사자](가|이)\s*(?:[가-힣]{1,6}(?:하여|해|하고|·)\s*){0,2}(보낸|발송한|작성한|통지한|송부한)`처럼 앞 동사 연쇄(최대 2개)를 허용한다. 서증 라벨까지의 거리 제한(25자)은 유지한다.
- 시험: '피고가 작성하여 보낸 을 제1호증', '피고가 작성·발송한 을 제1호증' = 상대방 발신(제외). 같은 꼴에 원고 = 자기 측(판정).

**X3. 상대방 주장 제외가 '다투'를 모르고 30자 창에 묶여 있다 (`_OPPONENT_CLAIM_RE` 656~659행)**
- 원인:
  - 대안이 '주장하나·주장하지만·…' 또는 `(피고|원고|상대방)(는|은|가|이|측은)\s*[^.]{0,30}?(주장|항변|진술)`뿐이다. '다투지만·다투나·번복하였으나'가 없다.
  - 주어와 술어 사이가 30자를 넘으면(서증 인용이 끼면 흔하다) 놓친다.
  - 또 '원고는 … 진술'처럼 **자기 측** 진술까지 상대방 주장으로 빼는 위험이 있다.
- 해결:
  - 술어를 `(주장|진술|항변|번복)(하|했|하였)?(나|지만|는데|으나|며|고\s*있으나)|다투(나|지만|는데|었으나|며|고\s*있)`로 넓힌다.
  - 범위는 30자 창이 아니라 **같은 문장 안 그 주어의 절 끝까지**로 한다.
  - 주어는 서면 작성 당사자(`_detect_author_party`)의 **상대 당사자일 때만** 제외한다(A-4 W2와 같은 기준).
- 시험: 상대방 + 주장·다투·번복·항변 4꼴(서증 인용이 끼어 30자를 넘는 꼴 포함) = 오탐 0. 자기 측 '원고는 … 진술'이 과장 단정이면 = 양성.

**득점 0과 포함 여부 (사용자 결정 사항)**
- S9 표상 미득점 18건 중 7건이 '① 범주 미식별'이다. 은퇴·train의 서증 종류가 7범주 밖에 있다는 뜻이다. 범주를 특정 항목에 맞춰 늘리면 2-2 규약 위반이 된다.
- 따라서 X1~X3 뒤에도 득점은 0일 가능성이 높다. 평가 측은 X1~X3 수용 기준 충족 시 'Added(새 탐지 기능, 득점 없음)로 0.14.0에 포함할지'를 S9 표와 함께 사용자께 올린다.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 탐침과 지난 3~5차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- X1~X3 외에 새 범주·새 낱말 목록을 더하지 않는다.

### B-1 7차 보완 지시 (#165 `0daf35b` 보완, 10-25) — 원인별 해결 방안
X1~X3는 지시대로 반영됐다. 재현은 3·4·5차 세트 모두 6/6이다. 그러나 X1로 **'전액을·전부를' 같은 금전 전칭이 잡히기 시작하면서, 그동안 가려져 있던 판정 단계의 결함이 드러났다.** 지난 세트에서 새 오탐 4건(4차 2·5차 2)이 생겼고, 새 6차 세트의 정상 대조 오탐은 **8/12**다. 원인은 다섯이다. 그중 V3는 평가 측 X3 지시문이 종결형을 빠뜨린 탓도 있다(평가 측 지시 보완). 아래 V1~V5만 고친다. 줄 번호는 `0daf35b`의 `packages/claim_engine/evidence_consistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·은퇴 46.7/40.7/48.3/43.9·train 37.5/37.5/37.5/36.5: 모두 변화 0(EVI-OVR 득점 0, 하락 0, 오탐·A등급 0).
- 탐침(문장 비공개):
  | 세트 | 양성 | 정상 대조 오탐 |
  |---|---|---|
  | 3차 | 6/6 | 0/12 |
  | 4차 | 6/6 | 2/12(직전 0) |
  | 5차 | 6/6 | 2/12(직전 2, 꼴이 바뀜) |
  | 새 6차 | 5/6 | **8/12** |
  - 오탐 꼴: 지급 증빙(영수증·이체확인증)으로 '대금 전액 지급'을 증명, 견적서와 지급 증빙을 결합 원용, '…라고 보기 어렵습니다'(부정), '…다고 주장합니다·다툽니다·주장하고 있습니다'(상대방), '…하였다면'(가정), 상대방이 부사를 끼워 동사 둘을 이은 발신 관형절(상대방 발신).
  - 놓친 꼴: 서증 종류가 7범주 밖(범주 미식별, S9 표의 ①과 같음).
- CI(인용): PR·push 실행 필수 검사 모두 성공.

**V1. 금전 전칭이 '전칭_전기간'으로 들어가 지급 증빙까지 덮지 못한다 (875~879행, 매트릭스 592~635행, 결합 예외 931·939행)**
- 원인:
  - 875~879행이 `TOTAL_AMOUNT_MODIFIER_RE`(금전 전칭)를 '전칭_전기간'으로 분류한다. 매트릭스상 '전칭_전기간'은 모든 범주가 `False`라서, 영수증·통장거래내역 같은 **지급 증빙으로 '대금 전액 지급'을 증명해도** 과장으로 잡힌다.
  - 931·939행 결합 예외는 `"전칭_전기간" not in matched_pred_cats`를 요구한다. 그래서 견적서와 이체확인증을 함께 원용해도 예외가 빠진다.
  - 금전 전칭은 '지급·변제 완료'의 **범위**를 말하는 것이지, '항상·전 기간·모든 거래' 같은 기간·범위 전칭과 성격이 다르다. 메모 128 매트릭스의 '영수입금' 행 주석('그 금액 한도에서 변제·완료는 덮음')과도 맞지 않는다.
- 해결:
  - 금전 전칭(`TOTAL_AMOUNT_MODIFIER_RE` 일치)은 '전칭_전기간'에 넣지 않는다. 술어가 지급·변제·수령·완료이면 '완료_확정'의 수식으로 보아 **'완료_확정'의 매트릭스 값을 따른다**. 술어가 없으면 범주를 더하지 않는다.
  - '전칭_전기간'은 기간·범위 전칭(항상·늘·전 기간·모든 거래 등 기존 낱말)만 맡는다.
  - 결합 원용은 인용된 모든 서증 범주의 매트릭스 값을 **합집합**으로 보고 판정한다. 931·939행의 특례 조건은 이 합집합 판정으로 대체한다.
  - 메모 128과의 관계: 매트릭스 값은 바꾸지 않는다. 금전 전칭의 분류만 바꾼다(평가 측이 조건부 승인한 메모 조건의 해석을 이렇게 정한다).
- 시험: 영수증·통장거래내역으로 '대금 전액 지급' = 대조. 견적서 + 이체확인증 결합 = 대조. 견적서·명함만으로 '대금 전액 지급' = 양성(유지).

**V2. 부정 표지가 좁다 (`_NEGATED_PREDICATE_RE` 653~655행)**
- 원인: '볼 수 없·단정할 수 없…'뿐이라 '보기 어렵·인정하기 어렵·단정하기 어렵·부족하'를 놓친다(평가 측 확인: '보기 어렵습니다' 불일치).
- 해결: `(?:보|인정하|단정하|판단하)기\s*(?:어렵|힘들|곤란)|(?:인정하|증명하)기에\s*부족|부족하다고\s*보`를 더한다. 낱말을 늘리는 대신 '-기 어렵/부족' 구조로 잡는다.
- 시험: '…라고 보기 어렵습니다', '…하기에 부족합니다' = 오탐 0.

**V3. 상대방 주장 술어에 종결형이 없다 (`_OPPONENT_CLAIM_VERBS_PAT` 658~661행, `_is_opponent_claim` 672~690행)**
- 원인: 술어 뒤가 연결어미(-나·-지만·-는데·-으나·-며·-고 있으나)뿐이다. '주장합니다·주장하고 있습니다·다툽니다·다퉜다'를 놓친다(평가 측 확인: 세 꼴 모두 `False`). 평가 측 X3 지시문의 정규식이 그랬다(평가 측 지시 보완).
- 해결: `(?:(?:주장|진술|항변|번복)(?:하|합|했|하였|한)|다(?:투|툽|퉜|퉈))`로 바꾸고 어미를 제한하지 않는다. 상대 당사자 주어 조건(`_get_opponent_party_pattern`)은 유지한다. 자기 측 주어는 지금처럼 빼지 않는다.
- 시험: 상대방 + 주장합니다·주장하고 있습니다·다툽니다·다퉜으나 = 오탐 0. 자기 측 진술 + 과장 = 양성(유지).

**V4. 가정 표지가 '-였다면'을 놓친다 (`_CONDITIONAL_RE` 688행)**
- 원인: `(라면|한다면|할 경우|인 경우)`라서 '지급하였다면·받았다면'(-었다면/-였다면)을 놓친다.
- 해결: `(?:[었였았]?다면|라면|할\s*경우|인\s*경우|하더라도|더라도)`로 바꾼다('설령'이 앞에 있으면 문장 전체를 가정으로 본다).
- 시험: '설령 …하였다면', '…받았다면' = 오탐 0.

**V5. 발신인 동사 연쇄에 부사가 끼면 못 읽는다 (`_detect_exhibit_sender` 733~736행)**
- 원인: X2 정규식이 동사 연쇄(`…하여`)만 허용한다. '직접·스스로·미리' 같은 부사가 끼면 발신인을 못 정한다(평가 측 확인: 부사가 끼면 `None`, 부사를 빼면 상대 당사자로 정해짐).
- 해결: 당사자 표지 뒤에 부사 1개(`[가-힣]{1,4}\s+`, 단 당사자 호칭·서증 라벨 제외)를 허용한 뒤 기존 동사 연쇄를 잇는다.
- 시험: '[상대방]가 [부사] [동사]하여 [동사]한 [서증 라벨]' 꼴 = 상대방 발신(제외).

**득점 0과 포함 여부 (사용자 결정 사항, 변경 없음)**
- 세트 득점 0이 지속된다. V1~V5 수용 기준 충족 시 'Added(새 탐지 기능, 득점 없음)로 0.14.0에 포함할지'를 S9 표와 함께 사용자께 올린다.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 탐침과 지난 3~6차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- V1~V5 외에 새 범주·새 낱말 목록을 더하지 않는다. 매트릭스 값은 바꾸지 않는다.

### B-1 8차 보완 지시 (#165 `17f7734` 보완, 10-25) — 원인별 해결 방안
V1~V5는 지시대로 반영됐다. 부정(V2)·상대방 종결형(V3)·가정(V4)·부사 낀 발신(V5) 꼴의 오탐이 모두 없어졌다. 7차의 6차 세트 오탐 8/12는 1/12가 됐다. 남은 원인은 넷이다. 그중 **BB1은 평가 측 V1 지시의 결함**이다. '대금 전액'과 '채무 전부'를 구분하지 않고 금전 전칭을 모두 '완료_확정'으로 보내라고 해서, 메모 128이 막으려던 '영수증 한 장으로 채무 전부 소멸 단정'까지 덮이게 됐다(평가 측 지시 정정). 아래 BB1~BB4만 고친다. 줄 번호는 `17f7734`의 `packages/claim_engine/evidence_consistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·은퇴 46.7/40.7/48.3/43.9·train 37.5/37.5/37.5/36.5: 모두 변화 0(EVI-OVR 득점 0, 하락 0, 오탐·A등급 0).
- 탐침(문장 비공개). BB1 정정에 따라 평가 측이 지난 세트의 양성 2문장(특정 대금·대여금의 '전액 변제'를 지급 증빙으로 증명)을 **대조로 다시 분류**했다. 그 문장들은 이번 판정대로 잡히지 않는 것이 맞다.
  | 세트 | 양성 | 정상 대조 오탐 |
  |---|---|---|
  | 3차 | 5/6 | 1/12 |
  | 4차 | 5/5(재분류 1) | 1/13 |
  | 5차 | 3/5(재분류 1) | 1/13 |
  | 6차 | 4/6 | 1/12(직전 8/12) |
  - 오탐 꼴: 견적서와 계좌·통장 거래내역 결합 원용(3세트 공통), 상대방이 작성해 보낸 확인서로 상대방 쪽 사실을 증명.
  - 놓친 꼴: 특정되지 않은 '채무 전부'를 영수증으로 증명, 금전 전칭 + '치르다·받다·납부하다' 술어, 서증 종류가 7범주 밖(S9 ①).
- CI(인용): PR·push 실행 필수 검사 모두 성공.
- 이번 회차는 새 세트 없이 지난 4세트로 판정했다(남은 결함이 지난 세트에서 재현되므로). 수용 판단 때는 새 세트를 짓는다.

**BB1. 금전 전칭을 '특정 금액'과 '채무 전체'로 나눈다 (952~956행, 926~928행)**
- 원인: 평가 측 V1 지시대로 `TOTAL_AMOUNT_MODIFIER_RE`(금전 전칭)를 지급 술어가 있으면 모두 '완료_확정'으로 보낸다. 그런데 금전 전칭에는 두 종류가 있다.
  - (가) **특정 채무의 금액 범위**: '[…대금·…금·차임] 전액·전부를 지급·변제'. 영수증·입금증·이체확인증은 그 금액 지급을 증명할 수 있다. '완료_확정'으로 본다(V1 그대로).
  - (나) **당사자 사이 채무 전체**: '[당사자]에 대한 채무 전부', '모든 채무', '채무 일체', '일체의 채무'처럼 특정 채무 명사 없이 채무 전체를 가리키는 꼴. 영수증 한 장은 그 영수증의 금액 지급만 증명하고, 다른 채무가 없다는 사실까지 증명하지 못한다. 메모 128 매트릭스 '영수입금' 행 주석('전액·모든 채무 등 전칭은 단독으로 못 덮음')이 막으려던 꼴이다.
- 해결:
  - `TOTAL_AMOUNT_MODIFIER_RE`가 맞은 명사 N을 본다. N이 특정 금액 명사(`…대금|…금|…비|차임|원리금` 접미, 기존 `_AMOUNT_NOUN_PAT`)이고 그 앞에 '[당사자]에 대한'만 있고 다른 수식이 없어도 (가)다. N이 맨 '채무'(접두 금액 명사 없음)이거나 '모든·일체의'가 앞에 오면 (나)다.
  - (나)는 '전칭_전기간'으로 분류한다(매트릭스상 모든 범주가 못 덮음). 결합 원용이라도 합집합에 '전칭_전기간'이 없으면 과장이다.
- 시험: '[당사자]에 대한 채무 전부·채무 일체' + [변제 술어] + 영수증 = 양성. '[…대금] 전액을 지급' + 영수증 = 대조. '[…대금] 채무 전부를 변제' + 영수증 = 대조(특정 채무).

**BB2. 금전 전칭의 지급 술어가 닫힌 목록이다 (953~955행)**
- 원인: 금전 전칭을 '완료_확정'으로 올리는 조건이 `(지급|변제|수령|완납|완료|정산|상환|갚|입금|결제)` 낱말 목록이다. '치르다·받다·납부하다·송금하다·내다'를 놓친다(평가 측 확인: 세 꼴 모두 술어 범주 없음으로 빠짐). 새 낱말 목록은 2-2 규약상 늘리지 않는다.
- 해결: 별도 목록을 두지 않는다. 기존 '완료_확정' 술어 판정(`CLAIM_PREDICATE_CATEGORIES["완료_확정"]` 낱말 + `COMPLETION_PREDICATE_RE`)을 그대로 쓰고, 금전 명사 N이 그 술어의 **목적어**(`N(을|를)? … 술어` 같은 절)일 때만 '완료_확정'으로 본다. 기존 사전에 없는 '치르·받·납부·송금'은 V2 방식(어간 + 어미)으로 `COMPLETION_PREDICATE_RE` 어간에 넣는다(지급 행위 어간, 낱말 목록 아님).
- 시험: 금전 전칭 + 치른·받은·납부한 + 견적서·신분증 = 양성(서증이 지급을 못 덮음). 같은 술어 + 영수증 = 대조.

**BB3. 결합 합집합이 거래내역 서증의 범주를 못 찾는다 (854~877행, 범주 사전 533행)**
- 원인: V1 합집합 판정은 `EVIDENCE_KIND_CATEGORIES`로 서증 범주를 찾는다. 그런데 '영수입금' 범주(533행)에 '통장거래내역·계좌거래내역'이 없다. 옛 결합 예외가 쓰던 `_PROVABLE_PAYMENT_KINDS_RE`(735~740행)에는 있었는데, V1에서 그 정규식을 쓰지 않게 되면서 결합 원용이 깨졌다(평가 측 확인: 두 서증의 범주 `None`, 견적서 + 거래내역 결합이 3세트 모두 B). `_PROVABLE_PAYMENT_KINDS_RE`·`_PROVABLE_AGREEMENT_KINDS_RE`는 이제 쓰이지 않는다.
- 해결: `_PROVABLE_PAYMENT_KINDS_RE`의 서증 이름을 '영수입금' 범주로, `_PROVABLE_AGREEMENT_KINDS_RE`의 이름을 해당 범주로 **옮기고** 두 정규식을 지운다(낱말 총수는 늘지 않는다). 범주 판정은 접미 일치('…거래내역'·'…확인증')로 한다(V3과 같다).
- 시험: 견적서 + 계좌·통장 거래내역 결합 = 대조. 견적서 단독 = 양성(유지).

**BB4. 상대방 작성 확인서를 상대방 쪽 사실의 증명으로 쓰면 제외해야 한다 (993~1003행)**
- 원인: S3의 상대방 발신 제외가 '일방통지' 범주에만 걸린다. V5로 발신인은 정확히 잡히게 됐지만, 상대방이 작성해 보낸 **확인서·각서(진술확인 범주)**로 상대방 쪽 사실(공사 완료·수령 등)을 증명하는 것은 상대방의 자인을 쓰는 것이라 과장이 아니다. 그런데도 C로 잡힌다.
- 해결: 발신인(작성자)이 상대 당사자이고 범주가 '일방통지' 또는 '진술확인'이면 제외한다. 술어의 주체가 상대방이거나 상대방 의무의 이행·완료일 때로 한정한다(자기 측 의무를 상대방 확인서로 단정하는 꼴은 지금처럼 판정).
- 시험: 상대방이 작성해 보낸 확인서 + 상대방 측 완료 = 대조. 자기 측 작성 확인서 + 과장 = 양성(유지).

**정리**
- 984~991행의 합집합 판정 뒤에 남은 도달 불가 줄(`continue` 뒤 `debug_counters` 갱신과 `continue`)을 지운다.

**득점 0과 포함 여부 (사용자 결정 사항, 변경 없음)**
- 세트 득점 0이 지속된다. BB1~BB4 수용 기준 충족 시 'Added(새 탐지 기능, 득점 없음)로 0.14.0에 포함할지'를 S9 표와 함께 사용자께 올린다.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 새로 짓는 탐침과 지난 3~6차 세트(재분류 반영) 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- BB1~BB4 외에 새 범주·새 낱말 목록을 더하지 않는다. 매트릭스 값은 바꾸지 않는다.

### B-1 8차 보완 지시 부록 — 평가 측 사전 검증 결과 (#165, 10-25)
평가 측이 8차 지시 BB1~BB4를 `17f7734` 사본에 적용해 검증했다. **지시대로 하면 수용 기준을 충족한다**(남는 놓침 1건은 7범주 밖 서증, 범위 밖). 아래 세 점을 지킨다.

**검증 결과(평가 측 사본)**
- 탐침 3~6차(재분류 반영): 양성 6/6·5/5·5/5·5/6(합 21/22), 정상 대조 오탐 0/50.
- 기존 시험: `tests/test_evidence_overreach.py` 전부 통과, `-k "evidence or overreach or numbering or tk73 or claim"` 전부 통과.
- 세트: 고정·은퇴 변화 0, 하락 0.

**구현 시 주의(사본 적용 중 확인)**
- BB2: `COMPLETION_PREDICATE_RE`의 금전 명사와 술어 사이 수식어는 **최대 둘, 조사 허용**으로 둔다: `(?:(?:모두|전부|전액|이미|다)(?:[을를이가])?\s*){0,2}`. 하나만 허용하면 '[…대금] 전액을 모두 지급', '[…대금] 전액을 이미 지급' 꼴의 기존 양성 시험 3개(`test_x3_…`·`test_v1_…`·`test_v3_…`)가 실패한다. 어간 묶음은 기존 '마치·끝내·갚'에 지급 행위 어간(치르·받·납부·송금·지급·변제·상환·입금·결제·정산·수령)을 더한다. 그다음 금전 전칭 → 완료_확정 판정은 별도 낱말 목록 없이 `COMPLETION_PREDICATE_RE` 일치만 본다.
- BB3: `_PROVABLE_AGREEMENT_KINDS_RE`의 이름(계약서·합의서 등)이 들어갈 범주는 7범주에 없다. 옮기지 말고, 쓰이지 않는 정규식만 지운다(지시 정정). `_PROVABLE_PAYMENT_KINDS_RE`의 거래내역·세금계산서·지급증명서는 '영수입금'으로 옮긴다.
- BB4: 평가 측 사본은 '진술확인' 범주에 상대방 발신 제외를 그대로 넓힌 단순형으로 검증했다(기존 시험 통과). '술어 주체가 상대방일 때로 한정'은 더해도 되지만, 더하면 같은 시험을 다시 돌려 확인한다.

### B-1 9차 판정 — 조건부 승인 (#165 `fb92a19`, 10-25) — 한 줄 수정 조건
BB1~BB4가 반영됐다. 지난 4세트는 양성 21/22·오탐 0/50이다. 평가 측이 새로 지은 7차 세트에서 오탐 2건이 나왔는데, 원인은 하나다(CC1). **CC1 한 줄만 고치면 수용한다.** 평가 측이 그 수정을 `fb92a19` 사본에 적용해 미리 검증했다(아래). 줄 번호는 `fb92a19`의 `packages/claim_engine/evidence_consistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·은퇴 46.7/40.7/48.3/43.9·train 37.5/37.5/37.5/36.5: 모두 변화 0(EVI-OVR 득점 0, 하락 0, 오탐·A등급 0).
- 탐침(문장 비공개):
  | 세트 | 현행 양성 | 현행 오탐 | CC1 적용 사본 양성 | CC1 적용 사본 오탐 |
  |---|---|---|---|---|
  | 3차 | 6/6 | 0/12 | 6/6 | 0/12 |
  | 4차 | 5/5 | 0/13 | 5/5 | 0/13 |
  | 5차 | 5/5 | 0/13 | 5/5 | 0/13 |
  | 6차 | 5/6 | 0/12 | 5/6 | 0/12 |
  | 새 7차 | 5/6 | **2/12** | 5/6 | **0/12** |
  - 현행 오탐 꼴: 합의서로 상대방의 합의·감면 합의를 증명.
  - 놓친 꼴(기준 안, 고치지 않아도 됨): 서증 종류가 7범주 밖(S9 ①), 자기 측이 보낸 통지서로 상대방 내심(악의)을 단정하는 꼴 1건.
- CC1 적용 사본의 기존 시험: `tests/test_evidence_overreach.py` 전부 통과.
- CI(인용): PR·push 실행 필수 검사 모두 성공.

**CC1. 합의서류를 '진술확인' 범주에 넣지 않는다 (범주 사전 537~540행)**
- 원인: BB3에서 옛 `_PROVABLE_AGREEMENT_KINDS_RE`의 이름(각서·이행각서·합의서·약정서·조율서·협약서)을 '진술확인' 범주로 옮겼다. 그런데 '진술확인'은 매트릭스상 '상대방의사표시'를 못 덮는 범주다. 그래서 **합의서로 상대방의 합의를 증명하는 정상 서술**이 과장(C)으로 잡힌다. 합의서는 당사자 합의를 직접 증명하는 처분문서라 '진술확인'과 성격이 다르다. 평가 측 부록도 '옮기지 말고 지운다'였다.
- 해결: 539행의 `"각서", "이행각서", "합의서", "약정서", "조율서", "협약서",`를 지운다. 이 이름들은 7범주 어디에도 넣지 않는다(범주 미식별 = 판정하지 않음, BB3 이전 동작과 같다).
- 시험: 합의서로 상대방 합의 증명, 합의서로 감면 합의 증명 = 대조(오탐 0) 2개를 더한다. 기존 시험은 그대로 통과해야 한다.

**수용 조건**
- CC1만 고친다. 다른 변경을 더하지 않는다.
- 필수 CI 성공. 평가 측은 CC1 커밋을 받으면 3~7차 세트와 기존 시험을 다시 돌려 위 사본 결과와 같은지만 확인하고 수용한다.

**득점 0과 포함 여부 — 사용자 결정(10-25)**
- 세트 득점은 끝까지 0이다. 사용자 결정: 수용 뒤 'Added(새 탐지 기능, 세트 득점 없음)'로 0.14.0에 포함한다. CHANGELOG에는 '세트 득점 없음, 일반 표현 탐침으로만 검증'을 함께 적는다.

### B-1 판정 — 수용 (#165 `02a30b6`, 10-25)
CC1이 지시대로 반영됐다(범주 사전에서 합의서류 6낱말 삭제, 대조 시험 2개 추가, 다른 변경 없음). **수용한다.** 남은 보완 지시는 없다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·은퇴 46.7/40.7/48.3/43.9·train 37.5/37.5/37.5/36.5: 항목 변화 0, 오탐·A등급 0.
- 탐침(문장 비공개): 3차 6/6·0/12, 4차 5/5·0/13, 5차 5/5·0/13, 6차 5/6·0/12, 7차 5/6·0/12 — 합 26/28·오탐 0/62. 사전 검증 사본 결과와 같다.
- 시험: `tests/test_evidence_overreach.py` 전부 통과, `-k "evidence or overreach or numbering or tk73 or claim"` 전부 통과(평가 측 재실행). CI(인용): PR·push 실행 필수 검사 모두 성공.
- Steve `c88c208`(#167 병합)과 로컬 병합 시험: 충돌 없음.

**알려진 미해결(known_open, 후속)**
- 서증 종류가 7범주 밖이면 판정하지 않는다(S9 ①, 범위 밖).
- 자기 측이 보낸 통지서로 상대방 내심(악의)을 단정하는 꼴을 놓친다.

**0.14.0 포함(사용자 결정 10-25)**: 'Added(새 탐지 기능, 세트 득점 없음)'. CHANGELOG에 '세트 득점 없음, 일반 표현 탐침으로만 검증'을 함께 적는다.

**병합**: 10-25 사용자 지시 뒤 병합 커밋 `5031b5f`로 Steve에 넣었다(head `02a30b6`).

### B-3 2차 보완 지시 (#167 `af28269` 불승인, 10-24) — 메모 보정본 먼저, 2-2 규약 전부 적용
**문제(원인)**
1. 평가 세트 정답지 문구 2건이 규칙에 들어가 CI 점수 하락 게이트가 실패한다(0절 위반).
2. 새 `_ARITH_MULT_RE`·`_ARITH_ADD_RE`·`_ARITH_SUB_RE`가 기존 `calculation.py`와 같은 식을 다시 잡는다. 그래서 `test_pipeline_entrypoint_leading_multiplier_calculation`이 2건을 받아 실패한다(4절 병렬 검사 금지 위반).
3. 장소·서명자·발신·접수·순액 규칙(상태표 B-3 행의 5개)은 고정 구절 틀이다. 틀을 조금만 바꿔도 0이다.
4. 메모 #158의 핵심인 '같은 대상의 같은 속성'을 문서 전체에서 모으는 절차가 없다. 정규식 한 개가 한 문장 안 두 진술을 한꺼번에 잡는 방식이다.
5. TK-125 문서 커밋이 섞였다.

**고칠 것(전부)**
1. **삭제**: 평가 세트 문구 2건이 든 규칙, `_ARITH_*` 4개, 위 5개 틀 정규식. 산식 꼴이 부족하면 별도 PR로 `calculation.py`를 고친다.
2. **3항 추출**: 문장마다 `(대상, 속성, 값)`을 뽑는다.
   - 대상: 같은 명사구, 또는 지시어(그·위·해당·같은·동일)를 앞 명사로 푼 것.
   - 속성: 닫힌 종류만 쓴다. 금액·수량, 일시, 장소, 서명자 목록, 횟수, 당사자 지위.
   - 값은 정규화한다(금액 원 단위, 날짜 ISO, 사람 이름 집합).
3. **비교**: 문서 전체를 (대상, 속성)으로 묶는다. 단일 값 속성에서 값이 둘 이상이면 낸다.
   - 장소: 같은 대상, 같은 시간대, '~에만·계속·내내' 같은 한정 표지(문법 표지 사전)가 있는데 다른 장소가 나올 때.
   - 서명자: '유일·단독·~만' 한정 표지가 있는데 다른 서명자가 나오거나, 서명했다고 한 사람을 서명하지 않았다고 할 때. 사람 이름 슬롯으로 판정하고 문구를 고정하지 않는다.
4. **제외(구조로)**: 정정·오기, 주위적·예비적, 상대방 주장 인용, 가정·조건, 부분 수식(잔금·계약금·일부), 시점이 다른 값(변경 전·후).
5. **성능**: 묶음 비교 O(n), 4배당 비 < 8(점검표 2항).
6. **시험**: 속성 6종 × 양성 1개 이상 × 2-2 다-3 세 변형, 대조 6개 이상(제외 구조별 1개). 기존 시험 전체 통과 출력을 붙인다.
7. TK-125는 이 PR에서 빼고 별도 PR로 낸다. 보호 경로 변경 제안이라 평가 측이 따로 판정한다.

**수용**: 2-2 라 전부. 은퇴 10의 EVI-INCONS 5건은 득점 0이다. 이 득점을 노리고 문구를 맞추면 2-2 나-3 대조에서 무효가 된다.

### B-3 3차 보완 지시 (#167 `90f56b3` 불승인, 10-24) — 원인별 해결 방안
평가 세트 문구 0건(CI 통과 조건 해소), 옛 틀 정규식 삭제, 메모 129 방향 반영은 확인했다. 그러나 **병렬 산식 검사가 남아 기존 시험이 실패**하고, 일반 표현에서는 **양성 0**이다. 아래 T1~T9를 **모두, 한 번에** 고친다. 줄 번호는 `90f56b3`의 `packages/claim_engine/internal_inconsistency.py` 기준이다. 메모를 다시 내지 않는다. 결과는 PR 본문의 'T번호 → 바꾼 함수 → 시험 이름' 대응표로 낸다.

**측정 요약**
- 평가 측 재실행(오프라인, Steve `0887d49` 같은 탐지 조건, 항목 단위, train 포함):
  - 고정 82.6/81.9 불변. train 변화 0.
  - 은퇴: 08b 40.7→42.6, 09 48.3→51.7(EVI-INCONS 3항목).
  - **득점 귀속(평가 측 확인):** 3항목 중 2항목(08b 1, 09 1)은 이 PR의 산식 검사(`ARITHMETIC_MISMATCH`, T1)에서, 1항목(09)은 장소 규칙에서 나왔다. 산식 득점은 B-3 득점으로 세지 않는다(병렬 검사 금지).
- 평가 측 새 탐침(문장 비공개): **양성 0/6**(기준 2/3 미달), 정상 대조 오탐 0/10.
  - 놓친 꼴: 총액 표지 없는 대금 충돌, 지시어가 다른 같은 사고의 날짜 둘, '같은 날'로 이어지는 장소 충돌, '원고 ○○만이' 꼴 단독 서명 충돌, '원고는 이 사건 임대차계약의 임대인' 꼴 지위 역전, 수량 충돌.
- 시험: `tests/test_calculation_leading_multiplier.py::test_pipeline_entrypoint_leading_multiplier_calculation` 실패(`ARITHMETIC_MISMATCH` 2건). 2차 판정과 같은 원인이다.

**T1. 병렬 산식 검사가 남아 있다 (424~445행, `parse_arithmetic_expression` 181행~)**
- 원인: 옛 `_ARITH_*` 정규식을 수식 파서로 바꿨을 뿐, B-3이 여전히 `ARITHMETIC_MISMATCH`를 낸다. 기존 `calculation.py`와 같은 식을 이중으로 잡아 위 기존 시험이 실패한다(2-2 나-5, 조건 5 위반).
- 해결:
  - B-3에서 산식 판정을 **삭제**한다.
  - 은퇴 2항목처럼 `calculation.py`가 놓치는 꼴('천 단위 쉼표 수 × 정수 = 잘못 적힌 결과', 결과 뒤 단위·조사)은 **`calculation.py`의 기존 식 탐지를 고쳐** 잡는다. 이 PR에서 별도 커밋으로 해도 된다.
  - 결과는 한 문서에 산식 결과 1건뿐이어야 한다. `test_calculation_leading_multiplier.py` 통과, 그리고 `calculation.py` 쪽 시험에 새 꼴 3변형을 넣는다.

**T2. 상대방의 주장을 자기 진술의 모순으로 판정한다 (예외 31~38행)**
- 원인: 예외가 '주장하나·주장은 사실과 다르·주장은 이유 없'뿐이다. '피고는 …라고 **주장합니다/다툽니다/번복합니다**'가 그대로 모순 진술로 들어간다.
  - 평가 측 확인: '총 매매대금 2억 원' + '피고는 총 매매대금이 3억 원이라고 주장합니다' → AMOUNT 1건(오탐).
  - 이 PR의 양성 시험 일부(서명자 변형 3, 금액 변형 1·2)가 바로 이 꼴이다. **상대방 주장 인용은 문서 안 불일치가 아니다**(서면에서 가장 흔한 정상 서술).
- 해결:
  - 문장의 주어가 상대 당사자이고 술어가 인용 종결(`-다고|-라고`) + (주장|다투|진술|번복|항변)이면, 그 인용절 안의 값은 **작성자 진술 집합에서 뺀다**.
  - 위 양성 시험 3개는 작성자 자신의 두 진술이 충돌하는 꼴로 다시 쓴다. 이 꼴은 대조 시험으로 옮긴다.

**T3. 대상 키에 지시어 접두가 들어간다 (514행 `target_key = prefix_kind`)**
- 원인: '이 사건 사고'와 '위 사고'가 서로 다른 키가 되어 비교되지 않는다(평가 측 확인: 접두 같으면 DATE 1건, 다르면 0건).
- 해결: 키는 **핵심 명사(kind)와 계약·사건 종류**로만 만든다. 지시어(위·이 사건·본건·해당·동)는 키에서 빼고, 같은 종류의 직전 대상으로 해소한다.

**T4. 금액은 '총·총액·합계' 표지가 있어야만 잡는다 (497행 `_TOTAL_AMOUNT_KEYWORD_RE`)**
- 원인: '매매대금은 2억 원' 같은 일반 확정 진술을 놓친다.
- 해결:
  - 속성 = 계약 대금 명사 사전(매매대금·공사대금·용역대금·차임·보증금·대여금·약정금, 전체 기재) + 확정 서술(`-은/는 … 원(이다|으로 정하|으로 약정)`).
  - '총'은 선택 표지로 둔다. 부분 수식어(잔금·계약금·중도금·이자·지연손해금) 제외는 유지한다.

**T5. 한국어 금액 해석 오류 (`_KOREAN_MONEY_RE` 107행, `_parse_korean_amount` 150행)**
- 원인: '2억 5천만 원'을 200,000,005로 읽는다(평가 측 확인). '천·백·십' 단위를 처리하지 못한다.
- 해결: 억·만 아래 자리의 천·백·십 단위와 아라비아 숫자 혼용을 해석한다.
- 시험: '2억 5천만 원'=250,000,000, '3천5백만 원'=35,000,000, '1억2천만 원'=120,000,000, '5,000만 원'=50,000,000.

**T6. 장소는 날짜가 문장마다 그대로 있어야만 비교한다 (519~526행 `last_date`)**
- 원인: '같은 날·당일·그날'을 해석하지 않아, 둘째 진술의 날짜가 없으면 건너뛴다.
- 해결: 같은 단락 안에서 상대 날짜 표현을 직전 절대 날짜로 푼다. 주어가 생략된 문장은 같은 단락 안에서만 직전 주어를 잇는다.

**T7. 서명자 이름을 직책+이름에서만 뽑는다 (`_PARTY_TITLE_NAME_RE` 86행, 단독 표지 535행)**
- 원인: '원고 김민수'·'피고 박지훈' 꼴은 role만 잡히고 이름이 빠진다. 단독 표지에 '만·만이·혼자'가 없다.
- 해결: `(원고|피고|신청인|피신청인)\s+[가-힣]{2,4}` 꼴의 이름을 잡는다. 단독 표지에 '만|만이|혼자|외에는'을 넣는다.
- 공동 서명 대조(둘 다 서명했다는 정상 서술)는 유지한다.

**T8. 당사자 지위가 '원고·임대인/임차인·인접 표현'에 고정돼 있다 (141~142행, 448~453행)**
- 원인: `원고(는|가)\s*임대인` 같은 틀이라 '원고는 이 사건 임대차계약의 임대인입니다'도 놓친다. 다른 당사자·다른 계약 지위는 볼 수 없다(2-2 나-1 문장 틀).
- 해결:
  - (당사자, 계약, 지위) 3항으로 바꾼다. 당사자 = 당사자 호칭 전체. 지위 = 닫힌 짝 사전(임대인/임차인, 매도인/매수인, 도급인/수급인, 대주/차주, 위임인/수임인). 결합 = `X는 (… 계약의|에서) Z(이다|로서|인)`.
  - 같은 당사자·같은 계약에서 짝의 반대 지위가 나오면 모순이다.
  - 전대·반소·별개 계약은 제외(유지).

**T9. 득점 귀속과 train 원인표를 낸다**
- 은퇴·train EVI-INCONS 미득점 항목마다 멈춘 단계를 **건수로만** 표로 낸다(문장 인용 금지): ① 속성 낱말 없음, ② 값 해석 실패, ③ 대상 키 불일치, ④ 날짜·주체 미해소, ⑤ 예외로 제외, ⑥ 결과는 냈으나 채점 위치 불일치.
- 특정 항목에 맞춘 낱말 추가는 2-2 규약 위반이다.

**시험 (전부 자기 문장)**
- 양성: 속성 6종(금액·수량·일시·장소·서명자·지위) × 3변형. 변형 하나는 반드시 지시어가 다른 꼴(T3), 하나는 상대 날짜(T6).
- 대조: T2 상대방 주장 3꼴(주장합니다·다툽니다·번복합니다), 공동 서명, 서로 다른 계약, 시점이 다른 장소, 부분 금액, 정정, 주위적·예비적.
- 회귀: `test_calculation_leading_multiplier.py` 포함 전체 통과 출력.

**제출물**
- T1~T9 대응표, 득점 귀속표(산식 득점은 calculation.py 쪽으로 따로 표기), train EVI-INCONS 원인표(T9), 점검표 1~7항, precheck 요약.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공(기존 산식 시험 포함).
- 평가 측이 새로 짓는 비공개 탐침에서 양성 2/3 이상, 정상 대조 오탐 0.
- B-3 득점은 산식을 뺀 규칙의 귀속분만 센다.

### B-3 4차 보완 지시 (#167 `cb21298` 보완, 10-24) — 원인별 해결 방안
T1(병렬 산식 삭제)·T3(지시어 키)·T5(천·백·십)·T6(같은 단락 상대 날짜)·T7(호칭+이름·'만이')는 반영됐다. 기존 산식 시험도 통과한다. 지난 3차 탐침 세트는 양성 0/6 → 3/6(한 단락 묶음 4/6), 오탐 0/10이다. 그러나 **새 4차 탐침에서 정상 대조 오탐이 6/12**로 크게 늘었다. 일반 표현에서 슬롯을 넓게 잡으면서 결합 조건(그 값이 그 대상의 그 속성인지)이 빠졌기 때문이다. 아래 Y1~Y9를 **모두, 한 번에** 고친다. 줄 번호는 `cb21298`의 `packages/claim_engine/internal_inconsistency.py` 기준이다(Y7은 `calculation.py`).

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·train 37.5/37.5/37.5/36.5 변화 0. 은퇴 08·08b 불변, 09 48.3→50.0, 10 43.9→44.3, 하락 0, 오탐·A등급 0.
  - 득점 귀속(평가 측 확인, 규칙 ID만): 09 1항목 = `EVI.INCONS_LOC_EXCLUSIVE`(장소), 10 1항목(부분 점수) = `EVI.INCONS_INTERNAL_AMOUNT`(금액). `calculation.py`를 Steve 판으로 되돌려도 같다(산식 확장 귀속 0). 3차의 산식 득점(08b·09)은 사라졌다(T1대로).
  - 금액 득점은 Y1이 지적하는 넓은 조건 위에서 나왔다. Y1~Y3 수정 뒤에도 남는 득점만 B-3 득점으로 센다.
- 탐침(문장 비공개):
  - 3차 세트 재실행: 양성 3/6(단락 분리)·4/6(한 단락), 오탐 0/10.
  - 새 4차 세트: 양성 4/6, **오탐 6/12**.
  - 오탐 꼴: 계약 체결일과 이행일, 사고일과 보험금 청구일, 대금 중 일부 지급액, 원고 주장 인용, 보증금과 차임, 날짜가 끼어 있는 '…다고 다툽니다'.
  - 놓친 꼴: 계약명이 당사자보다 앞에 오는 지위 역전, 수량 충돌.
- 시험: 관련 시험 전부 통과(평가 측 재실행). CI(인용): PR 실행 필수 5종 성공. **push 실행 '점수 하락 게이트' 실패**: `check_test_edits`가 옛 시험 이름 15개 삭제를 잡았다(Y9).
- PR 본문이 갱신되지 않았다. T 대응표·득점 귀속표·T9 원인표가 없다.

**Y1. 금액 확정 서술 조건이 사실상 꺼져 있다 (513·521행, `_TOTAL_AMOUNT_KEYWORD_RE` 138~144행)**
- 원인: T4에서 '총'을 선택 표지로 바꾸면서 `_TOTAL_AMOUNT_KEYWORD_RE`가 대금 명사 하나만으로 맞는다. 그래서 `has_total_kw`가 대금 명사가 있는 모든 절에서 참이다. 521행 `is_definitive = has_total_kw or …`라 확정 서술 확인을 건너뛴다(평가 측 확인: '대금 중 … 원을 지급' 절이 참). 지급·변제한 일부 금액이 계약 총액으로 들어간다.
- 해결:
  - `has_total_kw`는 **명시 총액 표지(총·총액·합계·전액)**일 때만 참으로 한다. 대금 명사 일치와 분리한다.
  - 표지가 없으면 확정 서술 결합을 요구한다: `N(은|는|이|가|을|를)? … 금액 (이다|입니다|으로 정하|으로 약정|으로 합의)`. 금액 뒤 술어가 지급·변제·송금·입금·수령이면 계약 총액 슬롯이 아니다.
  - 금액 앞 '중·가운데·의 일부'도 부분 표지로 본다.
- 시험: 대금 중 일부 지급 = 대조. 총액 확정 둘이 충돌 = 양성.

**Y2. 금액 키가 계약 종류뿐이라 속성이 다른 금액끼리 비교된다 (526행)**
- 원인: `key = f"total_amount_{cat}"`라서 같은 임대차의 보증금과 차임처럼 **다른 속성**이 한 버킷에 들어간다(평가 측 확인: 보증금 5천만·차임 200만 → C 1건).
- 해결: 키를 (계약 종류, 대금 명사 정규형)으로 만든다. 대금 명사 정규형: 매매대금·공사대금·용역대금→대금, 보증금·임대차보증금→보증금, 차임·월세→차임, 대여금·약정금은 각자. 기간 단위(월·연)가 붙은 금액은 기간 단위도 키에 넣는다.
- 시험: 보증금·차임 = 대조. 같은 보증금 두 값 = 양성.

**Y3. 날짜 슬롯이 '대상의 사건 술어'와 묶이지 않는다 (529~538행, `_INCIDENT_DATE_EXCLUDE_RE` 45행)**
- 원인:
  - 절에 대상 명사('사고·계약')와 날짜만 있으면 슬롯이 된다. 그래서 '계약 체결일'과 '계약에 따른 인도일', '사고 발생일'과 '사고에 관한 보험금 청구일'이 같은 키(`event_계약`·`event_사고`)로 비교된다(평가 측 확인: 두 꼴 모두 C 1건).
  - 이를 막는 수단이 후속 사건 낱말 목록(`_INCIDENT_DATE_EXCLUDE_RE`)뿐이라 목록 밖 낱말(청구·인도·이행·만료 등)에서 계속 깨진다.
  - 532행 `cur_date`는 계산만 하고 쓰지 않는다. 533행이 `last_date`를 쓰므로, 상대 날짜 표지 없이도 앞 절 날짜가 대상 명사 절에 붙는다.
- 해결:
  - 키를 **(대상 핵심 명사, 사건 술어 종류)**로 만든다. 사건 술어 종류는 닫힌 사전으로 정한다: 사고·화재 → 발생(발생하·일어나·났), 계약 → 체결(체결하·맺), 해지·해제는 각자.
  - 날짜는 **그 술어가 있는 절의 날짜**일 때만 그 키에 넣는다. 대상 명사가 '위 사고에 관하여·계약에 따른'처럼 부사어로만 나오고 술어가 다른 사건(청구·인도·지급)이면 슬롯이 아니다.
  - `_INCIDENT_DATE_EXCLUDE_RE` 목록은 지운다(구조 규칙으로 대체).
  - 날짜 승계는 상대 날짜 표지가 있을 때만 한다(`cur_date`를 실제로 쓴다).
- 시험: 체결일·이행일, 발생일·청구일, 발생일·치료일 = 대조. 같은 사고 발생일 둘(지시어 다름) = 양성.

**Y4. 상대방 주장 제외가 날짜·활용형·원고 주어에서 깨진다 (`_OPPONENT_CLAIM_RE` 55~57행, `_LEGITIMATE_EXCEPTION_RE` 31~39행)**
- 원인(평가 측 확인):
  - 주어~술어 창이 `[^.\n]{0,100}?`이다. 서면의 날짜 표기 'YYYY. M. D.'의 마침표에서 창이 끊긴다. 그래서 날짜가 낀 상대방 주장은 빠지지 않는다.
  - 술어가 `다투`라 '다툽니다·다퉜'과 맞지 않는다(ㅂ 활용).
  - 주어가 `피고|상대방|피신청인`뿐이다. 피고 측 서면에서 원고의 주장을 인용하면 빠지지 않는다.
- 해결:
  - 창은 마침표 대신 **문장 경계(`sentence_bounds`) 안**으로 한다. 날짜 마침표는 경계가 아니다.
  - 술어를 `(주장|진술|항변|번복)(하|합|했|하였)|다(투|툽|퉜|퉈)`로 바꾼다.
  - 주어는 서면 작성 당사자의 **상대 당사자**로 정한다. 작성 당사자는 표제·작성자 표시에서 정하고, B-1의 `_detect_author_party`가 있으면 그것을 쓴다. 작성 당사자를 정하지 못하면 원고·피고 모두 받되, 반박 표지(-나·-지만·사실과 다르·이유 없)가 붙은 인용만 뺀다.
- 시험: 날짜가 낀 '…다고 다툽니다', 원고 주장 인용 + '사실과 다릅니다', '다퉜으나' = 오탐 0. 작성자 자신의 두 진술 충돌 = 양성.

**Y5. 지위 키가 어긋나고 계약명 선행 어순을 못 읽는다 (431~435행, `_PARTY_ROLE_STMT_RE` 180~185행)**
- 원인:
  - 433행 `contract_val = role_m.group("contract") or _contract_category(sentence)`라서 계약명이 정규식에 잡히면 '임대차'(원문)가, 못 잡히면 'LEASE'(분류 코드)가 키에 들어간다. 같은 계약인데 키가 달라 비교되지 않는다(평가 측 확인).
  - 정규식이 '당사자 → 계약 → 지위' 어순만 받는다. '위 임대차계약에서 원고는 임차인으로서'처럼 계약이 앞에 오면 못 잡는다.
- 해결:
  - 키의 계약은 언제나 `_contract_category()` 결과(분류 코드)로 통일한다.
  - 계약 명사는 같은 문장 안에서 당사자 앞뒤 어느 쪽이든 찾는다. 결합 = 같은 절 안의 (당사자 주어, 지위 + 서술 표지).
- 시험: 계약명 선행·후행·생략(문장에 계약 종류만) 3변형 = 양성. 별개 계약 = 대조(유지).

**Y6. 수량 속성이 없다**
- 원인: 3차 T 시험 범위 '속성 6종 × 3변형'의 수량이 구현·시험 모두에 없다. 금액 정규식만 있어 '개·대·톤·㎡' 수량은 슬롯이 되지 않는다.
- 해결: 수량 슬롯 = 키 (대상 명사 핵심, 단위 문자열) + 값 `숫자 + 바로 뒤 단위 낱말`(숫자 뒤 한글 1~2자 또는 단위 기호를 그대로 단위로 쓴다. 메모 129 조건대로 **단위 목록을 열거하지 않는다**. 금액 단위 '원·만·억'과 날짜·시각·조문 표지는 제외) + 확정 서술(Y1과 같은 결합). 단위가 다르면 비교하지 않는다. '총'은 선택 표지. 부분 표지(그중·일부·나머지·추가로)는 뺀다. 합계 검산은 `calculation.py` 몫이다.
- 시험: 수량 충돌 3변형 = 양성. 부분 인도·추가 납품 = 대조.

**Y7. 산식 확장이 통화 없는 수에도 켜진다 (`calculation.py` 143~145행, 224~240행)**
- 원인: `has_large_number`(1000 이상) 또는 쉼표만으로 '수 × 수'를 금액 산식으로 계산한다. 우변 숫자도 단위 없이 금액으로 읽는다. 평가 측 확인: '2,024 × 3'이 산식 값 6,072가 되고, 면적 '…제곱미터' 산식이 금액 행으로 잡힌다. 은퇴 항목을 잡는 데 필요한 조건(쉼표 수 × 정수 = 원 단위 결과)보다 넓다.
- 해결: 통화 표지가 없는 산식은 **같은 행 좌우 어디든 통화(원·₩·천·만·억)가 있거나 열 머리가 `AMOUNT_HEADER_RE`일 때만** 계산한다. `has_large_number` 단독 조건은 지운다. 우변의 단위 없는 숫자도 같은 조건에서만 금액으로 읽는다.
- 시험: 면적·치수·연도 꼴 = 산식 결과 없음. 쉼표 수 × 정수 = 잘못 적힌 원 금액 = 양성(현행 시험 유지).

**Y8. 그 밖의 정리**
- 상대 날짜(T6): 같은 단락이 원칙이다. 단락 첫 문장의 상대 날짜(같은 날·당일)는 **바로 앞 단락의 마지막 절대 날짜**까지 잇는다(한 단락까지만). 평가 측 3차 지시가 '같은 단락'으로만 적어 단락이 바뀌는 흔한 꼴을 놓쳤다(평가 측 지시 보완).
- 한글 수사: '삼천만 원'을 10,000,000으로 읽는다(`_parse_sub_chunk` 194행~, 한글 숫자 미처리). 일·이·삼…구를 숫자로 바꾼 뒤 단위를 계산한다.
- PR 본문에 Y1~Y9·T1~T9 대응표, 득점 귀속표, T9 원인표(은퇴·train EVI-INCONS 미득점, 단계별 건수, 문장 인용 금지)를 낸다.

**Y9. 시험 삭제 승인 절차 (push 실행 `check_test_edits` 실패)**
- 원인: `test_evi_incons_internal.py`의 옛 시험 15개(산식 양성 3, 지위·조항 양성 2, 대조 1~10)가 이름이 바뀌거나 지워졌다. 내용은 대부분 새 이름 시험으로 옮겨졌다(평가 측 확인: 대조 1~8·지위·조항은 새 이름 시험 존재, 대조 9는 T2 3꼴, 대조 10은 T1 대조). 산식 양성 3개 삭제는 T1이 요구한 것이다. 그러나 규칙상 삭제·이름 변경은 `docs/handoff/requests/`의 사유 제출과 평가 측 승인이 먼저다.
- 해결: `docs/handoff/requests/`에 '옛 시험 → 새 시험' 대응표(15행)를 올린다. 평가 측은 산식 양성 3개 삭제(T1, `calculation.py` 쪽 시험 3개로 이전)와 이름 변경 12개를 그 대응표가 맞으면 승인한다. Y3로 `_INCIDENT_DATE_EXCLUDE_RE`를 지워도 사고일·치료일 대조 시험은 그대로 통과해야 한다.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공(기존 산식 시험 포함).
- 평가 측이 새로 짓는 비공개 탐침과 지난 3·4차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- B-3 득점은 산식을 뺀 규칙의 귀속분만 센다.
- Y1~Y9 외에 새 속성·새 낱말 목록을 더하지 않는다. 목록으로 막던 곳(후속 사건 낱말)은 구조 규칙으로 바꾼다.

### B-3 5차 보완 지시 (#167 `ae5c060` 보완 — 수용 직전, 10-25) — 원인별 해결 방안
Y1~Y5·Y7~Y9가 반영돼 **정상 대조 오탐이 6/12에서 0으로 줄었다.** 지난 3·4차 세트와 새 5차 세트 모두 양성 2/3 이상, 오탐 0이다. 탐침 기준을 처음 충족했다. 남은 것은 **Y6 수량이 메모 129 조건과 Y6 지시를 어긴 점**(단위·대상 명사를 닫힌 목록으로 열거)과, 그 때문에 생기는 놓침이다. 아래 Q1~Q3만 고친다. **이것만 고치면 평가 측 새 탐침 확인 뒤 수용한다.** 줄 번호는 `ae5c060`의 `packages/claim_engine/internal_inconsistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·train 37.5/37.5/37.5/36.5 변화 0. 은퇴 09 48.3→50.0(`EVI.INCONS_LOC_EXCLUSIVE`, 장소 규칙), 08·08b·10 불변, 하락 0, 오탐·A등급 0. 4차의 은퇴 10 금액 부분 점수는 Y1로 확정 서술 조건을 되살리면서 사라졌다(예상대로).
- 탐침(문장 비공개):
  | 세트 | 양성 | 정상 대조 오탐 |
  |---|---|---|
  | 3차 | 4/6 | 0/10 |
  | 4차 | 4/6(직전 4/6) | 0/12(직전 6/12) |
  | 새 5차 | 5/6 | 0/12 |
  - 놓친 꼴: 수량 충돌 3세트 모두, 과거형 확정 서술('…원이었습니다'), 관형형 사건 술어('일어난').
- 시험: 관련 시험 통과(평가 측 재실행). CI(인용): PR·push 실행 필수 검사 모두 성공.
- Y9 시험 이전 사유서(requests/130): 평가 측 승인. 대응표 14·15행의 새 시험 이름이 실제와 다르다(`_disputes`·`_recants`·`_no_arithmetic_mismatch_in_b3`가 맞다). 사유서만 고친다. 승인 목록(`approved_test_marks.json`)은 평가 측이 등록했다.

**Q1. 수량 단위가 닫힌 목록이다 (`_QUANTITY_RE` 229~231행)**
- 원인: 단위를 `개|대|톤|평|㎡|m²|명|필지|건|통|권|장|박스|상자|포대`로 열거했다. 메모 129 조건('수량 단위 열거 금지')과 4차 Y6 해결('단위 목록을 열거하지 않는다')을 어긴다. 목록 밖 단위(kg·리터·벌·켤레·그루 등)는 놓치고, 목록 안 '장·통·건'은 '장소·통지·건물' 같은 낱말 앞부분과 겹칠 위험이 있다(뒤 조건으로 일부만 막힌다).
- 해결: 숫자 바로 뒤의 단위 토큰을 **구조로** 잡는다: `(?P<num>…)\s*(?P<unit>[가-힣]{1,2}|[A-Za-z㎡㎏ℓ²³]{1,4})(?=조사|서술 표지|공백·문장부호)`. 그다음 **제외 규칙**만 둔다: 금액 단위(원·만·억·천), 날짜·시각(년·월·일·시·분·초), 조문·순번(조·항·호·차·번·회), 비율(%·퍼센트·배). 제외는 '열거'가 아니라 다른 속성(금액·일시·조문)으로 이미 처리하는 단위를 빼는 것이다.
- 시험: 목록 밖 단위 2종(구현 측이 고른다) 충돌 = 양성. 조문·순번·비율 수 = 슬롯 없음.

**Q2. 수량 대상 명사가 닫힌 목록이다 (736~739행 `m_tn`)**
- 원인: 대상 명사를 `차량|자동차|기계|장비|물품|제품|자재|목적물|토지|건물|필지|면적|인원|인력`의 접미로만 찾는다. 목록 밖 대상 명사는 슬롯이 되지 않는다(평가 측 확인: 3세트의 수량 양성이 모두 이 때문에 빠짐). 이것도 낱말 목록이다.
- 해결: 대상 = 같은 절에서 수량 앞의 **주제·주어·목적어 명사구**(`X(은|는|이|가|을|를|의)`)의 핵심 명사다. 지시어(위·이 사건·해당)는 직전 대상으로 푼다(T3와 같은 방식). '수량·개수·물량'처럼 속성 이름 자체가 머리 명사이면 그 앞 `X의`의 X를 대상으로 쓴다('위 [X]의 인도 수량' → X). 당사자 호칭은 대상이 아니다.
- 시험: 목록 밖 대상 2종 충돌 = 양성. 서로 다른 대상의 수량 = 대조.

**Q3. 확정 서술과 사건 술어의 활용형 (`_DEFINITIVE_PREDICATE_RE` 190~192행, `_QUANTITY_RE` 뒤 조건, `EVENT_PREDICATE_MAP` 220~226행)**
- 원인:
  - 확정 서술이 '이다·입니다·으로 정하…'뿐이라 과거형 '…이었습니다·…였다'를 놓친다(평가 측 확인: 금액 '…원이었습니다' 불일치).
  - 수량 뒤 조건도 '임·이다·입니다'만 받아 '…개였습니다'를 놓친다.
  - 사건 술어가 '일어나'만 있어 관형형 '일어난'(받침 결합)을 놓친다.
- 해결: 확정 서술 = `(?:이|였|이었)?(?:다|습니다|음)|으로\s*(?:정하|약정|합의|기재|명시)` 계열로 어간+어미 결합으로 만든다. 사건 술어는 '일어나|일어난|일어났|났|난'처럼 받침 결합형을 함께 둔다(4차 Y3의 닫힌 사전 안에서 활용형만 보탠다).
- 시험: '…원이었습니다' 금액 충돌, '…개였습니다' 수량 충돌, '…가 일어난 [날짜]' 날짜 충돌 = 양성.

**제출물**
- Q1~Q3 대응표, PR 본문의 Y1~Y9·T1~T9 대응표·득점 귀속표·T9 원인표(아직 PR 본문에 없다), requests/130 대응표 이름 정정.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 다시 새로 짓는 비공개 탐침과 지난 3~5차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- Q1~Q3 외에 새 속성·새 낱말 목록을 더하지 않는다. 단위·대상은 목록이 아니라 구조로 잡는다.

### B-3 6차 보완 지시 (#167 `853ad02` 보완 — 수용 직전, 10-25) — 원인별 해결 방안
Q1~Q3가 반영됐다. 수량 단위·대상 명사의 닫힌 목록이 구조 규칙으로 바뀌었고, 지난 3세트는 양성 17/18·오탐 0/34다. 사유서 130 정정도 확인했다. 그러나 평가 측이 새로 지은 6차 세트에서 **오탐 1건과 놓침 1건**이 나왔다. 원인은 셋이다. 그중 QQ2는 **평가 측 Q3 지시의 결함**이다(확정 서술 정규식의 앞부분을 선택으로 둬서, 아무 '-다·-습니다'나 확정 서술로 맞게 했다). 아래 QQ1~QQ3만 고친다. **이것만 고치면 평가 측 새 탐침 확인 뒤 수용한다.** 줄 번호는 `853ad02`의 `packages/claim_engine/internal_inconsistency.py` 기준이다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·train 변화 0. 은퇴 09 48.3→50.0(`EVI.INCONS_LOC_EXCLUSIVE`), 10 43.9→44.3(`EVI.INCONS_INTERNAL_QUANTITY`, 부분 점수), 08·08b 불변, 하락 0, 오탐·A등급 0.
  - **은퇴 10의 수량 득점은 B-3 득점으로 세지 않는다.** 평가 측이 QQ1·QQ2만 고친 임시 변형으로 다시 재면 그 득점이 사라진다. 결함 위에서 난 득점이다. 09의 장소 득점은 그대로 남는다.
- 탐침(문장 비공개):
  | 세트 | 양성 | 정상 대조 오탐 |
  |---|---|---|
  | 3차 | 5/6 | 0/10 |
  | 4차 | 6/6 | 0/12 |
  | 5차 | 6/6 | 0/12 |
  | 새 6차 | 7/8 | **1/12** |
  - 오탐 꼴: 서로 다른 일의 인원 수('[명사] [N]명과 [다른 동사]' 꼴)가 같은 대상의 수량 충돌로 잡힘.
  - 놓친 꼴: '[대상]은 모두 [N][단위]입니다'(전칭 부사가 대상으로 잡힘, 3차 세트의 수량 놓침도 같은 원인).
  - 평가 측 임시 변형(QQ1·QQ2만 고침): 4세트 오탐 모두 0, 6차 양성 6/8(기존 이행 동사 밖의 동사를 쓴 목적어 꼴 1건 추가 놓침, 기준 2/3은 충족).
- 시험: 관련 시험 통과(평가 측 재실행). CI(인용): PR·push 실행 필수 검사 모두 성공.

**QQ1. 단위 토큰이 조사까지 삼킨다 (`_QUANTITY_RE` 229~233행)**
- 원인: 단위가 `[가-힣]{1,2}?`(1~2자)라서, 뒤 조건(조사·서술 표지·공백)을 맞추려고 '명과'처럼 **단위 + 조사**를 두 글자 단위로 잡는다(평가 측 확인: '5명과' → 단위 '명과'). 두 문장에 같은 '명과'가 있으면 같은 키가 된다.
- 해결: 단위 토큰을 잡은 뒤, 두 번째 글자가 조사(`과|와|을|를|이|가|은|는|에|의|로|도|만`)이면 한 글자 단위로 줄이고 그 글자를 뒤 조건 쪽으로 넘긴다. 단위 뒤 허용 조사에 `과|와|도|만`을 더한다.
- 시험: '[N]명과', '[N]개를', '[N]대가' 꼴에서 단위가 한 글자로 잡히는지 단위 시험.

**QQ2. 확정 서술이 문장 뒤 아무 '-다'에나 맞는다 (`_QUANTITY_DEFINITIVE_RE` 248~250행, `_DEFINITIVE_PREDICATE_RE` 190~192행)**
- 원인: 평가 측 Q3 지시대로 `(?:이|였|이었)?(?:다|습니다|입니다|음)`을 넣었는데 앞부분이 선택이라, 수량·금액 뒤 30자 안의 **아무 동사 종결**(값과 무관한 다른 동사)이 확정 서술로 맞는다(평가 측 확인: '[N]명과 [다른 동사]하였습니다'의 확정 서술 참). 그래서 값을 확정하는 문장이 아닌데도 슬롯이 된다. 금액 쪽 `_DEFINITIVE_PREDICATE_RE`도 같은 꼴이다(이번 탐침에서 금액 오탐은 없었지만 같은 원인이 남아 있다).
- 해결: 확정 서술은 **값 바로 뒤에 붙는 서술**만 인정한다(`re.match`로 앞에서부터, 공백만 허용).
  - 계사: `(?:이|였|이었)(?:다|습니다|음)|입니다|이다|임`.
  - 확정 동사: `(?:으)?로\s*(?:정하|약정|합의|기재|명시)`.
  - 목적어 + 이행 동사(수량): 현행 `(?:을|를)\s*(?:공급|납품|매매|인도|보유)` 그대로(값이 그 동사의 목적어인 꼴). 동사를 늘리지 않는다.
- 시험: '[N]명과 [다른 동사]하였습니다' = 슬롯 없음. '[N][단위]이었습니다·입니다', '[N][단위]를 납품하였다' = 슬롯.

**QQ3. 전칭 부사가 수량 대상으로 잡힌다 (`_extract_quantity_target` 296행 `m_direct`)**
- 원인: 2단계 '수량 바로 앞 명사'가 '모두·총·전부·약' 같은 **부사·관형사**도 2자 이상이면 대상으로 받는다(평가 측 확인: '[대상]은 모두 [N][단위]입니다' → 대상 '모두'). 그러면 같은 대상의 다른 문장과 키가 달라져 충돌을 놓친다.
- 해결: 수량 앞 토큰이 수량 수식 부사·관형사(`모두|총|전부|약|합계|도합|무려|겨우|최소|최대`)이면 그 토큰을 건너뛰고 그 앞 명사구(3단계 주제·주어·목적어)로 대상을 정한다. 이 묶음은 내용어가 아니라 문법 범주(수량 수식어)로 둔다.
- 시험: '[대상]은 모두 [N][단위]입니다' + '위 [대상]의 [속성] 수량은 [M][단위]였습니다' = 양성.

**제출물**
- QQ1~QQ3 대응표, PR 본문의 득점 귀속표(은퇴 10 수량 득점이 QQ1·QQ2 뒤에도 남는지 명시), T9 원인표.

**수용 기준(변경 없음)**
- 고정·은퇴 하락 0, 오탐·A등급 증가 0, 필수 CI 성공.
- 평가 측이 다시 새로 짓는 비공개 탐침과 지난 3~6차 세트 모두에서 양성 2/3 이상, 정상 대조 오탐 0.
- QQ1~QQ3 외에 새 속성·새 낱말 목록을 더하지 않는다.

### B-3 6차 보완 지시 부록 — 평가 측 사전 검증 결과 (#167, 10-25)
평가 측이 6차 지시 QQ1~QQ3를 `853ad02` 사본에 그대로 적용해 검증했다. **지시대로 하면 수용 기준을 충족한다.** 구현 시 아래 두 점만 지킨다.

**검증 결과(평가 측 사본)**
- 탐침 3~6차: 양성 6/6·6/6·6/6·7/8(합 25/26), 정상 대조 오탐 0/46.
- 기존 시험: `tests/test_evi_incons_internal.py`·`tests/test_calculation_leading_multiplier.py` 전부 통과.
- 세트: 고정 82.6/81.9, 은퇴 09 50.0(장소, 유지)·10 43.9(결함 위 수량 득점 소멸)·08·08b 불변, 하락 0.

**구현 시 주의(사본 적용 중 확인)**
- QQ1: 단위를 한 글자로 줄였으면, 확정 서술을 보는 `following_q`도 **줄인 단위 바로 뒤**(`q_m.start("unit") + len(u)`)부터 잘라야 한다. 지금처럼 `q_m.end()`에서 자르면 넘긴 조사('를' 등)가 빠져 'N개를 납품' 꼴을 놓친다.
- QQ2: 목적어 + 이행 동사 꼴은 `을`과 `를`을 모두 받는다(`[을를]\s*(?:공급|납품|매매|인도|보유)`). 앞에서부터 맞추도록 `^\s*`로 시작한다.
- 남는 놓침 1건(기존 이행 동사 밖의 동사)은 기준 안이다. 동사를 늘리지 않는다.

### B-3 판정 — 수용 (#167 `a444e51`, 10-25)
QQ1~QQ3가 평가 측 사전 검증 부록대로 반영됐다. **수용한다.** 남은 보완 지시는 없다. 아래 '알려진 미해결'은 이번 PR 범위 밖이며 후속 티켓으로만 남긴다.

**측정 요약**
- 평가 측 재실행: 오프라인, Steve `3b017eb`와 같은 탐지 조건, 항목 단위, train 포함.
  - 고정 82.6/81.9·train 37.5/37.5/37.5/36.5 변화 0. 은퇴 09 48.3→50.0(`EVI.INCONS_LOC_EXCLUSIVE`, 장소 규칙), 08·08b·10 불변, 하락 0, 오탐·A등급 0. 결함 위 수량 득점(은퇴 10)은 사라졌다(예정대로).
- 탐침(문장 비공개):
  | 세트 | 양성 | 정상 대조 오탐 |
  |---|---|---|
  | 3차 | 6/6 | 0/10 |
  | 4차 | 6/6 | 0/12 |
  | 5차 | 6/6 | 0/12 |
  | 6차 | 7/8 | 0/12 |
  | 새 7차 | 6/8 | 0/12 |
  - 사전 검증 사본 결과(3~6차 25/26·0/46)와 같다.
- 시험: `tests/test_evi_incons_internal.py`·`tests/test_calculation_leading_multiplier.py` 전부 통과(평가 측 재실행). CI(인용): PR·push 실행 필수 검사 모두 성공.
- B-3 득점 귀속: 은퇴 09 1항목(장소 규칙). 산식 득점 0(T1대로 `calculation.py`로 분리).

**알려진 미해결(known_open, 후속)**
- 서명자 규칙의 대상 문서가 `_EXHIBIT_TARGET_RE`(159~161행)의 문서 명사(계약서·확인서·동의서·각서·합의서)에 묶여, 그 밖의 처분문서(약정서 등) 단독 서명 충돌을 놓친다.
- 수량의 '값 + 목적어 + 이행 동사' 꼴은 기존 이행 동사(공급·납품·매매·인도·보유) 밖이거나 사이에 부사어가 끼면 놓친다.

**병합 전 확인**
- 사용자 병합 지시('#167병합') 뒤 평가 측이 병합 커밋(merge commit)으로 Steve에 넣는다. 시험 이전 승인 목록(`approved_test_marks.json`, requests/130)은 평가 PR로 Steve에 들어간다.

### C-1 TK-84 / C-2 TK-78 / C-3 TK-82
- 각 티켓 요구대로 구현한다. 탐지 diff 0, 점검표 1·3항.
- TK-78: 새 네트워크 호출을 만들지 않고 기존 `LookupTrace`·판정별 `source_lookup`을 모은다. 질의어·URL·인용 원문·키는 넣지 않는다.
- TK-82: 동기화 예산이 남을 때만 1회 재시도한다. 4xx·크기 상한·예산 소진은 재시도하지 않는다. `httpx.MockTransport` 시험 4종을 둔다.

### D-1~D-4 화면 개편 (사용자 개선안)
- **공통:** 탐지 diff 0, 고정·은퇴 점수 불변. 서버 측 시험은 바꾸지 않는다(TK-87의 보고서 점검 조건만 예외). 고친 화면 시험마다 '전에 확인하던 요구 → 새 시험의 확인 위치' 대응표를 PR에 낸다. 확인하던 요구가 하나라도 빠지면 불수용이다.
- API·DB 표(`document-relations`·`compare`·`search`·`calculations`·`finding_workflows`)는 이번에 지우지 않는다. 화면에서 부르지 않게만 한다.
- **보고서에서 사건 일지를 뺀다(사용자 결정 10-19):** 보고서의 '검증 상세(JSON)'·Excel '기술부록'·보고서 스냅숏에서 `timeline`을 제외한다. 날짜 분석 엔진과 실행 결과 JSON(`to_payload`, 채점기 입력)의 `timeline`은 그대로 둔다(TK-86 요구 2).
- **기존 시험 수정은 승인됐다(사용자 10-19).** 조건: 위 대응표 제출, 서버 측 시험 유지(TK-86 보고서 내보내기·TK-87 보고서 점검 조건만 예외), 고친 시험은 평가 측이 `approved_test_marks.json`에 올린다.
- '확인이 필요한 내용' 요약(TK-87)은 기존 결과 필드만 조합한다. 새 모델 호출·근거 없는 문장 생성은 금지다.
- 순서: D-1·D-2·D-3을 먼저, D-4는 D-3 병합 뒤 설계 메모부터. D-4는 결과 유형·등급·상태를 바꾸지 않고 화면 배치만 바꾼다. **채점기·`match_spec`은 바꾸지 않는다.**

### E-1 TK-83 (설계 메모 먼저)
- 엇갈린 항목만 세 번째 공급자로 보내도 최종 항목별 판정이 지금과 같아지는 규칙, 완결성 검사와의 관계, 실패·잘림 처리, 호출 수 예상을 메모로 낸다. OFF(`all`)·`off` 모드 동작은 바꾸지 않는다.

## 4. 그 뒤
- #123 잔여(공식 통계 표시, `legal_engine`→`claim_engine` 경계), known_open TK-44/49·45·55·73, Drive 주장 상한 변경, EVI-LOGIC(은퇴 0/10, 모델 의존 여부 확인 필요)은 근거가 생긴 뒤 설계 메모로 다룬다.
- 금지는 그대로다: 산식·병기 검사 병렬 신설, SRC-UNV `.invalid` 규칙, 채점기·match_spec 변경.
- 운영 관찰(평가 측): ON 상태 운영 실행의 실패·잘림·비용, 하위 파일 내려받기(TK-80 잔여). 결함이 나오면 원인 유형별 티켓으로 이 문서에 넣는다.

## 5. 공통 제출 점검표
탐지를 바꾸는 PR은 1~7항, 그 밖은 해당 항목만 낸다. 해당 없으면 사유를 적는다. **수치는 반드시 PR을 올리는 그 head로 잰다**(#126에서 본문 수치가 실측과 여러 번 달랐다).

| # | 조건 | PR에 첨부 |
|---|---|---|
| 1 | 실제 진입점(`parse_document`→`VerificationPipeline.run`) 시험 1개 이상. 결과 개수·내용까지 확인(`>= 1`만 보는 시험 불인정) | 시험 이름 |
| 2 | 새 정규식·분석 경로마다 길이 1배·4배 각 3회, 최솟값 비 < 8, 4배 최솟값 < 1초. 반복 안의 반복(`(…+)*`) 금지 | 경로·측정값·재현 명령 |
| 3 | 보고 수치는 재현 명령과 출력을 그대로 | 명령·출력·최종 SHA·환경 |
| 4 | 은퇴 4세트와 고정 dev·holdout 전후 점수표 | 기준·후보 SHA, 점수·재현율·오탐·A등급 |
| 5 | train 해당 유형의 전후 재현율(`scripts/eval_testset.py`) | 유형·분모·전후 |
| 6 | 일반화: 은퇴 4세트·dev·holdout의 **같은 유형 항목** 득점 전후. train에서만 오르거나 **평가 세트 문구 일치로만 오르면 불수용** | 세트별 항목 수·전후 득점 |
| 7 | 원문 대조: `python scripts/check_train_phrase_overlap.py --base origin/Steve_ACASiaLAW --corpus-text <train 텍스트>` | 출력 전문 |

**PR 전에 직접 돌릴 것 (한 줄 명령, 사용자 승인 10-18)**
```
python scripts/precheck_pr.py --tests <바꾼 기능의 시험 파일>
```
- 고정 점수 게이트, 은퇴 4세트 비교, 회귀·수용·TK-73 시험, 평가 세트 문구 대조를 CI와 같은 순서로 돈다.
- **빠른 반복(TK-125, 10-24 반영):** `python scripts/precheck_pr.py --quick --tests <시험 파일>`는 게이트·문구 대조·지정 시험만 돈다(약 20초). 은퇴 비교의 기준 집계는 로컬에서 캐시돼 두 번째부터 절반쯤 걸린다. `--quick` 요약을 PR에 붙이면 같은 head의 CI '은퇴 세트 비교'·'테스트' 성공을 함께 적는다. 출력 끝 '요약'을 PR 본문에 붙인다. 하나라도 실패면 PR을 올리지 않는다.
- **평가 세트 문구 대조는 CI에서도 자동으로 돈다**(점수 하락 게이트 잡의 '평가 세트 문구 대조'). 은퇴·고정 세트 정답지 문장과 같은 문구를 새로 넣으면 실패한다. 일반 법률 표현이라 판단되면 PR에 근거를 적는다. 평가 측이 확인해 허용 목록에 올린다.
- 릴리스 기준: 0.13.1과 같은 조건으로 함께 재어 고정 dev·holdout 합계가 올라야 한다(예외 없음, 2절). 표시 보강은 상승 근거로 세지 않는다.
- 평가 측은 릴리스 판정에서 은퇴 세트 **항목 단위** 회귀(오른 항목·내린 항목)를 함께 본다.
- 표시 보강(발췌·문맥을 붙여 채점 토큰이 맞게 된 것)은 탐지 개선과 나눠 적는다.

## 6. 보고와 판정
- **판정 전달 방식(2026-10-24 사용자 지시):** 평가 측은 PR마다 측정·판정이 끝나는 즉시 그 PR의 보완 지시를 전달한다(다른 PR을 기다리지 않음). 받은 PR부터 바로 보완을 시작한다. PR 코멘트와 이 문서 3절이 같은 내용이다.
- 보고는 PR 코멘트 3줄(바꾼 것·남은 것·'검토 요청' + `git rev-parse HEAD` 출력)과 위 표.
- 평가 측은 '검토 요청'이 있고 CI가 끝난 SHA만 판정한다. 수용은 다음 중 하나 이상을 입증하고, 회귀 0·하드코딩 0을 지킨 경우다.
  - (가) 기존 점수 상승: 같은 유형 항목이 train뿐 아니라 은퇴·고정 세트에서도 오른다.
  - (나) 새 기능: 실제 진입점 시험으로 동작을 보인다.
  - (다) 사용자 지시 사항 개선: 지시와 증거를 대응시킨다.
- 같은 접근이 두 번 실패하면 세 번째 전에 설계 메모를 다시 낸다.
- 사용자 PC·브라우저 실행은 따로 배정받은 경우에만 한다. 유료 호출, 운영 설정 변경, 배포는 하지 않는다.

## 2-17. TK-76 3주기 남은 유형 착수 — EVI-FORM 설계 메모 요청 (11-05, 사용자 'TK-76 남은 유형의 착수를 claude 제안대로 시행')

- 순서(평가 측 제안·사용자 승인): EVI-FORM → EVI-NUM(TK-73 조율) → EVI-DATE → EVI-COPY → EVI-LOGIC 잔여 → EVI-INCONS C. 근거는 Steve `90cc681` 은퇴 5세트 유형별 손실(오프라인 집계): EVI-FORM 9.3 · EVI-NUM 7.8 · EVI-DATE 6.0 · EVI-COPY 6.0 · EVI-LOGIC 3.7. EVI-OVR 잔여 4꼴은 다음 주기.
- 평가 측 시안 사본(저장소 밖, `8f336b0`)과 그 증분 [patches/TK-76_cycle3_form_prototype_on_90cc681.diff](patches/TK-76_cycle3_form_prototype_on_90cc681.diff)는 참고용이다(독립 4차 탐침 5/8로 2/3 미달).

```
[평가 측 설계 메모 요청 — TK-76 3주기 EVI-FORM(서증 형식 결함) 구조 규칙, 기준 Steve 90cc681, 11-05]

순서(평가 측 제안, 사용자 승인 11-05): EVI-FORM → EVI-NUM(TK-73과 조율) → EVI-DATE → EVI-COPY → EVI-LOGIC 잔여 → EVI-INCONS C(발신 시각). 근거: Steve 90cc681 은퇴 5세트 유형별 손실(오프라인, 집계) EVI-FORM 9.3(12항목·획득 2.7) · EVI-NUM 7.8 · EVI-DATE 6.0 · EVI-COPY 6.0 · EVI-LOGIC 3.7. 한 유형씩, 메모 PR → 구현 PR. 이번은 EVI-FORM 메모 PR이다.

1. 진단 (평가 측 재실행)
- 현재 경로: packages/claim_engine/evidence_consistency.py check_evidence_form_defects(2284행~)의 4개 축(205~292행 정규식: 자리표시·미제출 자인·필수 기재 공란·판독 불가)과 check_statements(1655행, 서명 생략). 모두 '정해진 낱말 + 정해진 술어' 일치라서 같은 결함을 다른 말로 쓰면 놓친다.
- 평가 측 새 비공개 탐침 4세트(문장 비공개, 합 양성 34·대조 38), 기준 Steve 90cc681: 양성 3/34 · 대조 오탐 0/38.
- train: 이 평가 환경에 원본이 없어 미측정. b68 진단(requests/82): train EVI-FORM 40항목 전부 0.25 부분 점수(구체 결함 경로 없음).

2. 법적 근거 (법제처 현행 원문 확인: 민사소송법 MST 290113 시행 2026-10-02, 민사소송규칙 MST 291043 시행 2026-10-12)
- 민사소송법 제277조(외국어 문서에는 번역문을 붙여야 한다), 제355조 제1항(원본·정본·인증 있는 등본으로 제출), 제358조(본인·대리인의 서명·날인·무인이 있으면 진정 추정).
- 민사소송규칙 제105조 제1항(문서의 제목·작성자·작성일을 밝힘, 기재상 명백하면 예외)·제3항(사본은 명확해야 함)·제4항(일부를 증거로 해도 전부 제출, 허가 시 초본), 제106조 제2항(국어 아닌 문자 → 번역문), 제107조 제2항(원고 "갑", 피고 "을", 독립당사자참가인 "병"), 제109조 제3호·제5호(번역문 미첨부, 작성자·작성일 불명 → 채택하지 않을 수 있음).
- 판정 강도: 모두 SUSPICIOUS·B. '진정 추정을 받지 못함·채택하지 않을 수 있음'이지 위조·무효 확정이 아니다. CONTRADICTED·A로 내지 않는다(기존 4개 축의 상태는 바꾸지 않는다).

3. 구조 규칙 후보 (메모에서 각각 구조·제외 조건·법 근거를 정한다)
G1 번역문 미첨부 — 자기 측 입증방법 행의 서증명이 국어 아닌 문자로 된 것(한글 글자 수 대 라틴·한자·가나 글자 수 비율), 같은 호증의 다른 가지번호 행·같은 행·본문에 번역 표지가 없을 때. 대조: 한글 서증명 속 영문 회사명·약칭·규격명, 번역 가지번호가 있는 것.
G2 자기 입증방법의 부호 불일치 — 작성 당사자(서명 줄·표제)가 원고인데 입증방법 행이 모두 '을'(피고면 모두 '갑'). 대조: 본문에서 상대방 호증을 원용·탄핵하는 문장(입증방법 밖), 섞인 목록(번호 문제는 EVI-NUM·TK-73 몫).
G3 진술·확인 문서의 서명·작성일 칸 공란 — 표제가 확인서·진술서·경위서·각서인 문서에서, 서명 줄이 '이름 칸 라벨 + (빈칸·밑줄) + (서명/인/날인)'으로 이름이 비어 있거나, 날짜 줄이 연도 뒤 월·일이 빈칸. 대조: 가림 표기(○○)는 공란이 아니다, 이름·날짜가 채워진 것, 전자제출 서면의 서명 생략(기존 check_statements 제외 조건 유지).
G4 형식 요소 부재·불능 자인 + 증명 주장 — 한 문장에서 양보 연결(-(으)나·-지만·-더라도·-는데도) 앞 절이 '그 서증의' 형식 요소(작성 명의·작성일·서명/날인·원본·판독 가능성)가 없거나 불능이라고 하고, 뒤 절이 그 서증으로 증명된다고 한다. 소유 연결은 앞 절에 자기 호증 표지가 있거나 그 호증 서증명의 핵심어가 있을 때만. 대조: 서증과 무관한 사실을 모른다는 양보(평가 측 재현: 이 연결이 없으면 오탐), 상대방 증거 탄핵, 원본 지참·추완 예정(기존 _EVI_FORM_NON_DEFECT_CONTEXT_RE 등 유지).
G5 일부 쪽만 제출(규칙 105조 4항) — 미검증. 허가 여부를 서면에서 알 수 없으므로 낼지, 낸다면 '허가 확인 필요' 안내로만 낼지 메모에서 정한다.

4. 평가 측 시안과 그 한계 (참고용, 그대로 쓰지 않는다)
- 시안: docs/handoff/patches/TK-76_cycle3_form_prototype_on_90cc681.diff(evaluator/round8-promotion) — G1~G4를 check_evidence_form_structure 하나로 붙인 것.
- 결과: 1차(시안과 함께 지음) 0/8→7/8·대조 0/8. 2·3차(독립, 그 뒤 시안 보정에 씀) 1/10→10/10·0/10, 1/8→7/8·0/10(보정 전 5/8·오탐 1). 4차(독립, 보정 안 함) 1/8→5/8·0/10 — 2/3 미달. 은퇴 5세트·고정 dev 82.6·holdout 81.9 변화 0·오탐 0, 관련 20개 파일 654건 통과, 하드코딩 점검 통과.
- 4차에서 남은 꼴(문장 비공개): (가) 양보 어미·불능 술어를 활용형으로 열거해 다른 활용('-드나' 꼴 등)을 놓침, (나) 형식 요소를 낱말로 열거해 '(…한) 사람의 이름' 꼴·다른 훼손 동사를 놓침, (다) 서증명 핵심어 추출이 접미어(…본 등)를 떼지 못해 소유 연결 실패. → 메모에서 어간·어미를 낱말 목록이 아니라 구조(어간 + 연결 어미, '-기 어렵/힘들', '-ㄹ 수 없', '-지 않/못', 상실 동사)로 정하고, 형식 요소는 법정 요소 범주(규칙 105조 1항·법 358조·355조)로 정한다. 기존 _CONCESSIVE(65행) 재사용 검토.
- 3차 남은 1건: 소명방법의 '소갑' 목록 줄이 exhibit_rows에 행으로 잡히지 않고, '채권자 성명 (인)' 서명 줄을 작성 당사자로 읽지 못함(공용 입력). 또 공용 _EXHIBIT_SECTION_HEAD_RE(446행)에 '증거방법' 머리가 없다. 1절('공용 입력을 바꾸지 않는다')대로 공용 결과는 바꾸지 말고 새 검사 안에서 복사본으로 구역·당사자를 정한다(시안의 _form_section_rows). 공용을 바꾸려면 메모에서 영향(TK-73 시험 포함)을 재고 따로 승인받는다.
- 시안 정규식에는 인접 수량자(\s{2,}\s* 등)가 있다. 구현은 CodeQL py/redos를 피하는 꼴로 쓴다(TK-139 J15 사례).
- 평가 세트 문구 점검은 상세 문구의 '민사소송법 제'·'민사소송규칙 제'를 의심으로 띄운다. 일반 법령명 인용이므로 평가 측이 허용한다 — PR 본문에 적는다.

5. 메모 PR 제출물
- 규칙별: 구조 정의(낱말 목록이 아니라 꼴), 법 근거 조문, 제외 조건, 상태·등급, 기존 4개 축과의 관계(같은 호증 중복 판정 1건으로 — 시안은 공란 축과 G4가 같은 호증에 둘 다 냈다), 공용 입력 불변 방법.
- 규칙별 공개 합성 양성 3·대조 3 이상(평가 측 탐침·train·평가 세트 문장 금지, 2-2), 변형 시험 계획(어순·연결 어미·같은 꼴 다른 낱말).
- train 측정 계획: EVI-FORM train 전후 재현율·분모·SHA·같은 조건, 미득점 원인 건수표(문장 인용 금지).

6. 수용 기준(구현 PR)
- 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 4세트 하락 없음.
- 은퇴·고정 하락 0·오탐 0, 관련 기존 시험(위 20개 파일 654건) 통과, verify_all 전체(탐지 엔진 변경), CodeQL 게이트 성공, 2-2 다 제출물(귀속표·train 원인표 건수).
```

### 2-17-1. #234 EVI-FORM 설계 메모 판정 — 보완 1회 (11-05, head `5ad160d`)

- 평가 측 사본 `0c149f5`(시안 + M4·M5)로 사전 검증. 시안 증분 갱신: [patches/TK-76_cycle3_form_prototype_on_90cc681.diff](patches/TK-76_cycle3_form_prototype_on_90cc681.diff).

```
[평가 측 판정 — #234 TK-76 3주기 EVI-FORM 설계 메모 (head 5ad160d, 기준 Steve 90cc681), 11-05]

판정: 보완 1회(메모 고침 커밋). 구조(G1~G4, G5 제외, 공용 입력 불변, ReDoS 방지, 2-2 다 계획)는 요청과 맞다. 아래 M1~M7을 메모에 반영하면 승인하고 구현 PR로 넘어간다. 메모만 바뀌는 PR이므로 제품 시험은 해당 없음.
- CI 결과 인용: 필수 확인 전부 성공.
- 평가 측 재실행(사본 0c149f5 = 지난 시안 + M4·M5 적용, 저장소 밖): 비공개 탐침 1~4차 7/8·10/10·7/8·5/8, 대조 오탐 0 — 지난 시안과 같음. 아래 M2·M4 오탐 재현 2건 해소. 관련 20개 파일 654건 통과, 은퇴 5세트 변화 0·오탐 0. 시안 증분 갱신: docs/handoff/patches/TK-76_cycle3_form_prototype_on_90cc681.diff.

원인과 고칠 것 (절 번호는 메모 기준)

M1 [법령 인용 부정확] 2.1절·3.5절 — 따옴표 속 조문이 원문과 다르다(조 제목 포함). 법제처 현행 원문(평가 측 확인)으로 바꾸거나, 따옴표를 빼고 요지로 적는다.
- 민사소송법 제355조 제1항: "법원에 문서를 제출하거나 보낼 때에는 원본, 정본 또는 인증이 있는 등본으로 하여야 한다." 제358조 제목은 '사문서의 진정의 추정'.
- 민사소송규칙 제105조(문서를 제출하는 방식에 의한 서증신청) ①"문서를 제출하여 서증의 신청을 하는 때에는 문서의 제목ㆍ작성자 및 작성일을 밝혀야 한다. 다만, 문서의 기재상 명백한 경우에는 그러하지 아니하다." ③"제2항의 사본은 명확한 것이어야 하며 재판장은 사본이 불명확한 때에는 사본을 다시 제출하도록 명할 수 있다." ④"문서의 일부를 증거로 하는 때에도 문서의 전부를 제출하여야 한다. 다만, 그 사본은 재판장의 허가를 받아 증거로 원용할 부분의 초본만을 제출할 수 있다." → 3.5절 '법원의 허가'를 '재판장의 허가(사본에 한함)'로.
- 제106조(증거설명서의 제출 등) ②"서증이 국어 아닌 문자 또는 부호로 되어 있는 때에는 그 문서의 번역문을 붙여야 한다. 다만, 문서의 일부를 증거로 하는 때에는 재판장의 허가를 받아 그 부분의 번역문만을 붙일 수 있다."
- 제107조(서증 사본의 작성 등) ②"서증 사본에는 다음 각호의 구분에 따른 부호와 서증의 제출순서에 따른 번호를 붙여야 한다." 1. 원고 "갑" 2. 피고 "을" 3. 독립당사자참가인 "병". ③ 가지부호.
- 제109조(서증에 대한 증거결정) 3호 "국어 아닌 문자 또는 부호로 되어 있는 문서로서 그 번역문을 붙이지 아니하거나 재판장의 번역문 제출명령에 따르지 아니한 때", 5호 "문서의 작성자 또는 그 작성일이 분명하지 아니한 경우로서 이를 밝히도록 한 재판장의 명령에 따르지 아니한 때". → 5호는 재판장 명령 불응이 요건이다. G3·G4 근거 서술을 '명령이 있으면 밝혀야 할 사항이 비어 있음(채택 거부 사유가 될 수 있음)'으로 고친다. SUSPICIOUS·B는 그대로.

M2 [G4 오탐] 3.4절 형식 요소 '작성명의' 꼴 (?:[가-힣]+한)?\s*(?:사람|자|명의)(?:의)?\s*(?:이름|성명)? — 모든 부분이 생략 가능해 '채무자'·'자료'의 '자' 한 글자에 걸린다. 평가 측 재현: 자기 호증에 '채무자의 주소가 적혀 있지 않으나 … 증명' 꼴 → 이 꼴을 넣으면 G4 판정(형식 요소 아님). 고칠 것: 행위 어근과 묶인 꼴만 — 작성자·작성인·명의인·서명자·확인자·진술인, 또는 '(작성|서명|확인|진술|날인)한 사람(의) 이름/성명'. 맨 '자'·'사람' 단독은 쓰지 않는다.

M3 [G4 소유 결속] 3.4절 핵심어 추출 — 한 글자 접미어 '서'·'증'·'본'과 '내역·자료·문서·서류'를 떼면 '계약서→계약', '영수증→영수'처럼 앞 절의 일반 명사와 쉽게 결속한다. 고칠 것: 떼는 것은 제출 형태 표지(사본·원본·출력본·출력물·캡처·사진)뿐, 남은 서증명 전체(2자 이상)가 앞 절에 그대로 있을 때만 결속. 또 6.2절 어순 변형 '[호증 후행형] …문서이기는 하나, 갑 제N호증에 의해…'는 메모 자신의 결속 규칙(앞 절에 표지·서증명)과 충돌하고 6.1 G4 대조 1(사실 부지 양보)과 구조로 구분되지 않는다(평가 측 사본에서 둘 다 미검출 — 규칙대로). 양성 변형에서 빼고, 앞 절 안에서 어순을 바꾸는 변형(서증명 → 형식 요소 / 형식 요소 → 서증명)으로 바꾼다.

M4 [G1 오탐, 평가 측 시안 결함 포함] 3.1절 (C ≥ 3 ∧ H = 0) — 한자만으로 된 서증명을 외국 문자로 본다. 국한문 국내 문서(옛 토지대장·제적등본 같은 이름)도 번역문 미첨부가 된다. 평가 측 재현: 한자 표기 국내 공부 서증명 → TRANSLATION_MISSING. 평가 측 시안도 같은 결함이었다(평가 측 책임). 고칠 것: 한자 단독 이름은 가나가 있거나, KS X 1001 한자 집합(EUC-KR로 인코딩되는 한자) 밖 글자(간체자·일본 신자체 등)가 하나라도 있을 때만 외국 문자로 본다. 라틴 조건은 그대로. 6.1 G1 양성 3(국한문 계약서 이름)은 대조로 옮기고, 간체자·가나 서증명을 양성으로 새로 짓는다. 평가 측 사본에서 탐침 1~4차 변화 없음 확인.

M5 [중복 우선순위가 기존 판정을 바꿈] 5절 — 새 규칙(G4 등)을 기존 축보다 앞에 두면 기존 축 2·4의 CONTRADICTED 판정이 SUSPICIOUS로 대체되어 2.2절 '기존 상태 불변'과 모순되고, 은퇴·고정 득점 경로가 바뀔 수 있다. 고칠 것: 기존 축이 이미 판정한 호증에는 새 규칙을 내지 않는다(새 규칙이 양보). 새 규칙끼리는 메모 순서. check_evidence_form_defects의 서명·seen_exhibits를 바꾸지 말고, check_document에서 기존 결과의 exhibit 집합으로 새 결과를 거른다(평가 측 사본 _form_findings). 사본에서 탐침·654건·은퇴 변화 없음.

M6 [G2 소명 부호] 3.2절은 상대방 부호를 {을}/{갑}으로만 적었는데 6.1 G2 양성 3은 '소을'이다. 상대방 집합을 원고 측 {을, 소을}, 피고 측 {갑, 소갑}으로 적고, 채권자·신청인 → 원고 측, 채무자·피신청인 → 피고 측 대응은 새 검사 안에서만 한다고 적는다.

M7 [작은 것]
- 시험 경로: tests/claim_engine/는 없다. 기존 tests/test_evidence_form_defects.py 옆 tests/test_evidence_form_structure.py로.
- 6.3 귀속표: 규칙 표가 아니라 '규칙 끄기 재측정으로 고정·은퇴·train 득점 변화'를 적는다고 명시(변화 0이면 '세트 득점 0').
- 6.4 train 원인표: 서술 분류 A~D 대신 규칙별 멈춘 단계 건수(목록 행 없음·외국 문자 아님·소유 결속 실패·양보 연결 없음·제외 조건·판정)로.

제출물·수용 기준
- 메모 고침 커밋 1개(제품·시험 코드 0줄). 평가 측이 M1~M7 반영을 확인하면 승인 → Steve 병합(사용자 승인) → 구현 PR.
- 구현 PR 수용 기준은 메모 7.1절 그대로(새 비공개 탐침 2/3 이상·대조 오탐 0, 은퇴·고정 하락 0·오탐 0, 관련 20개 파일 654건, verify_all 전체, CodeQL 게이트, 2-2 다).
```

### 2-17-2. #234 EVI-FORM 설계 메모 2차 판정 — 조건부 승인 (11-06, head `811199b`)

- 평가 측 사본 `ba62f9f`(시안 + M4·M5 + C1·C2)로 사전 검증. 시안 증분 갱신: [patches/TK-76_cycle3_form_prototype_on_90cc681.diff](patches/TK-76_cycle3_form_prototype_on_90cc681.diff).

```
[평가 측 2차 판정 — #234 TK-76 3주기 EVI-FORM 설계 메모 보완본 (head 811199b, 기준 Steve 90cc681), 11-06]

판정: 조건부 승인. M1~M7 반영 확인(법령 원문·제목, 작성명의 어근 결합, 형태 표지만 분리, KS X 1001, 기존 축 우선, 소을·소갑, 시험 경로·귀속표·단계 건수표). 메모는 CI 완료 뒤 Steve 병합 가능. 아래 C1~C3은 구현 PR의 필수 조건이다(구현 PR에서 메모 해당 절도 함께 고친다).
- CI 결과 인용(판정 시점): CodeQL 새 경고 게이트·점수 하락 게이트·은퇴 세트 비교·Docker OCR 성공, 테스트 2종은 실행 중(문서만 바뀐 PR).
- 평가 측 재실행(사본 ba62f9f = 시안 + M4·M5 + C1·C2, 저장소 밖): 비공개 탐침 1~4차 7/8·10/10·7/8·6/8, 새 5차(C1 보정에 씀) 기준 1/6 → 5/6, 새 6차(독립, 보정 안 함) 기준 1/5·0/7 → 5/5·0/7. 대조 오탐 전 세트 0. 관련 20개 파일 654건 통과, 은퇴 5세트 변화 0·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0. 시안 증분 갱신: docs/handoff/patches/TK-76_cycle3_form_prototype_on_90cc681.diff.

C1 [G4 정의가 메모 자신의 예문을 놓침] 3.4절 2)·3) — 불능 술어·양보 어미·판독성 요소를 낱말로 열거해서(평가 측 첫 시안의 목록 그대로), 메모 6.1 G4 양성 1('…판독하기 어려우나')과 6.2 어순 변형 두 예문이 메모 정의로는 판정되지 않는다(평가 측 사본 재현: 3건 모두 미검출). 이는 1차 요청 4절 (가)(나)의 한계 그대로다. 고칠 것(사본에서 검증):
- 불능 술어: '[ㄹ 받침 음절] 수 (가|는)? 없'(ㄹ 받침 음절은 유니코드 조합식 (코드−0xAC00) % 28 == 8로 만든다 — 낱말 목록 아님), '[가-힣]기 (가|는)? (어렵|어려|힘들|힘드|곤란)', '(판독|식별|확인|해독)(이|은|도)? (곤란|불가|어렵|어려|힘들|힘드)', 그리고 기존 보관·상실·기재 부재 꼴.
- 양보 어미: '[가-힣]나' 또는 '지만|더라도|는데도|음에도' 뒤 공백·쉼표(어간을 열거하지 않는다).
- 판독성 요소: '글씨·글자·숫자·금액·기재 내용'은 같은 앞 절에 지각 동사 '판독·식별·해독·알아보·읽'이 이어질 때만 형식 요소로 본다(훼손 동사 목록 대신). 평가 측 재현: 이 짝 조건이 없으면 '계약서에 따라 금액을 산정하기 어려우나 …' 꼴이 오탐.
- 다른 형식 요소(작성명의·작성일·서명/날인·원본)는 메모 정의 그대로.
C2 [ReDoS, 평가 측 시안 결함] 3.3절 작성일 줄 정규식(연도 뒤 '\s*…(?:_{1,}|\s{2,})\s*…' 꼴)은 인접 수량자라, 연도 뒤 긴 공백 입력에서 평가 측 측정 120초 안에 끝나지 않았다(평가 측 시안을 메모가 옮긴 것 — 평가 측 책임). 고칠 것: 줄을 먼저 _BLANK_RUN_RE = r"_+|\s{2,}"로 '□' 하나로 접고(선형), 접힌 줄을 단일 수량자 정규식으로 본다 — 작성일 '^ ?(?:\d{4}|20○○) ?년? ?\.? ?□ ?\.? ?월? ?□ ?\.? ?일? ?\.? ?$', 서명 줄 '(라벨)(?: ?성 ?명)? ?[:：]? ?□? ?\( ?(서명|인|날인|…) ?\) ?$'. 사본 측정: 같은 입력 0.003초, 탐침 결과 변화 없음. 구현 PR에서 모든 새 정규식을 긴 공백·반복 음절 입력(2만 자)으로 시간 시험을 둔다.
C3 [문구] 2.2절 '채택 각하' → '서증으로 채택하지 아니함(채택결정 취소 포함)'. 규칙 제109조 본문 요지는 '당사자가 서증을 신청한 경우 … 사유가 있는 때에는 법원은 그 서증을 채택하지 아니하거나 채택결정을 취소할 수 있다'.

알려진 한계(이번 범위 밖, 구현 PR에 적는다): 번체 중국어 서증명은 KS X 1001 한자와 구별되지 않아 G1이 못 잡는다. 연도까지 빈 작성일 줄('    년    월    일')은 서명 줄이 비어 있을 때만 G3로 잡힌다.

수용 기준(구현 PR): 메모 7.1절 + C1~C3. 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 6세트 하락 없음.
```

### 2-17-3. #235 EVI-FORM 구현 판정 — 보완 1회 (11-06, head `e8ea49e`)

- 평가 측 사본 `f72f1b1`+시험(이 head + D1~D5)으로 사전 검증. 증분: [patches/TK-76_form_impl_fix_on_e8ea49e.diff](patches/TK-76_form_impl_fix_on_e8ea49e.diff). 게이트 허용 등록: `ca40ee9`.

```
[평가 측 판정 — #235 TK-76 3주기 EVI-FORM 구조 규칙 구현 (head e8ea49e, 기준 Steve 90cc681), 11-06]

판정: 보완 1회(작은 보완 — 평가 측 사본 증분을 그대로 적용하면 된다). 메모·C1~C3 구조는 맞게 구현됐다. 남은 결함 D1~D5 가운데 D1·D5와 게이트 실패는 평가 측 시안·지시에서 물려받은 것이다(평가 측 책임).
- CI 결과 인용: '점수 하락 게이트' 실패 — 원인은 평가 세트 문구 점검이 일반 법령명 '민사소송법 제'·'민사소송규칙 제'를 의심으로 띄운 것 하나뿐이다(수용 시험 1,236·회귀 장부 2,357 통과, 회귀 게이트 '회귀 없음', 하드코딩·시험 약화·보호 경로·버전 정책 통과). 평가 측이 1차 요청에서 '허용'이라고만 적고 허용 목록 등록을 빠뜨렸다. CodeQL 새 경고 게이트·은퇴 세트 비교·Docker OCR 성공.
- 평가 측 재실행(이 head): 지난 탐침 1~6차 7/8·10/10·7/8·7/8·5/6·5/5·대조 오탐 0. 판정용 새 비공개 탐침 7~9차(이번에 새로 지음) 7/8·2/5·4/4(합 13/17) — 대조 오탐 3/24(1/10·1/8·1/6) → 수용 기준(오탐 0) 미달. 관련 21개 파일 667건 통과(654 + 이 PR 13).
- 평가 측 사본 f72f1b1+시험(저장소 밖, 이 head + D1~D5): 탐침 1~6차 7/8·10/10·8/8·7/8·5/6·5/5, 7차 8/8·0/10(D1·D3 보정에 씀), 8차 4/5·0/8(D5 보정에 씀), 9차(독립, 보정 안 함) 4/4·0/6. 대조 오탐 전 세트 0. 관련 21개 파일 667건 + 평가 측 시험 10건 통과(이 head에서 평가 측 시험 6건 실패). 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 하드코딩·시험 약화 점검 통과, ca40ee9 적용 시 평가 세트 문구 '의심 없음'. 새 정규식·주소 검사·빈칸 접기 2만 자 악성 입력 0.01초 이하.
- 평가 측 재실행(이 head): verify_all --base 90cc681 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,449·브라우저 197).

원인과 고칠 것 (줄 번호는 e8ea49e의 packages/claim_engine/evidence_consistency.py)

G0 [게이트] 평가 측 커밋 ca40ee9(evaluator/round8-promotion, docs/scorecards/approved_eval_phrases.json 한 파일)를 이 브랜치에 cherry-pick한다. 두 법령명을 '행정절차법 제'와 같은 일반 인용으로 등록했다. 평가 측 사본에서 check_train_phrase_overlap --eval-sets '의심 없음' 확인.

D1 [G1 오탐, 평가 측 시안 결함] 2545행 _foreign_script_name — 국문 서증명 안의 괄호 속 영문 약어 풀이('…(영문 원어 풀이) 국문 명칭' 꼴)를 라틴 글자로 세어 외국 문서로 본다. 판정 탐침 7·9차 오탐 각 1건. 고칠 것: 반각·전각 괄호 속 부연 [(（][^()（）]{0,200}[)）]을 빼고 센다. 괄호 밖이 비면 원래 이름으로 본다(외국어 이름 + 괄호 속 국문 부연은 그대로 외국 문서).
D2 [G1 오탐 꼴] 같은 함수 — 주소·도메인·전자우편 표기(점·@로 이은 영숫자, 한글 없음)를 외국어로 센다. D3을 넣으면 소명방법 행에서 드러난다(평가 측 사본 재현). 고칠 것: 낱말 단위로 그런 토큰을 뺀다. 정규식 없이 문자 검사로 한다(평가 측이 정규식 꼴 '[A-Za-z0-9_-]+(?:[.@][A-Za-z0-9_-]+)+'를 써 보니 4만 자 입력에 27.9초 — 쓰지 않는다).
D3 [미탐, 메모 4.1절 미이행] 2636행 check_evidence_form_structure — '채권자 ○○○ (인)'처럼 가린 이름의 신청 사건 서명 줄은 공용 _detect_author_party가 작성 측을 못 정해, 소갑 행을 자기 것으로 보지 않는다(판정 탐침 7차 미탐). 고칠 것: 새 검사 안에서만 _form_author — 공용 결과를 먼저 쓰고, 정하지 못하면 끝 15블록의 줄 머리 '(위)? 채권자|신청인 → 원고 측 {갑, 소갑}', '채무자|피신청인 → 피고 측 {을, 소을}'.
D4 [메모 5절 미이행] 2713행 _form_findings — 새 규칙끼리 같은 호증 1건이 구현되지 않았다(같은 외국어 서증에 G1·G4 둘 다 나옴). 고칠 것: G4가 낸 호증(가지번호 앞까지)에는 G1을 내지 않는다.
D5 [G3 미탐, 평가 측 C2 지시 결함] 2568·2576행 — '_+|\s{2,}'는 공백·밑줄이 섞인 빈칸('  ____  ')을 '□□□'로 접어 단일 '□' 정규식이 못 맞춘다(판정 탐침 8차 미탐). 고칠 것: _BLANK_RUN_RE = r"[_\s]+"로 연속 덩어리 전체를 보고, 밑줄이 섞였거나 두 칸 이상이면 '□' 하나, 한 칸이면 공백 하나로 접는다(콜백, 선형). 2573행 작성일 줄에 앞 두 자리만 적힌 연도 '(?:19|20) ?□'를 더한다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_form_impl_fix_on_e8ea49e.diff(evaluator/round8-promotion) — 제품 1파일 + 평가 측 시험 tests/test_tk76_form_eval_supplement.py 10건. 그대로 적용해도 되고 같은 구조로 다시 써도 된다. 그리고 G0 cherry-pick.
- 2-2: D1~D5 각각 양성·대조 시험(평가 측 탐침 문장 금지). PR 본문 3.1의 '탐침 1~6차' 수치는 평가 측 사전 검증값을 옮긴 것임을 밝힌다(구현 측 측정 아님). train 단계 건수표는 원본이 없으면 '미측정'으로 적는다(단계 정의만 있는 표는 건수표가 아니다).
- 수용: CI 전부 성공(게이트 포함), 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 9세트 하락 없음, 은퇴·고정 하락 0·오탐 0, verify_all 전체.
```
- #234 Steve 병합 `00e668a`(11-06, 사용자 지시 '#234 병합', 평가 측이 expectedHeadSha `811199b`로 실행). 메모의 C1~C3은 #235 구현 조건으로 남는다.

### 2-17-4. #235 EVI-FORM 구현 2차 판정 — 수용 (11-06, head `3446dda`)

```
[평가 측 2차 판정 — #235 TK-76 3주기 EVI-FORM 구조 규칙 구현 보완본 (head 3446dda, 기준 Steve 90cc681), 11-06]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/evidence_consistency.py)가 평가 측 사본 f72f1b1과 같다(평가 측 대조 diff 0). 평가 측 시험 tests/test_tk76_form_eval_supplement.py 10건 동일, 허용 등록 ca40ee9 cherry-pick 확인, 메모 C3·D1~D5 반영.
- CI 결과 인용: '점수 하락 게이트'·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공.
- 평가 측 재실행(이 head): verify_all --base 90cc681 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,464·브라우저 197, 보호 경로 변경 1개는 평가 측 커밋 ca40ee9). 판정용 새 비공개 탐침 10차(이번에 새로 지음) 기준 Steve 1/6 → 6/6·대조 오탐 0/9. 지난 탐침 1~9차 7/8·10/10·8/8·7/8·5/6·5/5·8/8·4/5·4/4, 대조 오탐 전 세트 0(합 58/64·0/78). 평가 세트 문구 '의심 없음', 하드코딩·시험 약화 점검 통과. 은퇴·고정은 같은 제품 코드의 사본에서 53.3/48.6/56.9/45.8/34.1·오탐 0, 82.6/81.9·FP 0 — 변화 0(세트 득점 0).
- 2-2 다: 귀속표 '세트 득점 0' 확인, 탐침 수치는 평가 측 값 인용으로 밝힘, train은 원본 없음으로 '미측정'(평가 측도 미측정).
- 남은 한계(후속): 번체 중국어 서증명(G1), 연도까지 빈 작성일 줄(G3 단독), '…담당자가 누구인지 알 수 없지만' 꼴처럼 작성 명의와 다른 사람의 신원 불명(G4 범위 밖), 일부 쪽만 제출(G5, 재판장 허가 여부 판별 불가).
```
- #235 Steve 병합 `13641e0`(11-06, 사용자 지시 '#235병합', 평가 측이 expectedHeadSha `3446dda`로 실행). TK-76 EVI-FORM 완료. 다음 유형 EVI-NUM(TK-73 조율).

## 2-18. TK-76 3주기 EVI-NUM 구현 지시 (11-06, 사용자 'EVI-NUM 착수 지시')

- TK-73(Codex)은 진행 중 PR 없음, 잔여는 같은 번호 중복 1꼴 — 이번 지시는 중복 판정 키를 건드리지 않는다.
- 평가 측 사본 `d32f874`(저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_num_on_13641e0.diff](patches/TK-76_cycle3_num_on_13641e0.diff).

```
[평가 측 구현 지시 — TK-76 3주기 EVI-NUM(호증 번호·목록 대조) 후속 PR(E1~E3), 기준 Steve 13641e0, 11-06]

목적: 호증 번호·목록 대조(EVI-NUM)의 오탐 1꼴과 미탐 2꼴을 고친다. 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료, 고칠 양이 작다). TK-73(같은 번호 중복 판정 키, Codex)과 겹치지 않는다 — _numbering의 중복 판정(comparison_keys·seen)은 건드리지 않는다.

평가 측 사전 검증(사본 d32f874, Steve 13641e0 위, 저장소 밖 비공개 탐침 — 문장 비공개):
- 1차(설계와 함께 지음): 기준 양성 6/8·대조 오탐 3/8 → 사본 8/8·0/8. 2차(독립, 보정 안 함): 기준 4/6·2/8 → 6/6·0/8.
- 기준의 오탐 5건은 모두 '본문이 언급한 증거가 증거 목록에 없다'(앞 서면에서 낸 호증 인용, 추후 제출 예고)다. 준비서면의 입증방법에는 새로 내는 호증만 적는 것이 보통이라, 실제 서면에서 자주 나는 꼴이다.
- 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 관련 23개 파일 687건 통과. 평가 세트 문구 '의심 없음', 하드코딩·시험 약화 점검 통과. verify_all --base 13641e0 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,471·브라우저 197).
- 평가 측이 시험해 보고 뺀 것: 결번·목록 밖 판정 발췌에 서증명·인용 문장을 넣는 보강(train 진단 (d) '발췌에 항목명 누락' 대응)은 은퇴 1세트에서 34.1→32.1·오탐 0→1이 되어 지시하지 않는다. 발췌 문구는 바꾸지 않는다.

원인과 고칠 것 (줄 번호는 Steve 13641e0의 packages/claim_engine/evidence_consistency.py)

E1 [오탐] 목록 밖 인용이 앞 서면 호증·추후 제출 예고를 구분하지 않음 — _numbering 1612~1621행
- 원인: exhibit_keys(text)로 본문 전체의 (당사자, 번호)를 모아 목록에 없으면 모두 '목록에 없다'로 낸다. 같은 파일 축 3(2017행 부근)은 _PRIOR_SUBMISSION_RE로 앞 제출 인용을 거르지만 이 경로는 거르지 않는다.
- 고칠 것: 본문을 sentence_bounds로 문장 단위로 보고 parse_exhibits로 인용을 모은다. 다음 인용은 뺀다 — (가) 그 당사자의 목록 구역 번호가 N(>1)부터 시작하면 N보다 작은 번호(앞 서면에서 낸 호증), (나) 같은 문장에 _PRIOR_SUBMISSION_RE(1746행) 또는 추후 제출 표지가 있는 인용. 추후 제출 표지는 새 정규식 _FUTURE_SUBMISSION_RE = r"(?:추후|향후|다음 ?기일에|나중에|보완하여)[^.\n]{0,30}?(?:제출하겠|내겠|제출할|낼 ?예정|제출 ?예정)|제출할 ?예정|제출하겠습니다"(모듈 앞쪽, 145행 _NORMAL_FUTURE_SUBMISSION_RE 옆).
E2 [미탐] 가지번호 인용이 목록 가지번호 밖 — 같은 함수(새 판정)
- 원인: 목록 밖 판정이 (당사자, 번호)만 보아 '갑 제N호증의 k'를 인용했는데 목록에는 그 호증의 가지번호가 1~m(k>m)뿐인 경우를 놓친다.
- 고칠 것: E1에서 모은 인용의 가지번호 (p, n, b)가, 목록이 가지번호로 나뉜 호증(branches 사전에 (p, n)이 있음)이고 b > max(목록 가지번호)이면 EVIDENCE_LIST_MISMATCH·B·MEDIUM, rule_id·defect_code 'BRANCH_REFERENCE_MISSING'. 중간 결번(b < max)은 기존 가지번호 결번 판정이 맡으므로 내지 않는다(같은 호증 두 판정 방지).
E3 [미탐] 괄호 속 서증명 끝의 ')'를 경계로 보지 않음 — 축 3, 2030행 name_pat
- 원인: '(갑 제N호증 서증명)' 꼴에서 서증명 바로 뒤가 ')'라 뒤 경계 예견 (?=[\s.,;:~!?]|$)에 맞지 않아, 본문 번호와 목록 번호가 다른 경우를 놓친다.
- 고칠 것: 뒤 경계에 ')'·'）'·']'를 더한다: (?=[\s.,;:~!?)）\]]|$).

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_num_on_13641e0.diff(evaluator/round8-promotion) — 제품 1파일(30줄 남짓), 평가 측 시험 tests/test_tk76_num_eval.py 7건(기준에서 4건 실패, 3건은 대조). 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2: 고정 문장 틀·닫힌 장면 사전 금지, 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표(규칙별 고정·은퇴 득점 — 변화 0이면 '세트 득점 0'), 변형 시험(어순·연결 어미·같은 꼴 다른 낱말, E1은 앞 제출 표지 3꼴·추후 제출 표지 3꼴), train은 원본이 없으면 '미측정'.
- 수용: CI 전부 성공, 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 2세트 하락 없음, 은퇴·고정 하락 0·오탐 0, verify_all 전체, TK-73 시험 포함 관련 시험 통과.
- 남은 EVI-NUM(이번 범위 밖): train 진단 (d) 발췌 항목명 — 채점 토큰 대조 문제로, 발췌 보강은 위와 같이 은퇴 오탐을 만들어 보류. TK-73 잔여(같은 자료명·다른 문서·한쪽만 날짜)는 Codex 몫.
```

### 2-18-1. #236 EVI-NUM 판정 — 수용 (11-08, head `3b1c6a7`)

```
[평가 측 판정 — #236 TK-76 3주기 EVI-NUM 후속(E1~E3) (head 3b1c6a7, 기준 Steve 13641e0), 11-08]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/evidence_consistency.py)가 평가 측 사본 d32f874와 같다(평가 측 대조 diff 0). 평가 측 시험 7건 동일 + 구현 측 변형 시험 5건(앞 제출 3꼴·추후 제출 3꼴·실제 누락 3건, 가지번호 초과 3건·중간 결번 비중복, 괄호 경계 3꼴). TK-73 중복 판정 키·발췌 문구 불변 확인.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공.
- 평가 측 재실행(이 head): verify_all --base 13641e0 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,476·브라우저 197). 판정용 새 비공개 탐침 3차(이번에 새로 지음) 기준 Steve 4/6·대조 오탐 4/8 → 6/6·0/8. 지난 1·2차 8/8·6/6·대조 오탐 0(합 20/20·0/24). 관련 24개 파일 699건 통과. 평가 세트 문구 '의심 없음', 하드코딩·시험 약화 점검 통과. 은퇴·고정은 같은 제품 코드의 사본에서 53.3/48.6/56.9/45.8/34.1·오탐 0, 82.6/81.9·FP 0 — 변화 0(세트 득점 0).
- 2-2 다: 귀속표 '세트 득점 0', 탐침 수치는 평가 측 값 인용으로 밝힘, train '미측정'(평가 측도 미측정).
- 남은 EVI-NUM(후속): 발췌 항목명 보강(train 진단 (d))은 은퇴 오탐을 만들어 보류, TK-73 잔여(같은 자료명·다른 문서·한쪽만 날짜)는 Codex 몫.
```
- #236 Steve 병합 `77b8d07`(11-08, 사용자 지시 '#236 병합', 평가 측이 expectedHeadSha `3b1c6a7`로 실행). TK-76 EVI-NUM 완료. 다음 유형 EVI-DATE.

## 2-19. TK-76 3주기 EVI-DATE 지시 (11-08, 사용자 'EVI-DATE 착수 지시')

- 평가 측 사본 `378f7a1`(T1, 저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_date_t1_on_77b8d07.diff](patches/TK-76_cycle3_date_t1_on_77b8d07.diff). T2·T3는 진단만(미검증).

```
[평가 측 지시 — TK-76 3주기 EVI-DATE(날짜·시각 선후), 기준 Steve 77b8d07, 11-08]

두 PR로 낸다. PR-A(T1)는 바로 구현(평가 측 사본으로 사전 검증 완료). PR-B(T2·T3)는 사건 칸(EventSlot) 경로를 고쳐야 하므로 설계 메모 PR부터 낸다.

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 1차 탐침(양성 8·대조 8) 기준 Steve 5/8·오탐 0/8. 날짜·요일 불일치, 달력에 없는 날짜(점·하이픈), 서증 작성일 > 서면 작성일은 이미 잡힌다(b68 진단의 '요일 병기 부재'는 그 뒤 구현됨).
- 놓친 3꼴: (T1) 'A부터 B까지 N일간' 기간 일수 오류, (T2) 같은 날 시각 역전(결정 시각보다 이른 시각의 통지), (T3) 서면이 스스로 밝힌 인과 표지('그 사유가 된 …')의 원인 사건 날짜가 결과보다 뒤.
- train은 이 평가 환경에 원본이 없어 미측정.

== PR-A: T1 기간 일수 (바로 구현) ==

평가 측 사전 검증(사본 378f7a1): 1차 5/8 → 6/8(T1만 해당)·오탐 0/8, 2차(T1 독립, 보정 안 함) 기준 0/4 → 4/4·0/6. 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 관련 15개 파일 427건 통과, 2만 자 악성 입력 0.004초. 평가 세트 문구 '의심 없음', 하드코딩·시험 약화 점검 통과. verify_all --base 77b8d07 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,482·브라우저 197).

T1 [미탐] 기간 일수 'A부터 B까지 N일(간|동안)' — packages/claim_engine/date_verifier.py 39~43행 DAYS_ELAPSED_RE, 1476행 '3. 경과 일수 계산 검증'
- 원인: DAYS_ELAPSED_RE는 'A로부터 N일 지난 B' 꼴(시작일 → 일수 → 끝날)만 본다. 법률 서면에 흔한 'A부터 B까지 N일간'(시작일 → 끝날 → 일수) 꼴은 보지 않는다.
- 고칠 것: 새 정규식 DAYS_RANGE_RE(연·월·일 점·하이픈·'년월일' 꼴, '부터|에서' … '까지', 선택 '총|모두|합계', N, '일 ?(간|동안|에 걸쳐)'; 공백은 \s? 단일 수량자)와 1476행 앞에 '3-1' 검사를 둔다. 실제 일수는 양 끝 포함((B−A)+1), 민법 제157조 초일 불산입 여부에 따라 1일 차이는 허용(|포함 일수 − N| > 1일 때만). 앞 20자·뒤 15자 안에 셈법이 다른 표지(영업일·근무일·평일·공휴일·휴일·주말·근로일·출근일·실근무·제외)가 있으면 건너뛴다. 'N개월간'은 대상이 아니다. TIMELINE_CONTRADICTION·CONTRADICTED·A·MEDIUM, rule_id 'claim_engine.date_verifier:DAYS_RANGE_MISMATCH', 발췌는 일치 문자열.
- 제출물: 평가 측 사본 증분 docs/handoff/patches/TK-76_cycle3_date_t1_on_77b8d07.diff(evaluator/round8-promotion) — 제품 1파일, 평가 측 시험 tests/test_tk76_date_range_eval.py 6건. 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 수용: CI 전부 성공, 평가 측 새 비공개 탐침 양성 2/3 이상·대조 오탐 0, 은퇴·고정 하락 0·오탐 0, verify_all 전체, 2-2 다(귀속표 '세트 득점 0', 변형 시험 3종, train '미측정').

== PR-B: T2·T3 설계 메모 ==

T2 [미탐] 같은 날 시각 역전 — 평가 측 진단(미검증):
- EventSlot(548~590행)에 time_min 필드가 있으나 1207행 슬롯 생성에서 채우지 않고, 1874행 비교는 날짜(d_effect < d_cause)만 본다. TIME_RE(608행)는 정의만 있다.
- '같은 날·당일·동일자' 같은 상대 표현이 앞 슬롯 날짜를 물려받지 않아(현재는 '다음 날·익일'만 is_next_day로 처리) 날짜가 None이 된다.
- EVENT_ORDER_RULES(285행)에 '처분(결정·의결) → 통지'(그 결정을 알리는 통지) 쌍이 없다(신청→처분, 신청→통지, 발송·통지→도달 등만 있음).
- 메모에서 정할 것: 절 안 시각(TIME_RE, 오전·오후 12시간 표기 환산) 채우기, 같은 날 표현의 날짜 상속 범위(같은 문장·바로 앞 절만), 같은 날짜일 때 시각 비교(결과 시각 < 원인 시각), 처분→통지 쌍의 법적 근거(예: 근로기준법 제27조 제1항 "사용자는 근로자를 해고하려면 해고사유와 해고시기를 서면으로 통지하여야 한다" — 법제처 현행 원문, MST 285279 시행 2026-10-08 평가 측 확인. 통지 대상이 그 결정일 때만, require_target_match), 기존 A-4 안전장치(R4 대상 일치·R5 주체·AA5 회고 서술 제외) 유지.

T3 [미탐] 서면이 밝힌 인과 표지의 원인 날짜가 결과보다 뒤 — 평가 측 진단(미검증):
- 1547~1551행 SEND_HEADER_RE·PAST_EVENT_RE 검사는 '발송일:·작성일:' 머리 날짜가 있을 때만 '…에 개최된/의결에 따라' 꼴을 본다. 본문에서 날짜가 있는 행위 X와 '그(X의) 사유가 된 / 근거가 된 / …에 따른' 날짜 Y를 잇는 꼴은 보지 않는다.
- 메모에서 정할 것: 인과 표지(사유가 된·근거가 된·…에 따라·…에 근거하여·…의 결과)로 X(결과)와 Y(원인)를 같은 문장 또는 바로 다음 문장에서 잇는 구조, 지시어('그', '위') 결속, Y > X일 때 판정(등급 B), 제외(가정·예정 서술 '…할 예정인', 상대방 주장 인용, '사후에 추인한' 같은 추인·보완 서술).

PR-B 제출물: 메모(구조 정의·법적 근거·제외 조건·기존 규칙과의 관계·공개 합성 양성 3·대조 3 이상, 평가 측 탐침 문장 금지), 변형 시험 계획, train 측정 계획(원본 없으면 '미측정'). 메모 승인 뒤 구현 PR.
```

### 2-19-1. #237(T1) 수용·#238(T2·T3 메모) 조건부 승인 (11-08)

```
[평가 측 판정 — #237 TK-76 3주기 EVI-DATE PR-A(T1 기간 일수) (head 0f002e9, 기준 Steve 77b8d07), 11-08]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/date_verifier.py)가 평가 측 사본 378f7a1과 같다(평가 측 대조 diff 0). 평가 측 시험 6건 동일 + 구현 측 변형 시험 3건(어순·연결 어미, 날짜 서식·낱말, 셈법 제외·정상 대조).
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공.
- 평가 측 재실행(이 head): verify_all --base 77b8d07 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,485·브라우저 197). 판정용 새 비공개 탐침 3차(이번에 새로 지음, T1) 기준 Steve 0/4 → 4/4·대조 오탐 0/6. 지난 1·2차 6/8·4/4·대조 오탐 0. 은퇴·고정은 같은 제품 코드의 사본에서 53.3/48.6/56.9/45.8/34.1·오탐 0, 82.6/81.9·FP 0 — 변화 0(세트 득점 0).
- 2-2 다: 귀속표 '세트 득점 0', 탐침 수치는 평가 측 값 인용으로 밝힘, train '미측정'.
```

```
[평가 측 판정 — #238 TK-76 3주기 EVI-DATE PR-B 설계 메모(T2·T3) (head f69642a, 기준 Steve 77b8d07), 11-08]

판정: 조건부 승인. 구조(T2 시각 채우기·같은 날 상속·처분→통지 쌍·같은 날 시각 비교, T3 역행·순행 인과 구문과 제외 조건, 기존 _emit_temporal_inversion 경로로 1건 배출)는 요청과 맞다. 메모는 CI 완료 상태라 Steve 병합 가능. 아래 D1~D3은 구현 PR의 필수 조건이다(구현 PR에서 메모 해당 절도 함께 고친다).
- CI 결과 인용: 필수 확인 전부 성공(문서만 바뀐 PR).
- 평가 측 확인: 법제처 현행 원문(행정절차법 MST 239291 시행 2023-03-24, 근로기준법 MST 285279 시행 2026-10-08, 민법 MST 284415 시행 2026-03-17), 메모의 시각 정규식 대조(아래 D2, 사본 아님 — 정규식 단독 시험).

D1 [법적 근거 오귀속] 2.1절·3.1(3) statute — '처분 → 통지' 쌍의 근거로 든 두 조문이 그 선후의 근거가 아니다.
- 행정절차법 제24조(처분의 방식) 제1항은 "행정청이 처분을 할 때에는 … 문서로 하여야 하며 …"로 처분의 형식(문서)을 정한다. 처분 뒤에 통지가 온다는 규정이 아니다.
- 민법 제111조(의사표시의 효력발생시기) 제1항은 "상대방이 있는 의사표시는 상대방에게 도달한 때에 그 효력이 생긴다."로 도달주의를 정한다. 기존 '발송·통지 → 도달' 쌍의 근거이고 '처분 → 통지'의 근거가 아니다.
- 고칠 것: 처분→통지 쌍의 근거는 '통지는 그 결정 내용을 알리는 것이므로 결정이 먼저'라는 논리칙으로 적고, 해고 결정은 근로기준법 제27조 제1항(해고사유·시기 서면통지)을 예로 둔다. statute 문자열은 "근로기준법 제27조 제1항(해고 통지)·논리칙"으로. 사전통지 제외 근거로 든 행정절차법 제21조(처분의 사전 통지)·근로기준법 제26조(해고의 예고)는 원문과 맞다(유지).
D2 [시각 정규식 오탐] 3.1(1) TIME_RE — '(?P<h2>[012]?\d)\s?시'가 시간 길이·명사를 시각으로 읽는다. 평가 측 정규식 단독 시험: '하루 8시간'→'8시', '24시간 이내'→'24시', '제1시'→'1시', '3시점'→'3시', '1시기'→'1시'. 근로 사건 서면의 근로시간 서술이 사건 시각으로 붙어 오탐이 될 수 있다(메모의 '제1시 등과 겹치지 않도록' 서술과 정규식이 다름).
- 고칠 것: 앞 경계 (?<![\d제]), '시' 바로 뒤 (?!간|각|행|효|점|기|장|설) 예견. 같은 시험에서 위 5꼴은 모두 빠지고 '오후 4시 10분'·'16시'·'10시경'·'09:30'은 그대로 잡힌다(2만 자 입력 0.013초). 구현 PR 시험에 시간 길이 대조('8시간 근무', '24시간 이내')를 넣는다.
D3 [T3 인과 결합 범위] 3.2(2) 구문 꼴 A — '절 안에 날짜 d_Y와 인과 연결 표지(…에 따라 등)가 있으면'으로 적혀 있어, 법령·규정 인용('근로기준법 제23조에 따라')이나 같은 절의 다른 날짜가 d_Y로 잡힐 수 있다.
- 고칠 것: d_Y는 인과 연결 표지가 직접 받는 명사구 안의 날짜로 한정한다 — '날짜 + (관형어: 개최된·체결된·실시된·발령된·의결된 등 과거 관형형) + 명사 + 인과 연결 표지' 사이에 절 경계(쉼표·연결 어미)가 없을 때만. 법령명·조문 인용 뒤의 '…에 따라'는 원인 사건이 아니므로 제외(조문 표지 '제N조' 직후의 연결 표지). '시행되는/시행된 규정에 따라'처럼 규범의 시행일과 행위일을 잇는 꼴은 소급 적용 여부를 서면에서 알 수 없으므로 이번 범위에서 제외(후속)로 적는다.

제출물·수용 기준(구현 PR)
- 메모 6절 + D1~D3. 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(시간 길이 서술·법령 인용 '…에 따라' 대조 포함), 은퇴·고정 하락 0·오탐 0, verify_all 전체, 기존 A-4 시험·날짜 관련 시험 통과, 신규 정규식 2만 자 선형 시간 시험.
```
- #237 Steve 병합 `c977c0b`, #238 Steve 병합 `900502a`(11-08, 사용자 지시 '#237,238 병합', 평가 측이 expectedHeadSha `0f002e9`·`f69642a`로 실행). 다음: T2·T3 구현 PR(D1~D3 포함), EVI-COPY 착수 가능.

### 2-19-2. EVI-DATE PR-B 구현 요청 (T2·T3, D1~D3) (11-08, 사용자 '#238 판정문 전달·T2·T3 구현 PR 요청')

```
[평가 측 구현 요청 — TK-76 3주기 EVI-DATE PR-B 구현(T2·T3), 기준 Steve 900502a(#238 메모 병합), 11-08]

#238 설계 메모(docs/handoff/requests/TK-76_cycle3_evi_date_design_memo.md)를 조건부 승인했고 Steve에 병합했다(900502a). 메모대로 T2·T3를 구현 PR로 낸다. 아래 D1~D3은 필수 조건이며, 구현 PR에서 메모의 해당 절도 함께 고친다.

D1 [법적 근거 오귀속] 메모 2.1절·3.1(3) statute — '처분 → 통지' 쌍의 근거로 든 두 조문이 그 선후의 근거가 아니다(법제처 현행 원문 평가 측 확인).
- 행정절차법 제24조(처분의 방식) 제1항은 "행정청이 처분을 할 때에는 … 문서로 하여야 하며 …"로 처분의 형식(문서)을 정한다.
- 민법 제111조(의사표시의 효력발생시기) 제1항은 "상대방이 있는 의사표시는 상대방에게 도달한 때에 그 효력이 생긴다."로 도달주의를 정한다(기존 '발송·통지 → 도달' 쌍의 근거).
- 고칠 것: 처분→통지 쌍의 근거는 '통지는 그 결정 내용을 알리는 것이므로 결정이 먼저'라는 논리칙으로 적고, 해고 결정은 근로기준법 제27조 제1항(해고사유·시기 서면통지)을 예로 둔다. statute 문자열은 "근로기준법 제27조 제1항(해고 통지)·논리칙". 사전통지 제외 근거(행정절차법 제21조, 근로기준법 제26조)는 원문과 맞다(유지).
D2 [시각 정규식 오탐] 메모 3.1(1) TIME_RE — '(?P<h2>[012]?\d)\s?시'가 '하루 8시간'→'8시', '24시간 이내'→'24시', '제1시'→'1시', '3시점'→'3시', '1시기'→'1시'로 읽는다(평가 측 정규식 단독 시험). 고칠 것: 앞 경계 (?<![\d제]), '시' 바로 뒤 (?!간|각|행|효|점|기|장|설). 같은 시험에서 위 5꼴은 빠지고 '오후 4시 10분'·'16시'·'10시경'·'09:30'은 그대로 잡힌다(2만 자 0.013초). 시험에 시간 길이 대조('8시간 근무', '24시간 이내')를 넣는다.
D3 [T3 인과 결합 범위] 메모 3.2(2) 구문 꼴 A — d_Y는 인과 연결 표지가 직접 받는 명사구 안의 날짜로 한정한다: '날짜 + (과거 관형형: 개최된·체결된·실시된·발령된·의결된 등) + 명사 + 인과 연결 표지' 사이에 절 경계(쉼표·연결 어미)가 없을 때만. 법령·조문 인용 뒤의 '…에 따라'(조문 표지 '제N조' 직후)는 원인 사건이 아니므로 제외. '시행되는/시행된 규정에 따라'(규범 시행일 ↔ 행위일)는 소급 여부를 서면에서 알 수 없으므로 이번 범위에서 제외(후속)로 적는다.

제출물·수용 기준
- 구현: packages/claim_engine/date_verifier.py(메모 3·4절 + D1~D3), 시험 tests/test_tk76_date_t2_t3_eval.py(메모 5.1 합성 13건 + 3대 변형 + 시간 길이·법령 인용 대조 + 신규 정규식 2만 자 선형 시간), 메모 2.1·3.1(1)·3.1(3)·3.2(2) 수정.
- 2-2: 고정 문장 틀·닫힌 장면 사전 금지, 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표(T2·T3 규칙별 고정·은퇴 득점, 변화 0이면 '세트 득점 0'), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(시간 길이 서술·법령 인용 '…에 따라' 대조 포함), 기존 A-4 시험·날짜 관련 시험 통과, 은퇴·고정 하락 0·오탐 0, verify_all 전체.
```

## 2-20. TK-76 3주기 EVI-COPY 구현 지시 (C1) (11-08, 사용자 'EVI-COPY 착수 지시')

- 평가 측 사본 `521d341`(저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_copy_c1_on_900502a.diff](patches/TK-76_cycle3_copy_c1_on_900502a.diff). 은퇴 세트는 집계 숫자만 확인(문서 내용 열람 없음).

```
[평가 측 구현 지시 — TK-76 3주기 EVI-COPY(서면 간 문장 복사) C1, 기준 Steve 900502a, 11-08]

목적: 진술 문서가 다른 서면 문장을 어미·조사만 바꿔 옮긴 대필 꼴(C1)을 잡는다. 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료).

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 현재 경로(packages/claim_engine/evidence_consistency.py 3089행 cross_document_copies)는 5글자 조각 겹침 0.9 이상(140행 COPY_SIMILARITY)인 문장만 같다고 본다. 진술 문서 ← 다른 서면, 소송서면·증거설명서 ← 사실경위서 경로가 있다.
- 탐침 1·2차(합 양성 10·대조 8) 기준 9/10·오탐 0/8. 사실경위서 → 소장·준비서면·의견서·증거설명서·진술서, 진술서 ↔ 진술서 복사는 잡힌다. 놓친 꼴은 어미·조사만 바꾼 복사뿐(5글자 조각 겹침 0.54~0.67로 0.9에 못 미침).
- 은퇴 세트(오프라인, 집계 숫자만 확인 — 문서 내용 열람 없음): EVI-COPY 7항목 중 6항목 미탐. 문서 종류 분포·문서 쌍 유사도 구간 집계로 보면 놓친 세트의 유사 문장 쌍은 주로 '소송서면 ↔ 사실경위서로 분류되지 않은 문서' 사이에 있다. 평가 측이 원문 범위를 그 문서들로 넓혀 보니 은퇴 1세트 53.3→49.3·오탐 0→2, 놓친 세트 득점 0 — 그래서 원문 범위 확장은 지시하지 않는다(후속 검토, 문서 종류 판별은 이번 범위 밖).

평가 측 사전 검증(사본 521d341): 탐침 1차 4/5→5/5·0/4, 2차 5/5·0/4 유지, 3차(독립, 같은 사건을 자기 말로 쓴 진술·두 목격자 진술 대조 포함) 기준 1/3 → 2/3·대조 오탐 0/5. 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 관련 23개 파일 675건 통과. 평가 세트 문구 '의심 없음', 하드코딩·시험 약화 점검 통과. 추가 시간: 진술 60문장 × 서면 6개 × 150문장 입력에서 0.4초 이내(같은 입력의 기존 경로 자체 비용은 별도). verify_all --base 900502a 전체 종료 0(수용 1,239·회귀 장부 2,357·전체 9,489·브라우저 197).

C1 [미탐] 어미·조사만 바꾼 복사 — 3162행 'for other_id, matched in pairs.items()' 앞
- 원인: 5글자 조각 겹침은 문장 끝 어미('-습니다'→'-다', '-하였고'→'-했으며')와 조사가 바뀌면 크게 떨어진다.
- 고칠 것: 진술 문서(DOC_KIND_STATEMENT) 주인일 때만, 진술 구역 문장마다 어절 어간 순서열(_stem_seq: 한글·영숫자 어절에서 세 글자 이상이면 앞 두 글자, 두 글자면 그대로, 한 글자 어절 제외)을 만든다. 다른 문서 문장과 최장 공통 부분열 길이(_lcs_len, 동적 계획, 각 200개 상한) / 짧은 쪽 길이 ≥ 0.85이고 양쪽 어간 8개 이상이면 쌍으로 본다. 같은 상대 문서에 대해 (기존 정확 일치 쌍 + 이 쌍) 합이 2쌍 이상이고 새 쌍이 1개 이상일 때만 그 문서의 pairs에 더한다(같은 사건을 자기 말로 쓴 진술과 가르기 위해 한 문장만으로는 내지 않음). 계산 줄이기: 공통 어간 수(중복 포함 최소합)가 0.85 × 짧은 쪽 길이에 못 미치면 최장 공통 부분열을 계산하지 않는다. 등급·문구는 기존 진술 문서 경로(B·SUSPICIOUS) 그대로.
- 원문 범위·소송서면 경로·5글자 조각 임계값(0.9)은 바꾸지 않는다.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_copy_c1_on_900502a.diff(evaluator/round8-promotion) — 제품 1파일, 평가 측 시험 tests/test_tk76_copy_eval.py 4건. 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2: 고정 문장 틀·닫힌 장면 사전 금지, 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표('세트 득점 0'), 변형 시험(어미 3꼴·조사 3꼴·어순 유지, 자기 말 서술 대조 3건), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 3세트 하락 없음, 은퇴·고정 하락 0·오탐 0, verify_all 전체.
```

## 2-21. TK-76 3주기 EVI-LOGIC 잔여 구현 지시 (L1~L3) (11-08, 사용자 'EVI-LOGIC 잔여 착수 지시')

- 평가 측 사본 `a004116`(기준 `900502a`, 저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_logic_l1l3_on_900502a.diff](patches/TK-76_cycle3_logic_l1l3_on_900502a.diff). L3 법적 근거는 법제처 판례 원문(대법원 1999. 1. 29. 선고 98다48903 판결) 확인.

```
[평가 측 구현 지시 — TK-76 3주기 EVI-LOGIC 잔여(L1~L3), 기준 Steve 900502a, 11-08]

목적: 진술·서면의 논리 결함 잔여 3꼴을 잡는다. 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 2주기(#204) 지각 범위 6구조는 그대로 둔다.

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 2주기 기록상 남은 꼴: 침묵을 동의로 추론, 반복 사건 단정, 앞 문장 맥락이 필요한 장소 모순, 유사과학 근거. 이번 범위는 앞의 셋(L3·L2·L1). 유사과학 근거는 모델 판단 영역이라 범위 밖.
- 1차 탐침(양성 6·대조 7) 기준 Steve 0/6·오탐 0/7 — 세 꼴 모두 경로 없음. perception_conflict(evidence_consistency.py 97행)는 한 문장 안에서만 보고, REASONING_GAP 규칙은 없다.

평가 측 사전 검증(사본 a004116): 1차 0/6 → 6/6·0/7, 2차(독립, 보정에 씀) 0/4 → 4/4·0/8(보정 전 4/4·오탐 3), 3차(독립, 보정에 씀) 0/4 → 4/4·0/7(보정 전 오탐 1), 4차(독립, 보정 안 함) 0/3 → 2/3·0/6. 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 관련 24개 파일 739건 통과, 2만 어절 악성 입력 0.016초. 평가 세트 문구 '의심 없음', 하드코딩·시험 약화 점검 통과. verify_all --base 900502a 전체: 수용 1,239·회귀 장부 2,357·전체 9,490 통과·브라우저 197, 실패 2건은 OCR 시간 초과(평가 측 동시 실행 부하로 30초 제한 초과 — Steve 900502a도 같은 실패, 제한 300초로 다시 돌려 두 건 통과)로 제품 변경과 무관.

규칙 (evidence_consistency.py, 새 함수 check_reasoning_structure를 check_document(2793행)에 더한다. 문장은 sentence_bounds로 보고 빈 문장은 건너뛴다)
L1 [미탐] 앞 문장의 다른 장소 체재 + 다음 문장의 같은 때 직접 지각 — STATEMENT_BEYOND_PERCEPTION·C·SUSPICIOUS, rule_id 'EVI.BEYOND_PERCEPTION_STRUCTURE', pattern 'ELSEWHERE_PREV_SENTENCE'
- 앞 문장: '(에|에서) + 어절 0~4개 + (있었|머물렀|지냈|중이었)(습니다|다|음)' 그리고 앞 문장이나 다음 문장 앞 30자 안에 시간 표지(같은 시각·그 시간·그때·당시·하루 종일·내내·동시에).
- 다음 문장: 기존 _PERC_RE·_DIRECT_RE가 있고 _MEDIATED_RE(매개 경로)가 없고, 이미 perception_conflict로 잡힌 문장이 아님.
- 제외: 두 문장 어디든 이동·시간 경과 표지(올라와·내려와·돌아와·이동·도착·떠나·'-다가'·뒤에·이후·나중에).
L2 [미탐] 한 번의 사실을 근거로 늘 그렇다고 단정 — REASONING_GAP·C·SUSPICIOUS·LOW, rule_id 'EVI.SINGLE_TO_ALWAYS'
- 인과 연결(으므로·므로·으니·니까·기 때문에·따라서·그러므로) 앞에 한 번 표지(한 번·한 차례·1회, 뒤에 '도·시·경우·마다·이상·이내'가 오면 아님)와 과거 관찰(었·았·였·했 또는 '사실/적/일이 있'), 뒤에 늘 표지(매번·항상·늘·언제나·매일·상습·번번이·습관적). 앞에 늘 표지가 이미 있으면 아님.
L3 [미탐] 답·이의가 없었다는 이유만으로 동의·승낙을 추론 — REASONING_GAP·C·SUSPICIOUS·LOW, rule_id 'EVI.SILENCE_AS_CONSENT'
- 법적 근거(평가 측 법제처 판례 원문 확인): 대법원 1999. 1. 29. 선고 98다48903 판결 [2] — 상법 제53조가 적용될 수 있는 경우가 아니라면 청약 상대방에게 회답 의무가 없으므로, 기간 내 이의가 없으면 승낙으로 간주한다고 표시했어도 상대방을 구속하지 않는다.
- 인과 연결 앞에 침묵 서술(답·회신·응답·대답·이의·반대·의견 + 하지 않·안 하·보내지 않·제기하지 않·없(뒤에 '이'가 오는 '없이'는 아님) 또는 '침묵'), 뒤에 동의 표지(동의·승낙·수락·합의·승인 + 한·하였·했·한 것).
- 제외: 간주 약정·법정 근거(약정·간주·본다고·보기로·상법 제53조·낙부 통지·상시 거래), 부정('볼 수 없'·'아니'), 행동으로 드러난 묵시 동의('없이 + 지급·수령·이행·사용·받아·서명·날인·계속·납부·인도·입금').
- L2·L3 공통 제외: 인과 연결 뒤에 상대방 주장 인용·반박('…다는/라는 … 주장·지적·의견·말·항변', 근거가 없·이유 없·부당·받아들일 수 없·오해).

알려진 한계(이번 범위 밖): 장소 조사 없이 '…견학 중이었다'처럼 쓴 체재 문장(L1, 4차 탐침 미탐 1), 유사과학 근거.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_logic_l1l3_on_900502a.diff(evaluator/round8-promotion) — 제품 1파일, 평가 측 시험 tests/test_tk76_logic_eval.py 7건. 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2: 고정 문장 틀·닫힌 장면 사전 금지, 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표('세트 득점 0'), 변형 시험(어순·연결 어미·같은 꼴 다른 낱말, L3 제외 3꼴), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 4세트 하락 없음, 은퇴·고정 하락 0·오탐 0, verify_all 전체.
```

## 2-22. TK-76 3주기 EVI-INCONS C 설계 메모 요청 (11-08, 사용자 'EVI-INCONS C 설계 메모 요청')

```
[평가 측 설계 메모 요청 — TK-76 3주기 EVI-INCONS C(문서 안 같은 대상의 두 날짜·시각), 기준 Steve 900502a, 11-08]

목적: 한 문서 안에서 하나뿐인 같은 사건(예: 단 한 차례 보낸 회신, '위 통지')에 서로 다른 날짜·시각을 적은 모순을 잡는다. 설계 메모 PR부터 낸다(메모 승인 뒤 구현 PR).

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 3주기 1항 진단(11-03) 범주 C: 문서 안 같은 대상 두 값 2항목(서명자 1은 TK-90 known_open, 같은 회신의 발신 시각 1). 이번 메모 범위는 날짜·시각 쪽.
- 탐침(양성 3·대조 4) 기준 Steve 0/3·오탐 0/4. 꼴: 유일성 표지('단 한 차례·유일한') 사건에 다른 날짜, 같은 날 두 시각, 지시어('위·그') 결속 사건에 다른 날짜.
- 원인(코드 대조, 미검증): packages/claim_engine/internal_inconsistency.py(616행 check_internal_inconsistency)는 장소·서명자·금액·수량·당사자 지위·조항 원용 칸을 다루고, 날짜는 장소 비교의 시간 기준(block_last_date 646행)으로만 쓴다. 같은 사건의 날짜·시각을 속성 값으로 모아 비교하는 칸이 없다. date_verifier.py의 A-4 선후 규칙은 서로 다른 사건 사이의 순서를 보므로 이 꼴(같은 사건 두 값)을 다루지 않는다.

메모에서 정할 것
1. 대상 식별: 사건 명사 범주(회신·답변·통지·발송·해지·결의 등 — date_verifier.py EVENT_KINDS 범주 재사용 검토, 새 닫힌 장면 목록 금지)와 같은 대상 결속 조건 — 유일성 표지(단 한 차례·한 번·유일한·처음이자 마지막) 또는 지시어(위·그·해당·이 사건) + 같은 사건 명사.
2. 속성: 날짜(연·월·일)와 시각(EVI-DATE T2의 시각 정규식 — '8시간' 같은 시간 길이 제외 조건 포함)을 같은 대상의 값으로 묶는 규칙. 같은 문장·인접 문장·같은 문단 범위.
3. 다른 속성 구분(오탐 원천): 작성일·발송일·도달일·접수일처럼 한 사건의 서로 다른 단계 날짜는 다른 속성이다('작성하여 … 발송', '발송 … 도달'). 차수·순번 표지(1차·2차·두 번째)가 있으면 다른 대상이다.
4. 제외: 정정·오기 바로잡음(_LEGITIMATE_EXCEPTION_RE 재사용), 상대방 주장 인용(_is_opponent_claim_sentence), 주위적·예비적, 가정.
5. 판정: FACT_CONTRADICTION(문서 안, 기존 유형), 등급 C·SUSPICIOUS(본문 서술 상호 모순 — 모듈 머리 6항 원칙), 발췌에 두 값과 대상 명사.
6. 기존 규칙과의 관계: EVI-DATE T2·T3(서로 다른 사건 선후)·A-4 규칙과 같은 문장 쌍을 겹쳐 내지 않는 방법.
7. 공개 합성 양성 3·대조 3 이상(평가 측 탐침 문장 금지), 변형 시험 계획, 2-2 다(귀속표·train '미측정').

수용 기준(구현 PR): 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(단계별 날짜·차수 표지 대조 포함), 은퇴·고정 하락 0·오탐 0, verify_all 전체, 기존 internal_inconsistency·A-4 시험 통과.
```

### 2-19-3. #239 EVI-DATE T2·T3 구현 판정 — 수용 (11-08, head `0410246`, 사용자 '#239, 240 바로 판정')

- 11-08 사용자 승인 개정(AGENT_ROLES 2.1): 탐지 엔진 PR 수용은 CI 결과 인용 + 평가 측 비공개 탐침 + diff 검토. `verify_all` 전체는 릴리스 후보만.

```
[평가 측 판정 — #239 TK-76 3주기 EVI-DATE PR-B(T2·T3) (head 0410246, 기준 Steve 900502a), 11-08]

판정: 수용. 사용자 병합 승인 대기. T2 대상 맞추기 보강은 병합 뒤 별도 후속 PR(지시 NEXT 2-19-4).
- D1~D3 반영 확인: statute "근로기준법 제27조 제1항(해고 통지)·논리칙"(320행), TIME_RE 앞 경계 (?<![\d제])·'시' 뒤 (?!간|각|행|효|점|기|장|설)(627~628행), T3 절 경계 한정·'제N조에 따라'·'시행되는/시행된 규정' 제외(2280행 부근). 메모 2.1·3.1·3.2 수정 포함. 시험 tests/test_tk76_date_t2_t3_eval.py 16개 함수(메모 5.1 합성 13건·D2 시간 길이·D3 대조·3대 변형·진입점·2만 자 선형 시간).
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공.
- 평가 측 재실행(이 head): 판정용 새 비공개 탐침 4·5·6차(이번에 새로 지음) 기준 Steve 0/9 → 6/9(2/3)·대조 오탐 0/19. 지난 1차 6/8 → 7/8(같은 날 시각 역전 1건은 Steve도 미탐 — 하락 아님), T1 2·3차 4/4 유지, 대조 오탐 0. 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0 — 변화 0. 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). verify_all 전체: 11-08 사용자 승인 개정(AGENT_ROLES 2.1)에 따라 돌리지 않고 같은 SHA CI 결과로 갈음(CI가 같은 단계를 모두 돔).
- 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
- 남은 것(후속): T2 처분 → 통지 대상 맞추기 6원인(F1~F6) — 평가 측 사본으로 독립 8차 2/4 → 4/4·오탐 0 확인, 후속 지시로 낸다. 띄어쓰기 없는 2만 자 입력 약 43초·날짜+관형어+명사 800회 반복 약 11초는 Steve에도 있는 기존 경로(A-4 쌍 비교 등) 비용 — 별도 후속 과제.
```

### 2-20-1. #240 EVI-COPY C1 구현 판정 — 수용 (11-08, head `1272d2e`, 사용자 '#239, 240 바로 판정')

```
[평가 측 판정 — #240 TK-76 3주기 EVI-COPY C1(어미·조사만 바꾼 복사) (head 1272d2e, 기준 Steve 900502a), 11-08]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/evidence_consistency.py +51)가 평가 측 사본 521d341과 같다(평가 측 대조 diff 0). 평가 측 시험 4건 동일 + 구현 측 변형 시험 4건(어미 3꼴, 조사 3꼴, 정확 일치·가벼운 고침 섞인 어순 유지, 자기 말 서술 대조 3건).
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공.
- 평가 측 재실행(이 head): 판정용 새 비공개 탐침 4차(이번에 새로 지음) 기준 Steve 0/2 → 2/2·대조 오탐 0/3. 지난 1~3차 5/5·5/5·2/3·대조 오탐 0. 은퇴는 CI 결과 인용(은퇴 세트 비교 성공 — 후퇴 없음). 고정은 같은 제품 코드의 사본에서 82.6/81.9·FP 0 — 변화 0(세트 득점 0). verify_all 전체: 11-08 사용자 승인 개정(AGENT_ROLES 2.1)에 따라 돌리지 않고 같은 SHA CI 결과로 갈음(CI가 같은 단계를 모두 돔).
- 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
- 남은 EVI-COPY(후속): 원문 범위 확장(사실경위서로 분류되지 않은 문서)은 은퇴 오탐을 만들어 보류 — 문서 종류 판별과 함께 후속 검토.
```

- **#239 Steve 병합 `bb46bce`, #240 Steve 병합 `2969d8c`**(11-08, 사용자 지시 '#239, 240 병합', 평가 측이 expectedHeadSha `0410246`·`1272d2e`로 실행). Steve의 제품·시험 파일 = 판정 head(평가 측 대조 diff 0). 2-21(EVI-LOGIC)·2-19-4(T2 후속) 증분은 `2969d8c`에 그대로 적용된다(평가 측 `git apply --check`·관련 시험·탐침 확인).
- 11-08 개정(AGENT_ROLES 2.1)에 따라 2-21·2-22 수용 기준의 'verify_all 전체'는 'CI 전부 성공(인용)'으로 읽는다(평가 측 verify_all은 릴리스 후보만).

### 2-19-4. EVI-DATE T2 대상 맞추기 후속 구현 지시 (F1~F6) (11-08, #239 병합 뒤)

- 평가 측 사본 `16bf6de`(기준 `0410246`, 저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_date_t2_target_on_0410246.diff](patches/TK-76_cycle3_date_t2_target_on_0410246.diff).

```
[평가 측 후속 구현 지시 — TK-76 3주기 EVI-DATE T2 대상 맞추기 보강(F1~F6), 기준 Steve 2969d8c(#239·#240 병합), 11-08]

목적: #239(T2·T3)는 수용 기준을 넘겼으나, 처분 → 통지 규칙(DISPOSITION_BEFORE_NOTICE)이 같은 처분을 다른 꼴로 적으면 대상을 못 맞춰 놓친다. 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료). date_verifier.py는 Steve 2969d8c와 #239 head 0410246이 같으므로 증분이 그대로 적용된다(평가 측 확인).

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 판정용 새 탐침 4·5·6차 합 #239 6/9(T2 놓침 3), 독립 7차(T2 대상 꼴 4) 0/4, 독립 8차 2/4. 놓친 꼴은 모두 '처분 사건은 날짜와 함께 잡히나, 통지 쪽과 대상이 맞지 않거나 처분에 날짜가 붙지 않음'이다. 대조 오탐은 전부 0.
- 원인은 6가지다(줄 번호는 0410246 packages/claim_engine/date_verifier.py 기준, 공개 합성 예는 평가 측 시험 문장).

F1 [대상 추출이 관형 수식을 끌어옴] _extract_clause_slots(949행)의 대상이 '…을 근거로 원고에 대한 ○○처분'에서 '근거로원고'가 된다. 2070~2099행 require_target_match 블록은 _same_object_noun(534행) 엄격 일치 하나로만 보므로 통지 쪽 '○○부과'와 맞지 않는다.
F2 [같은 처분의 다른 표기] '감봉 2개월 징계' ↔ '감봉 징계', '직위해제의결' ↔ '직위해제 통지서'처럼 기간·사건 꼬리가 붙거나 빠지면 엄격 일치가 실패한다.
F3 [통지 목적어가 처분 사건으로 중복 생성] '그 ○○처분을 통지하였다'의 '○○처분'이 처분 슬롯으로도 만들어져, 통지와 같은 날짜의 처분 사건이 하나 더 생긴다(정상 순서 쌍과 섞임).
F4 [날짜만 있는 절의 날짜를 넘기지 않음] '피고는 2024. 10. 8. 민원 내용을 검토하여 원고에 대한 ○○처분을 결정하였다'에서 '-하여'(CLAUSE_DELIMITER_RE 136행)로 절이 나뉘고, 앞 절은 사건 낱말이 없어 1153행에서 버려진다. 1096행 날짜 물려받기는 '같은 날' 표지·연속 시각일 때만 하므로 뒤 절 처분에 날짜가 없다.
F5 [처분 사건 낱말 누락] EVENT_KIND_SURFACE_FORMS '처분'(195행)에 '의결'은 있고 '결의'가 없다. '○○ 결의를 하였는데'는 처분 사건이 생기지 않는다.
F6 [주제어 꼴 통지의 대상 빈칸] '등록 취소 통지는 …', '제적 통지서는 …'처럼 대상 표지 없이 앞 명사만 붙은 통지는 대상이 비거나 '통지서'(사건 낱말뿐)라 Z1(2074행)에서 버려진다.

고칠 것 (평가 측 사본 16bf6de, 제품 1파일 +94/−4)
- F1·F2: DISPOSITION_BEFORE_NOTICE에만, 엄격 일치가 실패하면 대체 비교 _disposition_notice_target_match를 쓴다. 양쪽 대상과 사건 표면형에서 공백을 지우고 사건 꼬리(처분·결정·의결·결의·명령·판정·통지서·통지·통보·고지·발송·송부)를 뗀 2자 이상 핵심 명사끼리, 한쪽이 다른 쪽을 담거나 숫자를 지운 두 글자 조각 겹침 ≥ 0.6(짧은 쪽 기준)이면 같은 대상. 단 차수 표지 '(\d+)\s?차'(뒤에 량·선·원·례 아님)가 양쪽 절에 있고 서로 다르면 다른 대상.
- F3: 처분 슬롯 바로 뒤가 '을/를 + 어절 0~2개 + (원고·피고·신청인·피신청인·상대방)(에게)? + 어절 0~1개 + 통지·통보·발송·송부·송달·고지'이면 그 처분 슬롯은 이 규칙의 원인으로 쓰지 않는다.
- F4: 사건 낱말 없는 절에 날짜가 있고 구분자가 쉼표·세미콜론·줄바꿈·마침표가 아니면(연결 어미) 그 날짜를 같은 문장의 바로 다음 절에 넘긴다(다음 절에 자기 날짜가 없을 때만, 한 번만). 날짜 바로 뒤가 '자'('2024. 10. 1.자 감사보고서')이면 문서 작성일이므로 넘기지 않는다.
- F5: '처분'에 결의·결의하·결의했·결의한을 더한다.
- F6: DISPOSITION_BEFORE_NOTICE에서 통지 쪽 대상이 비거나 사건 꼬리를 떼면 빈 문자열이면, 사건 낱말 바로 앞 명사 1~2어절(2자 이상, 조사로 끝나지 않음, 앞 40자 안)을 대상으로 쓴다(슬롯 자체는 바꾸지 않고 비교에만 씀).

평가 측 사전 검증(사본 16bf6de, 기준 0410246)
- 탐침 #239 → 사본: 1차 7/8 → 8/8, 4차 2/4 → 4/4, 5차 2/3 → 3/3, 6차 2/2 유지, 7차 0/4 → 4/4(7차는 F4~F6 보정에 씀), 독립 8차(보정 안 함, '-하여' 절·결의·주제어 통지·다른 낱말) 2/4 → 4/4. T1 2·3차 4/4 유지. 대조 오탐 1~8차 전부 0(합 0/48, '…일자 문서' 날짜·차수 다름·다른 사람·사전통지·정상 순서 포함).
- 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 관련 17개 파일 372건 통과(날짜·A-4·내부 모순 시험, 이 컨테이너에서 Steve도 시간 초과로 실패하는 회전 스캔 OCR 1건 제외). Steve 2969d8c에 EVI-LOGIC 증분과 함께 적용해도 관련 시험 통과·탐침 결과 같음. verify_all은 11-08 개정 규칙에 따라 사본에서 돌리지 않음.
- 시간: 2만 자 악성 입력 2종에서 #239와 같은 수준(추가 비용 없음, 앞 명사 찾기는 40자 창). 띄어쓰기 없는 2만 자 입력은 Steve 900502a·#239·사본 모두 약 43초 — 기존 경로 비용이라 이번 범위 밖(후속 과제로 따로 기록).

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_date_t2_target_on_0410246.diff(evaluator/round8-promotion) — 제품 1파일, 평가 측 시험 tests/test_tk76_date_t2_target_eval.py 12건(양성 6·대조 6). 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2: 고정 문장 틀·닫힌 장면 사전 금지(F5는 기존 사건 낱말 사전에 같은 뜻 낱말만 더함), 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표('세트 득점 0'이면 그대로 적음), 변형 시험(어순·연결 어미·같은 꼴 다른 낱말, F4 '…일자 문서' 대조), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 8세트 하락 없음, 은퇴·고정 하락 0·오탐 0(CI 인용), 기존 A-4·T2·T3 시험 통과.
```

### 2-21-1. #241 EVI-LOGIC 잔여 구현 판정 — 수용 (11-08, head `37d6ec2`, 사용자 '#241, 242 점검')

```
[평가 측 판정 — #241 TK-76 3주기 EVI-LOGIC 잔여(L1~L3) (head 37d6ec2, 기준 Steve 900502a → 현재 2969d8c), 11-08]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/evidence_consistency.py +63)가 평가 측 사본 a004116과 같다(평가 측 대조 diff 0). 평가 측 시험 7건 동일 + 구현 측 변형 시험 3건 추가(tests/test_tk76_logic_eval.py 10개 메서드, 기존 7건 수정 없음).
- 현재 Steve 2969d8c(#239·#240 병합)와 충돌 없이 병합됨(평가 측 시험 병합). #240이 같은 파일을 고쳤으나 위치가 달라 자동 병합.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공(CI는 #240 병합 전 기준 900502a로 돌았으므로 현재 Steve와의 병합은 평가 측 재실행으로 확인 — 아래).
- 평가 측 재실행(Steve 2969d8c + #241 병합본): 판정용 새 비공개 탐침 5차(이번에 새로 지음, L1·L2·L3 각 2꼴) 기준 Steve 0/6 → 5/6·대조 오탐 0/7. 지난 1~4차 6/6·4/4·4/4·2/3·대조 오탐 0(하락 없음). 관련 25개 파일 750건 통과(#243과 함께 병합한 상태에서도 관련 35개 파일 1,010건 통과). 은퇴·고정은 CI 결과 인용(은퇴 세트 비교·점수 하락 게이트 성공)과 같은 제품 코드의 사본 측정(변화 0)으로 확인. verify_all 전체는 11-08 개정 규칙(AGENT_ROLES 2.1)에 따라 돌리지 않음.
- 2-2 다: 귀속표 L1~L3 각 '세트 득점 0', train '미측정'.
- 남은 것(후속, 작음): 5차 미탐 1건은 '[인칭 대명사] 눈으로' 꼴의 직접 지각 표지를 기존 _DIRECT_RE(61행, 2주기 규칙 — '두 눈으로'만)가 받지 않아서다. 지시 범위 밖이라 이번 판정에 반영하지 않는다. 지시서 '알려진 한계'(장소 조사 없는 체재 꼴)와 함께 후속 묶음으로 둔다.
```

### 2-22-1. #242 EVI-INCONS C 설계 메모 판정 — 보완 1회 (11-08, head `c632fdb`, 사용자 '#241, 242 점검')

```
[평가 측 판정 — #242 TK-76 3주기 EVI-INCONS C 설계 메모 (head c632fdb, 기준 Steve 2969d8c), 11-08]

판정: 보완 1회(메모 고침 커밋). 범위·판정 규격(FACT_CONTRADICTION·C·SUSPICIOUS)·결속 방식(유일성 표지·지시어)·단계·차수 분리의 큰 틀은 요청과 맞다. 아래 N1~N9를 메모에 반영하면 승인하고 구현 PR로 넘어간다. 메모만 바뀌는 PR이므로 제품 시험은 해당 없음.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·Docker OCR 성공, 테스트 2종은 판정 시점 실행 중(문서만 바뀐 PR).
- 평가 측 확인 방법: 메모의 정규식을 그대로 옮겨 단독 시험(N4·N6·N7 재현), 코드 위치는 Steve 2969d8c 대조, 단계·결속 규칙의 오탐(N2·N3·N5)은 메모 규칙을 비공개 탐침 대조 꼴에 손으로 적용해 확인 — 구현 전이라 실행 검증은 미검증.

원인과 고칠 것 (절 번호는 메모 기준, 줄 번호는 Steve 2969d8c)

N1 [코드 인용 부정확] 1절·2.1·2.2·2.3·2.4절 줄 번호와 내용이 실제와 다르다.
- internal_inconsistency.py: EVENT_PREDICATE_MAP은 223행이고 범주는 사고·화재·계약·해지·해제(메모는 '177~189행, 사고·화재·계약·채무·소송'). _LEGITIMATE_EXCEPTION_RE 32행(메모 365~373), _is_opponent_claim_sentence 64행(메모 412), _TEMPORAL_SEQUENCE_WORDS_RE 394행(메모 192~201). EVI.INCONS_INTERNAL_DATE는 946행 부근(맞음).
- date_verifier.py: EVENT_KIND_SURFACE_FORMS 184행(메모 196~244), TIME_RE 626행(메모 111~119). 메모가 '그대로 재사용'한다며 옮긴 TIME_RE는 실제와 다르다(실제: ampm은 오전|오후만, '\s?' 한 칸, '경' 없음, 끝 (?!\d)). 고칠 것: TIME_RE·_parse_time_match를 date_verifier에서 import해 그대로 쓴다고 적는다. 새벽·아침·저녁·밤·'경'을 넓히려면 새 정규식으로 따로 적고 2만 자 선형 시간 시험을 계획에 넣는다.
- 기준 커밋을 2969d8c로 고친다.

N2 [단계 혼합 — 정상 경과 오탐] 2.3(1) ISSUE_SEND에 결정 행위(처분·결정·결의·의결·해지·해제)와 알림 행위(통지·통보·고지·발송·회신)를 함께 넣었다. 그러면 '…일 원고에 대한 정직 처분을 결정하고, …일 원고에게 위 처분을 통지하였다'(처분 → 통지 정상 경과, EVI-DATE T2가 순서를 보는 쌍)가 (처분, ISSUE_SEND) 두 값으로 묶여 모순이 된다. 고칠 것: DECIDE(처분·결정·결의·의결·해지·해제·취소·철회·체결·합의 — 법률행위·결정 자체)와 NOTIFY_SEND(통지·통보·고지·발송·발신·송부·회신·답변·교부)를 다른 단계로 나눈다. ARRIVE_RECEIVE에 '도착'을 더한다(도착 꼴 누락). 2.6(1)의 '중복 없음' 논증도 이 분리를 전제로 다시 쓴다.

N3 [결속 키에 주체·논항 위치 없음 — 별건 결속] 2.1(2)·2.2(3) 결속 키가 (사건 명사, 단계)뿐이다. (a) 서로 다른 당사자의 같은 명사(원고의 회신·피고의 회신)가 유일성 표지 하나로 문서 전체에서 묶인다. (b) 지시어+명사가 다른 서술어의 수식어 안에 있을 때('[지시어+사건 명사]에 대한 다른 서면을 …일 보냈다' 꼴, '위 통지의 내용을 …일 확인' 꼴) 그 날짜는 회신·통지의 날짜가 아닌데 같은 단계 값으로 묶인다(평가 측 비공개 대조 꼴과 같은 구조). 고칠 것: 키에 행위 주체(주격 '은/는/이/가' 당사자, 없으면 문장 주어 승계)를 넣고 주체가 다르면 비교하지 않는다. 지시어+사건 명사가 날짜를 받는 서술어의 직접 논항(주어·목적어 '을/를·은/는·이/가')일 때만 결속하고, 뒤에 '에 대한·에 대하여·에 관한·에 따른·의·을 받은·을 받고'가 오면 결속하지 않는다.

N4 [복합 사건 명사의 머리] '해지 통지', '시정명령 통지', '이행청구 통지'처럼 사건 명사가 둘 이어지면 무엇이 대상인지 정하지 않았다. 메모의 _ANAPHORA_EVENT_RE는 '그 해지 통지는 …'에서 명사를 '해지'로 잡는다(평가 측 정규식 단독 시험). 고칠 것: 이어진 사건 명사 중 마지막(머리)을 키로, 앞은 내용 수식(content)으로 보고, 지시어 결속도 머리 명사로 맞춘다(content가 서로 다르면 별건).

N5 [문서 일자 '…자'를 행위 날짜로 봄] 2.3(1) 마지막 예('위 통지는 3월 5일자였으나 … 그 통지를 3월 8일에 하였다'를 같은 ISSUE_SEND로 비교)는 정상 경과다 — '…일자/…자'는 문서에 적힌 작성·표시 일자이고 발송일과 다를 수 있다. 고칠 것: 날짜 바로 뒤가 '자'('…일자', '…자 통지')이면 DATED(문서 일자) 단계로 두고 다른 단계와 비교하지 않는다. 그 예는 대조로 옮긴다.

N6 [유일성 표지가 부정 표현을 잡음] _UNIQUENESS_MARKER_RE가 '단 한 번도 회신하지 않았다'의 '단 한 번'을 잡는다(평가 측 정규식 단독 시험). 2.4(4) 부정 제외가 절 서술어만 보면 다른 절의 같은 명사를 유일 사건으로 묶을 수 있다. 고칠 것: 표지 뒤 '도'면 유일성 표지가 아니다((?!\s*도)).

N7 [지시어 앞 경계 없음] _ANAPHORA_EVENT_RE의 (?:위|그|해당|…|동)에 앞 경계가 없어 '행위 통지'→'위 통지', '행동 통지'→'동 통지'로 잡힌다(평가 측 정규식 단독 시험). 고칠 것: 앞에 (?<![가-힣0-9]).

N8 [양성 3이 상대방 서면 탄핵 서술] 3.1 양성 3 '피신청인은 위 통지를 …에 하였다고 기재하여 앞뒤가 맞지 않는다'는 작성자가 상대방 서면의 모순을 지적하는 문장이다. 작성자 자신의 모순이 아니고, 2.4(2) 상대방 주장 인용 제외와도 충돌한다. 고칠 것: 작성자 자신의 서술(지시어 결속 + 다른 날짜)로 바꾸고, 이 문장은 대조로 옮긴다.

N9 [기존 규칙과의 관계 방향, 정의 빈칸]
- 2.6(2): 새 규칙이 발화하면 기존 EVI.INCONS_INTERNAL_DATE를 억제한다고 했다. 이것은 기존 판정을 바꾼다(공용 입력·기존 상태 불변 원칙, #234 M5 선례). 고칠 것: 기존 규칙이 이미 낸 (명사, 블록 쌍)에는 새 규칙이 양보한다. 기존 EVENT_PREDICATE_MAP의 해지·해제가 새 범주와 겹친다는 것을 명시한다.
- 2.1(2) 조건 C는 A·B를 다시 말할 뿐이라 정의가 없다. 지우거나 A·B와 다른 조건으로 정의한다.
- 작은 것: 시각에 '경·무렵·쯤·전후'가 붙으면 60분 미만 차이는 모순으로 보지 않는다. 기한 제외 '부터\s*.*?까지'는 같은 절 안으로 한정한다. 3.2 대조에 N2(처분 결정 → 통지)·N3(다른 주체·수식어 속 지시어)·N5('…일자' 문서 일자) 꼴을 더한다.

제출물·수용 기준
- 메모 고침 커밋 1개(제품·시험 코드 0줄). 평가 측이 N1~N9 반영을 확인하면 승인 → Steve 병합(사용자 승인) → 구현 PR.
- 구현 PR 수용 기준은 요청서(NEXT 2-22) 그대로: 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(단계별 날짜·차수·주체 대조 포함), 은퇴·고정 하락 0·오탐 0(CI 인용), 기존 internal_inconsistency·A-4·T2 시험 통과.
```

### 2-19-5. #243 EVI-DATE T2 대상 맞추기 보강 판정 — 수용 (11-08, head `8ddf851`, 사용자 '#243도 평가')

```
[평가 측 판정 — #243 TK-76 3주기 EVI-DATE T2 대상 맞추기 보강(F1~F6) (head 8ddf851, 기준 Steve 2969d8c), 11-08]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/date_verifier.py +94/−4)가 평가 측 사본 16bf6de와 같다(평가 측 대조 diff 0). 평가 측 시험 12건 동일 + 구현 측 변형 시험 추가(어순·연결 어미·같은 꼴 다른 낱말, '…일자 문서'·차수 대조).
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공(같은 SHA에 중복으로 걸린 두 번째 CI 실행은 판정 시점 진행 중, 실패 0).
- 평가 측 재실행(이 head): 판정용 새 비공개 탐침 9차(이번에 새로 지음 — 관형 수식 대상·결의·기간 수식·주제어 통지, 대조에 '…일자 문서'·차수·다른 사람·정상 순서·조사 절 날짜) 기준 Steve 1/4 → 4/4·대조 오탐 0/5. 지난 1~8차 하락 없음(8/8·4/4·4/4·4/4·3/3·2/2·4/4·4/4), 대조 오탐 합 0/48. #241과 함께 Steve에 병합한 상태에서 관련 35개 파일 1,010건 통과, 다른 유형 탐침(LOGIC·COPY·NUM·FORM) 결과 변화 없음. 은퇴·고정은 같은 제품 코드의 사본 측정(은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 82.6/81.9·FP 0 — 변화 0)과 CI 결과 인용. verify_all 전체는 11-08 개정 규칙(AGENT_ROLES 2.1)에 따라 돌리지 않음.
- 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
- 남은 것(별도 후속 과제): 띄어쓰기 없는 2만 자 입력 약 43초·날짜+관형어+명사 800회 반복 약 11초는 Steve에도 있는 기존 경로(A-4 쌍 비교 등) 비용 — 이 PR 범위 밖.
```

### 2-22-2. #242 EVI-INCONS C 설계 메모 2차 판정 — 조건부 승인 (11-08, head `1871edf`, 사용자 '#242 보완완료')

```
[평가 측 판정 — #242 TK-76 3주기 EVI-INCONS C 설계 메모 보완본 (head 1871edf, 기준 Steve 2969d8c), 11-08]

판정: 조건부 승인. N1~N9는 모두 반영됐다(줄 번호·TIME_RE import, DECIDE·NOTIFY_SEND·DATED 단계 분리와 '도착', 주체·직접 논항 제약, 복합 명사 머리, '…자' 문서 일자, '(?!\s*도)', 지시어 앞 경계, 양성 3 교체·탄핵 서술 대조, 기존 규칙 우선·조건 C 삭제·근사 시각·기한 절 한정). 아래 C1을 구현 PR에서 반영하는 조건으로 메모를 승인한다(메모 재제출 불요, 구현 PR에서 메모 2.1(4) 정규식도 함께 고친다).
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·Docker OCR 성공, 테스트 2종은 판정 시점 실행 중(문서만 바뀐 PR).
- 평가 측 재실행: 메모 2.1(4) _ANAPHORA_EVENT_RE·_UNIQUENESS_MARKER_RE를 그대로 옮겨 단독 시험. 지시어 앞 경계('행위 통지'·'행동 통지' 미매칭)·복합 명사 머리('그 해지 통지'→해지/통지)·'단 한 번도' 제외는 의도대로 동작. 2만 자 악성 입력 0.002초.

C1 [지시어 정규식 — 기본 꼴 오분해·'서' 꼴 누락, 평가 측 단독 시험 재현] 메모 2.1(4) 조건 B
- (a) '위 통지를 발송하였다'를 content='통지를'·head='발송'으로 나눈다. 원인: 선택 그룹 (?:(?P<content>…)\s*)?가 탐욕적이라 내용 수식이 있는 경로를 먼저 시도하고, 조사를 포함한 '통지를'을 content로 삼은 뒤 서술 명사 '발송'을 head로 잡는다.
- (b) '위 통지서는', '그 회신서를', '위 답변서에'는 아예 잡히지 않는다. 원인: head 뒤 부정 전방탐색 (?!\s*(?:…|서))가 '서'를 막아, 2.1(1)의 '통지서→통지' 정규화와 어긋난다.
- 고칠 것: 선택 그룹을 게으르게((?:(?P<content>[가-힣]{2,12}?)\s*)??) 하고, head 뒤를 (?P<head>…)(?P<doc>서)?(?!\s*(?:사건 명사))로 바꾼다. 평가 측 단독 시험에서 '위 통지를 발송'→(없음, 통지), '위 통지서는'→(없음, 통지, 서), '그 해지 통지서를'→(해지, 통지, 서), '위 시정명령 통지를'→(시정명령, 통지), '해당 해지 통보를'→(해지, 통보), '행위 통지' 미매칭, 2만 자 악성 입력 0.003초.
- 시험: 위 꼴을 구현 PR의 3대 변형 시험 ②에 넣는다.

다음 단계: 사용자 병합 승인 → Steve 병합 → 구현 PR(메모 3.3 시험 계획 + C1). 구현 PR 수용 기준은 요청서(NEXT 2-22)와 같다: 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(단계·차수·주체 대조 포함), 은퇴·고정 하락 0·오탐 0(CI 인용), 기존 internal_inconsistency·A-4·T2 시험 통과.
```

- **#241 Steve 병합 `d50c52a`, #243 Steve 병합 `0dd8ec5`, #242 Steve 병합 `a89311c`**(11-08, 사용자 지시 '#241,242,243 병합', 평가 측이 expectedHeadSha `37d6ec2`·`8ddf851`·`1871edf`로 실행). Steve `packages/`·`tests/` = 평가 측 병합 시험본(관련 35개 파일 1,010건 통과). #242는 점수 하락 게이트가 동시 실행 정책으로 취소돼 재실행 후 병합.

### 2-22-3. EVI-INCONS C 구현 요청 (#242 병합 뒤, 구현 조건 C1) (11-08)

```
[평가 측 구현 요청 — TK-76 3주기 EVI-INCONS C 구현(EVI.INCONS_SAME_EVENT_DATETIME), 기준 Steve a89311c(#242 메모 병합), 11-08]

#242 설계 메모(docs/handoff/requests/TK-76_cycle3_evi_incons_c_design_memo.md, 보완본 1871edf)를 조건부 승인했고 Steve에 병합했다. 메모대로 구현 PR을 낸다. 아래 C1은 필수 조건이며, 구현 PR에서 메모 2.1(4) 정규식도 함께 고친다.

C1 [지시어 정규식 — 기본 꼴 오분해·'서' 꼴 누락, 평가 측 단독 시험 재현] 메모 2.1(4) 조건 B _ANAPHORA_EVENT_RE
- (a) '위 통지를 발송하였다'를 content='통지를'·head='발송'으로 나눈다. 원인: 선택 그룹 (?:(?P<content>…)\s*)?가 탐욕적이라 내용 수식이 있는 경로를 먼저 시도한다.
- (b) '위 통지서는', '그 회신서를', '위 답변서에'를 잡지 못한다. 원인: head 뒤 부정 전방탐색 (?!\s*(?:…|서))가 '서'를 막는다(메모 2.1(1) '통지서→통지' 정규화와 어긋남).
- 고칠 것: (?:(?P<content>[가-힣]{2,12}?)\s*)?? (게으른 선택) 그리고 (?P<head>사건 명사)(?P<doc>서)?(?!\s*(?:사건 명사)). 평가 측 단독 시험: '위 통지를 발송'→(없음, 통지), '위 통지서는'→(없음, 통지, 서), '그 해지 통지서를'→(해지, 통지, 서), '위 시정명령 통지를'→(시정명령, 통지), '해당 해지 통보를'→(해지, 통보), '행위 통지' 미매칭, 2만 자 악성 입력 0.003초.

구현 범위(메모 그대로): internal_inconsistency.py에 같은 사건(유일성 표지·지시어 결속)의 두 날짜·시각 비교 — 주체·복합 명사 머리·7단계(DATED·DRAFT·DECIDE·NOTIFY_SEND·ARRIVE_RECEIVE·SUBMIT_FILE·EFFECTIVE)·차수 분리, 제외 5종, FACT_CONTRADICTION·C·SUSPICIOUS·MEDIUM, 기존 EVI.INCONS_INTERNAL_DATE 우선(새 규칙 양보), TIME_RE·_parse_time_match는 date_verifier에서 import.

제출물·수용 기준
- 구현: packages/claim_engine/internal_inconsistency.py, 시험 tests/test_tk76_incons_c_eval.py(메모 3.1 양성 3·3.2 대조 7 + 3대 변형(C1 꼴 포함) + 2만 자 선형 시간), 메모 2.1(4) 정규식 수정.
- 2-2: 닫힌 장면 사전·고정 문장 틀 금지(사건 명사는 기존 범주 재사용), 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표('세트 득점 0'이면 그대로), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 판정 때 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(단계·차수·주체·문서 일자 대조 포함), 기존 internal_inconsistency·A-4·T2 시험 통과, 은퇴·고정 하락 0·오탐 0(CI 인용).
```

## 2-23. TK-76 3주기 EVI-INCONS 산식 후속 구현 지시 (Q1~Q3, 옛 '단위 대') (11-08, 사용자 ''대' 수량 산식 착수 지시')

- 평가 측 사본 `757ca53`(기준 `0dd8ec5`, 저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_calc_label_on_0dd8ec5.diff](patches/TK-76_cycle3_calc_label_on_0dd8ec5.diff). 11-05 진단('단위 대')을 정정.

```
[평가 측 구현 지시 — TK-76 3주기 EVI-INCONS 산식 후속(Q1~Q3, 옛 이름 '단위 대 수량 산식'), 기준 Steve a89311c(제품 코드는 0dd8ec5와 같음), 11-08]

목적: 서술형 산식의 결과 이름표·달력 시점 이름표 때문에 틀린 합계를 놓치는 꼴을 잡는다. 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료).

진단 정정: 11-05 기록의 '단위 대 수량 산식 미탐'은 원인을 잘못 짚었다. 단위 '대'는 원인이 아니다('47대와 52대를 더하면 89대'는 지금도 잡힌다). 실제 원인은 아래 Q1~Q3이며, 금액 산식에서도 같은 꼴이 놓친다(평가 측 재현).

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 지난 산식 탐침 2차(N월분) 3/4 — 놓친 1건이 이 꼴. 새 4차(이번에 지음, 보정에 씀) Steve 0/5, 새 5차(독립, 보정 안 함) Steve 0/5. 대조 오탐 0.

원인과 고칠 것 (줄 번호는 Steve 0dd8ec5 packages/claim_engine/calculation.py)

Q1 [미탐] 결과 이름표의 '고'로 끝나는 명사를 연결 어미로 읽음 — 148행 _CLAUSE_BREAK_RE, 545행
- 원인: _CLAUSE_BREAK_RE = [가-힣](?:고|며|으나|지만|는데)(?:\s|,)가 '…를 더하면 출고 대수는 N대'의 '출고 '를 연결 어미 '-고'로 읽어 결과가 다른 절이라고 보고 버린다. 입고·신고·광고·재고·원고·피고처럼 '고'로 끝나는 명사가 결과 이름표에 오면 금액·수량 모두 놓친다('판매 대수는'은 잡힘 — 평가 측 재현).
- 고칠 것: _VERBAL_CLAUSE_BREAK_RE = re.compile(r"(?:하|되|했|됐|였|었|았|있|없|않|이)(?:고|며|으나|지만|는데)(?:\s|,)|,")를 두고, 545행에서 after_ops 안의 마지막 연산 서술어(_OP_PREDICATE_RE) 앞부분은 기존 _CLAUSE_BREAK_RE로, 뒤부분(결과 이름표 구간)은 _VERBAL_CLAUSE_BREAK_RE로 본다. 연산 서술어가 없으면 기존 그대로. '더하였고 남은 …'·'합하면, …'(쉼표)·'더하고 남은 …'은 계속 절 경계다(평가 측 대조 확인).

Q2 [미탐] 결과 이름표 안의 수를 피연산자로 넣음 — 527행 res_token = tokens[-1] 다음
- 원인: '…를 더하면 2분기 처리 건수는 N건'의 '2분기'가 연산 서술어 뒤인데도 피연산자로 들어가 셋을 더한다.
- 고칠 것: ops에서, 결과를 이끄는 연산 서술어(_OP_PREDICATE_RE 일치 중 '…기'로 끝나는 중위 서술어 '곱하기'는 제외) 중 마지막 것보다 뒤에 있는 토큰을 뺀다. 단 그 앞에 피연산자가 2개 이상 남을 때만(그렇지 않으면 그대로) — '8 곱하기 26,000은 …' 같은 중위 산식 보존(tests/test_tk76_cycle3_calculation.py 기존 시험, 평가 측 첫 시안에서 깨졌다가 이 조건으로 해결).

Q3 [미탐] 달력 시점('N월'·'N분기'·'N반기')을 수량으로 읽음 — 310행 unit_is_ordinal_label, 153행 근처
- 원인: '1월 접수 37건과 2월 접수 45건을 더하면 …'의 '1월'·'2월'을 피연산자로 읽는다. 'N월분'(N1)·차수(G3)는 이름표로 보지만 맨 달력 시점은 보지 않는다.
- 고칠 것: _CALENDAR_LABEL_RANGE = {"월": (1, 12), "분기": (1, 4), "반기": (1, 2)}를 두고, unit_part가 이 중 하나이고 값이 범위 안이며 바로 뒤가 연산 기호가 아니면 이름표(True). 'N개월'(기간의 양)은 unit_part가 '개월'이라 해당 없음, '13월'처럼 범위 밖이면 이름표 아님.

평가 측 사전 검증(사본 757ca53, 기준 0dd8ec5)
- 탐침: 새 5차(독립, 보정 안 함) Steve 0/5 → 4/5·대조 오탐 0/6(남은 1건은 피연산자 앞에 '수+일반 명사' 이름표가 붙은 꼴 — 이번 범위 밖). 4차(보정에 씀) 0/5 → 4/5·0/6(남은 1건은 기존 '할인' 가드 158행 TAX_DEDUCTION_GUARD_RE — 의도된 제외, 범위 밖). 지난 산식 탐침: N월분 2차 3/4 → 4/4, PR1 4차 8/9 → 9/9, 1·3차·5·6차 유지, 대조 오탐 전부 0.
- 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 관련 36개 파일 882건 통과. 하드코딩·시험 약화·평가 세트 문구 점검 통과('의심 없음'). 악성 입력 3종(띄어쓰기 없는 2만 자, 같은 문장 400회, '출고' 6천 회) 0.06초 이내 — Steve와 같은 수준. verify_all은 11-08 개정 규칙에 따라 사본에서 돌리지 않음.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_calc_label_on_0dd8ec5.diff(evaluator/round8-promotion) — 제품 1파일(+31/−1), 평가 측 시험 tests/test_tk76_calc_label_eval.py 12건(양성 6·대조 6, 기준에서 양성 6건 실패). 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2: 닫힌 낱말 사전·고정 문장 틀 금지(Q1은 용언 어미 꼴, Q3은 달력 단위 값 범위 — 명사 목록을 만들지 않는다), 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표('세트 득점 0'), 변형 시험(어순·연결 어미·같은 꼴 다른 낱말, 금액·수량 각각), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0, 지난 산식 탐침 하락 없음, 은퇴·고정 하락 0·오탐 0(CI 인용), 기존 산식 시험 통과.
```

## 2-24. TK-76 3주기 EVI-OVR 잔여 5꼴 구현 지시 (O1~O5) (11-08, 사용자 'EVI-OVR 잔여 4꼴 처리 이번 릴리스 포함')

- 평가 측 사본 `c0a17e5`(기준 `0dd8ec5`, 저장소 밖)로 사전 검증. 증분: [patches/TK-76_cycle3_ovr_residual_on_0dd8ec5.diff](patches/TK-76_cycle3_ovr_residual_on_0dd8ec5.diff). 상태표의 '4꼴'은 #230 1차 판정 집계, 수용 판정 기록은 5꼴.

```
[평가 측 구현 지시 — TK-76 3주기 EVI-OVR 잔여 5꼴(O1~O5), 기준 Steve a89311c(제품 코드는 0dd8ec5와 같음), 11-08]

목적: #230(EVI-OVR) 수용 때 남긴 미탐 5꼴을 잡는다(사용자 결정 11-08: 이번 릴리스 포함). 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 공용 입력(exhibit_rows·parse_exhibits)은 바꾸지 않는다(1절, #126 선례).

진단 (평가 측 재실행, 저장소 밖 비공개 탐침 — 문장 비공개)
- 지난 EVI-OVR 탐침을 현재 Steve로 다시 돌림: 3차 2/6, 5차 5/6 — 놓친 5건이 아래 O1~O5와 하나씩 맞는다. 1차 8/9의 미탐 1건('전부' 변제 주장 대 일부 금액 서증)은 5꼴 밖(후속).

원인과 고칠 것 (줄 번호는 Steve 0dd8ec5 packages/claim_engine/evidence_consistency.py)

O1 [미탐] 상대방 의사표시의 주체를 잘못 고름 — 986행 _find_clause_subject, 1263행
- 원인 (가): 주체 표지에 소유격 '의'를 같이 넣고 마지막 당사자를 고른다. '피고가 원고의 청구에 동의하였다'의 주체를 '원고'(=발신인)로 보아 일방통지 과장을 내지 않는다. (나): 당사자 뒤 동격 명사('피고 회사가', '피고 법인이')를 주체로 받지 않아 주체 미정 → 제외된다(평가 측 재현).
- 고칠 것: 먼저 주격만 본다 — (?P<p>원고|피고|신청인|피신청인|채권자|채무자)(?:\s*측|\s+[가-힣]{1,4}?)?(?:은|는|이|가)(?![가-힣]) 중 마지막. 없을 때만 기존 정규식(소유격 포함)으로 돌아간다.

O2 [미탐] '소갑/소을' 목록 줄이 행이 되지 않음 — 1013행 앞(행 색인 직전)
- 원인: 공용 호증 문법(exhibits.py 58행 parse_exhibits)이 '소갑 제1호증'을 '갑 1호증'(시작 위치 1)로 풀고, _exhibit_lines(462행)는 줄 첫머리(위치 0)에 호증이 있는 줄만 행으로 받아 '1. 소갑 제1호증 …' 목록 줄이 행이 되지 않는다(no_row). 본문 인용은 ('갑', 1)로 풀리므로 키는 맞다.
- 고칠 것: 이 검사 안에서만 _SO_EXHIBIT_LINE_RE = ^\s*(?:\d{1,2}\s*[.)]\s*|[-*•·]\s*)?소(?P<party>갑|을)\s*제?\s*(?P<num>\d+)\s*호증(?P<rest>[^\n]*)$ (re.M)로 읽은 줄을, 같은 키 행이 없을 때 보충 행(party='갑'/'을', name=rest)으로 rows에 더한다. exhibit_rows·parse_exhibits는 그대로(시험으로 확인).

O3 [미탐] 맨 '이행하였다' 완료 단정 — 657~663행 COMPLETION_PREDICATE_RE
- 원인: '이행'은 명사 자리(이행을 마쳤다)에서만 보고, '…의무를 (모두) 이행하였다'의 동사 꼴은 완료 술어에 없다.
- 고칠 것: 둘째 갈래 끝에 이행(?:하였|했)(?!는지|는가|다면|더라도|으면)[가-힣]*|이행한(?=\s|$)를 더한다(의문·가정 어미 제외).

O4 [미탐] '알고 있었다' 꼴의 인식 단정 — 639행 INTENT_STATE_RE
- 원인: 내심 상태는 고의·악의·인식·공모·통모 낱말과 '-려는 의사' 꼴만 보고, 'X임을/사실을 (처음부터) 알고 있었다·알았다·알면서'를 보지 않는다.
- 고칠 것: (?<![가-힣])(?:[가-힣]{1,15}?(?:임|음)|사실|점|것)을\s*(?:[가-힣]{1,5}\s+)?알(?:고\s*있|았|면서|고서)를 더한다(앞 어절 길이 제한·어절 시작 경계 필수 — 아래 사전 검증 참고). '알았는지 확인할 수 없다'처럼 부정·의문은 기존 상한 문맥과 대조 시험으로 확인(평가 측 대조 오탐 0).

O5 [미탐] 전칭 부정('한 번도 … 적이 없다') — 1192행 전칭_전기간
- 원인: 전칭_전기간은 '항상·매번·모든·계속·내내·줄곧·일체' 낱말만 본다. '단 한 번도/한 차례도/전혀 … 한 적이·일이·바가 없다'는 전 기간에 대한 단정인데 범주가 없다.
- 고칠 것: UNIVERSAL_NEGATION_RE = (?:(?:단\s*)?한\s*(?:번|차례)도|전혀|결코)\s*[^.!?]{0,30}?(?:적|일|바|사실)(?:이|은|는)?\s*없 를 두고, 1192행 낱말 일치가 없을 때 이 꼴이면 전칭_전기간으로 더한다.

평가 측 사전 검증(사본 c0a17e5, 기준 0dd8ec5)
- 탐침: 3차 2/6 → 6/6, 5차 5/6 → 6/6, 1차 8/9·2차 5/5 유지, 대조 오탐 0(합 0/30). 새 6차(독립, 보정 안 함 — 동격 주체·소갑·맨 이행·앎·전칭 부정, 대조에 자기 측 동격 주체·상대방 발신 소을·의문형 이행·부정된 앎·서증 없는 전칭 부정·정상 영수증) Steve 0/5 → 5/5, 대조 오탐 1/7 — 이 1건(자기 측 확인서로 자기 측 동의를 증명하는 꼴)은 Steve도 똑같이 내는 기존 동작(이번 수정과 무관, 후속).
- 관련 25개 파일 702건 통과(평가 측 시험 13건 포함), 다른 유형 탐침(LOGIC·COPY·FORM·NUM) 결과 변화 없음. 바뀐 함수·정규식은 이 모듈 밖에서 쓰지 않음(평가 측 확인). 은퇴 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0).
- 하드코딩·시험 약화·평가 세트 문구 점검 통과('의심 없음'). 새 정규식 악성 입력(띄어쓰기 없는 2만 자 등 6종) 최악 0.004초. 평가 측 첫 시안의 O4 정규식은 앞 어절 길이 제한이 없어 2만 자 3.3초(이차 시간)였고, 길이 제한 {1,15}과 어절 시작 경계 (?<![가-힣])로 고쳤다 — 그대로 따른다. verify_all은 11-08 개정 규칙에 따라 사본에서 돌리지 않음.

제출물·수용 기준
- 평가 측 사본 증분: docs/handoff/patches/TK-76_cycle3_ovr_residual_on_0dd8ec5.diff(evaluator/round8-promotion) — 제품 1파일(+44/−2), 평가 측 시험 tests/test_tk76_ovr_residual_eval.py 13건(양성 6·대조 6·공용 입력 불변 1, 기준에서 양성 6건 실패). 그대로 적용해도 되고 같은 구조로 다시 써도 된다.
- 2-2: 닫힌 장면 사전·고정 문장 틀 금지(O1~O5는 꼴 규칙, 기존 범주 사전에 낱말을 더하지 않음), 평가 측 탐침 문장 사용 금지. 2-2 다: 귀속표(꼴별 '세트 득점 0'), 변형 시험(어순·연결 어미·같은 꼴 다른 낱말, O3·O4 의문·부정 대조), train '미측정'.
- 수용: CI 전부 성공, 평가 측이 새로 짓는 비공개 탐침 양성 2/3 이상·대조 오탐 0(기존 동작으로 Steve와 같은 판정은 따로 표시), 지난 EVI-OVR 탐침 하락 없음, 은퇴·고정 하락 0·오탐 0(CI 인용), 기존 EVI-OVR·EVI-LOGIC 시험 통과.
- 범위 밖(후속): '전부' 변제 주장 대 일부 금액 서증, 자기 측 확인서로 자기 측 의사표시를 증명하는 꼴(기존 동작 검토).
```

### 2-23-1. #244 산식 후속 Q1~Q3 판정 — 수용 (11-09, head `7d85a77`, 사용자 '#244,245,246 확인')

```
[평가 측 판정 — #244 TK-76 3주기 EVI-INCONS 산식 후속(Q1~Q3) (head 7d85a77, 기준 Steve a89311c), 11-09]

판정: 수용. 사용자 병합 승인 대기.
- 제품 코드(packages/claim_engine/calculation.py +31/−1)가 평가 측 사본 757ca53과 같다(평가 측 대조 diff 0). 평가 측 시험 12건 동일 + 구현 측 변형 시험 추가(금액·수량 각각 어순·연결 어미·같은 꼴 다른 낱말).
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공.
- 평가 측 재실행: 판정용 새 비공개 탐침 6차(이번에 새로 지음 — '고' 명사 이름표·결과 이름표 속 시점 수·달력 시점·뺄셈 공제, 대조에 맞는 합계·쉼표 절 경계·연결 어미) 기준 Steve 0/4 → 4/4·대조 오탐 0/5. 지난 산식 탐침 하락 없음. #245·#246과 함께 Steve에 병합한 상태에서 관련 60개 파일 1,591건 중 실패 1건은 #245 쪽 시험(아래 #245 판정) — 산식 시험은 전부 통과. 은퇴·고정은 CI 결과 인용 + 같은 제품 코드의 사본 측정(변화 0).
- 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
```

### 2-24-1. #245 EVI-OVR 잔여 5꼴 판정 — 보완 1회(작음) (11-09, head `c8eaea6`)

- 평가 측 사본 보완 증분: [patches/TK-76_cycle3_ovr_followup_on_c8eaea6.diff](patches/TK-76_cycle3_ovr_followup_on_c8eaea6.diff). B2·B3은 평가 측 지시(2-24) 결함.

```
[평가 측 판정 — #245 TK-76 3주기 EVI-OVR 잔여 5꼴(O1~O5) (head c8eaea6, 기준 Steve a89311c), 11-09]

판정: 보완 1회(작음). 제품 코드는 평가 측 사본 c0a17e5와 같다(diff 0). 아래 B1~B3을 한 커밋으로 고치면 수용한다. B2·B3은 평가 측 지시(2-24) 정규식의 결함으로 평가 측 책임이다.
- CI 결과 인용: 테스트 3종(SQLite·PostgreSQL·합산) 실패 — 원인은 B1(구현 측 변형 시험). 점수 하락 게이트·CodeQL·은퇴 세트 비교·Docker OCR 성공.
- 평가 측 재실행: 판정용 새 비공개 탐침 7차(이번에 새로 지음) 기준 Steve 1/5 → 5/5·대조 오탐 1/6 — 오탐 1건이 B2. 지난 1~6차 하락 없음.

원인과 고칠 것
B1 [시험 결함, CI 실패 원인] tests/test_tk76_ovr_residual_eval.py 58~84행 test_variations_o1_to_o5…
- 원인: 양성 변형의 서증명 '독촉장'(64행)·'요청서'(O3 변형)는 EVIDENCE_KIND_CATEGORIES(evidence_consistency.py 606행 근처) 7범주에 없는 이름이라 판정 대상(no_cat)이 아니다. 시험이 제품이 하지 않기로 한 일을 요구한다.
- 고칠 것: 범주 낱말로 바꾼다('독촉장'→'통고서', '요청서'→'견적서' — 평가 측 확인). 범주 사전에 낱말을 더하지 않는다(2-2).
B2 [오탐, 평가 측 지시 결함] O4 의문·가정형 앎 — evidence_consistency.py 643행 INTENT_STATE_RE
- 원인: '알(?:고\s*있|았|면서|고서)'가 '…임을 알았는지는 알 수 없다'·'알고 있었는지'·'알았다면'을 앎 단정으로 읽는다(평가 측 새 7차 대조에서 재현 — 사전 검증 대조에는 '확인할 수 없다' 가드가 함께 있어 드러나지 않았다).
- 고칠 것: (?:알(?:고\s*있|았)(?!었?(?:는지|는가|던가|던지|다면|더라도|으면|을지))|알면서|알고서). '었'을 전방탐색 안에 두어야 '알고 있었는지'에서 되짚어 빠져나가지 않는다(평가 측 첫 고침에서 확인).
B3 [미탐, 평가 측 지시 결함] O5 전칭 부정 조사 — UNIVERSAL_NEGATION_RE
- 원인: (?:적|일|바|사실)(?:이|은|는)?\s*없 — '…한 바가 없다'·'그런 일도 없다'의 조사 '가·도'가 빠졌다.
- 고칠 것: (?:이|가|은|는|도)?로 넓힌다.

평가 측 사전 검증(사본 위 보완 커밋, 기준 c0a17e5 = #245 제품)
- B1을 고친 구현 측 변형 시험 + 평가 측 시험 + 보완 시험 35건 통과. 관련 25개 파일 713건 통과. 탐침 7차 5/5·0/6, 6차 5/5·1/7(기존 동작 1건 — 2-24 기록), 3·5차 6/6·0/8, 1차 8/9·0/12, 2차 5/5·0/2. 새 정규식 악성 입력 최악 0.007초.
- 증분: docs/handoff/patches/TK-76_cycle3_ovr_followup_on_c8eaea6.diff — 제품 1파일 2줄, 평가 측 시험 tests/test_tk76_ovr_followup_eval.py 11건(의문·가정 4·앎 단정 3·문서 1·전칭 부정 조사 3).

수용 기준: CI 전부 성공, 평가 측 새 탐침 대조 오탐 0(기존 동작 표시분 제외), 지난 탐침 하락 없음.
```

### 2-22-4. #246 EVI-INCONS C 구현 판정 — 보완 1회(작음) (11-09, head `e6622fe`)

- 평가 측 사본 보완 증분: [patches/TK-76_cycle3_incons_c_d1_on_e6622fe.diff](patches/TK-76_cycle3_incons_c_d1_on_e6622fe.diff).

```
[평가 측 판정 — #246 TK-76 3주기 EVI-INCONS C 구현(EVI.INCONS_SAME_EVENT_DATETIME, C1) (head e6622fe, 기준 Steve a89311c), 11-09]

판정: 보완 1회(작음). 메모·C1을 따른 구현이며 탐지 기준은 충족한다. 아래 D1(사용자에게 보이는 결과 제목 결함)을 고치면 수용한다.
- C1 반영 확인: _ANAPHORA_EVENT_RE(internal_inconsistency.py 1203행)에 게으른 선택(??)·'서' 허용·앞 경계. 메모 2.1(4) 정규식 수정 포함.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·Docker OCR 성공, 테스트 2종은 판정 시점 실행 중. 평가 측 병합본 시험에서 #246 시험 파일은 모두 통과.
- 평가 측 재실행: 요청 때 비공개 탐침 1차 Steve 0/3 → 2/3·대조 0/4. 판정용 새 2차(이번에 새로 지음 — 유일성·지시어·시각, 대조에 작성→발송·결정→통보·차수·다른 주체·'…자' 문서 일자·상대방 주장·'단 한 번도') Steve 1/3 → 2/3·대조 오탐 0/7(Steve의 1건은 기존 EVI.INCONS_INTERNAL_DATE — 새 규칙이 양보, 설계대로). 합 4/6·대조 0/11. 악성 입력 4종 최악 0.067초(Steve 0.032초 수준). #244·#245와 함께 병합한 상태에서 관련 시험 통과(실패 1건은 #245 쪽).

원인과 고칠 것
D1 [결과 제목에 날짜 조각] internal_inconsistency.py 1334행 _clean_content_prefix(1344행)
- 원인: 비지시어 사건 명사의 내용 수식을 명사 앞 15자의 마지막 어절로 잡는데, 한글인지 보지 않는다. 평가 측 공개 시험 문장 '피고가 2024. 5. 13. 발송한 위 이행최고서에는 …'에서 '13.'이 내용 수식이 되어 제목이 '문서 내 동일 사건(13. 발송) …'으로 나온다(평가 측 재현).
- 고칠 것: 1344행을 if not re.fullmatch(r"[가-힣]{2,12}", clean) or clean in _CONTENT_EXCLUDE_WORDS: return None 으로 바꾼다. 평가 측 사본에서 제목 '동일 사건(발송)', 탐침 1·2차 결과 같음, 관련 시험 통과.
- 증분: docs/handoff/patches/TK-76_cycle3_incons_c_d1_on_e6622fe.diff — 제품 1줄, 평가 측 시험 tests/test_tk76_incons_c_title_eval.py 1건(이 head에서 실패, 고친 뒤 통과).

알려진 한계(범위 밖, 후속): 사건 명사가 법률행위 범주(메모 2.1(1))에 한정되어 전달 수단 명사(범주 밖 일반 명사)로 적은 같은 사건의 시각 모순은 잡지 않는다(새 2차 미탐 1). 앞에 '단'이 없는 맨 '한 번'은 유일성 표지가 아니다(설계대로, 1차 미탐 1).

수용 기준: CI 전부 성공, D1 시험 통과, 탐침 결과 하락 없음.
```

### 2-24-2. #245 EVI-OVR 잔여 보완본 판정 — 수용 (11-09, head `deea2ff`, 사용자 '#245,246 보완 커밋확인')

```
[평가 측 판정 — #245 보완본 TK-76 3주기 EVI-OVR 잔여 5꼴 (head deea2ff, 기준 Steve a836bba), 11-09]

판정: 수용. 사용자 병합 승인 대기.
- B1~B3 반영 확인: 제품 코드(evidence_consistency.py)가 평가 측 보완 사본과 같다(diff 0). 변형 시험의 서증명을 범주 낱말로 교체('독촉장'→'통고서', '요청서'→'견적서'), 평가 측 보완 시험 tests/test_tk76_ovr_followup_eval.py 11건 포함.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공(같은 SHA 두 벌 모두).
- 평가 측 재실행: 판정용 새 비공개 탐침 8차(이번에 새로 지음 — 동격 주체·맨 이행·앎·전칭 부정, 대조에 의문형 앎·의문형 이행·가정형 앎·자기 측 동격 주체·정상 영수증) 기준 Steve 0/4 → 4/4·대조 오탐 0/5. 지난 1~7차 하락 없음(7차 5/5·0/6). #246 보완본과 함께 현재 Steve(a836bba)에 병합한 상태에서 관련 62개 파일 1,603건 통과. 은퇴·고정은 CI 결과 인용 + 같은 제품 코드의 사본 측정(변화 0).
- 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
- 후속(범위 밖): '전부' 변제 주장 대 일부 금액 서증, 자기 측 확인서로 자기 측 의사표시를 증명하는 꼴(기존 동작 검토).
```

### 2-22-5. #246 EVI-INCONS C 보완본 판정 — 보완 1회 더(D2) (11-09, head `6d7e59a`)

- 평가 측 사본 보완 증분: [patches/TK-76_cycle3_incons_c_d2_on_6d7e59a.diff](patches/TK-76_cycle3_incons_c_d2_on_6d7e59a.diff). 관형절 속 날짜 꼴은 범위 밖(평가 측 N3 지시의 빈칸) — 사용자 결정 대기.

```
[평가 측 판정 — #246 보완본 TK-76 3주기 EVI-INCONS C (head 6d7e59a, 기준 Steve a836bba), 11-09]

판정: 보완 1회 더(작음). D1은 반영됐다(제품 = 평가 측 D1 사본, 시험 포함). 판정용 새 탐침에서 같은 사건의 단계가 어긋나는 결함(D2)이 드러났다 — 고치면 수용한다.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·Docker OCR·PostgreSQL 시험 성공, SQLite 시험은 판정 시점 실행 중(실패 0).
- 평가 측 재실행: 판정용 새 비공개 탐침 3차(이번에 새로 지음) 기준 Steve 0/3 → 이 head 0/3·대조 오탐 0/6. D2를 고친 평가 측 사본 1/3·0/6. 남은 2건은 관형절 속 날짜 꼴(아래 '범위 밖'). 지난 1·2차 2/3·2/3·대조 0/11 유지(사본도 같음). #245와 함께 Steve에 병합한 상태에서 관련 62개 파일 1,603건 통과.

원인과 고칠 것
D2 [미탐] 같은 사건에 서로 다른 단계를 매김 — internal_inconsistency.py 1350행 _determine_stage_role, 1576행 호출부
- 원인 (가): 서술어에서 단계를 못 정해 명사 기본 단계로 넘어갈 때, 지시어 결속 명사는 h_start~h_end가 '위 청구'·'위 해제 통지'처럼 지시어를 포함한 구간이라 _DEFAULT_NOUN_STAGE에서 찾지 못하고 기본값 NOTIFY_SEND가 된다. 그래서 '…단 한 차례 청구를 하였다'(SUBMIT_FILE)와 '…위 청구를 하였다'(NOTIFY_SEND)가 다른 단계로 갈린다(평가 측 슬롯 출력으로 재현).
- 원인 (나): 앞 25자 창에서 단계 꼴을 찾을 때 맨 명사도 서술어로 읽는다. '…[결정류 명사] 통지를 하였다' 꼴에서 내용 수식(결정류 명사)이 DECIDE로 잡혀, 같은 '[내용] 통지'가 DECIDE/NOTIFY_SEND로 갈린다.
- 고칠 것: _determine_stage_role에 head_noun 인자를 더하고(1576행에서 head_noun 전달), 기본 단계는 _DEFAULT_NOUN_STAGE.get(head_noun)로 찾는다. 앞 25자 창은 서술어 꼴만 본다 — any(not re.fullmatch(r"[가-힣]{2}", mm.group(0)) for mm in pat.finditer(before_window)) (맨 두 글자 명사 일치는 버림).
- 평가 측 사전 검증(사본 7311279 = 이 head + D2): '…청구를 하였다 / 위 청구를 하였다', '…[내용] 통지를 하였다 / 위 [내용] 통지를 하였다' 꼴 탐지, '결정을 하였고 … 위 결정을 통지' 단계 분리 유지(오탐 0). 관련 580건 통과, 악성 입력 4종 최악 0.082초. 증분: docs/handoff/patches/TK-76_cycle3_incons_c_d2_on_6d7e59a.diff — 제품 1파일(+8/−4), 평가 측 시험 2건 추가(tests/test_tk76_incons_c_title_eval.py, 이 head에서 1건 실패·고친 뒤 통과).

범위 밖(후속, 설계 보강 필요): 날짜가 관형절 안에 있는 꼴('[날짜]에 [동사]한 [지시어] [사건 명사]에는/는 …', 관형절 날짜와 주절의 다른 단계 서술어가 한 절에 함께 있는 꼴)은 관형절 날짜와 주절 서술어가 한 절에 섞여 결속·단계가 어긋난다. 메모가 직접 논항만 결속하도록 한 것(평가 측 N3 지시)의 빈칸이라 이번 수용 조건으로 묻지 않는다. 사용자 결정에 따라 후속 티켓으로 둔다.

수용 기준: CI 전부 성공, D2 시험 통과, 지난 탐침 하락 없음.
```

### 2-22-6. #246 EVI-INCONS C 3차 판정 — 보완 1회 더 D3(관형절 날짜) (11-09, head `7e223f9`, 사용자 '관형절 날짜 꼴은 B안으로 이번 릴리스 포함'·'#246 확인')

- 평가 측 사본 보완 증분: [patches/TK-76_cycle3_incons_c_d3_on_7e223f9.diff](patches/TK-76_cycle3_incons_c_d3_on_7e223f9.diff). D2는 반영 확인(제품 = 사본 `7311279`).

```
[평가 측 판정 — #246 3차 TK-76 3주기 EVI-INCONS C (head 7e223f9, 기준 Steve a356d76), 11-09]

판정: 보완 1회 더 — D3(관형절 속 날짜 꼴). D2는 반영됐다(제품·시험 = 평가 측 D2 사본 7311279, diff 0). 관형절 꼴은 사용자 결정(11-09 'B안, 이번 릴리스 포함')으로 이번 PR 범위에 넣는다. D3를 반영하면 수용한다.
- CI 결과 인용: 이 head의 CI는 판정 시점 실행 중(직전 head 6d7e59a는 필수 확인 전부 성공).
- 평가 측 재실행: 판정용 새 비공개 탐침 4차(이번에 새로 지음, 보정 안 함) 기준 Steve 0/4 → 이 head 1/4·대조 오탐 0/6 → D3 사본 3/4·0/6. 3차(D3 보정에 씀) 1/3 → 3/3·0/6. 지난 1·2차: 사본 3/3·2/3, 대조 0/11.

원인과 고칠 것
D3 [미탐] 관형절 속 날짜 꼴 — internal_inconsistency.py _check_same_event_datetime_inconsistency 루프(pred_tail 부정 검사·날짜/시각 추출·_determine_stage_role 호출부)
- 원인 (가): '[날짜·시각]에 [동사]한 (위·그) [사건 명사]에는 [다른 내용]이 없었다' 꼴에서 부정 검사가 사건 명사 뒤 꼬리 전체를 보아, 사건과 무관한 주절의 '없었'으로 사건을 버린다.
- 원인 (나): '[날짜] [동사]한 그 [사건 명사]는 … 같은 달 N일 도달하였다' 꼴에서 단계를 주절 서술어('도달')로 정하고 날짜는 관형절 날짜를 써서 단계·날짜가 어긋난다.
- 고칠 것: _RELATIVE_EVENT_VERB_RE = (?P<verb>[가-힣]{0,6}(?:한|된|보낸|낸|받은))(?!\s+(?:차례|번|회|건|명|가지)(?:\s|$))\s+(?:(?:위|그|해당|이\s*사건|본건|동)\s+)?(?:[가-힣]{2,12}\s+)?$ 를 clause[:h_start]에 대어, 일치하고 그 앞(관형절)에 날짜·시각(_FULL_DATE_RE·TIME_RE·_SAME_MONTH_DAY_RE·_MONTH_DAY_RE·_RELATIVE_DATE_RE)이 있을 때만 '관형절 모드'로 본다. 관형절 모드에서는 (1) 날짜·시각을 clause[:관형절 끝]에서만 뽑고, (2) 단계는 관형절 동사로 정하며(_relative_verb_stage: 단계 꼴 일치, 기능동사 '한·된'뿐이면 머리 명사 기본 단계), (3) pred_tail 부정 검사를 하지 않는다. 관형절에 날짜가 없으면('작성한 위 통지서를 [날짜] 발송') 지금 그대로.
- 주의(평가 측 첫 시안에서 잡은 결함): 수사 '한'('단 한 차례', '한 번')을 관형절 동사로 읽지 않도록 위 부정 전방탐색이 필요하다 — 빠지면 메모 3.2 대조(작성→발송→도착)가 깨진다(tests/test_tk76_incons_c_eval.py 기존 시험에서 확인).
- 평가 측 사전 검증(사본 197837b = 이 head + D3): 관련 582건 통과(기존 메모 대조 포함), 4차 3/4·0/6, 3차 3/3·0/6, 2차 2/3·0/7, 1차 3/3·0/4. 악성 입력 4종 최악 0.07초, 새 정규식 단독 0.007초. 증분: docs/handoff/patches/TK-76_cycle3_incons_c_d3_on_7e223f9.diff — 제품 1파일(+40/−13), 평가 측 시험 2건 추가(tests/test_tk76_incons_c_title_eval.py — 이 head에서 양성 1건 실패, 고친 뒤 통과).

남은 한계(범위 밖): 관형절 날짜가 있어도 사건 명사 뒤가 '-에 대하여·-에 대한'인 꼴은 메모 2.1(3) 수식어 제외 규칙에 따라 결속하지 않는다(4차 미탐 1).

수용 기준: CI 전부 성공, D3 시험 통과, 기존 메모 대조 시험 통과, 탐침 하락 없음·대조 오탐 0.
```

### 2-22-7. #246 EVI-INCONS C 4차 판정 — 수용 (11-09, head `dc4e6c1`, 사용자 '#246 보완 커밋확인')

```
[평가 측 판정 — #246 4차 TK-76 3주기 EVI-INCONS C (head dc4e6c1, 기준 Steve a356d76), 11-09]

판정: 수용. 사용자 병합 승인 대기.
- D3 반영 확인: 제품 코드(internal_inconsistency.py)와 평가 측 시험이 평가 측 D3 사본 197837b와 같다(diff 0). 앞서 D1·D2·C1 반영 확인.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공(같은 SHA 두 벌 모두).
- 평가 측 재실행: 판정용 새 비공개 탐침 5차(이번에 새로 지음 — 관형절 날짜·같은 날 시각·기능동사·지시어, 대조에 작성→도달·신청→접수·결정→통보·다른 주체·'단 한 번도'·차수) 기준 Steve 0/4 → 4/4·대조 오탐 0/6. 지난 1~4차 3/3·2/3·3/3·3/4, 대조 오탐 0(합 0/23). 현재 Steve(a356d76)에 병합한 상태에서 관련 62개 파일 1,607건 통과. 악성 입력 최악 0.07초(Steve 수준). 은퇴·고정은 CI 결과 인용.
- 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
- 후속(작음, 수용을 막지 않음): 두 슬롯의 머리 명사가 다를 때('[명사 A]를 [동사 B]하였다' ↔ '위 [명사 A] [명사 B]는') 결과 제목이 '동일 사건(A A)'처럼 낱말이 겹친다 — 1750행 부근 target_display가 한 슬롯의 내용 수식과 다른 슬롯의 머리 명사를 섞는다. 내용 수식이 있는 슬롯의 (내용, 머리)를 함께 쓰면 고쳐진다.
- 남은 한계(범위 밖): 사건 명사 뒤가 '-에 대하여·-에 대한'인 꼴(메모 2.1(3)), 법률행위 범주 밖 전달 수단 명사.
```

- **#246 Steve 병합 `3d54f77`**(11-09, 사용자 지시 '#246 병합', 평가 측이 expectedHeadSha `dc4e6c1`로 실행). Steve `packages/`·`tests/` = 평가 측 병합 시험본(1,607건 통과). TK-76 3주기 구현 PR 모두 병합.

## 2-25. EVI-INCONS C 후속 T1 — 결과 제목 낱말 겹침 (릴리스 전 수정) (11-09, 사용자 '제목 낱말 겹침 후속 처리 릴리스 전 수정')

- **11-09 2-27절(A 묶음)로 대체.** 아래는 기록용.

- 평가 측 사본 `60d292e`(기준 `3d54f77`) 사전 검증. 증분: [patches/TK-76_cycle3_incons_c_title_t1_on_3d54f77.diff](patches/TK-76_cycle3_incons_c_title_t1_on_3d54f77.diff).

```
[평가 측 구현 지시 — TK-76 3주기 EVI-INCONS C 후속 T1(결과 제목 낱말 겹침), 기준 Steve 3d54f77(#246 병합), 11-09]

목적: 릴리스 전 마무리(사용자 결정 11-09 '릴리스 전 수정'). 한 줄짜리 표시 결함. 한 PR로 낸다. 설계 메모 불요(평가 측 사본으로 사전 검증 완료).

T1 [표시 결함] 결과 제목의 대상 표시에 같은 낱말이 겹침 — packages/claim_engine/internal_inconsistency.py 1748~1752행 target_display
- 원인: 내용 수식은 slot_a 또는 slot_b 중 있는 쪽에서, 머리 명사는 늘 slot_a에서 가져와 섞는다. 첫 문장의 목적어가 사건 명사('…에 대한 [사건 명사 A]를 [동사 B]하였다' → 머리 A)이고 둘째 문장이 '위 [A] [B 명사]'(내용 A·머리 B)이면 제목이 '동일 사건(A A)'가 된다(평가 측 재현: '…해고를 의결하였다' ↔ '…한 위 해고 의결은' → '동일 사건(해고 해고)').
- 고칠 것: 내용 수식이 있는 슬롯을 골라(disp_slot = slot_a if slot_a.content_prefix else (slot_b if slot_b.content_prefix else slot_a)) 그 슬롯의 (내용 수식, 머리 명사)를 함께 쓴다. 내용 수식이 머리 명사와 같으면 머리 명사만 쓴다.
- 판정 로직(결속·단계·비교)은 바꾸지 않는다.

평가 측 사전 검증(사본 60d292e, 기준 3d54f77)
- 평가 측 시험 tests/test_tk76_incons_c_title_dup_eval.py 2건 — Steve에서 1건 실패('해고 해고'), 사본에서 통과('해고 의결'·'해지 통지'). 관련 시험(internal_inconsistency·check_document 관련) 307건 통과. EVI-INCONS C 비공개 탐침 1~5차 결과 변화 없음(3/3·2/3·3/3·3/4·4/4, 대조 오탐 0) — 제목만 바뀜.
- 증분: docs/handoff/patches/TK-76_cycle3_incons_c_title_t1_on_3d54f77.diff — 제품 1파일(+6/−5), 평가 측 시험 1파일 2건.

제출물·수용 기준
- 증분 그대로 적용해도 되고 같은 구조로 다시 써도 된다. 2-2 다: 귀속표 '세트 득점 0'(표시만 바뀜), train '미측정'.
- 수용: CI 전부 성공, 평가 측 시험 통과, 탐침 결과 변화 없음. 수용·병합 뒤 그 Steve SHA를 릴리스 후보로 평가 측 verify_all 전체 1회.
```

## 2-26. 후속 과제 흡수 — TK-76 3주기 마무리 (11-09, 사용자 지시 '식별되는 추가 문제들은 tk 구현과정에서 함께 해결')

- 원칙(CLAUDE.md·AGENT_ROLES 2.1 개정): 판정·사전 검증에서 드러난 문제는 같은 TK의 같은 보완 회차에서 해결한다. 예외 (가) 규칙으로 풀 수 없는 것(모델 판단·외부 자료), (나) 설계 범위를 바꾸는 것 — 둘 다 미루기 전에 사용자 범위 결정.
- 이번 릴리스 전 처리 대상(TK-76 3주기에서 '후속'으로 적어 둔 것). 평가 측이 모듈별로 사본 사전 검증 → 구현 지시 → 판정. 이미 지시한 T1(2-25)은 A 묶음에 합친다.

| 묶음(파일) | 항목 | 분류 | 출처 |
|---|---|---|---|
| A internal_inconsistency.py | T1 결과 제목 낱말 겹침 | 결함 | #246 4차 |
| A | T2 끝 음절이 조사와 같은 두 글자 내용 수식('이의 신청'→'신청') | 결함(표시) | A 묶음 사전 검증 중 발견 |
| A | I1 관형절 날짜 + 사건 명사 뒤 '-에 대하여·-에 대한' 꼴 | 미탐(설계 빈칸) | #246 3·4차 |
| A | I2 법률행위 범주 밖 전달 수단 명사로 적은 같은 사건 | (나) 범주 확장 — 사용자 결정 | #246 1차 |
| B evidence_consistency.py | L1 직접 지각 표지 '[인칭 대명사] 눈으로' | 미탐 | #241 |
| B | L2 장소 조사 없는 체재 꼴 | 미탐 | 2-21 지시 한계 |
| B | O1 '전부' 변제 주장 대 일부 금액 서증 | 미탐 | #230·#245 |
| B | O2 자기 측 확인서로 자기 측 의사표시를 증명하는 꼴(기존 동작) | 오탐 여부 판단 필요 | #245 6차 |
| B | L3·L4(지각 구조 같은 자리·다른 사람 체재 오탐), O3~O6(작성자 '피신청인' 오독·완료 목적어 '차임·원리금'·본문 '소을' 인용·명사형 의사표시) | 결함 — 점검표로 발견(11-10) | B 묶음 사전 검증 |
| C calculation.py | Q4 피연산자 앞 '수+일반 명사' 이름표 | 미탐 | 2-23 |
| C | Q5 분배형 곱셈('각·각각·1인당 … 씩 … 합계') | 미탐 — 점검표로 발견(11-10) | C 묶음 사전 검증 |
| D date_verifier.py | P1 띄어쓰기 없는 2만 자 약 43초·같은 꼴 800회 약 11초(A-4 쌍 비교 비용) | 성능 | #239 |
| E evidence_consistency.py(EVI-COPY) | C2 원문 범위 확장(사실경위서로 분류되지 않은 문서)·문서 종류 판별 | (나) 설계 범위 — 사용자 결정 | 2-20(은퇴 오탐 2로 보류) |
| — | 유사과학 근거(EVI-LOGIC 2주기) | (가) 모델 판단 — 규칙 범위 밖 | 2-21 |
- 사용자 결정(11-09): E(EVI-COPY 원문 범위 확장·문서 종류 판별)는 다음 릴리스 첫 TK로(설계 메모부터). I2(INCONS C 전달 수단 명사)는 이번 릴리스 포함. O2는 평가 측 판단으로 오탐(자기 측 의사표시는 '상대방 의사표시' 범주가 아님)으로 보아 B 묶음에서 고친다. 유사과학 근거는 (가)로 범위 밖.
- 사용자 결정(11-10 '공용 호증 문법의 소을 인식 부분은 제안대로 하고, 나머지는 미구현'): (1) 공용 호증 문법(exhibits.py)의 '소을' 인식은 이번 릴리스에 별도 소형 TK-149로 고친다(2-30절). (2) 상대 날짜의 날짜 셈('그 이틀 뒤' 꼴, INCONS C 점검표 3판 남은 1칸)과 (3) 일반·지시어 경로의 명사구 해석 통합은 **미구현**으로 닫는다(후속 티켓으로 두지 않음).
- 진행 순서: A(T1·I1·I2) → B(L1·L2·O1·O2) → C(Q4) → D(P1). **A 묶음 지시 완료(11-09, 2-27절).** **B 묶음 지시 완료(11-10, 2-29절).** **C 묶음 지시 완료(11-10, 2-31절).** **D 묶음 지시 완료(11-10, 2-32절) — 후속 흡수 지시 전부 완료. 네 증분(B·TK-149·C·D)은 함께 적용해도 충돌 없음(평가 측 시험 103건 통과).** 묶음마다 평가 측 사본 사전 검증 후 구현 지시, 판정은 기존 규약. 모두 병합 뒤 릴리스 후보 verify_all.

## 2-27. EVI-INCONS C 후속 A 묶음(T1·T2·I1·I2) 구현 지시 — 2-25절 대체 (11-09, 2-26절 진행 순서 A)

- 평가 측 사본 `ffe9efd`(기준 `3d54f77`, 저장소 밖) 사전 검증. 증분: [patches/TK-76_cycle3_incons_c_a_bundle_on_3d54f77.diff](patches/TK-76_cycle3_incons_c_a_bundle_on_3d54f77.diff)(2-25절 T1 증분 포함).
- T2는 사전 검증 중 새 탐침에서 드러난 표시 결함으로, 사용자 지시(11-09)에 따라 같은 묶음에 넣었다.

```
[평가 측 구현 지시 — TK-76 3주기 EVI-INCONS C 후속 A 묶음(T1·T2·I1·I2), 기준 Steve 3d54f77(#246 병합), 11-09]

목적: 릴리스 전 마무리. 사용자 결정 11-09 '식별되는 추가 문제는 TK 구현 과정에서 함께 해결', I2(전달 수단 명사)는 이번 릴리스 포함. 2-25절 T1 지시를 이 묶음으로 대체한다(T1만 낸 PR이 있으면 같은 PR에 이어 붙인다). 한 PR, 제품 1파일 packages/claim_engine/internal_inconsistency.py. 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 줄 번호는 3d54f77 기준.

T1 [표시 결함] 결과 제목 대상 표시에 같은 낱말이 겹침 — 1748~1752행 target_display
- 원인: 내용 수식은 slot_a·slot_b 중 있는 쪽에서, 머리 명사는 늘 slot_a에서 가져와 섞는다. '…[사건 명사 A]를 [동사 B]하였다' ↔ '…한 위 [A] [B 명사]는' 꼴이면 '동일 사건(A A)'(평가 측 재현: '해고 해고').
- 고칠 것: disp_slot = slot_a if slot_a.content_prefix else (slot_b if slot_b.content_prefix else slot_a). 그 슬롯의 (내용 수식, 머리 명사)를 함께 쓰고, 내용 수식 == 머리 명사면 머리 명사만.

T2 [표시 결함] 끝 음절이 조사와 같은 두 글자 내용 수식이 제목에서 빠짐 — 1334행 _clean_content_prefix, 1341행 조사 꼬리 검사
- 원인: 마지막 어절이 '과·의·도·만'으로 끝나면 조사로 보고 버린다. '이의·항의·사과·불만·결과' 같은 두 글자 명사도 버려져 '동일 사건(이의 신청)'이 '동일 사건(신청)'으로 나온다(평가 측 새 탐침에서 3건 확인 — 판정은 맞고 제목만 줄어듦).
- 고칠 것: 마지막 어절이 정확히 [가-힣][과의도만]이고 첫 글자가 인칭·지시 대명사 음절(_PRONOUN_SYLLABLES = "그저나너내누뭐걔얘쟤")이 아니면 조사 꼬리 검사를 건너뛴다. 그 밖(은·는·이·가·을·를·에·로·와, 날·일·시·분·경·한·된 등)은 지금 그대로 버린다('바로·같은·후에·그의·나도·그만'은 계속 None).

I1 [미탐] 관형절에 그 사건의 날짜가 있는데 사건 명사 뒤가 '-에 대하여·-에 대한'인 꼴 — 1377행 _extract_event_from_clause, 1385행 지시어 루프의 _NON_ARGUMENT_SUFFIX_RE 검사
- 원인: '[날짜]에 [동사]한 위 [사건 명사]에 대하여 …' 꼴을 메모 2.1(3) 수식어 제외 규칙으로 늘 버린다. D3(관형절 모드)가 그 날짜를 그 사건에 묶을 수 있는데도 결속 전에 빠진다(#246 3·4차 판정 '남은 한계').
- 고칠 것: 지시어 루프(1385행)에서만, 꼬리가 _NON_ARGUMENT_SUFFIX_RE에 맞더라도 clause[:m.start()]가 '날짜·시각이 든 관형절'로 끝나면 결속한다. 판별 함수 _has_dated_relative_clause(prefix): _RELATIVE_EVENT_VERB_RE.search(prefix + " ")가 맞고, 그 앞 prefix[:m.start()]에 _FULL_DATE_RE·TIME_RE·_SAME_MONTH_DAY_RE·_MONTH_DAY_RE·_RELATIVE_DATE_RE 중 하나가 있을 때 True. 일반 후보 루프(1399행)는 바꾸지 않는다. 관형절 없는 '위 청구에 대하여 [다른 날짜] 답변서 제출'은 지금처럼 버린다(대조 시험 있음).

I2 [미탐·범주 확장, 사용자 결정] 같은 사건을 전달 수단 명사로 적은 꼴 — 1189행 SAME_EVENT_NOUNS, 1291행 _DEFAULT_NOUN_STAGE, 1385·1399행 후보 루프
- 원인: '해명 메일·사과 문자메시지·항의 서신'처럼 전달 수단 명사로 적은 사건은 사건 명사 목록에 없어 결속되지 않는다.
- 고칠 것: (1) SAME_EVENT_NOUNS에 "문자메시지","이메일","전자우편","메일","문자","서신","편지","팩스"를 더하고(긴 낱말이 앞에 오게), _DEFAULT_NOUN_STAGE에서 모두 NOTIFY_SEND. (2) 수단 쓰임 제외: _MEDIUM_NOUNS(같은 8개)와 _is_medium_instrument(head, after) = head in _MEDIUM_NOUNS and re.match(r"^(?:으로|로)(?:써|서)?(?![가-힣])", after). 지시어 루프와 일반 후보 루프 모두에서 True면 continue.
- 주의(평가 측 첫 시안에서 잡은 결함): (2)가 빠지면 '[다른 사건]을 … 팩스로 보냈다'에서 '팩스'가 사건 명사를 밀어내 기존 탐침 1건이 미탐으로 떨어진다. '문자 그대로' 관용구는 머리 명사 뒤가 조사·서술어가 아니라 결속되지 않음을 대조 시험으로 확인한다.

판정 로직(단계 비교·쌍 선택·중복 억제)은 바꾸지 않는다.

평가 측 사전 검증(사본 ffe9efd = 3d54f77 + T1·T2·I1·I2, 평가 측 재실행)
- 평가 측 시험 tests/test_tk76_incons_c_title_dup_eval.py 9건(T1 2·I1 2·I2 3·T2 2, 양성 5·대조 4) — Steve 3d54f77에서 5건 실패(양성 전부), 사본에서 9건 통과.
- 관련 시험(internal_inconsistency·INCONS·check_document·claim_engine 관련 70개 파일) 1,670건 통과.
- EVI-INCONS C 비공개 탐침: 1~5차 Steve 3/3·2/3·3/3·3/4·4/4 → 사본 3/3·3/3·3/3·4/4·4/4, 대조 오탐 0/29 유지. 6차(I1·I2 확인, T2 보정에 씀) Steve 1/5 → 5/5·0/7. 7차(판정용 새로 지음, 보정 안 함) Steve 1/4 → 4/4·0/6.
- 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0 → 변화 0. 고정 dev 82.6·holdout 81.9·FP 0 → 변화 0(세트 득점 0).
- 악성 입력 6종(띄어쓰기 없는 2만 자, 반복 유일 표지, 800줄, 지시어 반복, 수단 명사 반복, 관형절+'에 대하여' 반복) 최악 0.063초(Steve 0.064초).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_incons_c_a_bundle_on_3d54f77.diff — 제품 1파일(+41/−7), 평가 측 시험 1파일 9건. 3d54f77에 git apply --check 통과. 2-25절 T1 증분을 포함한다(대체).

제출물·수용 기준
- 증분 그대로 적용해도 되고 같은 구조로 다시 써도 된다. PR 본문에 T1·T2·I1·I2 → 바꾼 함수 → 시험 이름 대응표. 2-2 다: 귀속표 '세트 득점 0'(표시·범주 확장, 은퇴·고정 변화 0), train '미측정'.
- 수용: CI 전부 성공, 평가 측 시험 9건 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침 하락 없음. 이어 B(L1·L2·O1·O2)·C(Q4)·D(P1) 묶음 지시를 따로 낸다(2-26절). 모두 병합 뒤 릴리스 후보 verify_all 전체 1회.
```

### 2-27-1. #247 판정 (11-09, head `0ce0741`, 기준 Steve `3d54f77`)

- 판정: T1 반영 확인(2-25절 수용 기준 충족). 2-25절이 2-27절로 대체됐으므로 같은 PR에 T2·I1·I2를 이어 붙인 뒤 최종 수용. PR 코멘트로 전달.
- T1: 제품·평가 측 시험 = 사본 `60d292e`(diff 0).
- CI 결과 인용: 필수 확인 전부 성공(같은 SHA 두 벌).
- 평가 측 재실행: 평가 측 시험 2건 통과, INCONS C 탐침 1~5차 3/3·2/3·3/3·3/4·4/4·대조 0/29(기준과 같음, 제목만 바뀜), 판정용 7차 1/4(A 묶음 미반영분, 예상대로).
- 2-2 다: '세트 득점 0', train '미측정' 확인.

### 2-27-2. #247 2차 판정 — 보완 1회(I3·I4) (11-09, head `86f54c9`)

- T1·T2·I1·I2 반영(제품·시험 = 사본 `ffe9efd`). 판정용 새 8·9차에서 Steve에도 있던 기존 동작의 오탐 1꼴('알리다·전하다' 단계 누락)·미탐 1꼴(지시어 뒤 두 어절 내용 수식)이 드러나 사용자 지시(11-09)에 따라 같은 PR에서 고친다. 사본 `88f1b3a` 사전 검증, 증분 [patches/TK-76_cycle3_incons_c_i3_i4_on_86f54c9.diff](patches/TK-76_cycle3_incons_c_i3_i4_on_86f54c9.diff). PR 코멘트로 전달.

```
[평가 측 판정 — #247 2차 TK-76 3주기 EVI-INCONS C 후속 A 묶음 (head 86f54c9, 기준 Steve 3d54f77), 11-09]

판정: 보완 1회(작음). T1·T2·I1·I2는 반영됐다(제품·시험 = 평가 측 사본 ffe9efd, diff 0). 판정용 새 탐침에서 기존 동작(Steve 3d54f77에도 있음, 이 PR의 회귀 아님)의 오탐 1꼴·미탐 1꼴이 드러났다. 사용자 지시(11-09 '식별되는 추가 문제는 TK 구현 과정에서 함께 해결')에 따라 이 PR에서 I3·I4를 고치면 수용한다.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공(같은 SHA 두 벌 모두).
- 평가 측 재실행: 평가 측 시험 9건 통과. 탐침 1~7차 3/3·3/3·3/3·4/4·4/4·5/5·4/4, 대조 오탐 0/42(사전 검증과 같음). 판정용 새 8차 Steve 1/4·대조 오탐 1/6 → 이 head 3/4·1/6. 판정용 새 9차(보정 안 함) Steve 1/3·1/6 → 이 head 2/3·1/6 → I3·I4 사본 3/3·0/6.

원인과 고칠 것 (줄 번호는 86f54c9의 packages/claim_engine/internal_inconsistency.py 기준)
I3 [오탐] '알리다·전하다'를 알림 단계 서술어로 보지 않음 — 1288행 _STAGE_PREDICATE_PATTERNS의 NOTIFY_SEND
- 원인: '[날짜] [결정류 명사]를 결정·의결하였고, [다른 날짜] 위 [같은 명사]를 [상대방]에게 알렸다/전하였다' 꼴에서 둘째 서술어가 단계 꼴에 없어 머리 명사의 기본 단계(DECIDE)로 넘어간다. 결정과 그 통지가 같은 단계로 묶여 '동일 사건 일자 모순' 오탐(평가 측 슬롯 출력으로 재현: 두 슬롯 모두 DECIDE). 8차·9차 대조 각 1건.
- 고칠 것: NOTIFY_SEND 패턴 끝에 |(?<![가-힣])(?:알리|알렸|알린|알려(?!지))|(?<![가-힣])(?:전했|전한|전하고|전하여|전하였|전해) 를 더한다. 앞 경계 (?<![가-힣])는 '완전했다' 같은 낱말 속 일치를, (?!지)는 '알려진'(피동·앎)을 막는다.

I4 [미탐] 지시어 뒤 내용 수식이 두 어절인 꼴 — 1205행 _ANAPHORA_EVENT_RE content 그룹, 1408행 지시어 루프
- 원인: content가 한 어절([가-힣]{2,12}?)만 받아 '위 [명사] [명사] [사건 명사]' 꼴은 지시어 결속이 안 되고, 일반 후보로 넘어가면 꼬리 '-에 대하여'로 빠진다(I1은 지시어 루프에서만 작동). 8차·9차 양성 각 1건.
- 고칠 것: (1) content를 (?P<content>[가-힣]{2,12}?(?:\s+[가-힣]{2,12}?)??) 로 넓힌다(두 어절까지). (2) 지시어 루프에서 content가 두 어절이면 앞 어절이 _clean_content_prefix를 통과(명사)할 때만 결속하고, 아니면 continue — '위 [상대방]에게 보낸 [사건 명사]'처럼 지시어가 다른 명사를 꾸미는 꼴을 막는다. 내용 수식 값은 지금처럼 _clean_content_prefix(마지막 어절).

평가 측 사전 검증(사본 88f1b3a = 이 head + I3·I4, 평가 측 재실행)
- 평가 측 시험 4건 추가(tests/test_tk76_incons_c_title_dup_eval.py, 총 13건: I3 대조 2·I4 양성 1·I4 대조 1) — 이 head에서 3건 실패, 사본에서 13건 통과.
- 관련 시험(70개 파일) 1,674건 통과. 탐침 1~9차 3/3·3/3·3/3·4/4·4/4·5/5·4/4·4/4·3/3, 대조 오탐 0/54(8차는 I3·I4 보정에 씀, 9차는 보정 안 함).
- 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0).
- 악성 입력 7종(두 어절 지시어·'알려진·전해' 반복 추가) 최악 0.065초(Steve 0.062초).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_incons_c_i3_i4_on_86f54c9.diff — 제품 1파일(+8/−3), 평가 측 시험 4건. 이 head에 git apply --check 통과.

수용 기준: CI 전부 성공, 평가 측 시험 13건 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침 하락 없음. PR 본문 대응표에 I3·I4 행 추가, 귀속표 '세트 득점 0'·train '미측정'.
```

### 2-27-3. #247 3차 판정 — 보완 1회 더(I5·I6) (11-09, head `8171fc2`)

- I3·I4 반영(제품·시험 = 사본 `88f1b3a`). 판정용 새 10차 head 1/3·오탐 1/6(수용 미달). I5는 I2(전달 수단 명사)가 드러낸 지시어 경로의 머리 명사 선택 결함(Steve 대비 회귀 1건), I6은 같은 파일 EVI.INCONS_INTERNAL_DATE의 기존 결함. 사본 `c6416a9` 사전 검증, 증분 [patches/TK-76_cycle3_incons_c_i5_i6_on_8171fc2.diff](patches/TK-76_cycle3_incons_c_i5_i6_on_8171fc2.diff). PR 코멘트로 전달.
- 평가 측 기록: 2차 판정(2-27-2)에서 8·9차 탐침을 돌릴 때 쓴 worktree는 올바른 head(`86f54c9`)였다. 이번 판정의 첫 실행은 worktree가 옛 head에 머물러 다시 돌렸다(결과는 새 head 기준으로만 적음).

```
[평가 측 판정 — #247 3차 TK-76 3주기 EVI-INCONS C 후속 A 묶음 (head 8171fc2, 기준 Steve 3d54f77), 11-09]

판정: 보완 1회 더(작음). I3·I4는 반영됐다(제품·시험 = 평가 측 사본 88f1b3a, diff 0). 판정용 새 탐침 10차에서 양성 1/3·대조 오탐 1/6으로 수용 기준(2/3 이상·오탐 0)에 못 미쳤다. 원인 2개(I5·I6)를 고치면 수용한다. 둘 다 사전 검증을 마쳤다.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·Docker OCR·PostgreSQL 시험 성공, SQLite 시험은 한 벌 성공·한 벌 판정 시점 실행 중(실패 0).
- 평가 측 재실행: 평가 측 시험 13건 통과. 탐침 1~9차 3/3·3/3·3/3·4/4·4/4·5/5·4/4·4/4·3/3, 대조 오탐 0/54(사전 검증과 같음). 판정용 새 10차 Steve 2/3·오탐 1/6 → 이 head 1/3·1/6. 이 가운데 양성 1건은 Steve가 잡고 이 head가 놓친다(I2 회귀, 아래 I5).
- PR 본문 대응표의 I3·I4 시험 이름이 실제 시험 파일의 이름과 다르다(test_i3_control_decide_then_notify_by_allida·…_by_jeonhada, test_i4_two_word_content_after_demonstrative_binds·test_i4_control_demonstrative_modifies_other_noun). 본문을 실제 이름으로 고친다.

원인과 고칠 것 (줄 번호는 8171fc2의 packages/claim_engine/internal_inconsistency.py 기준)
I5 [미탐·회귀] 복합 명사구에서 일반 경로와 지시어 경로가 서로 다른 머리 명사를 고른다 — 1205행 _ANAPHORA_EVENT_RE, 1401행 지시어 루프
- 원인: 일반 경로(_GENERAL_EVENT_RE, 1212행)는 명사구의 '마지막' 사건 명사를 머리로 쓴다. 지시어 정규식은 content를 최소 일치로 잡아 '위 [사건 명사 A] [일반 명사] [사건 명사 B]'에서 A를 머리로 고른다(B 앞에 사건 명사가 아닌 낱말이 끼면 부정 전방탐색이 A를 막지 못함). 그래서 같은 사건이 'B'(첫 문장)와 'A'(지시어 문장)로 갈려 same_head(1703행)가 거짓이 된다(평가 측 슬롯 출력으로 재현: '[A] [일반 명사] 통지' ↔ '위 [A] [일반 명사] 통지' → 머리 통지/A). I2로 전달 수단 명사가 사건 명사가 되면서 '위 [결정류 명사] [일반 명사] [전달 수단 명사]' 꼴이 Steve(둘 다 머리 A로 같았음)보다 나빠졌다. 또 '위 [명사] [사건 명사 A] [사건 명사 B]'(내용 두 어절의 마지막이 사건 명사)는 일반 경로의 보조 머리(alt_head)와 짝이 안 맞아 결속되지 않는다.
- 고칠 것: (1) 지시어 정규식은 지금(최소 일치) 그대로 둔다 — 최대 일치로 바꾸면 '위 [사건 명사]에는 [사건 명사] [명사]' 꼴에서 조사 붙은 어절을 삼켜 머리가 틀어진다(평가 측 첫 시안에서 탐침 3·5차 각 1건 하락으로 확인). (2) 확장 정규식 _ANAPHORA_EXT_RE = \s+(?P<mid>[가-힣]{2,12})\s+(?P<head2>사건 명사 대안)(?!\s*(?:사건 명사 대안)) 을 두고, 지시어 일치의 doc('서')가 없을 때 clause[m.end():]에 match하여, mid가 사건 명사가 아니고 시간·관계 명사 집합 _ANAPHORA_EXT_BLOCK(이후·이전·직후·직전·당시·무렵·관련·이외·대신·과정·도중·전후·결과·다음·뒤)에 없고 _clean_content_prefix(mid)를 통과하면 머리를 head2로 옮긴다(alt_head = 원래 머리, 내용 수식 = mid, 끝 위치 = 확장 끝). 꼬리 검사(_NON_ARGUMENT_SUFFIX_RE·_is_medium_instrument)는 옮긴 머리·끝 위치로 한다. (3) 확장이 없고 내용 수식이 두 어절이며 마지막 어절이 사건 명사이면 alt_head = 그 어절, 내용 수식 = 앞 어절(한 어절 내용은 지금 그대로). 반환 튜플의 alt_head 자리(지금 None)에 넣는다.

I6 [오탐·기존] EVI.INCONS_INTERNAL_DATE가 명사로만 쓰인 '해지·해제'를 사건 서술로 읽는다 — 224~230행 EVENT_PREDICATE_MAP의 "해지"·"해제"
- 원인: 서술어 꼴이 해지(?:하|했|…)? 처럼 접미가 선택이라 낱말 '해지' 자체가 서술어로 일치한다. '[날짜] 해지 [일반 명사]를 결정하였고, [다른 날짜] 위 해지 [일반 명사] 결정을 알렸다' 꼴이 '동일 사건 발생일 진술 불일치'로 잡힌다(Steve 3d54f77에도 있음, 10차·11차 대조 각 1건).
- 고칠 것: 두 항목의 접미를 필수로 — (?:해지(?:하|했|하였|한|하고|하여|되었|된|되)), (?:해제(?:…같음…)). 서술로 쓰인 '해지하였다·해지된'은 그대로 잡는다(시험 있음). 이 수정으로 INTERNAL_DATE가 우연히 잡던 '[사건 명사] [결정 동사]' 꼴은 I5를 거쳐 EVI.INCONS_SAME_EVENT_DATETIME이 잡는다(11차 양성 2건 확인).

평가 측 사전 검증(사본 c6416a9 = 이 head + I5·I6, 평가 측 재실행)
- 평가 측 시험 5건 추가(총 18건: I5 양성 2·I5 대조 1·I6 대조 1·I6 양성 1) — 이 head에서 3건 실패, 사본에서 18건 통과.
- 관련 시험(70개 파일) 1,679건 통과. 탐침 1~10차 3/3·3/3·3/3·4/4·4/4·5/5·4/4·4/4·3/3·3/3, 대조 오탐 0/60(10차는 I5·I6 보정에 씀). 판정용 새 11차(보정 안 함) Steve 2/3·오탐 1/6, 이 head 3/3·1/6 → 사본 3/3·0/6.
- 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0).
- 악성 입력 9종(확장 사슬·'해지' 반복 추가) 최악 0.073초(Steve 0.077초).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_incons_c_i5_i6_on_8171fc2.diff — 제품 1파일(+30/−6), 평가 측 시험 5건. 이 head에 git apply --check 통과.

수용 기준: CI 전부 성공, 평가 측 시험 18건 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침 하락 없음. PR 본문 대응표에 I5·I6 행 추가·시험 이름 정정, 귀속표 '세트 득점 0'·train '미측정'.
```

#### 2-27-3 추가분 — I7, 증분 교체 (11-09, 사용자 지시 '판정마다 새 탐침에서 기존 결함이 하나씩 드러나는 이유 분석·개선')

- 원인 분석과 개선: [process_review_2026-11-09_probe_rounds](../scorecards/process_review_2026-11-09_probe_rounds.md). 평가 측이 축 조합 점검표(비공개)로 사본을 훑어 I7(가정 '-였다면'·의문 '-였는지'를 단정으로 읽음, 메모 2.4 빈칸, Steve에도 있음)을 판정 전에 찾아 넣었다.
- 증분 교체: [patches/TK-76_cycle3_incons_c_i5_i7_on_8171fc2.diff](patches/TK-76_cycle3_incons_c_i5_i7_on_8171fc2.diff)(I5·I6·I7, 제품 +33/−7, 평가 측 시험 7건). i5_i6 증분은 기록용.
- 사전 검증(사본 `892766e`, 평가 측 재실행): 시험 20건(head 5 실패 → 사본 통과), 점검표 1판 Steve 150/224·오탐 14/118 → 224/224·0/118, 2판 22/22·2/10 → 22/22·0/10, 3판 4/7·0/17 → 6/7·0/17(남은 1칸: 날짜 셈 상대 날짜 — (나) 사용자 결정 대기), 관련 1,681건, 탐침 1~11차 만점·대조 0/66, 은퇴·고정 변화 0, 악성 입력 0.069초.
- PR 코멘트로 전달(I7 원인·고칠 것·수용 기준 교체).

## 2-28. 구현 측 축별 자체 점검 (11-09, 사용자 지시 '다음 구현에서는 반드시 개선', AGENT_ROLES 2.1 개정)

- 탐지 규칙을 바꾸는 PR은 본문에 '축별 자체 점검' 표를 낸다: 바꾼 규칙마다 같은 축의 다른 값 3개 이상(서술어 동의어, 명사구 구조 변형, 어미·서법 변형, 날짜·시각 표기 변형 등)을 공개 합성 문장으로 돌린 결과(양성·대조 각각). 평가 측 탐침·점검표 문장과 은퇴·train 문장은 쓰지 않는다.
- 어휘·범주를 넓힌 경우(명사·서술어 목록 추가 등) 그 낱말이 다른 경로(일반·지시어·관형절)와 같은 파일의 다른 규칙에서 어떻게 처리되는지 확인해 표에 적는다.
- 평가 측 증분을 그대로 적용해도 이 표는 낸다. 표에서 실패가 나오면 같은 PR에서 고치고 적는다(11-09 규칙).
- **대조 문장은 '그 규칙만 빼면 잡히는 꼴'로 짓는다**(11-10 추가): 유일 표지 + 지시어 결속 + 다른 날짜처럼 다른 조건은 모두 양성과 같게 두고 그 규칙이 막는 요소만 넣는다. 다른 이유(결속 부재·다른 부정어)로 걸러지는 대조는 그 규칙을 시험하지 못한다(#247 4차: 자체 점검 I7 대조 '-였을지'가 통과로 적혔으나 같은 어미가 판정 탐침에서 오탐).

### 2-27-4. #247 4차 판정 — 보완 1회 더(I8·I9) (11-10, head `a21ddb3`)

- I5·I6·I7 반영(제품·시험 = 사본 `892766e`), 축별 자체 점검 표 제출 확인. 판정용 새 12차 head 3/4·오탐 2/6. 결함 분류(AGENT_ROLES 2.1): 오탐 2 = 점검표에 있던 서법 축의 다른 값 — **평가 측 I7 지시가 어미를 좁은 닫힌 목록으로 적은 지시 결함**, 미탐 1 = 점검표에 없던 제외 낱말 축. 점검표 4판(서법 20값·단정 8값·제외 낱말 8칸·정정 진술 6칸)을 만들어 두 축 전체를 한 번에 고친다. 사본 `b64a772` 사전 검증, 증분 [patches/TK-76_cycle3_incons_c_i8_i9_on_a21ddb3.diff](patches/TK-76_cycle3_incons_c_i8_i9_on_a21ddb3.diff). PR 코멘트로 전달.

```
[평가 측 판정 — #247 4차 TK-76 3주기 EVI-INCONS C 후속 A 묶음 (head a21ddb3, 기준 Steve 3d54f77), 11-10]

판정: 보완 1회 더(작음). I5·I6·I7은 반영됐다(제품·시험 = 평가 측 사본 892766e, diff 0). 축별 자체 점검 표(2-28)도 확인했다. 판정용 새 탐침 12차에서 양성 3/4·대조 오탐 2/6으로 오탐 기준(0)에 못 미쳤다. AGENT_ROLES 2.1(11-09 개정)에 따라 결함을 분류했다. 오탐 2건은 점검표에 있던 서법 축의 다른 값이다. 평가 측 I7 지시가 어미를 좁은 닫힌 목록으로 적은 **평가 측 지시 결함**이다. 미탐 1건은 점검표에 없던 축(제외 낱말이 사건 명사구의 수식어로 쓰인 꼴)이다. 두 축 모두 축 전체를 한 번에 고친다(I8·I9). 둘 다 Steve 3d54f77에도 있다.
- CI 결과 인용: 점수 하락 게이트·CodeQL 새 경고 게이트·은퇴 세트 비교·테스트 3종·Docker OCR 포함 필수 확인 전부 성공(같은 SHA 두 벌 모두).
- 평가 측 재실행: 평가 측 시험 20건 통과. 점검표 1~3판 224/224·0/118, 22/22·0/10, 6/7·0/17(사전 검증과 같음). 탐침 1~11차 만점·대조 0/66. 판정용 새 12차 Steve 3/4·2/6 → 이 head 3/4·2/6.
- 자체 점검 표 관련: I7 대조 3('-였을지')이 통과로 적혀 있으나 같은 어미가 12차에서 오탐을 냈다. 그 대조 문장이 I7이 아닌 다른 이유(유일 표지·지시어 결속 부재 등)로 걸러졌을 수 있다. 대조 문장은 '그 규칙만 빼면 잡히는 꼴'(유일 표지 + 지시어 결속 + 다른 날짜)로 지어야 그 규칙을 시험한다(NEXT 2-28에 추가).

원인과 고칠 것 (줄 번호는 a21ddb3의 packages/claim_engine/internal_inconsistency.py 기준)
I8 [오탐·기존, 평가 측 I7 지시 결함] 서법 축 — 1264행 _CLAUSE_NEGATION_FUTURE_RE
- 원인: I7이 '-다면·-라면·-더라도·-더라면·-는지·-은지·-는가·-을까·-할 이유'만 넣었다. 같은 축의 다른 값이 단정으로 읽힌다. 해당 꼴은 가정('-으면·-다 해도·-어도'), 의문('-을지·-느냐'), 선택('-거나·-든지'), 추측('-을 것·-을 수·-을 가능성·-듯·-겠'), 당위('-었어야'), 예정('-기로 하')이다. 점검표 4판 서법 축 대조 20칸 중 이 head 14칸 오탐(Steve 18칸), 12차 대조 2건.
- 고칠 것: I7 줄 뒤에 다음을 더한다.
  |으면(?!서)|다\s*(?:해도|하여도)|(?:었|였|았|했)어도|을지|할지|될지|느냐|거나|든지|던지|(?:을|할|될)\s*(?:것|수|가능성|듯|터)|(?:한|은|는|된)\s*듯|겠|(?:었|였|았|했)어야|해야\s*(?:했|하였|한다|합니다)|기로\s*(?:하|했|약정|합의|결정)
- '-면서'는 (?!서)로 막는다. 단정 어미('-였고·-였으며·-였는데·-였으나·-였음' 등)는 걸리지 않는다(점검표 4판 단정 8칸 양성).

I9 [미탐·기존] 제외 낱말 축 — 1258행 _SAME_EVENT_EXCEPTION_RE, 1536행 문장 단위 제외 가드
- 원인: 메모 2.4(1) '오기·정정' 제외를 낱말 검색으로 해서, '정정'·'오기'·'착오'가 사건 명사구의 수식어로 쓰인 문장('[정정류 낱말] [명사] [사건 명사]'·'[정정류 낱말] [사건 명사]')도 통째로 버린다. 점검표 4판 양성 8칸 중 이 head 6칸 미탐, 12차 양성 1건.
- 고칠 것: 1536행의 _SAME_EVENT_EXCEPTION_RE.search(sentence)를 _has_same_event_exception(sentence)로 바꾼다. 이 함수는 finditer로 각 일치를 보아, 일치가 정정류 낱말(_CORRECTION_WORDS = 오기·착오·오타·정정·수정)이고 앞 글자가 한글이 아니며 바로 뒤가 \s+(?:[가-힣]{2,12}\s+)?(?:사건 명사 대안)(?:서)?(?:을|를|은|는|이|가|에|의|과|와|도|만|으로|로|\s|$)이면 그 일치를 건너뛴다. 남은 일치가 하나라도 있으면 True다. 사건 명사 대안을 쓰는 정규식은 SAME_EVENT_NOUNS 정의 뒤에 만든다(지연 생성). '예비적·가정적·설령' 같은 주장 유형 낱말과 '정정합니다·오기이므로·착오로·정정 기재' 같은 진짜 정정 진술은 지금처럼 제외한다(점검표 4판 정정 진술 대조 6칸).

평가 측 사전 검증(사본 b64a772 = 이 head + I8·I9, 평가 측 재실행)
- 평가 측 시험 8건 추가(총 28건: I8 대조 6(서법별 매개변수)·I9 양성 1·I9 대조 1) — 이 head에서 7건 실패, 사본에서 28건 통과(변별 확인).
- 점검표 1~4판 224/224·0/118, 22/22·0/10, 6/7·0/17, 16/16·0/26(4판: 이 head 10/16·14/26). 3판 남은 1칸(날짜 셈 상대 날짜)은 사용자 범위 결정 대기.
- 탐침 1~12차 만점·대조 0/72(12차는 I8·I9 보정에 씀). 확인용 새 13차(보정 안 함) Steve 1/3·0/6, 이 head 2/3·0/6 → 사본 3/3·0/6.
- 관련 시험(70개 파일) 1,689건 통과. 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 악성 입력 11종(서법 어미·정정 낱말 반복 추가) 최악 0.09초(같은 시점 Steve 0.083초).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_incons_c_i8_i9_on_a21ddb3.diff — 제품 1파일(+25/−2), 평가 측 시험 8건. 이 head에 git apply --check 통과.

수용 기준: CI 전부 성공, 평가 측 시험 28건 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침·점검표 하락 없음. PR 본문 대응표에 I8·I9 행 추가, 축별 자체 점검 표에 I8(서법 축 전 값)·I9(정정류 낱말 수식어 대 정정 진술) 추가 — 대조는 '그 규칙만 빼면 잡히는 꼴'로. 귀속표 '세트 득점 0'·train '미측정'.
```

## 2-29. TK-76 3주기 후속 B 묶음(EVI-LOGIC 지각 구조 L1a~L4 · EVI-OVR O1~O6) 구현 지시 (11-10, 2-26절 진행 순서 B)

- 평가 측 사본 `25e5109`(기준 `3d54f77`, 저장소 밖) 사전 검증 — 축 조합 점검표(지각 구조 474+42칸, OVR 1판 258+416칸·2판 8+9칸) 전 칸 통과. 증분: [patches/TK-76_cycle3_b_bundle_logic_ovr_on_3d54f77.diff](patches/TK-76_cycle3_b_bundle_logic_ovr_on_3d54f77.diff).
- 공용 호증 문법(exhibits.py parse_exhibits)이 본문 '소을 제N호증'을 풀지 못하는 결함은 이 TK에서 OVR 검사 안에서만 보충했다(O5). 공용 문법 수정은 모든 서증 검사에 걸리므로 사용자 결정 사항으로 올렸다.

```
[평가 측 구현 지시 — TK-76 3주기 후속 B 묶음(EVI-LOGIC 지각 구조 L1a~L4 · EVI-OVR O1~O6), 기준 Steve 3d54f77, 11-10]

목적: 릴리스 전 마무리(NEXT 2-26 진행 순서 B). 사용자 결정 11-09 '식별된 추가 문제는 TK 구현 과정에서 함께 해결'. 한 PR, 제품 1파일 packages/claim_engine/evidence_consistency.py. 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 공용 입력(exhibits.py parse_exhibits·exhibit_rows)은 바꾸지 않는다(1절, #126 선례). 줄 번호는 3d54f77 기준.

평가 측 방법(AGENT_ROLES 2.1, 11-09 개정): 표본 탐침과 함께 축 조합 점검표(비공개)로 사본 전 칸 통과를 확인했다. 2-26 표의 4꼴(L1·L2·O1·O2)을 점검표로 펼치자 같은 규칙의 다른 결함 6꼴(L3·L4·O3~O6)이 드러나 함께 넣는다.

A. EVI-LOGIC 지각 구조(check_reasoning_structure, rule_id EVI.BEYOND_PERCEPTION_STRUCTURE, #241)
L1a [미탐] '[인칭 대명사] (두) 눈으로' 직접 지각 표지 — 61행 _DIRECT_RE
- 원인: '두 눈으로'만 받는다('제·내·저의·나의·본인의·이 눈으로' 놓침). 점검표 지각 표지 축 9값 중 2값 전부 미탐.
- 고칠 것: 두\s*눈으로 뒤에 |(?:제|내|저의|나의|본인의|이)\s*(?:두\s*)?눈으로 를 더한다.
L2 [미탐] 장소 조사 없는 체재 — 2835행 _L1_STAY_RE
- 원인: '(에|에서) … 있었/머물렀/지냈/중이었'만 받아 '[장소] 출장 중이었다'를 놓친다(점검표 체재 축 4값 180칸 미탐).
- 고칠 것: 끝에 |(?:출장|견학|여행|파견|체류|연수|유학)\s?중이었(?:습니다|다|음) 를 더한다. '입원·휴가'는 자리를 떠났는지 불분명해 넣지 않는다(대조 시험).
L3 [오탐·기존] 체재 장소가 곧 현장이거나 같은 자리인데 '다른 장소'로 본다 — 2865행 조건
- 원인: 규칙이 체재 장소와 지각 장소가 다른지 보지 않는다. '[시간 표지] [현장]에 있었다 → 그때 직접 보았다', '[다른 사람]과 함께 [장소]에 있었다', '[도시] 출장 중 → [같은 도시]의 장소에서 보았다'가 오탐(점검표 대조 '현장 체재'·'같은 자리' Steve 6칸).
- 고칠 것: 새 함수 _l1_elsewhere_stay(prev, sent)로 바꾼다(2865행의 _L1_STAY_RE.search(prev) 자리). (1) 체재 일치까지의 앞 문장에 같은 자리 표지 _L1_COLOC_RE = 현장|그\s?곳|거기|그\s?자리|같은\s?(?:곳|장소|공간|방|사무실|층|건물)|함께|같이|옆|곁|맞은\s?편|바로\s?앞 이 있으면 False. (2) 체재 일치 앞 20자~일치 끝의 한글 2자 이상 낱말에서 끝 조사(에서·에·의·은·는·이·가)를 뗀 뒤, 1인칭 지칭(저·제·나·내·본인·진술인·증인)·시간 낱말(당시·하루·종일·같은·시간·시각·그날·그때·사건·당일·무렵)·체재 서술어(있었·머물렀·지냈·중이었로 시작)를 뺀 장소 낱말이 지각 문장에 다시 나오면 False(같은 곳).
- 주의(평가 측 첫 시안에서 잡은 결함): 제외 목록은 조사를 뗀 꼴로 비교한다. '본인은'으로 적으면 '본인'이 남아 기존 시험 test_l1_variations_word_order_endings_and_lexicon이 깨진다.
L4 [오탐·기존] 체재한 사람이 진술인이 아니다 — 같은 함수
- 원인: '그 시각 제 배우자는 …에 있었다 → 그때 저는 직접 보았다'를 진술인의 체재로 본다(점검표 대조 Steve 3칸).
- 고칠 것: prev[:체재 일치 끝]에서 _OTHER_SUBJECT_RE(-이 부사·1인칭 제외) 주어가 있고 _FIRST_PERSON_RE가 없으면 False. 범위를 체재 일치 '시작'까지로 잡으면 '[사건]이 난 시간에 저는 …' 꼴에서 체재 일치가 '시간에'부터 시작해 1인칭 주어를 삼키고 '[사건]이'를 남의 주어로 읽는다(평가 측 첫 시안 결함 — 확인용 6차 양성 1 회귀로 잡음).

B. EVI-OVR(check_evidence_overreach, #230·#245)
O1 [미탐] '특정 채무 전부·전액 변제'를 영수·입금 서증 금액이 덮지 못함 — 1317행 'if not matched_pred_cats:' 앞
- 원인: 영수입금 범주는 '그 금액 한도에서' 완료를 덮는다(능력표 주석)고 하면서 서증 금액과 채무 금액을 비교하지 않는다. '[채무 명사] 전부를 갚았음은 갑 제N호증 [영수류](금 X원)'이 덮인 것으로 처리된다(1차 탐침 미탐 1, 점검표 160칸 미탐).
- 고칠 것: 완료_확정이 잡혔고 TOTAL_AMOUNT_MODIFIER_RE 일치가 (가) 특정 채무(is_specific_amt)이며 이 서증과 인용된 모든 서증이 영수입금 범주일 때, 인용 서증 행(name·purpose)의 금액 합 N(\d[\d,]*\s*(만|억)?\s*원)이 있고, 문서 전체에서 '[그 채무 명사](은|는|이|가|을|를|의)? (합계|총)? (금)? M원' 꼴의 최대값 M이 없거나 N < M이면 '전칭_전기간'을 더한다(영수입금은 전칭을 못 덮음 — 능력표 그대로). N ≥ M, 금액 없는 서증 행, 계약서 등 다른 범주 서증을 함께 인용한 경우, '[채무] 중 X원' 일부 주장은 그대로 둔다(대조 시험).
- 근거(증거 평가): 영수·입금 서증은 그 금액을 지급한 사실을 증명할 뿐, 그것이 채무 전부라는 점은 채무 금액을 따로 밝혀야 한다. 결과는 기존과 같이 C·SUSPICIOUS·사람 확인.
O2 [오탐·기존] 자기 측 의사표시를 '상대방 의사표시'로 셈 — 1315행(일방통지 외 범주 else 분기)
- 원인: 진술확인류(확인서·사실확인서·진술서)는 상대방 의사표시를 못 덮는데, 의사표시의 주체가 그 서증을 낸 쪽이어도 센다(6차 대조 1, 점검표 Steve 84칸 오탐).
- 고칠 것: else 분기에서 opp_subj가 있고, 주체 앞에 쌍방 꼴(당사자 (측)? (와|과|및) 당사자)이 없고, 술어가 계약 성립류(계약체결·약정성립·체결되었·성립되었)가 아니며, 주체 쪽(원고·신청인·채권자 → 갑 / 피고·피신청인·채무자 → 을)이 서증 행 party('소'를 뗀 값)와 같으면 '상대방의사표시'를 더하지 않는다.
O3 [판정 오류·기존] '작성자: 피신청인'을 '신청인'으로 읽음 — 977행 _detect_exhibit_sender
- 원인: ("원고","피고","신청인","피신청인",…) 순서의 문자열 포함 검사라 '피신청인' 안의 '신청인'이 먼저 잡힌다.
- 고칠 것: ("피신청인","신청인","원고","피고","채권자","채무자") 순서로, re.search(rf"(?<![가-힣]){p}", author)로 본다.
O4 [미탐·기존] 완료 술어 목적어에 '차임·원리금' 없음 — 664행 COMPLETION_PREDICATE_RE 첫 갈래
- 원인: 같은 파일의 금전 명사 목록 _AMOUNT_NOUN_PAT(차임·원리금 포함)과 완료 술어의 목적어 목록이 어긋나 '차임 전부를 지급하였음'이 완료로 잡히지 않는다.
- 고칠 것: 첫 갈래 (?:지급|변제|납부|이행|시공|공사|인도|대금|채무|…)에 차임|원리금 을 더한다.
O5 [미탐·기존] 본문의 '소을 제N호증' 인용을 못 읽음 — 1064행·1091행 parse_exhibits 호출
- 원인: 공용 호증 문법이 '소갑'은 '갑'으로 풀지만 '소을'은 풀지 못한다(평가 측 확인: parse_exhibits('소을 제7호증 …') → 빈 목록). 소을 서증 인용 문장이 통째로 빠진다.
- 고칠 것: 이 검사 안에서만 _ovr_parse_exhibits(text) = parse_exhibits(text) + (?<![가-힣])소(?P<party>갑|을)\s*제?\s*(?P<num>\d+)\s*호증 일치 중 없는 키 보충으로 두 호출을 바꾼다. 공용 문법은 그대로(별도 결정 사항으로 평가 측이 사용자에게 올림).
O6 [미탐·기존] 명사형 의사표시('[상대방]의 [승낙·동의]가 있었다') — 743행 _match_predicate_word, 794행 '4. 절 종결 위치' 앞
- 고칠 것: cat == "상대방의사표시"일 때 tail이 ^\s*[이가]\s*(?:있었|있다|있음|있는|있은|존재하였|존재했)(?!는지|는가|다면|더라도|으면|을지) 이면 True.

평가 측 사전 검증(사본 25e5109 = 3d54f77 + 위 전부, 평가 측 재실행)
- 평가 측 시험 tests/test_tk76_b_bundle_eval.py 21건(매개변수 포함, 양성 11·대조 10) — Steve에서 14건 실패(양성 전부·핵심 대조), 사본에서 21건 통과. 기존 tests/test_tk76_logic_eval.py 포함 31건 통과.
- 축 조합 점검표: 지각 구조(체재 10꼴 × 시간 표지 5 × 지각 표지 9 + 진술인 지칭 4 × 시간 위치 3, 대조 13꼴) Steve 226/474·오탐 9/42 → 사본 474/474·0/42. OVR 1판(채무 명사 5 × 전칭 3 × 술어 4 × 영수류 4, 금액 상태 6꼴; 주체 쪽 × 당사자 표기 8 × 의사표시 4 × 진술류 3) Steve 86/258·84/416 → 258/258·0/416. OVR 2판(만 원 단위·금액 뒤 서술·원리금·두 장 합계·측 주체·명사형·관형형·쌍방·소을) Steve 3/8·2/9 → 8/8·0/9.
- 지난 탐침: EVI-LOGIC 1~5차 Steve 6/6·4/4·4/4·2/3·5/6 → 사본 6/6·4/4·4/4·3/3·6/6, 대조 0/35. EVI-OVR 1·2·3·5·6·7·8차 Steve 8/9·5/5·6/6·6/6·5/5(오탐 1/7)·5/5·4/4 → 사본 전부 만점, 대조 0/48. 확인용 새 탐침(보정 안 함): EVI-OVR 9차 Steve 1/4·2/5 → 4/4·0/5, EVI-LOGIC 7차 Steve 1/3·3/5 → 3/3·0/5(6차는 L4 보정에 씀).
- 관련 시험(evidence_consistency·check_document·서증 관련 42개 파일) 990건 통과. 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 악성 입력 5종(띄어쓰기 없는 2만 자·체재 반복·체재 토큰 400·서증 199행·금액 3,000개) Steve 대비 같은 수준(check_document 2만 자 1.9초는 Steve와 같은 기존 동작).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_b_bundle_logic_ovr_on_3d54f77.diff — 제품 1파일(+116/−10), 평가 측 시험 1파일 21건. 3d54f77에 git apply --check 통과.

제출물·수용 기준
- 증분 그대로 적용해도 되고 같은 구조로 다시 써도 된다. PR 본문에 L1a~L4·O1~O6 → 바꾼 함수 → 시험 이름 대응표, 축별 자체 점검 표(NEXT 2-28: 항목마다 같은 축의 다른 값 3개 이상, 대조는 '그 규칙만 빼면 잡히는 꼴'로). 2-2 다: 귀속표 '세트 득점 0', train '미측정'.
- 수용: CI 전부 성공, 평가 측 시험 21건·기존 test_tk76_logic_eval 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침·점검표 하락 없음.
```

## 2-30. TK-149 공용 호증 문법 '소갑·소을' 구현 지시 (11-10, 사용자 '공용 호증 문법의 소을 인식 부분은 제안대로')

- 평가 측 사본 `1ec6773`(기준 `3d54f77`) 사전 검증 — 공용 입력 변경이라 전체 시험(11,115건)으로 확인. 증분: [patches/TK-149_so_eul_exhibit_grammar_on_3d54f77.diff](patches/TK-149_so_eul_exhibit_grammar_on_3d54f77.diff). B 묶음(2-29) 증분과 함께 적용해도 충돌 없음(평가 측 확인).
- **X5(평가 측 #245 보호 시험 단언 1건 변경): 사용자 승인(11-10 '승인').** 지시문의 'X5 사용자 승인' 수용 조건은 충족 — 남은 조건은 CI·평가 측 시험·새 탐침.

```
[평가 측 구현 지시 — TK-149 공용 호증 문법 '소갑·소을'(신청 사건 서증 부호), 기준 Steve 3d54f77, 11-10]

목적: 사용자 결정 11-10('공용 호증 문법의 소을 인식 부분은 제안대로'). B 묶음 사전 검증 중 발견했다(NEXT 2-29 O5). 공용 입력이라 모든 서증 검사에 걸리므로 B 묶음과 따로 한 PR로 낸다. 제품 2파일(packages/claim_engine/exhibits.py, packages/claim_engine/evidence_consistency.py). 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 줄 번호는 3d54f77 기준.

X1 [미탐·기존] 본문의 '소을 제N호증'을 호증으로 읽지 못함 — exhibits.py 28~30행 PARTY_RE
- 원인: '을'은 목적격 조사와 구별하려고 앞 글자가 한글이 아닐 때만 당사자로 본다((?<![가-힣]) 갈래). '소을'은 '소' 뒤의 '을'이라 빠진다('갑'은 이 제한이 없어 '소갑'은 '갑'으로 읽힘). 평가 측 확인: parse_exhibits('소을 제7호증 …') → 빈 목록. 신청 사건 서면에서 소을 인용과 그 목록 대조가 통째로 꺼진다.
- 고칠 것: '(?:갑|병)…' 갈래 다음에 |(?<=(?<![가-힣])소)을(?:\s?[가나다…](?=\s*(?:제\s*)?\d))? 갈래를 더한다('소' 앞이 한글이 아닐 때의 '소을'만). 받침 없는 '소' 뒤 목적격 조사는 '를'이므로 조사 '을'과 겹치지 않는다(대조 시험: '사실을 제3호증으로', '대소을 제2호증', '같은 법 제2조 제3호').
X2 [미탐·기존] 증거목록 줄 '1. 소갑 제1호증 …'·'소을 제2호증 …'이 행이 되지 않음 — exhibits.py 65행(parse_exhibits의 start), evidence_consistency.py 489행 _exhibit_lines
- 원인: 호증 표기(label)·위치(span)가 '갑·을'부터 잡혀 '소' 다음 위치(1)에서 시작하고, _exhibit_lines는 줄 첫머리(위치 0)에서 시작하는 호증만 목록으로 받는다(#245 O2에서 EVI-OVR 안에서만 보충했던 결함).
- 고칠 것: parse_exhibits에서 party가 '갑·을'이고 바로 앞 글자가 '소'이며 그 앞이 한글이 아니면 start를 1 줄인다(당사자 키 party는 '갑·을' 그대로, label·span만 '소'부터). _HANGUL_RE = re.compile(r"[가-힣]")을 CRIMINAL_PARTIES 아래에 둔다. 그러면 _exhibit_lines는 바꾸지 않아도 목록 줄이 행이 된다.
X3 [표시·기존] 신청 사건 서면의 결과 제목이 '갑·을 제N호증'으로 나옴 — evidence_consistency.py 2895행 check_document
- 원인: 여러 검사가 제목을 (당사자 키, 번호)로 다시 조립한다(368·1604~1690·2117·2215행 등). 서면이 '소갑·소을'로 적어도 '갑 제3호증'으로 보인다.
- 고칠 것: check_document의 반환 목록을 _so_notation_display(doc, findings)에 통과시킨다. 이 함수는 읽기 본문의 parse_exhibits 결과 중 party가 갑·을인 참조가 있고 그 label이 모두 '소'로 시작할 때만, 각 결과의 title·detail에서 (?<![가-힣])(갑|을)(\s?제\s?\d)를 '소\1\2'로 바꾼다. 맨 '갑·을' 인용이 섞여 있으면 바꾸지 않는다. Finding은 dataclass라 제자리 수정한다.

X4 [중복·TK-149로 생김] EVI-FORM이 같은 '소' 서증을 두 번 셈 — evidence_consistency.py 2690행 _form_section_rows
- 원인: EVI-FORM은 공용 행이 '소갑·소을' 목록 줄을 만들지 못하던 때의 자체 보충 행(party '소갑·소을')을 만든다. X2 뒤에는 공용 행(party '갑·을', id '소갑 …')도 생겨 같은 서증의 번역문 미첨부(G1)가 2건 나온다(기존 시험 test_evidence_form_structure::test_d3_applicant_sign_line_positive_and_control 2 != 1로 잡힘).
- 고칠 것: 반환 직전에 so_keys = {(r["party"][-1], r["number"]) for r in so_rows}를 만들고, rows에서 id가 '소'로 시작하고 (party, number)가 so_keys에 있는 공용 행을 뺀다. 공용 행의 label은 _row(368행)가 '갑 제N호증'으로 다시 조립하므로 label이 아니라 id로 판별한다(평가 측 첫 시안 결함).
X5 [보호 시험 단언 변경 — 사용자 승인 필요] tests/test_tk76_ovr_residual_eval.py::test_shared_exhibit_rows_unchanged_for_so_lines
- #245(11-09) 때 평가 측이 '공용 입력을 바꾸지 않는다'를 지키려고 넣은 보호 시험이 '공용 행은 소갑 목록 줄을 행으로 만들지 않는다'를 단언한다. 이 TK의 요구(사용자 결정)와 정면으로 충돌한다(CLAUDE.md: 옛 요구의 보호 시험은 구현을 되돌리지 않고 평가 측이 사용자 승인으로 고친다).
- 바꿀 것(증분에 포함): 같은 시험 이름에서 단언만 [('갑', 3, '소갑 제3호증')]로 바꾸고 주석에 TK-149 결정을 적는다. 시험 이름·삭제 변경 없음(check_test_edits '삭제·표시 변경 없음'). 사용자 승인 전에는 PR을 수용하지 않는다.

B 묶음(NEXT 2-29)과의 관계: B의 O5(_ovr_parse_exhibits)와 #245 O2(_ovr_so_exhibit_rows)는 이 TK 뒤에는 중복 보충이 되지만, 키가 이미 있으면 건너뛰므로 그대로 둬도 된다(평가 측이 두 증분을 함께 적용해 확인 — 충돌 없음, 점검표·탐침·시험 44건 같음). 병합 순서는 상관없다. **[11-10 정정: 병합 순서는 상관있다 — #248(B 묶음)을 먼저 병합한다. 2-30-1절]**

평가 측 사전 검증(사본 1ec6773 = 3d54f77 + X1~X5, 평가 측 재실행)
- 평가 측 시험 tests/test_tk149_so_exhibits_eval.py 13건(매개변수 포함) — Steve에서 9건 실패, 사본에서 13건 통과.
- 호증 표기 점검표(당사자 4 × 표기 8꼴(기본·제 없음·붙임·가지번호·묶음·범위·이어 적기·공동 당사자) × 문맥 5(문두·공백·괄호·'및'·줄머리), 대조 8꼴) Steve 120/160 → 사본 160/160, 대조 오탐 0/8. 하류 검사(신청 사건 서면 5꼴): 본문·목록이 맞는 서면 새 결과 0, 목록에 없는 소갑·소을 인용은 EVI.EVIDENCE_LIST_MISMATCH로 잡힘(Steve는 놓침), 제목은 '소갑·소을' 표기.
- 전체 시험(공용 입력 변경이라 관련 시험이 아니라 전체) 11,115건 통과·실패 0(건너뜀 35). 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0. 다른 유형 탐침 EVI-FORM 1~10차·EVI-OVR 1~9차 Steve와 같음.
- 악성 입력 5종(소을 3,000개·'소' 2만 자·조사 '을' 5,000개 등) 최악 0.02초.
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-149_so_eul_exhibit_grammar_on_3d54f77.diff — 제품 2파일(+24/−2), 평가 측 시험 1파일 13건 + 보호 시험 단언 1건 변경(X5). 3d54f77에 git apply --check 통과.

제출물·수용 기준
- 증분 그대로 적용해도 되고 같은 구조로 다시 써도 된다. PR 본문에 X1~X3 → 바꾼 함수 → 시험 이름 대응표, 축별 자체 점검 표(NEXT 2-28: 표기 꼴·문맥 축의 다른 값 3개 이상, 대조는 '그 규칙만 빼면 잡히는 꼴'로 — 예: 받침 있는 낱말 + '을 제N호증'). 2-2 다: 귀속표, train '미측정'.
- 공용 입력 변경이므로 CI 전 시험·은퇴 세트 비교·점수 하락 게이트 성공이 필수다. 수용: X5 사용자 승인, CI 전부 성공, 평가 측 시험 13건·기존 EVI-FORM 시험 통과, 판정용 새 탐침(신청 사건 서면) 양성 2/3 이상·대조 오탐 0.
```

## 2-31. TK-76 3주기 후속 C 묶음(산식 Q4·Q5) 구현 지시 (11-10, 2-26절 진행 순서 C)

- 평가 측 사본 `1a552f3`(기준 `3d54f77`) 사전 검증 — 축 조합 점검표(Q4 206+207칸, Q5 32+34칸) 전 칸 통과. 증분: [patches/TK-76_cycle3_calc_q4q5_on_3d54f77.diff](patches/TK-76_cycle3_calc_q4q5_on_3d54f77.diff).

```
[평가 측 구현 지시 — TK-76 3주기 후속 C 묶음(산식 Q4·Q5), 기준 Steve 3d54f77, 11-10]

목적: 릴리스 전 마무리(NEXT 2-26 진행 순서 C). 사용자 결정 11-09 '식별된 추가 문제는 TK 구현 과정에서 함께 해결'. 한 PR, 제품 1파일 packages/claim_engine/calculation.py. 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 줄 번호는 3d54f77 기준.

평가 측 방법(AGENT_ROLES 2.1): 2-26 표의 Q4를 축 조합 점검표(비공개)로 펼치자, 같은 엔진의 분배형 곱셈 축(Q5)이 Steve에서 전 칸 미탐으로 드러나 함께 넣는다.

Q4 [미탐] 피연산자 앞 '[수][명사]' 이름표 — 516행('=' 산식)·551행 뒤(서술형 산식)
- 원인: '[N][명사] [명사] [수량][단위]와 [M][명사] [명사] [수량][단위]를 합하면 [결과]'에서 'N[명사]'가 피연산자로 들어간다. 단위가 [명사]와 [단위]로 섞여 _is_unit_compatible(덧셈은 단위 하나)이 거짓이 되어 검산 자체가 꺼진다(산식 탐침 5차 미탐 1, 점검표 이름표 명사 10 × 단위 5 × 연결 4 = 200칸 Steve 전 칸 미탐). '제N…'은 이미 빠지고, 차수(N차·N회차)·달력(N월·N분기)·기간(N월분)은 기존 규칙이 이름표로 본다 — 이 축은 그 밖의 '수+명사'다.
- 고칠 것: _units_ok(435행) 앞에 _drop_quantity_labels(ops, res_token, text)를 두고, '=' 산식은 res_token = res[0] 다음, 서술형은 Q2 거르기(551행 블록) 다음에 ops = _drop_quantity_labels(...)를 넣는다. 규칙: 결과 단위 ru(_eff_unit)가 있을 때, 토큰 t와 바로 다음 토큰 nxt에 대해 (1) t의 한글 단위가 있고 ru와 다르며 (2) nxt의 단위가 ru와 같고 (3) t의 조사가 없거나 의·에서·에이고 (4) 둘 사이 글자가 15자 이하이며 연결어 _LABEL_LINK_BLOCK_RE = 와|과|및|그리고|더하기|빼기|곱하기|나누기|각|[+\-−×*xX✕✖=,·] 이 없으면 t를 뺀다. 뺀 뒤 피연산자가 2개 미만이면 원래 ops를 돌려준다(곱셈의 인원·횟수 보존 — '3명 × 70,000원'·'3명 각 …원씩').
- 기호 단위: 토큰 추출(356행)은 한글 단위만 잡아 '45㎡'의 단위가 비어 있다. 토큰 추출은 바꾸지 말고(기존 곱셈·백분율 판정 보존), 이 판정 안에서만 _eff_unit(tok, text) = tok.unit 또는 수 바로 뒤의 _SYMBOL_UNIT_RE = \s*(㎡|㎏|㎞|㎝|㎜|㎖|ℓ|m²|kg|km|cm|mm|m|L|%)(?![A-Za-z]) 를 단위로 쓴다(평가 측 첫 시안에서 ㎡ 50칸 미탐으로 잡음).
- 명사 목록을 두지 않는 구조 규칙이다(2-2).

Q5 [미탐·기존] 분배형 곱셈('[N][명·곳·개 …] 각/각각/1인당 [X]원씩 … 합계·모두 [T]원') — 457행 _evaluate_formula_operands의 피연산자 2개 분기
- 원인: 결과 앞 '합계·모두'를 보고 덧셈 규칙(합계|더하…)이 먼저 적용되고, '씩' 곱셈 규칙은 첫 피연산자에 붙은 '씩'만 본다('8시간씩 5일 … 모두'는 잡히지만 '3명 각 5만 원씩 … 합계'는 놓침). 점검표 분배 표지 4 × 개수 표현 4 × 단가 2 = 32칸 Steve 전 칸 미탐.
- 고칠 것: 457행 분기 맨 앞에서, after_ops에 _TOTAL_MARK_RE가 있고 ops[0]·ops[1]의 단위가 다르며(인원·개수 × 단가), (ops[1]의 조사가 '씩'이거나 ops[1] 뒤가 '씩'이거나, 두 피연산자 사이에 (?<![가-힣])각(?:각)?(?![가-힣])이 있고 ops[1] 부근에 '씩'이 있으면) ops[0]×ops[1], '*'를 돌려준다. '1인당' 꼴은 Q4가 '1인당'을 이름표로 빼서 같은 규칙에 걸린다.
- 주의(평가 측 첫 시안에서 잡은 결함): 단위 다름 조건이 없으면 '기본급 [X]원과 수당 [Y]원씩을 합계 [T]원'을 곱으로 읽어 오탐이 난다(대조 시험).

평가 측 사전 검증(사본 1a552f3 = 3d54f77 + Q4·Q5, 평가 측 재실행)
- 평가 측 시험 tests/test_tk76_calc_q4q5_eval.py 12건(양성 6·대조 6) — Steve에서 6건 실패(양성 전부), 사본에서 12건 통과.
- 축 조합 점검표: Q4(이름표 명사 10 × 수량 단위 5(㎡ 포함) × 연결 4, 금액 3꼴, 시간 이름표, 곱셈 보존 2꼴; 같은 수의 맞는 합계 대조) Steve 1/206·0/207 → 사본 206/206·0/207. Q5(32칸, 대조 34칸) Steve 0/32 → 32/32·0/34.
- 지난 산식 탐침(nm1~6, probe3~6) 하락 없음 — nm5 4/5 → 5/5(Q4), nm4의 1건은 기존 '할인' 가드(의도된 제외, 범위 밖). 확인용 새 산식 7차(보정 안 함) Steve 0/4 → 4/4·대조 오탐 0/5.
- 관련 시험(calculation·ARITHMETIC 관련 37개 파일) 895건 통과. 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0(세트 득점 0). 악성 입력 7종(띄어쓰기 없는 2만 자·같은 문장 400회·이름표 3,000개·기호 단위 3,000개·분배 문장 400회 등) Steve와 같은 수준(분배 문장 400회 1.5초는 Steve와 같은 기존 비용).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_calc_q4q5_on_3d54f77.diff — 제품 1파일(+35/−0), 평가 측 시험 1파일 12건. 3d54f77에 git apply --check 통과.

제출물·수용 기준
- 증분 그대로 적용해도 되고 같은 구조로 다시 써도 된다. PR 본문에 Q4·Q5 → 바꾼 함수 → 시험 이름 대응표, 축별 자체 점검 표(NEXT 2-28: 이름표 명사·단위·연결어, 분배 표지·개수 표현 축의 다른 값 3개 이상, 대조는 '그 규칙만 빼면 잡히는 꼴' — 같은 수의 맞는 합계). 2-2 다: 귀속표, train '미측정'.
- 수용: CI 전부 성공, 평가 측 시험 12건·기존 산식 시험 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 산식 탐침 하락 없음.
```

## 2-32. TK-76 3주기 후속 D 묶음(날짜 검증 성능 P1) 구현 지시 (11-10, 2-26절 진행 순서 D)

- 평가 측 사본 `674dd21`(기준 `3d54f77`) 사전 검증 — 성능만 바꾸는 수정이라 결과 동일성을 차등 비교(문장 4,907개·긴 문서 320개, 차이 0)로 확인. 증분: [patches/TK-76_cycle3_date_perf_p1_on_3d54f77.diff](patches/TK-76_cycle3_date_perf_p1_on_3d54f77.diff).

```
[평가 측 구현 지시 — TK-76 3주기 후속 D 묶음(날짜 검증 성능 P1), 기준 Steve 3d54f77, 11-10]

목적: 릴리스 전 마무리(NEXT 2-26 진행 순서 D). #239 판정 때 기록한 기존 경로 비용(띄어쓰기 없는 2만 자 약 43초, 같은 꼴 800회 약 11초)을 없앤다. 한 PR, 제품 1파일 packages/claim_engine/date_verifier.py. **판정 결과는 바뀌지 않아야 한다(성능만).** 설계 메모 불요(평가 측 사본으로 사전 검증 완료). 줄 번호는 3d54f77 기준.

진단(평가 측 재실행, 정규식별 시간 측정)
- 띄어쓰기 없는 한글 2만 자 + 날짜 문장: Steve 약 34초 — 거의 전부(34.3초)가 CONJUGATED_ORDER_RE.finditer.
- 날짜+관형어+명사 800회 한 절: Steve 약 9초 — TARGET_PRE_RE.search 5.0초(사건 801번 × 절 앞부분 전체), 사건 뒤 텍스트에 거는 '…에 대한 것이다·처분' 정규식 1.4초, SUBJECT_RE 0.8초, 나머지는 파이썬 반복.

P1-a [이차 시간] 816행 CONJUGATED_ORDER_RE = (?P<verb>[가-힣]+)\s*(?P<conn>뒤|후|다음)|다가
- 원인: 길이 제한 없는 [가-힣]+가 긴 한글 연속에서 시작 위치마다 끝까지 훑고 되돌아간다.
- 고칠 것: verb를 [가-힣]{1,10}으로. _has_narrative_order_connective(825행)는 동사의 마지막 글자(어미 은·는·던·후·뒤·다음, 받침 ㄴ)만 보므로 결과가 같다.
P1-b [이차 시간] 1227·1229행 TARGET_PRE_RE.search(pre_text) / search(clause_text[:e_end + 1])
- 원인: TARGET_PRE_RE(706행)는 끝에 \s*$가 붙는 꼴이라 일치 길이가 짧은데(공백 제외 약 150자), 사건마다 절 앞부분 전체를 검색한다.
- 고칠 것: 715행 앞에 _TARGET_WINDOW = 400을 두고 두 호출을 pre_text[-_TARGET_WINDOW:], clause_text[:e_end + 1][-_TARGET_WINDOW:]로 바꾼다(끝에 붙는 일치는 창 안에서 시작하므로 결과 같음).
P1-c [반복 비용] 1258~1263행 m_post = re.search(대상 명사구 + '에 대한·대하여·따른' + '것이다·입니다·처분·결정·명령', following_evt)
- 고칠 것: _POST_TARGET_TAIL_RE = 에\s*(?:대한|대하여|따른)\s*(?:것(?:이다|입니다)|처분|결정|명령) 을 두고, `if not target:`를 `if not target and _POST_TARGET_TAIL_RE.search(following_evt):`로 바꾼다(고정 꼴이 없으면 전체 정규식도 일치할 수 없으므로 결과 같음). m_post는 이 블록 안에서만 쓴다(평가 측 확인).
- SUBJECT_RE(1179행)는 손대지 않는다(절 단위로 한 번에 모으면 경계 걸친 일치가 달라질 수 있어 결과 동일성을 보장하기 어렵다).

평가 측 사전 검증(사본 674dd21 = 3d54f77 + P1-a~c, 평가 측 재실행)
- 시간: 띄어쓰기 없는 2만 자 Steve 34.3초 → 0.12초, 800회 꼴 9.1초 → 2.3초, 1,500회 고아 날짜 0.1초 → 0.1초.
- 결과 동일성(차등 비교): 저장소 시험·평가 측 탐침의 날짜 포함 문장 4,907개(결과 있는 문장 168) Steve·사본 출력(유형·제목·설명·rule_id) 차이 0. 그 문장을 30개씩 한 줄로 이은 긴 문서 320개(마침표 유지·제거 두 벌, 결과 443건) 차이 0. 날짜 탐침 1~9차 Steve와 같음.
- 평가 측 시험 tests/test_tk76_date_perf_p1_eval.py 2건 — Steve에서 시간 시험 1건 실패(상한 5초, Steve 34초), 사본 통과.
- 관련 시험(date_verifier·TIMELINE 관련 17개 파일) 413건 통과. 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0.
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_date_perf_p1_on_3d54f77.diff — 제품 1파일(+11/−4), 평가 측 시험 1파일 2건. 3d54f77에 git apply --check 통과.

제출물·수용 기준
- 증분 그대로 적용해도 되고 같은 구조로 다시 써도 된다. 다시 쓰면 결과 동일성을 같은 방식(차등 비교)으로 보이고 PR 본문에 적는다. 귀속표 '세트 득점 0'(성능만), train '미측정'.
- 수용: CI 전부 성공, 평가 측 시험 2건 통과, 평가 측 차등 비교 차이 0(판정 시 평가 측 재실행), 날짜 탐침 결과 동일.
```

### 2-29-1. #248 B 묶음 1차 판정 — 보완 1회(L4b·L5·L6) (11-10, head `2520296`)

- 제품·시험 = 사본 `25e5109`(diff 0). OVR 10차 4/4·0/5 통과, LOGIC 8차 미달. 점검표 2판(다른 때 표지·문장 안·줄 나뉨·다른 사람 지칭 축)으로 축 전체 수정 — 사본 `2680f72`, 증분 [patches/TK-76_cycle3_b_l5_l6_on_2520296.diff](patches/TK-76_cycle3_b_l5_l6_on_2520296.diff). CI 일시 실패 1건(화면 시험, 평가 측 재실행 3회 통과). PR 코멘트로 전달.

```
[평가 측 판정 — #248 1차 TK-76 3주기 후속 B 묶음 (head 2520296, 기준 Steve 3d54f77), 11-10]

판정: 보완 1회(작음). EVI-OVR O1~O6은 수용 수준이고, EVI-LOGIC 지각 구조에서 판정용 새 탐침 미달 → L4b·L5·L6을 고치면 수용한다. 제품·시험은 평가 측 사본 25e5109와 같다(diff 0). 축별 자체 점검 표 제출 확인.
- CI 결과 인용: 한 벌은 필수 확인 전부 성공. 다른 한 벌의 'PostgreSQL/pgvector + Celery 브로커' 시험 1건 실패 — tests/test_drive_rag_relevance.py::test_web_shows_drive_health_selection_and_duplicates의 Playwright 요소 캡처 30초 시간 초과(11,089건 통과). 이 PR이 바꾸지 않은 화면 시험이고, 같은 SHA의 다른 한 벌에서 통과했으며, 평가 측 재실행 3회 모두 통과 — 환경 요인 일시 실패로 본다(수용 조건 아님. 보완 커밋의 CI에서 다시 확인).
- 평가 측 재실행: 평가 측 시험 21건 통과. 점검표 지각 구조 1판 474/474·0/42, OVR 1판 258/258·0/416, 2판 8/8·0/9(사전 검증과 같음). 지난 탐침 LOGIC 1~7차·OVR 1~9차 만점·대조 오탐 0. 판정용 새 탐침: OVR 10차 Steve 2/4·1/5 → 이 head 4/4·0/5(통과). LOGIC 8차 Steve 1/3·3/5 → 이 head 1/3·1/5(미달).
- 결함 분류(AGENT_ROLES 2.1): LOGIC 8차의 미탐 1·오탐 1은 점검표에 없던 축(문장 안·줄 나뉨 체재, 다른 때 표지)이다. 8차 양성 1건('[장소] 야간 근무 중' 꼴)은 현장이 그 장소일 수도 있어 평가 측 탐침 결함으로 빼고 기록한다. 축을 펼친 점검표 2판에서 다른 때 표지 96칸이 이 head에서 전부 오탐(Steve 48칸 — L2로 조사 없는 체재를 받으면서 같은 결함 칸이 늘었다), 문장 안 체재 264칸 미탐(Steve와 같은 기존 결함). 확인용 9차에서 다른 사람 지칭 축의 값 하나('[명사]의 [한 음절 명사]는')가 더 드러나 함께 넣는다(L4b).

원인과 고칠 것 (줄 번호는 2520296의 packages/claim_engine/evidence_consistency.py 기준)
L5 [오탐·기존, L2로 늘어남] 지각 문장이 다른 때를 밝혀도 같은 때로 본다 — 2943행 _L1_MOVE_RE, 2970행 L1 조건
- 원인: 이동·시간 경과 표지가 '뒤에·이후·나중에'뿐이라 '[N일] 뒤·이틀 후·다음 날·이튿날·전날·그 후·며칠 뒤·사흘 전' 같은 다른 때 표지를 놓친다.
- 고칠 것: _L1_OTHER_TIME_RE = (?:\d+|하루|이틀|사흘|나흘|닷새|엿새|이레|며칠|몇|한|두|세|일주일|열흘|보름)\s?(?:일|시간|분|주일?|달|개월|해|년)?\s?(?:뒤|후|전|만에)(?![가-힣])|다음\s?날|이튿날|익일|전날|그\s?(?:후|뒤|전|다음)(?![가-힣])|이후|이전|나중에|훗날|얼마\s?(?:뒤|후) 를 두고, 지각 문장(또는 L6의 뒷부분)에 있으면 L1을 적용하지 않는다.
L6 [미탐·기존] 한 문장 안·줄 나뉨에서 체재 절이 연결어미로 이어지는 꼴 — 2970행 L1 블록
- 원인: L1은 '앞 문장 체재(…습니다·다·음) + 다음 문장 지각'만 보고, 문장 안 규칙(perception_conflict의 _ELSEWHERE_RE)은 '있었·머물렀·지냈 + 으나·지만·는데'와 '같은·그 시각·동시에'만 받는다. '[장소]에 있었는데/으므로/고/기에, 그때 … 직접 보았다', 그리고 PDF 줄바꿈으로 앞 줄이 '…연수 중이었으므로,'로 끝나는 꼴을 놓친다.
- 고칠 것: _L1_INLINE_RE = (?P<stay>(?:에|에서)\s?(?:[가-힣0-9]+\s){0,4}?(?:있었|머물렀|지냈|중이었)|(?:출장|견학|여행|파견|체류|연수|유학)\s?중이었)(?P<conn>으므로|므로|는데|으나|지만|고|기에|어서|으며)\s?,?\s 를 두고 L1 블록을 (앞부분, 뒷부분, 꼴) 쌍으로 바꾼다. (1) 앞 줄이 _L1_INLINE_RE로 끝나면 그 체재 절을 '…습니다.'로 바꾼 것을 앞 문장으로 쓴다(줄 나뉨). (2) 앞 문장 쌍이 성립하지 않고 이 문장 안에 _L1_INLINE_RE가 있으면 (sent[:conn 시작] + '습니다.', sent[일치 끝:])를 쌍으로 쓰고 pattern 'ELSEWHERE_IN_SENTENCE'. 두 경우 모두 기존 조건(_l1_elsewhere_stay·시간 표지·이동·매개·_PERC_RE·_DIRECT_RE·perception_conflict)과 L5를 그대로 적용한다. 결과 제목·설명은 꼴에 따라 '앞 문장의'/'같은 문장 안의'로 나눈다.
L4b [오탐·기존] '[명사]의 [한 음절 명사]는·제 [한 음절 명사]는' 주어를 진술인으로 본다 — 2941행 _l1_elsewhere_stay의 주어 검사
- 원인: _OTHER_SUBJECT_RE는 부사 '-이'와 구별하려고 두 음절 이상 명사만 받아 '원고의 딸은·제 형은·그의 처는'을 놓친다.
- 고칠 것: _POSSESSED_SUBJECT_RE = (?:[가-힣]+의|제|내|저의|그|저희|우리)\s+(?:[가-힣]+\s+)?[가-힣]{1,4}(?:은|는|이|가)\s 를 두고, others가 비었을 때 이것이 맞으면 다른 사람 주어로 본다(1인칭 표지가 있으면 기존대로 진술인).

평가 측 사전 검증(사본 2680f72 = 이 head + L4b·L5·L6, 평가 측 재실행)
- 평가 측 시험 10건 추가(총 31건, 기존 test_tk76_logic_eval 10건 포함 41건: L5 대조 4·L6 양성 2·L6 대조 1·L4b 대조 3 — 매개변수 포함) — 이 head에서 8건 실패, 사본에서 41건 통과.
- 지각 구조 점검표 2판(다른 때 표지 12값 × 체재 4 × 지각 2, 같은 때 표지 4, 문장 안 연결어미 6 × 체재 4 × 시간 표지 3 × 지각 표지 4, 줄 나뉨 24, 다른 사람 지칭 8값, 문장 안 대조 5꼴) Steve 36/332·오탐 64/151, 이 head 44/332·100/151 → 사본 332/332·0/151. 1판 474/474·0/42 유지.
- 탐침: LOGIC 1~9차 하락 없음(8차 2/3 — 남은 1건은 위 평가 측 탐침 결함), 확인용 새 10차(보정 안 함) Steve 1/3·1/5, 이 head 1/3·0/5 → 사본 3/3·0/5. OVR 1~10차 그대로.
- 관련 시험(42개 파일) 1,000건 통과. 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0. 악성 입력(문장 안 체재 300회·토큰 3,000개·다른 때 300회 등) 최악 0.012초.
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.
- 증분: docs/handoff/patches/TK-76_cycle3_b_l5_l6_on_2520296.diff — 제품 1파일(+33/−6), 평가 측 시험 10건. 이 head에 git apply --check 통과. TK-149(공용 호증 문법) 증분과 함께 적용해도 충돌 없음(평가 측 확인).

수용 기준: CI 전부 성공, 평가 측 시험 31건·기존 test_tk76_logic_eval 통과, 판정용 새 탐침 양성 2/3 이상·대조 오탐 0, 지난 탐침·점검표 하락 없음. PR 본문 대응표에 L4b·L5·L6 행, 축별 자체 점검 표에 다른 때 표지·문장 안 연결어미·줄 나뉨·다른 사람 지칭 축(대조는 '그 규칙만 빼면 잡히는 꼴'). 귀속표 '세트 득점 0'·train '미측정'.
```

### 2-30-1. #249 TK-149 판정 — 수용(조건 2개) (11-10, head `24f20cf`)

- 제품·시험 = 사본 `1ec6773`(diff 0), X5 사용자 승인(11-10). PR 코멘트로 전달.
- 조건 1: CI 한 벌 전부 성공, 다른 한 벌 SQLite 시험 1건 판정 시점 실행 중(실패 0) — 성공 확인 뒤 병합.
- 조건 2(평가 측 지시 정정): **#248(B 묶음) 병합 뒤 병합.** 단독 적용 시 EVI-OVR 기존 오탐(자기 측 의사표시, #248 O2·O3이 고침)이 '소을' 서면으로 번진다(OVR 10차 대조 1/5 → 2/5, #248 보완본과 함께면 0/5). 2-30 지시문의 '병합 순서는 상관없다'는 평가 측 오류.
- 평가 측 재실행: 시험 45건 통과, 호증 표기 점검표 160/160·0/8, 판정용 새 탐침(신청 사건 서면) Steve 0/4 → 4/4·대조 0/6·다른 유형 새 결과 0, EVI-FORM 1~10차 같음. CI 결과 인용: 게이트·은퇴 비교·CodeQL·OCR·PostgreSQL 성공.

### 2-31-1. #250 C 묶음 1차 판정 — 보완 1회(Q6) (11-10, head `a78ac9d`)

- 제품·시험 = 사본 `1a552f3`(diff 0). 판정용 새 8차 Steve 0/4·0/6 → head 4/4·**3/6**(회귀). **평가 측 Q5 설계(2-31) 결함**: 단가의 기준이 인원수와 다른 꼴(시간당·매월·1주당·사이의 다른 수량)을 개수 × 단가로 검산해 A등급 오탐. 사전 검증 점검표에 '단가의 기준' 축이 없었다. 축을 펼친 점검표에서 head 대조 112/146칸 오탐(Steve 0).
- 보완 Q6(_other_rate_basis): 사본 `d3d1582`, 증분 [patches/TK-76_cycle3_calc_q6_on_a78ac9d.diff](patches/TK-76_cycle3_calc_q6_on_a78ac9d.diff)(제품 +34/−1, 시험 6건). 시험 18건(head 4 실패), 점검표 35/35·0/146·Q4 206/206·0/207, 탐침 1~9차 하락 0, 확인용 10차(보정 안 함) head 3/3·4/6 → 사본 2/3·0/6(남은 1건: 개수 낱말과 기준 낱말이 동의어인 꼴 — 미탐 방향 한계), 관련 901건, 은퇴·고정 변화 0. 원인·고칠 것 전문은 PR 코멘트.

## 2-33. 11-11 판정 — #247~#251 병합 사후 확인, LV-01~06(#252~#257) 1차 판정·보완 지시

### 2-33-1. #247~#251 병합 사후 확인(평가 측 재실행, Steve `649a162`)
- 사용자가 #247~#251을 병합했다(평가 측 부재 중). 병합분과 평가 측 마지막 사본 대조:
  - #247(A 묶음) = 사본 `b64a772`(I8·I9) diff 0. **#247 보완 지시문은 다시 낼 것이 없다**(I8·I9가 그대로 반영·병합됨).
  - #248(B 묶음) = 사본 `2680f72`(L4b·L5·L6) diff 0, #249(TK-149) = 사본 `1ec6773`(X1~X5) diff 0.
  - #250(C 묶음)·#251(D 묶음)에는 **평가 측이 판정하지 않은 커밋**이 함께 병합됐다: Q7(`1e7f269`)·Q7-R1(`5a155f0`)·P1d(`359f2c9`, 설계 메모와 `test_codex_*` 시험 동반).
    - P1d: 날짜 차등 비교(480문서·결과 607건) 기준 대비 차이 0, 처리 시간 2만 자 0.08초·800회 2.1초 — 문제없음.
    - Q7: 산식 점검표 Q4 206/206·0/207 유지, **Q5 양성 35/35 → 33/35**('N개 업체에 업체당 … 합계' 꼴 2칸 미탐, 오탐 0). 작은 재현율 후퇴 — 다음 산식 TK에서 회복(아래 D6).
  - Steve `649a162`: 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 dev 82.6·holdout 81.9·FP 0 — 변화 0.
- **B 묶음 지각 구조 규칙(L1, #241·#248 병합·미배포)의 정밀도 결함**: 평가 측 11-10 발견(통상 목격 진술 오탐). 보정에 쓰지 않은 확인 탐침 12차: Steve 양성 5/5·대조 오탐 8/12, 평가 측 L7 사본 6/12, '양보 연결만' 안 2/12(양성 3/5). 세 안 모두 수용 수준이 아니다(원인: '에서'가 사건 장소인지, 출처('가방에서')·조망 지점('창가에서')인지 규칙으로 가리지 못함). → D4 사용자 결정.

### 2-33-2. LV-01~06 1차 판정 (head `d8af690` — 연쇄 PR 끝, 기준 Steve `3d54f77`)
- CI 결과 인용: 두 벌 모두 시험 실패(출력 계약 시험 16건, 근거 시험 1건, 한 벌에서 API 시험 2건), 점수 하락 게이트 한 벌 실패(로그에 원인 줄 없음)·다른 벌 성공.
- 평가 측 재실행(Steve `649a162` + `d8af690` 합본, 충돌 없음): 전체 11,427건 중 실패 17(출력 계약 16 `test_tk72_citation_output_compatibility`, 근거 1 `test_ground_truth_prepared_brief::test_precedent_and_regulation_existence`). API 시험 2건은 평가 측에서 통과(CI 일시 실패로 봄). 고정 82.6/81.9/0 변화 0. 은퇴 20261009 56.9→57.3, 20261025 34.1→36.4 — **득점 귀속 결과 인위적 득점**: `citation.context`를 1,000자로 넓힌 탓에 같은 UNVERIFIED 결과의 발췌가 정답 항목 낱말과 겹쳐 점수가 붙었다(형 불일치로 버려진 낱말 일치 25→43). 그 확장만 되돌리면 두 세트 모두 기준값.
- 점검 스크립트: 하드코딩·시험 약화·보호 경로 통과. 평가 세트 문구 의심 9건은 모두 설명·안내 문안(판정 규칙 아님) — 문제 삼지 않는다.
- 평가 측 축 탐침(비공개, 꼴만): 날짜 역할 8칸, 인용문 차이 12칸, 판시 왜곡 8칸, 처리 시간.

판정: **#252~#257 보완 1회**(제품 5파일 +84/−19, 평가 측 사본 `dd951fb`에서 사전 검증 완료) + 사용자 승인·결정 4건(X6·D3·D4·D5, 2-33-3).

### 2-33-3. 사용자 결정·승인 필요 항목
- **X6(보호 시험 단언 변경, 승인 필요)**: `tests/test_ground_truth_prepared_brief.py::test_precedent_and_regulation_existence`가 '형식이 맞는데 미러에서 찾지 못한 판례 = CRITICAL + FAKE_PRECEDENT'를 단언한다. 11-10 사용자 수용 P1(존재 판정 3단화, 부존재 확정만 CRITICAL)과 충돌. 새 단언: severity MEDIUM, 태그 SOURCE_LIMIT, levels.authority_status UNCONFIRMED_SOURCE_LIMIT(시험 이름 유지). 옛 요구 시험이 새 요구와 충돌하므로 평가 측이 승인 뒤 고친다(CLAUDE.md).
- **D3(기존 규칙 법리, 새 TK-150 제안)**: `config/legal_rules/rules.json` ADMIN.DEADLINE_CALCULATION_SCENARIOS가 '이의신청 결과 통지일 기준 제소기간 기산' 주장을 일률로 CONTRADICTED·A로 본다. 행정기본법 제36조 제4항은 이의신청 결과를 통지받은 날부터 90일 이내 행정심판·행정소송을 허용하고, 부칙 제6조는 이를 같은 법 부칙 제1조 단서 시행일(2023. 3. 24.) 이후 처분부터 적용한다([국가법령정보센터 행정기본법](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=246871)). 규칙 설명이 근거로 든 대법원 2014. 4. 24. 선고 2013두10809 판결은 그 이전 법리다. 평가 측 탐침: 2024년 처분에도 A등급 CONTRADICTED(Steve·LV 모두). 제안: 처분일 2023. 3. 24. 이후이거나 처분일 불명이면 '확인 필요'(SUSPICIOUS·C)로 낮추고, 그 이전 처분에만 현 판정 유지. 법리 범위 판단이라 사용자 결정.
- **D4(지각 구조 L1, 0.18.0 전)**: (가) 0.18.0에서 L1(앞 문장 체재 + 다음 문장 직접 지각)을 끄고 설계 메모로 재도입(권고 — 확인 탐침에서 세 안 모두 오탐 다수), (나) 평가 측 L7(장소 근거) 적용 — 확인 탐침 오탐 6/12 잔존, (다) 그대로 배포.
- **D5(LV-06 조치 안내의 전제)**: 석명촉구·사본 제출 요구서 안이 '상대방 서면'을 전제로 쓰였다. 자기 서면 점검(실무에서 더 흔함)에는 '인용 정정'이 맞는 조치다. 서면 역할(자기·상대방) 입력을 둘지 결정 필요(설계 범위).
- D6(기록): Q7 병합으로 Q5 2칸 재현율 후퇴 — 다음 산식 TK에서 회복 지시.

### 2-33-4. 구현 지시(전달문)
- 증분: [patches/LV_01-06_fix_on_d8af690.diff](patches/LV_01-06_fix_on_d8af690.diff)(제품 5파일), 평가 측 공개 시험 [patches/test_lv_eval_fix.py](patches/test_lv_eval_fix.py)(11건 — `d8af690`에서 10건 실패·대조 1건 통과, 사본 11건 통과).

```
[평가 측 판정·보완 지시 — LV-01~06 (#252~#257), head d8af690, 기준 Steve 3d54f77 → 현재 Steve 649a162, 11-11]

판정: 보완 1회. 아래 F1~F9를 고치면 수용한다(X6은 사용자 승인 뒤 평가 측이 시험을 고친다 — 구현 측은 그 시험을 고치지 않는다).
- 줄 번호는 d8af690 기준. 항목별로 해당 PR 브랜치에 커밋하고, 지금까지처럼 앞 브랜치를 다음 브랜치에 병합해 전파한다.
  F1~F3 → #252(lv01), F4 → #253(lv02), F5~F7 → #255(lv04), F8 → #256(lv05), F9 → #257(lv06).
- 평가 측 사본 dd951fb(= d8af690 + 아래 전부)로 사전 검증했다. 증분 docs/handoff/patches/LV_01-06_fix_on_d8af690.diff(제품 5파일 +84/−19)를
  그대로 적용해도 된다. 다르게 쓰면 아래 시험·점검을 같은 방식으로 보이고 PR 본문 '축별 자체 점검' 표(NEXT 2-28)에 적는다.
- Steve 최신(649a162, #247~#251 병합)과 병합 충돌 없음(평가 측 확인). 브랜치를 Steve 최신에 맞춰 병합해도 된다.

[#252 LV-01] packages/legal_engine/legal_rules.py
F1 [오탐·보류 오류] '처분이 있은 날'과 '처분이 있음을 안 날'을 같은 역할로 묶는다 — 135행
- 원인: 처분일 정규식에 '처분을 안 날'이 들어 있어, 두 날짜를 모두 적은 서면이 '원처분일 상충'으로 계산 보류된다.
  설계 메모 3.4도 DISPOSITION(있은 날)과 NOTICE_RECEIVED(안 날)를 나눈다. 행정소송법 제20조 제1항(안 날부터 90일)·제2항(있은 날부터 1년)의 기산점이 다르다.
- 고칠 것: 135행 정규식에서 '처분을\s*안\s*날'을 뺀다. 통지일 블록 뒤에 aware_dates를 따로 모은다:
  r"처분(?:이\s*있음|\s*등이\s*있음)?을\s*안\s*날\s*[:：]?\s*" + DATE_RE.pattern. 상충 검사에 len(aware_dates) > 1('처분을 안 날 상충')을 더하고,
  보류 문안의 '확인된 날짜 후보'와 계산 결과에 '처분을 안 날(Y. M. D.) 기준: N일 경과'를 원처분일 다음에 넣는다.
F2 [표시 오류] 재결서 정본 송달일을 '이의신청 통보일'로 표시 — 212행 notif_label
- 고칠 것: notif_label = "재결서 송달일"(본문에 '재결서'가 있으면) → "이의신청 통보일"('이의') → "통지일" 순.
F3 [미탐·보류 과다] 서술형 소제기('… 이 사건 소를 제기하였습니다')를 못 읽는다 — 178행
- 고칠 것: '본\s*소를?' 갈래를 '(?:본|이\s*사건)\s*소를?'로 넓힌다(서법·부정 제외 검사는 그대로).
- 106행 DRAFTING_LINE_RE는 쓰는 곳이 없다. 지우거나 쓰는 곳을 만든다(메모 3.4와 맞출 것: 작성일은 소제기일로 쓰지 않는다).

[#253 LV-02] packages/legal_engine/citation_extractor.py
F4 [계약 위반·인위적 득점] citation.context를 m.end()+1000으로 넓혔다 — 608·630·657·683행
- 재현: 보호 시험 tests/test_tk72_citation_output_compatibility.py 16건 실패(인용 추출 출력 계약). 넓어진 context는 AI 의미 검토의
  claim(pipeline.py 1475행 citation.context[:2000])과 근거 꾸러미 입력(1469행), 별개의견 판정(verifier.py 1071행), 결과 발췌(verifier.py 1231행)에
  그대로 들어가 다른 인용의 문장이 섞인다. 은퇴 세트 2개 점수 상승(56.9→57.3, 34.1→36.4)은 이 넓은 발췌가 정답 항목 낱말과 우연히 겹친 인위적 득점이다(평가 측 귀속 확인).
- 고칠 것: 네 줄을 원래 범위(+200, 630행은 +120)로 되돌린다. 넓은 평가 문맥은 _extract_linked_claim(doc 읽기 텍스트 + reading_span/span)으로만 만든다
  (설계 메모 3.2 '평가 문맥과 원형 표기 분리'). LV-02 시험은 되돌린 뒤에도 전부 통과한다(평가 측 확인).
- 메모 3.2의 masked_evaluation_context·char_map은 구현되지 않았다. 구현하지 않을 거면 메모에서 '후속'으로 옮긴다.

[#255 LV-04] packages/legal_engine/quote_diff.py
F5 [오탐] 창 끝 어절의 추가·삭제를 의미 변경으로 기록 — 104~118행
- 원인: 117행 'is_boundary and not kinds → 건너뜀'으로 바꾸면서, 창 정렬이 원문 끝 어절을 빼먹은 자리(창이 '원고가'를 뺐는데 인용은 '원고는')의
  'insert' 하나가 그대로 _classify에 들어가 PARTY_SWAP(주어·객체 바뀜)이 된다. 반대로 끝 어절의 부정 반전('없다'→'있다')은 창이 '없다'를 빼먹어
  insert '있다'만 남고 분류가 비어 버려진다(미탐).
- 고칠 것: 104행 segment 바로 뒤에 창 앞뒤의 원문 어절 prev_word·next_word를 구한다(norm_off에서 segment 위치 기준).
  op 루프에서 is_boundary이고 op가 delete면 건너뛴다(인용 범위 절단). insert면 상대 어절(구간 처음이면 before 또는 prev_word, 끝이면 after 또는 next_word)과
  맞대어 replace로 바꾼 뒤 분류한다(상대가 없거나 같으면 건너뜀).
F6 [오탐] 부정 활용형 차이를 부정어 변경으로 분류 — 23행
- 원인: NEGATION 정규식이 활용형('없다'·'없는')을 따로 잡아 '볼 수 없다'→'볼 수 없는 것이다'를 부정어 변경으로 본다.
- 고칠 것: 어절 대조용 NEGATION은 어간만(r"아니|않|못|없|불가|금지|배제"). 어절 대조가 성립하지 않는 낮은 유사도(0.85 미만)의 창 전체 비교에서만
  지금의 활용형 정규식을 쓴다(_classify(…, surface=True)). 구현 측 시험 test_lv_round4_contract_eval.py::test_quote_actual_verifier_…(3건)은 이 경로로 통과한다.
F7 [오탐] 생략 인용·무변경 인용을 창 전체 재분류로 '변경'으로 만든다 — 238~265행
- 원인: quote_changes가 None(구간마다 일치)이면 252행이 후보 창 전체와 인용을 _classify한다. 생략 표시('…')로 건너뛴 원문 부분의 낱말이
  '변경'으로 잡혀 MODIFIED_QUOTE가 되고, verifier.py 472행에서 TRUNCATED가 MODIFIED로 바뀐다.
- 고칠 것: (가) 인용에 생략 표시가 있고 ELLIPSIS_RE로 나눈 구간(MIN_SEGMENT 이상)이 모두 _segment_ops에서 (비율, 변경 없음)이면 EXACT_MATCH
  ('생략 표시로 나눈 구간이 모두 공식 원문과 일치')를 돌려준다. (나) 그 밖에 quote_changes가 None이면 max_ratio < 0.85일 때만 창 전체를
  _classify(surface=True)하고, 0.85 이상이면 MINOR_WORDING으로 둔다.
- MIN_SIMILARITY를 0.85→0.75로 낮춘 근거(어떤 꼴이 0.75~0.85에 드는지)를 PR 본문에 적는다. 평가 측은 이번에 바꾸지 않았다.

[#256 LV-05] packages/legal_engine/opinion_attribution.py
F8 [미탐·오탐·시간] 판시 왜곡 결정 규칙 2개
- (a) 미탐: CHANGED_PRECEDENT_RE의 old_cases(292행) [^.。\n]가 실제 판결 표기 '대법원 1999. 3. 9. 선고 98다… 판결'의 날짜 마침표에서 끊겨 한 번도 맞지 않는다.
  → old_cases를 (?:[^.。\n]|\.(?=\s*\d|\s*선고)){4,200}? 로.
- (b) 오탐: 변경한 판결의 새 법리를 정확히 인용해도(극성이 같은 기산점 변경 꼴) 옛 판시와 겹침 0.45 이상이면 CHANGED_PRECEDENT가 된다(343행).
  → 결합 텍스트에서 변경 문장을 뺀 나머지 문장(새 판시)과의 최대 겹침 sim_new를 구하고, sim > sim_new일 때만 판정한다. 새 판시의 'A가 아니라 B' 꼴은
  주제 조사 뒤 'A가 아니라' 부분을 빼고 견준다(re.sub(r"(?<=[는은])\s+[^,.]{1,40}?(?:이|가)\s*아니라\s*", " ", x)).
- (c) 미탐: 원심 오인(410행)이 부정 명제의 원심 판단('…구속하지 않는다고 판단')을 놓친다. 주장 끝 괄호 인용 '(대법원 … 판결)'이 남아
  _claim_core가 전달 표현을 떼지 못하고, 극성 비교가 '판단하였다'를 본다.
  → _reported_core(claim) = _claim_core(끝 괄호 인용 표시를 뗀 claim)을 두고 두 규칙의 core에 쓴다(괄호 정규식: \s*\([^()]{0,120}(?:판결|결정|선고|참조)[^()]{0,40}\)\s*[.。]?\s*$).
  공용 _claim_core는 바꾸지 않는다(다른 경로 영향).
- (d) 시간: REVERSED_LOWER_COURT_RE(298행)의 '.*?'가 줄 끝까지 되훑어 한 줄 긴 전문에서 이차 시간(평가 측: 7만 자 9.5초). → [^\n]{0,400}? 로(사본 0.34초).

[#257 LV-06] packages/legal_engine/actionable_guidance.py
F9 [법리 오류] 채무불이행 손해배상(민법 제390조)의 요건사실에 '귀책사유'를 넣었다 — 49행
- 근거: 민법 제390조 단서('채무자의 고의나 과실없이 이행할 수 없게 된 때에는 그러하지 아니하다') — 귀책사유 없음은 채무자가 주장·증명하는 항변이다.
  원고 서면에 귀책사유 주장이 없다고 '요건사실 누락'으로 알리면 틀린 조언이다.
- 고칠 것: 49행 요소를 지우고 그 자리에 근거 주석을 둔다. 같은 파일 253행 '판결 취지가 왜곡되었습니다'는 결정 규칙의 추정이므로
  '왜곡되었을 가능성이 있습니다(규칙 판정, 원문 확인 필요)'로 바꾼다.
- 조치 안내가 '상대방 서면'을 전제로 한 점(석명촉구·사본 제출 요구서 안)은 사용자 결정(D5) 뒤 지시한다. 이번 PR에서는 바꾸지 않는다.

[#254 LV-03] 제품 변경 없음. 근거 시험 1건 실패는 X6(사용자 승인 대기, 평가 측이 고침).

평가 측 사전 검증(사본 dd951fb, 평가 측 재실행)
- 공개 시험 tests/test_lv_eval_fix.py(평가 측 작성, docs/handoff/patches/test_lv_eval_fix.py) 11건: d8af690에서 10건 실패(E8은 대조 — 양쪽 통과), 사본 11건 통과.
  이 파일을 #257 브랜치 tests/에 그대로 넣는다.
- LV 시험·구현 측 계약 시험·출력 계약·근거 시험 17개 파일 514건: d8af690 실패 17 → 사본 실패 1(X6 해당 근거 시험만).
- 평가 측 축 탐침(비공개): 날짜 역할 8칸 기대대로, 인용문 차이 12칸(조사·활용·생략·부정 반전·주어·수치·단서) 기대대로, 판시 왜곡 8칸(옛 법리 인용·새 법리 인용·
  변경 사실 기술·원심 오인 긍정/부정·경과 기술) 기대대로. 원심 오인 7만 자 9.5초 → 0.34초.
- Steve 649a162 + 사본 합본: 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0(F4로 인위적 득점 제거 — 기준과 같음), 고정 82.6/81.9/0 변화 0.
  전체 시험 11,427건 중 실패 1(X6 근거 시험만). (수정 전 d8af690 합본은 실패 17(출력 계약 16 + X6)).
- 하드코딩 변경분·시험 약화·보호 경로 점검 통과, 평가 세트 문구 '의심 없음'.

수용 기준
- CI 전부 성공(X6 시험 수정 전에는 근거 시험 1건 실패만 허용 — 평가 측이 X6 승인 뒤 같은 PR 묶음 병합 전에 고친다).
- 평가 측 공개 시험 11건 통과, 출력 계약 시험 16건 통과(F4), 평가 측 축 탐침 재실행 결과 위와 같음.
- 은퇴·고정 세트 기준 대비 하락 0. 은퇴 점수 상승이 있으면 평가 측 귀속 확인 전에는 득점으로 적지 않는다.
- PR 본문 축별 자체 점검 표: F1(역할 3값: 있은 날·안 날·통지/송달), F5~F7(창 처음·끝 × 추가·삭제·치환, 생략 유무), F8(날짜 표기 유무 × 새/옛 법리, 원심 판단 긍정/부정 × 괄호 인용 유무).
```

### 2-33-5. 사용자 결정 반영 (11-11)
- **X6 승인**(사용자 11-11 'X6 승인'): `tests/test_ground_truth_prepared_brief.py::test_precedent_and_regulation_existence` 단언 3줄 변경 — CRITICAL·FAKE_PRECEDENT → MEDIUM·SOURCE_LIMIT(FAKE_PRECEDENT 없음)·levels.authority_status UNCONFIRMED_SOURCE_LIMIT. 시험 이름 유지, 삭제 없음. 평가 측 증분 [patches/X6_ground_truth_assertion_on_ea2ef8a.diff](patches/X6_ground_truth_assertion_on_ea2ef8a.diff): #254 head `ea2ef8a`·#257 head `d8af690`·평가 측 사본 `dd951fb`에 적용 가능, 적용 뒤 그 시험 통과(평가 측 재실행). 구현 측이 #254 브랜치에 그대로 넣고 연쇄로 전파한다(X5와 같은 방식).
- **D4: L1 비활성화**(사용자 11-11 '권고대로 L1 비활성화') → **TK-151**. 아래 2-34 지시.
- D3(TK-150)는 11-11 '제안대로 진행' → 2-33-6 F10. D5는 '보류'.

## 2-34. TK-151 지각 구조 L1 기본 비활성화 구현 지시 (11-11, 사용자 결정 D4)
- 평가 측 사본 `97d241b`(기준 Steve `649a162`) 사전 검증. 증분 [patches/TK-151_l1_off_on_649a162.diff](patches/TK-151_l1_off_on_649a162.diff).

```
[평가 측 구현 지시 — TK-151 지각 구조 L1 기본 비활성화, 기준 Steve 649a162, 11-11]

목적: 사용자 결정 D4(11-11 '권고대로 L1 비활성화'). 0.18.0 배포 전에 EVI.BEYOND_PERCEPTION_STRUCTURE의 L1(앞 문장 다른 장소 체재 + 다음 문장 직접 지각,
문장 안 연결어미 꼴 포함)을 기본으로 끈다. 규칙 코드는 지우지 않고 재설계 때 다시 켠다. 한 PR, 제품 1파일 packages/claim_engine/evidence_consistency.py + 시험 2파일.
설계 메모 불요(평가 측 사본으로 사전 검증 완료).

원인(평가 측 재실행): L1은 목격자가 자기 위치를 밝힌 통상 진술('당시 저는 [장소]에 있었습니다. 그때 … 직접 보았습니다')을 '다른 장소 체재'로 단정한다.
보정에 쓰지 않은 확인 탐침 12차에서 Steve 649a162 대조 오탐 8/12. 평가 측 수정안 둘(사건 장소 근거 요구 6/12, 양보 연결 한정 2/12·양성 3/5)도 수용 수준이 아니다
('에서'가 사건 장소인지 출처·조망 지점인지 규칙으로 못 가림). 재설계는 설계 메모로 따로 다룬다.

고칠 것(줄 번호는 649a162 기준)
1. 18행 import re 앞에 import os.
2. check_reasoning_structure(2977행) 바로 앞에 다음 함수를 두고 주석으로 이유(TK-151, 사용자 결정 D4)를 적는다:
   def _l1_enabled() -> bool: return os.environ.get("LV_ENABLE_PERCEPTION_STRUCTURE_L1", "0") == "1"
   - 호출 때마다 읽는다(모듈 상수로 고정하지 않는다 — 시험이 monkeypatch로 켠다).
3. 함수 첫머리에서 l1_on = _l1_enabled()를 한 번 구하고,
   - 2990행 'if prev and not _L1_OTHER_TIME_RE.search(sent):' → 'if l1_on and prev and not …'
   - 2995행 'm_in = _L1_INLINE_RE.search(sent)' → 'm_in = _L1_INLINE_RE.search(sent) if l1_on else None'
   이렇게 하면 pair가 None으로 남아 L1 결과가 나오지 않고, 같은 루프의 L2·L3는 그대로 돈다.
4. 바꾸지 말 것: perception_conflict(같은 문장 안 규칙, 0.17.0 배포분 — ELSEWHERE_SAME_TIME 포함), L1 보조 정규식·함수(_L1_*, _l1_elsewhere_stay),
   L2·L3. 파이프라인·설정·화면은 건드리지 않는다.

시험
- tests/test_tk76_logic_eval.py: TestL1PreviousSentenceElsewhere에 setUp으로 mock.patch.dict(os.environ, {"LV_ENABLE_PERCEPTION_STRUCTURE_L1": "1"})를 걸어
  기존 단언을 그대로 둔다(약화 없음). 새 클래스 TestL1DisabledByDefault 1건 — 스위치 없이 L1 양성 2꼴(앞 문장 체재·문장 안 '-는데')이 결과를 내지 않음.
- tests/test_tk76_b_bundle_eval.py: pytest fixture l1_on(monkeypatch.setenv(…, "1"))을 두고 이름이 test_l로 시작하는 L 계열 시험 8개에만 인자로 준다
  (O 계열 시험은 그대로).
- 증분 docs/handoff/patches/TK-151_l1_off_on_649a162.diff를 그대로 적용해도 된다.

평가 측 사전 검증(사본 97d241b, 평가 측 재실행)
- 관련 시험 3파일(logic·B 묶음·perception_structure) 74건 통과. 시험 약화 점검 '삭제·표시 변경 없음', 하드코딩·보호 경로 통과.
- 확인 탐침 11차 Steve 양성 4/4·대조 오탐 2/7 → 사본 1/4·0/7, 12차 Steve 5/5·8/12 → 1/5·0/12(남은 양성은 같은 문장 안 규칙 — 의도대로).
- 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 82.6/81.9/0 — 변화 0(L1은 세트 득점에 기여 없음).
- 전체 시험 11,231건 통과(실패 0, 건너뜀 35).

제출물·수용 기준
- 귀속표 '세트 득점 0'. PR 본문에 사용자 결정 원문('D4는 권고대로 L1 비활성화')과 대응을 적는다.
- 수용: CI 전부 성공, 위 시험 통과, 평가 측 확인 탐침 재실행 결과 위와 같음.
- LV 연쇄(#252~#257)와 같은 파일을 건드리지 않으므로 병합 순서는 상관없다(평가 측 확인: LV는 legal_engine만 바꾼다).
```

### 2-33-6. D3 결정 반영 — F10(TK-150)을 #252 보완에 추가 (11-11, 사용자 'D3는 제안대로 진행, D5는 보류')
- D5(조치 안내의 서면 역할)는 보류 — LV-06 문안은 이번 회차에 바꾸지 않는다(F9만).
- TK-150은 같은 파일·같은 함수 영역(legal_rules.py)이라 별도 PR 대신 #252 보완 F10으로 넣는다. 평가 측 사본 `7ddc7a9`(= `dd951fb` + X6 + F10).
- 증분 [patches/LV_01-06_fix_on_d8af690.diff](patches/LV_01-06_fix_on_d8af690.diff)를 F10까지 포함해 갱신(제품 5파일 +136/−22), 공개 시험 [patches/test_lv_eval_fix.py](patches/test_lv_eval_fix.py) 14건으로 갱신.

```
[평가 측 보완 지시 추가 — F10(TK-150) → #252(LV-01), 사용자 결정 D3, 11-11]

F10 [법리 오류·A등급 오탐] ADMIN.DEADLINE_CALCULATION_SCENARIOS가 이의신청 결과 통지일 기산 주장을 일률로 CONTRADICTED·A로 판정한다
- 위치: packages/legal_engine/legal_rules.py _finding(d8af690 243행), 규칙 정의 config/legal_rules/rules.json(설정은 바꾸지 않는다).
- 근거: 행정기본법 제36조 제4항 — 이의신청 결과를 통지받은 날(통지기간 내 통지가 없으면 그 기간 만료일 다음 날)부터 90일 이내 행정심판·행정소송 제기 가능.
  부칙 제6조 — 제36조는 부칙 제1조 단서 시행일(2023. 3. 24.) 이후에 하는 처분부터 적용. 같은 조 제8항 — 공무원 징계, 국가인권위원회 진정 결정, 노동위원회 의결,
  형사·행형·보안처분, 외국인 출입국·난민인정·귀화·국적회복, 과태료에는 적용하지 않는다. 규칙 설명의 대법원 2014. 4. 24. 선고 2013두10809 판결은 그 이전 법리다.
  재현(평가 측): Steve 649a162·d8af690 모두 2024년 처분 서면에서 A등급 CONTRADICTED.
- 고칠 것:
  1. typing import에 Optional, Tuple을 더한다.
  2. _finding 바로 앞에 ADMIN_ACT_36_START = (2023, 3, 24), ADMIN_ACT_36_EXCLUDED_RE = r"징계|국가인권위원회|노동위원회|형사|행형|보안처분|출입국|난민|귀화|국적\s*회복|과태료"
     (제8항 각 호), 함수 _admin_objection_premise(doc, claim) -> (전제, 처분일)를 둔다:
     scope_text = claim + "\n" + doc.full_text. 제8항 낱말이 있으면 ("EXCLUDED", None).
     처분일은 F1 뒤의 처분일 정규식(처분일·원처분일·처분이 있은 날 + DATE_RE, 없으면 DATE_RE + 0~25자 + 처분·결정 + 받·하·내렸·고지·있은)으로 모은다.
     서로 다른 날짜가 정확히 하나가 아니면 ("UNKNOWN", None), 하나면 2023. 3. 24. 전 "PRE_2023", 그 날 이후(당일 포함) "POST_2023".
  3. _finding에서 verdict = rule["verdict"], status_value = rule.get("status", "SUSPICIOUS")를 지역 변수로 두고, 이 규칙이면 전제를 구해
     features["admin_basic_act_36"]에 적는다. POST_2023·UNKNOWN이면 grade "C", status SUSPICIOUS, verdict
     "이의신청 통지일 기준 제소기간 기산 주장 — 처분일·적용 법령 확인 필요", features의 verdict·confidence도 같이 바꾸고 설명을 바꾼다:
     · POST_2023: 처분일(Y. M. D.)이 2023. 3. 24. 이후 → 행정기본법 제36조 제4항(부칙 제6조)에 따라 통지받은 날부터 90일 가능. 같은 조 제1항 이의신청(처분을 받은 날부터 30일)인지,
       제8항 적용 제외·개별 법률 특례인지 확인 필요.
     · UNKNOWN: 처분일을 문서에서 특정하지 못했다 → 2023. 3. 24. 이후면 통지일부터 90일 가능, 그 이전이면 '다음 설명이 적용된다' + 규칙의 기존 설명(rule["explanation"])을 잇는다.
       판례 번호를 파이썬 코드에 직접 쓰지 않는다(tests/acceptance/test_no_case_literals.py — 평가 측 첫 시안이 이 시험에 걸려 고쳤다).
     PRE_2023·EXCLUDED는 지금 판정(CONTRADICTED·A, 기존 설명) 그대로. 동적 일수 계산(_calculate_dynamic_deadline) 덧붙임은 네 경우 모두 그대로.
  4. Finding.create의 status·title은 지역 변수(status_value·verdict)를 쓴다. 다른 규칙의 결과는 바뀌지 않는다.
- 바꾸지 말 것: rules.json(다른 경로가 같은 규칙 정의를 읽는다), 다른 규칙의 _finding 경로.

평가 측 사전 검증(사본 7ddc7a9, 평가 측 재실행)
- 처분일 축 탐침 6칸(2024 처분·2022 처분·처분일 불명·적용 제외(과태료) 2024·경계 2023. 3. 24.·경계 2023. 3. 23.): Steve·d8af690 전부 CONTRADICTED·A →
  사본 SUSPICIOUS·C / CONTRADICTED·A / SUSPICIOUS·C / CONTRADICTED·A / SUSPICIOUS·C / CONTRADICTED·A(설계대로).
- 공개 시험 tests/test_lv_eval_fix.py 14건(E12~E14 추가): d8af690에서 12건 실패(E8·E13은 대조 — 양쪽 통과), 사본 14건 통과.
- 이 규칙을 쓰는 기존 시험(test_efficacy_round2·test_efficacy_improvements)과 LV 시험·근거 시험 156건 통과.
- 하드코딩·보호 경로 통과. 평가 세트 문구 의심 2건('행정기본법 제', '통지받은 날부터')은 설명 문안의 법령명·조문 문구다(판정 규칙 아님).
- Steve 649a162 + 사본(첫 시안 4444669) 합본: 전체 11,427건 중 실패 1(사건 고유값 시험 — 설명에 판례 번호를 코드로 넣음) → 설명을 규칙 설정으로 돌린 7ddc7a9에서 그 시험 포함 관련 105건 통과
  (설명 문자열 한 곳만 바뀌어 전체는 다시 돌리지 않음). 은퇴 5세트·고정 82.6/81.9/0 변화 0. X6 적용으로 근거 시험 통과.
```

### 2-33-7. LV 보완본 2차 판정·TK-151(#258) 판정 (11-11, 평가 측 재실행)
- 구현 측 보완 push(18:46~18:56 UTC): #252 `7b799f5`·#253 `862d9d6`·#254 `07af746`·#255 `3d02741`·#256 `606f114`·#257 `b128126`, #258 TK-151 `cfaebc4`. 각 브랜치에 Steve `649a162` 병합.
- LV 범위 제품 코드 = 평가 측 사본 `7ddc7a9`(diff 0), X6·공개 시험 파일 동일. TK-151 = 사본 `97d241b`(diff 0).
- 확인 탐침(보정 미사용)에서 LV-04 원래 결함 F11(당사자 맞바꿈 미탐) 발견 → #255 보완 1회. 증분 [patches/LV_F11_party_swap_on_b128126.diff](patches/LV_F11_party_swap_on_b128126.diff), 공개 시험 15건.
- CI(인용): 조회 시점 두 PR 모두 실행 중(#257 은퇴 세트 비교 성공).

```
[평가 측 판정 — LV-01~06 보완본(#252~#257, 끝 head b128126) 2차 + TK-151(#258, head cfaebc4), 11-11]

판정
- #252~#257: F1~F10·X6은 평가 측 사본과 같다(legal_engine 등 LV 범위 diff 0, 공개 시험·X6 시험 파일 동일, 브랜치에 Steve 649a162 병합 확인).
  다만 보정에 쓰지 않은 확인 탐침(AGENT_ROLES 2.1 (8)②)에서 LV-04 원래 결함 1건(F11)이 새로 드러났다 → #255 보완 1회(작음). F11 반영 뒤 연쇄 전체 수용 방향.
- #258 TK-151: 평가 측 사본 97d241b와 diff 0 → 수용(조건: CI 전부 성공). LV와 파일이 겹치지 않아 병합 순서 무관.

F11 [미탐] 인용문에서 두 당사자를 맞바꾸면(예: '채권자는 채무자에게'→'채무자는 채권자에게') PARTY_SWAP이 아니라 MINOR_WORDING이 된다
- 위치: packages/legal_engine/quote_diff.py(b128126 기준) 25행 PARTY_SWAP 정규식, 94~98행 _classify.
- 원인(재현): _classify가 각 유형의 일치를 집합(set)으로 견준다. 맞바꿈은 두 쪽 집합이 {채권자, 채무자}로 같아 변경이 없다고 본다. 이 결함은 LV-04 첫 구현부터 있었고
  평가 측 1차 점검표(원고→피고 한쪽 치환만 넣음)의 빈칸이었다(점검표 빈칸 → 축 전체를 한 번에 고침, AGENT_ROLES 2.1 (2)). 또 역할 명사 어휘가 좁다(도급인·수급인 등 없음).
- 고칠 것:
  1. PARTY_SWAP 정규식을 긴 낱말 먼저 두는 목록으로 넓힌다:
     주채무자|피상속인|피신청인|피청구인|피고인|원고|피고|처분청|행정청|당사자|채권자|채무자|신청인|청구인|상속인|매도인|매수인|임대인|임차인|도급인|수급인|위임인|수임인|
     사용자|근로자|보증인|양도인|양수인|증여자|수증자|임치인|수치인|가해자|피해자|소유자|점유자
     ('대주·차주'는 '대주주' 같은 낱말 안에서 잘려 맞으므로 넣지 않는다.)
  2. _classify에서 PARTY_SWAP만 집합이 아니라 나온 순서(리스트)로 견준다(_ORDERED_KINDS = {"PARTY_SWAP"}). 다른 유형은 지금처럼 집합 비교.
     NEGATION의 surface 인자 처리(F6)는 그대로.
- 바꾸지 말 것: categorize_quote_diff의 흐름(F5~F7), MIN_SIMILARITY, 다른 유형 정규식.
- 증분: docs/handoff/patches/LV_F11_party_swap_on_b128126.diff(제품 1파일 + 공개 시험 E15). #255 브랜치에 커밋하고 지금처럼 #256·#257로 병합 전파한다.

평가 측 재실행
- 보완 head b128126: LV·계약·출력 계약·근거·사건 고유값 시험 21파일 583건 통과. 1차 축 탐침(날짜 역할 8·처분일 6·인용문 12·판시 왜곡 8칸) 사본과 같음. 원심 오인 7만 자 0.44초.
- 확인 탐침(새로 지음, 보정 미사용) 12칸: d8af690 6/12 → b128126 11/12(당사자 맞바꿈 1칸 미탐) → F11 사본 9e9924a 12/12.
- 당사자 축 점검표 9칸(맞바꿈 문장 처음·중간, 한쪽 치환, 다른 역할 명사 치환, 조사만 다름, 같은 순서 다른 낱말, 생략 인용, 정확 인용, 피고인↔피고): b128126 6/9 → 사본 9/9.
- 공개 시험 15건(E15 추가): b128126에서 E15만 실패, 사본 15건 통과. 인용 대조를 쓰는 시험 39파일 1,048건 통과(사본).
- 하드코딩·시험 약화·보호 경로 통과, 평가 세트 문구 '의심 없음'.
- 사본 9e9924a(= b128126 + F11, Steve 649a162 포함) 전체 11,442건 통과(실패 0, 건너뜀 35). 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 82.6/81.9/0 — 변화 0.

수용 기준
- F11 반영(증분 그대로 또는 같은 구조) + 공개 시험 15건 통과 + CI 전부 성공 → #252~#257 연쇄 수용. 병합 순서는 #252 → #257 차례 또는 #257 하나(앞 PR 전부 포함).
```

### 2-33-8. LV 보완본 2차 보충 — CI 실패 2종 원인(F12 실제 결함, 문구 의심 허용 등록) (11-11, 평가 측 재실행)
- PostgreSQL 벌 API 시험 2건 실패를 로컬 PostgreSQL 16 + pgvector로 재현: Finding 객체가 결과 데이터 JSON에 들어감(LV-05 4327e02) → F12. **1차 판정에서 '일시 실패'로 본 것은 평가 측 오판**.
- 점수 하락 게이트 실패는 평가 세트 문구 의심 11건(설명·안내 문안) → 평가 측 허용 등록 커밋 `22d3fd7`(구현 측이 #252에 체리픽).
- 증분 [patches/LV_F11_F12_on_b128126.diff](patches/LV_F11_F12_on_b128126.diff)(F11 단독 증분은 대체), 공개 시험 16건.

```
[평가 측 판정 보충 — LV 보완본 2차(#252~#257, 끝 head b128126): CI 실패 2종 원인 확인, F12 추가 + 허용 문구 등록, 11-11]

앞 코멘트(#255, F11)에 더해 아래를 함께 반영한다. 증분은 F11·F12를 합친 docs/handoff/patches/LV_F11_F12_on_b128126.diff로 교체했다(제품 2파일 + 공개 시험 16건).

1) CI '테스트 (PostgreSQL/pgvector + Celery 브로커)' 실패 2건 — 실제 결함(F12, #256 LV-05에서 들어옴, 커밋 4327e02)
- 증상(CI 결과 인용): tests/test_api.py::test_vertical_slice_end_to_end(실행 상태 FAILED), ::test_run_listings_and_status_polls_never_read_the_stored_result(KeyError 'documents').
  1차 판정 때 'CI 일시 실패'로 본 것은 평가 측 오판이었다 — SQLite에서는 통과하고 PostgreSQL에서만 난다.
- 재현(평가 측, 로컬 PostgreSQL 16 + pgvector): Steve 649a162 통과, b128126 실패. verification_runs.errors = "Object of type Finding is not JSON serializable"(3회 재시도 모두).
- 원인: packages/legal_engine/verifier.py 229행 result.data["verdicts"][*]["findings"] = list(v.findings) — Finding 객체가 결과 데이터(JSON 칸)에 그대로 들어간다.
  PostgreSQL JSON 칸은 객체를 직렬화하지 못해 실행 전체가 실패한다.
- 고칠 것(#256 브랜치): 그 줄을
  [{"finding_id": f.finding_id, "type": str(f.type), "tags": list(f.tags or []), "confidence_features": dict(f.confidence_features or {})} for f in v.findings]
  로 바꾼다. 읽는 쪽(argument_validity_verifier.py 452행 v_findings)은 이미 dict를 처리한다(type·tags·confidence_features). 다른 소비처 없음(평가 측 grep).
- 공개 시험 E16(tests/test_lv_eval_fix.py): 결과 데이터 json.dumps 통과·findings가 dict인지. b128126에서 실패, 사본 통과.

2) CI '점수 하락 게이트' 실패 — 결함 아님(평가 세트 문구 의심 11건, 실패 시험 0건)
- check_train_phrase_overlap.py --eval-sets가 결과 설명·안내 문안·주석의 일반 표현 11건을 '의심'으로 표시해 종료 코드 1. 평가 측이 위치를 하나씩 확인했다 — 모두 탐지 조건(정규식·판정 분기)이 아니다.
- 평가 측 허용 등록 커밋: 평가 브랜치 evaluator/round8-promotion 22d3fd7(docs/scorecards/approved_eval_phrases.json만, 평가 측 저자).
  #252 브랜치에 git cherry-pick 22d3fd7 하고 연쇄로 전파한다(평가 측 커밋은 그대로 옮기고 고치지 않는다). 평가 측 확인: 체리픽 뒤 '평가 세트 문구 의심 없음'.

평가 측 재실행(사본 2fded7c = b128126 + F11 + F12)
- 공개 시험 16건 통과(b128126에서 E15·E16 실패). PostgreSQL로 tests/test_api.py 31건 통과(b128126은 2건 실패).
- SQLite 전체: F11 사본 9e9924a 11,442건 통과(F12는 그 위 한 줄 변경). PostgreSQL 16 + pgvector 전체: 사본 2fded7c 11,443건 통과(실패 0, 건너뜀 32).
- 은퇴 5세트·고정 82.6/81.9/0 변화 0(9e9924a 기준).

수용 기준
- F11(#255)·F12(#256)·허용 문구 체리픽(#252) 반영 후 연쇄 전파, 공개 시험 16건 통과, CI 전부 성공(두 시험 벌·점수 하락 게이트 포함) → #252~#257 연쇄 수용.
- 평가 측 교훈(기록): CI의 PostgreSQL 벌에서만 나는 실패는 일시 실패로 넘기지 않고 로컬 PostgreSQL로 재현한다(AGENT_ROLES 2.1 (10)).
```
- 11-11 #258(TK-151) 사용자 병합 → Steve `c89e191`. LV 보완 커밋은 새 Steve 기준으로 병합해도 충돌 없음(평가 측 확인).

### 2-33-9. LV 보완본 3차 판정 — 수용(조건: CI 남은 시험 벌 성공) (11-11, 평가 측 재실행)
- 구현 측 push(21:07~21:11 UTC): #252 `1ad54a4`(평가 측 허용 등록 22d3fd7 체리픽, 평가 측 저자 유지)·#253 `a60d659`·#254 `ad87376`·#255 `3ca0c86`(F11)·#256 `bee1201`(F12)·#257 `105ce3f`(공개 시험 16건).
- LV 범위 제품 코드 = 평가 측 사본 `2fded7c`(diff 0), 공개 시험·X6 시험·허용 목록 동일. 브랜치 기준은 Steve `649a162`(#258 이전) — Steve 최신 `c89e191`과 충돌 없음.
- 평가 측 재실행(Steve `c89e191` + `105ce3f` 합본 `c000753`): 공개 시험 16건·L1 시험 등 58건 통과, 확인 탐침 12/12, 당사자 축 9/9, 평가 세트 문구 의심 없음, PostgreSQL 16 + pgvector로 tests/test_api.py 31건 통과. 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0, 고정 82.6/81.9/0 — 변화 0. SQLite 전체 11,444건 중 실패 1(`test_tk76_incons_c_eval.py::test_linear_time_on_20k_chars` 0.83초 > 0.5초) — 단독 재실행 합본·Steve 각 3회 모두 통과(0.04초), LV가 바꾸지 않은 모듈(internal_inconsistency.py diff 0) → 평가 측 환경 부하로 판단.
- CI(인용): 점수 하락 게이트 두 벌·은퇴 세트 비교·CodeQL 성공, SQLite 한 벌 성공. PostgreSQL 두 벌·SQLite 한 벌은 조회 시점 실행 중.
- 판정: **#252~#257 수용**(조건: 남은 CI 시험 벌 성공). 병합은 #257 하나(앞 PR 전부 포함) 또는 #252→#257 차례. 병합 뒤 릴리스 후보 SHA에서 평가 측 verify_all 전체 1회.
- 11-12 CI 재확인(인용): #257 head `105ce3f` 시험 두 벌(SQLite·PostgreSQL 각 2회)·점수 하락 게이트·은퇴 세트 비교·CodeQL·OCR 전부 성공 → **#252~#257 수용 조건 충족**. PR이 초안(draft) 상태라 병합 전 '검토 준비'로 바꿔야 한다.
- 11-12 사용자 '#252~257 병합' → 평가 측이 각 head = 판정 SHA 확인, 초안 해제 뒤 #252→#257 차례 병합: Steve `a506de9`·`04c2f3d`·`3284a61`·`680f26a`·`3bc9f16`·`db7e81c`. 최종 Steve 트리 = 평가 측 검증 합본 `c000753` 트리(d7f5bca, 동일).
- 11-12 사용자 결정: '봉인시험 미시행', '대신 0.17에서의 온라인 시험 결과와 0.18에서의 온라인 시험결과를 릴리스 이후에 비교해서 결과를 평가' → 계획 `docs/scorecards/online_compare_0170_0180_plan.md`(기준: case9 23/23 run_652b72461668487a, 신기능 탐침 4종 47항목 online_probe_0170_20261103.md). 판정서에 봉인 시험 갈음으로 적는다.

## 2-35. 0.18.0 버전 커밋 지시 (11-12, 평가 PR #259 Steve 병합 `84000fc` 뒤)
- 평가 측 사본으로 만들어 점검: check_version_policy '위반 없음(상향 1건 0.17.0 → 0.18.0)', 버전 관련 시험 3파일 49건 통과. 증분 [patches/v0.18.0_version_commit_on_84000fc.diff](patches/v0.18.0_version_commit_on_84000fc.diff).
- 11-12 #260 버전 커밋 `d5bca4c` 판정: 평가 측 사본 증분과 diff 0, check_version_policy 위반 없음(0.17.0 → 0.18.0) → 수용(조건: 남은 CI 1건 성공).
- 11-12 #260 CI 재확인(인용): SQLite·PostgreSQL 각 2벌·점수 하락 게이트 두 벌·은퇴 세트 비교·CodeQL·OCR 전부 성공, mergeable clean → 수용 조건 충족(병합 대기).
- 11-12 사용자 '#260병합' → Steve `18659a1`(expectedHeadSha `d5bca4c`, CI 전부 성공). 버전 0.18.0이 Steve에 들어감. 다음: 릴리스 PR(Steve → main).
- 11-12 배포 확인(사용자 제공 /api/health): status ok, version 0.18.0, commit `3c75071c9baba295e713d912d3e4876fdf585955`(= #261 병합 커밋), database ok → 0.18.0 운영 배포 확인. 다음: 0.17.0 대 0.18.0 온라인 비교(사용자 실행 결과 JSON 대기).
- 11-12 사용자 '태그 완료' → 원격 `refs/tags/v.0.18.0` = `3c75071c9baba295e713d912d3e4876fdf585955`(main #261 병합 커밋, 경량 태그 — v.0.13.1과 같은 형식) 확인. 0.18.0 릴리스 주기의 남은 일: 0.17.0 대 0.18.0 온라인 비교.
- 11-12 0.17.0 대 0.18.0 온라인 비교 1차(정답지 대조 전): case9 22/23 — EX-1 회귀(LV-03 X6 정책으로 미발견 대법원 판례 MEDIUM), 나머지 22항목 통과. 탐침: D docx·hwpx·hwp 표 합계·비율 진단 개선(TK-144·146), B 반복 인용 보존(TK-145), A CRITICAL 오단정 감소(잔여 가능), C 0.17.0과 같은 꼴. 기록 `online_compare_0170_0180_20261112.md`. 사용자 결정 필요(EX-1)·정답지 요청.
- 11-12 0.17.0 대 0.18.0 온라인 비교 2차(정답지 대조) 38/47(0.17.0 25/45). 새 결함 TK-152(P1, 두 음절 약칭 추정)·TK-153(P2, 판결 의견 표지 꼴) — 지시문은 사용자 승인 뒤 사본 사전 검증을 거쳐 낸다. case9 EX-1(LV-03 X6 정책) 처리 사용자 결정 대기. 기록 `docs/scorecards/online_compare_0170_0180_20261112.md` 5절.

## 2-36. 0.18.0 온라인 비교 후속 — TK-152·153·154 구현 지시 (11-12, 사용자 'EX-1 처리 결정: 둘다 처리', 'TK-152,153 지시문 작성 승인')
- 구현 주체: Antigravity(다음 릴리스). PR 3개, 서로 독립(같은 파일을 고치지 않음 — 합본 사본에서 충돌 없음 확인).
- 사전 검증(평가 측 재실행): 사본 TK-152 `37d1bce`·`df6fc3c`, TK-153 `ff77e27`, TK-154 `6125e4a`(모두 main `3c75071` 기준), 합본 전체 11,422건 통과·실패 0, 은퇴 4세트·고정 세트 변화 0.
- 사용자 결정 대기 X7: TK-152 (d)(두 음절 어간 후보 0건을 미결 MEDIUM으로 — 보호 시험 단언 1건 변경). 승인 전에는 (a)~(c)만 구현한다.
- case9 명세(EX-1)는 바꾸지 않는다: TK-154가 현 기대(HIGH 이상)를 충족할 것으로 본다. 배포 후 온라인 case9로 확인한다(미검증).
- 증분: [patches/TK-152_abc_on_3c75071.diff](patches/TK-152_abc_on_3c75071.diff)·[patches/TK-152_d_X7_on_37d1bce.diff](patches/TK-152_d_X7_on_37d1bce.diff)·[patches/TK-153_on_3c75071.diff](patches/TK-153_on_3c75071.diff)·[patches/TK-154_on_3c75071.diff](patches/TK-154_on_3c75071.diff)

### 2-36-1. TK-152
```
[TK-152(P1) 두 음절 어간 약칭 추정 — 구현 지시]  기준: main 3c75071(0.18.0)  평가 측 사본: 37d1bce((a)~(c)), df6fc3c((d) 포함)

1. 문제
- 0.18.0 온라인 탐침 A(비공식 약칭 6건)에서 실재 법률 2건이 아직 '법령 목록에서 찾지 못한 법령'(STATUTE_NONEXISTENT·CRITICAL)으로 나온다.
- 1건은 정식명을 확정하지 못했다(MEDIUM). 오단정은 아니지만 정식명을 놓친 것이다.

2. 원인(파일·줄은 3c75071 기준, 운영 결과 JSON에 담긴 실제 목록 응답으로 평가 측 재현)
 C1. packages/legal_engine/law_name_inference.py 100~101행 score(): 공식 약칭 대조는 기본점 800, 정식명 대조는 600이다(정식명은 공식 약칭이 없는 법률일 때만 씀).
     → 글자가 떨어져 맞는 다른 법률의 공식 약칭(둘째 글자가 넷째 말마디)이 794점이다. 첫 두 말마디가 그대로 맞는 정답 법률의 정식명은 596점이다. 차이 198점(MARGIN 100 이상)으로 틀린 후보가 우선 후보가 된다.
 C2. packages/legal_engine/source_review.py 112~119행: 우선 후보 법령에 인용 조문이 없으면 outcome을 ARTICLE_NOT_IN_CANDIDATE로 두고 _law_absent로 돌아간다.
     → 555행 UNDECIDED_INFERENCE에 이 값이 없어 513행 '약칭 꼴 미결(MEDIUM)' 분기를 건너뛰고, 537행 일반 분기 CRITICAL('비슷한 이름의 법령도 없다')이 된다. C1의 틀린 후보가 이 경로로 CRITICAL을 만든다.
 C3. score()에 '어간이 대상 어간 맨 앞에 그대로 이어 나옴'에 대한 가산이 없다.
     → 정답 공식 약칭(어간이 그대로 앞에 이어짐) 798점과 다른 법령 약칭(둘째 글자가 둘째 말마디) 796점이 동점 처리돼 AMBIGUOUS(MEDIUM)가 된다.
 C4. 93행 첫 글자 규칙과 사전식 목록(official_legal.py 193행, 첫 글자 초성)의 한계: 공식 약칭이 앞 낱말을 생략한 꼴이면 그 법률이 다른 초성 목록에 있어 후보가 0건(NO_CANDIDATE)이 된다.
     → TK-143 정책상 NO_CANDIDATE는 CRITICAL이다.

3. 고칠 것
 F1(C1·C3). 두 음절 어간일 때(min_stem == SHORT_STEM이고 어간 2자) score()가 새 함수 _short_score()를 쓴다. 3자 이상 어간의 점수·규칙은 그대로 둔다(TK-130 시험 유지).
     - 대조 대상은 지금처럼 공식 약칭, 없으면 정식명이다. 약칭이라고 가산하지 않는다.
     - 대상의 법령 종류가 같고 첫 글자가 같아야 한다. '…법'으로 적힌 이름이면 대상 이름이 '법'·'법률'로 끝나야 한다('…에 관한 규칙' 제외).
     - 등급: 어간이 대상 어간 맨 앞에 그대로 이어 나옴 1000, 둘째 글자가 대상 어간 셋째 글자(둘째 말마디 첫 음절) 850, 그 밖의 말마디 첫 음절 정렬(_initials_subsequence) 700, 해당 없음 0.
     - 점수 = 등급 − min(대상 어간 길이 − 2, 100). THRESHOLD 500·MARGIN 100은 그대로다.
     - 기존 '두 음절은 말마디 첫 음절이거나 정식명 첫 낱말 그대로'(96~99행) 조건은 _short_score가 대신하므로 지운다.
 F2(C2). UNDECIDED_INFERENCE에 "ARTICLE_NOT_IN_CANDIDATE"를 넣는다.
     - 115행에서 outcome을 둘 때 candidates=[후보 법령명]도 함께 둔다.
     - 513행 MEDIUM 결과의 detail은 이 outcome이면 '약칭 추정 후보 법령의 조회 버전에 인용 조문이 없어 그 후보로 확정하지 못했다(후보: …)'로 적는다.
     - INFERENCE_NOTES에 같은 뜻의 항목을 넣는다.
     - 어간 4자 이상(약칭 꼴 아님)은 지금처럼 원래 판정을 유지한다.
 F3(C4) — 사용자 결정 X7 승인 시에만. 두 음절 어간(약칭 꼴)이 NO_CANDIDATE면 미결로 본다.
     - 513행 조건을 _undecided_inference(law_name, alias)로 바꾼다. 이 함수는 outcome이 UNDECIDED_INFERENCE이거나, NO_CANDIDATE이면서 어간이 2자일 때 참이다.
     - detail은 '첫 글자 목록에 글자 순서가 맞는 후보가 없으나, 앞 낱말을 생략한 공식 약칭일 수 있다'로 적는다.
     - 어간 3자 약칭 꼴의 NO_CANDIDATE와 4자 이상(지어낸 법률명)은 CRITICAL을 유지한다.
     - 보호 시험 단언 변경 1건이 필요하다: tests/test_tk143_short_abbreviation.py의 test_short_name_with_no_candidate_in_complete_list_keeps_not_found_law. 입력을 '가나다법'(3자, CRITICAL 유지)으로 바꾸고, 두 음절 '가나법'은 새 시험에서 ABBREVIATION_UNRESOLVED(MEDIUM)로 단언한다. 이 변경은 평가 측이 사용자 승인으로 반영한다.

4. 확인 시험(새 파일 tests/test_tk152_short_abbreviation_ranking.py — 합성 법령명, TK-130 시험의 목록·본문 흉내 재사용)
 - 약칭 가산이 첫 두 말마디 정식명을 이기지 못함(C1), 공식 약칭 맨 앞 이어짐이 이김(C3), 법률로 적힌 이름에 규칙이 후보로 오지 않음, 같은 등급 둘은 AMBIGUOUS 유지.
 - 우선 후보에 인용 조문이 없으면 ARTICLE_NOT_IN_CANDIDATE → ABBREVIATION_UNRESOLVED·MEDIUM·UNVERIFIED, detail에 후보명(C2). 어간 4자 이상은 NOT_FOUND_LAW 유지.
 - 고치기 전 코드(3c75071)에서는 C1·C3·C2 시험 3건이 실패하고 대조 3건은 통과해야 한다(평가 측 확인).
 - 기존 시험 유지: test_tk130_abbreviation_inference·test_tk143_short_abbreviation(F3을 넣으면 위 1건만 변경).

5. 평가 측 사전 검증(평가 측 재실행)
 - 실제 목록 응답(ㄱ 1,433건·ㄴ 220건·ㅅ 712건) 재현 — 탐침 A의 두 음절 약칭 6꼴:
   양성 4건(C1·C3 대상 포함)이 정답 법률로 추정됨. 고치기 전에는 1건 정답, 1건 틀린 법률, 1건 동점, 1건 정답이었다.
   모호 대조(A-C3)는 AMBIGUOUS 유지. C4 꼴 1건은 후보 0건(F3 없이는 CRITICAL, F3 적용 시 MEDIUM).
 - 추가 점검 13꼴(실재·가공 섞음): 고치기 전에 엉뚱한 법률 1개를 고르던 일반 낱말 꼴 2개가 AMBIGUOUS로 바뀜. 고치기 전 AMBIGUOUS였던 실재 약칭 꼴 2개가 정답 법률로 추정됨. 나머지는 고치기 전과 같은 결론(AMBIGUOUS 또는 후보 0).
 - 관련 시험 42건 통과(F3 포함, 단언 변경 1건 반영). 은퇴 4세트(main 기준)·고정 세트: 은퇴 4세트 53.3/48.6/56.9/45.8·오탐 0, 고정 dev 82.6·holdout 81.9·오탐 0 — 단독 사본·합본 모두 변화 0. 단 오프라인 측정은 공식 DB를 조회하지 않으므로 이 변경 경로를 직접 재지 못한다. 전체 시험: 합본 사본(3c75071 + TK-152 (a)~(d)·TK-153·TK-154, SQLite, LV_ALLOW_NETWORK=0) 전체 11,422건 통과·실패 0(화면 시험 포함, 건너뜀 11·예상 실패 24)
 - 미검증: 추정 법령의 조문 본문 대조(A-P3·P4의 인용 조문 존재는 정답지·공식 링크로 확인. 운영 본문 응답은 이번 결과에 없어 끝까지 재현하지 못함). 3자 어간·4자 이상 어간은 이번 변경 범위 밖.

6. 제출물·수용 기준
 - PR 1개(제품: law_name_inference.py·source_review.py, 시험: 새 파일 1개, F3 승인 시 test_tk143 단언 1건 — 평가 측이 반영).
 - 수용 기준: 4절 시험 통과, 필수 CI 성공, 은퇴·고정 세트 득점 하락·오탐 증가 0, 하드코딩 점검 통과(실재 법령명·약칭을 제품 코드에 넣지 않음 — 목록 응답만으로 판정).
```

### 2-36-2. TK-153
```
[TK-153(P2) 판결 의견 머리말 꼴 인식 — 구현 지시]  기준: main 3c75071(0.18.0)  평가 측 사본: ff77e27

1. 문제
- 전원합의체 판결의 반대의견 문장을 '다수의견'으로 귀속한 인용을 결정적 의견 귀속 검사(v3 D3·TK-135)가 잡지 못한다. 0.17.0·0.18.0 온라인 탐침에서 같은 결과였고, 이번에는 AI 의미 검토만 잡았다(모델 의견이라 실행마다 달라질 수 있음).
- 평가 측 재현(운영 결과 JSON에 담긴 공식 판결 응답 4건): 의견 표지가 전문에서 인식된 판결은 1/4뿐이다. 나머지 3건은 전문 전체가 다수의견으로 분류됐다. 그래서 근거 발췌 구간의 opinion_kinds도 반대의견 구간을 MAJORITY로 적는다.

2. 원인(파일·줄은 3c75071 기준)
 C1. packages/legal_engine/opinion_attribution.py 24~26행 FULL_MARKER_RE는 '…의 반대의견은 다음과 같다' 꼴만 인식한다. 공식 전문은 '8. 피고인 1에 대한 ○○의 점에 관한 대법관 갑, 대법관 을의 반대의견   (본문)'처럼 번호 붙은 머리말만 두고 본문을 바로 잇는 꼴이 많다. '9. 대법관 갑의 별개의견', '13. 다수의견에 대한 대법관 갑의 보충의견'도 같은 꼴이다.
     → law_go_kr.fetch_case가 <br/>를 공백으로 바꾸므로(law_go_kr.py 367행) 줄 끝으로는 머리말을 가릴 수 없다.
 C2. 27~29행 SUMMARY_MARKER_RE는 괄호 첫머리가 '대법관'(또는 '…에 대한')일 때만 인식한다. 판결요지의 '[피고인 갑에 대한 ○○의 점에 관한 대법관 을의 반대의견]'(쟁점 한정 첫머리)은 놓친다.
 C3. 82행 _kind는 대상 의견('반대의견에 대한')을 머리말 첫머리(target 그룹)에서만 읽는다. '대법관 갑의 반대의견에 대한 대법관 을의 보충의견'처럼 이름 사이에 있으면 보충의견(다수 쪽)으로 잘못 센다(새 머리말 꼴에서 생기는 문제).

3. 고칠 것(평가 측 사본 ff77e27과 같은 구조 — 그대로 옮겨도 된다)
 F1. HEADING_MARKER_RE를 새로 만든다. 조건은 다음과 같다.
     - 번호로 시작: (?<![\d.])\d{1,2}\s*\.\s+
     - 선택 첫머리: '(다수의견|반대의견|별개의견)에 대한'(target 그룹) 또는 마침표·대괄호 없는 150자 이내의 '…에 관한/에 대한' 쟁점 한정(뒤에 '대법관'이 와야 함)
     - '대법관 …의' + kind(반대보충의견|반대의견|별개의견|보충의견)
     - kind 바로 뒤가 공백(?=\s)이어야 한다. 그래야 '…의 반대의견이 있는 외에는', '…의 별개의견, …', '…의 반대의견에 대하여'(문장 속 언급)를 제외한다.
 F2. SUMMARY_MARKER_RE의 target 뒤에 선택 그룹 '[^\[\]]{1,150}?에\s*관한\s*(?=대법관)'을 넣는다.
 F3. _kind에서 target 그룹이 비었으면 매치 전체에서 '(다수의견|반대의견|별개의견)에 대한'을 찾아 target으로 쓴다.
 F4. _markers가 FULL·SUMMARY·HEADING 세 정규식의 매치를 위치 순으로 합친다. split_opinions·opinion_ranges·quote_opinion·evidence_pack은 그대로 둔다. 모두 _markers를 쓰므로 함께 고쳐진다.

4. 확인 시험(새 파일 tests/test_tk153_opinion_heading.py — 판결 문장은 합성)
 - 번호 머리말 4꼴(쟁점 한정 반대의견, 번호만 있는 별개의견, '반대의견에 대한 … 보충의견', '다수의견에 대한 … 보충의견')을 split_opinions·opinion_ranges가 각 의견으로 나눈다.
 - 문장 속 언급 4꼴(…이 있는 외에는 / 쉼표 나열 / '…에 대하여 본다' / 판례 인용 날짜 뒤 번호)은 머리말이 아니다.
 - 쟁점 한정 판결요지 괄호가 반대의견 표지로 인식된다.
 - LegalVerifier._opinion_findings: 번호 머리말 아래 반대의견 문장을 다수의견으로 인용하면 MISATTRIBUTED_OPINION·CONTRADICTED·A. 다수의견·다수의견 보충의견 문장은 결과 없음.
 - 고치기 전 코드(3c75071)에서는 이 파일의 6건 중 4건이 실패하고 2건(문장 속 언급·다수의견 무결과)은 통과해야 한다(평가 측 확인).
 - 기존 시험 유지: test_v3_d3_opinion·test_tk135_opinion_evidence·test_lv05_holding_distortion·test_v4_p5_legal_rules·test_evidence_rag_review·test_lv_eval_fix·test_tk145_repeated_case_citation.

5. 평가 측 사전 검증(사본 ff77e27, 평가 측 재실행)
 - 공식 판결 응답 6건(전원합의체 4건·일반 2건)의 표지: 고치기 전 전문 표지 인식 1/4 → 4/4. 머리말 위치는 정답지의 다수의견 끝 위치와 일치(문자 수 셈 방식 차이 150자 안). 일반 판결 2건은 표지 0(변화 없음).
 - 탐침 B 7항목 귀속: B-C3(반대의견을 다수의견으로 귀속)이 결정적으로 MISATTRIBUTED(A). 양성 4건·나머지 대조 2건 오탐 0.
 - 관련 시험 87건 통과, 새 시험 6건 통과. 은퇴 4세트(main 기준) 53.3/48.6/56.9/45.8·오탐 0 변화 0, 고정 dev 82.6·holdout 81.9·오탐 0 변화 0. 전체 시험: 합본 사본(3c75071 + TK-152 (a)~(d)·TK-153·TK-154, SQLite, LV_ALLOW_NETWORK=0) 전체 11,422건 통과·실패 0(화면 시험 포함, 건너뜀 11·예상 실패 24). TK-153 단독 전체 시험은 세 사본 동시 실행 부하 중 OCR 시간 시험 1건이 일시 실패해 중단(그 시험은 단독 재실행에서 main·사본 모두 통과)
 - 미검증: AI 의미 검토 단계의 변화(근거 발췌 구간 opinion_kinds가 바뀌면 TK-135 '반대·별개의견 구간만 근거인 지지 판단 불채택'이 더 자주 작동할 수 있음 — 모델 호출이 필요해 오프라인으로 재지 못함).

6. 제출물·수용 기준
 - PR 1개(제품: opinion_attribution.py만, 시험: 새 파일 1개). 기존 시험 단언 변경 없음.
 - 수용 기준: 위 4절 시험 통과, 필수 CI 성공, 은퇴·고정 세트 변화 0(오탐 증가 0), 하드코딩 점검 통과(시험 판결 문장·이름을 제품 코드에 넣지 않음).
```

### 2-36-3. TK-154
```
[TK-154(P1) 미발견 대법원 전원합의체 판결 '부존재 의심'(HIGH) — 구현 지시]  기준: main 3c75071(0.18.0)  평가 측 사본: 6125e4a
사용자 원문(2026-11-12): "EX-1 처리 결정: 둘다 처리" — (나) 규칙 보정 새 티켓 + (다) 그 결과에 맞춰 명세 정리.

1. 문제
- 0.18.0 온라인 case9 EX-1(서면이 인용한 대법원 전원합의체 판결, 사건번호 형식은 유효, 공식 DB에 없음)이 MEDIUM '조회 범위 내에서 찾지 못한 판례'로만 나와 회귀했다(0.17.0 CRITICAL → 0.18.0 MEDIUM, 명세 기대 HIGH 이상).
- LV-03(사용자 승인 X6)은 미발견 판례를 일률로 '확인 불가'(MEDIUM)로 둔다. 그래서 지어낸 대법원 판례도 MEDIUM으로만 알린다.

2. 원인과 근거(파일·줄은 3c75071 기준)
 C1. packages/legal_engine/verifier.py 354~361행: 형식이 유효한 미발견 판례는 법원·판결 종류와 무관하게 severity MEDIUM, tags SOURCE_LIMIT이다. authority_status.py 91~99행 is_covered_precedent_scope는 늘 False다(전수 수록 증명 없음 — LV-03-R4, 유지).
 C2. 공개 범위 근거: 법원도서관 조사심의관 '판례공보와 종합법률정보'(2017. 8. 4., https://www.scourt.go.kr/portal/gongbo/PeoplePopupView.work?gubun=24&seqNum=1827)
     - 판결 등급 'A급은 전원합의체 및 대법원판례집에 실을 만한 매우 중요한 판결', 'A급과 C급으로 분류된 판결은 판례공보에 싣고'
     - 공보 게시는 매월 1일·15일, 종합법률정보 등록은 게시 며칠 후
     → 전원합의체 판결은 공보 게재·공개 DB 등록 대상이다.
     → 다만 시스템이 조회하는 국가법령정보 판례 DB가 공보 판결 전부를 담는다는 공식 증명은 찾지 못했다. 그래서 확정(CRITICAL)이 아니라 의심(HIGH)이다.

3. 고칠 것(평가 측 사본 6125e4a와 같은 구조)
 F1. authority_status.py에 ENBANC_PUBLICATION_LAG_DAYS = 180(공보 월 2회 게재·DB 등록·국가법령정보 연계 지연을 넉넉히 둔 값)과 enbanc_absence_suspected(citation, current_date)를 둔다. 아래가 모두 참일 때만 참이다.
     - get_court_tier == SUPREME
     - case_kind 또는 raw_text에 '전원합의체'(서면 스스로의 표기)
     - decision_date와 current_date가 유효하고, 선고일 ≤ 기준일 − 180일
 F2. verifier.py:
     - verify_case(self, citation, current_date=None). verify_citations(101행)가 current_date를 넘긴다. None이면 today_korea().
     - 미발견·형식 유효 분기(354행 else 앞)에 elif enbanc_absence_suspected(...)를 넣는다. 결과:
       · status NOT_FOUND, severity HIGH, tags ["LEGAL","CASE","ENBANC_NOT_FOUND"](SOURCE_LIMIT·FAKE_PRECEDENT 없음)
       · 제목 '공개 대상인 대법원 전원합의체 판결을 조회 범위에서 찾지 못함(부존재 의심): …'
       · 설명: 공보 게재 대상, 180일 경과, 오기 또는 실재하지 않을 가능성이 높음, 전수 수록 미증명이라 확정하지 않음, 사본·종합법률정보로 확인
       · levels·features의 authority_status는 SUSPICIOUS('존재의심'), features에 suspicion_basis="ENBANC_PUBLICATION_EXPECTED"·publication_lag_days
     - CONFIRMED_NONEXISTENT·CRITICAL은 쓰지 않는다(X6 유지).
 F3. 조회 실패(READY 아님)·헌재 사건번호·하급심·전원합의체 표기 없음·선고일 없음·180일 이내는 지금 동작 그대로다.

4. 확인 시험(새 파일 tests/test_tk154_enbanc_not_found.py — 사건번호·날짜 합성)
 - 180일 지난 전원합의체 미발견: HIGH·NOT_FOUND·ENBANC_NOT_FOUND, SUSPICIOUS, '확정하지 않' 문구
 - 전원합의체 표기 없음·180일 이내·선고일 없음·하급심: MEDIUM·SOURCE_LIMIT 유지
 - 조회 실패: 모든 결과 UNVERIFIED, HIGH 이상 없음
 - 경계: 선고일 + 180일 당일 참, 하루 전 거짓
 - 기존 시험 유지(단언 변경 없음): test_lv03_three_tier_authority·test_lv_contract_review_eval·test_ground_truth_prepared_brief·test_legal_engine·test_lv_round2/3/4_contract_eval·test_lv04_quote_diff

5. 평가 측 사전 검증(평가 측 재실행)
 - case9 EX-1과 같은 서지(대법원·전원합의체 표기·선고 2023년, 기준일 2026-11-12)를 빈 조회 결과로 돌리면 CASE_NOT_FOUND HIGH. case9 명세 EX-1(CASE_NOT_FOUND, HIGH 이상)을 바꾸지 않고 충족할 것으로 본다.
 - 온라인 재측정은 미검증이다. 배포 후 사용자 실행이 필요하다.
 - 관련 시험 통과, 새 시험 7건 통과. 은퇴 4세트(main 기준)·고정 세트: 은퇴 4세트 53.3/48.6/56.9/45.8·오탐 0, 고정 dev 82.6·holdout 81.9·오탐 0 — 단독 사본·합본 모두 변화 0. 단 오프라인 측정은 공식 DB를 조회하지 않으므로 이 변경 경로를 직접 재지 못한다. 전체 시험: 합본 사본(3c75071 + TK-152 (a)~(d)·TK-153·TK-154, SQLite, LV_ALLOW_NETWORK=0) 전체 11,422건 통과·실패 0(화면 시험 포함, 건너뜀 11·예상 실패 24)
 - 미검증: 국가법령정보 판례 DB의 전원합의체 수록률(표본 대조 필요 — 운영 조회 키가 있어야 함), 180일 값의 적정성(공보 게재 후 국가법령정보 반영 지연 실측 없음).

6. 제출물·수용 기준
 - PR 1개(제품: authority_status.py·verifier.py, 시험: 새 파일 1개). 기존 시험 단언 변경 없음. case9 명세(보호 경로) 변경 없음.
 - 수용 기준: 4절 시험 통과, 필수 CI 성공, 은퇴·고정 세트 변화 0(오탐 증가 0), 배포 후 온라인 case9 23/23 확인(사용자 실행).
```
- 11-12 사용자 '평가pr 생성 병합' → #262 생성(head `b5f60bb`, CI 전부 성공 — 인용) → 병합 Steve `e6ffe84`(expectedHeadSha 확인). Steve의 NEXT 잘림(48줄) 복원 반영. 지시 NEXT 2-36 전달 가능, X7 결정 대기.

### 2-36-4. 사용자 결정 X7 승인 (11-12)
- 사용자 원문: "X7 결정: 두 음절 약칭이 후보 0건일 때 CRITICAL 대신 MEDIUM으로 승인"
- TK-152는 F3(C4)까지 한 PR로 구현한다(평가 측 사본 `df6fc3c` = `37d1bce` + (d)). 보호 시험 `tests/test_tk143_short_abbreviation.py::test_short_name_with_no_candidate_in_complete_list_keeps_not_found_law`의 단언 변경(입력 '가나다법'으로 CRITICAL 유지 확인) + 새 시험 `test_two_syllable_name_with_no_candidate_is_unverified`(두 음절 '가나법' → ABBREVIATION_UNRESOLVED·MEDIUM)는 승인된 변경이다. 시험 이름은 유지한다. 증분 [patches/TK-152_d_X7_on_37d1bce.diff](patches/TK-152_d_X7_on_37d1bce.diff).
- 수용 기준 추가: 어간 3자 약칭 꼴 후보 0건과 어간 4자 이상(지어낸 법률명)은 CRITICAL 유지.

### 2-36-5. #263(TK-152) 판정 — 내용 수용, 대상 브랜치 정정(보완 1건) (11-12, head `49f97b9`)
- 제품 = 사본 `df6fc3c`와 같은 구조(더 보수적 차이 2: is_subsequence 유지·정식명 '…법/법률' 끝 확인). 실제 목록 응답 재현 15꼴 사본과 같음, 새 시험 10건 변별(3c75071 실패 6·통과 4), 관련 45건 통과, 하드코딩 통과, 은퇴 5세트·고정 82.6/81.9/0 변화 0(기준 Steve `e6ffe84`, 평가 측 재실행). CI 전부 성공(인용).
- 보완: PR이 main 대상·main `3c75071`에서 분기 → Steve에서 새 브랜치 + `git cherry-pick 49f97b9`(충돌 없음)로 Steve 대상 PR을 다시 내고 #263은 닫는다. 대상만 바꾸면 Steve의 sealed_20261025 등이 지워지는 diff가 생긴다. 평가 측 지시 표기 결함('기준: main 3c75071' = 사본 기준 코드, 제품 코드는 Steve와 같음) — TK-153·154도 Steve `e6ffe84` 기준. PR 코멘트로 전달.
- 11-12 #264(TK-152, Steve 대상, head `9768bc8`) **수용**: 3fbf56f = #263 49f97b9 cherry-pick, 9768bc8 = X7 승인 시험 추가(test_tk143). 제품 = 평가 측 판정본 diff 0, 관련 46건 통과, CI 전부 성공(인용). #263 닫힘. 병합 대기(사용자).
- 11-12 사용자 '#264 병합' → Steve `d8b1b2a`(expectedHeadSha `9768bc8`, CI 전부 성공). TK-152 병합. 남은 것: TK-153·154 PR.
- 11-12 #265(TK-153, head `6e9c8f3`)·#266(TK-154, head `86d8d04`) **수용**: 제품·시험 = 사본 ff77e27·6125e4a diff 0, 합본(Steve `d8b1b2a` + 두 PR, 충돌 없음) 관련 296건 통과, B-C3 결정적 검출(A), 하드코딩 통과, 은퇴 5세트·고정 변화 0(평가 측 재실행). CI 전부 성공(인용). 병합 대기(사용자). 병합 뒤 릴리스 후보 verify_all.
- 11-12 사용자 '#255,256 병합'(#255·#256은 11-11 병합 완료 — #265·#266으로 해석) → #265 병합 Steve `4118677`(expectedHeadSha `6e9c8f3`), #266 병합 Steve `9406d9c`(expectedHeadSha `86d8d04`). Steve 제품·시험 = 평가 합본 `8e1294c` diff 0. 다음: 릴리스 후보 verify_all 전체.
- 11-12 0.19.0 릴리스 후보 Steve `9406d9c`(TK-152·153·154) verify_all 전체 모드(기준 0.18.0 main `3c75071`, 평가 측 재실행) **종료 0**: environment·acceptance 1,239·regression_ledger 2,357·score_gate·regression_gate(회귀 없음)·hardcoding_diff·test_edits·protected_paths(16개 승인)·version_policy·full_tests 9,997·browser_tests 197, 실제 실패 0. 은퇴 4세트(main 기준) 53.3/48.6/56.9/45.8·20261025 34.1·고정 82.6/81.9/0 — 0.18.0과 같음. 다음: 0.19.0 판정(봉인 시험 여부 사용자 결정).

## 2-37. 0.19.0 판정·버전 커밋 지시 (11-12, 사용자 '봉인시험 미시행, 평가 PR 생성 병합')
- 판정서: `docs/scorecards/version_verdicts.json` 0.19.0(minor, changed·fixed, measured_commit `9406d9c`). 봉인 시험은 사용자 결정으로 미실시, 배포 뒤 0.18.0 대 0.19.0 온라인 비교로 갈음.
- 평가 측 사본으로 만들어 점검: check_version_policy '위반 없음(상향 1건 0.18.0 → 0.19.0)', `scripts/update_readme.py` 생성 결과와 README 일치, 버전·README 관련 시험 통과. 증분 [patches/v0.19.0_version_commit_on_9406d9c.diff](patches/v0.19.0_version_commit_on_9406d9c.diff).

```
[0.19.0 버전 커밋 — 구현 지시]  기준: 이 평가 PR이 Steve에 병합된 뒤의 Steve 최신
- 판정서: docs/scorecards/version_verdicts.json 0.19.0(minor, changed·fixed, 9406d9c 기준). 평가 측 판정 없이 버전을 올리지 않는다.
- 커밋 1개, PR 1개(Steve_ACASiaLAW 대상). 바꿀 파일 5개 — 평가 측 증분 docs/handoff/patches/v0.19.0_version_commit_on_9406d9c.diff를 그대로 적용한다(git apply).
  · packages/common/config.py: Settings.version "0.18.0" → "0.19.0"(주석 포함)
  · docs/releases.json: 0.19.0 항목 추가(판정 요약·TK-154·153·152 변경 3줄)
  · docs/release_highlights.json: "0.19" 요약 4줄
  · README.md·docs/RELEASE_HISTORY.md: scripts/update_readme.py 생성 결과(증분과 같음)
- 확인: python scripts/check_version_policy.py --base <Steve 최신> → '위반 없음(상향 1건 0.18.0 → 0.19.0)', python scripts/update_readme.py 실행 뒤 변경 없음, tests/test_update_readme.py·tests/test_v4_run_manifest.py 통과.
- 수용 기준: 평가 측 증분과 diff 0, 필수 CI 성공. 그 밖의 파일은 바꾸지 않는다.
```
- 11-12 #267(평가 PR, 0.19.0 판정서) CI 전부 성공(인용) → 병합 Steve `7375695`(expectedHeadSha `c48d8fc`). 버전 커밋 지시 NEXT 2-37 전달 가능(증분이 새 Steve에 그대로 적용됨 — 평가 측 확인).
- 11-12 #268 0.19.0 버전 커밋(head `98a7754`) **수용**: 평가 측 증분과 diff 0, check_version_policy 위반 없음(0.18.0 → 0.19.0), update_readme 변경 없음, 관련 시험 15건 통과(평가 측 재실행). CI 전부 성공(인용). 병합 대기(사용자) → 릴리스 PR.
- 11-12 사용자 '#268 병합' → Steve `e57855f`(expectedHeadSha `98a7754`). 버전 0.19.0이 Steve에 들어감. 다음: 릴리스 PR(Steve → main, sealed_20261025 제외).
- 11-12 사용자 '릴리스 PR 생성, 병합' → #269(release/0.19.0, main `3c75071` + Steve `e57855f`, 제외 11파일 유지) CI 전부 성공(인용) → 병합 main `5b878a1`(expectedHeadSha `1f6c9e6`). 다음: 배포 확인(/api/health version 0.19.0·commit 5b878a1) → 태그 v.0.19.0(사용자) → 0.18.0 대 0.19.0 온라인 비교.
- 11-12 배포 확인(사용자 제공 /api/health): status ok, version 0.19.0, commit `5b878a10402b7da0eafc2bc2b52e144696e61966`(= #269 병합 커밋), database ok → 0.19.0 운영 배포 확인. 다음: 태그 v.0.19.0(사용자) → 0.18.0 대 0.19.0 온라인 비교(사용자 실행).
- 11-12 0.18.0 대 0.19.0 온라인 비교 1차(사용자 실행, 5b878a1): case9 20/23(0.18.0 22/23) — EX-1 통과(TK-154), AI-1·2·4 실패(첫 모델 UNCERTAIN → 효율 라우팅으로 두 번째 의견 미호출, 모델 변동·코드 무관). 탐침 받은 33항목 26/33(0.18.0과 같음), B-C3 결정적 검출(TK-153). 탐침 A·D hwp 결과 없음 — 재업로드 요청. 기록 online_compare_0180_0190_20261112.md.
- 11-13 0.19.0 온라인 2차(탐침 A·D hwp 추가): A 8/10 → 10/10(실재 법률 CRITICAL 오단정 2 → 0, TK-152), D hwp 4/4 같음. 47항목 0.18.0 38/47 → 0.19.0 40/47, 회귀 0. case9 20/23(EX-1 통과, AI 판별 3항목 모델 변동).
- 11-13 case9 재실행(0.19.0 5b878a1): 23/23 — AI 판별 첫 모델 AI 쪽 0.68 → 두 번째 의견 호출 → AI-1·2·4 통과. 1차 20/23은 모델 응답 변동 확인(2회 중 1회 유보). 0.19.0 온라인 최종: case9 23/23, 탐침 40/47, 회귀 0.
- 11-13 사용자 '태그완료' → 원격 `refs/tags/v.0.19.0` = `5b878a10402b7da0eafc2bc2b52e144696e61966`(main #269 병합 커밋, 경량 태그 — v.0.18.0과 같은 형식) 확인. 0.19.0 릴리스 주기 완료(판정·버전 커밋·릴리스·배포·온라인 비교·태그). 다음: 다음 주기 범위 사용자 결정.
- 11-13 사용자 '프로그램 개선 소요 명세서 for V.1.0.0' 타당성 분석·개선 계획 제안 작성(docs/handoff/V1_0_0_UI_IMPROVEMENT_PLAN_20261113.md): 항목별 현행 코드 확인, 작업 묶음 W1~W5, 버전 경로(0.20.0 → 1.0.0 이정표 조건), 사용자 결정 D1~D5. 발견: 배포 차단 사유 문구 결함(공식 원문 확인 판례에 '조회 불가' 표기, gate.py 216~219행), 표 위치 칸 넘침 원인(배지 nowrap·영문 kind), 의심 사유 강제 절단.
- 11-13 사용자 '세부설명은 case9 온라인 결과 화면 기준' → 계획 문서 5절 덧붙임: case9 3회분 대조(6-1 HIGH 2건 일치, 행 종류 영문 배지 16행, 표 영문 코드 8종, 의심 사유 16행 중 12행 잘림, 명세 예시 문구는 0.18.0 판), 명세 밖 같은 성격 3건(D6).
- 11-13 사용자 'D1~D6 권고대로 진행' → V1.0.0 개선 계획 6절 기록. 다음: W1~W5 평가 측 사본 사전 검증 → 지시문.


## 2-38. V1.0.0 개선(0.20.0) — TK-155 화면·보고서 정리, TK-156 AI 판별 두 모델 고정 구현 지시 (11-13, 사용자 'D1~D6 권고대로 진행')
- 근거: [V1_0_0_UI_IMPROVEMENT_PLAN_20261113.md](V1_0_0_UI_IMPROVEMENT_PLAN_20261113.md)(원문 부록 A, 결정 6절). 평가 측 사본(e57855f 기준)에 먼저 적용해 사전 검증했다. 패치: `docs/handoff/patches/TK-155_156_v1ui_on_e57855f.diff`.
- 사전 검증 요약(평가 측 재실행): 전체 시험 11,444 통과·실패 0, 은퇴 5세트·고정 세트 변화 0, case9·탐침 B·C·D 화면 영문 코드 0.
- 사용자 승인 대기: 기존 시험 단언 변경(TK-155 8파일 13건, TK-156 1파일 2건). 승인 전에는 전달하지 않는다.
- 두 PR 모두 Steve_ACASiaLAW 대상. TK-155는 화면 PR이라 캡처·원문 대응표를 사용자께 보이고 확인 뒤 수용한다.

### 2-38-1. TK-155

```
[TK-155(P2) 화면·보고서 정리 — 「프로그램 개선 소요 명세서 for V.1.0.0」 1~3·5~7번 + D6 — 구현 지시]
기준: Steve_ACASiaLAW e57855f(0.19.0)  평가 측 사본: v1ui(패치 docs/handoff/patches/TK-155_156_v1ui_on_e57855f.diff — router.py·test_efficient_llm_routing.py 부분은 TK-156)
PR 대상 브랜치: Steve_ACASiaLAW(main 아님). 버전: 0.20.0(changed·removed). 화면 PR이라 **사용자 확인 뒤 수용**한다(CLAUDE.md 2026-10-25).

0. 사용자 원문과 결정
 원문 전문은 docs/handoff/V1_0_0_UI_IMPROVEMENT_PLAN_20261113.md 부록 A에 그대로 있다(이 티켓의 원문). 결정(11-13 "D1~D6 권고대로 진행"):
 D1 '확인 전 항목' → 탭 제목 옆 '검토 결정 대기 n'으로 이동 / D2 '진행 상태' → 카드 삭제, 완료가 아닐 때만 한 줄 안내(사유 보기)
 D3 배포 판정 → 화면 패널·엑셀 요약 행 모두 삭제(결과 JSON scores.release_gate는 유지) / D5 참고문헌 표기 → 셀 반복 삭제, 표 위 범례 한 줄
 D6 명세 밖 같은 성격 3건 포함: 인젝션 결과의 영문 코드, 영문 오류 문장, '을(를)' 조사

1. 원문 문장별 대응표(수용 기준 — 줄 번호는 e57855f)
 | 원문 | 현행 위치·원인 | 고칠 것 | 확인 |
 | 1 '법률문서 검토' 삭제 | index.html 7행 span.eyebrow | 지운다 | 캡처 01 |
 | 1-1 미지정 문구 삭제, 입력값만 표시 | app.js 799행 projectMeta('사건번호 미지정'·'적용법령 기준일 미지정'), 748행 사이드바 | 값 있는 것만 ' · '로 잇고, 하나도 없으면 projectMeta를 hidden. 사이드바는 [사건번호, '자료 n개'] | 캡처 01, 값 있는 프로젝트 캡처 |
 | 1-3 8개 → 'AI 작성 진단'(현행 표기)·'출처 미확인 인용 n건'·'법률적으로 무리한 주장 n건' | app.js 1047~1116 renderSummary 8칸 | 3칸. 출처 미확인 = 기존 '성립 불가'+'공식 DB 미확인' 합(1029~1044행 계산 그대로), 성립 불가가 있으면 작은 글 '사건번호 형식 오류 n건 포함'. 무리한 주장 = '법률적으로 무리한 주장' 탭 행 수(renderFindings의 3단 분류 수, 필터와 무관). 카드를 누르면 그 탭으로 이동. styles.css 357행 .summary 4칸 → 3칸, 좁은 화면(967행) 1칸 | 캡처 01: 9건·9건이 각 탭 행 수와 같음 |
 | 1-3-1 '검토에 포함' 삭제 | 1052행 | 지운다 | 캡처 01 |
 | 1-3-2 '배포 가능 상태' 삭제 | 1053행 | 지운다(D3) | 캡처 01 |
 | 1-3-3 '검증 위험 지수' 삭제 | 1054행 | 지운다 | 캡처 01 |
 | 1-3-4 성립 불가·공식DB 미확인 통합 | 1056~1057행 | 위 '출처 미확인 인용' 1칸 | 캡처 01 |
 | 1-3-5 '확인 전 항목' | 1058행 | D1: 카드 삭제. '출처가 확인되지 않는 항목'·'법률적으로 무리한 주장' 탭 h2 옆 배지 '검토 결정 대기 n'(그 탭 행에 묶인 결과 중 review_status NEEDS_REVIEW 수, 0이면 숨김). 배지를 누르면 기존 explainReviewPending 설명 | 캡처 03·04 |
 | 1-3-6 '진행상태' 통합 | 1059행 | D2: 카드 삭제. 실행 상태가 PARTIAL_COMPLETED·FAILED·CANCELLED일 때만 카드 아래 한 줄 '<상태>: … [사유 보기]'(기존 explainRunStatus). 진행 중은 기존 진행 막대 | 캡처 01 |
 | 2 배포차단 사유 중복이면 삭제 | 1093~1112 renderGateReasons, 사유 문장 gate.py 216~263 | D3: 화면 패널과 GATE_LABELS 삭제. packages/report_engine/exporters.py 179~188행 엑셀 요약의 배포가능 상태·검증위험 지수·지수 성격·차단 사유·사람 검토 사유 행 삭제. gate.py·결과 JSON은 그대로 | 캡처 01, 엑셀 요약 시트 |
 | 2-1 (남길 경우) 쉬운 말 | — | D3로 해당 없음 | — |
 | 3 '작성주체 확률이 아니라 …' 삭제 | gate.py 137행 → 화면 gate-note, 엑셀 '지수 성격' | 화면·엑셀에서 빠짐(위 2와 함께). gate.py 데이터는 유지 | 캡처 01, 엑셀 |
 | 5·5-2 'AI 작성 참고 신호 문구' 제목 반복 → 한 번 + 번호 목록 | app.js AI_DIAGNOSIS 결과를 결과마다 카드로 그림(ai_document_detector.py 890행이 근거별로 같은 제목 생성) | 화면에서 같은 (중요도, 제목) 결과를 카드 하나로 묶고 제목 옆 '(n건)', 근거는 ol 번호 목록. 결과 데이터 구조는 그대로 | 캡처 02 '(4건)' + 1~4 |
 | 5-1 안내문 삭제 | index.html 13행 #aiTabNoticeBanner | 지운다 | 캡처 02 |
 | 5-3 인젝션 경고 간소화 | app.js 1190행 | '프롬프트 인젝션 속임수 검증: AI 판단 왜곡 지시문 탐지 — 이 문서는 AI 검토에서 제외' 한 줄(격리 결과 해석에 필요한 마지막 구절은 계획 1절 5-3 판단대로 유지) | 캡처 02 |
 | 6-0 검색 삭제 | index.html 14행 #findingSearch, app.js renderFindings의 검색어 필터·3314행 이벤트 | 입력창과 검색어 필터 코드를 함께 지운다(중요도 필터는 유지) | 캡처 03 |
 | 6-1 HIGH 이상 안내 배너 삭제 | index.html 14행 #highSecurityAlertBanner, app.js 2510~2520 | 요소와 그 갱신 코드를 함께 지운다 | 캡처 03 |
 | 6-2·7-1 위치 칸 넘침 | styles.css 483~492 .badge white-space:nowrap(위치 칸 폭 10%), 행 종류 배지가 label()에 한글 이름이 없어 영문 코드 그대로(app.js 53행·2339~2341) | 표 셀 안 배지만 줄바꿈 허용(td .badge {white-space:normal; overflow-wrap:anywhere; max-width:100%}). labels에 CITATION '인용'·FACT '사실관계'·TEMPORAL '적용 시점'·REFERENCE '참고문헌' 추가 | 캡처 03·04: 배지가 칸 안 |
 | 6-3·7-2 셀 속 영문 코드 삭제 | 화면이 코드를 그대로 쓰는 곳(2430~2445 상태 코드 줄, reference_case_match) + 엔진 문장 속 코드('(RETROACTIVE_APPLICATION_ERROR)' 등) | ① 판정 배지와 겹치는 상태 코드 줄은 그리지 않는다(설명 문장 ai_generation_basis만). ② friendlyText에서 괄호 속 코드 '(XXX_YYY)'를 지우고, 남은 대문자 코드는 '코드→한글' 표(labels + CODE_WORDS)로 바꾼다. ③ 셀에 쓰는 문장(claim_text·verdict_label·설명·where)은 모두 friendlyText를 거친다. 표에 넣을 코드: OFFICIAL_NOT_FOUND·OFFICIAL_CONFIRMED·NOT_ASSESSED·NOT_CHECKED·NOT_MENTIONED·PENDING_REVIEW·UNVERIFIED_SCOPE·NOT_IN_REFERENCE·IN_REFERENCE·RETROACTIVE_APPLICATION_ERROR(사본의 한글 이름 그대로 옮겨도 된다) | 5절 '코드 잔존' 결과 |
 | 6-4·7-3 '[RAG참고자료]' 삭제 | 사실관계 행 설명 앞 접두 | friendlyText에서 '[RAG참고자료]' 접두를 지운다 | 캡처 04 |
 | 6-5·7-4 '참고문헌·구속력 없음, 공식 확인 아님' 셀 반복 삭제 | app.js 2194·2233·2348행 | D5: 셀 상자 제목은 '주요 참고문헌 대조', 위치 배지는 '참고문헌'. 대신 두 탭 표 위(#referenceStatus·#legalReferenceStatus 뒤)에 범례 한 줄 '주요 참고문헌은 등록된 검증 자료입니다. 판례·법령과 달리 법적 구속력은 없습니다.' | 캡처 03·04 |
 | 6-6 미확인 범위 가독성 | app.js 2806~2812 접힌 회색 글 | 경고색 테두리 카드(details.unverified-card): 요약줄에 '미확인 범위 n건 — 인용 a · 참고자료 b'(unverified_items.kind별: citation 인용, reference_library 참고자료, 그 밖 기타), 펼치면 지금 목록 | 캡처 03 |
 | 6-7·7-6 긴 셀 3~5줄 + 세부 보기 | 셀 전문 표시 | 문서 주장·설명·근거 문장에 .clamp(4줄, -webkit-line-clamp:4). 넘치면 바로 아래 '더보기' 버튼 → 같은 자리에서 펼침/'접기'. 별도 링크 대신 제자리 펼침(계획 1절 6-7 판단). 인쇄·보고서는 전문 | 캡처 03·04 '더보기' |
 | 7-5 '의심 사유' 잘림 | app.js 2476~2483: 첫 문장(20~120자) 또는 97자에서 자르고 '…' | 자르지 않고 .clamp + 더보기. 단 '확인 대상'과 같은 글이면(공백 무시, 한쪽이 다른 쪽을 포함) 한 번만 보이고, 사유가 더 길면 그 전문을 '확인 대상' 줄에 쓴다(정보 손실 0) | 캡처 04 |
 | D6-1 인젝션 결과의 영문 코드 | 제목 'META_INSTRUCTION 후보: ROLE_OVERRIDE — 경로: …', 설명 '분류=INSTRUCTION_LIKE', 'visible_text 위치', '(심각도 HIGH)', 검사한 층 encoded_text·outline | ① 결과 유형 이름(META_INSTRUCTION·HIDDEN_INSTRUCTION 등 FindingType)은 app.js에 적지 않는다 — 보호 시험 tests/acceptance/test_f1_protected.py T4(app.js의 FindingType 이름 3개 이하)와 충돌한다(사전 검증에서 확인). packages/common/finding_category_map.py에 FINDING_TYPE_SCREEN_NAMES(ADVERSARIAL_FINDING_TYPES 16종 → 한글)를 두고 apps/api/routers/projects.py get_finding_categories 응답에 "names"로 싣는다. friendlyText는 state.findingCategories.names를 먼저 본다. ② 의도(ROLE_OVERRIDE 등 InjectionIntent)·분류(INSTRUCTION_LIKE·PROMPT_INJECTION_LIKELY)·유니코드 신호(ZERO_WIDTH 등 unicode_scan kind)는 app.js CODE_WORDS. ③ 소문자 층·필드 이름은 LAYER_NAMES 보강(scanner.scanned_paths가 내는 이름 전부)과 FIELD_WORDS. ④ 심각도는 label() | 캡처 02, API 시험 |
 | D6-2 영문 오류 문장 | packages/legal_engine/verifier.py 1237행 '공식 Source 조회…', 1261행 message가 'Multiple versions share the requested effective boundary' 등 영문 그대로 | 모듈 함수 _readable_source_message(message): packages.verification_engine.review_items.HUMAN_READABLE_UNVERIFIED_REASONS로 아는 문장은 한국어로 바꾸고 모르는 것은 그대로. 1261행 detail에 사용. '공식 Source' → '공식 출처' | 시험 + 캡처 03 |
 | D6-3 '을(를)'·'이(가)' | packages/legal_engine/argument_validity_verifier.py 639·662~663행 '{noun}을(를)'·'{noun}이(가)' | noun이 '법령'이면 을/이, '판례'면 를/가로 고른다 | 시험 |
 | (부수) AI 판별 생략 사유(D4 화면 쪽) | app.js modelOpinions | 의견이 2개 이상이고 Gemini를 부르지 않았으면 'Gemini: 두 모델 판정이 일치해 세 번째 의견은 묻지 않았습니다.'(판정이 엇갈렸는데 없으면 '이번 실행에서는 호출하지 않았습니다.') | 캡처 02 |
 | (부수) AI 탭 설명문의 필드 이름 | ai_document_detector.py 605~610 SCORE_DEFINITIONS 'ai_score'·'finding.confidence', 판정 근거 목록 'AI_PARTIAL_GENERATION로 최종 확정함' | 화면에서 friendlyText로 '점수'·'값'·'일부 AI 작성'. 엔진 문장은 바꾸지 않는다 | 캡처 02 |

2. 범위 밖(이번에 하지 않음 — 사용자 판단 후보로 보고)
 - '출처가 확인되지 않는 항목' 탭 아래 접힌 '주요 참고문헌 검토 결과(RAG)' 처리 기록: 자료별 상태 코드(INDEXED_PARTIAL·REFERENCE_PARTIALLY_READ·NOT_SELECTED_METADATA 등)와 ISO 시각이 그대로 보인다. 원문 6-3은 '표 중 … 셀'이라 범위 밖으로 두었다.
 - Word·PDF 보고서의 'AI 진단' 칸이 판정 코드(AI_PARTIAL_GENERATION 등)를 그대로 쓴다(docx_report.py 183행). 원문은 화면 기준이라 범위 밖.
 - 6-1 계획의 선택 항목('AI 작성·보안 진단' 탭 버튼에 HIGH 이상 건수)은 넣지 않았다.

3. 기존 시험과의 충돌(평가 측이 사용자 승인으로 고칠 단언 — 구현 측은 사본 패치의 시험 변경을 그대로 옮긴다)
 사본에 적용한 뒤 관련 시험 58파일을 돌려 13건이 옛 요구 단언으로 실패했다(8파일). 모두 원문이 없애거나 바꾸라고 한 것을 확인하던 단언이다. 사본에서 아래처럼 고쳐 통과를 확인했다(평가 측 재실행). **사용자 승인 대상**이며, 승인 뒤 구현 측은 패치의 시험 변경을 그대로 옮긴다(되돌리지 않는다).
 | 시험 | 옛 단언 | 새 단언(근거) |
 | test_f1_ai_security_tab_browser.py — test_ai_tab_renamed_and_notice_banner_visible | #aiTabNoticeBanner 보임 | 이름을 …_removed로, 배너 0개(5-1) |
 | 같은 파일 — test_high_security_alert_banner_visible_and_jumpable | HIGH 배너 보임·점프 | …_removed: 배너 0개, 탭 버튼으로 이동(6-1) |
 | test_f2_review_screen_browser.py — …_reason_truncation_and_location_display | 의심 사유 '…' 포함·120자 이하 | '…'로 끝나지 않음, .clamp, 더보기 누르면 .expanded(7-5) |
 | 같은 파일 — test_f2_filters_search_severity_review_status | #findingSearch 검색 동작 | #findingSearch 0개(6-0). 중요도 필터 단언 유지 |
 | test_frontend_gate.py — test_gate_reasons_are_shown_open_and_readable(2) | '배포 차단 — 사유 6건' 패널 | …_not_rendered: 카드 3개, 배포 판정 문구·사유 없음(D3) |
 | test_frontend_metric_explain.py — …_metrics_explain_themselves(2) | '확인 전 항목'·'진행 상태' 카드 클릭 | 카드 없음. 출처 탭 '검토 결정 대기 2' 배지 → '검토 결정 대기란' 대화상자(성격별 건수 단언 유지), 상단 안내 '사유 보기' → '진행 상태: 일부 미확인' 대화상자(원인별 단언 전부 유지)(D1·D2) |
 | test_frontend_summary_compact.py(3) | .metric 8개, '배포가능 상태'·'검증위험 지수' 보임 | 3개, 세 제목 보임, 없앤 다섯 제목 0개(1-3). 크기 단언 유지 |
 | test_tk61_layout_browser.py — test_tk61_security_finding_items_vertical_layout | 모든 .security-finding-item에 '> .link-button'·'> small' | AI 작성 진단 묶음은 '머리 위·번호 목록 아래'를 따로 확인, 위아래 배치 단언은 나머지 항목에 그대로(5-2) |
 | test_tk88_three_tier_review.py — test_frontend_app_js_classification_matches_specification | app.js에 '참고문헌(구속력 없음)' | app.js에 없음 + index.html 범례 '법적 구속력은 없습니다'(D5) |
 (TK-156의 test_efficient_llm_routing.py 단언 2건은 TK-156 지시에 적는다.)

4. 새 시험(구현 측이 추가)
 새 파일 tests/test_tk155_ui_cleanup.py — 평가 측 사본에 작성해 통과 확인. 패치의 파일을 그대로 옮겨도 된다(문장·사건번호·법령명은 모두 합성).
 - 화면(Playwright): 엔진이 내는 코드 꼴을 흉내 낸 합성 결과(TEMPORAL·CITATION·FACT 행, 같은 제목 AI 신호 4건, 인젝션 결과, release_gate)로
   ① 상단 .metric 3개, 출처 미확인 '2건'+'사건번호 형식 오류 1건 포함', 없앤 문구·배포 판정 사유 없음, eyebrow 없음, 빈 projectMeta 숨김, 사이드바 '미지정' 없음, 상단 코드 0
   ② 사건번호·기준일 입력 시 projectMeta = '2026가합1 · 적용법령 기준 2025-01-02'
   ③ AI 탭: 'AI 작성 참고 신호 문구' 묶음 1개·번호 근거 4개·'(4건)', 인젝션 한 줄, 안내 배너 없음, 카드 안 코드 0
   ④ 출처·법리 탭 표: 코드 0, '[RAG참고자료]'·'구속력 없음' 없음, 셀 밖으로 나간 배지 0, 표 위 범례 있음
   ⑤ 긴 의심 사유: '…' 없음, 전문이 DOM에 있음, '더보기'↔'접기'
   ⑥ 검색창·HIGH 배너 없음, 미확인 범위 카드 '미확인 범위 2건'·'인용 1'·'참고자료 1'
 - API: /api/finding-categories의 names가 ADVERSARIAL_FINDING_TYPES 16종 전부를 한글로 담음(기존 categories·tabs·counts 단언은 그대로).
 - 단위: _readable_source_message(영문 → 한국어, 모르는 문장 그대로), argument_validity_verifier.py에 '{noun}을(를)'·'{noun}이(가)' 없음, to_xlsx 요약 시트에 배포 판정 다섯 행 없음.
 - 고치기 전 코드(e57855f)에서는 화면·단위 9건 중 8건이 실패하고 대조 1건(②)은 통과한다(평가 측 확인). API 시험은 names가 없어 실패한다.

5. 평가 측 사전 검증(평가 측 재실행, 사본 v1ui = e57855f + TK-155·156, SQLite, LV_ALLOW_NETWORK=0)
 - 화면: case9 0.19.0 온라인 결과(run_dfde0992367c475f)로 실제 진입점(index.html)을 그려 캡처(전·후 4장씩). 영문 코드 꼴(대문자 XXX_YYY·소문자 xxx_yyy) 잔존 수 — 상단 요약, AI 탭 카드, 출처 탭 표, 법리 탭 표의 innerText, 개인정보 가림 토큰 제외:
   case9 전 4·18·12·8 → 후 0·0·0·0
   탐침 B 전 3·9·16·3 → 후 0·0·0·0 / 탐침 C 전 0·6·0·1 → 후 0 / 탐침 D(docx) 전 0·2·0·2 → 후 0
   (표 밖 범위 밖 RAG 처리 기록에는 남는다 — 2절)
   사전 검증 중 고친 빈틈: 모델 의견 문장 속 'reference_date', 탐침 B의 유니코드 신호 'ZERO_WIDTH', 스캐너 층 이름 'encoded_text'·'outline'이 처음 적용본에서 남아 표에 추가했다. 모델 문장은 실행마다 다른 식별자를 담을 수 있으므로 4절 ① 화면 시험으로 회귀를 막는다.
 - 카드 건수: 출처 미확인 9건 = 출처 탭 요약 '총 9건(공식 DB 미확인 9건)', 무리한 주장 9건 = 법리 탭 9행.
 - 의심 사유: 법리 탭 9행 모두 전문 유지(잘림 0). 같은 글 중복 6행은 한 번만 표시, 그중 3행은 더 긴 사유 전문으로 대체.
 - 관련 시험: 관련 시험 58파일(바뀐 문구·요소를 참조하는 시험 + 화면 시험) 첫 실행에서 13건 실패(전부 3절 옛 요구 단언) → 단언 변경 뒤 통과. 이어 전체 시험에서 보호 시험 test_f1_protected T4 1건 실패(app.js에 FindingType 이름 6개) → 1절 D6-1 ①처럼 서버 배정표로 옮겨 통과
 - 전체 시험: 사본 전체(e57855f + TK-155·156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 11,444건 통과·실패 0(건너뜀 11·예상 실패 24)
 - 은퇴·고정 세트: 은퇴 5세트(기준 e57855f, 제품 파일 9개 변경) 53.3/48.6/56.9/45.8/34.1·오탐 0 → 같음(후퇴 없음), 고정 dev 82.6·holdout 81.9·오탐 0(0.19.0과 같음). 단 오프라인 측정은 화면·AI 판별 경로를 재지 못한다
 - 미검증: 실제 운영 화면(브라우저 종류·글꼴 차이)에서의 4줄 줄임 위치, Word·PDF 보고서 모양(엑셀 요약 행 삭제만 시험으로 확인).

6. 제출물·수용 기준
 - PR 1개(제품: apps/web/index.html·static/app.js·static/styles.css, apps/api/routers/projects.py, packages/common/finding_category_map.py, packages/report_engine/exporters.py, packages/legal_engine/verifier.py·argument_validity_verifier.py; 시험: 4절 새 시험 + 3절 단언 변경). 보호 시험(tests/acceptance/)은 바꾸지 않는다.
 - 수용 기준: 4절 시험 통과, 필수 CI 성공, 은퇴·고정 세트 득점 하락·오탐 증가 0, 1절 대응표 각 행의 '확인' 충족.
 - 화면 수용 절차: PR에 case9(또는 같은 꼴 합성 결과) 실제 진입점 캡처 4장(상단·AI·출처·법리, 긴 문구 펼침 포함)과 1절 대응표를 붙인다 → 평가 측이 같은 캡처를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
 - 배포 후 사용자 확인: 온라인 case9에서 1절 대응표 항목 재확인.
```

### 2-38-2. TK-156

```
[TK-156(P2) AI 작성 판별은 늘 두 모델 + 엇갈리면 Gemini — 구현 지시]  기준: Steve_ACASiaLAW e57855f(0.19.0)  평가 측 사본: v1ui(커밋 전 작업 사본, 패치 docs/handoff/patches/TK-155_156_v1ui_on_e57855f.diff 중 router.py·test_efficient_llm_routing.py 부분)
PR 대상 브랜치: Steve_ACASiaLAW(main 아님). TK-155(화면)와 별도 PR로 낸다.

0. 사용자 원문(2026-11-13, 「프로그램 개선 소요 명세서 for V.1.0.0」 4번)과 결정
 원문: "4. AI 작성,보안 진단 - gemini 평가가 제외된 이유 분석 빛 해결방안 제시"
 결정 D4(11-13 "D1~D6 권고대로 진행"): 판별은 항상 두 모델(OpenAI·Anthropic), 엇갈리면 Gemini. 호출하지 않은 모델은 화면에 생략 사유 표시(화면 쪽은 TK-155 W3에 포함).

 원문 대응표(수용 기준)
 | 원문 | 대응 | 확인 |
 | gemini 평가가 제외된 이유 분석 | C1·C2(아래) | 판정서에 원인 기재 |
 | 해결방안 제시 | F1(두 모델 고정, 엇갈리면 세 번째), TK-155 W3 생략 사유 표시 | 4절 시험 + 온라인 반복 측정 |

1. 문제
- case9 0.19.0 온라인 결과에서 AI 작성 판별에 Gemini 의견이 없다. 사용자는 Gemini가 '제외'된 것으로 보았다.
- 같은 case9를 같은 조건으로 두 번 돌렸을 때 첫 모델 점수가 0.55·0.68로 갈렸고, 2회 중 1회는 판정이 유보됐다(0.19.0 run_2ed19999b01d47c0·run_dfde0992367c475f).

2. 원인(파일·줄은 e57855f 기준)
 C1. packages/llm_router/router.py 371행 `wanted = 1 if advisory else 2`: AI 작성 판별(advisory)은 OpenAI 한 모델로 시작한다.
 C2. 같은 파일 387~392행: 첫 응답이 needs_additional_review(AI 작성 긍정 등)이거나 metadata_ai_hint·표본 추출(llm_review_sample_percent)에 걸릴 때만 wanted=2로 올려 Anthropic을 부른다. 세 번째(Gemini)는 두 의견이 엇갈릴 때만 부른다(conflicting).
     → Gemini 제외는 결함이 아니라 효율 라우팅 설계다. 그러나 첫 모델 한 번의 응답이 '두 번째 의견을 부를지'와 최종 판정을 함께 가른다. 그래서 실행마다 판정이 흔들린다(1절 실측).

3. 고칠 것
 F1. router.py consult_all: advisory도 `wanted = 2`로 둔다. 387~392행의 '첫 응답 보고 올리기' 블록과, 그 때문에만 쓰던 import(sampled·needs_additional_review)를 지운다. 두 의견이 엇갈리면 세 번째를 부르는 기존 conflicting 경로는 그대로 둔다.
     - routing.py의 sampled·needs_additional_review 함수는 지우지 않는다(sampled는 test_efficient_llm_routing.py 163~164행이 직접 시험한다).
     - 법리 검토(is_argument_review)·일반 검토 경로는 바꾸지 않는다.
 F2. 비용: 판별 호출이 문서당 최소 1회 늘어난다(사용자 결정 D4에서 감수). LV_LLM_EFFICIENT_ROUTING 끄면 동작은 지금과 같다(세 모델 모두).

4. 확인 시험
 - tests/test_efficient_llm_routing.py: authorship 판별 parametrize의 ("UNCERTAIN", False, 0, 1)·("HUMAN_AUTHORED_LIKELY", False, 0, 1)을 기대 호출 수 2로 바꾼다. **이 두 단언은 옛 요구(단일 모델 시작)를 담은 시험이라 사용자 결정 D4로 평가 측이 바꾼 것이다(CLAUDE.md 2026-10-25 규칙).** 사본의 변경을 그대로 옮긴다.
 - 새 시험 test_authorship_disagreement_adds_third_provider: openai AI_PARTIAL_GENERATION / anthropic UNCERTAIN → 요청 3건(세 번째 호출).
 - 기존 시험 유지: tests/test_efficient_llm_routing.py 나머지, LLM 라우터·AI 판별 시험(test_ai_document_detector 등).

5. 평가 측 사전 검증(평가 측 재실행, 사본 v1ui = e57855f + TK-155·156 변경, SQLite, LV_ALLOW_NETWORK=0)
 - test_efficient_llm_routing.py 47건 통과(단언 변경 2건·새 시험 1건 포함).
 - 관련·전체 시험 결과: 사본 전체(e57855f + TK-155·156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 11,444건 통과·실패 0(건너뜀 11·예상 실패 24)
 - 은퇴·고정 세트: 은퇴 5세트(기준 e57855f, 제품 파일 9개 변경) 53.3/48.6/56.9/45.8/34.1·오탐 0 → 같음(후퇴 없음), 고정 dev 82.6·holdout 81.9·오탐 0(0.19.0과 같음). 단 오프라인 측정은 화면·AI 판별 경로를 재지 못한다
 - 미검증: 실제 모델 호출에서의 판정 안정성(온라인 필요). 오프라인 측정은 AI 작성 판별을 재지 못한다.

6. 제출물·수용 기준
 - PR 1개(제품: router.py, 시험: test_efficient_llm_routing.py — 단언 2건 변경은 평가 측 승인분, 새 시험 1건).
 - 수용 기준: 4절 시험 통과, 필수 CI 성공, 은퇴·고정 세트 변화 0.
 - 배포 후 사용자 측정(수용 조건): 온라인 case9를 같은 조건으로 3회 이상 실행해 ① 매 실행 모델별 판정이 2개 이상, ② 엇갈린 실행에는 Gemini 의견이 있음, ③ 판정 유보 비율이 0.19.0(2회 중 1회)보다 늘지 않음을 확인한다.
```

### 2-38-3. 사용자 결정(11-13 2차): 시험 단언 변경 승인, 범위 밖 3건 포함
- 원문: "1. 시험 단언 변경 승인 2. 범위 밖 3건 이번 릴리스 포함 *향후에도 최초에 의도했던 기능 개선, 오류 보완 등은 해당 릴리스에 포함하는 것이 원칙"
- 반영: TK-155에 R1(참고문헌 처리 기록)·R2(Word·PDF 보고서)·R3(AI 탭 배지)과 표 단일화(packages/common/display_text.py)를 더했다. 원칙은 CLAUDE.md·AGENT_ROLES에 기록.
- 갱신된 TK-155 지시 전문(2-38-1을 대체):

```
[TK-155(P2) 화면·보고서 정리 — 「프로그램 개선 소요 명세서 for V.1.0.0」 1~3·5~7번 + D6 — 구현 지시]
기준: Steve_ACASiaLAW e57855f(0.19.0)  평가 측 사본: v1ui(패치 docs/handoff/patches/TK-155_156_v1ui_on_e57855f.diff — router.py·test_efficient_llm_routing.py 부분은 TK-156)
PR 대상 브랜치: Steve_ACASiaLAW(main 아님). 버전: 0.20.0(changed·removed). 화면 PR이라 **사용자 확인 뒤 수용**한다(CLAUDE.md 2026-10-25).

0. 사용자 원문과 결정
 원문 전문은 docs/handoff/V1_0_0_UI_IMPROVEMENT_PLAN_20261113.md 부록 A에 그대로 있다(이 티켓의 원문). 결정(11-13 "D1~D6 권고대로 진행"):
 D1 '확인 전 항목' → 탭 제목 옆 '검토 결정 대기 n'으로 이동 / D2 '진행 상태' → 카드 삭제, 완료가 아닐 때만 한 줄 안내(사유 보기)
 D3 배포 판정 → 화면 패널·엑셀 요약 행 모두 삭제(결과 JSON scores.release_gate는 유지) / D5 참고문헌 표기 → 셀 반복 삭제, 표 위 범례 한 줄
 D6 명세 밖 같은 성격 3건 포함: 인젝션 결과의 영문 코드, 영문 오류 문장, '을(를)' 조사
 사용자 결정(11-13 2차, 원문): "1. 시험 단언 변경 승인 2. 범위 밖 3건 이번 릴리스 포함 *향후에도 최초에 의도했던 기능 개선, 오류 보완 등은 해당 릴리스에 포함하는 것이 원칙"
  → 3절 시험 단언 변경은 승인됨. 사전 검증에서 범위 밖으로 두었던 3건(R1 참고문헌 처리 기록, R2 Word·PDF 보고서, R3 AI 탭 배지)을 1절에 넣었다.

1. 원문 문장별 대응표(수용 기준 — 줄 번호는 e57855f)
 | 원문 | 현행 위치·원인 | 고칠 것 | 확인 |
 | 1 '법률문서 검토' 삭제 | index.html 7행 span.eyebrow | 지운다 | 캡처 01 |
 | 1-1 미지정 문구 삭제, 입력값만 표시 | app.js 799행 projectMeta('사건번호 미지정'·'적용법령 기준일 미지정'), 748행 사이드바 | 값 있는 것만 ' · '로 잇고, 하나도 없으면 projectMeta를 hidden. 사이드바는 [사건번호, '자료 n개'] | 캡처 01, 값 있는 프로젝트 캡처 |
 | 1-3 8개 → 'AI 작성 진단'(현행 표기)·'출처 미확인 인용 n건'·'법률적으로 무리한 주장 n건' | app.js 1047~1116 renderSummary 8칸 | 3칸. 출처 미확인 = 기존 '성립 불가'+'공식 DB 미확인' 합(1029~1044행 계산 그대로), 성립 불가가 있으면 작은 글 '사건번호 형식 오류 n건 포함'. 무리한 주장 = '법률적으로 무리한 주장' 탭 행 수(renderFindings의 3단 분류 수, 필터와 무관). 카드를 누르면 그 탭으로 이동. styles.css 357행 .summary 4칸 → 3칸, 좁은 화면(967행) 1칸 | 캡처 01: 9건·9건이 각 탭 행 수와 같음 |
 | 1-3-1 '검토에 포함' 삭제 | 1052행 | 지운다 | 캡처 01 |
 | 1-3-2 '배포 가능 상태' 삭제 | 1053행 | 지운다(D3) | 캡처 01 |
 | 1-3-3 '검증 위험 지수' 삭제 | 1054행 | 지운다 | 캡처 01 |
 | 1-3-4 성립 불가·공식DB 미확인 통합 | 1056~1057행 | 위 '출처 미확인 인용' 1칸 | 캡처 01 |
 | 1-3-5 '확인 전 항목' | 1058행 | D1: 카드 삭제. '출처가 확인되지 않는 항목'·'법률적으로 무리한 주장' 탭 h2 옆 배지 '검토 결정 대기 n'(그 탭 행에 묶인 결과 중 review_status NEEDS_REVIEW 수, 0이면 숨김). 배지를 누르면 기존 explainReviewPending 설명 | 캡처 03·04 |
 | 1-3-6 '진행상태' 통합 | 1059행 | D2: 카드 삭제. 실행 상태가 PARTIAL_COMPLETED·FAILED·CANCELLED일 때만 카드 아래 한 줄 '<상태>: … [사유 보기]'(기존 explainRunStatus). 진행 중은 기존 진행 막대 | 캡처 01 |
 | 2 배포차단 사유 중복이면 삭제 | 1093~1112 renderGateReasons, 사유 문장 gate.py 216~263 | D3: 화면 패널과 GATE_LABELS 삭제. packages/report_engine/exporters.py 179~188행 엑셀 요약의 배포가능 상태·검증위험 지수·지수 성격·차단 사유·사람 검토 사유 행 삭제. gate.py·결과 JSON은 그대로 | 캡처 01, 엑셀 요약 시트 |
 | 2-1 (남길 경우) 쉬운 말 | — | D3로 해당 없음 | — |
 | 3 '작성주체 확률이 아니라 …' 삭제 | gate.py 137행 → 화면 gate-note, 엑셀 '지수 성격' | 화면·엑셀에서 빠짐(위 2와 함께). gate.py 데이터는 유지 | 캡처 01, 엑셀 |
 | 5·5-2 'AI 작성 참고 신호 문구' 제목 반복 → 한 번 + 번호 목록 | app.js AI_DIAGNOSIS 결과를 결과마다 카드로 그림(ai_document_detector.py 890행이 근거별로 같은 제목 생성) | 화면에서 같은 (중요도, 제목) 결과를 카드 하나로 묶고 제목 옆 '(n건)', 근거는 ol 번호 목록. 결과 데이터 구조는 그대로 | 캡처 02 '(4건)' + 1~4 |
 | 5-1 안내문 삭제 | index.html 13행 #aiTabNoticeBanner | 지운다 | 캡처 02 |
 | 5-3 인젝션 경고 간소화 | app.js 1190행 | '프롬프트 인젝션 속임수 검증: AI 판단 왜곡 지시문 탐지 — 이 문서는 AI 검토에서 제외' 한 줄(격리 결과 해석에 필요한 마지막 구절은 계획 1절 5-3 판단대로 유지) | 캡처 02 |
 | 6-0 검색 삭제 | index.html 14행 #findingSearch, app.js renderFindings의 검색어 필터·3314행 이벤트 | 입력창과 검색어 필터 코드를 함께 지운다(중요도 필터는 유지) | 캡처 03 |
 | 6-1 HIGH 이상 안내 배너 삭제 | index.html 14행 #highSecurityAlertBanner, app.js 2510~2520 | 요소와 그 갱신 코드를 함께 지운다 | 캡처 03 |
 | 6-2·7-1 위치 칸 넘침 | styles.css 483~492 .badge white-space:nowrap(위치 칸 폭 10%), 행 종류 배지가 label()에 한글 이름이 없어 영문 코드 그대로(app.js 53행·2339~2341) | 표 셀 안 배지만 줄바꿈 허용(td .badge {white-space:normal; overflow-wrap:anywhere; max-width:100%}). labels에 CITATION '인용'·FACT '사실관계'·TEMPORAL '적용 시점'·REFERENCE '참고문헌' 추가 | 캡처 03·04: 배지가 칸 안 |
 | 6-3·7-2 셀 속 영문 코드 삭제 | 화면이 코드를 그대로 쓰는 곳(2430~2445 상태 코드 줄, reference_case_match) + 엔진 문장 속 코드('(RETROACTIVE_APPLICATION_ERROR)' 등) | ① 판정 배지와 겹치는 상태 코드 줄은 그리지 않는다(설명 문장 ai_generation_basis만). ② friendlyText에서 괄호 속 코드 '(XXX_YYY)'를 지우고, 남은 대문자 코드는 '코드→한글' 표(labels + CODE_WORDS)로 바꾼다. ③ 셀에 쓰는 문장(claim_text·verdict_label·설명·where)은 모두 friendlyText를 거친다. 표에 넣을 코드: OFFICIAL_NOT_FOUND·OFFICIAL_CONFIRMED·NOT_ASSESSED·NOT_CHECKED·NOT_MENTIONED·PENDING_REVIEW·UNVERIFIED_SCOPE·NOT_IN_REFERENCE·IN_REFERENCE·RETROACTIVE_APPLICATION_ERROR(사본의 한글 이름 그대로 옮겨도 된다) | 5절 '코드 잔존' 결과 |
 | 6-4·7-3 '[RAG참고자료]' 삭제 | 사실관계 행 설명 앞 접두 | friendlyText에서 '[RAG참고자료]' 접두를 지운다 | 캡처 04 |
 | 6-5·7-4 '참고문헌·구속력 없음, 공식 확인 아님' 셀 반복 삭제 | app.js 2194·2233·2348행 | D5: 셀 상자 제목은 '주요 참고문헌 대조', 위치 배지는 '참고문헌'. 대신 두 탭 표 위(#referenceStatus·#legalReferenceStatus 뒤)에 범례 한 줄 '주요 참고문헌은 등록된 검증 자료입니다. 판례·법령과 달리 법적 구속력은 없습니다.' | 캡처 03·04 |
 | 6-6 미확인 범위 가독성 | app.js 2806~2812 접힌 회색 글 | 경고색 테두리 카드(details.unverified-card): 요약줄에 '미확인 범위 n건 — 인용 a · 참고자료 b'(unverified_items.kind별: citation 인용, reference_library 참고자료, 그 밖 기타), 펼치면 지금 목록 | 캡처 03 |
 | 6-7·7-6 긴 셀 3~5줄 + 세부 보기 | 셀 전문 표시 | 문서 주장·설명·근거 문장에 .clamp(4줄, -webkit-line-clamp:4). 넘치면 바로 아래 '더보기' 버튼 → 같은 자리에서 펼침/'접기'. 별도 링크 대신 제자리 펼침(계획 1절 6-7 판단). 인쇄·보고서는 전문 | 캡처 03·04 '더보기' |
 | 7-5 '의심 사유' 잘림 | app.js 2476~2483: 첫 문장(20~120자) 또는 97자에서 자르고 '…' | 자르지 않고 .clamp + 더보기. 단 '확인 대상'과 같은 글이면(공백 무시, 한쪽이 다른 쪽을 포함) 한 번만 보이고, 사유가 더 길면 그 전문을 '확인 대상' 줄에 쓴다(정보 손실 0) | 캡처 04 |
 | D6-1 인젝션 결과의 영문 코드 | 제목 'META_INSTRUCTION 후보: ROLE_OVERRIDE — 경로: …', 설명 '분류=INSTRUCTION_LIKE', 'visible_text 위치', '(심각도 HIGH)', 검사한 층 encoded_text·outline | ① 코드 → 한글 표는 새 모듈 packages/common/display_text.py 하나에 둔다: FINDING_TYPE_NAMES(결과 유형 97종 전부, 모듈 끝 assert로 FindingType 전수 보장), CODE_WORDS(의도·분류·유니코드 신호·행 상태·참고문헌 처리 코드), FIELD_WORDS(소문자 식별자), WORD_NAMES(밑줄 없는 단어: 심각도·상태·인용 종류·참고 의견 관계), 함수 readable(text)·word(value)·korean_time(value). ② apps/api/routers/projects.py get_finding_categories 응답에 names·code_words·field_words·word_names를 싣는다. app.js friendlyText는 이 표(state.findingCategories)로 바꾸고 app.js에는 같은 표를 두지 않는다 — 보호 시험 tests/acceptance/test_f1_protected.py T4(app.js의 FindingType 이름 3개 이하)와 충돌하기 때문이다(사전 검증에서 확인). ③ 소문자 층 이름은 LAYER_NAMES 보강(scanner.scanned_paths가 내는 이름 전부). ④ 심각도는 label() | 캡처 02, API 시험 |
 | R1(범위 밖 → 포함) 참고문헌(RAG) 처리 기록의 코드 | app.js 1266~1380 referenceSection: 자료 상태(INDEXED_PARTIAL 등)·사유(REFERENCE_PARTIALLY_READ 등)·선정 사유·검토 사유·검색 사유를 코드 그대로, 조회 시각 ISO(2026-11-13T01:00:11.45…+00:00), 인증 방식 service_account | 사유·상태는 friendlyText/refWord(code_words), 조회·수정 시각은 koreanTime(한국 시각 'YYYY-MM-DD HH:MM'), 인증 방식은 서비스 계정·API 키·주입된 인증·없음, AI 참고 의견·맥락 검토 문장·후보 제목·출처 제목도 friendlyText. 코드 목록은 packages/rag_engine(library.py·extract.py·drive.py·relevance.py·review.py)이 실제로 내는 값이며, 문장이 정해진 것은 review_items.HUMAN_READABLE_UNVERIFIED_REASONS·화면 statuses와 같은 말 | 캡처 03(펼침), 화면 시험 |
 | R2(범위 밖 → 포함) Word·PDF 보고서의 코드 | docx_report.py 183행 'AI 진단' 칸 판정 코드, 50행 paragraph·77행 표 칸·156·263행 제목이 코드 그대로. pdf_report.py 85행 _escape, 209·222행 인용 상태, 441·522행 '근거 문구 대조 True/False', 185·196행 'CRITICAL·HIGH', 365행 'Severity 상한 MEDIUM…', 426행 'VERIFIED는'. rag_engine/review.py 783행 report_lines의 상태·사유·시각, reference_opinions.py 34행 관계(SUPPORTS 등), terminology.py REVIEW_NOTICE 'VERIFIED로' | 본문 글은 readable/word를 거친다(docx paragraph·표 칸·제목, pdf _escape, 인용 상태 칸, report_lines, 관계). 고정 문장은 한글로('2. 핵심 사항(심각도 매우 높음·높음)', "'확인됨'은 …", "심각도는 '보통'을 넘지 않고 근거 등급 D, 검증 상태 '확인 불가'로…", '근거 문구 대조 일치/불일치·미확인'). **기술 부록(docx json_lines, pdf _appendix_blocks)과 JSON·CSV·엑셀 기술부록은 코드 그대로 둔다**(감사 추적용 원자료) | 보고서 시험, 5절 잔존 수 |
 | R3(범위 밖 → 포함) 6-1 선택 항목 | (없음) | 'AI 작성·보안 진단' 탭 버튼에 높음 이상 건수: button.dataset.highCount + CSS ::after '높음 이상 n'(버튼 이름·접근성 이름은 그대로 — 기존 시험이 버튼 글자를 'AI 작성·보안 진단'으로 단언), title에 설명. 0건이면 표시 없음 | 캡처(탭 줄), 화면 시험 |
 | D6-2 영문 오류 문장 | packages/legal_engine/verifier.py 1237행 '공식 Source 조회…', 1261행 message가 'Multiple versions share the requested effective boundary' 등 영문 그대로 | 모듈 함수 _readable_source_message(message): packages.verification_engine.review_items.HUMAN_READABLE_UNVERIFIED_REASONS로 아는 문장은 한국어로 바꾸고 모르는 것은 그대로. 1261행 detail에 사용. '공식 Source' → '공식 출처' | 시험 + 캡처 03 |
 | D6-3 '을(를)'·'이(가)' | packages/legal_engine/argument_validity_verifier.py 639·662~663행 '{noun}을(를)'·'{noun}이(가)' | noun이 '법령'이면 을/이, '판례'면 를/가로 고른다 | 시험 |
 | (부수) AI 판별 생략 사유(D4 화면 쪽) | app.js modelOpinions | 의견이 2개 이상이고 Gemini를 부르지 않았으면 'Gemini: 두 모델 판정이 일치해 세 번째 의견은 묻지 않았습니다.'(판정이 엇갈렸는데 없으면 '이번 실행에서는 호출하지 않았습니다.') | 캡처 02 |
 | (부수) AI 탭 설명문의 필드 이름 | ai_document_detector.py 605~610 SCORE_DEFINITIONS 'ai_score'·'finding.confidence', 판정 근거 목록 'AI_PARTIAL_GENERATION로 최종 확정함' | 화면에서 friendlyText로 '점수'·'값'·'일부 AI 작성'. 엔진 문장은 바꾸지 않는다 | 캡처 02 |

2. 남겨 두는 것(근거)
 - 사용자 Drive 파일명(예: 밑줄이 든 영문 파일명), 개인정보 가림 토큰([PERSON_003] 등): 원래 이름·토큰이라 바꾸지 않는다.
 - 관리자 설정용 환경변수 이름(LV_KCI_KEY 등, '연결 키 미설정 / LV_KCI_KEY 환경변수 필요'): 관리자가 그 이름으로 설정해야 하므로 둔다.
 - 모델 의견 원문 속 단어(예: 모델이 쓴 'INSUFFICIENT에 가까운'): 모델 응답을 고쳐 쓰지 않는다.
 - 기술 부록·JSON·CSV·엑셀 기술부록의 코드(감사 추적용).

3. 기존 시험과의 충돌(평가 측이 사용자 승인으로 고칠 단언 — 구현 측은 사본 패치의 시험 변경을 그대로 옮긴다)
 사본에 적용한 뒤 관련 시험 58파일을 돌려 13건이 옛 요구 단언으로 실패했다(8파일). 모두 원문이 없애거나 바꾸라고 한 것을 확인하던 단언이다. 사본에서 아래처럼 고쳐 통과를 확인했다(평가 측 재실행). **사용자 승인 완료(11-13 "시험 단언 변경 승인")** — 구현 측은 패치의 시험 변경을 그대로 옮긴다(되돌리지 않는다).
 | 시험 | 옛 단언 | 새 단언(근거) |
 | test_f1_ai_security_tab_browser.py — test_ai_tab_renamed_and_notice_banner_visible | #aiTabNoticeBanner 보임 | 이름을 …_removed로, 배너 0개(5-1) |
 | 같은 파일 — test_high_security_alert_banner_visible_and_jumpable | HIGH 배너 보임·점프 | …_removed: 배너 0개, 탭 버튼으로 이동(6-1) |
 | test_f2_review_screen_browser.py — …_reason_truncation_and_location_display | 의심 사유 '…' 포함·120자 이하 | '…'로 끝나지 않음, .clamp, 더보기 누르면 .expanded(7-5) |
 | 같은 파일 — test_f2_filters_search_severity_review_status | #findingSearch 검색 동작 | #findingSearch 0개(6-0). 중요도 필터 단언 유지 |
 | test_frontend_gate.py — test_gate_reasons_are_shown_open_and_readable(2) | '배포 차단 — 사유 6건' 패널 | …_not_rendered: 카드 3개, 배포 판정 문구·사유 없음(D3) |
 | test_frontend_metric_explain.py — …_metrics_explain_themselves(2) | '확인 전 항목'·'진행 상태' 카드 클릭 | 카드 없음. 출처 탭 '검토 결정 대기 2' 배지 → '검토 결정 대기란' 대화상자(성격별 건수 단언 유지), 상단 안내 '사유 보기' → '진행 상태: 일부 미확인' 대화상자(원인별 단언 전부 유지)(D1·D2) |
 | test_frontend_summary_compact.py(3) | .metric 8개, '배포가능 상태'·'검증위험 지수' 보임 | 3개, 세 제목 보임, 없앤 다섯 제목 0개(1-3). 크기 단언 유지 |
 | test_tk61_layout_browser.py — test_tk61_security_finding_items_vertical_layout | 모든 .security-finding-item에 '> .link-button'·'> small' | AI 작성 진단 묶음은 '머리 위·번호 목록 아래'를 따로 확인, 위아래 배치 단언은 나머지 항목에 그대로(5-2) |
 | test_tk88_three_tier_review.py — test_frontend_app_js_classification_matches_specification | app.js에 '참고문헌(구속력 없음)' | app.js에 없음 + index.html 범례 '법적 구속력은 없습니다'(D5) |
 (TK-156의 test_efficient_llm_routing.py 단언 2건은 TK-156 지시에 적는다.)

4. 새 시험(구현 측이 추가)
 새 파일 tests/test_tk155_ui_cleanup.py — 평가 측 사본에 작성해 통과 확인. 패치의 파일을 그대로 옮겨도 된다(문장·사건번호·법령명은 모두 합성).
 - 화면(Playwright): 엔진이 내는 코드 꼴을 흉내 낸 합성 결과(TEMPORAL·CITATION·FACT 행, 같은 제목 AI 신호 4건, 인젝션 결과, release_gate)로
   ① 상단 .metric 3개, 출처 미확인 '2건'+'사건번호 형식 오류 1건 포함', 없앤 문구·배포 판정 사유 없음, eyebrow 없음, 빈 projectMeta 숨김, 사이드바 '미지정' 없음, 상단 코드 0
   ② 사건번호·기준일 입력 시 projectMeta = '2026가합1 · 적용법령 기준 2025-01-02'
   ③ AI 탭: 'AI 작성 참고 신호 문구' 묶음 1개·번호 근거 4개·'(4건)', 인젝션 한 줄, 안내 배너 없음, 카드 안 코드 0
   ④ 출처·법리 탭 표: 코드 0, '[RAG참고자료]'·'구속력 없음' 없음, 셀 밖으로 나간 배지 0, 표 위 범례 있음
   ⑤ 긴 의심 사유: '…' 없음, 전문이 DOM에 있음, '더보기'↔'접기'
   ⑥ 검색창·HIGH 배너 없음, 미확인 범위 카드 '미확인 범위 2건'·'인용 1'·'참고자료 1'
 - 화면(추가): ⑦ 참고문헌 처리 기록(펼침)에 코드 0, '조회 2026-11-13 10:00', '서비스 계정'·'일부 색인'·'지시문 의심으로 보안 격리', 'None' 없음 ⑧ AI 탭 버튼 data-high-count="1"·::after '높음 이상 1'·버튼 글자 'AI 작성·보안 진단' 그대로
 - API: /api/finding-categories의 names가 FindingType 97종 전부를 한글로 담고 code_words·field_words가 있음(기존 categories·tabs·counts 단언은 그대로).
 - 보고서: 같은 합성 결과로 운영과 같은 보기(apps/api/routers/reports.py _RunView·_DocumentView·_FindingView)를 만들어 Word·PDF 본문에 코드 0, 참고문헌 처리 기록이 한글('일부 색인'·'지시문 의심으로 보안 격리').
 - 단위(추가): readable이 화면 규칙과 같음(유형·의도·층 이름 변환, 괄호 코드·[RAG참고자료] 삭제, [PERSON_003] 보존), word('HIGH')='높음'·word('INDEXED')='색인 완료'·word('CONTRADICTS')='불부합'.
 - 단위: _readable_source_message(영문 → 한국어, 모르는 문장 그대로), argument_validity_verifier.py에 '{noun}을(를)'·'{noun}이(가)' 없음, to_xlsx 요약 시트에 배포 판정 다섯 행 없음.
 - 고치기 전 코드(e57855f)에서는 packages/common/display_text가 없어 이 파일 전체가 수집 단계에서 실패한다(평가 측 확인). 모듈 없이 돌린 1차 확인에서는 화면·단위 9건 중 8건 실패, 대조 1건(②) 통과였다.

5. 평가 측 사전 검증(평가 측 재실행, 사본 v1ui = e57855f + TK-155·156, SQLite, LV_ALLOW_NETWORK=0)
 - 화면: case9 0.19.0 온라인 결과(run_dfde0992367c475f)로 실제 진입점(index.html)을 그려 캡처(전·후 4장씩). 영문 코드 꼴(대문자 XXX_YYY·소문자 xxx_yyy) 잔존 수 — 상단 요약, AI 탭 카드, 출처 탭 표, 법리 탭 표의 innerText, 개인정보 가림 토큰 제외:
   case9 전 4·18·12·8 → 후 0·0·0·0
   탐침 B 전 3·9·16·3 → 후 0·0·0·0 / 탐침 C 전 0·6·0·1 → 후 0 / 탐침 D(docx) 전 0·2·0·2 → 후 0
   참고문헌 처리 기록까지 포함한 네 탭 전체(innerText, 펼침, 운영 배정표 API 함수 응답 그대로): case9·B·C·D 모두 사용자 Drive 파일명 1건만 남음(2절)
   측정 정정: 표를 서버로 옮긴 직후 캡처 도구가 배정표를 흉내 내며 code_words를 빠뜨려 한때 잘못 쟀다(운영 API 함수를 그대로 쓰게 고쳐 다시 잼). 그 과정에서 영문 낱말 치환이 코드 일부를 바꾸는 결함을 찾아 고쳤다(경계 조건).
 - Word·PDF 보고서(운영과 같은 _RunView로 생성, 기술 부록 제외 형식): 영문 코드 꼴 잔존 Word/PDF
   case9 115/138 → 2/2, 탐침 B 96/118 → 2/2, 탐침 C 72/80 → 2/2 (남은 2 = Drive 파일명 1·관리자 환경변수 이름 1, 2절). 밑줄 없는 단어 코드(HIGH·CONTRADICTED·True 등)도 0(모델 의견 원문 속 단어 제외)
   사전 검증 중 고친 빈틈: 모델 의견 문장 속 'reference_date', 탐침 B의 유니코드 신호 'ZERO_WIDTH', 스캐너 층 이름 'encoded_text'·'outline'이 처음 적용본에서 남아 표에 추가했다. 보고서는 인용 상태 칸이 '상태+단계 설명' 여러 줄이라 칸 전체 대조로는 안 바뀌어 상태 부분만 word()로 바꿨다. 화면 '유형별' 집계(검토 결정 대기 설명)도 유형 코드를 그대로 쓰던 것을 names로 해소. 모델 문장은 실행마다 다른 식별자를 담을 수 있으므로 4절 ① 화면 시험으로 회귀를 막는다.
 - 카드 건수: 출처 미확인 9건 = 출처 탭 요약 '총 9건(공식 DB 미확인 9건)', 무리한 주장 9건 = 법리 탭 9행.
 - 의심 사유: 법리 탭 9행 모두 전문 유지(잘림 0). 같은 글 중복 6행은 한 번만 표시, 그중 3행은 더 긴 사유 전문으로 대체.
 - 관련 시험: 관련 시험 58파일(바뀐 문구·요소를 참조하는 시험 + 화면 시험) 첫 실행에서 13건 실패(전부 3절 옛 요구 단언) → 단언 변경 뒤 통과. 이어 전체 시험에서 보호 시험 test_f1_protected T4 1건 실패(app.js에 FindingType 이름 6개) → 1절 D6-1 ①처럼 서버 배정표로 옮겨 통과
 - 전체 시험(범위 밖 3건 포함 최종본): 사본 19f2293(e57855f + TK-155 전체·TK-156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 전체 11,449건 통과·실패 0(건너뜀 11·예상 실패 24). 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0 → 같음(후퇴 없음), 고정 dev 82.6·holdout 81.9·오탐 0(precheck_pr 성적표)
 - 은퇴·고정 세트: 은퇴 5세트(기준 e57855f, 제품 파일 9개 변경) 53.3/48.6/56.9/45.8/34.1·오탐 0 → 같음(후퇴 없음), 고정 dev 82.6·holdout 81.9·오탐 0(0.19.0과 같음). 단 오프라인 측정은 화면·AI 판별 경로를 재지 못한다
 - 평가 측 사전 검증의 빈틈(11-13 #271 판정에서 확인): 첫 지시를 낼 때 scripts/precheck_pr.py를 돌리지 않아 ① 평가 세트 문구 대조 2건(argument_validity_verifier 설명문)과 ② 시험 삭제 게이트(시험 함수 이름 변경 = 삭제로 셈)를 지시문에서 놓쳤다. 구현 측이 #271에서 뜻이 같은 표현·옛 함수 이름 유지로 해결했고 사본도 같게 고쳤다. 범위 밖 3건을 넣으며 유형 이름 4개도 같은 대조에 걸려 바꿨다(사실관계 불일치·날짜 선후 불일치·프롬프트 속임수 의심·증거 날짜 선후 뒤바뀜). 이후 지시는 precheck_pr까지 돌려 낸다.
 - 미검증: 실제 운영 화면(브라우저 종류·글꼴 차이)에서의 4줄 줄임 위치, Word·PDF 보고서 모양(엑셀 요약 행 삭제만 시험으로 확인).

6. 제출물·수용 기준
 - PR 1개(제품: apps/web/index.html·static/app.js·static/styles.css, apps/api/routers/projects.py, 새 packages/common/display_text.py, packages/common/terminology.py(REVIEW_NOTICE), packages/report_engine/exporters.py·docx_report.py·pdf_report.py·reference_opinions.py, packages/rag_engine/review.py(report_lines), packages/legal_engine/verifier.py·argument_validity_verifier.py; 시험: 4절 새 시험 + 3절 단언 변경). 보호 시험(tests/acceptance/)은 바꾸지 않는다.
 - 수용 기준: 4절 시험 통과, 필수 CI 성공, 은퇴·고정 세트 득점 하락·오탐 증가 0, 1절 대응표 각 행의 '확인' 충족.
 - 화면 수용 절차: PR에 case9(또는 같은 꼴 합성 결과) 실제 진입점 캡처 4장(상단·AI·출처·법리, 긴 문구·참고문헌 처리 기록 펼침 포함)과 Word·PDF 보고서 각 1부, 1절 대응표를 붙인다 → 평가 측이 같은 캡처를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
 - 배포 후 사용자 확인: 온라인 case9에서 1절 대응표 항목 재확인.
```

### 2-38-4. #270(TK-156) 판정 — 수용 (11-13, head `d6840e0`)
- 평가 측 사본과 diff 0(router.py·test_efficient_llm_routing.py). 필수 CI 전부 성공(CI 결과 인용). 평가 측 재실행: 사본 전체 시험 11,449 통과·실패 0, 은퇴·고정 세트 변화 0.
- 병합 가능(사용자 승인). 최종 수용 조건: 배포 뒤 온라인 case9 같은 조건 3회 이상(지시 6절).

### 2-38-5. #271(TK-155) 판정 — 1차 범위 수용 가능, 보완 1(범위 밖 3건 포함) (11-13, head `1f98dda`)
- 1차 지시 범위는 사본과 같다(구현 측의 평가 세트 문구 회피 2건·시험 함수 이름 유지는 타당 — 평가 측 사전 검증이 precheck_pr을 빠뜨린 탓, 사본도 같게 고침). 필수 CI 전부 성공(인용).
- 보완 지시(전문):

```
[#271(TK-155) 보완 지시 1 — 범위 밖 3건 포함(사용자 결정) + 코드→한글 표 단일화]  평가한 SHA: 1f98dda  평가 측 사본: c4953f4(e57855f 기준)
보완 패치: docs/handoff/patches/TK-155_supplement_on_pr271_1f98dda.diff (#271 head 1f98dda → 평가 측 사본 차이 전부, git apply 가능)

0. 판정 요약(평가 측 재실행 + CI 결과 인용)
 - 1차 지시 범위(원문 1~3·5~7, D1~D6)는 수용 가능: 평가 측 사본과 차이 없음(평가 세트 문구 회피 2건·시험 함수 이름 유지 포함 — 사본도 같게 고쳤다). 필수 CI 전부 성공(인용).
 - 다만 PR을 낸 뒤 사용자 결정이 추가됐다. 원문: "2. 범위 밖 3건 이번 릴리스 포함 *향후에도 최초에 의도했던 기능 개선, 오류 보완 등은 해당 릴리스에 포함하는 것이 원칙". 그래서 이 PR에 아래 R1~R3을 더한다(같은 PR에서 화면 확인을 한 번에 받기 위해).

1. 문제와 원인(줄 번호는 1f98dda 기준)
 R1. 참고문헌(RAG) 처리 기록(출처 탭 표 위 '주요 참고문헌 검토 결과(RAG)')이 코드 그대로다.
     - app.js referenceSection: 자료 상태(INDEXED_PARTIAL·PARSE_FAILED…)·사유(REFERENCE_PARTIALLY_READ·NAME_PATH_NOT_RELATED…)·선정 사유(RELEVANT_REFERENCE_FOUND)·검토 사유(EXACT_QUOTES_CHECKED_…)·검색 사유, 조회 시각 ISO('2026-11-13T01:00:11.45…+00:00'), 인증 방식 'service_account'.
     - case9 실측: 이 기록에만 코드 70개.
 R2. Word·PDF 보고서 본문이 코드 그대로다.
     - case9 실측: Word 115개, PDF 138개(탐침 B 96/118, C 72/80).
     - 출처 ① 'AI 진단' 칸 판정 코드(docx_report.py 'v = det.get("verdict")').
     - 출처 ② 결과 유형 칸(FindingType 97종, PDF '유형').
     - 출처 ③ 인용 상태 칸(CONTRADICTED·PARTIALLY_VERIFIED…).
     - 출처 ④ rag_engine/review.py report_lines의 상태·사유·ISO 시각.
     - 출처 ⑤ reference_opinions.py 관계(SUPPORTS·CONTRADICTS…).
     - 출처 ⑥ 고정 문장('핵심 CRITICAL·HIGH', 'VERIFIED는', 'Severity 상한 MEDIUM…', '근거 문구 대조 True/False', terminology.REVIEW_NOTICE 'VERIFIED로').
 R3. 계획 6-1 선택 항목: HIGH 배너를 없앴으므로 'AI 작성·보안 진단' 탭 버튼에 높음 이상 건수를 단다.
 R4(구조). 화면 표(CODE_WORDS·FIELD_WORDS, finding_category_map의 16종 이름)를 보고서도 써야 한다. JS·Python에 같은 표를 두 벌 두면 어긋난다.
     → 표를 Python 한 곳에 두고 화면은 API로 받는다. 보호 시험 F1 T4(app.js FindingType 이름 3개 이하)도 그대로 지킨다.

2. 고칠 것(보완 패치와 같은 구조)
 F1(R4). 새 모듈 packages/common/display_text.py
     - FINDING_TYPE_NAMES(97종 전부. 모듈 끝 assert로 FindingType 전수 보장)
     - CODE_WORDS(의도·분류·유니코드 신호·행 상태·참고문헌 처리 코드 — rag_engine이 실제로 내는 값)
     - FIELD_WORDS(소문자 식별자)
     - WORD_NAMES(밑줄 없는 단어: 심각도·상태·인용 종류·참고 의견 관계 — 화면 labels·REFERENCE_RELATIONS와 같은 말)
     - 함수 readable(text)·word(value)·korean_time(value). readable은 app.js friendlyText와 같은 규칙이다.
     - finding_category_map.py의 FINDING_TYPE_SCREEN_NAMES는 지운다.
     - projects.py get_finding_categories에 names·code_words·field_words·word_names를 싣는다.
     - app.js의 CODE_WORDS·FIELD_WORDS 상수를 지우고, friendlyText·refWord가 state.findingCategories 표를 쓴다.
     - 유형 이름 4개는 평가 세트 문구 대조에 걸려 바꿨다: 사실관계 불일치·날짜 선후 불일치·프롬프트 속임수 의심·증거 날짜 선후 뒤바뀜.
 F2(R1). app.js referenceSection
     - 상태·사유·선정·검토·검색 사유: refWord / friendlyText
     - 조회·수정 시각: koreanTime(한국 시각 'YYYY-MM-DD HH:MM')
     - 인증 방식: CREDENTIAL_MODES(서비스 계정·API 키·주입된 인증·없음)
     - AI 참고 의견·맥락 검토 문장·후보·출처 제목: friendlyText
 F3(R2). 보고서
     - docx_report.py: paragraph(raw=False)가 readable을 거친다. 표 칸은 word, 제목은 readable. 기술 부록(json_lines)은 raw=True.
     - pdf_report.py: _escape가 word를 거친다(_appendix_blocks는 그대로). 인용 상태 칸은 word(status)+단계 설명. '근거 문구 대조 일치/불일치·미확인'. 고정 문장 한글화.
     - rag_engine/review.py report_lines: word·korean_time 사용, read_pages None → 0.
     - reference_opinions.py: 관계에 word.
     - terminology.py REVIEW_NOTICE: "'확인됨'으로".
     - JSON·CSV·엑셀 기술부록의 코드는 그대로 둔다(감사 추적용).
 F5. 영문 낱말 치환(UNVERIFIED·QUARANTINED·UNCERTAIN·Source 등)은 앞뒤가 영문·숫자·밑줄이 아닐 때만 한다(app.js friendlyText, display_text.readable). 경계 없이 바꾸면 표에 없는 코드 안까지 바뀐다(사전 검증에서 'REFERENCE_QUARANTINED' → 'REFERENCE_안전 검토 필요' 깨짐 확인).
 F4(R3). renderFindings
     - 높음 이상 AI·보안 결과 수를 탭 버튼 data-high-count에 둔다.
     - styles.css .tabs button[data-high-count]::after { content: "높음 이상 " attr(data-high-count) … }
     - 버튼 글자(접근성 이름)는 그대로다. 기존 시험이 'AI 작성·보안 진단'으로 단언한다.

3. 확인 시험
 - tests/test_tk155_ui_cleanup.py 보강(패치 그대로):
   · 참고문헌 처리 기록 코드 0·한국 시각·'서비스 계정'·'None' 없음
   · 탭 버튼 '높음 이상 1'·버튼 글자 유지
   · readable 규칙
   · Word·PDF 본문 코드 0(운영과 같은 _RunView)
   · API names 97종·code_words
 - 기존 시험 단언 변경 4건(사용자 승인 대상 — 승인 전에는 병합하지 않음):
   · test_drive_rag_relevance.py::test_web_shows_drive_health_selection_and_duplicates: '인증 api_key' → '인증 API 키'
   · test_evidence_rag_review.py::test_reference_issues_are_listed_once_in_export: 'REFERENCE_PARTIALLY_READ' 1회 → '일부 쪽만 읽음' 1회 + 코드 없음
   · test_report_completion.py 2건(test_cross_format_labels_appendix_and_docx_zip·test_summary_report_keeps_review_content_and_moves_the_full_record_to_json): 'UNVERIFIED' in text → _unverified_shown(text)(엑셀·JSON은 코드, Word·PDF는 한글 중 하나). FINAL·스냅숏 해시·출처 URL 단언은 그대로.
 - 게이트(평가 측 재실행, 사본 c4953f4): 평가 세트 문구 대조 '의심 없음', check_test_edits '삭제·표시 변경 없음'(assert 감소 경고 1건 = 승인된 test_frontend_gate 변경), check_hardcoding_diff 통과, 보호 경로 변경 없음.

4. 평가 측 사전 검증(평가 측 재실행)
 - 화면(운영 /api/finding-categories 함수 응답 그대로, case9·탐침 B·C·D, 네 탭 전체 innerText, 참고문헌 처리 기록 펼침): 영문 코드 꼴은 사용자 Drive 파일명 1건만 남음(고치기 전 출처 탭 85·87·69·69). 밑줄 없는 단어 코드(INDEXED 등) 11 → 0.
 - 보고서 Word/PDF 코드 잔존: case9 115/138 → 2/2, B 96/118 → 2/2, C 72/80 → 2/2. 남은 2건은 Drive 파일명과 관리자 환경변수 이름(LV_KCI_KEY)이며, 남기는 근거는 TK-155 2절이다.
 - 전체 시험·은퇴 세트: 사본 19f2293(e57855f + TK-155 전체·TK-156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 전체 11,449건 통과·실패 0(사본 19f2293. 그 뒤 F5 경계 수정 c4953f4는 관련 시험 14파일 재실행 통과)(건너뜀 11·예상 실패 24). 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0 → 같음(후퇴 없음), 고정 dev 82.6·holdout 81.9·오탐 0(precheck_pr 성적표)
 - 미검증: 실제 운영 브라우저의 글꼴 차이, Word 프로그램에서 연 모양(텍스트 추출로만 확인).

5. 제출물·수용 기준
 - #271에 커밋 추가(보완 패치 적용). 대상 브랜치 Steve_ACASiaLAW 그대로.
 - 수용 기준: 3절 시험 통과, 필수 CI 성공, precheck_pr의 평가 세트 문구 대조 통과, 은퇴·고정 세트 변화 0.
 - 화면 PR 절차: 평가 측이 최종 head로 캡처(상단·AI·출처(참고문헌 처리 기록 펼침)·법리)와 Word·PDF 각 1부를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
```

### 2-38-6. 사용자 '#270 병합, 시험 단언 변경 4건 승인' (11-13)
- #270 병합 → Steve `f19ec47`(expectedHeadSha `d6840e0`). TK-156 최종 수용 조건(온라인 case9 3회)은 0.20.0 배포 뒤.
- #271 보완 1의 시험 단언 변경 4건 승인. 전달용 보완 지시(승인 반영판, 2-38-5를 대체):

```
[#271(TK-155) 보완 지시 1 — 범위 밖 3건 포함(사용자 결정) + 코드→한글 표 단일화]  평가한 SHA: 1f98dda  평가 측 사본: c4953f4(e57855f 기준)
보완 패치: docs/handoff/patches/TK-155_supplement_on_pr271_1f98dda.diff (#271 head 1f98dda → 평가 측 사본 차이 전부, git apply 가능)

0. 판정 요약(평가 측 재실행 + CI 결과 인용)
 - 1차 지시 범위(원문 1~3·5~7, D1~D6)는 수용 가능: 평가 측 사본과 차이 없음(평가 세트 문구 회피 2건·시험 함수 이름 유지 포함 — 사본도 같게 고쳤다). 필수 CI 전부 성공(인용).
 - 다만 PR을 낸 뒤 사용자 결정이 추가됐다. 원문: "2. 범위 밖 3건 이번 릴리스 포함 *향후에도 최초에 의도했던 기능 개선, 오류 보완 등은 해당 릴리스에 포함하는 것이 원칙". 그래서 이 PR에 아래 R1~R3을 더한다(같은 PR에서 화면 확인을 한 번에 받기 위해).

1. 문제와 원인(줄 번호는 1f98dda 기준)
 R1. 참고문헌(RAG) 처리 기록(출처 탭 표 위 '주요 참고문헌 검토 결과(RAG)')이 코드 그대로다.
     - app.js referenceSection: 자료 상태(INDEXED_PARTIAL·PARSE_FAILED…)·사유(REFERENCE_PARTIALLY_READ·NAME_PATH_NOT_RELATED…)·선정 사유(RELEVANT_REFERENCE_FOUND)·검토 사유(EXACT_QUOTES_CHECKED_…)·검색 사유, 조회 시각 ISO('2026-11-13T01:00:11.45…+00:00'), 인증 방식 'service_account'.
     - case9 실측: 이 기록에만 코드 70개.
 R2. Word·PDF 보고서 본문이 코드 그대로다.
     - case9 실측: Word 115개, PDF 138개(탐침 B 96/118, C 72/80).
     - 출처 ① 'AI 진단' 칸 판정 코드(docx_report.py 'v = det.get("verdict")').
     - 출처 ② 결과 유형 칸(FindingType 97종, PDF '유형').
     - 출처 ③ 인용 상태 칸(CONTRADICTED·PARTIALLY_VERIFIED…).
     - 출처 ④ rag_engine/review.py report_lines의 상태·사유·ISO 시각.
     - 출처 ⑤ reference_opinions.py 관계(SUPPORTS·CONTRADICTS…).
     - 출처 ⑥ 고정 문장('핵심 CRITICAL·HIGH', 'VERIFIED는', 'Severity 상한 MEDIUM…', '근거 문구 대조 True/False', terminology.REVIEW_NOTICE 'VERIFIED로').
 R3. 계획 6-1 선택 항목: HIGH 배너를 없앴으므로 'AI 작성·보안 진단' 탭 버튼에 높음 이상 건수를 단다.
 R4(구조). 화면 표(CODE_WORDS·FIELD_WORDS, finding_category_map의 16종 이름)를 보고서도 써야 한다. JS·Python에 같은 표를 두 벌 두면 어긋난다.
     → 표를 Python 한 곳에 두고 화면은 API로 받는다. 보호 시험 F1 T4(app.js FindingType 이름 3개 이하)도 그대로 지킨다.

2. 고칠 것(보완 패치와 같은 구조)
 F1(R4). 새 모듈 packages/common/display_text.py
     - FINDING_TYPE_NAMES(97종 전부. 모듈 끝 assert로 FindingType 전수 보장)
     - CODE_WORDS(의도·분류·유니코드 신호·행 상태·참고문헌 처리 코드 — rag_engine이 실제로 내는 값)
     - FIELD_WORDS(소문자 식별자)
     - WORD_NAMES(밑줄 없는 단어: 심각도·상태·인용 종류·참고 의견 관계 — 화면 labels·REFERENCE_RELATIONS와 같은 말)
     - 함수 readable(text)·word(value)·korean_time(value). readable은 app.js friendlyText와 같은 규칙이다.
     - finding_category_map.py의 FINDING_TYPE_SCREEN_NAMES는 지운다.
     - projects.py get_finding_categories에 names·code_words·field_words·word_names를 싣는다.
     - app.js의 CODE_WORDS·FIELD_WORDS 상수를 지우고, friendlyText·refWord가 state.findingCategories 표를 쓴다.
     - 유형 이름 4개는 평가 세트 문구 대조에 걸려 바꿨다: 사실관계 불일치·날짜 선후 불일치·프롬프트 속임수 의심·증거 날짜 선후 뒤바뀜.
 F2(R1). app.js referenceSection
     - 상태·사유·선정·검토·검색 사유: refWord / friendlyText
     - 조회·수정 시각: koreanTime(한국 시각 'YYYY-MM-DD HH:MM')
     - 인증 방식: CREDENTIAL_MODES(서비스 계정·API 키·주입된 인증·없음)
     - AI 참고 의견·맥락 검토 문장·후보·출처 제목: friendlyText
 F3(R2). 보고서
     - docx_report.py: paragraph(raw=False)가 readable을 거친다. 표 칸은 word, 제목은 readable. 기술 부록(json_lines)은 raw=True.
     - pdf_report.py: _escape가 word를 거친다(_appendix_blocks는 그대로). 인용 상태 칸은 word(status)+단계 설명. '근거 문구 대조 일치/불일치·미확인'. 고정 문장 한글화.
     - rag_engine/review.py report_lines: word·korean_time 사용, read_pages None → 0.
     - reference_opinions.py: 관계에 word.
     - terminology.py REVIEW_NOTICE: "'확인됨'으로".
     - JSON·CSV·엑셀 기술부록의 코드는 그대로 둔다(감사 추적용).
 F5. 영문 낱말 치환(UNVERIFIED·QUARANTINED·UNCERTAIN·Source 등)은 앞뒤가 영문·숫자·밑줄이 아닐 때만 한다(app.js friendlyText, display_text.readable). 경계 없이 바꾸면 표에 없는 코드 안까지 바뀐다(사전 검증에서 'REFERENCE_QUARANTINED' → 'REFERENCE_안전 검토 필요' 깨짐 확인).
 F4(R3). renderFindings
     - 높음 이상 AI·보안 결과 수를 탭 버튼 data-high-count에 둔다.
     - styles.css .tabs button[data-high-count]::after { content: "높음 이상 " attr(data-high-count) … }
     - 버튼 글자(접근성 이름)는 그대로다. 기존 시험이 'AI 작성·보안 진단'으로 단언한다.

3. 확인 시험
 - tests/test_tk155_ui_cleanup.py 보강(패치 그대로):
   · 참고문헌 처리 기록 코드 0·한국 시각·'서비스 계정'·'None' 없음
   · 탭 버튼 '높음 이상 1'·버튼 글자 유지
   · readable 규칙
   · Word·PDF 본문 코드 0(운영과 같은 _RunView)
   · API names 97종·code_words
 - 기존 시험 단언 변경 4건(사용자 승인 완료 11-13 "시험 단언 변경 4건 승인" — 패치의 변경을 그대로 옮긴다, 되돌리지 않는다):
   · test_drive_rag_relevance.py::test_web_shows_drive_health_selection_and_duplicates: '인증 api_key' → '인증 API 키'
   · test_evidence_rag_review.py::test_reference_issues_are_listed_once_in_export: 'REFERENCE_PARTIALLY_READ' 1회 → '일부 쪽만 읽음' 1회 + 코드 없음
   · test_report_completion.py 2건(test_cross_format_labels_appendix_and_docx_zip·test_summary_report_keeps_review_content_and_moves_the_full_record_to_json): 'UNVERIFIED' in text → _unverified_shown(text)(엑셀·JSON은 코드, Word·PDF는 한글 중 하나). FINAL·스냅숏 해시·출처 URL 단언은 그대로.
 - 게이트(평가 측 재실행, 사본 c4953f4): 평가 세트 문구 대조 '의심 없음', check_test_edits '삭제·표시 변경 없음'(assert 감소 경고 1건 = 승인된 test_frontend_gate 변경), check_hardcoding_diff 통과, 보호 경로 변경 없음.

4. 평가 측 사전 검증(평가 측 재실행)
 - 화면(운영 /api/finding-categories 함수 응답 그대로, case9·탐침 B·C·D, 네 탭 전체 innerText, 참고문헌 처리 기록 펼침): 영문 코드 꼴은 사용자 Drive 파일명 1건만 남음(고치기 전 출처 탭 85·87·69·69). 밑줄 없는 단어 코드(INDEXED 등) 11 → 0.
 - 보고서 Word/PDF 코드 잔존: case9 115/138 → 2/2, B 96/118 → 2/2, C 72/80 → 2/2. 남은 2건은 Drive 파일명과 관리자 환경변수 이름(LV_KCI_KEY)이며, 남기는 근거는 TK-155 2절이다.
 - 전체 시험·은퇴 세트: 사본 19f2293(e57855f + TK-155 전체·TK-156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 전체 11,449건 통과·실패 0(사본 19f2293. 그 뒤 F5 경계 수정 c4953f4는 관련 시험 14파일 재실행 통과)(건너뜀 11·예상 실패 24). 은퇴 5세트 53.3/48.6/56.9/45.8/34.1·오탐 0 → 같음(후퇴 없음), 고정 dev 82.6·holdout 81.9·오탐 0(precheck_pr 성적표)
 - 미검증: 실제 운영 브라우저의 글꼴 차이, Word 프로그램에서 연 모양(텍스트 추출로만 확인).

5. 제출물·수용 기준
 - #271에 커밋 추가(보완 패치 적용). 대상 브랜치 Steve_ACASiaLAW 그대로. #270(TK-156)이 Steve에 병합됐으므로(f19ec47) 먼저 Steve를 병합 커밋으로 받아도 된다(겹치는 파일 없음 — 보완 패치는 router.py·test_efficient_llm_routing.py를 건드리지 않는다).
 - 수용 기준: 3절 시험 통과, 필수 CI 성공, precheck_pr의 평가 세트 문구 대조 통과, 은퇴·고정 세트 변화 0.
 - 화면 PR 절차: 평가 측이 최종 head로 캡처(상단·AI·출처(참고문헌 처리 기록 펼침)·법리)와 Word·PDF 각 1부를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
```

### 2-38-7. D1~D6 반영 대조(11-13, 사용자 질문 'D1~D6 권고안이 TK 155, 156에 모두 반영되어 있어?')
- 평가 측이 #271 head·Steve `f19ec47`·사본에서 코드로 대조:
  - D1(탭 배지 '검토 결정 대기 n'·대화상자 탭 범위): #271 반영
  - D2(완료가 아닐 때만 한 줄 안내): #271 반영
  - D3(배포 판정 화면·엑셀 삭제, 결과 JSON 유지): #271 반영. Word·PDF에는 원래 배포 판정이 없다
  - D4(판별 두 모델 고정 + Gemini 생략 사유): 라우터는 #270(병합), 화면 사유는 #271
  - D6(영문 코드·영문 오류 문장·조사): #271 반영
  - D5(셀마다 '구속력 없음' 반복 삭제): 화면은 반영(출처 탭 38·법리 탭 9 → 0). **Word·PDF 보고서 미반영**(case9 칸별 26회) → 보완 2

### 2-38-8. #271(TK-155) 판정 — 보완 1 반영 확인, 보완 2(D5 보고서) (11-13, head `a4e0131`)

```
[#271(TK-155) 보완 지시 2 — D5를 Word·PDF 보고서에도 적용]  평가한 SHA: a4e0131  평가 측 사본: f18acb1(e57855f 기준)
보완 패치: docs/handoff/patches/TK-155_supplement2_on_pr271_a4e0131.diff (a4e0131 → 사본 차이 전부, 5파일, git apply 가능)

0. 판정 요약
 - 보완 1은 그대로 반영됐다: a4e0131 = 평가 측 사본 c4953f4(router 제외 diff 0). 필수 CI 전부 성공(CI 결과 인용).
 - 평가 측이 보완 1을 낸 뒤 D1~D6 반영 여부를 코드로 대조하다가 D5 빈틈 1건을 찾았다. 평가 측 지시 누락이며 구현 측 결함이 아니다.

1. 문제·원인(줄 번호는 a4e0131 기준)
 C1. D5 결정 원문: '셀마다 반복 삭제, 표 위 범례 한 줄로 한 번만'. 화면에는 적용됐으나 Word·PDF 보고서에는 적용되지 않았다.
     - 화면: 변경 전 출처 탭 38회·법리 탭 9회 → 0회(범례 1줄).
     - 보고서: packages/report_engine/reference_opinions.py basis_text 첫 줄이 '[참고문헌 대조] ' + NOTICE('참고문헌·구속력 없음, 공식 확인 아님')다.
     - 이 문장이 참고문헌 대조 칸마다 붙는다. case9 Word·PDF 각 26회.
 C2. '3. 법률적으로 무리한 주장' 표에도 참고문헌 대조 칸이 있다. 그런데 표 위 안내(REPORT_NOTICE)는 '2.' 표 위에만 있다.
     - docx_report.py 224행·pdf_report.py 288행 참조.

2. 고칠 것(보완 패치와 같음)
 F1. reference_opinions.py
     - LEGEND = "주요 참고문헌은 등록된 검증 자료입니다. 판례·법령과 달리 법적 구속력은 없습니다."(화면 범례와 같은 말)
     - REPORT_NOTICE 끝을 NOTICE → LEGEND로 바꾼다.
     - basis_text 첫 줄은 '[참고문헌 대조]'만 둔다.
     - NOTICE import는 지운다(rag_engine.reference_binding.NOTICE 자체와 엑셀 '공식 여부' 열은 그대로).
 F2. docx_report.py·pdf_report.py: '3. 법률적으로 무리한 주장' 표 위에도 REPORT_NOTICE를 한 번 둔다(표가 있을 때만).

3. 확인 시험
 - tests/test_tk155_ui_cleanup.py:
   · Word·PDF 본문에 '구속력 없음' 없음
   · 새 시험 test_report_reference_notice_is_a_legend_not_per_cell(basis_text에 '구속력' 없음, '[참고문헌 대조]'로 시작, 관계 '불부합', LEGEND ⊂ REPORT_NOTICE)
 - 기존 시험 단언 변경 1건(사용자 승인 필요 — 승인 전에는 병합하지 않는다):
   · tests/test_tk127_stage2_drive_pipeline.py::test_four_reports_retain_unofficial_reference_opinions(매개변수 3개)
   · 옛 단언: Word 칸마다 '공식 확인 아님'
   · 새 단언: 칸에 '[참고문헌 대조]' 표지·'구속력 없음' 없음 + Word 본문에 LEGEND + PDF에 LEGEND·'공식 확인'
   · 엑셀 '공식 여부' 열 단언 3개는 그대로.
   · 근거: D5가 옛 TK-88·127 '칸마다 표시' 결정을 바꾼 것(V1_0_0_UI_IMPROVEMENT_PLAN 1절 6-5).

4. 평가 측 사전 검증(평가 측 재실행, 사본 f18acb1)
 - case9 Word/PDF 칸별 '구속력 없음' 26/26 → 0/0, 표 위 안내 1회. 탐침 B는 표 2개에 안내 2회.
 - 관련 시험(보고서·참고문헌·TK-88·TK-127·TK-155 등) 통과.
 - 게이트: 평가 세트 문구 대조 '의심 없음', check_test_edits '삭제·표시 변경 없음', check_hardcoding_diff 통과, 보호 경로 변경 없음.
 - 전체 시험: 사본 f18acb1(e57855f + TK-155 전체(보완 1·2)·TK-156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 전체 11,450건 통과·실패 0(건너뜀 11·예상 실패 24). 첫 실행의 실패 2건은 평가 측이 측정 환경에 numpy를 들인 탓(numpy가 있으면 openpyxl이 그것을 쓰고 대형 판례표 격리 추출 시험이 실패) — 환경 복원 뒤 재실행에서 통과. 운영 의존성에는 numpy가 없다(requirements.txt, pgvector 0.5.1 의존 없음)
 - 미검증: 보고서를 받는 쪽(상대방·법원)의 오해 가능성 — 표 위 안내로 대체한 효과는 사용자 판단 사항이다.

5. 제출물·수용 기준
 - #271에 커밋 추가(보완 패치 2 적용).
 - 수용 기준: 3절 시험 통과, 필수 CI 성공, precheck_pr 평가 세트 문구 대조 통과, 은퇴·고정 세트 변화 0.
 - 화면·보고서 수용 절차: 평가 측이 최종 head로 캡처와 Word·PDF를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
```

### 2-38-9. #272(평가 v2 전환, Codex 평가 기준 재검토) 판정 — 타당, README 그래프 추가 (11-13)
- 사용자 지시: "타당한 방향으로 검토되었는지 확인한 후 타당하다면 병합" + "병합하기 전에, readme.md의 현재 버전별 변경내역 표를 버전별 성능 발전 추이 그래프로 변경하고, 그래프 하단에는 어떤 벤치마크 기준인지를 표시".
- 평가 측 재실행(head 46d45f7):
  - 성적표: 구 산식 82.6/81.9·확인 오탐 0, v2 일대일 42/56·41/54 — PR 본문과 같음
  - score_gate 통과, 다층 대시보드 생성
  - tests/acceptance 전체 통과
  - 은퇴 5세트 목록·해시 검증 5
  - 보호 경로 '모두 평가 측 커밋'
  - 새 파일 정답 문자열(10자 이상 1,379개) 자동 대조 일치 0 — 정답 내용은 열람하지 않음
- 타당성:
  - 게이트를 모두 강화하는 방향이다(기준/후보 실패·세트 누락·분모·해시 변경을 통과로 보지 않음).
  - 기존 baseline·정답·제품 코드 변경 없음.
  - 미측정 층은 NOT_MEASURED로 명시하고 법률 품질 승인으로 바꾸지 않는다.
  - 유일한 기존 시험 변경(retired_compare 기대값)도 강화 방향이다.
- 주의(사용자 결정 필요): retired_manifest는 '5세트 모두 릴리스 승격에서 유지'를 요구한다.
  - #189 이후 릴리스 PR은 main에서 sealed_20261025 11파일을 빼 왔다(main은 4세트).
  - 다음 릴리스 PR(0.20.0)은 이 11파일을 main에 포함해야 CI가 통과한다.
  - 해당 세트는 10-25 사용자 결정으로 이미 개발용(retired)으로 이전됐다.
- README(평가 측, `91b3ee7`, #272 브랜치):
  - 버전별 변경내역 표 → '버전별 성능 발전 추이' 그래프(docs/assets/performance_trend.png)
  - 그래프 아래 벤치마크 기준 설명: 내부 회귀 벤치마크, 7세트·51문서·365항목(법률 123), v0.10~v0.19 같은 조건 재측정 2026-11-13, 공개 벤치마크·실무 정확도 아님
  - 자료 docs/scorecards/version_performance.csv, 생성 scripts/render_performance_chart.py·update_readme.py, 시험 2건 추가
  - 상세 변경은 docs/RELEASE_HISTORY.md 링크
- CI(인용): pull_request 실행 전부 성공. 같은 SHA push 실행의 1건(test_regex_performance_ratio_under_8, 시간 비 8.6>8)은 #272와 무관한 러너 시간 변동이다. 실패 작업만 재실행했다.

### 2-38-10. 사용자 'TK-127 시험 단언 변경 승인' (11-13) — #271 보완 2 전달판(2-38-8을 대체)

```
[#271(TK-155) 보완 지시 2 — D5를 Word·PDF 보고서에도 적용]  평가한 SHA: a4e0131  평가 측 사본: f18acb1(e57855f 기준)
보완 패치: docs/handoff/patches/TK-155_supplement2_on_pr271_a4e0131.diff (a4e0131 → 사본 차이 전부, 5파일, git apply 가능)

0. 판정 요약
 - 보완 1은 그대로 반영됐다: a4e0131 = 평가 측 사본 c4953f4(router 제외 diff 0). 필수 CI 전부 성공(CI 결과 인용).
 - 평가 측이 보완 1을 낸 뒤 D1~D6 반영 여부를 코드로 대조하다가 D5 빈틈 1건을 찾았다. 평가 측 지시 누락이며 구현 측 결함이 아니다.

1. 문제·원인(줄 번호는 a4e0131 기준)
 C1. D5 결정 원문: '셀마다 반복 삭제, 표 위 범례 한 줄로 한 번만'. 화면에는 적용됐으나 Word·PDF 보고서에는 적용되지 않았다.
     - 화면: 변경 전 출처 탭 38회·법리 탭 9회 → 0회(범례 1줄).
     - 보고서: packages/report_engine/reference_opinions.py basis_text 첫 줄이 '[참고문헌 대조] ' + NOTICE('참고문헌·구속력 없음, 공식 확인 아님')다.
     - 이 문장이 참고문헌 대조 칸마다 붙는다. case9 Word·PDF 각 26회.
 C2. '3. 법률적으로 무리한 주장' 표에도 참고문헌 대조 칸이 있다. 그런데 표 위 안내(REPORT_NOTICE)는 '2.' 표 위에만 있다.
     - docx_report.py 224행·pdf_report.py 288행 참조.

2. 고칠 것(보완 패치와 같음)
 F1. reference_opinions.py
     - LEGEND = "주요 참고문헌은 등록된 검증 자료입니다. 판례·법령과 달리 법적 구속력은 없습니다."(화면 범례와 같은 말)
     - REPORT_NOTICE 끝을 NOTICE → LEGEND로 바꾼다.
     - basis_text 첫 줄은 '[참고문헌 대조]'만 둔다.
     - NOTICE import는 지운다(rag_engine.reference_binding.NOTICE 자체와 엑셀 '공식 여부' 열은 그대로).
 F2. docx_report.py·pdf_report.py: '3. 법률적으로 무리한 주장' 표 위에도 REPORT_NOTICE를 한 번 둔다(표가 있을 때만).

3. 확인 시험
 - tests/test_tk155_ui_cleanup.py:
   · Word·PDF 본문에 '구속력 없음' 없음
   · 새 시험 test_report_reference_notice_is_a_legend_not_per_cell(basis_text에 '구속력' 없음, '[참고문헌 대조]'로 시작, 관계 '불부합', LEGEND ⊂ REPORT_NOTICE)
 - 기존 시험 단언 변경 1건(사용자 승인 완료 11-13 "TK-127 시험 단언 변경 승인" — 패치의 변경을 그대로 옮긴다, 되돌리지 않는다):
   · tests/test_tk127_stage2_drive_pipeline.py::test_four_reports_retain_unofficial_reference_opinions(매개변수 3개)
   · 옛 단언: Word 칸마다 '공식 확인 아님'
   · 새 단언: 칸에 '[참고문헌 대조]' 표지·'구속력 없음' 없음 + Word 본문에 LEGEND + PDF에 LEGEND·'공식 확인'
   · 엑셀 '공식 여부' 열 단언 3개는 그대로.
   · 근거: D5가 옛 TK-88·127 '칸마다 표시' 결정을 바꾼 것(V1_0_0_UI_IMPROVEMENT_PLAN 1절 6-5).

4. 평가 측 사전 검증(평가 측 재실행, 사본 f18acb1)
 - case9 Word/PDF 칸별 '구속력 없음' 26/26 → 0/0, 표 위 안내 1회. 탐침 B는 표 2개에 안내 2회.
 - 관련 시험(보고서·참고문헌·TK-88·TK-127·TK-155 등) 통과.
 - 게이트: 평가 세트 문구 대조 '의심 없음', check_test_edits '삭제·표시 변경 없음', check_hardcoding_diff 통과, 보호 경로 변경 없음.
 - 전체 시험: 사본 f18acb1(e57855f + TK-155 전체(보완 1·2)·TK-156, SQLite, LV_ALLOW_NETWORK=0, 화면 시험 포함) 전체 11,450건 통과·실패 0(건너뜀 11·예상 실패 24). 첫 실행의 실패 2건은 평가 측이 측정 환경에 numpy를 들인 탓(numpy가 있으면 openpyxl이 그것을 쓰고 대형 판례표 격리 추출 시험이 실패) — 환경 복원 뒤 재실행에서 통과. 운영 의존성에는 numpy가 없다(requirements.txt, pgvector 0.5.1 의존 없음)
 - 미검증: 보고서를 받는 쪽(상대방·법원)의 오해 가능성 — 표 위 안내로 대체한 효과는 사용자 판단 사항이다.

5. 제출물·수용 기준
 - #271에 커밋 추가(보완 패치 2 적용).
 - 수용 기준: 3절 시험 통과, 필수 CI 성공, precheck_pr 평가 세트 문구 대조 통과, 은퇴·고정 세트 변화 0.
 - 화면·보고서 수용 절차: 평가 측이 최종 head로 캡처와 Word·PDF를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
```

## 2-39. 법률 AI 벤치마크 기준 보완·신규 기능 계획과 TK 분할 (11-13, 사용자 '제안 계획 문서로 저장하고 TK 지시로 나눠줘')
- 계획·티켓 명세: [LEGAL_AI_BENCHMARK_IMPROVEMENT_PLAN_20261113.md](LEGAL_AI_BENCHMARK_IMPROVEMENT_PLAN_20261113.md).
- 티켓: EV-1(평가 측, 탐침 미통과 7건 원인), TK-157(경고 묶기·정밀도 라벨), TK-158(기준일 법령 버전 확정), TK-159(공식 원문 근거 구간), TK-160(주장 3분류), TK-161(AI 판별 반복 안정성), TK-162(판례 변경 추적), TK-163(원문 대조 보기), TK-164(사건 연대표), TK-165(KBL 정기 측정), TK-166(법률가 라벨 시험셋), TK-167(법관 AI 가이드북 체크리스트 보고서), TK-168(공개 인터페이스 문서·계약 시험).
- 구현 지시서는 아직 내지 않았다. 착수 순서대로 평가 측 사본 사전 검증(precheck_pr·관련 시험·은퇴·고정 세트) 뒤 티켓별로 낸다. 첫 묶음 권고: EV-1·TK-157·TK-158·TK-168(초안).


## 2-40. 사용자 결정 반영·EV-1 결과·TK-169 구현 지시·첫 묶음 초안 (11-13, 사용자 'TK 167 제외, TK 166·168은 v1.0 단계', '첫 묶음: EV-1, TK-157, TK-158, TK-168 초안 준비')
- #272 병합 기록:
  - Steve `0de85a4`(expectedHeadSha `91b3ee7`). CI 재실행 성공 확인 뒤 사용자 지시로 병합했다.
  - 판정 코멘트: https://github.com/stevelee0119/ACASia_LAW/pull/272#issuecomment-6849967575
- 사용자 결정:
  - TK-167 제외(자료 확보 불가).
  - TK-166·168은 v1.0 단계에서 시행한다.
  - v1.0 절차는 '상업화 가능 수준'이 객관적으로 판단될 때만 고려한다.
  - 판단 기준(제안, 사용자 승인 필요)은 계획 문서 6.7절에 있다.
- 첫 묶음:
  - EV-1: 계획 문서 6.3절. 원인 분류를 마쳤고, 구현 티켓은 **TK-169**다.
  - TK-157·158·168: 초안만 있다(6.4~6.6절). 사전 검증 전이며 지시는 아직 내지 않았다.
- KBL 라이선스 검토: 6.8절. TK-165는 라이선서의 서면 상업 이용 허락을 받은 뒤 착수하기를 권고한다.

### 2-40-1. TK-169 지각 범위 같은 문장 규칙 일반화 — 구현 지시(전달판)
- 보완 패치: [patches/EV-1_perception_on_0de85a4.diff](patches/EV-1_perception_on_0de85a4.diff)
- 평가 측 사본: `646a6f3`(저장소 밖)

```
[TK-169 지각 범위 같은 문장 규칙 일반화 — EV-1 결과 구현 지시]  기준 SHA: 0de85a4(Steve_ACASiaLAW)  평가 측 사본: 646a6f3
보완 패치: docs/handoff/patches/EV-1_perception_on_0de85a4.diff
 - 0de85a4 → 사본 차이 전부: 제품 1파일 + 새 시험 1파일
 - git apply 가능
대상 릴리스: 0.20.x(사용자 원칙 '최초 의도한 개선은 해당 릴리스에 포함')

0. 배경
 - 0.19.0 온라인 탐침 47항목 중 미통과 7건은 모두 탐침 C(진술서 지각 범위)의 양성이다.
 - C 성적은 9/16이다: 양성 1/8, 대조 8/8.
 - 평가 측이 같은 문장을 0de85a4 perception_conflict에 넣어 온라인 결과를 그대로 재현했다(평가 측 재실행).
 - 원인은 7건 모두 '같은 꼴의 다른 어미·낱말'을 정규식이 받지 못한 일반화 부족이다. 모델 변동이나 명세 문제는 없다.
 - 탐침 문장은 공개하지 않고 꼴만 적는다.

1. 원인(파일: packages/claim_engine/evidence_consistency.py, 줄은 0de85a4 기준, 함수 perception_conflict 99행)
 C1. 경험 부정 꼴 미수용(1건)
     - 68행 _ACCESS_NEG_RE는 '열·뜯·살펴보…-지 않/못'만 받는다.
     - '살펴본·열어 본·개봉한 적(일)이 없지만' 꼴의 접근 부정을 놓친다.
 C2. 닫힘 서술형·내부 노출 부정 미수용(1건)
     - 72행 _CLOSED_RE는 관형형('닫힌·잠긴·불투명한')+최대 2낱말+'안·속·내부'+조사 '의·에·에서'가 바로 붙을 때만 받는다.
     - '…이 잠겨 있어 내부가 드러나지 않았는데도 … 그 속에서 … 보았다' 꼴을 놓친다.
 C3. 장소 출입 낱말 목록이 좁음(1건)
     - 74행 _NEVER_THERE_RE는 '간·가 본·방문한·들어간·참석한'만 받는다.
     - '발을 들인 적', '출입한 적', '들어가 본 적'을 놓친다. '-는데도' 어미도 없다.
 C4. 머무름 연결형 미수용(1건)
     - 83행 _ELSEWHERE_RE는 '있었·머물렀·지냈'에 양보 어미가 바로 붙어야 한다.
     - '…에 머물러(있으면서) …(매체도 듣지) 않았지만, 같은 시각 다른 곳에서 … 제 귀로 들었다' 꼴을 놓친다.
 C5. '소리만' 뒤 다른 서술어, 시각 주장 표지(2건)
     - 86행 _SOUND_ONLY_RE의 '소리만' 뒤 서술어는 '듣고·들었지만·들은 채'뿐이다. '접했고·전달되어·들렸고·났'을 놓친다.
     - 88행 _VISUAL_CLAIM_RE는 '직접·분명히·똑똑히'+동사가 바로 붙어야 한다. '눈으로 분명히 확인', '육안으로 확인'을 놓친다.
     - 63행 _DIRECT_RE에 '육안으로'가 없다.
 C6. 의식 회복 부정 미수용(1건)
     - 75행 _INCAP_RE에 '의식이 돌아오지 않', '의식을 되찾지 못', '정신을 차리지 못'이 없다.

2. 고칠 것(보완 패치와 같음, 꼴·구조 단위로만 넓히고 장면 낱말은 넣지 않는다)
 F1. _DIRECT_RE에 '육안으로' 추가.
 F2. 새 _ACCESS_EXP_NEG_RE: 경험 부정 꼴의 접근 부정.
     - 꼴: (연|열어 본|뜯어 본|뜯은|펼쳐 본|들여다 본|살펴 본|꺼내 본|개봉한|열람한) + 적/일 + (이|은|도)? + 없(었)? + (지만|으나|는데(도)|음에도|고)
     - '연' 앞은 한글이 아니어야 한다.
     - 기존 UNOPENED_INSIDE 분기와 같은 뒤 조건(_INSIDE_RE → _PERC_RE)으로 판정한다.
 F3. 새 CLOSED_INSIDE 경로.
     - 두 꼴 가운데 하나를 받는다: _HIDDEN_INSIDE_RE((닫혀|잠겨|봉인되어|밀봉되어|가려져|덮여) 있 + 연결·양보 어미), 또는 '안·속·안쪽·내부(조사) (전혀·조금도) 보이지·드러나지·들여다보이지 않/못'.
     - 그 뒤에 내부 지시(_INSIDE_REF_RE: (그) 안·속·안쪽·내부 + 에서·의·에 있던·에 든)가 와야 한다.
     - 내부 지시 뒤에 시각 지각 동사(_VISUAL_PERC_RE: 보았·봤·목격·읽었·직접 본)가 있어야 한다. 청각은 닫힌 문 너머로도 가능하므로 받지 않는다.
     - 문장 안에 직접 표지(_DIRECT_RE)가 있어야 한다.
     - 제외 1: 연 행위(_OPENED_RE)가 있으면 받지 않는다.
     - 제외 2: 투명 경로(_SEE_THROUGH_RE: 유리·(불 제외)투명한·틈(새)으로·창(문) 너머)가 있으면 받지 않는다. '불투명한'이 '투명한'에 걸리지 않도록 (?<!불)을 둔다.
 F4. _NEVER_THERE_RE 낱말: 와 본·들어가 본·출입한·발을 (들인|디딘|들여놓은) 추가, 어미에 '-는데도' 추가.
 F5. _INCAP_RE에 '의식이 돌아오지 (못|않)', '의식을 되찾지 (못|않)', '정신을 차리지 (못|않)' 추가.
     - 새 _REPORTED_RE('…다/라고 (낱말 0~2개) 들었·들은·전해'): INCAP 뒤에 이것이 있으면 받지 않는다. 옮긴 말은 직접 지각이 아니다.
 F6. 새 ELSEWHERE_SAME_TIME 경로(기존 경로는 그대로 둔다).
     - _STAY_LINK_RE: (장소)(에|에서) + 낱말 0~2개 + (머물러|머무르며|머물면서|있으면서|있었고|머물렀고|지내며).
     - 그 뒤 '같은/그 시각·동시에' 앞에 양보 어미(지만|으나|는데도|음에도)가 있어야 한다.
     - 시각 표지 뒤에 지각 장소 '(낱말)에서'가 있어야 하고, 그 낱말이 머문 장소 낱말과 달라야 한다.
     - 시각 표지 뒤에 _PERC_RE와 _DIRECT_RE가 모두 있어야 한다.
     - TK-151로 끈 L1(문장 사이 체재)은 다시 켜지 않는다. 이 경로는 같은 문장 안에서 양보·다른 장소·직접 표지가 모두 있을 때만 받는다.
 F7. _SOUND_ONLY_RE '소리만' 뒤 서술어에 접했·들렸·들려 왔·전달되·났 추가.
     - _VISUAL_CLAIM_RE: (직접|분명히|똑똑히|육안으로|눈으로) + (낱말 0~1개) + (확인했·보았·봤·읽었).
     - 소리 표지와 시각 주장 사이에 _THEN_LOOKED_RE(이후·그 뒤·다음에·들어가·다가가·가 보니·문을 열·내다보)가 있으면 받지 않는다. 소리 뒤에 가서 본 것은 모순이 아니다.
     - 이 제외는 기존 '소리만' 경로에도 적용된다. 기존 시험은 모두 통과한다.
 공통: 매개 경로(_MEDIATED_RE)가 있으면 먼저 None을 돌려주는 기존 순서를 유지한다.

3. 확인할 시험
 - 새 tests/test_ev1_perception_forms.py(패치에 있음): 평가 측 합성 문장 28건(양성 12·대조 16). 탐침 문장이 아니다.
   · 양성: 경험 부정 2, 닫힘 서술·노출 부정 2, 출입 낱말 2, 의식 회복 부정 2, 머무름 연결형 2, 소리만 다른 서술어 2
   · 대조: 지각 주장 없음, 겉면만 읽음, 닫힌 곳의 소리, 유리창 너머, 연 뒤 관찰, 전해 들음, 보도를 봄, 다른 사람의 의식 상실, 옮긴 말, 같은 장소, 소리 뒤 들어가 확인, 소리만·지각 부정, TK-151 L1 오탐 꼴, 잠김·확인 못 함, 닫힌 사무실 안에서 들음
 - 기존 시험 그대로 통과: tests/test_tk76_perception_structure.py, test_tk76_logic_eval.py, test_tk76_b_bundle_eval.py, test_v2_root_causes.py
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 646a6f3 = 0de85a4 + 패치, SQLite, LV_ALLOW_NETWORK=0)
 - 탐침 C 정답지 문장(16): 양성 8/8, 대조 오탐 0/8. 0de85a4는 양성 1/8.
 - 탐침 A·B 정답지 문장(17): 새 오탐 0. D는 표 문서라 문장이 없다.
 - 평가 측 일반화 문장 28건: 사본 28/28, 0de85a4 17/28.
 - 고정 세트: dev 82.6·holdout 81.9, 확인 오탐 0, v2 일대일 42/56·41/54. 변화 0.
 - 은퇴 5세트: 변화 0(후퇴 없음).
 - 게이트: check_hardcoding_diff 통과, check_test_edits '삭제·표시 변경 없음', check_protected_paths 변경 없음.
 - precheck_pr(전체 모드): 종료 0(성적표·점수 게이트, 은퇴 비교, 회귀·수용·기능 시험(+3절 시험), 평가 세트 문구 대조 모두 통과)
 - 전체 시험: 평가 측 재실행 진행 중 — 이 지시문 발행 시점에는 미검증. 결과는 NEXT 2-40에 추가한다
 - 미검증:
   · 온라인 문서 단위 재측정(PDF 줄바꿈으로 나뉜 문장 결합)은 배포 뒤 온라인 탐침 C로 확인한다.
   · 실제 사건 진술서에서의 새 오탐률은 측정하지 않았다(고정·은퇴 세트에 해당 꼴이 적다).
   · 고정·은퇴 세트 점수가 오르지 않은 것은 그 세트에 이 꼴이 없어서다. 개선은 탐침·합성 시험으로만 확인됐다.

5. 제출물·수용 기준
 - Steve_ACASiaLAW 기준 새 PR 하나.
   · 제품: packages/claim_engine/evidence_consistency.py
   · 시험: 새 tests/test_ev1_perception_forms.py
   · 보호 시험(tests/acceptance/)은 바꾸지 않는다.
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · precheck_pr 평가 세트 문구 대조 통과
   · 고정·은퇴 세트 변화 0(또는 상승), 확인 오탐 0
 - 배포 뒤 온라인 탐침 C 재측정(사용자 실행): 양성 8/8·대조 0/8 목표. 미달 항목은 평가 측이 다시 원인을 분석한다.
```

### 2-40-2. 사용자 '상업적 이익 목적으로 사용하지 않을 예정' (11-13)
- KBL(CC BY-NC 4.0)을 이용한 성능 측정은 비상업 이용 범위에 든다. TK-165의 라이선스 선행 조건은 해소됐다.
- 남은 결정은 모델 호출 비용과 착수 시기다.
- 지킬 조건과 미확정 1건(유료 법률 업무에 쓰는 경우)은 계획 문서 6.9절에 있다.

### 2-40-3. 사용자 'KBL은 사용하지 않는 것으로' (11-13)
- TK-165는 제외한다. 유료 법률 업무에는 쓰지 않는다(사용자 확인).
- Steve에 남은 KBL 채점기·참조는 다음 평가 PR에서 정리한다. 이 PR은 사용자 병합 승인이 필요하고, 보호 시험 변경은 사용자께 먼저 보인다(계획 문서 6.10절).
- 구현 측이 할 일은 없다.

### 2-40-4. #273(TK-169) 판정 — 수용 (11-13, head `5bba701`)
- 판정 코멘트: https://github.com/stevelee0119/ACASia_LAW/pull/273#issuecomment-6854385325
- head는 평가 측 사본 `646a6f3`과 diff 0이다. 필수 CI 성공(CI 결과 인용).
- verify_all 전체 모드(평가 측 재실행, 기준 `0de85a4`): 종료 0.
  - 수용 1,280·원장 2,357·전체 10,028·화면 197, 실패 0
  - 점수·회귀·하드코딩·시험 삭제·보호 경로·버전 정책 통과
- 병합은 사용자 승인 대기다. 배포 뒤 온라인 탐침 C 재측정(사용자 실행)으로 마무리한다.

### 2-40-5. #271(TK-155) 판정 — 보완 2 반영·사용자 화면 확인 완료, 보완 3(사용자 지시 'AI 탭 영문 표기 한글화, TK-155 범위') (11-13, head `044dcee`)
- 판정 코멘트: https://github.com/stevelee0119/ACASia_LAW/pull/271#issuecomment-6854694969
- 보완 패치: [patches/TK-155_supplement3_on_pr271_044dcee.diff](patches/TK-155_supplement3_on_pr271_044dcee.diff)
- 평가 측 사본: `79c1671`(저장소 밖)

```
[#271(TK-155) 보완 지시 3 — AI 탭에 남은 영문·기호 표기를 짧은 한글 설명으로]  평가한 SHA: 044dcee  평가 측 사본: 79c1671(044dcee 기준)
보완 패치: docs/handoff/patches/TK-155_supplement3_on_pr271_044dcee.diff
 - 044dcee → 사본 차이 전부: 4파일, git apply 가능
 - Steve 0de85a4에 #271을 합친 트리에도 그대로 적용된다

0. 판정 요약
 - 보완 2(044dcee)는 평가 측 사본 f18acb1과 같다(TK-156 라우터 2파일 제외 diff 0). 필수 CI 전부 성공(CI 결과 인용).
 - 사용자 화면 확인 완료(11-13).
 - 사용자가 새로 지시했다(원문): "AI 탭에 남은 영문 표기 INSTRUCTION_LIKE 등과 같은 것은 한글 설명으로 변경, 그리고 이해하기 쉽고 간결하게 표기하도록 하고 TK-155 범위에 포함"

1. 문제·원인(줄 번호는 044dcee 기준)
 C1. 화면 표시 규칙(friendlyText, packages/common/display_text.readable)은 '코드(XXX_YYY)'만 한글로 바꾼다.
     - 엔진 문장 속 '키=값', 모델 표지, 유니코드 문자 이름, 층 이름은 그대로 나온다.
     - 0.19.0 온라인 결과 4건(case9·B·C·D) AI 탭에 남은 꼴과 출처:
       · '분류=지시형 문구, 점수=1.0, 보조신호=0개', '…시스템 지침이나 Tool 권한을 변경하지 않는다.'
         출처: packages/adversarial_engine/scanner.py 290·294~296·384~385·687행
       · 'Unicode 은닉 신호: 폭 0 문자 — ZERO WIDTH NO-BREAK SPACE (BOM) (U+FEFF) 1회', 'xml 레이어.'
         출처: scanner.py 406·448·449행, packages/common/textutil.py 13~17행
       · '근거: [openai] …', '모델 간 판단 불일치: openai=…, anthropic=…, gemini=…'
         출처: AI 작성 판별 결과 문장
       · '작성 프로그램=Writer', '작성자=python-docx', 'creator=python-docx'
         출처: 메타데이터 진단 문장
       · 모델 근거 끝 마침표와 '. 발췌'가 겹친 '.. 발췌'
     - 화면 측정(평가 측 재실행, 044dcee, 4탭 텍스트): case9 48건, B 66건, C 28건, D 12건.
     - 같은 문장이 Word·PDF에도 실린다(readable 경유): case9 39, B 49, C 14, D 12.
 C2. 검사 항목 설명(apps/web/static/app.js 1190~1191행 INJECTION_CHECKS)에 'Base64 등으로 감춘 문자열', '이미지·OCR 층', '유니코드'가 있다.
 C3. 화면 friendlyText(app.js 87행)의 문장 치환 표가 display_text._PHRASES와 따로 적혀 있다(두 벌).

2. 고칠 것(보완 패치와 같음 — 결과 데이터·엔진 문장은 바꾸지 않고 표시만 바꾼다)
 F1. packages/common/display_text.py _PHRASES 뒤에 치환 쌍을 더한다.
     - 순서 그대로, 긴 문구 먼저.
     - 바꾼 결과가 다시 걸리지 않게 만든다(두 번 적용해도 같다).
     - 공개 이름 PHRASES = _PHRASES를 둔다.
     - 치환 내용:
       · '본 문자열은 자료로만 취급되며' → '이 문자열은 자료로만 다루며', '시스템 지침이나 Tool 권한을' → '시스템 지시나 도구 권한을'(문장 끝 '변경하지 않는다'는 열쇠에 넣지 않는다 — 평가 세트 문구 대조에 걸린다)
       · 'Tool 권한' → '도구 권한'
       · 'Unicode 은닉 신호: 폭 0 문자(zero-width) — ', 'Unicode 은닉 신호: 폭 0 문자 — ' → '보이지 않는 문자: '
       · 'Unicode 은닉 신호', 'Unicode 신호' → '보이지 않는 문자'
       · 'ZERO WIDTH NO-BREAK SPACE (BOM)' → '폭 없는 공백'
       · ZERO WIDTH SPACE·NON-JOINER·JOINER, WORD JOINER → 폭 없는 공백, 폭 없는 글자 분리 문자, 폭 없는 글자 결합 문자, 폭 없는 단어 결합 문자
       · '[openai] ' → '(OpenAI) ', '[anthropic] ' → '(Anthropic) ', '[gemini] ' → '(Gemini) '
       · 'openai=' → 'OpenAI ', 'anthropic=' → 'Anthropic ', 'gemini=' → 'Gemini '
       · '분류=' → '분류: ', '점수=' → '점수 ', '보조신호=' → '보조 신호 '
       · '(PDF 생성) 프로그램=', '작성 프로그램=', '작성자=', 'creator=', 'producer=' → '…: '
       · 'xml|metadata|annotation|attachment|outline 레이어' → '문서 내부 구조|문서 속성|주석|첨부 파일|북마크 층'
       · 남은 '레이어' → '층'
       · '.. 발췌' → '. 발췌'
     - 모델·회사 이름(OpenAI·Anthropic·Gemini)과 도구 이름 값(Writer·python-docx 등)은 고유명사·자료값이라 그대로 둔다.
     - 개인정보 가림 표지([PERSON_003] 등)도 기존 결정대로 그대로 둔다.
 F2. apps/api/routers/projects.py get_finding_categories에 "phrases": [list(pair) for pair in PHRASES]를 더한다(import에 PHRASES).
 F3. app.js friendlyText 87행: 치환 표를 `tables.phrases || [기존 기본 표]`로 바꾼다. 서버 표 하나가 기준이고, 받지 못했을 때만 기본 표를 쓴다.
 F4. app.js INJECTION_CHECKS: '보이지 않는 유니코드 문자' → '보이지 않는 문자', 'Base64 등으로 감춘 문자열' → '부호로 바꿔 감춘 문자열', '이미지·OCR 층의 지시문' → '이미지 속 글자의 지시문'.

3. 확인 시험(tests/test_tk155_ui_cleanup.py, 패치에 있음)
 - FINDINGS에 합성 2건을 더한다(UNICODE_SMUGGLING, AUTHORSHIP_METADATA_LEAK). 기존 색인 FINDINGS[5]는 그대로다.
 - 시험용 cats에 "phrases"를 더한다.
 - 새 시험:
   · test_engine_phrases_read_as_short_korean(엔진 문장 꼴 14개 × 남은 꼴 0, 코드 0, 두 번 적용 불변)
   · test_engine_phrase_examples_are_concise
   · test_finding_categories_api_serves_phrases
   · test_ai_tab_security_items_have_no_english_leftovers(브라우저)
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 79c1671, SQLite, LV_ALLOW_NETWORK=0)
 - 0.19.0 온라인 결과 4건 화면(AI 탭 포함 4탭) 남은 꼴(키=값·[모델]·Tool·Unicode·ZERO WIDTH·레이어·'..'·Base64): case9 48→0, B 66→0, C 28→0, D 12→0.
 - Word·PDF 남은 꼴: case9 39→0, B 49→0, C 14→0, D 12→0.
 - 남은 영문은 모델·회사 이름, 도구 이름 값, 개인정보 가림 표지뿐이다.
 - tests/test_tk155_ui_cleanup.py 전체 통과. 새 브라우저 시험은 3회 반복 통과.
 - 관련 기존 시험(화면·보고서·적대 엔진·분류표·수용 시험 등 표시 문구와 맞닿은 파일): 24개 파일 + 보고서 시험 + tests/acceptance + test_tk127 — 2,272건 통과·실패 0(예상 실패 24)
 - 게이트(기준 044dcee): check_hardcoding_diff 통과, check_test_edits '삭제·표시 변경 없음', check_protected_paths 변경 없음, 평가 세트 문구 대조 '의심 없음'(첫 판은 치환 열쇠의 문장 끝 '변경하지 않는다'가 은퇴 세트 정답지 1항목과 겹쳐 걸렸다 → 열쇠를 짧은 조각으로 나눠 해소)
 - 참고: Steve 0de85a4에 044dcee를 합친 트리에서 test_reference_processing_record_has_no_codes_and_korean_time이 1회 실패했다.
   · 같은 트리에서 단독으로 재실행하니 통과했다.
   · 평가 측 환경에 시험 실행이 3개 겹친 부하에서 브라우저 대기 시간이 초과된 것으로 판단한다. CI에서는 통과했다.
 - 미검증:
   · 운영 화면은 배포 뒤 사용자 확인으로 본다.
   · 이 표에 없는 새 엔진 문장 꼴이 나오면 그대로 영문이 보일 수 있다. 그때는 같은 표에 쌍을 더한다.

5. 제출물·수용 기준
 - #271에 커밋 추가(보완 패치 3 적용).
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · precheck_pr 평가 세트 문구 대조 통과
   · 은퇴·고정 세트 변화 0
 - 화면 수용 절차: 평가 측이 최종 head로 AI 탭 캡처(case9·B·C·D)를 재현해 사용자께 보이고 **사용자 확인 뒤 수용**.
```

### 2-40-6. 사용자 '#273 병합, 271 화면 확인 완료' (11-13)
- #273 병합: Steve `bf93d3c`(expectedHeadSha `5bba701`).
- #271 화면 확인: 사용자가 보완 3 사본(`79c1671`) AI 탭 캡처 4장(case9·B·C·D)을 확인했다.
- #271 head는 아직 `044dcee`이고, 보완 3 커밋은 없다.
- 구현 측 보완 3 head가 사본 `79c1671`과 diff 0이고 필수 CI가 성공하면, 같은 화면이므로 이 확인으로 수용한다.
  - 차이가 있으면 최종 head로 다시 캡처해 확인을 받는다.

## 2-41. 0.20.0 범위 확대 — 계획 TK-157~164 순차 진행 (11-13, 사용자 '#271 이후 구현할 사항들을 순서대로 진행해서 전체를 이번 릴리스에 반영, v1.0은 추후 재판단')
- 순서·막힘: 계획 문서 6.11절(TK-157 → 158 → 159 → 160 → 164 → 163 → 162 → 161).
- TK-161은 모델 호출이 필요해 오프라인 사전 검증이 불가하다. 사용자 결정이 필요하다.
- 이번 절에서 낸 지시: TK-157a(서버 집계), TK-158. TK-157b(화면 묶음·집계 표시)는 #271 병합 뒤에 낸다.

### 2-41-1. TK-157a 지시(전달판)
- 패치: [patches/TK-157a_review_quality_on_bf93d3c.diff](patches/TK-157a_review_quality_on_bf93d3c.diff)

```
[TK-157a 검토 결정의 유형별 집계(정밀도 라벨 축적) — 서버 API]  기준 SHA: bf93d3c(Steve_ACASiaLAW)  평가 측 사본: 7c7456a
보완 패치: docs/handoff/patches/TK-157a_review_quality_on_bf93d3c.diff
 - bf93d3c → 사본 차이 전부: 제품 1파일 + 새 시험 1파일, git apply 가능
대상 릴리스: 0.20.0
화면 쪽(TK-157b: 같은 문서·같은 유형·같은 위치 경고 묶기, 집계 표시)은 #271 병합 뒤 따로 지시한다(app.js가 #271과 겹친다).

0. 배경 — 평가 측 1단계 측정(평가 측 재실행, bf93d3c, 고정 2세트 + 은퇴 5세트 = 51문서, 문서·정답 열람 없이 채점기 출력의 유형·상태·등급·문서 키·위치만 집계)
 - 정답지 밖 미판정 경고: 102건(#272 감사 수치 재현), 29문서에 분포.
 - 상태별: CONTRADICTED 48, SUSPICIOUS 47, UNVERIFIED 7.
 - 등급별: A 72, B 22, C 8.
 - 유형별: 증거 목록·날짜·번호 계열 44, 보안·포렌식 계열 약 45, 법률 계열 6.
 - 같은 문서·같은 유형 중복: 24건(14묶음). 그중 같은 위치(쪽·블록)는 많아야 17건.
 - 결론:
   · 묶기로 줄일 수 있는 것은 많아야 약 4분의 1이다.
   · 나머지가 정답지 누락인지 실제 오탐인지는 라벨 없이는 가를 수 없다.
   · 그래서 담당자 검토 결정(수용·오탐·조치 완료)을 유형별로 모아 정밀도를 쌓는 장치가 먼저다.

1. 원인(줄 번호는 bf93d3c 기준)
 C1. 담당자 결정은 이미 저장된다(apps/api/db.py 372행 FindingRow.review_status, apps/api/routers/verification.py 347행 PATCH /findings/{id}/review, workspace.py 264행 구조화 결정 동기화).
     - 그러나 결정을 유형별로 모아 보는 경로가 없다.
     - 그래서 '어느 경고 유형이 자주 오탐으로 판정되는가'를 잴 수 없다.

2. 고칠 것(보완 패치와 같음)
 F1. verification.py에 GET /api/review-quality를 더한다.
     - filter_project_query로 보이는 사건(삭제 제외)만 센다.
     - advisory_only 경고는 뺀다.
     - FindingRow.type별 NEEDS_REVIEW·ACCEPTED·FALSE_POSITIVE·RESOLVED 개수, total, decided(=total−NEEDS_REVIEW)를 낸다.
     - 비율:
       · acceptance_rate=(ACCEPTED+RESOLVED)/decided, false_positive_rate=FALSE_POSITIVE/decided
       · decided가 REVIEW_QUALITY_MIN_DECIDED(5) 미만이면 비율은 null이고 enough_samples=false다.
     - 개수만 낸다: 문서 ID·제목·메모·작성자는 싣지 않는다.
     - note에 '법률가 독립 라벨(정밀도 측정)을 대신하지 않는다'를 적는다.

3. 확인 시험(새 tests/test_tk157_review_quality.py, 패치에 있음 — test_api의 로그인·업로드·실행 경로를 쓴다)
 - 결정 하나 → 해당 유형 FALSE_POSITIVE +1, 표본 부족이면 비율 null, 응답에 메모·제목·문서 ID 없음.
 - 최소 표본을 1로 바꾸면 비율이 나온다.
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 7c7456a, SQLite, LV_ALLOW_NETWORK=0)
 - 새 시험 2건 통과.
 - precheck_pr 전체 모드(+ test_api·test_identity_security·test_operations_completion): 종료 0 — 고정·은퇴 변화 0, 회귀·수용·기능 시험 통과, 평가 세트 문구 대조 통과
 - 게이트: check_hardcoding_diff 통과, check_test_edits '삭제·표시 변경 없음', check_protected_paths 변경 없음, 평가 세트 문구 대조 '의심 없음'.
 - 미검증: PostgreSQL에서의 집계 질의(CI 'PostgreSQL/pgvector' 잡으로 확인).

5. 제출물·수용 기준
 - Steve_ACASiaLAW 기준 새 PR 하나.
   · 제품: apps/api/routers/verification.py
   · 시험: 새 시험 1파일
 - 수용 기준: 3절 시험 통과, 필수 CI(PostgreSQL 포함) 성공, 고정·은퇴 세트 변화 0.
```

### 2-41-2. TK-158 지시(전달판)
- 패치: [patches/TK-158_same_boundary_on_bf93d3c.diff](patches/TK-158_same_boundary_on_bf93d3c.diff)

```
[TK-158 기준일 법령 판 확정 — 같은 시행일에 개정판이 여럿일 때]  기준 SHA: bf93d3c(Steve_ACASiaLAW)  평가 측 사본: a5746ec
보완 패치: docs/handoff/patches/TK-158_same_boundary_on_bf93d3c.diff
 - bf93d3c → 사본 차이 전부: 제품 4파일 + 새 시험 1파일, git apply 가능
대상 릴리스: 0.20.0(사용자 11-13 '#271 이후 계획 전부 이번 릴리스')

0. 배경
 - 0.19.0 온라인 case9의 '국가재정법 제96조'(기준일 2023-06-12)는 공식 원문을 찾고도 법령 존재·조문·본문·시간 적용이 모두 '확인하지 못함'이었다.
 - 사유는 'Multiple versions share the requested effective boundary'였다. 같은 결과가 2회 나왔다(결과 JSON unverified_items·legal_verdicts[8]).

1. 원인(줄 번호는 bf93d3c 기준)
 C1. packages/source_adapters/legal_history.py 79행 select_version은 기준일에 시행 중인 판 가운데 시행일이 가장 늦은 판이 둘 이상이면 106행에서 ValueError를 낸다.
 C2. packages/source_adapters/official_legal.py 224행 resolve_statute가 233행에서 이를 받고, 242행에서 그대로 ERROR로 돌린다.
 C3. packages/legal_engine/source_review.py 50·55행 verify_statute_source가 ERROR를 받아 판정 전체를 미확인으로 남긴다.
 C4. 같은 문제를 시간 적용 검토 경로는 이미 다룬다.
     - packages/legal_engine/temporal_review.py 559행 select_versions가 같은 경계의 판을 모두 돌려준다.
     - 보호 시험 tests/acceptance/test_ft_protected.py T11은 '같은 시행일 판들의 조문이 같으면 미확인으로 남기지 않는다'를 이미 요구한다.
     - 주 경로(C2·C3)에만 이 원칙이 없다.

2. 고칠 것(보완 패치와 같음)
 F1. legal_history.py
     - BOUNDARY_ERROR(기존 문장)와 BOUNDARY_TEXT_DIFFERS 상수를 둔다.
     - boundary_versions(records, as_of)를 둔다: select_version과 같은 검증 규칙(식별·중복·소급·폐지)으로 같은 시행일 판을 모두 고른다. 판 번호(MST) 오름차순으로 결정적으로 정렬한다.
     - select_version의 106행은 BOUNDARY_ERROR를 쓴다(문장은 같다).
 F2. official_legal.py resolve_statute에 선택 인자 article=None을 더한다.
     - BOUNDARY_ERROR이고 article이 있으면 _resolve_same_boundary로 간다.
       · 같은 경계의 판마다 본문을 받는다(fetch_law_version).
       · select_provision(본문, article)로 인용 조문 문언을 얻고, 공백을 지워 비교한다.
       · 모두 VERIFIED이고 문언이 하나뿐이면 확정한다: 첫 판의 본문을 돌려주고 version_selection="SAME_PROVISION_AT_BOUNDARY"와 boundary_versions=[MST…]를 싣는다.
       · 문언이 다르면 ERROR(BOUNDARY_TEXT_DIFFERS).
       · 본문을 못 받았거나 조문이 없으면 ERROR(원래 사유).
     - article이 없으면 지금과 같다.
     - '나중에 공포된 판이 앞 판을 포함한다' 같은 추정은 법률 판단이므로 넣지 않는다. 부칙·경과규정 해석도 넣지 않는다.
 F3. source_review.py: 50·55행 호출을 _resolve(verifier, law_name, citation, as_of, current_date)로 바꾼다.
     - 어댑터의 resolve_statute가 article 인자를 받을 때만 citation.article을 넘긴다(inspect.signature). 받지 않는 시험용 가짜 어댑터는 예전대로 부른다.
     - TypeError를 잡는 방식은 쓰지 않는다. 내부 오류를 가린다.
 F4. packages/verification_engine/review_items.py 37행 앞에 BOUNDARY_TEXT_DIFFERS의 사람 말을 둔다: '같은 날 시행된 개정판이 여럿이고 인용 조문 문언이 판마다 달라 어느 판인지 확인 필요'.
     - 긴 문장이 먼저 와야 부분 일치에서 짧은 문장보다 먼저 걸린다.

3. 확인 시험(새 tests/test_tk158_same_boundary_versions.py, 패치에 있음 — 합성 연혁·본문, 네트워크 없음)
 - 같은 문언 → 확정(SAME_PROVISION_AT_BOUNDARY, boundary_versions=["200","201"], 대표 판 200)
 - 다른 조(제8조)만 판마다 다름 → 확정(인용 조문만 비교)
 - 인용 조문 문언이 판마다 다름 → ERROR(BOUNDARY_TEXT_DIFFERS) + 사람 말
 - article 없음 → 예전 ERROR 그대로
 - 어느 판에도 없는 조문 → 확정하지 않음
 - 연혁 순서를 뒤집어도 같은 결과
 - 검증기 주 경로(verify_statute)에서:
   · 같은 문언 → official_record에 version_selection이 실리고 BOUNDARY_ERROR 메모가 없음
   · 다른 문언 → official_record 없음 + BOUNDARY_TEXT_DIFFERS 사유
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 = bf93d3c + 패치, SQLite, LV_ALLOW_NETWORK=0)
 - 새 시험 9건 통과.
 - precheck_pr 전체 모드:
   · 고정 82.6 / 81.9, 확인 오탐 0, v2 일대일 42/56·41/54 — 변화 0
   · 은퇴 5세트 변화 0(후퇴 없음)
   · 평가 세트 문구 대조 '의심 없음'
   · 회귀·수용·기능 시험(법령·연혁·검토 항목·시간 적용 관련 시험 포함)에서 1건 실패: tests/regression/test_tk24_statutory_exclusion.py::…cold_budget(시간 예산 시험)
     → 사본과 기준 bf93d3c 양쪽에서 단독 2회씩 통과. 평가 측 실행이 겹친 부하로 판단하며, 이 변경과 무관한 영역(주장 분류 시간)이다.
 - 게이트: check_hardcoding_diff 통과, check_test_edits '삭제·표시 변경 없음', check_protected_paths 변경 없음.
 - 미검증:
   · case9 국가재정법 제96조의 실제 연혁에서 두 판의 제96조 문언이 같은지는 평가 환경에서 law.go.kr을 조회할 수 없어 확인하지 못했다.
   · 배포 뒤 온라인 case9 재실행(사용자 실행)에서 그 행의 사유가 확정 또는 '판마다 다름'으로 바뀌는지 본다.

5. 제출물·수용 기준
 - Steve_ACASiaLAW 기준 새 PR 하나.
   · 제품: legal_history.py, official_legal.py, source_review.py, review_items.py
   · 시험: 새 시험 1파일
   · 보호 시험(tests/acceptance/)은 바꾸지 않는다.
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · precheck_pr 평가 세트 문구 대조 통과
   · 고정·은퇴 세트 변화 0, 확인 오탐 0
   · 보호 시험 T11 통과
 - 법률 판단 엔진 변경이므로 수용 SHA에서 평가 측이 verify_all 전체 모드를 한 번 돈다.
```

### 2-41-3. 사용자 'TK-161은 권고대로 (가)' (11-13)
- 순서:
  1. TK-161 외 0.20.0 대상을 모두 병합하고 배포한다.
  2. case9를 3회 온라인 측정한다(사용자 실행).
  3. 측정 근거로 TK-161 지시를 낸다.
  4. 후속판으로 배포한다.
- 자세한 내용은 계획 문서 6.12절에 있다. 구현 측이 지금 할 일은 없다.

### 2-41-4. TK-159 지시(전달판)
- 패치: [patches/TK-159_evidence_basis_on_bf93d3c.diff](patches/TK-159_evidence_basis_on_bf93d3c.diff)

```
[TK-159 판정별 공식 원문 근거 구간(B1)]  기준 SHA: bf93d3c(Steve_ACASiaLAW)  평가 측 사본: 9eec3d9
보완 패치: docs/handoff/patches/TK-159_evidence_basis_on_bf93d3c.diff
 - bf93d3c → 사본 차이 전부: 제품 3파일(새 1) + 새 시험 1파일, git apply 가능
대상 릴리스: 0.20.0. TK-158과 겹치는 파일이 없다(둘 다 bf93d3c 기준, 병합 순서 무관). TK-160·163·162가 이 결과를 쓴다.

0. 배경(계획 문서 3절 TK-159, 근거 Stanford RegLab 환각 연구·LegalBench-RAG 근거 구간 평가)
 - 판정은 서면 쪽 위치(citation.span)만 남긴다.
 - 공식 원문 쪽에서 '어느 판결·어느 판·어느 구간을 근거로 했는지'와 '근거를 못 찾은 것(조회 실패)인지, 찾았는데 다른 것(판단)인지'가 결과 JSON에서 구분되지 않는다.

1. 원인(줄 번호는 bf93d3c 기준)
 C1. packages/legal_engine/verifier.py 213~243행 result.data["verdicts"] 사전에 근거 칸이 없다.
     - official_record는 실리지만 그 모양이 경로마다 다르다(판례: source_id·holding·summary, 공식 법령: law_id·version_id, 내부 사본 법령: law_name·text).
 C2. 같은 파일 Level 3 인용 대조(474~497행)는 공식 원문과의 유사도·판정만 남기고, 인용문이 원문의 어디와 맞았는지(구간)는 남기지 않는다.
     - packages/common/textutil.py 105행 contains_fuzzy_normalized는 최고 유사도만 돌려준다.

2. 고칠 것(보완 패치와 같음 — 판정·점수는 바꾸지 않는다)
 F1. textutil.py에 locate_fuzzy_normalized(h, n) → (유사도, 시작 위치)를 더한다.
     - contains_fuzzy_normalized와 같은 창 비교(len(n)//4 간격, quick_ratio 가지치기)를 쓴다.
     - 정확히 포함되면 (1.0, find 위치)를 돌려준다.
     - 기존 함수는 바꾸지 않는다.
 F2. 새 packages/legal_engine/evidence_basis.py
     - quote_span(인용문, 공식 원문):
       · normalize_quote로 정규화한 문자열 기준의 [start, end), similarity를 낸다.
       · 그 문자열의 SHA-256(text_sha256)과 길이, 발췌(최대 200자)를 함께 낸다. 원문 전문은 싣지 않는다.
     - build_basis(verdict) → {basis_status, source, passage}
       · source 종류:
         - OFFICIAL_CASE: 판례 source_id·법원·선고일·사건번호·링크·객체 참조
         - OFFICIAL_LAW: 법령 ID·판 번호(MST)·시행일·version_selection·링크·객체 참조
         - MIRROR_LAW: 내부 사본 법령. 공식 응답과 구분한다
         - DETERMINISTIC_RULE: 형식·범위 규칙
       · passage: 판례는 review["quote_span"], 법령은 review["provision"](경로·문언 해시·발췌)
       · basis_status:
         - SOURCE_MATCHED / SOURCE_MISMATCHED / SOURCE_FOUND_NOT_DECIDED(원문 있음)
         - LOOKUP_FAILED / NOT_FOUND / NO_SOURCE(원문 없음)
         - RULE_BASED(공식 원문 없이 형식 규칙으로 정한 불일치. 예: 아직 오지 않은 연도의 사건번호)
         - MISSING_BASIS(확인·불일치 판정인데 근거가 없는 경우. 드러내기만 하고 판정은 바꾸지 않는다)
 F3. verifier.py
     - Level 3 판정 직후(497행 뒤) quote_span을 review["quote_span"]에 남긴다. 필드 표시: 전문 있으면 full_text+holding+summary, 없으면 holding+summary.
     - verdicts 사전에 "evidence_basis": build_basis(v)를 더한다(240행 뒤).

3. 확인 시험(새 tests/test_tk159_evidence_basis.py, 패치에 있음 — 시험용 내부 Mirror의 가상 판례·법령, 합성 문장)
 - 모든 판정에 알려진 basis_status가 있고 MISSING_BASIS 0
 - 인용 일치 → SOURCE_MATCHED + 판례 식별자 + 정규화 구간·해시·발췌
 - 조회 불가 → 원문 없음 상태(불일치로 보고하지 않음)
 - 메타데이터 불일치 → SOURCE_MISMATCHED + 식별자
 - 형식상 불가능한 사건번호 → RULE_BASED + 규칙 이름
 - locate_fuzzy_normalized의 유사도 = contains_fuzzy_normalized 끝까지 훑은 최고값(3꼴)
 - quote_span 해시 = 정규화 문자열 해시, 빈 입력 None
 - 공식 법령(가짜 어댑터) → OFFICIAL_LAW + 판 번호·시행일 + 조문 해시·경로
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 9eec3d9, SQLite, LV_ALLOW_NETWORK=0)
 - 새 시험 10건 통과.
 - 고정 2세트 판정 60건의 근거 상태:
   · CONTRADICTED 15 → RULE_BASED(첫 판에서는 MISSING_BASIS로 나와 F2에 RULE_BASED를 넣었다)
   · CONTRADICTED 2 → SOURCE_MISMATCHED
   · PARTIALLY_VERIFIED 4 → SOURCE_MATCHED
   · UNVERIFIED 39 → LOOKUP_FAILED
   · MISSING_BASIS 0
 - precheck_pr 전체 모드(+ 법률 엔진·LV·TK-150번대·시간 적용 시험): 종료 0
   · 고정 82.6 / 81.9 / 오탐 0 변화 0
   · 은퇴 5세트 후퇴 없음
   · 평가 세트 문구 대조 통과
 - 게이트: check_hardcoding_diff 통과, check_test_edits '삭제·표시 변경 없음', check_protected_paths 변경 없음.
 - 미검증:
   · 실제 공식 판결문 전문에서의 구간 정확도(온라인, 배포 뒤 case9·탐침 B의 결과 JSON으로 확인)
   · 인용 대조 1회당 창 비교가 한 번 더 도는 비용(오프라인 전체 시험 시간 변화로 간접 확인만 했다)

5. 제출물·수용 기준
 - Steve_ACASiaLAW 기준 새 PR 하나.
   · 제품: textutil.py, evidence_basis.py(새), verifier.py
   · 시험: 새 시험 1파일
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · 고정·은퇴 세트 변화 0, 확인 오탐 0
   · 성능 시험(test_regex_performance 등) 통과
 - 법률 판단 엔진 변경이므로 수용 SHA에서 평가 측이 verify_all 전체 모드를 한 번 돈다.
```

### 2-41-5. TK-160 지시(전달판, TK-159 병합 뒤 착수)
- 패치: [patches/TK-160_claim_three_way_on_TK-159.diff](patches/TK-160_claim_three_way_on_TK-159.diff)

```
[TK-160 주장 판정 3분류(근거 일치·근거와 모순·근거 부족) + 근거 의무(B2)]  기준: TK-159 적용 트리(bf93d3c + TK-159 패치)  평가 측 사본: 9855fbf
보완 패치: docs/handoff/patches/TK-160_claim_three_way_on_TK-159.diff
 - TK-159 사본(9eec3d9) → 사본 차이 전부: 제품 1파일 + 새 시험 1파일, git apply 가능
선행: TK-159 병합. TK-159 PR이 병합된 Steve 위에서 브랜치를 만든다.
대상 릴리스: 0.20.0. 화면 표시(3분류 배지)는 #271 병합 뒤 TK-163과 함께 지시한다.

0. 배경(계획 문서 3절 TK-160, 근거 ContractNLI 지지·모순·언급 없음 + 근거 구간)
 - '법률적으로 무리한 주장' 행은 basis(UNCONFIRMED·CONTENT_MISMATCH·CONTRADICTION·OFFICIAL_CONFIRMED·DISTINGUISHABLE·FABRICATION_SUSPECTED)와 판정 문구만 가진다.
 - 이 행이 '근거가 주장과 어긋난다'는 것인지 '근거를 확인 못 했다'는 것인지가 같은 표·같은 무게로 보인다.
 - 공식 원문 구간 없이 '불일치'로 읽히는 행도 생길 수 있다.

1. 원인(줄 번호는 bf93d3c 기준 — TK-159는 이 파일을 바꾸지 않는다)
 C1. packages/legal_engine/argument_validity_verifier.py 144행 HallucinationTableRow와 to_dict(178~208행)에 근거 상태와 연결된 3분류가 없다.
 C2. 같은 파일 474~496행 basis 결정은 판정 상태(status)만 본다. 그래서 근거 구간(TK-159 evidence_basis)이 없어도 CONTENT_MISMATCH가 될 수 있다.
     - 예: 형식 규칙 위반(법원 부호 불일치)이 status CONTRADICTED로 와서 CONTENT_MISMATCH가 된다. 고정 2세트에서 30행.

2. 고칠 것(보완 패치와 같음 — 기존 basis·판정 문구·error_category는 바꾸지 않고 덧붙인다)
 F1. CLAIM_VERDICTS("SUPPORTED","CONTRADICTED","INSUFFICIENT")와 한글 라벨(근거 일치·근거와 모순·근거 부족)을 둔다.
 F2. classify_claim(basis, evidence_basis, grounded_quote) → (3분류, 낮춘 사유):
     - evidence_basis.basis_status == RULE_BASED → INSUFFICIENT('인용 형식 오류로 근거를 확인할 수 없음')
     - basis ∈ {CONTRADICTION, CONTENT_MISMATCH}:
       · 공식 원문(source 있고 RULE_BASED·MISSING_BASIS 아님) + 근거 구간(passage 또는 판시 근거 발췌 grounded_evidence_quote)이 있으면 CONTRADICTED
       · 아니면 INSUFFICIENT('공식 원문의 근거 구간이 없어 모순으로 단정하지 않음')
     - basis == OFFICIAL_CONFIRMED: 공식 원문이면 SUPPORTED, 아니면 INSUFFICIENT(사유 명시)
     - 그 밖(UNCONFIRMED·DISTINGUISHABLE·FABRICATION_SUSPECTED 등) → INSUFFICIENT
 F3. HallucinationTableRow에 evidence_basis(dict)·grounded_evidence_quote(str) 칸을 더한다(@dataclass 바로 아래에 둔다).
     - 행을 만드는 곳(705행 근처)에서 item["verdict"]["evidence_basis"]와 item["grounded_evidence_quote"]를 넘긴다.
 F4. to_dict에 claim_verdict·claim_verdict_label·claim_verdict_note·claim_evidence(TK-159 근거)를 더한다.

3. 확인 시험(새 tests/test_tk160_claim_three_way.py, 패치에 있음 — 합성 값)
 - classify_claim 10꼴(원문 구간 있는 불일치 → 모순, 판시 근거 발췌 → 모순, 구간 없는 모순 → 근거 부족, 조회 실패·형식 규칙 → 근거 부족, 공식 확인 → 근거 일치 등)
 - 근거 구간 없는 CONTRADICTED 0(다섯 꼴)
 - to_dict: 3분류 칸이 실리고 기존 basis·validity_verdict는 그대로
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 9855fbf, SQLite, LV_ALLOW_NETWORK=0)
 - 새 시험 12건 통과.
 - 고정 2세트 행 분포:
   · CONTENT_MISMATCH 30 → 근거 부족(사유: 인용 형식 오류)
   · UNCONFIRMED 12 → 근거 부족
   · 모순·일치 0(오프라인은 공식 DB 미조회 조건이라 예상된 값)
 - precheck_pr 전체 모드(기준 TK-159 사본, + 주장 표·보고서·화면 관련 시험): 종료 0
   · 고정 82.6 / 81.9 / 오탐 0 변화 0
   · 은퇴 5세트 후퇴 없음
   · 평가 세트 문구 대조 통과
 - 게이트: check_hardcoding_diff·check_test_edits·check_protected_paths 통과.
 - 미검증:
   · 공식 DB 조회 조건에서 모순·일치 분포(배포 뒤 case9·탐침 B 온라인 결과로 확인)
   · 3분류 macro-F1(법률가 라벨, v1.0 단계 TK-166)

5. 제출물·수용 기준
 - TK-159 병합 뒤 Steve_ACASiaLAW 기준 새 PR 하나.
   · 제품: argument_validity_verifier.py
   · 시험: 새 시험 1파일
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · 고정·은퇴 세트 변화 0, 확인 오탐 0
   · 근거 구간 없는 CONTRADICTED 0
```

### 2-41-6. #271 병합을 기다리는 티켓
- 대상: TK-157b(경고 묶기·집계 화면), TK-162(판례 변경 추적 — 새 경고 유형에 #271 display_text 한글 이름 필요), TK-163(원문 대조 보기), TK-164(사건 연대표), TK-160 화면 배지.
- 모두 #271이 고치는 app.js·display_text와 겹친다. #271 병합 뒤 그 위에서 사본을 만들어 사전 검증하고 지시한다.

### 2-41-7. #271·#274·#275 판정 (11-13)
- #271: head는 여전히 `044dcee`다. 보완 3(NEXT 2-40-5) 커밋이 아직 없어 판정을 바꾸지 않는다(보완 3 대기).
- #274(TK-157a) 수용:
  - head `2044c36` = 사본 `7c7456a`(diff 0), 필수 CI 성공(인용).
  - 엔진 변경이 아니라 verify_all 전체 모드는 생략한다.
  - 코멘트: https://github.com/stevelee0119/ACASia_LAW/pull/274#issuecomment-6865325335
- #275(TK-158) 수용:
  - head `258d8f0` = 사본 `a5746ec`(diff 0), 필수 CI 성공(인용).
  - verify_all 전체 모드 종료 0(평가 측 재실행): 전체 10,037·화면 197·수용 1,280·원장 2,357, 실패 0.
  - 코멘트: https://github.com/stevelee0119/ACASia_LAW/pull/275#issuecomment-6865635061
- 병합은 사용자 승인 대기다.

### 2-41-8. 사용자 '#274, 275 병합' (11-13)
- 병합 결과:
  - #274 → Steve `2708865`(expectedHeadSha `2044c36`)
  - #275 → Steve `b94750b`(expectedHeadSha `258d8f0`)
- 병합 뒤 확인(평가 측 재실행, `b94750b`):
  - 두 PR의 새 시험과 보호 시험 test_ft_protected(T11 포함)가 통과했다.
  - TK-159 보완 패치는 `b94750b`에 그대로 적용된다(git apply --check). TK-159 지시는 Steve 최신 위에서 진행하면 된다.

## 2-42. 법률 벤치마크 도입안 독립 검토 (11-13, 사용자 첨부 지시문 '상업적 이용 가능 법률 벤치마크 도입안')
- 보고서: [../scorecards/benchmark_adoption_review_2026-11-13.md](../scorecards/benchmark_adoption_review_2026-11-13.md)(검토 SHA `b94750b`).
- 판정:
  - 전체 '일부 채택'.
  - ContractNLI 조건부 채택(구성요소 시험).
  - LegalBench-RAG·CUAD·MAUD·LegalBench·Harvey LAB 보류.
  - KBL 제외(사용자 결정).
- 평가 측 할 일:
  - P0: KBL 경로 정리, EVALUATION_V2 5절 개정, 허용 목록
  - P1: 자산 고정
  - P3: 어댑터
  - P4: 시범 실행(사용자 비용 승인)
  - P5: 전체 실행

### 2-42-1. BM-1·BM-2 지시(전달판)
- 패치: [patches/BM-1_2_nli_component_on_b94750b.diff](patches/BM-1_2_nli_component_on_b94750b.diff)

```
[BM-1·BM-2 공개 벤치마크(ContractNLI) 구성요소 시험 기반 — 채점기와 판정 진입점]  검토 SHA: b94750b(Steve_ACASiaLAW)  평가 측 사본: a28a66f
보완 패치: docs/handoff/patches/BM-1_2_nli_component_on_b94750b.diff
 - b94750b → 사본 차이 전부: 제품 3파일(새 1) + 새 시험 2파일, git apply 가능
근거 문서: docs/scorecards/benchmark_adoption_review_2026-11-13.md(평가 측 도입안 검토, 판정 '일부 채택' — ContractNLI만 조건부 채택)
대상 릴리스: 0.20.0(사용자 원칙: 최초 의도한 개선은 해당 릴리스에 포함)

0. 배경과 범위
 - ContractNLI(CC BY 4.0, 공식 사이트 원문 확인)는 '주장 하나가 문서에 의해 지지·모순·언급 없음인가 + 근거 구간'을 묻는다.
   · 제품의 참고자료 대조 판정(packages/rag_engine/review.py, 지지·모순·맥락·근거 부족)과 과제 구조가 같다.
 - 평가 측이 이 판정 구성요소를 영문 원형 그대로 재기 위해 필요한 제품 쪽 변경 두 가지를 이 PR로 넣는다.
   · 어댑터·실행·보고는 평가 측이 한다(scripts/benchmarks/, 실행 manifest, 대시보드 층).
 - 이 PR은 모델을 호출하지 않는다. 운영 동작(문서 전체 참고자료 대조)은 바꾸지 않는다.
 - 이 결과는 '영문 계약 NLI 구성요소 성적'일 뿐이다. 한국법 인용 진위나 주장 타당성의 성적이 아니다.

1. 관측한 부족·근본 원인(줄 번호는 b94750b 기준)
 C1. 판정 진입점 부재:
     - packages/rag_engine/review.py 257행 review_document가 문서 선정(library.select)·관련성 문턱·분할(_split_sources_into_batches)·재시도와 판정 요청 생성을 한 루프(442~448행)에 묶고 있다.
     - 판정만 따로 부를 방법이 없다.
     - 그래서 평가 어댑터가 프롬프트(RAG_REVIEW_SYSTEM_PROMPT)·스키마(ENVELOPE_SCHEMA)·근거 검증(162행 grounded_observations)을 복제해야 한다. 그러면 운영과 다른 판정을 재거나, 어댑터에 판단이 숨어든다.
 C2. 채점기 부재:
     - packages/evaluation/quality.py는 오류 유형 다중 라벨 지표(precision/recall/F1·false VERIFIED)만 있다.
     - 3분류 혼동행렬·macro-F1·근거 문자 구간 지표가 없어 ContractNLI 공식 지표를 재현할 수 없다.
     - 실행 실패(모델 오류·미지원)를 분모에 남기는 규칙도 이 과제에는 따로 정의되어 있지 않다.

2. 변경할 계약·구조(보완 패치와 같음 — 구현 방식은 바꿔도 되나 아래 입력·출력 의미와 실패 처리는 그대로)
 F1. BM-1 새 packages/evaluation/nli.py(+ __init__ 내보내기)
     - NLILabel(item_id, benchmark_id, benchmark_revision, document_id, case_family_id, hypothesis_id, split, label∈{ENTAILMENT, CONTRADICTION, NOT_MENTIONED}, spans=[[start,end)…])
       · NOT_MENTIONED에 구간이 있으면 거절한다.
       · 구간은 비어 있지 않고, 정렬되어 있으며, 겹치지 않아야 한다.
     - NLIPrediction(item_id, run_id, system_version, benchmark_revision, execution_status∈{OK, ERROR, UNSUPPORTED}, label, spans)
       · OK만 label을 가진다. ERROR/UNSUPPORTED는 label이 없다.
     - evaluate_nli(labels, predictions, split="TEST", bootstrap_samples, seed)
       · 거절: 중복 라벨·중복 예측·모르는 ID, 벤치마크 revision 섞임, run·system_version 섞임, case_family_id 분할 누출, 빈 집단.
       · 누락·ERROR·UNSUPPORTED는 'MISSING' 결과로 분모에 남긴다. NOT_MENTIONED로 바꾸지 않는다.
       · 지표: 혼동행렬(정답 3 × 결과 4), 클래스별 P/R/F1, macro-F1(3클래스 모두 정의될 때만), accuracy, completeness.
       · 근거 구간: 관계가 맞은 항목만 문자 단위로 비교한다. 관계가 틀리면 구간 재현 0이다.
       · 불확실성: case_family_id 단위 부트스트랩 macro-F1 95% 구간.
       · claim_scope="CLAIM_DOCUMENT_RELATION_ONLY"와 notice(한국법·인용 진위·주장 타당성이 아님, NOT_MENTIONED는 거짓·부존재가 아님)를 싣는다.
     - 기존 quality.py·schemas.py는 바꾸지 않는다.
 F2. BM-2 packages/rag_engine/review.py
     - build_review_request(document, sources, *, korean_profile, reference_date, batch):
       · 442~448행의 LLMRequest 생성과 with_review_context를 이 함수로 옮긴다.
       · review_document는 이 함수를 부른다. 요청 내용(system·user JSON·schema·max_tokens·metadata·input_contract)은 바이트 단위로 같아야 한다.
     - judge_claim_against_sources(claim_text, sources, router, *, policy, korean_profile=False, reference_date=None) → dict
       · 같은 요청·같은 역할(LLMRole.PRIMARY_REASONER)·같은 근거 검증(grounded_observations)으로 한 번 판정한다.
       · 문서 선정·관련성 문턱·분할·재시도·법률 판단은 하지 않는다.
       · 반환 status:
         - NO_PROVIDER(공급자 없음)
         - MODEL_FAILED(사용 안 됨·격리)
         - REJECTED(봉투 스키마 위반)
         - OK(관측 0개 이상)
       · 그 밖의 반환값: observations(근거 검증을 통과한 것만), rejected(거절 사유), executions(실행 기록).
 보존할 동작:
  - review_document의 요청·분할·재시도·관측 채택·기록은 그대로다.
  - grounded_observations의 거절 규칙(QUOTE_NOT_GROUNDED·INVALID_ITEM_SCHEMA·INVALID_ENVELOPE)은 그대로다.

3. 시험(패치에 있음 — 합성 값, 가짜 라우터, 네트워크 없음)
 - 새 tests/test_bm1_nli_scoring.py(14건):
   · 양성: 완전 일치 → macro-F1·span F1 1.0
   · 음성: 누락·ERROR·UNSUPPORTED가 분모에 남고 NOT_MENTIONED로 세지지 않음
   · 경계: 관계가 틀리면 구간 재현 0, 부분 겹침 0.5/0.5
   · 교차: 중복·모르는 ID·revision 섞임·버전 섞임·분할 누출 거절, 잘못된 정답 구간 3꼴 거절, OK/ERROR 라벨 규칙, 사건군 단위 구간·범위 고지
 - 새 tests/test_bm2_component_entry.py(5건):
   · 요청이 운영 상수(system·schema·input_contract)와 같음
   · 근거 있는 관측 반환
   · 근거 없는 인용 거절(QUOTE_NOT_GROUNDED)
   · 관측 0개는 OK
   · NO_PROVIDER·MODEL_FAILED(사용 안 됨·격리) 명시
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, 사본 a28a66f = b94750b + 패치, SQLite, LV_ALLOW_NETWORK=0)
 - 새 시험 19건 통과.
 - precheck_pr 전체 모드(+ 참고자료 대조·평가 계약 관련 기존 시험): 종료 0
   · 고정 82.6 / 81.9 / 오탐 0 변화 0
   · 은퇴 5세트 후퇴 없음
   · 평가 세트 문구 대조 통과
 - 게이트: check_hardcoding_diff 통과, check_test_edits '삭제·표시 변경 없음', check_protected_paths 변경 없음.
 - 미검증:
   · 실제 모델로 ContractNLI 문항을 판정한 성능(평가 측 P4 시범 실행, 사용자 비용 승인 뒤)
   · 영문 NDA 전문을 참고자료 하나로 넣을 때의 길이 한도(시범 실행에서 확인)

5. 제출물·수용 기준
 - Steve_ACASiaLAW 기준 새 PR 하나.
   · 제품: packages/evaluation/nli.py(새)·__init__.py, packages/rag_engine/review.py
   · 시험: 새 시험 2파일
   · 보호 시험(tests/acceptance/)은 바꾸지 않는다.
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · 고정·은퇴 세트 변화 0, 확인 오탐 0
   · review_document 관련 기존 시험(참고자료 대조·Drive RAG) 통과
 - 하지 말 것:
   · 어댑터·정규화표(SUPPORTS→ENTAILMENT 등)를 제품 코드에 넣지 않는다. 평가 측 스크립트의 몫이다.
   · 벤치마크 원문·정답을 저장소에 넣지 않는다.
```


## 2-43. #271·#276 판정 (11-13, 사용자 '#276, 271 판정준비 완료')
- #271 head `87a5563`:
  - 보완 3 사본(79c1671)과 diff 0이다(평가 측 재실행).
  - CI 테스트 4개 작업 중 3개가 같은 화면 시험 1건으로 실패했다(CI 결과 인용). 1개(run 43513970921 SQLite)는 통과했다.
  - 원인 2건을 평가 측 재실행으로 확인했다(지연 주입 27조합, 병합 트리 6/27 실패, 사본 27/27 통과):
    - C1: 시험 동기화(닫힌 <details>의 innerText)
    - C2: 제품(표시 표보다 결과가 먼저 상태에 들어가 영문 코드가 잠시 보임)
  - 판정: **보완 4 필요**(아래 전달판). 보완 3 화면은 사용자 확인을 마쳤다. 보완 4는 정상 상태의 표시를 바꾸지 않는다.
- #276: 2-43-2에 기록.

### 2-43-1. #271 보완 4 지시(전달판)
```
[#271 TK-155 보완 4 — CI 화면 시험 간헐 실패(참고문헌 처리 기록) 원인 2건]  검토 SHA: 87a5563(#271 head)  평가 측 사본: c9e8183
보완 패치: docs/handoff/patches/TK-155_supplement4_on_pr271_87a5563.diff
 - 87a5563 → 사본 차이 전부: 제품 1파일(app.js 3줄) + 기존 PR 시험 파일 1개(이 PR이 새로 만든 파일)
 - git apply 가능. Steve b94750b + #276 병합 트리에도 충돌 없이 적용됨.

0. 관측(CI 결과 인용)
 - 실패한 시험: tests/test_tk155_ui_cleanup.py::test_reference_processing_record_has_no_codes_and_korean_time
 - 실패 메시지: AssertionError: assert '조회 2026-11-13 10:00' in ''
 - 실패한 작업 3개(같은 시험만 실패, 나머지 11,546건 통과):
   · run 43513977769 SQLite
   · run 43513977769 PostgreSQL
   · run 43513970921 PostgreSQL
 - 통과한 작업 1개: run 43513970921 SQLite
 - 결론: 결정적 실패가 아니라 경쟁 상태다.

1. 원인(평가 측 재실행으로 확인, 줄 번호는 87a5563 기준)
 C1. 시험 동기화 결함 — 닫힌 <details> 안의 innerText
   - 참고문헌 처리 기록(.reference-section)은 접힌 <details class="reference-status-line"> 안에 그려진다.
     · referenceStatusLine, app.js 2265~2277행
   - 탭을 누르면 workflow.js activate(275~277행)가 'await refresh(); renderFindings();'로 한 번 더 그린다.
   - 결과 적재(app.js 1948행 loadResults → 1963행 renderFindings)도 따로 그린다.
     · 호출 경로 추적 결과, 한 번 열 때 .reference-section이 2번 생성된다.
   - 시험은 '첫 요소 attach 확인 → details를 연다 → inner_text' 순서로 읽는다.
     · 그 사이에 다시 그리기가 끼면 새 <details>는 닫혀 있다.
     · Chromium에서 닫힌 <details> 안 요소의 innerText는 ''다(재현으로 확인).
 C2. 제품 결함 — 표시 표보다 결과가 먼저 상태에 들어감
   - loadResults(app.js 1957·1959행)는 state.result를 넣은 뒤에야 loadFindingCategories(코드→한글 표)를 기다린다.
   - 그 사이 사용자가 탭을 누르면 표 없이 그려진다.
     · 이때 displayTables()는 {}다(60행 '표를 받기 전에는 코드를 그대로 둔다').
     · 그래서 INDEXED_PARTIAL·REFERENCE_PARTIALLY_READ·RELEVANT_REFERENCE_FOUND 같은 영문 코드가 잠시 화면에 나온다.
   - 이는 TK-155 목표('화면에 영문 코드 없음')와 어긋난다. 표를 서버로 옮긴 #271이 생긴 창이다.
 재현(평가 측 재실행, 응답 지연 주입 27조합):
   · 지연 대상: /finding-categories·/result·/issues 응답을 각각 0·300·900ms(issues는 0·150·600ms) 늦춘다.
   · #271 병합 트리: 6/27 실패(빈 문자열 또는 영문 코드 노출)
   · 사본: 27/27 통과

2. 고칠 것(보완 패치와 같음)
 F1. app.js loadResults:
     - 'await loadFindingCategories(options);'를 state.result·state.findings 대입 앞으로 옮긴다.
     - 옮긴 뒤 generation 확인을 한 번 더 한다.
     - 결과·발견 목록 조회, workflowUI.refresh, 그리기 순서는 그대로 둔다.
 F2. 실패한 시험을 '열림 상태와 무관한 읽기 + 자동 대기'로 바꾼다:
     - expect(section).to_contain_text("조회 2026-11-13 10:00")로 마지막 그리기를 기다린다.
     - 그 뒤 section.text_content()로 읽는다.
     - details를 여는 page.evaluate는 뺀다.
     - 기존 단언 4개(코드 없음·한국 시각·서비스 계정 등 문구·None 없음)는 모두 유지한다(assert 수 4 → 4).
 F3. 회귀 시험 test_reference_record_shows_no_codes_while_display_tables_load를 추가한다:
     - add_init_script로 /finding-categories 응답만 1.5초 늦춘다.
     - 검토 탭을 누르고 600ms 뒤에 확인한다: 이 시점의 .reference-section에 코드가 0개여야 한다.
     - 그 뒤 '일부 색인' 표시와 코드 0개를 확인한다.
     - 이 시험은 87a5563 app.js에서 실패하고, F1 적용 뒤 통과한다(양·음성 대조 확인).
 하지 말 것:
   - 시험에 wait_for_timeout만 늘려 맞추지 않는다.
   - details 열림 상태를 강제로 유지하는 제품 변경은 이번 범위가 아니다(탭 전환 시 접히는 기존 동작 유지).

3. 평가 측 사전 검증(평가 측 재실행, 사본 c9e8183, SQLite, LV_ALLOW_NETWORK=0)
 - tests/test_tk155_ui_cleanup.py 34건 통과.
 - 지연 주입 27조합 통과(병합 트리 6/27 실패와 대조).
 - precheck_pr --quick(+ test_tk155_ui_cleanup·test_frontend_* 19파일): 종료 0
   · 고정 82.6 / 81.9 / 오탐 0 변화 0
   · 평가 세트 문구 대조 통과
 - 게이트:
   · check_test_edits: 기존 시험의 삭제·표시 변경 없음, assert 약화 경고 없음
   · check_hardcoding_diff: 통과
   · check_protected_paths: 변경 없음
 - 화면: 정상 상태의 표시는 바뀌지 않는다(일시적 코드 노출만 없앰). 그래서 새 화면 확인은 요청하지 않는다.
 - 미검증: CI 러너에서 반복 실행한 안정성(제출 뒤 CI 4개 작업 결과로 확인).

4. 제출물·수용 기준
 - 같은 PR(#271)에 커밋을 추가한다.
 - 수용 기준:
   · 필수 CI 4개 테스트 작업 모두 성공
   · 위 두 시험 통과
   · 고정·은퇴 세트 변화 0
   · 보호 경로 변경 없음
```

## 2-44. 법률 벤치마크 도입안 재평가 r2 (11-13, 사용자 '영어권 … 채택할 필요가 없는것 아닐까? … KBL은 이용허락과 적합성을 확인한 범위에서 보조 평가로 검토', 첨부 지시문 '비상업적 연구')
- 보고서: [../scorecards/benchmark_adoption_review_2026-11-13_r2.md](../scorecards/benchmark_adoption_review_2026-11-13_r2.md)(검토 SHA `b94750b`). r1의 영어권·KBL 판정과 계획(P0·P3~P5)을 대체한다.
- 판정:
  - 주 평가는 한국법 독립 평가(유지·보강).
  - 영어권 자료 도입은 전부 제외한다. ContractNLI 조건부 채택과 시범 비용 승인 요청은 철회한다. 지표 정의만 방법으로 채택한다.
  - KBL은 statute_number_and_content_matching_qa 하나만 보조 채택 후보다(조건 확인 대기, 시범 R3).
    - 현재 고정 과제 statute_hallucination_qa는 제품 평가에서 제외한다(모델 단독, 기준시점 지난 정답).
    - 나머지 과제는 제외한다.
- **2-42-1 BM-1·BM-2 지시는 보내지 않는다.**
  - BM-1은 라벨을 TK-160 3분류로 바꿔 사본 사전 검증 뒤 다시 지시한다.
  - BM-2는 목적을 한국법 구성요소 시험으로 바꿔 함께 지시한다.
- 평가 측 할 일:
  - R0: 평가 PR — KBL 층을 제품 성적표에서 분리, 과제 교체, ContractNLI 계획 삭제(보호 경로, 사용자 승인)
  - R1: 연구 기록·자산 manifest
  - R2: 어댑터
  - R3: 시범 실행(공식 DB 조회 환경)
  - R4: 보조 채택 판단

## 2-45. 벤치마크 재평가 r3 — 제로베이스·ACASIA 비상업 연구 설정 (11-13, 사용자 '벤치마크 재평가시에 kbl 이용과 관련해서, acasia의 목적을 비상업적 연구로 설정해서 검토해. … 벤치마크 적용 필요성까지 제로베이스에서 같이 검토해줘')
- 보고서: [../scorecards/benchmark_adoption_review_2026-11-13_r3.md](../scorecards/benchmark_adoption_review_2026-11-13_r3.md). r2의 2절·6절을 대체한다.
- 판정:
  - 외부 벤치마크는 주 평가 수단으로 필요하지 않다. 공백 두 곳(법령명 실재, 조문 내용 일치)의 외부 작성 사례 교차 확인에만 KBL 일부를 보조로 쓴다:
    - K1: statute_content
    - K2: statute_hallucination에서 법령명만 파생해 자체 라벨
  - 자체 '조문 바꿔치기' 생성 세트를 새 주 수단으로 채택한다. 고정 세트의 조문 내용 불일치는 3+3건, 한 분야뿐이다.
  - 영어권은 제외한다.
  - KBL 선택형 정답률은 제외한다.
- **BM-1·BM-2는 TK-166 착수 때까지 연기한다(지시 없음).** 소비처가 없다.
- 이용허락:
  - ACASIA 비상업 연구 설정에서 조건 A를 확인했다. 별도 서면 허락은 필요하다는 결론이 아니다.
  - 지킬 조건: 표시·변경 표시, 비상업 복제, 목적 변경 시 중지.
  - 측정 타당성 조건: 게이트·기준선 비연결, 자체 사례 재현 뒤 티켓, 학습 금지.
- 평가 측 할 일:
  - Z0: 평가 PR(KBL 층 분리·선택형 고정 해제)
  - Z1: 자체 생성기
  - Z2: KBL 어댑터
  - Z3: 시범(온라인, 모델 호출 0)
  - Z4: 사전 결정 규칙으로 유지·종료 판단

### 2-43-2. #276(TK-159) 판정: 수용 (11-13)
- head `5175a0c`는 사본 9eec3d9와 diff 0이다(평가 측 재실행). CI 성공(인용).
- verify_all 전체(기준 bf93d3c):
  - acceptance 1,280, full 10,038, browser 197: 실패 0.
  - regression_ledger: 시간 예산 시험 1건이 평가 측 동시 부하로 실패했다. 이 PR은 `classify_claims` 경로를 바꾸지 않는다. 부하 없이 재실행하니 3회 통과, `tests/regression` 2,357건 통과.
- 수용 코멘트를 게시했다. 병합은 사용자 승인으로 한다. 병합 뒤 TK-160 지시(2-41-5)를 낸다.

## 2-46. 사용자 결정 — 추가 벤치마크 미적용 (11-13)
- 사용자 원문: "추가 벤치마크는 필요성이 높지 않아보이니 미적용 하자."
- 구현 측 지시 없음. BM-1·BM-2 지시는 내지 않는다(TK-166 때 다시 판단).
- 평가 측 정리(Z0, 보호 경로 → 사용자 승인 뒤 평가 PR). 저장소에 남은 KBL 경로:
  - `scripts/evaluate_kbl.py`
  - `scripts/evaluation_dashboard.py`의 `--kbl-*` 인자·`public_benchmark` 층
  - EVALUATION_V2 5절 'KBL을 한국법 우선 과제로 채택'
  - `tests/acceptance/test_evaluation_v2.py`의 KBL 시험 5건
  - `check_protected_paths.py`·CODEOWNERS 항목
- 자체 조문 바꿔치기 세트(Z1)는 보류한다.

## 2-47. 사용자 '#276병합' (11-13) → TK-160 지시
- #276 병합: Steve `f594043`(머지 커밋, 평가 측이 사용자 지시로 실행, head 5175a0c 고정).
- TK-160 패치를 f594043에 그대로 적용했다(2-41-5 패치와 바이트 동일). 사본 6f0efaa에서 precheck --quick 종료 0, 고정 82.6 / 81.9 / 오탐 0, 게이트 3종 통과.
- 2-41-5를 대체하는 전달판:

### 2-47-1. TK-160 지시(전달판, f594043 기준)
```
[TK-160 주장 판정 3분류(근거 일치·근거와 모순·근거 부족) + 근거 의무(B2)]  기준: Steve_ACASiaLAW f594043(#276 TK-159 병합 뒤)  평가 측 사본: 6f0efaa
보완 패치: docs/handoff/patches/TK-160_claim_three_way_on_TK-159.diff
 - f594043 → 사본 차이 전부: 제품 1파일 + 새 시험 1파일, git apply 가능(TK-159 사본 기준 패치와 바이트 동일)
선행: TK-159 병합 — 충족(#276, f594043). 이 SHA에서 브랜치를 만든다.
대상 릴리스: 0.20.0. 화면 표시(3분류 배지)는 #271 병합 뒤 TK-163과 함께 지시한다.

0. 배경(계획 문서 3절 TK-160 — 외부 벤치마크는 쓰지 않는다(계획 6.15). 3분류는 제품 자체 판정 구분이다)
 - '법률적으로 무리한 주장' 행은 basis(UNCONFIRMED·CONTENT_MISMATCH·CONTRADICTION·OFFICIAL_CONFIRMED·DISTINGUISHABLE·FABRICATION_SUSPECTED)와 판정 문구만 가진다.
 - 이 행이 '근거가 주장과 어긋난다'는 것인지 '근거를 확인 못 했다'는 것인지가 같은 표·같은 무게로 보인다.
 - 공식 원문 구간 없이 '불일치'로 읽히는 행도 생길 수 있다.

1. 원인(줄 번호는 bf93d3c 기준 — f594043까지 이 파일은 바뀌지 않았다)
 C1. packages/legal_engine/argument_validity_verifier.py 144행 HallucinationTableRow와 to_dict(178~208행)에 근거 상태와 연결된 3분류가 없다.
 C2. 같은 파일 474~496행 basis 결정은 판정 상태(status)만 본다. 그래서 근거 구간(TK-159 evidence_basis)이 없어도 CONTENT_MISMATCH가 될 수 있다.
     - 예: 형식 규칙 위반(법원 부호 불일치)이 status CONTRADICTED로 와서 CONTENT_MISMATCH가 된다. 고정 2세트에서 30행.

2. 고칠 것(보완 패치와 같음 — 기존 basis·판정 문구·error_category는 바꾸지 않고 덧붙인다)
 F1. CLAIM_VERDICTS("SUPPORTED","CONTRADICTED","INSUFFICIENT")와 한글 라벨(근거 일치·근거와 모순·근거 부족)을 둔다.
 F2. classify_claim(basis, evidence_basis, grounded_quote) → (3분류, 낮춘 사유):
     - evidence_basis.basis_status == RULE_BASED → INSUFFICIENT('인용 형식 오류로 근거를 확인할 수 없음')
     - basis ∈ {CONTRADICTION, CONTENT_MISMATCH}:
       · 공식 원문(source 있고 RULE_BASED·MISSING_BASIS 아님) + 근거 구간(passage 또는 판시 근거 발췌 grounded_evidence_quote)이 있으면 CONTRADICTED
       · 아니면 INSUFFICIENT('공식 원문의 근거 구간이 없어 모순으로 단정하지 않음')
     - basis == OFFICIAL_CONFIRMED: 공식 원문이면 SUPPORTED, 아니면 INSUFFICIENT(사유 명시)
     - 그 밖(UNCONFIRMED·DISTINGUISHABLE·FABRICATION_SUSPECTED 등) → INSUFFICIENT
 F3. HallucinationTableRow에 evidence_basis(dict)·grounded_evidence_quote(str) 칸을 더한다(@dataclass 바로 아래에 둔다).
     - 행을 만드는 곳(705행 근처)에서 item["verdict"]["evidence_basis"]와 item["grounded_evidence_quote"]를 넘긴다.
 F4. to_dict에 claim_verdict·claim_verdict_label·claim_verdict_note·claim_evidence(TK-159 근거)를 더한다.

3. 확인 시험(새 tests/test_tk160_claim_three_way.py, 패치에 있음 — 합성 값)
 - classify_claim 10꼴(원문 구간 있는 불일치 → 모순, 판시 근거 발췌 → 모순, 구간 없는 모순 → 근거 부족, 조회 실패·형식 규칙 → 근거 부족, 공식 확인 → 근거 일치 등)
 - 근거 구간 없는 CONTRADICTED 0(다섯 꼴)
 - to_dict: 3분류 칸이 실리고 기존 basis·validity_verdict는 그대로
 - 기존 시험 단언 변경: 없음.

4. 평가 측 사전 검증(평가 측 재실행, SQLite, LV_ALLOW_NETWORK=0)
 - 병합 뒤 재확인(사본 6f0efaa = f594043 + 패치): precheck_pr --quick(+ TK-159 시험·argument_validity_verifier를 쓰는 기존 시험 27파일) 종료 0, 고정 82.6 / 81.9 / 오탐 0, 평가 세트 문구 대조 통과, 게이트 3종 통과.
 - 아래는 처음 사전 검증(사본 9855fbf = TK-159 사본 + 패치) 결과다.
 - 새 시험 12건 통과.
 - 고정 2세트 행 분포:
   · CONTENT_MISMATCH 30 → 근거 부족(사유: 인용 형식 오류)
   · UNCONFIRMED 12 → 근거 부족
   · 모순·일치 0(오프라인은 공식 DB 미조회 조건이라 예상된 값)
 - precheck_pr 전체 모드(기준 TK-159 사본, + 주장 표·보고서·화면 관련 시험): 종료 0
   · 고정 82.6 / 81.9 / 오탐 0 변화 0
   · 은퇴 5세트 후퇴 없음
   · 평가 세트 문구 대조 통과
 - 게이트: check_hardcoding_diff·check_test_edits·check_protected_paths 통과.
 - 미검증:
   · 공식 DB 조회 조건에서 모순·일치 분포(배포 뒤 case9·탐침 B 온라인 결과로 확인)
   · 3분류 macro-F1(법률가 라벨, v1.0 단계 TK-166)

5. 제출물·수용 기준
 - Steve_ACASiaLAW(f594043) 기준 새 PR 하나.
   · 제품: argument_validity_verifier.py
   · 시험: 새 시험 1파일
 - 수용 기준:
   · 3절 시험 통과, 필수 CI 성공
   · 고정·은퇴 세트 변화 0, 확인 오탐 0
   · 근거 구간 없는 CONTRADICTED 0
```

## 2-48. 사용자 'KBL 경로 정리 PR 생성' (11-13) → #277
- 평가 PR: https://github.com/stevelee0119/ACASia_LAW/pull/277 (`evaluator/kbl-cleanup` b36e023 → Steve f594043).
- 변경:
  - evaluate_kbl.py를 삭제했다.
  - dashboard·성적표의 public_benchmark를 NOT_APPLIED로 바꿨다.
  - EVALUATION_V2 5절을 '미적용'으로 고쳤다.
  - 보호 시험 KBL 5건(6사례)을 '미적용·입력 경로 없음' 시험 1건으로 바꿨다.
  - 보호 경로 목록·CODEOWNERS·역할 문서를 정리했다.
  - r1~r3 문서를 포함했다.
- 평가 측 재실행:
  - precheck --quick 종료 0, 고정 82.6 / 81.9 / 오탐 0.
  - 수용 시험 1,275 통과(1,280 − 6 + 1).
  - 대시보드 종료 0.
  - 게이트 통과(모두 평가 측 커밋).
- 구현 측 할 일 없음. 병합은 사용자 승인(보호 경로)으로 한다.

### 2-48-1. 사용자 '#277의 보호 시험 변경승인' (11-13)
- head b36e023의 tests/acceptance/test_evaluation_v2.py 변경을 승인받았다: KBL 시험 5건(6사례) 삭제, 미적용 시험 1건 추가, NOT_APPLIED 단언 보강.
- PR에 승인 기록 코멘트를 남겼다. 남은 선행요건은 필수 CI 성공이고, 병합은 사용자 지시로 한다.

## 2-49. 잔여 티켓 착수 시점 — 사용자 '그럼 #271 병합 이후에 계속하자' (11-13)
- 사용자 원문 앞 요청: "잔여 tk중에 현시점에서 구현착수 가능한 것들은 지시문을 생성해줘"
- 평가 측 점검 결과:
  - 지금 낼 수 있는 지시는 TK-160뿐이다(2-47-1에서 이미 냈다).
  - TK-157b·TK-163·TK-164·TK-160 화면 배지는 #271이 고치는 화면(app.js)·보고서(report_engine)·display_text와 겹친다.
  - TK-162는 새 지적 유형이 #271의 표시 이름 표(모든 유형 이름 필수 시험)와 맞물린다.
  - TK-161은 0.20.0 배포 뒤 측정이 선행이다.
- TK-162를 둘로 나누는 안을 검토했다:
  - 백엔드: 인용한 대법원 판례를 본문 검색으로 역조회하고 opinion_attribution.CHANGED_PRECEDENT_RE를 재사용해 판정에 참고 기록.
  - 지적·화면: #271 뒤.
  - 사용자 결정에 따라 중단하고, #271 병합 뒤 한꺼번에 사본 사전 검증·지시한다(사본 작업은 하지 않은 상태).
- #271 병합 뒤 순서(계획 6.11): TK-164 → TK-163 → TK-162 → TK-157b, 그리고 TK-160 배지(TK-163과 함께). 한 번에 하나씩 낸다.

### 2-48-2. #277 CI 경과 (11-14)
- head b36e023에서 pull_request 실행의 '점수 하락 게이트'가 실패했다(CI 결과 인용).
  - 원인: check_test_edits가 PR 병합 커밋(꼬리표 없음)까지 범위로 보아 '모든 커밋이 평가 측' 예외가 적용되지 않았다. 그래서 승인된 KBL 시험 5건 삭제를 미승인 삭제로 잡았다.
  - push 실행(같은 SHA)은 통과했다.
- 해결: 브랜치에 커밋 f5051c1(Steve, `Agent: evaluator`)이 올라왔다. docs/scorecards/approved_test_marks.json에 그 5건을 `mark: delete`로 등록했다(근거: 사용자 승인 코멘트 6866901823). 게이트 자체는 바꾸지 않았다.
- 평가 측 재실행: f594043 위 병합 커밋을 모의로 만들어 check_test_edits를 돌렸다. 5건이 '(삭제)' 승인으로 표시되고, 미승인 삭제는 0이다.
- head f5051c1의 필수 CI는 전부 성공이다(CI 결과 인용): 테스트 4개 작업·점수 하락 게이트·은퇴 세트 비교·CodeQL·Docker OCR.
- 병합 선행요건(보호 시험 승인·CI 성공)은 충족됐다. 병합은 사용자 지시로 한다.

### 2-43-3. #271(TK-155) 판정: 수용 (11-14, 사용자 '#271 판정준비 완료')
- head `a1f9862`는 보완 4 사본 c9e8183과 diff 0이다(평가 측 재실행). 중간 커밋 ef74f85·9cb2a54의 다른 접근은 최종 트리에 없다.
- CI는 전부 성공이다(인용). PR 실행은 현재 Steve f594043과의 병합 트리에서 돌았다.
- 화면: 보완 3은 사용자 확인 완료. 보완 4는 정상 상태 표시 불변.
- 수용 코멘트를 게시했다. 병합은 사용자 지시로 한다. 병합 뒤 2-49 순서로 진행한다.

### 2-43-4. 사용자 '#271,#277 병합' (11-14)
- 병합 결과: #271 → Steve `731ba5a`, #277 → `d9416e0`. 평가 측이 사용자 지시로 실행했고 head SHA를 고정했다.
- 병합 뒤 확인(평가 측 재실행, d9416e0):
  - TK-155·평가 계약·TK-159 시험이 종료 0이다.
  - 고정 82.6 / 81.9 / 오탐 0이다.
  - TK-160 패치가 그대로 적용된다(2-47-1 지시 유효).
- #277 구독을 해제했다.
- 다음: 2-49 순서로 TK-164부터 사본 사전 검증 → 지시.

### 2-47-2. #278(TK-160) 판정: 수용 (11-14, 사용자 '#278확인')
- head `87b93a5`는 사본 6f0efaa와 diff 0이다(평가 측 재실행). CI는 성공이다(인용, f594043 기준 실행).
- 현재 Steve d9416e0과의 병합 트리에서 verify_all 전체 모드를 단독 실행했다. 종료 0이다.
  - acceptance 1,275 / regression 2,357 / full 10,095 / browser 197 모두 실패 0.
  - 고정 82.6 / 81.9 / 오탐 0이다.
- 수용 코멘트를 게시했다. 병합은 사용자 지시로 한다. 화면 배지는 TK-163과 함께 지시한다.

### 2-47-3. 사용자 '#278병합' (11-14)
- #278을 Steve `1e2c351`로 병합했다(head 87b93a5 고정, 평가 측이 사용자 지시로 실행).
- 병합 결과 트리를 verify_all 전체를 돌린 평가 측 병합 트리(4c9eb6a)와 비교했다.
- 다음: TK-164(사건 연대표) 사본 사전 검증·화면 캡처 → 사용자 확인 → 지시.

## 2-50. TK-164 제외 (11-14, 사용자 'TK-164 사본 사전 검증 진행' 중 결정)
- 사전 검증 착수 중 충돌을 발견했다. TK-164(사건 연대표 화면·보고서)는 사용자 개선안(10-19)에 따라 TK-86(5be2251)이 지운 '사건 일지' 탭과 사실상 같은 기능이다.
  - TK-86은 보고서에서도 timeline을 뺐다: exporters.py·snapshot.py.
- 질문 'TK-164(사건 연대표)는 10-19 TK-86으로 지운 사건 일지 탭과 사실상 같은 기능 — 어떻게 진행할까요?'에 대한 사용자 선택: 'TK-164 제외'.
- 반영:
  - TK-164는 0.20.0에서 뺀다. 사본 작업은 하지 않았다.
  - TK-86 결정(탭 삭제, 보고서 timeline 제외)을 유지한다. 날짜 분석·날짜 모순 탐지와 결과 JSON의 timeline은 지금처럼 동작한다.
- 남은 0.20.0 순서: TK-163(+TK-160 배지) → TK-162 → TK-157b, 배포 뒤 TK-161.
