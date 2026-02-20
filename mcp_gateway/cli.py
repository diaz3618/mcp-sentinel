"""CLI argument parsing and main entry point."""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

import uvicorn

from mcp_gateway.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from mcp_gateway.display.logging_config import setup_logging

module_logger = logging.getLogger(__name__)

uvicorn_svr_inst: Optional[uvicorn.Server] = None


async def main_async(host: str, port: int, log_lvl_cli: str) -> None:
    """Async main function to start and manage the Uvicorn server."""
    global uvicorn_svr_inst

    log_fpath, cfg_log_lvl = setup_logging(log_lvl_cli)

    module_logger.info(
        f"---- {SERVER_NAME} v{SERVER_VERSION} starting "
        f"(file log level: {cfg_log_lvl}) ----"
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    cfg_abs_path = os.path.join(project_dir, "config.json")
    module_logger.info(f"Configuration file path resolved to: {cfg_abs_path}")

    # Import app here to avoid circular imports at module level
    from mcp_gateway.server.app import app

    app_s = app.state
    app_s.host = host
    app_s.port = port
    app_s.actual_log_file = log_fpath
    app_s.file_log_level_configured = cfg_log_lvl
    app_s.config_file_path = cfg_abs_path
    module_logger.debug("Configuration parameters stored in app.state.")

    uvicorn_cfg = uvicorn.Config(
        app="mcp_gateway.server.app:app",
        host=host,
        port=port,
        log_config=None,
        log_level=cfg_log_lvl.lower() if cfg_log_lvl == "DEBUG" else "warning",
    )
    uvicorn_svr_inst = uvicorn.Server(uvicorn_cfg)

    module_logger.info(
        f"Preparing to start Uvicorn server: http://{host}:{port}"
    )
    try:
        await uvicorn_svr_inst.serve()
    except (KeyboardInterrupt, SystemExit) as e_exit:
        module_logger.info(
            f"Server stopped due to '{type(e_exit).__name__}'."
        )
    except Exception as e_serve:
        module_logger.exception(
            f"Unexpected error while running Uvicorn server: {e_serve}"
        )
        raise
    finally:
        module_logger.info(
            f"{SERVER_NAME} has shut down or is shutting down."
        )


def main() -> None:
    """Program entry point: parse arguments and start the async main."""
    parser = argparse.ArgumentParser(
        description=f"Start {SERVER_NAME} v{SERVER_VERSION}"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"Host address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set file logging level (default: info)",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        default=False,
        help="Disable the TUI and use plain console output",
    )
    args = parser.parse_args()

    # TODO: Phase 3 - When TUI is implemented, check args.no_tui
    # to decide between TUI and console mode.

    try:
        asyncio.run(
            main_async(
                host=args.host,
                port=args.port,
                log_lvl_cli=args.log_level,
            )
        )
    except KeyboardInterrupt:
        module_logger.info(
            f"{SERVER_NAME} main program interrupted by KeyboardInterrupt."
        )
    except SystemExit as e_sys_exit:
        if e_sys_exit.code is None or e_sys_exit.code == 0:
            module_logger.info(
                f"{SERVER_NAME} main program exited normally "
                f"(code: {e_sys_exit.code})."
            )
        else:
            module_logger.error(
                f"{SERVER_NAME} main program exited with SystemExit "
                f"(code: {e_sys_exit.code})."
            )
    except Exception as e_fatal:
        module_logger.exception(
            f"{SERVER_NAME} main program encountered an uncaught fatal error: "
            f"{e_fatal}"
        )
        sys.exit(1)
    finally:
        module_logger.info(f"{SERVER_NAME} application finished.")
