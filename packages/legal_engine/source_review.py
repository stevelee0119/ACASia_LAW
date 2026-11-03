"""Advisory source reviews without pipeline or persistence schema dependencies.

Call verify_citations(case_date=<one explicit issue date>, incident_date=...)
once per issue. Today's date never supplies the missing reference date.
Source records retain every list page/detail snapshot in EngineResult.
"""
from __future__ import annotations

import re

from packages.common.enums import CitationType, EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding
from packages.source_adapters.legal_history import legal_date, select_provision, today_korea

from .spec_mapping import relevance_review
from .verification_labels import provision_label


def date_context(as_of=None, incident_date=None, current_date=None):
    return {"reference_date": as_of, "incident_date": incident_date,
            "current_date": current_date if current_date is not None else today_korea(),
            "reference_basis": "EXPLICIT_REVIEW_DATE" if as_of else "MISSING",
            "advisory_only": True}


def _mismatch(verdict, title, detail, excerpt):
    citation = verdict.citation
    ids = [r.source_record_id for r in verdict.source_records]
    verdict.findings.append(Finding.create(
        type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.CONTRADICTED,
        severity=Severity.MEDIUM, evidence_grade=EvidenceGrade.A,
        title=title, detail=detail, document_id=citation.document_id,
        block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "SOURCE_TEXT"],
        evidence=[Evidence.create(description="조회한 공식 버전의 원문", grade=EvidenceGrade.A,
                                  excerpt=excerpt, source_record_ids=ids)],
    ))


def verify_statute_source(verifier, citation, *, as_of=None, incident_date=None, current_date=None):
    from .verifier import CitationVerdict

    verdict = CitationVerdict(citation, VerificationStatus.UNVERIFIED)
    verdict.review = {"dates": date_context(as_of, incident_date, current_date),
                      "advisory_only": True, "applicability": "REVIEW_NEEDED"}
    verdict.levels.update(temporal="UNVERIFIED", content="UNVERIFIED", applicability="REVIEW_NEEDED")
    if any(value is not None and not legal_date(value) for value in (as_of, incident_date, current_date)):
        verdict.notes.append("유효한 기준일이 필요하다. 누락·오류 날짜를 오늘로 대체하지 않는다")
        return verdict
    response = verifier.registry.law.resolve_statute(citation.law_name, as_of=as_of, current_date=current_date)
    verdict.source_records.extend(response.source_records)
    alias = (citation.attributes or {}).get("law_alias_candidate")
    if response.ok and (response.message or "").startswith("EXACT_LAW_NOT_FOUND:") and alias:
        # 적힌 이름이 목록에 없고, 같은 문서가 정식 법령명을 함께 쓴 경우: 정식명으로 다시 조회한다.
        retried = verifier.registry.law.resolve_statute(alias, as_of=as_of, current_date=current_date)
        verdict.source_records.extend(retried.source_records)
        verdict.review["law_alias"] = {"written": citation.law_name, "resolved": alias,
                                       "basis": citation.attributes.get("law_alias_basis"),
                                       "found": bool(retried.ok and not (retried.message or "").startswith(
                                           "EXACT_LAW_NOT_FOUND:"))}
        if verdict.review["law_alias"]["found"]:
            verdict.notes.append(f"'{citation.law_name}'은(는) 목록에 없어 문서의 정식 법령명 「{alias}」로 조회했다"
                                 "(약칭으로 판단한 근거는 문서 안의 표기다)")
            response = retried
        else:
            # An unresolved alias (including a failed detail parse) is not a nonexistent law.
            verdict.notes.append("법령 약칭 후보를 확인하지 못했다. 정식명칭·조회 상태를 확인해야 한다")
            verdict.findings.append(verifier._unverified_finding(citation, verdict.notes[-1], retried.source_record))
            return verdict
    inferred = None
    if response.ok and (response.message or "").startswith("EXACT_LAW_NOT_FOUND:") and not alias \
            and not _is_ordinance_form(citation.law_name):
        # 자치법규 꼴은 국가 법령 약칭으로 추정하지 않는다. 자치법규 목록에서 따로 찾는다(TK-134).
        inferred, retried = _infer_abbreviation(verifier, verdict, citation, as_of, current_date)
        if inferred is not None and retried is None:
            # 후보는 골랐으나 그 법령의 연혁·전문 조회를 마치지 못했다: 부존재가 아니라 미확인이다.
            verdict.findings.append(verifier._unverified_finding(citation, verdict.notes[-1], None))
            return verdict
        if inferred is not None:
            inferred["original"] = response
            response = retried
    if response.ok and (response.message or "").startswith("EXACT_LAW_NOT_FOUND:"):
        _law_absent(verdict, response, verifier=verifier)
        return verdict
    if not response.ok or not response.complete or len(response.records) != 1:
        verdict.notes.append(response.message or "완전한 시행법 연혁과 전문을 확보하지 못했다")
        verdict.findings.append(verifier._unverified_finding(citation, verdict.notes[-1], response.source_record))
        return verdict
    official = response.records[0]
    verdict.official_record = official
    verdict.levels.update(existence="VERIFIED", version="VERIFIED")
    if inferred is not None:
        # 약칭 추정으로 찾은 법령은 존재 '확인'이 아니다. 조문 대조는 하되 확인됨으로 올리지 않는다.
        verdict.levels["existence"] = "INFERRED_FROM_ABBREVIATION"
    verdict.review["version"] = {key: official.get(key) for key in (
        "law_id", "version_id", "effective_from", "effective_until", "promulgation_date",
        "date_basis", "history_complete", "current_version", "current_as_of")}
    verdict.review["supplementary_provisions"] = official.get("supplementary_provisions", [])
    verdict.review["transitional_review_needed"] = bool(official.get("transitional_review_needed"))
    verdict.review["supplementary_review_needed"] = not official.get("supplementary_complete")
    # Citation has no subitem field. Only recover an explicit locator from its
    # preserved raw_text, never from surrounding context.
    subitems = re.findall(r"([가-힣])\s*목", citation.raw_text)
    if len(subitems) > 1 or "부칙" in citation.raw_text:
        verdict.notes.append("부칙 직접 인용 또는 복수 목 지정은 자동 대응하지 않는다")
        return verdict
    provision = select_provision(official, citation.article or "", citation.paragraph,
                                 citation.item, subitems[0] if subitems else None)
    verdict.review["provision"] = provision
    verdict.levels["article"] = provision["status"]
    verdict.levels["provision"] = provision["status"]
    if provision["status"] == "NOT_FOUND":
        if inferred is not None:
            # 추정 법령에 인용 조문이 없으면 추정을 버리고 원래 판정(법령 목록 미발견)으로 돌아간다.
            verdict.review["law_alias"].update(found=False, outcome="ARTICLE_NOT_IN_CANDIDATE")
            verdict.notes.append("추정 후보 법령의 조회 버전에 인용 조문이 없어 추정을 버리고 원래 판정을 유지한다")
            verdict.official_record = None
            verdict.levels.update(existence="NOT_FOUND", version="UNVERIFIED")
            _law_absent(verdict, inferred["original"], verifier=verifier)
            return verdict
        _article_absent(verdict, official, provision, as_of)
        return verdict
    if inferred is not None:
        _abbreviation_inferred(verdict, inferred["candidate"], provision["status"])
    if provision["status"] != "VERIFIED":
        verdict.notes.append(provision.get("reason", "지정 조항호목의 전문을 확인하지 못했다"))
        return verdict
    _offense_name_check(verdict, official, provision)
    article_start = provision.get("article_effective_from")
    enforcement = official.get("enforcement_note") or ""
    supplement_text = "\n".join(s.get("text", "") for s in official.get("supplementary_provisions", []))
    partial = bool(enforcement.strip()) or bool(re.search(
        r"다만|일부\s+.*시행|각 호.*시행|대통령령으로 정하는 날|별도로 정하는 날",
        supplement_text))
    verdict.review["enforcement_review_needed"] = bool(
        partial or not article_start or (as_of and article_start > legal_date(as_of)))
    if as_of and article_start and article_start <= legal_date(as_of) and not partial:
        verdict.levels["temporal"] = "VERIFIED"
        verdict.notes.append(f"사건 특정 기준일({as_of}) 당시 시행 법령(시행일: {official.get('effective_from') or article_start}) 제{citation.article}조 특정 검토 완료")
    else:
        verdict.notes.append("기준일·조문 시행일 또는 부분 시행 조건 확인이 필요하다")
    if not official.get("supplementary_complete") or official.get("transitional_review_needed"):
        supplements = official.get("supplementary_provisions") or []
        trans_texts = [s.get("text", "").strip() for s in supplements if s.get("transitional")]
        if trans_texts:
            verdict.notes.append(f"부칙·경과조치의 사건 적용 여부는 검토자가 확인해야 한다 (부칙 내용: {trans_texts[0][:100]}...)")
        else:
            verdict.notes.append("부칙·경과조치의 사건 적용 여부는 검토자가 확인해야 한다")
        verdict.levels["temporal"] = "UNVERIFIED"
    verdict.levels["content"] = "AVAILABLE"
    verdict.status = VerificationStatus.PARTIALLY_VERIFIED
    if citation.quoted_text:
        level, ratio = verifier._compare_quote(citation.quoted_text, provision["text"])
        if level == "CONTRADICTED" and verdict.levels["temporal"] != "VERIFIED":
            level = "UNVERIFIED"
        verdict.levels["content"] = level
        verdict.review["quote_similarity"] = ratio
        if level == "CONTRADICTED":
            verdict.status = VerificationStatus.CONTRADICTED
            _mismatch(verdict, "지정 조항호목의 공식 원문과 인용문 불일치",
                      "조회한 시행 버전의 해당 조항호목에 대한 문언 대조 결과이다. 사건 적용 결론은 아니다.",
                      provision["text"])
        elif level != "VERIFIED":
            verdict.notes.append("직접 인용문은 해당 조항호목 원문 대조가 더 필요하다")
    else:
        _compare_asserted_content(verdict, provision)
    if (verdict.levels["content"] in ("VERIFIED", "NOT_ASSERTED") and verdict.levels["temporal"] == "VERIFIED"
            and verdict.status != VerificationStatus.CONTRADICTED):
        # 법령·조문 존재, 문서가 주장한 내용(또는 주장 없음), 기준일 시행 버전까지 확인했다.
        # 기준일이 없으면 본문 대조를 마쳐도 PARTIALLY_VERIFIED로 두고, 본문 대조 완료는
        # component_summary의 content_confirmed로 따로 센다.
        verdict.status = VerificationStatus.VERIFIED
    if inferred is not None and verdict.status == VerificationStatus.VERIFIED:
        verdict.status = VerificationStatus.PARTIALLY_VERIFIED
    # v3 D4: 기준일이 없으면 현행 버전 기준 일치로 확인 완료하고 기준일 확인은 권고로만 둔다.
    verdict.status, label, advisory = provision_label(verdict.levels, verdict.status, as_of)
    verdict.review["verification_label"] = label
    verdict.review["applicability"] = "APPLICABILITY_UNREVIEWED"
    if advisory:
        verdict.review.setdefault("advisories", []).append(advisory)
        verdict.levels["temporal_basis"] = "CURRENT_VERSION"
    verdict.notes.append("시행 버전·본문 대조는 사건에 대한 법률 적용 결론이 아니다")
    return verdict


