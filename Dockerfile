FROM python:3.11-slim-bullseye AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

# Install dependencies and create virtual environment
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-cache --no-root

FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKSPACE_DIR="/app/agent_workspace" \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

# Create a non-root user with proper home directory
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /home/appuser -m appuser && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser

WORKDIR /app

# Create necessary directories
RUN mkdir -p ${WORKSPACE_DIR} && \
    chown -R appuser:appuser /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY --chown=appuser:appuser . .

# Set proper permissions
RUN chmod -R 750 /app && \
    chown -R appuser:appuser /app/.venv

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use shell form for better environment variable handling
CMD ["sh", "-c", "poetry run python api.py"]