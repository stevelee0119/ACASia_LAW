"""비공식 약칭으로 적힌 법령명의 공식 법령 추정(TK-130).

서면은 공식 약칭이 아닌 줄임말("중대재해법", "인공지능법")을 자주 쓴다. 국가법령정보 목록 검색은 이런 이름에
0건을 돌려주고, 문서 안에 정식 법령명도 없으면 지금까지는 '법령 목록에서 찾지 못한 법령'(CRITICAL)이 됐다.

어간(끝의 법·시행령·시행규칙을 뗀 몸통)으로 다시 찾은 목록에서, 적힌 이름의 글자가 후보의 공식 약칭
(약칭이 없으면 정식 법령명) 안에 순서대로 모두 나오는지(부분수열)로 점수를 매긴다. 판단 규칙(보수적):
- 법령 종류(법률·시행령·시행규칙)가 다르면 후보가 아니다.
- 후보에 공식 약칭이 있으면 약칭과만 대조한다. 약칭이 없을 때만 정식 법령명과 대조한다.
- 첫 글자가 같아야 한다. 어간은 3자 이상이어야 한다.
- 문턱을 넘는 법령(law_id)이 하나뿐이거나, 1위가 2위보다 충분히 앞설 때만 추정한다.
이 추정은 존재 확인이 아니다. 호출 측은 추정 법령에 인용 조문이 있을 때만 쓰고, '확인됨'으로 올리지 않는다.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

KIND_SUFFIXES = (("시행규칙", "시행규칙"), ("시행령", "시행령"))
MIN_STEM = 3
SHORT_STEM = 2          # 두 글자 어간('노조'·'산안')은 첫 글자 사전식 목록에서만 고른다(TK-143)
# 법제처 lawSearch.do의 gana 값. ㅇ은 'ah'다('a'는 알 수 없는 값으로 처리되어 전체 목록 5,631건이 온다 — 11-03 평가 측
# 실제 응답 확인, TK-148). 알 수 없는 값은 오류 없이 필터 없는 목록을 돌려주므로 값이 틀리면 늘 상한(INCOMPLETE)에 걸린다.
_GANA = ("ga", "ga", "na", "da", "da", "ra", "ma", "ba", "ba", "sa", "sa", "ah", "ja", "ja", "cha", "ka", "ta",
         "pa", "ha")


def gana_code(name: str) -> Optional[str]:
    """첫 글자의 초성을 법제처 사전식 검색 값(ga·na·da …)으로. 한글 음절이 아니면 None."""
    c = compact(name)
    if not c or not ("가" <= c[0] <= "힣"):
        return None
    return _GANA[(ord(c[0]) - 0xAC00) // 588]
THRESHOLD = 500
MARGIN = 100


def compact(name: Optional[str]) -> str:
    text = unicodedata.normalize("NFC", name or "")
    return re.sub(r"[\s·•「」『』]", "", text)


def law_kind(name: str) -> str:
    c = compact(name)
    for suffix, kind in KIND_SUFFIXES:
        if c.endswith(suffix):
            return kind
    return "법률"


def stem(name: str) -> str:
    c = compact(name)
    for suffix, _ in KIND_SUFFIXES:
        if c.endswith(suffix):
            c = c[: -len(suffix)]
            break
    return re.sub(r"(법률|법)$", "", c)


def is_subsequence(query: str, target: str) -> bool:
    if not query or len(query) > len(target):
        return False
    at = 0
    for ch in query:
        at = target.find(ch, at)
        if at < 0:
            return False
        at += 1
    return True


def _initials_subsequence(query: str, target: str) -> bool:
    """두 음절 줄임말의 각 글자가 정식명의 말마디 첫 음절(공백 없는 정식명에서 짝수 위치로 근사)에 순서대로 있는지.
    한국어 법령명은 두 음절 낱말이 이어진 꼴이 대부분이라 줄임말 글자는 짝수 위치에 온다('노동조합' → 노·조)."""
    at = 0
    for ch in query:
        i = target.find(ch, at)
        while i >= 0 and i % 2:
            i = target.find(ch, i + 1)
        if i < 0:
            return False
        at = i + 1
    return True


def score(written: str, record: Dict[str, Any], *, min_stem: int = MIN_STEM) -> int:
    q = compact(written)
    if len(stem(q)) < min_stem:
        return 0
    abbreviation = compact(record.get("abbreviation"))
    target = abbreviation or compact(record.get("law_name"))
    if not target or law_kind(target) != law_kind(q) or target[0] != q[0]:
        return 0
    if target == q or not is_subsequence(q, target):
        return 0
    if min_stem == SHORT_STEM and len(stem(q)) == SHORT_STEM and not (
            _initials_subsequence(stem(q), stem(target)) or stem(target).startswith(stem(q))):
        return 0                       # 두 음절 줄임말: 말마디 첫 음절이거나 정식명 첫 낱말 그대로(TK-143)
    base = 800 if abbreviation else 600
    return base - min(len(target) - len(q), 200 if not abbreviation else 100)


def pick(written: str, records: Iterable[Dict[str, Any]], *, min_stem: int = MIN_STEM
         ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """(우선 후보, 문턱을 넘은 후보 목록). 1위가 하나뿐이거나 2위보다 MARGIN 이상 앞설 때만 우선 후보를 정한다."""
    best: Dict[str, Dict[str, Any]] = {}
    for record in records:
        law_id = str(record.get("law_id") or "").lstrip("0")
        value = score(written, record, min_stem=min_stem)
        if not law_id or value < THRESHOLD:
            continue
        if law_id not in best or value > best[law_id]["score"]:
            best[law_id] = {"law_name": record.get("law_name"), "law_id": law_id,
                            "abbreviation": record.get("abbreviation") or None, "score": value,
                            "basis": "OFFICIAL_ABBREVIATION_SUBSEQUENCE" if record.get("abbreviation")
                            else "OFFICIAL_NAME_SUBSEQUENCE"}
    ranked = sorted(best.values(), key=lambda c: -c["score"])
    if not ranked or (len(ranked) > 1 and ranked[0]["score"] - ranked[1]["score"] < MARGIN):
        return None, ranked
    chosen = dict(ranked[0], candidate_count=len(ranked))
    return chosen, ranked
