# ACASia_LAW

변호사의 법률문서 검토를 보조하는 검증 작업 공간입니다. 준비서면·소장·진술서 같은 서면을 올리면
인용한 판례·법령을 공식 출처와 대조하고, 사실관계·날짜·계산·증거 목록의 어긋남과 문서에 숨은 지시문을 찾아
**무엇을 다시 확인해야 하는지**를 보고서로 정리합니다.

- **확인한 것과 확인하지 못한 것을 나눕니다.** 공식 DB에서 찾지 못한 판례는 '미확인'이지 '부존재'가 아닙니다.
- **법률 판단을 대신하지 않습니다.** 진정성립·위조·고의와 주장의 당부는 사용자가 판단합니다.
- **AI 모델의 의견은 참고입니다.** 판정은 공식 출처와 결정론적 검사가 먼저 정합니다.

**현재 운영 버전:** 0.13.1 (2026-10-19 배포). 버전별 변경은 아래 표, 개발 중인 변경과 평가 결과는
[일자별 추이표](docs/scorecards/DAILY_TREND.md)를 보세요.

## 목차
- [버전별 변경 내역](#버전별-변경-내역)
- [핵심 원칙](#핵심-원칙)
- [무엇을 검사하나](#무엇을-검사하나)
- [빠른 시작](#빠른-시작)
- [배포와 배포 후 확인](#배포와-배포-후-확인)
- [한계](#한계)
- [문서 안내](#문서-안내)

## 버전별 변경 내역

<!-- RELEASES:START -->

> 릴리스 계열별 핵심 요약입니다. 버전별 상세는 [변경 이력](docs/RELEASE_HISTORY.md)에 있습니다. 이 표는 `docs/releases.json`·`docs/release_highlights.json`에서 자동으로 만들어집니다(`python scripts/update_readme.py`).

| 릴리스 | 기간 | 핵심 변경 |
|---|---|---|
| **0.14** (0.14.0) | 2026-10-25 | • 구조 탐지 추가: 사건 순서 역전(EVI-DATE), 문서 안 장소·서명자·수량 불일치(EVI-INCONS), 경위서 원문 통째 복제(EVI-COPY), 서증 원용 범위 초과(EVI-OVR, 세트 득점 없음)<br>• 고정 시험 개발 82.6 유지, 홀드아웃 80.1→81.9, 오탐 0건(0.13.1과 같은 조건)<br>• 인젝션 채널별 구조 탐지(TK-89), 정상 서술 지시문 오탐 방지(TK-92)<br>• 검토 화면 3단 개편·'확인이 필요한 내용' 요약, 저활용 탭 정리, 미확인 판례·법령 외부 AI 검증 프롬프트(TK-94) |
| **0.13** (0.13.0–0.13.1) | 2026-10-11 ~ 2026-10-18 | • 연락처 전체 범위 가림 완성(외부 모델 도달 0건)<br>• 서증 형식·번호 일관성, 금액 표기 검사 보강(TK-76)<br>• 고정 시험 개발 81.7→82.6, 홀드아웃 79.2→80.1, 오탐 0건<br>• 효율 라우팅 추가(기본 OFF), Drive 서비스 계정 전환(TK-80) |
| **0.12** (0.12.0) | 2026-10-10 | • 증거 목록 결번 판정 범위 정정(TK-67, 오탐 1→0)<br>• 계좌번호 종류 분류 개선(TK-58)<br>• 표준판례 표 행 단위 색인·주장별 대조(TK-71)<br>• Drive 대조 출력 잘림 방지(TK-68) |
| **0.11** (0.11.0) | 2026-10-09 | • 번호 붙은 입증방법 제목 인식, 목록 번호의 본문 중복 언급 제외(TK-64, 오탐 3→1)<br>• 법리 주장 선별 규칙·예산형 상한(TK-63)<br>• 모델 응답 형식·비용 기록 정리(TK-65) |
| **0.10** (0.10.0) | 2026-10-04 | • 고정 시험 개발 79.9→81.7, 홀드아웃 77.3→79.2, 오탐 증가 0<br>• 연락처·주민등록번호 표기 변형 가림, 구조화 요청의 실명 외부 도달 차단(TK-57·51)<br>• 업로드 개인정보 안내 1.1판 |
| **0.9** (0.9.0–0.9.13) | 2026-09-25 ~ 2026-09-30 | • 결정론 검사 확대: 없는 조문, 성립 불가 사건번호, 날짜·요일·경과일수, 표 합계·산식, 표결 정족수<br>• 법령명·약칭·행위시법 인식 정밀화, 법리 규칙 추가(사람 확인 항목)<br>• Drive 참고자료 관련도 선정·연결 기록, 인젝션·개인정보 탐지 확대<br>• 평가 채점기 v2 |
| **0.8** (0.8.0–0.8.8) | 2026-09-25 | • 인젝션 경로 전수 검사(북마크·양식 필드·ActualText·폭 0 문자 등)<br>• 사실 대조 재설계(같은 사건 문서끼리), 증거·금액 대조, 호증 서식 일반화<br>• 구현 감사표·실행 매니페스트 보강, 사건부호표 보충<br>• 작업 임차·예산 원장 결함 수정 |
| **0.7** (0.7.0–0.7.2) | 2026-09-25 | • 저장 공간 관리(사용량 표시·VACUUM), 보고서 고정본 압축(1건 477KB→66KB)<br>• 실행 매니페스트(엔진별 실행 기록)와 구현 감사표<br>• 법원–사건부호 불일치 판정, 헌재 사건번호 처리 수정 |
| **0.6** (0.6.0–0.6.9) | 2026-09-24 | • 법원–사건부호 호환 검사, 인용문 어절 대조, HWP 표 복원<br>• 법리 주장 검토 재설계(유형 분류 → 근거 조회 → 판단)<br>• 숨김 글자 탐지(투명·가림·저대비), 쪽별 OCR 품질 판정<br>• 휴지통 영구 삭제, HTTP 500 문의 번호 |
| **0.5** (0.5.0) | 2026-09-21 | • 인증·역할 기반 접근통제, 제품명 ACASia_LAW<br>• 세 모델(GPT·Claude·Gemini) 교차검증, AI 작성 판별·주장 타당성 검토<br>• 업로드 원본 암호화, 보고서 백그라운드 생성, 평가 하네스 v2 |
| **0.4** (0.4.0) | 2026-09-18 | • OCR·PostgreSQL(pgvector)·Celery, Render 배포·CI<br>• AI 관여 흔적 분석, 배포 진단(/api/diagnostics)<br>• 검토 흐름(판정 검토·쟁점표·보고서 확정) |
| **0.2** (0.2.0) | 2026-09-06 | • 최초 구현: 문서 파서, 인용 추출, 공식 출처 조회, 은닉 지시문 탐지, 감사추적 해시 체인 |

<!-- RELEASES:END -->

## 핵심 원칙

| 원칙 | 구현 |
|---|---|
| Source First | 사건번호·선고일·조문·계산·해시는 공식 API와 결정론적 엔진이 먼저 확인한다. LLM은 의미 비교·반대검증에만 쓴다. |
| Evidence First | 모든 Finding은 `Evidence`와 `SourceRecord`에 연결된다. |
| Human Final Decision | 위조·진정성립·고의에 관한 최종 평가는 사용자에게 남긴다. |
| Abstention | 확정이 불가능하면 `UNVERIFIED` / `ABSTAIN`으로 남긴다. |
| Provider Independence | OpenAI·Anthropic·Gemini·Local LLM을 교체 가능한 Provider로 구성한다. |
| Graceful Degradation | 한 Source나 모델의 장애가 전체 Job 실패로 이어지지 않는다(`PARTIAL_COMPLETED`). |
| Secure by Design | 문서는 자료이지 명령이 아니다. Tool 권한은 최소화한다. |
| Reproducibility | 파일·Source·모델·프롬프트 버전·결과를 추적한다. |

## 무엇을 검사하나

| 영역 | 검사 내용 | 판정의 근거 |
|---|---|---|
| 판례·법령 인용 | 사건번호 형식, 존재(조회 범위 내), 선고일·법원, 인용문, 시행 버전·조문 | 국가법령정보 공식 API. 형식상 성립할 수 없는 번호만 확정 판정 |
| 법률 주장 | 인용 판례 취지와의 상반, 사실관계 차이, 공식 DB 미확인 근거 | 규칙과 공식 원문. 모델 의견은 참고로만 표시 |
| 사실관계·날짜·계산 | 문서 안 진술 불일치(같은 대상의 장소·서명자·수량 충돌 포함), 같은 대상에 대한 사건 순서와 날짜의 역전, 달력에 없는 날짜·요일, 금액·이자 계산 | 결정론적 엔진. 불일치·역전은 확정이 아닌 검토 단서(B·C) |
| 증거 정합성 | 호증 목록의 결번·날짜·자료명, 첨부 여부, 진술서 형식, 다른 서면(경위서 등) 원문의 통째 복제, 서증 종류가 뒷받침할 수 있는 범위를 넘은 원용 | 문서 안 대조. 원용 범위는 서증 종류별 일반 기준으로 검토 단서(B·C)만 표시하고, 증명력은 사람이 판단 |
| 문서 속 숨은 지시문 | 흰 글자·작은 글자·가림·주석·메타데이터·폭 0 문자 등에 숨긴 AI 대상 지시 | 결정론적 포렌식, 모든 AI 호출보다 먼저 실행 |
| AI 작성 가능성 | 대화형 서두·면책 문구 같은 객관적 흔적과 모델별 판단 | 참고 신호. 모델 의견이 갈리면 판단 유보 |
| 개인정보 | 외부 모델에 보내기 전 성명·연락처·주민등록번호 등 가림 | 한국형 개인정보 탐지 |

판정 기준과 단계별 처리는 [시스템 구조와 검증 방식](docs/SYSTEM_GUIDE.md)에 있습니다.

## 빠른 시작

**Windows(로컬 단일 사용자):** `.\scripts\start-local.ps1` → http://127.0.0.1:8765
(포트가 사용 중이면 `.\scripts\start-local.ps1 -Port 8766`). 기존 데이터가 있으면 실행 전에 백업하고
`python -m alembic upgrade head`를 적용하세요.

**Linux·macOS:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn apps.api.main:app --reload      # http://localhost:8000
```

한국어 OCR을 쓰려면 시스템 패키지가 필요하다.

```bash
sudo apt install tesseract-ocr tesseract-ocr-kor
```

전체 구성(API + Worker + PostgreSQL/pgvector + Redis):

```bash
cp .env.example .env      # LV_PSEUDONYM_SECRET, POSTGRES_PASSWORD 등을 채운다
docker compose up --build
```

API Key가 하나도 없어도 동작한다. 이 경우 외부 Source 검증 항목은 `UNVERIFIED`로 표시되고,
결정론적 검사(은닉 텍스트·인젝션·포렌식·계산·타임라인)는 모두 정상 수행된다.

기본은 로컬 단일 소유자 모드다. 다중 사용자 운영은 `LV_AUTH_MODE=multi-user`와 HTTPS, 계정 초기 설정,
사건별 권한과 키 보관 설정이 필요하다([인증·권한·키 관리](docs/IDENTITY_SECURITY_INTEGRATION.md)).
시험 실행 방법은 [시스템 구조와 검증 방식](docs/SYSTEM_GUIDE.md#개발-환경에서-시험-실행)에 있다.

### 환경변수

| 변수 | 용도 |
|---|---|
| `LV_LAW_GO_KR_OC` | 국가법령정보 공동활용 OC (판례·법령 공식 검증) |
| `LV_KCI_KEY` | KCI 학술 API Key |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | LLM Provider. 기본 모델은 `config/providers.json`(gpt-6-luna · claude-opus-5-5 · gemini-3.8-flash). 보고서의 모델별 판정에는 "OpenAI · GPT-6 Luna"처럼 공급자와 모델명이 함께 표시된다 |
| `LV_OPENAI_MODEL` / `LV_ANTHROPIC_MODEL` / `LV_GEMINI_MODEL` | 모델 ID 덮어쓰기(공급자가 모델을 바꿨을 때) |
| `LV_LLM_CROSS_CHECK` | AI 교차검증 범위. `all`(기본, 사용 가능한 모델 모두) · `auto`(판례 의미·적용 검토에서만 신뢰도가 낮거나 중요도가 높을 때 반증 모델 사용, 다른 검토는 `all`과 같음) · `off`(1순위 모델 하나) |
| `LV_LLM_EFFICIENT_ROUTING` | 효율 라우팅(기본 OFF). `1`이면 작업별로 모델을 나눠 쓰고, `LV_LLM_CROSS_CHECK=auto`와 함께 법리 검토에서 의견이 엇갈린 항목만 세 번째 모델에 보낸다 |
| `LV_HTTP_TIMEOUT` | 외부 출처 요청 제한시간(초, 기본 12). law.go.kr 응답이 느리면 30 권장 |
| `LV_SOURCE_MIN_INTERVAL_SECONDS` | 같은 출처에 연달아 보내는 요청 간격(초, 기본 0.3) |
| `LV_PSEUDONYM_SECRET` | 실명-가명 매핑 암호화 키. **운영에서는 반드시 교체한다.** |
| `LV_DATABASE_URL` | 기본 SQLite. 운영은 `postgresql+psycopg://...` |
| `LV_CELERY_BROKER` | 설정하면 Celery Worker로 분산 처리한다. 없으면 인프로세스. |
| `LV_OCR_LANG` / `LV_INDEPENDENT_OCR` | OCR 언어(기본 `kor+eng`), 독립 OCR 교차검증 모드 |
| `LV_ALLOW_NETWORK=0` | 폐쇄망 모드. 외부 Adapter를 모두 비활성화한다. |

기본 설정은 `.env.example`, 추가 인증·작업·예산 설정은 [인증·권한·키 관리](docs/IDENTITY_SECURITY_INTEGRATION.md)와 [작업 복구·비용 원장](docs/OPERATIONS_DURABILITY.md)에 있다.

API Key는 Frontend LocalStorage나 평문 DB에 저장하지 않는다. 응답에도 키 값은 포함되지 않으며 보유 여부만 노출한다.

## 배포와 배포 후 확인

운영은 Render에서 Docker 런타임(OCR 포함)으로 돌린다. `render.yaml` 블루프린트로 웹 서비스·PostgreSQL·디스크·
환경변수를 한 번에 만들 수 있다. **영구 디스크 없이 배포하면 업로드 원본이 재배포 때 사라진다.**
절차는 [Render 배포](docs/DEPLOY_RENDER.md), 보고서·휴지통·저장 공간·오류 추적은 [운영 안내](docs/OPERATIONS_GUIDE.md)를 보세요.

### 배포 후 확인

관리자로 로그인한 브라우저에서 아래 주소를 연다. 비밀값은 응답에 포함되지 않는다.

| 주소 | 확인할 것 |
|---|---|
| `/api/health` | `commit`이 방금 병합한 커밋인지 |
| `/api/diagnostics` | OCR·디스크 내구성·저장소 암호화, AI 공급자별 키 보유와 `cross_check` 설정 (키가 있어도 쿼터 초과는 여기서 보이지 않는다. 실연동 점검이나 보고서의 불참 사유로 확인한다) |
| `/api/diagnostics/sources` | 이 서버에서 law.go.kr 사건번호 조회와 **판례 전문 조회**가 되는지. `verdict`가 `FULL_TEXT_UNAVAILABLE`이면 `steps[].message`가 원인이다(HTTP 상태, JSON이 아닌 응답, 형식 차이 등) |

## 한계

- 공식 DB는 모든 재판을 수록하지 않는다. 찾지 못한 판례는 '미확인'으로 남기고 부존재로 단정하지 않는다.
- 판례 취지·문맥 왜곡(Level 4·5)은 AI 모델 구간이다. 모델이 없으면 확인 완료로 올리지 않는다.
- 주장 유형·첨부 목록·기준일 후보는 어휘 규칙으로 찾으므로 표현이 다르면 놓칠 수 있다. 확정 판정이 아닌 검토 단서로 쓴다.
- 사건 순서 역전·진술 불일치·증거 원용 범위 검사는 문장 구조로 같은 대상을 확인할 때만 표시한다. 관형절로 엮인 두 사건이나 정해진 서증 범주(7종) 밖의 증거처럼 구조가 드러나지 않으면 놓친다.
- OCR 정확도는 원본 품질에 좌우된다. 비용 한도는 사전 승인 원장이며 공급자 청구액 보증이 아니다.
- 상세: [시스템 구조와 검증 방식 — 구현 범위와 한계](docs/SYSTEM_GUIDE.md#구현-범위와-한계), [구현 현황](docs/IMPLEMENTATION_STATUS.md)

## 문서 안내

| 문서 | 내용 |
|---|---|
| [운영 안내](docs/OPERATIONS_GUIDE.md) | AI 모델 응답 실패 사유, GitHub Actions 실행, CLI 일괄 검증, 보고서 생성, 휴지통·영구 삭제, 저장 공간, HTTP 500 추적 |
| [시스템 구조와 검증 방식](docs/SYSTEM_GUIDE.md) | 코드 구조, 인프라, 검증 파이프라인, AI 교차검증, 판정 기준, Release Gate, 시험 실행, 구현 범위와 한계 |
| [Render 배포](docs/DEPLOY_RENDER.md) | 배포 설정 절차 |
| [인증·권한·키 관리](docs/IDENTITY_SECURITY_INTEGRATION.md) · [작업 복구·비용 원장](docs/OPERATIONS_DURABILITY.md) | 다중 사용자 운영, 작업 복구, 예산 |
| [구현 현황](docs/IMPLEMENTATION_STATUS.md) | 완료 범위와 검증 근거 |
| [개선 계획](docs/ASSESSMENT_AND_IMPROVEMENT_PLAN.md) | 초기 진단과 개선 계획(기록) |
| [일자별 추이표](docs/scorecards/DAILY_TREND.md) · [판정서](docs/scorecards/f1_gate_verdict.md) | 개발 중 성능 점수와 평가 판정 |
| [에이전트 역할](docs/AGENT_ROLES.md) | 구현·평가 분리, PR 규칙, 필수 검사 |

## 참고 Source

국가법령정보 공동활용 <https://open.law.go.kr/> · KCI <https://www.kci.go.kr/> ·
OpenAlex <https://developers.openalex.org/> · Semantic Scholar <https://www.semanticscholar.org/product/api> ·
Crossref <https://www.crossref.org/documentation/retrieve-metadata/rest-api/> ·
C2PA <https://spec.c2pa.org/> ·
OWASP Prompt Injection Prevention Cheat Sheet
<https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html> ·
NIST Generative AI <https://www.nist.gov/artificial-intelligence>

본 시스템은 검증 보조 도구이다. 진정성립·위조·고의에 관한 판단은 사용자의 책임이다.
