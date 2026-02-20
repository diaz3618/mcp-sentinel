"""Backend MCP server connection management."""

import asyncio
import logging
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

try:
    import httpx

    SSE_NET_EXCS: tuple = (
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    )
except ImportError:
    SSE_NET_EXCS = ()

from mcp_gateway.constants import MCP_INIT_TIMEOUT, SSE_LOCAL_START_DELAY
from mcp_gateway.errors import BackendServerError, ConfigurationError

logger = logging.getLogger(__name__)


async def _log_subproc_stream(
    stream: Optional[asyncio.StreamReader], svr_name: str, stream_name: str
) -> None:
    """Asynchronously read and log lines from subprocess streams."""
    if not stream:
        return
    while True:
        try:
            line_bytes = await stream.readline()
            if not line_bytes:
                logger.debug("[%s-%s] Stream ended (EOF).", svr_name, stream_name)
                break
            line = line_bytes.decode(errors="replace").strip()
            if line:
                logger.info("[%s-%s] %s", svr_name, stream_name, line)
        except asyncio.CancelledError:
            logger.debug("[%s-%s] Logging task was cancelled.", svr_name, stream_name)
            break
        except Exception as e_stream:
            logger.error(
                "[%s-%s] Error while reading stream: %s",
                svr_name, stream_name, e_stream,
                exc_info=True,
            )
            break


@asynccontextmanager
async def _manage_subproc(
    cmd_to_exec: str,
    args: List[str],
    proc_env: Optional[Dict[str, str]],
    svr_name: str,
) -> AsyncGenerator[asyncio.subprocess.Process, None]:
    """Async context manager for starting and stopping subprocesses."""
    process: Optional[asyncio.subprocess.Process] = None
    stdout_log_task: Optional[asyncio.Task] = None
    stderr_log_task: Optional[asyncio.Task] = None
    actual_cmd = cmd_to_exec

    try:
        py_exec = sys.executable or "python"
        actual_cmd = py_exec if cmd_to_exec.lower() == "python" else cmd_to_exec

        logger.info(
            "[%s] Preparing to start local process: '%s' args: %s",
            svr_name, actual_cmd, args,
        )

        current_env = os.environ.copy()
        if proc_env:
            current_env.update(proc_env)

        process = await asyncio.create_subprocess_exec(
            actual_cmd,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=current_env,
        )
        logger.info("[%s] Local process started (PID: %s).", svr_name, process.pid)

        if process.stdout:
            stdout_log_task = asyncio.create_task(
                _log_subproc_stream(process.stdout, svr_name, "stdout"),
                name=f"{svr_name}_stdout_logger",
            )
        if process.stderr:
            stderr_log_task = asyncio.create_task(
                _log_subproc_stream(process.stderr, svr_name, "stderr"),
                name=f"{svr_name}_stderr_logger",
            )
        yield process

    except FileNotFoundError:
        logger.error(
            "[%s] Failed to start local process: command '%s' not found.",
            svr_name, actual_cmd,
            exc_info=True,
        )
        raise
    except Exception:
        logger.error(
            "[%s] Unexpected error starting local process '%s'.",
            svr_name, actual_cmd,
            exc_info=True,
        )
        raise
    finally:
        if stdout_log_task and not stdout_log_task.done():
            stdout_log_task.cancel()
        if stderr_log_task and not stderr_log_task.done():
            stderr_log_task.cancel()

        if stdout_log_task or stderr_log_task:
            await asyncio.gather(
                stdout_log_task, stderr_log_task, return_exceptions=True
            )
            logger.debug("[%s] Subprocess stream logging tasks completed.", svr_name)

        if process and process.returncode is None:
            logger.info(
                "[%s] Attempting to terminate local process (PID: %s)...",
                svr_name, process.pid,
            )
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=3.0)
                logger.info(
                    "[%s] Local process (PID: %s) terminated successfully.",
                    svr_name, process.pid,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[%s] Timeout while terminating local process "
                    "(PID: %s), trying kill...",
                    svr_name, process.pid,
                )
                process.kill()
                await process.wait()
                logger.info(
                    "[%s] Local process (PID: %s) was force-killed.",
                    svr_name, process.pid,
                )
            except ProcessLookupError:
                logger.warning(
                    "[%s] Local process not found while terminating "
                    "(PID: %s).",
                    svr_name, process.pid,
                )
            except Exception as e_term:
                logger.error(
                    "[%s] Error terminating local process "
                    "(PID: %s): %s",
                    svr_name, process.pid, e_term,
                    exc_info=True,
                )


