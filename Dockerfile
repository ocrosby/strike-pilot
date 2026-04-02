FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first so Docker caches the install layer
COPY pyproject.toml uv.lock ./

# Install runtime dependencies only (no dev extras)
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/

EXPOSE 8000

# Liveness probe — restart the container if the process stops responding.
# Uses Python's stdlib so no extra tooling is needed in the slim image.
# Kubernetes configures readiness and startup probes in the Pod spec; the
# Docker HEALTHCHECK covers non-Kubernetes environments (docker run, Compose).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')" \
    || exit 1

CMD ["uv", "run", "strike-pilot", "serve", "--host", "0.0.0.0", "--port", "8000"]
