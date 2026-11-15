"""온라인 검증 보고서(JSON)를 정답 명세로 채점한다(평가 에이전트 소관, 보호 경로).

사용자는 새 서면을 실제 환경(네트워크·모델·Drive)에서 돌려 보고서 JSON을 준다. 오프라인 점검(`probe_document.py`)이 재지 못하는
AI 작성 판정·공식 DB 대조·Drive 대조·모델 경로를 이 도구가 같은 명세 형식으로 잰다. 보고서에는 그 보고서를 만든 커밋이 들어 있으므로
'어느 코드가 낸 점수인지'가 기록된다. 입력 조건이 사용자 환경이라 오프라인 점수와 섞어 증감을 비교하지 않는다.

    python scripts/score_report.py --report <보고서.json> --spec tests/fixtures/probes/case7_suspension_online.json
    python scripts/score_report.py --report ... --spec ... --record --note "서면7 수신 직후"   # docs/scorecards/first_touch_log.jsonl에 한 줄

명세 항목(kind)
- finding       : 조건에 맞는 finding이 있다(probe_document와 같은 조건: types, min_severity, statuses, text_all, text_any)
- no_finding    : 조건에 맞는 finding이 없다
- pii_kind      : 마스킹 요약(masked_preview.kinds)에 kind가 1건 이상 있다(종류 단위. 항목별 마스킹 여부는 보고서에 없다)
- ai_verdict    : 문서별 AI 작성 판정이 any_of 중 하나다
- ai_models     : 모델 의견 중 min_score 이상이면서 AI 쪽(verdict가 AI_로 시작)인 것이 at_least개 이상이다
- rag_relationship : Drive 대조 의견(engine_data.rag.observations) 중 relationship이 같고 claim_quote에 text가 든 것이 있다.
                     항목에 "scope": "claim"이 있으면 의견의 claim_id로 찾은 주장 원문(documents[].claims[].text)에 text가 들어도
                     통과한다(2026-10-09 사용자 결정: claim_quote는 모델이 고른 인용 범위라 같은 주장에 대한 같은 의견도 범위에 따라
                     결과가 갈렸다). 명세 머리의 rule_version이 기록에 남는다. 규칙 판이 다른 점수끼리 증감을 비교하지 않는다.
- no_rag_relationship : rag_relationship과 같은 조건(scope 포함)에 맞는 의견이 없다(대조군: 참고자료와 맞는 주장에 '모순' 의견이
                     나오지 않아야 한다, 2026-10-09 D4 재검토 1단계)
- run_health    : 실행 기록(run_manifest)으로 파이프라인이 의도대로 돌았는지 본다(2026-11-14 평가 체계 감사 보완).
                  finding 항목이 다 맞아도 단계가 예외를 삼키거나 공식 DB·Drive·모델이 실제로 일하지 않았으면 실패한다.
                  check 값:
                  · engine_errors   : 엔진 단계 오류가 없다(allow에 적은 '단계:예외 종류'·'단계'는 제외)
                  · law_db_ready    : 국가법령정보(law_go_kr) 연결이 READY다
                  · source_lookups  : 공식 DB 조회가 min_requests번 이상이고 재시도 실패가 max_retryable_failures 이하다
                  · models_ok       : 모델 호출 실패 비율이 max_failed_ratio 이하이고 호출이 min_calls번 이상이다
                  · reference_sync  : Drive 참고자료 동기화가 끝났다(reference_sync 단계 오류 없음, 참고자료 상태 READY)
                  · commit_present  : 보고서에 배포 커밋(implementation.git_commit)이 있다
- rag_source_selected     : Drive 대조에 쓰인 참고자료(engine_data.rag.sources) 중 제목에 title이 든 것이 있다.
                            "expect": false면 없어야 통과(무관 자료가 뽑히지 않는지 보는 음성 대조군, U3)
- rag_source_relationship : 제목에 title이 든 참고자료에서 나온 의견 중 relationship이 any_of에 드는 것이 있다.
                            "expect": false면 없어야 통과(지지 자료에서 '모순', 무관 자료에서 '지지·모순'이 나오지 않는지, U3)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "scorecards" / "first_touch_log.jsonl"
KINDS = {"finding", "no_finding", "pii_kind", "ai_verdict", "ai_models", "rag_relationship", "no_rag_relationship",
         "run_health", "rag_source_selected", "rag_source_relationship"}
HEALTH_CHECKS = {"engine_errors", "law_db_ready", "source_lookups", "models_ok", "reference_sync", "commit_present"}


def _probe():
    spec = importlib.util.spec_from_file_location("probe_document", ROOT / "scripts" / "probe_document.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("probe_document", module)
    spec.loader.exec_module(module)
    return module


def load_spec(path: Path) -> Dict[str, Any]:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = [c["id"] for c in spec["checks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("명세의 항목 id가 겹친다")
    for check in spec["checks"]:
        if check["kind"] not in KINDS:
            raise ValueError(f"알 수 없는 kind: {check['kind']}")
        if check.get("scope", "quote") not in ("quote", "claim"):
            raise ValueError(f"알 수 없는 scope: {check.get('scope')}")
        if check["kind"] == "run_health" and check.get("check") not in HEALTH_CHECKS:
            raise ValueError(f"알 수 없는 run_health check: {check.get('check')}")
    return spec


def observe_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """보고서 JSON에서 채점에 쓰는 관찰값만 뽑는다. 모든 문서를 합친다."""
    findings: List[Dict[str, str]] = []
    pii_kinds: Dict[str, int] = {}
    verdicts: List[str] = []
    models: List[Dict[str, Any]] = []
    rag: List[Dict[str, Any]] = []
    rag_sources: List[str] = []
    claim_texts: Dict[str, str] = {}
    for doc in report.get("documents", []):
        for claim in doc.get("claims") or []:
            if claim.get("claim_id"):
                claim_texts[str(claim["claim_id"])] = str(claim.get("text") or "")
        for f in doc.get("findings", []):
            findings.append({"type": str(f.get("type")), "severity": str(f.get("severity")),
                             "status": str(f.get("status")), "text": json.dumps(f, ensure_ascii=False, default=str)})
        for kind, count in ((doc.get("masked_preview") or {}).get("kinds") or {}).items():
            pii_kinds[kind] = pii_kinds.get(kind, 0) + int(count)
        detector = doc.get("ai_detector_result") or {}
        models.extend(detector.get("model_opinions") or [])
        rag_data = (doc.get("engine_data") or {}).get("rag") or {}
        titles = {str(s.get("source_id")): str(s.get("title") or "") for s in rag_data.get("sources") or []}
        rag_sources.extend(titles.values())
        for observation in rag_data.get("observations") or []:
            rag.append({**observation, "_source_title": titles.get(str(observation.get("source_id")), "")})
    for f in report.get("project_findings") or []:
        findings.append({"type": str(f.get("type")), "severity": str(f.get("severity")),
                         "status": str(f.get("status")), "text": json.dumps(f, ensure_ascii=False, default=str)})
    for entry in ((report.get("scores") or {}).get("axes") or {}).get("ai_authorship", {}).get("documents", []):
        verdicts.append(str(entry.get("verdict")))
    manifest = report.get("run_manifest") or {}
    return {"rag_sources": rag_sources, "findings": findings, "pii_kinds": pii_kinds, "ai_verdicts": verdicts, "ai_models": models, "rag": rag, "claim_texts": claim_texts,
            "commit": ((manifest.get("implementation") or {}).get("git_commit") or "")[:12],
            "versions": manifest.get("versions") or {},
            "network": bool(((manifest.get("environment") or {}).get("network"))),
            "manifest": manifest,
            "run_id": report.get("run_id"), "started_at": report.get("started_at")}


def evaluate(spec: Dict[str, Any], obs: Dict[str, Any]) -> List[Dict[str, Any]]:
    probe = _probe()
    rows = []
    for check in spec["checks"]:
        kind = check["kind"]
        if kind in ("finding", "no_finding"):
            hit = any(probe._finding_matches(f, check) for f in obs["findings"])
            passed = hit if kind == "finding" else not hit
        elif kind == "pii_kind":
            passed = obs["pii_kinds"].get(check["kind_name"], 0) >= 1
        elif kind == "ai_verdict":
            passed = any(v in check["any_of"] for v in obs["ai_verdicts"])
        elif kind == "ai_models":
            ai = [m for m in obs["ai_models"]
                  if float(m.get("score") or 0) >= float(check.get("min_score", 0))
                  and str(m.get("verdict", "")).startswith("AI_")]
            passed = len(ai) >= int(check.get("at_least", 1))
        elif kind == "rag_source_selected":
            hit = any(check["title"] in title for title in obs.get("rag_sources") or [])
            passed = hit if check.get("expect", True) else not hit
        elif kind == "rag_source_relationship":
            hit = any(check["title"] in o.get("_source_title", "") and o.get("relationship") in check["any_of"]
                      for o in obs["rag"])
            passed = hit if check.get("expect", True) else not hit
        elif kind == "run_health":
            passed, detail = run_health(check, obs.get("manifest") or {})
            rows.append({"id": check["id"], "label": check.get("label", ""), "passed": bool(passed), "detail": detail})
            continue
        else:  # rag_relationship / no_rag_relationship
            claim_scope = check.get("scope") == "claim"
            texts = obs.get("claim_texts") or {}
            passed = any(o.get("relationship") == check["relationship"]
                         and (check["text"] in str(o.get("claim_quote", ""))
                              or (claim_scope and check["text"] in texts.get(str(o.get("claim_id")), "")))
                         for o in obs["rag"])
            if kind == "no_rag_relationship":
                passed = not passed
        rows.append({"id": check["id"], "label": check.get("label", ""), "passed": bool(passed)})
    return rows


def run_health(check: Dict[str, Any], manifest: Dict[str, Any]) -> tuple:
    """(통과 여부, 근거 한 줄). 근거에는 단계 이름·상태·건수만 쓴다(문서 내용 없음)."""
    which = check["check"]
    engines = manifest.get("engines") or {}
    if which == "engine_errors":
        allow = set(check.get("allow") or [])
        bad = []
        for stage, entry in sorted(engines.items()):
            if not isinstance(entry, dict):
                continue
            for error in entry.get("errors") or []:
                kind = str(error).rsplit(": ", 1)[-1].strip()
                if stage in allow or f"{stage}:{kind}" in allow:
                    continue
                bad.append(f"{stage}:{kind}")
        return not bad, ("오류 " + ", ".join(sorted(set(bad)))) if bad else "엔진 오류 없음"
    if which == "law_db_ready":
        status = (manifest.get("sources") or {}).get("law_go_kr") or ((manifest.get("environment") or {}).get("law_db") or {}).get("status")
        return status == "READY", f"law_go_kr {status}"
    if which == "source_lookups":
        summary = manifest.get("source_lookup_summary") or {}
        requests = int(summary.get("requests") or summary.get("total_requests") or 0)
        failures = int(summary.get("retryable_failures") or summary.get("total_retryable_failures") or 0)
        ok = requests >= int(check.get("min_requests", 1)) and failures <= int(check.get("max_retryable_failures", 0))
        return ok, f"조회 {requests}건, 재시도 실패 {failures}건, 상태 {summary.get('by_status') or {}}"
    if which == "models_ok":
        summary = manifest.get("model_execution_summary") or {}
        providers = summary.get("providers") or {}
        calls = sum(int(p.get("calls") or 0) for p in providers.values())
        failed = sum(int(p.get("failed") or 0) for p in providers.values())
        ratio = failed / calls if calls else 0.0
        ok = calls >= int(check.get("min_calls", 1)) and ratio <= float(check.get("max_failed_ratio", 0.1))
        kinds = sorted({k.split(":", 1)[0] for p in providers.values() for k in (p.get("errors") or {})})
        return ok, f"호출 {calls}건, 실패 {failed}건({ratio:.0%})" + (f", 실패 종류 {', '.join(kinds)}" if kinds else "")
    if which == "reference_sync":
        library = manifest.get("reference_library") or {}
        diagnostics = library.get("diagnostics") or {}
        errors = (engines.get("reference_sync") or {}).get("errors") or []
        status = library.get("status")
        issues = diagnostics.get("issue_counts") or {}
        tables = diagnostics.get("case_table_candidates") or []
        table_rows = sum(int(t.get("indexed_rows") or 0) for t in tables if isinstance(t, dict))
        quarantined_tables = sum(1 for t in tables if isinstance(t, dict) and t.get("reason") == "REFERENCE_QUARANTINED")
        ok = (not errors and status == "READY") or bool(
            check.get("allow_partial") and status == "PARTIAL"
            and int(issues.get("REFERENCE_QUARANTINED", 0)) <= int(check.get("max_quarantined", 0))
            and quarantined_tables == 0)
        detail = (f"참고자료 {status}, 색인 {library.get('files_indexed')}/{library.get('files_seen')}개, 동기화 오류 {len(errors)}건, "
                  f"문제 {dict(sorted(issues.items()))}, 판례표 후보 {len(tables)}개(격리 {quarantined_tables}, 색인 행 {table_rows})")
        return ok, detail
    commit = str(((manifest.get("implementation") or {}).get("git_commit")) or "")
    return bool(commit), f"커밋 {commit[:12] or '없음'}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def score(report_path: Path, spec_path: Path) -> Dict[str, Any]:
    spec = load_spec(spec_path)
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    obs = observe_report(report)
    rows = evaluate(spec, obs)
    failed = [r["id"] for r in rows if not r["passed"]]
    return {"spec": spec["name"], "rule_version": spec.get("rule_version", "1"), "rows": rows, "total": len(rows),
            "passed": len(rows) - len(failed), "failed": failed,
            "commit": obs["commit"], "versions": obs["versions"], "network": obs["network"], "run_id": obs["run_id"],
            "report_sha256": sha256_file(Path(report_path))}


def render(result: Dict[str, Any]) -> str:
    lines = [f"{result['spec']}(규칙 {result.get('rule_version', '1')}판) — 온라인 보고서 {result['passed']}/{result['total']} "
             f"(커밋 {result['commit'] or '?'}, 네트워크 {'켬' if result['network'] else '끔'}, run {result['run_id']})"]
    for row in result["rows"]:
        lines.append(f"  {'통과' if row['passed'] else '실패'}  {row['id']:<8} {row['label']}"
                     + (f" — {row['detail']}" if row.get("detail") else ""))
    return "\n".join(lines)


def record(result: Dict[str, Any], note: str, log: Path = LOG) -> None:
    entry = {"recorded": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sha": result["commit"],
             "measured_commit": result["commit"], "backfilled": False, "spec": result["spec"],
             "rule_version": result.get("rule_version", "1"), "input": "online_report",
             "passed": result["passed"], "total": result["total"], "failed": result["failed"], "note": note,
             "condition": "online(사용자 환경: 네트워크·모델·Drive), 보고서 JSON 채점",
             "report_sha256": result["report_sha256"], "run_id": result["run_id"], "versions": result["versions"]}
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--note", default="")
    parser.add_argument("--log", type=Path, default=LOG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = score(args.report, args.spec)
    print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    if args.record:
        record(result, args.note, args.log)
        print(f"기록: {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
