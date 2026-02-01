#!/bin/bash
# TraceTap Regression Test Runner
# Runs Playwright tests and generates reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$SCRIPT_DIR/.."
TESTS_DIR="$EXAMPLE_DIR/generated-tests"

echo "==================================================="
echo "  TraceTap Regression Test Runner"
echo "==================================================="
echo ""

cd "$TESTS_DIR"

# Check for dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    npx playwright install
    echo ""
fi

# Parse arguments
REPORT=false
DEBUG=false
UI=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --report) REPORT=true ;;
        --debug) DEBUG=true ;;
        --ui) UI=true ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --report    Show HTML report after tests"
            echo "  --debug     Run tests in debug mode"
            echo "  --ui        Run tests in UI mode"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Run tests
if [ "$UI" = true ]; then
    echo "Running tests in UI mode..."
    npx playwright test --ui
elif [ "$DEBUG" = true ]; then
    echo "Running tests in debug mode..."
    npx playwright test --debug
else
    echo "Running regression tests..."
    npx playwright test

    if [ "$REPORT" = true ]; then
        echo ""
        echo "Opening test report..."
        npx playwright show-report
    fi
fi

echo ""
echo "==================================================="
echo "  Test Run Complete"
echo "==================================================="
