"""Encrypted secret management.

Provides encrypted storage for API keys, tokens, and credentials
with resolution of ``secret:name`` references in configuration.
"""

from argus_mcp.secrets.resolver import resolve_secrets
from argus_mcp.secrets.store import SecretStore

__all__ = [
    "SecretStore",
    "resolve_secrets",
]
