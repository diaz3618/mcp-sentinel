# ──────────────────────────────────────────────────────────────
# MCP Sentinel — Multi-stage Docker build
# ──────────────────────────────────────────────────────────────
# Stage 1: Build environment (install deps with uv)
# Stage 2: Slim runtime image
#
# Usage:
#   docker build -t mcp-sentinel .
#   docker run -p 9000:9000 -v ./config.yaml:/app/config.yaml mcp-sentinel
#
# Mount a custom config:
#   docker run -p 8080:8080 \
#     -v ./my-config.yaml:/app/config.yaml \
#     mcp-sentinel server --host 0.0.0.0 --port 8080
#
# For stdio-based backend MCP servers that need Node.js (npx):
#   The runtime image includes Node.js LTS for npx-based servers.
# ──────────────────────────────────────────────────────────────

# ── Stage 1: Builder ────────────────────────────────────────
# nosemgrep: docker-user-root (builder stage is discarded; runtime uses USER sentinel)
FROM python:3.13-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy dependency metadata first (cache-friendly layer)
COPY pyproject.toml ./
COPY mcp_sentinel/ ./mcp_sentinel/

# Install the package and all runtime dependencies into a virtual env
# nosemgrep: docker-pip-no-cache (uv uses --no-cache, not --no-cache-dir)
# nosemgrep: dependency-docker-no-unpinned-pip-install
RUN uv venv /opt/venv && \
    UV_LINK_MODE=copy uv pip install --no-cache --python /opt/venv/bin/python . && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true


# ── Stage 2: Runtime ───────────────────────────────────────
# nosemgrep: docker-user-root (USER sentinel set below at line ~80)
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="MCP Sentinel" \
      org.opencontainers.image.description="Central aggregation server for MCP (Model Context Protocol) backends" \
      org.opencontainers.image.source="https://github.com/diaz3618/MCP-Gateway" \
      org.opencontainers.image.licenses="GPL-3.0-only"

# Install Node.js LTS (for npx-based MCP backend servers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Put the venv on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for runtime security
RUN groupadd -r sentinel && useradd -r -g sentinel -d /app sentinel

WORKDIR /app

# Copy example config as fallback (user should mount their own config.yaml)
COPY example_config.yaml ./example_config.yaml
COPY example_config.yaml ./config.yaml

# Create directories for logs and PID files (owned by sentinel user)
RUN mkdir -p /app/logs /app/pids && chown -R sentinel:sentinel /app

# Switch to non-root user
USER sentinel

# Default port
EXPOSE 9000

# Health check via the management API
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/manage/v1/health')" || exit 1

# Run the server bound to all interfaces
ENTRYPOINT ["mcp-sentinel"]
CMD ["server", "--host", "0.0.0.0", "--port", "9000"]
