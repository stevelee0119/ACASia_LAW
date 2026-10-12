# TK44/49 PAGE named ActualText 제한 제품 전달

제품 SHA: `88b0cfd04ccb668fabc28cd1318223a5e0696cbb`.
승인 설계: PR95 `e97bd81d60c3af500a4e8d5578b488d0f2e55044`.
의존 제품: PR90 `b1e506f2eab2b830cb8fb7fd074d22dcdc3be589`.
구현/평가 분리: 구현자는 공개 합성 입력과 자기 checkout만 사용했다.

## 실제 제품

`actualtext_boundaries.py`는 현재 PAGE Resources의 exact Properties/name만
조회한다. 선택 dictionary의 직접 bytes만 기존 closed Span/original glyph/
visibility/ancestor/rotation/paint/strict mapping 증명을 통과할 때 JOIN 또는
SPACE를 제공한다. 이름, MCID, cache value는 source identity가 아니다.
간접 문자열은 인증하지 않으며 별도 보안 검사에 전달한다. Form resource
인증/간접 검사 복원은 이번 범위에 없다.

`NamedActualTextCapture`는 parser document마다 새로 생성된다. cache/
context/inspection을 제품 객체가 직접 관리하며 prototype monkeypatch나
global runtime 대체가 없다. 입력 parser가 가진 객체의 alias를 재사용하며
같은 decoded text를 context마다 복사하지 않는다. PAGE별 cache scope와
독립 glyph 증명을 계속 확인한다.

cap은 retained named context 128, reference visit 512, reference cache 64,
distinct decode 64/64,000 chars, decoded-entry raw byte retention 128,000,
inspection 50 strings/100,000 chars다. inspection 한 문자열은 2,000 chars
이하이며 참조 반복 전에 decode/dedup/cap을 적용한다. raw byte cap은 기존
PDF parser 객체 그래프나 전체 입력 peak memory의 상한이라는 주장이 아니다.
원래 inline source의 기존 상한/출력은 변경하지 않았다.

inspection completeness는 lifecycle 결과다. 미해석 페이지, 지원하지 않는
present source, resolution 실패, truncation 및 budget 초과는 false로 남는다.
다른 페이지의 성공이 이 상태를 덮지 않는다. 알려진 dictionary의 ActualText
key 부재와 해석하지 않은 source 부재를 구분한다. aggregate snapshot은 문서
종료 후 각 page accounting에 동일하게 반영한다. 실제 보안 검사의 internal
ActualText/scanned path/finding을 확인했으며 `to_dict()`의 structure/raw 제외
계약을 유지한다. 새 raw replacement text를 JSON에 추가하지 않았다.

## 공개 검증

제품 tree에서 관련 **384 PASS, 9.70s**, error/skip/xfail 0.

```
python -m pytest -o addopts='' -q --tb=short \
  tests/test_tk44_named_actualtext_provider.py \
  tests/test_tk44_named_actualtext_capability_spike.py \
  tests/test_tk44_named_actualtext_activation_spike.py \
  tests/test_tk44_named_actualtext_capture_budget_spike.py \
  tests/test_tk44_named_inspection_lifecycle_spike.py \
  tests/test_tk44_actualtext_provider.py \
  tests/acceptance/test_tk44_boundary_signal_contract.py \
  tests/test_boundary_candidates.py \
  tests/test_boundary_signal_observations.py \
  tests/test_tk06_actualtext_zwsp.py
```

새 실제 provider 88건은 원래 parse_document를 호출하며 adapter를 답으로
사용하지 않는다. 3 문구 × 3 폭(420/595/720) × JOIN/SPACE × direct/indirect
dictionary 36건, source/visibility 음성 17건, lifecycle 7건과 반복 capture/
예산/unsupported/부재/참조 오류/보안/다른 page·Form/painted-space/NFKC/
font·다른 문단 대조를 포함한다. source certification이 거절된 간접 명령의
internal 문자열, scanner path와 실제 SUSPICIOUS/A finding도 양성으로 확인했다.
Form-only 간접 명령은 여전히 검사되지 않는 기존 잔여로 시험에 기록했다.

기존 설계 비교 **103 기대값은 수정하지 않았다**. 설계 시험의 'baseline'
의미를 public b1e로 유지하도록 테스트 전용 snapshot을 고정했다. snapshot
blob은 원본과 동일한 `1c765f50cd028b579e159b8f7b15797186cb9305`이며 shallow
CI checkout의 과거 git object 가용성에 의존하지 않는다. 처음 제품 연결 시
prototype monkeypatch를 baseline adapter가 잘못 frozen 경로로 보낸 실행은
40 FAIL/63 PASS였다. test-only 경로 선택을 교정한 뒤 103 PASS(2.67s)를
확인했고 원래 expected/제품 기준을 바꾸지 않았다.

참조 65회 × 2k/60k 문자열은 decode 1/cache 1 또는 2/retained ≤2k였다.
513회 참조 대조는 visit 512/cache 2/decode 1/context 128에서 멈췄다.
distinct 60k 두 문자열은 첫 decode 후 character admission을 거절했다.
따로 실행한 신규 limit 2건도 2 PASS(0.38s)였으며 최종 384 실행에 포함됐다.
이는 bounded capture와 association candidate accounting의 증거다. 기존
paint bucket binary lookup 비용과 regex/parser 내부 비용까지 O(N)으로
증명하거나 전체 pipeline 성능을 보장하는 측정은 아니다.

## 남은 범위와 판정

원래 UNKNOWN primary/legacy 0.75 page-width floor/alternative consumer는
변경하지 않았다. resource Form/structure-tree/untagged logical source 및
Form-only indirect inspection은 미구현이다. 기존 문자열·TC06·61개 보호
계약 기대값과 보호 경로를 수정하지 않았다. DOCX 제품 byte는 변경하지
않았으며 원래 47/19/1·40/19/1·폭9/fixed·전체 acceptance/regression 및
비공개 gate 판정은 root가 exact 제출 SHA에서 담당한다.

이 receipt-only 후속 tip은 제품 차이 0이어야 한다. exact CI/score/독립
좁은 감사/원래 gate 전 수용·통합·배포·전체 TK44/49 완료를 주장하지 않는다.
TK45 PR96은 별도 설계-only이며 이 제품에 합치지 않았다.
