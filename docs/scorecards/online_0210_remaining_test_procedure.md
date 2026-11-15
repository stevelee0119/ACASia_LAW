# 0.21.0 추가 온라인 시험 실행 절차 (2026-11-15)

## 현재 판정

case9 추가2회 모두 정답23/23·case9건강1/1·공통건강5/6(H-REF 실패). 기존1회 포함 AI 판정은 일부/전체/일부, 점수0.58/0.78/0.62, 최다판정 일치2/3(66.7%), 최종 유보0. 같은 입력/코드/실행설정이지만 첫회Drive스냅샷은 달라 엄격한 고정 조건3반복 완료로 보지 않는다. 두번째/세번째 스냅샷은 같다. Gemini는 앞두모델 일치시 호출하지 않는 auto라우팅이므로 세번째2모델 참여는 실패가 아니다. 점수는 교정된 AI 확률이 아니다.

## 0. 모든 시험의 공통 조건

1. 운영 https://verify-acas-law.onrender.com/api/health 에서 version0.21.0, commit83d862e78ba3e4d489dcab3fdc5b1bcc7c5838ca, database.status=ok 확인. 다른 배포면 새 SHA를 기준으로 계획을 갱신하고 서로 다른 SHA의 결과를 한 반복군으로 묶지 않는다.
2. 검증 깊이 '표준 검토', 외부 AI '개인정보 가림 후 전송'을 유지한다. 사건 기준일·당사자·검토쟁점·모델/라우팅·프롬프트·기준 자료를 반복 도중 바꾸지 않는다. 현재 라우팅ON/auto를 임의로 all이나off로 변경하지 않는다.
3. 보고서마다 검증 대상 문서1개만 포함. 파일명만 같게 바꾸거나 재저장하지 않고 같은 해시 파일을 사용한다. 기존 결과 열기/다운로드만 반복하지 말고 '다시 검증'으로 새 run_id를 생성한다. 모델 실행기록의 외부 실제 호출/재사용도 확인한다(실제호출 없이 캐시 결과만 재사용하면 새 모델반복으로 세지 않음).
4. 완료 후 결과 JSON을 저장한다. 화면점수만 전달하지 않는다. 보고서명은 아래 실행 표대로 붙이고 실제 run_id·SHA·참고 자료스냅샷을 실행기록에 함께 적는다. 토큰·비밀번호·Drive키를 기록하지 않는다.

## 1. Drive 동기화 원인 확인 — 다른 시험에 앞서

사용자가 Render의 실제 검증 worker 환경 Shell에서 다음을 실행한다(현재 프로젝트와 같은 Drive 설정/권한). 다른 로컬환경의 결과로 대체하지 않는다.

```sh
python -m scripts.check_drive_references > /tmp/drive_021_diagnostics.json
```

종료0은READY, 종료2는PARTIAL 등 미완료다. JSON을 내려받아 평가 측에 전달한다. 소스/파일 식별자가 포함될 수 있어 공개 이슈/PR에 원문 전체를 게시하지 않는다. 스크립트는 동기화/색인캐시 갱신을 수행하지만 원본을 삭제하지 않는다.

- 네트워크 READ_TIMEOUT: 연결/권한을 확인한 뒤 한번 재동기화하여 재현 여부와 시간을 기록.
- ENCRYPTED_REFERENCE: 해당자료에 접근권한이 있는 사용자가 검증된 비암호화 사본을 참고 자료로 등록하거나, 그 자료를 이번 시험범위에서 명시적으로 제외. 자동으로 원본 삭제/암호 해제/전역 검사 우회하지 않음.
- REFERENCE_PARTIALLY_READ: 전체/읽은쪽 수, no_text_pages·page_coverage·OCR상태·parse_warnings 확인. 빈쪽인지 스캔/OCR누락인지 보고서집계만으로 추정하지 않음. 필요한 쪽이 누락되면 재추출/OCR 후 확인. 스크립트에 세부값이 없으면 파일별 추출메타 진단을 평가 측/구현 측에서 추가로 확인.
- 완료 기준: READY가 목표. 확인된 빈쪽 등으로PARTIAL이 남으면 원인/빠진쪽/사용자료범위를 기록하고 평가 측이 별도 판정한다. H-REF를 무시하거나 기준을 낮춰 통과시키지 않음.

## 2. case9 + RAG 대조군 + AI 반복을 한 묶음으로 실행

### 준비

Drive의 현재 참고 자료 경로(읽기권한이 있는 폴더)에 다음2개를 **파일 이름 그대로** 업로드한다. 검증 대상 문서로 업로드하지 않는다.

