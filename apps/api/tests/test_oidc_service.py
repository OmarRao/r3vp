"""Unit tests for the pure OIDC service logic (no network, no database).

An RSA keypair is generated in-process, id_tokens are signed locally, and a
matching in-memory JWKS is built - so signature and claim validation are
exercised exactly as they would be against a real IdP, minus the network.
"""
from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from src.services import oidc

ISSUER = "https://idp.example.com/"
AUDIENCE = "r3vp-client-id"
KID = "test-key-1"


@pytest.fixture(scope="module")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def jwks(keypair):
    pub_jwk = json.loads(RSAAlgorithm.to_jwk(keypair.public_key()))
    pub_jwk.update({"kid": KID, "use": "sig", "alg": "RS256"})
    return {"keys": [pub_jwk]}


def _make_token(keypair, **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "idp|user-123",
        "email": "user@example.com",
        "iat": now,
        "exp": now + 300,
        "nonce": "nonce-abc",
    }
    claims.update(overrides)
    return jwt.encode(claims, keypair, algorithm="RS256", headers={"kid": KID})


# ---- state / nonce ----

def test_state_and_nonce_are_unique_and_high_entropy():
    states = {oidc.generate_state() for _ in range(100)}
    nonces = {oidc.generate_nonce() for _ in range(100)}
    assert len(states) == 100
    assert len(nonces) == 100
    assert all(len(s) >= 32 for s in states)


# ---- authorization URL ----

def test_build_authorization_url_contains_required_params():
    req = oidc.build_authorization_url(
        "https://idp.example.com/authorize",
        client_id="abc",
        redirect_uri="https://app/callback",
        scopes=["openid", "email"],
    )
    parsed = urlparse(req.url)
    qs = parse_qs(parsed.query)
    assert parsed.path == "/authorize"
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == ["abc"]
    assert qs["redirect_uri"] == ["https://app/callback"]
    assert qs["scope"] == ["openid email"]
    assert qs["state"] == [req.state]
    assert qs["nonce"] == [req.nonce]


def test_build_authorization_url_forces_openid_scope():
    req = oidc.build_authorization_url(
        "https://idp/authorize", client_id="a", redirect_uri="https://cb", scopes=["email"]
    )
    qs = parse_qs(urlparse(req.url).query)
    assert "openid" in qs["scope"][0].split()


def test_build_authorization_url_appends_when_endpoint_has_query():
    req = oidc.build_authorization_url(
        "https://idp/authorize?foo=bar", client_id="a", redirect_uri="https://cb"
    )
    assert "?foo=bar&" in req.url


def test_build_authorization_url_requires_client_id():
    with pytest.raises(oidc.OidcError):
        oidc.build_authorization_url("https://idp/authorize", client_id="", redirect_uri="https://cb")


# ---- id_token validation: happy path ----

def test_validate_id_token_valid(keypair, jwks):
    token = _make_token(keypair)
    claims = oidc.validate_id_token(
        token, jwks, issuer=ISSUER, audience=AUDIENCE, nonce="nonce-abc"
    )
    assert claims["sub"] == "idp|user-123"
    assert claims["email"] == "user@example.com"


# ---- id_token validation: error paths ----

def test_validate_id_token_bad_signature(keypair, jwks):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "email": "e@x", "iat": int(time.time()),
         "exp": int(time.time()) + 300},
        other, algorithm="RS256", headers={"kid": KID},
    )
    with pytest.raises(oidc.OidcValidationError):
        oidc.validate_id_token(token, jwks, issuer=ISSUER, audience=AUDIENCE)


def test_validate_id_token_expired(keypair, jwks):
    token = _make_token(keypair, iat=int(time.time()) - 600, exp=int(time.time()) - 300)
    with pytest.raises(oidc.OidcValidationError):
        oidc.validate_id_token(token, jwks, issuer=ISSUER, audience=AUDIENCE)


def test_validate_id_token_wrong_audience(keypair, jwks):
    token = _make_token(keypair, aud="someone-else")
    with pytest.raises(oidc.OidcValidationError):
        oidc.validate_id_token(token, jwks, issuer=ISSUER, audience=AUDIENCE)


def test_validate_id_token_wrong_issuer(keypair, jwks):
    token = _make_token(keypair, iss="https://evil.example.com/")
    with pytest.raises(oidc.OidcValidationError):
        oidc.validate_id_token(token, jwks, issuer=ISSUER, audience=AUDIENCE)


def test_validate_id_token_nonce_mismatch(keypair, jwks):
    token = _make_token(keypair, nonce="attacker-nonce")
    with pytest.raises(oidc.OidcValidationError):
        oidc.validate_id_token(token, jwks, issuer=ISSUER, audience=AUDIENCE, nonce="nonce-abc")


def test_validate_id_token_unknown_kid(keypair, jwks):
    token = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "email": "e@x", "iat": int(time.time()),
         "exp": int(time.time()) + 300},
        keypair, algorithm="RS256", headers={"kid": "unknown-kid"},
    )
    with pytest.raises(oidc.OidcValidationError):
        oidc.validate_id_token(token, jwks, issuer=ISSUER, audience=AUDIENCE)


# ---- claim mapping ----

def test_map_claims_to_identity_defaults():
    identity = oidc.map_claims_to_identity({"sub": "s", "email": "a@b.com"})
    assert identity.subject == "s"
    assert identity.email == "a@b.com"
    assert identity.role == "viewer"


def test_map_claims_to_identity_custom_mapping():
    claims = {"sub": "s", "upn": "a@b.com", "app_role": "Admin"}
    identity = oidc.map_claims_to_identity(claims, {"email": "upn", "role": "app_role"})
    assert identity.email == "a@b.com"
    assert identity.role == "admin"  # lower-cased


def test_map_claims_to_identity_missing_email():
    with pytest.raises(oidc.OidcValidationError):
        oidc.map_claims_to_identity({"sub": "s"})


def test_map_claims_to_identity_missing_sub():
    with pytest.raises(oidc.OidcValidationError):
        oidc.map_claims_to_identity({"email": "a@b.com"})
