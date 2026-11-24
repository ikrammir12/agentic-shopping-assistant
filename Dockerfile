# Use Python 3.14
FROM python:3.14-slim

# Install a pinned version of UV
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

# Python and UV configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

# Set working directory
WORKDIR /app

# Copy dependency configuration first
COPY pyproject.toml uv.lock ./

# Install production dependencies using the lockfile
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code
COPY app/ ./app/
COPY Database/ ./Database/

# Create a non-root application user
# Give it permission to write to SQLite and application logs
RUN groupadd --system appuser \
    && useradd --system --gid appuser \
       --home-dir /home/appuser --create-home appuser \
    && mkdir -p /app/app/logs \
    && chown -R appuser:appuser /app/Database /app/app/logs

# Use the virtual environment
ENV PATH="/app/.venv/bin:${PATH}"

# Run as a non-root user
USER appuser

# FastAPI port
EXPOSE 8000

# Container health check
HEALTHCHECK --interval=30s \
    --timeout=5s \
    --start-period=20s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]