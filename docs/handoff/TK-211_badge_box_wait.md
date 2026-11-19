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

---

## 원인 재정정 (2026-11-19, 평가 측 실측)

**두 번째 진단도 불완전했다.** 앞에서 "`bounding_box()`가 `None`인 것은 그 요소가 DOM에서
떨어진 것"이라고 적었으나, 떨어진 경우는 `None`이 아니라 **시간초과**다. Locator는 선택자를
다시 풀기 때문이다. 실측으로 조건을 확정했다.

| 요소 상태 | `is_visible()` | `bounding_box()` |
|---|---|---|
| 보통 | True | 박스 |
| 0 크기 | False | **박스(0 크기)** |
| **`display:none`** | False | **None** |
| `visibility:hidden` | False | 박스 |
| 제거됨 | — | **TimeoutError** |

즉 `None`은 **레이아웃 박스가 없을 때만** 나온다. 곧 그 요소나 그 조상이 `display:none`일
때뿐이다. 따라서 44415551963 실행이 `assert (None)`로 깨진 것은 **가시성 단언이 통과한 뒤
측정 순간에 검토 탭 패널이 다시 그려져 `display:none`이 된 것**이다.

이것이 왜 중요한가: 앞선 회차에서 내가 넣은 완화(가시성 단언을 측정 앞에 더 놓기)는 **그 창을
없앨 수 없다.** 단언과 측정이 별개 호출이기 때문이다. 실제로 그 완화가 들어간 head
`8d858466`에서 실패가 났다. 진단이 틀렸으니 완화도 효과가 없었다.

## 수정

두 좌표를 **한 번의 `wait_for_function`**으로 함께 읽는다. 그 JS는 둘 다 레이아웃 박스를
가질 때만 값을 돌려주므로, 일시적 `display:none`을 기다려 주고 두 측정 사이의 창이 아예 없다.
래핑 뒤 측정도 같은 방식으로 바꿨다(재배치 조건을 같은 호출에 넣었다). **단언 내용은 그대로다** —
좌측 x 차이 1.5px 미만, 근거 배지가 아래 줄.

`tests/test_aegislaw_261116_batch_a.py`의 `_READ_BOXES_JS` 하나를 두고 래핑판은 조건 한 줄을
끼워 만든다. 두 곳이 어긋나지 않게 하기 위함이다.

## 사전 검증 (평가 측 재실행, 실제 브라우저)

| 검증 | 결과 |
|---|---|
| `None` 조건 실측 | 위 표. `display:none`만 `None`, 제거는 시간초과, 0 크기·`visibility:hidden`은 박스 |
| **증상 재현** | 가시성 단언 통과 뒤 행을 120ms 동안 `display:none`으로 두니 옛 패턴이 `first=None claim=None` → `assert first and claim` **실패**. CI 실패와 같은 꼴이다 |
| **수정 확인** | 같은 조건에서 새 패턴은 한 번에 읽어 **견딘다**(좌측차 0.00px) |
| **시험이 무력해지지 않았는지** | 근거 배지를 `margin-left: 20px`로 밀자 좌측차 20.00px → 단언(<1.5) **실패**. 시험이 결함을 여전히 잡는다 |
| 본 시험 실행 | 통과 (평가 환경, 사전 설치 Chromium) |

## 상태

**해소.** 1~2코어 실행기에서의 재발 여부는 CI 실행으로 확인한다(이 수정이 병합된 뒤 관찰).

## 정정 이력

1. 1차 진단: "`to_be_visible()`이 레이아웃 박스를 보장하지 않는다" — **틀렸다**(가시성은 비어
   있지 않은 박스를 요구한다). PR #345 사후 검토 지적으로 확인.
2. 2차 진단: "`None`은 요소가 떨어진 것" — **불완전했다**(떨어지면 시간초과다).
   2026-11-19 실측으로 `display:none`이 유일한 `None` 조건임을 확정.
3. 세 번째에 와서야 원인과 해법이 맞았다. 교훈: **Playwright API의 반환 조건을 기억으로 적지
   않는다. 조건표를 실제 브라우저로 한 번 재고 그 표를 근거로 쓴다.**
