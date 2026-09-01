"""Canonical URL/document identity and content hashing."""

from __future__ import annotations

import hashlib
import posixpath
import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

_TRACKING_QUERY_KEYS = frozenset(
    {"fbclid", "gclid", "msclkid", "utm_campaign", "utm_medium", "utm_source"}
)


def canonicalize_url(url: str) -> str:
    """Return a stable public URL identity without fetching the URL.

    Fragments and common tracking parameters do not identify source content.
    Credentials, unsupported schemes, malformed hosts, and control characters
    are rejected rather than silently normalized into a different resource.
    """

    if not isinstance(url, str) or not url or url != url.strip():
        raise ValueError("URL must be a non-empty string without surrounding whitespace")
    if any(ord(character) < 32 for character in url):
        raise ValueError("URL must not contain control characters")
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("URL is malformed") from error
    if scheme not in {"http", "https"} or not host:
        raise ValueError("source URL must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("source URL must not contain credentials")
    try:
        normalized_host = host.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise ValueError("source URL host is malformed") from error
    if not normalized_host:
        raise ValueError("source URL host is empty")
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    host_for_url = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    netloc = host_for_url if port is None or default_port else f"{host_for_url}:{port}"
    path = parsed.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = f"/{path}"
    if parsed.path.endswith("/") and path != "/":
        path += "/"
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in _TRACKING_QUERY_KEYS and not key.casefold().startswith("utm_")
        ],
        doseq=True,
        safe="/:,",
    )
    return urlunsplit((scheme, netloc, quote(path, safe="/%:@!$&'()*+,;="), query, ""))


def canonical_domain(value: str) -> str:
    """Normalize a domain or URL to a lower-case hostname."""

    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if not parsed.hostname:
        raise ValueError("domain is malformed")
    return parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()


def canonical_document_identity(
    *,
    canonical_url: str | None = None,
    external_document_id: str | None = None,
) -> str:
    """Build a stable source identity, preferring a publisher document ID."""

    if external_document_id is not None and external_document_id.strip():
        return f"document:{external_document_id.strip()}"
    if canonical_url is None:
        raise ValueError("canonical_url or external_document_id is required")
    return f"url:{canonicalize_url(canonical_url)}"


def content_hash(content: str | bytes) -> str:
    """Hash source bytes deterministically using SHA-256."""

    raw = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(raw).hexdigest()


def metadata_content_hash(metadata: Mapping[str, object]) -> str:
    """Hash metadata-only snapshots deterministically when no body is retained."""

    import json

    serialized = json.dumps(dict(metadata), sort_keys=True, separators=(",", ":"), default=str)
    return content_hash(serialized)


__all__ = [
    "canonical_document_identity",
    "canonical_domain",
    "canonicalize_url",
    "content_hash",
    "metadata_content_hash",
    "normalize_canonical_url",
    "sha256_content_hash",
]

# Explicit aliases keep the identity boundary easy to discover for callers
# that describe the operation as normalization rather than canonicalization.
normalize_canonical_url = canonicalize_url
sha256_content_hash = content_hash
