# PAGE named ActualText: 미지원 source의 inspection coverage (제품 전 보완)

PR95/ad8d의 source 인증은 stream/non-string에서 이미 UNKNOWN이다. 그러나 capture `entry(raw)`가 non-bytes를 조용히 반환하여 선택된 실제 PAGE ActualText stream의 decode0/수집0을 `inspection_complete=true`로 표시했다. 이 메모는 그 coverage 오표시만 고친 test-only capability 보완이며 packages 제품 diff0다. 기존88 기대값, cap/문맥/visibility/source 보호는 바꾸지 않는다.

## 공개 실패·계약

원래 ad8 capture에 실제 PDF stream·number·dictionary present values, missing/invalid selected Properties 및 unresolved string reference를 적용한 새7건은 **6 FAIL/1 PASS**였다. 정확히 dictionary가 해석되고 `ActualText` key가 없는 경우만 known absence라 complete를 유지한다. key가 있는데 값이 stream/non-string인 경우, 선택된 property가 없거나 dictionary로 해석되지 않거나 원래 indirect reference가 해석되지 않는 경우는 **UNKNOWN + inspection_complete=false**, decode/수집0이다. budget overflow와 unsupported/resolution failure는 다른 사유이며 `budget_exceeded`를 잘못 세우지 않는다.

추가 진단은 `unsupported_actualtext_values`, `actualtext_absent`, `selected_property_missing`, `selected_property_invalid`, 기존 `resolution_failures`로 나눈다. 스트림을 문자열로 억지 변환하거나 명령을 안전하다고 인증하지 않는다. unsupported present source는 검사되지 않았다는 coverage 한계를 남긴다. 문자열 인증의 strict reject와 원래 indirect-string inspection은 분리한다: 원래 indirect 문자열을 성공적으로 한 번 검사했는데 certification이 PDFObjRef를 거절했다는 이유로 coverage를 거짓 실패로 만들지 않는다. 기존 direct/indirect×2k/60k capture1 및 raw 객체 재사용·page/Form cache scope/caps는 그대로다.

## 확인·잔여

test-only adapter의 선택된 PAGE Properties와 capture 시점에만 이 진단을 붙였다. entry-byte admission/strict decoding/reference/cache/context/retained caps, 원문 reading/serialization/security 양성 및 Form-only indirect 잔여는 그대로 유지한다. 공개 **95 PASS/2.49s**를 제품 변경 없이 확인했다. 내부 parser/object graph 전체 coverage·Form/resource 전체 복원·whole linearity 주장은 없다. 실제 미지원 stream을 안전 또는 검사 완료로 표시하지 않는 최소 메타데이터 계약이며 제품은 root 승인 전이다.
