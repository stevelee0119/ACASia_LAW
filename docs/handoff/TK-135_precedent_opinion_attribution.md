# TK-135 판례 의견 귀속 — 별개의견 인용과 의미 검토 근거 구간 (P2, 결함 수정, 평가 측 수정본)

- 결정: 2026-11-03 사용자 '다음 릴리스 범위'·'A1~A3 + B1 설계 메모 진행'. 배정 Antigravity.
- 기준: Steve `892bbd8`. 수정본 `patches/TK-135_opinion_attribution_on_892bbd8.diff`(5개 파일 +204/−8, 11-03 2판: 표지 탐색을 `_markers`로 합쳐 `split_opinions`·`opinion_ranges` 중복 제거, 동작 동일).

## 1. 현황 정정(평가 측)

- 11-03 목록에서 '의견 귀속이 없다'고 적은 것은 일부 틀렸다. v3 D3(`verifier._opinion_findings`, 931행)가 이미 있다.
  - 직접 인용이 반대의견에만 있으면 CASE_HOLDING_DISTORTION·MISATTRIBUTED_OPINION(CONTRADICTED, A).
  - 요약이 반대의견에 더 가까우면 `attribute_claim`(2-gram 포함률)으로 A·B.
- 남은 빈틈은 아래 세 가지다.

## 2. 원인(재현으로 확인, `892bbd8`)

1. **별개의견 미검사**: `_opinion_findings` 955~961행은 `split_opinions(...)["DISSENT"]`만 본다. 별개의견에만 있는 문장을 판시로 직접 인용해도 결과가 없다(평가 측 탐침 0/4).
2. **발췌 구간에 의견 표시 없음**: `evidence_pack._pack`(124행)이 만드는 구간에 어느 의견인지가 없다. 모델은 반대·별개의견 문장을 판시와 구별할 수 없다.
3. **반대의견 근거로 지지 판정 채택**: `pipeline._semantic_review` 1459~1462행 `grounded`는 근거 인용이 보낸 구간 안에 있는지만 본다. 모델이 반대의견 문장만 근거로 '취지 부합(VERIFIED)'을 내도 채택된다(합성 재현으로 확인).

## 3. 수정(수정본 내용)

1. `opinion_attribution.py`
   - `opinion_ranges(text)`: 원문 위치 기준 의견 구간. 다수의견 보충의견은 MAJORITY, 반대의견 보충의견은 기존 `_kind`대로 DISSENT.
   - `quote_opinion(quote, text)`: 인용이 다수(보충 포함)에 있으면 MAJORITY, 반대·별개에만 있으면 그 종류. 6자 미만·표지 없는 판결은 None(판단하지 않음).
2. `evidence_pack._pack`: 구간마다 `opinion_kinds`. `SELECTOR_VERSION` `tk135-1`.
3. `verifier._opinion_findings`: 직접 인용이 별개의견에만 있고 다수의견에 없으며, 인용 주변 문맥에 '별개의견' 표시가 없으면 MISATTRIBUTED_OPINION·**SUSPICIOUS·B**(closest CONCURRING). 반대의견 분기가 먼저다.
4. `pipeline._semantic_review`
   - payload `opinion_sections`(다수의견만이 아닌 구간)와 질문 문구 한 문장 추가.
   - 지지 판정(VERIFIED·SUPPORTED)의 근거 인용이 **모두** 반대·별개의견에만 있으면 `grounded=False`, `minority_opinion_evidence=True`, 사유 '…판시 근거로 채택하지 않음'.
   - 반박 판정(CONTRADICTED)은 반대의견 인용을 허용한다.
   - 가린 실행은 가린 전문(`project_masked` 첫 반환값)으로 의견을 가린다.
5. 새 시험 `tests/test_tk135_opinion_evidence.py` 10건.

## 4. 평가 측 사전 검증(평가 측 재실행, 저장소 밖 사본)

- 새 시험 10/10 통과. 원본에서는 수집 단계 실패(새 함수 없음).
- 관련 기존 시험(TK-131 발췌·v3 D3·case6 의견·모델 의견 화면·legal_engine·의미 검토 계열) 147건 통과.
- 비공개 탐침(합성, 다른 표현): 별개의견 직접 인용 양성 4/4, 대조(서면이 별개의견이라 밝힘·다수의견 인용·표지 없는 판결·짧은 조각·다수 보충의견) 오탐 0/5. 원본 0/4.
- 문구 대조 '의심 없음', 하드코딩·시험 수정·보호 경로 점검 통과.
- verify_all 전체 모드: 아래 '검증 결과'에 적는다.

## 5. 한계·범위 밖

- 실제 대법원 판결 전문의 의견 표지 변형(예: '대법관 ○의 별개의견에 대한 보충의견')은 기존 정규식 범위만 다룬다. 실제 판결 탐침은 온라인 탐침(F)으로 잰다(미검증).
- 에스컬레이션 단계의 참고 의견(`additional_advice`)에는 의견 구간 필터를 넣지 않았다(참고 표시만 함).
- 요약(인용부호 없는 서술)이 별개의견 취지인 경우의 판정은 넣지 않았다. 별개의견은 결론이 같아 오탐 위험이 크다.

## 6. 수용

- diff = 수정본(다르면 사유와 대체 시험).
- 필수 CI 전부 성공, 기존 시험 수정 0, 고정 변화 0, 은퇴 하락·오탐 증가 0.
- 평가 측 새 탐침: 양성 ≥ 3/4, 대조 오탐 0.
