"""Drive opinions in the citation table; separate from external AI answers."""
from packages.rag_engine.reference_binding import NOTICE, bind_observations, value

REPORT_NOTICE = ("본 참고문헌 대조 의견은 사설 Google Drive 자료를 기반으로 한 보조 검토 의견이며, "
                 "공식 판정·등급·점수 또는 공식 확인(OFFICIAL_CONFIRMED)이 아닙니다. " + NOTICE)


def reference_rows(document):
    items = [i.to_dict() if hasattr(i, "to_dict") else dict(i)
             for i in value(document, "review_items", [])]
    if not items and value(document, "citations", []):
        from packages.verification_engine.review_items import build_document_review_items
        items = [i.to_dict() for i in build_document_review_items(document)]
    unmatched = bind_observations(items, document)
    doc_id = value(document, "document_id", "")
    for observation in unmatched:
        items.append({"item_id": f"{doc_id}_REFERENCE_{observation.get('claim_id') or 'O' + str(observation['observation_index'])}",
                      "claim_text": observation.get("claim_quote", ""), "reference_status": "PENDING_REVIEW",
                      "reference_observations": [observation]})
    return [i for i in items if i.get("reference_observations")]


def basis_text(item):
    parts = ["[참고문헌 대조] " + NOTICE]
    for observation in item.get("reference_observations", []):
        source = observation.get("source_detail") or {}
        parts.append(f"{source.get('title') or observation.get('source_id', '')} · {observation.get('relationship', '')}")
        parts.append(observation.get("source_quote", ""))
        if observation.get("explanation"):
            parts.append(observation["explanation"])
    return "\n".join(parts)


def table_additions(document, existing_rows):
    """Add reference-only citations/standalone observations without duplicate rows."""
    existing_ids = {r.get("citation_id") for r in existing_rows if r.get("citation_id")}
    return [[value(document, "filename", ""), item.get("claim_text", ""), basis_text(item),
             "참고자료 지지 상태: " + item.get("reference_status", "PENDING_REVIEW")]
            for item in reference_rows(document) if not item.get("citation_id") or item["citation_id"] not in existing_ids]


def row_basis(document, row):
    return "\n".join(basis_text(item) for item in reference_rows(document)
                     if row.get("citation_id") and item.get("citation_id") == row["citation_id"])
