"""Synthetic pilot only: execute server and real app.js, no evaluation data."""
import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.rag_engine.reference_binding import bind_observations, compact_text, identifier_match
from packages.verification_engine.review_items import build_document_review_items

ROOT = Path(__file__).resolve().parents[1]


def pilot_cases():
    cases = []
    for index, topic in enumerate(["보관", "전달", "반환", "점검", "기록"], start=1):
        number = f"2097가합88{index:03d}"
        law = f"가상{topic}법"
        claim = f"가상의 {topic} 절차를 이행할 의무가 있다는 합성 주장입니다"
        case = {"citation_id": "c", "raw_text": number, "case_number": number}
        statute = {"citation_id": "c", "raw_text": f"{law} 제{index}조", "law_name": law, "article": str(index)}
        def add(group, citation, excerpt, linked, supported, structural=False, relationship="SUPPORTS"):
            cases.append({"name": f"{group}-{index}", "group": group, "citation": citation,
                          "claim": claim, "excerpt": excerpt, "linked": linked, "supported": supported,
                          "structural": structural, "relationship": relationship})
        add("P1", case, f"{number} 판결의 {topic} 절차 설명입니다.", True, True)
        add("P2", statute, f"「{law}」 제{index}조는 {topic} 절차를 설명합니다.", True, True)
        add("N1", statute, f"{law} 제{index + 20}조. {claim}", False, False)
        if index <= 3:
            add("N2", case, f"2097가합99{index:03d} 판결. {claim}", False, False)
            add("N3", case, claim, False, False)
            add("N4", {"citation_id": "c", "raw_text": claim}, claim, False, False)
            add("S_missing", case if index != 2 else statute, claim, True, False, True)
            add("S_conflict", case if index != 2 else statute,
                f"2097가합77{index:03d}" if index != 2 else f"{law} 제{index + 20}조", True, False, True)
            add("S_match", case if index != 2 else statute,
                number if index != 2 else f"{law} 제{index}조", True, True, True)
            add("S_context", case, number, True, False, True, "CONTEXT")
    return cases


def make_document(case):
    observation = {"claim_id": "claim" if case["structural"] else None, "claim_quote": case["claim"],
                   "source_id": "R1", "source_quote": case["excerpt"], "relationship": case["relationship"],
                   "explanation": "합성 통제 자료 대조 의견"}
    return SimpleNamespace(document_id="synthetic", filename="합성서면.pdf", findings=[],
                           citations=[copy.deepcopy(case["citation"])],
                           claims=[{"claim_id": "claim", "citation_ids": ["c"]}],
                           ai_hallucination_table=[{"citation_id": "c", "claim_text": case["claim"]}],
                           engine_data={"rag": {"drive_used": True, "observations": [observation],
                                                "sources": [{"source_id": "R1", "title": "합성 참고문헌", "text": case["excerpt"]}]}})


def execute_server(case):
    doc = make_document(case)
    items = [i.to_dict() for i in build_document_review_items(doc)]
    unmatched = bind_observations(items, doc)
    return {"doc": vars(doc), "items": items, "unmatched": unmatched,
            "linked": bool(items[0]["reference_observations"]), "supported": items[0]["reference_status"] == "SUPPORTED"}


