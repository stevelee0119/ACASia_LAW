"""Hybrid Retrieval Tier 1 (Exact Legal Identifier Index) & Tier 2 (BM25 Lexical Scorer) (P1 PR-07).

Extracts canonical Korean legal identifiers:
- Case numbers (e.g., `2020다12345`, `2019헌마100`)
- Statute articles (`<법령명> 제N조(의M)(제K항)`)
- Exhibit numbers (`갑 제1호증`, `을 제2호증의1`)

Provides an O(1) SQLite/in-memory inverted index (`IdentifierIndex`) for exact Tier 1 pinning
and a BM25 lexical scorer (`bm25_score_chunks`) combining character bigrams with content tokens.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import re
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from packages.legal_engine.normalize import canonical_article, extract_all_case_numbers
from packages.rag_engine.relevance import tokens as bigram_tokens


_STATUTE_CITE_RE = re.compile(
    r"(?P<law>[가-힣]{2,20}(?:\s+[가-힣]{1,10}){0,3}?(?:법률|법|헌법|령|규칙))\s*"
    r"제\s*(?P<art>\d+)\s*조(?:\s*의\s*(?P<sub>\d+))?(?:\s*제\s*(?P<para>\d+)\s*항)?"
)
_EXHIBIT_RE = re.compile(
    r"(?P<side>[갑을병정])\s*제\s*(?P<num>\d+)\s*호증(?:\s*의\s*(?P<sub>\d+))?"
)


@dataclass(frozen=True)
class LegalIdentifier:
    kind: str       # CASE | STATUTE | EXHIBIT
    canonical: str  # Normalized lookup key


def extract_legal_identifiers(text: str) -> List[LegalIdentifier]:
    """Extract deduplicated canonical legal identifiers from text."""
    raw = str(text or "")
    if not raw.strip():
        return []

    seen: Set[Tuple[str, str]] = set()
    found: List[LegalIdentifier] = []

    for year, code, num in extract_all_case_numbers(raw):
        canon = f"{year}{code}{num}"
        key = ("CASE", canon)
        if key not in seen:
            seen.add(key)
            found.append(LegalIdentifier(kind="CASE", canonical=canon))

    for m in _STATUTE_CITE_RE.finditer(raw):
        law = re.sub(r"\s+", "", m.group("law"))
        art = canonical_article(
            f"제{m.group('art')}조"
            + (f"의{m.group('sub')}" if m.group("sub") else "")
            + (f"제{m.group('para')}항" if m.group("para") else "")
        )
        canon = f"{law}:{art}"
        key = ("STATUTE", canon)
        if key not in seen:
            seen.add(key)
            found.append(LegalIdentifier(kind="STATUTE", canonical=canon))

    for m in _EXHIBIT_RE.finditer(raw):
        canon = f"{m.group('side')}제{m.group('num')}호증" + (f"의{m.group('sub')}" if m.group("sub") else "")
        key = ("EXHIBIT", canon)
        if key not in seen:
            seen.add(key)
            found.append(LegalIdentifier(kind="EXHIBIT", canonical=canon))

    return found


class IdentifierIndex:
    """SQLite-backed (or `:memory:`) inverted index for O(1) Tier 1 identifier pinning."""

    def __init__(self, conn: Optional[sqlite3.Connection] = None) -> None:
        self.conn = conn or sqlite3.connect(":memory:")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_identifiers (
                kind TEXT NOT NULL,
                canonical TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                PRIMARY KEY (kind, canonical, chunk_id)
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunk_id_lookup ON chunk_identifiers (kind, canonical)"
        )

    def index_chunk(self, chunk_id: str, file_id: str, text: str) -> List[LegalIdentifier]:
        idents = extract_legal_identifiers(text)
        if not idents:
            return []
        with self.conn:
            self.conn.executemany(
                "INSERT OR IGNORE INTO chunk_identifiers (kind, canonical, chunk_id, file_id) VALUES (?, ?, ?, ?)",
                [(ident.kind, ident.canonical, chunk_id, file_id) for ident in idents],
            )
        return idents

    def lookup(self, query_text: str) -> Dict[str, List[LegalIdentifier]]:
        """Return mapping of `chunk_id -> matched LegalIdentifiers` for exact Tier 1 hits."""
        idents = extract_legal_identifiers(query_text)
        if not idents:
            return {}
        matched: Dict[str, List[LegalIdentifier]] = defaultdict(list)
        for ident in idents:
            rows = self.conn.execute(
                "SELECT chunk_id FROM chunk_identifiers WHERE kind = ? AND canonical = ?",
                (ident.kind, ident.canonical),
            ).fetchall()
            for (chunk_id,) in rows:
                matched[str(chunk_id)].append(ident)
        return dict(matched)


def _content_and_bigram_terms(text: str) -> List[str]:
    base = list(bigram_tokens(text))
    # Add whitespace-normalized word tokens >= 2 chars for exact compound matching
    words = [w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", text or "")]
    return base + words


def bm25_score_chunks(
    query: str,
    chunks: Sequence[Dict[str, Any]],
    *,
    identifier_hits: Optional[Dict[str, List[LegalIdentifier]]] = None,
    k1: float = 1.5,
    b: float = 0.75,
    tier1_boost: float = 10.0,
) -> List[Dict[str, Any]]:
    """Score and rank chunks by Tier 1 identifier pinning + Tier 2 BM25 lexical similarity."""
    if not chunks:
        return []
    q_terms = set(_content_and_bigram_terms(query))
    doc_terms_list: List[Counter[str]] = []
    doc_lengths: List[int] = []
    df: Counter[str] = Counter()

    for ch in chunks:
        terms = _content_and_bigram_terms(str(ch.get("text") or ""))
        tf = Counter(terms)
        doc_terms_list.append(tf)
        doc_lengths.append(sum(tf.values()))
        for term in tf:
            df[term] += 1

    n_docs = len(chunks)
    avgdl = (sum(doc_lengths) / n_docs) if n_docs else 1.0
    id_hits = identifier_hits or {}

    scored: List[Dict[str, Any]] = []
    for idx, ch in enumerate(chunks):
        tf = doc_terms_list[idx]
        dl = doc_lengths[idx] or 1
        bm25 = 0.0
        for term in q_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            idf = math.log(1.0 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            denom = freq + k1 * (1.0 - b + b * (dl / max(avgdl, 1e-6)))
            bm25 += idf * (freq * (k1 + 1.0)) / denom

        cid = str(ch.get("chunk_id") or "")
        pinned = id_hits.get(cid, [])
        total = bm25 + (tier1_boost * len(pinned))
        scored.append({
            **ch,
            "tier1_pinned": bool(pinned),
            "tier1_identifiers": [f"{p.kind}:{p.canonical}" for p in pinned],
            "bm25_score": round(bm25, 4),
            "hybrid_score": round(total, 4),
        })

    scored.sort(key=lambda r: (-int(r["tier1_pinned"]), -r["hybrid_score"], str(r.get("chunk_id") or "")))
    return scored
