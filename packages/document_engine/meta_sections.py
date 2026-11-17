"""부록·기능 점검 체크리스트 등 문서 자체 메타표/가이드 구간 식별.

서면 본문 뒤에 검증 항목표·테스트 체크리스트·기대 결과표 등이 부록으로 첨부된 경우,
해당 메타 구간의 주장·개체명·사건·인용이 실체 법률 주장·가공 판례·당사자 표에
섞이지 않도록 블록 ID 집합을 식별한다.

일반 증거 목록(호증/서증명/작성일), 사실관계 정리표(일시/내용/근거), 손해액 산정표는
메타표로 취급하지 않는다.
"""
from __future__ import annotations

import re
from typing import Any, Sequence, Set

from packages.common.schemas import NormalizedDocument

_APPENDIX_PREFIX_RE = re.compile(r"(?:부\s*록|부\s*속\s*서|별\s*첨|첨\s*부\s*표)")
_RUBRIC_KEYWORD_RE = re.compile(
    r"(?:체크\s*리스트|테스트|검증\s*(?:항목|표|시나리오|목록|가이드)|점검\s*(?:항목|표|목록)|"
    r"기대\s*(?:결과|판정)|오류\s*유형|탐지\s*대상|평가\s*(?:기준|항목|표)|기능\s*(?:목록|점검|검증))"
)
_STANDALONE_RUBRIC_HEADING_RE = re.compile(
    r"(?:테스트\s*(?:항목|체크\s*리스트|시나리오|표|목록|가이드)|"
    r"검증\s*(?:항목|체크\s*리스트|시나리오|표)|"
    r"점검\s*(?:항목|체크\s*리스트|표)|"
    r"체크\s*리스트|기능\s*검증\s*(?:표|목록)|기대\s*결과\s*(?:표|요약))"
)

_STRONG_RUBRIC_CELL_RE = re.compile(
    r"(?:테스트\s*(?:항목|내용|대상|유형|시나리오)|검증\s*(?:항목|대상|내용|시나리오)|"
    r"점검\s*(?:항목|대상)|기대\s*(?:결과|판정)|예상\s*(?:결과|판정)|"
    r"합격\s*기준|통과\s*기준|평가\s*기준|오류\s*유형|탐지\s*대상|"
    r"체크\s*(?:항목|리스트)|기능\s*검증)"
)
_RUBRIC_CELL_RE = re.compile(
    r"(?:테스트\s*(?:항목|내용|대상|유형|시나리오)|검증\s*(?:항목|대상|내용|유형|시나리오)|"
    r"점검\s*(?:항목|대상|내용)|기대\s*(?:결과|판정)|예상\s*(?:결과|판정)|"
    r"합격\s*기준|통과\s*기준|평가\s*(?:기준|대상|항목)|오류\s*유형|탐지\s*(?:대상|여부)|"
    r"체크\s*(?:항목|리스트)|핵심\s*기능|기능\s*분류|반영\s*(?:위치|여부)|포함\s*위치|구현\s*여부|관련\s*모듈)"
)

_REAL_LEGAL_TABLE_COL_RE = re.compile(
    r"^(?:호증|증거번호|증번|서증명|증거명|작성일|작성일자|입증취지|증명취지|"
    r"일자|날짜|일시|사건일시|내용|주요내용|사실관계|법적근거|근거|관련조항|적용법조|관련법조|"
    r"구분|항목|비목|산정기준|산정내역|청구금액|원금|이자|지연손해금|손해액|인정액|합계|금액|"
    r"작성자|명의인|증거|서증|비고)$"
)

_SENTENCE_TERMINAL_RE = re.compile(r"(?:다|요|습니다|ㅂ니다|한다|된다|이다)\s*[.!?。]\s*$")
_CLOSING_SIGNATURE_RE = re.compile(
    r"(?:(?:지방법원|고등법원|가정법원|행정법원|대법원|헌법재판소|법원)\s*귀중|"
    r"^\s*위\s*(?:원고|피고|신청인|피신청인|고소인|고발인|항소인|상고인|변호인)\b|"
    r"^\s*(?:원고|피고)\s*(?:소송)?대리인\b)"
)
_FORMAL_LEGAL_SECTION_RE = re.compile(
    r"^\s*(?:청구\s*취지|청구\s*원인|입증\s*방법|증거\s*설명|첨부\s*서류|결\s*론|"
    r"사실\s*관계\s*(?:정리|표|목록)?|증거\s*목록|서증\s*목록|손해액\s*산정\s*(?:내역|표)?|손해배상액\s*산정|"
    r"(?:[IVX]+\.|제\s*\d+\s*[장절]|\[(?:별지|별첨|첨부)\b[^\]]*\])\s*\S*)"
)


