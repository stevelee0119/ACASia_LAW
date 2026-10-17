# Codex 구현 전달문 — 2026-10-17 잔여 티켓 전용 (3)

이 문서 하나가 Codex 구현 세션에 대한 현행 지시다. 이전 전달문 전체를 대체한다. 작성: 평가 에이전트(Claude Code).

## 1. 체제
- 새 구현은 Antigravity, 평가는 Claude Code 평가 세션이 맡는다. Codex 구현 세션은 전환 시점의 열린 티켓(TK-44·45·49·55·73)만 마무리하기로 했고, **이번 회차로 모두 끝났다.** 새 티켓·새 기능은 배정하지 않는다.
- 봉인 세트·고정 비공개 벤치마크·개발 말뭉치 출제는 저장소를 연결하지 않은 Codex **격리 세션**이 맡는다. 이 구현 세션은 출제·채점에 쓰지 않는다.

## 2. 마무리 결과

| 티켓 | PR·SHA | 결과 | 상태 |
|---|---|---|---|
| TK-44·49 | #116 `3f9aef2` | [수용](https://github.com/stevelee0119/verify_ACAS_LAW/pull/116#issuecomment-6233278233), Steve 병합 `e331234` | known_open(structure-tree 연결·비태그 UNKNOWN primary·0.75 floor·대체 consumer) |
| TK-73 | #122 `9a56188` | [수용](https://github.com/stevelee0119/verify_ACAS_LAW/pull/122#issuecomment-6233372558), Steve 병합 `46acf51` | known_open(한쪽 행에만 날짜가 있는 1건) |
| TK-55 | #106 `2936764` | 수용·평가 측 통합 | known_open(기존 저장 ID 등) |
| TK-45 | #96 | 불승인, 사용자 결정으로 중지 | known_open |
| 설계·검토 PR | #108·#117·#92 | 제품 PR 병합 뒤 평가 측이 닫음 | — |

- 은퇴 c세트(`sealed_20261010`) A등급 오탐은 3→1이 됐다(CI '은퇴 세트 비교'와 평가 측 재실행 일치).
- `verify_all` 전체 모드는 이번 릴리스 후보 SHA에서 평가 측이 1회 돈다.

## 3. 할 일
- **없음.** known_open 잔여의 재개는 사용자 결정이다. 재개되면 이 문서를 다시 낸다.
- 릴리스 뒤 CI·운영에서 위 PR과 관련된 실패가 나오면 평가 측이 티켓으로 정리해 이 문서로 알린다.
