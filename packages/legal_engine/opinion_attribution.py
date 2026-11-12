"""판결의 의견 귀속과 결론 방향 검사(v3 D3).

전원합의체 판결은 다수의견과 반대의견·별개의견·보충의견이 한 판결에 함께 실린다. 서면이 반대의견의 취지를
그 판결의 판시처럼 요약하면, 판결을 인용했지만 법리는 정반대가 된다. 판결 전체와의 유사도 하나로는 이것을
가려낼 수 없다(여러 의견이 같은 쟁점을 같은 낱말로 다루므로).

1. 의견 구간 분리: 판결 전문의 "대법관 …의 반대의견은 다음과 같다", 판결요지의 "[다수의견]",
   "[대법관 …의 반대의견]" 표지로 다수의견·반대의견·별개의견·보충의견 구간을 나눈다. 첫 표지 앞의 이유 부분은
   다수의견이다. '반대의견에 대한 보충의견'은 반대의견 쪽으로 센다.
2. 귀속: 서면의 요약 문장을 각 구간과 글자 2-gram 포함률(구간 안 가장 비슷한 창)로 비교한다. 반대의견이
   다수의견보다 뚜렷이 가까우면 MISATTRIBUTED_OPINION이다.
3. 결론 방향: 판시사항·판결요지의 "…인지 여부(적극)/(소극)/(원칙적 소극)" 쟁점 가운데 서면 문장과 같은 쟁점을
   고르고, 서면이 그 쟁점에 대해 판결과 반대 방향으로 단정하는지 부정 표현의 짝수·홀수로 비교한다.
4. 서술형 판결요지("사용자는 … 보호의무를 부담한다.")는 쟁점 표지가 없으므로, 서면 절과 거의 같은 말로 된 판결요지
   문장을 찾아(겹침 SUMMARY_MATCH 이상) 끝 서술어의 긍정·부정이 반대인지 본다(v4 P5 HOLDING_REVERSED).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

OPINION_KINDS = {"반대의견": "DISSENT", "별개의견": "CONCURRING", "보충의견": "SUPPLEMENTARY",
                 "반대보충의견": "DISSENT", "다수의견": "MAJORITY"}
FULL_MARKER_RE = re.compile(
    r"(?:\d+\s*\.\s*)?(?P<target>(?:다수의견|반대의견|별개의견)에\s*대한\s*)?(?:대법관\s*[^.\n]{1,80}?의\s*)?"
    r"(?P<kind>반대보충의견|반대의견|별개의견|보충의견)은\s*다음과\s*같다\s*\.?")
SUMMARY_MARKER_RE = re.compile(
    r"\[\s*(?P<target>(?:다수의견|반대의견|별개의견)에\s*대한\s*)?"
    r"(?:[^\[\]]{1,150}?에\s*관한\s*(?=대법관))?"          # 쟁점 한정 첫머리 '[피고인 …의 점에 관한 대법관 …](TK-153)
    r"(?:대법관\s*[^\]]{1,80}?의\s*)?"
    r"(?P<kind>다수의견|반대보충의견|반대의견|별개의견|보충의견)\s*\]")
# 전문의 번호 붙은 의견 머리말(TK-153). 공식 전문은 '다음과 같다' 없이 '8. …의 점에 관한 대법관 …의 반대의견'처럼
# 머리말만 두고 바로 본문을 잇는 꼴이 많다(<br/>은 공백으로 바뀌어 줄 끝으로 가릴 수 없다). 번호로 시작하고 의견 종류
# 바로 뒤가 공백(조사·쉼표 없음)이어야 머리말이다 — '…의 반대의견이 있는 외에는', '…의 별개의견, …'은 문장 속 언급이다.
HEADING_MARKER_RE = re.compile(
    r"(?<![\d.])\d{1,2}\s*\.\s+"
    r"(?:(?P<target>(?:다수의견|반대의견|별개의견)에\s*대한\s*)|[^.\[\]]{1,150}?(?:에\s*관한|에\s*대한)\s+(?=대법관))?"
    r"대법관\s*[^.\[\]]{1,80}?의\s*(?P<kind>반대보충의견|반대의견|별개의견|보충의견)(?=\s)")
TARGET_IN_MARKER_RE = re.compile(r"(?:다수의견|반대의견|별개의견)에\s*대한")
DROP_RE = re.compile(r"[\s\"'“”‘’.,·「」『』()\[\]<>《》~\-]")
REPORTING_TAIL_RE = re.compile(
    r"[\s\"'“”‘’]*(?:(?:(?:이?라|다|하)고\s*)?(?:판시|판단|설시)(?:하였|했|한)(?:다|습니다)"
    r"|(?:(?:이?라|다|하)고\s*)(?:보았|밝혔|하였|했)(?:다|습니다))\s*\.?\s*$")
CLAUSE_SPLIT_RE = re.compile(r"\s*[,，;]\s*|\s+(?:하며|이며)\s+")
FINAL_NEGATION_RE = re.compile(r"않|아니|없|못|불요|안\s*되|안\s*돼|안된")   # '…하여서는 안 된다'도 부정(TK-145)
FINAL_WINDOW = 7  # 절 끝 서술어(압축 글자 수)만 보고 긍정·부정을 가린다. 앞의 종속절 부정("거치지 않은 채")은 보지 않는다
NEGATION_RE = re.compile(r"않|아니|없|불요|못")
ISSUE_RE = re.compile(r"(?P<issue>[^\[\]]+?)\s*여부\s*\(\s*(?P<principled>원칙적\s*)?(?P<direction>적극|소극)\s*\)")

SUMMARY_MATCH = 0.6          # 서술형 판결요지 문장과 이만큼 겹치고, 끝 서술어가 같은 말이어야 같은 명제로 본다
SUMMARY_SENTENCE_RE = re.compile(r"(?<=[다음함])\s*\.\s*|\n+")
MISATTRIBUTION_MARGIN = 0.1   # 반대의견이 다수의견보다 이만큼 더 가까워야 한다
MISATTRIBUTION_FLOOR = 0.5    # 그리고 반대의견과 절반 이상 겹쳐야 한다
ISSUE_MATCH_FLOOR = 0.3       # 서면 절이 판시사항 쟁점과 이만큼 겹쳐야 같은 쟁점으로 본다
ISSUE_STRONG = 0.45           # 이 이상이면 확정(B), 그 아래는 사람 확인(C)
ISSUE_MARGIN = 0.08           # 두 번째로 가까운 쟁점보다 이만큼 앞서야 한다
STOP_STEMS = {"대하", "있는", "하는", "하고", "것이", "것은", "것으", "경우", "그", "이를", "으로", "에서", "여부",
              "등", "및", "수", "할", "한", "된다", "이다", "있다", "없다"}


def _compact(text: str) -> str:
    return DROP_RE.sub("", text or "")


def _bigrams(text: str) -> set:
    compact = _compact(text)
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def _claim_core(claim: str) -> str:
    """서면 문장에서 '…라고 판시하였다' 같은 전달 표현을 뗀 주장 부분."""
    core = re.sub(r"\s*\(\s*(?:(?:등\s*)?참조|등)?\s*\)\s*\.?\s*$", "", (claim or "").strip())
    return REPORTING_TAIL_RE.sub("", core).strip()


def _containment(claim: str, section: str) -> float:
    """claim의 2-gram이 section 안 가장 비슷한 창에 들어 있는 비율."""
    grams = _bigrams(claim)
    body = _compact(section)
    if not grams or not body:
        return 0.0
    width = max(len(_compact(claim)) * 2, 20)
    step = max(1, width // 4)
    best = 0.0
    for start in range(0, max(1, len(body) - width + 1), step):
        window = body[start:start + width]
        window_grams = {window[i:i + 2] for i in range(len(window) - 1)}
        best = max(best, len(grams & window_grams) / len(grams))
    return best


def _kind(match: re.Match) -> str:
    kind = OPINION_KINDS[match.group("kind").replace(" ", "")]
    target = (match.group("target") or "").replace(" ", "")
    if not target:  # '…의 반대의견에 대한 대법관 …의 보충의견'처럼 대상 의견이 이름 사이에 있는 머리말(TK-153)
        inner = TARGET_IN_MARKER_RE.search(match.group(0))
        target = inner.group(0).replace(" ", "") if inner else ""
    if kind == "SUPPLEMENTARY" and target.startswith("반대의견"):
        return "DISSENT"  # 반대의견에 대한 보충의견은 반대의견 쪽 논거다
    return kind


def _markers(text: str) -> List[re.Match]:
    """전문·판결요지의 의견 표지를 위치 순으로. split_opinions·opinion_ranges가 함께 쓴다."""
    return sorted(list(FULL_MARKER_RE.finditer(text)) + list(SUMMARY_MARKER_RE.finditer(text))
                  + list(HEADING_MARKER_RE.finditer(text)),
                  key=lambda m: m.start())


def split_opinions(text: str) -> Dict[str, Any]:
    """판결 전문·판결요지를 의견 구간으로 나눈다. {'MAJORITY': str, 'DISSENT': [...], ...}"""
    out: Dict[str, Any] = {"MAJORITY": "", "DISSENT": [], "CONCURRING": [], "SUPPLEMENTARY": []}
    text = text or ""
    markers = _markers(text)
    if not markers:
        out["MAJORITY"] = text
        return out
    majority = [text[:markers[0].start()]]
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = text[marker.end():end].strip()
        kind = _kind(marker)
        if kind == "MAJORITY":
            majority.append(body)
        else:
            out[kind].append(body)
    out["MAJORITY"] = " ".join(part.strip() for part in majority if part.strip())
    return out


def opinion_ranges(text: str) -> List[Tuple[int, int, str]]:
    """원문 위치 기준 의견 구간 [(시작, 끝, 종류)]. 표지가 없으면 전체가 다수의견이다(TK-135)."""
    text = text or ""
    markers = _markers(text)
    if not markers:
        return [(0, len(text), "MAJORITY")] if text else []
    ranges = [(0, markers[0].start(), "MAJORITY")] if markers[0].start() > 0 else []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        kind = _kind(marker)
        ranges.append((marker.start(), end, "MAJORITY" if kind == "SUPPLEMENTARY" else kind))
    return ranges


def quote_opinion(quote: str, text: str) -> Optional[str]:
    """인용 문구가 판결의 어느 의견에 있는지. 다수의견(다수의견 보충의견 포함)에 있으면 MAJORITY,
    반대의견·별개의견에만 있으면 그 종류, 어디에도 없거나 표지가 없으면 None(판단하지 않음)."""
    key = _compact(quote)
    if len(key) < 6:
        return None
    parts = split_opinions(text)
    if not (parts["DISSENT"] or parts["CONCURRING"]):
        return None
    if key in _compact(parts["MAJORITY"]) or any(key in _compact(s) for s in parts["SUPPLEMENTARY"]):
        return "MAJORITY"
    for kind in ("DISSENT", "CONCURRING"):
        if any(key in _compact(s) for s in parts[kind]):
            return kind
    return None


def attribute_claim(claim: str, full_text: str, summary: str = "") -> Dict[str, Any]:
    """서면의 판결 요약이 어느 의견에 가장 가까운지. verdict는 MISATTRIBUTED_OPINION 또는 None."""
    parts = [split_opinions(full_text), split_opinions(summary)]
    majority = " ".join(p["MAJORITY"] for p in parts)
    sections = {kind: [s for p in parts for s in p[kind]] for kind in ("DISSENT", "CONCURRING", "SUPPLEMENTARY")}
    core = _claim_core(claim)
    scores = {"MAJORITY": round(_containment(core, majority), 3)}
    for kind, texts in sections.items():
        if texts:
            scores[kind] = round(max(_containment(core, t) for t in texts), 3)
    closest = max(scores, key=scores.get)
    verdict = None
    if "DISSENT" in scores and closest == "DISSENT" and scores["DISSENT"] >= MISATTRIBUTION_FLOOR \
            and scores["DISSENT"] - scores["MAJORITY"] >= MISATTRIBUTION_MARGIN:
        verdict = "MISATTRIBUTED_OPINION"
    return {"verdict": verdict, "closest": closest, "scores": scores,
            "dissent_excerpt": (sections["DISSENT"][0][:300] if sections["DISSENT"] else ""),
            "majority_excerpt": majority[:300]}


def holding_issues(holding: str) -> List[Dict[str, Any]]:
    """판시사항·판결요지의 '…인지 여부(적극/소극)' 쟁점."""
    issues = []
    for chunk in re.split(r"\[\s*\d+\s*\]", holding or ""):
        for m in ISSUE_RE.finditer(chunk):
            issues.append({"issue": m.group("issue").strip(" ,/;"), "direction": m.group("direction"),
                           "principled": bool(m.group("principled"))})
    return issues


def _stems(text: str) -> set:
    """어절의 앞 두 글자(조사·어미를 뗀 어간 근사). 서로 다르게 풀어 쓴 같은 쟁점을 잇는다."""
    words = re.findall(r"[가-힣]+", text or "")
    return {w[:2] for w in words if w[:2] not in STOP_STEMS and len(w) >= 1} - {""}


def _overlap(a: str, b: str) -> float:
    ga, gb = _bigrams(a), _bigrams(b)
    bigram = len(ga & gb) / min(len(ga), len(gb)) if ga and gb else 0.0
    sa, sb = _stems(a), _stems(b)
    stem = len(sa & sb) / len(sa) if sa and sb else 0.0
    return max(bigram, stem)


def _clause_negated(text: str) -> bool:
    # Keep the predicate intact: trimming '는지' moves '없는 때' into the final window.
    compact = re.sub(r"지$", "", _compact(_claim_core(text)))
    return bool(FINAL_NEGATION_RE.search(compact[-FINAL_WINDOW:]))


def _clauses(core: str) -> List[str]:
    parts = [part.strip(" \"'“”‘’") for part in CLAUSE_SPLIT_RE.split(core or "")]
    return [part for part in parts if len(_compact(part)) >= 6]


def direction_conflict(claim: str, holding: str) -> Optional[Dict[str, Any]]:
    """서면이 판시사항 쟁점에 대해 판결과 반대 방향으로 단정하면 그 쟁점과 방향을, 아니면 None.

    주장을 절로 나누고, 절마다 가장 가까운 쟁점과 비교한다. 긍정·부정은 절 끝 서술어로만 가린다
    ("거치지 않은 채 … 징계사유가 된다"는 긍정). 쟁점 문장도 "…인지 여부" 앞 서술어로 가린다.
    """
    issues = holding_issues(holding)
    clauses = _clauses(_claim_core(claim))
    if not issues or not clauses:
        return None
    found = []
    for clause in clauses:
        ranked = sorted(issues, key=lambda i: _overlap(clause, i["issue"]), reverse=True)
        best = ranked[0]
        similarity = _overlap(clause, best["issue"])
        runner_up = _overlap(clause, ranked[1]["issue"]) if len(ranked) > 1 else 0.0
        if similarity < ISSUE_MATCH_FLOOR or similarity - runner_up < ISSUE_MARGIN:
            continue
        # 쟁점을 긍정하는 서면 절: 절과 쟁점의 끝 서술어 부정 여부가 같다.
        claim_affirms = _clause_negated(clause) == _clause_negated(best["issue"])
        if claim_affirms == (best["direction"] == "적극"):
            continue
        found.append({"issue": best["issue"], "holding_direction": best["direction"],
                      "principled": best["principled"], "claim_direction": "적극" if claim_affirms else "소극",
                      "issue_similarity": round(similarity, 3), "clause": clause,
                      "strong": similarity >= ISSUE_STRONG})
    if not found:
        return None
    return sorted(found, key=lambda f: (not f["strong"], f["principled"], -f["issue_similarity"]))[0]


# 끝 서술어 비교에서 건너뛸 부정·보조 용언(있다·없다·한다·된다 등)
AUXILIARY_RE = re.compile(r"^(?:않|아니|없|못|수|것|있|한다|하다|된다|된|되|필요)")


def _predicate(text: str) -> str:
    """끝 서술어 첫 음절의 초성·중성('부담하지 않는다' → '부담'의 ㅂ+ㅜ). 활용형(진다·지지)의 받침 차이는 무시한다."""
    words = [w for w in re.findall(r"[가-힣]+", text or "") if not AUXILIARY_RE.match(w)]
    if not words:
        return ""
    code = ord(words[-1][0]) - 0xAC00
    return f"{code // 588}-{(code % 588) // 28}"


def _positive(text: str) -> str:
    """부정 보조용언 어절을 뺀 글(겹침 계산용)."""
    return " ".join(w for w in re.findall(r"[가-힣]+", text or "") if not re.match(r"^(?:않|아니|없|못)", w))


def _predicate(text: str) -> str:
    """끝 서술어의 어간 두 글자('보호의무를 부담하지 않는다' → '부담'). 부정 보조용언은 건너뛴다."""
    words = [w for w in re.findall(r"[가-힣]+", text or "") if not AUXILIARY_RE.match(w)]
    return words[-1][:2] if words else ""


LEAD_RE = re.compile(r"^\s*(?:\d{1,3}\s*[.)]\s*)?(?:은|는|이|가|도)?\s+")


def summary_direction_conflict(claim: str, summary: str) -> Optional[Dict[str, Any]]:
    """서술형 판결요지와 같은 명제를 반대 방향(긍정↔부정)으로 요약했는지. 쟁점 표지('여부(적극)')가 있으면 쓰지 않는다.

    겹침은 부정 보조용언(않·아니·없·못)을 빼고 잰다. 방향은 끝 서술어로 따로 비교한다.
    """
    if not summary or ISSUE_RE.search(summary):
        return None
    sentences = [s.strip() for s in SUMMARY_SENTENCE_RE.split(summary) if len(_compact(s)) >= 8]
    found = []
    core = LEAD_RE.sub("", _claim_core(claim))  # 번호("16.")와 인용 뒤 조사("은")를 뗀다
    for clause in _clauses(core):
        ranked = sorted(sentences, key=lambda s: _overlap(clause, s), reverse=True)
        if not ranked:
            continue
        best = ranked[0]
        similarity = _overlap(_positive(clause), _positive(best))
        if (similarity < SUMMARY_MATCH or _predicate(clause) != _predicate(best) or not _predicate(clause)
                or _clause_negated(clause) == _clause_negated(best)):
            continue
        found.append({"issue": best, "holding_direction": "부정" if _clause_negated(best) else "긍정",
                      "claim_direction": "부정" if _clause_negated(clause) else "긍정", "principled": False,
                      "issue_similarity": round(similarity, 3), "clause": clause, "strong": True, "declarative": True})
    return max(found, key=lambda f: f["issue_similarity"]) if found else None


# ---------------------------------------------------------------------------
# LV-05: 판시 취지 및 명제 왜곡 탐지 (CIT-MIS) 결정적 3규칙 및 근거 문장 검증
# ---------------------------------------------------------------------------

CHANGED_PRECEDENT_RE = re.compile(
    r"(?:이와\s*달리|종전에)\s*(?P<old_holding>[^.。\n]{5,180}?)"
    r"(?:판시한|보았던|판단한)\s*(?:대법원\s*)?(?P<old_cases>(?:[^.。\n]|\.(?=\s*\d|\s*선고)){4,200}?)"
    r"(?:판결|결정)(?:\s*등)?은\s*이\s*(?:판결|결정)의\s*견해에\s*배치되는\s*범위\s*(?:내)?에서\s*"
    r"(?:이를\s*)?변경(?:하기로\s*한다|한다)"
)

REVERSED_LOWER_COURT_RE = re.compile(
    r"원심(?:은|이)\s*(?P<lower_holding>[^.。\n]{6,200}?)(?:라고|다고|으로)\s*(?:판단|판시)(?:하였다|하였으나|한\s*것)[^\n]{0,400}?"
    r"(?:이러한\s*원심의\s*판단에는|원심판결에는)[^.。\n]{0,120}?(?:법리를\s*오해|위법이\s*있)"
    r"|(?P<lower_holding_alt>[^.。\n]{6,180}?)(?:라고|다고)\s*판단한\s*원심판결에는[^.。\n]{0,100}?(?:법리를\s*오해|위법)"
)


_TAIL_CITATION_PAREN_RE = re.compile(r"\s*\([^()]{0,120}(?:판결|결정|선고|참조)[^()]{0,40}\)\s*[.。]?\s*$")


def _reported_core(claim: str) -> str:
    """끝의 괄호 인용 표시('(대법원 … 판결)')를 떼고 전달 표현('…다고 판단하였다')을 뗀 주장 부분."""
    return _claim_core(_TAIL_CITATION_PAREN_RE.sub("", claim or ""))


def extract_grounded_evidence_quote(claim: str, official_text: str) -> str:
    """공식 판결 원문(판결요지·전문)에서 서면 주장과 가장 어휘 겹침이 높은 근거 문장을 추출한다."""
    if not official_text or not claim:
        return ""
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[다함음])\s*\.\s*|\n+", official_text)
        if len(_compact(s)) >= 8
    ]
    if not sentences:
        return official_text[:250].strip()
    core = _claim_core(claim)
    ranked = sorted(sentences, key=lambda s: _overlap(core, s), reverse=True)
    return ranked[0][:300]


def detect_changed_precedent_distortion(
    claim: str,
    full_text: str,
    summary: str = "",
    cited_case_number: str = "",
) -> Optional[Dict[str, Any]]:
    """전원합의체 판결 등에서 폐기·변경된 종전 판례의 법리를 현행 판시처럼 인용했는지 검사한다."""
    combined = " ".join(part for part in (summary, full_text) if part)
    if not combined or not claim:
        return None
    # 종전 판례가 변경·폐기되었다는 사실을 정확히 기술한 서술은 왜곡이 아니다
    if re.search(r"(?:변경|폐기)(?:되|되었|된|하였|했)", claim):
        return None
    core = _reported_core(claim)
    for m in CHANGED_PRECEDENT_RE.finditer(combined):
        old_holding = (m.group("old_holding") or "").strip()
        old_cases = (m.group("old_cases") or "").strip()
        sentence = m.group(0).strip()
        # 1) 인용한 사건번호 자체가 변경 대상 판례 목록에 들어 있거나
        case_norm = re.sub(r"\s+", "", cited_case_number or "")
        in_old_cases = bool(case_norm and len(case_norm) >= 6 and case_norm in re.sub(r"\s+", "", old_cases))
        # 2) 서면 주장이 변경(폐기)된 종전 판시 구절과 높은 유사도를 보이는 경우
        sim = _overlap(_positive(core), _positive(old_holding)) if old_holding else 0.0
        # 새 판결(변경한 판결)의 다른 문장 — 바뀐 법리 자체 — 에 더 가까우면 새 판시를 정확히 인용한 것이다
        others = [x for x in re.split(r"(?<=[다함음])\s*\.\s*|\n+", combined.replace(sentence, " ")) if len(_compact(x)) >= 8]
        # 'A가 아니라 B' 꼴의 새 판시는 부정된 A 부분을 빼고 견준다
        others = [re.sub(r"(?<=[는은])\s+[^,.]{1,40}?(?:이|가)\s*아니라\s*", " ", x) for x in others]
        sim_new = max((_overlap(_positive(core), _positive(x)) for x in others), default=0.0)
        if in_old_cases or (sim >= 0.45 and sim > sim_new and _clause_negated(core) == _clause_negated(old_holding)):
            return {
                "verdict": "CHANGED_PRECEDENT",
                "old_holding": old_holding,
                "old_cases": old_cases,
                "similarity": round(sim, 3),
                "grounded_evidence_quote": sentence[:300],
            }
    return None


def _is_explicit_supreme_adoption(sentence: str) -> bool:
    """대법원이 해당 법리/판단을 자신의 판시로 인정·채택·판단했다고 명시한 문장인지 검사 (LV-05-R5)."""
    # 1) 대법원이 주어로 등장하고 채택/인정/판단 술어가 결합되어 있는지 확인
    m = re.search(
        r"대법원(?:은|이|도)?\b[^.\n]{0,120}?(?:인정|수긍|채택|받아들|선언|확인|보았|밝혔|판단하였|판시하였|판단했|판시했)(?:다|음|고|다고)",
        sentence,
    )
    if not m:
        if not re.search(
            r"대법원(?:은|이|도)?\b[^.\n]{0,120}?(?:인정|수긍|채택|받아들|판단|판시|선언|확인|보았|밝혔)",
            sentence,
        ):
            return False

    # 2) 그러나 대법원의 주절 술어가 원심판결/판단을 파기·배척·취소하는 행위인 경우는 채택이 아님
    #    예: '대법원은 [원심 판단]이라고 판단한 원심판결을 파기하였다'
    if re.search(
        r"(?:판단|판시|인정|인용|보)한\s*(?:원심판결|원심결정|하급심판결|원심)(?:을|은|에\s*대하여|에\s*대해)?\s*(?:파기|배척|취소)",
        sentence,
    ):
        return False
    if re.search(
        r"대법원(?:은|이|도)?\b[^.\n]{0,120}?(?:원심판결|원심결정|하급심판결|원심의\s*판단|원심)(?:을|은|에\s*대하여|에\s*대해)?\s*(?:파기|배척|취소)(?:하였|했|한|함|다|환송)",
        sentence,
    ):
        return False

    return True


def detect_reversed_remand_confusion(
    claim: str,
    full_text: str,
    summary: str = "",
) -> Optional[Dict[str, Any]]:
    """상고심(파기환송) 판결에서 배척된 원심의 판단을 대법원 판시인 것처럼 인용했는지 검사한다."""
    combined = " ".join(part for part in (summary, full_text) if part)
    if not combined or not claim:
        return None

    sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n+", claim) if s.strip()]
    adoption_sentences = [s for s in sentences if _is_explicit_supreme_adoption(s)]
    explicit_supreme_adoption = bool(adoption_sentences) or _is_explicit_supreme_adoption(claim)

    if not explicit_supreme_adoption:
        # 원심 판단이 파기·배척되었다는 사실을 정확히 기술한 서술은 왜곡(오인)이 아니다
        if re.search(r"(?:배척|파기|취소)(?:되|되었|되였|하였|했|한|된|었)|배척된\s*원심|파기된\s*원심", claim):
            return None
        # 사건 경과의 설명이거나 화자가 원심으로 한정되어 대법원 판시로 채택하지 않은 서술은 왜곡이 아니다
        if re.search(r"(?:사건\s*경과|경위의?\s*설명|원심(?:의\s*판단|판결)?을?\s*소개)", claim):
            return None
        if re.search(r"^\s*(?:원심|1심|제1심|하급심|원심\s*법원)(?:은|는|이)\b", claim):
            return None

    # 채택 문장이 분리된 경우 해당 문장 우선 검토, 아니면 전체 claim
    target_claim = " ".join(adoption_sentences) if adoption_sentences else claim
    core = _reported_core(target_claim)
    for m in REVERSED_LOWER_COURT_RE.finditer(combined):
        lower_holding = (m.group("lower_holding") or m.group("lower_holding_alt") or "").strip()
        if not lower_holding:
            continue
        sim = _overlap(_positive(core), _positive(lower_holding))
        if sim >= 0.45 and _clause_negated(core) == _clause_negated(lower_holding):
            return {
                "verdict": "REVERSED_REMAND_CONFUSION",
                "lower_holding": lower_holding,
                "similarity": round(sim, 3),
                "grounded_evidence_quote": m.group(0).strip()[:300],
            }
    return None