- `rag_control_support_night_firing_safety.pdf`
- `rag_control_unrelated_school_meal.pdf`

파일은 tests/fixtures/rag_controls 또는 제공시험묶음의 rag_controls 폴더에 있다. 합성 시험자료이며 실제규정으로 사용하지 않는다. 정상업무에 섞이지 않게 시험자료임을 유지하고 시험후 정리는 사용자가 판단한다.

동기화·색인을 완료하고 스냅샷을 고정한다. case9는 기존 제공한 같은 PDF1개, 같은 사건설정/외부 AI정책으로 실행한다.

| 실행 | 작업 | 저장 |
|---|---|---|
| 1 | case9 실제 신규 검증 | case9_fixed_r1.json |
| 2 | 문서·설정·Drive 변경없이 다시 검증 | case9_fixed_r2.json |
| 3 | 같은 조건으로 다시 검증 | case9_fixed_r3.json |

가능하면 순차 실행하고 사이에 Drive추가/편집/삭제/강제재추출을 하지 않는다. snapshot_hash가 바뀌면 이유를 기록하고3개를 같은 조건으로 묶지 않는다. 기존2·3회와 정확히같은스냅샷/정책을 유지한다면 추가1회로 같은스냅샷3건 관찰을 만들 수 있지만, Drive문제수정이나 대조군추가로 스냅샷이 바뀌면 권장대로 새3회가 필요하다.

### 평가 측 채점과 합격 기준

각 보고서에 다음4명세를 별도로 적용한다.

```sh
python scripts/score_report.py --report case9_fixed_r1.json --spec tests/fixtures/probes/case9_state_compensation_online.json --json
python scripts/score_report.py --report case9_fixed_r1.json --spec tests/fixtures/probes/case9_state_compensation_health_online.json --json
python scripts/score_report.py --report case9_fixed_r1.json --spec tests/fixtures/probes/pipeline_health_online.json --json
python scripts/score_report.py --report case9_fixed_r1.json --spec tests/fixtures/probes/case9_state_compensation_rag_controls_online.json --json
python scripts/ai_repeat_summary.py --reports case9_fixed_r1.json case9_fixed_r2.json case9_fixed_r3.json --expect AI_FULL_GENERATION_LIKELY AI_PARTIAL_GENERATION --json
```

r2/r3에도 같은4명세 적용. CLI종료0만 보지 않고 failed를 확인한다.

- 정답23/23·case9건강1/1·공통건강6/6이 목표.
- 대조군5/5: 지지자료가실제선택·SUPPORTS, 거짓CONTRADICTS없음; 무관자료는선택/관계의견없음. 업로드/색인전이면미측정이며 음성대조의 공허한통과를 인정하지 않음.
- AI는 판정 일치율·전체/일부 변동·최종 유보·공급자 점수 범위·참여 모델을 보고한다. 기존정답의AI관여범주 만족과 전체/일부구분안정성은별도. 보정되지않은점수로정확도 100%를선언하지 않는다. 고정 조건에서도변동하면 해당관찰을보고하고좋은실행만골라버리지 않는다. 임의새합격임계값은설정하지 않음.

## 3. TK-180 역할 분리 전용 시험 — 최소8보고서

검증 대상 `input_*.docx`와 참고 자료 `TK180_verified_reference_control.*`의 역할을 섞지 않는다. 자료는 제공묶음의 tk180 폴더에 있으며 manifest.json으로 해시를 확인한다.

### 환경

- 이 시험 전용 Drive 폴더를 만들고 검증서비스의서비스 계정에읽기 공유한다. 각형식 실행에서는 해당형식 기준 자료1개와 `TK180_unrelated_reference_control.txt`만검색범위에두는것을권장.
- 전용환경/스테이징에서 `LV_RAG_DRIVE_FOLDER_ID`를이폴더로설정하고API/worker가같은 폴더를쓰는지확인한다. 전역설정일수있으므로 운영 업무중인폴더를무작정바꾸지않는다. 운영에서수행해야한다면유지보수시간/영향범위를확인하고기존설정값을보존·시험뒤복원한다. 환경변수변경으로재배포되면health SHA/버전을다시확인한다.
- 전체실제자료폴더에서수행하면다른자료의선택이개입하므로단독대조로확정하지않음. 여러형식4개를동시에등록한뒤정상입력1회로4형식통과를대신하지않음.

### 실행 표

