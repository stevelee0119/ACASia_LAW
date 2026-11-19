"""제11.1장 Claim Extraction, 제11.3장 Entity Resolution, 제11.4장 Timeline.

Rule 기반으로 먼저 구조화하고, 의미 판단이 필요한 부분만 LLM에 위임한다.
단순 의견(OPINION)은 사실 검증 대상에서 기본 제외한다.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Dict, List, Optional, Tuple

from packages.common.enums import ClaimType, EntityType
from packages.common.schemas import Claim, Citation, Entity, Event, NormalizedDocument
from packages.common.textutil import sentences

from packages.document_engine.meta_sections import meta_checklist_block_ids
from packages.pii_engine.detector import (
    COMPANY_STOPWORDS,
    LEGAL_MILITARY_STOPWORDS,
    MILITARY_NOUNS,
    PARTY_HEADER_STOPWORDS,
    REPRESENTATIVE_NAME_STOPWORDS,
    _CATEGORY_JOSA_TAIL_RE,
    _has_category_name_ambiguity,
    is_valid_korean_name_structure,
)
from packages.pii_engine.name_stopwords import PERSON_CATEGORY_STOPWORDS

from .calculation import parse_amounts
from .classification import (classify_sentence, document_kind, segment_kind, assertion_mode,
                             event_role, NOMINAL_FACT_RE, PAST_FACT_RE, OPINION_RE as EXPLICIT_OPINION_RE)
from .entity_resolution import resolve_entities
from .exhibits import parse_exhibits
from .structure import ACTION_PATTERNS, extract_evidence_references, structure_claim_text

# --- Claim 유형 판별 규칙 ----------------------------------------------------
OPINION_RE = re.compile(r"(생각한다|사료된다|보아야\s*한다|타당하다|부당하다|바람직하다|판단된다|여겨진다|믿는다)")
LEGAL_RULE_RE = re.compile(r"(제\s*\d+\s*조|법률\s*제\s*\d+\s*호|규정하고\s*있다|정하고\s*있다|따르면)")
# 판례 취지 서술: 경어체(판시하였습니다, 설시하였습니다 등) 포함
CASE_HOLDING_RE = re.compile(r"(판시하였다|판시한|판결하였다|설시하였다|입장이다|취지이다|보고\s*있다|판시하였습니다|판시했습니다|판결하였습니다|설시하였습니다)")
DOCUMENT_EXISTENCE_RE = re.compile(r"(갑\s*제?\s*\d+\s*호증|을\s*제?\s*\d+\s*호증|증\s*제?\s*\d+\s*호|첨부(?:한|된|하였습니다)|제출(?:한|하였다|하였습니다))")
CALCULATION_RE = re.compile(r"(합계|총액|이자|지연손해금|비율|%|원을\s*지급)")
INTERPRETATION_RE = re.compile(r"(해석된다|해석하여야|유권해석|법령해석)")
# 사실 서술: 평서문 및 경어체/존댓말 과거 완료 서술(체결하였습니다, 납품하였습니다, 공제하였습니다 등) 포함
FACT_RE = re.compile(
    r"(?:(?:였|었|았|했|됐)(?:다|습니다))|"
    r"(하였다|했다|이다|였다|당하였다|지급하였다|체결하였다|발생하였다|근무하였다|"
    r"하였습니다|했습니다|입니다|였습니다|이었습니다|되었습니다|됐습니다|공제하였습니다|납품하였습니다|"
    r"마무리되었습니다|종료되었습니다|확인되었습니다|통보하였습니다|협의하였습니다|요청하였습니다)"
)

DATE_RE = re.compile(
    r"(?P<y>(?:19|20)\d{2})\s*[.\-년]\s*(?P<m>\d{1,2})\s*[.\-월]\s*(?P<d>\d{1,2})\s*[일]?"
)
PARTIAL_DATE_RE = re.compile(r"(?<![\d가-힣])\d{1,2}\s*월\s*\d{1,2}\s*일(?![자])")
EVENT_KIND_RE = [
    ("CONTRACT", re.compile(r"(계약(?:을)?\s*체결|약정|합의)")),
    ("TERMINATION", re.compile(r"(해지|해제|종료|파기)")),
    ("PAYMENT", re.compile(r"(지급|송금|입금|변제)")),
    ("INCORPORATION", re.compile(r"(설립|법인등기|개업)")),
    ("FILING", re.compile(r"(제출|접수|신청|고소|고발|기소)")),
    ("DECISION", re.compile(r"(선고|판결|결정|처분)")),
    ("INCIDENT", re.compile(r"(사고|발생|폭행|상해|침해|위반)")),
]
_ADJACENT_DISQUALIFY_RE = re.compile(
    r"(?:"
    r"존재하지|제출되지|작성되지|교부되지|발행되지|첨부되지|미제출|미작성|미확인|"
    r"위조|변조|허위|거짓|무관|별개|해당하지|다투|부인|배척|신빙성|인정할\s*수\s*없|단정할\s*수\s*없|"
    r"불명|다르다|다름|아니다|아니라|추정|가능성|여부|인지|"
    r"그러나|다만|하지만|반면|한편|그런데|오히려|달리|또는|혹은|"
    r"위\s*(?:각|두|세|여러|모든)\s*(?:사건|사실|행위|날짜)|앞선\s*사건|여러\s*사건|각\s*사건|어느\s*사건|모든\s*사건|전후\s*사건"
    r")"
)
_ADJACENT_SUBJECT_RE = re.compile(
    r"(?:원고|피고|피고인|상대방|신청인|피신청인|채권자|채무자|공급자|구매자|증인|참고인|당사자|소외|고소인|고발인)"
    r"(?:\s+[가-힣]{2,4})?(?:은|는|이|가)\b"
)
_ADJACENT_ROLE_RE = re.compile(
    r"(?:원고|피고|피고인|상대방|신청인|피신청인|채권자|채무자|공급자|구매자|"
    r"증인|참고인|당사자|소외|고소인|고발인|대리인|임대인|임차인|매도인|매수인|"
    r"수급인|도급인|발주자|시공사|위탁사|피의자|망)(?!신문조서)"
)
_ADJACENT_ORG_RE = re.compile(
    r"(?:주식회사|유한회사|합자회사|합명회사|재단법인|사단법인|학교법인|의료법인|법인|"
    r"\(주\)|㈜|\(유\)|유한책임회사|"
    r"[가-힣]{1,10}(?:회사|상사|은행|공사|공단|협회|병원|학교|학원|구청|시청|경찰서|검찰청|법원|위원회|재단|조합))\b"
)
_ADJACENT_ATTRIBUTION_WORDS_RE = re.compile(
    r"(?:명의의|측의|소유|귀속|작성명의|제출명의|보관명의|발행명의)"
)
_ADJACENT_POSSESSIVE_RE = re.compile(
    r"(?<![가-힣])의\b|[가-힣]+의(?:\s|[.,()\[\]{}:;/\-~–·'\"“”‘’「」『』【】]|$)"
)
_ALLOWED_UI_NOUN_STEMS = {"합", "결", "동", "협", "질", "이", "정", "명", "품", "건", "소", "주"}

_ADJACENT_CASE_PARTICLE_START_RE = re.compile(
    r"^\s*(?:[은는이가을를]|으로|에는|에도|에서|에게|과의|와의|만으로는|만으로)\b"
)
_ADJACENT_PARTICLE_RE = re.compile(
    r"(?:에서|에게|한테|으로|로써|로서|와의|과의|에는|에도|만을|만을위한|만으로는|만으로)\b|"
    r"[가-힣]{2,15}(?:은|는|이|가|을|를)\b"
)

_ADJACENT_ACTION_PREDICATE_RE = re.compile(
    r"(?:보관|소지|작성|날인|제출|교부|송부|수령|보유|은닉|폐기|인도|발급|위임|체결|"
    r"송금|입금|지급|발송|촬영|회신|청구|통지|통보|반환|변제|공제|요청|진술|설명|주장|"
    r"선고|판결|기소|고소|고발|신청|접수)(?:\s*[.!?。]|\s*$)"
)
_ACTION_WORDS = {
    "보관", "소지", "작성", "날인", "제출", "교부", "송부", "수령", "보유", "은닉",
    "폐기", "인도", "발급", "위임", "체결", "송금", "입금", "지급", "발송", "촬영",
    "회신", "청구", "통지", "통보", "반환", "변제", "공제", "요청", "진술", "설명",
    "주장", "선고", "판결", "기소", "고소", "고발", "신청", "접수",
}
_ADJACENT_FINITE_END_RE = re.compile(
    r"(?:하였다|했다|되었다|됐다|였다|었다|았다|이다|하다|되다|한다|된다|있다|없다|않다|니다|습니다|시오|까요|겠다)\s*[.!?。]?$"
)
_ADJACENT_VERB_STEM_RE = re.compile(
    r"(?:하|되|받|보내|주|쓰|만들)(?:였|었|았|다|고|며|면서|지만|으나|므로|는데|니|면|여)"
)
_ADJACENT_ATTACHMENT_RE = re.compile(
    r"(?:별첨|별지|첨부)\s*제?\s*\d+\s*호?(?:\s*의\s*\d+)*"
    r"(?:\s*[,\(]?\s*(?:제\s*|[pP]\.\s*)?\d+(?:\s*[~～\-–]\s*\d+)?\s*(?:쪽|면|페이지|[pP](?![A-Za-z]))\s*\)?)?"
)

_INDICATOR_TOKENS = {
    "및", "내지", "외", "등", "각", "참조", "첨부", "호증", "호", "건", "부", "매",
    "장", "쪽", "면", "페이지", "p", "P", "pp", "PP",
}
_DOCUMENT_NOUN_SUFFIXES = (
    "서", "표", "증", "장", "록", "문", "지", "도", "면", "본",
    "첩", "철", "권", "사본", "출력물", "캡처", "파일", "사진",
    "영상", "녹음", "녹취", "자료", "내역", "목록", "명세", "조서",
)
_DOCUMENT_NOUNS = {
    "내용증명", "문자", "메시지", "이메일", "메일", "카카오톡", "카톡",
    "약정", "계약", "영수증", "공정표", "도면", "사진", "일지", "장부",
    "전표", "세금계산서", "통장사본", "통화녹음", "녹취록", "보고서", "견적서",
}
_ALLOWED_TITLE_MODIFIERS = {
    "수정", "최종", "초안", "변경", "추가", "보완", "임시", "공식", "표준", "약식",
    "현장", "물품", "부동산", "토지", "건물", "차량", "거래", "정산", "매매", "임대차",
    "도급", "근로", "고용", "합의", "확약", "세금", "공정", "검수", "측량", "촬영",
    "발주", "문의", "제안", "회의", "상세", "요약", "관련", "별첨", "별지", "사본",
    "원본", "출력", "출력물", "화면", "캡처", "사진", "도면", "녹음", "녹취", "동영상",
    "영상", "파일", "명세", "내역", "목록", "정본", "등본", "초본", "계약서", "계약",
}

PARTY_ROLE_WORDS = {
    "원고", "피고", "피고인", "참고인", "피의자", "증인", "고소인", "고발인",
    "신청인", "피신청인", "채권자", "채무자", "소외", "망",
}
ORG_WORDS = {"주식회사", "유한회사", "합자회사", "재단법인", "사단법인", "법인"}

# 당사자 표기 바로 뒤에 올 수 있으나 사람 이름이 아닌 토큰.
# 조사가 그대로 이름으로 잡히면 "피고는 원고에게" 에서 '에게'가 PERSON이 된다.
NON_NAME_TOKENS = {
    # 조사·어미
    "에게", "에게서", "으로", "에서", "부터", "까지", "에는", "에도", "라고", "이라",
    "한테", "께서", "께는", "이며", "이고", "라는", "이라는",
    # 당사자 표기 뒤에 흔히 오는 일반명사
    "제출", "주장", "진술", "청구", "답변", "준비", "서면", "대리", "본인", "측은", "측이",
    "소송", "대리인", "당사자", "사건", "회사", "법인", "명의", "프로젝트", "계약", "합의",
    "이행", "손해", "배상", "지급", "반환", "확인", "신청", "요청", "통지", "최고",
}

_PERSON_STOPWORDS = (
    NON_NAME_TOKENS
    | PARTY_ROLE_WORDS
    | PARTY_HEADER_STOPWORDS
    | REPRESENTATIVE_NAME_STOPWORDS
    | PERSON_CATEGORY_STOPWORDS
    # 개인정보 엔진과 같은 직책·처분·계약 명사 목록을 쓴다(P2-1②). 성씨로 시작하는
    # 직책 명사('사단장' 등)는 성씨 체계 검사만으로는 걸러지지 않는다.
    | LEGAL_MILITARY_STOPWORDS
    | set(MILITARY_NOUNS)
    | {
        "측", "원고측", "피고측", "상대측", "회사측",
        "대한", "관한", "의한", "위한", "따른", "인한", "같은", "다른",
        "있는", "없는", "하는", "되는", "하여", "되어", "위해", "대해",
        "관해", "따라", "인해", "영위", "대법원", "고등법원", "지방법원",
        "헌법재판소", "법원", "재판부", "당해", "해당", "관련", "본건", "이건",
        "각", "위",
    }
)

_NON_NAME_VERB_ADNOMINAL_SUFFIXES = (
    "하는", "되는", "있는", "없는", "한다", "된다", "했다", "됐다", "였다", "이다",
    "하며", "되며", "하고", "되고", "하여", "되어", "하지", "되지", "하다", "되다",
)

COMPANY_MODIFIER_STOPWORDS = PARTY_ROLE_WORDS | ORG_WORDS | COMPANY_STOPWORDS | {
    "민간", "국영", "공영", "공공", "일반", "기존", "신규", "당해", "해당", "관련", "특정",
    "외국", "국내", "해외", "대형", "중소", "주요", "영리", "비영리", "선정", "협력", "하도급",
    "모회사", "자회사", "계열", "관계", "모든", "다른", "어느", "각", "본", "위", "동",
    "원고측", "피고측", "상대방", "제3자", "특수목적", "유가증권", "비상장", "상장",
}
_COMPANY_MODIFIER_VERB_SUFFIXES = (
    "하는", "되는", "있는", "없는", "한다", "된다",
    "하였고", "하였으며", "하였고서", "했고", "됐고", "았고", "었고", "였고",
    "하고", "하며", "되며", "이고", "이며", "하거나", "되거나", "이므로", "하므로",
    "했으나", "했지만", "하였으나", "하여", "되어", "위한", "대한", "관한", "따른", "의한", "인한", "통한",
    "계약한", "체결한", "관련된", "선정된", "설립된", "지정된", "운영하는", "영위하는",
)
_AFTER_COMPANY_WORD_RE = re.compile(r"\s+([가-힣A-Za-z0-9]{1,20})")
_ORG_MARKER_RE = re.compile(r"(?:주식회사|㈜)")
# 복합 조사를 먼저 본다('…상사로부터'의 '로부터'를 떼지 못하면 조사가 법인명에 남아
# 같은 법인이 두 엔티티로 갈린다). 대안 순서가 곧 우선순위다.
_COMPANY_JOSA_TAIL_RE = re.compile(
    r"(?:으로부터|로부터|에게서|으로|에서|에게|과의|와의|은|는|이|가|을|를|과|와|에|의|도)$")


def _strip_company_josa(name: str) -> str:
    cleaned = (name or "").strip()
    m = _COMPANY_JOSA_TAIL_RE.search(cleaned)
    if m and m.start() >= 2:
        return cleaned[:m.start()]
    return cleaned


# 당사자 표기 뒤의 이름. 뒤에 법인 표시가 오면 사람 이름이 아니다.
# 이름 뒤 조사는 선택이 아니라 '조사 또는 경계'로 못박는다.
PERSON_CONTEXT_RE = re.compile(
    r"(?:원고|피고인|피고|참고인|피의자|증인|고소인|고발인|신청인|피신청인|채권자|채무자|망|소외)\s*"
    r"(?!주식회사|유한회사|합자회사|재단법인|사단법인)"
    r"([가-힣]{2,4}?)(?:은|는|이|가|을|를|과|와|의|에게|에|도)?(?![가-힣])"
)


def is_person_name(token: str, *, full_token: str = "", after_text: str = "") -> bool:
    """당사자 표기 뒤에 잡힌 토큰이 사람 이름일 수 있는지 본다.

    개인정보 엔진의 `is_valid_korean_name_structure`를 그대로 쓴다(P2-1②). 두 엔진이 같은
    이름 구조 규칙을 쓰므로, 개인정보 엔진이 성명으로 보지 않는 토큰은 여기서도 엔티티가 되지 않는다.
    """
    name = (token or "").strip()
    if len(name) < 2 or len(name) > 4:
        return False
    if not all("\uac00" <= ch <= "\ud7a3" for ch in name):
        return False
    if full_token:
        ft = full_token.strip()
        if ft.endswith(_NON_NAME_VERB_ADNOMINAL_SUFFIXES):
            return False
        if ft.endswith(("한", "된", "할", "될")) and ft[:-1] in _PERSON_STOPWORDS:
            return False
    if name in _PERSON_STOPWORDS:
        return False
    if name.startswith("측") or name.endswith("측"):
        return False
    if name.endswith(_NON_NAME_VERB_ADNOMINAL_SUFFIXES):
        return False
    # 조사만으로 이루어진 토큰은 이름이 아니다
    if all(ch in "은는이가을를과와의에도로서만며고" for ch in name):
        return False
    particle = _CATEGORY_JOSA_TAIL_RE.search(name)
    if particle is not None:
        stem = name[:particle.start()]
        if stem in _PERSON_STOPWORDS and not _has_category_name_ambiguity(name):
            return False
    # PERSON_CONTEXT_RE는 '원고·피고·증인·소외' 등 명시적 당사자 표기 직후만 잡으므로
    # 명시적 라벨로 본다(후행 문맥으로 정상 성명을 지우지 않는다, TK-39와 같은 취급).
    if not is_valid_korean_name_structure(name, after_text, is_explicit_label=True):
        return False
    return True


def _is_company_modifier_stopword(token: str) -> bool:
    name = (token or "").strip()
    if not name or name in COMPANY_MODIFIER_STOPWORDS:
        return True
    if name.endswith(_COMPANY_MODIFIER_VERB_SUFFIXES):
        return True
    particle = _CATEGORY_JOSA_TAIL_RE.search(name)
    if particle is not None and name[:particle.start()] in COMPANY_MODIFIER_STOPWORDS:
        return True
    return False


COMPANY_CONTEXT_RE = re.compile(
    r"(?<![가-힣])([가-힣A-Za-z0-9]{2,10})\s*(?:주식회사|㈜)|(?:주식회사|㈜)\s+([가-힣A-Za-z0-9]{1,20})"
)
COURT_CONTEXT_RE = re.compile(r"([가-힣]{2,10}(?:지방|고등|가정|행정|회생|특허|군사)?법원|대법원|헌법재판소)")


def classify_claim(sentence: str) -> ClaimType:
    if assertion_mode(sentence) in ("HYPOTHETICAL", "ALTERNATIVE", "QUOTED_OTHER"):
        return ClaimType.OPINION
    if OPINION_RE.search(sentence) or EXPLICIT_OPINION_RE.search(sentence):
        return ClaimType.OPINION
    if CASE_HOLDING_RE.search(sentence):
        return ClaimType.CASE_HOLDING
    if INTERPRETATION_RE.search(sentence):
        return ClaimType.LEGAL_INTERPRETATION
    if LEGAL_RULE_RE.search(sentence):
        return ClaimType.LEGAL_RULE
    if DOCUMENT_EXISTENCE_RE.search(sentence):
        return ClaimType.DOCUMENT_EXISTENCE
    if CALCULATION_RE.search(sentence) and parse_amounts(sentence):
        return ClaimType.CALCULATION
    if FACT_RE.search(sentence) or NOMINAL_FACT_RE.search(sentence):
        return ClaimType.FACT
    return ClaimType.OPINION


def partial_date_candidates(sentence, block_text):
    """Keep omitted years as contextual candidates, never confirmed event dates."""
    full = [m.span() for m in DATE_RE.finditer(sentence)]
    years = sorted({int(m["y"]) for m in DATE_RE.finditer(block_text)})
    candidates = []
    for match in re.finditer(r"(?<![\d.])(?P<m>\d{1,2})\s*[.월]\s*(?P<d>\d{1,2})\s*[.일]", sentence):
        if any(start <= match.start() < end for start, end in full):
            continue
        values = []
        for year in years:
            try:
                values.append(date(year, int(match["m"]), int(match["d"])).isoformat())
            except ValueError:
                continue
        candidates.append({"raw_text": match.group(), "span": list(match.span()), "candidate_dates": values,
            "status": "CONTEXT_CANDIDATE" if len(values) == 1 else "UNRESOLVED",
            "basis": "SAME_BLOCK_EXPLICIT_YEARS", "confirmed": False})
    return candidates


def extract_claims(doc: NormalizedDocument, citations: Optional[List[Citation]] = None,
                   *, project_id: Optional[str] = None, source_run_id: Optional[str] = None) -> List[Claim]:
    """표시 본문에서 Claim을 추출한다."""
    citations = citations or []
    by_block: Dict[str, List[Citation]] = {}
    for citation in citations:
        if citation.block_id:
            by_block.setdefault(citation.block_id, []).append(citation)

    claims: List[Claim] = []
    meta_ids = meta_checklist_block_ids(doc)
    kind = document_kind(b.text for b in doc.prose_blocks()[:8])
    for block in doc.prose_blocks():
        in_meta = block.block_id in meta_ids
        cursor = 0
        for sentence in sentences(block.text):
            start = block.text.find(sentence, cursor)
            if start < 0:
                continue
            cursor = start + len(sentence)
            if len(sentence) < 10:
                continue
            segment = (
                "DOCUMENT_GUIDE"
                if in_meta
                else segment_kind(sentence, block_type=block.block_type, source_layer=block.source_layer,
                                  table_ref=block.attributes.get("table_ref"))
            )
            claim_type = classify_sentence(sentence, segment, classify_claim)
            related = [
                c.citation_id
                for c in by_block.get(block.block_id, [])
                if c.raw_text and c.raw_text[:12] in sentence
            ]
            claims.append(
                Claim.create(
                    claim_type,
                    sentence,
                    document_id=doc.document_id,
                    block_id=block.block_id,
                    page=block.page,
                    citation_ids=related,
                    attributes={"length": len(sentence), "extraction_method": "LEXICAL_RULES",
                                "evidence_relationship": "UNASSESSED",
                                # 제목·안내·인용·OCR·표 구간을 본문과 구분해 남긴다.
                                "segment_kind": segment, "document_kind": kind,
                                "assertion_mode": assertion_mode(sentence), "event_role": event_role(sentence),
                                "partial_date_candidates": partial_date_candidates(sentence, block.text),
                                "classification_status": ("UNCLASSIFIED" if claim_type == ClaimType.OPINION
                                    and assertion_mode(sentence) == "ASSERTED"
                                    and not (OPINION_RE.search(sentence) or EXPLICIT_OPINION_RE.search(sentence))
                                    else "CLASSIFIED"),
                                "verification_target": claim_type not in (
                                    ClaimType.DOCUMENT_META, ClaimType.ADVERSARIAL_INSTRUCTION)},
                    project_id=project_id or doc.metadata.get("project_id"),
                    source_run_id=source_run_id,
                    source_document_sha256=doc.sha256,
                    span=(start, cursor),
                    evidence_references=extract_evidence_references(
                        sentence, document_id=doc.document_id, block_id=block.block_id,
                        page=block.page, source_run_id=source_run_id,
                        document_sha256=doc.sha256, offset=start),
                    **structure_claim_text(sentence),
                )
            )
    return claims


def extract_entities(doc: NormalizedDocument, *, project_id: Optional[str] = None) -> List[Entity]:
    """사람·법인·법원 등을 추출한다. 동일 대상 통합은 resolve_entities가 담당한다."""
    found: Dict[Tuple[str, str], Entity] = {}
    meta_ids = meta_checklist_block_ids(doc)

    def add(entity_type: EntityType, name: str, block, span: Tuple[int, int]) -> None:
        name = name.strip()
        if not name:
            return
        key = (str(entity_type), name)
        entity = found.get(key)
        if entity is None:
            entity = Entity.create(entity_type, name, project_id=project_id or doc.metadata.get("project_id"),
                                   needs_user_confirmation=True, resolution_basis="DOCUMENT_MENTIONS_ONLY")
            found[key] = entity
        entity.mentions.append(
            {"document_id": doc.document_id, "block_id": block.block_id, "page": block.page, "span": list(span)}
        )

    for block in doc.prose_blocks():
        if block.block_id in meta_ids:
            continue
        for m in PERSON_CONTEXT_RE.finditer(block.text):
            if not is_person_name(m.group(1), full_token=block.text[m.start(1):m.end()],
                                  after_text=block.text[m.end():m.end() + 20]):
                continue
            add(EntityType.PERSON, m.group(1), block, (m.start(1), m.end(1)))
        for m in COMPANY_CONTEXT_RE.finditer(block.text):
            if m.group(1) is not None:
                name = m.group(1).strip()
                if _is_company_modifier_stopword(name):
                    after = _AFTER_COMPANY_WORD_RE.match(block.text, m.end())
                    if after:
                        after_name = _strip_company_josa(after.group(1))
                        if not _is_company_modifier_stopword(after_name):
                            org_match = _ORG_MARKER_RE.search(m.group(0))
                            span_start = m.start() + (org_match.start() if org_match else 0)
                            add(EntityType.COMPANY, after_name, block, (span_start, after.end()))
                    continue
                add(EntityType.COMPANY, name, block, (m.start(), m.end()))
            else:
                name = _strip_company_josa(m.group(2) or "")
                if _is_company_modifier_stopword(name):
                    continue
                add(EntityType.COMPANY, name, block, (m.start(), m.end()))
        for m in COURT_CONTEXT_RE.finditer(block.text):
            add(EntityType.COURT, m.group(1), block, (m.start(1), m.end(1)))
        for amount in parse_amounts(block.text, block_id=block.block_id, page=block.page):
            add(EntityType.MONEY, amount.raw, block, (amount.start, amount.end))
    return list(found.values())


_PRECEDENT_COURT_CUE_RE = re.compile(
    # 종류어 앞 수식어는 선택이다. 앞에 지명이 붙지 않는 이름도 받는다.
    r"(?:대법원|헌법재판소|전원합의체|[가-힣]{0,10}(?:지방|고등|가정|행정|회생|특허|군사)법원)"
)
_PRECEDENT_AFTER_RE = re.compile(
    r"^\s*\.?\s*(?:(?:선고|자)\s*(?:전원재판부\s*|전원합의체\s*)?\d{2,4}[가-힣]{1,4}\d+|"
    r"(?:전원합의체\s*)?\d{2,4}[가-힣]{1,4}\d+\s*(?:전원재판부\s*)?(?:판결|결정|명령))"
)
_PRECEDENT_AFTER_GENERIC_RE = re.compile(
    r"^\s*\.?\s*자?\s*(?:(?:전원합의체|전원재판부)\s*)?(?:"
    r"(?:판결|결정|명령)[가-힣]*|"
    r"(?:선고|판시|설시|판단|결정)\s*[하한할함합해했되된될됨됩돼][가-힣]*"
    r")"
)
_INSTANT_CASE_COURT_RE = re.compile(
    r"이\s*사건\s*(?:원심|제?1심|제?2심|항소심|상고심|소송|사건)"
)
_CASE_CITATION_NUM_RE = re.compile(r"\d{2,4}[가-힣]{1,4}\d+")
_STATUTE_AFTER_ACTION_RE = re.compile(
    r"^\s*\.?\s*(?:(?:,|·)\s*)?(?:(?:자\s*)?(?:법률|대통령령|총리령|부령|시행령|시행규칙|조례)(?:\s*제\s*\d+\s*호|\s*(?:일부|전부)?\s*개정|\s*제정|\s*공포|\s*시행|로|으로|,)|"
    r"(?:일부\s*개정|전부\s*개정|제정|개정|신설|삭제|공포)(?:된|되어|한|으로|법|조항)?)"
)
_STATUTE_EFFECTIVE_RE = re.compile(
    r"^\s*\.?\s*(?:부터\s*)?(?:개정(?:되|된|되었)|공포(?:되|된|되었)|시행(?:하|일|되|된|되었)?)"
)
_STATUTE_CUE_RE = re.compile(
    r"(?:법률\s*제\s*\d+\s*호|대통령령\s*제\s*\d+\s*호|총리령\s*제\s*\d+\s*호|부령\s*제\s*\d+\s*호|"
    r"[가-힣]+(?:법률|법령|법|시행령|시행규칙|부칙|조례|규칙|훈령|예규|고시)|"
    r"(?<![가-힣])(?:법률|법령|대통령령|총리령|부령|시행령|시행규칙|부칙|조례|훈령|예규)|"
    r"(?:이|그|해당|동|위|개정|현행|구)\s*(?:법|규칙)|"
    r"제\s*\d+\s*조)"
)
_PARTY_FACT_VERB_RE = re.compile(
    r"(?:체결|약정|합의|지급|송금|입금|변제|교부|설립|개업|접수|제출|신청|고소|고발|기소|"
    r"해지|해제|종료|파기|통지|통보|발송|수령|근무|입사|퇴직|퇴사|사망|출생|사고|발생|"
    r"폭행|상해|침해|납품|인도|"
    # 당사자 행위·채무 상태 표지 추가분. 설계 메모가 열거한 '당사자 행위 … 지체'를 포함하고,
    # 법령·판례를 근거로 들며 당사자가 행위한 문장이 사건에서 탈락하지 않게 한다.
    # 판단 주체가 법원인 동사(선고·판결·결정·처분)는 넣지 않는다.
    r"청구|지체|이행|반환|최고|독촉|공탁)"
)
_PARTY_SUBJECT_CUE_RE = re.compile(
    r"(?<![가-힣])(?:"
    r"(?:원고|피고|피고인|신청인|피신청인|채권자|채무자|청구인|피청구인|항고인|상고인|"
    r"고소인|고발인|피의자|피해자|상대방|당사자|소외|망|임대인|임차인|매도인|매수인|"
    r"도급인|수급인|사용자|근로자|처분청|과세관청|관할청|피심인|소외인)"
    r"(?:\s+[가-힣A-Za-z0-9()㈜]{1,12})?\s*(?:측)?(?:은|는|이|가|도|에게|에\s*대하여)(?![가-힣])"
    r"|"
    r"이\s*사건\s*(?:처분|부과|과세|계약|소|소송|청구|사고|합의|결의|해고|명령|통지)"
    r")"
)
_PARTY_PAST_PREDICATE_RE = re.compile(
    r"(?:하였|되었|받았|보냈|내렸|올렸|마쳤|거쳤|두었|주었|왔|갔|냈|쳤|웠|졌|렸|겼|녔|셨|였|었|았|했|됐)"
    r"(?:다|습니다|음|고|으며|며|으나|지만)(?![가-힣])"
)


# 행위 주체 판정용. 주격 조사만 받는다(에게·에 대하여는 목적어·부사어이므로 주체가 아니다).
_PARTY_NOMINATIVE_CUE_RE = re.compile(
    r"(?<![가-힣])(?:"
    r"(?:원고|피고|피고인|신청인|피신청인|채권자|채무자|청구인|피청구인|항고인|상고인|"
    r"고소인|고발인|피의자|피해자|상대방|당사자|소외|망|임대인|임차인|매도인|매수인|"
    r"도급인|수급인|사용자|근로자|처분청|과세관청|관할청|피심인|소외인)"
    r"(?:\s+[가-힣A-Za-z0-9()㈜]{1,12})?\s*(?:측)?(?:은|는|이|가)(?![가-힣])"
    r")"
)
# 주격과 날짜 사이에 서술어가 있으면 그 주격은 내포절의 것이다.
_EMBEDDED_PREDICATE_RE = re.compile(
    # 인용·간접화법 어미. 어간을 열거하지 않고 어미만 본다.
    r"(?:다고|라고|냐고|자고|다며|다는|라며|느냐고)(?![가-힣])"
    # 관형형이 뒤 명사를 꾸미는 꼴(주격이 그 명사절 안에 있다는 표지)
    r"|[가-힣](?:한|던|는|된)\s"
)


def _is_legal_authority_date(sentence: str, match_start: int, match_end: int) -> bool:
    """판례 선고·결정일 또는 법령 제정·개정·시행일 등 법적 근거 날짜인지 판별한다."""
    before = sentence[max(0, match_start - 35):match_start]
    after = sentence[match_end:]

    # 1) 판례/헌재 결정 인용 날짜 ("대법원 2021. 5. 13. 선고 2020다12345 판결", "2019. 7. 18.자 2018헌마100")
    if _PRECEDENT_AFTER_RE.match(after):
        return True
    if _PRECEDENT_COURT_CUE_RE.search(before) and _PRECEDENT_AFTER_GENERIC_RE.match(after):
        if _INSTANT_CASE_COURT_RE.search(before) and not _CASE_CITATION_NUM_RE.search(after[:30]):
            return False
        court_last = max((m.end() for m in _PRECEDENT_COURT_CUE_RE.finditer(before)), default=0)
        tail = before[court_last:]
        party = None
        for m in _PARTY_NOMINATIVE_CUE_RE.finditer(tail):
            party = m
        if party is not None and not _EMBEDDED_PREDICATE_RE.search(tail[party.end():]):
            return False
        return True

    # 2) 법령 제정·개정·공포·시행 날짜
    if _STATUTE_AFTER_ACTION_RE.match(after):
        return True
    if _STATUTE_CUE_RE.search(before) and _STATUTE_EFFECTIVE_RE.match(after):
        return True

    return False


def _has_party_fact_cue(sentence: str) -> bool:
    """문장에 당사자 사이의 구체적 사건·행위 표지가 있는지 본다."""
    if any(regex.search(sentence) for name, regex in EVENT_KIND_RE if name != "DECISION"):
        return True
    if _PARTY_FACT_VERB_RE.search(sentence):
        return True
    if _PARTY_SUBJECT_CUE_RE.search(sentence) and (
        PAST_FACT_RE.search(sentence)
        or NOMINAL_FACT_RE.search(sentence)
        or _PARTY_PAST_PREDICATE_RE.search(sentence)
    ):
        return True
    return False

def _collect_event_evidence_references(
    sentence: str, *, document_id: str, block_id: str, page: Optional[int],
    source_run_id: Optional[str], document_sha256: str, offset: int,
    include_attachments: bool = False,
) -> List[dict]:
    """사건/인접 문장에서 호증 참조를 수집하되 원문 span을 보존한다."""
    refs = extract_evidence_references(
        sentence, document_id=document_id, block_id=block_id,
        page=page, source_run_id=source_run_id,
        document_sha256=document_sha256, offset=offset,
    )
    by_span: Dict[Tuple[int, int], List[dict]] = {}
    for item in parse_exhibits(sentence):
        by_span.setdefault(tuple(item["span"]), []).append(item)

    merged: List[dict] = list(refs)
    for (s0, s1), items in sorted(by_span.items()):
        abs_span = [offset + s0, offset + s1]
        overlapping = [
            r for r in merged
            if not (r["span"][1] <= abs_span[0] or r["span"][0] >= abs_span[1])
        ]
        # extract_evidence_references가 쪽 범위까지 이미 넓게 잡았으면 유지하고,
        # 복수/가지번호/특수 당사자(소갑·을가·증 등)로 parse_exhibits가 더 넓거나 유일하게 잡았을 때 반영한다.
        if overlapping and all((r["span"][1] - r["span"][0]) >= (s1 - s0) for r in overlapping):
            continue
        merged = [r for r in merged if r not in overlapping]
        first_ex = items[0]
        branches = [b for item in items for b in (item.get("branches") or [])]
        merged.append({
            "key": ":".join([first_ex["party"], str(first_ex["number"]), *map(str, branches)]),
            "raw_text": sentence[s0:s1],
            "side": first_ex["party"],
            "attachment": None,
            "number": first_ex["number"],
            "branches": branches,
            "page_start": None,
            "page_end": None,
            "parse_status": "PARSED",
            "document_id": document_id,
            "block_id": block_id,
            "page": page,
            "source_run_id": source_run_id,
            "document_sha256": document_sha256,
            "span": abs_span,
        })

    if include_attachments:
        for m in _ADJACENT_ATTACHMENT_RE.finditer(sentence):
            abs_span = [offset + m.start(), offset + m.end()]
            if any(not (r["span"][1] <= abs_span[0] or r["span"][0] >= abs_span[1]) for r in merged):
                continue
            merged.append({
                "key": "",
                "raw_text": sentence[m.start():m.end()],
                "side": None,
                "attachment": m.group(0),
                "number": None,
                "branches": [],
                "page_start": None,
                "page_end": None,
                "parse_status": "PARSED",
                "document_id": document_id,
                "block_id": block_id,
                "page": page,
                "source_run_id": source_run_id,
                "document_sha256": document_sha256,
                "span": abs_span,
            })

    merged.sort(key=lambda r: (r["span"][0], r["span"][1]))
    return merged


def _can_event_bind_adjacent(date_count: int, structure: dict) -> bool:
    """단일 확정 사건 문장만 바로 뒤 인접 호증 구절을 연결할 수 있다."""
    if date_count != 1:
        return False
    if structure.get("stance") != "ASSERTED":
        return False
    if any(structure.get(flag) for flag in ("negated", "hearsay", "quoted", "conditional", "alternative")):
        return False
    return True


def _is_allowed_evidence_residual(residual: str) -> bool:
    """호증 참조 제거 후 잔여 구절이 허용된 증거 제목/표지 문법에 맞는지 엄격히 판정한다."""
    if not residual:
        return True
    if ":" in residual or "：" in residual:
        return False
    if _ADJACENT_DISQUALIFY_RE.search(residual):
        return False
    if _ADJACENT_ROLE_RE.search(residual):
        return False
    if _ADJACENT_ORG_RE.search(residual):
        return False
    if _ADJACENT_ATTRIBUTION_WORDS_RE.search(residual):
        return False
    for match in _ADJACENT_POSSESSIVE_RE.finditer(residual):
        word = match.group(0).strip(" .,()[]{}:;/-~–·'\"“”‘’「」『』【】")
        if word == "의":
            return False
        if word.endswith("의"):
            stem = word[:-1]
            if stem not in _ALLOWED_UI_NOUN_STEMS:
                return False
    if _ADJACENT_CASE_PARTICLE_START_RE.search(residual):
        return False
    if _ADJACENT_PARTICLE_RE.search(residual):
        return False
    if _ADJACENT_ACTION_PREDICATE_RE.search(residual):
        return False
    if _ADJACENT_FINITE_END_RE.search(residual) or _ADJACENT_VERB_STEM_RE.search(residual):
        return False
    if any(pat.search(residual) for _, pat in ACTION_PATTERNS):
        return False

    tokens = [t.strip() for t in re.split(r"[\s.,()\[\]{}:;/\-~–·'\"“”‘’「」『』【】]+", residual) if t.strip()]
    if not tokens:
        return True

    title_tokens = []
    for t in tokens:
        if t in _INDICATOR_TOKENS or re.match(r"^\d+(?:건|부|매|장|쪽|면|호)?$", t):
            continue
        title_tokens.append(t)

    if not title_tokens:
        return True

    if len(title_tokens) > 4:
        return False
    if sum(len(t) for t in title_tokens) > 30:
        return False

    for t in title_tokens:
        if not re.match(r"^[가-힣A-Za-z0-9]+$", t):
            return False
        if t in _ACTION_WORDS:
            return False

    if len(title_tokens) > 1:
        for mod in title_tokens[:-1]:
            if mod not in _ALLOWED_TITLE_MODIFIERS:
                return False

    last_token = title_tokens[-1]
    ends_with_doc_suffix = any(last_token.endswith(sfx) for sfx in _DOCUMENT_NOUN_SUFFIXES)
    is_doc_noun = last_token in _DOCUMENT_NOUNS
    if not (ends_with_doc_suffix or is_doc_noun):
        return False

    return True


def _adjacent_evidence_refs(
    next_sentence: str, *, document_id: str, block_id: str, page: Optional[int],
    source_run_id: Optional[str], document_sha256: str, offset: int,
) -> Optional[List[dict]]:
    """바로 뒤 문장이 새 사건/부정/전언/가정/주체/모호함 없는 호증 전용 구절일 때만 참조를 반환한다."""
    if not next_sentence or DATE_RE.search(next_sentence) or PARTIAL_DATE_RE.search(next_sentence):
        return None
    if ":" in next_sentence or "：" in next_sentence:
        return None
    refs = _collect_event_evidence_references(
        next_sentence, document_id=document_id, block_id=block_id,
        page=page, source_run_id=source_run_id,
        document_sha256=document_sha256, offset=offset,
        include_attachments=True,
    )
    if not refs or any(r.get("parse_status") != "PARSED" for r in refs):
        return None

    next_struct = structure_claim_text(next_sentence)
    if any(next_struct.get(flag) for flag in ("negated", "hearsay", "conditional", "alternative")):
        return None
    if next_struct.get("stance") in ("DENIED", "REPORTED", "CONDITIONAL", "ALTERNATIVE", "UNKNOWN", "AMBIGUOUS"):
        return None
    if _ADJACENT_DISQUALIFY_RE.search(next_sentence):
        return None

    # 호증 참조 구간을 제거한 나머지 문구에서 새 서술·주체·조사 경계를 점검한다.
    chars = list(next_sentence)
    for ref in refs:
        rel_start = max(0, ref["span"][0] - offset)
        rel_end = min(len(chars), ref["span"][1] - offset)
        for idx in range(rel_start, rel_end):
            chars[idx] = " "
    residual = " ".join("".join(chars).split())

    if not _is_allowed_evidence_residual(residual):
        return None
    compact_residual = re.sub(r"[\s.,()\[\]{}:;/\-~–·'\"“”‘’「」『』【】]", "", residual)
    if len(compact_residual) > 40:
        return None
    return refs


def extract_events(doc: NormalizedDocument, *, project_id: Optional[str] = None,
                   source_run_id: Optional[str] = None) -> List[Event]:
    """제11.4장 Timeline 입력. 판례·법령 인용 날짜를 걸러내고 사건 사실관계를 중심으로 추출하며,
    날짜와 같은 문장 또는 바로 뒤 인접 호증 구절의 근거를 결합한다."""
    events: List[Event] = []
    meta_ids = meta_checklist_block_ids(doc)
    for block in doc.prose_blocks():
        if block.block_id in meta_ids:
            continue
        sent_spans: List[Tuple[str, int, int]] = []
        cursor = 0
        for sentence in sentences(block.text):
            start = block.text.find(sentence, cursor)
            if start < 0:
                continue
            cursor = start + len(sentence)
            sent_spans.append((sentence, start, cursor))

        for idx, (sentence, start, end) in enumerate(sent_spans):
            # 판례·법령 인용 문장은 사건으로 뽑지 않는다(배치C). 다만 sent_spans에는 남겨 두어
            # 바로 뒤 문장의 호증을 앞 사건에 결속하는 TK-188 경로가 그대로 동작하게 한다.
            if not _has_party_fact_cue(sentence) and (
                CASE_HOLDING_RE.search(sentence)
                or classify_claim(sentence) in (ClaimType.CASE_HOLDING, ClaimType.LEGAL_RULE,
                                                ClaimType.LEGAL_INTERPRETATION)
            ):
                continue
            structure = structure_claim_text(sentence)
            structure.pop("asserted_date")
            parsed_dates: List[Tuple[re.Match[str], date]] = []
            for m in DATE_RE.finditer(sentence):
                if _is_legal_authority_date(sentence, m.start(), m.end()):
                    continue
                try:
                    value = date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
                except ValueError:
                    continue
                parsed_dates.append((m, value))
            if not parsed_dates:
                continue

            evidence_refs = _collect_event_evidence_references(
                sentence, document_id=doc.document_id, block_id=block.block_id,
                page=block.page, source_run_id=source_run_id,
                document_sha256=doc.sha256, offset=start,
            )
            if _can_event_bind_adjacent(len(parsed_dates), structure):
                seen_spans = {tuple(r["span"]) for r in evidence_refs}
                for next_sent, next_start, _ in sent_spans[idx + 1:]:
                    adj_refs = _adjacent_evidence_refs(
                        next_sent, document_id=doc.document_id, block_id=block.block_id,
                        page=block.page, source_run_id=source_run_id,
                        document_sha256=doc.sha256, offset=next_start,
                    )
                    if not adj_refs:
                        break
                    for ref in adj_refs:
                        ref_span = tuple(ref["span"])
                        if ref_span not in seen_spans:
                            seen_spans.add(ref_span)
                            evidence_refs.append(ref)

            for m, value in parsed_dates:
                kind = "GENERIC"
                for name, regex in EVENT_KIND_RE:
                    if regex.search(sentence):
                        kind = name
                        break
                events.append(
                    Event.create(
                        value,
                        sentence.strip()[:300],
                        document_id=doc.document_id,
                        block_id=block.block_id,
                        page=block.page,
                        event_kind=kind,
                        raw_date_text=m.group(0),
                        project_id=project_id or doc.metadata.get("project_id"),
                        source_run_id=source_run_id, source_document_sha256=doc.sha256,
                        span=(start, end),
                        evidence_references=[dict(r) for r in evidence_refs],
                        **structure,
                    )
                )
    return events
