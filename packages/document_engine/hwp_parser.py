"""HWPX / HWP Parser.

HWPX는 OWPML(ZIP+XML) 구조를 직접 읽는다.
Binary HWP는 native parse를 시도하고 실패 시 UNSUPPORTED로 표시하여
전체 Job을 실패시키지 않는다(제14.2장, 제10장 Graceful Degradation).
"""
from __future__ import annotations

import io
import re
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from packages.common.schemas import Block, NormalizedDocument, Page, new_id

from .base import DocumentParser, ParserError
from .ooxml_common import local_name, parse_xml, read_entries, safe_open_zip


class HwpxParser(DocumentParser):
    name = "HwpxParser"
    extensions = [".hwpx"]
    mime_types = ["application/hwp+zip", "application/vnd.hancom.hwpx"]

    def parse(self, path: str, *, document_id: str, filename: str, mime_type: str, sha256: str) -> NormalizedDocument:
        doc = NormalizedDocument(
            document_id=document_id,
            filename=filename,
            mime_type=mime_type or self.mime_types[0],
            sha256=sha256,
            parser_name=self.name,
        )
        try:
            zf = safe_open_zip(path)
        except Exception as exc:
            raise ParserError(f"HWPX ZIP 처리 실패: {exc}") from exc

        visible: List[str] = []
        hidden: List[str] = []
        xml_parts: List[str] = []
        page = Page(page_number=1)

        with zf:
            doc.structure["zip_entries"] = [i.filename for i in zf.infolist()]
            entries = read_entries(zf, lambda n: n.endswith(".xml"))
            sections = {k: v for k, v in entries.items() if "section" in k.lower()}
            manifest = read_entries(zf, lambda n: n.lower().endswith(".hpf"))
            budget = {"cells": 0, "nodes": 0, "chars": 0}   # 문서 전체 누계(섹션을 넘어 이어진다)
            for section_index, name in enumerate(_section_order(sections, manifest)):
                data = sections[name]
                xml_parts.append(data.decode("utf-8", "replace"))
                try:
                    root = parse_xml(data)
                except Exception as exc:
                    doc.parse_warnings.append(f"{name} 파싱 실패: {exc}")
                    continue
                # 문서 단위 XML 노드 누적 상한(TK-140). 넘으면 이 섹션부터 본문을 읽지 않고 그 사실을 남긴다.
                budget["nodes"] += sum(1 for _ in root.iter())
                if budget["nodes"] > HWPX_MAX_DOC_NODES:
                    doc.parse_warnings.append(f"{name}: 문서 XML 노드 누적 상한({HWPX_MAX_DOC_NODES})을 넘어 이 섹션부터 본문을 읽지 않았다")
                    doc.structure["body_truncated"] = True
                    break
                # 문단 글자는 그 문단에 직접 딸린 글자만 모은다. 표(tbl) 안 글자는 표 셀에 한 번만 배정한다(TK-132).
                for para in root.iter():
                    if not _hp(para, "p") or _inside_table(para):
                        continue
                    text = _own_text(para).strip()
                    if not text:
                        continue
                    budget["chars"] += len(text)
                    if budget["chars"] > HWPX_MAX_DOC_CHARS:   # 문서 단위 글자 누적 상한(TK-140)
                        if not doc.structure.get("body_truncated"):
                            doc.parse_warnings.append(f"{name}: 문서 글자 누적 상한({HWPX_MAX_DOC_CHARS})을 넘어 나머지 본문을 읽지 않았다")
                        doc.structure["body_truncated"] = True
                        break
                    page.blocks.append(
                        Block(block_id=new_id("B"), text=text, page=1, source_layer="visible_text")
                    )
                    visible.append(text)
                if doc.structure.get("body_truncated"):
                    break                                       # 상한을 넘은 뒤에는 표·다음 섹션을 읽지 않는다
                for table in _hwpx_tables(root, section_index, doc.parse_warnings, budget):
                    flat = "\n".join(" | ".join(row) for row in table["cells"])
                    if not table["complete"]:
                        # 불완전한 표는 계산·사실·증거·첨부 소비자에 표로 넘기지 않는다(부분 표로 합계·부재를 확정하지 않게).
                        # 글자는 일반 문단으로 남기고, 위치·사유만 따로 기록한다.
                        doc.structure.setdefault("partial_tables", []).append(
                            {k: table[k] for k in ("table_ref", "row_count", "column_count", "nested",
                                                    "parent_table_ref")} | {"reason": "INCOMPLETE_STRUCTURE"})
                        page.blocks.append(Block(block_id=new_id("B"), text=flat, page=1, source_layer="visible_text"))
                        visible.append(flat)
                        continue
                    doc.structure.setdefault("tables", []).append(table)
                    page.blocks.append(Block(
                        block_id=new_id("B"), text=flat, page=1, source_layer="visible_text", block_type="table",
                        attributes={"table_index": table["table_index"], "cells": table["cells"],
                                    "table_ref": table["table_ref"]}))
                    visible.append(flat)

            # 메모/주석/설정
            for name, data in entries.items():
                low = name.lower()
                if any(k in low for k in ("memo", "comment", "annotation")):
                    xml_parts.append(data.decode("utf-8", "replace"))
                    try:
                        root = parse_xml(data)
                    except Exception:
                        continue
                    texts = [t.text.strip() for t in root.iter() if _hp(t, "t") and t.text and t.text.strip()]
                    for t in texts:
                        page.blocks.append(
                            Block(
                                block_id=new_id("B"),
                                text=t,
                                page=1,
                                source_layer="xml",
                                block_type="comment",
                                visible=False,
                                attributes={"part": name},
                            )
                        )
                        hidden.append(t)
                if "content.hpf" in low or "meta" in low or "version" in low:
                    xml_parts.append(data.decode("utf-8", "replace"))

            meta = entries.get("Contents/content.hpf") or entries.get("META-INF/container.xml")
            if meta:
                try:
                    root = parse_xml(meta)
                    for el in root.iter():
                        tag = local_name(el.tag)
                        if el.text and el.text.strip() and tag in ("title", "creator", "date", "publisher", "subject"):
                            doc.metadata[tag] = el.text.strip()
                except Exception:
                    pass

        doc.pages.append(page)
        doc.raw_layers["rendered_text"] = "\n".join(visible)
        doc.raw_layers["raw_text"] = "\n".join(visible + hidden)
        doc.raw_layers["hidden_text"] = "\n".join(hidden)
        doc.raw_layers["xml"] = "\n".join(xml_parts)
        doc.raw_layers["metadata_text"] = "\n".join(f"{k}: {v}" for k, v in doc.metadata.items())

        # 블록 문단 복원 (TK-22): 구조 신호 기반 일관된 블록 구조 유지
        from .paragraph_reconstruction import reconstruct_page_blocks
        for p in doc.pages:
            p.blocks = reconstruct_page_blocks(
                p.blocks,
                page_num=p.page_number,
                page_width=p.width,
                page_height=p.height,
            )
        return doc