GENERIC_OFFENSE_WORDS = {"위반", "처벌", "범죄", "본죄", "해당", "같은", "동조", "이법", "위법"}
OFFENSE_NAME_RE = re.compile(r"^\s*의\s*(?P<name>[가-힣·ㆍ]{1,12}?)(?:죄|범죄)")
ARTICLE_TITLE_RE = re.compile(r"^\s*제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\((?P<title>[^)\n]{1,60})\)")


def _offense_name_check(verdict, official, provision):
    """'제10조의 누설죄'처럼 서면이 조문에 붙인 죄명이 공식 조문 제목과 맞는지 본다.

    죄명의 핵심어(두 글자 이상)가 조문 제목에 하나도 없으면, 같은 법에서 그 핵심어가 제목에 든 조문을
    함께 적어 알린다. 죄명은 약칭으로 쓰는 일이 있어 CONTRADICTED가 아니라 SUSPICIOUS로 둔다.
    """
    citation = verdict.citation
    claim = (citation.attributes or {}).get("claim_text") or ""
    named = OFFENSE_NAME_RE.match(claim)
    if not named:
        return
    title = provision.get("article_title")
    if not title:
        found = ARTICLE_TITLE_RE.match(provision.get("text") or "")
        title = found.group("title") if found else None
    if not title:
        return
    compact_title = re.sub(r"\s+", "", title)
    # '위반죄'·'처벌규정 위반죄'처럼 조문 내용을 가리키지 않는 일반 죄명은 대조하지 않는다.
    stems = [s for s in re.split(r"[·ㆍ\s]", named.group("name")) if len(s) >= 2 and s not in GENERIC_OFFENSE_WORDS]
    if not stems or any(s in compact_title for s in stems):
        return
    others = [f"제{r['number']}조({r['title']})" for r in official.get("provisions") or []
              if r.get("title") and any(s in re.sub(r"\s+", "", r["title"]) for s in stems)][:4]
    compared = compared_label(citation)
    ids = [r.source_record_id for r in verdict.source_records]
    verdict.review["offense_name_check"] = {"claimed": named.group("name") + "죄", "article_title": title,
                                            "articles_with_term": others}
    verdict.findings.append(Finding.create(
        type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.SUSPICIOUS, severity=Severity.MEDIUM,
        evidence_grade=EvidenceGrade.A,
        title=f"조문 제목과 서면이 적은 죄명이 다르다: {compared} — 서면 '{named.group('name')}죄' / 조문 제목 '{title}'",
        detail=(f"조회한 시행 버전의 {compared} 제목은 '{title}'이다. 서면은 이 조문을 '{named.group('name')}죄'의 근거로 적었다. "
                + (f"같은 법에서 제목에 '{'·'.join(stems)}'이(가) 든 조문: {', '.join(others)}. " if others else "")
                + "조문 번호 오기이거나 다른 조문의 죄를 잘못 연결했을 수 있으므로 사람이 확인한다."),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "SOURCE_TEXT", "OFFENSE_NAME_MISMATCH"],
        confidence_features={"deterministic_rule": True, "rule_id": "LEGAL.OFFENSE_NAME_VS_ARTICLE_TITLE",
                             "claimed_offense": named.group("name"), "article_title": title,
                             "articles_with_term": others},
        evidence=[Evidence.create(description="조회한 공식 버전의 조문 제목·본문", grade=EvidenceGrade.A,
                                  excerpt=f"({title}) " + (provision.get("text") or "")[:300], source_record_ids=ids),
                  Evidence.create(description="문서의 주장", grade=EvidenceGrade.B, document_id=citation.document_id,
                                  block_id=citation.block_id, excerpt=claim[:200])],
    ))


