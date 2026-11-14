"""TK-162 판례 효력 확인: 서면이 인용한 대법원 판례가 뒤의 전원합의체 판결에서 변경 대상으로 적혔는지 역조회한다.

- 대법원이 종전 판례를 변경하려면 전원합의체가 판단한다(법원조직법 제7조 제1항 제3호). 변경한 판결 이유에는
  "… 판결 등은 이 판결의 견해에 배치되는 범위에서 (이를) (모두) 변경하기로 한다" 문장이 실린다.
- 공식 원문으로 실재가 확인된 대법원 판례만 대상이다. 그 사건번호로 공식 판례 본문을 검색하고, 뒤에 선고된 판결의
  전문에서 위 문장을 찾아 변경 대상 사건번호 목록에 인용 판례가 있는지 본다.
- 찾으면 경고(사람 검토 필요)다. '배치되는 범위'가 서면의 주장과 겹치는지는 사람이 판단한다. 찾지 못한 것은
  '변경되지 않았다'는 확인이 아니다(조회 범위·상한 안에서 찾지 못했을 뿐이다).
- 인용 확인 엔진 밖, 처리 흐름(파이프라인)의 별도 단계 'precedent_change'에서 돈다. 인용 확인의 조회·재조회
  흐름과 횟수에 끼지 않는다. 빠른 검토(QUICK)에서는 건너뛴다. 조회 상한을 둔다.
- 사건번호를 제품 코드에 넣지 않는다(하드코딩 금지). 판정 근거는 공식 판결 원문의 문장이다.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from packages.common.enums import AdapterStatus, EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding

from .authority_status import get_court_tier
from .normalize import canonical_case_number, extract_all_case_numbers

MAX_CITATIONS = 8        # 한 번의 인용 확인에서 역조회할 판례 수 상한
MAX_FETCH_PER_CITATION = 3  # 판례마다 전문을 받아 볼 뒤 판결 수 상한
SEARCH_DISPLAY = 20

# 변경 문장의 끝. 앞부분(변경 대상 목록)은 문장 시작까지 거슬러 올라가 잡는다.
OVERRULE_END_RE = re.compile(
    r"견해에\s*배치되는\s*범위\s*(?:내)?에서\s*(?:이를\s*)?(?:모두\s*)?변경(?:하기로\s*한다|한다)")
# 문장 끝: '다.'·'함.' 뒤 공백. 날짜 '2008. 2. 14.'의 마침표는 숫자 뒤라 끝으로 보지 않는다.
SENTENCE_END_RE = re.compile(r"(?<=[다함음])\.\s")
LOOKBACK = 1200


def overruling_sentences(text: str) -> List[Dict[str, Any]]:
    """판결 전문에서 판례 변경 문장과 그 안의 변경 대상 사건번호(정규형)를 뽑는다."""
    out: List[Dict[str, Any]] = []
    for m in OVERRULE_END_RE.finditer(text or ""):
        window = text[max(0, m.start() - LOOKBACK):m.start()]
        ends = list(SENTENCE_END_RE.finditer(window))
        head = window[ends[-1].end():] if ends else window
        sentence = re.sub(r"\s+", " ", head + m.group(0)).strip()
        numbers = []
        for year, code, serial in extract_all_case_numbers(sentence):
            number = f"{year}{code}{serial}"
            if number not in numbers:
                numbers.append(number)
        if numbers:
            out.append({"sentence": sentence, "case_numbers": numbers})
    return out


def _later(candidate: Dict[str, Any], cited_date: Optional[str]) -> bool:
    date = str(candidate.get("decision_date") or "")
    return not cited_date or not date or date > cited_date


def _korean_date(value: Any) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value or ""))
    return f"{m.group(1)}. {int(m.group(2))}. {int(m.group(3))}." if m else str(value or "")


def _finding(citation, change: Dict[str, Any]) -> Finding:
    by = change["overruled_by"]
    decided = f"{_korean_date(by.get('decision_date'))} 선고 " if by.get("decision_date") else ""
    label = f"{by.get('court') or '대법원'} {decided}{by.get('case_number') or ''} {by.get('case_kind') or '판결'}".strip()
    return Finding.create(
        FindingType.CASE_HOLDING_DISTORTION, VerificationStatus.SUSPICIOUS, Severity.HIGH, EvidenceGrade.A,
        f"뒤의 판결로 변경된 판례 인용 의심: {citation.raw_text}",
        # 칸에는 핵심만 둔다(사용자 11-14 '핵심내용만 간략하게'). 변경 문장 전문은 근거(evidence)에 싣는다.
        detail=(f"{label}이 이 판례를 변경 대상으로 적었습니다. 변경된 범위('이 판결의 견해에 배치되는 범위')가 "
                f"서면의 주장과 겹치는지 확인하세요."),
        confidence=0.85,
        confidence_features={"citation_id": citation.citation_id, "rule_id": "TK162.PRECEDENT_OVERRULED",
                             "verdict_label": "PRECEDENT_OVERRULED", "defect_summary": "뒤의 판결로 변경된 판례 인용",
                             "grounded_evidence_quote": change["sentence"][:300], "overruled_by": by,
                             "deterministic_rule": False},
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", tags=["LEGAL", "CASE", "PRECEDENT_OVERRULED"],
        evidence=[Evidence.create(description="뒤에 선고된 판결의 판례 변경 문장(공식 원문)", grade=EvidenceGrade.A,
                                  excerpt=change["sentence"][:300])])


def check_precedent_change(adapter: Any, citation, official: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """판례 하나를 역조회한다. 반환 status: OVERRULED · NOT_FOUND_IN_SCOPE · INCOMPLETE · LOOKUP_FAILED."""
    official = official or {}
    cited = canonical_case_number(official.get("case_number") or citation.canonical_case_number or citation.case_number or "")
    cited_date = str(official.get("decision_date") or citation.decision_date or "") or None
    response = adapter.search_cases_by_query(cited, org="400201", display=SEARCH_DISPLAY)
    if response.status != AdapterStatus.READY:
        return {"status": "LOOKUP_FAILED", "reason": str(response.status), "checked": 0}
    candidates = [r for r in (response.records or [])
                  if canonical_case_number(str(r.get("case_number") or "")) != cited and _later(r, cited_date)]
    # 전원합의체 판결을 먼저(최근 것부터), 그다음 나머지 판결을 최근 것부터 본다.
    enbanc = [r for r in candidates if str(r.get("case_kind") or "") == "전원합의체 판결"]
    others = sorted((r for r in candidates if r not in enbanc), key=lambda r: str(r.get("decision_date") or ""), reverse=True)
    ordered = sorted(enbanc, key=lambda r: str(r.get("decision_date") or ""), reverse=True) + others
    checked = 0
    for record in ordered[:MAX_FETCH_PER_CITATION]:
        text = record.get("full_text")
        if not text and hasattr(adapter, "fetch_case"):
            detail = adapter.fetch_case(record)
            if detail.status != AdapterStatus.READY or not detail.records:
                continue
            text = detail.records[0].get("full_text") or ""
        checked += 1
        for item in overruling_sentences(text or ""):
            if cited in item["case_numbers"]:
                by = {k: record.get(k) for k in ("court", "decision_date", "case_number", "case_kind", "source_id")}
                by["detail_link"] = record.get("detail_link")
                return {"status": "OVERRULED", "overruled_by": by, "sentence": item["sentence"], "checked": checked,
                        "candidates": len(ordered)}
    return {"status": "NOT_FOUND_IN_SCOPE" if len(ordered) <= MAX_FETCH_PER_CITATION else "INCOMPLETE",
            "checked": checked, "candidates": len(ordered),
            "note": "조회 범위·상한 안에서 변경 문장을 찾지 못했다. 변경되지 않았다는 확인은 아니다."}


_CONFIRMED = {str(VerificationStatus.VERIFIED), str(VerificationStatus.PARTIALLY_VERIFIED)}


def review_precedent_changes(legal: Any, citations: List[Any], verdicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """파이프라인 단계: 인용 확인이 끝난 판정(engine_data.legal_verdicts) 가운데 공식 원문으로 확인된 대법원 판례를
    역조회한다. 판정 사전의 review['precedent_change']에 결과를 적고, 경고는 돌려준다(호출 측이 결과에 더한다).
    판정 status(실재 확인)는 바꾸지 않는다. 기준일별 판정에 같은 인용이 여러 번 있어도 조회·경고는 한 번이다."""
    by_id = {c.citation_id: c for c in citations}
    targets = []
    for verdict in verdicts:
        citation = by_id.get(verdict.get("citation_id"))
        if citation is None or not verdict.get("official_record") or str(verdict.get("status")) not in _CONFIRMED \
                or get_court_tier(citation) != "SUPREME":
            continue
        targets.append((verdict, citation))
    summary: Dict[str, Any] = {"status": "NO_TARGET", "targets": 0, "looked_up": 0, "findings": []}
    if not targets:
        return summary
    adapter = getattr(getattr(legal, "registry", None), "law", None)
    ready = adapter is not None and hasattr(adapter, "search_cases_by_query") and \
        (adapter.status() if hasattr(adapter, "status") else AdapterStatus.READY) == AdapterStatus.READY
    seen: Dict[str, Dict[str, Any]] = {}
    warned = set()
    for verdict, citation in targets:
        review = verdict.setdefault("review", {})
        if review is None:
            review = verdict["review"] = {}
        if not ready:
            review["precedent_change"] = {"status": "NOT_ASSESSED", "reason": "SOURCE_UNAVAILABLE"}
            continue
        key = canonical_case_number(citation.canonical_case_number or citation.case_number or "")
        if key in seen:
            change = seen[key]
        elif len(seen) >= MAX_CITATIONS:
            review["precedent_change"] = {"status": "NOT_ASSESSED", "reason": "LOOKUP_BUDGET"}
            continue
        else:
            try:
                change = check_precedent_change(adapter, citation, verdict.get("official_record"))
            except Exception as exc:  # 조회 오류는 판정을 바꾸지 않는다
                change = {"status": "LOOKUP_FAILED", "reason": type(exc).__name__, "checked": 0}
            seen[key] = change
        review["precedent_change"] = change
        if change["status"] == "OVERRULED" and citation.citation_id not in warned:
            warned.add(citation.citation_id)
            finding = _finding(citation, change)
            summary["findings"].append(finding)
            verdict.setdefault("findings", []).append({
                "finding_id": finding.finding_id, "type": str(finding.type), "tags": list(finding.tags),
                "confidence_features": dict(finding.confidence_features)})
    summary.update(targets=len({c.citation_id for _, c in targets}), looked_up=len(seen),
                   status="SOURCE_UNAVAILABLE" if not ready else ("OVERRULED_FOUND" if summary["findings"] else "CHECKED"))
    return summary
