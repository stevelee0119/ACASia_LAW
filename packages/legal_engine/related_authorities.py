"""Explicitly separated discovery of bounded related authorities, never invented citations."""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from packages.common.enums import AdapterStatus, CitationType
from packages.common.schemas import Citation
from .normalize import canonical_law_name

NATIONAL_CONTRACT = "국가를 당사자로 하는 계약에 관한 법률"

# 명시 참조 패턴 (C5 5단계 판별: 명시 법령 > 같은 법/이 법 > 같은 법 시행령 > 같은 조 배제 > 인용 법령 기본값)
EXPLICIT_REF_RE = re.compile(
    r"(?:(?P<named_law>「[^」]+」|[가-힣]+법(?:\s*시행령)?)|(?P<same_law>같은\s*법(?:\s*시행령)?|이\s*법)|(?P<same_art>같은\s*조))?"
    r"\s*제\s*(?P<art>\d+)조(?:의(?P<branch>\d+))?(?:\s*제\s*(?P<para>\d+)항)?\s*"
    r"(?:에\s*(?:따라|의하여|따른|의한|규정된)|(?:을|를)\s*준용하)"
)


def _norm_art_key(art_str: Any) -> Tuple[int, int]:
    """조문 번호를 (본조번호, 가지번호) 정수로 정규화한다."""
    if art_str is None:
        return (0, 0)
    s = str(art_str).strip()
    m = re.match(r"^(\d+)(?:[의\-~](\d+))?", s)
    if not m:
        return (0, 0)
    main_num = int(m.group(1))
    sub_num = int(m.group(2)) if m.group(2) else 0
    return (main_num, sub_num)


def _fmt_art_str(main_num: int, sub_num: int) -> str:
    """정규화된 조문 키를 문자열 표기로 변환한다."""
    return f"{main_num}의{sub_num}" if sub_num else str(main_num)


def candidates(doc, citations):
    statutes = {(canonical_law_name(c.law_name or "").replace(" ", ""), c.article) for c in citations
                if c.type == CitationType.STATUTE}
    national = canonical_law_name(NATIONAL_CONTRACT).replace(" ", "")
    if not any(name == national for name, _ in statutes) or not re.search(r"지체상금", doc.visible_text):
        return []
    authorities = [(NATIONAL_CONTRACT, "26", "지체상금의 요건·귀책 및 면제 사유 검토"),
                   ("민법", "492", "납품대금 원금과의 상계 요건 별도 검토"),
                   ("민법", "493", "상계 의사표시 및 효력 별도 검토")]
    return [Citation.create(CitationType.STATUTE, f"{law} 제{article}조", document_id=doc.document_id,
                law_name=law, article=article, attributes={"origin": "DISCOVERED_AUTHORITY", "purpose": purpose})
            for law, article, purpose in authorities
            if (canonical_law_name(law).replace(" ", ""), article) not in statutes]


