# TraceTap Docker Guide

Run TraceTap in Docker with zero local setup required.

## Quick Start

### Option 1: Run directly with Docker

```bash
# Pull the image (once published to Docker Hub)
docker pull tracetap/tracetap:latest

# Run TraceTap proxy
docker run -it --rm \
  -p 8080:8080 \
  -v $(pwd)/captures:/captures \
  tracetap/tracetap \
  python tracetap.py --listen 8080 --raw-log /captures/capture.json
```

### Option 2: Use Docker Compose (Recommended)

```bash
# Start TraceTap proxy
docker-compose up tracetap

# Start mock server
docker-compose --profile mock up tracetap-mock

# Replay traffic
docker-compose --profile replay up tracetap-replay
```

## Configuration

### Environment Variables

Set these in a `.env` file or pass via `-e`:

```bash
# Required for AI features
ANTHROPIC_API_KEY=your-api-key-here

# Optional: customize mitmproxy config location
MITMPROXY_CONFDIR=/data/.mitmproxy
```

### Volumes

- `/data` - Persistent storage for mitmproxy certificates and config
- `/captures` - Mount this to save/load capture files

## Common Use Cases

### 1. Basic Traffic Capture

```bash
docker run -it --rm \
  -p 8080:8080 \
  -v $(pwd)/captures:/captures \
  tracetap/tracetap \
  python tracetap.py \
    --listen 8080 \
    --raw-log /captures/session.json \
    --export /captures/collection.json
```

**Configure your app to use proxy:** `http://localhost:8080`

### 2. Capture with Host Filtering

```bash
docker run -it --rm \
  -p 8080:8080 \
  -v $(pwd)/captures:/captures \
  tracetap/tracetap \
  python tracetap.py \
    --listen 8080 \
    --filter api.example.com \
    --raw-log /captures/api-only.json
```

### 3. Run Mock Server

```bash
docker run -it --rm \
  -p 9000:9000 \
  -v $(pwd)/captures:/captures \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  tracetap/tracetap \
  python tracetap-replay.py \
    /captures/session.json \
    --mock-server \
    --mock-port 9000 \
    --mock-mode intelligent
```

**Access mock server:** `http://localhost:9000`

### 4. Replay Traffic to Staging

```bash
docker run -it --rm \
  -v $(pwd)/captures:/captures \
  tracetap/tracetap \
  python tracetap-replay.py \
    /captures/production.json \
    --target https://staging.example.com \
    --workers 5
```

### 5. Generate Playwright Tests

```bash
docker run -it --rm \
  -v $(pwd)/captures:/captures \
  -v $(pwd)/tests:/tests \
  tracetap/tracetap \
  python tracetap-playwright.py \
    /captures/collection.json \
    -o /tests/api.spec.ts
```

## Docker Compose Examples

### Capture Mode

```yaml
# docker-compose.yml
services:
  tracetap:
    image: tracetap/tracetap:latest
    ports:
      - "8080:8080"
    volumes:
      - ./captures:/captures
    command: >
      python tracetap.py
      --listen 8080
      --raw-log /captures/capture.json
```

```bash
docker-compose up
```

### Mock Server Mode

```yaml
services:
  tracetap-mock:
    image: tracetap/tracetap:latest
    ports:
      - "9000:9000"
    volumes:
      - ./captures:/captures
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    command: >
      python tracetap-replay.py
      /captures/session.json
      --mock-server
      --mock-port 9000
```

```bash
export ANTHROPIC_API_KEY=your-key
docker-compose up tracetap-mock
```

## Building the Image

### Local Build

```bash
# Build the image
docker build -t tracetap/tracetap:latest .

# Check image size
docker images tracetap/tracetap:latest

# Should be < 500MB
```

### Multi-platform Build

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -t tracetap/tracetap:latest \
  --push .
```

## Certificate Management

### First Run

On first run, mitmproxy generates a CA certificate. To trust it:

#### macOS

```bash
# Copy certificate from container
docker cp tracetap:/data/.mitmproxy/mitmproxy-ca-cert.pem .

# Install to keychain
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  mitmproxy-ca-cert.pem
```

#### Linux

```bash
# Copy certificate
docker cp tracetap:/data/.mitmproxy/mitmproxy-ca-cert.pem .

# Install (Ubuntu/Debian)
sudo cp mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates
```

#### Windows

```bash
# Copy certificate
docker cp tracetap:/data/.mitmproxy/mitmproxy-ca-cert.pem .

# Import via certmgr.msc to "Trusted Root Certification Authorities"
```

### Persistent Certificates

Use a volume to persist certificates across container restarts:

```bash
docker run -it --rm \
  -p 8080:8080 \
  -v tracetap-data:/data \
  -v $(pwd)/captures:/captures \
  tracetap/tracetap
```

## Troubleshooting

### Issue: Cannot connect to proxy

**Solution:** Ensure port 8080 is accessible and not blocked by firewall:

```bash
# Test connection
curl -x http://localhost:8080 http://example.com
```

### Issue: HTTPS traffic not captured

**Solution:** Install mitmproxy CA certificate (see Certificate Management above)

### Issue: Permission denied writing captures

**Solution:** Fix volume permissions:

```bash
# Create captures directory with correct permissions
mkdir -p captures
chmod 777 captures  # Or set appropriate user permissions
```

### Issue: Container exits immediately

**Solution:** Check logs:

```bash
docker logs tracetap
```

Most likely missing command or invalid arguments.

### Issue: Image size too large

**Solution:** The multi-stage build should keep it under 500MB. If larger:

```bash
# Remove unused dependencies
# Check .dockerignore includes test files, docs, etc.
docker build --no-cache -t tracetap/tracetap:latest .
```

## Publishing

### Docker Hub

```bash
# Login
docker login

# Tag
docker tag tracetap/tracetap:latest tracetap/tracetap:1.0.0

# Push
docker push tracetap/tracetap:latest
docker push tracetap/tracetap:1.0.0
```

### GitHub Container Registry

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag
docker tag tracetap/tracetap:latest ghcr.io/vassilissoum/tracetap:latest

# Push
docker push ghcr.io/vassilissoum/tracetap:latest
```

## Best Practices

1. **Use specific versions** in production, not `latest`
2. **Persist certificates** using volumes to avoid re-trusting
3. **Set API key** via environment variables, not in command
4. **Mount captures directory** to access files from host
5. **Use docker-compose** for complex setups with multiple services
6. **Check health** with `docker ps` to ensure container is healthy
7. **Review logs** with `docker logs tracetap` for debugging

## Resources

- [Dockerfile](../Dockerfile)
- [docker-compose.yml](../docker-compose.yml)
- [Main Documentation](../README.md)
- [Replay Documentation](../REPLAY.md)

## Support

For Docker-specific issues:
- Check existing issues: https://github.com/VassilisSoum/tracetap/issues
- Create new issue with `docker` label
