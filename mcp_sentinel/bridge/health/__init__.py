"""Health monitoring package for backend MCP servers.

Public API
----------
- :class:`HealthChecker` — Background health-check scheduler
- :class:`BackendHealth` — Per-backend health record
- :class:`HealthState` — Observed health enum
- :class:`CircuitBreaker` — Per-backend circuit breaker
- :class:`CircuitState` — Circuit breaker state enum
"""

from mcp_sentinel.bridge.health.checker import (
    BackendHealth,
    HealthChecker,
    HealthState,
)
from mcp_sentinel.bridge.health.circuit_breaker import CircuitBreaker, CircuitState

__all__ = [
    "BackendHealth",
    "CircuitBreaker",
    "CircuitState",
    "HealthChecker",
    "HealthState",
]
