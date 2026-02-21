"""CLI argument parsing and main entry point."""

import argparse
import asyncio
import logging
import os
import signal
import sys
from typing import Optional

import uvicorn

from mcp_sentinel.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from mcp_sentinel.display.logging_config import setup_logging

module_logger = logging.getLogger(__name__)

uvicorn_svr_inst: Optional[uvicorn.Server] = None


async def main_async(host: str, port: int, log_lvl_cli: str) -> None:
    """Async main function to start and manage the Uvicorn server."""
    global uvicorn_svr_inst

    log_fpath, cfg_log_lvl = setup_logging(log_lvl_cli)

    module_logger.info(
        "---- %s v%s starting (file log level: %s) ----",
        SERVER_NAME,
        SERVER_VERSION,
        cfg_log_lvl,
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    cfg_abs_path = os.path.join(project_dir, "config.json")
    module_logger.info("Configuration file path resolved to: %s", cfg_abs_path)

    # Import app here to avoid circular imports at module level
    from mcp_sentinel.server.app import app

    app_s = app.state
    app_s.host = host
    app_s.port = port
    app_s.actual_log_file = log_fpath
    app_s.file_log_level_configured = cfg_log_lvl
    app_s.config_file_path = cfg_abs_path
    module_logger.debug("Configuration parameters stored in app.state.")

    uvicorn_cfg = uvicorn.Config(
        app="mcp_sentinel.server.app:app",
        host=host,
        port=port,
        log_config=None,
        log_level=cfg_log_lvl.lower() if cfg_log_lvl == "DEBUG" else "warning",
    )
    uvicorn_svr_inst = uvicorn.Server(uvicorn_cfg)

    module_logger.info("Preparing to start Uvicorn server: http://%s:%s", host, port)
    try:
        await uvicorn_svr_inst.serve()
    except (KeyboardInterrupt, SystemExit) as e_exit:
        module_logger.info("Server stopped due to '%s'.", type(e_exit).__name__)
    except Exception as e_serve:
        module_logger.exception("Unexpected error while running Uvicorn server: %s", e_serve)
        raise
    finally:
        module_logger.info("%s has shut down or is shutting down.", SERVER_NAME)


def main() -> None:
    """Program entry point: parse arguments and start the async main."""
    parser = argparse.ArgumentParser(description=f"Start {SERVER_NAME} v{SERVER_VERSION}")
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

    if args.no_tui:
        # Plain console mode — run Uvicorn directly on the main thread.
        # Install a signal handler so the first Ctrl+C triggers a
        # graceful shutdown and the second forces an exit.
        _force_exit_count = 0

        def _sigint_handler(sig: int, frame: object) -> None:
            nonlocal _force_exit_count
            _force_exit_count += 1
            if _force_exit_count >= 2:
                module_logger.info("Force exit requested (double Ctrl+C).")
                # Restore default handler and re-raise for clean exit
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                os._exit(1)
            module_logger.info("Ctrl+C received — shutting down…")
            print("\n[Ctrl+C] Shutting down gracefully… (press again to force)")
            if uvicorn_svr_inst is not None:
                uvicorn_svr_inst.should_exit = True

        signal.signal(signal.SIGINT, _sigint_handler)

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
                "%s main program interrupted by KeyboardInterrupt.",
                SERVER_NAME,
            )
        except SystemExit as e_sys_exit:
            if e_sys_exit.code is None or e_sys_exit.code == 0:
                module_logger.info(
                    "%s main program exited normally (code: %s).",
                    SERVER_NAME,
                    e_sys_exit.code,
                )
            else:
                module_logger.error(
                    "%s main program exited with SystemExit (code: %s).",
                    SERVER_NAME,
                    e_sys_exit.code,
                )
        except Exception as e_fatal:
            module_logger.exception(
                "%s main program encountered an uncaught fatal error: %s",
                SERVER_NAME,
                e_fatal,
            )
            sys.exit(1)
        finally:
            module_logger.info("%s application finished.", SERVER_NAME)
    else:
        # TUI mode (default) — Textual owns the main thread.
        # Save terminal state so we can guarantee restoration even
        # if the TUI crashes or misbehaves during shutdown.
        _saved_termios = None
        try:
            import termios

            _saved_termios = termios.tcgetattr(sys.stdin.fileno())
        except Exception:
            pass  # stdin may not be a real terminal (CI, pipe, etc.)

        try:
            from mcp_sentinel.tui.app import SentinelApp

            tui_app = SentinelApp(
                host=args.host,
                port=args.port,
                log_level=args.log_level,
            )
            tui_app.run()
        except ImportError as e_imp:
            print(
                f"Error: Textual is required for TUI mode but could not be "
                f"imported ({e_imp}). Use --no-tui for plain console output.",
                file=sys.stderr,
            )
            sys.exit(1)
        except KeyboardInterrupt:
            module_logger.info(
                "%s TUI interrupted by KeyboardInterrupt.", SERVER_NAME
            )
        except Exception as e_fatal:
            module_logger.exception(
                "%s TUI encountered an uncaught fatal error: %s",
                SERVER_NAME,
                e_fatal,
            )
            sys.exit(1)
        finally:
            # ── Aggressive terminal restoration ──────────────────
            # Textual puts the terminal in raw/noecho mode.  If the
            # driver's cleanup fails for any reason the terminal is
            # left invisible to the user.  We apply multiple layers
            # of restoration to guarantee a usable terminal.

            # 1) Python-level streams back to originals FIRST so any
            #    subsequent print() lands on the real terminal.
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            # 2) Restore saved termios attributes.
            if _saved_termios is not None:
                try:
                    import termios

                    fd = sys.stdin.fileno()
                    termios.tcsetattr(fd, termios.TCSANOW, _saved_termios)
                except Exception:
                    pass

            # 3) stty sane — nuclear option that re-enables echo,
            #    canonical mode, and sane line discipline.  Use
            #    subprocess.run for reliability over os.system.
            import subprocess as _sp

            try:
                _sp.run(
                    ["stty", "sane"],
                    stdin=sys.stdin,
                    stdout=_sp.DEVNULL,
                    stderr=_sp.DEVNULL,
                    timeout=2,
                )
            except Exception:
                # Final fallback via os.system
                try:
                    os.system("stty sane 2>/dev/null")
                except Exception:
                    pass

            # 4) Re-enable echo explicitly in case stty sane missed it
            try:
                import termios

                fd = sys.stdin.fileno()
                attrs = termios.tcgetattr(fd)
                attrs[3] |= termios.ECHO | termios.ICANON
                termios.tcsetattr(fd, termios.TCSANOW, attrs)
            except Exception:
                pass

            # 5) Print a newline so the shell prompt appears cleanly
            try:
                print()
            except Exception:
                pass

            module_logger.info("%s application finished.", SERVER_NAME)
