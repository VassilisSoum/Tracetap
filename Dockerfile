# Multi-stage build for optimized TraceTap Docker image
# Target size: < 500MB

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-replay.txt ./
COPY pyproject.toml ./

# Install Python dependencies to /install
RUN pip install --no-cache-dir --prefix=/install \
    -r requirements.txt \
    -r requirements-replay.txt

# Stage 2: Runtime
FROM python:3.11-slim

LABEL maintainer="Vassilis Soumakis"
LABEL description="TraceTap - HTTP/HTTPS traffic capture proxy with AI-powered testing tools"
LABEL version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Create app directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY tracetap.py tracetap-replay.py tracetap-playwright.py ./
COPY pyproject.toml README.md LICENSE ./

# Create directory for captures
RUN mkdir -p /captures /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MITMPROXY_CONFDIR=/data/.mitmproxy

# Expose proxy port
EXPOSE 8080

# Expose mock server port (if used)
EXPOSE 8081

# Default command: show help
CMD ["python", "tracetap.py", "--help"]

# Volume for persistent data (captures, certs)
VOLUME ["/data", "/captures"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1
