"""Console status display and log-file status writing."""

import logging
import os
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from mcp import types as mcp_types

from mcp_gateway.constants import (
    AUTHOR,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_LEVEL,
    SERVER_NAME,
    SERVER_VERSION,
    SSE_PATH,
)

logger = logging.getLogger(__name__)

# ── Status callback system ──────────────────────────────────────
# When a TUI callback is registered, status updates are forwarded
# to the TUI instead of printing to stdout.

StatusCallback = Callable[[str, Dict[str, Any], bool], None]

_callback_lock = threading.Lock()
_status_callback: Optional[StatusCallback] = None
_suppress_console: bool = False


def set_status_callback(callback: StatusCallback, suppress_console: bool = True) -> None:
    """Register a callback that receives every status update.

    Args:
        callback: ``(stage, status_info, is_final) -> None``
        suppress_console: If *True*, ``disp_console_status`` will not
            print to stdout while the callback is active (TUI mode).
    """
    global _status_callback, _suppress_console
    with _callback_lock:
        _status_callback = callback
        _suppress_console = suppress_console


def clear_status_callback() -> None:
    """Remove the active status callback."""
    global _status_callback, _suppress_console
    with _callback_lock:
        _status_callback = None
        _suppress_console = False


def gen_status_info(
    app_state: Optional[object],
    status_msg: str,
    tools: Optional[List[mcp_types.Tool]] = None,
    resources: Optional[List[mcp_types.Resource]] = None,
    prompts: Optional[List[mcp_types.Prompt]] = None,
    err_msg: Optional[str] = None,
    conn_svrs_num: Optional[int] = None,
    total_svrs_num: Optional[int] = None,
    route_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a structured dictionary of status information."""
    host = getattr(app_state, "host", "N/A") if app_state else "N/A"
    port = getattr(app_state, "port", 0) if app_state else 0

    info: Dict[str, Any] = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status_msg": status_msg,
        "host": host,
        "port": port,
        "log_fpath": (
            getattr(app_state, "actual_log_file", DEFAULT_LOG_FILE)
            if app_state
            else DEFAULT_LOG_FILE
        ),
        "log_lvl_cfg": (
            getattr(app_state, "file_log_level_configured", DEFAULT_LOG_LEVEL)
            if app_state
            else DEFAULT_LOG_LEVEL
        ),
        "sse_url": f"http://{host}:{port}{SSE_PATH}" if port > 0 else "N/A",
        "cfg_fpath": (getattr(app_state, "config_file_path", "N/A") if app_state else "N/A"),
        "err_msg": err_msg,
        "tools": tools or [],
        "resources": resources or [],
        "prompts": prompts or [],
    }
    if tools is not None:
        info["tools_count"] = len(tools)
    if resources is not None:
        info["resources_count"] = len(resources)
    if prompts is not None:
        info["prompts_count"] = len(prompts)
    if conn_svrs_num is not None:
        info["conn_svrs_num"] = conn_svrs_num
    if total_svrs_num is not None:
        info["total_svrs_num"] = total_svrs_num
    if route_map is not None:
        info["route_map"] = route_map
    return info


def disp_console_status(stage: str, status_info: Dict[str, Any], is_final: bool = False) -> None:
    """Print formatted status information to the console.

    When a TUI callback is registered via ``set_status_callback``,
    the update is forwarded there instead of (or in addition to) stdout.
    """
    # Forward to registered callback (TUI mode)
    with _callback_lock:
        cb = _status_callback
        suppress = _suppress_console

    if cb is not None:
        try:
            cb(stage, status_info, is_final)
        except Exception:
            logger.debug("Status callback error", exc_info=True)

    # If console output is suppressed (TUI active), skip printing
    if suppress:
        return

    header = f" MCP Gateway v{SERVER_VERSION} (by {AUTHOR}) "
    sep_char = "="
    line_len = 70

    if not hasattr(disp_console_status, "header_printed") or is_final:
        print(f"\n{sep_char * line_len}")
        print(f"{header:-^{line_len}}")
        print(f"{sep_char * line_len}")
        if not is_final:
            disp_console_status.header_printed = True  # type: ignore[attr-defined]
        else:
            if hasattr(disp_console_status, "header_printed"):
                delattr(disp_console_status, "header_printed")

    print(f"[{status_info['ts']}] {stage} Status: {status_info['status_msg']}")

    if not is_final and stage == "🚀 Initialization":
        print(f"    Server Name: {SERVER_NAME}")
        print(f"    SSE URL: {status_info['sse_url']}")
        print(f"    Config File: {os.path.basename(status_info['cfg_fpath'])}")
        print(f"    Log File: {status_info['log_fpath']} " f"(level: {status_info['log_lvl_cfg']})")

    if "total_svrs_num" in status_info and "conn_svrs_num" in status_info:
        print(
            f"    Backend Services: {status_info['conn_svrs_num']} / "
            f"{status_info['total_svrs_num']} connected"
        )

    if "tools_count" in status_info:
        print(f"    MCP Tools: {status_info['tools_count']} loaded")
    if "resources_count" in status_info:
        print(f"    MCP Resources: {status_info['resources_count']} loaded")
    if "prompts_count" in status_info:
        print(f"    MCP Prompts: {status_info['prompts_count']} loaded")

    if status_info.get("err_msg"):
        print(f"    !! Error: {status_info['err_msg']}")

    if not is_final:
        print("-" * line_len)

    if is_final:
        print(f"    Log File: {status_info['log_fpath']}")
        print(f"{sep_char * line_len}\n")


def log_file_status(status_info: Dict[str, Any], log_lvl: int = logging.INFO) -> None:
    """Write detailed status information to the log file."""
    log_lines = [
        f"Server Status Update: {status_info['status_msg']}",
        f"  Author: {AUTHOR}",
        f"  SSE URL: {status_info['sse_url']}",
        f"  Config File Used: {status_info['cfg_fpath']}",
        f"  Configured File Log Level: {status_info['log_lvl_cfg']}",
        f"  Actual Log File: {status_info['log_fpath']}",
    ]
    if "total_svrs_num" in status_info and "conn_svrs_num" in status_info:
        log_lines.append(
            f"  Backend Services: {status_info['conn_svrs_num']}/"
            f"{status_info['total_svrs_num']} connected"
        )
    if status_info.get("err_msg"):
        log_lines.append(f"  Error Details: {status_info['err_msg']}")

    for cap_type_plural, cap_key_count, cap_list_key in [
        ("Tools", "tools_count", "tools"),
        ("Resources", "resources_count", "resources"),
        ("Prompts", "prompts_count", "prompts"),
    ]:
        if cap_key_count in status_info:
            log_lines.append(f"  Loaded MCP {cap_type_plural} " f"({status_info[cap_key_count]}):")
            cap_list = status_info.get(cap_list_key, [])
            if cap_list:
                for item in cap_list:
                    desc = item.description.strip().split("\n")[0] if item.description else "-"
                    log_lines.append(f"    - {item.name}, Description: {desc}")
            elif status_info[cap_key_count] > 0:
                log_lines.append(
                    f"    Detail list for {cap_list_key} not provided in "
                    "status_info for logging, but count is > 0."
                )
            else:
                log_lines.append(f"    No {cap_list_key} loaded.")

    logger.log(log_lvl, "\n".join(log_lines))
