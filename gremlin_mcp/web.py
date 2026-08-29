from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import hashlib
import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Iterable, Mapping

from gremlin_mcp.router import route

WEB_SCHEMA = "GREMLIN_WEB_RESEARCH_V0_1"
WEB_VERSION = "0.1.0"
USER_AGENT = "GREMLIN-Research/0.1 (+https://github.com/AdrianLipa90/GREMLIN)"
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_MAX_BYTES = 1_000_000
MAX_LIMIT = 25


class WebAccessError(RuntimeError):
    pass


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commitment(domain: bytes, payload: Any) -> str:
    return hashlib.blake2b(domain + _canonical(payload), digest_size=32).hexdigest()


def _validate_host(hostname: str) -> None:
    host = hostname.strip().rstrip(".").lower()
    if not host:
        raise WebAccessError("URL hostname is required")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise WebAccessError("local hostnames are blocked")
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise WebAccessError(f"DNS resolution failed for {host}") from exc
    if not infos:
        raise WebAccessError(f"DNS produced no addresses for {host}")
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise WebAccessError(f"unparseable resolved address for {host}") from exc
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise WebAccessError(f"blocked non-public address for {host}: {ip}")


def validate_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(str(url).strip())
    if parsed.scheme.lower() != "https":
        raise WebAccessError("only HTTPS URLs are allowed")
    if parsed.username or parsed.password:
        raise WebAccessError("userinfo in URLs is blocked")
    if parsed.port not in (None, 443):
        raise WebAccessError("only HTTPS port 443 is allowed")
    if not parsed.hostname:
        raise WebAccessError("URL hostname is required")
    _validate_host(parsed.hostname)
    return urllib.parse.urlunsplit(parsed)


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        safe = validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, safe)


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_SafeRedirectHandler())


