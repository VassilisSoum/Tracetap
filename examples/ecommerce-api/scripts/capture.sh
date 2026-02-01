#!/bin/bash
# TraceTap E-commerce Capture Script
# Captures API traffic from the sample e-commerce server

set -e

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EXAMPLE_DIR="$SCRIPT_DIR/.."

echo "==================================================="
echo "  TraceTap E-commerce Traffic Capture"
echo "==================================================="
echo ""
echo "This script will:"
echo "  1. Start the TraceTap proxy on port 8080"
echo "  2. Capture traffic to localhost:5000"
echo "  3. Export to captured-traffic/checkout-flow.json"
echo ""
echo "Prerequisites:"
echo "  - Sample API running on port 5000"
echo "  - Run: python sample-api/server.py"
echo ""
echo "Press Ctrl+C to stop capture and export."
echo ""

cd "$PROJECT_ROOT"

python tracetap.py \
    --listen 8080 \
    --export "$EXAMPLE_DIR/captured-traffic/checkout-flow.json" \
    --raw-log "$EXAMPLE_DIR/captured-traffic/raw-traffic.json" \
    --session "ecommerce-checkout" \
    --filter-host "localhost:5000"
