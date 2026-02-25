"""Incoming authentication — JWT validation and OIDC discovery.

This package provides the *incoming* auth for MCP data plane
connections (separate from the outgoing auth in ``bridge.auth``
which handles credentials *sent to* backend servers).
"""

from mcp_sentinel.server.auth.jwt import JWTValidator
from mcp_sentinel.server.auth.oidc import OIDCDiscovery
from mcp_sentinel.server.auth.providers import AuthProviderRegistry, UserIdentity

__all__ = [
    "AuthProviderRegistry",
    "JWTValidator",
    "OIDCDiscovery",
    "UserIdentity",
]
