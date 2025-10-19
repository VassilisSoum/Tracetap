#!/bin/bash

###############################################################################
# Chrome Certificate Manager for mitmproxy
#
# This script installs or removes the mitmproxy CA certificate for Chrome
# on Linux systems.
#
# Usage:
#   ./chrome-cert-manager.sh install   - Install certificate
#   ./chrome-cert-manager.sh remove    - Remove certificate
#   ./chrome-cert-manager.sh status    - Check certificate status
#   ./chrome-cert-manager.sh restart   - Restart Chrome
#   ./chrome-cert-manager.sh verify    - Test HTTPS interception
###############################################################################

set -e

# Configuration
CERT_NAME="mitmproxy"
CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
NSS_DB="sql:$HOME/.pki/nssdb"
SYSTEM_CERT_PATH="/usr/local/share/ca-certificates/mitmproxy.crt"

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

check_certutil() {
    if ! command -v certutil &> /dev/null; then
        print_warning "certutil not found. Installing libnss3-tools..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y libnss3-tools
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y nss-tools
        elif command -v pacman &> /dev/null; then
            sudo pacman -S nss
        else
            print_error "Cannot install certutil automatically. Please install libnss3-tools manually."
            exit 1
        fi
    fi
    print_success "certutil is available"
}

check_certificate_file() {
    if [ ! -f "$CERT_PATH" ]; then
        print_warning "Certificate not found at $CERT_PATH"
        print_info "Generating certificate by running mitmproxy briefly..."

        # Try TraceTap if available
        if [ -f "./tracetap-linux-x64" ]; then
            timeout 5 ./tracetap-linux-x64 --listen 8081 2>/dev/null || true
            sleep 2
        fi

        # Try Python version
        if [ ! -f "$CERT_PATH" ] && [ -f "tracetap.py" ]; then
            timeout 5 python3 tracetap.py --listen 8081 2>/dev/null || true
            sleep 2
        fi

        # Fallback to mitmdump
        if [ ! -f "$CERT_PATH" ]; then
            timeout 5 mitmdump -p 8081 2>/dev/null || true
            sleep 2
        fi

        if [ ! -f "$CERT_PATH" ]; then
            print_error "Failed to generate certificate"
            print_info "Try running: mitmdump -p 8081"
            print_info "Then press Ctrl+C after a few seconds"
            exit 1
        fi
    fi
    print_success "Certificate found: $CERT_PATH"
}

create_nss_db() {
    if [ ! -d "$HOME/.pki/nssdb" ]; then
        print_info "Creating NSS database..."
        mkdir -p "$HOME/.pki/nssdb"
        certutil -N -d "$NSS_DB" --empty-password
        print_success "NSS database created"
    else
        print_success "NSS database exists"
    fi
}

restart_chrome() {
    print_info "Restarting Chrome..."

    # Kill all Chrome processes gracefully
    if pgrep -x "chrome" > /dev/null; then
        print_info "Closing Chrome gracefully..."
        pkill -TERM chrome 2>/dev/null || true
        sleep 3

        # Force kill if still running
        if pgrep -x "chrome" > /dev/null; then
            print_info "Force closing Chrome..."
            pkill -KILL chrome 2>/dev/null || true
            sleep 2
        fi

        print_success "Chrome processes terminated"
    else
        print_info "Chrome is not running"
    fi

    # Ask if user wants to start Chrome
    read -p "Start Chrome now? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if command -v google-chrome &> /dev/null; then
            google-chrome &> /dev/null &
            disown
            sleep 2
            print_success "Chrome started"
        elif command -v chromium &> /dev/null; then
            chromium &> /dev/null &
            disown
            sleep 2
            print_success "Chromium started"
        else
            print_warning "Chrome/Chromium command not found. Please start manually."
        fi
    fi
}

