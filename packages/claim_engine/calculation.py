"""제11.5장 숫자 검증.

손해액, 이자, 기간, 합계, 비율은 LLM이 아닌 Python Calculation Engine으로 검산한다.
문서의 합계와 세부 금액 합산값이 다르면 ARITHMETIC_MISMATCH를 Evidence Grade A로 생성한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from packages.common.confidence import score as confidence_score
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument

ENGINE_NAME = "claim_engine.calculation"

AMOUNT_RE = re.compile(
    r"(?<![\d.,])(?P<cur>일금\s*|금\s*|[₩\\￥]\s*|KRW\s*)?(?P<sign>[-−+]?)\s*"
    r"(?P<amount>(?:\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|천)\s*)*\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|천)?)"
    r"(?:\s*(?P<unit>원정|원))?"
)
AMOUNT_PART_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(억|천만|백만|만|천)?")
TOTAL_LABEL_RE = re.compile(r"(합계|총액|총\s*금액|계|소계|합\s*계|총\s*계|지급총액|지급계|지급\s*총액|공제계|공제총액|공제\s*합계|실지급액|차인지급액|총수령액)")
ITEM_LABEL_RE = re.compile(r"(항목|내역|세부|명세)")
PERCENT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*%")
_BARE_PERCENT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)%?")
PERCENT_HEADER_RE = re.compile(r"비율|구성비|점유율|%|퍼센트")

UNIT_MULTIPLIER = {None: 1, "천": 1_000, "만": 10_000, "백만": 1_000_000, "천만": 10_000_000, "억": 100_000_000}

TOLERANCE = Decimal("0.01")
MIN_LINE_ITEMS = 2  # 줄 단위 내역은 최소 2건이 모여야 합계를 검산한다


@dataclass
class Amount:
    value: Decimal
    raw: str
    start: int
    end: int
    block_id: Optional[str] = None
    page: Optional[int] = None


@dataclass
class CalculationCheck:
    kind: str
    stated: Decimal
    computed: Decimal
    items: List[Amount] = field(default_factory=list)
    block_id: Optional[str] = None
    page: Optional[int] = None
    detail: str = ""
    rows: List[str] = field(default_factory=list)

    @property
    def matches(self) -> bool:
        return abs(self.stated - self.computed) <= TOLERANCE


def parse_amounts(text: str, *, block_id: Optional[str] = None, page: Optional[int] = None) -> List[Amount]:
    out: List[Amount] = []
    for m in AMOUNT_RE.finditer(text):
        try:
            parts = AMOUNT_PART_RE.findall(m.group("amount"))
            if any(not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", number) for number, _ in parts):
                continue
            has_cur = bool(m.group("cur"))
            has_unit = bool(m.group("unit"))
            has_mult = any(bool(unit) for _, unit in parts)
            if not (has_cur or has_unit or has_mult):
                continue
            # Do not silently parse the tail of an unsupported compound/currency.
            prefix = text[:m.start()]
            if re.search(r"(?:\d[\d,.]*\s*(?:조|경|백|십)|USD|EUR|JPY|[$€¥])\s*$", prefix, re.I):
                continue
            if re.match(r"\s*(?:조|경|백|십)(?=\s*(?:\d|[억만천백십원]|$))", text[m.end():]):
                continue
            units = [UNIT_MULTIPLIER.get(unit or None, 1) for _, unit in parts]
            if any(a <= b for a, b in zip(units, units[1:])):
                continue
            value = sum((Decimal(number.replace(",", "")) * multiplier
                         for (number, _), multiplier in zip(parts, units)), Decimal(0))
            if m.group("sign") in ("-", "−"):
                value = -value
        except InvalidOperation:  # pragma: no cover
            continue
        out.append(Amount(value, m.group(0), m.start(), m.end(), block_id, page))
    return out


def check_sum(items: List[Amount], stated: Amount) -> CalculationCheck:
    computed = sum((i.value for i in items), Decimal(0))
    return CalculationCheck(
        kind="SUM",
        stated=stated.value,
        computed=computed,
        items=items,
        block_id=stated.block_id,
        page=stated.page,
        detail=f"세부 {len(items)}건 합산 {computed:,} / 문서 기재 {stated.value:,}",
    )


def simple_interest(principal: Decimal, annual_rate_percent: Decimal, days: int) -> Decimal:
    """연 이율 단리. 민사 실무의 연 단위 일할 계산."""
    return (principal * annual_rate_percent / Decimal(100) * Decimal(days) / Decimal(365)).quantize(Decimal("1"))


def day_count(start: date, end: date, *, inclusive: bool = False) -> int:
    delta = (end - start).days
    return delta + 1 if inclusive else delta


OPERATOR_RE = re.compile(r"\s*([+\-−×xX*＋✕✖\u2a2f])\s*")
MULTIPLIER_RE = re.compile(r"^\s*[×xX*✕✖\u2a2f]\s*(\d[\d,]*(?:\.\d+)?)\s*(?:[가-힣]{1,4})?")
# '수 × 금액' 순서 산식 패턴 (예: 3 × 500,000원, 3개월 × 1,000,000원, 물품내역 1차 14건 × 17,000원)
# 닫힌 목록 대신 1~4자 일반 한글 단위 명사를 허용하여 일반화
LEADING_MULTIPLIER_RE = re.compile(
    r"(?:^|(?<=[\s:;\]\)\>]))(?P<mult>\d[\d,]*(?:\.\d+)?)\s*(?:[가-힣]{1,4})?\s*[×xX*✕✖\u2a2f]\s*"
)
AMOUNT_HEADER_RE = re.compile(r"(금액|합계|청구액|손해액|피해액|소계|청구\s*금액|총액|계)")

# --- TK-76 3주기 1항: 본문 서술형 및 일반 단위 산식 검증 정규식 및 가드 (M2~M7) ---
# M3: 단위 뒤에 결합되는 한국어 조사/보조사 분리 정규식
UNIT_JOSA_RE = re.compile(
    r"^(?P<unit>[가-힣]{1,4}?)(?P<josa>(?:만(?:[을이은는])?|이(?:다|며|고|라|면)|입니다|은|는|이|가|을|를|의|에(?:서)?|[으]?로|씩|[과와]|도))?(?=\s|[,.:;\]\)\>]|$)"
)

# 평가 측 보완(F3·F5·F8): 날짜·법령 위치·조사만·연산 서술어
_DATE_SPAN_RE = re.compile(r"\d{4}\s*(?:[.\-/]|년)\s*\d{1,2}\s*(?:[.\-/]|월)(?:\s*\d{1,2}\s*[.일]?)?|\d{4}\s*년|\d{4}\s*\.(?=\s|$)")
_LEGAL_LOCATOR_RE = re.compile(r"^(?:조|항|호|목)(?:의|$|[^가-힣])|^조(?:가|는|에|를|의)")
_JOSA_ONLY_RE = re.compile(r"(?:만(?:[을이은는])?|이(?:다|며|고|라|면)|입니다|은|는|이|가|을|를|의|에(?:서)?|[으]?로|씩|[과와]|도)")
_OPERATION_WORD_RE = re.compile(r"^(?:곱하|곱한|합하|합한|더하|더한|빼|뺀|공제|차감)")
# 연산 서술어(명시적 연산 표지)와 합계 표지. 결과를 잇는 절에 이 가운데 하나가 있어야 서술형 산식으로 본다(메모 M4·N3).
# 연산 종류별 서술어. 서술형 판별 관문(_OP_PREDICATE_RE)과 계산(_evaluate_formula_operands)이 같은 목록을 쓴다(평가 측 2차 보완 G1).
_MUL_PRED = r"곱하[면여]|곱한|곱하기"
_ADD_PRED = r"합하[면여]|합산하[면여]|합한|합산한|더하[면여]|더한"
_SUB_PRED = r"공제하[면여]|공제한|차감하[면여]|차감한|뺀|빼면"
_OP_PREDICATE_RE = re.compile(f"{_MUL_PRED}|{_ADD_PRED}|{_SUB_PRED}")
# 연산 결과를 가리키는 명사('그 곱은'·'합은'·'차는')는 명시적 연산 표지다. 절 경계가 있어도 결과를 잇는다.
_OP_RESULT_NOUN_RE = re.compile(r"(?:^|\s)(?:그\s*)?(?P<noun>곱|합|차)(?:은|는|이|가)(?=\s|$)")
_TOTAL_MARK_RE = re.compile(r"(?:^|\s)(?:총|전체|모두|합계|합산)")
# 절 경계: 연결 어미(-고·-며·-으나·-지만·-는데) 뒤 공백이나 쉼표가 결과 앞에 있으면 다른 절이다(메모 M4)
_CLAUSE_BREAK_RE = re.compile(r"[가-힣](?:고|며|으나|지만|는데)(?:\s|,)|,")
# 연산 서술어('더하면'·'빼면' 등) 뒤 결과 이름표 구간에서는 용언 어간 뒤 연결 어미만 절 경계로 본다.
# '출고·입고·신고·광고·재고·원고' 같은 '고'로 끝나는 명사를 연결 어미 '-고'로 읽지 않기 위해서다(평가 측 진단, '대' 수량 산식 미탐)
_VERBAL_CLAUSE_BREAK_RE = re.compile(r"(?:하|되|했|됐|였|었|았|있|없|않|이)(?:고|며|으나|지만|는데)(?:\s|,)|,")
# 피연산자 절 경계: 연결 어미(-고·-며·-으나·-지만·-는데·-므로·-어서·-아서) 뒤, 또는 수 사이가 아닌 쉼표 뒤(평가 측 2차 보완 G2)
# 쉼표 뒤 공백을 건너 숫자가 오면('A원, N월분 B원') 나열이지 절 경계가 아니다(평가 측 보완 N3)
_OPERAND_CLAUSE_BREAK_RE = re.compile(r"[가-힣](?:고|며|으나|지만|는데|므로|어서|아서)(?=[\s,])|,(?! ?\d)")
# 차수·순번 표지('1차 120명'의 '1차')는 피연산자가 아니라 이름표다(평가 측 2차 보완 G3)
_ORDINAL_UNITS = ("차", "번째", "회차", "순위")
# 달력 시점 이름표 단위와 그 값 범위(평가 측 '대' 수량 산식 후속): N월(1~12)·N분기(1~4)·N반기(1~2)
_CALENDAR_LABEL_RANGE = {"월": (1, 12), "분기": (1, 4), "반기": (1, 2)}
# 기간 몫 이름표: 수 + 달력 기간(월·분기·반기·년·연) + '분'. 'N개월분'(기간의 양)·'N일분'은 수량이므로 넣지 않는다(평가 측 보완 N1)
_PERIOD_LABEL_RE = re.compile(r"(?:월|분기|반기|년|연)분")

# M7: 정당한 차이 가드 정규식
TAX_DEDUCTION_GUARD_RE = re.compile(r"(?:부가(?:가치)?세|공급가액|세액|VAT|원천징수|지연손해금|할인)")
# 근사치 표지는 수치에 붙은 독립 낱말일 때만 본다. '계약'·'위약금'·'약정'의 '약'은 표지가 아니다(평가 측 2차 보완 G4, 메모 M7 '수치 인접')
APPROX_GUARD_RE = re.compile(r"(?<![가-힣])(?:약|대략)\s*\d|\d[\d,.]*\s*[가-힣]{0,4}?\s*(?:가량|내외|남짓|이상|이하|미만|초과)")
RANGE_GUARD_RE = re.compile(r"(?:~|내지)")
CLAIM_QUOTE_GUARD_RE = re.compile(r"(?:주장하(?:나|였으나|며)|주장은\s*사실과|가정하더라도)")


def evaluate_expression(text: str, context_text: Optional[str] = None) -> Optional[Decimal]:
    """'3,100,000원 + 1,250,000원', '500,000원 × 3', '3 × 500,000원', '물품내역 1차 14건 × 17,000원' 같은 산식의 값. 산식이 아니면 None."""
    full_text = context_text if context_text is not None else text
    # 1. '수 × 금액' 선행 배수 산식 처리 (수량/개월수 × 단가 및 '천 단위 쉼표 수 × 정수')
    lead_match = LEADING_MULTIPLIER_RE.search(text)
    if lead_match:
        prefix = text[:lead_match.start()].strip()
        # 선행 텍스트에 연산자(+, -, *, /, =)가 없어야 단일 라벨 뒤의 수량 산식으로 취급
        if not re.search(r"[+\-−×xX*＋/=]", prefix):
            raw_lead = lead_match.group("mult")
            lead_mult = Decimal(raw_lead.replace(",", ""))
            remainder = text[lead_match.end():]
            amounts = parse_amounts(remainder)
            if not amounts:
                amt = parse_cell_amount(remainder)
                if amt:
                    # Y7: 통화 표지가 없는 산식은 같은 행 좌우 어디든 통화(원·₩·천·만·억)가 있거나 열 머리가 AMOUNT_HEADER_RE일 때만 계산한다.
                    # has_large_number 단독 조건은 완전히 삭제한다.
                    has_currency = bool(re.search(r"[원₩\\]|천|만|억", full_text))
                    has_comma = ("," in raw_lead) or ("," in amt.raw)
                    if has_currency and (has_comma or (lead_mult > 0 and amt.value > 0)):
                        return lead_mult * amt.value
                return None
            total = lead_mult * amounts[0].value
            cursor = amounts[0].end
            for amount in amounts[1:]:
                between = remainder[cursor:amount.start]
                if not between.strip() and amount.raw.lstrip()[:1] in "+-−":
                    total += amount.value
                    cursor = amount.end
                    continue
                op = OPERATOR_RE.fullmatch(between)
                if not op:
                    return None
                total = total - amount.value if op.group(1) in "-−" else total + amount.value
                cursor = amount.end
            tail = MULTIPLIER_RE.match(remainder[cursor:])
            if tail:
                total *= Decimal(tail.group(1).replace(",", ""))
            return total

    # 2. 일반 '금액 + 금액' 또는 '금액 × 수' 산식 처리
    amounts = parse_amounts(text)
    if not amounts:
        return None
    total = amounts[0].value
    cursor = amounts[0].end
    for amount in amounts[1:]:
        between = text[cursor:amount.start]
        if not between.strip() and amount.raw.lstrip()[:1] in "+-−":
            total += amount.value  # 금액 패턴이 부호를 금액에 붙여 읽었다(값에 부호가 이미 들어 있다)
            cursor = amount.end
            continue
        op = OPERATOR_RE.fullmatch(between)
        if not op:
            return None
        total = total - amount.value if op.group(1) in "-−" else total + amount.value
        cursor = amount.end
    tail = MULTIPLIER_RE.match(text[cursor:])
    if tail:
        total *= Decimal(tail.group(1).replace(",", ""))
        cursor += tail.end()
    elif len(amounts) == 1:
        return None
    return total


def parse_cell_amount(text: str, *, block_id: Optional[str] = None, page: Optional[int] = None) -> Optional[Amount]:
    """표 셀의 금액 파싱: '원'이나 '₩'이 붙은 경우뿐만 아니라 '3,200,000'이나 '0' 같은 순수 숫자도 금액으로 인식한다."""
    t = text.strip()
    if not t:
        return None
    amounts = parse_amounts(t, block_id=block_id, page=page)
    if amounts:
        return amounts[0]
    if re.fullmatch(r"[-−+]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", t):
        try:
            val = Decimal(t.replace(",", "").replace("−", "-"))
            return Amount(val, t, 0, len(t), block_id=block_id, page=page)
        except InvalidOperation:
            return None
    return None


def row_final_amount(text: str) -> Tuple[Optional[Amount], Optional[CalculationCheck]]:
    """행의 최종 금액과(있으면) 그 행 산식의 검산 결과. '=' 뒤 금액을 최종 금액으로 본다."""
    amounts = parse_amounts(text)
    if "=" in text:
        left, _, right = text.rpartition("=")
        right_amounts = parse_amounts(right)
        value = evaluate_expression(left[left.rfind(":") + 1:] if ":" in left else left, context_text=text)
        if right_amounts:
            final = right_amounts[0]
            check = None
            if value is not None:
                check = CalculationCheck(kind="FORMULA", stated=final.value, computed=value,
                                         detail=f"산식 '{' '.join(text.split())}'의 계산값 {value:,} / 기재 {final.value:,}")
            return Amount(final.value, final.raw, len(left) + 1 + final.start, len(left) + 1 + final.end), check
        else:
            # 우변에 조사가 붙어 있거나 단위가 생략된 경우 (T1: 결과 뒤 단위·조사 지원, Y7: 행 내 통화 확인)
            has_currency_in_row = bool(re.search(r"[원₩\\]|천|만|억", text))
            right_cell_amt = None
            if has_currency_in_row:
                right_cell_amt = parse_cell_amount(right)
                if not right_cell_amt:
                    m_num = re.search(r"(?P<val>\d{1,3}(?:,\d{3})+|\d+)\s*(?:원)?", right)
                    if m_num:
                        try:
                            v = Decimal(m_num.group("val").replace(",", ""))
                            if v > 0:
                                right_cell_amt = Amount(v, m_num.group(0), m_num.start(), m_num.end())
                        except InvalidOperation:
                            pass
            if right_cell_amt and value is not None and has_currency_in_row:
                check = CalculationCheck(kind="FORMULA", stated=right_cell_amt.value, computed=value,
                                         detail=f"산식 '{' '.join(text.split())}'의 계산값 {value:,} / 기재 {right_cell_amt.value:,}")
                return Amount(right_cell_amt.value, right_cell_amt.raw, len(left) + 1 + right_cell_amt.start, len(left) + 1 + right_cell_amt.end), check

    if not amounts:
        return None, None
    if len(amounts) == 1:
        return amounts[0], None
    return None, None


def row_cell_final_amount(text: str, *, block_id: Optional[str] = None, page: Optional[int] = None) -> Tuple[Optional[Amount], Optional[CalculationCheck]]:
    """표 셀의 최종 금액과 산식 검증. 단위가 생략된 천 단위 콤마 숫자도 지원한다."""
    if "=" in text:
        left, _, right = text.rpartition("=")
        right_amt = parse_cell_amount(right, block_id=block_id, page=page)
        value = evaluate_expression(left[left.rfind(":") + 1:] if ":" in left else left, context_text=text)
        if right_amt:
            check = None
            if value is not None:
                check = CalculationCheck(kind="FORMULA", stated=right_amt.value, computed=value,
                                         detail=f"산식 '{' '.join(text.split())}'의 계산값 {value:,} / 기재 {right_amt.value:,}")
            return right_amt, check
    amt = parse_cell_amount(text, block_id=block_id, page=page)
    if amt is not None:
        return amt, None
    return None, None


# --- TK-76 3주기 1항: 본문 서술형 및 일반 단위 산식 파서 및 검산 로직 (A 산식 일반화) ---

def unit_is_ordinal_label(m: "re.Match", text: str) -> bool:
    """'1차 120명'·'2회차 지급 30만 원'의 차수·순번(1차·2회차)은 이름표다. 바로 뒤가 연산 기호일 때만 수로 본다(평가 측 2차 보완 G3)."""
    up = m.group("unit_part") or ""
    if _PERIOD_LABEL_RE.match(up):
        return True  # 'N월분'·'N분기분'·'N년분'처럼 어느 기간 몫인지 가리키는 이름표(평가 측 보완 N1)
    # 달력 시점('1월 접수 37건'의 '1월', '3분기 매출'의 '3분기')은 수량이 아니라 이름표다. 'N개월'(기간의 양)은 '개월'이라 해당 없음
    if up in _CALENDAR_LABEL_RANGE and not re.match(r"\s*[×*xX✕✖\u2a2f+＋\-−=]", text[m.end():]):
        lo, hi = _CALENDAR_LABEL_RANGE[up]
        try:
            v = int(re.sub(r"[^\d]", "", m.group(0).split(up)[0]) or -1)
        except ValueError:
            v = -1
        if lo <= v <= hi:
            return True
    return up in _ORDINAL_UNITS and not re.match(r"\s*[×*xX✕✖\u2a2f+＋\-−=]", text[m.end():])


def _operand_clause_start(text: str, tokens: List[dict], end_pos: int) -> int:
    """end_pos 앞에서 피연산자 2개 이상이 남는 마지막 절 경계 위치. 없으면 0(평가 측 2차 보완 G2)."""
    for m in reversed(list(_OPERAND_CLAUSE_BREAK_RE.finditer(text, 0, end_pos))):
        if sum(1 for t in tokens if t["start"] >= m.end() and t["end"] <= end_pos) >= 2:
            return m.end()
    return 0


def _extract_formula_tokens(text: str) -> List[dict]:
    """문장 내에서 금액 및 일반 수치(단위, 조사 분리 포함) 토큰을 순서대로 추출한다."""
    amounts = parse_amounts(text)
    amt_spans = [(a.start, a.end) for a in amounts]
    tokens: List[dict] = []
    
    # 1. 금액 토큰 등록 (원화 단위)
    for a in amounts:
        tail = text[a.end:]
        m_josa = re.match(r"^(?:만(?:[을이은는])?|이(?:다|며|고|라|면)|입니다|은|는|이|가|을|를|의|에(?:서)?|[으]?로|씩|[과와]|도)", tail)
        josa = m_josa.group(0) if m_josa else None
        tokens.append({"val": a.value, "unit": "원", "josa": josa, "start": a.start, "end": a.end, "raw": a.raw})
    
    # 날짜(연·월·일)와 연도는 피연산자가 아니다(평가 측 보완 F5).
    date_spans = [(d.start(), d.end()) for d in _DATE_SPAN_RE.finditer(text)]
    # 2. 금액 외 일반 수치 및 단위 명사 탐색 (M3: 단위 뒤 조사 분리)
    for m in re.finditer(r"(?<![\d.,])(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit_part>[가-힣]{1,6})?", text):
        s, e = m.start(), m.end()
        # 이미 parse_amounts에서 파싱된 범위는 중복 제외
        if any(as_ <= s < ae or as_ < e <= ae for as_, ae in amt_spans):
            continue
        if any(ds <= s < de for ds, de in date_spans):
            continue
        # 법령 위치(제N조·항·호·목)의 번호는 피연산자가 아니다(평가 측 보완 F5)
        if _LEGAL_LOCATOR_RE.match(m.group("unit_part") or "") or re.search(r"제\s*$", text[max(0, s - 2):s]):
            continue
        # M2: 날짜(YYYY-MM-DD), 사건번호(2023가합1234) 등 하이픈/문장부호 결합 식별자는 배제
        context = text[max(0, s - 5):min(len(text), e + 10)]
        if re.search(r"\d{4}-\d{2}-\d{2}|\d{4}\.\s*\d|\d+[가-힣]+\d+", context):
            continue
        num_str = m.group("num").replace(",", "")
        try:
            val = Decimal(num_str)
        except InvalidOperation:
            continue
        if unit_is_ordinal_label(m, text):
            continue
        # 앞에 붙은 음수 부호(공백·여는 괄호·문장 시작 뒤의 '-'/'−')는 값에 넣는다(평가 측 보완 F3)
        if s >= 1 and text[s - 1] in "-−" and (s == 1 or text[s - 2] in " \t(:"):
            val = -val
        up = m.group("unit_part") or ""
        m_uj = UNIT_JOSA_RE.match(up)
        if _JOSA_ONLY_RE.fullmatch(up) or _OPERATION_WORD_RE.match(up):
            # 수 뒤가 조사뿐이거나 연산 서술어(곱하기 등)면 단위가 없다(평가 측 보완 F8, 메모 N2).
            # 연산 서술어는 토큰에 넣지 않는다(다음 피연산자와의 사이 글자에서 연산으로 읽히게).
            unit, josa = None, (up if _JOSA_ONLY_RE.fullmatch(up) else None)
            if _OPERATION_WORD_RE.match(up):
                e = m.end("num")
        elif m_uj:
            unit = m_uj.group("unit") or None
            josa = m_uj.group("josa")
        elif up:
            unit = up
            josa = None
        else:
            unit = None
            josa = None
        # '단당·상자당'처럼 앞에 '…당'이 붙은 수는 단위당 수량이다. 곱의 단위는 이 수의 단위다(평가 측 보완).
        per = bool(re.search(r"[가-힣]{1,4}당\s*$", text[max(0, s - 8):s]))
        tokens.append({"val": val, "unit": unit, "josa": josa, "start": s, "end": e, "raw": text[s:e], "per": per})
    
    tokens.sort(key=lambda t: t["start"])
    return tokens


def _is_unit_compatible(op_units: List[Optional[str]], res_unit: Optional[str], op_type: str) -> bool:
    """피연산자들의 단위와 결과 단위의 호환성 및 차원 변환 타당성을 검증한다."""
    if op_type in ("+", "-"):
        # 덧셈 및 뺄셈: 명시된 모든 단위가 일치해야 함
        valid_units = {u for u in op_units if u is not None}
        if res_unit is not None:
            valid_units.add(res_unit)
        return len(valid_units) <= 1
    elif op_type == "*":
        # 곱셈: 수량 단위 × 화폐 단위 = 화폐 단위 등 합리적 차원 변환 허용
        units = [u for u in op_units if u is not None]
        if not units:
            return True
        if len(units) == 1:
            return res_unit is None or res_unit == units[0] or res_unit == "원"
        if len(units) >= 2:
            u1, u2 = units[0], units[1]
            if "원" in (u1, u2):
                return res_unit == "원"
            # 횟수/배수 단위(회, 배, 번, 개월 등)와의 결합 시 기본 단위 보존 허용
            iter_units = ("회", "배", "번", "개월", "일", "년", "차", "주")
            if any(u in iter_units for u in (u1, u2)):
                base_unit = u1 if u2 in iter_units else u2
                return res_unit == base_unit or res_unit is None
            if u1 == u2:
                return res_unit == u1
            return False
    return True


# 평가 측 후속 Q4: '1공장 생산 214대'의 '1공장', '3호점 매출 120만 원'의 '3호점'처럼 바로 뒤 수량을 꾸미는 '수+명사' 이름표는
# 피연산자가 아니다. 뒤 수량과의 사이에 연결어(와·과·및·그리고·더하기·연산 기호·쉼표)가 없고, 이름표 단위는 결과 단위와 다르며
# 뒤 수량의 단위는 결과 단위와 같을 때만 뺀다(명사 목록을 두지 않는 구조 규칙)
_LABEL_LINK_BLOCK_RE = re.compile(r"와|과|및|그리고|더하기|빼기|곱하기|나누기|각|[+\-−×*xX✕✖=,·]")


_SYMBOL_UNIT_RE = re.compile(r"\s*(㎡|㎏|㎞|㎝|㎜|㎖|ℓ|m²|kg|km|cm|mm|m|L|%)(?![A-Za-z])")


def _eff_unit(tok: dict, text: str) -> Optional[str]:
    """토큰 단위. 한글 단위가 없으면 수 바로 뒤의 기호 단위(㎡·kg 등)를 이 판정 안에서만 단위로 본다."""
    if tok.get("unit"):
        return tok["unit"]
    m = _SYMBOL_UNIT_RE.match(text, tok["end"])
    return m.group(1) if m else None


def _drop_quantity_labels(ops: List[dict], res_token: dict, text: str) -> List[dict]:
    ru = _eff_unit(res_token, text)
    if not ru:
        return ops
    out: List[dict] = []
    for i, t in enumerate(ops):
        nxt = ops[i + 1] if i + 1 < len(ops) else None
        gap = text[t["end"]:nxt["start"]] if nxt is not None else ""
        if (nxt is not None and t.get("unit") and t["unit"] != ru and _eff_unit(nxt, text) == ru
                and t.get("josa") in (None, "의", "에서", "에") and len(gap) <= 15
                and not _LABEL_LINK_BLOCK_RE.search(gap)):
            continue
        out.append(t)
    # 이름표를 빼고 피연산자가 2개 미만이면 이름표가 아니라 실제 피연산자(곱셈의 인원·횟수 등)로 본다
    return out if len(out) >= 2 else ops


def _units_ok(ops: List[dict], res_token: dict, op_type: str) -> bool:
    """단위당 수량('…당 N단위')이 있는 곱은 그 단위가 결과 단위다. 그 밖에는 기존 호환성 규칙."""
    per = [o for o in ops if o.get("per") and o.get("unit")]
    if op_type == "*" and per:
        return res_token["unit"] == per[-1]["unit"]
    return _is_unit_compatible([o["unit"] for o in ops], res_token["unit"], op_type)


def _evaluate_formula_operands(ops: List[dict], text: str, after_ops: str = "") -> Tuple[Optional[Decimal], Optional[str]]:
    """피연산자 리스트와 연산 서술어(after_ops)를 바탕으로 계산값과 연산 종류를 도출한다."""
    if len(ops) < 2:
        return None, None
    
    # 2개 피연산자 뒤에 연산 서술어가 오는 서술형 산식 처리
    noun = _OP_RESULT_NOUN_RE.search(after_ops) if after_ops else None
    if len(ops) == 2 and noun:                         # '그 곱은/합은/차는' 결과 명사
        kind = noun.group("noun")
        if kind == "곱":
            return ops[0]["val"] * ops[1]["val"], "*"
        if kind == "합":
            return ops[0]["val"] + ops[1]["val"], "+"
        return ops[0]["val"] - ops[1]["val"], "-"
    if len(ops) == 2 and after_ops:
        # 평가 측 후속 Q5: 분배형 곱셈('N명 각 X원씩 … 합계', 'N곳에 각각 X원씩 … 모두')은 결과 앞 '합계·모두'가 있어도 곱이다.
        # 첫 피연산자(인원·개수)와 둘째(단가)의 단위가 다르고, '씩'이 둘째 피연산자에 붙거나 사이에 '각·각각'이 있을 때(덧셈 규칙보다 먼저 본다)
        if _TOTAL_MARK_RE.search(after_ops) and ops[0].get("unit") != ops[1].get("unit") and (
                ops[1].get("josa") == "씩" or re.match(r"\s*씩", text[ops[1]["end"]:])
                or (re.search(r"(?<![가-힣])각(?:각)?(?![가-힣])", text[ops[0]["end"]:ops[1]["start"]])
                    and re.search(r"씩", text[ops[1]["start"]:ops[1]["end"] + 2]))):
            return ops[0]["val"] * ops[1]["val"], "*"
        if re.search(f"{_SUB_PRED}|제외하[면여]", after_ops):
            return ops[0]["val"] - ops[1]["val"], "-"
        if re.search(f"합계|{_ADD_PRED}|모두\\s*합하", after_ops):
            return ops[0]["val"] + ops[1]["val"], "+"
        if re.search(f"{_MUL_PRED}|배한|\\b배로\\b|(?<=\\d)\\s*배", after_ops) or (
                ops[0]["josa"] == "씩" and _TOTAL_MARK_RE.search(after_ops)):
            return ops[0]["val"] * ops[1]["val"], "*"

    total = ops[0]["val"]
    cursor = ops[0]["end"]
    primary_op = None
    for i, op_token in enumerate(ops[1:], start=1):
        prev_token = ops[i - 1]
        prev_josa = prev_token.get("josa")
        between = text[cursor:op_token["start"]]
        raw_lead = op_token["raw"].lstrip()[:1]
        
        # 덧셈 연산자 판별 (직전 조사 '와/과', 명시적 '+' 기호, '와/과/더한/합한' 등 연결어)
        # '와/과' 나열은 연산이 아니다(평가 측 보완 F1). 기호나 연산 서술어가 있어야 덧셈이다.
        if raw_lead in ("+", "＋") or re.search(f"[+＋]|{_ADD_PRED}", between):
            total += op_token["val"]
            primary_op = primary_op or "+"
        # 뺄셈 연산자 판별 (M2: 하이픈 앞뒤 공백 또는 단위 결합 가드)
        elif raw_lead in ("-", "−") or re.search(f"(?<=\\s)[-−](?=\\s)|(?<=[가-힣])[-−]|\\b(?:{_SUB_PRED}|제외하[면여])", between):
            total = total + op_token["val"] if op_token["val"] < 0 else total - op_token["val"]
            primary_op = primary_op or "-"
        # 곱셈 연산자 판별 (기호, 배수 서술어, 주기 단위, '씩' 조사)
        # 단위(일·회·개월 등)만으로 곱셈을 추정하지 않는다(평가 측 보완 F6). '씩'은 결과 앞 합계 표지가 있을 때만.
        elif re.search(f"[×*xX✕✖\u2a2f]|{_MUL_PRED}|배한|\\b배로\\b|(?<=\\d)\\s*배", between) or (
                prev_josa == "씩" and _TOTAL_MARK_RE.search(after_ops)):
            total *= op_token["val"]
            primary_op = primary_op or "*"
        elif op_token["val"] < 0:
            total += op_token["val"]
            primary_op = primary_op or "-"
        else:
            return None, None
        cursor = op_token["end"]
    return total, primary_op


def _check_statement_formula(text: str) -> Optional[dict]:
    """단일 문장/절에서 산식(등호식 또는 서술형 산식)을 파싱하여 계산 불일치 여부를 검사한다."""
    # M7: 상대방 주장 인용 및 가정 문맥 가드
    if CLAIM_QUOTE_GUARD_RE.search(text):
        return None
    tokens = _extract_formula_tokens(text)
    if len(tokens) < 3:
        return None
    
    # 1. 등호('=')가 존재하는 산식 처리
    if "=" in text:
        eq_pos = text.rfind("=")
        cs = _operand_clause_start(text, tokens, eq_pos)
        ops = [t for t in tokens if cs <= t["start"] and t["end"] <= eq_pos]
        res = [t for t in tokens if t["start"] >= eq_pos]
        if not ops or not res or len(ops) < 2:
            return None
        res_token = res[0]
        ops = _drop_quantity_labels(ops, res_token, text)
        
        # M4: 동일 절 및 글자 수 상한 검증 (연산부~결과부 70자 이내)
        between_all = text[ops[0]["start"]:res_token["end"]]
        if len(between_all) > 70:
            return None
        # M7: 정당한 차이 가드 (근사치, 범위, 세액/이자 등)
        context_window = text[max(0, ops[0]["start"] - 10):min(len(text), res_token["end"] + 10)]
        if APPROX_GUARD_RE.search(context_window) or RANGE_GUARD_RE.search(context_window) or TAX_DEDUCTION_GUARD_RE.search(context_window):
            return None
            
        after_ops = text[ops[-1]["end"]:eq_pos]
        computed, op_type = _evaluate_formula_operands(ops, text, after_ops)
        if computed is None or op_type is None:
            return None
        # 단위 일치 및 차원 호환성 검증
        if not _units_ok(ops, res_token, op_type):
            return None
        if abs(computed - res_token["val"]) > Decimal("0.01"):
            formula_snippet = text[ops[0]["start"]:res_token["end"]].strip()
            return {"computed": computed, "stated": res_token["val"], "formula": formula_snippet,
                    "unit": res_token["unit"]}
        return None

    # 2. 서술어로 연결된 산식 처리 (M4: 결과 연결 표지 엄격화)
    res_token = tokens[-1]
    cs = _operand_clause_start(text, tokens[:-1], res_token["start"])
    ops = [t for t in tokens[:-1] if t["start"] >= cs]
    # 연산 서술어('더하면'·'빼면' 등) 뒤, 결과 앞의 수('1분기 신고 건수는'의 '1분기')는 결과 이름표의 일부이지 피연산자가 아니다
    # 피연산자 사이에 오는 '곱하기' 같은 중위 서술어는 제외하고, 그 앞에 피연산자가 2개 이상 남을 때만 거른다(기존 중위 산식 보존)
    if ops:
        pred_in = [m for m in _OP_PREDICATE_RE.finditer(text, ops[0]["start"], res_token["start"])
                   if not m.group(0).endswith("기")]
        if pred_in:
            before = [t for t in ops if t["start"] < pred_in[-1].start()]
            if len(before) >= 2:
                ops = before
    ops = _drop_quantity_labels(ops, res_token, text)
    if len(ops) < 2:
        return None
    between_all = text[ops[0]["start"]:res_token["end"]]
    if len(between_all) > 70:
        return None
    context_window = text[max(0, ops[0]["start"] - 10):min(len(text), res_token["end"] + 10)]
    if APPROX_GUARD_RE.search(context_window) or RANGE_GUARD_RE.search(context_window) or TAX_DEDUCTION_GUARD_RE.search(context_window):
        return None

    after_ops = text[ops[-1]["end"]:res_token["start"]]
    # 서술형은 결과 앞에 연산 서술어나 합계 표지가 있고, 그 사이에 절 경계가 없을 때만 본다(평가 측 보완 F7, 메모 M4)
    result_noun = _OP_RESULT_NOUN_RE.search(after_ops)
    if not (_OP_PREDICATE_RE.search(text[ops[0]["start"]:res_token["start"]]) or _TOTAL_MARK_RE.search(after_ops)
            or result_noun):
        return None
    pred_matches = list(_OP_PREDICATE_RE.finditer(after_ops))
    if pred_matches:
        pred_end = pred_matches[-1].end()
        clause_break = _CLAUSE_BREAK_RE.search(after_ops[:pred_end]) or _VERBAL_CLAUSE_BREAK_RE.search(after_ops[pred_end:])
    else:
        clause_break = _CLAUSE_BREAK_RE.search(after_ops)
    if clause_break and not result_noun:
        return None
    computed, op_type = _evaluate_formula_operands(ops, text, after_ops)
    if computed is None or op_type is None:
        return None
    if not _units_ok(ops, res_token, op_type):
        return None
    if abs(computed - res_token["val"]) > Decimal("0.01"):
        formula_snippet = text[ops[0]["start"]:res_token["end"]].strip()
        return {"computed": computed, "stated": res_token["val"], "formula": formula_snippet,
                "unit": res_token["unit"]}
    return None


class CalculationEngine:
    """문서에서 합계 진술을 찾아 세부 금액과 검산한다."""

    def verify_document(self, doc: NormalizedDocument) -> List[Finding]:
        findings: List[Finding] = []
        seen_blocks: set = set()
        for block in doc.body_blocks():
            if block.block_type == "table" or block.attributes.get("table_ref"):
                continue  # 표는 _verify_table_totals에서 행 단위로 검산한다
            found = self._verify_block(doc, block)
            if found:
                seen_blocks.add(block.block_id)
            findings.extend(found)
        findings.extend(self._verify_table_totals(doc))
        # 한 행·한 열 안의 표준 산식(공급가액+세액=합계, 원금+이자−변제=잔액, 지급총액−공제=실지급액)
        from .table_formulas import formula_graph_findings

        findings.extend(formula_graph_findings(doc))
        # 실무 서면은 항목이 줄마다 나뉘므로 줄 단위 내역-합계도 검산한다
        findings.extend(self._verify_line_items(doc, seen_blocks))
        # 본문 서술형 산식 및 일반 단위 산식 검산 추가 (TK-76 3주기 1항)
        findings.extend(self._verify_statement_formulas(doc))
        findings = self._deduplicate_totals(merge_same_total(findings))
        findings.extend(self._verify_percentages(doc, findings))
        from .claim_amounts import claim_amount_findings

        findings.extend(claim_amount_findings(doc))
        return findings

    def _deduplicate_totals(self, findings: List[Finding]) -> List[Finding]:
        """합계 검산 중복 제거: 중복·부분 판정 없이 가장 정확하고 포괄적인 한 건만 채택한다(과제 7)."""
        calc_findings: List[Finding] = []
        other_findings: List[Finding] = []
        for f in findings:
            if f.type == FindingType.ARITHMETIC_MISMATCH and (f.confidence_features or {}).get("stated"):
                calc_findings.append(f)
            else:
                other_findings.append(f)

        if len(calc_findings) <= 1:
            return findings

        # 세부 항목 수가 많고(가장 포괄적 검산), 심각도가 높은 것 우선 정렬
        calc_findings.sort(
            key=lambda x: (
                -int((x.confidence_features or {}).get("item_count", 0)),
                -x.severity.rank,
            )
        )

        kept: List[Finding] = []
        for cand in calc_findings:
            cand_feat = cand.confidence_features or {}
            cand_stated = cand_feat.get("stated")
            cand_page = cand.page
            cand_rows = set(cand_feat.get("rows_used") or [])

            duplicate = False
            for existing in kept:
                if _calculation_scope(cand) != _calculation_scope(existing):
                    continue
                ex_feat = existing.confidence_features or {}
                ex_stated = ex_feat.get("stated")
                ex_page = existing.page
                ex_rows = set(ex_feat.get("rows_used") or [])

                # 1) 같은 페이지에서 동일한 stated 금액을 검산한 경우 -> 중복
                if cand_page == ex_page and cand_stated == ex_stated:
                    duplicate = True
                    break
                # 2) rows_used가 서로 포함관계(subset)인 경우 -> 부분 판정이므로 이미 더 큰 쪽이 채택됨
                if cand_page == ex_page and cand_rows and ex_rows:
                    if cand_rows.issubset(ex_rows) or ex_rows.issubset(cand_rows):
                        duplicate = True
                        break

            if not duplicate:
                kept.append(cand)

        return other_findings + kept

    def _verify_percentages(self, doc: NormalizedDocument, totals: List[Finding]) -> List[Finding]:
        """비율(%) 열을 금액 열로 다시 계산한다(v5 3-3). 비율은 합계에서 나온 파생 수치이므로, 틀린 비율이 기재 합계
        기준으로는 맞으면 원인을 합계 칸 오류로 연결하고, 어느 기준으로도 맞지 않으면 비율 자체의 계산 오류로 본다."""
        out: List[Finding] = []
        for table_index, table in enumerate(doc.structure.get("tables") or []):
            cells = [[str(c or "").strip() for c in row] for row in table.get("cells") or []]
            if len(cells) < 3:
                continue
            header = cells[0]
            width = max(len(r) for r in cells)
            pct_share = [sum(1 for r in cells[1:] if i < len(r) and PERCENT_RE.search(r[i])) for i in range(width)]
            pct_cols = [i for i, h in enumerate(header) if PERCENT_HEADER_RE.search(h)] or \
                       [i for i in range(width) if pct_share[i] >= max(2, (len(cells) - 1) // 2)]
            if not pct_cols:
                continue
            pct_col = pct_cols[0]
            header_pct = pct_col < len(header) and bool(PERCENT_HEADER_RE.search(header[pct_col]))
            amount_cols = [i for i, h in enumerate(header) if AMOUNT_HEADER_RE.search(h) and i != pct_col]
            if not amount_cols:
                counts = [sum(1 for r in cells[1:] if i < len(r) and (parse_amounts(r[i]) or parse_cell_amount(r[i])))
                          if i != pct_col else -1
                          for i in range(width)]
                amount_cols = [max(range(width), key=lambda i: (counts[i], i))] if max(counts) > 0 else []
            if not amount_cols:
                continue
            col = amount_cols[-1]
            items, stated = [], None
            for row in cells[1:]:
                if col >= len(row) or pct_col >= len(row):
                    continue
                amount = parse_amounts(row[col])
                if not amount:
                    cell_amount = parse_cell_amount(row[col])   # 머리글에 단위가 있는 표 칸('1,200,000', TK-146)
                    amount = [cell_amount] if cell_amount else []
                if not amount:
                    continue
                if row and TOTAL_LABEL_RE.fullmatch(row[0].replace(" ", "")):
                    stated = amount[-1].value
                    continue
                pct = PERCENT_RE.search(row[pct_col])
                if not pct and header_pct:
                    # 머리글이 비율(%) 열이면 칸에 % 기호가 없는 수도 비율이다(TK-146)
                    pct = _BARE_PERCENT_RE.fullmatch(row[pct_col].replace(" ", ""))
                if pct:
                    items.append((row[0], amount[-1].value, Decimal(pct.group("num")), pct.group("num")))
            computed = sum((value for _, value, _, _ in items), Decimal(0))
            if len(items) < 2 or computed <= 0:
                continue
            wrong, derived = [], []
            for label, value, pct, raw in items:
                decimals = len(raw.split(".")[1]) if "." in raw else 0
                tolerance = Decimal("0.5") * (Decimal(10) ** -decimals) + Decimal("0.001")
                by_sum = value / computed * 100
                if abs(pct - by_sum) <= tolerance:
                    continue
                if stated and stated != computed and abs(pct - value / stated * 100) <= tolerance:
                    derived.append(f"{label}: {raw}% (기재 합계 기준 {value / stated * 100:.2f}%, 세부 합산 기준 {by_sum:.2f}%)")
                else:
                    wrong.append(f"{label}: 기재 {raw}% / 계산 {by_sum:.2f}%")
            if not (wrong or derived):
                continue
            table_ref = table.get("table_ref") or f"table-{table_index}"
            cause = next((f for f in totals if f.confidence_features.get("stated") == str(stated)
                          and f.confidence_features.get("table_ref") == table_ref
                          and f.confidence_features.get("table_column") == col), None) if derived else None
            if cause is not None:
                cause.confidence_features.setdefault("derived_effects", []).extend(derived)
            features = {"arithmetic_proof": True, "deterministic_rule": True, "rule_id": "CALC.PERCENT_MISMATCH",
                        "rows": wrong + derived, "computed_total": str(computed),
                        "stated_total": str(stated) if stated is not None else None,
                        "cause": "STATED_TOTAL" if derived and not wrong else "PERCENT_CALCULATION",
                        "cause_finding": cause.finding_id if cause is not None else None}
            title = ("비율(%)이 틀린 합계를 기준으로 계산되었다(원인: 합계 칸 오류)" if derived and not wrong
                     else "비율(%)이 금액으로 다시 계산한 값과 다르다")
            out.append(Finding.create(
                type=FindingType.ARITHMETIC_MISMATCH, status=VerificationStatus.CONTRADICTED, severity=Severity.MEDIUM,
                evidence_grade=EvidenceGrade.A, title=title,
                detail=("비율 열을 금액 열로 다시 계산했다(세부 합산 " + f"{computed:,}원). " + "; ".join((wrong + derived)[:6])
                        + (f". 비율은 기재 합계 {stated:,}원 기준으로 맞으므로 원인은 합계 칸이다." if derived and not wrong else "")),
                confidence=confidence_score(features), confidence_features=features, document_id=doc.document_id,
                page=table.get("page"), engine=ENGINE_NAME, tags=["CALCULATION", "PERCENT"],
                evidence=[Evidence.create(description="비율 열", grade=EvidenceGrade.A, document_id=doc.document_id,
                                          page=table.get("page"), excerpt="; ".join(wrong + derived)[:300])]))
        return out

    def _verify_line_items(self, doc: NormalizedDocument, seen_blocks: set) -> List[Finding]:
        """연속된 금액 줄 다음에 오는 합계 줄을 검산한다.

        같은 면에서 금액이 하나씩 적힌 줄이 연이어 나오고 그 뒤에 합계 줄이 오는
        서면 표준 형식을 대상으로 한다. 중간에 금액 없는 줄이 끼면 묶음을 끊어
        서로 무관한 금액을 합산하지 않는다.
        """
        findings: List[Finding] = []
        for page in doc.pages:
            blocks = [
                b for b in page.blocks
                if b.visible and b.block_type != "table" and b.text.strip()
                and not b.attributes.get("table_ref")
                and b.source_layer in ("visible_text", "ocr_layer")
            ]
            run: List[Amount] = []
            for block in blocks:
                if block.block_id in seen_blocks:
                    run = []
                    continue
                amounts = parse_amounts(block.text, block_id=block.block_id, page=block.page)
                is_total = bool(TOTAL_LABEL_RE.search(block.text))

                if is_total and amounts and len(run) >= MIN_LINE_ITEMS:
                    check = check_sum([a for a, _ in run], amounts[-1])
                    check.rows = [label for _, label in run]
                    if not check.matches:
                        excerpt = "\n".join(
                            [label for _, label in run] + [f"{TOTAL_LABEL_RE.search(block.text).group(0)} {amounts[-1].raw}"]
                        )
                        findings.append(self._mismatch_finding(doc, check, block.block_id, block.page, excerpt))
                    run = []
                    continue

                # 행마다 최종 금액을 쓴다. 산식 행('a원 + b원 = c원')은 '=' 뒤 금액을 쓰고 산식은 따로 검산한다(J3).
                final, formula = row_final_amount(block.text) if amounts else (None, None)
                if formula is not None and not formula.matches:
                    findings.append(self._formula_finding(doc, formula, block.block_id, block.page, block.text))
                if is_total:
                    run = []
                elif final is not None:
                    final.block_id, final.page = block.block_id, block.page
                    run.append((final, " ".join(block.text.split())[:120]))
                else:
                    run = []  # 금액 없는 줄이나 최종 금액을 가를 수 없는 줄에서 묶음을 끊는다
        return findings

    def _verify_statement_formulas(self, doc: NormalizedDocument) -> List[Finding]:
        """본문 서술형 산식 및 일반 단위 산식을 검산한다 (TK-76 3주기 1항).
        
        서술어 연결형 곱셈/덧셈/뺄셈, 비금액 일반 단위 산식, 결과 앞 이름표 부착 산식을 검증하여
        산술 계산 오차 발생 시 ARITHMETIC_MISMATCH 판정을 생성한다.
        """
        findings: List[Finding] = []
        seen_checks: set = set()
        for block in doc.body_blocks():
            if block.block_type == "table" or block.attributes.get("table_ref"):
                continue
            text = block.text.strip()
            if not text:
                continue
            # 문장 및 절 단위 분리 (문장 부호 및 줄바꿈 기준)
            sentences = re.split(r"(?<=[.?!;\n])\s+", text)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                result = _check_statement_formula(sentence)
                if result is not None:
                    key = (block.page, result["stated"], result["computed"])
                    if key in seen_checks:
                        continue
                    seen_checks.add(key)
                    check = CalculationCheck(
                        kind="FORMULA" if result.get("unit") in (None, "원") else "QUANTITY_FORMULA",
                        stated=result["stated"],
                        computed=result["computed"],
                        detail=f"산식 '{result['formula']}'의 계산값 {result['computed']:,} / 기재 {result['stated']:,}",
                    )
                    findings.append(self._formula_finding(doc, check, block.block_id, block.page, sentence))
        return findings

    def _verify_block(self, doc: NormalizedDocument, block) -> List[Finding]:
        text = block.text
        if not TOTAL_LABEL_RE.search(text):
            return []
        amounts = parse_amounts(text, block_id=block.block_id, page=block.page)
        if len(amounts) < 3:
            return []
        total_match = TOTAL_LABEL_RE.search(text)
        assert total_match is not None
        after = [a for a in amounts if a.start >= total_match.start()]
        before = [a for a in amounts if a.start < total_match.start()]
        # 합계가 속한 문단(직전 빈 줄 이후)으로 묶음을 한정하여 무관한 앞 문단(청구취지 등)을 합산하지 않는다
        prefix = text[:total_match.start()]
        last_break = prefix.rfind("\n\n")
        section_start = (last_break + 2) if last_break != -1 else 0
        section_before = [a for a in before if a.start >= section_start]
        if not after or len(section_before) < 2:
            return []
        # 뺄셈·곱셈 서술('…에서 …을 빼면 실지급액은 …')은 합계가 아니다 — 산식 검산(_verify_prose_formulas)이 맡는다(평가 측 보완 N2)
        if re.search(f"{_SUB_PRED}|{_MUL_PRED}", text[section_start:total_match.start()]):
            return []
        stated = after[0]
        check = check_sum(section_before, stated)
        if check.matches:
            return []
        return [self._mismatch_finding(doc, check, block.block_id, block.page, text[section_start:])]

    def _verify_cell_tables(self, doc: NormalizedDocument) -> Tuple[List[Finding], set]:
        """셀 단위 표: 모든 금액 열에 대해 세로 합산(지급총액, 공제계, 합계 등)과 실지급액 산식을 검산한다."""
        findings: List[Finding] = []
        handled = set()

        raw_tables = doc.structure.get("tables") or []
        if not raw_tables:
            return findings, handled

        # 열 수가 같다는 것만으로는 이어지는 표가 아니다. 위치·열 너비 비율·헤더 상태·이어짐 표지를 모두 갖춘
        # 연속 표만 가상 결합 표로 검산하고(table_continuation), 그 구성 표는 따로 검산하지 않는다. 구성 표를
        # 따로 검산하면 마지막 쪽의 최종 합계가 그 쪽 행만의 합으로 비교되어 오탐이 된다.
        from .table_continuation import find_continuations, possible_continuations

        chains = find_continuations(raw_tables, doc)
        uncertain = possible_continuations(raw_tables, doc)
        chained = {ref for chain in chains for ref in chain["members"]}
        tables_to_check = []
        for index, t in enumerate(raw_tables):
            ref = t.get("table_ref") or f"table-{index}"
            if ref in chained:
                continue
            tables_to_check.append({
                "page": t.get("page"),
                "table_ref": ref,
                "cells": [[str(c or "").strip() for c in row] for row in t.get("cells") or []],
            })
        for chain in chains:
            tables_to_check.append({"page": chain["page"], "table_ref": chain["table_ref"], "cells": chain["cells"],
                                    "continuation": {"members": chain["members"], "pages": chain["pages"],
                                                     "evidence": chain["evidence"]}})

        for table in tables_to_check:
            cells = table.get("cells") or []
            if len(cells) < 3:
                continue
            header = cells[0]
            col_count = len(header)

            # 금액이 존재하는 모든 데이터 열 탐색
            candidate_cols = []
            for col_idx in range(1, col_count):
                if PERCENT_HEADER_RE.search(header[col_idx]):
                    continue                     # 비율 열은 금액 합계 검산 대상이 아니다(비율 검사가 따로 본다, TK-146)
                amounts_in_col = sum(1 for r in cells[1:] if col_idx < len(r) and parse_cell_amount(r[col_idx]))
                if amounts_in_col >= 2:
                    candidate_cols.append(col_idx)

            if not candidate_cols:
                continue

            for col in candidate_cols:
                first_finding = len(findings)
                col_header_name = header[col] if col < len(header) else f"열 {col}"
                total_rows = [r for r in cells[1:] if r and is_total_label(r[0])]
                grand = total_rows[-1] if total_rows else None
                top: List[Amount] = []
                segment: List[Tuple[Amount, str]] = []
                subtotals: Dict[str, Amount] = {}
                grand_checked = False

                for row in cells[1:]:
                    if col >= len(row):
                        continue
                    row_label = row[0].strip()
                    cell_text = row[col].strip()
                    final, formula = row_cell_final_amount(cell_text)

                    # 산식 행 검산
                    for index, cell in enumerate(row):
                        if index == col or not cell or not parse_cell_amount(cell):
                            continue
                        val = evaluate_expression(cell.split("=")[0]) if "=" in cell or OPERATOR_RE.search(cell) else None
                        if final and val is not None and abs(val - final.value) > TOLERANCE:
                            chk = CalculationCheck(
                                kind="FORMULA", stated=final.value, computed=val,
                                detail=f"'{row_label}' 행 산식 '{cell}'의 계산값 {val:,} / 금액 칸 {final.value:,}"
                            )
                            findings.append(self._formula_finding(doc, chk, None, table.get("page"), " | ".join(row)))

                    if final is None:
                        continue

                    if any(row is r for r in total_rows):
                        # 1) 실지급액/차인지급액 산식 검증 (지급총액 - 공제계 = 실지급액)
                        if any(k in row_label for k in ["실지급", "차인지급", "총수령"]):
                            pay_total = next((v.value for k, v in subtotals.items() if any(p in k for p in ["지급", "총액", "기본"])), None)
                            ded_total = next((v.value for k, v in subtotals.items() if any(d in k for d in ["공제", "세금", "보험"])), None)
                            if pay_total is not None and ded_total is not None:
                                expected_net = pay_total - ded_total
                                if abs(final.value - expected_net) > TOLERANCE:
                                    chk_net = CalculationCheck(
                                        kind="NET_PAY", stated=final.value, computed=expected_net,
                                        detail=f"[{col_header_name}] 실지급액 산식(지급총액 {pay_total:,} - 공제계 {ded_total:,} = {expected_net:,}) / 기재 {final.value:,}"
                                    )
                                    findings.append(self._mismatch_finding(
                                        doc, chk_net, None, table.get("page"),
                                        "\n".join(" | ".join(r) for r in cells), label=f"{col_header_name} {row_label}"
                                    ))
                            # Net pay is a subtraction, not a sum of the preceding subtotals.
                            grand_checked = grand_checked or row is grand
                            continue

                        rows_used = [label for _, label in segment]
                        items = top + [a for a, _ in segment] if row is grand else [a for a, _ in segment]
                        if row is grand:
                            rows_used = [f"{a.raw}" for a in top] + rows_used
                        if len(items) >= 2:
                            check = check_sum(items, final)
                            check.rows = rows_used
                            if not check.matches:
                                excerpt = "\n".join(" | ".join(r) for r in cells)
                                label = "합계" if row is grand else f"{col_header_name} {row_label}"
                                findings.append(self._mismatch_finding(doc, check, None, table.get("page"), excerpt,
                                                                       label=label))
                            grand_checked = grand_checked or row is grand
                        if row is not grand:
                            top.append(final)  # 소계는 위 단계에서 한 항목이 된다
                            segment = []
                        subtotals[row_label] = final
                        continue

                    segment.append((final, f"{row_label}: {final.raw}"))

                if grand_checked:
                    handled.add(table.get("table_ref"))
                    handled.update((table.get("continuation") or {}).get("members") or [])
                for finding in findings[first_finding:]:
                    finding.confidence_features.update(table_ref=table["table_ref"], table_column=col)
                    if table["table_ref"] in uncertain and finding.title.startswith("합계가"):
                        # 앞 쪽 표와 형태·헤더는 이어지나 이어짐 표지가 없다: 최종 합계에 앞 쪽 행이 들어 있을 수 있어 확정 불가
                        finding.status = VerificationStatus.UNVERIFIED
                        finding.evidence_grade = EvidenceGrade.C
                        finding.advisory_only = True
                        finding.confidence_features["possible_continuation"] = uncertain[table["table_ref"]]
                        finding.detail += (f" 다만 이 표는 앞 쪽 표({uncertain[table['table_ref']]['from']})와 열 구조·헤더가 "
                                           "이어지나 '계속' 표지·이월 행·순번 연속이 없어 연속 표인지 확인되지 않는다. 앞 쪽 행이 "
                                           "합계에 포함되었을 수 있으므로 원본에서 표의 범위를 확인해야 한다.")
                    if table.get("continuation"):
                        # 가상 결합 표의 판정: 구성 표·쪽과 결합 근거를 남긴다(원래 table_ref는 그대로 유지)
                        finding.confidence_features["continuation"] = table["continuation"]
                        pages = table["continuation"]["pages"]
                        finding.detail += (f" 이 표는 {pages[0]}~{pages[-1]}쪽에 걸친 연속 표로 식별해 결합 검산했다"
                                           f"(구성 표 {', '.join(table['continuation']['members'])}).")

        return findings, handled

    def _verify_table_totals(self, doc: NormalizedDocument) -> List[Finding]:
        """표 블록에서 '합계' 행과 나머지 행의 금액을 대조한다."""
        findings, handled = self._verify_cell_tables(doc)
        for block in doc.blocks:
            if block.block_type != "table" or not block.visible:
                continue
            if block.attributes.get("table_ref") in handled:
                continue
            rows = [r for r in block.text.splitlines() if r.strip()]
            if len(rows) < 3:
                continue
            total_rows = [r for r in rows if TOTAL_LABEL_RE.search(r)]
            item_rows = [r for r in rows if not TOTAL_LABEL_RE.search(r)]
            if not total_rows:
                continue
            total_amounts = parse_amounts(total_rows[-1], block_id=block.block_id, page=block.page)
            if not total_amounts:
                continue
            items: List[Amount] = []
            for row in item_rows:
                row_amounts = parse_amounts(row, block_id=block.block_id, page=block.page)
                if row_amounts:
                    items.append(row_amounts[-1])
            if len(items) < 2:
                continue
            check = check_sum(items, total_amounts[-1])
            if not check.matches:
                findings.append(self._mismatch_finding(doc, check, block.block_id, block.page, block.text))
        return findings

    @staticmethod
    def _formula_finding(doc: NormalizedDocument, check: CalculationCheck, block_id, page, excerpt: str) -> Finding:
        difference = check.stated - check.computed
        features = {"arithmetic_proof": True, "deterministic_rule": True, "stated": str(check.stated),
                    "computed": str(check.computed), "difference": str(difference), "kind": "FORMULA",
                    "rule_id": "CALC.FORMULA"}
        return Finding.create(
            type=FindingType.ARITHMETIC_MISMATCH, status=VerificationStatus.CONTRADICTED, severity=Severity.HIGH,
            evidence_grade=EvidenceGrade.A,
            title=(f"산식의 계산 결과가 기재 금액과 다르다 (차이 {difference:,}원)" if check.kind != "QUANTITY_FORMULA"
                   else f"산식의 계산 결과가 기재 수치와 다르다 (차이 {difference:,})"),
            detail=f"{check.detail}. Python 계산엔진으로 검산한 결정론적 결과이다.",
            confidence=confidence_score(features), confidence_features=features, document_id=doc.document_id,
            block_id=block_id, page=page, engine=ENGINE_NAME, tags=["CALCULATION"],
            evidence=[Evidence.create(description="산식이 적힌 행", grade=EvidenceGrade.A, document_id=doc.document_id,
                                      block_id=block_id, page=page, excerpt=excerpt[:300])])

    @staticmethod
    def _mismatch_finding(doc: NormalizedDocument, check: CalculationCheck, block_id, page, excerpt: str,
                          label: str = "합계") -> Finding:
        difference = check.stated - check.computed
        features = {
            "arithmetic_proof": True,
            "deterministic_rule": True,
            "stated": str(check.stated),
            "computed": str(check.computed),
            "difference": str(difference),
            "item_count": len(check.items),
            # 판정 근거에 쓴 행(J3). 산식 행은 '=' 뒤 최종 금액으로 셌다.
            "rows_used": list(getattr(check, "rows", []) or [f"{a.raw}" for a in check.items]),
        }
        return Finding.create(
            type=FindingType.ARITHMETIC_MISMATCH,
            status=VerificationStatus.CONTRADICTED,
            severity=Severity.HIGH if abs(difference) > check.computed * Decimal("0.01") else Severity.MEDIUM,
            evidence_grade=EvidenceGrade.A,
            title=f"{label}가 세부 금액 합산값과 다르다 (차이 {difference:,}원)",
            detail=(
                f"{check.detail}. 차액 {difference:,}원. "
                "Python 계산엔진으로 검산한 결정론적 결과이다."
            ),
            confidence=confidence_score(features),
            confidence_features=features,
            document_id=doc.document_id,
            block_id=block_id,
            page=page,
            engine=ENGINE_NAME,
            tags=["CALCULATION"],
            evidence=[
                Evidence.create(
                    description="검산 대상 구간",
                    grade=EvidenceGrade.A,
                    document_id=doc.document_id,
                    block_id=block_id,
                    page=page,
                    excerpt=excerpt[:400],
                ),
                Evidence.create(
                    description="세부 금액",
                    grade=EvidenceGrade.A,
                    excerpt=", ".join(f"{a.raw}({a.value:,})" for a in check.items[:10]),
                ),
            ],
        )


# 셀 표의 합계 행 이름. 행 이름 '전체'가 합계 표현이어야 한다('설계비'·'계약금'·'회계감사비'의 '계'는 합계가 아니다).
_TOTAL_WORD = r"(?:합계|총계|소계|총액|총금액|총합계|지급총액|공제총액|공제합계)(?:액|금액)?"
TOTAL_CELL_LABEL_RE = re.compile(
    rf"^(?:[가-힣A-Za-z0-9·ㆍ.,~\-]{{0,10}}?{_TOTAL_WORD}|계|지급계|공제계|실지급액|차인지급액|총수령액)$")


def is_total_label(label: str) -> bool:
    """셀 표 첫 칸이 합계·소계 행 이름인가. 괄호·공백·콜론은 무시한다('합 계', '소계(1)', '1월분 합계')."""
    compact = re.sub(r"[\s()（）\[\]:：]", "", str(label or ""))
    compact = re.sub(r"\d+$", "", compact) if not compact.isdigit() else compact
    return bool(TOTAL_CELL_LABEL_RE.match(compact))


def _calculation_scope(finding: Finding) -> tuple:
    features = finding.confidence_features or {}
    return (finding.document_id, finding.page, features.get("table_ref") or finding.block_id,
            features.get("table_column"))


def merge_same_total(findings: List[Finding]) -> List[Finding]:
    """같은 합계(기재 금액이 같은 합계 칸)에 대한 합산 판정은 하나만 남긴다(v5 3-5).

    표를 칸 단위로 읽은 판정과 줄 단위로 읽은 판정이 함께 나오면, 줄 단위 쪽은 표 일부만 더해 차액이 틀린다.
    세부 항목을 가장 많이 포함한 판정을 남기고, 나머지는 근거(merged_partial_checks)로만 붙인다.
    """
    groups: dict = {}
    order: List[Finding] = []
    for finding in findings:
        features = finding.confidence_features or {}
        if finding.type != FindingType.ARITHMETIC_MISMATCH or features.get("kind") == "FORMULA" or "stated" not in features \
                or features.get("rule_id") not in (None, "CALC.SUM"):
            order.append(finding)
            continue
        key = (*_calculation_scope(finding), features["stated"])
        if key in groups:
            groups[key].append(finding)
            continue
        groups[key] = [finding]
        order.append(finding)
    out: List[Finding] = []
    for finding in order:
        group = groups.get((*_calculation_scope(finding), (finding.confidence_features or {}).get("stated")))
        if not group or group[0] is not finding:
            out.append(finding)
            continue
        best = max(group, key=lambda f: int(f.confidence_features.get("item_count") or 0))
        others = [f for f in group if f is not best]
        if others:
            best.confidence_features["merged_partial_checks"] = [
                {"computed": f.confidence_features.get("computed"), "item_count": f.confidence_features.get("item_count"),
                 "title": f.title} for f in others]
        out.append(best)
    return out
