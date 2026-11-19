# TK-211 배지 정렬 시험이 느린 실행기에서 레이아웃 박스를 못 재고 깨진다 (평가 측 시험 자산)

- 발견일: 2026-11-19 (평가 세션, PR #341 CI)
- 종류: **시험 자산 불안정.** 제품 결함이 아니다
- 상태: open

## 증상

`tests/test_aegislaw_261116_batch_a.py::test_review_verdict_badges_left_aligned_when_wrapped`가
같은 커밋에서 실행마다 갈린다.

| 실행 (head `8d858466`) | 결과 |
|---|---|
| 44415551963 | **실패** — `assert first_badge and claim_badge` → `assert (None)` |
| 44415562856 | 통과 |

평가 측 환경 단독 실행도 통과. 12,649건 중 1건만 실패했다.

## 원인

같은 시험 안에서 **첫 측정과 두 번째 측정의 대기 방식이 다르다.**

첫 측정(실패 지점)은 가시성만 기다린다.

    expect(container.locator("span.badge").first).to_be_visible()
    expect(row.locator(".claim-verdict")).to_be_visible()
    first_badge = container.locator("span.badge").first.bounding_box()
    claim_badge = row.locator(".claim-verdict").bounding_box()
    assert first_badge and claim_badge          # ← 여기서 None

두 번째 측정은 이미 박스 확정을 기다린다.

    page.wait_for_function(
        "() => { ... return !!(b && v && b.getBoundingClientRect().height && ... ); }")
    wrapped_first = container.locator("span.badge").first.bounding_box()

`expect(...).to_be_visible()`은 요소가 보이는 것만 보장하고 **레이아웃 박스가 잡힌 것은 보장하지
않는다.** 느린 실행기에서 배치가 끝나기 전에 `bounding_box()`를 불러 `None`이 돌아온다.
시험 주석도 이 위험을 적어 두었으나("1~2코어 실행기에서 렌더가 늦어지면 bounding_box()가 None을
돌려주어"), 넣은 대기가 가시성 단언이어서 부족하다.

## 고칠 방법

첫 측정 앞에도 두 번째 측정과 **같은 꼴의 `wait_for_function`**을 둔다. 배지와 `.claim-verdict`의
`getBoundingClientRect()`가 0이 아닌 높이·너비를 가질 때까지 기다린 뒤 잰다.
대기만 추가하고 **단언 내용은 바꾸지 않는다.** 시험을 건너뛰거나 허용 오차를 넓히지 않는다.

같은 파일·같은 묶음의 다른 Playwright 시험에도 `expect(...).to_be_visible()` 다음에 바로
`bounding_box()`를 부르는 자리가 있는지 전수로 보고, 있으면 함께 고친다(한 자리만 고치면
다음에 다른 자리가 깨진다).

## 수용 기준

1. 첫 측정 앞에 박스 확정 대기가 들어간다
2. 같은 파일에서 가시성 단언 직후 `bounding_box()`를 부르는 자리가 남지 않는다
3. 단언 내용·허용 오차 변경 없음, 건너뛰기·`xfail` 없음
4. 브라우저 시험 전체 통과

## 미검증

실패를 평가 측 환경에서 재현하지 못했다(단독 실행은 통과). 원인은 시험 코드의 대기 방식 차이로
정적 확인한 것이며, 느린 실행기를 흉내 내 재현하지는 않았다.
