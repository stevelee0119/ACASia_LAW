"""직접 인용문의 변형 탐지(v2 Phase 4, v3 D1: 어절 단위 diff, MODIFIED_QUOTE).

인용문이 원문과 거의 같아도(유사도 0.85 이상 1.0 미만) 정도 부사("현저하게")를 빼거나, 부정·양태("할 수
있다" ↔ "하여야 한다")·조문 한정어(단서·본문·제N항)·수량을 바꾸면 판시의 의미가 달라진다. 유사도만 보면 '일부
일치'로 통과한다.

1. 원문에서 인용문과 가장 비슷한 구간을 공백·문장부호를 뺀 글자열로 찾는다(띄어쓰기 차이는 변형이 아니다).
2. 그 구간을 어절 경계까지 넓혀 원문 어절열을 얻고, 인용문 어절열과 비교해 삭제·추가·치환 어절을 낸다.
   구간 양 끝의 차이는 인용 범위를 자른 자리일 수 있으므로 변형으로 보지 않는다.
3. 말줄임표(…, ..., (중략))로 생략을 표시한 인용은 표시된 구간마다 따로 대조한다(생략 자체는 변형이 아니다).
4. 바뀐 어절에 정도 부사·부정·양태·조문 한정어·수량이 들어 있고 양쪽이 다르면 의미 변형(meaningful)이다.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from packages.common.textutil import normalize_quote

MEANINGFUL_CHANGES = [
    ("DEGREE", "정도 부사", re.compile(r"현저|상당|명백|중대|매우|극히|다소|약간|전혀|반드시|항상|언제나|오로지|오직|특히")),
    ("NEGATION", "부정어 삽입/탈락", re.compile(r"아니|않|못|없|불가|금지|배제")),
    ("MODALITY", "양태(가능·의무)", re.compile(r"수있|하여야|해야|하도록|하여서는|할것|하지아니할")),
    # 긴 낱말을 먼저 둔다('주채무자'·'피신청인'이 '채무자'·'신청인'으로 잘리지 않게)
    ("PARTY_SWAP", "주어·객체 바뀜", re.compile(
        r"주채무자|피상속인|피신청인|피청구인|피고인|원고|피고|처분청|행정청|당사자|채권자|채무자|신청인|청구인|상속인"
        r"|매도인|매수인|임대인|임차인|도급인|수급인|위임인|수임인|사용자|근로자|보증인|양도인|양수인|증여자|수증자"
        r"|임치인|수치인|가해자|피해자|소유자|점유자")),
    ("PROVISION_QUALIFIER", "조문 한정어", re.compile(r"단서|본문|전단|후단|제\d+항|제\d+호|각호")),
    ("PROVISO_OMISSION", "단서·예외 탈락", re.compile(r"다만|특별한\s*사정이\s*없는\s*한|예외|제외")),
    ("NUMERIC", "수치 불일치", re.compile(r"\d+")),
]
MIN_SIMILARITY = 0.75
MIN_SEGMENT = 8  # 생략 표시로 나눈 구간 중 이보다 짧은 조각은 대조하지 않는다
ELLIPSIS_RE = re.compile(r"…+|\.{3,}|\(\s*중\s*략\s*\)|\[\s*중\s*략\s*\]")
DROP_RE = re.compile(r"[\s\"'“”‘’.,·「」『』()\[\]<>《》]")
OP_LABELS = {"delete": "삭제", "insert": "추가", "replace": "치환"}


def _compact(text: str) -> str:
    return DROP_RE.sub("", normalize_quote(text or ""))


def _compact_with_map(text: str) -> Tuple[str, List[int]]:
    kept, index = [], []
    for position, char in enumerate(text):
        if not DROP_RE.match(char):
            kept.append(char)
            index.append(position)
    return "".join(kept), index


def _best_window(haystack: str, needle: str) -> Tuple[int, int, float]:
    """haystack에서 needle과 가장 비슷한 구간 (시작, 끝, 유사도)."""
    if not needle or not haystack:
        return 0, 0, 0.0
    exact = haystack.find(needle)
    if exact >= 0:
        return exact, exact + len(needle), 1.0
    size = len(needle)
    best = (0, 0, 0.0)
    matcher = SequenceMatcher(None, "", needle, autojunk=False)
    step = max(1, size // 10)
    for width in {size, int(size * 1.1) + 1, int(size * 0.9)}:
        for start in range(0, max(1, len(haystack) - width + 1), step):
            window = haystack[start:start + width]
            matcher.set_seq1(window)
            if matcher.real_quick_ratio() <= best[2] or matcher.quick_ratio() <= best[2]:
                continue
            ratio = matcher.ratio()
            if ratio > best[2]:
                best = (start, start + len(window), ratio)
    return best


def _word_span(text: str, start: int, end: int) -> str:
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[start:end]


def _minor(original: str, quoted: str) -> bool:
    a, b = _compact(original), _compact(quoted)
    common = 0
    while common < min(len(a), len(b)) and a[common] == b[common]:
        common += 1
    return bool(a and b) and common >= 2 and max(len(a), len(b)) - common <= 2


# 창 전체 비교(어절 대조가 성립하지 않을 만큼 다른 인용)에서는 부정의 활용형까지 본다. 어절 대조에서는 어간만 본다
# ('없다'→'없는 것이다'는 부정이 그대로다).
_NEGATION_SURFACE_RE = re.compile(r"아니(?:한다|된다|하다)?|않(?:는다|다)?|못(?:한다|하다)?|없(?:다|는)?|불가|금지|배제")


# 당사자는 집합이 아니라 나온 순서로 견준다: '채권자는 채무자에게'→'채무자는 채권자에게'는 같은 낱말의 맞바꿈이다
_ORDERED_KINDS = {"PARTY_SWAP"}


def _classify(original: str, quoted: str, surface: bool = False) -> List[Tuple[str, str]]:
    a, b = _compact(original), _compact(quoted)
    out = []
    for kind, label, pattern in MEANINGFUL_CHANGES:
        pat = _NEGATION_SURFACE_RE if surface and kind == "NEGATION" else pattern
        found_a, found_b = pat.findall(a), pat.findall(b)
        if (found_a != found_b) if kind in _ORDERED_KINDS else (set(found_a) != set(found_b)):
            out.append((kind, label))
    return out


def _segment_ops(quote: str, official: str) -> Optional[Tuple[float, List[Dict[str, Any]]]]:
    norm_off = normalize_quote(official)
    compact_off, index = _compact_with_map(norm_off)
    needle = _compact(quote)
    start, end, ratio = _best_window(compact_off, needle)
    if ratio < MIN_SIMILARITY:
        return None
    if ratio >= 1.0:
        return ratio, []
    segment = _word_span(norm_off, index[start], index[end - 1] + 1)
    seg_at = norm_off.find(segment, max(0, index[start] - len(segment)))
    seg_at = seg_at if seg_at >= 0 else index[start]
    # 창 바로 앞뒤의 원문 어절(창 정렬이 끝 어절을 빼먹은 경우 맞대어 볼 상대)
    prev_word = (norm_off[:seg_at].split() or [""])[-1]
    next_word = (norm_off[seg_at + len(segment):].split() or [""])[0]
    original, quoted = segment.split(), normalize_quote(quote).split()
    keys_o, keys_q = [_compact(w) for w in original], [_compact(w) for w in quoted]
    ops: List[Dict[str, Any]] = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, keys_o, keys_q, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        is_boundary = (i1 == 0 and j1 == 0) or (i2 == len(original) and j2 == len(quoted))
        before, after = " ".join(original[i1 - 1:i1]), " ".join(original[i2:i2 + 1])
        o_text, q_text = " ".join(original[i1:i2]), " ".join(quoted[j1:j2])
        if _compact(o_text) == _compact(q_text):
            continue  # 띄어쓰기만 다름
        if is_boundary and op in ("insert", "delete"):
            # 창 정렬이 원문 끝 어절을 빼거나 넣은 자리다. 인용문에 더해진 어절은 바로 옆 원문 어절과 맞대어 본다
            # ('원고가'를 뺀 창 + 인용 '원고는' → '원고가'↔'원고는'). 원문에서만 빠진 끝 어절은 인용 범위 절단이다.
            if op == "delete":
                continue
            at_start = i1 == 0 and j1 == 0
            neighbor = (before or prev_word) if at_start else (after or next_word)
            if not neighbor or _compact(neighbor) == _compact(q_text):
                continue
            o_text, op = neighbor, "replace"
        kinds = _classify(o_text, q_text)
        if is_boundary and not kinds:
            continue  # 구간 끝의 단순 인용 범위 절단은 무시하되, 의미 변경(부정·주어 등)은 유지
        if not kinds and _minor(o_text, q_text):
            continue  # 어미·조사 1~2자 차이("것이라고"→"것이라")는 의미를 바꾸지 않는다
        ops.append({"op": op, "label": OP_LABELS[op], "original": o_text, "quoted": q_text,
                    "before": before, "after": after, "kinds": [k for k, _ in kinds],
                    "kind_labels": [label for _, label in kinds]})
    return ratio, ops


def quote_changes(quote: str, official_text: str) -> Optional[Dict[str, Any]]:
    """원문과 다른 어절이 있으면 {similarity, ops, changes, meaningful, deleted, inserted}, 없으면 None.

    유사도 0.85 미만(다른 문장)이나 완전 일치는 None이다. 불일치 판정은 호출하는 쪽의 유사도 검사가 맡는다.
    """
    segments = [s for s in ELLIPSIS_RE.split(quote or "") if len(_compact(s)) >= MIN_SEGMENT]
    if not segments:
        return None
    ratios, ops = [], []
    for segment in segments:
        found = _segment_ops(segment, official_text)
        if found is None:
            return None
        ratios.append(found[0])
        ops.extend(found[1])
    if not ops:
        return None
    changes = []
    for op in ops:
        for kind, label in zip(op["kinds"], op["kind_labels"]):
            side = {"delete": "원문에서 빠짐", "insert": "인용문에 더해짐"}.get(op["op"], "치환")
            text = op["original"] if op["op"] == "delete" else op["quoted"] if op["op"] == "insert" \
                else f"{op['original']} → {op['quoted']}"
            changes.append({"kind": kind, "label": label, "side": side, "text": text, "op": op["op"]})
    categories = []
    category_labels = []
    for c in changes:
        k = c["kind"]
        if k in ("QUANTITY", "NUMERIC") and "NUMERIC" not in categories:
            categories.append("NUMERIC")
            category_labels.append("수치 불일치")
        elif k == "NEGATION" and "NEGATION" not in categories:
            categories.append("NEGATION")
            category_labels.append("부정어 삽입/탈락")
        elif k == "PARTY_SWAP" and "PARTY_SWAP" not in categories:
            categories.append("PARTY_SWAP")
            category_labels.append("주어·객체 바뀜")
        elif k == "PROVISO_OMISSION" and "PROVISO_OMISSION" not in categories:
            categories.append("PROVISO_OMISSION")
            category_labels.append("단서·예외 탈락")
        elif k in ("MODALITY", "DEGREE", "PROVISION_QUALIFIER") and k not in categories:
            categories.append(k)
            category_labels.append(c["label"])

    return {"similarity": round(min(ratios), 3), "ops": ops, "changes": changes, "meaningful": bool(changes),
            "diff_categories": categories, "category_labels": category_labels,
            "deleted": [o["original"] for o in ops if o["op"] in ("delete", "replace")],
            "inserted": [o["quoted"] for o in ops if o["op"] in ("insert", "replace")]}


def categorize_quote_diff(quote: str, official_text: Optional[str], *, has_full_text: bool = True) -> Dict[str, Any]:
    """공식 판결문 원문과 인용문 대조 및 차이 유형 5종 구조화 (LV-04, CIT-FAB-Q)."""
    if not official_text or not has_full_text or len(official_text.strip()) < 30:
        return {
            "status": "TEXT_UNAVAILABLE",
            "can_compare": False,
            "similarity": None,
            "diff_categories": [],
            "category_labels": [],
            "reason": "공식 판결문 본문 미확보로 인용 대조 불가 (판결요지 등 요약본만 확보되어 본문 인용 대조 유보)",
            "defect_summary": "본문 미확보 대조 불가",
        }

    clean_quote = normalize_quote(quote or "").strip()
    if not clean_quote:
        return {
            "status": "NO_QUOTE",
            "can_compare": False,
            "similarity": 0.0,
            "diff_categories": [],
            "category_labels": [],
            "reason": "대조할 직접 인용문이 없습니다.",
            "defect_summary": "인용문 없음",
        }

    norm_off = normalize_quote(official_text)
    compact_off, off_map = _compact_with_map(norm_off)
    needle = _compact(clean_quote)
    if not needle:
        return {
            "status": "NO_QUOTE",
            "can_compare": False,
            "similarity": 0.0,
            "diff_categories": [],
            "category_labels": [],
            "reason": "대조할 직접 인용문이 없거나 기호만 포함되어 있습니다.",
            "defect_summary": "인용문 없음",
        }

    w_start, w_end, max_ratio = _best_window(compact_off, needle)

    if max_ratio < 0.50:
        return {
            "status": "UNALIGNED_QUOTE",
            "can_compare": True,
            "similarity": round(max_ratio, 3),
            "diff_categories": ["CONTENT_MISMATCH"],
            "category_labels": ["원문 대조 불일치 (대응 구간 미확정)"],
            "reason": f"공식 판결문 본문에서 직접 인용문과 일치하는 구간을 특정하지 못했습니다 (최대 유사도 {max_ratio:.2f}). 저유사도만으로 가공 인용을 단정하지 않고 원문 대조 필요로 처리합니다.",
            "defect_summary": f"인용문 불일치(유사도 {max_ratio:.2f})",
        }

    # 전체 문헌에서 인용문 대응 후보 구간(candidate_text)을 먼저 특정하여 무관한 타 문단의 숫자/어휘가 차이로 흡수되는 것 방지 (LV-04-R3)
    if off_map and w_start < len(off_map):
        o_start = off_map[w_start]
        o_end = off_map[min(len(off_map) - 1, max(0, w_end - 1))] + 1
        candidate_text = _word_span(norm_off, o_start, o_end)
    else:
        candidate_text = official_text

    changes_result = quote_changes(clean_quote, candidate_text)
    if not changes_result:
        changes_result = quote_changes(clean_quote, official_text)

    if not changes_result and ELLIPSIS_RE.search(clean_quote):
        segs = [x for x in ELLIPSIS_RE.split(clean_quote) if len(_compact(x)) >= MIN_SEGMENT]
        found = [_segment_ops(x, official_text) for x in segs]
        if segs and all(f is not None and not f[1] for f in found):
            return {
                "status": "EXACT_MATCH",
                "can_compare": True,
                "similarity": round(min(f[0] for f in found), 3),
                "diff_categories": [],
                "category_labels": [],
                "reason": "생략 표시로 나눈 구간이 모두 공식 원문과 일치합니다.",
                "defect_summary": "일치(생략 인용)",
            }

    if not changes_result:
        if max_ratio >= 0.995:
            return {
                "status": "EXACT_MATCH",
                "can_compare": True,
                "similarity": round(max_ratio, 3),
                "diff_categories": [],
                "category_labels": [],
                "reason": "공식 원문과 완전 일치합니다.",
                "defect_summary": "일치",
            }
        # 어절 대조에서 의미 변경이 없었으면(유사도 0.85 이상) 창 전체를 다시 분류하지 않는다(창 밖 어절이 변경으로 잡힌다).
        # 어절 대조가 성립하지 않을 만큼 다른 인용(0.85 미만)만 창 전체로 분류한다
        substantive = _classify(candidate_text, clean_quote, surface=True) if max_ratio < 0.85 else []
        cats = [k for k, _ in substantive]
        labels = [lbl for _, lbl in substantive]
        if not cats:
            if max_ratio < 0.85:
                cats = ["CONTENT_MISMATCH"]
                labels = ["내용 불일치"]
            else:
                cats = ["MINOR_WORDING"]
                labels = ["단순 자구·어미 차이"]
        return {
            "status": "MODIFIED_QUOTE",
            "can_compare": True,
            "similarity": round(max_ratio, 3),
            "diff_categories": cats,
            "category_labels": labels,
            "reason": (
                f"공식 원문과 표현상의 차이가 있습니다 (유사도 {max_ratio:.2f})."
                if "MINOR_WORDING" in cats
                else f"공식 원문과 실질적 내용 차이가 있습니다 (유사도 {max_ratio:.2f}): {', '.join(labels)}."
            ),
            "defect_summary": "단순 자구 차이" if "MINOR_WORDING" in cats else f"인용문 내용 차이({', '.join(labels)})",
        }

    cats = list(changes_result.get("diff_categories") or [])
    labels = list(changes_result.get("category_labels") or [])
    if not cats:
        cats = ["MINOR_WORDING"]
        labels = ["단순 자구·어미 차이"]

    return {
        "status": "MODIFIED_QUOTE",
        "can_compare": True,
        "similarity": changes_result["similarity"],
        "diff_categories": cats,
        "category_labels": labels,
        "ops": changes_result["ops"],
        "changes": changes_result["changes"],
        "meaningful": changes_result["meaningful"],
        "reason": render_quote_diff(changes_result),
        "defect_summary": quote_diff_summary(changes_result),
    }


def render_quote_diff(result: Dict[str, Any], limit: int = 4) -> str:
    """바뀐 어절을 원문과 나란히: 삭제 — 원문 「사회통념상 [현저하게] 타당성을」 → 인용 「사회통념상 타당성을」."""
    parts = []
    for op in (result.get("ops") or [])[:limit]:
        before = f"{op['before']} " if op["before"] else ""
        after = f" {op['after']}" if op["after"] else ""
        original = f"{before}[{op['original']}]{after}" if op["original"] else f"{before}{after}".strip()
        quoted = f"{before}[{op['quoted']}]{after}" if op["quoted"] else f"{before}{after}".strip()
        kinds = f"({', '.join(op['kind_labels'])})" if op["kind_labels"] else ""
        parts.append(f"{op['label']}{kinds} — 원문 「{original.strip()}」 → 인용 「{quoted.strip()}」")
    extra = len(result.get("ops") or []) - limit
    return "; ".join(parts) + (f"; 외 {extra}곳" if extra > 0 else "")


def quote_diff_summary(result: Dict[str, Any]) -> str:
    """짧은 결함 요약: 인용문 변형: 원문 '현저하게' 삭제."""
    pieces = []
    for op in (result.get("ops") or [])[:3]:
        if op["op"] == "delete":
            pieces.append(f"원문 '{op['original']}' 삭제")
        elif op["op"] == "insert":
            pieces.append(f"'{op['quoted']}' 추가")
        else:
            pieces.append(f"'{op['original']}'→'{op['quoted']}'")
    return "인용문 변형: " + ", ".join(pieces)
