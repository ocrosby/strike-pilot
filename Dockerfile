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

CMD ["uv", "run", "strike-pilot", "serve", "--host", "0.0.0.0", "--port", "8000"]