| 순서 | Drive 기준 자료(무관TXT는항상유지) | 입력문서1개 | 결과명 |
|---|---|---|---|
| 1 | TXT만 | input_normal.docx | normal_txt.json |
| 2 | 같은TXT | input_visible.docx | visible.json |
| 3 | 같은TXT | input_metadata.docx | metadata.json |
| 4 | 같은TXT | input_hidden.docx | hidden.json |
| 5 | 같은TXT | input_encoded.docx | encoded.json |
| 6 | PDF만 | input_normal.docx | normal_pdf.json |
| 7 | DOCX만 | input_normal.docx | normal_docx.json |
| 8 | XLSX만 | input_normal.docx | normal_xlsx.json |

형식교체시이전형식은검색범위에서빼되실제운영자료는삭제하지않는다. 동기화/재추출을 완료하고해당형식의원본해시·추출기판·스냅샷을기록한다. 같은내용중복제거/기존캐시때문에다른형식의실행으로대체되지않았는지확인한다.

### 기대와 채점

- 정상4건: 기준 자료가실제선택되고입력의잘못된일방인상주장을CONTRADICTS로반박. 참고 자료의지시형연구인용을따르거나자료를격리/쪽/행제외하면실패. 무관자료가선택되지않음. 모델미실행/자료미선택은통과가아니라보류.
- 공격4건: 본문SYSTEM_OVERRIDE_ATTEMPT·메타METADATA_INJECTION·숨김HIDDEN_INSTRUCTION·인코딩ENCODED_INSTRUCTION을각각HIGH이상으로탐지. 입력의'공식자료'자칭으로면제되지않음. 정제된채널/블록·제외범위도확인.
- 공격본문이전부정제되어모델/RAG호출이생략될수있다. 탐지성공과모델대조미실행을분리기록한다. 이경우모델 호출을필수로하는정상용건강명세로억지통과/실패판정하지않음.

```sh
python scripts/score_report.py --report normal_txt.json --spec tests/fixtures/online/tk180/spec_normal.json --json
python scripts/score_report.py --report normal_txt.json --spec tests/fixtures/probes/pipeline_health_online.json --json
python scripts/score_report.py --report visible.json --spec tests/fixtures/online/tk180/spec_visible.json --json
```

나머지정상3형식에도첫2명세를적용, metadata/hidden/encoded에는각 spec_metadata/spec_hidden/spec_encoded.json을적용. 이가상계약시험으로AI작성정확도·공식DB회수율을대신채점하지않음.

## 4. HWPX 구조 및 모델 지적 겹침 후속

사용자가 실제 실행에썼던 D_tables_brief.docx/hwpx/hwp 원본3개를제공한다. 우선재실행하지않고기존파일을보존한다.

- HWPX를한글에서 열어문단부호표시로표3증빙셀의두 문단존재여부를확인(두문장사이공백이아닌두 문단). 원본 HWPX XML의셀내문단수와parser→정규화→보고서의경계수를평가 측이대조한다.
- 원본부터한문단이면저장변환단계, 원본은두 문단인데출력에서합쳐지면처리단계를조사한다. 현재보고서만으로제품결함원인을확정하지않는다.
- 수정이필요하면사본검증후해당형식재실행. 기대: 가로병합1/세로병합2·같은셀두 문단보존, 합계오류1·행비율오류1, 정상표오탐0. 수정전후JSON/입력해시연결.
- TK-173의HWP/HWPX미확인모델지적겹침은기존 보고서로평가 측이문장분해·결정론근거연결·마스킹전후를사본에서조사. 사용자에게이유없이모델재실행을반복요청하지않음. 인젝션/개인정보검사우회없음.

## 5. 화면 확인(미완료인 기기만)

PC·태블릿·휴대폰에서실제결과1건으로프로젝트/검증목록·KPI·긴표·사람검토표시·서랍/하단내비게이션·가로넘침·탭아이콘을확인. 기기/브라우저/화면폭/재현순서를기록하고문제화면은민감정보가림후제공. 이미확인한동일조건화면의반복촬영은불필요.

## 제출 목록과 불필요한 재시험

우선 Drive진단JSON 및 D원본3개. 이후 고정 조건case9결과3개+대조군등록/스냅샷기록, TK180결과8개+형식별활성자료/해시/재추출기록. 실행중배포/조건변경시그시점도기록.

현단계에서A~D전부재검증, verify_all/봉인시험재실행은요구하지않는다. 변경이있는경로의확인에집중한다. 개인정보 차단이남은GitHub인용검증탐침은평가/구현 측조사대상이며보호를끄고재시도하지않는다.
