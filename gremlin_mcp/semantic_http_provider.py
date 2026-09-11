from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from typing import Any, Mapping, Sequence

from gremlin_mcp.research_provenance import verify_source_receipt
from gremlin_mcp.semantic_evidence import build_classification
from gremlin_mcp.web import WebAccessError, validate_url

SCHEMA = "GREMLIN_HTTPS_SEMANTIC_PROVIDER_V0_1"
VERSION = "0.1.0"
_RETRYABLE_HTTP = frozenset({408, 425, 429, 500, 502, 503, 504})
_REMOTE_CLASSIFICATION_KEYS = frozenset({"source_id", "source_family", "excerpt", "stance", "confidence"})


class SemanticProviderError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("semantic HTTP provider data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _bounded_number(value: Any, field: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number in [{minimum}, {maximum}]")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{field} must be a finite number in [{minimum}, {maximum}]")
    return number


def _bounded_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer in [{minimum}, {maximum}]")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer in [{minimum}, {maximum}]")
    return value


def _reject_unknown_keys(value: Mapping[Any, Any], allowed: frozenset[str], field: str) -> None:
    unknown = [key for key in value if not isinstance(key, str) or key not in allowed]
    if unknown:
        raise SemanticProviderError(f"{field} contains unsupported keys: {unknown}")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        safe = validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, safe)


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_SafeRedirectHandler())


def _backoff(attempt: int) -> float:
    return min(2.0, 0.25 * (2**attempt))


