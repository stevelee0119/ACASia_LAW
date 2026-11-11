"""DOCX Parser.

본문·표·머리말/꼬리말·각주·주석을 각각 Block으로 남기고,
w:vanish(숨김 서식), w:ins/w:del(미수락 변경이력), customXml, core/app properties를
structure에 담아 제7-A장 MM-2 포렌식에 전달한다.
"""
from __future__ import annotations

from typing import Any, Dict, List

from packages.common.schemas import Block, NormalizedDocument, Page, new_id

from .base import DocumentParser, ParserError
from .ooxml_common import local_name, parse_xml, read_entries, safe_open_zip, w


def _para_text(node, include_deleted: bool = True) -> str:
    parts: List[str] = []
    for t in node.iter():
        tag = local_name(t.tag)
        if tag in ("t", "delText") and t.text:
            if tag == "delText" and not include_deleted:
                continue
            parts.append(t.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag == "br":
            parts.append("\n")
    return "".join(parts)


def _run_is_hidden(run) -> bool:
    rpr = run.find(w("rPr"))
    if rpr is None:
        return False
    vanish = rpr.find(w("vanish"))
    if vanish is not None and vanish.get(w("val")) not in ("0", "false"):
        return True
    return False


def _run_is_white(run) -> bool:
    rpr = run.find(w("rPr"))
    if rpr is None:
        return False
    color = rpr.find(w("color"))
    if color is not None and (color.get(w("val")) or "").upper() in ("FFFFFF", "FFFFFE"):
        return True
    return False


def _run_font_size(run) -> float:
    rpr = run.find(w("rPr"))
    if rpr is None:
        return 0.0
    sz = rpr.find(w("sz"))
    if sz is None:
        return 0.0
    try:
        return float(sz.get(w("val"), "0")) / 2.0  # half-point
    except ValueError:
        return 0.0


class DocxParser(DocumentParser):
    name = "DocxParser"
    extensions = [".docx", ".docm", ".dotx"]
    mime_types = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-word.document.macroenabled.12",
    ]

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
            raise ParserError(f"DOCX ZIP 처리 실패: {exc}") from exc

        with zf:
            entries = read_entries(zf, lambda n: n.endswith(".xml") or n.endswith(".rels"))
            doc.structure["zip_entries"] = [i.filename for i in zf.infolist()]
            media = [i.filename for i in zf.infolist() if i.filename.startswith("word/media/")]
            doc.structure["embedded_media"] = media

            page = Page(page_number=1)
            xml_layer_parts: List[str] = []
            hidden_parts: List[str] = []
            visible_parts: List[str] = []

            body = entries.get("word/document.xml")
            if body is None:
                raise ParserError("word/document.xml 없음")
            xml_layer_parts.append(body.decode("utf-8", "replace"))
            root = parse_xml(body)

            tracked_inserts: List[Dict[str, Any]] = []
            tracked_deletes: List[Dict[str, Any]] = []
            hidden_runs: List[Dict[str, Any]] = []
            rsids: set[str] = set()
            table_positions = {}
            for table_index, table in enumerate(root.iter(w("tbl"))):
                for row_index, row in enumerate(table.findall(w("tr"))):
                    for column_index, cell in enumerate(row.findall(w("tc"))):
                        for paragraph in cell.iter(w("p")):
                            table_positions[paragraph] = {"table_ref": f"docx_t{table_index}",
                                "row": row_index, "column": column_index}
            paragraph_blocks: Dict[Any, str] = {}             # 표 칸 문단 → 블록 ID(TK-144)

            for para in root.iter(w("p")):
                text = _para_text(para, include_deleted=False)
                in_table = any(local_name(a.tag) == "tbl" for a in para.iterancestors())
                runs = list(para.iter(w("r")))
                hidden_run_texts = []
                for run in runs:
                    rtext = _para_text(run)
                    if not rtext.strip():
                        continue
                    reason = None
                    if _run_is_hidden(run):
                        reason = "W_VANISH"
                    elif _run_is_white(run):
                        reason = "WHITE_FONT"
                    elif 0 < _run_font_size(run) < 3.5:
                        reason = f"TINY_FONT({_run_font_size(run)}pt)"
                    if reason:
                        hidden_run_texts.append(rtext)
                        hidden_runs.append({"text": rtext, "reason": reason})
                    rsid = run.get(w("rsidR")) or run.get(w("rsidRDefault"))
                    if rsid:
                        rsids.add(rsid)

                for ins in para.iter(w("ins")):
                    t = _para_text(ins)
                    if t.strip():
                        tracked_inserts.append(
                            {"text": t, "author": ins.get(w("author"), ""), "date": ins.get(w("date"), "")}
                        )
                for dele in para.iter(w("del")):
                    t = _para_text(dele)
                    if t.strip():
                        tracked_deletes.append(
                            {"text": t, "author": dele.get(w("author"), ""), "date": dele.get(w("date"), "")}
                        )

                visible_text = text
                for h in hidden_run_texts:
                    visible_text = visible_text.replace(h, "")
                if visible_text.strip():
                    block_id = new_id("B")
                    if para in table_positions:
                        paragraph_blocks[para] = block_id
                    page.blocks.append(
                        Block(
                            block_id=block_id,
                            text=visible_text.strip(),
                            page=1,
                            source_layer="visible_text",
                            block_type="table" if in_table else "paragraph",
                            attributes=dict(table_positions.get(para, {})),
                        )
                    )
                    visible_parts.append(visible_text.strip())
                for h in hidden_run_texts:
                    page.blocks.append(
                        Block(
                            block_id=new_id("B"),
                            text=h.strip(),
                            page=1,
                            source_layer="hidden_text",
                            block_type="paragraph",
                            visible=False,
                            attributes={"hidden_reason": next(
                                (r["reason"] for r in hidden_runs if r["text"] == h), "HIDDEN"
                            )},
                        )
                    )
                    hidden_parts.append(h.strip())

            # 표 구조(TK-144): 칸 문단은 이미 table 블록이다. 표 블록을 새로 만들지 않고 행·열 구조만 남긴다
            # (HWP의 LINES_WITH_STRUCTURE와 같은 계약). 계산·사실·첨부 소비자는 structure["tables"]만 본다.
            try:
                tables, partial = _docx_table_structures(root, paragraph_blocks, doc.parse_warnings)
            except Exception as exc:                       # 구조 복원 실패는 본문을 해치지 않는다
                tables, partial = [], []
                doc.parse_warnings.append(f"DOCX 표 구조 복원 실패(본문 텍스트는 유지): {exc}")
            if tables:
                doc.structure["tables"] = tables
            if partial:
                doc.structure["partial_tables"] = partial

            # 머리말/꼬리말/각주/미주/주석
            for entry_name, data in entries.items():
                base = entry_name.split("/")[-1]
                kind = None
                if base.startswith("header"):
                    kind = "header"
                elif base.startswith("footer"):
                    kind = "footer"
                elif base.startswith("footnotes"):
                    kind = "footnote"
                elif base.startswith("endnotes"):
                    kind = "footnote"
                elif base.startswith("comments"):
                    kind = "comment"
                if not kind:
                    continue
                xml_layer_parts.append(data.decode("utf-8", "replace"))
                try:
                    sub = parse_xml(data)
                except Exception:
                    continue
                for para in sub.iter(w("p")):
                    t = _para_text(para).strip()
                    if not t:
                        continue
                    page.blocks.append(
                        Block(
                            block_id=new_id("B"),
                            text=t,
                            page=1,
                            source_layer="visible_text" if kind in ("header", "footer", "footnote") else "xml",
                            block_type=kind,
                            visible=kind != "comment",
                            attributes={"part": entry_name},
                        )
                    )
                    if kind == "comment":
                        hidden_parts.append(t)
                    else:
                        visible_parts.append(t)

            comments_xml = entries.get("word/comments.xml")
            comments: List[Dict[str, Any]] = []
            if comments_xml is not None:
                try:
                    croot = parse_xml(comments_xml)
                    for c in croot.iter(w("comment")):
                        comments.append(
                            {
                                "id": c.get(w("id"), ""),
                                "author": c.get(w("author"), ""),
                                "date": c.get(w("date"), ""),
                                "text": _para_text(c).strip(),
                            }
                        )
                except Exception as exc:  # pragma: no cover
                    doc.parse_warnings.append(f"comments.xml 파싱 실패: {exc}")

            # core / app properties
            props: Dict[str, Any] = {}
            for prop_file in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"):
                data = entries.get(prop_file)
                if data is None:
                    continue
                xml_layer_parts.append(data.decode("utf-8", "replace"))
                try:
                    proot = parse_xml(data)
                except Exception:
                    continue
                for el in proot.iter():
                    tag = local_name(el.tag)
                    if el.text and el.text.strip() and tag not in ("Properties", "coreProperties"):
                        props[tag] = el.text.strip()
                    if tag == "property":
                        pname = el.get("name")
                        pval = "".join(x.text or "" for x in el.iter() if x.text)
                        if pname:
                            props[f"custom:{pname}"] = pval.strip()
            doc.metadata.update(props)

            custom_xml = {k: v.decode("utf-8", "replace") for k, v in entries.items() if k.startswith("customXml/")}
            doc.structure.update(
                {
                    "tracked_inserts": tracked_inserts,
                    "tracked_deletes": tracked_deletes,
                    "hidden_runs": hidden_runs,
                    "comments": comments,
                    "rsids": sorted(rsids),
                    "custom_xml": custom_xml,
                    "properties": props,
                }
            )
            doc.pages.append(page)

        doc.raw_layers["rendered_text"] = "\n".join(visible_parts)
        doc.raw_layers["raw_text"] = "\n".join(visible_parts + hidden_parts)
        doc.raw_layers["hidden_text"] = "\n".join(hidden_parts)
        doc.raw_layers["xml"] = "\n".join(xml_layer_parts)
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


