#!/bin/bash
set -e

# Start Xvfb (virtual framebuffer)
Xvfb $DISPLAY -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH} -ac &
sleep 1

# Start fluxbox window manager
fluxbox &
sleep 1

# Start VNC server (no password for local use)
x11vnc -display $DISPLAY -forever -nopw -quiet -xkb &
sleep 1

# Start noVNC (websocket bridge to VNC)
websockify --web /usr/share/novnc $NOVNC_PORT localhost:$VNC_PORT &

echo ""
echo "========================================="
echo "  TraceTap is ready!"
echo "  Open http://localhost:${NOVNC_PORT} in your browser"
echo "  for the noVNC desktop interface."
echo ""
echo "  Run commands in this terminal:"
echo "    tracetap record https://example.com"
echo "    tracetap generate recordings/<id> -o tests/test.spec.ts"
echo "    tracetap doctor"
echo "========================================="
echo ""

# Execute the provided command (default: bash)
exec "$@"