verify_https_interception() {
    print_header "Testing HTTPS Interception"

    # Check if mitmproxy is running
    if ! lsof -i :8080 &> /dev/null; then
        print_warning "No proxy detected on port 8080"
        print_info "Start TraceTap first: ./tracetap-linux-x64 --listen 8080"
        return 1
    fi

    print_info "Testing HTTPS connection through proxy..."

    # Test with curl
    if command -v curl &> /dev/null; then
        echo ""
        if curl -s -x http://localhost:8080 -k https://httpbin.org/get > /dev/null; then
            print_success "HTTPS interception working!"
            print_info "Certificate is trusted for command-line tools"
        else
            print_warning "HTTPS interception test failed"
            print_info "This is normal if certificate isn't installed system-wide"
        fi
    fi

    echo ""
    print_info "Manual browser test:"
    echo "  1. Configure FoxyProxy or browser proxy to use localhost:8080"
    echo "  2. Visit https://httpbin.org/get"
    echo "  3. You should NOT see certificate warnings"
    echo ""
}

###############################################################################
# Main Functions
###############################################################################

install_certificate() {
    print_header "Installing mitmproxy Certificate for Chrome"

    # Check prerequisites
    check_certutil
    check_certificate_file
    create_nss_db

    echo ""
    print_info "Installing certificate in Chrome (NSS database)..."

    # Remove old certificate if exists
    if certutil -L -d "$NSS_DB" -n "$CERT_NAME" &> /dev/null; then
        certutil -D -d "$NSS_DB" -n "$CERT_NAME"
        print_info "Removed existing certificate"
    fi

    # Install certificate
    certutil -A -d "$NSS_DB" -t "C,," -n "$CERT_NAME" -i "$CERT_PATH"
    print_success "Certificate installed in Chrome"

    # Optionally install system-wide
    echo ""
    read -p "Install system-wide (affects all browsers and CLI tools)? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing system-wide certificate..."
        sudo cp "$CERT_PATH" "$SYSTEM_CERT_PATH"
        sudo update-ca-certificates 2>/dev/null || sudo update-ca-trust 2>/dev/null || true
        print_success "System-wide certificate installed"
    fi

    # Install for Firefox if profile exists
    echo ""
    FIREFOX_PROFILES="$HOME/.mozilla/firefox"
    if [ -d "$FIREFOX_PROFILES" ]; then
        read -p "Install certificate for Firefox too? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for profile in "$FIREFOX_PROFILES"/*.default*; do
                if [ -d "$profile" ]; then
                    print_info "Installing for Firefox profile: $(basename $profile)"
                    certutil -A -d "sql:$profile" -t "C,," -n "$CERT_NAME" -i "$CERT_PATH" 2>/dev/null || true
                fi
            done
            print_success "Firefox certificate installed"
        fi
    fi

    # Verify installation
    echo ""
    print_info "Verifying installation..."
    if certutil -L -d "$NSS_DB" | grep -q "$CERT_NAME"; then
        print_success "Certificate verified in NSS database"

        # Show certificate details
        echo ""
        echo "Certificate details:"
        certutil -L -d "$NSS_DB" -n "$CERT_NAME" | head -10
    else
        print_error "Certificate not found in NSS database"
        exit 1
    fi

    print_header "Installation Complete!"

    echo "Next steps:"
    echo "  1. Restart Chrome:     ${GREEN}./$(basename $0) restart${NC}"
    echo "  2. Start TraceTap:     ${GREEN}./tracetap-linux-x64 --listen 8080 --export output.json${NC}"
    echo "  3. Configure FoxyProxy to use localhost:8080"
    echo "  4. Test installation:  ${GREEN}./$(basename $0) verify${NC}"
    echo ""

    read -p "Restart Chrome now? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        restart_chrome
    fi
}

