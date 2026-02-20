import asyncio
import logging
import os
import sys
from typing import Dict, Optional, Any, List, Tuple, AsyncGenerator
from contextlib import asynccontextmanager, AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
try:
    import httpx

    SSE_NET_EXCS = (httpx.ConnectError, httpx.TimeoutException,
                    httpx.NetworkError, httpx.ReadTimeout, httpx.WriteTimeout,
                    httpx.PoolTimeout)
except ImportError:
    SSE_NET_EXCS = ()

from errors import BackendServerError, ConfigurationError

logger = logging.getLogger(__name__)

SSE_LOCAL_START_DELAY = 5
MCP_INIT_TIMEOUT = 15


async def _log_subproc_stream(stream: Optional[asyncio.StreamReader],
                              svr_name: str, stream_name: str):
    """Asynchronously read and log lines from subprocess streams."""
    if not stream:
        return
    while True:
        try:
            line_bytes = await stream.readline()
            if not line_bytes:
                logger.debug(f"[{svr_name}-{stream_name}] Stream ended (EOF).")
                break
            line = line_bytes.decode(errors='replace').strip()
            if line:
                logger.info(f"[{svr_name}-{stream_name}] {line}")
        except asyncio.CancelledError:
            logger.debug(f"[{svr_name}-{stream_name}] Logging task was cancelled.")
            break
        except Exception as e_stream:
            logger.error(f"[{svr_name}-{stream_name}] Error while reading stream: {e_stream}",
                         exc_info=True)
            break


@asynccontextmanager
async def _manage_subproc(
        cmd_to_exec: str, args: List[str], proc_env: Optional[Dict[str, str]],
        svr_name: str) -> AsyncGenerator[asyncio.subprocess.Process, None]:
    """Async context manager for starting and stopping subprocesses."""
    process: Optional[asyncio.subprocess.Process] = None
    stdout_log_task: Optional[asyncio.Task] = None
    stderr_log_task: Optional[asyncio.Task] = None
    try:

        py_exec = sys.executable or "python"
        actual_cmd = py_exec if cmd_to_exec.lower(
        ) == "python" else cmd_to_exec

        logger.info(f"[{svr_name}] Preparing to start local process: '{actual_cmd}' args: {args}")

        current_env = os.environ.copy()
        if proc_env:
            current_env.update(proc_env)

        process = await asyncio.create_subprocess_exec(
            actual_cmd,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=current_env)
        logger.info(f"[{svr_name}] Local process started (PID: {process.pid}).")

        if process.stdout:
            stdout_log_task = asyncio.create_task(
                _log_subproc_stream(process.stdout, svr_name, "stdout"),
                name=f"{svr_name}_stdout_logger")
        if process.stderr:
            stderr_log_task = asyncio.create_task(
                _log_subproc_stream(process.stderr, svr_name, "stderr"),
                name=f"{svr_name}_stderr_logger")
        yield process
    except FileNotFoundError:
        logger.error(f"[{svr_name}] Failed to start local process: command '{actual_cmd}' not found.",
                     exc_info=True)
        raise
    except Exception as e_subproc:
        logger.error(f"[{svr_name}] Unexpected error starting local process '{actual_cmd}'.",
                     exc_info=True)
        raise
    finally:

        if stdout_log_task and not stdout_log_task.done():
            stdout_log_task.cancel()
        if stderr_log_task and not stderr_log_task.done():
            stderr_log_task.cancel()

        if stdout_log_task or stderr_log_task:
            await asyncio.gather(stdout_log_task,
                                 stderr_log_task,
                                 return_exceptions=True)
            logger.debug(f"[{svr_name}] Subprocess stream logging tasks completed.")

        if process and process.returncode is None:
            logger.info(f"[{svr_name}] Attempting to terminate local process (PID: {process.pid})...")
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=3.0)
                logger.info(f"[{svr_name}] Local process (PID: {process.pid}) terminated successfully.")
            except asyncio.TimeoutError:
                logger.warning(
                    f"[{svr_name}] Timeout while terminating local process (PID: {process.pid}), trying kill..."
                )
                process.kill()
                await process.wait()
                logger.info(
                    f"[{svr_name}] Local process (PID: {process.pid}) was force-killed.")
            except ProcessLookupError:
                logger.warning(
                    f"[{svr_name}] Local process not found while terminating (PID: {process.pid}).")
            except Exception as e_term:
                logger.error(
                    f"[{svr_name}] Error terminating local process (PID: {process.pid}): {e_term}",
                    exc_info=True)


