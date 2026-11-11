# -*- coding: utf-8 -*-
"""TK-139 처분기준 별표 대조 1유형 모듈 (W1~W5, G1~G4 엄수).

- W1: 업종 절 일치 (서면의 영업 종류 결정론적 일치, 업종 절 안에서만 행 매칭)
- W2: 단위 환산 금지 (개월->일수 환산 금지, 같은 단위끼리만 비교하고 다르면 UNVERIFIED)
- W3: 병합 셀 전파 (파서의 merges·covered를 사용해 대분류·근거 법령을 하위 행으로 전파)
- W4: www.law.go.kr 고정 도메인 다운로드, 크기 상한 2.0MB, 타임아웃 5.0초
- W5: 서면의 처분 문구 포함 문장 내 위반 사실 절 대상 2-gram Jaccard >= 0.60, 격차 >= 0.20
- G1~G4: 행 오연결 0, 단위/각주 누락 0, 구버전 혼동 0, 불완전 표 확정 판정 0
- 결과 성격: 순수 검토 자료 (advisory_only: True, finding 승격 금지)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

# 처분 문구 정규식: '영업정지 15일', '영업정지 2개월' 등
DISPOSITION_RE = re.compile(r"영업정지\s*(?P<val>\d+)\s*(?P<unit>일|월|개월)")

# 위반 차수 정규식: '1차 위반', '첫 번째 위반', '2차 처분' 등
VIOLATION_ORDER_RE = re.compile(r"(?P<ord>[12345]|일|이|삼|첫|두|세)\s*(?:차|번째)\s*(?:위반|처분)?")

ORDER_MAP = {
    "1": 1, "일": 1, "첫": 1,
    "2": 2, "이": 2, "두": 2,
    "3": 3, "삼": 3, "세": 3,
    "4": 4, "5": 5,
}

# 업종 키워드 분류 매핑 (W1)
INDUSTRY_PATTERNS = [
    ("식품제조·가공업", re.compile(r"식품제조[\s·]*가공업|식품제조업|제조가공업")),
    ("식품접객업", re.compile(r"식품접객업|일반음식점|휴게음식점|단란주점|유흥주점|위탁급식|제과점")),
    ("즉석판매제조·가공업", re.compile(r"즉석판매제조[\s·]*가공업|즉석판매")),
    ("식품소분·판매업", re.compile(r"식품소분[\s·]*판매업|기타식품판매업|유통전문판매업")),
]


def char_2grams(text: str) -> Set[str]:
    """문자열에서 공백과 문장부호를 제거하고 문자 단위 2-gram 집합을 반환한다 (Q5, W5)."""
    cleaned = re.sub(r"[\s\.,·ㆍ「」\(\)\[\]\-~_]+", "", text)
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def jaccard_similarity(a: str, b: str) -> float:
    """두 문자열 간의 문자 단위 bigram Jaccard 유사도를 계산한다."""
    set_a = char_2grams(a)
    set_b = char_2grams(b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return round(inter / union, 4) if union > 0 else 0.0

_REASON_RE = re.compile(r"(?:다는|였다는|했다는|라는|다고)?\s*(?:이유|사유|까닭)(?:로|에서)|(?:다|였다|했다)고\s*하여|(?:다|이라)며|함에\s*따라")
_ACTOR_BOUNDARY_RE = re.compile(r"(?:^|\s)[가-힣]*(?:피고|행정청|처분청|청장|시장|군수|구청장)(?:은|는|이|가)\s+")
_PARTY_SUBJECT_RE = re.compile(r"(?:^|\s)(?:원고|신청인|청구인)(?:가|는|은|이)\s+")


def _reason_clause(sentence: str, raw_disposition: str) -> str:
    pos = sentence.find(raw_disposition)
    before = sentence[:pos] if pos >= 0 else sentence
    # 처분 주체 절(…은/는) 뒤에서 시작해, 그 뒤 첫 '이유·사유' 연결어 앞까지가 위반 사실이다
    actors = list(_ACTOR_BOUNDARY_RE.finditer(before))
    start = actors[-1].end() if actors else 0
    reason = _REASON_RE.search(before, start)
    if not reason:
        return ""
    span = before[start:reason.start()]
    hits = list(_PARTY_SUBJECT_RE.finditer(span))
    if hits:
        span = span[hits[-1].end():]
    span = re.split(r"[,;]", span)[-1]
    return _strip_tail(re.sub(r"(?:하였|했|였|하|았|었)?$", "", span.strip()).strip())


_TAIL_RE = re.compile(r" ?(?:하는 ?)?(?:행위를 ?)?(?:한|하는|된)? ?(?:것|경우)?(?:로서)?$")  # 공백을 한 칸으로 줄인 뒤 적용(J15: 인접 공백 반복 제거)


# 조문 인용구 판별(평가 측 보완 J13, CodeQL py/redos 대응 J15): 중첩 반복 없는 단일 토큰 정규식으로
# '…에 따른' 앞부분이 인용 토큰만으로 이루어졌는지 지워 보고 확인한다(정규식 역추적이 입력 길이에 비례).
_CITE_END_RE = re.compile(r"에 ?(?:따른|의한|규정된)")
_CITE_TOKEN_RE = re.compile(
    r"「[^」]{1,60}」|[가-힣]{0,20}법|시행령|시행규칙|영|규칙|제\d{1,4}조(?:의\d{1,3})?|제?\d{1,3}[항호]|[가-하]목"
    r"|단서|본문|전단|후단|및|또는|[ㆍ·, ]")
_PAREN_RE = re.compile(r"\([^()]{0,200}\)")


def _strip_cite(text: str) -> str:
    """위반 서술 앞의 조문 인용구('법 제N조제M항에 따른')와 괄호 속 부연('(…을 포함한다)')을 뗀다(양쪽 같은 규칙, 평가 측 보완 J13·J14·J15)."""
    out = " ".join(_PAREN_RE.sub("", text).split())
    m = _CITE_END_RE.search(out, 0, 120)
    if m:
        head = out[:m.start()]
        if "제" in head and re.search(r"제\d", head) and not _CITE_TOKEN_RE.sub("", head):
            out = out[m.end():].strip()
    return out or text


def _strip_tail(text: str) -> str:
    """위반 서술 끝의 형식어('…하는 행위를 한 경우'·'…한 것')를 뗀다(양쪽 같은 규칙, 평가 측 보완 J5)."""
    out = _TAIL_RE.sub("", " ".join(text.split())).strip()
    return out or text


_ROW_ENUM_RE = re.compile(r"(?:^|\s)(?:\d+(?:의\d+)?\.|[가-하]\.|\d+\)|[가-하]\))\s")


def _row_core(violation_text: str) -> str:
    """별표 행 위반사항에서 상위 항목('1. 법 제N조를 위반한 경우')과 번호를 떼고 마지막 세목만 남긴다(평가 측 보완 J5)."""
    parts = [p.strip() for p in _ROW_ENUM_RE.split(violation_text) if p and p.strip()]
    return _strip_tail(_strip_cite(parts[-1] if parts else violation_text.strip()))


def extract_document_claim(text: str) -> Optional[Dict[str, Any]]:
    """서면 텍스트에서 처분 문구, 위반 차수, 위반 사실 절 및 업종을 추출한다 (Q4, Q7, W1, W5)."""
    if not text:
        return None

    disp_match = DISPOSITION_RE.search(text)
    if not disp_match:
        return None

    claimed_val = int(disp_match.group("val"))
    raw_unit = disp_match.group("unit")
    claimed_unit = "월" if raw_unit in ("월", "개월") else "일"
    raw_disposition = disp_match.group(0)

    # 처분 문구가 포함된 문장 및 위반 사실 절 추출 (W5)
    start_pos = max(0, disp_match.start() - 300)
    end_pos = min(len(text), disp_match.end() + 150)
    window = text[start_pos:end_pos]

    # 날짜(2023. 5. 1.) 점에 의해 잘리지 않도록 안전한 문장 분할 (온점 뒤 공백+대문자/한글 또는 줄바꿈)
    sentences = re.split(r"(?<=[가-힣\)\'\"\]])\.(?:\s+|$)|[\r\n]+", window)
    matched_sent = next((s for s in sentences if raw_disposition in s), window).strip()

    # 차수 추출: 처분 문장 또는 주변에서 '1차 위반', '첫 번째 위반', '2차 처분' 등
    # 차수는 처분 문장 안의 '[N]차' 꼴에서만 정한다. 없으면 None(평가 측 보완 J4: 1차로 가정하지 않는다)
    claimed_order = None
    ord_match = re.search(r"(?<![0-9가-힣])(?P<ord>[123])\s*차(?:\s*(?:위반|처분))?", matched_sent)
    if ord_match:
        claimed_order = int(ord_match.group("ord"))
    else:
        m_word = re.search(r"(?<![가-힣])(?P<w>첫|두|세)\s*번째\s*(?:위반|처분)", matched_sent)
        if m_word:
            claimed_order = {"첫": 1, "두": 2, "세": 3}[m_word.group("w")]

    # 업종 추출 (W1)
    matched_industry: Optional[str] = None
    industry_hits = []
    for ind_name, ind_pat in INDUSTRY_PATTERNS:
        if ind_pat.search(text):
            industry_hits.append(ind_name)

    if len(industry_hits) == 1:
        matched_industry = industry_hits[0]
    elif len(industry_hits) > 1:
        local_hits = [name for name, pat in INDUSTRY_PATTERNS if pat.search(window)]
        if len(local_hits) == 1:
            matched_industry = local_hits[0]

    # 위반 사실 절(평가 측 보완 J5): 처분 문구 앞에서 마지막 '이유·사유' 연결어 앞 구간을 잡고,
    # 그 구간에서 처분 주체 절(…은/는) 뒤·당사자 주격(원고가/원고는) 뒤만 남긴다. 날짜·차수·행정청 낱말이 섞이지 않게 한다.
    reason_clause = _reason_clause(matched_sent, raw_disposition)
    # 위반 사실 절 추출 (W5):
    # 처분 문구 앞부분 분리
    parts = matched_sent.split(raw_disposition)
    raw_before = parts[0].strip() if parts else matched_sent.strip()

    # 1) 처분 문구 바로 앞의 날짜, 처분/위반 차수 및 행정청 수식어구 제거 (ReDoS 방지를 위해 단순 정규식 루프 처리)
    cleaned_before = raw_before.rstrip()
    for _ in range(5):
        prev = cleaned_before
        # 차수 수식구: '1차 위반에 따른', '2차 처분으로', '첫 번째 처분' 등
        cleaned_before = re.sub(r"(?:[12345]|일|이|삼|첫|두|세)\s*(?:차|번째)?\s*(?:위반|처분)?(?:\s*(?:에\s*따른|으로|로))?\s*$", "", cleaned_before)
        # 날짜 수식구: '2023. 5. 1.자', '2023-05-01자' 등
        cleaned_before = re.sub(r"\d{4}[\.\s-]+\d{1,2}[\.\s-]+\d{1,2}\.?\s*(?:자)?\s*$", "", cleaned_before)
        # 행정청 수식구: '피고로부터', '관할구청으로부터' 등
        cleaned_before = re.sub(r"(?:피고|행정청|관할구청)(?:는|로부터|에게|은)?\s*$", "", cleaned_before)
        cleaned_before = cleaned_before.rstrip()
        if cleaned_before == prev:
            break

    # 2) 절(clause) 단위 분리: 쉼표(,)나 세미콜론(;) 기준으로 원고 지위/업종 절 분리
    clauses = re.split(r"[,;]+", cleaned_before)
    candidate_clauses = []
    for cl in clauses:
        cl_clean = cl.strip()
        if not cl_clean:
            continue
        # 단순히 업종이나 원고 지위만 명시한 절('원고는 서울 마포구에서 일반음식점을 운영하는 자로서') 제외
        is_just_identity = any(ind_pat.search(cl_clean) for _, ind_pat in INDUSTRY_PATTERNS) and (
            "운영" in cl_clean or "영위" in cl_clean or "자로서" in cl_clean or cl_clean.startswith("원고는") or len(cl_clean) <= 15
        )
        if not is_just_identity:
            candidate_clauses.append(cl_clean)

    if candidate_clauses:
        target_clause = candidate_clauses[-1]
    else:
        target_clause = cleaned_before or raw_before

    # 3) 서두의 업종 수식어 제거 (예: '일반음식점에서', '식품접객업소에서')
    for _, ind_pat in INDUSTRY_PATTERNS:
        target_clause = re.sub(
            r"^(?:원고(?:는|가)?\s*)?(?:" + ind_pat.pattern + r")(?:\s*(?:영업소|업소|매장))?(?:에서|을|를|의|은|는|에\s*대해|에\s*대하여)?\s*",
            "",
            target_clause,
        ).strip()

    # 4) 후미의 이유/원인 조사 및 어미 정돈 (예: '...보관하였다는 이유로' -> '...보관', '...위반으로' -> '...위반')
    target_clause = re.sub(
        r"(?:하였다는|했다는|하였다고\s*하여|했다는\s*이유로|하였다는\s*이유로|이유로|인하여|함에\s*따라|하여|으로|로)$",
        "",
        target_clause,
    ).strip()

    if reason_clause:
        target_clause = reason_clause
    return {
        "raw_disposition": raw_disposition,
        "claimed_val": claimed_val,
        "claimed_unit": claimed_unit,
        "claimed_order": claimed_order,
        "violation_clause": target_clause,
        "matched_industry": matched_industry,
        "sentence": matched_sent.strip(),
    }


def parse_and_propagate_table(hwp_bytes: bytes) -> Tuple[Optional[List[Dict[str, Any]]], bool, str]:
    """별표 HWP 바이너리를 파싱하고 병합 셀(merges·covered)을 전파하여 정규화된 행 목록을 생성한다 (W3, G4)."""
    if not hwp_bytes:
        return None, False, "EMPTY_HWP_BYTES"

    from packages.document_engine.hwp_parser import _extract_hwp_table_structures

    warnings: List[str] = []
    try:
        tables, partial, _ = _extract_hwp_table_structures(hwp_bytes, warnings)
    except Exception as exc:
        return None, False, f"HWP_PARSER_EXCEPTION: {type(exc).__name__}"

    if not tables:
        return None, False, "NO_COMPLETE_TABLES_FOUND"

    # 가장 큰 표(행 수가 가장 많은 표)를 행정처분기준 표로 채택
    tables.sort(key=lambda t: t.get("row_count", 0), reverse=True)
    table = tables[0]

    cells = table.get("cells") or []
    if not cells or len(cells) < 3 or len(cells[0]) < 3:
        return None, False, "TABLE_GRID_TOO_SMALL"

    row_count = len(cells)
    col_count = len(cells[0])

    # 1. 2차원 복사본 생성
    grid = [[cells[r][c] for c in range(col_count)] for r in range(row_count)]

    # 2. merges와 covered를 반영하여 앵커 텍스트 전파 (W3)
    covered = table.get("covered") or set()
    merges = table.get("merges") or {}

    # 실제 HWP 파서의 merges는 [{"row","col","row_span","col_span"}, ...] 목록이다(평가 측 보완 J2)
    merge_list = []
    if isinstance(merges, dict):
        merge_list = [(r, c, rs, cs) for (r, c), (rs, cs) in merges.items()]
    else:
        for m in merges:
            if isinstance(m, dict):
                merge_list.append((int(m.get("row", 0)), int(m.get("col", 0)),
                                   int(m.get("row_span", 1)), int(m.get("col_span", 1))))
    for r, c, rspan, cspan in merge_list:
        anchor_val = grid[r][c].strip()
        if not anchor_val:
            continue
        for dr in range(rspan):
            for dc in range(cspan):
                if dr == 0 and dc == 0:
                    continue
                tr, tc = r + dr, c + dc
                if tr < row_count and tc < col_count:
                    # 덮인 칸에 앵커 텍스트 복제 전파
                    if not grid[tr][tc]:
                        grid[tr][tc] = anchor_val

    # 3. 열 역할 식별(평가 측 보완 J3): 전파 전 원본 칸에서, 덮인 칸을 빼고, 칸 전체가 머리글인 것만 본다.
    #    병합된 일반기준 문단(한 칸이 5열을 덮음)에 든 '1차'·'위반' 낱말로 열을 정하지 않는다.
    covered_set = {tuple(x) for x in covered}
    violation_col, law_col = -1, -1
    order_cols = {1: -1, 2: -1, 3: -1}
    header_end = -1
    for r in range(min(15, row_count)):
        for c in range(col_count):
            if (r, c) in covered_set:
                continue
            txt = re.sub(r"\s+", "", cells[r][c] or "")
            if txt in ("위반사항", "위반행위", "위반내용"):
                violation_col, header_end = c, max(header_end, r)
            elif txt in ("근거법령", "근거법조문", "근거규정"):
                law_col = c
            else:
                m_ord = re.fullmatch(r"([123])차(?:위반)?", txt)
                if m_ord:
                    order_cols[int(m_ord.group(1))] = c
                    header_end = max(header_end, r)
    if violation_col == -1 or -1 in order_cols.values():
        return None, False, "HEADER_COLUMNS_NOT_IDENTIFIED"

    # 4. 행별 업종 절 식별 및 정규화 행 목록 생성 (W1)
    # 업종 절 머리는 표 전체 폭을 덮는 병합 행이고 'N. ' 번호로 시작한다(평가 측 보완 J12).
    # 위반사항 칸 문장 속 업종 낱말('…은 2. 식품판매업 등의 …에 따른다')로 절을 바꾸지 않는다.
    full_width_rows = {r for r, c, rs, cs in merge_list if c == 0 and cs >= col_count}
    structured_rows: List[Dict[str, Any]] = []
    current_section: Optional[str] = None

    for r in range(row_count):
        row = grid[r]
        if r in full_width_rows:
            head = re.sub(r"\s+", " ", (cells[r][0] or "")).strip()
            if head.startswith("Ⅲ"):
                current_section = None  # 개별기준 끝(과징금 제외 대상 등)
                continue
            m_sec = re.match(r"^(?:Ⅱ\.\s*개별기준\s*)?\d+\.\s+(\S.*)$", head)
            if m_sec:
                current_section = m_sec.group(1)
            continue
        if current_section is None:
            continue

        violation_text = row[violation_col].strip() if violation_col < col_count else ""
        law_text = row[law_col].strip() if law_col < col_count else ""

        # 위반 내용이 없거나 머리글 행이면 스킵(머리글 이전 행 포함)
        if r <= header_end or not violation_text or any(h in violation_text for h in ("위반사항", "위반내용", "위반행위", "개별기준", "행정처분기준")):
            continue

        c1_text = row[order_cols[1]].strip() if order_cols[1] != -1 and order_cols[1] < col_count else ""
        c2_text = row[order_cols[2]].strip() if order_cols[2] != -1 and order_cols[2] < col_count else ""
        c3_text = row[order_cols[3]].strip() if order_cols[3] != -1 and order_cols[3] < col_count else ""

        structured_rows.append({
            "row_idx": r,
            "industry": current_section,
            "violation_text": violation_text,
            "law_text": law_text,
            "criteria_raw": {1: c1_text, 2: c2_text, 3: c3_text},
        })

    return structured_rows, True, "COMPLETED"


def parse_criteria_value_and_unit(criteria_str: str) -> Optional[Tuple[int, str]]:
    """처분기준 셀 문자열에서 수치와 단위를 추출한다 (W2: 단위 환산 금지)."""
    if not criteria_str:
        return None
    # 처분 종류가 서면과 같은 '영업정지'일 때만 수치를 읽는다('품목류 제조정지 1개월'·'시정명령'은 대조하지 않음, 평가 측 보완 J7)
    m = re.search(r"영업정지\s*(?P<val>\d+)\s*(?P<unit>일|월|개월)", criteria_str)
    if not m:
        return None
    val = int(m.group("val"))
    raw_unit = m.group("unit")
    unit = "월" if raw_unit in ("월", "개월") else "일"
    return (val, unit)


def verify_disposition_criteria(
    doc_text: str,
    appendix_hwp: bytes,
    *,
    case_date: Optional[str] = None,
    law_name: str = "",
    table_title: str = "",
    mst: Optional[str] = None,
    appendix_plain_text: Optional[str] = None,
) -> Dict[str, Any]:
    """처분기준 별표와 서면 주장을 대조하여 결과를 반환한다 (TK-139)."""
    out: Dict[str, Any] = {
        "status": "UNVERIFIED",
        "law_name": law_name,
        "table_title": table_title,
        "version_mst": mst or "",
        "effective_date": case_date or "",
        "matched_row": None,
        "document_claim": None,
        "comparison_result": "UNVERIFIED",
        "advisory_only": True,
        "discretionary_notes": "",
    }

    # G3: 처분일/기준일 미확정 시 즉시 UNVERIFIED (구버전 혼동 원천 차단, Q7)
    if not case_date:
        out["status"] = "UNVERIFIED (처분 기준일 미확정)"
        return out

    # 서면 주장 추출
    claim = extract_document_claim(doc_text)
    if not claim:
        out["status"] = "UNVERIFIED (서면 내 처분 문구 미검출)"
        return out
    out["document_claim"] = claim

    # W1: 업종 특정 — 서면의 업종 낱말(시행령 제21조 영업 종류)과, 별표 절 머리에 나열된 영업 이름 중 서면에 나오는 것
    doc_industry = claim.get("matched_industry")
    pattern_hits = [name for name, pat in INDUSTRY_PATTERNS if pat.search(doc_text)]
    if doc_industry is None and len(pattern_hits) >= 2:
        # 서면에 업종이 둘 이상 나오고 처분 문장 주변에서도 하나로 좁혀지지 않으면 보류한다
        out["status"] = "UNVERIFIED (서면의 영업 종류 특정 불가)"
        return out
    doc_names = {doc_industry} if doc_industry else set()
    for name, pat in INDUSTRY_PATTERNS:
        if name == doc_industry:
            doc_names.update(m.group(0) for m in pat.finditer(doc_text))

    # HWP 표 파싱 및 병합 전파 (W3, G4)
    structured_rows, success, parse_msg = parse_and_propagate_table(appendix_hwp)
    if not success or not structured_rows:
        out["status"] = f"UNVERIFIED (별표 HWP 표 구조 파싱 불가: {parse_msg})"
        return out

    # W1: 해당 업종 절 안의 행들만 후보군으로 수집
    # 서면 업종 이름이 절 머리(영 제21조 각 호 나열)에 나오는 절이 정확히 하나일 때만 그 절 안에서 맞춘다(J12)
    def _norm(t: str) -> str:
        return re.sub(r"[\s·ㆍ]", "", t or "")
    sections = list(dict.fromkeys(r["industry"] for r in structured_rows if r.get("industry")))

    def _section_names(sec: str) -> List[str]:
        # 절 머리의 '영 제21조제N호의 ○○업, 같은 조 제M호의 △△업 …' 나열과 절 제목('○○업 등')에서 영업 이름을 뽑는다
        names = re.findall(r"의\s*([가-힣][가-힣·ㆍ\s]*?업)(?=[\s,(.]|및|을|를|이|은|$)", sec)
        m_title = re.match(r"\s*([가-힣][가-힣·ㆍ\s]*?업)", sec)
        if m_title:
            names.append(m_title.group(1))
        return [n for n in (_norm(x) for x in names) if n]

    def _hits(sec: str) -> bool:
        listed = _section_names(sec)
        for n in (_norm(x) for x in doc_names):
            if n and any(n == l or l in n or n in l for l in listed):
                return True
        return False

    norm_doc = _norm(doc_text)
    if doc_industry is None:
        for sec in sections:
            doc_names.update(n for n in _section_names(sec) if len(n) >= 4 and n in norm_doc)
    if not doc_names:
        out["status"] = "UNVERIFIED (서면의 영업 종류 특정 불가)"
        return out
    hit_sections = [sec for sec in sections if _hits(sec)]
    if len(hit_sections) != 1:
        out["status"] = "UNVERIFIED (별표에서 해당 업종 절 미확인)" if not hit_sections else "UNVERIFIED (업종 절 복수 해당)"
        return out
    industry_candidates = [r for r in structured_rows if r.get("industry") == hit_sections[0]]
    if not industry_candidates:
        # 업종 절을 찾지 못하면 다른 업종 행과 맞추지 않는다(W1, 평가 측 보완 J6)
        out["status"] = "UNVERIFIED (별표에서 해당 업종 절 미확인)"
        return out

    # G1 & W5: 2-gram Jaccard 유사도 계산 및 유일성 검증
    violation_clause = claim["violation_clause"]
    scored_candidates = []
    for r in industry_candidates:
        score = jaccard_similarity(_strip_cite(violation_clause), _row_core(r["violation_text"]))
        scored_candidates.append((score, r))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    if not scored_candidates:
        out["status"] = "UNVERIFIED (후보 행 없음)"
        return out

    best_score, best_row = scored_candidates[0]
    second_score = scored_candidates[1][0] if len(scored_candidates) > 1 else 0.0

    # G1 & W5 가드: 최고 점수 >= 0.60 및 2위와의 격차 >= 0.20
    if best_score < 0.60:
        out["status"] = f"UNVERIFIED (적용 행 특정 불가: 최고 유사도 {best_score} < 0.60)"
        return out
    if (best_score - second_score) < 0.20:
        out["status"] = f"UNVERIFIED (적용 행 특정 불가: 1·2위 유사도 격차 {round(best_score - second_score, 4)} < 0.20)"
        return out

    # 행 매칭 성공
    matched_row_info = {
        "row_idx": best_row["row_idx"],
        "industry": best_row["industry"],
        "violation_text": best_row["violation_text"],
        "law_text": best_row["law_text"],
        "jaccard_score": best_score,
        "criteria_raw": best_row["criteria_raw"],
    }
    out["matched_row"] = matched_row_info

    # W2: 처분기준 대조 및 단위 환산 금지
    claimed_order = claim["claimed_order"]
    if claimed_order is None:
        out["status"] = "UNVERIFIED (서면의 위반 차수 미기재)"
        return out
    criteria_str = best_row["criteria_raw"].get(claimed_order) or best_row["criteria_raw"].get(str(claimed_order)) or ""
    parsed_crit = parse_criteria_value_and_unit(criteria_str)

    if not parsed_crit:
        out["status"] = f"UNVERIFIED (별표 {claimed_order}차 처분기준 수치/단위 파싱 불가: '{criteria_str}')"
        return out

    crit_val, crit_unit = parsed_crit
    claimed_val = claim["claimed_val"]
    claimed_unit = claim["claimed_unit"]

    # W2 단위 일치 검사: 단위가 다르면 환산하지 않고 UNVERIFIED
    if crit_unit != claimed_unit:
        out["status"] = f"UNVERIFIED (단위 상이 및 환산 금지: 별표는 '{crit_unit}', 서면은 '{claimed_unit}')"
        out["comparison_result"] = "UNVERIFIED"
        return out

    # 단위가 같으므로 수치 비교
    if claimed_val == crit_val:
        out["comparison_result"] = "MATCHED"
    else:
        out["comparison_result"] = "DISCREPANCY_DETECTED"

    # G2: 감경 재량 규정 확인 (일반기준 각주)
    full_text = appendix_plain_text or ""
    if "1/2" in full_text or "2분의 1" in full_text:
        out["discretionary_notes"] = "동기·결과에 따라 1/2 범위에서 감경 가능(일반기준)"

    out["status"] = "COMPLETED"
    return out
