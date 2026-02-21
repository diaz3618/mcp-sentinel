"""Logging configuration setup."""

import copy
import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Tuple

from mcp_gateway.constants import LOG_DIR

BASE_LOG_CFG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple_file": {
            "format": (
                "%(asctime)s - %(name)25s:%(lineno)-4d - "
                "%(levelname)-7s - %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file_handler": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "simple_file",
            "filename": "temp_log_name.log",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "uvicorn.error": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "uvicorn.access": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "WARNING",
        },
        "starlette": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "mcp_gateway": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "mcp_gateway.server": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "mcp_gateway.bridge": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "mcp_gateway.config": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "mcp_gateway.display": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
        "mcp": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["file_handler"],
        "level": "WARNING",
    },
}


def setup_logging(log_lvl_str: str, *, quiet: bool = False) -> Tuple[str, str]:
    """
    Set up the logging system.

    Uses a timestamped dynamic filename and adjusts module log levels
    based on command-line arguments.

    Args:
        log_lvl_str: The desired log level string (e.g., 'debug', 'info').
        quiet: If *True*, suppress all ``print()`` output (TUI mode).

    Returns:
        A tuple of (log_file_path, validated_log_level).
    """
    log_lvl_valid = log_lvl_str.upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_lvl_valid not in valid_levels:
        if not quiet:
            print(f"Warning: invalid log level '{log_lvl_str}'. Using 'INFO'.")
        log_lvl_valid = "INFO"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(LOG_DIR, exist_ok=True)
    log_fpath = os.path.join(LOG_DIR, f"gateway_{ts}_{log_lvl_valid}.log")

    log_cfg: dict = copy.deepcopy(BASE_LOG_CFG)
    log_cfg["handlers"]["file_handler"]["filename"] = log_fpath

    app_loggers_cfg = [
        "mcp_gateway",
        "mcp_gateway.server",
        "mcp_gateway.bridge",
        "mcp_gateway.config",
        "mcp_gateway.display",
        "mcp",
        "uvicorn",
        "uvicorn.error",
        "starlette",
    ]
    for name in app_loggers_cfg:
        if name in log_cfg["loggers"]:
            log_cfg["loggers"][name]["level"] = log_lvl_valid
        else:
            log_cfg["loggers"][name] = {
                "handlers": ["file_handler"],
                "propagate": False,
                "level": log_lvl_valid,
            }

    log_cfg["loggers"]["uvicorn.access"]["level"] = (
        "INFO" if log_lvl_valid == "DEBUG" else "WARNING"
    )
    log_cfg["root"]["level"] = (
        log_lvl_valid if log_lvl_valid == "DEBUG" else "WARNING"
    )

    try:
        logging.config.dictConfig(log_cfg)
        if not quiet:
            print(
                f"Logging initialized. File log level: {log_lvl_valid}, "
                f"log file: {log_fpath}"
            )
    except Exception as e_log_cfg:
        if not quiet:
            print(
                f"Error applying logging configuration: {e_log_cfg}",
                file=sys.stderr,
            )

    return log_fpath, log_lvl_valid
