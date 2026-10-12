"""API-key authentication dependency."""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    provided: str | None = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """Reject the request unless it carries the configured key.

    Uses a constant-time comparison so the key cannot be recovered through
    response-timing differences. When no key is configured auth is disabled,
    which is only intended for a service bound to localhost.
    """
    expected = settings.api_key
    if not expected:
        return
    if not provided or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
