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


# 조 번호 토큰. 앞에 법령 표지(「법령명」·○○법(시행령)·같은 법(시행령)·이 법·같은 조)가 붙을 수 있다.
_ART_TOKEN_RE = re.compile(
    r"(?:(?P<named_law>「[^」]+」|[가-힣]+법(?:\s*시행령)?)|(?P<same_law>같은\s*법(?:\s*시행령)?|이\s*법)|(?P<same_art>같은\s*조))?"
    r"\s*제\s*(?P<art>\d+)조(?:의(?P<branch>\d+))?(?:\s*제\s*\d+항)?(?:\s*제\s*\d+호)?")
# 앞 조 번호와 이어진 나열('제13조 및 제15조', '제34조, 제35조', '제14조와 제15조', '제1조부터 제3조까지')
_ART_CHAIN_RE = re.compile(r"^\s*(?:,|ㆍ|·|및|또는|와|과|부터|내지)\s*$")
# 참조로 볼 서술(이 서술이 바로 뒤에 붙은 조 번호만 참조로 낸다)
_REF_TAIL_RE = re.compile(r"\s*(?:에\s*(?:따라|의하여|따른|의한|규정된)|(?:을|를)\s*준용하)")


class AuthorityBudget:
    """TK-137 및 TK-138이 공유하는 통합 시간 예산 관리 객체 (U4, P7).

    - 전체 문서 누계 시간 상한: 15.0초
    - TK-137 단계 상한: 8.0초 (소진 시 조기 중단)
    - TK-138 단계 상한: 잔여 예산 (최소 7.0초 확보)
    - TK-138 목록 검색 가드: 잔여 >= 5.0초
    - TK-138 본문 상세 조회 가드: 잔여 >= 3.0초
    """

    def __init__(self, total_seconds: float = 15.0, tk137_max_seconds: float = 8.0, start_time: Optional[float] = None):
        self.start_time = time.monotonic() if start_time is None else start_time
        self.total_seconds = total_seconds
        self.tk137_max_seconds = tk137_max_seconds
        self.tk137_finished = False

    def start_tk137(self) -> None:
        self.tk137_finished = False

    def finish_tk137(self) -> None:
        self.tk137_finished = True

    def tk137_can_call(self) -> bool:
        """TK-137에서 새 외부 호출을 시작할 수 있는지 검사한다 (단계 상한 8초 및 전체 15초, U4)."""
        if self.tk137_finished:
            return False
        now = time.monotonic()
        elapsed = now - self.start_time
        return (elapsed < self.tk137_max_seconds) and (elapsed < self.total_seconds)

    def total_remaining(self) -> float:
        """문서 단위 전체 잔여 시간을 반환한다."""
        elapsed = time.monotonic() - self.start_time
        return max(0.0, self.total_seconds - elapsed)

    def tk138_can_search(self, min_needed: float = 5.0) -> bool:
        """TK-138 목록 검색 전 잔여 예산을 검사한다 (P7 가드: >= 5.0초)."""
        return self.total_remaining() >= min_needed

    def tk138_can_fetch_detail(self, min_needed: float = 3.0) -> bool:
        """TK-138 본문 상세 조회 전 잔여 예산을 검사한다 (P7 가드: >= 3.0초)."""
        return self.total_remaining() >= min_needed


def article_label(article: Any) -> str:
    """조 번호를 법령 표기로 쓴다: '7' → '제7조', '7의2' → '제7조의2'(평가 측 보완 R2)."""
    main_num, sub_num = _norm_art_key(article)
    if not main_num:
        return f"제{article}조"
    return f"제{main_num}조의{sub_num}" if sub_num else f"제{main_num}조"


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

    # 조 번호를 순서대로 읽으며 법을 정한다. 나열로 이어진 번호는 앞 번호의 법을 이어받는다(평가 측 보완 R1:
    # '「고용보험법」 제13조 및 제15조에 따른'의 제15조는 고용보험법이다).
    # '같은 법'은 바로 앞에 이름이 나온 다른 법을 가리킨다('「산지관리법」 제14조 … 같은 법 제15조의2' → 산지관리법).
    # 앞에 이름이 나온 법이 없을 때만 인용한 법이다. '이 법'은 언제나 인용한 법이다(평가 측 보완 R5).
    prev_end, prev_law, prev_same_art = None, None, False
    last_named: Optional[str] = None
    tokens = []
    for m in _ART_TOKEN_RE.finditer(text):
        gd = m.groupdict()
        if gd.get("named_law"):
            law = re.sub(r"[「」]", "", gd["named_law"]).strip()
            last_named = re.sub(r"\s*시행령$", "", law)
            same_art = False
        elif gd.get("same_law"):
            marker = gd["same_law"]
            base = (last_named or source_law) if marker.startswith("같은") else source_law
            law = f"{base} 시행령" if "시행령" in marker else base
            same_art = False
        elif gd.get("same_art"):
            law, same_art = source_law, True
        elif prev_end is not None and _ART_CHAIN_RE.match(text[prev_end:m.start()]):
            law, same_art = prev_law, prev_same_art
        else:
            law, same_art = source_law, False
        tokens.append((m, law, same_art))
        prev_end, prev_law, prev_same_art = m.end(), law, same_art

    for m, law, same_art in tokens:
        if not _REF_TAIL_RE.match(text, m.end()):
            continue
        gd = m.groupdict()
        if same_art:
            # 4단계: '같은 조'는 동일 조문 내부 참조이므로 외부 탐색 대상에서 제외
            continue
        target_law = law

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


