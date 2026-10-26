# syntax=docker/dockerfile:1
FROM python:3.12-slim

# uv for fast, reproducible installs. Pinned so builds don't drift.
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

# Install the exact locked dependency set first (cached layer), then the
# package. --frozen fails the build if uv.lock is out of date with pyproject.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# Non-root runtime.
RUN useradd --system --uid 1000 appuser
USER appuser

# Bind all interfaces inside the container; the host/tunnel controls exposure.
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

CMD ["kanboard-mcp"]
