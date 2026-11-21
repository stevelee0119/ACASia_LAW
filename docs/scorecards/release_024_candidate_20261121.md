# 0.24.0 릴리스 후보 오프라인 판정 (2026-11-21)

**판정: 오프라인 수용.** `main` 병합·배포는 아직 시행하지 않았다. 평가 대상은 `Steve_ACASiaLAW`의 `0055fa728202c2d4b500099fa2b6c29d8258c07e`이며, 기준은 운영 `main`의 `f7a7f49056fa4fc6239ffdad803eed53443d9045`이다. #353, #359~#374의 17개 PR을 포함한다. 후보 Git tree `d778607e42f1a0baf4acdffd8bba2b5fde6ec8c2`는 마지막 제품 PR #371의 수용 head와 같다.

## 필수 게이트

| 게이트 | 확인 결과 |
|---|---|
| 전체 `verify_all` | 후보의 깨끗한 작업 트리에서 `--base f7a7f49056fa4fc6239ffdad803eed53443d9045` 전체 모드 **종료 0**, 실패 단계 0. 수용 1,278, 회귀 원장 2,357, 일반 전체 11,470, 브라우저 200 통과; 실제 실패·strict XPASS 각 0. 환경·점수·회귀·하드코딩·시험 편집·보호 경로·버전 검사도 통과. 집계 JSON SHA-256 `35116076386ae9590a2bbc9af66f97b0830c8c21db6574d70e8f27b0c6a50602`(로컬 `artifacts/verify_all_ci_host_024.json`, 비공개 입력 없음). |
| 측정 환경 | Linux, Python 3.11.17, Tesseract 5.3.4, `kor`·`eng` 및 한글 글꼴. CI OCR 실행 파일·언어 자료를 격리 폴더에 두고 `bwrap` 임시 마운트로 글꼴 경로를 제공했다. 제품·시험·채점기 파일과 시스템 파일은 바꾸지 않았다. `verify_all`의 환경 일치 검사도 통과했다. |
| 점수·회귀 | 같은 조건의 운영 기준·후보 비교에서 dev 82.6→82.6, holdout 81.9→81.9, 확인 오탐·A등급 오탐 0 유지, 인젝션 방어 유지. 합산·세트별 RER 0. 은퇴 5세트와 회귀 게이트의 항목별 후퇴 0. |
| 새 봉인 세트 | 사용자 제공 짝 비교 집계. 동일 지문 `4b9c00017908d038cf03e5c8f018d2fa85ae43c1c2493d19fa1b533cf118792f`, 10문서·60결함. 운영·후보 모두 종료 0, 종합 37.9, 가중 재현율 0.379, v2 22/60, 오탐·A등급 오탐·엔진 오류 각 0, `injection_defended=true`. 원본 무결성 유지, 일회용 사본 삭제 확인. 이 세트는 재채점하지 않는다. |
| 필수 CI | 포함 PR의 최종 head 필수 게이트 성공. 준비 기록 PR #375의 `79a9b93aa28b3184d315f43471bff9a634a8ab21`에서 점수·은퇴·CodeQL·SQLite·PostgreSQL·Docker OCR 모두 성공. **이 판정 문서가 추가된 새 head의 CI는 병합 전 재확인한다.** |
| 열린 P1 회귀 | `ticket_registry.json`의 `open`+`priority=P1`+`kind=regression` 0건; `ticket_metrics.py --check` 156건 등록 확인. 최종 릴리스 PR에서도 재확인한다. |

앞선 로컬 Python 3.12.14·Tesseract 5.5.0 실행은 `verify_all` 종료 1이었다. 별도의 Docker 시도도 시간대 자료 누락과 Chromium 페이지 충돌로 종료 1이었다. 이 결과를 통과로 계산하지 않았다. 위의 최종 전체 실행은 CI 버전 Python·OCR과 호스트 Chromium을 결합한 동일 후보 SHA에서 종료 0을 확보한 것이다.

## 가치·버전·미측정

이번 범위는 로컬 LLM·공식 Source 카세트, RAG 검색 단계, 법률 절 정규화, 인용 NLI, 표 구조·OCR 폴백, 증거 그래프 등 새 기능을 포함한다. 각 기능의 진입점과 기본 `shadow`/`none` 설정은 포함 PR 시험과 필수 CI에서 검증했다. 따라서 `basis=["added"]`, 직전 0.23.0에서 **0.24.0 minor**를 판정한다. 오프라인 점수 순증이나 기존 결함 감소 수치는 주장하지 않는다.

고정 비공개 벤치마크는 `NOT_MEASURED`(참고 지표)다. 공식 DB·Drive·모델을 포함한 운영 온라인 실측과 실무 법률 정확도는 배포 전 `NOT_RUN`/`NOT_MEASURED`이며 합격으로 계산하지 않는다. 새 기능 릴리스이므로 배포 뒤 [온라인 평가 계획](FEATURE_ONLINE_EVALUATION.md)에 따라 점검한다. DB 마이그레이션과 배포 설정 변경은 없다.

## 남은 순서

1. 이 판정 기록 PR #375의 새 SHA 필수 CI를 확인하고 `Steve_ACASiaLAW`에 반영한다.
2. 구현 측이 판정서에 맞춘 **버전 전용 커밋 1개**로 0.24.0을 반영한다. 평가 측이 버전 정책과 같은 SHA의 CI를 확인한다.
3. 평가 측이 `Steve_ACASiaLAW` → `main` 릴리스 PR을 작성한다. **사용자가 병합을 승인**하면 Render 배포 뒤 health SHA·버전 및 온라인 기능 점검을 기록한다.

Agent: evaluator