def execute_browser(server_results):
    script = (ROOT / "apps/web/static/app.js").read_text(encoding="utf-8")
    start = script.index("const EXPLICIT_WHITESPACE_RE")
    end = script.index("function referenceObservationBlock", start)
    runner = script[start:end] + """
const inputs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const output = inputs.map(input => {
  const doc = input.doc;
  const items = input.items.map(item => ({...item, doc}));
  const unmatched = attachReferenceObservations(items, [doc]);
  const second = attachReferenceObservations(items, [doc]);
  return {linked:!!items[0].reference_observations.length,
    supported:items[0].reference_status === 'SUPPORTED',
    observations:items[0].reference_observations, unmatched:unmatched.map(x => x.observation),
    ids:second.map(x => referenceObservationRow(x).item_id),
    official_status:items[0].official_status};
});
process.stdout.write(JSON.stringify(output));
"""
    proc = subprocess.run(["node", "-e", runner], input=json.dumps(server_results),
                          capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(proc.stdout)


@pytest.mark.parametrize("case", pilot_cases(), ids=lambda c: c["name"])
def test_server_contract(case):
    result = execute_server(case)
    assert result["linked"] == case["linked"]
    assert result["supported"] == case["supported"]
    baseline = make_document(case)
    baseline.engine_data = {}
    assert result["items"][0]["official_status"] == build_document_review_items(baseline)[0].to_dict()["official_status"]
    for observation in result["items"][0]["reference_observations"] + result["unmatched"]:
        assert observation["source"] == "google_drive"
        assert observation["official"] is False and observation["binding"] is False


def metrics(expected, actual):
    result = {name: 0 for name in ("TP", "FP", "FN", "TN")}
    for truth, observed in zip(expected, actual, strict=True):
        result[("T" if truth == observed else "F") + ("P" if observed else "N")] += 1
    result["precision"] = result["TP"] / (result["TP"] + result["FP"]) if result["TP"] + result["FP"] else None
    result["coverage"] = result["TP"] / (result["TP"] + result["FN"]) if result["TP"] + result["FN"] else None
    return result


def benchmark(cases, server, browser):
    groups = {}
    for group in sorted({c["group"] for c in cases}):
        indices = [i for i, c in enumerate(cases) if c["group"] == group]
        groups[group] = {"n": len(indices)}
        for engine, outputs in (("server", server), ("browser", browser)):
            groups[group][engine] = {axis: metrics([cases[i][axis] for i in indices], [outputs[i][axis] for i in indices])
                                     for axis in ("linked", "supported")}
    sufficient = all(groups.get(k, {}).get("n", 0) >= n for k, n in
                     {"P1": 5, "P2": 5, "N1": 5, "N2": 3, "N3": 2, "N4": 2,
                      "S_missing": 3, "S_conflict": 3, "S_match": 3, "S_context": 3}.items())
    total = {engine: {axis: metrics([c[axis] for c in cases], [o[axis] for o in outputs]) for axis in ("linked", "supported")}
             for engine, outputs in (("server", server), ("browser", browser))}
    agreement = all((s["linked"], s["supported"]) == (b["linked"], b["supported"]) for s, b in zip(server, browser, strict=True))
    passed = sufficient and agreement and all(
        total[e]["linked"]["precision"] == 1 and total[e]["supported"]["FP"] == 0
        and sum(groups[g][e]["linked"]["TP"] for g in ("P1", "P2")) >= 8
        and all((groups[g][e]["linked"]["coverage"] or 0) >= .8 for g in ("P1", "P2")) for e in total)
    return {"scope": "합성 통제 파일럿; 통계적 보증 아님", "production_drive": "미측정",
            "groups": groups, "total": total, "agreement": agreement,
            "status": "PASS" if passed else "INDETERMINATE", "sufficient_sample": sufficient}


def test_node_parity_and_dynamic_pilot(tmp_path):
    cases = pilot_cases()
    server = [execute_server(c) for c in cases]
    browser = execute_browser(server)
    for expected, s, b in zip(cases, server, browser, strict=True):
        assert b["linked"] == expected["linked"] and b["supported"] == expected["supported"]
        assert b["observations"] == s["items"][0]["reference_observations"]
        assert b["unmatched"] == s["unmatched"]
        assert b["official_status"] == s["items"][0]["official_status"]
        assert b["ids"] == ([] if s["linked"] else ["synthetic_REFERENCE_O0"])
    report = benchmark(cases, server, browser)
    (tmp_path / "pilot.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    assert report["status"] == "PASS"
    assert benchmark(cases[:1], server[:1], browser[:1])["status"] == "INDETERMINATE"
    zeros = [{"linked": False, "supported": False} for _ in cases]
    assert benchmark(cases, zeros, zeros)["status"] == "INDETERMINATE"
    assert metrics([True], [False])["precision"] is None


@pytest.mark.parametrize("space", ["\ufeff", "\u001c\u001d\u001e\u001f", "\u00a0", "\u3000", "\t\r\n"])
def test_normalization_parity(space):
    case = pilot_cases()[0]
    case["excerpt"] = space.join(case["citation"]["case_number"])
    server = execute_server(case)
    browser = execute_browser([server])[0]
    assert server["linked"] and browser["linked"] and browser["supported"]
    assert compact_text(case["excerpt"]) == case["citation"]["case_number"]


@pytest.mark.parametrize("article", ["제7조의2", "제8조제2항", "제9조제3호"])
def test_complete_article_boundary(article):
    citation = {"law_name": "가상기록법", "article": article}
    assert identifier_match(citation, "가상기록법 " + article)["full"]
    assert not identifier_match(citation, "가상기록법 " + article + "0")["full"]


@pytest.mark.parametrize("law", ["가상보관법", "가상운송법", "가상점검법"])
def test_law_name_boundary_and_unique_fallback(law):
    case = {"name": "fallback", "group": "fallback", "citation": {"citation_id": "c", "law_name": law, "article": "13"},
            "claim": f"{law} 관련 보관과 운송 및 점검의 구체적인 절차를 확인하는 가상 주장", "structural": False,
            "relationship": "SUPPORTS", "linked": True, "supported": True}
    case["excerpt"] = law + " " + "가" * 120 + " 제13조"
    server = execute_server(case)
    assert server["linked"] and execute_browser([server])[0]["linked"]
    duplicate = copy.deepcopy(server)
    duplicate["items"].append({**duplicate["items"][0], "item_id": "second", "citation_id": "second"})
    duplicate["doc"]["citations"].append({**case["citation"], "citation_id": "second"})
    assert len(bind_observations(duplicate["items"], duplicate["doc"])) == 1
    assert not execute_browser([duplicate])[0]["linked"]
    case["excerpt"] = "다른" + law + " 제13조"
    rejected = execute_server(case)
    assert not rejected["linked"] and not execute_browser([rejected])[0]["linked"]
    case["excerpt"] = law + "률 제13조"
    suffix = execute_server(case)
    assert not suffix["linked"] and not execute_browser([suffix])[0]["linked"]
    # UTF-16 code units must not turn seven characters into a 15-character quote.
    case["excerpt"] = law + " " + "가" * 120 + " 제13조"
    case["claim"] = "🧾" * 8
    short = execute_server(case)
    assert not short["linked"] and not execute_browser([short])[0]["linked"]
