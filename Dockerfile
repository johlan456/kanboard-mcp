# syntax=docker/dockerfile:1
FROM python:3.12-slim

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached layer), then the package.
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system --no-cache .

# Non-root runtime.
RUN useradd --system --uid 1000 appuser
USER appuser

# Bind all interfaces inside the container; the host/tunnel controls exposure.
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

CMD ["kanboard-mcp"]
