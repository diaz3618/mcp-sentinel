"""Backend MCP server connection management."""

import asyncio
import logging
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

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

from mcp_sentinel.constants import (
    BACKEND_RETRIES,
    BACKEND_RETRY_DELAY,
    MCP_INIT_TIMEOUT,
    SSE_LOCAL_START_DELAY,
    STARTUP_TIMEOUT,
)
from mcp_sentinel.errors import BackendServerError, ConfigurationError

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
                svr_name,
                stream_name,
                e_stream,
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
            svr_name,
            actual_cmd,
            args,
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
        logger.debug(
            "[%s] Failed to start local process: command '%s' not found.",
            svr_name,
            actual_cmd,
            exc_info=True,
        )
        raise
    except Exception:
        logger.debug(
            "[%s] Unexpected error starting local process '%s'.",
            svr_name,
            actual_cmd,
            exc_info=True,
        )
        raise
    finally:
        if stdout_log_task and not stdout_log_task.done():
            stdout_log_task.cancel()
        if stderr_log_task and not stderr_log_task.done():
            stderr_log_task.cancel()

        if stdout_log_task or stderr_log_task:
            await asyncio.gather(stdout_log_task, stderr_log_task, return_exceptions=True)
            logger.debug("[%s] Subprocess stream logging tasks completed.", svr_name)

        if process and process.returncode is None:
            logger.info(
                "[%s] Attempting to terminate local process (PID: %s)...",
                svr_name,
                process.pid,
            )
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=3.0)
                logger.info(
                    "[%s] Local process (PID: %s) terminated successfully.",
                    svr_name,
                    process.pid,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[%s] Timeout while terminating local process " "(PID: %s), trying kill...",
                    svr_name,
                    process.pid,
                )
                process.kill()
                await process.wait()
                logger.info(
                    "[%s] Local process (PID: %s) was force-killed.",
                    svr_name,
                    process.pid,
                )
            except ProcessLookupError:
                logger.warning(
                    "[%s] Local process not found while terminating " "(PID: %s).",
                    svr_name,
                    process.pid,
                )
            except Exception as e_term:
                logger.error(
                    "[%s] Error terminating local process " "(PID: %s): %s",
                    svr_name,
                    process.pid,
                    e_term,
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
            svr_name,
            svr_type_str,
            context,
            e,
        )
    elif isinstance(e, (*SSE_NET_EXCS, ConnectionRefusedError, BrokenPipeError, ConnectionError)):
        logger.error(
            "[%s] (%s) Network/connection error during " "%s: %s: %s",
            svr_name,
            svr_type_str,
            context,
            type(e).__name__,
            e,
        )
    elif isinstance(e, FileNotFoundError):
        logger.error(
            "[%s] (local launch %s) Command or file not found " "'%s' during %s.",
            svr_name,
            svr_type_str,
            e.filename,
            context,
        )
    else:
        logger.exception(
            "[%s] (%s) Unexpected fatal error during %s.",
            svr_name,
            svr_type_str,
            context,
        )


