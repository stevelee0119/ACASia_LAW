"""Citation & quote attribution detector (TK-240).

Distinguishes reported opponent/third-party assertions (especially when
subsequently rebutted by the author) from the author's own direct legal
claims using stem + ending decomposition, while guarding against evasion
where an author cites an opponent's claim and then adopts its conclusion.
"""
from __future__ import annotations

import re
from typing import Any, Dict

_SELF_SUBJECT_RE = re.compile(
    r"(?:본\s*(?:원고|피고|신청인|피신청인|소송대리인|대리인)|당\s*(?:소송대리인|대리인)|작성자)(?:\s*(?:은|는|이|가|의))?"
)

_OPPONENT_SUBJECT_RE = re.compile(
    r"(?<!본\s)(?<!당\s)(?:원고|피고|상대방|청구인|피청구인|신청인|피신청인|항소인|피항소인|"
    r"상고인|피상고인|채권자|채무자|피고인|제3자)(?:\s*측)?(?:\s*(?:은|는|이|가|의|측은|측의|측에서는))?"
)

# 어간 + 어미 분해:
# 1) ~하- 계열 어간(주장·항변·진술·원용·인용·언급·지적·해석·이해·판단·단정·평가·간주) + 모든 평서/연결/존대/진행 어미
# 2) 다투- 계열 어간(다툰다·다퉜다·다투고 있다·다투며·다투나·다툽니다 등)
# 3) 보- 계열 어간(본다·봅니다·보았다·보고 있다·보며·보나 등)
# 4) 명사형 서술(~라는/다는/한다는 입장·견해·취지·주장·해석·판단 입니다/이다/이었다 등)
_HA_STEMS = (
    r"(?:주장|항변|진술|원용|인용|언급|지적|해석|이해|판단|단정|평가|간주)"
)
_HA_ENDINGS = (
    r"(?:하(?:다|고(?:\s*있(?:다|습니다|으며|으나|지만|는데|고))?|며|여(?:서)?|였(?:다|습니다|으나|지만|으며|고)?|"
    r"나|지만|는데|는|던|니|ㄴ다|ㅂ니다)|"
    r"합(?:니다|니까)|"
    r"했(?:다|습니다|으나|지만|으며|고|다는|다고)?|"
    r"한다(?:고|는|면|니|는\s*(?:입장|취지|주장|견해|해석|판단))?)"
)
_DATU_STEM_ENDING = (
    r"다투(?:다|고(?:\s*있(?:다|습니다|으나|지만|는데|고))?|며|었(?:다|습니다|으나|지만|으며|고)?|나|지만|는데|ㄴ다|ㅂ니다)|"
    r"다퉜(?:다|습니다|으나|지만|으며|고)?|다툰다(?:고|는)?|다툽니다"
)
_BO_STEM_ENDING = (
    r"보(?:다|고(?:\s*있(?:다|습니다|으나|지만|는데|고))?|며|았(?:다|습니다|으나|지만|으며|고)?|나|지만|는데|ㄴ다|ㅂ니다)|"
    r"본다(?:고|는)?|봅니다"
)
_STANCE_NOUN_ENDING = (
    r"(?:입장|주장|취지|항변|견해|해석|판단)(?:이(?:다|고|며|라|었(?:다|습니다)|었으나)|입니다|이었(?:다|습니다)|였(?:다|습니다)|을\s*(?:취하|보이|내세우))"
)

_QUOTE_PARTICLE_RE = r"(?:라고|다고|라는|다는|취지로|것처럼|듯이|것으로)"

_REPORTED_SPEECH_RE = re.compile(
    rf"{_QUOTE_PARTICLE_RE}\s*(?:{_HA_STEMS}{_HA_ENDINGS}|{_DATU_STEM_ENDING}|{_BO_STEM_ENDING})|"
    rf"(?:라는|다는|한다는|본다는|다툰다는)\s*{_STANCE_NOUN_ENDING}"
)

_CONCESSIVE_REPORT_RE = re.compile(
    rf"(?:{_HA_STEMS}(?:하(?:나|지만|였으나|였지만|는데|고\s*있으나|고\s*있지만)|"
    r"했(?:으나|지만)|합니다만)|"
    r"다투(?:나|지만|었으나|었지만|고\s*있으나)|다퉜(?:으나|지만)|"
    r"보(?:나|지만|았으나|았지만|고\s*있으나))"
)

_REBUTTAL_MARKER_RE = re.compile(
    r"(?:그러나|하지만|다만|그렇지만|이와\s*달리|그럼에도|반면)[^.!?\n]{0,120}"
    r"(?:취지와\s*다르|취지에\s*반하|다릅니다|다르다|타당하지\s*않|이유\s*없|"
    r"받아들일\s*수\s*없|성립하지\s*않|적용되지\s*않|맞지\s*않|잘못|허위|왜곡|근거\s*없|부당)"
)

_SELF_ADOPTION_RE = re.compile(
    r"(?:따라서|그러므로|결국|이에\s*따라|마찬가지로|당사도|원고도|피고도|"
    r"본\s*(?:원고|피고|소송대리인)(?:도| 역시)|같은\s*취지에서|그\s*주장과\s*같이)"
    r"[^.!?\n]{0,100}"
    r"(?:타당|정당|인정|적용|성립|맞|동의|따라야|인용되어야|책임이\s*있)"
)


def assess_reported_quote_attribution(
    context: str,
    *,
    raw_text: str = "",
    quoted_text: str = "",
) -> Dict[str, Any]:
    """Assess whether a citation/quote in `context` is an opponent/third-party reported assertion."""
    text = (context or "").strip()
    if not text:
        return {
            "is_reported_opponent_quote": False,
            "has_opponent_marker": False,
            "has_reported_verb": False,
            "has_rebuttal": False,
            "adopted_by_author": False,
        }

    anchor = (quoted_text or raw_text or "").strip()
    window = text
    if anchor and len(text) > 500:
        idx = text.find(anchor[:40])
        if idx != -1:
            start = max(0, idx - 220)
            end = min(len(text), idx + len(anchor) + 260)
            window = text[start:end]

    has_self_subject = bool(_SELF_SUBJECT_RE.search(window))
    has_opponent = bool(_OPPONENT_SUBJECT_RE.search(window)) and not (
        has_self_subject and not re.search(r"(?:피고|상대방|청구인|피청구인|제3자)(?:\s*측)?(?:은|는|이|가)", window)
    )
    has_reported_verb = bool(_REPORTED_SPEECH_RE.search(window))
    has_concessive = bool(_CONCESSIVE_REPORT_RE.search(window))
    has_rebuttal = bool(_REBUTTAL_MARKER_RE.search(window)) or has_concessive
    adopted_by_author = bool(_SELF_ADOPTION_RE.search(window)) and not has_rebuttal

    is_reported = bool(has_opponent and (has_reported_verb or has_concessive) and not adopted_by_author)
    return {
        "is_reported_opponent_quote": is_reported,
        "has_opponent_marker": has_opponent,
        "has_reported_verb": has_reported_verb or has_concessive,
        "has_rebuttal": has_rebuttal,
        "adopted_by_author": adopted_by_author,
    }
