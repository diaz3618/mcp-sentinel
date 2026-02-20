import asyncio
import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request

from mcp import ClientSession
from mcp.server import Server as McpServer
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp import types as mcp_types

from config_loader import load_and_validate_config, ConfigurationError
from client_manager import ClientManager
from capability_registry import CapabilityRegistry
from errors import BackendServerError

SERVER_NAME = "MCP_Bridge_Server"
SERVER_VERSION = "3.0.1"
AUTHOR = "trtyr"
SSE_PATH = "/sse"
POST_MESSAGES_PATH = "/messages/"

DEFAULT_LOG_FPATH = "unknown_bridge_log.log"
DEFAULT_LOG_LVL = "INFO"

logger = logging.getLogger(__name__)

mcp_server = McpServer(SERVER_NAME)
mcp_server.manager: Optional[ClientManager] = None
mcp_server.registry: Optional[CapabilityRegistry] = None
logger.debug(f"Underlying MCP server instance '{mcp_server.name}' created.")


def _gen_status_info(app_state: Optional[object],
                     status_msg: str,
                     tools: Optional[List[mcp_types.Tool]] = None,
                     resources: Optional[List[mcp_types.Resource]] = None,
                     prompts: Optional[List[mcp_types.Prompt]] = None,
                     err_msg: Optional[str] = None,
                     conn_svrs_num: Optional[int] = None,
                     total_svrs_num: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate a structured dictionary of status information.
    """
    host = getattr(app_state, 'host', 'N/A') if app_state else 'N/A'
    port = getattr(app_state, 'port', 0) if app_state else 0

    info: Dict[str, Any] = {
        "ts":
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status_msg":
        status_msg,
        "host":
        host,
        "port":
        port,
        "log_fpath":
        getattr(app_state, 'actual_log_file', DEFAULT_LOG_FPATH)
        if app_state else DEFAULT_LOG_FPATH,
        "log_lvl_cfg":
        getattr(app_state, 'file_log_level_configured', DEFAULT_LOG_LVL)
        if app_state else DEFAULT_LOG_LVL,
        "sse_url":
        f"http://{host}:{port}{SSE_PATH}" if port > 0 else "N/A",
        "cfg_fpath":
        getattr(app_state, 'config_file_path', 'N/A') if app_state else 'N/A',
        "err_msg":
        err_msg,
        "tools":
        tools or [],
        "resources":
        resources or [],
        "prompts":
        prompts or []
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
    return info


def disp_console_status(stage: str,
                        status_info: Dict[str, Any],
                        is_final: bool = False):
    """Print formatted status information to the console."""
    header = f" MCP Bridge Server v{SERVER_VERSION} (by {AUTHOR}) "
    sep_char = "="
    line_len = 70

    if not hasattr(disp_console_status, "header_printed") or is_final:
        print(f"\n{sep_char * line_len}")
        print(f"{header:-^{line_len}}")
        print(f"{sep_char * line_len}")
        if not is_final:
            disp_console_status.header_printed = True
        else:
            if hasattr(disp_console_status, "header_printed"):
                delattr(disp_console_status, "header_printed")

    print(f"[{status_info['ts']}] {stage} Status: {status_info['status_msg']}")

    if not is_final and stage == "🚀 Initialization":
        print(f"    Server Name: {SERVER_NAME}")
        print(f"    SSE URL: {status_info['sse_url']}")
        print(f"    Config File: {os.path.basename(status_info['cfg_fpath'])}")
        print(
            f"    Log File: {status_info['log_fpath']} (level: {status_info['log_lvl_cfg']})"
        )

    if "total_svrs_num" in status_info and "conn_svrs_num" in status_info:
        print(
            f"    Backend Services: {status_info['conn_svrs_num']} / {status_info['total_svrs_num']} connected"
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


def log_file_status(status_info: Dict[str, Any], log_lvl: int = logging.INFO):
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
            f"  Backend Services: {status_info['conn_svrs_num']}/{status_info['total_svrs_num']} connected"
        )
    if status_info.get("err_msg"):
        log_lines.append(f"  Error Details: {status_info['err_msg']}")

    for cap_type_plural, cap_key_count, cap_list_key in [
        ("Tools", "tools_count", "tools"),
        ("Resources", "resources_count", "resources"),
        ("Prompts", "prompts_count", "prompts")
    ]:
        if cap_key_count in status_info:
            log_lines.append(
                f"  Loaded MCP {cap_type_plural} ({status_info[cap_key_count]}):"
            )
            cap_list = status_info.get(cap_list_key, [])
            if cap_list:
                for item in cap_list:
                    desc = item.description.strip().split(
                        '\n')[0] if item.description else "-"
                    log_lines.append(f"    - {item.name}, Description: {desc}")
            elif status_info[cap_key_count] > 0:
                log_lines.append(
                    f"    Detail list for {cap_list_key} not provided in status_info for logging, but count is > 0."
                )
            else:
                log_lines.append(f"    No {cap_list_key} loaded.")

    logger.log(log_lvl, "\n".join(log_lines))


async def _setup_app_configs(app_state: object) -> Tuple[str, Dict[str, Any]]:
    """Load and validate the configuration file."""
    cfg_fpath = getattr(app_state, 'config_file_path', "config.json")
    logger.info(f"Loading configuration file: {cfg_fpath}")

    status_info_load = _gen_status_info(
        app_state, f"Loading configuration ({os.path.basename(cfg_fpath)})...")
    disp_console_status("📄 Config Load", status_info_load)
    log_file_status(status_info_load)

    config = load_and_validate_config(cfg_fpath)
    total_svrs = len(config)
    logger.info(f"Configuration loaded and validated successfully; {total_svrs} backend entries.")

    status_info_loaded = _gen_status_info(app_state,
                                          f"Configuration load complete; {total_svrs} backend services.",
                                          total_svrs_num=total_svrs)
    disp_console_status("📄 Config Load", status_info_loaded)
    return cfg_fpath, config


async def _connect_backends(
        manager: ClientManager, config: Dict[str, Any],
        app_state: object) -> Tuple[int, int, Dict[str, ClientSession]]:
    """Connect all backend servers."""
    total_svrs = len(config)
    status_msg_conn = f"Connecting {total_svrs} backend services..."
    status_info_conn_start = _gen_status_info(app_state,
                                              status_msg_conn,
                                              total_svrs_num=total_svrs)
    disp_console_status("🔌 Backend Connection", status_info_conn_start)
    log_file_status(status_info_conn_start)

    await manager.start_all(config)
    active_sessions = manager.get_all_sessions()
    conn_svrs = len(active_sessions)

    log_lvl_conn = logging.INFO
    if conn_svrs == 0 and total_svrs > 0:
        conn_msg_short = f"❌ All backend connections failed ({conn_svrs}/{total_svrs})"
        log_lvl_conn = logging.ERROR
    elif conn_svrs < total_svrs:
        conn_msg_short = f"⚠️ Partial backend connection failure ({conn_svrs}/{total_svrs})"
        log_lvl_conn = logging.WARNING
    else:
        conn_msg_short = (
            f"✅ All backend connections succeeded ({conn_svrs}/{total_svrs})"
            if total_svrs > 0 else "✅ (No backend services configured)"
        )

    status_info_conn_done = _gen_status_info(app_state,
                                             conn_msg_short,
                                             conn_svrs_num=conn_svrs,
                                             total_svrs_num=total_svrs)
    disp_console_status("🔌 Backend Connection", status_info_conn_done)
    log_file_status(status_info_conn_done, log_lvl=log_lvl_conn)

    if conn_svrs == 0 and total_svrs > 0:
        raise BackendServerError(
            f"Unable to connect to any backend server ({total_svrs} configured). Bridge server cannot start.")
    return conn_svrs, total_svrs, active_sessions


async def _discover_capabilities(
    registry: CapabilityRegistry, active_sessions: Dict[str, ClientSession],
    app_state: object, conn_svrs_num: int, total_svrs_num: int
) -> Tuple[List[mcp_types.Tool], List[mcp_types.Resource],
           List[mcp_types.Prompt]]:
    """Discover and register capabilities from all backends."""
    status_msg_disc = (
        f"Discovering MCP capabilities ({conn_svrs_num}/{total_svrs_num} services connected)..."
    )
    status_info_disc_start = _gen_status_info(app_state,
                                              status_msg_disc,
                                              conn_svrs_num=conn_svrs_num,
                                              total_svrs_num=total_svrs_num)
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
        logger.info("No active backend sessions, skipping capability discovery.")

    status_info_disc_done = _gen_status_info(app_state,
                                             "Capability discovery and registration complete.",
                                             tools=tools,
                                             resources=resources,
                                             prompts=prompts,
                                             conn_svrs_num=conn_svrs_num,
                                             total_svrs_num=total_svrs_num)

    disp_console_status("🔍 Capability Discovery", status_info_disc_done)
    log_file_status(status_info_disc_done)
    return tools, resources, prompts


def _init_bridge_components(mcp_svr_instance: McpServer,
                            cli_manager: ClientManager,
                            cap_registry: CapabilityRegistry):
    """Initialize core bridge server components."""
    mcp_svr_instance.manager = cli_manager
    mcp_svr_instance.registry = cap_registry
    logger.info("ClientManager and CapabilityRegistry attached to mcp_server instance.")


@asynccontextmanager
async def app_lifespan(app: Starlette) -> AsyncIterator[None]:
    """Application lifespan management: startup and shutdown."""
    global mcp_server

    app_s = app.state
    logger.info(f"Bridge server '{SERVER_NAME}' v{SERVER_VERSION} startup sequence started...")
    logger.info(f"Author: {AUTHOR}")
    logger.debug(
        f"Lifespan received host='{getattr(app_s, 'host', 'N/A')}', port={getattr(app_s, 'port', 0)}"
    )
    logger.info(
        f"Configured file log level: {getattr(app_s, 'file_log_level_configured', DEFAULT_LOG_LVL)}"
    )
    logger.info(
        f"Actual log file: {getattr(app_s, 'actual_log_file', DEFAULT_LOG_FPATH)}")
    logger.info(
        f"Configuration file in use: {getattr(app_s, 'config_file_path', 'config.json')}")

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
        status_info_init = _gen_status_info(app_s, "Bridge server is starting...")
        disp_console_status("🚀 Initialization", status_info_init)
        log_file_status(status_info_init)

        _, config_data = await _setup_app_configs(app_s)
        conn_svrs, total_svrs, active_sess = await _connect_backends(
            cli_mgr, config_data, app_s)
        tools, resources, prompts = await _discover_capabilities(
            cap_reg, active_sess, app_s, conn_svrs, total_svrs)
        _init_bridge_components(mcp_server, cli_mgr, cap_reg)

        logger.info("Lifespan startup phase completed successfully.")
        startup_ok = True

        status_info_ready = _gen_status_info(app_s,
                                             "Server started successfully and is ready.",
                                             tools=tools,
                                             resources=resources,
                                             prompts=prompts,
                                             conn_svrs_num=conn_svrs,
                                             total_svrs_num=total_svrs)
        disp_console_status("✅ Service Ready", status_info_ready)
        log_file_status(status_info_ready)
        yield

    except ConfigurationError as e_cfg:
        logger.exception(f"Configuration error: {e_cfg}")
        err_detail_msg = f"Configuration error: {e_cfg}"
        status_info_fail = _gen_status_info(app_s,
                                            "Server startup failed.",
                                            err_msg=err_detail_msg,
                                            total_svrs_num=total_svrs)
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    except BackendServerError as e_backend:
        logger.exception(f"Backend error: {e_backend}")
        err_detail_msg = f"Backend error: {e_backend}"
        status_info_fail = _gen_status_info(app_s,
                                            "Server startup failed.",
                                            err_msg=err_detail_msg,
                                            conn_svrs_num=conn_svrs,
                                            total_svrs_num=total_svrs)
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    except Exception as e_exc:
        logger.exception(f"Unexpected error during lifespan startup: {e_exc}")
        err_detail_msg = f"Unexpected error: {type(e_exc).__name__} - {e_exc}"
        status_info_fail = _gen_status_info(app_s,
                                            "Server startup failed.",
                                            err_msg=err_detail_msg,
                                            conn_svrs_num=conn_svrs,
                                            total_svrs_num=total_svrs)
        disp_console_status("❌ Startup Failed", status_info_fail)
        log_file_status(status_info_fail, log_lvl=logging.ERROR)
        raise
    finally:
        logger.info(f"Bridge server '{SERVER_NAME}' shutdown sequence started...")
        status_info_shutdown = _gen_status_info(app_s,
                                                "Server is shutting down...",
                                                tools=tools,
                                                resources=resources,
                                                prompts=prompts,
                                                conn_svrs_num=conn_svrs,
                                                total_svrs_num=total_svrs)
        disp_console_status("🛑 Shutting Down", status_info_shutdown, is_final=False)
        log_file_status(status_info_shutdown, log_lvl=logging.WARNING)

        active_manager = mcp_server.manager if mcp_server.manager else cli_mgr
        if active_manager:
            logger.info("Stopping all backend server connections...")
            await active_manager.stop_all()
            logger.info("Backend connections stopped.")
        else:
            logger.warning("ClientManager not initialized/attached; skipping stop step.")

        final_msg_short = (
            "Server shut down normally."
            if startup_ok else
            f"Server exited abnormally{(f' - Error: {err_detail_msg}' if err_detail_msg else '')}"
        )
        final_icon = "✅" if startup_ok else "❌"
        final_log_lvl = logging.INFO if startup_ok else logging.ERROR

        status_info_final = _gen_status_info(
            app_s,
            final_msg_short,
            err_msg=err_detail_msg if not startup_ok else None)
        disp_console_status(f"{final_icon} Final Status",
                            status_info_final,
                            is_final=True)
        log_file_status(status_info_final, log_lvl=final_log_lvl)
        logger.info(f"Bridge server '{SERVER_NAME}' shutdown sequence completed.")


async def _fwd_req_helper(cap_name_full: str, mcp_method: str,
                          args: Optional[Dict[str, Any]],
                          mcp_svr: McpServer) -> Any:
    """Helper to forward MCP requests to the correct backend server."""
    logger.info(
        f"Forwarding request: capability='{cap_name_full}', method='{mcp_method}', args={args}")

    registry = mcp_svr.registry
    manager = mcp_svr.manager

    if not registry or not manager:
        logger.error("registry or manager is unset during forwarding. This is a critical internal error.")
        raise BackendServerError("Internal bridge server error: core components not initialized.")

    route_info = registry.resolve_capability(cap_name_full)
    if not route_info:
        logger.warning(f"Unable to resolve capability name '{cap_name_full}'. MCP client should receive an error.")
        raise ValueError(f"Capability '{cap_name_full}' does not exist.")

    svr_name, orig_cap_name = route_info
    logger.debug(
        f"Capability '{cap_name_full}' resolved to server '{svr_name}' capability '{orig_cap_name}'.")

    session = manager.get_session(svr_name)
    if not session:
        logger.error(f"Unable to get active session for server '{svr_name}' while forwarding '{cap_name_full}'.")
        raise RuntimeError(
            f"Unable to connect to backend server '{svr_name}' providing '{cap_name_full}' "
            "(session missing or lost).")

    try:
        target_method_on_session = getattr(session, mcp_method)
    except AttributeError:
        logger.exception(f"Internal programming error: method '{mcp_method}' not found on ClientSession.")
        raise NotImplementedError(f"Internal bridge server error: forward method '{mcp_method}' not found.")

    try:
        logger.debug(
            f"Calling backend '{svr_name}' method '{mcp_method}' (original capability: '{orig_cap_name}')"
        )
        result: Any
        if mcp_method == "call_tool":
            result = await target_method_on_session(name=orig_cap_name,
                                                    arguments=args or {})
        elif mcp_method == "read_resource":
            content, mime_type = await target_method_on_session(
                name=orig_cap_name)
            result = mcp_types.ReadResourceResult(content=content,
                                                  mime_type=mime_type)
        elif mcp_method == "get_prompt":
            result = await target_method_on_session(name=orig_cap_name,
                                                    arguments=args)
        else:
            logger.error(f"Internal programming error: unknown forwarding method '{mcp_method}'.")
            raise NotImplementedError(
                f"Internal bridge server error: cannot handle request type '{mcp_method}'.")

        logger.info(
            f"Received backend result from '{svr_name}' for '{mcp_method}' (capability: '{cap_name_full}')."
        )
        return result
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout communicating with backend '{svr_name}' (capability: '{cap_name_full}', method: '{mcp_method}')."
        )
        raise
    except (ConnectionError, BrokenPipeError) as conn_e:
        logger.error(
            f"Connection lost to backend '{svr_name}' (capability: '{cap_name_full}', method: '{mcp_method}'): "
            f"{type(conn_e).__name__}"
        )
        raise
    except BackendServerError:
        logger.warning(f"Backend '{svr_name}' reported a server error while handling '{cap_name_full}'.")
        raise
    except Exception as e_fwd:
        logger.exception(
            f"Unexpected error forwarding request to backend '{svr_name}' "
            f"(capability: '{cap_name_full}', method: '{mcp_method}')"
        )
        raise BackendServerError(
            f"Unexpected backend error while handling request '{cap_name_full}' "
            f"from '{svr_name}': {type(e_fwd).__name__}"
        ) from e_fwd


@mcp_server.list_tools()
async def handle_list_tools() -> List[mcp_types.Tool]:
    logger.debug("Handling listTools request...")
    if not mcp_server.registry: raise BackendServerError("Registry is not initialized")
    tools = mcp_server.registry.get_aggregated_tools()
    logger.info(f"Returning {len(tools)} aggregated tools")
    return tools


@mcp_server.list_resources()
async def handle_list_resources() -> List[mcp_types.Resource]:
    logger.debug("Handling listResources request...")
    if not mcp_server.registry: raise BackendServerError("Registry is not initialized")
    resources = mcp_server.registry.get_aggregated_resources()
    logger.info(f"Returning {len(resources)} aggregated resources")
    return resources


@mcp_server.list_prompts()
async def handle_list_prompts() -> List[mcp_types.Prompt]:
    logger.debug("Handling listPrompts request...")
    if not mcp_server.registry: raise BackendServerError("Registry is not initialized")
    prompts = mcp_server.registry.get_aggregated_prompts()
    logger.info(f"Returning {len(prompts)} aggregated prompts")
    return prompts


@mcp_server.call_tool()
async def handle_call_tool(
        name: str, arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    logger.debug(f"Handling callTool: name='{name}'")
    result = await _fwd_req_helper(name, "call_tool", arguments, mcp_server)
    if isinstance(result, mcp_types.CallToolResult):
        return result.content
    logger.error(f"call_tool forwarding returned unexpected type: {type(result)} for tool '{name}'")
    raise BackendServerError(f"Backend returned invalid type for tool call '{name}'.")


@mcp_server.read_resource()
async def handle_read_resource(name: str) -> mcp_types.ReadResourceResult:
    logger.debug(f"Handling readResource: name='{name}'")
    result = await _fwd_req_helper(name, "read_resource", None, mcp_server)
    if isinstance(result, mcp_types.ReadResourceResult):
        return result
    logger.error(
        f"read_resource forwarding returned unexpected type: {type(result)} for resource '{name}'")
    raise BackendServerError(f"Backend returned invalid type for resource read '{name}'.")


@mcp_server.get_prompt()
async def handle_get_prompt(
        name: str,
        arguments: Optional[Dict[str,
                                 Any]] = None) -> mcp_types.GetPromptResult:
    logger.debug(f"Handling getPrompt: name='{name}'")
    typed_args: Optional[Dict[str, str]] = None
    if arguments is not None:
        try:
            typed_args = {k: str(v) for k, v in arguments.items()}
        except Exception:
            logger.warning(
                f"Could not cast get_prompt arguments to Dict[str, str] for prompt '{name}'. "
                "Will fall back to original arguments.",
                exc_info=True)
            pass

    result = await _fwd_req_helper(name, "get_prompt", typed_args or arguments,
                                   mcp_server)
    if isinstance(result, mcp_types.GetPromptResult):
        return result
    logger.error(f"get_prompt forwarding returned unexpected type: {type(result)} for prompt '{name}'")
    raise BackendServerError(f"Backend returned invalid type for prompt '{name}'.")


sse_transport = SseServerTransport(POST_MESSAGES_PATH)


async def handle_sse(request: Request) -> None:
    """Handle incoming SSE connection requests."""
    logger.debug(f"Received new SSE connection request (GET): {request.url}")
    global mcp_server
    if not mcp_server.manager or not mcp_server.registry:
        logger.error(
            "manager or registry is unset in handle_sse. Missing critical components; cannot handle SSE connection.")
        return

    async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
    ) as (read_stream, write_stream):
        try:
            srv_caps = {}
            if mcp_server.registry:
                srv_caps = mcp_server.get_capabilities(NotificationOptions(),
                                                       {})
            else:
                logger.warning(
                    "mcp_server.registry is unset; SSE initialization will use empty capabilities.")
            logger.debug(f"Server capabilities for SSE connection: {srv_caps}")
        except Exception as e_caps:
            logger.exception(
                f"Error getting mcp_server.get_capabilities for SSE connection: {e_caps}")
            srv_caps = {}

        init_opts = InitializationOptions(
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            capabilities=srv_caps,
        )
        logger.debug(
            f"Running mcp_server.run (MCP main loop) for SSE connection with options: {init_opts}"
        )
        await mcp_server.run(read_stream, write_stream, init_opts)
    logger.debug(f"SSE connection closed: {request.url}")


app: Starlette = Starlette(lifespan=app_lifespan,
                           routes=[
                               Route(SSE_PATH, endpoint=handle_sse),
                               Mount(POST_MESSAGES_PATH,
                                     app=sse_transport.handle_post_message),
                           ])
logger.info(
    f"Starlette ASGI app '{SERVER_NAME}' created. SSE GET on {SSE_PATH}, POST on {POST_MESSAGES_PATH}"
)