remove_certificate() {
    print_header "Removing mitmproxy Certificate"

    check_certutil

    # Remove from Chrome (NSS database)
    echo ""
    print_info "Removing certificate from Chrome..."
    if certutil -L -d "$NSS_DB" -n "$CERT_NAME" &> /dev/null; then
        certutil -D -d "$NSS_DB" -n "$CERT_NAME"
        print_success "Certificate removed from Chrome"
    else
        print_warning "Certificate not found in Chrome"
    fi

    # Remove from Firefox
    FIREFOX_PROFILES="$HOME/.mozilla/firefox"
    if [ -d "$FIREFOX_PROFILES" ]; then
        echo ""
        read -p "Remove certificate from Firefox too? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for profile in "$FIREFOX_PROFILES"/*.default*; do
                if [ -d "$profile" ]; then
                    if certutil -L -d "sql:$profile" -n "$CERT_NAME" &> /dev/null; then
                        certutil -D -d "sql:$profile" -n "$CERT_NAME" 2>/dev/null || true
                        print_info "Removed from Firefox profile: $(basename $profile)"
                    fi
                fi
            done
            print_success "Firefox certificate removed"
        fi
    fi

    # Remove system-wide certificate
    if [ -f "$SYSTEM_CERT_PATH" ]; then
        echo ""
        read -p "Remove system-wide certificate? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing system-wide certificate..."
            sudo rm -f "$SYSTEM_CERT_PATH"
            sudo update-ca-certificates 2>/dev/null || sudo update-ca-trust 2>/dev/null || true
            print_success "System-wide certificate removed"
        fi
    fi

    # Verify removal
    echo ""
    print_info "Verifying removal..."
    if certutil -L -d "$NSS_DB" | grep -q "$CERT_NAME"; then
        print_error "Certificate still found in NSS database"
        exit 1
    else
        print_success "Certificate successfully removed"
    fi

    print_header "Removal Complete!"

    read -p "Restart Chrome now? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        restart_chrome
    fi
}

show_status() {
    print_header "Certificate Status"

    # Check if certutil is available
    if ! command -v certutil &> /dev/null; then
        print_warning "certutil not installed (libnss3-tools)"
        echo ""
    else
        print_success "certutil is installed"
    fi

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

    # Check NSS database
    echo ""
    if [ -d "$HOME/.pki/nssdb" ]; then
        print_success "NSS database exists"

        if command -v certutil &> /dev/null; then
            echo ""
            if certutil -L -d "$NSS_DB" -n "$CERT_NAME" &> /dev/null; then
                print_success "Certificate installed in Chrome"
                echo ""
                echo "Chrome certificate status:"
                certutil -L -d "$NSS_DB" | grep "$CERT_NAME" || true
            else
                print_error "Certificate NOT installed in Chrome"
            fi
        fi
    else
        print_error "NSS database not found"
    fi

    # Check Firefox
    echo ""
    FIREFOX_PROFILES="$HOME/.mozilla/firefox"
    if [ -d "$FIREFOX_PROFILES" ]; then
        firefox_installed=false
        for profile in "$FIREFOX_PROFILES"/*.default*; do
            if [ -d "$profile" ] && command -v certutil &> /dev/null; then
                if certutil -L -d "sql:$profile" -n "$CERT_NAME" &> /dev/null 2>&1; then
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
    fi

    # Check system-wide installation
    echo ""
    if [ -f "$SYSTEM_CERT_PATH" ]; then
        print_success "System-wide certificate installed"
    else
        print_info "System-wide certificate not installed"
    fi

    # Check if proxy is running
    echo ""
    if lsof -i :8080 &> /dev/null 2>&1; then
        print_success "Proxy detected on port 8080"
    else
        print_info "No proxy running on port 8080"
    fi

    # Check if Chrome is running
    echo ""
    if pgrep -x "chrome" > /dev/null; then
        print_info "Chrome is currently running"
    else
        print_info "Chrome is not running"
    fi

    echo ""
}

show_usage() {
    cat << EOF
Usage: $(basename $0) [COMMAND]

Commands:
    install     Install mitmproxy certificate for Chrome
    remove      Remove mitmproxy certificate from Chrome
    status      Show certificate installation status
    restart     Restart Chrome browser
    verify      Test HTTPS interception
    help        Show this help message

Examples:
    # First-time setup
    ./$(basename $0) install
    ./$(basename $0) verify

    # Check if certificate is installed
    ./$(basename $0) status

    # Remove certificate
    ./$(basename $0) remove

    # Restart Chrome after installing
    ./$(basename $0) restart

Notes:
    - Requires libnss3-tools (installs automatically on Debian/Ubuntu)
    - Chrome must be restarted after installing/removing certificate
    - Certificate file: $CERT_PATH
    - NSS database: $NSS_DB
    - Also supports Firefox certificate installation

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
    restart)
        restart_chrome
        ;;
    verify)
        verify_https_interception
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