# --- HWPX 표(TK-132) ---------------------------------------------------------------------------------------------
# 상한(TK-132 설계 메모 4의 제안값): 표당 행·열·칸, 문서 전체 칸, 표 중첩 깊이. 할당 전에 검사한다.
HWPX_MAX_ROWS = 10000
HWPX_MAX_COLS = 256
HWPX_MAX_CELLS = 100000
HWPX_MAX_DOC_CELLS = 200000
HWPX_MAX_DEPTH = 8
HWPX_MAX_DOC_NODES = 2_000_000     # 문서 전체 XML 요소 수(TK-140)
HWPX_MAX_DOC_CHARS = 20_000_000    # 문서 전체 본문 글자 수(TK-140)
HWPML_NS = "http://www.hancom.co.kr/hwpml/"


def _hp(el, name: str) -> bool:
    """HWPX 본문 요소인지: local-name이 같고, 이름공간이 한컴 HWPML(연도 무관)이거나 없을 때만(TK-140).

    다른 이름공간(외부 XML 조각 등)의 같은 이름 요소를 본문·표로 읽지 않는다.
    """
    tag = el.tag if isinstance(el.tag, str) else ""
    if local_name(tag) != name:
        return False
    return not tag.startswith("{") or tag[1:].startswith(HWPML_NS)


