"""서면 간 엔티티 교차 일치성 검증기 (XDOC).

소장, 준비서면, 답변서 등 본안 서면의 주장과
첨부된 증거 서류(근로계약서, 판정서, 출퇴근기록부 등) 간의
날짜, 수치, 인적사항 엔티티를 교차 대조하여 불일치(XDOC)를 정밀 탐지한다.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.common.confidence import score as confidence_score
from packages.document_engine.reading_text import build_reading_text

ENGINE_NAME = "claim_engine.cross_document_entities"

# 날짜 패턴 (YYYY. M. D. 또는 YYYY-MM-DD 또는 YYYY년 M월 D일)
_DATE_PATTERNS = [
    re.compile(r"(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})(?:일)?"),
]

# 엔티티 키워드 패턴 목록 (양방향 일반 규칙)
ENTITY_PATTERNS: Dict[str, List[re.Pattern]] = {
    "입사일": [
        re.compile(r"(?:입사(?:일|한)?|채용(?:일|된)?|근로계약\s*체결일|근무\s*시작일|근무기간)[^.\n\d]{0,20}(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}(?:일|\.)?)"),
        re.compile(r"(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}(?:일|\.)?)[^\n]{0,30}?(?:입사|채용|근무를?\s*시작|근로계약\s*체결)"),
    ],
    "퇴사일": [
        re.compile(r"(?:퇴사(?:일|한)?|해고(?:일|된)?|근로관계\s*종료일)[^.\n\d]{0,20}(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}(?:일|\.)?)"),
        re.compile(r"(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}(?:일|\.)?)[^\n]{0,30}?(?:퇴사|해고|근로관계\s*(?:가\s*)?종료)"),
    ],
    "판정일": [
        # 판정 기관 이름은 지역명을 나열하지 않고 '…위원회'의 일반 형태로 본다(특정 기관명 리터럴 없음)
        re.compile(r"(?:[가-힣]{0,6}위원회|지노위|중노위)?\s*(?:재결|처분|판정|의결|결정)[^.\n\d]{0,20}(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}(?:일|\.)?)"),
        re.compile(r"(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}(?:일|\.)?)[^\n]{0,30}?(?:판정|재결|의결)"),
    ],
    "연장근로시간": [
        re.compile(r"(?:총\s*)?(?:연장|초과|휴일)\s*근로(?:시간)?\s*(?:합계|총|총합)?[^.\n\d]{0,10}(\d+)\s*(?:시간|H)"),
    ],
}


def _norm_date(date_str: str) -> Optional[str]:
    """날짜 문자열을 YYYY-MM-DD 형식으로 정규화한다."""
    if not date_str:
        return None
    for pat in _DATE_PATTERNS:
        m = pat.search(date_str)
        if m:
            y, mth, d = m.groups()
            try:
                return date(int(y), int(mth), int(d)).isoformat()
            except ValueError:
                return None
    return None


def _get_doc_text(doc: NormalizedDocument) -> str:
    """NormalizedDocument에서 텍스트를 안전하게 추출한다."""
    return build_reading_text(doc).text


def extract_document_entities(doc: NormalizedDocument) -> Dict[str, List[Dict[str, Any]]]:
    """문서 텍스트에서 주요 사실관계 엔티티를 추출한다."""
    entities: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    text = _get_doc_text(doc)
    filename = doc.filename or doc.document_id

    # 출퇴근기록부/근무시간 합계 특별 추출 (예: 30 + 28 + 30 = 88)
    time_sum_match = re.search(r"(\d+)\s*\+\s*(\d+)(?:\s*\+\s*(\d+))?\s*=\s*(\d+)", text)
    if time_sum_match and re.search(r"(?:연장|초과|휴일)\s*근로", text[max(0, time_sum_match.start() - 40):time_sum_match.end() + 20]):
        calc_total = int(time_sum_match.group(4) or time_sum_match.group(3) or time_sum_match.group(2))
        entities["연장근로시간"].append({
            "raw": f"{calc_total}시간 (산출합계)",
            "norm": calc_total,
            "span": (time_sum_match.start(), time_sum_match.end()),
            "context": time_sum_match.group(0),
            "document_id": doc.document_id,
            "filename": filename,
        })

    for key, pat_list in ENTITY_PATTERNS.items():
        for pat in pat_list:
            for match in pat.finditer(text):
                val_raw = match.group(1).strip()
                if "일" in key:
                    val_norm = _norm_date(val_raw)
                else:
                    # 덧셈식의 피연산자인 경우 건너뜀
                    after_match = text[match.end():match.end() + 10]
                    if "+" in after_match:
                        continue
                    try:
                        val_norm = int(val_raw)
                    except ValueError:
                        val_norm = val_raw

                if val_norm is not None:
                    # 중복 엔티티 방지 (동일 norm)
                    if any(e["norm"] == val_norm for e in entities[key]):
                        continue
                    start = max(0, match.start() - 40)
                    end = min(len(text), match.end() + 40)
                    entities[key].append({
                        "raw": val_raw,
                        "norm": val_norm,
                        "span": (match.start(), match.end()),
                        "context": text[start:end].replace("\n", " ").strip(),
                        "document_id": doc.document_id,
                        "filename": filename,
                    })

    return entities


# --- 당사자·사건 바인딩 -----------------------------------------------------------------------------
# 사실의 주체가 될 수 있는 당사자 지위. 복수형('원고들')·번호('원고 1')는 누구인지 특정되지 않으므로 바인딩하지 않는다.
PARTY_ROLE_RE = re.compile(
    r"(?P<role>피고인|피해자|피청구인|피신청인|청구인|신청인|채권자|채무자|근로자|사용자|고소인|참가인|원고|피고)"
    r"(?P<plural>들|\s*\d+\s*[.)]?|\s*등)?(?P<particle>께서|의|은|는|이|가|측|에게)?")
SUBJECT_PARTICLES = {"께서", "은", "는", "이", "가"}
# 당사자에 묶이는 사실(누구의 입사일인가). 판정일처럼 사건·기관에 묶이는 사실은 판정 기관까지 같아야 같은 사실이므로
# 승격하지 않고, 연장근로시간은 기간(어느 달·어느 기간)이 묶여야 하므로 승격하지 않는다.
PARTY_BOUND_KEYS = {"입사일", "퇴사일"}
_SENTENCE_END_RE = re.compile(r"(?:[다요음함임]\.|[!?。])(?=\s|$)|\n")


def _sentence_bounds(text: str, start: int, end: int) -> Tuple[int, int]:
    """start~end를 포함하는 문장의 범위. 날짜의 마침표('2021. 3. 4.')로 문장을 끊지 않도록 종결 어미 뒤 마침표만 본다."""
    left = 0
    for m in _SENTENCE_END_RE.finditer(text, 0, start):
        left = m.end()
    m = _SENTENCE_END_RE.search(text, end)
    return left, (m.end() if m else len(text))


def bind_subject(sentence: str, position: int) -> Optional[str]:
    """문장 안에서 position(사실 표기 위치)의 주체 당사자. 특정할 수 없으면 None.

    1) 사실 바로 앞(15자 안)의 소유격 '원고의 입사일' → 원고
    2) 주격·보조사로 표시된 당사자가 문장에 하나뿐이면 그 당사자('원고는 … 피고 회사에 입사')
    3) 문장에 나온 당사자가 하나뿐이고 '에게'로 표시되지 않았으면 그 당사자('원고 입사일: …')
    """
    mentions = [m for m in PARTY_ROLE_RE.finditer(sentence) if not m.group("plural")]
    before = [m for m in mentions if m.start() < position]
    possessive = [m for m in before if m.group("particle") == "의" and position - m.end() <= 15]
    if possessive:
        return possessive[-1].group("role")
    subjects = {m.group("role") for m in mentions if m.group("particle") in SUBJECT_PARTICLES}
    if len(subjects) == 1:
        return subjects.pop()
    roles = {m.group("role") for m in mentions if m.group("particle") != "에게"}
    if len(roles) == 1 and not subjects:
        return roles.pop()
    return None


def _annotate(doc: NormalizedDocument, entities: Dict[str, List[Dict[str, Any]]], facts: List[Dict[str, Any]]) -> None:
    """엔티티마다 주체 당사자(subject)와 양태(modality: 확정/예정/가정/상대방 주장)를 붙인다."""
    from .fact_store import PARTY_RE, modality

    text = _get_doc_text(doc)
    names: Dict[str, set] = defaultdict(set)
    plural = set()
    for fact in facts:
        if fact["document_id"] == doc.document_id and fact["attribute"] == "party_name":
            names[fact["key"]].add(fact["value"])
            if fact["plural_role"]:
                plural.add(fact["key"])
    for items in entities.values():
        for item in items:
            start, end = item["span"]
            left, right = _sentence_bounds(text, start, end)
            sentence = text[left:right]
            item["subject"] = bind_subject(sentence, start - left)
            role = item["subject"]
            # Reuse the fact store's explicit masked-name evidence; role alone is not identity.
            local_names = {m.group("name") for m in PARTY_RE.finditer(sentence) if m.group("role") == role}
            role_reference = any(m.group("role") == role and not m.group("plural")
                                 and m.group("particle") in SUBJECT_PARTICLES | {"의"}
                                 for m in PARTY_ROLE_RE.finditer(sentence))
            item["subject_identity"] = (next(iter(names[role]))
                                        if role not in plural and len(names[role]) == 1
                                        and (local_names == names[role] or (not local_names and role_reference)) else None)
            item["modality"] = modality(sentence, end - left)


def _xdoc_finding(key: str, by_doc: Dict[str, List[Dict[str, Any]]], *, bound: Optional[Dict[str, Any]] = None
                  ) -> Finding:
    """문서 간 차이 finding. bound가 있으면 같은 사건·같은 당사자의 확정 서술 모순(CONTRADICTED, B)."""
    details_list = []
    for items in by_doc.values():
        fn = items[0]["filename"]
        vals = ", ".join(f"'{it['raw']}'(맥락: {it['context'][:30]})" for it in items)
        details_list.append(f"[{fn}] {vals}")
    features: Dict[str, Any] = {
        "cross_document_inconsistency": True,
        "entity_type": key,
        "defect_code": "XDOC",
        "same_subject_confirmed": bool(bound),
        "documents": [items[0]["filename"] for items in by_doc.values()],
    }
    if bound:
        features.update(bound)
        grade, status = EvidenceGrade.B, VerificationStatus.CONTRADICTED
        title = f"문서 간 사실 모순(XDOC): {bound['subject']} {bound['subject_identity']}의 '{key}' 기재가 서로 다르다"
        detail = (f"같은 사건(사건번호 {', '.join(bound['shared_case_numbers'])})의 문서들이 같은 당사자"
                  f"({bound['subject']} {bound['subject_identity']})의 "
                  f"'{key}'를 서로 다르게 확정적으로 적었다: " + " vs ".join(details_list)
                  + ". 상대방 주장·가정적 서술·예정 사항은 비교에서 뺐다. 어느 쪽이 맞는지는 원본 증거로 확인해야 한다.")
    else:
        grade, status = EvidenceGrade.C, VerificationStatus.SUSPICIOUS
        title = f"문서 간 기재 차이 확인 필요(XDOC): '{key}' 상이"
        detail = (f"문서 간 '{key}' 기재가 상이합니다: " + " vs ".join(details_list)
                  + ". 같은 당사자·사건·기간의 사실인지는 확인되지 않았으므로 모순을 확정하지 않습니다.")
    evidence_items = [Evidence.create(description=f"{items[0]['filename']} 기재", grade=grade,
                                      document_id=items[0]["document_id"], excerpt=items[0]["context"][:300],
                                      supports=False) for items in by_doc.values()]
    return Finding.create(
        type=FindingType.CROSS_DOCUMENT_CONTRADICTION, status=status,
        severity=Severity.HIGH if bound else Severity.MEDIUM, evidence_grade=grade, advisory_only=not bound,
        title=title, detail=detail, confidence=confidence_score(features), confidence_features=features,
        document_id=next(iter(by_doc)), engine=ENGINE_NAME, tags=["FACT", "CROSS_DOCUMENT", "XDOC", key],
        evidence=evidence_items)


def _group_by_doc(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_doc: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_doc[item["document_id"]].append(item)
    return by_doc


def _differs(by_doc: Dict[str, List[Dict[str, Any]]]) -> bool:
    if len(by_doc) < 2:
        return False
    value_sets = [{item["norm"] for item in items} for items in by_doc.values()]
    return not all(values == value_sets[0] for values in value_sets[1:])


def verify_cross_document_entities(docs: List[NormalizedDocument]) -> List[Finding]:
    """사건 내 문서들 간의 엔티티 불일치(XDOC)를 검증한다.

    - 비교는 같은 사건 묶음(fact_store.case_groups: 자기 사건번호·당사자 이름) 안에서만 한다.
    - 상대방 주장·가정적 항변('설령 ~라 하더라도')·예정 사항에 든 값은 비교에서 뺀다(확정 서술만 비교).
    - 같은 사건번호를 공유하는 문서들이 같은 당사자의 당사자 귀속 사실(입사일·퇴사일)을 서로 다른 단일 값으로 확정
      서술하면 CONTRADICTED(B)로 올린다. 그 밖의 차이는 확인이 필요한 참고(C, advisory)로 둔다.
    """
    from .fact_store import CONFIRMED, build_fact_store, case_groups, own_case_numbers

    findings: List[Finding] = []
    if len(docs) < 2:
        return findings
    doc_entity_map: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    facts = build_fact_store(docs)
    for doc in docs:
        entities = extract_document_entities(doc)
        _annotate(doc, entities, facts)
        doc_entity_map[doc.document_id] = entities
    numbers = {doc.document_id: own_case_numbers(doc) for doc in docs}
    groups = case_groups(docs, facts)

    for group in groups:
        if len(group) < 2:
            continue
        for key in ENTITY_PATTERNS:
            items = [item for doc_id in group for item in doc_entity_map[doc_id].get(key, [])
                     if item.get("modality", CONFIRMED) == CONFIRMED]
            if not items:
                continue
            reported = False
            # 1) 같은 당사자에 묶인 확정 서술끼리
            if key in PARTY_BOUND_KEYS:
                for subject in sorted({i["subject"] for i in items if i.get("subject")}):
                    subject_items = [i for i in items if i.get("subject") == subject]
                    identities = {i.get("subject_identity") for i in subject_items}
                    subject_reported = False
                    # Compare each identified person separately before considering an unbound advisory.
                    for identity in sorted(i for i in identities if i is not None) + [None]:
                        if identity is None and (None not in identities or subject_reported):
                            continue
                        by_doc = _group_by_doc(subject_items if identity is None else
                                               [i for i in subject_items if i.get("subject_identity") == identity])
                        if not _differs(by_doc):
                            continue
                        shared = set.intersection(*(numbers[d] for d in by_doc))
                        single = all(len({i["norm"] for i in its}) == 1 for its in by_doc.values())
                        bound = ({"subject": subject, "subject_identity": identity,
                                  "shared_case_numbers": sorted(shared), "binding": "PARTY_IDENTITY_AND_CASE",
                                  "rule_id": "XDOC.PARTY_FACT_CONFLICT"}
                                 if shared and single and identity is not None else None)
                        findings.append(_xdoc_finding(key, by_doc, bound=bound))
                        reported = subject_reported = True
            if reported:
                continue
            # 2) 주체를 특정하지 못한 값이 있으면 참고(C)로만 알린다. 서로 다른 당사자의 값끼리는 비교하지 않는다.
            if not any(i.get("subject") is None for i in items):
                continue
            by_doc = _group_by_doc(items)
            if _differs(by_doc):
                findings.append(_xdoc_finding(key, by_doc))
    findings.extend(_verify_anchored(docs, groups))
    return findings


# --- TK-76 3주기 1항 PR2: 앵커가 있는 대상·속성의 문서 간 대조(설계 메모 3.1·M6·M7, 승인 조건 N1) ---------------------
# 같은 대상임을 문서 밖에서 확정하는 앵커가 있을 때만 비교한다. '위·해당·같은'은 각 문서 안의 앞말을 가리키므로 앵커가 아니다.
#   1) 유일 소송물 표지: '이 사건 [대상]'·'본건 [대상]'
#   2) 서증 번호: '갑 제N호증(의 M)'(괄호 안 문서명은 건너뜀)
# 속성 낱말은 닫힌 목록이 아니라 꼴로 정한다: 1~4자 + 날짜 접미(일·일자)·금액 접미(금액·대금)·수량 접미(수량·면적·인원).
_ANCHOR_RE = re.compile(
    r"(?:(?P<unique>이\s*사건|본건)\s*(?:(?P<target>[가-힣]{1,8}?)(?:의\s*|\s+))?|"
    r"(?P<party>갑|을|병)\s*(?:제\s*)?(?P<no>\d{1,3})\s*호\s*증(?:의\s*(?P<sub>\d{1,3}))?(?:\s*[(（][^)）]{1,20}[)）]|\s+[가-힣]{2,10}(?=의))?"
    r"(?:의\s*|\s+))(?:기재\s*)?(?P<attr>[가-힣]{1,4}?(?:일자|일|금)|[가-힣]{0,4}?(?:금액|대금|수량|면적|인원))"
    # 속성 끝 경계: 한글이 더 이어지면('입금'+'일') 더 긴 속성으로 되짚는다(평가 측 보완 S1)
    r"(?=\s|[은는이가을를의에도과와으로:：]|$)"
    r"\s*(?:은|는|이|가|을|를|:|：)?\s*(?:모두\s*|각\s*)?")
_ANCHOR_DATE_RE = re.compile(r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
# 단위 뒤의 조사·서술 어미(였다·입니다·임 등)는 단위가 아니다(#224 2판)
_ANCHOR_QTY_RE = re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>[가-힣㎡㎥]{1,4}?)(?=[은는이가을를의에과와도로였입임\s,.)]|$)")
# 같은 대상이라도 값이 정당하게 달라지는 문맥(메모 M7): 정정·예비적 주장·기준 시점·가정·청구 변경·상대방 주장.
# 상대방 주장은 '다투-'의 줄어든 꼴(다툰·다퉈·다툴)과 전달 인용('…라고 + 서술어')까지 본다(#224 2판).
_ANCHOR_GUARD_RE = re.compile(r"착오|오기|정정|바로잡|예비적|주위적|기준(?:으로|일|시점|일자)?|가정|설령|만약|변경|확장|감축|"
                              r"예정|연기|계획|주장|항변|다[투툰퉈툴]|(?:이)?라고\s+[가-힣]")
# 청구 금액·청구 관련 속성은 청구 확장·감축으로 정당하게 바뀐다(fact_store가 따로 다룬다). '…기일'(변론·선고 기일 등 절차 일정)은 바뀌는 것이 정상이다
_ANCHOR_SKIP_ATTR_RE = re.compile(r"청구")


def _anchored_items(doc: NormalizedDocument) -> List[Dict[str, Any]]:
    """앵커가 있는 (대상, 속성) 값 목록. 값을 읽지 못하거나 양태가 확정이 아니면 넣지 않는다."""
    from .calculation import parse_amounts
    from .fact_store import CONFIRMED, modality

    text = _get_doc_text(doc)
    out: List[Dict[str, Any]] = []
    for m in _ANCHOR_RE.finditer(text):
        # '…일자'와 '…일'은 같은 속성이다
        attr = m.group("attr")[:-1] if m.group("attr").endswith("일자") else m.group("attr")
        if attr in ENTITY_PATTERNS or _ANCHOR_SKIP_ATTR_RE.search(attr) or attr.endswith("기일"):
            continue
        if m.group("unique"):
            target = m.group("target") or ""
            anchor = ("UNIQUE", target)
            label = f"이 사건 {target}".rstrip()
        else:
            anchor = ("EXHIBIT", f"{m.group('party')}{m.group('no')}-{m.group('sub') or ''}")
            label = f"{m.group('party')} 제{m.group('no')}호증" + (f"의 {m.group('sub')}" if m.group("sub") else "")
        tail = text[m.end():m.end() + 30]
        if attr.endswith("일"):
            dm = _ANCHOR_DATE_RE.match(tail)
            if not dm:
                continue
            try:
                value = date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3))).isoformat()
            except ValueError:
                continue
            raw, kind, vend = dm.group(0), "DATE", dm.end()
        elif attr.endswith(("금액", "대금", "금")):
            # 값은 속성 바로 뒤의 금액만 읽는다('…금 중 300만 원'처럼 부분 금액은 읽지 않는다)
            amounts = [a for a in parse_amounts(tail) if a.start == 0 and a.raw.rstrip().endswith(("원", "원정"))]
            if not amounts:
                continue
            value, raw, kind, vend = str(amounts[0].value), amounts[0].raw, "AMOUNT", amounts[0].end
        else:
            qm = _ANCHOR_QTY_RE.match(tail)
            if not qm:
                continue
            value = (qm.group("num").replace(",", ""), qm.group("unit"))
            raw, kind, vend = qm.group(0), "QUANTITY", qm.end()
        left, right = _sentence_bounds(text, m.start(), m.end() + vend)
        sentence = text[left:right]
        if _ANCHOR_GUARD_RE.search(sentence) or modality(sentence, m.end() + vend - left) != CONFIRMED:
            continue
        out.append({"key": (anchor, attr), "label": label, "attr": attr, "kind": kind, "norm": value, "raw": raw.strip(),
                    "context": text[max(0, m.start() - 20):min(len(text), m.end() + vend + 20)].replace("\n", " ").strip(),
                    "document_id": doc.document_id, "filename": doc.filename or doc.document_id})
    return out


def _anchored_finding(label: str, attr: str, by_doc: Dict[str, List[Dict[str, Any]]]) -> Finding:
    """앵커가 있는 같은 대상·속성의 문서 간 값 차이(설계 메모 4.1: CROSS_DOCUMENT_CONTRADICTION·SUSPICIOUS·B·HIGH)."""
    details = " vs ".join(f"[{its[0]['filename']}] '{its[0]['raw']}'" for its in by_doc.values())
    features: Dict[str, Any] = {"cross_document_inconsistency": True, "entity_type": attr, "defect_code": "XDOC",
                                "rule_id": "XDOC.ANCHORED_ATTRIBUTE", "anchor": label,
                                "documents": [its[0]["filename"] for its in by_doc.values()]}
    evidence = [Evidence.create(description=f"{its[0]['filename']} 기재", grade=EvidenceGrade.B,
                                document_id=its[0]["document_id"], excerpt=its[0]["context"][:300], supports=False)
                for its in by_doc.values()]
    return Finding.create(
        type=FindingType.CROSS_DOCUMENT_CONTRADICTION, status=VerificationStatus.SUSPICIOUS, severity=Severity.HIGH,
        evidence_grade=EvidenceGrade.B, advisory_only=False,
        title=f"문서 간 기재 모순(XDOC): '{label}'의 '{attr}'가 문서마다 다르다",
        detail=(f"같은 사건 문서들이 '{label}'의 '{attr}'를 서로 다르게 적었다: {details}. "
                "정정·예비적 주장·기준 시점·가정·상대방 주장 문장은 비교에서 뺐다. 어느 쪽이 맞는지는 원본 증거로 확인해야 한다."),
        confidence=confidence_score(features), confidence_features=features, document_id=next(iter(by_doc)),
        engine=ENGINE_NAME, tags=["FACT", "CROSS_DOCUMENT", "XDOC", "ANCHORED", attr], evidence=evidence)


def _verify_anchored(docs: List[NormalizedDocument], groups: List[List[str]]) -> List[Finding]:
    """사건 묶음 안에서 앵커가 같은 (대상, 속성)을 문서마다 하나의 값으로 적었는데 값이 다르면 알린다."""
    by_id = {d.document_id: d for d in docs}
    findings: List[Finding] = []
    for group in groups:
        if len(group) < 2:
            continue
        items: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for doc_id in group:
            for item in _anchored_items(by_id[doc_id]):
                items[item["key"]].append(item)
        for key, its in items.items():
            by_doc = _group_by_doc(its)
            if len(by_doc) < 2:
                continue
            # 한 문서 안에서 값이 둘 이상이면 어느 값이 그 문서의 주장인지 알 수 없다 — 비교하지 않는다
            if any(len({i["norm"] for i in v}) != 1 for v in by_doc.values()):
                continue
            if its[0]["kind"] == "QUANTITY" and len({i["norm"][1] for i in its}) != 1:
                continue
            if _differs(by_doc):
                findings.append(_anchored_finding(its[0]["label"], its[0]["attr"], by_doc))
    return findings
