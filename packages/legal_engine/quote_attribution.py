"""Citation & quote attribution detector (TK-240).

Distinguishes reported opponent/third-party assertions (especially when
subsequently rebutted by the author) from the author's own direct legal
claims, while guarding against evasion where an author cites an opponent's
claim and then adopts its conclusion as their own.
"""
from __future__ import annotations

import re
from typing import Any, Dict

_OPPONENT_SUBJECT_RE = re.compile(
    r"(?:원고|피고|상대방|청구인|피청구인|신청인|피신청인|항소인|피항소인|"
    r"상고인|피상고인|채권자|채무자|피고인|제3자)(?:\s*측)?(?:\s*(?:은|는|이|가|의|측은|측의))?"
)

_REPORTED_SPEECH_RE = re.compile(
    r"(?:라고|다고|라는|다는|취지로|것처럼|듯이)\s*"
    r"(?:주장하|주장했|주장하였|주장하며|주장하고|주장하나|주장하지만|주장한다|"
    r"항변하|항변했|항변하였|항변한다|다투|진술하|진술했|원용하|내세우|언급하|인용하)|"
    r"(?:라는|다는)\s*(?:입장|주장|취지|항변|견해)(?:이|입니|이었|였|을)"
)

_CONCESSIVE_REPORT_RE = re.compile(
    r"(?:주장|항변|진술|인용)(?:하나|하지만|하였으나|하였지만|하는데|하고\s*있으나|합니다만)"
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
    """Assess whether a citation/quote in `context` is an opponent's reported assertion."""
    text = (context or "").strip()
    if not text:
        return {
            "is_reported_opponent_quote": False,
            "has_opponent_marker": False,
            "has_reported_verb": False,
            "has_rebuttal": False,
            "adopted_by_author": False,
        }

    # Narrow window around the citation/quote if context is long
    anchor = (quoted_text or raw_text or "").strip()
    window = text
    if anchor and len(text) > 500:
        idx = text.find(anchor[:40])
        if idx != -1:
            start = max(0, idx - 220)
            end = min(len(text), idx + len(anchor) + 260)
            window = text[start:end]

    has_opponent = bool(_OPPONENT_SUBJECT_RE.search(window))
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
