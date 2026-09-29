"""URL and artifact security guards for browser adapters."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _blocked_host(host: str) -> bool:
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
        return bool(address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified)
    except ValueError:
        pass
    try:
        resolved = {item[4][0] for item in socket.getaddrinfo(lowered, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        resolved = set()
    return any(_blocked_host(address) for address in resolved)


def validate_public_https_url(url: str, allowed_hosts=None) -> str:
    parsed = urlparse(str(url))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("browser navigation requires an HTTPS URL without embedded credentials")
    host = parsed.hostname.lower().rstrip(".")
    if _blocked_host(host):
        raise ValueError(f"browser navigation blocked private or local host: {host}")
    allowed = tuple(str(value).lower().rstrip(".") for value in (allowed_hosts or ()) if value)
    if allowed and not any(host == item or host.endswith("." + item) for item in allowed):
        raise ValueError(f"browser URL is outside the source allowlist: {host}")
    return host


def validate_redirect(original: str, final: str, allowed_hosts=None) -> None:
    original_host = validate_public_https_url(original, allowed_hosts)
    final_host = validate_public_https_url(final, allowed_hosts)
    if not allowed_hosts and final_host != original_host:
        raise ValueError(f"cross-origin browser redirect blocked: {original_host} -> {final_host}")