def _compare_asserted_content(verdict, provision):
    """직접 인용문이 없을 때, 문서가 조문에 대해 풀어 쓴 주장(claim_text)을 조문 본문과 대조한다(v2 R5)."""
    from .provision_content import compare_claim_to_provision

    citation = verdict.citation
    claim = (citation.attributes or {}).get("claim_text")
    outcome = compare_claim_to_provision(
        claim, provision.get("text") or "",
        numbers_only=(citation.attributes or {}).get("claim_mode") == "PARENTHETICAL_BASIS",
        subject=(citation.attributes or {}).get("claim_subject"))
    verdict.review["content_comparison"] = {**outcome, "claim_text": claim}
    status = outcome["status"]
    verdict.levels["content"] = status
    if status != "CONTRADICTED":
        return
    verdict.status = VerificationStatus.CONTRADICTED
    exact_version = verdict.levels.get("temporal") == "VERIFIED"
    compared = compared_label(citation)
    ids = [r.source_record_id for r in verdict.source_records]

    # 1) 조문의 재량/의무 왜곡 (MODALITY)
    if outcome.get("basis") == "MODALITY":
        verdict.findings.append(_modality_finding(verdict, provision, claim, outcome.get("modality", {}), compared, ids,
                                                  exact_version))
        return

    # 2) 조문 준용 규정 및 적용 배제 주장 상충 (STATUTORY_APPLICATION_CONFLICT, STATUTORY_MISQUOTATION)
    if outcome.get("basis") in ("STATUTORY_APPLICATION_CONFLICT", "STATUTORY_MISQUOTATION"):
        verdict.findings.append(Finding.create(
            type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.CONTRADICTED,
            severity=Severity.HIGH, evidence_grade=EvidenceGrade.A if exact_version else EvidenceGrade.B,
            title=f"조문 취지·준용 규정과 상충되는 주장이다: {compared}",
            detail=(f"비교 대상 조문: {compared}. 문서의 주장: '{claim}'. "
                    f"사유: {outcome.get('reason', '')}. "
                    + ("" if exact_version else "기준일이 없어 현행(조회) 버전과 비교했다. 사건 당시 시행 버전이 다르면 "
                       "결론이 달라질 수 있으므로 시행 버전을 확인해야 한다.")),
            document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
            engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "SOURCE_TEXT", "STATUTORY_CONFLICT"],
            confidence_features={"claim_text": claim, "reason": outcome.get("reason"),
                                 "compared_version": (verdict.review.get("version") or {}).get("version_id")},
            evidence=[Evidence.create(description="조회한 공식 버전의 조문 본문", grade=EvidenceGrade.A,
                                      excerpt=(provision.get("text") or "")[:400], source_record_ids=ids),
                      Evidence.create(description="문서의 주장", grade=EvidenceGrade.B,
                                      document_id=citation.document_id, block_id=citation.block_id,
                                      excerpt=claim or "")],
        ))
        return

    # 3) 수치 불일치 (NUMERIC)
    mismatches = outcome.get("mismatches") or []
    pairs = "; ".join(f"문서 {m['claimed']} / 조문 {m['official']}" for m in mismatches) if mismatches else (outcome.get("reason") or "불일치")
    verdict.findings.append(Finding.create(
        type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.CONTRADICTED,
        severity=Severity.HIGH, evidence_grade=EvidenceGrade.A if exact_version else EvidenceGrade.B,
        title=f"조문 본문과 수치가 다르다: {compared} ({pairs})",
        detail=(f"비교 대상 조문: {compared}. 문서가 이 조문의 내용으로 적은 기간·비율이 조회한 시행 버전의 조문 본문과 다르다. "
                + ("" if exact_version else "기준일이 없어 현행(조회) 버전과 비교했다. 사건 당시 시행 버전이 다르면 "
                   "결론이 달라질 수 있으므로 시행 버전을 확인해야 한다.")),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "SOURCE_TEXT", "NUMERIC_MISMATCH"],
        confidence_features={"numeric_mismatches": mismatches, "claim_text": claim,
                             "compared_version": (verdict.review.get("version") or {}).get("version_id")},
        evidence=[Evidence.create(description="조회한 공식 버전의 조문 본문", grade=EvidenceGrade.A,
                                  excerpt=(provision.get("text") or "")[:400], source_record_ids=ids),
                  Evidence.create(description="문서의 주장", grade=EvidenceGrade.B,
                                  document_id=citation.document_id, block_id=citation.block_id,
                                  excerpt=claim or "")],
    ))


def _modality_finding(verdict, provision, claim, modality, compared, ids, exact_version):
    """조문의 재량('할 수 있다')을 의무로, 또는 의무('하여야 한다')를 재량으로 적은 주장(v4 P5)."""
    citation = verdict.citation
    kind = modality["kind"]
    heading = ("조문은 재량('할 수 있다')인데 의무로 주장했다" if kind == "DISCRETION_AS_MANDATE"
               else "조문은 의무('하여야 한다')인데 재량·의무 없음으로 주장했다")
    return Finding.create(
        type=FindingType.LEGAL_ARGUMENT_INVALID, status=VerificationStatus.CONTRADICTED, severity=Severity.HIGH,
        evidence_grade=EvidenceGrade.A if exact_version else EvidenceGrade.B,
        title=f"{heading}: {compared} — 문서 {modality['claimed']} / 조문 {modality['official']}",
        detail=(f"비교 대상 조문: {compared}. 문서는 '{modality['act']}'을(를) {modality['claimed']}로 적었으나 조회한 조문 본문은 "
                f"{modality['official']}로 정한다. 재량과 의무의 차이는 처분의 위법성 판단 등 결론을 바꿀 수 있다. "
                + ("" if exact_version else "기준일이 없어 조회(현행) 버전과 비교했다. ")
                + "사건에 대한 적용 결론은 내리지 않는다."),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "SOURCE_TEXT", "MODALITY"],
        confidence=0.85 if exact_version else 0.75,
        confidence_features={"deterministic_rule": True, "rule_id": f"CLAIM.{kind}", "modality": modality,
                             "claim_text": claim, "compared_version": (verdict.review.get("version") or {}).get("version_id")},
        evidence=[Evidence.create(description="조회한 공식 버전의 조문 본문", grade=EvidenceGrade.A,
                                  excerpt=(provision.get("text") or "")[:400], source_record_ids=ids),
                  Evidence.create(description="문서의 주장", grade=EvidenceGrade.B, document_id=citation.document_id,
                                  block_id=citation.block_id, excerpt=claim or "")],
    )


def _normalize_reference_name(name: str) -> str:
    """비교를 위한 규범·파일명 정규화 (접두 태그, 확장자, 괄호, 특수기호, 구분자, 공백 제거)."""
    name = (name or "").strip()
    # [RAG참고자료] 등 접두 태그 제거
    name = re.sub(r"^\[(?:RAG\s*)?참고자료\]\s*", "", name)
    # 파일 확장자(.pdf, .hwp, .hwpx, .docx, .txt 등) 제거
    name = re.sub(r"\.(?:pdf|hwpx?|docx?|txt)$", "", name, flags=re.IGNORECASE)
    # 낫표, 따옴표, 괄호, 특수기호, 언더스코어, 하이픈, 공백 제거
    return re.sub(r"[「」『』\[\]()\"'_\-\s]", "", name)


def _is_statute_form(law_name: str) -> bool:
    """법률·시행령 등 일반 법령 형태인지 판정 (법, 법률, 시행령, 시행규칙, 대통령령, 부령, 총리령, 조례)."""
    cleaned = re.sub(r"[「」『』\s]", "", law_name or "")
    statute_suffixes = ("법", "법률", "시행령", "대통령령", "시행규칙", "부령", "총리령", "조례")
    return any(cleaned.endswith(s) for s in statute_suffixes)


LOCAL_GOV_TOKEN_RE = re.compile(r"^[가-힣]+(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구)(?:교육청)?$")


def _is_ordinance_form(law_name: str) -> bool:
    """자치법규(조례, 지자체 이름으로 시작하는 규칙) 형태인지. 법령 목록(target=law)에는 없는 규범이다(TK-134)."""
    cleaned = re.sub(r"[「」『』]", "", law_name or "").strip()
    compact = cleaned.replace(" ", "")
    if compact.endswith("조례"):
        return True
    first = cleaned.split()[0] if cleaned.split() else ""
    return compact.endswith("규칙") and not compact.endswith("시행규칙") and bool(LOCAL_GOV_TOKEN_RE.match(first)) \
        and first != cleaned


def _is_internal_or_admin_rule(law_name: str) -> bool:
    """법률·대통령령 등 일반 법령이 아닌 내부 규정·행정규칙·지침 형태인지 판정."""
    cleaned = re.sub(r"[「」『』\s]", "", law_name or "")
    if not cleaned:
        return False
    # 일반 법령 접미사 (법, 법률, 시행령, 대통령령, 시행규칙, 부령, 총리령, 조례)
    statute_suffixes = ("법", "법률", "시행령", "대통령령", "시행규칙", "부령", "총리령", "조례")
    # 내부 규정 / 행정규칙 / 사규 접미사
    internal_suffixes = (
        "규정", "지침", "훈령", "예규", "고시", "공고", "기준",
        "특수조건", "일반조건", "사규", "정관", "요령", "세칙",
        "수칙", "준칙", "편람", "매뉴얼",
    )
    if any(cleaned.endswith(s) for s in internal_suffixes):
        return True
    if any(cleaned.endswith(s) for s in statute_suffixes):
        return False
    return False


