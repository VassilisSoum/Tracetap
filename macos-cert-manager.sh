#!/bin/bash

###############################################################################
# macOS Certificate Manager for mitmproxy
#
# This script installs or removes the mitmproxy CA certificate on macOS
# Works with Chrome, Safari, and Firefox
#
# Usage:
#   ./macos-cert-manager.sh install   - Install certificate
#   ./macos-cert-manager.sh remove    - Remove certificate
#   ./macos-cert-manager.sh status    - Check certificate status
###############################################################################

set -e

# Configuration
CERT_NAME="mitmproxy"
CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
# Use full path for keychain (required on newer macOS)
KEYCHAIN="$HOME/Library/Keychains/login.keychain-db"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

###############################################################################
# Helper Functions
###############################################################################

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_header() {
    echo ""
    echo "=================================================="
    echo "$1"
    echo "=================================================="
    echo ""
}

# macOS-compatible timeout function
run_with_timeout() {
    local timeout=$1
    shift
    local command=("$@")

    # Run command in background
    "${command[@]}" 2>/dev/null &
    local pid=$!

    # Wait with timeout
    local count=0
    while kill -0 $pid 2>/dev/null && [ $count -lt $timeout ]; do
        sleep 1
        count=$((count + 1))
    done

    # Kill if still running
    if kill -0 $pid 2>/dev/null; then
        kill $pid 2>/dev/null || true
        wait $pid 2>/dev/null || true
    fi
}

check_certificate_file() {
    if [ ! -f "$CERT_PATH" ]; then
        print_warning "Certificate not found at $CERT_PATH"
        print_info "Generating certificate by running mitmproxy briefly..."

        # Try TraceTap if available (Intel)
        if [ -f "./tracetap-macos-x64" ]; then
            print_info "Starting tracetap-macos-x64..."
            run_with_timeout 5 ./tracetap-macos-x64 --listen 8081
            sleep 2
        # Try TraceTap (Apple Silicon)
        elif [ -f "./tracetap-macos-arm64" ]; then
            print_info "Starting tracetap-macos-arm64..."
            run_with_timeout 5 ./tracetap-macos-arm64 --listen 8081
            sleep 2
        fi

        # Try Python version
        if [ ! -f "$CERT_PATH" ] && [ -f "tracetap.py" ]; then
            print_info "Starting tracetap.py..."
            run_with_timeout 5 python3 tracetap.py --listen 8081
            sleep 2
        fi

        # Fallback to mitmdump
        if [ ! -f "$CERT_PATH" ]; then
            if command -v mitmdump &> /dev/null; then
                print_info "Starting mitmdump..."
                run_with_timeout 5 mitmdump -p 8081
                sleep 2
            fi
        fi

        if [ ! -f "$CERT_PATH" ]; then
            print_error "Failed to generate certificate"
            print_info "Try running manually: mitmdump -p 8081"
            print_info "Then press Ctrl+C after a few seconds"
            exit 1
        fi
    fi
    print_success "Certificate found: $CERT_PATH"
}

###############################################################################
# Main Functions
###############################################################################

install_certificate() {
    print_header "Installing mitmproxy Certificate for macOS"

    check_certificate_file

    echo ""
    print_info "Installing certificate in macOS Keychain..."
    print_warning "You will be prompted for your password"

    # Remove old certificate if exists
    if security find-certificate -c "$CERT_NAME" login.keychain &> /dev/null; then
        print_info "Removing existing certificate..."
        security delete-certificate -c "$CERT_NAME" login.keychain 2>/dev/null || true
    fi

    # Import certificate into keychain
    # Using login.keychain without full path works better across macOS versions
    security add-trusted-cert -d -r trustRoot -k login.keychain "$CERT_PATH"

    if [ $? -eq 0 ]; then
        print_success "Certificate installed in Keychain"
    else
        print_error "Failed to install certificate"
        print_info "You may need to:"
        print_info "  1. Go to Keychain Access.app"
        print_info "  2. Find 'mitmproxy' certificate"
        print_info "  3. Double-click and set 'Always Trust'"
        exit 1
    fi

    # Install for Firefox if it exists
    echo ""
    FIREFOX_PROFILES="$HOME/Library/Application Support/Firefox/Profiles"
    if [ -d "$FIREFOX_PROFILES" ]; then
        # Check if certutil is available
        if command -v certutil &> /dev/null; then
            read -p "Install certificate for Firefox too? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                for profile in "$FIREFOX_PROFILES"/*.default*; do
                    if [ -d "$profile" ]; then
                        print_info "Installing for Firefox profile: $(basename "$profile")"
                        # Use sql: prefix for Firefox profile database
                        certutil -A -d "sql:$profile" -t "C,," -n "$CERT_NAME" -i "$CERT_PATH" 2>/dev/null || true
                    fi
                done
                print_success "Firefox certificate installed"
            fi
        else
            print_info "certutil not found - skipping Firefox"
            print_info "Install with: brew install nss"
        fi
    fi

    # Verify installation
    echo ""
    print_info "Verifying installation..."
    if security find-certificate -c "$CERT_NAME" login.keychain &> /dev/null; then
        print_success "Certificate verified in Keychain"

        # Show certificate details
        echo ""
        echo "Certificate details:"
        security find-certificate -c "$CERT_NAME" -p login.keychain 2>/dev/null | \
            openssl x509 -noout -subject -issuer -dates 2>/dev/null || true
    else
        print_error "Certificate not found in Keychain"
        exit 1
    fi

    print_header "Installation Complete!"

    echo "The certificate is now trusted by:"
    echo "  ✓ Safari"
    echo "  ✓ Chrome"
    echo "  ✓ All macOS system apps"
    if [ -d "$FIREFOX_PROFILES" ] && command -v certutil &> /dev/null; then
        echo "  ✓ Firefox"
    fi
    echo ""
    echo "Next steps:"
    echo "  1. Close and reopen all browsers"
    echo "  2. Start TraceTap:    ${GREEN}./tracetap-macos-* --listen 8080${NC}"
    echo "  3. Configure proxy in browser (use FoxyProxy extension)"
    echo "  4. Browse HTTPS sites - no certificate warnings!"
    echo ""
}

