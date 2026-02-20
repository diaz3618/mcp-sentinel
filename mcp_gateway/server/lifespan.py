"""Application lifespan management - startup and shutdown sequences."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp import ClientSession
from mcp import types as mcp_types
from starlette.applications import Starlette

from mcp_gateway.bridge.capability_registry import CapabilityRegistry
from mcp_gateway.bridge.client_manager import ClientManager
from mcp_gateway.config import load_and_validate_config
from mcp_gateway.constants import SERVER_NAME, SERVER_VERSION, AUTHOR
from mcp_gateway.display.console import (
    disp_console_status,
    gen_status_info,
    log_file_status,
)
from mcp_gateway.errors import BackendServerError, ConfigurationError

logger = logging.getLogger(__name__)

DEFAULT_LOG_FPATH = "unknown_gateway.log"
DEFAULT_LOG_LVL = "INFO"


async def _setup_app_configs(
    app_state: object,
) -> tuple[str, Dict[str, Any]]:
    """Load and validate the configuration file."""
    import os

    cfg_fpath = getattr(app_state, "config_file_path", "config.json")
    logger.info(f"Loading configuration file: {cfg_fpath}")

    status_info_load = gen_status_info(
        app_state,
        f"Loading configuration ({os.path.basename(cfg_fpath)})...",
    )
    disp_console_status("📄 Config Load", status_info_load)
    log_file_status(status_info_load)

    config = load_and_validate_config(cfg_fpath)
    total_svrs = len(config)
    logger.info(
        f"Configuration loaded and validated successfully; "
        f"{total_svrs} backend entries."
    )

    status_info_loaded = gen_status_info(
        app_state,
        f"Configuration load complete; {total_svrs} backend services.",
        total_svrs_num=total_svrs,
    )
    disp_console_status("📄 Config Load", status_info_loaded)
    return cfg_fpath, config


async def _connect_backends(
    manager: ClientManager,
    config: Dict[str, Any],
    app_state: object,
) -> tuple[int, int, Dict[str, ClientSession]]:
    """Connect all backend servers."""
    total_svrs = len(config)
    status_msg_conn = f"Connecting {total_svrs} backend services..."
    status_info_conn_start = gen_status_info(
        app_state, status_msg_conn, total_svrs_num=total_svrs
    )
    disp_console_status("🔌 Backend Connection", status_info_conn_start)
    log_file_status(status_info_conn_start)

    await manager.start_all(config)
    active_sessions = manager.get_all_sessions()
    conn_svrs = len(active_sessions)

    log_lvl_conn = logging.INFO
    if conn_svrs == 0 and total_svrs > 0:
        conn_msg_short = (
            f"❌ All backend connections failed ({conn_svrs}/{total_svrs})"
        )
        log_lvl_conn = logging.ERROR
    elif conn_svrs < total_svrs:
        conn_msg_short = (
            f"⚠️ Partial backend connection failure ({conn_svrs}/{total_svrs})"
        )
        log_lvl_conn = logging.WARNING
    else:
        conn_msg_short = (
            f"✅ All backend connections succeeded ({conn_svrs}/{total_svrs})"
            if total_svrs > 0
            else "✅ (No backend services configured)"
        )

    status_info_conn_done = gen_status_info(
        app_state,
        conn_msg_short,
        conn_svrs_num=conn_svrs,
        total_svrs_num=total_svrs,
    )
    disp_console_status("🔌 Backend Connection", status_info_conn_done)
    log_file_status(status_info_conn_done, log_lvl=log_lvl_conn)

    if conn_svrs == 0 and total_svrs > 0:
        raise BackendServerError(
            f"Unable to connect to any backend server ({total_svrs} configured). "
            "Gateway server cannot start."
        )
    return conn_svrs, total_svrs, active_sessions


async def _discover_capabilities(
    registry: CapabilityRegistry,
    active_sessions: Dict[str, ClientSession],
    app_state: object,
    conn_svrs_num: int,
    total_svrs_num: int,
) -> tuple[
    List[mcp_types.Tool], List[mcp_types.Resource], List[mcp_types.Prompt]
]:
    """Discover and register capabilities from all backends."""
    status_msg_disc = (
        f"Discovering MCP capabilities "
        f"({conn_svrs_num}/{total_svrs_num} services connected)..."
    )
    status_info_disc_start = gen_status_info(
        app_state,
        status_msg_disc,
        conn_svrs_num=conn_svrs_num,
        total_svrs_num=total_svrs_num,
    )
    disp_console_status("🔍 Capability Discovery", status_info_disc_start)
    log_file_status(status_info_disc_start)

    tools: List[mcp_types.Tool] = []
    resources: List[mcp_types.Resource] = []
    prompts: List[mcp_types.Prompt] = []

    if conn_svrs_num > 0:
        await registry.discover_and_register(active_sessions)
        tools = registry.get_aggregated_tools()
        resources = registry.get_aggregated_resources()
        prompts = registry.get_aggregated_prompts()
    else:
        logger.info(
            "No active backend sessions, skipping capability discovery."
        )

    status_info_disc_done = gen_status_info(
        app_state,
        "Capability discovery and registration complete.",
        tools=tools,
        resources=resources,
        prompts=prompts,
        conn_svrs_num=conn_svrs_num,
        total_svrs_num=total_svrs_num,
    )
    disp_console_status("🔍 Capability Discovery", status_info_disc_done)
    log_file_status(status_info_disc_done)
    return tools, resources, prompts


def _init_gateway_components(
    mcp_svr_instance: Any,
    cli_manager: ClientManager,
    cap_registry: CapabilityRegistry,
) -> None:
    """Attach core bridge components to the MCP server instance."""
    mcp_svr_instance.manager = cli_manager
    mcp_svr_instance.registry = cap_registry
    logger.info(
        "ClientManager and CapabilityRegistry attached to mcp_server instance."
    )


@asynccontextmanager
async def app_lifespan(app: Starlette) -> AsyncIterator[None]:
    """Application lifespan management: startup and shutdown."""
    from mcp_gateway.server.app import mcp_server

    app_s = app.state
    logger.info(
        f"Gateway server '{SERVER_NAME}' v{SERVER_VERSION} "
        "startup sequence started..."
    )
    logger.info(f"Author: {AUTHOR}")
    logger.debug(
        f"Lifespan received host='{getattr(app_s, 'host', 'N/A')}', "
        f"port={getattr(app_s, 'port', 0)}"
    )
    logger.info(
        f"Configured file log level: "
        f"{getattr(app_s, 'file_log_level_configured', DEFAULT_LOG_LVL)}"
    )
    logger.info(
        f"Actual log file: "
        f"{getattr(app_s, 'actual_log_file', DEFAULT_LOG_FPATH)}"
    )
    logger.info(
        f"Configuration file in use: "
        f"{getattr(app_s, 'config_file_path', 'config.json')}"
    )

    cli_mgr = ClientManager()
    cap_reg = CapabilityRegistry()
    startup_ok = False

    tools: List[mcp_types.Tool] = []
    resources: List[mcp_types.Resource] = []
    prompts: List[mcp_types.Prompt] = []
    err_detail_msg: Optional[str] = None
    conn_svrs: int = 0
    total_svrs: int = 0

    try:
        status_info_init = gen_status_info(
            app_s, "Gateway server is starting..."
        )
        disp_console_status("🚀 Initialization", status_info_init)
        log_file_status(status_info_init)

        _, config_data = await _setup_app_configs(app_s)
        conn_svrs, total_svrs, active_sess = await _connect_backends(
            cli_mgr, config_data, app_s
        )
        tools, resources, prompts = await _discover_capabilities(
            cap_reg, active_sess, app_s, conn_svrs, total_svrs
        )
        _init_gateway_components(mcp_server, cli_mgr, cap_reg)

        logger.info("Lifespan startup phase completed successfully.")
        startup_ok = True

        status_info_ready = gen_status_info(
            app_s,
            "Server started successfully and is ready.",
            tools=tools,
            resources=resources,
            prompts=prompts,
            conn_svrs_num=conn_svrs,
            total_svrs_num=total_svrs,
            route_map=cap_reg._route_map,
        )
        disp_console_status("✅ Service Ready", status_info_ready)
        log_file_status(status_info_ready)
        yield

    except ConfigurationError as e_cfg:
        logger.exception(f"Configuration error: {e_cfg}")
        err_detail_msg = f"Configuration error: {e_cfg}"
        status_info_fail = gen_status_info(
            app_s,
            "Server startup failed.",
            err_msg=err_detail_msg,
            total_svrs_num=total_svrs,
        )
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    except BackendServerError as e_backend:
        logger.exception(f"Backend error: {e_backend}")
        err_detail_msg = f"Backend error: {e_backend}"
        status_info_fail = gen_status_info(
            app_s,
            "Server startup failed.",
            err_msg=err_detail_msg,
            conn_svrs_num=conn_svrs,
            total_svrs_num=total_svrs,
        )
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    except Exception as e_exc:
        logger.exception(
            f"Unexpected error during lifespan startup: {e_exc}"
        )
        err_detail_msg = f"Unexpected error: {type(e_exc).__name__} - {e_exc}"
        status_info_fail = gen_status_info(
            app_s,
            "Server startup failed.",
            err_msg=err_detail_msg,
            conn_svrs_num=conn_svrs,
            total_svrs_num=total_svrs,
        )
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    finally:
        logger.info(
            f"Gateway server '{SERVER_NAME}' shutdown sequence started..."
        )
        status_info_shutdown = gen_status_info(
            app_s,
            "Server is shutting down...",
            tools=tools,
            resources=resources,
            prompts=prompts,
            conn_svrs_num=conn_svrs,
            total_svrs_num=total_svrs,
        )
        disp_console_status(
            "🛑 Shutting Down", status_info_shutdown, is_final=False
        )
        log_file_status(status_info_shutdown, log_lvl=logging.WARNING)

        active_manager = (
            mcp_server.manager if mcp_server.manager else cli_mgr
        )
        if active_manager:
            logger.info("Stopping all backend server connections...")
            await active_manager.stop_all()
            logger.info("Backend connections stopped.")
        else:
            logger.warning(
                "ClientManager not initialized/attached; skipping stop step."
            )

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
        disp_console_status(
            f"{final_icon} Final Status", status_info_final, is_final=True
        )
        log_file_status(status_info_final, log_lvl=final_log_lvl)
        logger.info(
            f"Gateway server '{SERVER_NAME}' shutdown sequence completed."
        )
