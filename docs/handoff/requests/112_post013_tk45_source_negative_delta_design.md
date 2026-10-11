# TK45: 기존 판정 보존 + 직접 부정/효과 증명 증분 (제품 전 설계)

시작 `2a85aa0e043cb6d13993742c2a053a8b048c48d5`. 이전 e21의 첫 UNKNOWN → 긍정 행위 증명 → 다른 긍정 요건과 선택 해소 경로는 이식하지 않는다. 그 경로의 실제 정상 7/8 불수용을 유지한다. 이 설계는 기존 정상·UNKNOWN·요건 확인 요청·SUSPICIOUS/UNVERIFIED 결과를 재분류하지 않고 **작성자의 직접 요건부정 또는 타 법적 효과 단정이 새 원문 증명으로 확정된 경우만** 기존 rule의 finding을 추가한다. 다른 요건 POSITIVE의 존재는 증거·면제 조건이 아니다.

## 방법과 공개 근거

후보 생성, 원문 결합 증명, 법적 효과 범위, 최종 선택을 분리한다. 기존 설정의 양보 lead와 실제 `-더라도` 연결어미로 국소 양보절 후보를 찾되, 설정된 양보 *동사* 목록만으로 절을 제한하지 않는다. 각 문장을 한 번 인덱싱하여 원문 논항/조사/술어/어미/인용·조건·발화주체 경계를 공유한다. 첫 구현은 같은 문장 안의 명시적 연결만 다루며 인접 문장의 범위를 승계하지 않는다.

* 부정: configured requirement의 자기 원문 occurrence → 바로 결합한 목적격 → 독립 동작 술어 → 단일 직접 부정 보조 구성 → 관측 과거/유한 연결종결을 모두 증명한다. 최소 첫 계약은 동작명사를 목적어로 받는 독립 `하다1` sense1의 `하지 않았다` 구성이다. `-하다` 접사·보조/인용 하다, 다른 목적어, 부수 동작 부정, 필요성 부정, 중첩 부정, 계획/조건/보고는 증명하지 않는다. 임의 동사의 의미를 형태만으로 인정하지 않는다. 기존 absent polarity는 그대로 적용하며 충돌은 새 증명 없음이다.
* 효과: 기존 configured 법적 범위 후보와 자기 목적격 → 실제 유한활용 술어 → 문맥상 선택된 개별 sense → 작성자의 현재 범주적 법적 결론을 함께 증명한다. `받다1:10` 결정·판결의 작용과 `면하다1(免):1` 책임·의무 해방은 일반 물건 수령/방향·직면과 분리한다. 법률명사 단독·lemma prefix·사전 조회만으로 의미를 확정하지 않는다. 법적 객체, 규범적 단정, 술어 결합 중 하나라도 불명확하면 새 효과 증명 없음이다. 애매한 책임/징계/제재의 의미를 lemma 전체에 부여하지 않는다.
* 선택: 새 증명이 없으면 baseline 출력 그대로다. 기존 finding의 상태/등급/심각도/원문·규칙번호는 변경하지 않는다. 확정 증명은 같은 rule의 중복을 피하여 추가하고 근거 span, 선택 sense/application role, 작성자·효과 범위를 남긴다. 사실 진실성·요건 충족·법적 충분성은 인증하지 않는다. 기존 UNKNOWN 경고를 삭제하지 않으며 새 후보 실패 자체를 정상 문장의 새 경고로 삼지 않는다.

NIKL 한국어기초사전(2026-10-11 HTTP200 직접 조회): [-더라도](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=-%EB%8D%94%EB%9D%BC%EB%8F%84) “앞에 오는 말을 가정하거나 인정하지만 … 영향을 끼치지 않음”; [-지 않다](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=-%EC%A7%80%20%EC%95%8A%EB%8B%A4) “앞말이 나타내는 행위나 상태를 부정”; [하다](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%ED%95%98%EB%8B%A4) 하다1 sense1 “어떤 행동이나 동작, 활동 등을 행하다”; [받다](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EB%B0%9B%EB%8B%A4) 받다1 sense10 “어떠한 결정이나 판결을 당하다”; [면하다](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EB%A9%B4%ED%95%98%EB%8B%A4) 면하다1(免) sense1 “책임이나 의무를 지지 않게 되다”. 공식 뜻과 제품의 DENIAL/LEGAL_EFFECT application role은 별개이며 국소 frame가 불명확하면 선택 sense를 만들지 않는다.

## 공개 precheck·보호·한계

제품 변경 없이 actual TXT 전체 pipeline 18건에서 새 직접 부정 3·효과 3은 모두 finding 0, 정상 3과 UNKNOWN/부수부정/중첩/인용/상대/조건/필요성/타논항/사실수령 대조 9도 0이었다. 공개 시험은 첫 6건의 미검출을 고정하고 반대 대조, 기존 경고, 정중체·focus·prefix 충돌 및 quote/opponent/rebuttal 각 2+를 추가한다. 원문 span과 최종 verdict까지 검증하고 TXT/PDF/DOCX·32k 성장에서 기존 기대값을 수정하지 않는다. 인덱스 방문량과 이진조회 비용을 분리하며 전체 pipeline O(N)을 주장하지 않는다.

일반 새로운 의미 분류·모델/사전 의존성·전체 e21 이식·완료/긍정 인증·UNKNOWN consumer 면제 확장은 제외한다. 승인 뒤 최소 제품+관련 시험+동일 SHA CI/3줄 요청까지 약 60–90분; 19:51 목표 달성·원래 정상8/8 및 부정/확장 둘 다 시작보다 증가 여부는 별도 평가이며 이 메모로 완료를 주장하지 않는다. 기존 보호·원장·버전·기준선·rule_id 0 계약 불변.