def find_matching_read_reference(law_name: str, verifier) -> str | None:
    """본문을 읽은 사용자 참고자료(summary['sources'] 또는 direct refs) 중 정규화 제목이 완전히 일치하는 문서를 찾는다.

    1. 법령 형태 인용(법·법률·시행령 등)은 참고자료 대조로 CRITICAL을 낮추지 않는다(U1).
    2. 본문을 실제로 읽은 참고자료(summary['sources'])만 후보로 삼는다 (inventory 미독/실패 파일 제외).
    3. 정규화 제목이 동일(exact match)해야 하며 부분 문자열 일치는 허용하지 않는다.
    """
    if not law_name:
        return None
    # 법령 형태 인용은 참고자료 매칭으로 면책하지 않음
    if _is_statute_form(law_name):
        return None
    # 내부 규정·행정규칙 형태여야 함
    if not _is_internal_or_admin_rule(law_name):
        return None

    target_norm = _normalize_reference_name(law_name)
    if not target_norm:
        return None

    candidate_names: list[str] = []
    if verifier is not None:
        # 1) verifier에 직접 전달된 참고자료 목록 (단위 시험 및 명시 주입)
        direct_refs = getattr(verifier, "user_references", None) or getattr(verifier, "user_refs", None) or []
        if isinstance(direct_refs, list):
            for r in direct_refs:
                if isinstance(r, str):
                    candidate_names.append(r)
                elif isinstance(r, dict):
                    candidate_names.append(r.get("name") or r.get("filename") or r.get("title") or "")

        # 2) ReferenceLibrary의 summary['sources'] (본문 읽기 성공 파일, inventory 미독/실패 파일 제외)
        lib = getattr(verifier, "references", None) or getattr(verifier, "reference_library", None)
        if lib is not None:
            summary = getattr(lib, "summary", {}) or {}
            for item in summary.get("sources", []):
                if isinstance(item, dict):
                    name = item.get("name") or item.get("filename") or item.get("title")
                    if name:
                        candidate_names.append(name)

    for cand in candidate_names:
        cand_norm = _normalize_reference_name(cand)
        # 부분 일치가 아니라 정규화 후 완전 일치만 인정
        if cand_norm and cand_norm == target_norm:
            return cand
    return None


def _find_matching_user_reference(law_name: str, verifier, citation, verdict) -> str | None:
    """기존 호출 호환용 래퍼 (find_matching_read_reference 호출)."""
    return find_matching_read_reference(law_name, verifier)


def _law_absent(verdict, response, verifier=None):
    """법령 목록 조회는 성공했으나 같은 이름의 법령이 없다(NOT_FOUND_LAW).

    국가법령정보 법령 목록에서 찾지 못했다는 뜻이다.
    1) 본문을 읽은 사용자 참고자료(Drive)와 제목이 일치하는 내부 규정: '참고자료에서 확인'으로 처리하고 CRITICAL 미발행, INFO finding 생성.
    2) 내부 규정·행정규칙·지침 형태인 경우: 존재하지 않는 법령(CRITICAL)이 아니라 내부 규정 가능성(LOW)으로 알림.
    3) 일반 법령(법·법률 등) 형태인 경우: 기존대로 부존재 가능성 CRITICAL(증거 B) 유지.
    """
    import json

    citation = verdict.citation
    candidates = json.loads(response.message.split(":", 1)[1] or "[]")
    verdict.status = VerificationStatus.NOT_FOUND
    verdict.levels.update(existence="NOT_FOUND", article="NOT_FOUND", provision="NOT_FOUND")
    verdict.review["law_candidates"] = candidates
    ids = [r.source_record_id for r in verdict.source_records]

    # 1. 사용자 참고자료(Drive) 매칭 확인: 본문을 읽은 참고자료와 제목이 일치하는 내부 규정만 허용
    matched_ref = find_matching_read_reference(citation.law_name, verifier)
    if matched_ref:
        verdict.status = VerificationStatus.PARTIALLY_VERIFIED
        verdict.levels["existence"] = "FOUND_IN_USER_REFERENCES"
        verdict.review["user_reference_match"] = matched_ref
        verdict.notes.append(
            f"공식 법령 목록에는 없으나 읽은 사용자 참고자료(Drive) 「{matched_ref}」에서 확인되었다. "
            "공식 법령이 아닌 내부 규정이므로 해당 참고자료 원문과의 대조 대상으로 처리한다"
        )
        # 조용히 넘기지 않고 INFO로 참고자료 대조 대상 finding을 남긴다(TK-29 요구 4)
        verdict.findings.append(Finding.create(
            type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.PARTIALLY_VERIFIED,
            severity=Severity.INFO, evidence_grade=EvidenceGrade.B,
            title=f"사용자 참고자료 대조 대상 규범: {citation.law_name}",
            detail=f"공식 법령 목록에 없는 규범이나, 읽은 참고자료 「{matched_ref}」와 제목이 일치하여 참고자료 원문 대조 대상으로 분류함.",
            document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
            engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "USER_REFERENCE_MATCH"],
            confidence_features={"verdict_label": "FOUND_IN_USER_REFERENCES", "matched_reference": matched_ref,
                                 "law_name": citation.law_name},
            evidence=[Evidence.create(description="사용자 참고자료 일치", grade=EvidenceGrade.B,
                                      excerpt=matched_ref, source_record_ids=ids)],
        ))
        return

    # 2. 내부 규정 / 행정규칙 / 지침 등 비법령 규범 형태 확인: 심각도 LOW (HIGH 미만)
    if _is_internal_or_admin_rule(citation.law_name) or citation.type == CitationType.ADMIN_RULE:
        verdict.levels["existence"] = "NOT_FOUND_IN_STATUTE_LIST"
        verdict.notes.append(
            f"공식 법령 목록에서 「{citation.law_name}」을(를) 찾지 못했으나, 법령이 아닌 내부 규정·행정규칙·지침 형태이다. "
            "공식 법령 목록에 없는 것이 정상이거나 기관 내부 규범일 수 있으므로 사람이 원문을 확인해야 한다"
        )
        verdict.findings.append(Finding.create(
            type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.NOT_FOUND, severity=Severity.LOW,
            evidence_grade=EvidenceGrade.B,
            title=f"법령 목록에서 찾지 못한 규범(내부 규정·지침 가능): {citation.law_name}",
            detail=("국가법령정보 법령 목록에서 같은 이름의 법령을 찾지 못했다(조회 범위 내 미발견). "
                    + (f"비슷한 이름: {', '.join(candidates)}. " if candidates else "")
                    + "법령이 아닌 기관 내부 규정·행정규칙·지침일 수 있으므로 존재하지 않는 법령으로 단정하지 않는다. "
                    + "소관 기관 원문이나 첨부 자료를 확인해야 한다."),
            document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
            engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "ADMIN_RULE", "INTERNAL_REGULATION"],
            confidence_features={"verdict_label": "NOT_FOUND_IN_STATUTE_LIST", "absence_scope": "SEARCHED_SCOPE_ONLY",
                                 "law_candidates": candidates, "law_name": citation.law_name,
                                 "is_internal_or_admin_rule": True},
            evidence=[Evidence.create(description="법령 목록 조회 결과", grade=EvidenceGrade.B,
                                      excerpt=", ".join(candidates) or "(목록 없음)", source_record_ids=ids,
                                      supports=False)],
        ))
        return

    # 2-1. 자치법규(조례 등) 형태: 법령 목록이 아니라 자치법규 목록에서 다시 찾는다(TK-134)
    if _is_ordinance_form(citation.law_name):
        _ordinance_lookup(verdict, verifier, candidates)
        return

    # 2-2. 짧은 약칭 꼴(어간 3자 이하)인데 약칭 추정이 후보 여럿·목록 상한·조회 실패로 결론을 내지 못했으면 부존재로
    #      단정하지 않는다(TK-143). 공식 목록을 끝까지 읽고도 후보가 전혀 없으면(NO_CANDIDATE) 지금처럼 CRITICAL이다.
    if _abbreviation_like(citation.law_name) and (verdict.review.get("law_alias") or {}).get("outcome") in UNDECIDED_INFERENCE:
        verdict.status = VerificationStatus.UNVERIFIED
        verdict.levels.update(existence="UNVERIFIED", article="UNVERIFIED", provision="UNVERIFIED")
        alias = verdict.review.get("law_alias") or {}
        verdict.notes.append(f"'{citation.law_name}'은(는) 약칭으로 보이나 정식 법령을 확인 불가 — 부존재로 단정하지 않는다")
        verdict.findings.append(Finding.create(
            type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.UNVERIFIED, severity=Severity.MEDIUM,
            evidence_grade=EvidenceGrade.C,
            title=f"약칭으로 보이나 정식 법령을 확정하지 못함: {citation.law_name}",
            detail=("공식 법령 목록에 같은 이름이 없고, 약칭 추정으로도 정식 법령 하나를 고르지 못했다"
                    + (f"(후보: {', '.join(alias.get('candidates') or [])})" if alias.get("candidates") else "")
                    + ". 실무 줄임말일 수 있으므로 존재하지 않는 법령으로 단정하지 않는다. 정식 법령명을 서면에서 확인해야 한다."),
            document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
            engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "STATUTE", "ABBREVIATION_UNRESOLVED"],
            confidence_features={"verdict_label": "ABBREVIATION_UNRESOLVED", "law_name": citation.law_name,
                                 "inference_outcome": alias.get("outcome"), "law_candidates": candidates},
            evidence=[Evidence.create(description="법령 목록·약칭 추정 결과", grade=EvidenceGrade.C,
                                      excerpt=", ".join(alias.get("candidates") or candidates) or "(후보 없음)",
                                      source_record_ids=ids, supports=False)],
        ))
        return

    # 3. 일반 법령(법, 법률 등) 형태: 기존 CRITICAL 부존재 판정 유지 (대조군)
    verdict.findings.append(Finding.create(
        type=FindingType.STATUTE_NONEXISTENT, status=VerificationStatus.NOT_FOUND, severity=Severity.CRITICAL,
        evidence_grade=EvidenceGrade.B,
        title=f"법령 목록에서 찾지 못한 법령(NOT_FOUND_LAW): {citation.law_name}",
        detail=("국가법령정보 법령 목록에서 같은 이름의 법령을 찾지 못했다(조회 범위 내 미발견, 부존재 확정 아님). "
                + (f"비슷한 이름: {', '.join(candidates)}. " if candidates else "비슷한 이름의 법령도 없다. ")
                + "법령명 오기·약칭·폐지 여부를 원문으로 확인해야 한다."),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "STATUTE", "NOT_FOUND_LAW", "FAKE_REGULATION"],
        confidence_features={"verdict_label": "NOT_FOUND_LAW", "absence_scope": "SEARCHED_SCOPE_ONLY",
                             "law_candidates": candidates, "law_name": citation.law_name},
        evidence=[Evidence.create(description="법령 목록 조회 결과", grade=EvidenceGrade.B,
                                  excerpt=", ".join(candidates) or "(목록 없음)", source_record_ids=ids,
                                  supports=False)],
    ))


