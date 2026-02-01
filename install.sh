#!/usr/bin/env bash
#
# TraceTap One-Line Installer
# Usage: curl -sSL https://get.tracetap.io | bash
#
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Banner
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║        TraceTap Installer - From Traffic to Tests        ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Detect OS
info "Detecting operating system..."
OS=""
case "$(uname -s)" in
    Linux*)     OS="Linux";;
    Darwin*)    OS="macOS";;
    CYGWIN*)    OS="Windows";;
    MINGW*)     OS="Windows";;
    MSYS*)      OS="Windows";;
    *)          OS="UNKNOWN";;
esac

if [ "$OS" = "UNKNOWN" ]; then
    error "Unsupported operating system: $(uname -s)"
    exit 1
fi

success "Detected: $OS"

# Check for Python
info "Checking for Python installation..."
PYTHON_CMD=""

# Try different Python commands
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        # Check Python version
        VERSION=$($cmd -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)

        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
            PYTHON_CMD=$cmd
            success "Found Python $VERSION at $(which $cmd)"
            break
        else
            warn "Found Python $VERSION, but TraceTap requires Python 3.8+"
        fi
    fi
done

# Install Python if not found
if [ -z "$PYTHON_CMD" ]; then
    warn "Python 3.8+ not found. Installing..."

    if [ "$OS" = "Linux" ]; then
        # Detect Linux distribution
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            case $ID in
                ubuntu|debian)
                    info "Installing Python via apt..."
                    sudo apt-get update -qq
                    sudo apt-get install -y python3 python3-pip python3-venv
                    PYTHON_CMD=python3
                    ;;
                fedora|rhel|centos)
                    info "Installing Python via dnf/yum..."
                    if command -v dnf &> /dev/null; then
                        sudo dnf install -y python3 python3-pip
                    else
                        sudo yum install -y python3 python3-pip
                    fi
                    PYTHON_CMD=python3
                    ;;
                arch)
                    info "Installing Python via pacman..."
                    sudo pacman -Sy --noconfirm python python-pip
                    PYTHON_CMD=python3
                    ;;
                *)
                    error "Unsupported Linux distribution: $ID"
                    error "Please install Python 3.8+ manually and re-run this script"
                    exit 1
                    ;;
            esac
        else
            error "Cannot detect Linux distribution"
            error "Please install Python 3.8+ manually and re-run this script"
            exit 1
        fi
    elif [ "$OS" = "macOS" ]; then
        if command -v brew &> /dev/null; then
            info "Installing Python via Homebrew..."
            brew install python@3.11
            PYTHON_CMD=python3
        else
            error "Homebrew not found"
            error "Please install Python 3.8+ manually from https://python.org"
            error "Or install Homebrew first: https://brew.sh"
            exit 1
        fi
    elif [ "$OS" = "Windows" ]; then
        error "Python not found on Windows"
        error "Please install Python 3.8+ from https://python.org"
        error "Make sure to check 'Add Python to PATH' during installation"
        exit 1
    fi

    success "Python installed successfully"
fi

# Verify pip is available
info "Checking for pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    warn "pip not found, installing..."
    $PYTHON_CMD -m ensurepip --upgrade
fi
success "pip is available"

# Install TraceTap
info "Installing TraceTap..."
echo ""

# Use pip install with user flag to avoid permission issues
if $PYTHON_CMD -m pip install --user --upgrade tracetap; then
    success "TraceTap installed successfully!"
else
    error "Failed to install TraceTap"
    error "Please check the error messages above and try again"
    exit 1
fi

echo ""

# Verify installation
info "Verifying installation..."

# Check if tracetap command is available
if command -v tracetap &> /dev/null; then
    VERSION=$(tracetap --version 2>/dev/null || echo "unknown")
    success "TraceTap is installed and ready to use!"
    info "Version: $VERSION"
else
    warn "TraceTap installed but not found in PATH"

    # Try to find the installation location
    USER_BASE=$($PYTHON_CMD -m site --user-base)
    BIN_DIR="$USER_BASE/bin"

    if [ -f "$BIN_DIR/tracetap" ]; then
        warn "TraceTap is installed at: $BIN_DIR/tracetap"
        warn ""
        warn "Please add the following to your shell configuration file:"
        warn "  export PATH=\"\$PATH:$BIN_DIR\""
        warn ""

        if [ "$OS" = "macOS" ] || [ "$OS" = "Linux" ]; then
            # Detect shell
            SHELL_NAME=$(basename "$SHELL")
            case $SHELL_NAME in
                bash)
                    CONFIG_FILE="$HOME/.bashrc"
                    ;;
                zsh)
                    CONFIG_FILE="$HOME/.zshrc"
                    ;;
                fish)
                    CONFIG_FILE="$HOME/.config/fish/config.fish"
                    ;;
                *)
                    CONFIG_FILE="$HOME/.profile"
                    ;;
            esac

            warn "For your shell ($SHELL_NAME), add it to: $CONFIG_FILE"
            warn ""
            read -p "Would you like me to add it automatically? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "" >> "$CONFIG_FILE"
                echo "# TraceTap PATH" >> "$CONFIG_FILE"
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$CONFIG_FILE"
                success "Added to $CONFIG_FILE"
                warn "Please restart your shell or run: source $CONFIG_FILE"
            fi
        fi
    else
        error "Cannot locate TraceTap installation"
        error "Please try installing manually: $PYTHON_CMD -m pip install tracetap"
        exit 1
    fi
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║               🎉 Installation Complete! 🎉               ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
info "Get started with: ${GREEN}tracetap quickstart${NC}"
info "Or view help with:  ${GREEN}tracetap --help${NC}"
echo ""
info "Documentation: https://github.com/VassilisSoum/tracetap#readme"
info "Report issues:  https://github.com/VassilisSoum/tracetap/issues"
echo ""
success "Happy testing! 🚀"
echo ""