remove_certificate() {
    print_header "Removing mitmproxy Certificate"

    # Remove from macOS Keychain
    echo ""
    print_info "Removing certificate from Keychain..."
    print_warning "You may be prompted for your password"

    if security find-certificate -c "$CERT_NAME" login.keychain &> /dev/null; then
        security delete-certificate -c "$CERT_NAME" login.keychain
        print_success "Certificate removed from Keychain"
    else
        print_warning "Certificate not found in Keychain"
    fi

    # Remove from Firefox
    FIREFOX_PROFILES="$HOME/Library/Application Support/Firefox/Profiles"
    if [ -d "$FIREFOX_PROFILES" ] && command -v certutil &> /dev/null; then
        echo ""
        read -p "Remove certificate from Firefox too? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for profile in "$FIREFOX_PROFILES"/*.default*; do
                if [ -d "$profile" ]; then
                    if certutil -L -d "sql:$profile" 2>/dev/null | grep -q "$CERT_NAME"; then
                        certutil -D -d "sql:$profile" -n "$CERT_NAME" 2>/dev/null || true
                        print_info "Removed from Firefox profile: $(basename "$profile")"
                    fi
                fi
            done
            print_success "Firefox certificate removed"
        fi
    fi

    # Verify removal
    echo ""
    print_info "Verifying removal..."
    if security find-certificate -c "$CERT_NAME" login.keychain &> /dev/null; then
        print_error "Certificate still found in Keychain"
        exit 1
    else
        print_success "Certificate successfully removed"
    fi

    print_header "Removal Complete!"
    echo "Close and reopen all browsers for changes to take effect."
    echo ""
}

show_status() {
    print_header "Certificate Status"

    # Check certificate file
    if [ -f "$CERT_PATH" ]; then
        print_success "Certificate file exists: $CERT_PATH"

        # Show certificate info
        echo ""
        echo "Certificate details:"
        openssl x509 -in "$CERT_PATH" -noout -subject -issuer -dates 2>/dev/null || true
    else
        print_error "Certificate file not found: $CERT_PATH"
        print_info "Run TraceTap or mitmdump once to generate it"
    fi

    # Check macOS Keychain
    echo ""
    if security find-certificate -c "$CERT_NAME" login.keychain &> /dev/null; then
        print_success "Certificate installed in macOS Keychain"
        print_info "Trusted by Safari, Chrome, and system apps"

        echo ""
        echo "Keychain certificate info:"
        security find-certificate -c "$CERT_NAME" -p login.keychain 2>/dev/null | \
            openssl x509 -noout -subject -issuer 2>/dev/null || true
    else
        print_error "Certificate NOT installed in macOS Keychain"
    fi

    # Check Firefox
    echo ""
    FIREFOX_PROFILES="$HOME/Library/Application Support/Firefox/Profiles"
    if [ -d "$FIREFOX_PROFILES" ] && command -v certutil &> /dev/null; then
        firefox_installed=false
        for profile in "$FIREFOX_PROFILES"/*.default*; do
            if [ -d "$profile" ]; then
                if certutil -L -d "sql:$profile" 2>/dev/null | grep -q "$CERT_NAME"; then
                    firefox_installed=true
                    break
                fi
            fi
        done

        if $firefox_installed; then
            print_success "Certificate installed in Firefox"
        else
            print_info "Certificate not installed in Firefox"
        fi
    else
        print_info "Firefox not found or certutil not installed"
    fi

    # Check if proxy is running
    echo ""
    if lsof -i :8080 &> /dev/null 2>&1; then
        print_success "Proxy detected on port 8080"
    else
        print_info "No proxy running on port 8080"
    fi

    echo ""
}

show_usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND]

Commands:
    install     Install mitmproxy certificate in macOS Keychain
    remove      Remove mitmproxy certificate from Keychain
    status      Show certificate installation status
    help        Show this help message

Examples:
    # First-time setup
    ./$(basename "$0") install

    # Check if certificate is installed
    ./$(basename "$0") status

    # Remove certificate
    ./$(basename "$0") remove

Notes:
    - Works with Safari, Chrome, and all system apps
    - Firefox support requires: brew install nss
    - Certificate file: $CERT_PATH
    - Keychain: login.keychain
    - Close and reopen browsers after install/remove

EOF
}

###############################################################################
# Main Script
###############################################################################

case "${1:-}" in
    install)
        install_certificate
        ;;
    remove)
        remove_certificate
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Invalid command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac