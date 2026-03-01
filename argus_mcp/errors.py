"""Custom exception classes for Argus MCP."""

from typing import Optional


class ArgusBaseError(Exception):
    """Base class for all custom exceptions in Argus MCP."""

    pass


class ConfigurationError(ArgusBaseError):
    """Raised when loading or validating the configuration file fails."""

    pass


class BackendServerError(ArgusBaseError):
    """
    Raised when interacting with a backend MCP server fails,
    or when a backend server reports an error.
    """

    def __init__(
        self,
        message: str,
        svr_name: Optional[str] = None,
        orig_exc: Optional[Exception] = None,
    ):
        self.svr_name = svr_name
        self.orig_exc = orig_exc

        full_msg = "Backend server error"
        if svr_name:
            full_msg += f" (server: {svr_name})"
        full_msg += f": {message}"
        if orig_exc:
            full_msg += f" (original error: {type(orig_exc).__name__})"
        super().__init__(full_msg)


class CapabilityConflictError(ArgusBaseError):
    """
    Raised when capability names conflict while aggregating from
    different backend servers.
    """

    def __init__(self, cap_name: str, svr1_name: str, svr2_name: str):
        message = (
            f"Capability name conflict: '{cap_name}' is provided by both "
            f"'{svr1_name}' and '{svr2_name}'. Ensure server names or "
            "capability prefixes are unique, or configure a conflict "
            "resolution strategy."
        )
        super().__init__(message)
