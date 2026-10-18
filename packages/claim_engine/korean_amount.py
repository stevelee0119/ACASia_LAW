"""한글 금액 표기 해석과 한글·숫자 병기 대조(v4 P4, AMOUNT_WORDS_MISMATCH).

서면은 '금 칠백만원(7,500,000원)'처럼 한글과 숫자를 함께 적는다. 두 값이 다르면 어느 쪽이 맞는지 문서만으로는
알 수 없으므로 불일치만 보고한다(Evidence A: 같은 문장 안의 두 표기를 계산으로 대조).

해석 범위: 일·이·삼…구, 십·백·천, 만·억·조 단위와 숫자 혼용('3억 5천만', '1억2,000만'). '일금 …원정'의
'일금'·'정'은 표기 관습으로 보고 뺀다. 해석할 수 없는 글자가 섞이면 None을 돌려준다(추측하지 않는다).
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text

ENGINE_NAME = "claim_engine.korean_amount"
DIGITS = {"영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "륙": 6, "칠": 7, "팔": 8, "구": 9}
SMALL = {"십": 10, "백": 100, "천": 1000}
LARGE = {"만": 10 ** 4, "억": 10 ** 8, "조": 10 ** 12}
WORD_CHARS = "영공일이삼사오육륙칠팔구십백천만억조"
# 한글 금액(숫자 섞임 허용) 뒤에 괄호 안 숫자 금액, 또는 그 반대
# 앞 글자가 한글이면(조사 '이' 등) 금액의 시작이 아니다. '금'·'일금' 바로 뒤는 허용한다.
KOREAN_AMOUNT = rf"(?:(?<=금)|(?<![가-힣\d]))(?:\d[\d,]*\s*)?[{WORD_CHARS}](?:[{WORD_CHARS}\d,\s]*[{WORD_CHARS}])?"
# 숫자 및 한글 금액 앞 통화 기호(일금, 금, KRW, ₩, ￦, ￥, 역슬래시)와 뒤의 '-'·'원정' 등 표기 통합
CURRENCY_PREFIX = r"(?:일금\s*|금\s*|[₩￦\\￥]\s*|KRW\s*)"
AMOUNT_SUFFIX = r"(?:\s*원\s*정|\s*원정|\s*원|\s*정|,?-|\.-)?"
NUMERIC_AMOUNT = r"\d{1,3}(?:,\d{3})+|\d+"
PAIR_RE = re.compile(
    rf"(?:{CURRENCY_PREFIX})?\s*(?P<words>{KOREAN_AMOUNT})\s*(?:원\s*(?:정)?)?\s*[(（]\s*(?:{CURRENCY_PREFIX})?(?P<digits>{NUMERIC_AMOUNT}){AMOUNT_SUFFIX}\s*[)）]"
    rf"|(?:{CURRENCY_PREFIX})?(?P<digits2>{NUMERIC_AMOUNT}){AMOUNT_SUFFIX}\s*[(（]\s*(?:{CURRENCY_PREFIX})?\s*(?P<words2>{KOREAN_AMOUNT})\s*(?:원\s*(?:정)?)?\s*[)）]"
)


def _small(text: str) -> Optional[int]:
    """만 미만 구간('칠백오십', '3천5백', '2,000')의 값."""
    if not text:
        return 0
    if re.fullmatch(r"[\d,]+", text):
        return int(text.replace(",", ""))
    total, pending = 0, None
    for ch in re.findall(r"\d+|[^\d]", text.replace(",", "")):
        if ch.isdigit():
            if pending is not None:
                return None
            pending = int(ch)
        elif ch in DIGITS:
            if pending is not None:
                return None
            pending = DIGITS[ch]
        elif ch in SMALL:
            total += (1 if pending is None else pending) * SMALL[ch]
            pending = None
        else:
            return None
    return total + (pending or 0)


def parse_korean_amount(text: str) -> Optional[Decimal]:
    """'이억오천만' → 250000000. 해석할 수 없으면 None."""
    body = re.sub(r"\s+", "", text or "")
    body = re.sub(r"^(?:일금|금|[₩\\￥]|KRW)+", "", body)
    # 보안(TK-38 B): 지수 증가 정규식 (?:원정|원|정)+$를 선형 [원정]+$로 교체
    body = re.sub(r"[원정]+$", "", body)
    if not body or not re.fullmatch(rf"[{WORD_CHARS}\d,]+", body):
        return None
    if not re.search(rf"[{WORD_CHARS}]", body):
        return None
    total = 0
    for part in re.split(r"(?<=[만억조])", body):
        if not part:
            continue
        unit = LARGE.get(part[-1])
        head = part[:-1] if unit else part
        value = _small(head)
        if value is None:
            return None
        if unit and value == 0 and head == "":
            value = 1  # '만원', '억원'
        total += value * (unit or 1)
    return Decimal(total)


# 괄호형 항목 표지 ([항목명], 【항목명】, <항목명>)
BRACKET_HEADING_RE = re.compile(r"[\[【<](?P<title>[^\]】>\n]{2,25})[\]】>]")
# 날짜 형태 정규식 (항목명에서 배제)
_DATE_STRIP_RE = re.compile(
    r"(?:(?:19|20)\d{2}[.\-/년]\s*)?\d{1,2}[.\-/월]\s*\d{1,2}[일.]?(?:\s*\([월화수목금토일]\))?"
)
# 번호/불릿 머리 정규식
_BULLET_NUM_RE = re.compile(
    r"^(?:[\s\-\*•·◦▪※▶▷○●□■\t|]+|"
    r"(?:\(?[0-9]{1,3}\)?|[0-9]{1,3}[.)]|[가나다라마바사아자차카타파하][.)]|\([가나다라마바사아자차카타파하]\))\s*)+"
)
# 서술어 종결어미, 연결어미 및 조사 패턴 (일반 문장의 주어/목적어/부사어 등 배제용)
_JOSA_PREDICATE_RE = re.compile(
    r"(?:에서|으로|로|에게|에는|은|는|이|가|을|를|의|에|와|과|도|만|부터|까지|"
    r"하고|하며|하여|하였으나|하였으며|있으나|있으며|있고|바|임|함|음|다|대하여|따라|관하여|기준으로|청구함|지급함)\s*[,.]?$"
)
# 금액 형태 정규식 (통화 기호 또는 단위가 포함된 경우만 금액으로 인식)
_AMOUNT_STRIP_RE = re.compile(
    r"(?:일금\s*|금\s*|[₩\\￥]\s*|KRW\s*)[-−+]?\s*\d[\d,]*(?:\.\d+)?(?:\s*(?:억|천만|백만|만|천))?(?:\s*(?:원정|원))?|"
    r"[-−+]?\s*\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|천)\s*(?:원정|원)?|"
    r"[-−+]?\s*\d[\d,]*(?:\.\d+)?\s*(?:원정|원)"
)


def _find_item_heading(text: str, offset: int) -> Optional[str]:
    """매칭 위치 이전의 같은 줄에서 결함 값 바로 앞의 짧은 항목명(예: '물품정산 1차')을 추출한다.

    소제목이나 이전 줄로는 대체하지 않으며, 날짜·금액·번호·조사·서술문을 배제한 2~20자 명사구만 반환한다.
    """
    line_start = text.rfind("\n", 0, offset)
    s_idx = 0 if line_start == -1 else line_start + 1
    line_prefix = text[s_idx:offset].strip()

    if not line_prefix or len(line_prefix) > 40:
        return None

    # 1. 괄호형 항목 표지 우선 검사 ([물품정산 1차], <자재목록> 등)
    m_bracket = BRACKET_HEADING_RE.search(line_prefix)
    if m_bracket:
        return m_bracket.group(0).strip()

    # 2. 날짜 패턴 제거 (연도 숫자가 불릿 번호로 오인되는 것을 방지하고, 날짜 문자열 유입 차단)
    cleaned = _DATE_STRIP_RE.sub("", line_prefix).strip()

    # 3. 선행 불릿 및 번호 머리 제거
    cleaned = _BULLET_NUM_RE.sub("", cleaned).strip()

    # 4. 선행 금액 패턴 제거 (이전 금액이 있을 경우 그 이후부터 결함 금액 직전까지)
    amounts_in_prefix = list(_AMOUNT_STRIP_RE.finditer(cleaned))
    if amounts_in_prefix:
        cleaned = cleaned[amounts_in_prefix[-1].end():].strip()

    # 5. 서술문, 조사 및 구두점 배제 (문장의 일부인 경우 항목명이 아님)
    if not cleaned or len(cleaned) < 2 or len(cleaned) > 20:
        return None
    if any(p in cleaned for p in [".", ",", ";", "!", "?"]):
        return None
    if _JOSA_PREDICATE_RE.search(cleaned):
        return None

    # 6. 유효한 짧은 명사구 항목명 반환
    return cleaned


def words_digits_mismatches(doc: NormalizedDocument) -> List[Finding]:
    text = build_reading_text(doc).text
    out: List[Finding] = []
    for m in PAIR_RE.finditer(text):
        words, digits = (m.group("words"), m.group("digits")) if m.group("words") else (m.group("words2"), m.group("digits2"))
        word_value = parse_korean_amount(words)
        if word_value is None:
            continue
        digit_value = Decimal(digits.replace(",", ""))
        if word_value == digit_value:
            continue
        eff_h = _find_item_heading(text, m.start())
        h_prefix = f"{eff_h} " if eff_h else ""

        excerpt = " ".join(m.group(0).split())
        if eff_h:
            excerpt = f"{h_prefix}{excerpt}"

        features = {"deterministic_rule": True, "arithmetic_proof": True, "rule_id": "AMOUNT.WORDS_MISMATCH",
                    "defect_code": "AMOUNT_WORDS_MISMATCH", "words": words.strip(), "words_value": str(word_value),
                    "digits_value": str(digit_value), "difference": str(digit_value - word_value)}
        if eff_h:
            features["heading"] = eff_h

        out.append(Finding.create(
            type=FindingType.ARITHMETIC_MISMATCH, status=VerificationStatus.CONTRADICTED, severity=Severity.HIGH,
            evidence_grade=EvidenceGrade.A,
            title=f"한글 금액과 숫자 금액이 다르다(AMOUNT_WORDS_MISMATCH): '{words.strip()}'={word_value:,}원 / 숫자 {digit_value:,}원",
            detail=(f"{h_prefix}같은 자리에 병기한 한글 금액 '{words.strip()}'은 {word_value:,}원이고 숫자 금액은 {digit_value:,}원이다"
                    f"(차이 {digit_value - word_value:,}원). 어느 쪽이 맞는지는 문서만으로 알 수 없으므로 원본을 확인해야 한다."),
            confidence=0.95, confidence_features=features, document_id=doc.document_id, engine=ENGINE_NAME,
            tags=["CALCULATION", "AMOUNT"],
            evidence=[Evidence.create(description=f"{h_prefix}한글·숫자 병기".strip(), grade=EvidenceGrade.A, document_id=doc.document_id,
                                      excerpt=excerpt[:200])]))
    return out

