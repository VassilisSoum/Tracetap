#!/bin/bash
# Fix TraceTap dependency conflicts

set -e

echo "🔧 Fixing TraceTap dependency conflicts..."
echo ""

# Uninstall conflicting typing-extensions
echo "📦 Removing conflicting typing-extensions..."
pip uninstall -y typing-extensions 2>/dev/null || true

# Reinstall dependencies in correct order
echo "📦 Installing TraceTap dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Dependencies fixed!"
echo ""
echo "To install development/testing tools:"
echo "  pip install -r requirements-dev.txt"
echo ""
echo "To verify installation:"
echo "  python -c 'import mitmproxy; import typing_extensions; print(f\"typing-extensions: {typing_extensions.__version__}\")'"
