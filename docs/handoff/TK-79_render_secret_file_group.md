# TK-79 운영 컨테이너 사용자가 Render Secret File을 읽지 못해 Drive 서비스 계정 인증을 쓸 수 없다 (P2, 배포 설정, 기존 공백)
- 유형: 배포 설정(Docker 이미지 권한). 탐지·채점 규칙 변경이 아니다.
- 발견: 평가 측, 2026-10-17. 운영 참고자료 폴더의 링크 공개를 해제하는 절차를 준비하다 확인했다. 사용자 승인(3단계 'Dockerfile 수정')으로 Antigravity에 배정한다.

## 1. 배경과 증상
- 운영은 지금 API 키(`LV_DRIVE_API_KEY`)로 Drive를 읽는다. API 키는 공개 자료만 읽으므로 운영 참고자료 폴더가 '링크가 있는 모든 사용자'로 공개되어 있다.
- 비공개로 바꾸려면 서비스 계정 인증(`LV_DRIVE_SERVICE_ACCOUNT_FILE`, `packages/rag_engine/drive.py`)을 써야 한다. 이 경로는 키 **파일 경로**만 받는다.
  - 사용자가 서비스 계정을 만들었고 키의 `token_uri`도 확인했다. 운영 폴더도 그 계정에 뷰어로 공유했다(평가 측이 Drive 권한 조회로 확인).
- Render는 Secret File을 실행 중 `/etc/secrets/<파일명>`에 둔다([Render 문서](https://render.com/docs/configure-environment-variables#secret-files)).
  - Docker 서비스에서는 앱 사용자가 **그룹 1000**에 속해야 읽을 수 있다고 안내한다([Render Docker 문서](https://render.com/docs/docker-secrets): "make sure your application user is in group `1000`").
- `docker/Dockerfile`은 `useradd -m -u 10001 appuser` 뒤 `USER appuser`로 실행하고, 그룹 1000에 넣지 않는다.
  - 그래서 키 파일을 올려도 읽기가 '권한 없음'으로 실패할 것으로 본다.
  - 실패하면 `DriveClient._auth`가 `DRIVE_AUTH_FAILED`를 내고 운영의 Drive 대조가 멈춘다.
  - 평가 측은 Render 실행 환경에서 직접 재현하지 못했다. 근거는 위 문서와 Dockerfile이다.

## 2. 요구
1. `docker/Dockerfile`에서 `appuser`를 GID 1000 그룹의 보조 구성원으로 넣는다.
   - 기반 이미지(`python:3.11-slim`)에 GID 1000 그룹이 없으면 먼저 만든다. 예: `getent group 1000 || groupadd -g 1000 rendersecrets` 뒤 `usermod -a -G 1000 appuser`.
   - `appuser`의 UID(10001)·기본 그룹·`/app`·`/data` 소유권은 바꾸지 않는다. 루트 실행으로 바꾸지 않는다.
2. 제품 코드(`packages/`·`apps/`)와 `render.yaml`의 값은 바꾸지 않는다. 환경 변수와 Secret File 설정은 배포 뒤 사용자가 한다.

## 3. 시험
- `tests/test_server_startup.py`의 Dockerfile 검사처럼 정적 시험을 하나 둔다. 요구 1의 그룹 추가가 `USER appuser` 앞에 있는지 확인한다.
- CI `Docker OCR readiness` 잡에서 빌드한 이미지로 확인한다.
  - `docker run --rm acas-law-ocr-check id -G`의 출력에 `1000`이 있어야 한다.
  - `id -u`는 `10001`이어야 한다.
  - `.github/workflows/ci.yml`은 보호 경로다. 잡에 단계를 넣어야 하면 평가 측에 요청 티켓으로 알린다. 아니면 PR 본문에 같은 명령의 로컬 출력을 붙인다.
- 기존 시동·OCR 점검(`check_ocr_runtime`, `/api/health`, `check_upload_runtime`)이 그대로 통과한다.

## 4. 수용과 이후 순서
- CI 필수 검사 성공, 제품 diff 0(Dockerfile·시험만), 고정 81.7/79.2·오탐 0 불변.
- 이후 순서:
  1. 병합·운영 배포
  2. 사용자가 Render에 Secret File `drive-sa.json`과 `LV_DRIVE_SERVICE_ACCOUNT_FILE=/etc/secrets/drive-sa.json` 설정
  3. 운영 점검에서 참고자료 READY·파일 수 유지 확인
  4. 사용자가 운영 폴더 일반 액세스를 '제한됨'으로 변경
  5. 운영 점검 재확인
  6. 평가 측이 API 키로 폴더가 더는 읽히지 않는지 확인
