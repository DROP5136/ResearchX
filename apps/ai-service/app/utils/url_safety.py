"""URL safety helpers — block SSRF / dangerous schemes."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """Raised when a URL is not allowed for outbound fetching."""


_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.google.com",
}

_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript", "dict", "sftp", "ssh"}


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_public_http_url(url: str, *, allow_http: bool = True) -> str:
    """
    Validate that `url` is a safe http(s) URL for server-side fetching.
    Raises UnsafeURLError on rejection. Returns the stripped URL.
    """
    cleaned = (url or "").strip()
    if not cleaned or len(cleaned) > 2048:
        raise UnsafeURLError("URL is empty or too long")

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        raise UnsafeURLError(f"URL scheme '{scheme}' is not allowed")
    if scheme == "https":
        pass
    elif scheme == "http" and allow_http:
        pass
    else:
        raise UnsafeURLError("Only http and https URLs are allowed")

    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise UnsafeURLError("URL must include a hostname")
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise UnsafeURLError("Hostname is not allowed")

    # Literal IP in hostname
    try:
        ip = ipaddress.ip_address(host)
        if _is_private_ip(ip):
            raise UnsafeURLError("Private or reserved IP addresses are not allowed")
    except ValueError:
        # Not an IP — resolve DNS and check
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise UnsafeURLError("Unable to resolve hostname") from exc
        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if _is_private_ip(ip):
                raise UnsafeURLError("Hostname resolves to a private or reserved address")

    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with embedded credentials are not allowed")

    return cleaned
