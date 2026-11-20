"""4-Tier Hybrid Legal Retriever: Identifier Pinning + BM25 + Dense RRF + Reranker & Applicability (P1 PR-08).

Gracefully degrades to `LEXICAL_ONLY` when no embedding or reranker model is configured.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from packages.rag_engine.applicability_filter import annotate_applicability
from packages.rag_engine.identifier_index import IdentifierIndex, LegalIdentifier, bm25_score_chunks


class EmbeddingAdapter(ABC):
    name = "base"
    available = False

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Return embedding vectors aligned to `texts`."""


class NullEmbeddingAdapter(EmbeddingAdapter):
    name = "null"
    available = False

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        return []


class CallableEmbeddingAdapter(EmbeddingAdapter):
    def __init__(self, fn: Callable[[Sequence[str]], List[List[float]]], *, name: str = "custom") -> None:
        self._fn = fn
        self.name = name
        self.available = True

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        return self._fn(texts)


class RerankerAdapter(ABC):
    name = "base"
    available = False

    @abstractmethod
    def score(self, query: str, passages: Sequence[str]) -> List[float]:
        """Return relevance scores aligned to `passages`."""


class NullRerankerAdapter(RerankerAdapter):
    name = "null"
    available = False

    def score(self, query: str, passages: Sequence[str]) -> List[float]:
        return [0.0 for _ in passages]


class CallableRerankerAdapter(RerankerAdapter):
    def __init__(self, fn: Callable[[str, Sequence[str]], List[float]], *, name: str = "custom") -> None:
        self._fn = fn
        self.name = name
        self.available = True

    def score(self, query: str, passages: Sequence[str]) -> List[float]:
        return self._fn(query, passages)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return dot / (na * nb)


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]],
    *,
    k: int = 60,
) -> Dict[str, float]:
    """Compute Reciprocal Rank Fusion (RRF) scores across multiple ranked chunk_id lists."""
    scores: Dict[str, float] = {}
    for rlist in ranked_lists:
        for rank_0, cid in enumerate(rlist):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank_0 + 1)
    return scores


def retrieve_hybrid_chunks(
    query: str,
    chunks: Sequence[Dict[str, Any]],
    *,
    identifier_index: Optional[IdentifierIndex] = None,
    embedding_adapter: Optional[EmbeddingAdapter] = None,
    reranker_adapter: Optional[RerankerAdapter] = None,
    target_date: Optional[str] = None,
    case_type: Optional[str] = None,
    exclude_inapplicable: bool = False,
    top_k: int = 10,
    rerank_top_n: int = 30,
) -> Dict[str, Any]:
    """Execute 4-tier hybrid retrieval and return ranked chunks with retrieval mode telemetry."""
    if not chunks:
        return {"retrieval_mode": "EMPTY", "chunks": []}

    id_hits: Dict[str, List[LegalIdentifier]] = identifier_index.lookup(query) if identifier_index else {}
    lexical_ranked = bm25_score_chunks(query, chunks, identifier_hits=id_hits)
    lex_order = [str(c.get("chunk_id") or "") for c in lexical_ranked]

    ranked_lists: List[List[str]] = [lex_order]
    dense_scores: Dict[str, float] = {}
    retrieval_mode = "LEXICAL_ONLY"

    emb = embedding_adapter or NullEmbeddingAdapter()
    if emb.available:
        texts = [str(c.get("text") or "") for c in chunks]
        vecs = emb.embed([query] + texts)
        if len(vecs) == len(texts) + 1:
            q_vec, doc_vecs = vecs[0], vecs[1:]
            for ch, d_vec in zip(chunks, doc_vecs):
                cid = str(ch.get("chunk_id") or "")
                dense_scores[cid] = round(cosine_similarity(q_vec, d_vec), 4)
            dense_order = sorted(dense_scores, key=lambda cid: (-dense_scores[cid], cid))
            ranked_lists.append(dense_order)
            retrieval_mode = "RRF_DENSE"

    rrf_scores = reciprocal_rank_fusion(ranked_lists)
    by_id = {str(c.get("chunk_id") or ""): c for c in lexical_ranked}

    fused: List[Dict[str, Any]] = []
    for cid, ch in by_id.items():
        fused.append({
            **ch,
            "dense_score": dense_scores.get(cid),
            "rrf_score": round(rrf_scores.get(cid, 0.0), 6),
        })

    # Tier 1 exact identifier pins always stay at the top, followed by RRF score
    fused.sort(key=lambda r: (-int(bool(r.get("tier1_pinned"))), -r["rrf_score"], str(r.get("chunk_id") or "")))

    reranker = reranker_adapter or NullRerankerAdapter()
    if reranker.available and fused:
        head = fused[:max(1, rerank_top_n)]
        tail = fused[max(1, rerank_top_n):]
        r_scores = reranker.score(query, [str(c.get("text") or "") for c in head])
        if len(r_scores) == len(head):
            for item, sc in zip(head, r_scores):
                item["rerank_score"] = round(float(sc), 4)
            head.sort(
                key=lambda r: (
                    -int(bool(r.get("tier1_pinned"))),
                    -float(r.get("rerank_score") or 0.0),
                    -float(r.get("rrf_score") or 0.0),
                )
            )
            fused = head + tail
            retrieval_mode = "RRF_RERANK"

    annotated = annotate_applicability(
        fused,
        target_date=target_date,
        case_type=case_type,
        exclude_inapplicable=exclude_inapplicable,
    )
    return {
        "retrieval_mode": retrieval_mode,
        "chunks": annotated[:max(1, top_k)],
    }
