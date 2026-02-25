"""Pydantic configuration models for MCP Sentinel.

Defines the validated config structure using the versioned v1 format.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

# ── Shared per-backend configs ───────────────────────────────────────────


class TimeoutConfig(BaseModel):
    """Per-backend timeout configuration. Defaults are used when not specified."""

    init: Optional[float] = Field(
        default=None,
        ge=0,
        description="MCP session initialization timeout in seconds.",
    )
    cap_fetch: Optional[float] = Field(
        default=None,
        ge=0,
        description="Capability list fetch timeout in seconds.",
    )
    sse_startup: Optional[float] = Field(
        default=None,
        ge=0,
        description="Wait time for local SSE server startup in seconds.",
    )


class CapabilityFilterConfig(BaseModel):
    """Per-capability-type allow/deny filter configuration."""

    allow: List[str] = Field(
        default_factory=list,
        description="Glob patterns for allowed capability names.",
    )
    deny: List[str] = Field(
        default_factory=list,
        description="Glob patterns for denied capability names.",
    )


class FiltersConfig(BaseModel):
    """Per-backend capability filters (tools, resources, prompts)."""

    tools: CapabilityFilterConfig = Field(default_factory=CapabilityFilterConfig)
    resources: CapabilityFilterConfig = Field(default_factory=CapabilityFilterConfig)
    prompts: CapabilityFilterConfig = Field(default_factory=CapabilityFilterConfig)


class ToolOverrideEntry(BaseModel):
    """Rename and/or override description for a single tool."""

    name: Optional[str] = Field(default=None, description="New name to expose to clients.")
    description: Optional[str] = Field(
        default=None, description="Override description for the tool."
    )


# ── Outgoing authentication ──────────────────────────────────────────────


class StaticAuthConfig(BaseModel):
    """Static header-based authentication."""

    type: Literal["static"]
    headers: Dict[str, str] = Field(
        ..., min_length=1, description="Headers to inject (values support ${ENV_VAR})."
    )


class OAuth2AuthConfig(BaseModel):
    """OAuth 2.0 Client Credentials authentication."""

    type: Literal["oauth2"]
    token_url: str = Field(..., min_length=1, description="Token endpoint URL.")
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1, description="Supports ${ENV_VAR}.")
    scopes: List[str] = Field(default_factory=list)


AuthConfig = Annotated[
    Union[StaticAuthConfig, OAuth2AuthConfig],
    Field(discriminator="type"),
]


# ── Backend server configs ───────────────────────────────────────────────


class StdioBackendConfig(BaseModel):
    """Configuration for a stdio-type backend MCP server."""

    type: Literal["stdio"]
    command: str = Field(..., min_length=1, description="Executable to run")
    args: List[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    group: str = Field(default="default", description="Logical server group name.")
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    tool_overrides: Dict[str, ToolOverrideEntry] = Field(
        default_factory=dict,
        description="Per-tool rename and description overrides.",
    )
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)

    @field_validator("command")
    @classmethod
    def _strip_command(cls, v: str) -> str:
        return v.strip()


class SseBackendConfig(BaseModel):
    """Configuration for an SSE-type backend MCP server."""

    type: Literal["sse"]
    url: str = Field(..., min_length=1, description="SSE endpoint URL")
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Extra HTTP headers (e.g. Authorization). Supports ${ENV_VAR}.",
    )
    auth: Optional[AuthConfig] = Field(
        default=None,
        description="Outgoing authentication strategy for this backend.",
    )
    group: str = Field(default="default", description="Logical server group name.")
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    tool_overrides: Dict[str, ToolOverrideEntry] = Field(
        default_factory=dict,
        description="Per-tool rename and description overrides.",
    )
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL '{v}' must start with http:// or https://")
        return v

    @field_validator("command")
    @classmethod
    def _strip_command(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("command must be a non-empty string if provided")
        return v


class StreamableHttpBackendConfig(BaseModel):
    """Configuration for a streamable-http-type backend MCP server."""

    type: Literal["streamable-http"]
    url: str = Field(..., min_length=1, description="Streamable HTTP endpoint URL")
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Extra HTTP headers (e.g. Authorization). Supports ${ENV_VAR}.",
    )
    auth: Optional[AuthConfig] = Field(
        default=None,
        description="Outgoing authentication strategy for this backend.",
    )
    group: str = Field(default="default", description="Logical server group name.")
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    tool_overrides: Dict[str, ToolOverrideEntry] = Field(
        default_factory=dict,
        description="Per-tool rename and description overrides.",
    )
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL '{v}' must start with http:// or https://")
        return v


# Discriminated union: pick the right model based on "type" field
BackendConfig = Annotated[
    Union[StdioBackendConfig, SseBackendConfig, StreamableHttpBackendConfig],
    Field(discriminator="type"),
]


# ── Server settings ─────────────────────────────────────────────────────


class ManagementSettings(BaseModel):
    """Management API configuration."""

    enabled: bool = True
    token: Optional[str] = Field(
        default=None,
        description="Bearer token for /manage/ endpoints. Also SENTINEL_MGMT_TOKEN env var.",
    )


class ServerSettings(BaseModel):
    """Sentinel server settings (host, port, transport, management)."""

    host: str = "127.0.0.1"
    port: int = Field(default=9000, ge=1, le=65535)
    transport: Literal["sse", "streamable-http"] = "streamable-http"
    management: ManagementSettings = Field(default_factory=ManagementSettings)

    @field_validator("transport", mode="before")
    @classmethod
    def _normalise_transport(cls, v: str) -> str:
        """Accept 'http' as a shorthand for 'streamable-http'."""
        if isinstance(v, str) and v.strip().lower() == "http":
            return "streamable-http"
        return v


# ── Conflict resolution config ───────────────────────────────────────────


class ConflictResolutionConfig(BaseModel):
    """Configuration for capability name conflict resolution."""

    strategy: Literal["first-wins", "prefix", "priority", "error"] = Field(
        default="first-wins",
        description="Strategy for handling duplicate capability names across backends.",
    )
    separator: str = Field(
        default="_",
        description="Separator for prefix-based naming (e.g. 'server_tool').",
    )
    order: List[str] = Field(
        default_factory=list,
        description="Server priority list for 'priority' strategy (higher = first).",
    )


# ── Top-level config ────────────────────────────────────────────────────


class AuditConfig(BaseModel):
    """Audit logging settings."""

    enabled: bool = Field(default=True, description="Enable audit event logging.")
    file: str = Field(
        default="logs/audit.jsonl",
        description="Path to the JSON-line audit log file.",
    )
    max_size_mb: int = Field(default=100, ge=1, description="Max file size in MB before rotation.")
    backup_count: int = Field(
        default=5, ge=0, description="Number of rotated backup files to keep."
    )


class OptimizerConfig(BaseModel):
    """Tool optimizer (find_tool / call_tool) settings."""

    enabled: bool = Field(
        default=False,
        description="Enable the optimizer — replaces full tool catalog with find_tool + call_tool.",
    )
    keep_tools: List[str] = Field(
        default_factory=list,
        description="Tool names to always expose alongside the meta-tools.",
    )


class IncomingAuthConfig(BaseModel):
    """Incoming authentication config for the MCP data plane.

    Controls how connecting MCP clients are authenticated.
    """

    type: Literal["anonymous", "local", "jwt", "oidc"] = Field(
        default="anonymous",
        description="Auth type: anonymous (no auth), local (static token), jwt, or oidc.",
    )
    token: Optional[str] = Field(
        default=None,
        description="Static bearer token (for 'local' type). Supports ${ENV_VAR}.",
    )
    jwks_uri: Optional[str] = Field(
        default=None,
        description="JWKS URI for JWT key retrieval (for 'jwt' type).",
    )
    issuer: Optional[str] = Field(
        default=None,
        description="Expected JWT issuer (iss claim). For 'oidc' type, this is the discoverable issuer URL.",
    )
    audience: Optional[str] = Field(
        default=None,
        description="Expected JWT audience (aud claim).",
    )
    algorithms: List[str] = Field(
        default_factory=lambda: ["RS256", "ES256"],
        description="Allowed JWT signing algorithms.",
    )


class AuthorizationConfig(BaseModel):
    """Role-based authorization policy config."""

    enabled: bool = Field(default=False, description="Enable RBAC policy enforcement.")
    default_effect: Literal["allow", "deny"] = Field(
        default="deny",
        description="Default effect when no policy matches: 'allow' or 'deny'.",
    )
    policies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of authorization policy rules.",
    )


class SentinelConfig(BaseModel):
    """Top-level validated configuration for MCP Sentinel.

    Supports version ``"1"`` format::

        {
            "version": "1",
            "server": { ... },
            "backends": {
                "my-server": { "type": "stdio", ... }
            }
        }
    """

    version: str = "1"
    server: ServerSettings = Field(default_factory=ServerSettings)
    backends: Dict[str, BackendConfig] = Field(default_factory=dict)
    conflict_resolution: ConflictResolutionConfig = Field(default_factory=ConflictResolutionConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    incoming_auth: IncomingAuthConfig = Field(
        default_factory=IncomingAuthConfig,
        description="Incoming authentication for MCP data plane connections.",
    )
    authorization: AuthorizationConfig = Field(
        default_factory=AuthorizationConfig,
        description="Role-based authorization policy evaluation.",
    )
    feature_flags: Dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flag overrides (flag_name → enabled).",
    )

    @field_validator("backends")
    @classmethod
    def _validate_backend_names(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        for name in v:
            stripped = name.strip()
            if not stripped:
                raise ValueError("Backend name must be a non-empty string")
            if stripped != name:
                raise ValueError(f"Backend name '{name}' has leading/trailing whitespace")
        return v
