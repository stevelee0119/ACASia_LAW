# PR #128 기술 수용·통합 기록

평가일: 2026-10-18 한국 시각. 구현·평가 같은 계열(별도 세션). 이번 요청의 별도 평가 세션은 공개 저장소·합성 시험만 사용했고 비공개·봉인 원문에는 접근하지 않았다. 제품 직접 수정 없음.

## 판정과 근거

- **기술 수용·Steve 통합 완료.** 구현 SHA `c35bb2a5d2e3ce777a61929a822c8117914a3acb`, 통합 전 Steve `561d3fdb552857b3e051ee287b933dda6a68c288`, 실제 병합 SHA `933933a82b83c336dbae91175403792c941c4d9c` ([PR #128](https://github.com/stevelee0119/ACASia_LAW/pull/128)).
- **CI 결과 인용:** 구현 SHA의 [CI](https://github.com/stevelee0119/ACASia_LAW/actions/runs/39042005016), [점수 게이트·은퇴 비교](https://github.com/stevelee0119/ACASia_LAW/actions/runs/39042005019), [CodeQL](https://github.com/stevelee0119/ACASia_LAW/actions/runs/39042005035) 모두 성공. push CI `39042001484`·점수 `39042001616`도 성공. 새 성능 수치·실제 법률 품질·청구액 개선으로 해석하지 않는다.
- **평가 측 재실행:** 최신 Steve와 구현 SHA의 충돌 없는 로컬 병합 `41c1b6795026bf93173e1f6f24ae4dec4284be9f`에서 `python -m pytest -q tests/test_efficient_llm_routing.py tests/test_tk73_numbering_pipeline.py tests/test_tk55_generated_claim_identifiers.py` 종료 0, 72건 통과(26+3+43). 실제 GitHub 병합 `933933a`와 전체 트리 diff 0을 확인했다. 가짜 공급자·공개 합성 시험, 유료 API 호출 없음.
- diff 검토: 역할별 모델 선택, 명시 설정 우선, 재사용 전 정책·개인정보 검사, 예산 예약·사용량 정산, 대기 작업 설정 동결, 충돌 시 근거 있는 추가 의견 표시. PR #128 범위의 새 P1 회귀는 확인되지 않았다. 구현 측 기존 797통과/1건너뜀과 구분한다.
- 실제 통합 SHA의 [CI](https://github.com/stevelee0119/ACASia_LAW/actions/runs/39072920097)·[점수](https://github.com/stevelee0119/ACASia_LAW/actions/runs/39072920099)는 기록 시 진행 중이다. 구현 SHA의 성공을 통합 SHA의 성공으로 대체하지 않는다.

## 릴리스 준비와 남은 조건

1. 운영 `main`은 `b68cfeec2c5c168a3b9e6e2e92653ea6892521bf`, 버전 0.13.0 유지. 이번 병합은 배포가 아니다. PR #128에 DB migration 변경 없음.
2. [현행 릴리스 범위](RELEASE_PROCEDURE.md#2-3-이번-릴리스-범위-2026-10-17-사용자-결정)는 #125·#126 재설계본의 수용·병합을 기다린다. 기록 시 #125 head `b011af2`는 설계 보완, #126 head `24881ad`는 재설계 구현·보완·Steve 동기화까지 있으나 두 PR 모두 미병합이다. 별도 담당의 평가를 이 기록으로 대신하지 않는다.
3. 전체 Steve에는 탐지·파서 변경이 있다. 봉인은 **라우팅 변경 범위 밖이라는 이유가 아니라, 이번 릴리스의 사용자 결정(2026-10-17)**으로 생략한다. 최종 후보에서 dev/holdout·은퇴 4세트·고정 벤치 2판·train의 main 대조와 `verify_all` 전체 1회, 최종 동일 SHA CI가 필요하다. 범위가 아직 확정되지 않아 이번에는 전체 검증을 중복 실행하지 않았다. 비공개 벤치·train은 기존 자료 보유 평가 담당이 집계만 전달한다.
4. 잔여 known_open TK-44·45·49·55·73, 열린 TK-76(P1 기존 탐지 부족), TK-77(merged·CI 관찰 중)을 유지한다. '모든 P1 0'으로 기록하지 않는다. TK-45·55의 과거 회귀 티켓과 이번 후보에서 새로 확인된 P1 회귀를 구분한다.
5. 운영 환경변수는 이번 평가에서 조회·변경하지 않았다. 실제 적용 전에 명시 모델 override와 API/worker 설정을 확인해야 한다. 일반 Sonnet·검토 Sol·작성 정황 Luna·추가 의견 Opus, `auto`, 효율 라우팅 ON, 유료 prompt cache OFF, 표본 10%의 적용안은 [운영 문서](../handoff/efficient_legal_review.md)를 따른다. 키·기존 예산·한국법 프로필은 유지한다. 이전 snapshot 없는 대기 작업은 수동 재시도가 필요하다.
6. 대표 한국어 문서의 기존 구성 대비 품질·누락·오탐·근거 일치·지연·실제 비용은 미측정이다. 버전 상향 근거가 없으며, 최종 버전 판정·사용자 main 병합·배포 후 온라인 점검은 별도다.

**지금 가능:** 이 기술 수용 기록의 평가 PR 검토와 통합 SHA CI 확인. **지금 불가:** 완성된 릴리스로 main 병합·배포. 선행요건은 2~6항의 해당 검증·평가 및 사용자 최종 병합이다.