def _section_order(sections, manifest):
    """manifest(content.hpf)의 spine 순서를 먼저 따르고, 없으면 파일 이름의 숫자 순으로 정렬한다(section10이 section2 뒤)."""
    import posixpath

    order = []
    for package, data in manifest.items():
        try:
            root = parse_xml(data)
        except Exception:
            continue
        href = {el.get("id"): el.get("href") for el in root.iter() if local_name(el.tag) == "item"}
        base = posixpath.dirname(package)
        for el in root.iter():
            if local_name(el.tag) != "itemref":
                continue
            target = href.get(el.get("idref")) or ""
            if not target or "://" in target:                     # 외부 URL은 조회하지 않는다
                continue
            # href는 package 문서가 있는 디렉터리 기준이다(Contents/content.hpf의 section2.xml → Contents/section2.xml)
            path = posixpath.normpath(posixpath.join(base, target)).lstrip("/")
            if path in sections and path not in order:
                order.append(path)
    rest = [n for n in sections if n not in order]
    number = lambda n: int(re.search(r"(\d+)(?=\D*$)", n).group(1)) if re.search(r"\d+", n) else 0
    return order + sorted(rest, key=lambda n: (number(n), n))


def _inside_table(el) -> bool:
    return any(_hp(a, "tbl") for a in el.iterancestors())


def _own_text(el) -> str:
    """el 아래 글자(t) 중 el과 그 글자 사이에 표(tbl)가 끼지 않은 것만 잇는다."""
    out = []
    for t in el.iter():
        if not _hp(t, "t"):
            continue
        between = []
        for a in t.iterancestors():
            if a is el:
                break
            between.append(_hp(a, "tbl"))
        if not any(between):
            out.append(t.text or "")
    return "".join(out)


def _int(el, attr, default=None):
    try:
        return int(el.get(attr))
    except (TypeError, ValueError):
        return default


def _hwpx_tables(root, section_index, warnings, budget=None):
    """섹션 안의 표를 셀 주소·병합 그대로 2차원 표로 만든다. 병합 값은 앵커 칸에만 두고 덮인 칸은 빈칸이다."""
    tables = []
    budget = budget if budget is not None else {"cells": 0}
    all_tables = [el for el in root.iter() if _hp(el, "tbl")]
    position = {id(el): i for i, el in enumerate(all_tables)}   # 바깥 표 번호를 표마다 다시 세지 않는다(TK-140)
    for index, tbl in enumerate(all_tables):
        depth = sum(1 for a in tbl.iterancestors() if _hp(a, "tbl"))
        ref = f"hwpx_s{section_index}t{index}"
        rows_attr, cols_attr = _int(tbl, "rowCnt"), _int(tbl, "colCnt")
        cells, complete = [], depth < HWPX_MAX_DEPTH
        for r_i, tr in enumerate(c for c in tbl if _hp(c, "tr")):
            for c_i, tc in enumerate(c for c in tr if _hp(c, "tc")):
                addr = next((c for c in tc if _hp(c, "cellAddr")), None)
                span = next((c for c in tc if _hp(c, "cellSpan")), None)
                row = _int(addr, "rowAddr", r_i) if addr is not None else r_i
                col = _int(addr, "colAddr", c_i) if addr is not None else c_i
                row_span = max(1, _int(span, "rowSpan", 1)) if span is not None else 1
                col_span = max(1, _int(span, "colSpan", 1)) if span is not None else 1
                text = " ".join(_own_text(p).strip() for p in tc.iter()
                                if _hp(p, "p") and _nearest_cell(p) is tc and _own_text(p).strip())
                cells.append((row, col, row_span, col_span, text))
        rows = rows_attr or max((r + rs for r, _, rs, _, _ in cells), default=0)
        cols = cols_attr or max((c + cs for _, c, _, cs, _ in cells), default=0)
        if not (0 < rows <= HWPX_MAX_ROWS and 0 < cols <= HWPX_MAX_COLS and rows * cols <= HWPX_MAX_CELLS) \
                or budget["cells"] + rows * cols > HWPX_MAX_DOC_CELLS:
            warnings.append(f"{ref}: 표 크기 {rows}x{cols}가 상한을 넘거나 없어 표 구조를 만들지 않았다")
            continue
        budget["cells"] += rows * cols
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        owner = [[None for _ in range(cols)] for _ in range(rows)]
        merges = []
        for row, col, row_span, col_span, text in cells:
            if not (0 <= row < rows and 0 <= col < cols) or row + row_span > rows or col + col_span > cols:
                warnings.append(f"{ref}: 셀 주소·병합이 표 범위를 벗어나 그 칸을 빼고 표를 만들었다")
                complete = False
                continue
            if any(owner[r][c] is not None for r in range(row, row + row_span) for c in range(col, col + col_span)):
                warnings.append(f"{ref}: 겹치는 셀이 있어 뒤 셀을 빼고 표를 만들었다")
                complete = False
                continue
            for r in range(row, row + row_span):
                for c in range(col, col + col_span):
                    owner[r][c] = (row, col)
            grid[row][col] = text
            if row_span > 1 or col_span > 1:
                merges.append({"row": row, "col": col, "row_span": row_span, "col_span": col_span})
        parent = next((a for a in tbl.iterancestors() if _hp(a, "tbl")), None)
        tables.append({"table_ref": ref, "page": 1, "table_index": index, "cells": grid, "header": grid[0],
                       "title": None, "row_count": rows, "column_count": cols, "merges": merges,
                       "covered": [[r, c] for r in range(rows) for c in range(cols)
                                   if owner[r][c] not in (None, (r, c))],
                       "nested": depth > 0, "complete": complete,
                       "parent_table_ref": (f"hwpx_s{section_index}t{position[id(parent)]}"
                                            if parent is not None else None),
                       "representation": "TABLE_BLOCK"})
    return tables