UNDECIDED_INFERENCE = ("AMBIGUOUS", "INCOMPLETE", "LOOKUP_FAILED")


def _abbreviation_like(law_name: str) -> bool:
    """어간(끝의 법·시행령·시행규칙을 뗀 몸통)이 2~3자이고 공백 없는 이름 — 실무 줄임말 꼴(TK-143)."""
    from .law_name_inference import compact, stem

    c = compact(law_name)
    return c.endswith(("법", "법시행령", "법시행규칙")) and 2 <= len(stem(c)) <= 3 and " " not in (law_name or "").strip()


def _ordinance_lookup(verdict, verifier, law_candidates):
    """조례 인용: 자치법규 목록 조회 결과로 판정한다. 조회하지 못하면 부존재로 단정하지 않는다."""
    citation = verdict.citation
    adapter = getattr(getattr(verifier, "registry", None), "law", None)
    search = getattr(adapter, "search_ordinance", None)
    response = search(citation.law_name) if callable(search) else None
    if response is not None:
        verdict.source_records.extend(response.source_records or [response.source_record])
    ids = [r.source_record_id for r in verdict.source_records if r is not None]
    verdict.review["ordinance_lookup"] = {
        "searched": bool(response is not None and response.ok),
        "matches": [{k: r.get(k) for k in ("ordinance_name", "local_government", "ordinance_kind",
                                           "effective_from", "match")} for r in (response.records if response else [])][:10]}
    if response is None or not response.ok:
        verdict.status = VerificationStatus.UNVERIFIED
        verdict.levels.update(existence="UNVERIFIED", article="UNVERIFIED", provision="UNVERIFIED")
        verdict.notes.append(f"「{citation.law_name}」은(는) 자치법규 형태라 법령 목록에 없는 것이 정상이다. "
                             "자치법규 목록 조회를 완료하지 못해 존재 여부를 확인하지 못했다")
        verdict.findings.append(verifier._unverified_finding(
            citation, verdict.notes[-1], response.source_record if response is not None else None))
        return
    records = response.records
    if records and all(r.get("match") == "exact" for r in records) and len(records) == 1:
        record = records[0]
        verdict.status = VerificationStatus.PARTIALLY_VERIFIED
        verdict.official_record = record
        verdict.levels.update(existence="VERIFIED", version="UNVERIFIED")  # 기존 판정 어휘를 쓴다(spec_mapping·components)
        verdict.review["ordinance_lookup"]["source"] = "ORDINANCE_LIST"
        verdict.notes.append(f"자치법규 목록에서 「{record.get('ordinance_name')}」({record.get('local_government') or '지자체 미상'}, "
                             f"시행 {record.get('effective_from') or '미상'})을 확인했다")
        if citation.article:
            articles = adapter.fetch_ordinance_articles(record) if hasattr(adapter, "fetch_ordinance_articles") else None
            wanted = re.sub(r"\s", "", str(citation.article))
            if articles is None:
                verdict.levels.update(article="UNVERIFIED", provision="UNVERIFIED")
                verdict.notes.append("자치법규 본문을 받지 못해 조문은 대조하지 않았다")
            elif wanted in articles:
                verdict.levels.update(article="VERIFIED", provision="UNVERIFIED")
                verdict.notes.append(f"제{citation.article}조가 현행 본문에 있다(조문 내용 대조는 하지 않았다)")
            else:
                verdict.status = VerificationStatus.NOT_FOUND
                verdict.levels.update(article="NOT_FOUND_IN_SELECTED_VERSION", provision="NOT_FOUND_IN_SELECTED_VERSION")
                verdict.findings.append(Finding.create(
                    type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.NOT_FOUND, severity=Severity.HIGH,
                    evidence_grade=EvidenceGrade.B,
                    title=f"자치법규 현행 본문에 없는 조문: {citation.law_name} 제{citation.article}조",
                    detail=(f"자치법규 목록에서 확인한 「{record.get('ordinance_name')}」의 현행 본문 조문 {len(articles)}개에 "
                            f"제{citation.article}조가 없다. 개정 전 조문이었는지는 확인하지 않았다."),
                    document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
                    engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "ORDINANCE", "ARTICLE_NOT_FOUND"],
                    confidence_features={"verdict_label": "ORDINANCE_ARTICLE_NOT_FOUND", "law_name": citation.law_name,
                                         "searched_articles": len(articles)},
                    evidence=[Evidence.create(description="자치법규 본문 조문 목록", grade=EvidenceGrade.B,
                                              excerpt=", ".join(articles[:30]), source_record_ids=ids, supports=False)]))
        else:
            verdict.levels.update(article="UNVERIFIED", provision="UNVERIFIED")
        return
    if records:
        # 이름 끝만 같은 자치법규가 여럿(지자체 미기재) 또는 같은 이름이 여럿: 존재는 하나 어느 것인지 사람이 고른다.
        verdict.status = VerificationStatus.PARTIALLY_VERIFIED
        verdict.levels.update(existence="PARTIALLY_VERIFIED", article="UNVERIFIED", provision="UNVERIFIED")
        verdict.review["ordinance_lookup"]["ambiguous"] = True
        names = sorted({f"{r.get('ordinance_name')}({r.get('local_government') or '미상'})" for r in records})
        verdict.notes.append(f"자치법규 목록에 이름이 맞는 규범이 {len(records)}건 있다: {', '.join(names[:5])}"
                             + (" 외" if len(names) > 5 else "") + ". 어느 지자체 것인지 서면에서 확인해야 한다")
        return
    verdict.notes.append(f"자치법규 목록에서도 「{citation.law_name}」을(를) 찾지 못했다(조회 범위 내 미발견)")
    verdict.findings.append(Finding.create(
        type=FindingType.STATUTE_NONEXISTENT, status=VerificationStatus.NOT_FOUND, severity=Severity.HIGH,
        evidence_grade=EvidenceGrade.B,
        title=f"자치법규 목록에서 찾지 못한 조례: {citation.law_name}",
        detail=("국가법령정보 자치법규 목록에서 같은 이름(지자체 이름을 뺀 이름 끝 일치 포함)의 자치법규를 찾지 못했다"
                "(조회 범위 내 미발견, 부존재 확정 아님). 지자체명·조례명 오기, 폐지 여부를 원문으로 확인해야 한다."),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "ORDINANCE", "NOT_FOUND_ORDINANCE"],
        confidence_features={"verdict_label": "NOT_FOUND_ORDINANCE", "absence_scope": "SEARCHED_SCOPE_ONLY",
                             "law_candidates": law_candidates, "law_name": citation.law_name},
        evidence=[Evidence.create(description="자치법규 목록 조회 결과", grade=EvidenceGrade.B,
                                  excerpt="(일치 없음)", source_record_ids=ids, supports=False)],
    ))


