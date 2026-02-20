"""MCP capability discovery, registration, and routing."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

from mcp import ClientSession
from mcp import types as mcp_types

from mcp_gateway.constants import CAP_FETCH_TIMEOUT

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Discovers, registers, and routes MCP capabilities from backend servers."""

    def __init__(self) -> None:
        self._tools: List[mcp_types.Tool] = []
        self._resources: List[mcp_types.Resource] = []
        self._prompts: List[mcp_types.Prompt] = []
        self._route_map: Dict[str, Tuple[str, str]] = {}
        logger.info("CapabilityRegistry initialized.")

    async def _discover_caps_by_type(
        self,
        svr_name: str,
        session: ClientSession,
        cap_type: str,
        list_method_name: str,
        mcp_cls: Union[
            Type[mcp_types.Tool], Type[mcp_types.Resource], Type[mcp_types.Prompt]
        ],
        agg_list: List[Any],
    ) -> None:
        """
        Generic helper to discover and register a specific capability type.

        If a name conflict occurs (same capability from different servers),
        the new one is ignored and a warning is logged.

        TODO: Make conflict resolution strategy configurable
        (for example, auto-prefixing).
        """
        logger.debug(f"[{svr_name}] Starting discovery for {cap_type}...")
        try:
            list_method = getattr(session, list_method_name)
            logger.debug(
                f"[{svr_name}] Requesting {cap_type} list "
                f"(timeout {CAP_FETCH_TIMEOUT}s)..."
            )

            list_result = await asyncio.wait_for(
                list_method(), timeout=CAP_FETCH_TIMEOUT
            )

            orig_caps: List[Any] = []

            if hasattr(list_result, cap_type) and isinstance(
                getattr(list_result, cap_type), list
            ):
                orig_caps = getattr(list_result, cap_type)
            elif isinstance(list_result, list):
                orig_caps = list_result
            elif list_result is None:
                logger.info(
                    f"[{svr_name}] {list_method_name}() returned None, "
                    f"treating as no {cap_type}."
                )
                orig_caps = []
            else:
                logger.warning(
                    f"[{svr_name}] {list_method_name}() returned unknown type "
                    f"{type(list_result)}; unable to parse {cap_type} list. "
                    f"Raw value: {list_result!r}"
                )
                orig_caps = []

            logger.debug(
                f"[{svr_name}] Parsed {len(orig_caps)} raw {cap_type} from response."
            )

            registered_count = 0
            for cap_item_raw in orig_caps:
                if not isinstance(cap_item_raw, mcp_cls):
                    logger.warning(
                        f"[{svr_name}] Found non-{mcp_cls.__name__} object, "
                        f"skipped: {cap_item_raw!r}"
                    )
                    continue

                cap_item = cast(
                    Union[mcp_types.Tool, mcp_types.Resource, mcp_types.Prompt],
                    cap_item_raw,
                )

                if not cap_item.name:
                    logger.warning(
                        f"[{svr_name}] Found unnamed {cap_type[:-1]}, "
                        f"skipped: {cap_item!r}"
                    )
                    continue

                exp_cap_name = cap_item.name

                if exp_cap_name in self._route_map:
                    exist_svr_name, _ = self._route_map[exp_cap_name]
                    if exist_svr_name != svr_name:
                        logger.warning(
                            f"Conflict: {cap_type[:-1]} '{exp_cap_name}' is already "
                            f"registered by server '{exist_svr_name}'. The duplicate "
                            f"from server '{svr_name}' will be ignored."
                        )
                        continue
                    else:
                        logger.warning(
                            f"[{svr_name}] Duplicate {cap_type[:-1]} provided "
                            f"multiple times: '{exp_cap_name}'. Only the first "
                            "instance is registered."
                        )
                        continue

                agg_list.append(cap_item)
                self._route_map[exp_cap_name] = (svr_name, cap_item.name)
                registered_count += 1

            if registered_count > 0:
                logger.info(
                    f"[{svr_name}] Registered {registered_count} unique {cap_type}."
                )
            else:
                logger.info(
                    f"[{svr_name}] No new {cap_type} discovered or registered."
                )

        except asyncio.TimeoutError:
            logger.error(
                f"[{svr_name}] {list_method_name}() timed out "
                f"(>{CAP_FETCH_TIMEOUT}s)."
            )
        except mcp_types.Error as mcp_e:
            logger.error(
                f"[{svr_name}] MCP error during {list_method_name}(): "
                f"Type={mcp_e.type}, Msg='{mcp_e.message}'",
                exc_info=False,
            )
        except Exception:
            logger.exception(
                f"[{svr_name}] Unknown error while discovering {cap_type}."
            )

    async def discover_and_register(
        self, sessions: Dict[str, ClientSession]
    ) -> None:
        """Discover and register MCP capabilities from active backend sessions."""
        logger.info(
            f"Starting capability discovery/registration from "
            f"{len(sessions)} active sessions..."
        )

        self._tools.clear()
        self._resources.clear()
        self._prompts.clear()
        self._route_map.clear()

        discover_tasks = []
        for svr_name, session in sessions.items():
            if not session:
                logger.warning(
                    f"Skipping server '{svr_name}' because it has no valid session."
                )
                continue

            discover_tasks.append(
                self._discover_caps_by_type(
                    svr_name, session, "tools", "list_tools",
                    mcp_types.Tool, self._tools,
                )
            )
            discover_tasks.append(
                self._discover_caps_by_type(
                    svr_name, session, "resources", "list_resources",
                    mcp_types.Resource, self._resources,
                )
            )
            discover_tasks.append(
                self._discover_caps_by_type(
                    svr_name, session, "prompts", "list_prompts",
                    mcp_types.Prompt, self._prompts,
                )
            )

        await asyncio.gather(*discover_tasks, return_exceptions=True)

        logger.info(
            "Capability discovery attempts completed for all backend servers."
        )
        logger.info(
            f"Aggregated discovery: {len(self._tools)} tools, "
            f"{len(self._resources)} resources, "
            f"{len(self._prompts)} prompts."
        )
        logger.debug(f"Current route map: {self._route_map}")

    def get_aggregated_tools(self) -> List[mcp_types.Tool]:
        """Get the aggregated tool list."""
        return self._tools

    def get_aggregated_resources(self) -> List[mcp_types.Resource]:
        """Get the aggregated resource list."""
        return self._resources

    def get_aggregated_prompts(self) -> List[mcp_types.Prompt]:
        """Get the aggregated prompt list."""
        return self._prompts

    def resolve_capability(
        self, exp_cap_name: str
    ) -> Optional[Tuple[str, str]]:
        """
        Resolve an exposed capability name to:
        (backend server name, original backend capability name), or None.
        """
        return self._route_map.get(exp_cap_name)