def _nearest_cell(el):
    return next((a for a in el.iterancestors() if _hp(a, "tc")), None)


class HwpParser(DocumentParser):
    """Binary HWP 5.x. CFB 컨테이너의 BodyText 스트림을 zlib 해제해 텍스트만 추출한다."""

    name = "HwpParser"
    extensions = [".hwp"]
    mime_types = ["application/x-hwp", "application/haansofthwp"]

    def parse(self, path: str, *, document_id: str, filename: str, mime_type: str, sha256: str) -> NormalizedDocument:
        doc = NormalizedDocument(
            document_id=document_id,
            filename=filename,
            mime_type=mime_type or self.mime_types[0],
            sha256=sha256,
            parser_name=self.name,
        )
        raw = Path(path).read_bytes()
        if not raw.startswith(b"\xd0\xcf\x11\xe0"):
            doc.parse_warnings.append("HWP CFB 시그니처가 아니다. 형식 확인 필요.")
        texts: List[str] = []
        try:
            texts = _extract_hwp_text(raw, doc.parse_warnings)
        except Exception as exc:
            doc.parse_warnings.append(f"HWP native parse 실패: {exc}")

        if not texts:
            doc.parse_warnings.append(
                "Binary HWP 본문 추출에 실패했다. isolated conversion fallback(HWPX/PDF 변환) 후 재업로드가 필요하며, "
                "현재 문서의 본문 검증 항목은 UNVERIFIED로 처리한다."
            )
            doc.structure["unsupported_body"] = True
            doc.structure["body_extraction_failed"] = True
        else:
            doc.structure["body_extraction_scope"] = "HWP_PARAGRAPH_RECORDS"
            doc.structure["page_numbers_reliable"] = False
            doc.parse_warnings.append("HWP 본문 텍스트를 추출했습니다. 원본 쪽 번호와 시각적 배치·서식은 확인되지 않습니다.")

        if texts:
            # 표 구조(TK-133): 셀 글자는 이미 본문 문단 블록에 있다. 표 블록을 따로 만들어 중복 표시하지 않고,
            # 행·열 구조만 structure["tables"]에 남긴 뒤 셀 문단 블록에 table_ref를 붙인다(PDF의
            # LINES_WITH_STRUCTURE와 같은 계약). 문단 순서가 본문과 맞지 않으면 표를 내지 않는다.
            try:
                tables, partial, owners = _extract_hwp_table_structures(raw, doc.parse_warnings)
            except Exception as exc:
                tables, partial, owners = [], [], []
                doc.parse_warnings.append(f"HWP 표 구조 복원 실패(본문 텍스트는 유지): {exc}")
            # 문단 대응은 개수가 아니라 같은 레코드에서 읽은 글자가 같은 순서로 같은지로 확인한다(TK-140).
            if tables and [text for text, _ in owners] != texts:
                doc.parse_warnings.append("HWP 표 셀 문단과 본문 문단의 순서가 맞지 않아 표 구조를 내지 않았다")
                tables, owners = [], []
            if tables:
                doc.structure["tables"] = tables
            if partial:
                doc.structure["partial_tables"] = partial

        page = Page(page_number=1)
        for index, t in enumerate(texts):
            block = Block(block_id=new_id("B"), text=t, page=1, source_layer="visible_text")
            ref = owners[index][1] if texts and tables else None
            if ref:
                block.attributes["table_ref"] = ref
                next(x for x in tables if x["table_ref"] == ref)["line_block_ids"].append(block.block_id)
            page.blocks.append(block)
        doc.pages.append(page)
        joined = "\n".join(texts)
        doc.raw_layers["rendered_text"] = joined
        doc.raw_layers["raw_text"] = joined

        # 블록 문단 복원 (TK-22): 구조 신호 기반 일관된 블록 구조 유지
        from .paragraph_reconstruction import reconstruct_page_blocks
        for p in doc.pages:
            p.blocks = reconstruct_page_blocks(
                p.blocks,
                page_num=p.page_number,
                page_width=p.width,
                page_height=p.height,
            )
        return doc