class ClientManager:
    """Manages connections and sessions for all backend MCP servers."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ClientSession] = {}
        self._pending_tasks: Dict[str, asyncio.Task] = {}
        self._exit_stack = AsyncExitStack()
        self._devnull_files: list = []  # keep refs so GC doesn't close them early
        self._status_records: Dict[str, Any] = {}  # BackendStatusRecord instances
        self._progress_cb: Optional[Callable[..., None]] = None
        logger.info("ClientManager initialized.")

    async def _init_stdio_backend(
        self, svr_name: str, stdio_cfg: StdioServerParameters
    ) -> Tuple[Any, ClientSession]:
        """Initialize and connect to a stdio backend server."""
        logger.debug("[%s] Stdio backend, preparing stdio_client.", svr_name)

        # Suppress subprocess stderr so it does not corrupt the TUI.
        # The MCP SDK defaults errlog=sys.stderr, which writes directly
        # to fd 2 — the same fd Textual uses for rendering.  Sending a
        # devnull file-object prevents any backend process output from
        # bleeding through.
        devnull = open(os.devnull, "w")  # noqa: SIM115
        self._devnull_files.append(devnull)
        transport_ctx = stdio_client(stdio_cfg, errlog=devnull)
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
        sse_startup_delay: float = SSE_LOCAL_START_DELAY,
        headers: Optional[Dict[str, str]] = None,
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
                svr_name,
                sse_startup_delay,
            )
            await asyncio.sleep(sse_startup_delay)

        transport_ctx = sse_client(url=sse_url, headers=headers)
        streams = await self._exit_stack.enter_async_context(transport_ctx)
        logger.debug("[%s] (sse) transport streams established.", svr_name)

        session_ctx = ClientSession(*streams)
        session = await self._exit_stack.enter_async_context(session_ctx)
        return transport_ctx, session

    async def _init_streamablehttp_backend(
        self,
        svr_name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[Any, ClientSession]:
        """Initialize and connect to a streamable-http backend server."""
        logger.debug("[%s] Streamable-HTTP backend, url=%s", svr_name, url)
        transport_ctx = streamablehttp_client(url=url, headers=headers)
        read_stream, write_stream, _get_session_id = await self._exit_stack.enter_async_context(
            transport_ctx
        )
        logger.debug("[%s] (streamable-http) transport streams established.", svr_name)

        session_ctx = ClientSession(read_stream, write_stream)
        session = await self._exit_stack.enter_async_context(session_ctx)
        return transport_ctx, session

    async def _start_backend_svr(self, svr_name: str, svr_conf: Dict[str, Any]) -> bool:
        """Start and initialize a single backend server connection.

        The entire flow (subprocess spawn + MCP init) is wrapped in an
        overall ``startup_timeout`` so that cold-start package downloads
        (uvx / npx) don't hang indefinitely.
        """
        svr_type = svr_conf.get("type")
        logger.info("[%s] Attempting connection, type: %s...", svr_name, svr_type)

        startup_timeout = svr_conf.get("startup_timeout", STARTUP_TIMEOUT)

        # Create status record and transition PENDING → INITIALIZING
        from mcp_sentinel.runtime.models import BackendPhase, BackendStatusRecord

        record = self._status_records.get(svr_name)
        if record is None:
            record = BackendStatusRecord(name=svr_name)
            self._status_records[svr_name] = record

        try:
            record.transition(BackendPhase.INITIALIZING, f"Connecting ({svr_type})")
        except ValueError:
            pass

        # Notify progress display (if subscribed)
        if self._progress_cb is not None:
            self._progress_cb(svr_name, "initializing", f"Connecting ({svr_type})")

        try:
            await asyncio.wait_for(
                self._connect_backend(svr_name, svr_conf, svr_type, record),
                timeout=startup_timeout,
            )
            return True

        except asyncio.TimeoutError:
            msg = (
                f"Overall startup timed out after {startup_timeout}s "
                f"(subprocess spawn + MCP init)"
            )
            logger.error("[%s] (%s) %s", svr_name, svr_type or "unknown", msg)
            try:
                record.transition(BackendPhase.FAILED, msg)
            except ValueError:
                pass
            if self._progress_cb is not None:
                self._progress_cb(svr_name, "failed", msg)
            return False

        except asyncio.CancelledError:
            logger.warning(
                "[%s] (%s) startup task cancelled.",
                svr_name,
                svr_type or "unknown type",
            )
            try:
                record.transition(BackendPhase.FAILED, "Startup cancelled")
            except ValueError:
                pass
            if self._progress_cb is not None:
                self._progress_cb(svr_name, "failed", "Startup cancelled")
            return False
        except Exception as e_start:
            _log_backend_fail(svr_name, svr_type, e_start, context="connect/initialize")
            try:
                record.transition(BackendPhase.FAILED, str(e_start))
            except ValueError:
                pass
            if self._progress_cb is not None:
                self._progress_cb(svr_name, "failed", str(e_start))
            return False

    async def _connect_backend(
        self,
        svr_name: str,
        svr_conf: Dict[str, Any],
        svr_type: Optional[str],
        record: Any,
    ) -> None:
        """Inner connection logic (spawn transport + MCP init).

        Extracted so ``_start_backend_svr`` can wrap this in
        ``asyncio.wait_for`` with the overall ``startup_timeout``.
        """
        from mcp_sentinel.runtime.models import BackendPhase

        # Resolve outgoing-auth headers (if configured)
        auth_headers = await self._resolve_auth_headers(svr_name, svr_conf)

        session: Optional[ClientSession] = None

        if svr_type == "stdio":
            stdio_params = svr_conf.get("params")
            if not isinstance(stdio_params, StdioServerParameters):
                raise ConfigurationError(
                    f"Invalid stdio config for server '{svr_name}' " "('params' type mismatch)."
                )
            _, session = await self._init_stdio_backend(svr_name, stdio_params)

        elif svr_type == "sse":
            sse_url = svr_conf.get("url")
            if not isinstance(sse_url, str) or not sse_url:
                raise ConfigurationError(
                    f"Invalid SSE 'url' configuration for server '{svr_name}'."
                )
            # Merge static headers from config with auth-provider headers
            sse_headers = _merge_headers(svr_conf.get("headers"), auth_headers)
            _, session = await self._init_sse_backend(
                svr_name,
                sse_url,
                svr_conf.get("command"),
                svr_conf.get("args", []),
                svr_conf.get("env"),
                sse_startup_delay=svr_conf.get("sse_startup_delay", SSE_LOCAL_START_DELAY),
                headers=sse_headers,
            )

        elif svr_type == "streamable-http":
            sh_url = svr_conf.get("url")
            if not isinstance(sh_url, str) or not sh_url:
                raise ConfigurationError(
                    f"Invalid streamable-http 'url' configuration " f"for server '{svr_name}'."
                )
            sh_headers = _merge_headers(svr_conf.get("headers"), auth_headers)
            _, session = await self._init_streamablehttp_backend(svr_name, sh_url, sh_headers)

        else:
            raise ConfigurationError(
                f"Unsupported server type '{svr_type}' for server '{svr_name}'."
            )

        if not session:
            raise BackendServerError(f"[{svr_name}] ({svr_type}) Session could not be created.")

        init_timeout = svr_conf.get("init_timeout", MCP_INIT_TIMEOUT)
        logger.info(
            "[%s] Initializing MCP connection (timeout: %ss)...",
            svr_name,
            init_timeout,
        )
        await asyncio.wait_for(session.initialize(), timeout=init_timeout)

        self._sessions[svr_name] = session
        logger.info(
            "\u2705 MCP connection initialized for server '%s' (%s).",
            svr_name,
            svr_type,
        )
        try:
            record.transition(BackendPhase.READY, "Connection established")
        except ValueError:
            pass
        if self._progress_cb is not None:
            self._progress_cb(svr_name, "ready")

    async def start_all(
        self,
        config_data: Dict[str, Dict[str, Any]],
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> None:
        """Start all backend server connections, retrying failures.

        After the initial parallel connection attempt, any backends that
        failed are automatically retried up to ``retries`` times (per-backend
        or global default).  Between attempts the display shows "Retrying…"
        and a configurable delay (``retry_delay``) is applied.
        """
        self._progress_cb = progress_callback
        logger.info(
            "Starting all backend server connections (%s total)...",
            len(config_data),
        )

        # ── First pass: connect all backends in parallel ─────────────
        for svr_name, svr_conf in config_data.items():
            task = asyncio.create_task(
                self._start_backend_svr(svr_name, svr_conf),
                name=f"start_{svr_name}",
            )
            self._pending_tasks[svr_name] = task

        if self._pending_tasks:
            results = await asyncio.gather(*self._pending_tasks.values(), return_exceptions=True)
            first_pass: Dict[str, bool] = {}
            for svr_name, result in zip(self._pending_tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(
                        "[%s] Startup task failed with exception '%s'.",
                        svr_name,
                        type(result).__name__,
                    )
                    first_pass[svr_name] = False
                else:
                    first_pass[svr_name] = bool(result)
        else:
            first_pass = {}

        self._pending_tasks.clear()

        # ── Retry loop for failed backends ───────────────────────────
        failed_names = [n for n, ok in first_pass.items() if not ok]

        if failed_names:
            # Determine the global retry params (use the max across all
            # failed backends so every one gets its configured chances).
            max_retries = max(config_data[n].get("retries", BACKEND_RETRIES) for n in failed_names)
            logger.info(
                "%d backend(s) failed on first attempt — will retry up to %d time(s): %s",
                len(failed_names),
                max_retries,
                ", ".join(failed_names),
            )

            for attempt in range(1, max_retries + 1):
                if not failed_names:
                    break

                # Per-backend delay (use the max among remaining failures)
                delay = max(
                    config_data[n].get("retry_delay", BACKEND_RETRY_DELAY) for n in failed_names
                )
                logger.info(
                    "Retry attempt %d/%d — waiting %.1fs before retrying %d backend(s)...",
                    attempt,
                    max_retries,
                    delay,
                    len(failed_names),
                )

                # Signal "retrying" phase to display
                from mcp_sentinel.runtime.models import BackendPhase

                for svr_name in failed_names:
                    record = self._status_records.get(svr_name)
                    if record is not None:
                        try:
                            record.transition(
                                BackendPhase.RETRYING,
                                f"Retry {attempt}/{max_retries}",
                            )
                        except ValueError:
                            pass
                    if self._progress_cb is not None:
                        self._progress_cb(
                            svr_name,
                            "retrying",
                            f"Retry {attempt}/{max_retries} in {delay:.0f}s…",
                        )

                await asyncio.sleep(delay)

                # Retry failed backends in parallel
                retry_tasks: Dict[str, asyncio.Task] = {}
                for svr_name in failed_names:
                    svr_conf = config_data[svr_name]
                    # Only retry if this backend still has attempts left
                    per_backend_retries = svr_conf.get("retries", BACKEND_RETRIES)
                    if attempt > per_backend_retries:
                        continue
                    task = asyncio.create_task(
                        self._start_backend_svr(svr_name, svr_conf),
                        name=f"retry_{svr_name}_{attempt}",
                    )
                    retry_tasks[svr_name] = task

                if retry_tasks:
                    retry_results = await asyncio.gather(
                        *retry_tasks.values(), return_exceptions=True
                    )
                    for svr_name, result in zip(retry_tasks.keys(), retry_results):
                        if isinstance(result, Exception):
                            logger.error(
                                "[%s] Retry %d failed with exception '%s'.",
                                svr_name,
                                attempt,
                                type(result).__name__,
                            )
                        elif result is True:
                            logger.info(
                                "[%s] Retry %d succeeded.",
                                svr_name,
                                attempt,
                            )

                # Refresh the failed list for next iteration
                failed_names = [n for n in failed_names if n not in self._sessions]

        self._pending_tasks.clear()

        # Clear callback reference (no longer needed after startup)
        self._progress_cb = None

        active_svrs_count = len(self._sessions)
        total_svrs_count = len(config_data)
        logger.info(
            "All backend startup attempts completed. " "Active servers: %s/%s",
            active_svrs_count,
            total_svrs_count,
        )
        if active_svrs_count < total_svrs_count:
            logger.warning(
                "Some backend servers failed to start/connect. " "Check file logs for details."
            )

    async def stop_all(self) -> None:
        """Close all active sessions and subprocesses started by the manager."""
        logger.info("Stopping all backend connections and local processes (via AsyncExitStack)...")

        # Transition operational backends to SHUTTING_DOWN
        from mcp_sentinel.runtime.models import BackendPhase

        for name, rec in self._status_records.items():
            if rec.is_operational:
                try:
                    rec.transition(BackendPhase.SHUTTING_DOWN, "Graceful shutdown")
                except ValueError:
                    pass

        if self._pending_tasks:
            logger.info(
                "Cancelling %s pending startup tasks...",
                len(self._pending_tasks),
            )
            for task in self._pending_tasks.values():
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._pending_tasks.values(), return_exceptions=True)
            self._pending_tasks.clear()
            logger.info("Pending startup tasks cancelled and cleaned up.")

        logger.info("Calling AsyncExitStack.aclose() to clean up managed resources...")
        try:
            await self._exit_stack.aclose()
            logger.info(
                "AsyncExitStack closed all managed contexts " "(connections and subprocesses)."
            )
        except Exception as e_aclose:
            logger.exception(
                "Error while closing AsyncExitStack: %s. "
                "Some resources may not have been released.",
                e_aclose,
            )

        self._sessions.clear()

        # Close devnull file objects opened for subprocess stderr suppression
        for f in self._devnull_files:
            try:
                f.close()
            except Exception:
                pass
        self._devnull_files.clear()

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

    # ── Status records ───────────────────────────────────────────────────

    def get_status_record(self, svr_name: str) -> Optional[Any]:
        """Get the status record for a backend (or ``None``)."""
        return self._status_records.get(svr_name)

    def get_all_status_records(self) -> Dict[str, Any]:
        """Return a snapshot of all status records."""
        return dict(self._status_records)

    # ── Outgoing authentication ──────────────────────────────────────

    async def _resolve_auth_headers(
        self, svr_name: str, svr_conf: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Resolve outgoing-auth headers for a backend, if configured."""
        auth_cfg = svr_conf.get("auth")
        if not auth_cfg:
            return None
        try:
            from mcp_sentinel.bridge.auth.provider import create_auth_provider

            provider = create_auth_provider(auth_cfg)
            headers = await provider.get_headers()
            logger.info("[%s] Auth provider resolved: %s", svr_name, provider.redacted_repr())
            return headers
        except Exception as exc:
            logger.error("[%s] Failed to resolve auth headers: %s", svr_name, exc)
            return None


# ── Module-level helpers ─────────────────────────────────────────────────


def _merge_headers(
    static: Optional[Dict[str, str]],
    auth: Optional[Dict[str, str]],
) -> Optional[Dict[str, str]]:
    """Merge static config headers with auth-provider headers.

    Auth-provider headers take precedence over static ones (e.g. a
    provider-managed ``Authorization`` header overrides a static one).
    Returns ``None`` when both inputs are ``None``.
    """
    if not static and not auth:
        return None
    merged: Dict[str, str] = {}
    if static:
        merged.update(static)
    if auth:
        merged.update(auth)
    return merged
