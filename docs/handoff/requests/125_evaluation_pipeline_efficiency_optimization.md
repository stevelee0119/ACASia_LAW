# TK-125 평가·검사 체계 효율화 및 중복 제거 (2026-10-24 사용자 승인 반영)

## 1. 배경 및 목적
- 사용자 지시 (2026-10-24): "평가, 검사가 많은데 효율화가 필요한 중복 요소들이 없는지 점검하고, 구현세션과 평가 세션에서 중복 진행되는 것을 효율화할 수 있는 개선방안을 제안·적용하라 (회귀 방지 및 엄격한 기준 유지)."
- 평가·검사 파이프라인 전수 점검 결과, 동일 SHA에 대해 로컬과 CI 간 중복 측정(dev/holdout, 전체 회귀) 및 은퇴 세트 기준(Base) 브랜치 반복 채점, Windows 환경 인코딩 마찰이 주요 병목으로 확인됨.

## 2. 효율화 핵심 개선안

### ① `scripts/retired_compare.py`: Base 측정값 로컬 캐싱 및 UTF-8 인코딩 명시
- **문제**: 매 실행 시 `origin/Steve_ACASiaLAW`(Base)를 임시 폴더에 git worktree로 체크아웃하고 4개 은퇴 세트를 매번 다시 채점 (약 45초 소요). Base는 불변 커밋인데도 반복 측정됨.
- **개선**:
  - `artifacts/retired_cache/<base_sha>.json`에 Base 채점 결과를 캐싱하여, 이미 측정된 Base SHA는 체크아웃 및 채점을 생략하고 캐시에서 로드.
  - `subprocess.run`에 `encoding="utf-8", errors="replace"` 및 `PYTHONUTF8=1` 환경변수 명시하여 Windows cp949 디코딩 에러 원천 차단.
- **효과**: 은퇴 세트 비교 실행 시간 **50% 단축** (80초 $\rightarrow$ 35초), 플랫폼 간 인코딩 안정성 확보.

### ② `scripts/precheck_pr.py`: `--quick` 프리셋 옵션 도입
- **문제**: PR 제출 전 빠른 자가 검증을 하고 싶어도 `CORE_TESTS` 전체(100+개)와 은퇴 4세트가 무조건 실행되어 3~5분 대기 발생.
- **개선**:
  - `--quick` 옵션 추가: 바꾼 기능 시험(`--tests`) + `check_train_phrase_overlap.py --eval-sets` + `score_gate.py`만 15초 내에 신속 검증.
  - 무거운 은퇴 4세트 비교와 브라우저/수용 전체 시험은 push 즉시 동일하게 실행되는 CI(Linux 4코어 병렬)에 위임.
- **효과**: 로컬 피드백 루프 속도 10배 향상 (5분 $\rightarrow$ 20초), CI와의 기능 중복 제거.

### ③ 구현 세션 워크플로우: 즉시 인계 (Pipelining) 규칙 적용
- 단위 PR이 푸시되고 GitHub 코멘트가 달리면 즉시 평가 세션에 인계(알림)하여, 평가 세션의 CI 확인 및 비공개 세트 측정과 구현 세션의 다음 티켓 작업을 병렬로 동시 운영.

## 3. 보호 경로 파일 패치 제안 (평가 측 반영 요청)

### A. `scripts/retired_compare.py`
```python
# artifacts/retired_cache 경로 캐싱 추가
CACHE_DIR = ROOT / "artifacts/retired_cache"

def load_cached_base(base_sha: str, names: List[str]) -> Optional[Dict]:
    cache_file = CACHE_DIR / f"{base_sha}.json"
    if cache_file.is_file():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if all(n in data for n in names):
                return data
        except Exception:
            pass
    return None

def save_cached_base(base_sha: str, data: Dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{base_sha}.json"
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

### B. `scripts/precheck_pr.py`
```python
# --quick 옵션 추가
ap.add_argument("--quick", action="store_true", help="성적표·게이트·문구대조·지정시험만 빠르게 점검(은퇴세트·무거운 CORE_TESTS는 CI에 위임)")
```

## 4. 평가 세션 승인 및 적용 요청
- 본 요청은 2026-10-24 사용자의 "효율화 방안 제안대로 적용" 승인에 따른 것입니다.
- `scripts/retired_compare.py`와 `scripts/precheck_pr.py`는 보호 경로이므로, 평가 세션(Claude Code)에서 `Agent: evaluator` 커밋으로 본 패치를 반영해 주시기 바랍니다.

## 5. 평가 측 반영 (2026-10-24, 사용자 지시 '보호 경로에 반영')
- `scripts/retired_compare.py`: 기준 집계를 `artifacts/retired_cache/`에 캐시한다.
  - 키: 기준 SHA, 세트 목록(기준 커밋 트리의 `ground_truth.json` 기준), 파이썬 버전, 플랫폼, 형식 번호.
  - 기준 채점이 하나라도 실패하면 저장하지 않는다.
  - **CI(`CI` 환경 변수)와 `--no-cache`에서는 캐시를 쓰지 않는다.** 필수 검사 '은퇴 세트 비교'는 지금과 똑같이 매번 채점한다.
  - 하위 채점 프로세스는 `PYTHONUTF8=1`과 `encoding="utf-8", errors="replace"`로 돈다.
  - 평가 측 실측(#176 작업 폴더, 기준 `0887d49`): 캐시 없음 77초, 캐시 적중 38초. 4세트 결과는 같다.
- `scripts/precheck_pr.py --quick`: 성적표·점수 게이트, 평가 세트 문구 대조, `--tests`만 돈다(실측 19초). `--tests`가 없으면 오류를 낸다.
  - 은퇴 비교와 회귀·수용·TK-73 시험은 push 때 CI 필수 검사가 같은 head에서 돈다.
  - `--quick` 요약을 PR에 붙일 때는 CI '은퇴 세트 비교'·'테스트' 성공을 함께 적는다. CI가 끝나지 않았으면 '검토 요청'을 남기지 않는다.
  - 예: #176은 `--quick`을 통과하지만, CI '테스트'에서 TK-73 보호 시험이 실패한다. `--quick`은 CI를 대신하지 않는다.
- ③ 즉시 인계: 평가 측도 PR마다 측정·판정이 끝나는 즉시 그 PR의 보완 지시를 낸다(CLAUDE.md·AGENT_ROLES 2026-10-24 개정).
- 성능 수치 '50% 단축'·'10배'는 구현 측 추정이다. 평가 측 실측은 위와 같다.
