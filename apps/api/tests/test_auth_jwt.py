"""Unit tests for the PyJWT-based Auth0 token verification and notification senders.

These verify the migration off python-jose: token decode uses PyJWT's PyJWKClient,
invalid tokens raise 401, and a valid signed token yields a CurrentUser.
"""
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from src import auth


@pytest.fixture
def rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key


def _make_token(private_key, *, kid="test-kid", **claims) -> str:
    payload = {
        "sub": "auth0|abc123",
        "aud": "https://api.r3vp.io",
        "iss": "https://tenant.auth0.com/",
        **claims,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def test_uses_pyjwt_not_jose():
    """auth module should import PyJWT, not python-jose."""
    assert auth.jwt.__name__ == "jwt"
    assert hasattr(auth, "PyJWKClient")


def test_invalid_token_raises_401(monkeypatch):
    """A malformed token surfaces as a 401, not a 500."""
    monkeypatch.setattr(auth, "_jwk_client", auth._jwk_client.__wrapped__)

    class _Client:
        def get_signing_key_from_jwt(self, token):
            raise jwt.InvalidTokenError("bad token")

    monkeypatch.setattr(auth, "_jwk_client", lambda: _Client())
    with pytest.raises(HTTPException) as exc:
        auth._decode_token("not-a-real-token")
    assert exc.value.status_code == 401


def test_valid_token_decodes(monkeypatch, rsa_keypair):
    """A correctly signed RS256 token decodes to its claims via PyJWT."""
    org_id = str(uuid.uuid4())
    token = _make_token(rsa_keypair, **{"https://r3vp.io/org_id": org_id, "email": "j@contoso.com"})

    class _SigningKey:
        key = rsa_keypair.public_key()

    class _Client:
        def get_signing_key_from_jwt(self, t):
            return _SigningKey()

    monkeypatch.setattr(auth, "_jwk_client", lambda: _Client())
    monkeypatch.setattr(auth.settings, "auth0_audience", "https://api.r3vp.io", raising=False)
    monkeypatch.setattr(auth.settings, "auth0_domain", "tenant.auth0.com", raising=False)

    payload = auth._decode_token(token)
    assert payload["https://r3vp.io/org_id"] == org_id
    assert payload["email"] == "j@contoso.com"


@pytest.mark.asyncio
async def test_pagerduty_sender_posts_events_api(monkeypatch):
    """PagerDuty sender posts a trigger event to the Events API v2."""
    from src.services import notifications

    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(notifications.httpx, "AsyncClient", _Client)
    await notifications._send_pagerduty("ROUTINGKEY", "sql-prod-01", "run-1", "Recovery test FAILED")
    assert captured["url"] == "https://events.pagerduty.com/v2/enqueue"
    assert captured["json"]["routing_key"] == "ROUTINGKEY"
    assert captured["json"]["event_action"] == "trigger"


@pytest.mark.asyncio
async def test_webhook_sender_posts_generic_payload(monkeypatch):
    """Generic webhook sender posts an r3vp JSON payload to the configured URL."""
    from src.services import notifications

    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(notifications.httpx, "AsyncClient", _Client)
    await notifications._send_webhook("https://siem.example/ingest", "sql-prod-01", "run-1", "summary", ["test_failed"])
    assert captured["url"] == "https://siem.example/ingest"
    assert captured["json"]["source"] == "r3vp"
    assert captured["json"]["triggers"] == ["test_failed"]