MAX_HWP_SECTION_BYTES = 16 * 1024 * 1024
MAX_HWP_BODY_BYTES = 32 * 1024 * 1024
MAX_HWP_SECTIONS = 512
MAX_HWP_RECORDS = 200_000


def _paragraph_text(data: bytes) -> str:
    if len(data) % 2:
        raise ParserError("HWP 문단 텍스트 길이가 잘못되었습니다")
    output = bytearray()
    cursor = 0
    while cursor < len(data):
        code = struct.unpack_from("<H", data, cursor)[0]
        if code >= 32:
            output.extend(data[cursor:cursor + 2])
            cursor += 2
            continue
        # Inline/extended controls occupy eight UTF-16 code units, not one.
        width = 16 if code in {*range(1, 10), 11, 12, *range(14, 24)} else 2
        if cursor + width > len(data):
            raise ParserError("HWP 문단 제어문자가 잘렸습니다")
        replacement = {9: "\t", 10: "\n", 13: "\n", 24: "-", 30: " ", 31: " "}.get(code, "")
        output.extend(replacement.encode("utf-16-le"))
        cursor += width
    return output.decode("utf-16-le").strip()


def _section_text(data: bytes) -> List[str]:
    texts = []
    cursor = count = 0
    while cursor < len(data):
        count += 1
        if count > MAX_HWP_RECORDS or len(data) - cursor < 4:
            raise ParserError("HWP 레코드 수 초과 또는 잘린 헤더")
        header = struct.unpack_from("<I", data, cursor)[0]
        tag, size = header & 0x3FF, header >> 20
        cursor += 4
        if size == 0xFFF:
            if len(data) - cursor < 4:
                raise ParserError("HWP 확장 길이 헤더가 잘렸습니다")
            size = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
        if size > len(data) - cursor:
            raise ParserError("HWP 레코드 본문이 잘렸습니다")
        if tag == 0x43:  # HWPTAG_PARA_TEXT, including table-cell paragraphs.
            text = _paragraph_text(data[cursor:cursor + size])
            if text:
                texts.append(text)
        cursor += size
    return texts


def _extract_hwp_text(raw: bytes, notes: Optional[List[str]] = None) -> List[str]:
    """Read CFB streams and raw DEFLATE records per the Hancom HWP 5.0 spec.

    https://tech.hancom.com/python-hwp-parsing-2/
    Preview text and embedded binary data are not substitutes for the body.
    """
    results: List[str] = []
    for data in _section_streams(raw, notes):
        results.extend(_section_text(data))
    return results


