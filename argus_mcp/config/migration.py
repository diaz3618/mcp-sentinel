"""Environment variable expansion for configuration values.

Handles ``${VAR}`` environment variable expansion in string values.
"""

from __future__ import annotations

import os
import re
from typing import Any

# Regex for ${VAR_NAME} — captures the variable name inside ${}
_ENV_VAR_RE = re.compile(r"\$\{(\w+)\}")


def expand_env_vars(value: Any) -> Any:
    """Recursively expand ``${VAR}`` references in string values.

    - If the env var is not set, the placeholder is left unchanged.
    - Non-string leaves are returned as-is.
    - Dicts and lists are walked recursively.
    """
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)),
            value,
        )
    if isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value