def _article_absent(verdict, official, provision, as_of):
    """조회한 시행 버전의 전체 조문에 인용 조문이 없을 때의 판정.

    법령 자체는 공식 기록으로 확인됐으므로 법령 부존재가 아니다. 조문 조회가 실패한
    것도 아니다. 확인한 범위(버전·시행일·조문 수)를 그대로 적고, 그 범위 밖(다른 시행
    버전·부칙·별표)에 있었을 가능성은 열어 둔다. 허위·위조로 단정하지 않는다.
    """
    citation = verdict.citation
    verdict.status = VerificationStatus.NOT_FOUND
    verdict.levels["article"] = "NOT_FOUND_IN_SELECTED_VERSION"
    verdict.levels["provision"] = "NOT_FOUND_IN_SELECTED_VERSION"
    version = official.get("version_id")
    effective = official.get("effective_from")
    scope = (f"{official.get('law_name') or citation.law_name} 시행 버전 {version or '미상'}"
             f"(시행 {effective or '미상'})의 전체 조문 {provision.get('searched_articles')}개")
    basis = "기준일 " + str(as_of) if as_of else "기준일이 없어 현행 버전"
    compared = compared_label(citation)
    verdict.notes.append(f"{scope}를 대조했으나 {compared}에 해당하는 제{citation.article}조가 없다({basis} 기준). "
                         "다른 시행 버전·부칙에 있었는지는 확인하지 않았다")
    ids = [r.source_record_id for r in verdict.source_records]
    verdict.findings.append(Finding.create(
        type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.NOT_FOUND,
        severity=Severity.HIGH, evidence_grade=EvidenceGrade.A,
        title=f"조회한 시행 버전의 전체 조문에서 해당 조문을 찾지 못함: {compared}",
        detail=(f"법령은 공식 기록으로 확인했다. {scope}를 모두 대조했으나 {compared}에 해당하는 제{citation.article}조는 없다. "
                f"({basis} 기준) 조문 번호 오기, 다른 시행 버전의 조문, 부칙 조항일 수 있으므로 "
                "허위 인용으로 단정하지 않는다."),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page,
        span=citation.span, engine="legal_engine", source_record_ids=ids,
        confidence_features={"official_source_match": True, "absence_scope": "SELECTED_VERSION_FULL_TEXT",
                             "searched_articles": provision.get("searched_articles"),
                             "version_id": version, "reference_date": as_of},
        tags=["LEGAL", "STATUTE", "ARTICLE"],
        evidence=[Evidence.create(description="조회한 공식 버전의 조문 목록에 해당 조문 없음",
                                  grade=EvidenceGrade.A, excerpt=citation.raw_text,
                                  source_record_ids=ids, supports=False)],
    ))


def verify_decision_source(verifier, citation):
    from .verifier import CitationVerdict

    verdict = CitationVerdict(citation, VerificationStatus.UNVERIFIED)
    verdict.review = {"advisory_only": True, "applicability": "REVIEW_NEEDED"}
    interpretation = citation.type == CitationType.INTERPRETATION
    if interpretation and citation.court not in (None, "", "법제처"):
        verdict.notes.append("중앙부처별 1차 해석은 별도 공식 API 대상이다. 법제처 해석례로 대체하지 않는다")
        return verdict
    search = getattr(verifier.registry.law, "search_interpretation" if interpretation else "search_admin_decision", None)
    fetch = getattr(verifier.registry.law, "fetch_interpretation" if interpretation else "fetch_admin_decision", None)
    if not citation.case_number or search is None or fetch is None:
        verdict.notes.append("자료 종류에 맞는 공식 어댑터와 정확한 안건·사건번호가 필요하다")
        return verdict
    response = search(citation.case_number)
    verdict.source_records.extend(response.source_records)
    if not response.ok or not response.complete:
        verdict.notes.append(response.message or "공식 목록 검색을 완료하지 못했다")
        return verdict
    target = re.sub(r"\s+", "", citation.case_number)
    matches = [r for r in response.records if r.get("case_number") == target]
    if len(matches) > 1 and citation.court:
        matches = [r for r in matches if r.get("court", "").replace(" ", "") == citation.court.replace(" ", "")]
    if len(matches) != 1 or not matches[0].get("source_id"):
        verdict.notes.append("같은 안건·사건번호의 공식 기록이 없거나 여러 기록이 중복된다")
        return verdict
    official = dict(matches[0])
    verdict.official_record = official
    verdict.levels["existence"] = "VERIFIED"
    detail = fetch(official)
    verdict.source_records.extend(detail.source_records)
    if not detail.ok or not detail.records:
        verdict.notes.append(detail.message or "공식 전문 확인 불가")
        return verdict
    official = {**official, **detail.records[0]}
    verdict.official_record = official
    metadata_missing = not official.get("decision_date") or not official.get("court")
    mismatches = verifier._compare_metadata(citation, official)
    verdict.levels["metadata"] = "CONTRADICTED" if mismatches else "UNVERIFIED" if metadata_missing else "VERIFIED"
    verdict.levels["full_text"] = "VERIFIED" if detail.complete else "UNVERIFIED"
    verdict.levels["applicability"] = "REVIEW_NEEDED"
    if not detail.complete or metadata_missing:
        verdict.notes.append("공식 전문 또는 결정 메타데이터가 불완전하다")
        return verdict
    verdict.status = VerificationStatus.PARTIALLY_VERIFIED
    if mismatches:
        verdict.status = VerificationStatus.CONTRADICTED
        description = "; ".join(f"{field}: 문서 {doc} / 공식 {off}" for field, doc, off in mismatches)
        verdict.notes.append(description)
        _mismatch(verdict, "해석례·재결례 메타데이터 불일치", description, official["full_text"])
    if citation.quoted_text:
        level, ratio = verifier._compare_quote(citation.quoted_text, official["full_text"])
        verdict.levels["quote"] = level
        verdict.review["quote_similarity"] = ratio
        if level == "CONTRADICTED":
            verdict.status = VerificationStatus.CONTRADICTED
            _mismatch(verdict, "해석례·재결례 공식 전문과 인용문 불일치",
                      "공식 전문 문언 대조이며 사건 적용 결론은 아니다.", official["full_text"])
    verdict.notes.append("해석례·재결례의 존재·전문 확인과 사건 적용 가능성 판단은 별도이다")
    return verdict