def _extract_hwp_tables(raw: bytes, notes: Optional[List[str]] = None) -> List[List[List[str]]]:
    """표를 셀 단위로 복원한다(행 목록, 각 행은 열 순서의 셀 글자). 셀 글자를 이어 붙이지 않는다."""
    tables: List[List[List[str]]] = []
    for data in _section_streams(raw, notes):
        tables.extend(_section_tables(data))
    return tables


def _records(data: bytes):
    cursor = count = 0
    while cursor < len(data):
        count += 1
        if count > MAX_HWP_RECORDS or len(data) - cursor < 4:
            raise ParserError("HWP 레코드 수 초과 또는 잘린 헤더")
        header = struct.unpack_from("<I", data, cursor)[0]
        tag, level, size = header & 0x3FF, (header >> 10) & 0x3FF, header >> 20
        cursor += 4
        if size == 0xFFF:
            if len(data) - cursor < 4:
                raise ParserError("HWP 확장 길이 헤더가 잘렸습니다")
            size = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
        if size > len(data) - cursor:
            raise ParserError("HWP 레코드 본문이 잘렸습니다")
        yield tag, level, data[cursor:cursor + size]
        cursor += size


HWPTAG_TABLE, HWPTAG_LIST_HEADER, HWPTAG_PARA_TEXT = 0x4D, 0x48, 0x43


def _section_tables(data: bytes) -> List[List[List[str]]]:
    """HWPTAG_TABLE(행·열 수) 뒤의 셀 머리(HWPTAG_LIST_HEADER: 열·행 주소)마다 그 아래 문단 글자를 모은다."""
    tables: List[List[List[str]]] = []
    grid: Optional[List[List[str]]] = None
    table_level = cell_level = -1
    cell = None
    for tag, level, body in _records(data):
        if grid is not None and level < table_level:  # 표 제어보다 바깥 수준의 레코드가 나오면 표가 끝났다
            tables.append(grid)
            grid, cell = None, None
        if tag == HWPTAG_TABLE and len(body) >= 8 and grid is None:
            rows, cols = struct.unpack_from("<HH", body, 4)
            if 0 < rows <= 2000 and 0 < cols <= 100:
                grid = [["" for _ in range(cols)] for _ in range(rows)]
                table_level = level
        elif tag == HWPTAG_LIST_HEADER and grid is not None and len(body) >= 12 and level in (table_level, table_level + 1):
            col, row = struct.unpack_from("<HH", body, 8)
            cell = (row, col) if row < len(grid) and col < len(grid[0]) else None
            cell_level = level
        elif tag == HWPTAG_PARA_TEXT and grid is not None and cell is not None and level > cell_level:
            text = _paragraph_text(body)
            if text:
                row, col = cell
                grid[row][col] = f"{grid[row][col]} {text}".strip() if grid[row][col] else text
    if grid is not None:
        tables.append(grid)
    return tables


MAX_HWP_TABLE_ROWS = 2000
MAX_HWP_TABLE_COLS = 100
MAX_HWP_DOC_CELLS = 200_000


def _extract_hwp_table_structures(raw: bytes, warnings: List[str]
                                  ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, Optional[str]]]]:
    """표를 행·열 구조로 복원한다(TK-133). 병합 값은 앵커 칸에만 두고, 덮인 칸은 빈칸이다.

    셀 주소가 범위 밖이거나 겹치거나, 표 안에 표가 있으면(중첩 표 글자가 바깥 칸에 섞인다) 불완전한 표로 보고
    소비자(계산·사실·첨부 엔진)에 넘기지 않는다. 돌려주는 값: (완전한 표, 불완전한 표 요약, 비어 있지 않은 문단마다
    (문단 글자, 그 문단이 속한 완전한 표의 table_ref 또는 None) — _extract_hwp_text와 같은 순서)."""
    tables: List[Dict[str, Any]] = []
    partial: List[Dict[str, Any]] = []
    owners: List[Tuple[str, Optional[str]]] = []
    budget = {"cells": 0}
    for section, data in enumerate(_section_streams(raw)):
        found, paragraph_owners = _section_table_structures(data, warnings, budget)
        for index, table in enumerate(found):
            table["ref"] = f"hwp_s{section}t{index}"
        for table in found:
            ref = table["ref"]
            parent_ref = table["parent"]["ref"] if table.get("parent") is not None else None
            if not table["complete"]:
                partial.append({"table_ref": ref, "row_count": table["row_count"],
                                "column_count": table["column_count"], "reason": "INCOMPLETE_STRUCTURE",
                                "nested": table["nested"], "parent_table_ref": parent_ref})
                continue
            grid = table["cells"]
            tables.append({"table_ref": ref, "page": 1, "table_index": len(tables), "cells": grid,
                           "header": grid[0], "title": None, "row_count": len(grid),
                           "column_count": len(grid[0]), "merges": table["merges"], "covered": table["covered"],
                           "complete": True, "nested": table["nested"], "parent_table_ref": parent_ref,
                           "representation": "LINES_WITH_STRUCTURE", "source": "HWP_RECORDS", "line_block_ids": []})
        owners.extend((text, t["ref"] if t is not None and t["complete"] else None) for text, t in paragraph_owners)
    return tables, partial, owners


