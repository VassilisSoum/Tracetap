FROM python:3.12-slim-bookworm

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for Playwright, noVNC, and mitmproxy
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright browser dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libwayland-client0 \
    # X11 virtual framebuffer + window manager
    xvfb x11vnc fluxbox \
    # noVNC for browser-based access
    novnc websockify \
    # Utilities
    procps curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install TraceTap and dependencies
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir -e ".[dev]" && \
    # Install Playwright and Chromium browser
    playwright install chromium && \
    playwright install-deps chromium

# Generate mitmproxy CA certificate and install it
RUN mitmdump --set listen_port=0 --set connection_strategy=lazy -q &  \
    sleep 2 && kill %1 2>/dev/null; \
    # Install cert into system trust store
    cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && \
    update-ca-certificates

# noVNC configuration
ENV DISPLAY=:99
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV SCREEN_WIDTH=1920
ENV SCREEN_HEIGHT=1080
ENV SCREEN_DEPTH=24

# Startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose noVNC web interface
EXPOSE 6080

# Working directory for recordings
VOLUME /app/recordings

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["bash"]
