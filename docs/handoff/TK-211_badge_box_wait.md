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

## 원인 (2026-11-19 정정)

**처음 적은 진단은 틀렸다.** 처음에는 "`expect(...).to_be_visible()`이 레이아웃 박스가 잡힌 것을
보장하지 않는다"고 적었으나, Playwright의 가시성 판정은 **비어 있지 않은 박스를 이미 요구한다.**
평가 측 실측으로 확인했다.

    #a (width:0;height:0)    isVisible=false   boundingBox={"width":0,"height":0}
    #b (width:50px;height:20px) isVisible=true  boundingBox={"width":50,"height":20}

즉 가시성 단언이 통과한 시점에는 박스가 이미 비어 있지 않다. 또한 크기가 0인 요소도
`boundingBox()`는 `None`이 아니라 0 크기 박스를 돌려준다.

**`bounding_box()`가 `None`을 돌려주는 것은 그 요소가 측정 시점에 DOM에 붙어 있지 않을 때다.**

따라서 실제 원인은 **가시성 단언과 측정 사이에 요소가 바뀌는 것**이다. 이 시험은 검토 탭을 누른
뒤 표의 행을 찾는데, 화면 스크립트가 그 사이에 표를 다시 그리면 앞서 찾아 둔 요소가 떨어져 나가고
새 요소로 바뀐다. 느린 실행기에서는 그 재그리기가 단언 뒤에 올 확률이 높아진다.

    expect(container.locator("span.badge").first).to_be_visible()   # 이 시점의 요소는 살아 있다
    expect(row.locator(".claim-verdict")).to_be_visible()
    first_badge = container.locator("span.badge").first.bounding_box()   # 그 사이 재그리기 → None
    claim_badge = row.locator(".claim-verdict").bounding_box()
    assert first_badge and claim_badge

같은 시험의 두 번째 측정이 `wait_for_function`으로 통과하는 것은 박스를 기다려서가 아니라,
그 시점에는 재그리기가 이미 끝나 요소가 안정되어 있기 때문이다.

## 고칠 방법 (정정)

대기를 더 넣는 것으로는 풀리지 않는다. 단언과 측정 **사이의 창을 없앤다.**

두 박스를 **한 번의 `evaluate` 호출 안에서** 함께 읽는다. 그러면 읽는 사이에 재그리기가 끼어들
수 없고, 두 좌표가 같은 레이아웃 시점의 값임도 보장된다.

    boxes = row.evaluate("""el => {
        const b = el.querySelector('.review-verdict-badges span.badge');
        const v = el.querySelector('.claim-verdict');
        if (!b || !v) return null;
        const bb = b.getBoundingClientRect(), vb = v.getBoundingClientRect();
        return {bx: bb.x, by: bb.y, vx: vb.x, vy: vb.y};
    }""")
    assert boxes, "배지와 판정 열이 같은 시점에 모두 있어야 한다"

단언 내용(좌측 정렬 일치, 줄바꿈 확인)은 그대로 둔다. 허용 오차를 넓히거나 건너뛰지 않는다.

같은 파일·같은 묶음의 다른 Playwright 시험에서도 **두 요소의 좌표를 따로 읽어 비교하는 자리**를
전수로 찾아 같은 방식으로 바꾼다. 한 자리만 고치면 다음에 다른 자리가 깨진다.

## 수용 기준

1. 두 요소의 좌표를 한 번의 `evaluate` 안에서 함께 읽는다(단언과 측정 사이에 창이 없다)
2. 같은 파일에서 두 요소의 좌표를 따로 읽어 비교하는 자리가 남지 않는다(전수 조사 목록과 함께 보인다)
3. 단언 내용·허용 오차 변경 없음, 건너뛰기·`xfail` 없음
4. 브라우저 시험 전체 통과

## 미검증

실패를 평가 측 환경에서 재현하지 못했다(단독 실행은 통과). 느린 실행기를 흉내 내 재현하지 못했다.

Playwright의 가시성이 비어 있지 않은 박스를 요구한다는 점은 평가 측 실측으로 확인했다. 그러나
**재그리기가 실제로 그 창에서 일어난다는 것은 재현하지 못했다** — 화면 스크립트의 어느 경로가 표를
다시 그리는지까지는 추적하지 않았다. 고칠 방법(한 번의 `evaluate`)은 재그리기 여부와 무관하게 창
자체를 없애므로 원인 확정 전에도 적용할 수 있다.

## 정정 이력

2026-11-19 처음 적은 진단("가시성 단언은 레이아웃 박스가 잡힌 것을 보장하지 않는다")은 틀렸다.
PR #345 사후 검토 지적을 받아 평가 측이 실측으로 확인하고 고쳤다. 원인·고칠 방법·수용 기준을 모두
바꿨다.