MAX_HWP_TABLE_DEPTH = 8


def _section_table_structures(data: bytes, warnings: List[str], budget: Dict[str, int]
                              ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, Optional[Dict[str, Any]]]]]:
    """표를 열린 순서대로 만든다. 셀 안의 표(중첩 표)는 따로 열어 안쪽 표로 만들고, 그 안 문단은 안쪽 표에만
    배정한다(TK-140). 바깥 표의 칸에는 안쪽 표 글자가 섞이지 않는다."""
    out: List[Dict[str, Any]] = []                         # 열린 순서(바깥 표가 안쪽 표보다 앞)
    owners: List[Tuple[str, Optional[Dict[str, Any]]]] = []   # 비어 있지 않은 문단마다 (글자, 속한 표 또는 None)
    stack: List[Dict[str, Any]] = []                       # 열린 표: 바깥 → 안쪽

    for tag, level, body in _records(data):
        while stack and level < stack[-1]["_level"]:       # 표 제어보다 바깥 수준의 레코드가 나오면 그 표가 끝났다
            stack.pop()
        top = stack[-1] if stack else None
        if tag == HWPTAG_TABLE and len(body) >= 8:
            in_cell = top is not None and top["_cell"] is not None and level > top["_cell_level"]
            if top is not None and not in_cell:            # 셀 밖에 걸친 표 제어: 구조를 알 수 없어 바깥 표를 불완전으로
                if top["complete"]:
                    warnings.append("HWP 표 안의 표 위치를 셀에 대응하지 못해 바깥 표를 불완전한 표로 두었다")
                top["complete"] = False
                continue
            if len(stack) >= MAX_HWP_TABLE_DEPTH:
                if top["complete"]:
                    warnings.append("HWP 표 중첩 깊이가 상한을 넘어 바깥 표를 불완전한 표로 두었다")
                top["complete"] = False
                continue
            rows, cols = struct.unpack_from("<HH", body, 4)
            if not (0 < rows <= MAX_HWP_TABLE_ROWS and 0 < cols <= MAX_HWP_TABLE_COLS) or \
                    budget["cells"] + rows * cols > MAX_HWP_DOC_CELLS:
                warnings.append(f"HWP 표 크기({rows}×{cols})가 상한을 넘어 표 구조를 만들지 않았다")
                if top is not None:
                    top["complete"] = False                # 안쪽 표를 못 만들면 그 글자가 바깥 칸에 남지 않게 바깥도 불완전
                continue
            budget["cells"] += rows * cols
            table = {"cells": [["" for _ in range(cols)] for _ in range(rows)], "merges": [], "covered": [],
                     "complete": True, "row_count": rows, "column_count": cols,
                     "nested": top is not None, "parent": top,
                     "_level": level, "_cell": None, "_cell_level": -1,
                     "_owner": [[None] * cols for _ in range(rows)]}
            out.append(table)
            stack.append(table)
        elif tag == HWPTAG_LIST_HEADER and top is not None and level in (top["_level"], top["_level"] + 1):
            table = top
            table["_cell"], table["_cell_level"] = None, level
            if len(body) < 16:
                table["complete"] = False
                continue
            col, row, col_span, row_span = struct.unpack_from("<HHHH", body, 8)
            rows, cols, owner = table["row_count"], table["column_count"], table["_owner"]
            if col_span < 1 or row_span < 1 or row + row_span > rows or col + col_span > cols:
                if table["complete"]:
                    warnings.append("HWP 표 셀 주소·병합 범위가 표 범위를 벗어나 불완전한 표로 두었다")
                table["complete"] = False
                continue
            area = [(r, c) for r in range(row, row + row_span) for c in range(col, col + col_span)]
            if any(owner[r][c] is not None for r, c in area):
                if table["complete"]:
                    warnings.append("HWP 표 셀이 겹쳐 불완전한 표로 두었다")
                table["complete"] = False
                continue
            for r, c in area:
                owner[r][c] = (row, col)
            if row_span > 1 or col_span > 1:
                table["merges"].append({"row": row, "col": col, "row_span": row_span, "col_span": col_span})
                table["covered"].extend([r, c] for r, c in area if (r, c) != (row, col))
            table["_cell"] = (row, col)
        elif tag == HWPTAG_PARA_TEXT:
            text = _paragraph_text(body)
            if not text:
                continue
            if top is not None and top["_cell"] is not None and level > top["_cell_level"]:
                row, col = top["_cell"]
                grid = top["cells"]
                grid[row][col] = f"{grid[row][col]} {text}".strip() if grid[row][col] else text
                owners.append((text, top))
            else:
                owners.append((text, None))
    for table in out:
        for key in ("_level", "_cell", "_cell_level", "_owner"):
            table.pop(key, None)
    return out, owners


