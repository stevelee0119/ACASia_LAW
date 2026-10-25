"""TK-129: 검토자가 화면 표에 반영한 외부 AI 답변을 보고서에 싣는다.

답변은 사용자가 붙여넣은 외부 AI(엘박스 등)의 의견이다. 공식 확인이 아니므로 판정·등급·점수에는
쓰지 않고, 보고서에는 별도 절로만 싣는다. 대상 문구는 브라우저가 보낸 값을 쓰지 않고 고정된
검증 결과의 표 항목(review_items)에서 다시 찾는다.
"""
from __future__ import annotations

from typing import Any, Dict, List

EXTERNAL_AI_TITLE = "외부 AI 참고 의견 (사용자 입력, 공식 확인 아님)"
EXTERNAL_AI_NOTICE = ("엘박스 등 외부 AI의 답변을 검토자가 표에 반영한 것입니다. 공식 DB 판정·등급·점수에는 쓰지 않았으며, "
                      "판례·법령 원문은 판결서·국가법령정보센터로 확인해야 합니다.")
EXTERNAL_AI_HEADERS = ["번호", "대상", "판정", "근거", "요지", "반영 시각"]


def _targets(engine: Dict[str, Any]) -> Dict[str, str]:
    """표 항목 id → 대상 문구. 화면이 만드는 참고문헌 행 id(`{문서}_REFERENCE_{claim_id}`)도 포함한다."""
    targets: Dict[str, str] = {}
    for doc in engine.get("documents", []) or []:
        doc_id = doc.get("id") or doc.get("document_id") or ""
        for item in doc.get("review_items", []) or []:
            if item.get("item_id"):
                targets[item["item_id"]] = str(item.get("cited_authority") or item.get("claim_text") or item["item_id"])
        for observation in ((doc.get("engine_data") or {}).get("rag") or {}).get("observations", []) or []:
            if observation.get("claim_id"):
                targets.setdefault(f"{doc_id}_REFERENCE_{observation['claim_id']}",
                                   str(observation.get("claim_quote") or observation["claim_id"]))
    return targets


def unknown_items(engine: Dict[str, Any], answers: List[Dict[str, Any]]) -> List[str]:
    targets = _targets(engine)
    return sorted({a["item_id"] for a in answers if a["item_id"] not in targets})


def checked_answers(engine: Dict[str, Any], answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """번호 순으로 정렬하고 대상 문구를 고정 결과에서 채운다. 같은 번호는 마지막 것만 남긴다."""
    targets = _targets(engine)
    by_code: Dict[str, Dict[str, Any]] = {}
    for answer in answers:
        if answer["item_id"] in targets:
            by_code[answer["code"]] = {**answer, "target": targets[answer["item_id"]][:500]}
    return [by_code[code] for code in sorted(by_code, key=lambda c: (c[0], int(c[1:])))]


def external_answer_rows(snapshot: Dict[str, Any]) -> List[List[str]]:
    return [[a.get("code", ""), a.get("target", ""), a.get("verdict", ""), a.get("basis", ""),
             a.get("summary", ""), a.get("applied_at", "")] for a in (snapshot or {}).get("external_ai_answers", []) or []]
