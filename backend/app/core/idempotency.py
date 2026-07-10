"""Idempotency middleware for expensive POSTs (LD-28).

Protected routes require an `Idempotency-Key` header. Replay of the same
tenant+key returns the original response (from blob storage); the same key
with a different payload returns 409. Slice 1 protects the connector-run
routes; workflow-agent runs, trace creation, report drafts, and assistant
calls join this set in their slices (05 §11).

Implemented as pure ASGI middleware: it must buffer the request body (for
the request hash) and the response body (for replay storage), which
BaseHTTPMiddleware cannot do reliably.

Only successful (2xx) responses are recorded: a failed external call must
stay retryable under the same key (rationale in DECISIONS.md).
"""

import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.hashing import sha256_hex
from app.core.logging import get_logger, log_fields, request_id_var

logger = get_logger(__name__)

# (method, exact path) pairs requiring an Idempotency-Key. Extended per slice.
PROTECTED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/connectors/crystal/wallet-lookup"),
        ("POST", "/api/v1/connectors/crystal/wallet-lookup-and-attach"),
        ("POST", "/api/v1/ai/assistant"),
        ("POST", "/api/v1/reports/draft"),
    }
)

IDEMPOTENCY_HEADER = b"idempotency-key"
REPLAY_HEADER = (b"x-idempotent-replay", b"true")
IDEMPOTENCY_CONTAINER = "idempotency"
MAX_KEY_LENGTH = 255


def _error_body(code: str, message: str) -> bytes:
    return json.dumps(
        {"error": {"code": code, "message": message, "request_id": request_id_var.get() or ""}}
    ).encode()


class IdempotencyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or (scope["method"], scope["path"]) not in PROTECTED_ROUTES:
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        key = headers.get(IDEMPOTENCY_HEADER, b"").decode()
        if not key or len(key) > MAX_KEY_LENGTH:
            await self._send_json(
                send, 400,
                _error_body(
                    "idempotency_key_required",
                    "This endpoint requires an Idempotency-Key header (LD-28).",
                ),
            )
            return

        claims = scope.get("state", {}).get("auth_claims")
        tenant_id = await self._resolve_tenant_id(claims)
        if tenant_id is None:
            # No resolvable tenant: let the request fall through to the normal
            # auth/bootstrap error handling.
            await self.app(scope, receive, send)
            return

        body = await self._read_body(receive)
        request_hash = sha256_hex(body)

        stored = await self._find_record(tenant_id, key)
        if stored is not None:
            if stored.request_hash != request_hash:
                await self._send_json(
                    send, 409,
                    _error_body(
                        "idempotency_key_conflict",
                        "This Idempotency-Key was already used with a different payload.",
                    ),
                )
                return
            await self._replay(send, stored)
            return

        response = await self._call_downstream(scope, body, receive, send)
        if response is not None and 200 <= response["status"] < 300:
            await self._record(
                tenant_id, key, scope["path"], request_hash, response
            )

    @staticmethod
    async def _read_body(receive) -> bytes:
        chunks = []
        while True:
            message = await receive()
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    async def _call_downstream(self, scope, body: bytes, receive, send) -> dict | None:
        """Run the app with a replayable body; buffer and forward the response."""
        sent_body = False

        async def replay_receive():
            nonlocal sent_body
            if not sent_body:
                sent_body = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        response: dict = {"status": None, "headers": [], "body": b""}

        async def capture_send(message) -> None:
            if message["type"] == "http.response.start":
                response["status"] = message["status"]
                response["headers"] = message["headers"]
            elif message["type"] == "http.response.body":
                response["body"] += message.get("body", b"")
            await send(message)

        await self.app(scope, replay_receive, capture_send)
        return response if response["status"] is not None else None

    async def _resolve_tenant_id(self, claims):
        if claims is None:
            return None
        from app.db.repositories.users import get_user_by_oid
        from app.db.session import get_sessionmaker

        async with get_sessionmaker()() as session:
            user = await get_user_by_oid(session, claims.oid)
            return user.tenant_id if user else None

    async def _find_record(self, tenant_id, key: str):
        from app.db.models import IdempotencyKey
        from app.db.session import get_sessionmaker

        async with get_sessionmaker()() as session:
            result = await session.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id, IdempotencyKey.key == key
                )
            )
            return result.scalar_one_or_none()

    async def _record(
        self, tenant_id, key: str, route: str, request_hash: str, response: dict
    ) -> None:
        from app.db.models import IdempotencyKey
        from app.db.session import get_sessionmaker
        from app.integrations.factories import get_blob_storage

        envelope = json.dumps(
            {
                "status": response["status"],
                "content_type": next(
                    (v.decode() for k, v in response["headers"] if k == b"content-type"),
                    "application/json",
                ),
                "body": response["body"].decode(),
            }
        ).encode()
        storage_ref = await get_blob_storage().put(
            IDEMPOTENCY_CONTAINER, f"{tenant_id}/{key}.json", envelope
        )
        try:
            async with get_sessionmaker()() as session:
                session.add(
                    IdempotencyKey(
                        tenant_id=tenant_id,
                        key=key,
                        route=route,
                        request_hash=request_hash,
                        response_ref=storage_ref,
                    )
                )
                await session.commit()
        except IntegrityError:
            # Concurrent duplicate: the first writer wins; both stored the
            # same response payload, so nothing to reconcile.
            logger.info(
                "idempotency record already present",
                extra=log_fields(module="idempotency", action="record", status="duplicate"),
            )

    async def _replay(self, send, stored) -> None:
        from app.integrations.factories import get_blob_storage

        envelope = json.loads(await get_blob_storage().get(stored.response_ref))
        body = envelope["body"].encode()
        await send(
            {
                "type": "http.response.start",
                "status": envelope["status"],
                "headers": [
                    (b"content-type", envelope["content_type"].encode()),
                    (b"content-length", str(len(body)).encode()),
                    REPLAY_HEADER,
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
        logger.info(
            "idempotent replay served",
            extra=log_fields(module="idempotency", action="replay", status="ok"),
        )

    @staticmethod
    async def _send_json(send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