def _cell_text(cell: Any) -> str:
    if isinstance(cell, str):
        return cell.strip()
    if isinstance(cell, dict):
        return str(cell.get("text") or "").strip()
    return str(getattr(cell, "text", None) or cell or "").strip()


def _has_real_legal_table_header(rows: Sequence[Sequence[Any]]) -> bool:
    for row in rows[:2]:
        cells = [re.sub(r"\s+", "", _cell_text(c)) for c in row]
        nonempty = [c for c in cells if c]
        if len(nonempty) < 2:
            continue
        if any(_REAL_LEGAL_TABLE_COL_RE.fullmatch(c) for c in nonempty):
            return True
    return False


def is_meta_checklist_table_rows(rows: Sequence[Sequence[Any]]) -> bool:
    """표의 상단 헤더 행이 기능 점검/체크리스트/평가 메타표 구조인지 판별한다."""
    if not rows:
        return False
    if _has_real_legal_table_header(rows):
        return False
    nonempty_rows = []
    for row in rows:
        cells = [_cell_text(c) for c in row]
        nonempty = [c for c in cells if c]
        if len(nonempty) >= 2:
            nonempty_rows.append(nonempty)
        if len(nonempty_rows) >= 2:
            break
    for row_idx, cells in enumerate(nonempty_rows):
        rubric_hits = sum(1 for c in cells if len(c) <= 28 and _RUBRIC_CELL_RE.search(c))
        strong_hits = sum(1 for c in cells if len(c) <= 28 and _STRONG_RUBRIC_CELL_RE.search(c))
        if rubric_hits >= 2 or (row_idx == 0 and strong_hits >= 1 and len(cells) >= 2):
            return True
    return False


def _is_rubric_section_heading(text: str) -> bool:
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if not first_line or len(first_line) > 100:
        return False
    if _SENTENCE_TERMINAL_RE.search(first_line) and not _APPENDIX_PREFIX_RE.search(first_line):
        return False
    if _APPENDIX_PREFIX_RE.search(first_line) and _RUBRIC_KEYWORD_RE.search(first_line):
        return True
    return bool(_STANDALONE_RUBRIC_HEADING_RE.search(first_line))


def _is_flattened_rubric_header_block(text: str) -> bool:
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if not first_line or len(first_line) > 140:
        return False
    if _SENTENCE_TERMINAL_RE.search(first_line) and "|" not in first_line:
        return False
    if _REAL_LEGAL_TABLE_COL_RE.search(re.sub(r"\s+", "", first_line)) and "호증" in first_line:
        return False
    hits = {re.sub(r"\s+", "", m.group(0)) for m in _RUBRIC_CELL_RE.finditer(first_line)}
    return len(hits) >= 2


def meta_checklist_block_ids(doc: NormalizedDocument) -> Set[str]:
    """문서 내 부록/테스트 체크리스트 메타표에 속하는 block_id 집합을 반환한다."""
    meta_ids: Set[str] = set()
    state: str | None = None  # None | "section" | "header_row"
    header_blocks = 0

    for block in doc.body_blocks():
        text = (block.text or "").strip()
        if block.block_type == "table":
            rows = (block.attributes or {}).get("cells") or [
                line.split(" | ") for line in text.splitlines()
            ]
            if _has_real_legal_table_header(rows):
                state = None
                header_blocks = 0
                continue
            if is_meta_checklist_table_rows(rows):
                meta_ids.add(block.block_id)
            else:
                # 체크리스트 제목 뒤라는 이유만으로 임의의 표를 메타로 분류하지 않는다.
                # 메타 표가 아닌 정상 표가 나오면 체크리스트 부록 구간 상태를 해제한다.
                state = None
                header_blocks = 0
            continue

        if not text:
            continue

        if _is_rubric_section_heading(text):
            state = "section"
            header_blocks = 0
            meta_ids.add(block.block_id)
            continue

        if _CLOSING_SIGNATURE_RE.search(text) or _FORMAL_LEGAL_SECTION_RE.match(text):
            state = None
            header_blocks = 0
            continue

        if state is None:
            if _is_flattened_rubric_header_block(text):
                state = "header_row"
                header_blocks = 0
                meta_ids.add(block.block_id)
            continue

        if state == "header_row":
            header_blocks += 1
            is_item_or_row = bool(
                "|" in text
                or re.match(r"^\s*(?:\d+[.)]|[-•■□▶▷]|\[)", text)
                or len(text) <= 120
            )
            if (not is_item_or_row and _SENTENCE_TERMINAL_RE.search(text)) or header_blocks > 25:
                state = None
                header_blocks = 0
                continue

        meta_ids.add(block.block_id)

    return meta_ids
