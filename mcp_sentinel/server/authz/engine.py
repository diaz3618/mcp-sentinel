"""Policy evaluation engine.

Evaluates authorization policies against a user's roles and the
requested resource.  First-match semantics: the first policy that
matches determines the outcome.  If no policy matches, the
``default_effect`` is used.

Usage::

    engine = PolicyEngine(policies, default_effect="deny")
    decision = engine.evaluate(user_roles=["admin"], resource="tool:read_file")
"""

from __future__ import annotations

import logging
from typing import List

from mcp_sentinel.server.authz.policies import AuthzPolicy, PolicyDecision, load_policies

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluates authorization policies.

    Parameters
    ----------
    policies:
        Ordered list of policies.  First match wins.
    default_effect:
        Effect when no policy matches (``"allow"`` or ``"deny"``).
    """

    def __init__(
        self,
        policies: List[AuthzPolicy],
        default_effect: str = "deny",
    ) -> None:
        self._policies = list(policies)
        self._default = PolicyDecision.ALLOW if default_effect == "allow" else PolicyDecision.DENY

    def evaluate(
        self,
        user_roles: List[str],
        resource: str,
    ) -> PolicyDecision:
        """Evaluate policies for the given *user_roles* and *resource*.

        Returns :attr:`PolicyDecision.ALLOW` or :attr:`PolicyDecision.DENY`.
        """
        for policy in self._policies:
            if policy.matches(user_roles, resource):
                logger.debug(
                    "Policy match: %s → %s (resource=%s, roles=%s)",
                    policy.description or policy.effect,
                    policy.effect,
                    resource,
                    user_roles,
                )
                return PolicyDecision.ALLOW if policy.effect == "allow" else PolicyDecision.DENY

        logger.debug(
            "No policy match for resource=%s, roles=%s → default=%s",
            resource,
            user_roles,
            self._default.value,
        )
        return self._default

    def filter_allowed(
        self,
        user_roles: List[str],
        resources: List[str],
    ) -> List[str]:
        """Return only the *resources* the user is allowed to access.

        Used to filter ``list_tools`` responses.
        """
        return [r for r in resources if self.evaluate(user_roles, r) == PolicyDecision.ALLOW]

    def reload(self, policy_dicts: List[dict]) -> None:
        """Hot-reload policies from config (no restart needed)."""
        self._policies = load_policies(policy_dicts)
        logger.info("Authorization policies reloaded: %d rules", len(self._policies))

    @classmethod
    def from_config(cls, config: dict) -> PolicyEngine:
        """Create from the ``authorization`` section of SentinelConfig."""
        policies = load_policies(config.get("policies", []))
        default_effect = config.get("default_effect", "deny")
        return cls(policies, default_effect=default_effect)
