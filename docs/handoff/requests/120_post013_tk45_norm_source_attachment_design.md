# TK45: 민법 인용 위치와 자기 논항 연결 (제품 전 설계)

시작 `2a85aa0e043cb6d13993742c2a053a8b048c48d5`, 별도 branch `codex/post013-track-a-tk45-applicability`. 불수용 PR93/f8 제품은 동결하고 전체 이식하지 않는다. 원래 정상8/8 유지·부정/확장 각각 시작보다 엄격 증가·어느 것도 감소 없음 계약은 그대로다. 공개245/독립감사/CI는 그 조건을 대체하지 않았다. 이 메모/시험은 **제품 diff 0**이며 비공개 입력·표현·식별자는 사용하지 않았다.

## 원인·다른 접근·근거

f8의 norm proof는 anchor 직후 `민법 제…조`에만 `.match()`한다. 실제 민법 인용이 앞 부사어, 목적어의 괄호 참조, 결론에 결합한 괄호 부사어인 공개 입력에서도 그 위치 때문에 증명하지 못한다. 이번 접근은 인용을 문서 어디서든 찾는 것이 아니라 **독립 norm reference node의 원문 law/article/span → 닫힌 자기 논항 또는 결론 attachment edge → 별도 직접 부정/효과 증명**으로 분리한다. 다른 POSITIVE로 면제·행위 합성·UNKNOWN 재분류·옛 temporal attachment 재시도는 없다.

국립국어원 한국어기초사전 직접 HTTP200 조회(2026-10-11): [따르다1 sense8](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EB%94%B0%EB%A5%B4%EB%8B%A4) “어떤 조건이나 기준, 상황에 근거하다”; [의하다(依) sense1](https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EC%9D%98%ED%95%98%EB%8B%A4) “어떤 사람, 행위, 이념 등에 기초하거나 그것을 이유로 하다”. 공식 뜻과 application `AUTHORED_NORMATIVE_ADJUNCT`는 별개다. 법명·숫자·lemma 자체는 사건에 그 법이 적용됨/효과의 법적 타당성을 인증하지 않는다. 원래 설정의 민법 군집 article/range만 그대로 이용한다. 다른 군집 번호를 민법 번호로 자동 변환하지 않는다.

## 최소 계약

1. 원래 reading-prefix/첫 BODY/원문 source mapping·화자·quote/report/multiline/조건 보호는 그대로다. 한 문장의 닫힌 원문 frame만 대상으로 law=`민법`과 관측 `제…조`를 증명한다. 맨 앞 `norm에 따라/의하여, anchor …`와 기존 `anchor norm에 따라/의하여 …`는 직접 붙은 규범 부사어다. clause를 건너뛰거나 중간 새 actor/topic/unknown qualifier를 소비하지 않는다.
2. `requirement(norm)목적격 …`은 바로 같은 명사 occurrence의 **참조 연결만** 증명한다. 단독 괄호 인용은 규범적 효과를 정당화하는 부사어가 아니다. 기존 단일 직접 과거 부정 grammar의 자기 목적격·술어·부정·종결이 모두 입증된 경우만 추가 부정 후보를 허용한다. 결론 끝 `(norm)`도 닫힌 전체 자기 명제의 참조이며, 타 명제 인용을 가져오지 않는다. 추가 법적 효과는 명시적인 `에 따라/의하여` normative link와 자기 효과 객체·목적격·실제 술어 sense까지 따로 증명해야 한다.
3. 결론 뒤 `(norm에 따라/의하여)`는 정확한 괄호 closure+문장 terminal에 붙은 규범 부사어만 허용한다. bare article·다른 law·단순 인용/수령/필요성 부정·별개 절·중첩 부정·조건·계획·부분·타 논항·타 actor·보고/재반박은 증명 없음이다. `받다` 등의 사전 뜻이나 법률명사만으로 효과를 인증하지 않는다. 기존 finding/state/grade/severity/rule 및 UNKNOWN 출력은 변경하지 않는다. 새 proof 실패는 새 경고가 아니다.
4. law/article/reference/link/argument/case/predicate/closure/conclusion의 **원문 span과 slice**를 분리한다. 사실 진실성·이행/전체완료·법적 충분성·actor identity·다른 act 합성은 모두 false다. 기존 finding과 후속 판단의 중복 제외 계약을 유지한다. 현재 whitespace-view는 지원 설정만 원문 mapping과 함께 재사용한다. 현재 부정·효과 grammar 밖은 그대로 abstain한다.

## 공개 capability·예산·남은 범위

실제 TXT 전체 pipeline+독립 자동 norm-binding prototype **39 PASS/1.12s**: 앞/직후/목적어 괄호/결론 괄호 6개 직접 부정, 앞/직후/후행 괄호 규범 부사어 3개 효과의 원문 연결을 prototype이 찾았다. 자체 공개 f8 코드 비교는 그중 anchor 직후 3개만 proof를 만들고 나머지6은 abstain한다. 30개 bare/wrong-law/다른 조문·별개 절·actor/quote/report/rebuttal/multiline·부수/계획/부분/정상/타 논항·필요성/사실 수령 반대는 양쪽 proof 없음이다. Prototype은 source attachment만 출력하며 **selected legal-effect sense/finding/fulfillment를 생성하지 않는다**. 실제 finding 증가는 아직 미구현·미측정이다.

승인 시 baseline2a85에 최소 새 norm-node/attachment 소비자만 구현하고, f8의 승인된 직접 부정/효과 및 source 보호를 필요한 작은 모듈로 유지한다(전체 branch 이식0). 문장별 공유 인덱스·유한 수의 closed layout·한 lazy conclusion view를 사용하고 source accounting과 이진조회/regex 내부 비용을 구분한다. 전체 pipeline 선형성 주장은 없다. 기존152/245 기대값 및 32k parser→legal 보호, 실제 TXT/PDF/DOCX 양방향·scope/span/JSON, 긴 불일치·성장 비교를 수행한다. 기존 classifier whole32k >60초 잔여는 해소했다고 주장하지 않는다. 약60–90분 + exact CI/독립 source 감사/3줄 요청; 적용 범위가 넓어져도 원래 엄격 증가를 보장하지 않으며 root 원래 게이트로 판정한다. 인용 자체가 없는 문서·새 법률/문장간 scope·새 동사 의미/소유 관계·e21 consumer 예외는 이번 범위 밖이다.
