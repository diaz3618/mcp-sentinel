"""Application lifespan management - startup and shutdown sequences.

This module provides the Starlette ``lifespan`` async context manager that
delegates lifecycle management to :class:`~mcp_sentinel.runtime.SentinelService`.

The display/console status callbacks are kept here so that the runtime service
layer (``runtime/service.py``) remains presentation-agnostic and can be reused
by the management API (Phase 0.2).
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from starlette.applications import Starlette

from mcp_sentinel.constants import AUTHOR, SERVER_NAME, SERVER_VERSION
from mcp_sentinel.display.console import (
    disp_console_status,
    gen_status_info,
    log_file_status,
)
from mcp_sentinel.errors import BackendServerError, ConfigurationError
from mcp_sentinel.runtime.service import SentinelService

logger = logging.getLogger(__name__)

DEFAULT_LOG_FPATH = "unknown_sentinel.log"
DEFAULT_LOG_LVL = "INFO"


def _attach_to_mcp_server(
    mcp_svr_instance: Any,
    service: SentinelService,
) -> None:
    """Attach bridge components from the service to the MCP server instance.

    This preserves the existing monkey-patch pattern (mcp_server.manager /
    mcp_server.registry) until it is properly replaced in a later phase.
    Also builds and attaches the middleware chain and optimizer index.
    """
    from mcp_sentinel.audit import AuditLogger
    from mcp_sentinel.bridge.middleware import (
        AuditMiddleware,
        RecoveryMiddleware,
        RoutingMiddleware,
        build_chain,
    )
    from mcp_sentinel.bridge.optimizer import ToolIndex
    from mcp_sentinel.config.loader import load_sentinel_config

    mcp_svr_instance.manager = service.manager
    mcp_svr_instance.registry = service.registry

    # Initialise the structured audit logger
    audit_logger = AuditLogger()
    mcp_svr_instance.audit_logger = audit_logger

    # Build the middleware chain: Recovery → Audit → Routing (innermost).
    routing = RoutingMiddleware(service.registry, service.manager)
    chain = build_chain(
        middlewares=[RecoveryMiddleware(), AuditMiddleware(audit_logger=audit_logger)],
        handler=routing,
    )
    mcp_svr_instance.middleware_chain = chain
    logger.info(
        "ClientManager, CapabilityRegistry, and middleware chain "
        "attached to mcp_server instance."
    )

    # ── Optimizer (Task 3.1) ─────────────────────────────────────────
    optimizer_enabled = False
    keep_list: list[str] = []
    config_path = getattr(service, "_config_path", None)
    if config_path:
        try:
            full_cfg = load_sentinel_config(config_path)
            optimizer_enabled = full_cfg.optimizer.enabled
            keep_list = list(full_cfg.optimizer.keep_tools)
        except Exception:
            logger.debug("Could not read optimizer config; defaulting to disabled.")

    mcp_svr_instance.optimizer_enabled = optimizer_enabled
    mcp_svr_instance.optimizer_keep_list = keep_list

    if optimizer_enabled:
        tool_index = ToolIndex()
        tools = service.registry.get_aggregated_tools()
        route_map = service.registry.get_route_map()
        tool_index.store(tools, route_map)
        mcp_svr_instance.optimizer_index = tool_index
        logger.info(
            "Optimizer enabled: indexed %d tool(s), keep-list=%s.",
            tool_index.tool_count,
            keep_list or "(none)",
        )
    else:
        mcp_svr_instance.optimizer_index = None
        logger.debug("Optimizer disabled.")

    # ── Session Manager (Task 3.2) ───────────────────────────────────
    from mcp_sentinel.server.session import SessionManager

    session_manager = SessionManager()
    session_manager.start()
    mcp_svr_instance.session_manager = session_manager
    logger.info("SessionManager attached to mcp_server instance.")

    # ── Feature Flags (Task 3.8) ─────────────────────────────────────
    from mcp_sentinel.config.flags import FeatureFlags

    ff_overrides: dict[str, bool] = {}
    if config_path:
        try:
            _cfg = load_sentinel_config(config_path)
            ff_overrides = dict(_cfg.feature_flags)
        except Exception:
            logger.debug("Could not read feature_flags config; using defaults.")

    mcp_svr_instance.feature_flags = FeatureFlags(ff_overrides)
    logger.info("Feature flags: %s", mcp_svr_instance.feature_flags)


@asynccontextmanager
async def app_lifespan(app: Starlette) -> AsyncIterator[None]:
    """Application lifespan management: startup and shutdown.

    Creates a :class:`SentinelService`, drives its lifecycle, and decorates
    each phase with display/console status updates for the TUI / ``--no-tui``
    console.
    """
    from mcp_sentinel.server.app import mcp_server

    app_s = app.state
    logger.info(
        "Server '%s' v%s startup sequence started...",
        SERVER_NAME,
        SERVER_VERSION,
    )
    logger.info("Author: %s", AUTHOR)
    logger.debug(
        "Lifespan received host='%s', port=%s",
        getattr(app_s, "host", "N/A"),
        getattr(app_s, "port", 0),
    )
    logger.info(
        "Configured file log level: %s",
        getattr(app_s, "file_log_level_configured", DEFAULT_LOG_LVL),
    )
    logger.info(
        "Actual log file: %s",
        getattr(app_s, "actual_log_file", DEFAULT_LOG_FPATH),
    )

    config_path: str = getattr(app_s, "config_file_path", "")
    if not config_path:
        # Fallback auto-detect (should rarely hit — CLI sets this)
        from mcp_sentinel.cli import _find_config_file

        config_path = _find_config_file()
    logger.info("Configuration file in use: %s", config_path)

    service = SentinelService()
    # Store service on app.state so management API can access it later (0.2).
    app_s.sentinel_service = service  # type: ignore[attr-defined]

    # Also propagate to the management sub-app so its request handlers see
    # sentinel_service on *their* request.app.state (the sub-app's state).
    mgmt_app = getattr(app_s, "mgmt_app", None)
    if mgmt_app is not None:
        mgmt_app.state.sentinel_service = service  # type: ignore[attr-defined]
        # Forward host/port/transport so the status endpoint can build
        # correct URLs (the mgmt sub-app has its own State object).
        mgmt_app.state.host = getattr(app_s, "host", "127.0.0.1")  # type: ignore[attr-defined]
        mgmt_app.state.port = getattr(app_s, "port", 0)  # type: ignore[attr-defined]
        mgmt_app.state.transport_type = getattr(app_s, "transport_type", "streamable-http")  # type: ignore[attr-defined]

    startup_ok = False
    err_detail_msg: Optional[str] = None

    try:
        # ── Display: initializing ────────────────────────────────────
        status_info_init = gen_status_info(app_s, "Server is starting...")
        disp_console_status("Initialization", status_info_init)
        log_file_status(status_info_init)

        # ── Delegate full startup to SentinelService ─────────────────
        await service.start(config_path)

        # ── Monkey-patch bridge components onto mcp_server ───────────
        _attach_to_mcp_server(mcp_server, service)

        logger.info("Lifespan startup phase completed successfully.")
        startup_ok = True

        # ── Display: ready ───────────────────────────────────────────
        status_info_ready = gen_status_info(
            app_s,
            "Server started successfully and is ready.",
            tools=service.tools,
            resources=service.resources,
            prompts=service.prompts,
            conn_svrs_num=service.backends_connected,
            total_svrs_num=service.backends_total,
            route_map=service.registry.get_route_map(),
        )
        disp_console_status("✅ Service Ready", status_info_ready)
        log_file_status(status_info_ready)
        yield

    except ConfigurationError as e_cfg:
        logger.exception("Configuration error: %s", e_cfg)
        err_detail_msg = f"Configuration error: {e_cfg}"
        status_info_fail = gen_status_info(
            app_s,
            "Server startup failed.",
            err_msg=err_detail_msg,
            total_svrs_num=service.backends_total,
        )
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    except BackendServerError as e_backend:
        logger.exception("Backend error: %s", e_backend)
        err_detail_msg = f"Backend error: {e_backend}"
        status_info_fail = gen_status_info(
            app_s,
            "Server startup failed.",
            err_msg=err_detail_msg,
            conn_svrs_num=service.backends_connected,
            total_svrs_num=service.backends_total,
        )
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    except Exception as e_exc:
        logger.exception(
            "Unexpected error during lifespan startup: %s",
            e_exc,
        )
        err_detail_msg = f"Unexpected error: {type(e_exc).__name__} - {e_exc}"
        status_info_fail = gen_status_info(
            app_s,
            "Server startup failed.",
            err_msg=err_detail_msg,
            conn_svrs_num=service.backends_connected,
            total_svrs_num=service.backends_total,
        )
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    finally:
        logger.info(
            "Server '%s' shutdown sequence started...",
            SERVER_NAME,
        )
        status_info_shutdown = gen_status_info(
            app_s,
            "Server is shutting down...",
            tools=service.tools,
            resources=service.resources,
            prompts=service.prompts,
            conn_svrs_num=service.backends_connected,
            total_svrs_num=service.backends_total,
        )
        disp_console_status("🛑 Shutting Down", status_info_shutdown, is_final=False)
        log_file_status(status_info_shutdown, log_lvl=logging.WARNING)

        # ── Delegate shutdown to SentinelService ─────────────────────
        # Stop session manager before stopping backends
        sm = getattr(mcp_server, "session_manager", None)
        if sm is not None:
            await sm.stop()
        await service.stop()

        final_msg_short = (
            "Server shut down normally."
            if startup_ok
            else (
                f"Server exited abnormally"
                f"{(f' - Error: {err_detail_msg}' if err_detail_msg else '')}"
            )
        )
        final_icon = "✅" if startup_ok else "❌"
        final_log_lvl = logging.INFO if startup_ok else logging.ERROR

        status_info_final = gen_status_info(
            app_s,
            final_msg_short,
            err_msg=err_detail_msg if not startup_ok else None,
        )
        disp_console_status(f"{final_icon} Final Status", status_info_final, is_final=True)
        log_file_status(status_info_final, log_lvl=final_log_lvl)
        logger.info(
            "Server '%s' shutdown sequence completed.",
            SERVER_NAME,
        )