def _parse_thd_cmp(payload: Any) -> Tuple[Optional[Dict[Tuple[int, int], Dict[str, Any]]], str]:
    """3단 비교 JSON 응답을 조문별 매핑 딕셔너리로 파싱한다 (N4, N5)."""
    if not isinstance(payload, dict):
        return None, "INVALID_RESPONSE"
    if payload.get("_limit_exceeded"):
        return None, "LIMIT_EXCEEDED"

    # 최상위 서비스 컨테이너 탐색 (LspttnThdCmpLawXService 또는 ThdCmpLawXService)
    svc = payload.get("LspttnThdCmpLawXService") or payload.get("ThdCmpLawXService")
    if not isinstance(svc, dict):
        # 최상위 래핑이 없는 경우 직접 탐색
        svc = payload

    base_info = svc.get("기본정보") or {}
    if isinstance(base_info, dict) and base_info.get("삼단비교존재여부") == "N":
        return None, "THD_CMP_NOT_SUPPORTED"

    thd_body = svc.get("위임조문삼단비교") or svc.get("인용조문삼단비교") or {}
    if not isinstance(thd_body, dict):
        return {}, "COMPLETED"

    raw_articles = thd_body.get("법률조문") or []
    article_list = raw_articles if isinstance(raw_articles, list) else [raw_articles]

    result: Dict[Tuple[int, int], Dict[str, Any]] = {}

    decree_law = str(base_info.get("시행령명_한글") or "").strip()
    rule_law = str(base_info.get("시행규칙명_한글") or "").strip()

    for item in article_list:
        if not isinstance(item, dict):
            continue
        main_num = int(item.get("조번호") or 0)
        sub_num = int(item.get("조가지번호") or 0)
        if main_num == 0:
            continue
        key = (main_num, sub_num)

        t_title = str(item.get("조제목") or item.get("조문제목") or "").strip()
        t_content = str(item.get("조내용") or item.get("조문내용") or "").strip()

        if key not in result:
            result[key] = {
                "title": t_title,
                "content": t_content,
                "delegations": [],
                "_seen_targets": set(),
            }
        entry = result[key]
        if not entry["title"] and t_title:
            entry["title"] = t_title
        if not entry["content"] and t_content:
            entry["content"] = t_content

        # 시행령조문 및 시행규칙조문 수집 (단일 dict 또는 list of dict 정규화)
        for sub_key in ("시행령조문", "시행규칙조문"):
            sub_raw = item.get(sub_key)
            if not sub_raw:
                continue
            default_sub_law = decree_law if sub_key == "시행령조문" else rule_law
            subs = sub_raw if isinstance(sub_raw, list) else [sub_raw]
            for s in subs:
                if not isinstance(s, dict):
                    continue
                law_name = str(s.get("법령명") or default_sub_law or "").strip()
                t_main = int(s.get("조번호") or 0)
                t_sub = int(s.get("조가지번호") or 0)
                if not law_name or t_main == 0:
                    continue
                t_art_str = _fmt_art_str(t_main, t_sub)
                target_tuple = (law_name, t_art_str)
                # N5: 같은 조번호 병합 및 중복 제거
                if target_tuple in entry["_seen_targets"]:
                    continue
                entry["_seen_targets"].add(target_tuple)
                entry["delegations"].append({
                    "target_law": law_name,
                    "target_article": t_art_str,
                    "target_title": str(s.get("조제목") or s.get("조문제목") or "").strip(),
                    "target_excerpt": str(s.get("조내용") or s.get("조문내용") or "").strip(),
                })

    for v in result.values():
        v.pop("_seen_targets", None)

    return result, "COMPLETED"


def _extract_references(source_law: str, source_art: str, text: str,
                        law_articles: Dict[Tuple[int, int], Dict[str, Any]]) -> List[Dict[str, Any]]:
    """인용 조문 본문에서 명시 참조 조문을 5단계 규칙으로 추출한다 (C5)."""
    if not text:
        return []
    refs: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    src_key = _norm_art_key(source_art)

    for m in EXPLICIT_REF_RE.finditer(text):
        gd = m.groupdict()
        if gd.get("same_art"):
            # 4단계: '같은 조'는 동일 조문 내부 참조이므로 외부 탐색 대상에서 제외
            continue

        named = gd.get("named_law")
        same_law = gd.get("same_law")

        if named:
            # 1단계: 명시 법령
            target_law = re.sub(r"[「」]", "", named).strip()
        elif same_law:
            # 2, 3단계: '같은 법 시행령' 또는 '같은 법 / 이 법'
            if "시행령" in same_law:
                target_law = f"{source_law} 시행령"
            else:
                target_law = source_law
        else:
            # 5단계: 수식어가 없는 경우 인용 법령을 기본값으로 간주
            target_law = source_law

        main_num = int(gd["art"])
        sub_num = int(gd["branch"]) if gd.get("branch") else 0
        tgt_key = (main_num, sub_num)
        target_art_str = _fmt_art_str(main_num, sub_num)

        # 자기 자신 참조 제외
        if target_law == source_law and tgt_key == src_key:
            continue

        dedup_key = (target_law, target_art_str)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        target_title = ""
        target_excerpt = ""
        # 동일 법령인 경우 이미 수신한 3단 비교 법률조문에서 즉시 발췌
        if target_law == source_law and tgt_key in law_articles:
            matched = law_articles[tgt_key]
            target_title = matched.get("title", "")
            target_excerpt = matched.get("content", "")

        refs.append({
            "source_law": source_law,
            "source_article": source_art,
            "target_law": target_law,
            "target_article": target_art_str,
            "target_title": target_title,
            "target_excerpt": target_excerpt,
        })

    return refs


