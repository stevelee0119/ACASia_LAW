# RAG(Drive 참고자료 대조) 대조군 자료 — 시험용 합성 문서

2026-11-14 평가 체계 감사 U3(사용자 승인 'U-1~5 모두 반영'). 두 PDF 모두 평가용 합성 자료이며 실제 규정·지침이 아니다.

| 파일 | 역할 | 기대 |
|---|---|---|
| rag_control_support_night_firing_safety.pdf | 지지 자료: case9 서면의 '통제관이 포강 검사·불발탄 확인을 유기했다'는 주장과 같은 방향의 의무를 적는다 | 대조 자료로 뽑히고, '모순' 의견이 나오지 않으며, '지지' 의견이 나온다 |
| rag_control_unrelated_school_meal.pdf | 무관 자료: case9와 관련 없음 | 뽑히지 않고, '지지·모순' 의견이 나오지 않는다 |

사용 방법
1. 사용자가 두 파일을 운영 Drive 참고자료 폴더(또는 하위 폴더)에 파일 이름 그대로 올린다.
2. 배포 직후 온라인 점검(RELEASE_PROCEDURE 4절)의 case9 결과 JSON을 평가 측이 다음 명세로 함께 채점한다.
   `python scripts/score_report.py --report <결과.json> --spec tests/fixtures/probes/case9_state_compensation_rag_controls_online.json`
3. 자료를 올리기 전 결과는 이 명세로 채점하지 않는다(대조군 없음).
