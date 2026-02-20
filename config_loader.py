import json
import os
from typing import Dict, List, Optional, Any, Union

from mcp import StdioServerParameters
from errors import ConfigurationError

import logging

logger = logging.getLogger(__name__)


def _valid_str_list(data: Any, field_name: str, svr_name: str) -> List[str]:
    """Helper: validate that the input is a list of strings."""
    if not isinstance(data, list):
        raise ConfigurationError(
            f"Server '{svr_name}' field '{field_name}' must be a list of strings.")

    val_list: List[str] = []
    for i, item in enumerate(data):
        if not isinstance(item, str):
            raise ConfigurationError(
                f"Server '{svr_name}' field '{field_name}' item #{i+1} must be a string.")
        val_list.append(item)
    return val_list


def _valid_str_dict(data: Any, field_name: str,
                    svr_name: str) -> Dict[str, str]:
    """Helper: validate that the input is a dict[str, str]."""
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Server '{svr_name}' field '{field_name}' must be a JSON object "
            "(dictionary with string keys and values).")

    val_dict: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise ConfigurationError(
                f"Server '{svr_name}' field '{field_name}' must have string keys.")
        if not isinstance(value, str):
            raise ConfigurationError(
                f"Server '{svr_name}' field '{field_name}' value for key "
                f"'{key}' must be a string.")
        val_dict[key] = value
    return val_dict


def load_and_validate_config(cfg_fpath: str) -> Dict[str, Dict[str, Any]]:
    """
    Load and validate a JSON configuration file.
    Returns a dictionary where keys are server names and values are
    validated/processed server configs.
    """
    logger.debug(f"Loading configuration file: {cfg_fpath}")
    if not os.path.exists(cfg_fpath):
        logger.error(f"Configuration file not found: {cfg_fpath}")
        raise ConfigurationError(f"Configuration file does not exist: {cfg_fpath}")

    try:
        with open(cfg_fpath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e_json:
        logger.error(f"Failed to parse JSON configuration file '{cfg_fpath}': {e_json}", exc_info=True)
        raise ConfigurationError(f"Unable to parse JSON configuration file: {cfg_fpath}, error: {e_json}")
    except Exception as e_read:
        logger.error(f"Unexpected error reading configuration file '{cfg_fpath}': {e_read}", exc_info=True)
        raise ConfigurationError(f"Unexpected error reading configuration file: {cfg_fpath}, error: {e_read}")

    if not isinstance(raw_data, dict):
        logger.error("Top-level configuration content must be a JSON object (dictionary).")
        raise ConfigurationError("Top-level configuration content must be a JSON object (dictionary).")

    validated_configs: Dict[str, Dict[str, Any]] = {}
    logger.debug(f"Found {len(raw_data)} server configuration entries to validate.")

    for svr_name_raw, srv_conf_raw in raw_data.items():
        if not isinstance(svr_name_raw, str) or not svr_name_raw.strip():
            logger.warning(
                f"Invalid server name key in config: '{svr_name_raw}' (will be ignored). "
                "Name must be a non-empty string.")

            continue

        svr_name = svr_name_raw.strip()

        if not isinstance(srv_conf_raw, dict):
            logger.warning(
                f"Configuration for server '{svr_name}' must be a JSON object; got "
                f"{type(srv_conf_raw)} (will be ignored)."
            )
            continue

        srv_conf: Dict[str, Any] = srv_conf_raw

        svr_type = srv_conf.get("type")
        if not isinstance(svr_type, str) or svr_type not in ["stdio", "sse"]:
            logger.warning(
                f"Server '{svr_name}' has invalid or missing 'type'. Must be 'stdio' "
                f"or 'sse', got: {svr_type} (will be ignored)."
            )
            continue

        logger.debug(f"Validating server '{svr_name}' (type: {svr_type})")
        val_cfg_entry: Dict[str, Any] = {"type": svr_type}

        try:
            if svr_type == "stdio":
                cmd = srv_conf.get("command")
                if not isinstance(cmd, str) or not cmd.strip():
                    raise ConfigurationError(
                        f"Stdio server '{svr_name}' field 'command' must be a non-empty string.")

                cmd_args: List[str] = []
                if "args" in srv_conf:
                    cmd_args = _valid_str_list(srv_conf["args"], "args",
                                               svr_name)

                cmd_env: Optional[Dict[str, str]] = None
                if "env" in srv_conf and srv_conf["env"] is not None:
                    cmd_env = _valid_str_dict(srv_conf["env"], "env", svr_name)

                stdio_params = StdioServerParameters(command=cmd.strip(),
                                                     args=cmd_args,
                                                     env=cmd_env)
                val_cfg_entry["params"] = stdio_params

            elif svr_type == "sse":
                sse_url = srv_conf.get("url")
                if not isinstance(sse_url, str) or not sse_url.strip():
                    raise ConfigurationError(
                        f"SSE server '{svr_name}' field 'url' must be a non-empty string.")

                sse_url = sse_url.strip()
                if not sse_url.startswith(("http://", "https://")):
                    raise ConfigurationError(
                        f"SSE server '{svr_name}' field 'url' ('{sse_url}') does not look like "
                        "a valid HTTP/HTTPS URL."
                    )
                val_cfg_entry["url"] = sse_url

                if "command" in srv_conf:
                    sse_cmd = srv_conf.get("command")
                    if not isinstance(sse_cmd, str) or not sse_cmd.strip():
                        raise ConfigurationError(
                            f"SSE server '{svr_name}' field 'command' (for local startup) "
                            "must be a non-empty string."
                        )
                    val_cfg_entry['command'] = sse_cmd.strip()

                    sse_cmd_args: List[str] = []
                    if "args" in srv_conf:
                        sse_cmd_args = _valid_str_list(srv_conf["args"],
                                                       "args", svr_name)
                    val_cfg_entry['args'] = sse_cmd_args

                    sse_cmd_env: Optional[Dict[str, str]] = None
                    if "env" in srv_conf and srv_conf["env"] is not None:
                        sse_cmd_env = _valid_str_dict(srv_conf["env"], "env",
                                                      svr_name)
                    val_cfg_entry['env'] = sse_cmd_env

            validated_configs[svr_name] = val_cfg_entry
            logger.debug(f"Server '{svr_name}' configuration validated successfully.")

        except ConfigurationError as e_svr_cfg:
            logger.error(f"Invalid configuration for server '{svr_name}', skipped: {e_svr_cfg}")

        except Exception as e_svr_unexpected:
            logger.error(
                f"Unexpected error while processing server '{svr_name}', skipped: "
                f"{e_svr_unexpected}",
                exc_info=True)

    if not validated_configs and raw_data:
        logger.error("All server configurations in the file are invalid.")
        raise ConfigurationError("No valid server configurations were found in the file.")
    elif not validated_configs:
        logger.info(f"Configuration file '{cfg_fpath}' is empty or contains no server entries.")

    logger.info(
        f"Configuration file '{cfg_fpath}' loaded and validated. "
        f"Processed {len(validated_configs)} valid server configurations.")
    return validated_configs
