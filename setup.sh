#!/bin/bash
# TraceTap Setup Script
# Installs dependencies and verifies the installation

set -e

echo "╔═══════════════════════════════════════╗"
echo "║   TraceTap Setup                      ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python $python_version detected"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
echo ""

echo "╔═══════════════════════════════════════╗"
echo "║   Setup Complete!                     ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "📚 Quick Start:"
echo "   python3 tracetap_main.py --listen 8080"
echo ""
echo "   Then configure your client:"
echo "   export HTTP_PROXY=http://localhost:8080"
echo "   export HTTPS_PROXY=http://localhost:8080"
echo ""
echo "📖 See README.md for full documentation"
echo ""