def _request_bytes(
    url: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_bytes: int = DEFAULT_MAX_BYTES,
    accept: str = "text/html,application/json,application/xml,text/xml,text/plain;q=0.9,*/*;q=0.1",
) -> tuple[bytes, dict[str, Any]]:
    safe = validate_url(url)
    timeout = float(timeout_s)
    limit = int(max_bytes)
    if not (0.1 <= timeout <= 60.0):
        raise ValueError("timeout_s must be in [0.1, 60]")
    if not (1 <= limit <= 8_000_000):
        raise ValueError("max_bytes must be in [1, 8000000]")
    request = urllib.request.Request(
        safe,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Encoding": "identity",
        },
        method="GET",
    )
    try:
        with _opener().open(request, timeout=timeout) as response:
            body = response.read(limit + 1)
            if len(body) > limit:
                raise WebAccessError("response exceeded max_bytes")
            content_type = response.headers.get_content_type().lower()
            charset = response.headers.get_content_charset() or "utf-8"
            meta = {
                "url": response.geturl(),
                "status": int(getattr(response, "status", 200)),
                "content_type": content_type,
                "charset": charset,
                "content_length": len(body),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
            return body, meta
    except urllib.error.HTTPError as exc:
        raise WebAccessError(f"HTTP {exc.code} for {safe}") from exc
    except urllib.error.URLError as exc:
        raise WebAccessError(f"network error for {safe}: {exc.reason}") from exc


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        elif tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "article", "section", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        elif tag in {"p", "li", "article", "section", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = " ".join(" ".join(self.parts).split())
        return raw.strip()


def fetch_url(
    url: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_chars: int = 120_000,
) -> dict[str, Any]:
    body, meta = _request_bytes(url, timeout_s=timeout_s, max_bytes=max_bytes)
    content_type = str(meta["content_type"])
    charset = str(meta["charset"])
    if content_type.startswith("text/html"):
        parser = _TextExtractor()
        parser.feed(body.decode(charset, errors="replace"))
        text = parser.text()
    elif (
        content_type.startswith("text/")
        or content_type in {"application/json", "application/xml", "application/atom+xml", "application/rss+xml"}
    ):
        text = body.decode(charset, errors="replace")
    else:
        raise WebAccessError(f"unsupported content type: {content_type}")
    clipped = text[: max(1, int(max_chars))]
    core = {
        "schema": "GREMLIN_WEB_FETCH_RECEIPT_V0_1",
        "requested_url": str(url),
        "resolved_url": meta["url"],
        "http_status": meta["status"],
        "content_type": content_type,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "text": clipped,
        "text_truncated": len(text) > len(clipped),
        "authority": _authority(),
    }
    core["receipt_commitment"] = _commitment(b"GREMLIN-WEB-FETCH/v0.1\0", core)
    return core


def _bounded_limit(limit: int) -> int:
    n = int(limit)
    if not (1 <= n <= MAX_LIMIT):
        raise ValueError(f"limit must be in 1..{MAX_LIMIT}")
    return n


def search_crossref(query: str, *, limit: int = 8) -> dict[str, Any]:
    n = _bounded_limit(limit)
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
        {"query.bibliographic": q, "rows": n, "select": "DOI,title,URL,author,published,container-title,type,score"}
    )
    body, meta = _request_bytes(url, accept="application/json")
    data = json.loads(body.decode(str(meta["charset"]), errors="strict"))
    items = []
    for row in data.get("message", {}).get("items", [])[:n]:
        title = next(iter(row.get("title") or []), "")
        container = next(iter(row.get("container-title") or []), "")
        authors = []
        for author in row.get("author") or []:
            name = " ".join(x for x in (author.get("given", ""), author.get("family", "")) if x).strip()
            if name:
                authors.append(name)
        date_parts = ((row.get("published") or {}).get("date-parts") or [[]])[0]
        published = "-".join(str(x) for x in date_parts) if date_parts else None
        doi = row.get("DOI")
        items.append(
            {
                "provider": "crossref",
                "title": title,
                "url": row.get("URL") or (f"https://doi.org/{doi}" if doi else None),
                "doi": doi,
                "authors": authors,
                "published": published,
                "container": container,
                "type": row.get("type"),
                "provider_score": row.get("score"),
            }
        )
    result = {
        "schema": "GREMLIN_WEB_SEARCH_RECEIPT_V0_1",
        "provider": "crossref",
        "query": q,
        "results": items,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "authority": _authority(),
    }
    result["receipt_commitment"] = _commitment(b"GREMLIN-WEB-SEARCH/v0.1\0", result)
    return result


def search_arxiv(query: str, *, limit: int = 8) -> dict[str, Any]:
    n = _bounded_limit(limit)
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f"all:{q}", "start": 0, "max_results": n, "sortBy": "relevance"}
    )
    body, meta = _request_bytes(url, accept="application/atom+xml,application/xml,text/xml")
    root = ET.fromstring(body)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items = []
    for entry in root.findall("a:entry", ns)[:n]:
        title = " ".join((entry.findtext("a:title", default="", namespaces=ns)).split())
        summary = " ".join((entry.findtext("a:summary", default="", namespaces=ns)).split())
        authors = [
            " ".join((node.findtext("a:name", default="", namespaces=ns)).split())
            for node in entry.findall("a:author", ns)
        ]
        links = {node.attrib.get("rel", "alternate"): node.attrib.get("href") for node in entry.findall("a:link", ns)}
        items.append(
            {
                "provider": "arxiv",
                "title": title,
                "url": links.get("alternate") or entry.findtext("a:id", default="", namespaces=ns),
                "authors": [x for x in authors if x],
                "published": entry.findtext("a:published", default=None, namespaces=ns),
                "updated": entry.findtext("a:updated", default=None, namespaces=ns),
                "summary": summary,
            }
        )
    result = {
        "schema": "GREMLIN_WEB_SEARCH_RECEIPT_V0_1",
        "provider": "arxiv",
        "query": q,
        "results": items,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "authority": _authority(),
    }
    result["receipt_commitment"] = _commitment(b"GREMLIN-WEB-SEARCH/v0.1\0", result)
    return result


class _DDGParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._active: dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        cls = attr.get("class") or ""
        if tag == "a" and "result__a" in cls:
            href = attr.get("href") or ""
            self._active = {"url": href, "title": "", "snippet": ""}
            self._capture_title = True
        elif self._active is not None and "result__snippet" in cls:
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title:
            self._capture_title = False
            if self._active is not None:
                self.results.append(self._active)
                self._active = None
        self._capture_snippet = False

    def handle_data(self, data: str) -> None:
        if self._active is None:
            return
        if self._capture_title:
            self._active["title"] += data
        elif self._capture_snippet:
            self._active["snippet"] += data