def _log_backend_fail(
    svr_name: str,
    svr_type: Optional[str],
    e: Exception,
    context: str = "startup",
) -> None:
    """Helper to log backend startup/connection failures."""
    svr_type_str = svr_type or "unknown type"
    if isinstance(e, asyncio.TimeoutError):
        logger.error("[%s] (%s) %s timed out.", svr_name, svr_type_str, context)
    elif isinstance(e, ConfigurationError):
        logger.error(
            "[%s] (%s) Configuration error during %s: %s",
            svr_name, svr_type_str, context, e,
        )
    elif isinstance(
        e, (*SSE_NET_EXCS, ConnectionRefusedError, BrokenPipeError, ConnectionError)
    ):
        logger.error(
            "[%s] (%s) Network/connection error during "
            "%s: %s: %s",
            svr_name, svr_type_str, context, type(e).__name__, e,
        )
    elif isinstance(e, FileNotFoundError):
        logger.error(
            "[%s] (local launch %s) Command or file not found "
            "'%s' during %s.",
            svr_name, svr_type_str, e.filename, context,
        )
    else:
        logger.exception(
            "[%s] (%s) Unexpected fatal error during %s.",
            svr_name, svr_type_str, context,
        )


class ClientManager:
    """Manages connections and sessions for all backend MCP servers."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ClientSession] = {}
        self._pending_tasks: Dict[str, asyncio.Task] = {}
        self._exit_stack = AsyncExitStack()
        logger.info("ClientManager initialized.")

    async def _init_stdio_backend(
        self, svr_name: str, stdio_cfg: StdioServerParameters
    ) -> Tuple[Any, ClientSession]:
        """Initialize and connect to a stdio backend server."""
        logger.debug("[%s] Stdio backend, preparing stdio_client.", svr_name)

        transport_ctx = stdio_client(stdio_cfg)
        streams = await self._exit_stack.enter_async_context(transport_ctx)
        logger.debug("[%s] (stdio) transport streams established.", svr_name)

        session_ctx = ClientSession(*streams)
        session = await self._exit_stack.enter_async_context(session_ctx)
        return transport_ctx, session

    async def _init_sse_backend(
        self,
        svr_name: str,
        sse_url: str,
        sse_cmd: Optional[str],
        sse_cmd_args: List[str],
        sse_cmd_env: Optional[Dict[str, str]],
    ) -> Tuple[Any, ClientSession]:
        """Initialize and connect to an SSE backend; launch command first if configured."""
        if sse_cmd:
            logger.info(
                "[%s] Local launch command configured, starting SSE subprocess...",
                svr_name,
            )
            await self._exit_stack.enter_async_context(
                _manage_subproc(sse_cmd, sse_cmd_args, sse_cmd_env, svr_name)
            )
            logger.info(
                "[%s] Waiting %ss for local SSE server startup...",
                svr_name, SSE_LOCAL_START_DELAY,
            )
            await asyncio.sleep(SSE_LOCAL_START_DELAY)

        transport_ctx = sse_client(url=sse_url)
        streams = await self._exit_stack.enter_async_context(transport_ctx)
        logger.debug("[%s] (sse) transport streams established.", svr_name)

        session_ctx = ClientSession(*streams)
        session = await self._exit_stack.enter_async_context(session_ctx)
        return transport_ctx, session

    async def _start_backend_svr(
        self, svr_name: str, svr_conf: Dict[str, Any]
    ) -> bool:
        """Start and initialize a single backend server connection."""
        svr_type = svr_conf.get("type")
        logger.info("[%s] Attempting connection, type: %s...", svr_name, svr_type)
        session: Optional[ClientSession] = None

        try:
            if svr_type == "stdio":
                stdio_params = svr_conf.get("params")
                if not isinstance(stdio_params, StdioServerParameters):
                    raise ConfigurationError(
                        f"Invalid stdio config for server '{svr_name}' "
                        "('params' type mismatch)."
                    )
                _, session = await self._init_stdio_backend(svr_name, stdio_params)

            elif svr_type == "sse":
                sse_url = svr_conf.get("url")
                if not isinstance(sse_url, str) or not sse_url:
                    raise ConfigurationError(
                        f"Invalid SSE 'url' configuration for server '{svr_name}'."
                    )
                _, session = await self._init_sse_backend(
                    svr_name,
                    sse_url,
                    svr_conf.get("command"),
                    svr_conf.get("args", []),
                    svr_conf.get("env"),
                )
            else:
                raise ConfigurationError(
                    f"Unsupported server type '{svr_type}' for server '{svr_name}'."
                )

            if not session:
                raise BackendServerError(
                    f"[{svr_name}] ({svr_type}) Session could not be created."
                )

            logger.info(
                "[%s] Initializing MCP connection (timeout: %ss)...",
                svr_name, MCP_INIT_TIMEOUT,
            )
            await asyncio.wait_for(session.initialize(), timeout=MCP_INIT_TIMEOUT)

            self._sessions[svr_name] = session
            logger.info(
                "\u2705 MCP connection initialized for server '%s' (%s).",
                svr_name, svr_type,
            )
            return True

        except asyncio.CancelledError:
            logger.warning(
                "[%s] (%s) startup task cancelled.",
                svr_name, svr_type or 'unknown type',
            )
            return False
        except Exception as e_start:
            _log_backend_fail(svr_name, svr_type, e_start, context="connect/initialize")
            return False

    async def start_all(self, config_data: Dict[str, Dict[str, Any]]) -> None:
        """Start all backend server connections based on configuration."""
        logger.info(
            "Starting all backend server connections (%s total)...",
            len(config_data),
        )
        for svr_name, svr_conf in config_data.items():
            task = asyncio.create_task(
                self._start_backend_svr(svr_name, svr_conf),
                name=f"start_{svr_name}",
            )
            self._pending_tasks[svr_name] = task

        if self._pending_tasks:
            results = await asyncio.gather(
                *self._pending_tasks.values(), return_exceptions=True
            )
            for svr_name, result in zip(self._pending_tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(
                        "[%s] Startup task failed with exception '%s' "
                        "(details logged in _start_backend_svr).",
                        svr_name, type(result).__name__,
                    )
                elif result is False:
                    logger.warning(
                        "[%s] Startup task returned False "
                        "(details logged in _start_backend_svr).",
                        svr_name,
                    )

        self._pending_tasks.clear()

        active_svrs_count = len(self._sessions)
        total_svrs_count = len(config_data)
        logger.info(
            "All backend startup attempts completed. "
            "Active servers: %s/%s",
            active_svrs_count, total_svrs_count,
        )
        if active_svrs_count < total_svrs_count:
            logger.warning(
                "Some backend servers failed to start/connect. "
                "Check file logs for details."
            )

    async def stop_all(self) -> None:
        """Close all active sessions and subprocesses started by the manager."""
        logger.info(
            "Stopping all backend connections and local processes (via AsyncExitStack)..."
        )

        if self._pending_tasks:
            logger.info(
                "Cancelling %s pending startup tasks...",
                len(self._pending_tasks),
            )
            for task in self._pending_tasks.values():
                if not task.done():
                    task.cancel()
            await asyncio.gather(
                *self._pending_tasks.values(), return_exceptions=True
            )
            self._pending_tasks.clear()
            logger.info("Pending startup tasks cancelled and cleaned up.")

        logger.info(
            "Calling AsyncExitStack.aclose() to clean up managed resources..."
        )
        try:
            await self._exit_stack.aclose()
            logger.info(
                "AsyncExitStack closed all managed contexts "
                "(connections and subprocesses)."
            )
        except Exception as e_aclose:
            logger.exception(
                "Error while closing AsyncExitStack: %s. "
                "Some resources may not have been released.",
                e_aclose,
            )

        self._sessions.clear()
        logger.info("ClientManager closed, all sessions cleared.")

    def get_session(self, svr_name: str) -> Optional[ClientSession]:
        """Get an active backend session by server name."""
        return self._sessions.get(svr_name)

    def get_active_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._sessions)

    def get_all_sessions(self) -> Dict[str, ClientSession]:
        """Get a dictionary copy of all active sessions."""
        return self._sessions.copy()
