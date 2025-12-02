#!/bin/bash

###############################################################################
# Linux/Chrome Certificate Manager for mitmproxy (Wrapper Script)
#
# This is a thin wrapper around the new Python-based certificate installer.
# Maintains backwards compatibility with the old script interface.
#
# Usage:
#   ./chrome-cert-manager.sh install   - Install certificate
#   ./chrome-cert-manager.sh remove    - Remove certificate
#   ./chrome-cert-manager.sh status    - Check certificate status
###############################################################################

set -e

# Find the Python certificate manager
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_MANAGER="$SCRIPT_DIR/cert_manager.py"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "   Install Python 3 and try again"
    exit 1
fi

# Check if cert_manager.py exists
if [ ! -f "$CERT_MANAGER" ]; then
    echo "❌ Certificate manager not found: $CERT_MANAGER"
    echo "   Please ensure TraceTap is properly installed"
    exit 1
fi

show_usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND]

Commands:
    install     Install mitmproxy certificate system-wide
    remove      Remove mitmproxy certificate
    status      Show certificate installation status
    help        Show this help message

Examples:
    # First-time setup (requires sudo)
    ./$(basename "$0") install

    # Check if certificate is installed
    ./$(basename "$0") status

    # Remove certificate
    ./$(basename "$0") remove

Notes:
    - Installs certificate system-wide (requires sudo)
    - Works with Chrome, Curl, and system apps
    - For Firefox, additional setup may be required
    - Certificate file: ~/.mitmproxy/mitmproxy-ca-cert.pem

For detailed documentation:
    docs/CERTIFICATE_INSTALLATION.md
    docs/TROUBLESHOOTING.md

EOF
}

case "${1:-}" in
    install)
        python3 "$CERT_MANAGER" install
        ;;
    remove)
        python3 "$CERT_MANAGER" uninstall
        ;;
    status)
        echo "Certificate Installation Status"
        echo "================================"
        echo ""
        python3 "$CERT_MANAGER" info
        echo ""
        echo "Verification:"
        python3 "$CERT_MANAGER" verify
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "❌ Invalid command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac
