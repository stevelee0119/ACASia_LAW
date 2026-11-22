"""4-Tier Hybrid Legal Retriever: Identifier Pinning + BM25 + Dense RRF + Reranker & Applicability (P1 PR-08).

Gracefully degrades to `LEXICAL_ONLY` when no embedding or reranker model is configured.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import ipaddress
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from packages.rag_engine.applicability_filter import annotate_applicability
from packages.rag_engine.identifier_index import IdentifierIndex, LegalIdentifier, bm25_score_chunks


def _split_validated_http_endpoint(endpoint: str) -> Optional[Tuple[str, str]]:
    """Validate an HTTP(S) endpoint against SSRF sinks and split into (base_url, path)."""
    raw = (endpoint or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.hostname or parsed.username or parsed.password:
        return None
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return None
    except ValueError:
        pass
    port_part = f":{parsed.port}" if parsed.port else ""
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    base_url = f"{parsed.scheme.lower()}://{host}{port_part}"
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return base_url, path


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


class HttpEmbeddingAdapter(EmbeddingAdapter):
    """HTTP client adapter for OpenAI-compatible /embeddings endpoints."""

    name = "http_embedding"

    def __init__(
        self,
        endpoint: str,
        *,
        model: str = "",
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        post_fn: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.endpoint = (endpoint or "").strip()
        self.model = (model or "").strip()
        self._api_key = (api_key or "").strip() or None
        self.timeout = max(0.5, float(timeout))
        self._post_fn = post_fn
        split = _split_validated_http_endpoint(self.endpoint)
        self._base_url, self._path = split if split else ("", "")
        self.available = bool(split)

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not self.available or not texts:
            return []
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: Dict[str, Any] = {"input": list(texts)}
        if self.model:
            payload["model"] = self.model
        if self._post_fn is not None:
            resp = self._post_fn(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
        else:
            import httpx
            with httpx.Client(base_url=self._base_url, timeout=self.timeout) as client:
                resp = client.post(self._path, json=payload, headers=headers)
        if getattr(resp, "status_code", 200) >= 400:
            raise RuntimeError(f"EMBEDDING_HTTP_{getattr(resp, 'status_code', 500)}")
        data = resp.json()
        items = data.get("data") if isinstance(data, dict) else None
        if isinstance(items, list):
            ordered = sorted(items, key=lambda x: int(x.get("index", 0)) if isinstance(x, dict) else 0)
            return [list(map(float, x.get("embedding") or [])) for x in ordered if isinstance(x, dict)]
        if isinstance(data, dict) and isinstance(data.get("embeddings"), list):
            return [list(map(float, v)) for v in data["embeddings"]]
        return []


class HttpRerankerAdapter(RerankerAdapter):
    """HTTP client adapter for /rerank endpoints (Cohere/BGE/Jina compatible)."""

    name = "http_reranker"

    def __init__(
        self,
        endpoint: str,
        *,
        model: str = "",
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        post_fn: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.endpoint = (endpoint or "").strip()
        self.model = (model or "").strip()
        self._api_key = (api_key or "").strip() or None
        self.timeout = max(0.5, float(timeout))
        self._post_fn = post_fn
        split = _split_validated_http_endpoint(self.endpoint)
        self._base_url, self._path = split if split else ("", "")
        self.available = bool(split)

    def score(self, query: str, passages: Sequence[str]) -> List[float]:
        if not self.available or not passages:
            return [0.0 for _ in passages]
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: Dict[str, Any] = {"query": query, "documents": list(passages)}
        if self.model:
            payload["model"] = self.model
        if self._post_fn is not None:
            resp = self._post_fn(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
        else:
            import httpx
            with httpx.Client(base_url=self._base_url, timeout=self.timeout) as client:
                resp = client.post(self._path, json=payload, headers=headers)
        if getattr(resp, "status_code", 200) >= 400:
            raise RuntimeError(f"RERANKER_HTTP_{getattr(resp, 'status_code', 500)}")
        data = resp.json()
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return [0.0 for _ in passages]
        scores = [0.0 for _ in passages]
        for idx, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            pos = int(item.get("index", idx))
            if 0 <= pos < len(scores):
                scores[pos] = float(item.get("relevance_score", item.get("score", 0.0)) or 0.0)
        return scores


def build_rag_adapters_from_env(
    *,
    allow_network: bool = True,
) -> Tuple[Optional[EmbeddingAdapter], Optional[RerankerAdapter], Dict[str, Any]]:
    """Build configured HTTP embedding & reranker adapters from environment settings."""
    import os

    mode = (os.getenv("LV_RAG_RETRIEVAL_MODE") or "auto").strip().lower()
    emb_endpoint = (os.getenv("LV_RAG_EMBEDDING_ENDPOINT") or "").strip()
    emb_model = (os.getenv("LV_EMBEDDING_MODEL") or "").strip()
    emb_key = (os.getenv("LV_RAG_EMBEDDING_API_KEY") or "").strip() or None
    rerank_endpoint = (os.getenv("LV_RAG_RERANKER_ENDPOINT") or "").strip()
    rerank_model = (os.getenv("LV_RERANKER_MODEL") or "").strip()
    rerank_key = (os.getenv("LV_RAG_RERANKER_API_KEY") or "").strip() or None

    if mode in ("off", "lexical", "lexical_only"):
        return None, None, {"configured_mode": mode, "fallback_reason": "LEXICAL_MODE_CONFIGURED"}
    if not allow_network:
        return None, None, {"configured_mode": mode, "fallback_reason": "NETWORK_DISABLED"}

    emb = HttpEmbeddingAdapter(emb_endpoint, model=emb_model, api_key=emb_key) if emb_endpoint else None
    rerank = HttpRerankerAdapter(rerank_endpoint, model=rerank_model, api_key=rerank_key) if rerank_endpoint else None
    reasons: List[str] = []
    if not emb_endpoint:
        reasons.append("EMBEDDING_ENDPOINT_UNCONFIGURED")
    if not rerank_endpoint:
        reasons.append("RERANKER_ENDPOINT_UNCONFIGURED")
    return emb, rerank, {"configured_mode": mode, "fallback_reasons": reasons}


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
    chunk_vectors: Optional[Dict[str, List[float]]] = None,
    target_date: Optional[str] = None,
    case_type: Optional[str] = None,
    exclude_inapplicable: bool = False,
    top_k: int = 10,
    rerank_top_n: int = 30,
) -> Dict[str, Any]:
    """Execute 4-tier hybrid retrieval and return ranked chunks with retrieval mode telemetry."""
    if not chunks:
        return {
            "retrieval_mode": "EMPTY",
            "retrieval_warnings": [],
            "chunks": [],
            "computed_chunk_vectors": {},
            "retrieval_telemetry": {
                "effective_mode": "LEXICAL_ONLY",
                "embedding_requests": 0,
                "embedding_successes": 0,
                "embedding_failures": 0,
                "reranker_requests": 0,
                "reranker_successes": 0,
                "reranker_failures": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "fallback_reasons": ["EMPTY_CHUNKS"],
            },
        }

    id_hits: Dict[str, List[LegalIdentifier]] = identifier_index.lookup(query) if identifier_index else {}
    lexical_ranked = bm25_score_chunks(query, chunks, identifier_hits=id_hits)
    lex_order = [str(c.get("chunk_id") or "") for c in lexical_ranked]

    ranked_lists: List[List[str]] = [lex_order]
    dense_scores: Dict[str, float] = {}
    retrieval_mode = "LEXICAL_ONLY"
    retrieval_warnings: List[str] = []
    computed_chunk_vectors: Dict[str, List[float]] = {}
    emb_requests = 0
    emb_successes = 0
    emb_failures = 0
    rerank_requests = 0
    rerank_successes = 0
    rerank_failures = 0
    cache_hits = 0
    cache_misses = 0
    cached_map = dict(chunk_vectors or {})

    emb = embedding_adapter or NullEmbeddingAdapter()
    if emb.available:
        try:
            missing_chunks: List[Dict[str, Any]] = []
            for ch in chunks:
                cid = str(ch.get("chunk_id") or "")
                if cid in cached_map and cached_map[cid]:
                    cache_hits += 1
                else:
                    cache_misses += 1
                    missing_chunks.append(ch)
            texts_to_embed = [query] + [str(ch.get("text") or "") for ch in missing_chunks]
            emb_requests += 1
            vecs = emb.embed(texts_to_embed)
            if len(vecs) == len(texts_to_embed) and vecs[0]:
                emb_successes += 1
                q_vec = vecs[0]
                for ch, d_vec in zip(missing_chunks, vecs[1:]):
                    cid = str(ch.get("chunk_id") or "")
                    if d_vec:
                        cached_map[cid] = d_vec
                        computed_chunk_vectors[cid] = d_vec
                for ch in chunks:
                    cid = str(ch.get("chunk_id") or "")
                    d_vec = cached_map.get(cid)
                    if d_vec:
                        dense_scores[cid] = round(cosine_similarity(q_vec, d_vec), 4)
                if dense_scores:
                    dense_order = sorted(dense_scores, key=lambda cid: (-dense_scores[cid], cid))
                    ranked_lists.append(dense_order)
                    retrieval_mode = "RRF_DENSE"
            else:
                emb_failures += 1
                retrieval_warnings.append("EMBEDDING_FALLBACK:EMPTY_OR_MISMATCHED_VECTORS")
        except Exception as exc:
            emb_failures += 1
            retrieval_warnings.append(f"EMBEDDING_FALLBACK:{type(exc).__name__}")
            dense_scores.clear()
            retrieval_mode = "LEXICAL_ONLY"

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
        try:
            head = fused[:max(1, rerank_top_n)]
            tail = fused[max(1, rerank_top_n):]
            rerank_requests += 1
            r_scores = reranker.score(query, [str(c.get("text") or "") for c in head])
            if len(r_scores) == len(head):
                rerank_successes += 1
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
                retrieval_mode = "RRF_RERANK" if emb_successes > 0 else "LEXICAL_RERANK"
            else:
                rerank_failures += 1
                retrieval_warnings.append("RERANKER_FALLBACK:SCORE_COUNT_MISMATCH")
        except Exception as exc:
            rerank_failures += 1
            retrieval_warnings.append(f"RERANKER_FALLBACK:{type(exc).__name__}")

    annotated = annotate_applicability(
        fused,
        target_date=target_date,
        case_type=case_type,
        exclude_inapplicable=exclude_inapplicable,
    )
    effective_mode = (
        "HYBRID_RERANK" if (emb_successes > 0 and rerank_successes > 0)
        else "HYBRID_DENSE" if emb_successes > 0
        else "LEXICAL_RERANK" if rerank_successes > 0
        else "LEXICAL_ONLY"
    )
    return {
        "retrieval_mode": retrieval_mode,
        "retrieval_warnings": retrieval_warnings,
        "chunks": annotated[:max(1, top_k)],
        "computed_chunk_vectors": computed_chunk_vectors,
        "retrieval_telemetry": {
            "effective_mode": effective_mode,
            "embedding_requests": emb_requests,
            "embedding_successes": emb_successes,
            "embedding_failures": emb_failures,
            "reranker_requests": rerank_requests,
            "reranker_successes": rerank_successes,
            "reranker_failures": rerank_failures,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "fallback_reasons": list(retrieval_warnings),
        },
    }