def _discover_tk137_authorities(citations, verifier, case_date: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """공식 확인된 법률 조문 인용으로부터 깊이 1 위임 및 명시 참조를 탐색한다 (TK-137)."""
    adapter = getattr(verifier.registry, "law", None) if hasattr(verifier, "registry") else None
    if adapter is None or getattr(adapter, "name", "") != "law_go_kr":
        return [], [], "ADAPTER_UNAVAILABLE"

    # N3: allow_network False 또는 OC 없음 시 탐색 생략
    if not getattr(adapter.settings, "allow_network", True) or adapter.status() != AdapterStatus.READY:
        return [], [], "NETWORK_DISABLED"

    start_time = time.monotonic()
    total_budget = 15.0  # 문서 누계 시간 상한 15.0초 (N1)

    all_delegations: List[Dict[str, Any]] = []
    all_explicit_refs: List[Dict[str, Any]] = []
    thd_cmp_cache: Dict[str, Tuple[Optional[Dict[Tuple[int, int], Dict[str, Any]]], str]] = {}
    mst_cache: Dict[str, Optional[str]] = {}
    overall_status = "COMPLETED"

    # STATUTE 인용 추출
    statute_cites = [c for c in citations if c.type == CitationType.STATUTE and c.law_name and c.article]

    for c in statute_cites:
        # N5: 문서당 전체 관련 근거 20건 상한
        if len(all_delegations) + len(all_explicit_refs) >= 20:
            overall_status = "LIMIT_EXCEEDED"
            break

        law_name = c.law_name.strip()
        art_key = _norm_art_key(c.article)
        art_str = str(c.article).strip()

        # 법령 MST 획득 (단일 법령 1회 조회 및 캐시)
        if law_name not in mst_cache:
            # N1: 새 외부 호출 전 남은 시간 예산 확인
            if time.monotonic() - start_time >= total_budget:
                overall_status = "LIMIT_EXCEEDED"
                break
            try:
                resolved = adapter.resolve_statute(law_name, as_of=case_date)
                records = getattr(resolved, "records", []) or []
                mst = records[0].get("version_id") if records else None
                mst_cache[law_name] = str(mst) if mst else None
            except Exception:
                mst_cache[law_name] = None

        mst = mst_cache.get(law_name)
        if not mst:
            continue

        # 3단 비교 조회 (동일 MST당 1회 단일 호출 및 캐시, C2)
        if mst not in thd_cmp_cache:
            if time.monotonic() - start_time >= total_budget:
                overall_status = "LIMIT_EXCEEDED"
                break
            try:
                payload = adapter.get_thd_cmp(mst, knd="2")
                parsed_articles, status_str = _parse_thd_cmp(payload)
                thd_cmp_cache[mst] = (parsed_articles, status_str)
            except Exception:
                thd_cmp_cache[mst] = (None, "ERROR")

        law_articles, st = thd_cmp_cache[mst]
        if st != "COMPLETED" and overall_status == "COMPLETED":
            overall_status = st

        if not law_articles:
            continue

        art_data = law_articles.get(art_key)
        if not art_data:
            continue

        # 1. 위임 조문 수집
        raw_delegations = art_data.get("delegations", [])
        delegations = [{
            "source_law": law_name,
            "source_article": art_str,
            "target_law": d["target_law"],
            "target_article": d["target_article"],
            "target_title": d["target_title"],
            "target_excerpt": d["target_excerpt"],
        } for d in raw_delegations]

        # 2. 본문 명시 참조 수집
        explicit_refs = _extract_references(law_name, art_str, art_data.get("content", ""), law_articles)

        # N5: 인용당 최대 3건 절삭 (위임 우선, 남은 자리에 명시 참조)
        allowed_del = delegations[:3]
        rem_slots = max(0, 3 - len(allowed_del))
        allowed_ref = explicit_refs[:rem_slots]

        all_delegations.extend(allowed_del)
        all_explicit_refs.extend(allowed_ref)

    # 전체 상한 20건 절삭
    if len(all_delegations) + len(all_explicit_refs) > 20:
        overall_status = "LIMIT_EXCEEDED"
        max_del = min(len(all_delegations), 20)
        all_delegations = all_delegations[:max_del]
        rem = 20 - len(all_delegations)
        all_explicit_refs = all_explicit_refs[:rem]

    return all_delegations, all_explicit_refs, overall_status


def review_related_authorities(doc, citations, verifier, *, case_date=None, quick=False):
    """관련 법조문 및 위임/명시 참조 근거를 검토하여 단일 dict로 반환한다 (N2, N3)."""
    related = candidates(doc, citations)

    # N3: QUICK 프로필이거나 네트워크 불가 시 기존 동작 유지
    if quick:
        if not related:
            return None, []
        note = ("국가계약법 제15조 제3항의 지급지연 이자와 지체상금 상계는 납품대금 원금 상계와 구별한다. "
                "약정 효력·감액·귀책·상계 요건은 별도 판단이며 산술 검산만으로 적법성을 확정하지 않는다.")
        return {"origin": "DISCOVERED_AUTHORITY", "status": "NOT_ASSESSED", "note": note,
                "candidates": [c.to_dict() for c in related], "reason": "QUICK_PROFILE", "advisory_only": True}, []

    # TK-137 제한형 관련 근거 탐색 (깊이 1 위임 및 명시 참조)
    delegations: List[Dict[str, Any]] = []
    explicit_refs: List[Dict[str, Any]] = []
    delegation_status = "NOT_ASSESSED"

    try:
        delegations, explicit_refs, delegation_status = _discover_tk137_authorities(
            citations, verifier, case_date=case_date)
    except Exception:
        delegation_status = "ERROR"

    # 국가계약법 쟁점도 없고 TK-137 결과도 없는 경우 (N3 충족)
    if not related and not delegations and not explicit_refs:
        return None, []

    records = []
    verdicts = []
    candidates_list = []
    note = "관련 법령 및 위임·명시 참조 조문 검토"

    if related:
        note = ("국가계약법 제15조 제3항의 지급지연 이자와 지체상금 상계는 납품대금 원금 상계와 구별한다. "
                "약정 효력·감액·귀책·상계 요건은 별도 판단이며 산술 검산만으로 적법성을 확정하지 않는다.")
        verified = verifier.verify_citations(related, case_date=case_date)
        records = verified.source_records
        verdicts = verified.data.get("verdicts", [])
        candidates_list = [c.to_dict() for c in related]

    # N2: 기존 키·값 보존 + TK-137 확장 키 병합
    out = {
        "origin": "DISCOVERED_AUTHORITY",
        "status": "SOURCE_REVIEW_ONLY",
        "note": note,
        "candidates": candidates_list,
        "verdicts": verdicts,
        "reference_date": case_date,
        "temporal_applicability": "REVIEW_REQUIRED",
        "advisory_only": True,
        "included_in_explicit_citation_count": False,
        "delegation_status": delegation_status,
        "delegations": delegations,
        "explicit_references": explicit_refs,
    }
    return out, records


def report_lines(documents):
    """보고서 및 요약에 출력할 관련 근거 라인을 생성한다 (N6)."""
    lines = []
    for doc in documents:
        review = doc.engine_data.get("related_authorities")
        if not review:
            continue
        lines.append(f"{doc.filename}: 추가 관련 법조문 검토 / {review['status']} (문서의 직접 인용과 별도)")
        lines.append(review.get("note") or review.get("reason", "추가 확인 필요"))
        for candidate in review.get("candidates", []):
            verdict = next((v for v in review.get("verdicts", [])
                            if v.get("citation_id") == candidate.get("citation_id")), {})
            lines.append(f"{candidate['raw_text']} / 출처 조회: {verdict.get('status', 'NOT_ASSESSED')} / "
                         "사건 당시 적용·주장 타당성: 별도 검토 필요")
        # N6: 위임 및 명시 참조 라인 출력
        for d in review.get("delegations", []):
            title_part = f"({d['target_title']})" if d.get("target_title") else ""
            lines.append(f"[위임] {d['source_law']} 제{d['source_article']}조 → {d['target_law']} 제{d['target_article']}조{title_part} / 검토 자료")
        for r in review.get("explicit_references", []):
            title_part = f"({r['target_title']})" if r.get("target_title") else ""
            lines.append(f"[참조] {r['source_law']} 제{r['source_article']}조 → {r['target_law']} 제{r['target_article']}조{title_part} / 검토 자료")
    return lines
