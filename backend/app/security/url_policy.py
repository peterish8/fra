"""SSRF-safe policy for public HTTP/HTTPS retrieval."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Collection, Mapping, Sequence
from urllib.parse import urljoin, urlsplit

from pydantic import BaseModel, ConfigDict, Field

Resolver = Callable[[str], Sequence[str]]


class URLValidationResult(BaseModel):
    """Stable result for URL and redirect validation."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    url: str
    reason: str | None = None
    addresses: list[str] = Field(default_factory=list)


def resolve_hostname(hostname: str) -> list[str]:
    """Resolve a hostname using the system resolver for the current request."""

    infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


_DOCUMENTATION_NETWORKS = (
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32"),
)
_BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".localdomain", ".internal")
_DEFAULT_PORTS: Mapping[str, Collection[int]] = {"http": (80,), "https": (443,)}


def _address_reason(address: str) -> str | None:
    try:
        parsed = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return "INVALID_ADDRESS"
    if parsed.is_loopback:
        return "LOOPBACK"
    if parsed.is_link_local:
        return "LINK_LOCAL"
    if parsed.is_unspecified or parsed.is_multicast:
        return "UNSPECIFIED_OR_RESERVED"
    if any(parsed in network for network in _DOCUMENTATION_NETWORKS):
        return "UNSPECIFIED_OR_RESERVED"
    if parsed.is_reserved:
        return "UNSPECIFIED_OR_RESERVED"
    if parsed.is_private:
        return "PRIVATE"
    # 100.64.0.0/10 is shared address space, not public egress space, even
    # though ipaddress does not classify it as private.
    if parsed in ipaddress.ip_network("100.64.0.0/10"):
        return "PRIVATE"
    return None


def _invalid(url: str, reason: str) -> URLValidationResult:
    return URLValidationResult(allowed=False, url=url, reason=reason, addresses=[])


def validate_url(
    url: str,
    *,
    resolver: Resolver = resolve_hostname,
    allowed_ports: Mapping[str, Collection[int]] | None = None,
) -> URLValidationResult:
    """Allow only public HTTP/HTTPS URLs after DNS/IP policy checks."""

    if (
        not isinstance(url, str)
        or not url
        or url != url.strip()
        or any(ord(character) < 32 for character in url)
    ):
        return _invalid(str(url), "INVALID_URL")
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return _invalid(url, "INVALID_URL")
    if not scheme:
        return _invalid(url, "INVALID_URL")
    if scheme not in {"http", "https"}:
        return _invalid(url, "UNSUPPORTED_SCHEME")
    if not hostname or parsed.username or parsed.password or "%" in hostname:
        return _invalid(url, "INVALID_URL")
    hostname = hostname.rstrip(".").lower()
    if not hostname or hostname == "localhost" or hostname.endswith(_BLOCKED_HOST_SUFFIXES):
        return _invalid(url, "PRIVATE_HOST")
    ports = _DEFAULT_PORTS if allowed_ports is None else allowed_ports
    if port is not None and port not in ports.get(scheme, ()):
        return _invalid(url, "PORT_NOT_ALLOWED")

    try:
        addresses = [str(address) for address in resolver(hostname)]
    except (OSError, socket.gaierror, ValueError):
        return _invalid(url, "DNS_RESOLUTION_FAILED")
    if not addresses:
        return _invalid(url, "DNS_RESOLUTION_FAILED")
    for address in addresses:
        reason = _address_reason(address)
        if reason is not None:
            return URLValidationResult(allowed=False, url=url, reason=reason, addresses=addresses)
    return URLValidationResult(allowed=True, url=url, reason=None, addresses=addresses)


def validate_redirect_chain(
    initial_url: str,
    redirects: Sequence[str],
    *,
    resolver: Resolver = resolve_hostname,
    max_redirects: int = 3,
    allowed_ports: Mapping[str, Collection[int]] | None = None,
) -> URLValidationResult:
    """Validate the initial URL and each redirect, detecting DNS rebinding."""

    if not isinstance(max_redirects, int) or max_redirects < 0:
        return _invalid(initial_url, "INVALID_REDIRECT_LIMIT")

    first = validate_url(initial_url, resolver=resolver, allowed_ports=allowed_ports)
    if not first.allowed:
        return first
    if len(redirects) > max_redirects:
        return _invalid(initial_url, "REDIRECT_LIMIT_EXCEEDED")

    # Resolve once more immediately before the first request.  This closes the
    # gap between an initial DNS decision and network use, even when no HTTP
    # redirect is present.
    initial_recheck = validate_url(initial_url, resolver=resolver, allowed_ports=allowed_ports)
    if not initial_recheck.allowed:
        return URLValidationResult(
            allowed=False,
            url=initial_url,
            reason=(
                "DNS_REBINDING"
                if set(initial_recheck.addresses) != set(first.addresses)
                else initial_recheck.reason
            ),
            addresses=initial_recheck.addresses,
        )
    if set(initial_recheck.addresses) != set(first.addresses):
        return URLValidationResult(
            allowed=False,
            url=initial_url,
            reason="DNS_REBINDING",
            addresses=initial_recheck.addresses,
        )

    current = initial_url
    final_addresses = initial_recheck.addresses
    seen_addresses: dict[str, frozenset[str]] = {
        (urlsplit(initial_url).hostname or "").rstrip(".").lower(): frozenset(
            initial_recheck.addresses
        )
    }
    for redirect in redirects:
        if not isinstance(redirect, str):
            return _invalid(str(redirect), "INVALID_URL_REDIRECT")
        target = urljoin(current, redirect)
        checked = validate_url(target, resolver=resolver, allowed_ports=allowed_ports)
        try:
            hostname = (urlsplit(target).hostname or "").rstrip(".").lower()
        except ValueError:
            hostname = ""
        previous = seen_addresses.get(hostname)
        current_addresses = frozenset(checked.addresses)
        if previous is not None and previous != current_addresses:
            return URLValidationResult(
                allowed=False,
                url=target,
                reason="DNS_REBINDING",
                addresses=checked.addresses,
            )
        if not checked.allowed:
            reason = checked.reason or "URL_NOT_ALLOWED"
            if reason == "PRIVATE_HOST":
                reason = "PRIVATE"
            return URLValidationResult(
                allowed=False,
                url=target,
                reason=f"{reason}_REDIRECT",
                addresses=checked.addresses,
            )
        seen_addresses[hostname] = current_addresses
        current = target
        final_addresses = checked.addresses
    return URLValidationResult(allowed=True, url=current, reason=None, addresses=final_addresses)


__all__ = [
    "URLValidationResult",
    "resolve_hostname",
    "validate_redirect_chain",
    "validate_url",
]