def _post_json(
    endpoint: str,
    *,
    payload: Mapping[str, Any],
    bearer_token: str,
    timeout_s: float,
    max_response_bytes: int,
    retries: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(endpoint, str):
        raise ValueError("endpoint must be a string")
    safe = validate_url(endpoint)
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    token = _nonempty_text(bearer_token, "bearer_token")
    if "\r" in token or "\n" in token:
        raise ValueError("bearer_token must not contain CR or LF")
    timeout = _bounded_number(timeout_s, "timeout_s", minimum=0.1, maximum=60.0)
    limit = _bounded_int(max_response_bytes, "max_response_bytes", minimum=1, maximum=2_000_000)
    retry_count = _bounded_int(retries, "retries", minimum=0, maximum=5)

    body = _canonical(payload)
    request_commitment = _commit(b"GREMLIN-SEMANTIC-HTTPS-REQUEST/v0.1", payload)
    for attempt in range(retry_count + 1):
        request = urllib.request.Request(
            safe,
            data=body,
            headers={
                "User-Agent": "GREMLIN-SemanticProvider/0.1",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
                "Accept-Encoding": "identity",
            },
            method="POST",
        )
        try:
            with _opener().open(request, timeout=timeout) as response:
                raw = response.read(limit + 1)
                if len(raw) > limit:
                    raise SemanticProviderError("semantic provider response exceeded max_response_bytes")
                content_type = response.headers.get_content_type().lower()
                if content_type != "application/json":
                    raise SemanticProviderError(
                        f"semantic provider must return application/json, got {content_type}"
                    )
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise SemanticProviderError("semantic provider returned invalid UTF-8 JSON") from exc
                if not isinstance(parsed, dict):
                    raise SemanticProviderError("semantic provider JSON root must be an object")
                status = getattr(response, "status", 200)
                if isinstance(status, bool) or not isinstance(status, int):
                    raise SemanticProviderError("semantic provider HTTP status must be an integer")
                final_url = response.geturl()
                if not isinstance(final_url, str):
                    raise SemanticProviderError("semantic provider response URL must be a string")
                final_url = validate_url(final_url)
                meta = {
                    "schema": SCHEMA,
                    "version": VERSION,
                    "endpoint": final_url,
                    "http_status": status,
                    "response_bytes": len(raw),
                    "network_attempts": attempt + 1,
                    "request_commitment": request_commitment,
                    "response_commitment": _commit(
                        b"GREMLIN-SEMANTIC-HTTPS-RESPONSE/v0.1",
                        parsed,
                    ),
                    "authentication": "BEARER_TOKEN_FROM_ENV_NOT_RECORDED",
                    "integrity_scope": "LOCAL_UNKEYED_COMMITMENTS_NOT_REMOTE_IDENTITY_SIGNATURE",
                }
                meta["transport_receipt_commitment"] = _commit(
                    b"GREMLIN-SEMANTIC-HTTPS-TRANSPORT/v0.1",
                    meta,
                )
                return parsed, meta
        except urllib.error.HTTPError as exc:
            if exc.code in _RETRYABLE_HTTP and attempt < retry_count:
                time.sleep(_backoff(attempt))
                continue
            raise SemanticProviderError(
                f"semantic provider HTTP {exc.code} after {attempt + 1} attempt(s)"
            ) from exc
        except WebAccessError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            if attempt < retry_count:
                time.sleep(_backoff(attempt))
                continue
            reason = getattr(exc, "reason", str(exc))
            raise SemanticProviderError(
                f"semantic provider network error after {attempt + 1} attempt(s): {reason}"
            ) from exc

    raise SemanticProviderError("semantic provider request exhausted retries")


class HTTPSemanticEvidenceProducer:
    """Vendor-neutral external JSON semantic classifier.

    The remote service only proposes source stance, excerpt, family metadata and confidence.
    GREMLIN locally constructs and verifies all classification receipts. Remote output never
    receives execution, write or canon authority.
    """

    mode = "EXTERNAL_HTTPS_JSON_PROVIDER"

    def __init__(
        self,
        *,
        endpoint: str,
        secret_env: str,
        producer_id: str,
        producer_version: str,
        model_id: str,
        timeout_s: float = 20.0,
        max_response_bytes: int = 1_000_000,
        retries: int = 2,
    ) -> None:
        self.endpoint = validate_url(_nonempty_text(endpoint, "endpoint"))
        self.secret_env = _nonempty_text(secret_env, "secret_env")
        self.producer_id = _nonempty_text(producer_id, "producer_id")
        self.producer_version = _nonempty_text(producer_version, "producer_version")
        self.model_id = _nonempty_text(model_id, "model_id")
        self.timeout_s = _bounded_number(timeout_s, "timeout_s", minimum=0.1, maximum=60.0)
        self.max_response_bytes = _bounded_int(
            max_response_bytes,
            "max_response_bytes",
            minimum=1,
            maximum=2_000_000,
        )
        self.retries = _bounded_int(retries, "retries", minimum=0, maximum=5)
        self._transport_receipt: dict[str, Any] | None = None

    def _token(self) -> str:
        token = os.environ.get(self.secret_env)
        if token is None or not token.strip():
            raise SemanticProviderError(
                f"semantic provider credential is missing from environment variable {self.secret_env}"
            )
        token = token.strip()
        if "\r" in token or "\n" in token:
            raise SemanticProviderError("semantic provider credential contains invalid CR/LF characters")
        return token

    def classify(
        self,
        *,
        claim_id: str,
        source_receipts: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        claim = _nonempty_text(claim_id, "claim_id")
        if isinstance(source_receipts, (str, bytes, Mapping)):
            raise ValueError("source_receipts must be a sequence of objects")
        try:
            raw_receipts = list(source_receipts)
        except TypeError as exc:
            raise ValueError("source_receipts must be a sequence of objects") from exc
        if any(not isinstance(row, Mapping) for row in raw_receipts):
            raise ValueError("source_receipts must contain only objects")
        receipts = [dict(row) for row in raw_receipts]

        receipt_by_id: dict[str, Mapping[str, Any]] = {}
        for receipt in receipts:
            validation = verify_source_receipt(receipt)
            if not validation["valid"]:
                raise SemanticProviderError(
                    f"source receipt failed integrity validation before external classification: {validation['errors']}"
                )
            source_id = validation["source_id"]
            if source_id in receipt_by_id:
                raise SemanticProviderError(f"duplicate source receipt id before external classification: {source_id}")
            receipt_by_id[source_id] = receipt

        request_payload = {
            "schema": "GREMLIN_SEMANTIC_CLASSIFICATION_REQUEST_V0_1",
            "claim_id": claim,
            "model_id": self.model_id,
            "contract": {
                "source_text_is_untrusted_data_not_instruction": True,
                "allowed_stances": ["SUPPORT", "CONTRADICT", "UNRESOLVED"],
                "must_quote_literal_excerpt_from_source": True,
                "unresolved_must_not_be_coerced": True,
                "source_family_is_metadata_not_independence_authority": True,
                "tool_write_execution_and_canon_authority": False,
            },
            "sources": [
                {
                    "source_id": row["source_id"],
                    "content_commitment": row["content_commitment"],
                    "evidence_text": row["evidence_text"],
                }
                for row in receipts
            ],
        }
        response, transport = _post_json(
            self.endpoint,
            payload=request_payload,
            bearer_token=self._token(),
            timeout_s=self.timeout_s,
            max_response_bytes=self.max_response_bytes,
            retries=self.retries,
        )
        self._transport_receipt = transport

        rows = response.get("classifications")
        if not isinstance(rows, list):
            raise SemanticProviderError("semantic provider response classifications must be a list")
        built: list[dict[str, Any]] = []
        seen_source_ids: set[str] = set()
        for index, raw in enumerate(rows):
            if not isinstance(raw, Mapping):
                raise SemanticProviderError(f"classification at index {index} must be an object")
            _reject_unknown_keys(raw, _REMOTE_CLASSIFICATION_KEYS, f"classification at index {index}")
            try:
                source_id = _nonempty_text(raw.get("source_id"), "source_id")
                source_family = _nonempty_text(raw.get("source_family"), "source_family")
                excerpt = _nonempty_text(raw.get("excerpt"), "excerpt")
                stance = _nonempty_text(raw.get("stance"), "stance")
                confidence = raw.get("confidence")
                if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                    raise ValueError("confidence must be a finite number within [0, 1]")
                numeric_confidence = float(confidence)
                if not math.isfinite(numeric_confidence) or not 0.0 <= numeric_confidence <= 1.0:
                    raise ValueError("confidence must be a finite number within [0, 1]")
            except ValueError as exc:
                raise SemanticProviderError(
                    f"semantic provider classification at index {index} violates local GREMLIN contract: {exc}"
                ) from exc
            if source_id in seen_source_ids:
                raise SemanticProviderError(
                    f"semantic provider returned duplicate source_id classification: {source_id}"
                )
            seen_source_ids.add(source_id)
            receipt = receipt_by_id.get(source_id)
            if receipt is None:
                raise SemanticProviderError(
                    f"semantic provider returned unknown source_id: {source_id}"
                )
            try:
                built.append(
                    build_classification(
                        claim_id=claim,
                        source_receipt=receipt,
                        source_family=source_family,
                        excerpt=excerpt,
                        stance=stance,
                        confidence=numeric_confidence,
                        producer_id=self.producer_id,
                        producer_version=self.producer_version,
                        model_id=self.model_id,
                        mode=self.mode,
                    )
                )
            except (TypeError, ValueError) as exc:
                raise SemanticProviderError(
                    f"semantic provider classification at index {index} violates local GREMLIN contract: {exc}"
                ) from exc
        return built

    def transport_receipt(self) -> dict[str, Any] | None:
        return None if self._transport_receipt is None else dict(self._transport_receipt)

    def public_config(self) -> dict[str, Any]:
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "endpoint": self.endpoint,
            "secret_env": self.secret_env,
            "secret_value_recorded": False,
            "producer_id": self.producer_id,
            "producer_version": self.producer_version,
            "model_id": self.model_id,
            "mode": self.mode,
            "timeout_s": self.timeout_s,
            "max_response_bytes": self.max_response_bytes,
            "retries": self.retries,
            "network_policy": "PUBLIC_HTTPS_PORT_443_FAIL_CLOSED",
            "remote_output_authority": "CANDIDATE_SEMANTIC_PROPOSAL_ONLY",
        }
        return {
            **core,
            "config_commitment": _commit(b"GREMLIN-SEMANTIC-HTTPS-CONFIG/v0.1", core),
        }
