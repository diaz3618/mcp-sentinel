"""Shared constants for MCP Sentinel."""

SERVER_NAME = "MCP Sentinel"
SERVER_VERSION = "0.1.0"
AUTHOR = "diaz3618"

# Network defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000

# SSE transport paths
SSE_PATH = "/sse"
POST_MESSAGES_PATH = "/messages/"

# Logging defaults
LOG_DIR = "logs"
DEFAULT_LOG_FILE = "unknown_sentinel.log"
DEFAULT_LOG_LEVEL = "INFO"

# Backend connection timeouts
SSE_LOCAL_START_DELAY = 5  # seconds to wait for local SSE server startup
MCP_INIT_TIMEOUT = 15  # seconds for MCP session initialization
CAP_FETCH_TIMEOUT = 10.0  # seconds for capability list fetch
