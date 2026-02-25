"""Bearer token authentication for the Management API.

Token is resolved from (highest priority first):
1. ``SENTINEL_MGMT_TOKEN`` environment variable
2. ``management.token`` in the config file (future — Phase 0 config restructure)

If no token is configured, authentication is **disabled** and all requests pass.
``/manage/v1/health`` is always public regardless of auth configuration.
"""

import hmac
import logging
import os
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Environment variable for the management API token
MGMT_TOKEN_ENV_VAR = "SENTINEL_MGMT_TOKEN"

# Paths that never require authentication (relative to mount prefix)
PUBLIC_PATHS = frozenset({"/health"})


def resolve_token() -> Optional[str]:
    """Resolve the management API token from available sources.

    Returns ``None`` if no token is configured (auth disabled).
    """
    # 1. Environment variable (highest priority)
    env_token = os.environ.get(MGMT_TOKEN_ENV_VAR, "").strip()
    if env_token:
        logger.debug("Management API token resolved from %s env var.", MGMT_TOKEN_ENV_VAR)
        return env_token

    # 2. Config file (future — will be populated when config restructure lands)
    # For now, return None if env var is not set.
    return None


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces Bearer token auth on management routes.

    Usage::

        middleware = BearerAuthMiddleware(app, token="my-secret")
    """

    def __init__(self, app, token: Optional[str] = None) -> None:  # type: ignore[override]
        super().__init__(app)
        self._token = token
        if token:
            logger.info("Management API authentication ENABLED.")
        else:
            logger.warning(
                "Management API authentication DISABLED — no token configured. "
                "Set %s env var to secure admin endpoints.",
                MGMT_TOKEN_ENV_VAR,
            )

    @property
    def auth_enabled(self) -> bool:
        return self._token is not None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Always allow public paths
        if request.url.path in PUBLIC_PATHS or request.url.path.rstrip("/") in PUBLIC_PATHS:
            return await call_next(request)

        # If no token configured, allow all requests
        if not self.auth_enabled:
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized(
                "Missing or malformed Authorization header. Expected: Bearer <token>"
            )

        provided_token = auth_header[7:]  # Strip "Bearer " prefix

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_token, self._token):  # type: ignore[arg-type]
            logger.warning(
                "Failed authentication attempt from %s for %s",
                request.client.host if request.client else "unknown",
                request.url.path,
            )
            return _unauthorized("Invalid bearer token.")

        return await call_next(request)


def _unauthorized(message: str) -> JSONResponse:
    """Return a 401 Unauthorized JSON response."""
    return JSONResponse(
        {"error": "unauthorized", "message": message},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )
