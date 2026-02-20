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
        mcp_cls: Union[Type[mcp_types.Tool], Type[mcp_types.Resource], Type[mcp_types.Prompt]],
        agg_list: List[Any],
    ) -> None:
        """
        Generic helper to discover and register a specific capability type.

        If a name conflict occurs (same capability from different servers),
        the new one is ignored and a warning is logged.

        TODO: Make conflict resolution strategy configurable
        (for example, auto-prefixing).
        """
        logger.debug("[%s] Starting discovery for %s...", svr_name, cap_type)
        try:
            list_method = getattr(session, list_method_name)
            logger.debug(
                "[%s] Requesting %s list (timeout %ss)...",
                svr_name,
                cap_type,
                CAP_FETCH_TIMEOUT,
            )

            list_result = await asyncio.wait_for(list_method(), timeout=CAP_FETCH_TIMEOUT)

            orig_caps: List[Any] = []

            if hasattr(list_result, cap_type) and isinstance(getattr(list_result, cap_type), list):
                orig_caps = getattr(list_result, cap_type)
            elif isinstance(list_result, list):
                orig_caps = list_result
            elif list_result is None:
                logger.info(
                    "[%s] %s() returned None, treating as no %s.",
                    svr_name,
                    list_method_name,
                    cap_type,
                )
                orig_caps = []
            else:
                logger.warning(
                    "[%s] %s() returned unknown type %s; " "unable to parse %s list. Raw value: %r",
                    svr_name,
                    list_method_name,
                    type(list_result),
                    cap_type,
                    list_result,
                )
                orig_caps = []

            logger.debug(
                "[%s] Parsed %s raw %s from response.",
                svr_name,
                len(orig_caps),
                cap_type,
            )

            registered_count = 0
            for cap_item_raw in orig_caps:
                if not isinstance(cap_item_raw, mcp_cls):
                    logger.warning(
                        "[%s] Found non-%s object, skipped: %r",
                        svr_name,
                        mcp_cls.__name__,
                        cap_item_raw,
                    )
                    continue

                cap_item = cast(
                    Union[mcp_types.Tool, mcp_types.Resource, mcp_types.Prompt],
                    cap_item_raw,
                )

                if not cap_item.name:
                    logger.warning(
                        "[%s] Found unnamed %s, skipped: %r",
                        svr_name,
                        cap_type[:-1],
                        cap_item,
                    )
                    continue

                exp_cap_name = cap_item.name

                if exp_cap_name in self._route_map:
                    exist_svr_name, _ = self._route_map[exp_cap_name]
                    if exist_svr_name != svr_name:
                        logger.warning(
                            "Conflict: %s '%s' is already registered by "
                            "server '%s'. The duplicate from server '%s' "
                            "will be ignored.",
                            cap_type[:-1],
                            exp_cap_name,
                            exist_svr_name,
                            svr_name,
                        )
                        continue
                    else:
                        logger.warning(
                            "[%s] Duplicate %s provided multiple times: "
                            "'%s'. Only the first instance is registered.",
                            svr_name,
                            cap_type[:-1],
                            exp_cap_name,
                        )
                        continue

                agg_list.append(cap_item)
                self._route_map[exp_cap_name] = (svr_name, cap_item.name)
                registered_count += 1

            if registered_count > 0:
                logger.info(
                    "[%s] Registered %s unique %s.",
                    svr_name,
                    registered_count,
                    cap_type,
                )
            else:
                logger.info(
                    "[%s] No new %s discovered or registered.",
                    svr_name,
                    cap_type,
                )

        except asyncio.TimeoutError:
            logger.error(
                "[%s] %s() timed out (>%ss).",
                svr_name,
                list_method_name,
                CAP_FETCH_TIMEOUT,
            )
        except mcp_types.Error as mcp_e:
            logger.error(
                "[%s] MCP error during %s(): Type=%s, Msg='%s'",
                svr_name,
                list_method_name,
                mcp_e.type,
                mcp_e.message,
                exc_info=False,
            )
        except Exception:
            logger.exception(
                "[%s] Unknown error while discovering %s.",
                svr_name,
                cap_type,
            )

    async def discover_and_register(self, sessions: Dict[str, ClientSession]) -> None:
        """Discover and register MCP capabilities from active backend sessions."""
        logger.info(
            "Starting capability discovery/registration from " "%s active sessions...",
            len(sessions),
        )

        self._tools.clear()
        self._resources.clear()
        self._prompts.clear()
        self._route_map.clear()

        discover_tasks = []
        for svr_name, session in sessions.items():
            if not session:
                logger.warning(
                    "Skipping server '%s' because it has no valid session.",
                    svr_name,
                )
                continue

            discover_tasks.append(
                self._discover_caps_by_type(
                    svr_name,
                    session,
                    "tools",
                    "list_tools",
                    mcp_types.Tool,
                    self._tools,
                )
            )
            discover_tasks.append(
                self._discover_caps_by_type(
                    svr_name,
                    session,
                    "resources",
                    "list_resources",
                    mcp_types.Resource,
                    self._resources,
                )
            )
            discover_tasks.append(
                self._discover_caps_by_type(
                    svr_name,
                    session,
                    "prompts",
                    "list_prompts",
                    mcp_types.Prompt,
                    self._prompts,
                )
            )

        results = await asyncio.gather(*discover_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Capability discovery task %d failed: %s",
                    i,
                    result,
                    exc_info=result,
                )

        logger.info("Capability discovery attempts completed for all backend servers.")
        logger.info(
            "Aggregated discovery: %s tools, %s resources, %s prompts.",
            len(self._tools),
            len(self._resources),
            len(self._prompts),
        )
        logger.debug("Current route map: %s", self._route_map)

    def get_aggregated_tools(self) -> List[mcp_types.Tool]:
        """Get the aggregated tool list."""
        return self._tools

    def get_aggregated_resources(self) -> List[mcp_types.Resource]:
        """Get the aggregated resource list."""
        return self._resources

    def get_aggregated_prompts(self) -> List[mcp_types.Prompt]:
        """Get the aggregated prompt list."""
        return self._prompts

    def get_route_map(self) -> Dict[str, Tuple[str, str]]:
        """Get the capability-to-server routing map."""
        return self._route_map.copy()

    def resolve_capability(self, exp_cap_name: str) -> Optional[Tuple[str, str]]:
        """
        Resolve an exposed capability name to:
        (backend server name, original backend capability name), or None.
        """
        return self._route_map.get(exp_cap_name)
