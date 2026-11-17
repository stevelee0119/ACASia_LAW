"""Fail-closed inspection of assembled model input, without recording raw PII.

R8-A (TK-51): 구조화(JSON) 요청에서 라벨-값 쌍, 형제 필드 쌍, 배열 이웃 등
              복합 문맥을 복원하여 전송 전 개인정보를 탐지한다.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Set, Tuple

from packages.common.enums import LLMRole
from packages.legal_engine.argument_validity_verifier import _OPINION_SCHEMA, _OPINION_SYSTEM
from packages.llm_router.router import SYSTEM_BASE, _VERDICT_SCHEMA
from packages.pii_engine.detector import (
    PARTY_AND_TITLE_LABELS,
    STRUCTURED_PERSON_KEY_LABELS,
    DOUBLE_SURNAMES,
    JOSA,
    detect,
    is_valid_korean_name_structure,
)
from packages.pii_engine.pseudonym import (
    PSEUDONYM_PREFIXES,
    PSEUDONYM_SEQUENCE_PATTERN,
    canonical_pseudonym_token,
)
from packages.rag_engine.review import ENVELOPE_SCHEMA, ITEM_SCHEMA, KOREAN_RAG_REVIEW_SYSTEM_PROMPT, RAG_REVIEW_SYSTEM_PROMPT, SCHEMA
from packages.verification_engine.ai_document_detector import AI_DETECTOR_SYSTEM_PROMPT, _DETECTOR_SCHEMA

POLICY_VERSION = "payload-pii-v4"
_PSEUDONYM_PREFIX_PATTERN = "|".join(re.escape(prefix) for prefix in PSEUDONYM_PREFIXES)
_STRICT_PERSON_NAME_PREFIXES: Tuple[str, ...] = ("PERSON",)
_ROLE_PARTY_PREFIXES: Tuple[str, ...] = ("PERSON", "COMPANY", "AFFIL")
_CORPORATE_CAPABLE_ROLE_LABELS = frozenset({
    "원고", "피고", "신청인", "피신청인", "청구인", "피청구인", "상고인", "항소인",
    "채권자", "채무자", "대리인", "소송대리인", "대표이사", "대표자", "대표", "담당자",
    "이사장", "원장", "소장", "이사", "감사", "지배인", "관리인", "회장", "사장",
    "매도인", "매수인", "임대인", "임차인", "도급인", "수급인", "위임인", "수임인",
    "양도인", "양수인", "의뢰인", "상대방", "사용자", "보증인", "연대보증인", "법정대리인",
    "plaintiff", "defendant", "applicant", "claimant", "petitioner", "respondent",
    "representative", "counsel", "attorney", "employer", "account holder", "account owner",
    "payee",
})

# ===========================================================================
# 라벨 키 집합: detector.py의 PARTY_AND_TITLE_LABELS에서 단일 출처로 구성 (TK-51, TK-52 2절)
# 개인정보 종류 키(주민등록번호, 연락처, 이메일)도 포함
# ===========================================================================
_PII_TYPE_KEYS = {"주민등록번호", "주민번호", "연락처", "전화번호", "휴대전화", "이메일", "생년월일"}
# 라벨 어휘 + 개인정보 종류 키를 합쳐서 키: 값 문맥 복원 및 형제/이웃 결합 판정에 사용
CONTEXT_LABEL_KEYS: frozenset = frozenset(
    set(PARTY_AND_TITLE_LABELS) | set(STRUCTURED_PERSON_KEY_LABELS) | _PII_TYPE_KEYS
)

_NON_PERSON_NAME_KEY_HEADS = (
    "사건", "법원", "회사", "법인", "기관", "장소", "지명", "부서", "직무",
    "직책", "직위", "문서", "서류", "파일", "자료", "사업", "서비스",
)
_NON_PERSON_ENGLISH_KEY_HEADS = {
    "case", "court", "company", "corporation", "organization", "place", "location",
    "department", "team", "job", "position", "office", "document", "file", "event",
    "business", "service", "product", "site", "subject",
}
_ENGLISH_PERSON_KEY_LABELS = frozenset(
    label.casefold()
    for label in STRUCTURED_PERSON_KEY_LABELS
    if isinstance(label, str) and label.isascii() and label.strip()
)
_NAME_VALUE_RE = re.compile(
    r"^(?P<name>[가-힣]{2,4})"
    r"(?:\s*(?:님|씨|군|양|선생|변호사|변호인|사무관|검사|판사|대위|중위|소령|중령|대령|병장|상병|일병|이병))?"
    r"(?:\s*[（(][^()（）\r\n]{1,24}[)）])?$"
)
_KEY_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_ENGLISH_WORD_RE = re.compile(r"[a-z0-9]+")
_KEY_KOREAN_CLEAN_RE = re.compile(r"[^가-힣0-9a-z]")
_NAME_FIELD_SUFFIX_RE = re.compile(r"(?:성명|성함|이름|명의자|명)$")
_SPACED_NAME_PARTICLE_RE = re.compile(
    rf"^(?P<name>(?:[가-힣][ \t]?){{1,3}}[가-힣])(?:{JOSA})$"
)
_LEADING_NAME_VALUE_RE = re.compile(
    rf"^(?P<name>(?:[가-힣][ \t]?){{1,3}}[가-힣])(?:{JOSA}){{0,2}}(?=\s)"
)
_COMPOSITE_NAME_PARTICLE_RE = re.compile(
    rf"^(?P<name>(?:[가-힣][ \t]?){{1,3}}[가-힣])(?:{JOSA}){{1,2}}$"
)


def _build_masked_value_re(prefixes: Tuple[str, ...]) -> re.Pattern[str]:
    prefix_pat = "|".join(re.escape(prefix) for prefix in prefixes)
    single = (
        rf"(?:\[(?:{prefix_pat})_{PSEUDONYM_SEQUENCE_PATTERN}\]"
        rf"|(?:{prefix_pat})_{PSEUDONYM_SEQUENCE_PATTERN})(?:{JOSA})?"
    )
    return re.compile(rf"[ \t]*{single}(?:[ \t,;/]+{single})*[ \t]*")


# Strict canonical token grammar (balanced brackets, 3-digit bound, field-kind prefix distinction)
_MASKED_NAME_VALUE_RE = _build_masked_value_re(_STRICT_PERSON_NAME_PREFIXES)
_MASKED_ROLE_PARTY_VALUE_RE = _build_masked_value_re(_ROLE_PARTY_PREFIXES)
_MASKED_TOKEN_EXTRACTOR_RE = re.compile(
    rf"\[(?:{_PSEUDONYM_PREFIX_PATTERN})_{PSEUDONYM_SEQUENCE_PATTERN}\]"
    rf"|(?:{_PSEUDONYM_PREFIX_PATTERN})_{PSEUDONYM_SEQUENCE_PATTERN}"
)


def _allowed_prefixes_for_field(label: str | None, marker: bool) -> Tuple[str, ...]:
    if not marker and label and label.casefold() in _CORPORATE_CAPABLE_ROLE_LABELS:
        return _ROLE_PARTY_PREFIXES
    return _STRICT_PERSON_NAME_PREFIXES



def _normalise_korean_key(key: str) -> str:
    """공백·괄호·구두점 표기가 달라도 키의 한글 라벨을 비교한다."""
    text = unicodedata.normalize("NFKC", key)
    return _KEY_KOREAN_CLEAN_RE.sub("", text.casefold())


# Fixed label grammar is computed once, not rebuilt for every field.
_KOREAN_KEY_LABELS = tuple(sorted(
    ((_normalise_korean_key(label), label) for label in PARTY_AND_TITLE_LABELS),
    key=lambda pair: (-len(pair[0]), pair[0]),
))
_ENGLISH_KEY_PHRASES = tuple(sorted(
    (tuple(label.split()) for label in _ENGLISH_PERSON_KEY_LABELS),
    key=lambda phrase: (-len(phrase), phrase),
))
_ENGLISH_ROLE_TERMS = frozenset(
    label for label in _ENGLISH_PERSON_KEY_LABELS
    if " " not in label and label != "name"
)
_KOREAN_NON_PERSON_KEYS = frozenset(
    f"{head}{suffix}" for head in _NON_PERSON_NAME_KEY_HEADS
    for suffix in ("명", "이름")
)


def _key_words(key: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", key)
    separated = _KEY_CAMEL_BOUNDARY_RE.sub(" ", normalized)
    return tuple(_KEY_ENGLISH_WORD_RE.findall(separated.casefold()))


def _has_name_field_marker(key: Any) -> bool:
    """An unknown subject plus a name suffix is a field signal, not a person type."""
    if not isinstance(key, str):
        return False
    korean = _normalise_korean_key(key)
    if korean in _KOREAN_NON_PERSON_KEYS:
        return False
    words = _key_words(key)
    if any(word in _NON_PERSON_ENGLISH_KEY_HEADS for word in words):
        # Existing explicit human roles still override a non-person prefix.
        if not any(word in _ENGLISH_ROLE_TERMS for word in words):
            return False
    return bool(_NAME_FIELD_SUFFIX_RE.search(korean)) or bool(
        words and words[-1] in {"name", "nm", "surname", "forename"}
    )


def _person_label_for_key(key: Any) -> str | None:
    """키에서 사람 이름 문맥을 구성할 detector 라벨 어휘를 반환한다."""
    if not isinstance(key, str) or not key.strip():
        return None

    normalized = unicodedata.normalize("NFKC", key)
    korean_key = _normalise_korean_key(normalized)
    if korean_key:
        # 단순히 '-명/이름'으로 끝나는 비인명 키에는 사람 문맥을 붙이지 않는다.
        if korean_key in _KOREAN_NON_PERSON_KEYS:
            return None
        for label, original in _KOREAN_KEY_LABELS:
            if label and label in korean_key:
                return original
        if _NAME_FIELD_SUFFIX_RE.search(korean_key):
            return "이름"

    # camelCase, snake_case, 괄호·공백 변형을 동일한 영어 토큰으로 처리한다.
    words = _key_words(normalized)
    if not words:
        return None
    if any(word in _NON_PERSON_ENGLISH_KEY_HEADS for word in words):
        # 명시적인 사람 역할 표지가 있으면 'company representative'처럼 사람 필드로 인정한다.
        if not any(label in words for label in _ENGLISH_ROLE_TERMS):
            return None
    # Constant-sized phrase grammar; one traversal per key.
    phrase_matches = [
        (phrase, position)
        for position in range(len(words))
        for phrase in _ENGLISH_KEY_PHRASES
        if words[position:position + len(phrase)] == phrase
        and not (phrase == ("name",) and position != 0)
    ]
    if phrase_matches:
        phrase, _ = min(phrase_matches, key=lambda item: (-len(item[0]), item[1], item[0]))
        if phrase[-1] == "name" and tuple(phrase[:-1]) in _ENGLISH_KEY_PHRASES:
            return " ".join(phrase[:-1])
        return " ".join(phrase)
    if words[-1] == "nm":
        return "이름"
    return None


def _is_person_name_key(key: Any) -> bool:
    """detector 라벨 어휘를 바탕으로 키가 사람 이름 필드인지 판정한다."""
    return _person_label_for_key(key) is not None


def _name_like_value(value: str) -> str | None:
    """키 문맥을 붙일 단일 한국어 이름 토큰만 반환한다."""
    candidate = unicodedata.normalize("NFKC", value).strip()
    particle_match = _SPACED_NAME_PARTICLE_RE.fullmatch(candidate)
    if particle_match:
        stem = re.sub(r"[ \t]", "", particle_match.group("name"))
        compact = re.sub(r"[ \t]", "", candidate)
        # Preserve three-syllable names and four-syllable double-surname names.
        if len(compact) > 3 and not (
            len(compact) == 4 and compact[:2] in DOUBLE_SURNAMES
        ):
            if is_valid_korean_name_structure(stem):
                return stem
    match = _NAME_VALUE_RE.fullmatch(candidate)
    if not match:
        return None
    name = match.group("name")
    return name if is_valid_korean_name_structure(name) else None


def _uncertain_person_value(
    value: Any,
    *,
    explicit_name: bool,
    name_field: bool = False,
    allowed_prefixes: Tuple[str, ...] = _STRICT_PERSON_NAME_PREFIXES,
    trusted_spans: frozenset[Tuple[int, int, str]] | None = None,
) -> bool:
    """Decide send safety separately from extracting a single name token."""
    if not isinstance(value, str):
        return True
    text = unicodedata.normalize("NFKC", value).strip()
    if not text:
        return False
    masked_pattern = (
        _MASKED_ROLE_PARTY_VALUE_RE
        if allowed_prefixes == _ROLE_PARTY_PREFIXES
        else _MASKED_NAME_VALUE_RE
    )
    if masked_pattern.fullmatch(text):
        if trusted_spans is None:
            return False
        raw_matches = list(_MASKED_TOKEN_EXTRACTOR_RE.finditer(value))
        nfkc_matches = list(_MASKED_TOKEN_EXTRACTOR_RE.finditer(text))
        if not raw_matches or len(raw_matches) != len(nfkc_matches):
            return True
        for m in raw_matches:
            canon = canonical_pseudonym_token(
                m.group(0), allowed_prefixes=allowed_prefixes, bracketed=True,
            )
            if canon is None or (m.start(), m.end(), canon) not in trusted_spans:
                return True
        return False
    if _name_like_value(text):
        # Single-name context is checked by the normal detector.
        return False
    if explicit_name or name_field:
        # A grammatical name suffix supplies context even when its subject is
        # unknown. Inspect only a bounded name window, not arbitrary titles or
        # an exception vocabulary. Role-only keys retain their existing contract.
        for pattern in (_LEADING_NAME_VALUE_RE, _COMPOSITE_NAME_PARTICLE_RE):
            match = pattern.match(text)
            if match and is_valid_korean_name_structure(match.group("name")):
                return True
    # Name markers do not change a clearly non-name Korean value into a person.
    # Keep the same value-shape boundary for roles and explicit name fields;
    # foreign scripts, punctuation and non-string values remain uncertain.
    # A name-shaped first word alone cannot establish the type of a multiword
    # organization. Raw text is still scanned, with no new noun exemptions.
    compact = []
    for char in text:
        if "가" <= char <= "힣":
            if len(compact) < 5:
                compact.append(char)
        elif not char.isspace():
            return True
    # A short explicit name can have an unfamiliar surname or be transliterated.
    # Failure of the surname grammar is not proof of a non-person value.
    return len(compact) <= 4 and (
        explicit_name or is_valid_korean_name_structure("".join(compact))
    )


# ===========================================================================
# TK-28 (U3): 출처가 확인된 고정 시스템 프롬프트 및 스키마 등록소
# ===========================================================================
def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_schema(schema: Any) -> str:
    serialized = json.dumps(schema, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# 1. 등록 고정 시스템 프롬프트 목록
REGISTERED_SYSTEM_PROMPT_CONSTANTS: Dict[str, str] = {
    "SYS_AI_DOCUMENT_DETECTOR": AI_DETECTOR_SYSTEM_PROMPT,
    "SYS_RAG_REVIEW": RAG_REVIEW_SYSTEM_PROMPT,
    "SYS_ARGUMENT_OPINION": _OPINION_SYSTEM,
    "SYS_KOREAN_RAG_REVIEW": KOREAN_RAG_REVIEW_SYSTEM_PROMPT,
    "SYS_ROUTER_BASE": SYSTEM_BASE,
    "SYS_EMPTY": "",
}

REGISTERED_SYSTEM_HASHES: Set[str] = {
    _hash_text(prompt) for prompt in REGISTERED_SYSTEM_PROMPT_CONSTANTS.values()
}

# 2. 등록 고정 스키마 목록
REGISTERED_SCHEMA_CONSTANTS: Dict[str, Any] = {
    "SCHEMA_AI_DETECTOR": _DETECTOR_SCHEMA,
    "SCHEMA_RAG_ENVELOPE": ENVELOPE_SCHEMA,
    "SCHEMA_RAG_FULL": SCHEMA,
    "SCHEMA_RAG_ITEM": ITEM_SCHEMA,
    "SCHEMA_ARGUMENT_OPINION": _OPINION_SCHEMA,
    "SCHEMA_ROUTER_VERDICT": _VERDICT_SCHEMA,
}

REGISTERED_SCHEMA_HASHES: Set[str] = {
    _hash_schema(schema) for schema in REGISTERED_SCHEMA_CONSTANTS.values()
}


def is_registered_system_prompt(text: str) -> bool:
    """system 필드의 문자열이 출처가 확인된 등록 고정 상수인지 검증한다 (TK-28).

    1. 등록된 시스템 프롬프트 상수와 완전 일치
    2. router에서 SYSTEM_BASE + [역할] role + 등록 프롬프트로 조립된 고정 문자열과 완전 일치
    """
    if not isinstance(text, str):
        return False
    # 기본 등록 프롬프트와 완전 일치
    if _hash_text(text) in REGISTERED_SYSTEM_HASHES:
        return True
    # router의 고정 조립 패턴 확인: f"{SYSTEM_BASE}\n[역할] {role}\n{sub_prompt}"
    prefix = f"{SYSTEM_BASE}\n[역할] "
    if text.startswith(prefix):
        rest = text[len(prefix):]
        parts = rest.split("\n", 1)
        role_str = parts[0]
        sub_prompt = parts[1] if len(parts) > 1 else ""
        valid_roles = {str(r) for r in LLMRole} | {r.value for r in LLMRole}
        if role_str in valid_roles:
            return _hash_text(sub_prompt) in REGISTERED_SYSTEM_HASHES
    return False


def is_registered_schema(schema: Any) -> bool:
    """schema 필드가 출처가 확인된 등록 고정 스키마 상수인지 검증한다 (TK-28)."""
    if not isinstance(schema, (dict, list)):
        return False
    try:
        return _hash_schema(schema) in REGISTERED_SCHEMA_HASHES
    except Exception:
        return False


# ===========================================================================
# R8-A / 8B-2 (TK-51, TK-52 2절): 구조화 JSON 값에서 문맥을 복원하여 문자열 추출
# ===========================================================================
@dataclass(frozen=True)
class _JSONObjectPairs:
    """Inspection-only JSON object; duplicate values must never disappear."""

    pairs: tuple[tuple[str, Any], ...]


def _json_object_pairs(pairs):
    return _JSONObjectPairs(tuple(pairs))


def _try_json_parse(value: str):
    """문자열을 JSON으로 파싱 시도. 성공하면 파싱 결과, 실패하면 None 반환."""
    try:
        decoded = json.loads(value, object_pairs_hook=_json_object_pairs)
    except (ValueError, TypeError):
        return None
    if isinstance(decoded, (_JSONObjectPairs, list, str)):
        return decoded
    return None


def _collect_texts_with_spans(
    value,
    path: str = "",
    *,
    diag_path: str = "",
    _uncertain_paths: List[str] | None = None,
    _uncertain_diag_paths: List[str] | None = None,
    span_resolver=None,
) -> List[Tuple[str, str, frozenset[Tuple[int, int, str]] | None, str]]:
    """Collect (path, text, trusted_spans, diag_path) tuples with per-field provenance resolution."""
    results: List[Tuple[str, str, frozenset[Tuple[int, int, str]] | None, str]] = []

    if isinstance(value, str):
        decoded = _try_json_parse(value)
        if decoded is not None:
            results.extend(_collect_texts_with_spans(
                decoded,
                path,
                diag_path=diag_path,
                _uncertain_paths=_uncertain_paths,
                _uncertain_diag_paths=_uncertain_diag_paths,
                span_resolver=span_resolver,
            ))
        else:
            spans = span_resolver(path, value) if span_resolver is not None else None
            results.append((path, value, spans, diag_path or "root"))

    elif isinstance(value, (dict, _JSONObjectPairs)):
        str_items: List[Tuple[str, str]] = []
        items = value.pairs if isinstance(value, _JSONObjectPairs) else value.items()
        for key, item in items:
            key_str = str(key)
            current_path = f"{path}.{key_str}" if path else key_str
            safe_k = _safe_diagnostic_key(key_str)
            current_diag = f"{diag_path}.{safe_k}" if diag_path else safe_k
            label = _person_label_for_key(key)
            marker = _has_name_field_marker(key)
            item_spans = (
                span_resolver(current_path, item)
                if (span_resolver is not None and isinstance(item, str))
                else None
            )
            if (label or marker) and _uncertain_person_value(
                item,
                explicit_name=bool(label and marker),
                name_field=marker,
                allowed_prefixes=_allowed_prefixes_for_field(label, marker),
                trusted_spans=item_spans,
            ):
                if _uncertain_paths is not None:
                    _uncertain_paths.append(current_path)
                if _uncertain_diag_paths is not None:
                    _uncertain_diag_paths.append(current_diag)

            if isinstance(item, str):
                decoded = _try_json_parse(item)
                if decoded is not None:
                    results.extend(_collect_texts_with_spans(
                        decoded,
                        current_path,
                        diag_path=current_diag,
                        _uncertain_paths=_uncertain_paths,
                        _uncertain_diag_paths=_uncertain_diag_paths,
                        span_resolver=span_resolver,
                    ))
                else:
                    results.append((current_path, item, item_spans, current_diag))
                    if key in _PII_TYPE_KEYS:
                        if item_spans:
                            shift = len(key_str) + 2
                            shifted_spans = frozenset(
                                (ts + shift, te + shift, tok) for ts, te, tok in item_spans
                            )
                        else:
                            shifted_spans = item_spans
                        results.append((current_path, f"{key}: {item}", shifted_spans, current_diag))
                    else:
                        name = _name_like_value(item)
                        if (label or marker) and name:
                            label = label or "이름"
                            detector_label = "이름" if label.isascii() else label
                            synth_text = f"{detector_label}: {name}"
                            synth_spans = span_resolver(current_path, synth_text) if span_resolver is not None else None
                            results.append((current_path, synth_text, synth_spans, current_diag))
                    str_items.append((key, item))
            else:
                results.extend(_collect_texts_with_spans(
                    item,
                    current_path,
                    diag_path=current_diag,
                    _uncertain_paths=_uncertain_paths,
                    _uncertain_diag_paths=_uncertain_diag_paths,
                    span_resolver=span_resolver,
                ))

        for i in range(len(str_items) - 1):
            (k1, v1), (k2, v2) = str_items[i], str_items[i + 1]
            if v1 in CONTEXT_LABEL_KEYS and v2 not in CONTEXT_LABEL_KEYS and is_valid_korean_name_structure(v2):
                sibling_path = f"{path}.__siblings__[{i}]" if path else f"__siblings__[{i}]"
                sibling_diag = f"{diag_path}.__siblings__[{i}]" if diag_path else f"__siblings__[{i}]"
                synth_text = f"{v1} {v2}"
                synth_spans = span_resolver(sibling_path, synth_text) if span_resolver is not None else None
                results.append((sibling_path, synth_text, synth_spans, sibling_diag))

    elif isinstance(value, (list, tuple)):
        str_elements: List[str] = []
        for idx, item in enumerate(value):
            current_path = f"{path}[{idx}]"
            current_diag = f"{diag_path}[{idx}]" if diag_path else f"[{idx}]"
            if isinstance(item, str):
                decoded = _try_json_parse(item)
                if decoded is not None:
                    results.extend(_collect_texts_with_spans(
                        decoded,
                        current_path,
                        diag_path=current_diag,
                        _uncertain_paths=_uncertain_paths,
                        _uncertain_diag_paths=_uncertain_diag_paths,
                        span_resolver=span_resolver,
                    ))
                else:
                    elem_spans = span_resolver(current_path, item) if span_resolver is not None else None
                    results.append((current_path, item, elem_spans, current_diag))
                    str_elements.append(item)
            else:
                results.extend(_collect_texts_with_spans(
                    item,
                    current_path,
                    diag_path=current_diag,
                    _uncertain_paths=_uncertain_paths,
                    _uncertain_diag_paths=_uncertain_diag_paths,
                    span_resolver=span_resolver,
                ))

        for i in range(len(str_elements) - 1):
            w1, w2 = str_elements[i], str_elements[i + 1]
            if w1 in CONTEXT_LABEL_KEYS and w2 not in CONTEXT_LABEL_KEYS and is_valid_korean_name_structure(w2):
                neighbor_path = f"{path}.__neighbors__[{i}]" if path else f"__neighbors__[{i}]"
                neighbor_diag = f"{diag_path}.__neighbors__[{i}]" if diag_path else f"__neighbors__[{i}]"
                synth_text = f"{w1} {w2}"
                synth_spans = span_resolver(neighbor_path, synth_text) if span_resolver is not None else None
                results.append((neighbor_path, synth_text, synth_spans, neighbor_diag))

    return results


def _collect_texts_from_value(
    value,
    path: str = "",
    *,
    _uncertain_paths: List[str] | None = None,
) -> List[Tuple[str, str]]:
    """값에서 (경로, 검사할 텍스트) 쌍을 수집한다.

    사전:
      - 원본 문자열 값은 항상 검사.
      - 사람 표지 키의 단일 이름 꼴 값과 식별번호 종류 키에 문맥을 합성.
      - 불확실 성명 필드는 원문 없이 _uncertain_paths에 경로만 기록(TK-56).
      - 형제 결합: 선행 값이 라벨이고 후행 값이 라벨이 아니며 유효한 이름 구조일 때만 결합 문맥 합성 (역할/이름 쌍 지원).
    배열:
      - 선행 원소가 라벨이고 후행 원소가 라벨이 아니며 유효한 이름 구조일 때만 결합 문맥 합성 (라벨 나열 배열 과차단 방지).
    JSON 문자열:
      - 재귀적으로 파싱하여 같은 규칙 적용.
    """
    return [
        (collected_path, collected_text)
        for collected_path, collected_text, *_ in _collect_texts_with_spans(
            value, path, _uncertain_paths=_uncertain_paths,
        )
    ]


def _walk_fields(value, path="", *, _uncertain_paths=None):
    """필드 경로(path)와 함께 문자열 값들을 추출한다 (R8-A 강화 버전).

    TK-51/TK-56: 원본 값과 유효한 이름 문맥, 형제/배열 문맥을 추출한다.
    라벨 키 정의는 detector.py의 PARTY_AND_TITLE_LABELS에서 단일 출처로 가져온다.
    """
    for collected_path, collected_text in _collect_texts_from_value(
        value, path, _uncertain_paths=_uncertain_paths,
    ):
        yield collected_path, collected_text


# ===========================================================================
# 진단 출력용 경로·코드 정규화 (TK-186 보완: 입력 유래 임의 키·값 원문 노출 차단)
# ===========================================================================
_SAFE_DIAGNOSTIC_KEYS: frozenset[str] = frozenset({
    # LLMRequest 및 내부 감사 루트
    "system", "user", "schema", "max_tokens", "temperature",
    "metadata", "input_contract", "inspection_source",
    "original_system", "__original_system__", "cascade_source", "excerpt_source",
    # Cascade / Evidence 고정 필드
    "question", "official", "document", "primary_verdict",
    "case_number", "source_excerpt", "full_text", "excerpt_coverage",
    "excerpt_sections", "opinion_sections", "confirmed_metadata", "metadata_scope",
    "segment_id", "opinion_kinds", "original_start", "original_end",
    "court", "decision_date", "decision_type", "case_name",
    "masking", "attempted", "masked", "raw_chars", "masked_chars",
    "raw_sha256", "masked_sha256", "masked_types",
    "status", "confidence", "rationale", "evidence_quotes", "contradicts",
    "stage",
    # 1st-party input_contracts 고정 필드
    "document_filename", "metadata_ai_hint", "document_sample_text", "document_coverage",
    "total_chars", "inspected_chars", "sampling_mode", "is_full_coverage",
    "omitted_chars", "char_limit", "quote_masked_chars", "scope",
    "requested_chars", "model_executed",
    "untrusted_references", "reference_sources", "system_instructions",
    "jurisdiction", "reference_date", "reference_date_status",
    "source_id", "title", "text", "page", "claim_id", "claim_text",
    "items", "item_id", "cited_case", "surrounding_context_and_claim",
    "확인 상태", "원문 대조(어절 단위, 원문 기준)", "관련 권위 판례(참고)",
    # JSON Schema 고정 메타 키
    "type", "properties", "required", "additionalProperties", "enum",
    "minLength", "maxLength", "maxItems", "minItems", "pattern", "default",
    "observations", "claim_quote", "source_quote", "relationship", "explanation",
})
_SAFE_CONTRACT_FAILURE_CODES: frozenset[str] = frozenset({
    "input_contract", "cascade_source", "excerpt_source",
    "token_attestation", "excerpt_invalid_trace",
})
_SAFE_FAILURE_CODES: frozenset[str] = frozenset({
    "PII_INPUT_BLOCKED", "INPUT_CONTRACT_VIOLATION",
    "STATIC_PROMPT_FALSE_POSITIVE", "INSPECTION_EXCEPTION", "INSPECTION_FAILED",
})
_SAFE_DIAGNOSTIC_CATEGORIES: frozenset[str] = frozenset({
    "MASKING_PII_DETECTED", "REQUEST_WIRING_CONTRACT", "INSPECTION_EXCEPTION",
})
_SAFE_PII_KIND_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
def _safe_diagnostic_key(raw_key: Any) -> str:
    """허용 목록 밖의 객체 키를 원문이 드러나지 않는 고정 토큰(key_<12자 해시>)으로 변환한다."""
    key_str = str(raw_key)
    if key_str in _SAFE_DIAGNOSTIC_KEYS:
        return key_str
    digest = hashlib.sha256(key_str.encode("utf-8")).hexdigest()[:12]
    return f"key_{digest}"


def _safe_diagnostic_path(raw_path: Any, *, prefix: str = "") -> str:
    """타입이 지정된 경로 구간(객체 키=str, 배열 첨자=int)만 받아 외부 진단용 경로로 직렬화한다.

    문자열 경로를 사후 분할·추정하지 않는다. `key_` 접두나 `[숫자]` 모양의 문자열도 신뢰하지 않으며,
    허용 목록 밖의 객체 키는 모양과 무관하게 항상 해시 토큰으로 바꾼다. 실제 정수(bool 제외)만
    배열 첨자로 보존한다. 튜플/리스트가 아닌 입력은 구조를 알 수 없으므로 하나의 불투명 키로 해시한다.
    """
    if isinstance(raw_path, (tuple, list)):
        segments = tuple(raw_path)
    elif raw_path is None or raw_path == "":
        segments = ()
    else:
        segments = (raw_path,)
    normalized = ""
    for elem in segments:
        if isinstance(elem, int) and not isinstance(elem, bool) and elem >= 0:
            normalized = f"{normalized}[{elem}]" if normalized else f"[{elem}]"
        else:
            safe_k = _safe_diagnostic_key(elem)
            normalized = f"{normalized}.{safe_k}" if normalized else safe_k
    if not normalized:
        normalized = "root"
    if prefix:
        safe_prefix = _safe_diagnostic_key(prefix)
        return safe_prefix if normalized == "root" else f"{safe_prefix}.{normalized}"
    return normalized


def inspect_request(request, *, _original_system: str = None):
    """조립된 LLM 요청의 개인정보 포함 여부를 감사한다. 원문 PII는 기록하지 않는다.

    TK-28 (U3):
    - 종류 목록 방식을 폐기하고 등록된 고정 상수 출처 확인 방식으로 전환.
    - system/schema가 등록된 고정 상수와 정확히 일치할 때만 그 안의 탐지를 정적 오탐으로 인정.
    - 등록되지 않은 system/schema(동적 값 섞임 포함) 및 user 영역에서의 탐지는 PII 종류와 무관하게 차단.

    R8-A (TK-51):
    - _original_system이 주어지면 조립 전 원본 system을 별도 검사한다.
    """
    from .input_contracts import valid_input_contract
    from .cascade_source import cascade_inspection_text, valid_cascade_source
    from .excerpt_source import excerpt_inspection, valid_excerpt_source
    from .token_attestation import attested_spans_for, has_token_attestation, valid_token_attestation

    contract_failures = []
    if not valid_input_contract(request, original_system=_original_system):
        contract_failures.append("input_contract")
    if not valid_cascade_source(request, original_system=_original_system):
        contract_failures.append("cascade_source")
    if not valid_excerpt_source(request, original_system=_original_system):
        contract_failures.append("excerpt_source")
    if not valid_token_attestation(request, original_system=_original_system):
        contract_failures.append("token_attestation")
    contract_valid = not contract_failures
    is_attested = has_token_attestation(request)

    def _user_span_resolver(field_path: str, raw_text: str):
        return attested_spans_for(request, field_path, raw_text, original_system=_original_system)

    def _unattested_span_resolver(field_path: str, raw_text: str):
        return frozenset() if is_attested else None

    payload = asdict(request)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

    kinds = Counter()
    blocked_kinds = Counter()
    static_fp_kinds = Counter()
    detected_paths = set()

    excerpt_statuses, excerpt_matches = excerpt_inspection(request)
    if 'INVALID_TRACE' in excerpt_statuses:
        contract_valid = False
        if "excerpt_invalid_trace" not in contract_failures:
            contract_failures.append("excerpt_invalid_trace")
    for path, kind, _ in excerpt_matches:
        safe_kind = kind if isinstance(kind, str) and _SAFE_PII_KIND_RE.fullmatch(kind) else "PII"
        kinds[safe_kind] += 1
        blocked_kinds[safe_kind] += 1
        detected_paths.add(_safe_diagnostic_path(path, prefix="excerpt_source"))

    # Additional source inspection never replaces the original/assembled scans.
    # Even a mismatched context is inspected so PII keeps failure precedence.
    source_text = cascade_inspection_text(request)
    if source_text is not None:
        uncertain_diag_paths = []
        for path, text, spans, diag_path in _collect_texts_with_spans(
            source_text,
            "cascade_source",
            diag_path="cascade_source",
            _uncertain_diag_paths=uncertain_diag_paths,
            span_resolver=_user_span_resolver,
        ):
            matches = [m for m in detect(text, _trusted_spans=spans) if m.confidence >= 0.6]
            for match in matches:
                safe_kind = match.kind if isinstance(match.kind, str) and _SAFE_PII_KIND_RE.fullmatch(match.kind) else "PII"
                kinds[safe_kind] += 1
                blocked_kinds[safe_kind] += 1
                detected_paths.add(diag_path)
        if uncertain_diag_paths:
            kinds["PERSON"] += len(uncertain_diag_paths)
            blocked_kinds["PERSON"] += len(uncertain_diag_paths)
            detected_paths.update(uncertain_diag_paths)

    # R8-A: 조립 전 원본 system이 있으면 별도 검사 (JSON 구조 보존)
    if _original_system is not None:
        uncertain_diag_paths = []
        for path, text, spans, diag_path in _collect_texts_with_spans(
            _original_system,
            "original_system",
            diag_path="original_system",
            _uncertain_diag_paths=uncertain_diag_paths,
            span_resolver=_unattested_span_resolver,
        ):
            matches = [m for m in detect(text, _trusted_spans=spans) if m.confidence >= 0.6]
            for m in matches:
                safe_kind = m.kind if isinstance(m.kind, str) and _SAFE_PII_KIND_RE.fullmatch(m.kind) else "PII"
                kinds[safe_kind] += 1
                # 원본 system은 사용자 제공 동적 값이므로 등록 상수 면책 없음
                blocked_kinds[safe_kind] += 1
                detected_paths.add(diag_path)
        if uncertain_diag_paths:
            kinds["PERSON"] += len(uncertain_diag_paths)
            blocked_kinds["PERSON"] += len(uncertain_diag_paths)
            detected_paths.update(uncertain_diag_paths)

    # 최상위 payload 필드를 개별 순회하여 경로 기반 등록 판정이 정확하게 동작하도록 함
    # (payload 전체를 _walk_fields에 넘기면 최상위 형제 결합이 경로 판정을 혼동시킴)
    for top_key, top_value in payload.items():
        uncertain_diag_paths = []
        resolver = _user_span_resolver if top_key == "user" else _unattested_span_resolver
        top_diag = top_key if top_key in _SAFE_DIAGNOSTIC_KEYS else _safe_diagnostic_key(top_key)
        for path, text, spans, diag_path in _collect_texts_with_spans(
            top_value,
            top_key,
            diag_path=top_diag,
            _uncertain_diag_paths=uncertain_diag_paths,
            span_resolver=resolver,
        ):
            matches = [m for m in detect(text, _trusted_spans=spans) if m.confidence >= 0.6]
            if not matches:
                continue
            detected_paths.add(diag_path)
            for m in matches:
                safe_kind = m.kind if isinstance(m.kind, str) and _SAFE_PII_KIND_RE.fullmatch(m.kind) else "PII"
                kinds[safe_kind] += 1
                is_system_path = path.startswith("system")
                is_schema_path = path.startswith("schema")

                is_verified_static_source = False
                if is_system_path:
                    is_verified_static_source = is_registered_system_prompt(request.system)
                elif is_schema_path:
                    is_verified_static_source = is_registered_schema(request.schema)

                if is_verified_static_source:
                    # 출처가 확인된 등록 고정 상수 내에서의 탐지는 정적 안내문 오탐으로 면책
                    static_fp_kinds[safe_kind] += 1
                else:
                    # 등록되지 않은 영역(사용자 입력 또는 동적 값이 혼입된 시스템 프롬프트)에서의 탐지는
                    # PII 종류(PERSON, DOB, PHONE, EMAIL 등)와 무관하게 차단
                    blocked_kinds[safe_kind] += 1
        if uncertain_diag_paths:
            kinds["PERSON"] += len(uncertain_diag_paths)
            detected_paths.update(uncertain_diag_paths)
            is_verified_static_source = (
                top_key == "system" and is_registered_system_prompt(request.system)
            ) or (top_key == "schema" and is_registered_schema(request.schema))
            target = static_fp_kinds if is_verified_static_source else blocked_kinds
            target["PERSON"] += len(uncertain_diag_paths)

    if blocked_kinds:
        status = "BLOCKED"
        failure_code = "PII_INPUT_BLOCKED"
        diagnostic_category = "MASKING_PII_DETECTED"
    elif not contract_valid:
        status = "BLOCKED"
        failure_code = "INPUT_CONTRACT_VIOLATION"
        diagnostic_category = "REQUEST_WIRING_CONTRACT"
    elif static_fp_kinds:
        status = "PASSED"
        failure_code = "STATIC_PROMPT_FALSE_POSITIVE"
        diagnostic_category = None
    else:
        status = "PASSED"
        failure_code = None
        diagnostic_category = None

    safe_contract_failures = [
        cf if cf in _SAFE_CONTRACT_FAILURE_CODES else "contract_violation"
        for cf in contract_failures
    ]

    safe_masking = {}
    if source_text is not None:
        try:
            src_obj = json.loads(source_text)
            raw_mask_meta = ((src_obj.get("official") or {}).get("masking")
                             if isinstance(src_obj, dict) else None)
            if isinstance(raw_mask_meta, dict):
                for mk in ("attempted", "masked", "raw_chars", "masked_chars", "raw_sha256", "masked_sha256"):
                    mv = raw_mask_meta.get(mk)
                    if isinstance(mv, (bool, int)):
                        safe_masking[mk] = mv
                    elif isinstance(mv, str) and re.fullmatch(r"[0-9a-fA-F]{8,64}", mv):
                        safe_masking[mk] = mv[:64]
                if isinstance(raw_mask_meta.get("masked_types"), dict):
                    safe_masking["masked_types"] = {
                        (str(k) if _SAFE_PII_KIND_RE.fullmatch(str(k)) else "OTHER"): int(v)
                        for k, v in raw_mask_meta["masked_types"].items()
                        if isinstance(v, (int, float))
                    }
        except Exception:
            pass

    user_chars = len(request.user) if isinstance(request.user, str) else 0
    res = {
        "policy_version": POLICY_VERSION,
        "request_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "scope": "ASSEMBLED_LLM_REQUEST",
        "status": status,
        "detected_types": dict(kinds),
        "user_chars": user_chars,
    }
    if safe_masking:
        res["masking"] = safe_masking
    if excerpt_statuses:
        from packages.common.source_trace import MAX_SOURCE_CHARS, MAX_TRACE_CHARS
        res['excerpt_projection'] = {'statuses': dict(Counter(excerpt_statuses)),
                                    'source_char_limit': MAX_SOURCE_CHARS, 'trace_char_limit': MAX_TRACE_CHARS,
                                    'decoder_work_multiple': 8}
    if diagnostic_category:
        res["diagnostic_category"] = (
            diagnostic_category if diagnostic_category in _SAFE_DIAGNOSTIC_CATEGORIES else "INSPECTION_EXCEPTION"
        )
    if safe_contract_failures:
        res["contract_failures"] = safe_contract_failures
    if failure_code:
        res["failure_code"] = failure_code if failure_code in _SAFE_FAILURE_CODES else "INSPECTION_FAILED"
        res["detected_field_paths"] = sorted(detected_paths)
        res["retryable"] = failure_code == "STATIC_PROMPT_FALSE_POSITIVE"
        if failure_code == "STATIC_PROMPT_FALSE_POSITIVE":
            res["note"] = "출처가 확인된 등록 고정 상수의 정적 어휘 오탐으로 판정하여 호출을 허용함(동적 PII 없음)"
    if status != "PASSED":
        safe_blocked = {
            (k if isinstance(k, str) and _SAFE_PII_KIND_RE.fullmatch(k) else "PII"): int(v)
            for k, v in blocked_kinds.items()
        }
        types_str = ",".join(f"{k}:{v}" for k, v in sorted(safe_blocked.items())) or "none"
        paths_list = sorted(detected_paths)
        paths_str = ",".join((p[:32] + ".." if len(p) > 34 else p) for p in paths_list[:4])
        if len(paths_list) > 4:
            paths_str += f"(+{len(paths_list) - 4})"
        mask_str = (
            f"mask=yes({int(safe_masking.get('masked_chars', user_chars))})"
            if safe_masking.get("attempted") else f"mask=unrecorded(len={user_chars})"
        )
        safe_fc = res.get("failure_code") or "UNKNOWN"
        safe_cat = res.get("diagnostic_category") or safe_fc
        code_parts = [str(safe_fc)]
        if safe_contract_failures:
            code_parts.append(",".join(safe_contract_failures))
        res["safe_summary"] = (
            f"[{safe_cat}:{'/'.join(code_parts)}] "
            f"types={types_str}; paths={paths_str or '-'}; {mask_str}; sha={res['request_sha256'][:12]}"
        )
    return res
