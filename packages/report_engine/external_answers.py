"""TK-129: 검토자가 화면 표에 반영한 외부 AI 답변을 보고서에 싣는다.

답변은 사용자가 붙여넣은 외부 AI(엘박스 등)의 의견이다. 공식 확인이 아니므로 판정·등급·점수에는
쓰지 않고, 보고서에는 별도 절로만 싣는다. 대상 문구는 브라우저가 보낸 값을 쓰지 않고 고정된
검증 결과의 표 항목(review_items 또는 레거시 fallback 행)에서 다시 찾는다.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

EXTERNAL_AI_TITLE = "외부 AI 참고 의견 (사용자 입력, 공식 확인 아님)"
EXTERNAL_AI_NOTICE = ("엘박스 등 외부 AI의 답변을 검토자가 표에 반영한 것입니다. 공식 DB 판정·등급·점수에는 쓰지 않았으며, "
                      "판례·법령 원문은 판결서·국가법령정보센터로 확인해야 합니다.")
EXTERNAL_AI_STATUS_LABEL = "공식 확인 아님 (참고 의견)"
EXTERNAL_AI_HEADERS = ["번호", "대상", "판정", "근거", "요지", "반영 시각", "공식 여부"]
# 열 너비는 머리글과 같은 개수여야 한다. 개수가 다르면 Word는 남는 열에 너비·테두리가 없고 PDF 표는 본문 폭을 넘는다.
EXTERNAL_AI_PDF_WIDTHS = [28, 100, 55, 125, 95, 47, 40]  # 합 490pt — A4 본문 폭(210mm − 좌우 18mm) 약 493pt 안
EXTERNAL_AI_DOCX_WIDTHS = [0.4, 1.3, 0.8, 1.6, 1.4, 0.8, 0.7]  # 합 7.0in — Letter 본문 폭(8.5in − 좌우 0.75in)
CODE_PATTERN = re.compile(r"^[AB]\d{1,4}$")


def _is_ai_security_finding(finding: Dict[str, Any]) -> bool:
    """AI 작성 진단 및 보안 소견은 검토 표의 일반 행으로 노출되지 않는다."""
    ftype = str(finding.get("finding_type") or finding.get("type") or "")
    return "AI_GENERATED" in ftype or "AI_SECURITY" in ftype or "AI_DIAGNOSIS" in ftype


def _targets(engine: Dict[str, Any]) -> Dict[str, str]:
    """표 항목 id → 대상 문구.

    브라우저 UI가 렌더링하는 행 ID 생성 규칙과 100% 일치하도록 구성한다:
    1. review_items가 있는 경우: CLAIM 행을 제외한 각 review_item의 item_id.
    2. review_items가 비어 있는 경우(하위 호환 fallback):
       - ai_hallucination_table: {docId}_CITATION_{citation_id || location}
       - citation_id가 있는 비-AI finding: {docId}_CITATION_{cid}
       - citation_id가 없는 비-AI finding: {docId}_FINDING_{fid}
    3. 주요 참고문헌 관찰(RAG observations):
       - claim_id가 있는 관찰: {docId}_REFERENCE_{claim_id}
       - claim_id가 없는 관찰: {docId}_REFERENCE_O{문서 안 관찰 순번}
    """
    targets: Dict[str, str] = {}
    docs = engine.get("documents", []) or []
    all_findings = engine.get("findings", []) or []
    if not all_findings and hasattr(engine, "all_findings"):
        all_findings = [f.to_dict() if hasattr(f, "to_dict") else dict(f) for f in engine.all_findings]

    has_any_review_items = any(bool(d.get("review_items")) for d in docs)

    for doc in docs:
        doc_id = str(doc.get("id") or doc.get("document_id") or "")
        items = doc.get("review_items", []) or []

        if items:
            for item in items:
                # 브라우저 UI와 동일: CLAIM 행은 표에 렌더링되지 않음
                if item.get("kind") == "CLAIM":
                    continue
                item_id = item.get("item_id")
                if item_id:
                    targets[item_id] = str(item.get("cited_authority") or item.get("claim_text") or item_id)
        elif not has_any_review_items:
            # 하위 호환 폴백: review_items가 없을 때 브라우저 렌더링 방식 반영
            doc_findings = doc.get("findings", []) or [f for f in all_findings if f.get("document_id") == doc_id]
            non_ai_findings = [f for f in doc_findings if not _is_ai_security_finding(f)]
            attached_fids = set()

            # 1) ai_hallucination_table
            for row in doc.get("ai_hallucination_table", []) or []:
                row_cid = row.get("citation_id") or row.get("location") or ""
                target_id = f"{doc_id}_CITATION_{row_cid}"
                targets[target_id] = str(row.get("cited_authority") or row.get("claim_text") or row_cid)
                for f in non_ai_findings:
                    fid = f.get("id") or f.get("finding_id")
                    if fid and (f.get("citation_id") == row.get("citation_id") or
                                (row.get("cited_authority") and row.get("cited_authority") in (f.get("title") or ""))):
                        attached_fids.add(fid)

            # 2) citation_id가 있는 나머지 finding 그룹
            remaining_citations: Dict[str, List[Dict[str, Any]]] = {}
            for f in non_ai_findings:
                fid = f.get("id") or f.get("finding_id")
                cid = f.get("citation_id")
                if fid in attached_fids or not cid:
                    continue
                remaining_citations.setdefault(cid, []).append(f)

            for cid, group in remaining_citations.items():
                lead = group[0]
                target_id = f"{doc_id}_CITATION_{cid}"
                targets[target_id] = str(lead.get("title") or lead.get("detail") or cid)
                for f in group:
                    attached_fids.add(f.get("id") or f.get("finding_id"))

            # 3) citation_id가 없는 나머지 비-AI finding
            for f in non_ai_findings:
                fid = f.get("id") or f.get("finding_id")
                if fid in attached_fids:
                    continue
                target_id = f"{doc_id}_FINDING_{fid}"
                targets[target_id] = str(f.get("detail") or f.get("title") or fid)

        # 4) 주요 참고문헌 관찰(RAG): claim_id 형태와 index 형태 모두 등록
        observations = ((doc.get("engine_data") or {}).get("rag") or {}).get("observations", []) or []
        for idx, obs in enumerate(observations):
            quote = str(obs.get("claim_quote") or obs.get("claim_id") or f"참고문헌 관찰 {idx + 1}")
            # 화면(referenceObservationRow)과 같은 규칙: claim_id가 없으면 문서 안 관찰 순번 `O{n}`.
            targets.setdefault(f"{doc_id}_REFERENCE_{obs.get('claim_id') or f'O{idx}'}", quote)

    return targets


def unknown_items(engine: Dict[str, Any], answers: List[Dict[str, Any]]) -> List[str]:
    """검증 결과 표에 존재하지 않는 item_id 목록을 반환한다."""
    targets = _targets(engine)
    return sorted({a["item_id"] for a in answers if a.get("item_id") not in targets})


def validate_answers(engine: Dict[str, Any], answers: List[Dict[str, Any]]) -> List[str]:
    """답변의 코드-항목 연결 무결성, 코드 형식, 중복 바인딩을 전수 검증한다."""
    errors: List[str] = []
    targets = _targets(engine)

    # 1) 미등록 대상 항목 검사
    unknown = sorted({a["item_id"] for a in answers if a.get("item_id") not in targets})
    if unknown:
        errors.append(f"이 검증 결과의 표에 없는 항목의 외부 AI 답변이 있습니다: {', '.join(unknown[:5])}")

    code_to_item: Dict[str, str] = {}
    item_to_code: Dict[str, str] = {}

    for answer in answers:
        code = str(answer.get("code") or "").strip().upper()
        item_id = str(answer.get("item_id") or "").strip()

        # 2) 코드 형식 검증 (A1, B1 등)
        if not CODE_PATTERN.match(code):
            errors.append(f"유효하지 않은 외부 AI 답변 코드 형식입니다: {code}")
            continue

        # 3) 동일 코드에 서로 다른 대상 item_id 바인딩 검증 (코드 충돌 방지)
        if code in code_to_item and code_to_item[code] != item_id:
            errors.append(f"코드 {code}가 다중 대상({code_to_item[code]}, {item_id})에 중복 매핑되었습니다.")
        code_to_item[code] = item_id

        # 4) 동일 item_id에 복수 코드 바인딩 검증
        if item_id in item_to_code and item_to_code[item_id] != code:
            errors.append(f"대상 {item_id}에 복수 코드({item_to_code[item_id]}, {code})가 중복 매핑되었습니다.")
        item_to_code[item_id] = code

    return errors


def checked_answers(engine: Dict[str, Any], answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """번호 순으로 정렬하고 대상 문구와 비공식성 메타데이터(official=False)를 채운다.

    동일 번호는 마지막 답변으로 유지하며, 기계 판독 가능한 공식 여부 필드를 포함한다.
    """
    targets = _targets(engine)
    by_code: Dict[str, Dict[str, Any]] = {}
    for answer in answers:
        item_id = answer.get("item_id")
        code = answer.get("code")
        if item_id and item_id in targets and code:
            by_code[code] = {
                **answer,
                "target": targets[item_id][:500],
                "official": False,
                "source": "external_ai",
                "notice": EXTERNAL_AI_NOTICE,
            }
    return [by_code[c] for c in sorted(by_code, key=lambda c: (c[0], int(c[1:])))]


def external_answer_rows(snapshot: Dict[str, Any]) -> List[List[str]]:
    """XLSX, PDF, Word 렌더링에 사용할 행 목록(비공식 여부 열 포함)."""
    rows: List[List[str]] = []
    for a in (snapshot or {}).get("external_ai_answers", []) or []:
        rows.append([
            str(a.get("code", "")),
            str(a.get("target", "")),
            str(a.get("verdict", "")),
            str(a.get("basis", "")),
            str(a.get("summary", "")),
            str(a.get("applied_at", "")),
            EXTERNAL_AI_STATUS_LABEL,
        ])
    return rows
