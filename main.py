import uvicorn
import argparse
import logging
import logging.config
import sys
import os
from datetime import datetime
import copy
from typing import Tuple, Optional
import asyncio

try:
    import bridge_app
except ImportError as e_imp:
    print(f"Fatal error: unable to import bridge_app.py. Ensure the file exists and is on PYTHONPATH. Error: {e_imp}",
        file=sys.stderr)
    sys.exit(1)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

BASE_LOG_CFG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple_file": {
            "format":
            '%(asctime)s - %(name)25s:%(lineno)-4d - %(levelname)-7s - %(message)s',
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
            "level": "INFO"
        },
        "uvicorn.error": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        "uvicorn.access": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "WARNING"
        },
        "starlette": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        "bridge_app": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        "client_manager": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        "capability_registry": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        "config_loader": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        __name__: {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
        "mcp": {
            "handlers": ["file_handler"],
            "propagate": False,
            "level": "INFO"
        },
    },
    "root": {
        "handlers": ["file_handler"],
        "level": "WARNING",
    },
}


def setup_logging(log_lvl_str: str) -> Tuple[str, str]:
    """
    Set up the logging system.
    Uses a timestamped dynamic filename and adjusts module log levels
    based on command-line arguments.
    """
    log_lvl_valid = log_lvl_str.upper()
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_lvl_valid not in valid_levels:
        print(f"Warning: invalid log level '{log_lvl_str}'. Using 'INFO'.")
        log_lvl_valid = 'INFO'

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_fpath = os.path.join(LOG_DIR,
                             f"bridge_server_{ts}_{log_lvl_valid}.log")

    log_cfg = copy.deepcopy(BASE_LOG_CFG)
    log_cfg['handlers']['file_handler']['filename'] = log_fpath

    app_loggers_cfg = [
        "bridge_app", "client_manager", "capability_registry", "config_loader",
        __name__, "mcp", "uvicorn", "uvicorn.error", "starlette"
    ]
    for name in app_loggers_cfg:
        if name in log_cfg['loggers']:
            log_cfg['loggers'][name]['level'] = log_lvl_valid
        else:
            log_cfg['loggers'][name] = {
                "handlers": ["file_handler"],
                "propagate": False,
                "level": log_lvl_valid
            }

    log_cfg['loggers']['uvicorn.access'][
        'level'] = 'INFO' if log_lvl_valid == 'DEBUG' else 'WARNING'
    log_cfg['root'][
        'level'] = log_lvl_valid if log_lvl_valid == 'DEBUG' else 'WARNING'

    try:
        logging.config.dictConfig(log_cfg)
        print(f"Logging initialized. File log level: {log_lvl_valid}, log file: {log_fpath}")
    except Exception as e_log_cfg:
        print(f"Error applying logging configuration: {e_log_cfg}", file=sys.stderr)

    return log_fpath, log_lvl_valid


uvicorn_svr_inst: Optional[uvicorn.Server] = None
module_logger = logging.getLogger(__name__)


async def main_async(host: str, port: int, log_lvl_cli: str):
    """Async main function to start and manage the Uvicorn server."""
    global uvicorn_svr_inst

    log_fpath, cfg_log_lvl = setup_logging(log_lvl_cli)

    module_logger.info(
        f"---- {bridge_app.SERVER_NAME} v{bridge_app.SERVER_VERSION} starting (file log level: {cfg_log_lvl}) ----"
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_abs_path = os.path.join(script_dir, "config.json")
    module_logger.info(f"Configuration file path resolved to: {cfg_abs_path}")

    if hasattr(bridge_app, 'app') and bridge_app.app:
        app_s = bridge_app.app.state
        app_s.host = host
        app_s.port = port
        app_s.actual_log_file = log_fpath
        app_s.file_log_level_configured = cfg_log_lvl
        app_s.config_file_path = cfg_abs_path
        module_logger.debug("Configuration parameters stored in app.state.")
    else:
        module_logger.error("Could not find 'app' object in bridge_app. Server cannot start.")
        sys.exit(1)

    uvicorn_cfg = uvicorn.Config(
        app="bridge_app:app",
        host=host,
        port=port,
        log_config=None,
        log_level=cfg_log_lvl.lower() if cfg_log_lvl == 'DEBUG' else 'warning',
    )
    uvicorn_svr_inst = uvicorn.Server(uvicorn_cfg)

    module_logger.info(f"Preparing to start Uvicorn server: http://{host}:{port}")
    try:
        await uvicorn_svr_inst.serve()
    except (KeyboardInterrupt, SystemExit) as e_exit:
        module_logger.info(f"Server stopped due to '{type(e_exit).__name__}'.")

    except Exception as e_serve:
        module_logger.exception(f"Unexpected error while running Uvicorn server: {e_serve}")
        raise
    finally:
        module_logger.info(f"{bridge_app.SERVER_NAME} has shut down or is shutting down.")


def main():
    """Program entry point: parse arguments and start the async main."""
    parser = argparse.ArgumentParser(description="Start MCP Bridge Server")
    parser.add_argument('--host',
                        type=str,
                        default='0.0.0.0',
                        help='Host address (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=9000, help='Port (default: 9000)')
    parser.add_argument(
        '--log-level',
        type=str,
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Set file logging level (default: info)')
    args = parser.parse_args()

    try:
        asyncio.run(
            main_async(host=args.host,
                       port=args.port,
                       log_lvl_cli=args.log_level))
    except KeyboardInterrupt:
        module_logger.info("MCP Bridge Server main program interrupted by KeyboardInterrupt.")
    except SystemExit as e_sys_exit:

        if e_sys_exit.code is None or e_sys_exit.code == 0:
            module_logger.info(
                f"MCP Bridge Server main program exited normally (code: {e_sys_exit.code}).")
        else:
            module_logger.error(
                f"MCP Bridge Server main program exited with SystemExit (code: {e_sys_exit.code})."
            )
    except Exception as e_fatal:
        module_logger.exception(f"MCP Bridge Server main program encountered an uncaught fatal error: {e_fatal}")
        sys.exit(1)
    finally:
        module_logger.info("MCP Bridge Server application finished.")


if __name__ == "__main__":
    main()
