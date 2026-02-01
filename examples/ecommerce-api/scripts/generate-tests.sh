#!/bin/bash
# TraceTap Test Generation Script
# Generates Playwright tests and OpenAPI contract from captured traffic

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EXAMPLE_DIR="$SCRIPT_DIR/.."

echo "==================================================="
echo "  TraceTap Test & Contract Generation"
echo "==================================================="
echo ""

cd "$PROJECT_ROOT"

# Check if traffic file exists
if [ ! -f "$EXAMPLE_DIR/captured-traffic/checkout-flow.json" ]; then
    echo "Error: No captured traffic found!"
    echo "Run capture.sh first to capture API traffic."
    exit 1
fi

echo "Generating Playwright regression tests..."
echo ""

python tracetap-replay.py generate-regression \
    "$EXAMPLE_DIR/captured-traffic/checkout-flow.json" \
    -o "$EXAMPLE_DIR/generated-tests/regression.spec.ts" \
    --grouping flow \
    --base-url http://localhost:5000

echo ""
echo "Generating OpenAPI contract..."
echo ""

python tracetap-replay.py create-contract \
    "$EXAMPLE_DIR/captured-traffic/checkout-flow.json" \
    -o "$EXAMPLE_DIR/contracts/ecommerce-api.yaml" \
    --title "E-commerce API" \
    --version "1.0.0"

echo ""
echo "==================================================="
echo "  Generation Complete!"
echo "==================================================="
echo ""
echo "Generated files:"
echo "  - generated-tests/regression.spec.ts"
echo "  - contracts/ecommerce-api.yaml"
echo ""
echo "Next steps:"
echo "  1. Run tests: npx playwright test generated-tests/"
echo "  2. View contract: cat contracts/ecommerce-api.yaml"
