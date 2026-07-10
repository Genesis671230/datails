"""Real-token PKCE login test (LD-26).

Runs the genuine authorization-code + PKCE flow against the Entra External ID
tenant, then verifies the backend accepts the real token (and rejects a
tampered one). This is the gate before any frontend integration work.

Usage:
    .venv/bin/python scripts/pkce_login_test.py
Then open the printed URL, sign in, and watch the result.

Requires the backend running locally with AUTH_DEV_MODE=false and the
ENTRA_* variables set (see scripts/run_backend_entra.sh).
"""

import base64
import hashlib
import http.server
import json
import secrets
import sys
import threading
import urllib.parse

import httpx

TENANT_ID = "194ac953-cb8a-4e07-9890-65e73d2c024d"
AUTHORITY_HOST = f"https://datails.ciamlogin.com/{TENANT_ID}"
SPA_CLIENT_ID = "01c24144-4b73-41df-b51d-592eb1e85785"
API_CLIENT_ID = "00d8c4ff-db9c-4533-b344-48e08cf3af73"
SCOPE = f"api://{API_CLIENT_ID}/access_as_user openid profile email"
REDIRECT_URI = "http://localhost:8765/callback"
BACKEND_URL = "http://localhost:8000"

received: dict = {}
expected_state: str = ""


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        params = {key: value[0] for key, value in query.items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if params.get("state") != expected_state:
            # A redirect from an older run's tab — ignore it and keep waiting.
            self.wfile.write(
                b"<h2>Stale login session - close this tab and use the NEWEST link.</h2>"
            )
            return
        received.update(params)
        self.wfile.write(b"<h2>Datails PKCE test: login captured. Return to the terminal.</h2>")

    def log_message(self, *args):
        pass


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> int:
    global expected_state
    verifier = b64url(secrets.token_bytes(48))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    state = b64url(secrets.token_bytes(12))
    expected_state = state

    params = {
        "client_id": SPA_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{AUTHORITY_HOST}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
    print("\n=== Open this URL in your browser and sign in ===\n")
    print(url + "\n")

    server = http.server.HTTPServer(("localhost", 8765), CallbackHandler)
    server.timeout = 5

    def serve_until_captured():
        import time

        deadline = time.monotonic() + 600
        while "code" not in received and "error" not in received:
            if time.monotonic() > deadline:
                return
            server.handle_request()

    thread = threading.Thread(target=serve_until_captured, daemon=True)
    thread.start()
    thread.join(timeout=610)
    server.server_close()

    if "error" in received:
        print(f"FAIL: {received.get('error')}: {received.get('error_description', '')[:300]}")
        return 1
    if "code" not in received:
        print("FAIL: no authorization code received (timeout)")
        return 1
    print("authorization code received; exchanging with PKCE verifier…")

    token_response = httpx.post(
        f"{AUTHORITY_HOST}/oauth2/v2.0/token",
        data={
            "client_id": SPA_CLIENT_ID,
            "grant_type": "authorization_code",
            "code": received["code"],
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
            "scope": SCOPE,
        },
        # SPA-platform codes must be redeemed as a cross-origin request
        # (AADSTS9002327) — exactly what the browser does in production.
        headers={"Origin": "http://localhost:8765"},
        timeout=30,
    )
    if token_response.status_code != 200:
        print(f"FAIL: token exchange {token_response.status_code}: {token_response.text[:300]}")
        return 1
    access_token = token_response.json()["access_token"]

    claims = json.loads(
        base64.urlsafe_b64decode(access_token.split(".")[1] + "==").decode()
    )
    print(f"token acquired: iss={claims.get('iss')}")
    print(f"               aud={claims.get('aud')} oid={claims.get('oid')}")

    print("\n=== Backend verification (LD-1) ===")
    bootstrap = httpx.post(
        f"{BACKEND_URL}/api/v1/workspaces/bootstrap",
        json={"tenant_name": "PKCE Test Tenant"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    print(f"bootstrap with real token -> {bootstrap.status_code}")
    if bootstrap.status_code != 200:
        print(bootstrap.text[:500])
        return 1
    body = bootstrap.json()
    print(f"  tenant={body['tenant']['slug']} user_role={body['user']['role']}")

    me = httpx.get(
        f"{BACKEND_URL}/api/v1/workspaces/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    print(f"me with real token        -> {me.status_code}")

    tampered = access_token[:-8] + "AAAAAAAA"
    rejected = httpx.get(
        f"{BACKEND_URL}/api/v1/workspaces/me",
        headers={"Authorization": f"Bearer {tampered}"},
        timeout=30,
    )
    print(f"me with tampered token    -> {rejected.status_code} (expect 401)")

    ok = me.status_code == 200 and rejected.status_code == 401
    print("\nPKCE REAL-TOKEN TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
