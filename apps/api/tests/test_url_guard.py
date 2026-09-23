# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Unit tests for the SSRF URL guard.

Covers the fast literal check (no DNS) and the full resolving check, using an
injected resolver so tests never touch the network.
"""
import socket

import pytest

from src.services.url_guard import (
    UnsafeUrlError,
    assert_safe_url,
    check_scheme_and_literal,
    is_safe_url,
)


def _resolver_returning(*addrs):
    """Build a getaddrinfo stand-in that resolves any host to the given IPs."""
    def _resolve(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port)) for a in addrs]
    return _resolve


# --- literal / scheme check (no DNS) ---

def test_literal_metadata_ip_blocked():
    with pytest.raises(UnsafeUrlError):
        check_scheme_and_literal("http://169.254.169.254/latest/meta-data/")


def test_literal_loopback_blocked():
    with pytest.raises(UnsafeUrlError):
        check_scheme_and_literal("http://127.0.0.1:8080/x")


def test_literal_private_ranges_blocked():
    for url in (
        "http://10.0.0.5/hook",
        "http://192.168.1.1/hook",
        "https://172.16.4.9/hook",
        "http://[::1]/hook",
    ):
        with pytest.raises(UnsafeUrlError):
            check_scheme_and_literal(url)


def test_non_http_scheme_blocked():
    for url in ("file:///etc/passwd", "gopher://x/1", "ftp://host/f"):
        with pytest.raises(UnsafeUrlError):
            check_scheme_and_literal(url)


def test_missing_host_blocked():
    with pytest.raises(UnsafeUrlError):
        check_scheme_and_literal("http:///no-host")


def test_public_literal_ip_allowed():
    check_scheme_and_literal("https://8.8.8.8/collector")


def test_hostname_passes_literal_check():
    # A hostname cannot be classified without DNS, so the fast check lets it by.
    check_scheme_and_literal("https://hooks.slack.com/services/T/B/x")


# --- full resolving check (injected resolver) ---

def test_hostname_resolving_to_metadata_blocked():
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("https://evil.example/hook", resolver=_resolver_returning("169.254.169.254"))


def test_hostname_resolving_to_private_blocked():
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("https://rebind.example/hook", resolver=_resolver_returning("10.1.2.3"))


def test_hostname_with_mixed_addresses_blocked():
    # If any resolved address is non-public the URL is refused.
    with pytest.raises(UnsafeUrlError):
        assert_safe_url(
            "https://mixed.example/hook",
            resolver=_resolver_returning("93.184.216.34", "127.0.0.1"),
        )


def test_public_hostname_allowed():
    assert_safe_url("https://hooks.slack.com/x", resolver=_resolver_returning("93.184.216.34"))


def test_unresolvable_host_blocked():
    def _boom(host, port, *args, **kwargs):
        raise socket.gaierror("name resolution failed")

    with pytest.raises(UnsafeUrlError):
        assert_safe_url("https://nope.invalid/x", resolver=_boom)


def test_is_safe_url_wrapper():
    assert is_safe_url("http://127.0.0.1/") is False
    assert is_safe_url("file:///etc/passwd") is False
