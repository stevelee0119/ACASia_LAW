"""제10장 학술자료 Source Adapter.

AcademicSourceAdapter
 ├─ KCIAdapter            (국내 법률논문 우선)
 ├─ OpenAlexAdapter
 ├─ SemanticScholarAdapter
 └─ CrossrefAdapter
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from packages.common.enums import AdapterStatus

from .base import AdapterResponse, SourceAdapter


class AcademicSourceAdapter(SourceAdapter):
    kind = "academic"

    def search_work(self, title: str, *, authors: Optional[List[str]] = None, year: Optional[int] = None,
                    doi: Optional[str] = None) -> AdapterResponse:
        return self.search(title, authors=authors, year=year, doi=doi)

    def _http_get_with_retry(
        self,
        query: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 2,
        base_backoff: float = 0.15,
        allow_404: bool = False,
    ) -> Tuple[Optional[Any], Optional[AdapterResponse], Dict[str, Any]]:
        """Retry transient academic API failures (429/5xx/timeout) and separate failure causes."""
        attempts = 0
        last_code: Optional[int] = None
        for attempt in range(max_retries + 1):
            attempts += 1
            try:
                response = self._http_get(url, params=params, headers=headers)
            except Exception as exc:
                err_resp = self._transport_unavailable(query, exc)
                retryable = err_resp.status in (AdapterStatus.TIMEOUT, AdapterStatus.RATE_LIMITED, AdapterStatus.ERROR)
                cause = (
                    "TIMEOUT" if err_resp.status == AdapterStatus.TIMEOUT
                    else "RATE_LIMITED" if err_resp.status == AdapterStatus.RATE_LIMITED
                    else "TRANSPORT_ERROR"
                )
                if retryable and attempt < max_retries:
                    time.sleep(min(2.0, base_backoff * (2 ** attempt)))
                    continue
                err_resp.diagnostics = {
                    "attempts": attempts,
                    "error_cause": cause,
                    "error_type": type(exc).__name__,
                    "retryable": retryable,
                }
                return None, err_resp, err_resp.diagnostics

            code = int(getattr(response, "status_code", 0) or 0)
            last_code = code
            if code == 404 and allow_404:
                return response, None, {"attempts": attempts, "http_status": code, "error_cause": "NOT_FOUND"}
            if 200 <= code < 300:
                return response, None, {"attempts": attempts, "http_status": code, "error_cause": None}

            retryable = code in (408, 429) or (500 <= code < 600)
            if retryable and attempt < max_retries:
                retry_after = None
                try:
                    raw_ra = (getattr(response, "headers", None) or {}).get("Retry-After")
                    if raw_ra is not None:
                        retry_after = min(2.0, max(0.0, float(raw_ra)))
                except (TypeError, ValueError):
                    retry_after = None
                time.sleep(retry_after if retry_after is not None else min(2.0, base_backoff * (2 ** attempt)))
                continue

            if code == 429:
                diag = {"attempts": attempts, "http_status": code, "error_cause": "RATE_LIMITED", "retryable": True}
                return None, self._unavailable(query, AdapterStatus.RATE_LIMITED, "요청 한도 초과", diagnostics=diag), diag
            if 500 <= code < 600:
                diag = {"attempts": attempts, "http_status": code, "error_cause": "UPSTREAM_5XX", "retryable": True}
                return None, self._unavailable(query, AdapterStatus.ERROR, f"HTTP {code}", diagnostics=diag), diag
            diag = {"attempts": attempts, "http_status": code, "error_cause": "HTTP_4XX", "retryable": False}
            return None, self._unavailable(query, AdapterStatus.ERROR, f"HTTP {code}", diagnostics=diag), diag

        diag = {"attempts": attempts, "http_status": last_code, "error_cause": "UNKNOWN_ERROR", "retryable": False}
        return None, self._unavailable(query, AdapterStatus.ERROR, "조회를 수행하지 못했다", diagnostics=diag), diag


class KCIAdapter(AcademicSourceAdapter):
    name = "kci"
    requires_key = True
    key_env = "LV_KCI_KEY"
    homepage = "https://www.kci.go.kr/"
    ENDPOINT = "https://open.kci.go.kr/po/openapi/openApiSearch.kci"

    @property
    def api_key(self) -> Optional[str]:
        return self.settings.kci_key

    def search(self, query: str, **kwargs: Any) -> AdapterResponse:
        status = self.status()
        if status != AdapterStatus.READY:
            return self._unavailable(query, status, "KCI API Key가 없어 해당 항목은 UNVERIFIED로 표시한다.", diagnostics={"error_cause": str(status)})
        response, err_resp, diag = self._http_get_with_retry(
            query,
            self.ENDPOINT,
            params={"apiCode": "articleSearch", "key": self.api_key, "title": query, "displayCount": 10},
        )
        if err_resp is not None or response is None:
            return err_resp  # type: ignore[return-value]
        body = response.text

        records = _parse_kci_xml(body)
        return AdapterResponse(
            AdapterStatus.READY,
            records,
            self._record(query, AdapterStatus.READY, payload={"body_len": len(body)}, url=self.ENDPOINT,
                         used_fields=["title", "authors", "year", "journal"]),
            diagnostics=diag,
        )


class OpenAlexAdapter(AcademicSourceAdapter):
    name = "openalex"
    requires_key = False
    homepage = "https://developers.openalex.org/"
    ENDPOINT = "https://api.openalex.org/works"

    def search(self, query: str, **kwargs: Any) -> AdapterResponse:
        status = self.status()
        if status != AdapterStatus.READY:
            return self._unavailable(query, status, "네트워크 비활성", diagnostics={"error_cause": str(status)})
        doi = kwargs.get("doi")
        params: Dict[str, Any] = {"per-page": 5}
        if doi:
            params["filter"] = f"doi:{doi}"
        else:
            params["search"] = query
        response, err_resp, diag = self._http_get_with_retry(
            query,
            self.ENDPOINT,
            params=params,
            headers={"User-Agent": "legal-verifier/0.2"},
        )
        if err_resp is not None or response is None:
            return err_resp  # type: ignore[return-value]
        try:
            payload = response.json()
        except Exception as exc:
            resp = self._transport_unavailable(query, exc)
            resp.diagnostics = {"attempts": diag.get("attempts", 1), "error_cause": "INVALID_JSON", "retryable": False}
            return resp

        records = []
        for item in (payload.get("results") or [])[:5]:
            records.append(
                {
                    "title": item.get("title"),
                    "year": item.get("publication_year"),
                    "doi": (item.get("doi") or "").replace("https://doi.org/", "") or None,
                    "authors": [
                        a.get("author", {}).get("display_name")
                        for a in (item.get("authorships") or [])
                        if a.get("author")
                    ],
                    "journal": ((item.get("primary_location") or {}).get("source") or {}).get("display_name"),
                    "id": item.get("id"),
                }
            )
        return AdapterResponse(
            AdapterStatus.READY,
            records,
            self._record(query, AdapterStatus.READY, payload=payload, url=self.ENDPOINT,
                         used_fields=["title", "publication_year", "doi", "authorships"]),
            diagnostics=diag,
        )


class SemanticScholarAdapter(AcademicSourceAdapter):
    name = "semantic_scholar"
    requires_key = False
    homepage = "https://www.semanticscholar.org/product/api"
    ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"

    @property
    def api_key(self) -> Optional[str]:
        return self.settings.semantic_scholar_key

    def search(self, query: str, **kwargs: Any) -> AdapterResponse:
        status = self.status()
        if status != AdapterStatus.READY:
            return self._unavailable(query, status, "네트워크 비활성", diagnostics={"error_cause": str(status)})
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        response, err_resp, diag = self._http_get_with_retry(
            query,
            self.ENDPOINT,
            params={"query": query, "limit": 5, "fields": "title,year,authors,venue,externalIds"},
            headers=headers,
            base_backoff=0.15 if self.api_key else 0.05,
        )
        if err_resp is not None or response is None:
            return err_resp  # type: ignore[return-value]
        try:
            payload = response.json()
        except Exception as exc:
            resp = self._transport_unavailable(query, exc)
            resp.diagnostics = {"attempts": diag.get("attempts", 1), "error_cause": "INVALID_JSON", "retryable": False}
            return resp

        records = [
            {
                "title": item.get("title"),
                "year": item.get("year"),
                "authors": [a.get("name") for a in (item.get("authors") or [])],
                "journal": item.get("venue"),
                "doi": (item.get("externalIds") or {}).get("DOI"),
            }
            for item in (payload.get("data") or [])
        ]
        return AdapterResponse(
            AdapterStatus.READY,
            records,
            self._record(query, AdapterStatus.READY, payload=payload, url=self.ENDPOINT,
                         used_fields=["title", "year", "authors", "venue"]),
            diagnostics=diag,
        )


class CrossrefAdapter(AcademicSourceAdapter):
    name = "crossref"
    requires_key = False
    homepage = "https://www.crossref.org/documentation/retrieve-metadata/rest-api/"
    ENDPOINT = "https://api.crossref.org/works"

    def search(self, query: str, **kwargs: Any) -> AdapterResponse:
        status = self.status()
        if status != AdapterStatus.READY:
            return self._unavailable(query, status, "네트워크 비활성", diagnostics={"error_cause": str(status)})
        doi = kwargs.get("doi")
        url = f"{self.ENDPOINT}/{doi}" if doi else self.ENDPOINT
        params = None if doi else {"query.bibliographic": query, "rows": 5}
        headers = {"User-Agent": f"legal-verifier/0.2 (mailto:{self.settings.crossref_mailto or 'unknown'})"}
        response, err_resp, diag = self._http_get_with_retry(
            query,
            url,
            params=params,
            headers=headers,
            allow_404=True,
        )
        if err_resp is not None or response is None:
            return err_resp  # type: ignore[return-value]
        if response.status_code == 404:
            return AdapterResponse(
                AdapterStatus.READY, [], self._record(query, AdapterStatus.READY, payload={"found": False}, url=url),
                "DOI를 찾지 못했다",
                diagnostics=diag,
            )
        try:
            payload = response.json()
        except Exception as exc:
            resp = self._transport_unavailable(query, exc)
            resp.diagnostics = {"attempts": diag.get("attempts", 1), "error_cause": "INVALID_JSON", "retryable": False}
            return resp

        message = payload.get("message", {})
        items = message.get("items") if isinstance(message.get("items"), list) else [message]
        records = []
        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            date_parts = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
            records.append(
                {
                    "title": (item.get("title") or [None])[0],
                    "year": date_parts[0] if date_parts else None,
                    "authors": [
                        f"{a.get('family', '')} {a.get('given', '')}".strip() for a in (item.get("author") or [])
                    ],
                    "journal": (item.get("container-title") or [None])[0],
                    "doi": item.get("DOI"),
                }
            )
        return AdapterResponse(
            AdapterStatus.READY,
            records,
            self._record(query, AdapterStatus.READY, payload=payload, url=url,
                         used_fields=["title", "issued", "author", "DOI"]),
            diagnostics=diag,
        )


def _parse_kci_xml(body: str) -> List[Dict[str, Any]]:
    """KCI OpenAPI는 XML을 반환한다. 외부 엔티티를 차단하고 파싱한다."""
    try:
        from lxml import etree

        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        root = etree.fromstring(body.encode("utf-8"), parser=parser)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for record in root.iter("record"):
        def _text(tag: str) -> Optional[str]:
            el = record.find(f".//{tag}")
            return el.text.strip() if el is not None and el.text else None

        authors = [a.text.strip() for a in record.iter("author-name") if a.text]
        out.append(
            {
                "title": _text("article-title"),
                "year": int(_text("pub-year") or 0) or None,
                "authors": authors,
                "journal": _text("journal-name"),
                "doi": _text("doi"),
            }
        )
    return out
