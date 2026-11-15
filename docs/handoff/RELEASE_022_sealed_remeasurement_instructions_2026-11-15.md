# 0.22.0 봉인 시험 재측정 전달문

대상: 사용자 또는 봉인 시험 실행 담당자. 원문·정답·상세 finding은 비공개 위치에 유지하고 평가 측에는 집계 JSON만 전달한다.

## 현재 판정과 재측정 이유

제출된 실행 요약은 후보 `fca7534`에서 봉인 8문서/62항목, 구 산식 23.0, v2 13/62, 개인정보 종류 13/26, 확인 오탐/A 0, 엔진 오류 0을 보고했다. Python 3.11.2, Tesseract 5.3.0의 언어가 eng/osd뿐이므로 한국어 OCR 조건이 충족되지 않았다. 또한 같은 봉인 세트의 현재 운영본 측정이 없다. 따라서 이 값은 **제출된 후보 단독 관찰값**이며 릴리스 봉인 게이트 통과 또는 회귀 판정이 아니다.

보안 탐지 0/10과 구 산식 `injection_defended=true`는 서로 다른 지표다. 전자를 숨기거나 후자로 대체하지 않는다. OCR 누락이 낮은 점수의 원인인지도 재측정 전 단정하지 않는다.

## 고정할 조건

- 운영 기준: `83d862e78ba3e4d489dcab3fdc5b1bcc7c5838ca` (0.21.0).
- 제품 후보: `fca75347c5612b3a5960005726b4a31f7143b38a` (버전 표시가 아직 0.21.0이어도 정상).
- Linux, Python 3.11, Tesseract 5.3.4, eng/kor/osd. 실제 micro 버전·OCR 언어를 두 실행에서 같게 고정한다.
- 후보의 `requirements-test.txt`를 `pip install --require-hashes -r requirements-test.txt`로 설치한 **동일 가상환경**을 양쪽에서 사용한다. 두 트리마다 의존성을 다시 풀어 설치하지 않는다.
- 오프라인 `LV_ALLOW_NETWORK=0`, `OMP_THREAD_LIMIT=1`. API 키를 출력하거나 집계 파일에 넣지 않는다.
- 봉인 ZIP·ground_truth·match_spec·입력 파일을 변경하지 않는다. ZIP 및 답/매칭 명세 SHA-256을 비공개 실행 장부에 기록하고, 평가자에게는 데이터셋 지문을 전달한다.
- 자료는 저장소 밖 `/tmp/sealed_20261115`에서 실행한다. `path_guard.py`를 수정하거나 경로 검사를 끄지 않는다. `.sealed_out`은 비공개 상세 출력이며 GitHub/구현 PR에 올리지 않는다.

## 실행 순서

1. 한국어 OCR을 설치하고 `tesseract --version`, `tesseract --list-langs`, `python -m scripts.check_ocr_runtime`의 한국어 스캔 PDF self-test 통과를 확인한다. `kor`가 없으면 채점을 시작하지 않는다.
2. 깨끗한 독립 worktree 두 개를 위 전체 SHA에 만든다. `git rev-parse HEAD`와 `git status --porcelain`으로 SHA 및 미커밋 변경 0을 확인한다. 구현 세션의 작업 중인 트리에서 측정하지 않는다.
3. 아래 평가 파일이 두 SHA에서 같은지 `git diff --exit-code <운영SHA> <후보SHA> -- <파일들>`로 확인한다: `scripts/scorecard.py`, `scripts/eval_testset.py`, `scripts/evaluation_v2.py`, `scripts/path_guard.py`. 차이가 있으면 임의로 과거 점수와 비교하지 말고 평가 측에 알려 동일 채점기를 적용한다. 이번 범위에서는 해당 채점 파일의 변경이 없다.
4. 같은 가상환경의 Python으로, 각 worktree를 현재 디렉터리로 하여 다음을 순서대로 실행한다. 두 실행 사이에 패키지·OCR 자료·봉인 자료를 변경하지 않는다.

   운영 트리:
   `LV_ALLOW_NETWORK=0 OMP_THREAD_LIMIT=1 <동일venv>/bin/python scripts/scorecard.py --sealed-dir /tmp/sealed_20261115 --out /tmp/scorecard_sealed_main_021.json`

   후보 트리:
   `LV_ALLOW_NETWORK=0 OMP_THREAD_LIMIT=1 <동일venv>/bin/python scripts/scorecard.py --sealed-dir /tmp/sealed_20261115 --out /tmp/scorecard_sealed_candidate_022.json`

5. 각 JSON의 전체 `git.sha`가 지정한 운영/후보 SHA에 각각 대응하고 `dirty=false`인지 확인한다. 양쪽 실행 환경·봉인 데이터셋 SHA-256·채점 파일 해시·문서/항목/유형별 분모는 같아야 한다. 제품 SHA/버전과 그 변경으로 생긴 모델 설정·산출 점수의 차이는 비교 대상이므로 같게 만들지 않는다. 의도하지 않은 환경·자료·채점 조건 차이가 있으면 원인을 적고 비교를 보류한다.
6. 평가자에게 **두 성적표 집계 JSON**, 실행 종료 코드, 한국어 OCR self-test 결과, 동일 의존성 설치 확인을 전달한다. 원문·정답·문서별 상세·`.sealed_out`은 전달하지 않는다. 현재 텍스트 요약만으로 전체 SHA·데이터 지문·누락 필드를 검증할 수 없다.

## 평가 측 후속 판정

동일 조건 확인 후 고정/봉인의 점수·v2 유형별 적중·개인정보·확인 오탐/A·엔진 오류를 비교하고, 감소한 항목과 미측정을 별도로 기록한다. 0/10 보안 탐지의 유지/변화도 독립 표기한다. 총점 유지로 유형별 후퇴를 상쇄하지 않는다. 같은 낮은 점수가 유지된 경우에도 실무 정확도/보안성 입증이라고 표현하지 않는다. 새로운 절대 합격선을 사후에 만들어 적용하지 않는다.

평가자 도구 보완 커밋은 제품 코드와 봉인 채점기를 바꾸지 않는다. 버전/문서만 추가된 뒤에는 제품·채점기 diff 0 확인으로 위 후보 측정과 연결하며, 기능이 추가 변경되면 새 후보를 지정한다.
