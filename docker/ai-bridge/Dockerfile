# ClawBots AI Bridge
# Connects OpenSim bots to LLM providers

FROM python:3.11-slim

LABEL maintainer="Kalrav <kalrav-dev@proton.me>"
LABEL description="ClawBots AI Bridge - LLM integration for virtual agents"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -sf http://localhost:8765/health || exit 1

# Run server
CMD ["python", "server.py"]
