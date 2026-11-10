"""LV-06: 청구원인 요건사실 점검 및 실무 조치 안내 (Actionable Guidance).

1. 청구원인별(민법 750조 불법행위, 741조 부당이득, 390조 채무불이행, 544조 계약해제) 요건사실 주장 누락 점검
2. 확정오류 / 의심·출처한계 / 왜곡 3단계 실무 조치 가이드(석명신청 안, 인터넷 열람 링크, 변론 재구성 권고) 생성
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text

ENGINE_NAME = "legal_engine.actionable_guidance"

# ---------------------------------------------------------------------------
# 1. 청구원인 요건사실 정의 및 점검 규칙
# ---------------------------------------------------------------------------

CAUSE_OF_ACTION_RULES = [
    {
        "id": "TORT_750",
        "name": "불법행위 손해배상청구 (민법 제750조)",
        "trigger": re.compile(r"불법행위(?:로?\s*인한)?\s*손해배상|불법행위\s*(?:책임|성립)|민법\s*제?750조"),
        "elements": [
            ("가해행위/고의·과실", re.compile(r"가해행위|고의|과실|위법행위|부주의|의무\s*위반")),
            ("손해 발생", re.compile(r"손해(?:가|를|의)?\s*(?:발생|입|받|상당|액)")),
            ("인과관계", re.compile(r"인과관계|이로\s*인하|상당인과관계")),
        ],
    },
    {
        "id": "UNJUST_ENRICHMENT_741",
        "name": "부당이득반환청구 (민법 제741조)",
        "trigger": re.compile(r"부당이득\s*(?:반환|금)|민법\s*제?741조"),
        "elements": [
            ("법률상 원인 없음", re.compile(r"법률상\s*원인\s*(?:없이|없|결여|부존재)")),
            ("이익(수익)", re.compile(r"이익|수익|보유|취득|교부받")),
            ("손실/손해", re.compile(r"손실|손해")),
            ("인과관계", re.compile(r"인과관계|이로\s*인하|상당인과관계")),
        ],
    },
    {
        "id": "DEFAULT_390",
        "name": "채무불이행 손해배상청구 (민법 제390조)",
        "trigger": re.compile(r"채무불이행(?:으로?\s*인한)?\s*손해배상|채무불이행\s*(?:책임|성립)|민법\s*제?390조"),
        "elements": [
            ("채무불이행(이행지체·불능)", re.compile(r"채무불이행|이행지체|이행불능|불완전이행|이행하지\s*아니|지체하")),
            ("귀책사유", re.compile(r"귀책사유|고의|과실|책임\s*있는\s*사유")),
            ("손해 발생", re.compile(r"손해(?:가|를|의)?\s*(?:발생|입|받|상당)")),
            ("인과관계", re.compile(r"인과관계|이로\s*인하")),
        ],
    },
    {
        "id": "CONTRACT_RESCISSION_544",
        "name": "계약 해제 (민법 제544조 등)",
        "trigger": re.compile(r"계약(?:을)?\s*해제|계약해제|해제권|민법\s*제?544조"),
        "elements": [
            ("계약 체결", re.compile(r"계약(?:을)?\s*(?:체결|성립|약정)")),
            ("채무불이행(지체)", re.compile(r"채무불이행|이행지체|지체|이행하지\s*아니|불이행")),
            ("최고(독촉)", re.compile(r"최고|상당한\s*기간|촉구|독촉")),
            ("해제의사표시", re.compile(r"해제의\s*의사표시|해제한다|해제한다는\s*(?:통지|의사)|해제통고")),
        ],
    },
]


def check_cause_of_action_elements(doc: NormalizedDocument) -> List[Finding]:
    """서면 본문의 청구원인별 필수 요건사실 주장 누락을 점검한다."""
    text = build_reading_text(doc).text
    if not text:
        return []

    findings: List[Finding] = []
    for rule in CAUSE_OF_ACTION_RULES:
        matches = list(rule["trigger"].finditer(text))
        if not matches:
            continue

        active = False
        for m in matches:
            s0 = max(0, text.rfind("\n", 0, m.start()) + 1)
            s1 = text.find("\n", m.end())
            s1 = len(text) if s1 == -1 else s1
            sentence = text[s0:s1]
            if re.search(r"(?:청구|구|주장)(?:하지|하지는)?\s*(?:않|아니하|않는|않았)|배제한", sentence):
                continue
            if re.search(r"일반\s*조항|조항을?\s*둔다|조항에\s*불과|특약\s*조항", sentence):
                continue
            active = True
            break

        if not active:
            continue

        missing_elements: List[str] = []
        present_elements: List[str] = []
        for name, pattern in rule["elements"]:
            if pattern.search(text):
                present_elements.append(name)
            else:
                missing_elements.append(name)

        if missing_elements:
            features = {
                "deterministic_rule": True,
                "rule_id": f"CAUSE_OF_ACTION.{rule['id']}",
                "cause_id": rule["id"],
                "cause_name": rule["name"],
                "missing_elements": missing_elements,
                "present_elements": present_elements,
            }
            missing_str = ", ".join(missing_elements)
            findings.append(
                Finding.create(
                    type=FindingType.LEGAL_ARGUMENT_INVALID,
                    status=VerificationStatus.SUSPICIOUS,
                    severity=Severity.MEDIUM if len(missing_elements) >= 2 else Severity.LOW,
                    evidence_grade=EvidenceGrade.B,
                    title=f"청구원인 요건사실 주장 누락 점검({rule['name']}): [{missing_str}] 보완 필요",
                    detail=(
                        f"서면에서 '{rule['name']}'을 주장하고 있으나, 소송실무상 필수 요건사실 중 "
                        f"[{missing_str}]에 관한 구체적 주장이 명시되지 않았습니다. "
                        "변론기일 전 요건사실 주장 보강 및 입증자료 구비가 권고됩니다."
                    ),
                    confidence=0.75,
                    confidence_features=features,
                    document_id=doc.document_id,
                    engine=ENGINE_NAME,
                    tags=["LEGAL", "CAUSE_OF_ACTION", "ELEMENT_OMISSION"],
                    evidence=[
                        Evidence.create(
                            description="청구원인 주장 언급 구절",
                            grade=EvidenceGrade.B,
                            document_id=doc.document_id,
                            excerpt=text[max(0, rule["trigger"].search(text).start() - 50):rule["trigger"].search(text).end() + 100],
                        )
                    ],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# 2. 확정오류 / 의심·출처한계 / 왜곡 3단계 실무 조치 안내 생성
# ---------------------------------------------------------------------------

SCOURT_GLAW_URL = "https://glaw.scourt.go.kr"
SCOURT_RULING_SEARCH_URL = "https://www.scourt.go.kr/portal/information/finalruling/guide/index.html"


def generate_actionable_guidance(
    *,
    basis: str,
    cited_authority: str,
    claim_text: str = "",
    distortion_type: Optional[str] = None,
    grounded_evidence_quote: str = "",
    quote_diff_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """대조표 단일 행에 대해 확정오류/출처한계/왜곡 3단계 실무 조치(Actionable Guidance)를 생성한다."""
    diff_cats = quote_diff_categories or []

    # 1) 확정 부존재 (Tier 1: CONFIRMED_NONEXISTENT)
    if basis == "CONFIRMED_NONEXISTENT":
        return {
            "action_tier": "CONFIRMED_ERROR",
            "action_type": "CLARIFICATION_MOTION",
            "action_title": "판례 부존재 확인에 따른 석명 촉구 신청서(안)",
            "guidance_summary": (
                f"전수 수록 공인 DB에서 확인되지 않는 부존재 판례입니다({cited_authority}). "
                "상대방에게 판결문 사본 제출 또는 사건번호 정정을 요구하는 석명신청을 진행할 수 있습니다."
            ),
            "draft_motion_text": (
                f"[석명촉구신청서 안]\n"
                f"사건: [법원 사건번호]\n"
                f"신청인: [원고/피고]\n"
                f"피신청인: [상대방]\n\n"
                f"신청 취지:\n"
                f"상대방이 서면에서 원용한 판례({cited_authority})는 대한민국 법원 공식 판례 DB 및 종합법률정보에 "
                f"존재하지 않는 판례입니다.\n"
                f"이에 상대방에게 해당 판결문의 정본 또는 사본을 제출하거나, 정확한 사건번호 및 선고일자를 "
                f"석명하도록 촉구하여 주시기 바랍니다."
            ),
            "official_portal_url": SCOURT_GLAW_URL,
            "recommended_steps": [
                "1. 대법원 종합법률정보(glaw.scourt.go.kr)에서 사건번호 재확인",
                "2. 부존재 확인 시 재판부에 석명촉구신청서 제출",
                "3. 상대방의 출처 미제출 시 허위 주장으로 배척 요청",
            ],
        }

    # 2) 사건번호 형식 오기 의심 (FABRICATION_SUSPECTED / SUSPICIOUS)
    if basis in ("FABRICATION_SUSPECTED", "SUSPICIOUS"):
        return {
            "action_tier": "SOURCE_LIMIT_SUSPICIOUS",
            "action_type": "FORMAT_CORRECTION",
            "action_title": "성립 불가능한 사건번호 형식(오기 의심) 확인 안내",
            "guidance_summary": (
                f"사건번호({cited_authority})의 접수연도 또는 사건부호가 형식상 실재할 수 없어 오기(誤記)로 의심됩니다. "
                "정확한 사건번호를 확인하십시오."
            ),
            "draft_motion_text": (
                f"[사건번호 정정 요청 안]\n"
                f"원용된 {cited_authority}는 사건부호 또는 연도 체계상 오기(誤記)로 판단됩니다.\n"
                f"정확한 사건번호를 확인하여 주시기 바랍니다."
            ),
            "official_portal_url": SCOURT_GLAW_URL,
            "recommended_steps": [
                "1. 대법원 종합법률정보에서 유사 사건번호 검색",
                "2. 단순 오기인 경우 정확한 사건번호로 교체",
            ],
        }

    # 3) 출처 한계 및 미확인 (Tier 2: UNCONFIRMED, UNCONFIRMED_SOURCE_LIMIT)
    if basis in ("UNCONFIRMED", "UNCONFIRMED_SOURCE_LIMIT"):
        return {
            "action_tier": "SOURCE_LIMIT_SUSPICIOUS",
            "action_type": "SOURCE_VERIFICATION",
            "action_title": "공식 출처 확인 및 판결서 인터넷 열람 안내",
            "guidance_summary": (
                f"공식 공개 판례 DB 검색 결과 {cited_authority}의 기록을 확인하지 못했습니다. "
                "미공개 판결이거나 수록 범위 밖일 수 있으므로 공식 판결서 열람 또는 사본을 확인하십시오."
            ),
            "draft_motion_text": (
                f"[판결서 사본 제출 요구서 안]\n"
                f"상대방이 원용한 {cited_authority}는 공식 공개 판례 DB에서 확인되지 않는 판결입니다.\n"
                f"상대방은 해당 판결서의 사본을 제출하여 판결 취지 및 사실관계를 입증하여 주시기 바랍니다."
            ),
            "official_portal_url": SCOURT_RULING_SEARCH_URL,
            "recommended_steps": [
                "1. 법원 판결서 인터넷 열람 서비스(scourt.go.kr)에서 판결서 열람 신청",
                "2. 상대방에게 증거 설명서 또는 참고서면으로 판결서 사본 제출 요구",
                "3. 사본 확보 전까지 해당 판례를 전제로 한 법리 판단 유보",
            ],
        }

    # 3) 판시 왜곡 및 모순 (Tier 3: CONTRADICTION, CASE_HOLDING_DISTORTION)
    if basis == "CONTRADICTION" or distortion_type:
        title = (
            "변경된 종전 판례 인용에 따른 변론 재구성 권고" if distortion_type == "CHANGED_PRECEDENT"
            else "파기환송 원심 판단 오인에 따른 인용 정정 권고" if distortion_type == "REVERSED_REMAND_CONFUSION"
            else "반대의견 오인에 따른 다수의견 확인 및 변론 보완" if distortion_type == "MISATTRIBUTED_OPINION"
            else "판시 취지 왜곡에 따른 변론 재구성 권고"
        )
        return {
            "action_tier": "HOLDING_DISTORTION",
            "action_type": "HOLDING_CORRECTION",
            "action_title": title,
            "guidance_summary": (
                f"인용된 {cited_authority}의 판결 취지가 왜곡되었습니다. "
                + (f"공식 원문 근거: '{grounded_evidence_quote}'. " if grounded_evidence_quote else "")
                + "대법원 다수의견의 확립된 판시 법리에 맞추어 주장을 수정하거나 대체 선례를 원용하십시오."
            ),
            "draft_motion_text": None,
            "official_portal_url": SCOURT_GLAW_URL,
            "recommended_steps": [
                "1. 공식 원문의 판결요지 및 전문 직접 확인",
                "2. 왜곡되거나 변경된 판시를 전제로 한 주장을 철회하고 현행 대법원 판례로 교체",
                "3. 상대방의 왜곡 인용인 경우 준비서면에서 적극적으로 판시 왜곡 지적 및 반박",
            ],
        }

    # 4) 공식 DB 확인 완료 (Tier 4: OFFICIAL_CONFIRMED)
    if basis == "OFFICIAL_CONFIRMED":
        return {
            "action_tier": "OFFICIAL_CONFIRMED",
            "action_type": "APPLICATION_CHECK",
            "action_title": "사안의 사실관계 및 특약 조건 직접 검토 안내",
            "guidance_summary": (
                f"공식 판례 DB에서 {cited_authority}의 실재가 확인되었습니다. "
                "다만 본 사건의 구체적 계약 조항 및 사실관계에 유추적용될 수 있는지(사건 적용성) 직접 검토가 필요합니다."
            ),
            "draft_motion_text": None,
            "official_portal_url": SCOURT_GLAW_URL,
            "recommended_steps": [
                "1. 사안의 계약 조건 및 사실관계와 판례 사실관계 대조",
                "2. 특별한 항변 사유(신의칙, 특약 배제 등) 존재 여부 검토",
            ],
        }

    # 5) 사안 구별 (Tier 5: DISTINGUISHABLE)
    if basis == "DISTINGUISHABLE":
        return {
            "action_tier": "DISTINGUISHABLE",
            "action_type": "APPLICATION_CHECK",
            "action_title": "사안 구별 및 법리 적용 범위 직접 검토 안내",
            "guidance_summary": (
                f"원용된 {cited_authority}는 본 사건과 사실관계나 쟁점이 구별(distinguishable)될 가능성이 있습니다. "
                "해당 판례의 법리가 본 사건에 그대로 유추적용될 수 있는지 사실관계를 직접 대조하십시오."
            ),
            "draft_motion_text": None,
            "official_portal_url": SCOURT_GLAW_URL,
            "recommended_steps": [
                "1. 판례의 구체적 사실관계와 본건 사실관계의 차이점 분석",
                "2. 상대방 주장 법리의 적용 범위 한계 지적 준비",
            ],
        }

    # 6) 미검증 상태 및 미확인 상태값 (UNVERIFIED / 알 수 없는 상태, 중립적 확인 요청)
    if basis == "UNVERIFIED" or (basis not in ("CONTENT_MISMATCH", "MODIFIED_QUOTE") and not diff_cats):
        return {
            "action_tier": "SOURCE_LIMIT_SUSPICIOUS",
            "action_type": "SOURCE_VERIFICATION",
            "action_title": "공식 출처 및 판례 원문 확인 안내",
            "guidance_summary": (
                f"{cited_authority}에 대해 공식 출처 확인 및 원문 대조가 완료되지 않았습니다. "
                "공식 판례 DB 또는 판결문 사본을 통해 원문을 확인하십시오."
            ),
            "draft_motion_text": None,
            "official_portal_url": SCOURT_GLAW_URL,
            "recommended_steps": [
                "1. 공식 판례 DB(대법원 종합법률정보)에서 원문 검색",
                "2. 출처 미확인 시 상대방에게 사본 제출 또는 석명 요구",
            ],
        }

    # 7) 인용문 실질 차이 (Tier 7: CONTENT_MISMATCH / MODIFIED_QUOTE)
    return {
        "action_tier": "GENERAL",
        "action_type": "QUOTE_REVIEW",
        "action_title": "원문 대조 및 인용문 정정 안내",
        "guidance_summary": f"{cited_authority}의 인용문이 공식 원문과 차이가 있습니다. 원문과 대조하여 정확한 자구로 정정하십시오.",
        "draft_motion_text": None,
        "official_portal_url": SCOURT_GLAW_URL,
        "recommended_steps": [
            "1. 공식 원문과 인용문 어절 비교 확인",
            "2. 준비서면에서 정확한 판결요지 인용문으로 정정",
        ],
    }