def _unwrap_ddg_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.endswith("duckduckgo.com"):
        q = urllib.parse.parse_qs(parsed.query)
        target = next(iter(q.get("uddg", [])), None)
        if target:
            return urllib.parse.unquote(target)
    return url


def search_duckduckgo(query: str, *, limit: int = 8) -> dict[str, Any]:
    n = _bounded_limit(limit)
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})
    body, meta = _request_bytes(url, accept="text/html")
    parser = _DDGParser()
    parser.feed(body.decode(str(meta["charset"]), errors="replace"))
    items = []
    for row in parser.results[:n]:
        target = _unwrap_ddg_url(row["url"])
        if target.startswith("http://"):
            target = "https://" + target[len("http://") :]
        if not target.startswith("https://"):
            continue
        items.append(
            {
                "provider": "duckduckgo",
                "title": " ".join(row["title"].split()),
                "url": target,
                "snippet": " ".join(row["snippet"].split()),
            }
        )
    result = {
        "schema": "GREMLIN_WEB_SEARCH_RECEIPT_V0_1",
        "provider": "duckduckgo",
        "query": q,
        "results": items,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "authority": _authority(),
    }
    result["receipt_commitment"] = _commitment(b"GREMLIN-WEB-SEARCH/v0.1\0", result)
    return result


def _normalized_title(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _dedupe(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        key = str(row.get("doi") or "").strip().lower()
        if not key:
            key = str(row.get("url") or "").split("#", 1)[0].rstrip("/").lower()
        if not key:
            key = _normalized_title(str(row.get("title") or ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def search_web(
    query: str,
    *,
    providers: Iterable[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
) -> dict[str, Any]:
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")
    provider_names = tuple(str(x).strip().lower() for x in providers)
    if not provider_names:
        raise ValueError("at least one provider is required")
    dispatch = {
        "crossref": search_crossref,
        "arxiv": search_arxiv,
        "duckduckgo": search_duckduckgo,
    }
    receipts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    for name in provider_names:
        fn = dispatch.get(name)
        if fn is None:
            errors.append({"provider": name, "error": "UNKNOWN_PROVIDER"})
            continue
        try:
            receipt = fn(q, limit=limit_per_provider)
        except Exception as exc:
            errors.append({"provider": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        receipts.append(receipt)
        rows.extend(receipt["results"])
    deduped = _dedupe(rows)
    core = {
        "schema": WEB_SCHEMA,
        "version": WEB_VERSION,
        "mode": "INTERNET_SEARCH_CANDIDATE",
        "query": q,
        "providers_requested": list(provider_names),
        "providers_completed": [x["provider"] for x in receipts],
        "provider_errors": errors,
        "results": deduped,
        "raw_result_count": len(rows),
        "deduped_result_count": len(deduped),
        "search_receipts": receipts,
        "authority": _authority(),
    }
    core["evidence_commitment"] = _commitment(b"GREMLIN-WEB-EVIDENCE/v0.1\0", core)
    return core


def research(
    query: str,
    *,
    providers: Iterable[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
) -> dict[str, Any]:
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")
    routing_payload = {
        "query": q,
        "task": "internet research source review",
        "evidence": {"requested": True, "provenance_required": True},
    }
    decision = route(routing_payload, max_species=max_species)
    evidence = search_web(q, providers=providers, limit_per_provider=limit_per_provider)
    core = {
        "schema": "GREMLIN_RESEARCH_ENGINE_V0_1",
        "version": WEB_VERSION,
        "query": q,
        "octopus": decision,
        "evidence": evidence,
        "status": "EVIDENCE_READY" if evidence["results"] else "NO_EVIDENCE",
        "next_stage": "SPECIALIST_ANALYSIS_THEN_BELZEBUB_SYNTHESIS",
        "authority": _authority(),
    }
    core["research_commitment"] = _commitment(b"GREMLIN-RESEARCH/v0.1\0", core)
    return core