# --- DOCX 표 구조(TK-144) -------------------------------------------------------------------------------------------
DOCX_MAX_ROWS = 2000
DOCX_MAX_COLS = 100
DOCX_MAX_DOC_CELLS = 200_000


def _docx_table_structures(root, paragraph_blocks, warnings):
    """w:tbl을 행·열 표로 만든다. 가로 병합(gridSpan)·세로 병합(vMerge)은 앵커 칸에만 값을 두고 덮인 칸은 비운다.

    칸 글자는 그 칸에 직접 딸린 문단만 모은다(안쪽 표 문단은 안쪽 표에). 주소를 맞출 수 없거나 상한을 넘으면
    불완전한 표로 두고 소비자에 넘기지 않는다.
    """
    tables, partial, budget = [], [], 0
    all_tables = list(root.iter(w("tbl")))
    position = {id(t): i for i, t in enumerate(all_tables)}
    for index, tbl in enumerate(all_tables):
        ref = f"docx_t{index}"
        rows = tbl.findall(w("tr"))
        placed, complete, merges, covered = [], True, [], []
        open_vmerge = {}                                  # 열 → 세로 병합 앵커 (행, 열)
        width = 0
        for r_i, tr in enumerate(rows):
            col = 0
            for tc in tr.findall(w("tc")):
                pr = tc.find(w("tcPr"))
                span_el = pr.find(w("gridSpan")) if pr is not None else None
                vm_el = pr.find(w("vMerge")) if pr is not None else None
                try:
                    span = max(1, int(span_el.get(w("val")))) if span_el is not None else 1
                except (TypeError, ValueError):
                    span, complete = 1, False
                vmerge = None if vm_el is None else (vm_el.get(w("val")) or "continue")
                texts = [p for p in tc.iter(w("p"))
                         if next((a for a in p.iterancestors() if local_name(a.tag) == "tc"), None) is tc]
                block_ids = [paragraph_blocks[p] for p in texts if p in paragraph_blocks]
                if vmerge == "continue" and col in open_vmerge:
                    anchor = open_vmerge[col]
                    covered.extend([r_i, c] for c in range(col, col + span))
                    anchor["row_span"] += 1
                    anchor["block_ids"].extend(block_ids)
                else:
                    cell = {"row": r_i, "col": col, "row_span": 1, "col_span": span, "paras": texts,
                            "block_ids": block_ids}
                    placed.append(cell)
                    if vmerge == "restart":
                        open_vmerge[col] = cell
                    else:
                        open_vmerge.pop(col, None)
                    covered.extend([r_i, c] for c in range(col + 1, col + span))
                col += span
            width = max(width, col)
        height = len(rows)
        nested = any(local_name(a.tag) == "tbl" for a in tbl.iterancestors())
        parent = next((a for a in tbl.iterancestors() if local_name(a.tag) == "tbl"), None)
        if not (0 < height <= DOCX_MAX_ROWS and 0 < width <= DOCX_MAX_COLS) or budget + height * width > DOCX_MAX_DOC_CELLS:
            warnings.append(f"{ref}: 표 크기 {height}x{width}가 상한을 넘거나 없어 표 구조를 만들지 않았다")
            continue
        budget += height * width
        grid = [["" for _ in range(width)] for _ in range(height)]
        line_ids = []
        for cell in placed:
            text = " ".join(_para_text(p, include_deleted=False).strip() for p in cell["paras"]
                            if _para_text(p, include_deleted=False).strip())
            grid[cell["row"]][cell["col"]] = text
            line_ids.extend(cell["block_ids"])
            if cell["row_span"] > 1 or cell["col_span"] > 1:
                merges.append({k: cell[k] for k in ("row", "col", "row_span", "col_span")})
        entry = {"table_ref": ref, "page": 1, "table_index": len(tables), "cells": grid, "header": grid[0],
                 "title": None, "row_count": height, "column_count": width, "merges": merges, "covered": covered,
                 "nested": nested, "parent_table_ref": f"docx_t{position[id(parent)]}" if parent is not None else None,
                 "complete": complete, "representation": "LINES_WITH_STRUCTURE", "source": "DOCX_XML",
                 "line_block_ids": line_ids}
        if complete:
            tables.append(entry)
        else:
            partial.append({k: entry[k] for k in ("table_ref", "row_count", "column_count", "nested",
                                                  "parent_table_ref")} | {"reason": "INCOMPLETE_STRUCTURE"})
    return tables, partial
