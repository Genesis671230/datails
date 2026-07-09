"""Test-only JWT utilities.

Generates an RSA keypair once per test session, exposes a JWKS document for
seeding the app's JwksCache, and mints tokens with arbitrary claims so the
REAL validation path (signature, issuer, audience, expiry) is exercised —
no mocking of the verification itself.
"""

import json
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_KID = "test-signing-key"
TEST_AUTHORITY = "https://test.ciamlogin.com/00000000-0000-0000-0000-00000000dead/v2.0"
TEST_AUDIENCE = "api://datails-backend-test"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_document() -> dict:
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_private_key.public_key()))
    public_jwk["kid"] = TEST_KID
    public_jwk["use"] = "sig"
    public_jwk["alg"] = "RS256"
    return {"keys": [public_jwk]}


def mint_token(
    oid: str | None = None,
    *,
    email: str = "investigator@example.test",
    name: str = "Test Investigator",
    issuer: str = TEST_AUTHORITY,
    audience: str = TEST_AUDIENCE,
    expires_in: int = 600,
    kid: str = TEST_KID,
    drop_claims: tuple[str, ...] = (),
) -> str:
    now = int(time.time())
    payload = {
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
        "oid": oid or str(uuid.uuid4()),
        "email": email,
        "name": name,
    }
    for claim in drop_claims:
        payload.pop(claim, None)
    return jwt.encode(payload, _private_key, algorithm="RS256", headers={"kid": kid})