def _log_backend_fail(svr_name: str,
                      svr_type: Optional[str],
                      e: Exception,
                      context: str = "startup"):
    """Helper to log backend startup/connection failures."""
    svr_type_str = svr_type or 'unknown type'
    if isinstance(e, asyncio.TimeoutError):
        logger.error(f"[{svr_name}] ({svr_type_str}) {context} timed out.")
    elif isinstance(e, ConfigurationError):
        logger.error(f"[{svr_name}] ({svr_type_str}) Configuration error during {context}: {e}")
    elif isinstance(e, (*SSE_NET_EXCS, ConnectionRefusedError, BrokenPipeError,
                        ConnectionError)):
        logger.error(
            f"[{svr_name}] ({svr_type_str}) Network/connection error during "
            f"{context}: {type(e).__name__}: {e}"
        )
    elif isinstance(e, FileNotFoundError):
        logger.error(
            f"[{svr_name}] (local launch {svr_type_str}) Command or file not found "
            f"'{e.filename}' during {context}."
        )
    else:
        logger.exception(
            f"[{svr_name}] ({svr_type_str}) Unexpected fatal error during {context}.")


class ClientManager:
    """Manages connections and sessions for all backend MCP servers."""

    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._pending_tasks: Dict[str, asyncio.Task] = {}
        self._exit_stack = AsyncExitStack()
        logger.info("ClientManager initialized.")

    async def _init_stdio_backend(
            self, svr_name: str,
            stdio_cfg: StdioServerParameters) -> Tuple[Any, ClientSession]:
        """Initialize and connect to a stdio backend server."""
        logger.debug(f"[{svr_name}] Stdio backend, preparing stdio_client.")

        transport_ctx = stdio_client(stdio_cfg)
        streams = await self._exit_stack.enter_async_context(transport_ctx)
        logger.debug(f"[{svr_name}] (stdio) transport streams established.")

        session_ctx = ClientSession(*streams)
        session = await self._exit_stack.enter_async_context(session_ctx)
        return transport_ctx, session

    async def _init_sse_backend(
            self, svr_name: str, sse_url: str, sse_cmd: Optional[str],
            sse_cmd_args: List[str],
            sse_cmd_env: Optional[Dict[str,
                                       str]]) -> Tuple[Any, ClientSession]:
        """Initialize and connect to an SSE backend; launch command first if configured."""
        if sse_cmd:
            logger.info(f"[{svr_name}] Local launch command configured, starting SSE subprocess...")

            await self._exit_stack.enter_async_context(
                _manage_subproc(sse_cmd, sse_cmd_args, sse_cmd_env, svr_name))
            logger.info(
                f"[{svr_name}] Waiting {SSE_LOCAL_START_DELAY}s for local SSE server startup...")
            await asyncio.sleep(SSE_LOCAL_START_DELAY)

        transport_ctx = sse_client(url=sse_url)
        streams = await self._exit_stack.enter_async_context(transport_ctx)
        logger.debug(f"[{svr_name}] (sse) transport streams established.")

        session_ctx = ClientSession(*streams)
        session = await self._exit_stack.enter_async_context(session_ctx)
        return transport_ctx, session

    async def _start_backend_svr(self, svr_name: str,
                                 svr_conf: Dict[str, Any]) -> bool:
        """Start and initialize a single backend server connection."""
        svr_type = svr_conf.get('type')
        logger.info(f"[{svr_name}] Attempting connection, type: {svr_type}...")
        session: Optional[ClientSession] = None

        try:
            if svr_type == "stdio":
                stdio_params = svr_conf.get('params')
                if not isinstance(stdio_params, StdioServerParameters):
                    raise ConfigurationError(
                        f"Invalid stdio config for server '{svr_name}' ('params' type mismatch).")
                _, session = await self._init_stdio_backend(
                    svr_name, stdio_params)

            elif svr_type == "sse":
                sse_url = svr_conf.get('url')
                if not isinstance(sse_url, str) or not sse_url:
                    raise ConfigurationError(
                        f"Invalid SSE 'url' configuration for server '{svr_name}'.")

                _, session = await self._init_sse_backend(
                    svr_name, sse_url, svr_conf.get('command'),
                    svr_conf.get('args', []), svr_conf.get('env'))
            else:
                raise ConfigurationError(
                    f"Unsupported server type '{svr_type}' for server '{svr_name}'.")

            if not session:
                raise BackendServerError(
                    f"[{svr_name}] ({svr_type}) Session could not be created.")

            logger.info(
                f"[{svr_name}] Initializing MCP connection (timeout: {MCP_INIT_TIMEOUT}s)...")
            await asyncio.wait_for(session.initialize(),
                                   timeout=MCP_INIT_TIMEOUT)

            self._sessions[svr_name] = session
            logger.info(f"✅ MCP connection initialized for server '{svr_name}' ({svr_type}).")
            return True

        except asyncio.CancelledError:
            logger.warning(f"[{svr_name}] ({svr_type or 'unknown type'}) startup task cancelled.")
            return False
        except Exception as e_start:
            _log_backend_fail(svr_name, svr_type, e_start, context="connect/initialize")
            return False

    async def start_all(self, config_data: Dict[str, Dict[str, Any]]):
        """Start all backend server connections based on configuration."""
        logger.info(f"Starting all backend server connections ({len(config_data)} total)...")
        for svr_name, svr_conf in config_data.items():
            task = asyncio.create_task(self._start_backend_svr(
                svr_name, svr_conf),
                                       name=f"start_{svr_name}")
            self._pending_tasks[svr_name] = task

        if self._pending_tasks:

            results = await asyncio.gather(*self._pending_tasks.values(),
                                           return_exceptions=True)

            for svr_name, result in zip(self._pending_tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(
                        f"[{svr_name}] Startup task failed with exception "
                        f"'{type(result).__name__}' (details logged in _start_backend_svr)."
                    )
                elif result is False:
                    logger.warning(
                        f"[{svr_name}] Startup task returned False (details logged in _start_backend_svr)."
                    )

        self._pending_tasks.clear()

        active_svrs_count = len(self._sessions)
        total_svrs_count = len(config_data)
        logger.info(
            f"All backend startup attempts completed. Active servers: {active_svrs_count}/{total_svrs_count}")
        if active_svrs_count < total_svrs_count:
            logger.warning("Some backend servers failed to start/connect. Check file logs for details.")

    async def stop_all(self):
        """Close all active sessions and subprocesses started by the manager."""
        logger.info("Stopping all backend connections and local processes (via AsyncExitStack)...")

        if self._pending_tasks:
            logger.info(f"Cancelling {len(self._pending_tasks)} pending startup tasks...")
            for task in self._pending_tasks.values():
                if not task.done():
                    task.cancel()

            await asyncio.gather(*self._pending_tasks.values(),
                                 return_exceptions=True)
            self._pending_tasks.clear()
            logger.info("Pending startup tasks cancelled and cleaned up.")

        logger.info("Calling AsyncExitStack.aclose() to clean up managed resources...")
        try:
            await self._exit_stack.aclose()
            logger.info("AsyncExitStack closed all managed contexts (connections and subprocesses).")
        except Exception as e_aclose:
            logger.exception(
                f"Error while closing AsyncExitStack: {e_aclose}. Some resources may not have been released.")

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
