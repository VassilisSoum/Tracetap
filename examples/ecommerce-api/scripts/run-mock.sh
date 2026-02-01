#!/bin/bash
# TraceTap Mock Server Script
# Runs a mock server using captured traffic

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EXAMPLE_DIR="$SCRIPT_DIR/.."

echo "==================================================="
echo "  TraceTap Mock Server"
echo "==================================================="
echo ""

cd "$PROJECT_ROOT"

# Check if traffic file exists
if [ ! -f "$EXAMPLE_DIR/captured-traffic/checkout-flow.json" ]; then
    echo "Error: No captured traffic found!"
    echo "Run capture.sh first to capture API traffic."
    exit 1
fi

MOCK_PORT=${1:-9000}
MATCHING_MODE=${2:-fuzzy}

echo "Starting mock server..."
echo "  Port: $MOCK_PORT"
echo "  Matching: $MATCHING_MODE"
echo "  Traffic: checkout-flow.json"
echo ""
echo "Access mock at: http://localhost:$MOCK_PORT"
echo "Press Ctrl+C to stop."
echo ""

python tracetap-replay.py mock \
    "$EXAMPLE_DIR/captured-traffic/checkout-flow.json" \
    --port "$MOCK_PORT" \
    --matching "$MATCHING_MODE"
