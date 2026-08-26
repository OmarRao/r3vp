# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""HTTP hardening middleware: security response headers and correlation IDs.

Adds a standard set of security headers to every response and assigns each
request a correlation id (honoring an inbound ``X-Request-ID`` when present,
otherwise generating one). The id is bound to the structlog context so it
appears on every log line for the request, and echoed back in the response
``X-Request-ID`` header for cross-service tracing (appliance to SaaS).
"""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            clear_contextvars()
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        response.headers["X-Request-ID"] = request_id
        return response