def case_applicability_review(citation, official, *, source_record_ids=(), extracted=None):
    """Anchor supplied structured excerpts; never invent facts or legal rules.

    extracted accepts facts/issues/rules/conditions/exceptions/conclusion and
    subsequent_treatment lists of {excerpt, ...}. Only exact official full-text
    excerpts survive. Persist this advisory object in existing result data.
    """
    fields = ("facts", "issues", "rules", "conditions", "exceptions", "conclusion", "subsequent_treatment")
    text = (official or {}).get("full_text") or ""
    result = {
        "citation_id": citation.citation_id, "case_number": citation.case_number,
        "citation_context": citation.context, "source_record_ids": list(source_record_ids),
        "status": "REVIEW_NEEDED", "advisory_only": True, "applies_to_case": None,
        "precedential_effect": "NOT_DETERMINED", "sections": {}, "rejected_excerpts": [],
    }
    for key in fields:
        accepted = []
        rows = (extracted or {}).get(key, [])
        rows = rows if isinstance(rows, list) else [rows]
        for row in rows:
            excerpt = row.get("excerpt") if isinstance(row, dict) else None
            if text and source_record_ids and isinstance(excerpt, str) and excerpt.strip() and excerpt in text:
                start = text.index(excerpt)
                accepted.append({"excerpt": excerpt, "span": [start, start + len(excerpt)]})
            else:
                result["rejected_excerpts"].append({"section": key, "reason": "No exact official full-text anchor"})
        result["sections"][key] = accepted
    result["missing_sections"] = [key for key in fields if not result["sections"][key]]
    result["full_text_available"] = bool(text)
    # 제4.2장 관련성. 측정하지 않았으면 0점이 아니라 미측정이며, 관련성 검증을
    # 마쳤다는 표시로 쓸 수 없다. 값은 검토자나 임베딩 단계가 채운다.
    result["relevance"] = relevance_review((extracted or {}).get("relevance_axes"))
    return result


def verify_admin_rule_source(verifier, citation):
    """행정규칙(훈령·예규·고시·지침) 인용 검증.

    존재·식별정보·조항·본문·위임 근거·법적 효력을 따로 판정한다. 행정규칙은 원칙적으로
    행정조직 내부에서만 효력을 가지며, 상위법령의 위임과 결합하는 등 예외적인 경우에만
    대외적 구속력이 논의된다. 문서가 "법률과 같은 효력"이라고 적었다는 사실만으로
    효력을 확인 처리하지 않는다. 공식 기록이 불완전하면 미확인으로 남긴다.
    """
    from .verifier import CitationVerdict

    attrs = citation.attributes or {}
    verdict = CitationVerdict(citation, VerificationStatus.UNVERIFIED)
    verdict.review = {"advisory_only": True, "applicability": "REVIEW_NEEDED",
                      "document_claims": {key: attrs.get(key) for key in (
                          "rule_name", "issuing_agency", "rule_kind", "rule_number", "effective_date",
                          "delegation_basis", "claimed_effect")}}
    verdict.levels.update(existence="UNVERIFIED", metadata="UNVERIFIED", content="UNVERIFIED",
                          delegation="NOT_STATED" if not attrs.get("delegation_basis") else "UNVERIFIED",
                          legal_effect="CLAIM_NOT_VERIFIED" if attrs.get("claimed_effect") else "REVIEW_NEEDED",
                          applicability="REVIEW_NEEDED")
    if citation.article:
        verdict.levels["article"] = "UNVERIFIED"
    if attrs.get("claimed_effect"):
        verdict.notes.append(
            f"문서는 이 행정규칙이 '{attrs['claimed_effect']}'을 가진다고 적었으나, 행정규칙의 대외적 "
            "구속력은 위임 근거·내용에 따라 사람이 판단할 사항이어서 자동으로 확인하지 않는다")
    name = citation.law_name or attrs.get("rule_name")
    search = getattr(verifier.registry.law, "search_admin_rule", None)
    fetch = getattr(verifier.registry.law, "fetch_admin_rule", None)
    if search is None or fetch is None:
        verdict.notes.append("행정규칙 공식 조회 경로가 지원되지 않아 확인하지 못했다")
        verdict.findings.append(verifier._unverified_finding(citation, verdict.notes[-1]))
        return verdict
    agency = attrs.get("issuing_agency")
    kind = attrs.get("rule_kind")
    number = attrs.get("rule_number")
    query = name or f"{agency or ''} {kind or ''}".strip() or citation.raw_text
    response = search(query)
    verdict.source_records.extend(response.source_records)
    if not response.ok or not response.complete:
        verdict.notes.append(response.message or "행정규칙 공식 목록 검색을 완료하지 못했다")
        verdict.findings.append(verifier._unverified_finding(citation, verdict.notes[-1], response.source_record))
        return verdict
    from packages.source_adapters.law_go_kr import _same_law_name

    if name:
        matched = [r for r in response.records if _same_law_name(name, r.get("rule_name"))]
    else:
        matched = [r for r in response.records if (not agency or agency in str(r.get("agency") or ""))
                   and (not kind or kind in str(r.get("rule_kind") or ""))]
    exact = [r for r in matched if not number or str(r.get("number") or "").replace(" ", "") == number]
    if not matched or (number and not exact):
        verdict.status = VerificationStatus.NOT_FOUND
        verdict.levels["existence"] = "NOT_FOUND"
        verdict.notes.append(f"공식 행정규칙 목록 {len(response.records)}건에서 일치하는 규칙을 찾지 못했다"
                             "(조회 범위 내 미발견). 폐지·명칭 변경·미수록일 수 있어 부존재로 단정하지 않는다")
        ids = [r.source_record_id for r in verdict.source_records]
        verdict.findings.append(Finding.create(
            type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.NOT_FOUND,
            severity=Severity.MEDIUM, evidence_grade=EvidenceGrade.B,
            title=f"조회 범위 내에서 찾지 못한 행정규칙 인용: {citation.raw_text}",
            detail=verdict.notes[-1], document_id=citation.document_id, block_id=citation.block_id,
            page=citation.page, span=citation.span, engine="legal_engine", source_record_ids=ids,
            confidence_features={"absence_scope": "SEARCHED_SCOPE_ONLY", "searched_records": len(response.records),
                                 "searched_query": query},
            tags=["LEGAL", "ADMIN_RULE"],
        ))
        return verdict
    if len(exact) != 1:
        verdict.notes.append("일치하는 행정규칙이 여러 건이거나 발령번호가 일치하는 기록이 없어 하나로 특정하지 못했다")
        verdict.review["candidates"] = [{k: r.get(k) for k in ("rule_name", "number", "agency", "effective_from")}
                                        for r in matched[:10]]
        return verdict
    official = dict(exact[0])
    verdict.official_record = official
    verdict.levels["existence"] = "VERIFIED"
    detail = fetch(official)
    verdict.source_records.extend(detail.source_records)
    if detail.ok and detail.records:
        official = {**official, **detail.records[0]}
        verdict.official_record = official
    mismatches = []
    for field_name, doc_value, off_value in (
            ("발령기관", attrs.get("issuing_agency"), official.get("agency")),
            ("규칙 종류", attrs.get("rule_kind"), official.get("rule_kind")),
            ("시행일", attrs.get("effective_date"), official.get("effective_from"))):
        if doc_value and off_value and str(doc_value).replace(" ", "") not in str(off_value).replace(" ", ""):
            mismatches.append((field_name, doc_value, off_value))
    identity_known = all(official.get(k) for k in ("agency", "rule_kind", "effective_from"))
    verdict.levels["metadata"] = "CONTRADICTED" if mismatches else ("VERIFIED" if identity_known else "UNVERIFIED")
    if mismatches:
        description = "; ".join(f"{f}: 문서 {d} / 공식 {o}" for f, d, o in mismatches)
        verdict.notes.append(description)
        _mismatch(verdict, "행정규칙 식별정보 불일치", description, str(official.get("full_text") or "")[:300])
    complete = bool(detail.ok and detail.complete and official.get("articles") is not None)
    if citation.article:
        if not complete:
            verdict.notes.append("행정규칙 전문을 확보하지 못해 조항 존재를 확인하지 못했다")
        else:
            from .normalize import canonical_article
            articles = {canonical_article(a) for a in official.get("articles") or []}
            if canonical_article(citation.article) in articles:
                verdict.levels["article"] = "VERIFIED"
                text = (official.get("article_texts") or {}).get(canonical_article(citation.article), "")
                verdict.levels["content"] = "AVAILABLE" if text else "UNVERIFIED"
                if citation.quoted_text and text:
                    level, ratio = verifier._compare_quote(citation.quoted_text, text)
                    verdict.levels["content"] = level
                    verdict.review["quote_similarity"] = ratio
            else:
                verdict.levels["article"] = "NOT_FOUND_IN_SELECTED_VERSION"
                verdict.notes.append(f"확보한 행정규칙 전문의 조항 {len(articles)}개에 제{citation.article}조가 없다"
                                     "(조회한 버전 기준, 다른 시점 버전은 확인하지 않음)")
    basis = attrs.get("delegation_basis")
    if basis and complete:
        compact = re.sub(r"\s+", "", str(official.get("full_text") or ""))
        law = re.sub(r"[「」『』\s]", "", basis.split("제")[0])
        verdict.levels["delegation"] = "MENTIONED_IN_OFFICIAL_TEXT" if law and law in compact else "UNVERIFIED"
        verdict.notes.append("위임 근거 법령의 해당 조문이 실제로 이 규칙에 위임했는지는 그 법령 조문을 따로 확인해야 한다")
    if mismatches:
        verdict.status = VerificationStatus.CONTRADICTED
    elif verdict.levels.get("article") in ("NOT_FOUND_IN_SELECTED_VERSION",):
        verdict.status = VerificationStatus.NOT_FOUND
    else:
        # 존재·조항이 확인돼도 법적 효력과 사건 적용은 사람 몫이다.
        verdict.status = VerificationStatus.PARTIALLY_VERIFIED
    verdict.notes.append("행정규칙의 존재·조항 확인은 법적 구속력이나 사건 적용 결론이 아니다")
    return verdict