def _section_streams(raw: bytes, notes: Optional[List[str]] = None) -> List[bytes]:
    import olefile

    with olefile.OleFileIO(io.BytesIO(raw)) as ole:
        if not ole.exists("FileHeader") or ole.get_size("FileHeader") != 256:
            raise ParserError("HWP FileHeader가 없거나 길이가 잘못되었습니다")
        header = ole.openstream("FileHeader").read()
        if header[:32].rstrip(b"\0") != b"HWP Document File" or header[35] != 5:
            raise ParserError("지원하지 않는 HWP 형식입니다")
        flags = struct.unpack_from("<I", header, 36)[0]
        if flags & ((1 << 1) | (1 << 2) | (1 << 4) | (1 << 8) | (1 << 10)):
            raise ParserError("암호화·배포용·DRM HWP는 HWPX 또는 PDF 변환 후 검증해야 합니다")
        sections = [path for path in ole.listdir(streams=True, storages=False)
                    if len(path) == 2 and path[0] == "BodyText" and re.fullmatch(r"Section\d+", path[1])]
        sections.sort(key=lambda path: int(path[1][7:]))
        if not sections or len(sections) > MAX_HWP_SECTIONS:
            raise ParserError("HWP 본문 구역이 없거나 구역 수 한도를 초과했습니다")
        streams, body_size = [], 0
        for section in sections:
            if ole.get_size(section) > MAX_HWP_SECTION_BYTES:
                raise ParserError("HWP 본문 스트림 크기 한도 초과")
            data = ole.openstream(section).read()
            if flags & 1:
                decoder = zlib.decompressobj(-15)
                data = decoder.decompress(data, MAX_HWP_SECTION_BYTES + 1)
                if len(data) > MAX_HWP_SECTION_BYTES or not decoder.eof:
                    raise ParserError(f"HWP 압축 본문 한도 초과 또는 손상({section[1]}: 스트림 완결={decoder.eof}, "
                                      f"해제 {len(data)}바이트)")
                # 완결된 DEFLATE 스트림 뒤의 바이트는 본문이 아니다(작성기 채움 바이트). 읽지 않고 알린다.
                if decoder.unused_data and notes is not None:
                    notes.append(f"HWP {section[1]} 압축 스트림 뒤 {len(decoder.unused_data)}바이트는 본문으로 읽지 않았다")
            body_size += len(data)
            if body_size > MAX_HWP_BODY_BYTES:
                raise ParserError("HWP 전체 본문 크기 한도 초과")
            streams.append(data)
        return streams
