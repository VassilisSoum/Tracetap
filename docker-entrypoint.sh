#!/bin/bash
set -e

# Start Xvfb (virtual framebuffer) - needed for headed browser
if ! pgrep -x Xvfb > /dev/null 2>&1; then
    Xvfb $DISPLAY -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH} -ac > /dev/null 2>&1 &
    sleep 1
fi

# Only start desktop services if we're running interactively (bash/shell)
# Skip noVNC noise for one-off commands like 'tracetap generate'
if [ "$1" = "bash" ] || [ "$1" = "sh" ] || [ -z "$1" ]; then
    # Start fluxbox window manager
    fluxbox > /dev/null 2>&1 &
    sleep 1

    # Start VNC server
    x11vnc -display $DISPLAY -forever -nopw -quiet -xkb -localhost > /dev/null 2>&1 &
    sleep 1

    # Start noVNC
    websockify --web /usr/share/novnc $NOVNC_PORT localhost:$VNC_PORT > /dev/null 2>&1 &

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
fi

# Execute the provided command (default: bash)
exec "$@"