def compared_label(citation) -> str:
    """판정 근거에 적을 비교 대상 조문 이름. 앞 인용을 가리킨 표현은 푼 이름과 원문 표기를 함께 적는다."""
    resolved = (citation.attributes or {}).get("resolved_label")
    if resolved:
        return f"{resolved}('{citation.raw_text}')"
    return citation.raw_text


INFERENCE_NOTES = {
    "NO_CANDIDATE": "공식 목록에 글자 순서가 맞는 법령 후보가 없다",
    "AMBIGUOUS": "글자 순서가 맞는 법령 후보가 여럿이고 점수 차이가 작아 추정을 보류했다",
    "LOOKUP_FAILED": "약칭 후보 목록 조회에 실패해 후보를 확인하지 못했다",
    "INCOMPLETE": "약칭 후보 목록이 탐색 상한을 넘어 추정을 보류했다",
}


def _infer_abbreviation(verifier, verdict, citation, as_of, current_date):
    """문서에 정식 법령명이 없을 때 공식 목록에서 약칭 후보를 골라 그 법령 ID로 다시 조회한다(TK-130).

    돌려주는 값: (None, None) 후보 없음·모호·후보 목록 조회 실패 — 호출 측은 기존 판정을 유지한다.
    (inferred, None) 후보는 골랐으나 상세 조회 실패·ID 불일치 — 호출 측은 미확인으로 남긴다.
    (inferred, response) 후보 법령의 시행 버전 응답.
    """
    infer = getattr(verifier.registry.law, "infer_law_by_abbreviation", None)
    if infer is None:
        return None, None
    guess = infer(citation.law_name)
    verdict.source_records.extend(guess.source_records or [])
    outcome = guess.message if guess.ok else "LOOKUP_FAILED"
    record = {"written": citation.law_name, "outcome": outcome, "found": False}
    verdict.review["law_alias"] = record
    if outcome != "FOUND":
        record["candidates"] = [c.get("law_name") for c in (guess.records or [])][:5]
        verdict.notes.append(f"'{citation.law_name}' 약칭 추정: {INFERENCE_NOTES.get(outcome, outcome)}")
        return None, None
    candidate = guess.records[0]
    record.update(resolved=candidate["law_name"], law_id=candidate["law_id"], basis=candidate["basis"],
                  score=candidate["score"], candidate_count=candidate.get("candidate_count", 1),
                  official_abbreviation=candidate.get("abbreviation"))
    retried = verifier.registry.law.resolve_statute(candidate["law_name"], as_of=as_of, current_date=current_date,
                                                    law_id=candidate["law_id"])
    verdict.source_records.extend(retried.source_records)
    official = retried.records[0] if retried.ok and retried.complete and len(retried.records) == 1 else None
    same_id = official is not None and str(official.get("law_id") or "").lstrip("0") == candidate["law_id"]
    if not same_id:
        record["outcome"] = "CANDIDATE_LOOKUP_FAILED"
        verdict.notes.append(
            f"'{citation.law_name}'의 약칭 후보 「{candidate['law_name']}」을(를) 골랐으나 그 법령의 시행 버전·전문 조회를 "
            "마치지 못했다(법령 ID 확인 포함). 부존재 근거로 보지 않는다")
        return {"candidate": candidate}, None
    record["found"] = True
    verdict.notes.append(
        f"'{citation.law_name}'은(는) 공식 법령 목록에 같은 이름이 없어, 조회한 후보 중 우선 후보 「{candidate['law_name']}」"
        f"(법령 ID {candidate['law_id']})로 추정해 조문을 대조했다(추정, 정식명 확인 필요)")
    return {"candidate": candidate}, retried


PROVISION_PHRASES = {
    "VERIFIED": "인용 조문이 그 법령의 조회 버전에 있어 이 법령으로 대조했다",
    "DELETED": "법령명 후보만 추정됐다. 지정 조문은 조회 버전에서 삭제된 조문이다",
    "UNVERIFIED": "법령명 후보만 추정됐다. 지정 조항은 확인하지 못했다",
}


def _abbreviation_inferred(verdict, candidate, provision_status):
    """약칭 추정 결과를 LOW로 남긴다. 조항 확인 여부에 따라 설명을 나눈다(TK-130)."""
    citation = verdict.citation
    ids = [r.source_record_id for r in verdict.source_records]
    phrase = PROVISION_PHRASES.get(provision_status, PROVISION_PHRASES["UNVERIFIED"])
    count = candidate.get("candidate_count", 1)
    verdict.findings.append(Finding.create(
        type=FindingType.LAW_CITATION_ERROR, status=VerificationStatus.PARTIALLY_VERIFIED, severity=Severity.LOW,
        evidence_grade=EvidenceGrade.B,
        title=f"비공식 약칭으로 적힌 법령(추정: {candidate['law_name']}): {citation.law_name}",
        detail=(f"공식 법령 목록에 '{citation.law_name}'이라는 이름은 없다. 공식 목록을 조회한 후보 {count}개 중 "
                f"우선 후보 「{candidate['law_name']}」(법령 ID {candidate['law_id']})로 추정했다. {phrase}. "
                "추정이므로 정식 법령명으로 고쳐 적는 것이 좋다."),
        document_id=citation.document_id, block_id=citation.block_id, page=citation.page, span=citation.span,
        engine="legal_engine", source_record_ids=ids, tags=["LEGAL", "STATUTE", "ABBREVIATION_INFERRED"],
        confidence_features={"verdict_label": "ABBREVIATION_INFERRED", "law_name": citation.law_name,
                             "resolved_law_name": candidate["law_name"], "law_id": candidate["law_id"],
                             "basis": candidate["basis"], "score": candidate["score"],
                             "candidate_count": count, "provision_status": provision_status},
    ))
