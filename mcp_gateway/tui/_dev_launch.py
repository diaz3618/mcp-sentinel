"""Launcher for Textual dev tools — adds project root to sys.path."""
import glob  # noqa: I001
import os
import sys

# Add both the project root and the .venv site-packages to sys.path
# so the Textual MCP server can resolve the package and its dependencies.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

# Also add the venv site-packages for dependencies like mcp, starlette, etc.
_venv_sp = glob.glob(os.path.join(_project_root, ".venv", "lib", "python*", "site-packages"))
for sp in _venv_sp:
    if sp not in sys.path:
        sys.path.insert(1, sp)

from mcp_gateway.tui.app import GatewayApp  # noqa: E402

app = GatewayApp
