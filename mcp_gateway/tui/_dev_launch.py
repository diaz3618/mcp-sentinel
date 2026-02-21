"""Launcher for Textual dev tools — adds project root to sys.path.

The Textual MCP server is a long-running process that caches modules in
``sys.modules``.  To ensure every ``textual run`` invocation picks up the
latest source code we purge all ``mcp_gateway`` sub-modules before
re-importing ``GatewayApp``.
"""

import glob  # noqa: I001
import importlib
import os
import sys

# Add both the project root and the .venv site-packages to sys.path
# so the Textual MCP server can resolve the package and its dependencies.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Also add the venv site-packages for dependencies like mcp, starlette, etc.
_venv_sp = glob.glob(os.path.join(_project_root, ".venv", "lib", "python*", "site-packages"))
for sp in _venv_sp:
    if sp not in sys.path:
        sys.path.insert(1, sp)

# Purge cached mcp_gateway modules so the MCP server always uses fresh code.
_stale = [k for k in sys.modules if k == "mcp_gateway" or k.startswith("mcp_gateway.")]
for _k in _stale:
    del sys.modules[_k]

import mcp_gateway.tui.app  # noqa: E402

importlib.reload(mcp_gateway.tui.app)

app = mcp_gateway.tui.app.GatewayApp
