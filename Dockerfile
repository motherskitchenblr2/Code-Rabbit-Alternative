# =============================================================================
# Git-Fix Dockerfile - Multi-stage Build
# =============================================================================
# Usage:
#   Development: docker build --target development -t gitfix-api .
#   Production:  docker build --target production -t gitfix-api .
# =============================================================================

# =============================================================================
# BASE IMAGE
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.7.1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r gitfix && useradd -r -g gitfix -m -d /home/gitfix -s /bin/bash gitfix

# Set working directory
WORKDIR /app

# =============================================================================
# BUILDER STAGE - Install dependencies
# =============================================================================
FROM base as builder

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    less \
    netcat-openbsd \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/gitfix/.local

# Add local bin to PATH
ENV PATH=/home/gitfix/.local/bin:$PATH

# Copy application code
COPY --chown=gitfix:gitfix . .

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/tmp /app/celerybeat-schedule && \
    chown -R gitfix:gitfix /app/logs /app/uploads /app/tmp /app/celerybeat-schedule

# Switch to non-root user
USER gitfix

# Add local bin to PATH
ENV PATH=/home/gitfix/.local/bin:$PATH

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_DEBUG=true \
    FLASK_ENV=development \
    PORT=5000

# Expose ports
EXPOSE 5000

# Default command for development (with hot reload)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--debugger", "--reload", "--with-threads"]

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM base as production

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/gitfix/.local

# Add local bin to PATH
ENV PATH=/home/gitfix/.local/bin:$PATH

# Copy application code
COPY --chown=gitfix:gitfix . .

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/tmp && \
    chown -R gitfix:gitfix /app/logs /app/uploads /app/tmp

# Switch to non-root user
USER gitfix

# Add local bin to PATH
ENV PATH=/home/gitfix/.local/bin:$PATH

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_DEBUG=false \
    FLASK_ENV=production \
    PORT=5000

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Run application with Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]