def _discover_tk137_authorities(citations, verifier, case_date: Optional[str] = None,
                                verdicts: Optional[List[Dict[str, Any]]] = None,
                                budget: Optional[AuthorityBudget] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """공식 확인된 법률 조문 인용으로부터 깊이 1 위임 및 명시 참조를 탐색한다 (TK-137)."""
    adapter = getattr(verifier.registry, "law", None) if hasattr(verifier, "registry") else None
    if adapter is None or getattr(adapter, "name", "") != "law_go_kr":
        return [], [], "ADAPTER_UNAVAILABLE"

    # N3: allow_network False 또는 OC 없음 시 탐색 생략
    if not getattr(adapter.settings, "allow_network", True) or adapter.status() != AdapterStatus.READY:
        return [], [], "NETWORK_DISABLED"

    # N3: 출처 장애·차단 상태이거나 예산 소진 시 조기 생략 (기존 파이프라인 복구 동작 보호)
    try:
        from packages.source_adapters.transport import _session, FAILURE_THRESHOLD
        session = _session.get()
        if session is not None:
            adapter_name = getattr(adapter, "name", "law_go_kr")
            if (session.failures.get(adapter_name, 0) >= FAILURE_THRESHOLD or
                    adapter_name in getattr(session, "blocked", {}) or
                    session.remaining() <= 0):
                return [], [], "SOURCE_OUTAGE"
    except Exception:
        pass

    if budget is None:
        budget = AuthorityBudget(total_seconds=15.0, tk137_max_seconds=8.0)
    budget.start_tk137()

    all_delegations: List[Dict[str, Any]] = []
    all_explicit_refs: List[Dict[str, Any]] = []
    thd_cmp_cache: Dict[str, Tuple[Optional[Dict[Tuple[int, int], Dict[str, Any]]], str]] = {}
    mst_cache: Dict[str, Optional[str]] = {}
    overall_status = "COMPLETED"

    # 앞선 source_review 검증 결과(verdicts)가 주어진 경우 확인된 인용만 선별하고 기존 MST 캐시 적재 (N3)
    verified_ids: Optional[Set[str]] = None
    official_by_cid: Dict[str, Tuple[str, str]] = {}
    if verdicts is not None:
        verified_ids = set()
        for v in verdicts:
            cid = v.get("citation_id")
            st = v.get("status")
            confirmed = v.get("identity_confirmed")
            if st == "VERIFIED" or confirmed:
                if cid:
                    verified_ids.add(cid)
                rec = v.get("official_record") or {}
                if rec.get("version_id") and rec.get("law_name"):
                    mst_cache[str(rec["law_name"]).strip()] = str(rec["version_id"])
                    if cid:
                        # 인용 ID → (공식 법령명, 판정이 고른 판의 MST). 약칭으로 인용해도 다시 조회하지 않는다(평가 측 보완 R4)
                        official_by_cid[cid] = (str(rec["law_name"]).strip(), str(rec["version_id"]))

    # STATUTE 인용 추출 (확인된 조문 한정)
    statute_cites = [
        c for c in citations
        if c.type == CitationType.STATUTE and c.law_name and c.article
        and (verified_ids is None or c.citation_id in verified_ids)
    ]

    for c in statute_cites:
        # N5: 문서당 전체 관련 근거 20건 상한
        if len(all_delegations) + len(all_explicit_refs) >= 20:
            overall_status = "LIMIT_EXCEEDED"
            break

        law_name = c.law_name.strip()
        if c.citation_id in official_by_cid:
            law_name, official_mst = official_by_cid[c.citation_id]
            mst_cache.setdefault(law_name, official_mst)
        art_key = _norm_art_key(c.article)
        art_str = str(c.article).strip()

        # 법령 MST 획득 (단일 법령 1회 조회 및 캐시)
        if law_name not in mst_cache:
            # U4, N1: 새 외부 호출 전 남은 시간 예산 확인 (TK-137 상한 8초)
            if not budget.tk137_can_call():
                overall_status = "LIMIT_EXCEEDED"
                continue
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
            if not budget.tk137_can_call():
                overall_status = "LIMIT_EXCEEDED"
                continue
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

    budget.finish_tk137()

    # 전체 상한 20건 절삭
    if len(all_delegations) + len(all_explicit_refs) > 20:
        overall_status = "LIMIT_EXCEEDED"
        max_del = min(len(all_delegations), 20)
        all_delegations = all_delegations[:max_del]
        rem = 20 - len(all_delegations)
        all_explicit_refs = all_explicit_refs[:rem]

    return all_delegations, all_explicit_refs, overall_status


def _calculate_authority_score(item: Dict[str, Any]) -> Tuple[float, str]:
    """판례 메타데이터로부터 권위 점수와 계층 티어를 결정론적으로 산정한다 (P1, P2, U2).

    - 전원합의체: 목록 응답의 판결유형 == "전원합의체 판결" (+50점 가산, SUPREME_COURT_EN_BANC)
    - 법원 계층: 대법원(100점) > 고등/특허(50점) > 지방/행정/가정/회생(20점) > 기타(10점)
    - 결정례: 판결유형 == "결정" (-10점)
    - 선고일자: 최신순 (YYYYMMDD 내림차순을 소수점으로 환산하여 tie-breaker 반영)
    """
    court = str(item.get("court") or "").strip()
    case_kind = str(item.get("case_kind") or "").strip()
    decision_date = str(item.get("decision_date") or "").strip().replace("-", "")

    # 법원 계층 기본 점수
    if "대법원" in court:
        base_score = 100.0
        tier = "SUPREME_COURT"
    elif any(k in court for k in ("고등법원", "특허법원")):
        base_score = 50.0
        tier = "HIGH_COURT"
    elif any(k in court for k in ("지방법원", "행정법원", "가정법원", "회생법원")):
        base_score = 20.0
        tier = "LOWER_COURT"
    else:
        base_score = 10.0
        tier = "OTHER_COURT"

    # 전원합의체 판결 판별 (U2: 선고 필드 확인 제외, 판결유형 필드만 확인)
    is_en_banc = case_kind == "전원합의체 판결"
    if is_en_banc and "대법원" in court:
        base_score += 50.0
        tier = "SUPREME_COURT_EN_BANC"
    elif is_en_banc:
        base_score += 50.0

    # 결정례 감산
    if case_kind == "결정":
        base_score -= 10.0

    # 선고일자 최신순 가산 (YYYYMMDD 형식 정수를 1e8로 나누어 소수로 반영)
    date_score = 0.0
    if decision_date.isdigit() and len(decision_date) == 8:
        date_score = int(decision_date) / 100_000_000.0

    total_score = round(base_score + date_score, 8)
    return total_score, tier


def _discover_tk138_precedents(
    citations,
    verifier,
    case_date: Optional[str] = None,
    verdicts: Optional[List[Dict[str, Any]]] = None,
    budget: Optional[AuthorityBudget] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """공식 확인된 인용 조문으로부터 관련 판례를 탐색하고 권위 가중치를 부여한다 (TK-138)."""
    adapter = getattr(verifier.registry, "law", None) if hasattr(verifier, "registry") else None
    if adapter is None or getattr(adapter, "name", "") != "law_go_kr":
        return [], "ADAPTER_UNAVAILABLE"

    # P5: allow_network False 또는 OC 없음 시 판례 탐색 생략 (오프라인 점수 변화 0)
    if not getattr(adapter.settings, "allow_network", True) or adapter.status() != AdapterStatus.READY:
        return [], "NETWORK_DISABLED"

    # 출처 장애·차단 상태이거나 예산 소진 시 조기 생략
    try:
        from packages.source_adapters.transport import _session, FAILURE_THRESHOLD
        session = _session.get()
        if session is not None:
            adapter_name = getattr(adapter, "name", "law_go_kr")
            if (session.failures.get(adapter_name, 0) >= FAILURE_THRESHOLD or
                    adapter_name in getattr(session, "blocked", {}) or
                    session.remaining() <= 0):
                return [], "SOURCE_OUTAGE"
    except Exception:
        pass

    if budget is None:
        budget = AuthorityBudget(total_seconds=15.0, tk137_max_seconds=8.0)

    # 확인된 조문 선별
    verified_ids: Optional[Set[str]] = None
    if verdicts is not None:
        verified_ids = {
            v.get("citation_id") for v in verdicts
            if v.get("citation_id") and (v.get("status") == "VERIFIED" or v.get("identity_confirmed"))
        }

    statute_cites = [
        c for c in citations
        if c.type == CitationType.STATUTE and c.law_name and c.article
        and (verified_ids is None or c.citation_id in verified_ids)
    ]

    if not statute_cites:
        return [], "NO_RESULTS"

    # P3: 공식 확인된 인용 조문 '법령명 제N조'로 질의 구성 (인용 빈도 상위 1~2개 조문)
    from collections import Counter
    query_counter: Counter[str] = Counter()
    for c in statute_cites:
        q = f"{canonical_law_name(c.law_name)} {article_label(c.article)}"
        query_counter[q] += 1

    top_queries = [q for q, _ in query_counter.most_common(2)]
    if not top_queries:
        return [], "NO_RESULTS"

    precedents_map: Dict[str, Dict[str, Any]] = {}
    precedent_status = "COMPLETED"
    detail_calls = 0  # 본문 상세 조회는 문서당 최대 3건(메모 2.5, 평가 측 보완 H7)

    for query in top_queries:
        # P7: 목록 검색 전 잔여 예산 확인 (>= 5.0초)
        if not budget.tk138_can_search(5.0):
            precedent_status = "BUDGET_EXHAUSTED"
            break

        # U1: 대법원 한정 org="400201", search=2, display=100 본문 검색
        try:
            resp = adapter.search_cases_by_query(query, org="400201", display=100, page=1)
            if resp.status != AdapterStatus.READY:
                if resp.status == AdapterStatus.RATE_LIMITED:
                    precedent_status = "RATE_LIMITED"
                    break
                continue
            records = getattr(resp, "records", []) or []
            src_rec = getattr(resp, "source_record", None)
            attrs = getattr(src_rec, "attributes", {}) or {}
            total_count = attrs.get("total_count", len(records))
            returned_count = attrs.get("returned_count", len(records))
        except Exception:
            continue

        if not records:
            continue

        # 100건 전체에 대해 권위 점수 산정 및 정렬 (P3: 선택 편향 제거)
        scored_records = []
        for r in records:
            score, tier = _calculate_authority_score(r)
            scored_records.append((score, tier, r))

        # 권위 총점 내림차순, 사건번호 내림차순 정렬
        scored_records.sort(key=lambda x: (x[0], str(x[2].get("case_number") or "")), reverse=True)

        # 상위 2~3건 선별 (최상위 3건)
        top_items = scored_records[:3]
        for score, tier, item in top_items:
            case_no = str(item.get("case_number") or "").strip()
            if not case_no or case_no in precedents_map:
                continue

            summary = str(item.get("summary") or "").strip()
            source_id = str(item.get("source_id") or "").strip()

            # P1: 목록 메타에 요지가 없고 source_id가 있으면 최상위 건에 한해 본문 상세 조회 시도
            if not summary and source_id and hasattr(adapter, "fetch_case"):
                if detail_calls < 3 and budget.tk138_can_fetch_detail(3.0):
                    detail_calls += 1
                    try:
                        detail_resp = adapter.fetch_case(item)
                        if detail_resp.status == AdapterStatus.READY and detail_resp.records:
                            detail_rec = detail_resp.records[0]
                            summary = str(detail_rec.get("summary") or detail_rec.get("holding") or "").strip()
                    except Exception:
                        pass  # 안전 폴백: 목록 메타 유지 (P1)

            scope_text = f"검색 {total_count}건 중 {returned_count}건 (대법원 한정)"
            precedents_map[case_no] = {
                "case_number": case_no,
                "court": str(item.get("court") or "").strip(),
                "decision_date": str(item.get("decision_date") or "").strip(),
                "case_name": str(item.get("case_name") or "").strip(),
                "case_kind": str(item.get("case_kind") or "").strip(),
                "authority_score": score,
                "authority_tier": tier,
                "summary": summary,
                "source_id": source_id,
                "detail_link": str(item.get("detail_link") or "").strip(),
                "search_query": query,
                "total_count": total_count,
                "returned_count": returned_count,
                "search_scope": scope_text,
            }

    sorted_precedents = sorted(precedents_map.values(), key=lambda x: x["authority_score"], reverse=True)
    if not sorted_precedents and precedent_status == "COMPLETED":
        precedent_status = "NO_RESULTS"

    return sorted_precedents, precedent_status


def review_related_authorities(doc, citations, verifier, *, case_date=None, quick=False, verdicts=None):
    """관련 법조문, 위임/명시 참조 근거, 관련 권위 판례를 검토하여 단일 dict로 반환한다 (N2, N3, P8)."""
    related = candidates(doc, citations)

    # N3: QUICK 프로필이거나 네트워크 불가 시 기존 동작 유지
    if quick:
        if not related:
            return None, []
        note = ("국가계약법 제15조 제3항의 지급지연 이자와 지체상금 상계는 납품대금 원금 상계와 구별한다. "
                "약정 효력·감액·귀책·상계 요건은 별도 판단이며 산술 검산만으로 적법성을 확정하지 않는다.")
        return {"origin": "DISCOVERED_AUTHORITY", "status": "NOT_ASSESSED", "note": note,
                "candidates": [c.to_dict() for c in related], "reason": "QUICK_PROFILE", "advisory_only": True}, []

    budget = AuthorityBudget(total_seconds=15.0, tk137_max_seconds=8.0)

    # TK-137 제한형 관련 근거 탐색 (깊이 1 위임 및 명시 참조)
    delegations: List[Dict[str, Any]] = []
    explicit_refs: List[Dict[str, Any]] = []
    delegation_status = "NOT_ASSESSED"

    try:
        delegations, explicit_refs, delegation_status = _discover_tk137_authorities(
            citations, verifier, case_date=case_date, verdicts=verdicts, budget=budget)
    except Exception:
        delegation_status = "ERROR"

    # TK-138 관련 판례 탐색 및 권위 가중치 산정 (TK-137 후속)
    precedents: List[Dict[str, Any]] = []
    precedent_status = "NOT_ASSESSED"

    try:
        precedents, precedent_status = _discover_tk138_precedents(
            citations, verifier, case_date=case_date, verdicts=verdicts, budget=budget)
    except Exception:
        precedent_status = "ERROR"

    # 국가계약법 쟁점도 없고 TK-137, TK-138 결과도 없는 경우 (N3 충족)
    if not related and not delegations and not explicit_refs and not precedents:
        return None, []

    records = []
    verdicts = []
    candidates_list = []
    note = "관련 법령 및 위임·명시 참조 조문, 관련 권위 판례 검토"

    if related:
        note = ("국가계약법 제15조 제3항의 지급지연 이자와 지체상금 상계는 납품대금 원금 상계와 구별한다. "
                "약정 효력·감액·귀책·상계 요건은 별도 판단이며 산술 검산만으로 적법성을 확정하지 않는다.")
        verified = verifier.verify_citations(related, case_date=case_date)
        records = verified.source_records
        verdicts = verified.data.get("verdicts", [])
        candidates_list = [c.to_dict() for c in related]

    # N2, P8: 기존 키·값 보존 + TK-137 / TK-138 확장 키 병합
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
        "precedent_status": precedent_status,
        "precedents": precedents,
    }
    return out, records


def report_lines(documents):
    """보고서 및 요약에 출력할 관련 근거 라인을 생성한다 (N6, P8, U1, U5)."""
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
            lines.append(f"[위임] {d['source_law']} {article_label(d['source_article'])} → {d['target_law']} "
                         f"{article_label(d['target_article'])}{title_part} / 검토 자료")
        for r in review.get("explicit_references", []):
            title_part = f"({r['target_title']})" if r.get("target_title") else ""
            lines.append(f"[참조] {r['source_law']} {article_label(r['source_article'])} → {r['target_law']} "
                         f"{article_label(r['target_article'])}{title_part} / 검토 자료")
        # TK-138: 관련 판례 라인 출력 (P8, U1, U5)
        precedents = review.get("precedents", []) or []
        if precedents:
            # 화면과 같은 구조: 질의별 검색 범위를 머리 줄에 한 번, 판례는 그 아래 줄마다(평가 측 보완 K1)
            scopes: List[str] = []
            for p in precedents:
                s = f"{p['search_query']}: {p['search_scope']}" if p.get("search_query") and p.get("search_scope") else (p.get("search_scope") or "")
                if s and s not in scopes:
                    scopes.append(s)
            scope_desc = f"{' · '.join(scopes)} — " if scopes else ""
            lines.append(f"[관련 판례] {scope_desc}권위 순 정렬 {len(precedents)}건 / 검토 자료")
            for p in precedents:
                kind_part = f", {p['case_kind']}" if p.get("case_kind") else ""
                name_part = f" \"{p['case_name']}\"" if p.get("case_name") else ""
                lines.append(f"  · {p['case_number']} ({p['court']}, {p['decision_date']}{kind_part}){name_part} "
                             f"(사건 당시 적용·주장 타당성은 별도 검토)")
    return lines
