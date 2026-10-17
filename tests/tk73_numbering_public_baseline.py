"""Test-only original public numbering logic; never imported by product.

Frozen verbatim from Steve1d279d0 before TK73 activation. Historical labels
and expectations remain intact while the candidate follows the installed engine.
"""
from unittest.mock import patch
from packages.claim_engine import evidence_consistency as engine

BASE_SHA = "1d279d0a785dfcc5099daef530dde5006ea1c7c4"
SOURCE_SHA256 = '24aaeeba95453e5c31de51d8852529945b4896afdc22f754a880acbeded532e5'
SOURCE = r'''def _numbering(doc: NormalizedDocument, rows: List[Dict[str, Any]]) -> List[Finding]:
    out: List[Finding] = []
    # 같은 호증 번호(가지번호까지 같음)가 목록에 두 번 이상 나온다(v4 P4)
    # 목록 구역(표 또는 번호 붙은 입증방법 섹션)에 존재하는 호증 번호는 본문 언급을 중복 판단에서 제외 (TK-64)
    section_keys = {
        (r["party"], r["number"])
        for r in rows
        if r.get("in_section", not r.get("from_lines", False))
    }

    seen: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        is_in_section = row.get("in_section", not row.get("from_lines", False))
        # 목록 구역이 존재하는 서면에서, 해당 목록 구역에 이미 등록된 번호의 본문 행은 중복 집계에서 제외
        if section_keys and not is_in_section and (row["party"], row["number"]) in section_keys:
            continue
        keys = [(row["party"], row["number"], b) for b in row.get("branches") or []] or [(row["party"], row["number"], None)]
        for key in keys:
            seen.setdefault(key, []).append(row)
    for (party, number, branch), same in seen.items():
        if len(same) < 2:
            continue
        # 서증명이 실질적으로 상이한 증거에 부여된 경우만 중복 번호로 확정 (단순 반복 기재 제외, FP-01)
        distinct_names = {re.sub(r"\s", "", r.get("name") or "") for r in same}
        distinct_names.discard("")
        if len(distinct_names) < 2 and len(same) >= 2 and all(r.get("name") for r in same):
            continue
        label = f"{party} 제{number}호증" + (f"의 {branch}" if branch else "")
        names = ", ".join(r.get("name") or "(이름 없음)" for r in same)
        out.append(_finding(doc, FindingType.EVIDENCE_LIST_MISMATCH, EvidenceGrade.A, Severity.MEDIUM,
                            f"같은 호증 번호가 두 번 쓰였다: {label} — {names}",
                            "증거 목록에서 한 번호를 서로 다른 증거에 두 번 붙였다. 어느 증거를 가리키는지 "
                            "특정할 수 없으므로 번호를 바로잡아야 한다.", f"{label}: {names}",
                            features={"rule_id": "EVI.EVIDENCE_NUMBER_DUPLICATE",
                                      "defect_code": "EVIDENCE_NUMBER_DUPLICATE", "exhibit": label,
                                      "names": [r.get("name") for r in same]}))
    listed: Dict[str, set] = {}
    for row in rows:
        listed.setdefault(row["party"], set()).add(row["number"])
    # 가지번호: '의 2'만 있고 '의 1'이 없으면 결번이다(G5). 범위 표기('의 1 내지 3')는 모두 있는 것으로 본다.
    branches: Dict[tuple, set] = {}
    for row in rows:
        if row.get("branches"):
            branches.setdefault((row["party"], row["number"]), set()).update(row["branches"])
    for (party, number), present in sorted(branches.items()):
        missing = [b for b in range(1, max(present) + 1) if b not in present]
        if missing:
            labels = ", ".join(f"{party} 제{number}호증의 {b}" for b in missing)
            out.append(_finding(doc, FindingType.EVIDENCE_NUMBERING_GAP, EvidenceGrade.B, Severity.MEDIUM,
                                f"가지번호가 비어 있다: {labels} 결번",
                                "같은 호증의 가지번호가 1부터 이어지지 않는다. 누락된 증거가 있는지 확인해야 한다.",
                                ", ".join(f"{party} 제{number}호증의 {b}" for b in sorted(present)),
                                features={"party": party, "number": number, "missing_branches": missing}))
    # 당사자별 결번 판정: 목록 구역이 있으면 구역 번호로만, 구역 최소 번호부터 결번 산출 (TK-67)
    has_any_section = any(r.get("in_section", not r.get("from_lines", False)) for r in rows)
    for party, numbers in listed.items():
        sec_nums = {
            r["number"] for r in rows
            if r["party"] == party and r.get("in_section", not r.get("from_lines", False))
        }
        if has_any_section:
            if not sec_nums:
                # 서면에 목록 구역이 존재하나 해당 당사자는 본문 언급만 있는 경우 결번 판정 제외
                continue
            target_nums = sec_nums
            start_num = min(sec_nums)
        else:
            # 목록 구역이 없는 서면은 기존 동작 유지 (1번부터 결번 산출)
            target_nums = numbers
            start_num = 1
        gaps = [n for n in range(start_num, max(target_nums) + 1) if n not in target_nums]
        if gaps:
            out.append(_finding(doc, FindingType.EVIDENCE_NUMBERING_GAP, EvidenceGrade.B, Severity.MEDIUM,
                                f"호증 번호가 비어 있다: {party} 제{', '.join(map(str, gaps))}호증 결번",
                                "증거 목록의 번호가 연속하지 않는다. 누락된 증거가 있는지 확인해야 한다.",
                                ", ".join(f"{party} 제{n}호증" for n in sorted(target_nums)),
                                features={"party": party, "missing": gaps}))
    text = build_reading_text(doc).text
    mentioned = exhibit_keys(text)
    missing = sorted((p, n) for p, n in mentioned if p in listed and n not in listed[p])
    if missing:
        labels = ", ".join(f"{p} 제{n}호증" for p, n in missing)
        out.append(_finding(doc, FindingType.EVIDENCE_LIST_MISMATCH, EvidenceGrade.B, Severity.MEDIUM,
                            f"본문이 언급한 증거가 증거 목록에 없다: {labels}",
                            "본문에서 입증 근거로 든 호증이 증거 목록에 없다.", labels,
                            features={"missing_from_list": [f"{p} 제{n}호증" for p, n in missing]}))
    return out
'''

_namespace = dict(vars(engine))
exec(compile(SOURCE, "<public-original-numbering>", "exec"), _namespace)
numbering = _namespace["_numbering"]
_unguarded_namespace = dict(vars(engine))
exec(compile(SOURCE.replace('re.sub(r"\\s", "", r.get("name") or "")',
    're.sub(r"\\s", "", re.split(r"[,:]", r.get("name") or "", maxsplit=1)[0])'),
    "<public-unguarded-diagnostic>", "exec"), _unguarded_namespace)
unguarded_numbering = _unguarded_namespace["_numbering"]

def check_exhibits(doc):
    with patch.object(engine, "_numbering", numbering):
        return engine.check_exhibits(doc)

def check_document(doc):
    with patch.object(engine, "_numbering", numbering):
        return engine.check_document(doc)
