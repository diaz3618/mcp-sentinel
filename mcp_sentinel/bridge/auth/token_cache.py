"""Token caching with TTL-based expiry."""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_EXPIRY_BUFFER: float = 30.0  # Refresh this many seconds before expiry


class TokenCache:
    """Thread-safe in-memory token cache with expiry.

    Parameters
    ----------
    expiry_buffer:
        Number of seconds before actual token expiry to trigger a refresh.
    """

    def __init__(self, expiry_buffer: float = _DEFAULT_EXPIRY_BUFFER) -> None:
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._expiry_buffer = expiry_buffer

    @property
    def valid(self) -> bool:
        """``True`` if a cached token exists and has not expired."""
        return self._token is not None and time.monotonic() < self._expires_at

    def get(self) -> Optional[str]:
        """Return the cached token if still valid, else ``None``."""
        if self.valid:
            return self._token
        return None

    def set(self, token: str, expires_in: float) -> None:
        """Store *token* with a lifetime of *expires_in* seconds.

        The token will be considered expired ``expiry_buffer`` seconds
        before the actual TTL, ensuring a refresh happens in time.
        """
        effective_ttl = max(0.0, expires_in - self._expiry_buffer)
        self._token = token
        self._expires_at = time.monotonic() + effective_ttl
        logger.debug(
            "Token cached (expires_in=%.0fs, effective_ttl=%.0fs).",
            expires_in,
            effective_ttl,
        )

    def invalidate(self) -> None:
        """Clear the cached token."""
        self._token = None
        self._expires_at = 0.0
