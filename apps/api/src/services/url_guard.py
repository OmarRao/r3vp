# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""SSRF guard for outbound requests to user-supplied URLs.

Before the backend makes a server-side request to a URL a customer configured
(webhooks, SOAR/SIEM endpoints, report delivery), validate that it targets a
public host. Blocks non-http(s) schemes and any URL whose host is, or resolves
to, a loopback, private, link-local (including the cloud metadata endpoint
169.254.169.254), or other non-global address. This is the core defense against
server-side request forgery.

`check_scheme_and_literal` is synchronous and does no DNS, so it is safe to call
on the event loop (used at config-validation time). `assert_safe_url` also
resolves the host and must be run off the event loop (e.g. via asyncio.to_thread)
at dispatch time, which is where the actual outbound request is made.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_ALLOWED_SCHEMES = frozenset({"http", "https"})


class UnsafeUrlError(ValueError):
    """Raised when a URL is not safe to request from the server."""


def _default_port(scheme: str) -> int:
    return 443 if scheme.lower() == "https" else 80


def _reject_non_global(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, host: str, addr: str) -> None:
    # is_global is False for private, loopback, link-local, reserved,
    # multicast, and unspecified addresses - all of which we refuse.
    if not ip.is_global:
        raise UnsafeUrlError(f"URL host {host!r} resolves to non-public address {addr}")


def check_scheme_and_literal(url: str) -> None:
    """Fast, DNS-free check: scheme is http(s), a host is present, and if the
    host is a literal IP it is public. Safe to call on the event loop."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"URL scheme must be http or https, got {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL has no host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return  # not a literal IP; the full check resolves it at dispatch time
    _reject_non_global(ip, host, host)


def assert_safe_url(url: str, resolver=socket.getaddrinfo) -> None:
    """Full check including DNS resolution. Blocking; run off the event loop."""
    check_scheme_and_literal(url)
    parsed = urlparse(url)
    host = parsed.hostname
    assert host is not None  # guaranteed by check_scheme_and_literal
    port = parsed.port or _default_port(parsed.scheme)
    try:
        infos = resolver(host, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise UnsafeUrlError(f"could not resolve host {host!r}: {exc}") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise UnsafeUrlError(f"host {host!r} did not resolve to any address")
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError as exc:
            raise UnsafeUrlError(f"unparseable address {addr!r} for host {host!r}") from exc
        _reject_non_global(ip, host, addr)


def is_safe_url(url: str) -> bool:
    """True when the URL passes the full (DNS-resolving) SSRF check."""
    try:
        assert_safe_url(url)
        return True
    except UnsafeUrlError:
        return False
