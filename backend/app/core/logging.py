"""Structured logging.

Every log line is a single JSON object with the consistent field set required
by Block J of the architecture spec (request_id, tenant_id, workspace_id,
case_id, actor_id, module, action, status, timestamp). Request-scoped values
are carried in contextvars set by the request-context middleware, so services
never need to pass identifiers around just for logging.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
workspace_id_var: ContextVar[str | None] = ContextVar("workspace_id", default=None)
actor_id_var: ContextVar[str | None] = ContextVar("actor_id", default=None)

_CONTEXT_FIELDS = {
    "request_id": request_id_var,
    "tenant_id": tenant_id_var,
    "workspace_id": workspace_id_var,
    "actor_id": actor_id_var,
}

# Passed via logging `extra`; prefixed because `module` is a reserved
# LogRecord attribute. Emitted unprefixed in the JSON payload (Block J names).
_EXTRA_FIELDS = {
    "log_case_id": "case_id",
    "log_module": "module",
    "log_action": "action",
    "log_status": "status",
}


def log_fields(
    *,
    module: str | None = None,
    action: str | None = None,
    status: str | None = None,
    case_id: str | None = None,
) -> dict[str, str]:
    """Build the `extra` dict for a structured log call."""
    fields = {
        "log_module": module,
        "log_action": action,
        "log_status": status,
        "log_case_id": case_id,
    }
    return {key: value for key, value in fields.items() if value is not None}


class JsonFormatter(logging.Formatter):
    """Render each record as one JSON object with consistent fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field, var in _CONTEXT_FIELDS.items():
            value = var.get()
            if value is not None:
                payload[field] = value
        for attr, name in _EXTRA_FIELDS.items():
            value = getattr(record, attr, None)
            if value is not None:
                payload[name] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, at app startup."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own loggers should flow through the same JSON pipeline.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
