# ClawBots Production Dockerfile
# Multi-stage build for minimal image size

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install production extras
RUN pip install --no-cache-dir \
    asyncpg \
    redis \
    prometheus-client \
    python-json-logger \
    gunicorn

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM python:3.12-slim as production

# Labels
LABEL maintainer="Kalrav <kalrav-dev@proton.me>"
LABEL org.opencontainers.image.title="ClawBots"
LABEL org.opencontainers.image.description="A Living World for AI Agents"
LABEL org.opencontainers.image.version="0.2.0"

# Create non-root user
RUN groupadd -r clawbots && useradd -r -g clawbots clawbots

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ /app/src/
COPY web/ /app/web/

# Create directories
RUN mkdir -p /app/data /app/logs && \
    chown -R clawbots:clawbots /app

# Switch to non-root user
USER clawbots

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    CLAWBOTS_ENV=production \
    LOG_LEVEL=INFO \
    WORKERS=4

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Stage 3: Development (optional)
# =============================================================================
FROM production as development

USER root

# Install dev dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    httpx \
    black \
    ruff

USER clawbots

ENV CLAWBOTS_ENV=development

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
