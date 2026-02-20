"""Configuration file loading and validation."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from mcp import StdioServerParameters

from mcp_gateway.errors import ConfigurationError

logger = logging.getLogger(__name__)


def _validate_str_list(data: Any, field_name: str, svr_name: str) -> List[str]:
    """Validate that the input is a list of strings."""
    if not isinstance(data, list):
        raise ConfigurationError(
            f"Server '{svr_name}' field '{field_name}' must be a list of strings."
        )

    validated: List[str] = []
    for i, item in enumerate(data):
        if not isinstance(item, str):
            raise ConfigurationError(
                f"Server '{svr_name}' field '{field_name}' item #{i + 1} must be a string."
            )
        validated.append(item)
    return validated


def _validate_str_dict(data: Any, field_name: str, svr_name: str) -> Dict[str, str]:
    """Validate that the input is a dict[str, str]."""
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Server '{svr_name}' field '{field_name}' must be a JSON object "
            "(dictionary with string keys and values)."
        )

    validated: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise ConfigurationError(
                f"Server '{svr_name}' field '{field_name}' must have string keys."
            )
        if not isinstance(value, str):
            raise ConfigurationError(
                f"Server '{svr_name}' field '{field_name}' value for key "
                f"'{key}' must be a string."
            )
        validated[key] = value
    return validated


def _validate_stdio_config(
    svr_name: str, srv_conf: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate and build a stdio server configuration entry."""
    cmd = srv_conf.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        raise ConfigurationError(
            f"Stdio server '{svr_name}' field 'command' must be a non-empty string."
        )

    cmd_args: List[str] = []
    if "args" in srv_conf:
        cmd_args = _validate_str_list(srv_conf["args"], "args", svr_name)

    cmd_env: Optional[Dict[str, str]] = None
    if "env" in srv_conf and srv_conf["env"] is not None:
        cmd_env = _validate_str_dict(srv_conf["env"], "env", svr_name)

    stdio_params = StdioServerParameters(
        command=cmd.strip(), args=cmd_args, env=cmd_env
    )
    return {"type": "stdio", "params": stdio_params}


def _validate_sse_config(
    svr_name: str, srv_conf: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate and build an SSE server configuration entry."""
    sse_url = srv_conf.get("url")
    if not isinstance(sse_url, str) or not sse_url.strip():
        raise ConfigurationError(
            f"SSE server '{svr_name}' field 'url' must be a non-empty string."
        )

    sse_url = sse_url.strip()
    if not sse_url.startswith(("http://", "https://")):
        raise ConfigurationError(
            f"SSE server '{svr_name}' field 'url' ('{sse_url}') does not look like "
            "a valid HTTP/HTTPS URL."
        )

    entry: Dict[str, Any] = {"type": "sse", "url": sse_url}

    if "command" in srv_conf:
        sse_cmd = srv_conf.get("command")
        if not isinstance(sse_cmd, str) or not sse_cmd.strip():
            raise ConfigurationError(
                f"SSE server '{svr_name}' field 'command' (for local startup) "
                "must be a non-empty string."
            )
        entry["command"] = sse_cmd.strip()

        sse_cmd_args: List[str] = []
        if "args" in srv_conf:
            sse_cmd_args = _validate_str_list(srv_conf["args"], "args", svr_name)
        entry["args"] = sse_cmd_args

        sse_cmd_env: Optional[Dict[str, str]] = None
        if "env" in srv_conf and srv_conf["env"] is not None:
            sse_cmd_env = _validate_str_dict(srv_conf["env"], "env", svr_name)
        entry["env"] = sse_cmd_env

    return entry


def load_and_validate_config(cfg_fpath: str) -> Dict[str, Dict[str, Any]]:
    """
    Load and validate a JSON configuration file.

    Returns a dictionary where keys are server names and values are
    validated/processed server configs.

    Raises:
        ConfigurationError: If the file is missing, malformed, or contains
            no valid server configurations.
    """
    logger.debug("Loading configuration file: %s", cfg_fpath)
    if not os.path.exists(cfg_fpath):
        logger.error("Configuration file not found: %s", cfg_fpath)
        raise ConfigurationError(f"Configuration file does not exist: {cfg_fpath}")

    try:
        with open(cfg_fpath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e_json:
        logger.error(
            "Failed to parse JSON configuration file '%s': %s",
            cfg_fpath, e_json,
            exc_info=True,
        )
        raise ConfigurationError(
            f"Unable to parse JSON configuration file: {cfg_fpath}, error: {e_json}"
        )
    except Exception as e_read:
        logger.error(
            "Unexpected error reading configuration file '%s': %s",
            cfg_fpath, e_read,
            exc_info=True,
        )
        raise ConfigurationError(
            f"Unexpected error reading configuration file: {cfg_fpath}, error: {e_read}"
        )

    if not isinstance(raw_data, dict):
        logger.error("Top-level configuration content must be a JSON object (dictionary).")
        raise ConfigurationError(
            "Top-level configuration content must be a JSON object (dictionary)."
        )

    validated_configs: Dict[str, Dict[str, Any]] = {}
    logger.debug("Found %s server configuration entries to validate.", len(raw_data))

    type_validators = {
        "stdio": _validate_stdio_config,
        "sse": _validate_sse_config,
    }

    for svr_name_raw, srv_conf_raw in raw_data.items():
        if not isinstance(svr_name_raw, str) or not svr_name_raw.strip():
            logger.warning(
                "Invalid server name key in config: '%s' (will be ignored). "
                "Name must be a non-empty string.",
                svr_name_raw,
            )
            continue

        svr_name = svr_name_raw.strip()

        if not isinstance(srv_conf_raw, dict):
            logger.warning(
                "Configuration for server '%s' must be a JSON object; got "
                "%s (will be ignored).",
                svr_name, type(srv_conf_raw),
            )
            continue

        svr_type = srv_conf_raw.get("type")
        if not isinstance(svr_type, str) or svr_type not in type_validators:
            logger.warning(
                "Server '%s' has invalid or missing 'type'. Must be 'stdio' "
                "or 'sse', got: %s (will be ignored).",
                svr_name, svr_type,
            )
            continue

        logger.debug("Validating server '%s' (type: %s)", svr_name, svr_type)

        try:
            validator = type_validators[svr_type]
            validated_configs[svr_name] = validator(svr_name, srv_conf_raw)
            logger.debug("Server '%s' configuration validated successfully.", svr_name)
        except ConfigurationError as e_svr_cfg:
            logger.error(
                "Invalid configuration for server '%s', skipped: %s",
                svr_name, e_svr_cfg,
            )
        except Exception as e_svr_unexpected:
            logger.error(
                "Unexpected error while processing server '%s', skipped: %s",
                svr_name, e_svr_unexpected,
                exc_info=True,
            )

    if not validated_configs and raw_data:
        logger.error("All server configurations in the file are invalid.")
        raise ConfigurationError(
            "No valid server configurations were found in the file."
        )
    elif not validated_configs:
        logger.info(
            "Configuration file '%s' is empty or contains no server entries.",
            cfg_fpath,
        )

    logger.info(
        "Configuration file '%s' loaded and validated. "
        "Processed %s valid server configurations.",
        cfg_fpath, len(validated_configs),
    )
    return validated_configs
