"""법리 주장 검토: 주장 유형 분류 → 근거 조회 → 판단(추가지시 G4).

문구 하나하나를 맞히는 규칙이 아니라, 문장을 먼저 '주장 유형'으로 나누고 유형마다 근거를 찾아 판단한다.

| 유형 | 분류 기준(문장 구조) | 근거 조회 | 판단 |
|---|---|---|---|
| 위헌 주장 | '위헌'·'헌법에 위반' + 대상 조항 | 대상이 헌법 조항이면 심판 대상 규정(헌법재판소법 제41조·제68조), 법률 조항이면 헌재 결정 이력 | 헌법 조항 자체 → 형식상 불가. 단정적 위헌 주장인데 합헌 결정 → 모순, 각하 → 사람 확인. 이력 조회 불가 → 확인 불가 |
| 전칭 일반화 | '언제나'·'어떠한 경우에도'·'예외 없이'·'모든 경우' + 법적 효과 서술 | 같은·앞 문장의 근거 인용 | 근거 인용이 없으면 UNSUPPORTED_GENERALIZATION |
| 법률상 근거 없는 청구 유형 | 청구하는 구제 수단(배수 배상, 비형사 절차의 형벌, 사죄광고) | 구제 수단의 일반 근거 조문 | 개별 법률 근거를 들지 않으면 사람 확인 |
| 조문 요건 불일치 | '제N조에 따라/의하여' + 적용 대상 | 조회한 조문 원문의 주체 | 공적 주체 조문을 사인에게(또는 반대로) 적용하면 확인 필요 |
| 출처 불명 기준 | '기준표'·'지침'·'가이드라인' 등에 기대는 서술 | 발행 기관·번호·일자 | 출처를 특정할 수 없으면 확인 필요 |
| 소송요건 배제 | 제소기간·시효·전심절차·원고적격 + '적용되지 않는다'류 | 소송요건 조문 | 예외 조문·판례 없이 배제하면 확인 필요 |

판정은 서면의 문장과 근거 원문만으로 하며 사건의 결론(인용·기각)을 내리지 않는다. 근거 원문은
config/legal_rules/rules.json의 공식 원문(sources)을 쓰고, 없는 근거는 이름만 싣고 원문 미수록을 밝힌다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text, sentence_bounds

from .legal_rules import load_rules
from .polarity import ASSERTED, NEGATED, polarity
from .statutory_exclusion import exclusion_clauses

ENGINE_NAME = "legal_engine.claim_review"

# --- 문장 구성 요소 ----------------------------------------------------------------
LAW_NAME = r"[가-힣]+(?:\s[가-힣]+){0,4}?(?:법률|법|헌법|령|규칙)"
PROVISION_RE = re.compile(
    rf"(?P<law>{LAW_NAME})\s*제\s*(?P<art>\d+)\s*조(?:\s*의\s*(?P<sub>\d+))?(?:\s*제\s*(?P<para>\d+)\s*항)?")
BARE_PROVISION_RE = re.compile(r"제\s*\d+\s*조")
# 판례 인용은 사건번호나 '선고'가 있어야 한다. '판결'이라는 낱말만으로는 근거 인용으로 보지 않는다.
CASE_CITE_RE = re.compile(r"(?:19|20)?\d{2}\s*(?:헌[가-힣]|[가-힣]{1,3})\s*\d{2,6}|선고")
DIGIT_RE = re.compile(r"\d")
CITATION_ANY_RE = re.compile(rf"{PROVISION_RE.pattern}|{CASE_CITE_RE.pattern}|제\s*\d+\s*조")
CONSTITUTION_NAMES = {"헌법", "대한민국헌법", "대한민국 헌법"}

UNCON_RE = re.compile(r"위헌|헌법에\s*(?:위반|위배|반하|반한다|어긋)|헌법\s*위반")
UNCON_NEGATION_RE = re.compile(r"위헌(?:이|은|으로)?\s*(?:아니|라고\s*(?:할|볼)\s*수\s*없)|합헌|위헌\s*여부|위헌법률\s*심판\s*제청|"
                               r"위헌\s*(?:소지|의심|가능성)")
CERTAIN_RE = re.compile(r"명백(?:히|하게|한|하다)|분명(?:히|하게|하다)|당연히|의심의\s*여지(?:가|도)?\s*없|누가\s*보아도|자명")
STANDARD_OF_REVIEW_RE = re.compile(r"\s*(?:에|과|와)\s*(?:위반|위배|반하|반한|어긋|저촉)")
CONSTITUTION_ITSELF_RE = re.compile(r"헌법\s*(?:조항|규정|조문)\s*(?:그\s*)?자체")
# 헌법 조항 바로 뒤에 주어 조사와 '위헌'이 오면 그 조항 자체를 위헌이라고 한 것이다('헌법 제10조 자체가 위헌').
SUBJECT_UNCON_RE = re.compile(r"\s*(?:\(\s*[^)]{0,20}\))?\s*(?:자체|그\s*자체)?\s*(?:가|이|은|는)\s*[^.,]{0,80}?위헌")

QUANTIFIER_RE = re.compile(
    r"어떠한\s*경우(?:에도|라도|에라도)|어떤\s*경우(?:에도|라도)|언제나|항상|예외\s*(?:없이|없는|를\s*불문)|"
    r"모든\s*경우(?:에|에도)?|무조건|절대(?:로|적으로)?\s+(?=[가-힣])|예외가\s*(?:없다|있을\s*수\s*없)")
LEGAL_EFFECT_RE = re.compile(
    r"무효|위법|위헌|취소(?:되어야|하여야|사유|된다)|책임(?:을|이)\s*(?:진다|지게|있|부담)|배상(?:하여야|할\s*책임|책임)|"
    r"인정(?:된다|되어야|되지\s*않|될\s*수\s*없)|허용(?:된다|되지|될\s*수)|금지(?:된다|되)|할\s*수\s*없|하여야\s*한다|해야\s*한다|"
    r"적용(?:된다|되지)|성립(?:한다|하지|된다)|소멸(?:한다|하지|된다)|효력(?:이|을)|의무(?:가|를)|권리(?:가|를)|"
    r"정당화(?:된다|될)|면책(?:된다|되지)|징계(?:할|하여야|사유)|권리\s*남용|해당(?:한다|합니다|하지|된다)|"
    r"(?:될|받을|볼|감액될|거절될|취소될|배제될)\s*수\s*(?:없|있)|배상(?:하여야|해야)|지급(?:하여야|할\s*의무)|"
    # 법원의 판단 경향을 전칭으로 말하는 서술('항상 원고 승소 판결을 해 왔다')
    r"(?:판결|판단|결정|인용|기각|취소)(?:을|를)?\s*(?:해|하여)\s*왔|승소|패소")
QUALIFIER_RE = re.compile(r"특별한\s*사정이\s*없는\s*한|원칙적으로|대체로|일반적으로\s*(?:는|은)?\s*(?:[가-힣]+\s*){0,2}한다고\s*보|"
                          r"경우가\s*많|할\s*수\s*있다")

STANDARD_MARKER_RE = re.compile(r"표|기준|가이드라인|지침|매뉴얼|관행|해설서|안내서|편람|핸드북|요령")
STANDARD_NOUN_RE = re.compile(
    r"(?:[가-힣]{0,12}\s?)(?:산정\s*기준표|판정\s*기준표|기준표|산정\s*기준|산정표|요율표|가이드라인|지침|매뉴얼|업무\s*기준|내부\s*기준|실무\s*기준|"
    r"업계\s*(?:기준|관행)|표준\s*[가-힣]{0,6}표|판정\s*기준|해설서|안내서|편람|핸드북|업무\s*(?:처리\s*)?요령|실무\s*요령)")
RELIANCE_RE = re.compile(r"\s*(?:에\s*따르면|에\s*의하면|에\s*의하여|에\s*따라|에\s*근거|을\s*적용|를\s*적용|상\s)")
ISSUER_RE = re.compile(
    r"[가-힣]+(?:부|처|청|위원회|공단|공사|협회|학회|법원|재판소|연구원|진흥원|관리원|평가원|보험공단)\s*(?:의|가|이|에서|이\s*정한|가\s*정한)?\s|"
    r"고시|훈령|예규|규정\s*제|제\s*\d+\s*호|[\(（]\s*(?:19|20)\d{2}|(?:19|20)\d{2}\s*\.\s*\d{1,2}\s*\.|https?://|별표|시행령|시행규칙")

REQUIREMENT_TERMS = {
    "제소기간": ("행정소송법 제20조", r"제소\s*기간|출소\s*기간"),
    "소멸시효": ("민법 제162조", r"소멸\s*시효|시효\s*(?:기간|완성)"),
    "전심절차": ("행정소송법 제18조", r"전심\s*절차|전치\s*(?:절차|주의)|행정\s*심판\s*(?:전치|절차)|소청\s*(?:심사|절차)|"
                                  r"항고\s*(?:절차|제기|를\s*거치)"),
    "원고적격": ("행정소송법 제12조", r"원고\s*적격|당사자\s*적격|소의\s*이익|법률상\s*이익"),
}
EXCLUSION_RE = re.compile(
    r"적용되지\s*않|적용(?:이|을)\s*(?:없|받지\s*않)|무관|배제(?:된다|되어야)|필요(?:가|치)?\s*없|필요하지\s*않|불요|거치지\s*않아도|"
    r"문제(?:가\s*)?되지\s*않|문제가\s*없|제한을\s*받지\s*않|고려할\s*필요(?:가)?\s*없|따질\s*필요(?:가)?\s*없|"
    r"지나도\s*(?:된다|무방)|상관(?:이)?\s*없|의미가\s*없")
EXCEPTION_BASIS_RE = re.compile(r"정당한\s*사유|무효\s*(?:등\s*)?확인|단서|제\s*\d+\s*조\s*제\s*\d+\s*항|특별\s*규정|"
                                r"법률에\s*특별한|예외\s*규정")

MULTIPLE = r"(?:\d+|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*배"
PUNITIVE_RE = re.compile(rf"징벌적\s*(?:손해)?\s*배상|(?:손해액|손해|배상액|재산상\s*손해)의?\s*{MULTIPLE}(?:에\s*해당하는|의|를|을)?|"
                         rf"{MULTIPLE}\s*(?:의\s*)?(?:손해)?\s*배상")
CRIMINAL_RELIEF_RE = re.compile(
    r"(?:특정경제범죄법?상?\s*)?(?:징역|금고|벌금|형사\s*처벌|형벌|처벌)"
    r"[^.\n]{0,50}?"
    r"(?:병과하여|에\s*처한다|에\s*처하라|선고하여\s*(?:주시기|주실|주십시오|바랍니다)|선고하라|선고한다|처벌하라|하라|형벌을|징역형을|징역\s*\d+년)"
)
# 민사·국가배상 소송에서 법원이 명할 수 없는 인사·징계 조치(파면·해임·징계 등) 및 행정청 감독권 발동 청구
PERSONNEL_RELIEF_RE = re.compile(
    r"(?:파면|해임|징계|감봉|정직|강등|직위\s*해제|전보|특별근로감독\s*(?:등\s*)?지정)"
    r"[^.\n]{0,80}?"
    r"(?:하라|시켜라|에\s*처하라|할\s*것을\s*명한다|지정을\s*명한다|해임명령을|해임을\s*명한다|선고하여\s*(?:주시기|주실|주십시오|바랍니다)|해임\s*및)"
)
ADMIN_SANCTION_RELIEF_RE = re.compile(
    r"(?:의사면허\s*(?:취소|정지)|면허\s*(?:취소|정지)|영업정지|업무정지)"
    r"[^.\n]{0,80}?"
    r"(?:명한다|선고하여\s*(?:주시기|주실|주십시오|바랍니다)|선고하라|선고한다|처분을\s*명한다|취소처분을\s*명한다|처분을\s*선고)"
)
APOLOGY_RELIEF_RE = re.compile(r"사죄\s*광고|사과문을?\s*(?:게재|공표|낭독)하라|사죄문을?\s*(?:게재|공표)하라")
RELIEF_HEAD_RE = re.compile(r"청\s*구\s*취\s*지")
GROUNDS_HEAD_RE = re.compile(r"청\s*구\s*원\s*인")
# 형사 공소장 등 검사 형사소송 서면 판별 (의료행위상 진료·CT '검사' 등 의학 용어 오탐 방지)
CRIMINAL_DOC_RE = re.compile(
    r"(?:공소장|공소사실|피고인\s*(?:은|는|이|가)|담당\s*검사|"
    r"(?<![CT\s혈액조직추가정밀방사선내시경초음파의학임상])검사\s+[가-힣○]{2,3}(?!\s*(?:를|을|가|이|도|만|에|에서|결과|수치|시행|진행|의뢰|처방|장비|기기|실|장|료))|"
    r"구형|형사\s*공판)"
)

APPLY_RE = re.compile(r"(?:에\s*따라|에\s*의하여|에\s*의해|에\s*근거하여|이\s*적용되어|을\s*적용하면|를\s*적용하면|에서\s*정한)")
PUBLIC_ACTOR_RE = re.compile(r"국가|지방\s*자치\s*단체|공무원|행정청|공공\s*(?:단체|기관)|장관|처장|청장|시장|군수|구청장|도지사|교육감|사단장|참모총장")
PRIVATE_ACTOR_RE = re.compile(r"주식\s*회사|㈜|\(주\)|유한\s*회사|회사|법인|사업자|개인|사인|임대인|임차인|매도인|매수인|사용자|근로자")


@dataclass
class ClaimMatch:
    claim_type: str
    sentence: str
    start: int
    judgment: str
    grade: str
    status: str
    basis: List[Dict[str, Any]] = field(default_factory=list)
    detail: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


HistoryLookup = Callable[[str, str], Dict[str, Any]]


def _source(name: str) -> Dict[str, Any]:
    sources = load_rules().get("sources") or {}
    entry = sources.get(name) or (sources.get(f"대한민국{name}") if name.startswith("헌법 ") else None)
    if entry:
        return {"name": name, **entry}
    return {"name": name, "text": "", "note": "공식 원문을 규칙표에 수록하지 않았다(이름만 표시)"}


# 법령명 앞에서 멈출 어절 끝(조사·관형형 어미). '의'는 법령명 안에 흔하므로('공공기관의 정보공개에 관한 법률')
# 멈추지 않고, '에'는 '…에 관한 법률'처럼 이름 안에 있을 때만 이어 붙인다.
PARTICLE_END_RE = re.compile(r"(?:은|는|이|가|을|를|에|도|로|와|과|께서|에서|에게|인|된|한|던|적인)$")


def law_name(raw: str) -> str:
    """조항 앞의 어절 가운데 법령명만 남긴다. '피고 회사는 가상공공배상법' → '가상공공배상법'.

    법령명에는 띄어쓰기가 있을 수 있어('제조물 책임법') 끝 어절부터 거꾸로 붙이되, 조사로 끝나는 어절을
    만나면 멈춘다.
    """
    tokens = raw.split()
    kept: List[str] = []
    for token in reversed(tokens):
        # '…에 관한 법률'·'…에 따른 법률'처럼 법령명 안의 조사는 남긴다.
        inside_name = bool(kept) and ((kept[0] in ("관한", "대한", "따른", "의한") and token.endswith("에"))
                                      or token in ("관한", "대한", "따른", "의한"))
        if kept and PARTICLE_END_RE.search(token) and not inside_name:
            break
        kept.insert(0, token)
    return " ".join(kept)


def _provisions(sentence: str):
    return list(PROVISION_RE.finditer(sentence))


def _is_constitution(law: str) -> bool:
    # 앞 어절이 섞여도('…아니라 헌법') 끝 어절이 '헌법'이면 헌법 조항이다.
    tokens = law_name(law).split()
    return bool(tokens) and (tokens[-1] in CONSTITUTION_NAMES or " ".join(tokens[-2:]) in CONSTITUTION_NAMES)


def _has_citation(*texts: str) -> bool:
    # Every numeric alternative requires a decimal digit; the only digit-free
    # alternative is 선고.  Avoid retrying the long provision-name expression
    # at every word of a sentence that cannot contain any citation.
    return any(t and ("선고" in t or DIGIT_RE.search(t))
               and CITATION_ANY_RE.search(t) for t in texts)


# 앞 문장의 인용은 이 문장이 앞 문장을 이어받을 때만 근거로 본다('따라서', '이에 따라', '위 판결은' 등).
CONTINUATION_RE = re.compile(r"^\s*(?:\d+\.\s*)?(?:따라서|그러므로|그렇다면|이에\s*따라|이러한|이런|그러한|그런|이는|이와\s*같이|위\s*(?:판결|결정|조항|규정|판례)|"
                             r"같은\s*(?:조|법|취지)|동\s*(?:조|법|판결)|즉|결국)")


def _linked_previous(sentence: str, previous: str) -> str:
    return previous if CONTINUATION_RE.match(sentence) else ""


# --- 유형별 판단 ----------------------------------------------------------------------
def _unconstitutionality(sentence: str, lookup: Optional[HistoryLookup]) -> Optional[ClaimMatch]:
    if not UNCON_RE.search(sentence) or UNCON_NEGATION_RE.search(sentence):
        return None
    provisions = _provisions(sentence)
    targets = [m for m in provisions if not STANDARD_OF_REVIEW_RE.match(sentence, m.end())]
    itself = CONSTITUTION_ITSELF_RE.search(sentence)
    subject_const = [m for m in provisions if _is_constitution(m.group("law")) and SUBJECT_UNCON_RE.match(sentence, m.end())]
    if subject_const:
        targets = subject_const
    # A constitutional citation can be the standard of review for a contract,
    # not the provision being challenged. Require an explicit grammatical target.
    if subject_const or (itself and SUBJECT_UNCON_RE.match(sentence, itself.end())):
        if not itself and not targets:
            return None
        label = targets[0].group(0) if targets else "헌법 조항"
        return ClaimMatch(
            "UNCONSTITUTIONALITY", sentence, 0, "헌법 조항 자체를 위헌이라고 주장(심판 대상 아님)", "B", "CONTRADICTED",
            [_source("대한민국헌법 제111조"), _source("헌법재판소법 제41조"), _source("헌법재판소법 제68조")],
            f"'{label}'은 헌법 규정이다. 헌법재판소가 관장하는 위헌 심판은 '법률의 위헌여부 심판'(대한민국헌법 제111조 "
            "제1항 제1호)과 '법률이 정하는 헌법소원'(같은 항 제5호)이므로, 헌법 조항 자체는 위헌 여부 심판의 대상이 "
            "아니다.", {"target": label})
    statute_targets = [m for m in targets if not _is_constitution(m.group("law"))]
    if not statute_targets or not CERTAIN_RE.search(sentence):
        return None
    target = statute_targets[0]
    law, article = law_name(target.group("law")), target.group("art") + (
        f"의{target.group('sub')}" if target.group("sub") else "")
    label = f"{law} 제{article}조"
    history = lookup(law, article) if lookup else {"status": "UNAVAILABLE", "message": "헌재 결정 이력 조회기가 없다"}
    decisions = history.get("decisions") or []
    if history.get("status") != "READY":
        return ClaimMatch(
            "UNCONSTITUTIONALITY", sentence, 0, "단정적 위헌 주장(헌재 결정 이력 확인 불가)", "C", "UNVERIFIED", [],
            f"{label}이 명백히 위헌이라고 단정했다. 이 조항에 대한 헌법재판소 결정 이력을 확인하지 못했다"
            f"({history.get('message') or '조회 불가'}). 합헌 결정이 있는지 사람이 확인해야 한다.",
            {"target": label, "history": history})
    uncon = [d for d in decisions if d.get("result") in ("위헌", "헌법불합치", "한정위헌")]
    upheld = [d for d in decisions if d.get("result") in ("합헌", "한정합헌")]
    dismissed = [d for d in decisions if d.get("result") == "각하"]
    if uncon or not (upheld or dismissed):
        return None
    chosen = sorted(upheld or dismissed, key=lambda d: str(d.get("decision_date") or ""))[-1]
    cite = f"헌법재판소 {chosen.get('decision_date', '')} {chosen.get('case_number', '')} {chosen.get('result')} 결정".strip()
    basis = [{"name": cite, "text": chosen.get("summary") or chosen.get("case_name") or "", "url": chosen.get("url", "")}]
    if upheld:
        return ClaimMatch(
            "UNCONSTITUTIONALITY", sentence, 0, "합헌 결정이 있는 조항을 명백히 위헌이라고 주장", "B", "CONTRADICTED", basis,
            f"{label}에 대하여 {cite}이 있다. 이 결정을 다루지 않고 명백히 위헌이라고 단정했다.",
            {"target": label, "decisions": decisions})
    return ClaimMatch(
        "UNCONSTITUTIONALITY", sentence, 0, "각하 결정이 있는 조항을 명백히 위헌이라고 주장(사람 확인)", "C", "SUSPICIOUS", basis,
        f"{label}에 대하여 {cite}이 있다. 각하는 본안 판단이 아니므로 합헌을 뜻하지 않지만, 단정의 근거를 확인해야 한다.",
        {"target": label, "decisions": decisions})


def _generalization(sentence: str, previous: str) -> Optional[ClaimMatch]:
    quantifier = QUANTIFIER_RE.search(sentence)
    if not quantifier or not LEGAL_EFFECT_RE.search(sentence[quantifier.start():]):
        return None
    if QUALIFIER_RE.search(sentence) or _has_citation(sentence, _linked_previous(sentence, previous)):
        return None
    return ClaimMatch(
        "UNSUPPORTED_GENERALIZATION", sentence, 0, "근거 없는 전칭 법리 명제", "B", "SUSPICIOUS", [],
        f"'{quantifier.group(0).strip()}'로 예외를 모두 배제하는 법리 명제인데, 이 문장과 앞 문장에 근거 조문·판례가 없다. "
        "전칭 명제는 그 범위를 뒷받침하는 근거가 있어야 한다.", {"quantifier": quantifier.group(0).strip()})


def _remedy(sentence: str, in_relief: bool, criminal_doc: bool) -> Optional[ClaimMatch]:
    punitive = PUNITIVE_RE.search(sentence)
    if punitive and not _has_citation(sentence):
        return ClaimMatch(
            "NO_BASIS_REMEDY", sentence, 0, "개별 법률 근거 없이 배수·징벌적 배상 청구", "B", "SUSPICIOUS",
            [_source("민법 제393조"), _source("민법 제763조")],
            "민법상 손해배상은 통상의 손해(민법 제393조, 불법행위는 제763조로 준용)를 한도로 한다. 손해액의 배수를 "
            "배상하게 하려면 그렇게 정한 개별 법률 조항이 있어야 하는데, 서면은 근거 조항을 들지 않았다.",
            {"remedy": punitive.group(0)})
    if not criminal_doc and CRIMINAL_RELIEF_RE.search(sentence):
        return ClaimMatch(
            "NO_BASIS_REMEDY", sentence, 0, "형사절차가 아닌 민사소송에서 형벌(징역형) 선고 청구 (소송형태·관할 결함)", "A", "CONTRADICTED",
            [_source("형사소송법 제246조"), _source("민사소송법 제248조")],
            "형벌은 검사가 공소를 제기한 형사절차에서만 과할 수 있다(형사소송법 제246조 국가기소편의주의). "
            "민사소송 절차에서 피고에게 징역형 등 형벌을 병과하여 선고해 달라는 청구는 민사법원의 권한 범위를 벗어난 "
            "중대한 소송형태적 결함(JURISDICTIONAL_DEFECT)으로 각하/배척 대상이다.",
            {"remedy": "형사처벌", "defect_type": "JURISDICTIONAL_DEFECT"})
    if (in_relief or not criminal_doc) and PERSONNEL_RELIEF_RE.search(sentence):
        return ClaimMatch(
            "NO_BASIS_REMEDY", sentence, 0, "법원이 명할 수 없는 대표이사 해임 및 행정청 감독권 발동 청구 (소송형태·관할 결함)", "A", "CONTRADICTED",
            [_source("상법 제385조"), _source("근로기준법 제101조"), _source("민법 제394조")],
            "대표이사 해임은 상법상 주주총회 고유권한(상법 제385조)이며, 특별근로감독 지정은 행정관청의 고유 권한(근로기준법 제101조)이다. "
            "손해배상 등 민사소송의 청구취지나 판결로 피고 회사에게 대표이사 해임이나 행정청의 감독권 발동을 명할 수 없으므로, "
            "중대한 소송형태적 결함(JURISDICTIONAL_DEFECT)으로 각하/배척 대상이다.",
            {"remedy": "인사·감독명령", "defect_type": "JURISDICTIONAL_DEFECT"})
    if (in_relief or not criminal_doc) and ADMIN_SANCTION_RELIEF_RE.search(sentence):
        return ClaimMatch(
            "NO_BASIS_REMEDY", sentence, 0, "민사소송에서 행정청 고유권한인 의사면허취소 및 영업정지 처분 청구 (소송형태·관할 결함)", "A", "CONTRADICTED",
            [_source("의료법 제65조"), _source("의료법 제66조"), _source("민사소송법 제248조")],
            "의사면허 취소(의료법 제65조)나 의료기관 영업정지·업무정지(의료법 제66조) 처분은 보건복지부장관 또는 관할 행정관청의 "
            "고유 행정권한이다. 민사소송의 청구취지나 판결로 이를 직접 명하거나 처분할 수 없으므로, 민사재판권의 한계를 벗어난 "
            "중대한 소송형태적 결함(JURISDICTIONAL_DEFECT, UNFOUNDED_CLAIM)으로 각하/배척 대상이다.",
            {"remedy": "행정처분·영업정지·면허취소", "defect_type": "JURISDICTIONAL_DEFECT"})
    if in_relief and APOLOGY_RELIEF_RE.search(sentence):
        return ClaimMatch(
            "NO_BASIS_REMEDY", sentence, 0, "사죄광고·사과문 게재 강제 청구(사람 확인)", "C", "SUSPICIOUS",
            [_source("민법 제764조"), _source("헌법재판소 1991. 4. 1. 89헌마160 결정")],
            "명예훼손의 구제로 '명예회복에 적당한 처분'(민법 제764조)을 구할 수 있으나, 헌법재판소는 이 조항이 "
            "사죄광고를 포함하는 취지라면 헌법에 위반된다고 결정했다(헌법재판소 1991. 4. 1. 89헌마160). 청구 형태가 "
            "허용되는지 사람이 확인해야 한다.",
            {"remedy": "사죄광고"})
    return None


def _unsourced_standard(sentence: str) -> Optional[ClaimMatch]:
    # Every existing alternative contains one of these terminal markers.
    if not STANDARD_MARKER_RE.search(sentence):
        return None
    for noun in STANDARD_NOUN_RE.finditer(sentence):
        if not RELIANCE_RE.match(sentence, noun.end()):
            continue
        if ISSUER_RE.search(sentence) or _has_citation(sentence):
            return None
        name = noun.group(0).strip()
        return ClaimMatch(
            "UNSOURCED_STANDARD", sentence, 0, "출처를 특정할 수 없는 기준 인용", "B", "SUSPICIOUS", [],
            f"'{name}'에 기대어 판단하지만 발행 기관·문서 번호·일자가 없어 원문을 찾아 대조할 수 없다. 기준의 출처를 "
            "특정해야 한다.", {"standard": name})
    return None


def _requirement_exclusion(sentence: str, previous: str) -> Optional[ClaimMatch]:
    excluded = EXCLUSION_RE.search(sentence)
    if not excluded:
        return None
    for term, (basis, pattern) in REQUIREMENT_TERMS.items():
        hit = re.search(pattern, sentence)
        if not hit or abs(hit.start() - excluded.start()) > 60:
            continue
        # 예외 근거는 소송요건의 예외를 정한 조문·판례여야 한다. 헌법의 일반 기본권 조항(재판청구권 등)만 든
        # 경우는 예외 근거로 보지 않는다.
        previous = _linked_previous(sentence, previous)
        context = sentence + " " + previous
        has_numeric_citation = bool(DIGIT_RE.search(context))
        cited = ([m for m in PROVISION_RE.finditer(context) if not _is_constitution(m.group("law"))]
                 if has_numeric_citation else [])
        other_cite = CASE_CITE_RE.search(sentence) or (previous and CASE_CITE_RE.search(previous))
        constitutional_only = has_numeric_citation and bool(PROVISION_RE.search(sentence)) and not cited and not other_cite
        if EXCEPTION_BASIS_RE.search(sentence) and not constitutional_only:
            return None
        if (cited or other_cite) and not constitutional_only:
            return None
        return ClaimMatch(
            "LITIGATION_REQUIREMENT_EXCLUSION", sentence, 0, f"근거 없이 소송요건({term})을 배제", "B", "SUSPICIOUS",
            [_source(basis)],
            f"{term}은 소송요건 또는 권리 행사의 요건이다({basis}). 서면은 예외를 정한 조문이나 판례를 들지 않고 "
            f"{term}이 적용되지 않는다고 주장했다.", {"requirement": term})
    return None


def requirement_mismatches(doc: NormalizedDocument, provisions: Sequence[Dict[str, Any]]) -> List[ClaimMatch]:
    """조문 요건(주체) 불일치. provisions: {"law", "article", "text", "version"} — 조회한 공식 원문."""
    text = build_reading_text(doc).text
    out: List[ClaimMatch] = []
    for start, end in sentence_bounds(text):
        sentence = " ".join(text[start:end].split())
        for match in PROVISION_RE.finditer(sentence):
            if not APPLY_RE.match(sentence, match.end()):
                continue
            law, article = law_name(match.group("law")), match.group("art")
            official = next((p for p in provisions if p.get("law") == law and str(p.get("article")) == article
                             and p.get("text")), None)
            if not official:
                continue
            subject = re.match(r"\s*(?:①|제\s*\d+\s*조\S*\s*)?\s*(?:\([^)]*\)\s*)?([^,.。]{2,40}?)(?:은|는|이|가)\s",
                               official["text"])
            if not subject:
                continue
            article_subject = subject.group(1)
            # 적용 대상은 법령명 앞 부분이다. 정규식이 법령명 앞 어절까지 잡으므로 법령명만큼 잘라 낸다.
            before = sentence[:match.end("law")].rstrip()
            applied_to = before[:len(before) - len(law)]
            public_rule = bool(PUBLIC_ACTOR_RE.search(article_subject))
            private_rule = bool(PRIVATE_ACTOR_RE.search(article_subject))
            actor_private = bool(PRIVATE_ACTOR_RE.search(applied_to)) and not PUBLIC_ACTOR_RE.search(applied_to)
            # 공적 주체(국가·행정청·공무원 등)를 요건으로 한 조문을 사인(회사·개인)에게 적용한 경우만 본다.
            # 반대 방향(사인 요건 조문을 국가에 적용)은 국가도 사용자·임대인 등이 될 수 있어 판단하지 않는다.
            if public_rule and not private_rule and actor_private:
                label = f"{law} 제{article}조"
                out.append(ClaimMatch(
                    "REQUIREMENT_MISMATCH", sentence, start, "조문의 주체 요건과 적용 대상 불일치", "B", "SUSPICIOUS",
                    [{"name": label, "text": official["text"][:400], "url": official.get("url", ""),
                      "version": official.get("version")}],
                    f"비교 대상 조문: {label}({official.get('version') or '조회 버전'}). 조문의 주체는 "
                    f"'{article_subject.strip()}'인데 서면은 이 조문을 다른 부류의 당사자에게 적용했다. 요건 충족 여부를 "
                    "사람이 확인해야 한다.", {"article_subject": article_subject.strip(), "compared": label}))
    return out


# --- 문서 단위 ----------------------------------------------------------------------
def _unreasonable_argument(sentence: str, previous: str, *, criminal_doc: bool = False) -> Optional[ClaimMatch]:
    """무리한 법리 주장 4종을 인용 오류와 분리해 독립 탐지한다(다중 신호 + 예외·극성 확인)."""
    context = f"{previous} {sentence}".strip()

    # 1) 소멸시효 기간 왜곡 (민법 제162조 일반 채권 10년·제766조 불법행위 3년/10년 대상 권리에 한정)
    is_limitation_topic = bool(
        re.search(r"소멸\s*시효|시효\s*(?:기간|완성)|영구(?:적|히)?\s*(?:소멸하지|완성되지)\s*않", sentence)
    )
    is_limitation_excluded = bool(
        re.search(
            r"취득\s*시효|공소\s*시효|징계\s*시효|"
            r"시효\s*(?:중단|정지|기산(?:점)?|이익\s*포기)|최고|재판상\s*청구|승인|압류|가압류|가처분|기산점|"
            r"국유\s*재산|조세\s*채권|국세|지방세|과징금|과태료|"
            r"특별법|상법|어음법|수표법|근로기준법|국가배상법|공익사업|보험금|단기소멸시효|임금\s*채권",
            context,
        )
    )
    if is_limitation_topic and not is_limitation_excluded:
        year_m = re.search(r"(\d{2,3})\s*년", sentence)
        perpetual = bool(re.search(r"영구(?:적|히)?|(?:소멸|완성)(?:하지|되지)\s*않|완성될\s*수\s*없", sentence))
        years = int(year_m.group(1)) if year_m else None
        is_property_other_than_ownership = bool(
            re.search(r"소유권\s*(?:이외|외)(?:의)?\s*재산권|물권|지상권|전세권|지역권", context)
        )
        is_ownership_defense = bool(re.search(r"소유권|물권적\s*청구권|등기\s*청구권|말소\s*등기", sentence))

        is_general_bond = bool(re.search(
            r"일반\s*채권|대여금|차용금|매매\s*대금|용역\s*대금|공사\s*대금|물품\s*대금|"
            r"임대차\s*보증금|보증금\s*반환|구상금|구상권|부당\s*이득|계약\s*(?:상)?\s*(?:채권|청구권)|"
            r"채무\s*불이행|민법\s*제\s*162\s*조",
            context,
        ))
        is_tort_claim = bool(re.search(
            r"손해\s*배상|불법\s*행위|위자료|민법\s*제\s*766\s*조",
            context,
        ))
        is_claim_scope = (is_general_bond or is_tort_claim)

        # 연수만으로 판정하지 않으며, 반드시 일반 채권 또는 손해배상청구권 특정 문맥이 존재해야 한다.
        distorted = (
            (years is not None and years >= 11 and is_claim_scope and not is_property_other_than_ownership)
            or (perpetual and is_claim_scope and not is_ownership_defense)
        )
        if distorted:
            detail_val = f"{years}년" if years is not None else "영구·시효 미완성"
            sources = []
            if is_general_bond:
                sources.append(_source("민법 제162조"))
            if is_tort_claim:
                sources.append(_source("민법 제766조"))
            if not sources:
                sources = [_source("민법 제162조"), _source("민법 제766조")]

            if is_general_bond and not is_tort_claim:
                reason_text = (
                    f"민법 제162조 제1항은 일반 채권의 소멸시효를 10년으로 정한다. 법정 중단·정지나 특별법상 특례 근거 없이 "
                    f"일반 채권의 소멸시효를 {detail_val}로 단정하는 주장은 실정법 기준에 반한다."
                )
            elif is_tort_claim and not is_general_bond:
                reason_text = (
                    f"민법 제766조는 불법행위로 인한 손해배상청구권의 소멸시효를 안 날로부터 3년·불법행위를 한 날로부터 10년으로 정한다. "
                    f"법정 중단·정지나 특례 없이 불법행위 손해배상청구권의 소멸시효를 {detail_val}로 단정하는 주장은 실정법 기준에 반한다."
                )
            else:
                reason_text = (
                    f"민법 제162조 제1항은 일반 채권의 소멸시효를 10년으로, 제766조는 불법행위 손해배상청구권의 소멸시효를 "
                    f"안 날로부터 3년·불법행위를 한 날로부터 10년으로 정한다. 법정 중단·정지나 특별법상 특례 근거 없이 "
                    f"일반 채권·손해배상청구권의 소멸시효를 {detail_val}로 단정하는 주장은 실정법 기준에 반한다."
                )

            return ClaimMatch(
                "LIMITATION_PERIOD_DISTORTION", sentence, 0,
                f"소멸시효 기간의 법정 기준 왜곡 주장 ({detail_val})", "B", "CONTRADICTED",
                sources,
                reason_text,
                {"defect_type": "UNFOUNDED_CLAIM", "claimed_period": detail_val},
            )

    # 2) 민·형사 입증책임 및 무죄추정 혼동
    if (
        not criminal_doc
        and not re.search(r"공소\s*사실|공소\s*제기|구형|형사\s*처벌을?\s*(?:과하|명하|선고하)", sentence)
        and not re.search(
            r"별개|구별|다르|달리|독자적|기속되지\s*않|무관하게|불구하고\s*(?:민사|배상|책임)|"
            r"미치지\s*않|인정될\s*수\s*있|부정되는\s*것은\s*아니",
            sentence,
        )
    ):
        has_civil_context = bool(re.search(
            r"민사|손해\s*배상|배상\s*책임|배상|채무\s*불이행|불법\s*행위|계약\s*책임|국가\s*배상|청구|책임|징계|처분",
            context,
        ))
        presumption_confusion = bool(
            re.search(r"무죄\s*추정(?:의\s*원칙)?", sentence)
            and has_civil_context
            and re.search(
                r"면책|성립(?:하지|될\s*수\s*없)|인정(?:될|할)\s*수\s*없|부정|기각|배제|"
                r"책임(?:이|을)?\s*(?:없|질\s*수\s*없|묻기\s*어렵)|전제(?:될|할)\s*수\s*없",
                sentence,
            )
        )
        proof_confusion = bool(
            re.search(r"합리적.{0,2}의심[^.]{0,12}?없(?:을|는)\s*정도|범죄(?:의)?\s*증명(?:이)?\s*없", sentence)
            and re.search(r"민사|손해\s*배상|배상\s*책임|채무\s*불이행|계약\s*책임|증명\s*책임|입증\s*책임", context)
        )
        if presumption_confusion or proof_confusion:
            return ClaimMatch(
                "CIVIL_CRIMINAL_STANDARD_CONFUSION", sentence, 0,
                "민·형사 입증책임 및 무죄추정 원칙 혼동 주장", "B", "CONTRADICTED",
                [_source("헌법 제27조 제4항"), _source("민사소송법 제202조")],
                "헌법 제27조 제4항의 무죄추정 원칙과 형사상 고도 증명 기준은 형사피고인의 유죄 인정에 관한 "
                "원칙이다. 민사상 손해배상이나 채무불이행 책임은 변론 전체의 취지와 증거조사 결과에 따른 자유심증 및 "
                "증명의 우월성(고도의 개연성) 기준(민사소송법 제202조)으로 판단하므로 형사 기준을 그대로 적용해 배척할 수 없다.",
                {"defect_type": "UNFOUNDED_CLAIM"},
            )

    # 3) 하급심의 법률 효력 폐지 주장
    if (
        re.search(r"(?:지방|고등|가정|행정|회생|특허)\s*법원|하급심(?:\s*법원)?|일반\s*법원|제?\s*1\s*심\s*(?:법원|판결)|항소심\s*(?:법원|판결)", sentence)
        and re.search(
            r"(?:법률|법\s*조항|법조문|법\s*규정|민법|형법|상법|국가배상법|근로기준법|[가-힣]{2,15}법률?)"
            r"(?:\s*제\s*\d+\s*조(?:의\s*\d+)?)?"
            r"(?!\s*(?:시행령|시행규칙|규칙|고시|훈령|예규|조례|처분|계약|약관))",
            sentence,
        )
        and not re.search(r"약관\s*규정|계약\s*규정|사규|내부\s*규정", sentence)
        and not re.search(r"위헌\s*(?:법률\s*)?심판\s*제청|제청\s*신청|명령[\s·ㆍ]*규칙\s*(?:심사|위헌|위법)|헌법재판소(?:의|가)?\s*(?:위헌|헌법불합치)\s*결정", sentence)
        and re.search(
            r"위헌(?:으로|이라)\s*(?:판단하여\s*)?(?:직접\s*)?(?:폐지|무효화?|실효|효력을?\s*(?:상실|부인|배제|정지|소멸|박탈))|"
            r"(?:법률|법\s*조항|법조문|법\s*규정|(?:민법|형법|상법|국가배상법|근로기준법|[가-힣]{2,15}법)(?:\s*제\s*\d+\s*조(?:의\s*\d+)?)?)"
            r"(?:을|를|이|가|은|는)?\s*(?:직접\s*)?(?:위헌\s*(?:결정|선고)|폐지|실효|무효로\s*선언)|"
            r"(?:법률|법\s*조항|법조문|(?:민법|형법|상법|국가배상법|근로기준법|[가-힣]{2,15}법)(?:\s*제\s*\d+\s*조(?:의\s*\d+)?)?)"
            r"(?:의)?\s*효력(?:을|이)\s*(?:전면\s*)?(?:상실|폐지|소멸)(?:하|시|되)|"
            r"위헌[^.]{0,25}더\s*이상\s*(?:어떠한\s*)?(?:적용|효력)(?:도|이|을)?\s*(?:할|될|가질|인정할)\s*수\s*없",
            sentence,
        )
    ):
        return ClaimMatch(
            "LOWER_COURT_STATUTE_INVALIDATION", sentence, 0,
            "하급심 법원의 법률 효력 직접 폐지·무효화 주장", "B", "CONTRADICTED",
            [_source("헌법 제107조"), _source("헌법 제111조")],
            "헌법 제107조 제1항 및 제111조 제1항 제1호에 따라 법률의 위헌 여부 심판 권한은 헌법재판소에 전속하며, "
            "각급 법원은 명령·규칙이나 처분의 위헌·위법 심사 외에 법률의 효력을 직접 폐지·실효시킬 권한이 없고 위헌심판 제청만 가능하다.",
            {"defect_type": "JURISDICTIONAL_DEFECT"},
        )

    # 4) 계약 일방 변경·증액 주장
    if (
        re.search(
            r"일방적(?:인|으로)?\s*(?:통지|통보|고지|결정|선언|변경|인상|증액)|"
            r"(?:상대방|원고|피고|계약\s*당사자)(?:의)?\s*(?:동의|합의|승낙)(?:이나|도|가)?\s*없이(?:\s*(?:도|서도))?(?:\s*일방적으로)?",
            sentence,
        )
        and re.search(
            r"(?:계약\s*(?:내용|조건|금액|대금|단가|임대료|수수료|위약금|기간)|대금|임료|약정\s*(?:금액|내용)|계약상\s*의무)(?:을|를|이|가|은|는)?[^.]{0,35}?(?:변경|증액|인상|추가\s*부과|감액|개정|상향)|"
            r"(?:\d+(?:\.\d+)?\s*배|\d{3,}\s*%|두\s*배|세\s*배|네\s*배)[^.]{0,20}(?:증액|인상|청구|부과|상향)",
            sentence,
        )
        and re.search(
            r"유효(?:하다|합니다|하게|히)|효력(?:이|을)\s*(?:발생|인정|가지|갖)|구속(?:한다|력이\s*있)|"
            r"지급할\s*의무|따라야\s*(?:한다|합니다)|당연히\s*(?:변경|증액|인상|적용|성립)|"
            r"(?:변경|증액|인상)(?:되었다|됐다|된다|할\s*수\s*있)",
            sentence,
        )
        and not re.search(
            r"(?:물가\s*변동|단가\s*연동|차임\s*증감\s*청구|해지|해제)(?:에\s*따|으로\s*인)|"
            r"(?:계약상\s*조정\s*조항|조정\s*기준|별도\s*특약|당사자\s*(?:간|사이의)\s*합의)(?:이|가|에\s*(?:따|의))|"
            r"정관\s*변경|취업\s*규칙",
            sentence,
        )
    ):
        return ClaimMatch(
            "UNILATERAL_CONTRACT_MODIFICATION", sentence, 0,
            "합의·법정 근거 없는 계약 일방 변경 및 증액 주장", "B", "CONTRADICTED",
            [_source("민법 제105조"), _source("민법 제543조")],
            "계약 내용과 대금의 변경은 사적자치 원칙상 당사자의 의사 합치나 계약상 조정 특약 또는 법률의 명시적 규정이 있어야 효력이 발생한다. "
            "해지·해제의 형성권과 달리 일방적 통보·통지만으로 상대방의 동의 없이 계약 금액이나 조건을 증액·변경할 수 없다.",
            {"defect_type": "UNFOUNDED_CLAIM"},
        )
    return None


def _civil_inference(sentence: str, previous: str) -> Optional[ClaimMatch]:
    """Flag a missing inference step for human review, not a merits determination."""
    compact = re.sub(r"\s+", "", sentence)
    context = re.sub(r"\s+", "", previous + " " + sentence)
    if (re.search(r"(?:사기죄?|횡령죄?|배임죄?|형사(?:상)?범죄).{0,15}?(?:구성|성립|해당|인정)", compact)
            and re.search(r"채무불이행|(?:납기|지급|이행|대금|정산금|반환).{0,10}?(?:지연|지체|미지급|불이행)", context)
            and (re.search(r"만으로|곧바로|자동으로|당연히|단순", compact) or compact.startswith("이는"))):
        return ClaimMatch("CIVIL_FRAUD_INFERENCE", sentence, 0, "채무불이행에서 사기 고의로의 추론 검토", "C", "SUSPICIOUS",
            [_source("사기죄의 행위 당시 판단 기준")],
            "사후의 지체·불이행만으로 계약 당시 기망이나 편취 고의를 확정할 수 없다. 계약 체결 당시의 "
            "의사·능력, 기망행위, 처분행위와의 관계를 뒷받침하는 별도 사실과 증거를 확인해야 한다.")
    if (re.search(r"반증하지\s*못|무손해", compact)
            and re.search(r"확정\s*간주|확정간주|당연.{0,8}(?:확정|간주|인정)|자동.{0,8}(?:확정|간주|인정)|전액.{0,8}확정", compact)):
        return ClaimMatch("DAMAGE_PROOF_INFERENCE", sentence, 0, "입증책임의 임의 전도 및 손해액 당연 확정 궤변 (기각/각하 위험)", "B", "CONTRADICTED",
            [_source("민사소송법 제202조"), _source("민사소송법 제288조")],
            "민사소송법상 손해 발생과 손해액의 증명책임은 원고에게 있으며, 자유심증주의는 증거판단 원칙일 뿐 입증책임을 전환하지 않는다. "
            "피고에게 '무손해'라는 소극적 사실의 반증을 요구하여 불이행 시 손해액을 당연 확정·간주한다는 주장은 입증책임 분배 원칙을 "
            "정면으로 전도한 중대한 궤변(BURDEN_OF_PROOF_INVERSION, UNFOUNDED_CLAIM)으로 기각 대상이다.",
            {"defect_type": "BURDEN_OF_PROOF_INVERSION"})
    if (re.search(r"자유심증|입증책임|증명책임", compact)
            and re.search(r"청구(?:금액|액)|손해액|개발\s*손실액|손실액|법정손해|위자료", compact)
            and re.search(r"확정\s*간주|확정간주|당연.{0,8}(?:확정|간주|인정)|자동.{0,8}(?:확정|간주|인정)|전액.{0,8}확정", compact)):
        return ClaimMatch("DAMAGE_PROOF_INFERENCE", sentence, 0, "자유심증주의와 손해액 입증책임", "C", "SUSPICIOUS",
            [_source("민사소송법 제202조")],
            "자유심증주의는 증거의 증명력을 법관의 자유로운 판단에 맡기는 원칙일 뿐, 손해 발생과 액수의 "
            "증명책임을 면제하거나 입증 없이 청구금액 전액을 당연 인정하는 근거가 될 수 없다. 손해액 산정의 "
            "구체적 근거를 확인해야 한다.",
            {"defect_type": "BURDEN_OF_PROOF_INVERSION"})
    if (re.search(r"법인|회사", compact) and re.search(r"임직원|직원|근로자", compact)
            and re.search(r"정신적?고통|위자료", context) and re.search(r"대위|동일하므로|합산하여.{0,8}청구", compact)
            and not re.search(r"채권양도|선정당사자|선정당사자의|채권자대위.{0,12}요건", compact)):
        return ClaimMatch("THIRD_PARTY_DAMAGE", sentence, 0, "법인과 임직원 개인의 손해·청구권 구분", "C", "SUSPICIOUS",
            [_source("민법 제751조")],
            "법인 고유의 무형손해와 임직원 개인의 정신적 손해는 청구권자·손해 발생 근거를 구분해야 한다. "
            "직원들의 청구권을 회사가 행사한다면 양도·대위·선정당사자 등 권한과 요건을 확인해야 한다. "
            "법인에게 재산 외 손해가 발생할 수 없다고 단정하는 판단은 아니다.")
    if (re.search(r"헌법|기본권", compact)
            and re.search(r"변론권.*(?:박탈|배제|제한)|원천\s*박탈|즉각.*승소", compact)):
        return ClaimMatch("PRIVATE_CONSTITUTIONAL_EFFECT", sentence, 0, "사적 계약에 헌법 기본권 결부 변론권 박탈 궤변 (기각/각하 위험)", "B", "CONTRADICTED",
            [_source("헌법 제27조"), _source("민법 제103조")],
            "사법상 법률관계에 헌법상 기본권 침해 법리를 직접 적용하여 피고의 변론권 자체를 원천 박탈하고 즉각 승소 판결을 요구하는 주장은 "
            "헌법 제27조 재판청구권과 민사소송상 변론주의 원칙에 정면으로 위배되는 무리한 궤변(UNFOUNDED_CLAIM)으로 배척 대상이다.",
            {"defect_type": "UNFOUNDED_CLAIM"})
    if (re.search(r"계약|약정|사적자치|법률관계", context) and re.search(r"헌법|기본권|과잉금지", compact)
            and re.search(r"심리\s*없이|심리할필요없이|배척|각하", compact)):
        return ClaimMatch("PRIVATE_CONSTITUTIONAL_EFFECT", sentence, 0, "사적 계약에 대한 헌법 기본권 직접 적용", "C", "SUSPICIOUS",
            [_source("헌법 제27조"), _source("민법 제103조"), _source("헌법의 대사인적 효력")],
            "사인 간의 법률관계나 사적자치의 계약에 헌법상 기본권 규정이 직접 적용된다고 단정할 수 없다. "
            "민법 제103조 등 사법의 일반조항을 매개로 간접 적용되는지, 계약 조항이 반사회질서에 해당하는지를 "
            "검토해야 한다.",
            {"defect_type": "UNFOUNDED_CLAIM"})
    return None


def _provisional_relief_references(text: str) -> List[ClaimMatch]:
    relief = _relief_span(text)
    if not relief or CRIMINAL_DOC_RE.search(text[:3000]):
        return []
    body = text[relief[0]:relief[1]]
    starts = list(re.finditer(r"(?<!\d)(\d{1,2})\.\s*", body))
    items = [(m.group(1), m.start(), body[m.end():starts[i + 1].start() if i + 1 < len(starts) else len(body)])
             for i, m in enumerate(starts)]
    criminal = {number for number, _, content in items if re.search(
        r"(?:징역|금고|벌금|형사\s*처벌)[^.]{0,80}(?:처한다|처하라|선고하라)", content)}
    out = []
    for _, start, content in items:
        if not re.search(r"가집행할\s*수\s*있", content):
            continue
        refs = set(re.findall(r"제\s*(\d+)\s*항", content)) & criminal
        if refs:
            out.append(ClaimMatch("CRIMINAL_PROVISIONAL_EXECUTION", " ".join(content.split()), relief[0] + start,
                "형벌 청구 항목을 참조한 가집행 청구", "B", "CONTRADICTED", [_source("민사소송법 제213조")],
                "가집행 대상으로 참조한 청구 항목에 형벌 청구가 포함되어 있다. 민사 가집행선고는 재산권상 청구에 관한 "
                "판결을 대상으로 하며 형벌 청구에는 적용할 수 없다.", {"referenced_relief_items": sorted(refs)}))
    return out


def _relief_span(text: str):
    relief = RELIEF_HEAD_RE.search(text)
    if not relief:
        return None
    grounds = GROUNDS_HEAD_RE.search(text, relief.end())
    return relief.end(), grounds.start() if grounds else min(len(text), relief.end() + 1500)


def classify_claims(text: str, lookup: Optional[HistoryLookup] = None) -> List[ClaimMatch]:
    relief = _relief_span(text)
    # 민사 소장, 준비서면, 답변서 등 원고/피고 표기 및 청구취지가 있는 문서는 형사 공소장이 아님
    is_civil_pleading = bool(re.search(r"^\s*(?:소\s*장|준\s*비\s*서\s*면|답\s*변\s*서)|원\s*고\s*(?:[\d.]+|[가-힣])|청\s*구\s*취\s*지", text[:1000]))
    criminal_doc = bool(CRIMINAL_DOC_RE.search(text[:3000])) and not is_civil_pleading
    out: List[ClaimMatch] = []
    previous = ""
    for start, end in sentence_bounds(text):
        sentence = " ".join(text[start:end].split())
        if not sentence:
            continue
        in_relief = bool(relief and relief[0] <= start < relief[1])
        chosen = None
        for check in (lambda s: _unconstitutionality(s, lookup),
                      lambda s: _unreasonable_argument(s, previous, criminal_doc=criminal_doc),
                      lambda s: _civil_inference(s, previous),
                      lambda s: _generalization(s, previous),
                      lambda s: _remedy(s, in_relief, criminal_doc), _unsourced_standard,
                      lambda s: _requirement_exclusion(s, previous)):
            match = check(sentence)
            if match and not in_relief and not _author_asserts(match, previous):
                continue  # 부정·전달·가정으로 쓴 문장은 작성자의 주장이 아니다(v5 3-2)
            if match:
                match.start = start
                out.append(match)
                chosen = match
                break  # 한 문장은 가장 앞선 유형 하나로만 판정한다(같은 문장 이중 판정 방지)
        linked = _linked_previous(sentence, previous)
        legacy_excluded = EXCLUSION_RE.search(text[start:end]) if chosen else None
        for clause in exclusion_clauses(text[start:end], linked, cited=_has_citation(sentence, linked)):
            if (chosen and chosen.claim_type == "LITIGATION_REQUIREMENT_EXCLUSION"
                    and legacy_excluded and clause.start <= legacy_excluded.start() < clause.end
                    and "".join(clause.target.split()) == chosen.extra.get("requirement")):
                continue  # Keep the existing classification of this same exclusion proposition.
            out.append(ClaimMatch(
                "STATUTORY_RULE_EXCLUSION", text[start + clause.start:start + clause.end].strip(),
                start + clause.start, "추상적 근거로 법정 규정의 적용 배제 주장", "C", "SUSPICIOUS", [],
                f"{clause.target}의 적용을 배제한다는 결론에 법정 예외의 요건과 충족 사실을 연결한 근거가 확인되지 않는다. "
                "정의·형평이나 다른 제도의 유추만으로 적용을 배제할 수 있는지, 관련 법령·판례 및 구체적 요건을 확인해야 한다.",
                {"excluded_target": clause.target, "exclusion_ground": clause.ground}))
        previous = sentence
    return out


# 유형마다 '명제'로 볼 부분: (앞 부분, 명제 끝을 정하는 뒷부분). 극성은 명제 끝 뒤의 글로 판별한다.
_CLAIM_SPANS = {
    "LIMITATION_PERIOD_DISTORTION": (
        re.compile(r"소멸\s*시효|시효|영구"),
        re.compile(r"\d{2,3}\s*년|(?:소멸|완성)(?:하지|되지)\s*않|완성될\s*수\s*없|완성|소멸"),
    ),
    "CIVIL_CRIMINAL_STANDARD_CONFUSION": (
        re.compile(r"무죄\s*추정|합리적.{0,2}의심|범죄(?:의)?\s*증명"),
        re.compile(
            r"인정(?:될|할)\s*수\s*없|성립(?:하지|될\s*수\s*없)|전제(?:될|할)\s*수\s*없|"
            r"책임(?:이|을)?\s*(?:없|질\s*수\s*없|묻기\s*어렵)|묻기\s*어렵|물을\s*수\s*없|"
            r"적용|면책|부정|기각|배제"
        ),
    ),
    "LOWER_COURT_STATUTE_INVALIDATION": (
        re.compile(r"(?:지방|고등|가정|행정|회생|특허)\s*법원|하급심|일반\s*법원|제?\s*1\s*심|항소심"),
        re.compile(
            r"더\s*이상[^.]{0,30}?(?:적용|효력)[^.]{0,20}?수\s*없|"
            r"(?:폐지|실효|상실|소멸|무효화?|부인|배제)"
            r"(?:[^.,;]{0,30}?더\s*이상[^.]{0,30}?(?:적용|효력)[^.]{0,20}?수\s*없)?"
        ),
    ),
    "UNILATERAL_CONTRACT_MODIFICATION": (re.compile(r"일방적|동의\s*없이|합의\s*없이|통지(?:만)?으로|통보(?:만)?으로"), re.compile(r"유효|효력|변경|증액|인상|구속|의무")),
    "CIVIL_FRAUD_INFERENCE": (re.compile(r"사기죄"), re.compile(r"구성|성립|해당")),
    "DAMAGE_PROOF_INFERENCE": (re.compile(r"확정|간주|인정"), None),
    "THIRD_PARTY_DAMAGE": (re.compile(r"대위|동일|합산"), None),
    "PRIVATE_CONSTITUTIONAL_EFFECT": (re.compile(r"각하|기각|배척|박탈|승소"), None),
    "UNCONSTITUTIONALITY": (UNCON_RE, None),
    "UNSUPPORTED_GENERALIZATION": (QUANTIFIER_RE, LEGAL_EFFECT_RE),
    "NO_BASIS_REMEDY": (re.compile(r"징역|금고|벌금|형벌|처벌|배상"), None),
    "UNSOURCED_STANDARD": (STANDARD_NOUN_RE, RELIANCE_RE),
    "LITIGATION_REQUIREMENT_EXCLUSION": (EXCLUSION_RE, None),
}


def _author_asserts(match: ClaimMatch, previous: str) -> bool:
    """이 문장의 명제를 작성자가 단정했는가. 출처 불명 기준은 내용의 긍정·부정과 무관하게 그 기준에 기댄 것이
    문제이므로 부정은 보지 않고 전달·가정만 본다."""
    head, tail = _CLAIM_SPANS.get(match.claim_type, (None, None))
    found = head.search(match.sentence) if head else None
    if not found:
        return True
    end = found.end()
    if tail is not None:
        after = tail.search(match.sentence, found.start())
        if after:
            end = max(end, after.end())
    result = polarity(match.sentence, (found.start(), end), previous=previous)
    if match.claim_type == "UNSOURCED_STANDARD" and result == NEGATED:
        return True
    return result == ASSERTED


def _to_finding(doc: NormalizedDocument, match: ClaimMatch, reading) -> Finding:
    block, _ = reading.locate(match.start)
    kind = (FindingType.UNSUPPORTED_GENERALIZATION if match.claim_type == "UNSUPPORTED_GENERALIZATION"
            else FindingType.OVERCLAIM if match.claim_type == "UNCONDITIONAL_LEGAL_OVERCLAIM"
            else FindingType.CASE_HOLDING_DISTORTION if match.claim_type == "PRECEDENT_OVERGENERALIZATION"
            else FindingType.LAW_CITATION_ERROR if match.claim_type == "UNVERIFIED_ADMIN_INTERPRETATION"
            else FindingType.LEGAL_ARGUMENT_INVALID)
    grade = {"A": EvidenceGrade.A, "B": EvidenceGrade.B, "C": EvidenceGrade.C, "U": EvidenceGrade.U}.get(
        match.grade, EvidenceGrade.C
    )
    human = match.grade in ("C", "U") or match.status in ("SUSPICIOUS", "UNVERIFIED")
    evidence = [Evidence.create(description="서면의 주장", grade=EvidenceGrade.B, document_id=doc.document_id,
                                excerpt=match.sentence[:300], supports=False,
                                page=block.page if block else None, block_id=block.block_id if block else None)]
    for source in match.basis:
        evidence.append(Evidence.create(description=f"근거: {source['name']}" + (f" ({source['url']})" if source.get("url") else ""),
                                        grade=EvidenceGrade.A if source.get("text") else EvidenceGrade.U,
                                        excerpt=str(source.get("text") or source.get("note") or "")[:300]))
    sev = (Severity.HIGH if match.grade in ("A", "B") and match.status == "CONTRADICTED"
           else Severity.INFO if match.status == "UNVERIFIED"
           else Severity.MEDIUM)
    return Finding.create(
        type=kind, status=VerificationStatus(match.status),
        severity=sev,
        evidence_grade=grade,
        title=f"법리 검토({_TYPE_LABELS[match.claim_type]}): {match.judgment} — '{match.sentence[:70]}'",
        detail=match.detail + (" 근거: " + "; ".join(b["name"] for b in match.basis) if match.basis else ""),
        confidence={"A": 0.9, "B": 0.75, "C": 0.5, "U": 0.3}.get(match.grade, 0.5),
        confidence_features={"deterministic_rule": True, "rule_id": f"CLAIM.{match.claim_type}",
                             "claim_type": match.claim_type, "judgment": match.judgment, "claim": match.sentence[:300],
                             "basis": match.basis, "human_review": human, **match.extra},
        document_id=doc.document_id, engine=ENGINE_NAME,
        page=block.page if block else None, block_id=block.block_id if block else None,
        tags=["LEGAL_CLAIM", f"CLAIM.{match.claim_type}"]
        + ([match.extra["defect_type"]] if match.extra.get("defect_type") else [])
        + (["BURDEN_INVERSION"] if match.extra.get("defect_type") == "BURDEN_OF_PROOF_INVERSION" else [])
        + (["UNVERIFIED"] if match.status == "UNVERIFIED" else [])
        + (["HUMAN_REVIEW"] if human else []),
        evidence=evidence)


_TYPE_LABELS = {"LIMITATION_PERIOD_DISTORTION": "소멸시효 기간 왜곡",
                "CIVIL_CRIMINAL_STANDARD_CONFUSION": "민·형사 입증기준 혼동",
                "LOWER_COURT_STATUTE_INVALIDATION": "하급심 법률 폐지 주장",
                "UNILATERAL_CONTRACT_MODIFICATION": "계약 일방 변경·증액",
                "CIVIL_FRAUD_INFERENCE": "채무불이행과 사기", "DAMAGE_PROOF_INFERENCE": "손해 증명",
                "THIRD_PARTY_DAMAGE": "타인 손해 청구", "PRIVATE_CONSTITUTIONAL_EFFECT": "사법상 기본권 적용",
                "CRIMINAL_PROVISIONAL_EXECUTION": "가집행 참조 대상",
                "UNCONSTITUTIONALITY": "위헌 주장", "UNSUPPORTED_GENERALIZATION": "전칭 일반화",
                "NO_BASIS_REMEDY": "근거 없는 청구 유형", "REQUIREMENT_MISMATCH": "조문 요건 불일치",
                "STATUTORY_RULE_EXCLUSION": "법정 규정 적용 배제",
                "UNSOURCED_STANDARD": "출처 불명 기준", "LITIGATION_REQUIREMENT_EXCLUSION": "소송요건 배제",
                "UNCONDITIONAL_LEGAL_OVERCLAIM": "요건 생략 절대 단정",
                "PRECEDENT_OVERGENERALIZATION": "판례 취지 절대화·확대해석",
                "UNVERIFIED_ADMIN_INTERPRETATION": "행정해석·유권해석 미확인"}


_ABSOLUTE_MODALITY_RE = re.compile(r"(?:무조건|당연히|자동으로|예외\s*없이|어떠한\s*경우에도|언제나|반드시|절대로|전면\s*(?:무효|배제|부정|거부|면책))")
_BROAD_OVR_MODALITY_RE = re.compile(
    r"(?:만으로\s*(?:곧바로|즉시|바로)|을\s*불문하고|와\s*무관하게|에\s*관계\s*없이|여부와\s*상관\s*없이|"
    r"일률적으로|할\s*여지가\s*없|볼\s*수밖에\s*없|배제될\s*수\s*없|(?:로|으로)\s*(?:의제|간주)(?:되|된|합)|"
    r"(?:요건|절차|고의|과실|손해|인과관계|입증|증명|최고|통지|동의|승낙)(?:을|를|은|는|이|가)?\s*(?:요하지\s*않|필요가\s*없|거칠\s*필요)|"
    r"(?:일체|전부|누구나|모든)\s+[^.!?\n]{0,25}(?:성립|인정|무효|책임|배상|위법|해당))"
)
_QUOTED_ATTRIBUTION_RE = re.compile(r"(?:상대방은|(?:라고|다고)\s*(?:주장|항변|진술)|주장에\s*(?:따르면|의하면))")
_CASE_NO_HINT_RE = re.compile(r"(?:19|20)?\d{2}\s*[가-힣]{1,3}\s*\d{2,6}")


_LEGAL_EFFECT_RE = re.compile(
    r"(?:성립|인정|무효|취소|면책|책임|배상|위법|적법|해제|해지|적용|배제|추정|간주|조각|상계|시효|입증|증명|소급)"
)
_PROVISO_TEXT_RE = re.compile(r"(?:다만|단,|예외적으로|특별한\s*사정이\s*없는\s*한|원칙적으로)")


def _clause_normalizer_overclaims(text: str) -> List[ClaimMatch]:
    """Use ClauseNormalizer discourse_role/modality to flag multi-factor doctrines asserted unconditionally."""
    if not text:
        return []
    try:
        from packages.korean_nlp.clause_normalizer import normalize_sentence
    except Exception:
        return []

    out: List[ClaimMatch] = []
    for start, end in sentence_bounds(text):
        sentence = text[start:end].strip()
        if len(sentence) < 12 or _QUOTED_ATTRIBUTION_RE.search(sentence) or _PROVISO_TEXT_RE.search(sentence):
            continue
        clauses = normalize_sentence(sentence)
        if not clauses:
            continue
        if any(
            c.discourse_relation in ("CONDITION", "EXCEPTION_PROVISO", "CONCESSION")
            or c.modality in ("HYPOTHETICAL", "INTERROGATIVE", "PERMISSIVE")
            for c in clauses
        ):
            continue
        main_clauses = [
            c for c in clauses
            if c.discourse_relation == "MAIN"
            and c.polarity in ("ASSERTED", "NEGATED", "DOUBLE_NEGATED_ASSERTED")
        ]
        if not main_clauses:
            continue
        has_abs = any(c.modality == "MANDATORY" or _ABSOLUTE_MODALITY_RE.search(c.raw_text) for c in main_clauses) or bool(_ABSOLUTE_MODALITY_RE.search(sentence))
        has_broad = bool(_BROAD_OVR_MODALITY_RE.search(sentence))

        # 3대 일반 법리 과장 구조 (부정·반박·상대방 인용 제외)
        joined_main = " ".join(c.raw_text for c in main_clauses)
        is_rebuttal_or_neg = bool(re.search(
            r"(?:않는다|않았다|아니다|아니며|부당하다|이유\s*없|사실과\s*다르|배척|"
            r"(?:간주|인정|단정|추정|성립|적용)(?:할|될|하기)\s*수\s*없|성립하지\s*않|주장하|주장한|판단할\s*수\s*없)",
            joined_main,
        )) or bool(re.search(
            r"(?:(?:간주|인정|단정|추정|성립)(?:할|될|하기)\s*수\s*없|성립하지\s*않)",
            sentence,
        ))
        if is_rebuttal_or_neg:
            continue

        doctrinal_ovr = False
        # 1) 단순 침묵/미회신/부작위 -> 동의·승낙·합의·인정·효력 간주
        if (
            re.search(r"(?:미회신|회신(?:을|이)?\s*(?:하지\s*않|없)|답변(?:을|이)?\s*(?:하지\s*않|없)|침묵|무응답|이의(?:를)?\s*(?:제기하지\s*않|제기(?:가)?\s*없))", sentence)
            and re.search(r"(?:동의|승낙|승인|수락|합의|인정|자백|추인|수용|간주|추정)(?:한\s*것|으로\s*보|된다|한다|이다|되므로|하므로|에\s*해당|셈)", sentence)
            and not re.search(r"(?:특약|약정|법령|규정|상법|민법\s*제\d+조)", sentence)
        ):
            doctrinal_ovr = True
        # 2) 내부 지침/안내/매뉴얼 -> 대외적 법규범·상위법/법률 우선·법적 무효 단정
        elif (
            re.search(r"(?:내부\s*(?:지침|안내|규정|매뉴얼|기준|방침)|업무\s*편람|사내\s*규정)", sentence)
            and re.search(r"(?:법규범|법률상\s*의무|상위법|(?:법령|법률|시행령)(?:에|보다)\s*우선|대외적\s*구속력|직접\s*적용|당연히\s*(?:무효|위법)|무효(?:가|로)\s*된다)", sentence)
        ):
            doctrinal_ovr = True
        # 3) 단순 착오/누락/지연/불이행 -> 곧바로 고의·기망·사기·범죄 성립 단정
        elif (
            re.search(r"(?:단순(?:한)?\s*(?:지급\s*지연|지연|미지급|불이행|착오|누락|오류|불일치|미기재)|(?:지연|미지급|불이행|착오|누락)[^.\n]{0,12}?(?:곧바로|당연히|즉시))", sentence)
            and re.search(r"(?:고의|기망|사기죄?|배임죄?|횡령죄?|범죄|형사(?:상)?\s*(?:처벌|책임)|악의|범의|불법영득)", sentence)
            and re.search(r"(?:성립|인정|추정|단정|해당)", sentence)
        ):
            doctrinal_ovr = True

        if not has_abs and not has_broad and not doctrinal_ovr:
            continue

        # Multi-element / discretionary doctrines
        has_doctrine = doctrinal_ovr or (
            ("위법성" in sentence and "조각" in sentence)
            or ("과실상계" in sentence)
            or ("손해배상" in sentence and (has_abs or has_broad or "당연" in sentence))
            or (("소멸시효" in sentence or "제소기간" in sentence) and (has_abs or has_broad or "당연" in sentence))
            or (("입증책임" in sentence or "증명책임" in sentence) and (has_abs or has_broad or "전부" in sentence or "전가" in sentence or "항상" in sentence))
            or ("법률" in sentence and "개정" in sentence and ("소급" in sentence or "면책" in sentence))
            or (("기본권" in sentence or "저항권" in sentence) and (has_abs or has_broad or "절대" in sentence or "어떠한" in sentence or "전면" in sentence or "당연" in sentence or "발동" in sentence))
            or ("계약" in sentence and ("해제" in sentence or "해지" in sentence) and (has_abs or has_broad or "당연" in sentence))
            or (("징계" in sentence or "해고" in sentence) and (has_abs or has_broad or "당연" in sentence))
            or (("처분" in sentence or "재량" in sentence) and (has_abs or has_broad or "당연" in sentence))
            or (("신의칙" in sentence or "권리남용" in sentence) and (has_abs or has_broad or "배제" in sentence or "당연" in sentence))
            or (("부당이득" in sentence or "원상회복" in sentence) and (has_abs or has_broad or "당연" in sentence))
            or (("보증" in sentence or "연대책임" in sentence) and (has_abs or has_broad or "전부" in sentence))
            or (("명의신탁" in sentence or "강행법규" in sentence) and (has_abs or has_broad or "당연" in sentence))
            or (("포기" in sentence or "면책" in sentence or "고의" in sentence or "진정성립" in sentence) and (has_abs or has_broad))
        )
        if not has_doctrine:
            continue
        out.append(ClaimMatch(
            claim_type="UNCONDITIONAL_LEGAL_OVERCLAIM",
            sentence=sentence,
            start=start,
            judgment="복합 요건·예외·재량 검토 없이 절대 단정",
            grade="C",
            status="SUSPICIOUS",
            basis=[],
            detail="법률상 복합 요건·예외 단서 또는 법원 재량이 필요한 법리를 조건·예외 검토 없이 무조건·당연 성립/배제로 단정하고 있다.",
            extra={"defect_type": "OVERCLAIM", "clause_normalizer": True},
        ))
        if _CASE_NO_HINT_RE.search(sentence):
            out.append(ClaimMatch(
                claim_type="PRECEDENT_OVERGENERALIZATION",
                sentence=sentence,
                start=start,
                judgment="판례 취지를 예외 없는 절대 법리로 확대 단정",
                grade="C",
                status="SUSPICIOUS",
                basis=[],
                detail="구체적 사안과 복합 요건을 전제로 한 판례 취지를 예외 없는 절대적·일률적 법리로 확대해 원용하고 있다.",
                extra={"defect_type": "CIT-MIS", "clause_normalizer": True},
            ))
    return out


_ADMIN_INTERP_RE = re.compile(r"(?:유권해석|행정해석|질의회신|법령해석)")
_ADMIN_CONTEXT_RE = re.compile(r"(?:\d{4}\s*\.\s*\d{1,2}\s*\.|(?:부|청|처|위원회|관리관실|법제처)\b)")


def _unverified_admin_interpretations(text: str) -> List[ClaimMatch]:
    """Flag administrative/authoritative interpretation citations as UNVERIFIED (SRC-UNV)."""
    if not text:
        return []
    out: List[ClaimMatch] = []
    for start, end in sentence_bounds(text):
        sentence = text[start:end].strip()
        if len(sentence) < 10:
            continue
        if _ADMIN_INTERP_RE.search(sentence) and _ADMIN_CONTEXT_RE.search(sentence):
            out.append(ClaimMatch(
                claim_type="UNVERIFIED_ADMIN_INTERPRETATION",
                sentence=sentence,
                start=start,
                judgment="행정해석·유권해석 공식 출처 미확인",
                grade="U",
                status="UNVERIFIED",
                basis=[],
                detail="행정기관의 유권해석·질의회신·법령해석 인용은 공식 원문 데이터베이스 대조가 완료되지 않아 미확인(UNVERIFIED)으로 표시한다.",
                extra={"defect_type": "SRC-UNV"},
            ))
    return out


def review_claims(doc: NormalizedDocument, *, lookup: Optional[HistoryLookup] = None,
                  provisions: Sequence[Dict[str, Any]] = (), skip_sentences: Iterable[str] = ()) -> List[Finding]:
    """문서의 법리 주장을 유형별로 검토한다. skip_sentences: 다른 규칙이 이미 판정한 문장(이중 판정 방지)."""
    reading = build_reading_text(doc)
    text = reading.text
    skip = {re.sub(r"\s+", "", s) for s in skip_sentences if s}
    primary_matches = (
        classify_claims(text, lookup)
        + requirement_mismatches(doc, provisions)
        + _provisional_relief_references(text)
    )
    primary_keys = {re.sub(r"\s+", "", m.sentence) for m in primary_matches}
    overclaims = [
        m for m in _clause_normalizer_overclaims(text)
        if re.sub(r"\s+", "", m.sentence) not in primary_keys
    ]
    matches = primary_matches + overclaims + _unverified_admin_interpretations(text)
    out, seen = [], set()
    for match in matches:
        sentence_key = re.sub(r"\s+", "", match.sentence)
        key = (match.claim_type, sentence_key)
        if (key in seen or (sentence_key in skip and match.claim_type != "STATUTORY_RULE_EXCLUSION")
                or (match.claim_type == "NO_BASIS_REMEDY" and any(
                    len(s) >= 20 and (s in sentence_key or sentence_key in s) for s in skip))):
            continue
        seen.add(key)
        out.append(_to_finding(doc, match, reading))
    return out


def provision_texts(verdicts: Sequence[Dict[str, Any]], citations: Sequence[Any]) -> List[Dict[str, Any]]:
    """법령 인용 판정에서 조회한 공식 조문 원문을 모은다(조문 요건 대조용)."""
    by_id = {getattr(c, "citation_id", None): c for c in citations}
    out: List[Dict[str, Any]] = []
    for verdict in verdicts:
        citation = by_id.get(verdict.get("citation_id"))
        provision = (verdict.get("review") or {}).get("provision") or {}
        if not citation or not provision.get("text") or not getattr(citation, "law_name", None):
            continue
        version = (verdict.get("review") or {}).get("version") or {}
        out.append({"law": law_name(citation.law_name), "article": str(citation.article or "").replace("조", ""),
                    "text": provision["text"], "version": version.get("version_id") or version.get("effective_from"),
                    "url": ((verdict.get("official_record") or {}).get("url") or "")})
    return out
