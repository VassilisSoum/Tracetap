#!/bin/bash

################################################################################
# Demo Recording Script for TraceTap
#
# This script automates the capture and optimization of demo GIFs for
# TraceTap documentation.
#
# Usage:
#   ./scripts/record-demos.sh --all                  # Record all demos
#   ./scripts/record-demos.sh --demo quickstart      # Record specific demo
#   ./scripts/record-demos.sh --check-tools          # Verify dependencies
#   ./scripts/record-demos.sh --help                 # Show this help
#
# Demos Available:
#   - quickstart      Install → capture → generate tests (60s)
#   - regression      Snapshot regression generation (30s)
#   - ai-suggestions  AI test suggestions workflow (45s)
#   - contract        Contract verification (40s)
#   - report          HTML report generation and viewing (30s)
#
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEMOS_DIR="$SCRIPT_DIR/demo-scenarios"
OUTPUT_DIR="$PROJECT_ROOT/assets/demo-gifs"
SCREENSHOTS_DIR="$PROJECT_ROOT/assets/screenshots"
TEMP_DIR="/tmp/tracetap-recording-$$"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
RECORD_ALL=false
DEMO_NAME=""
CHECK_TOOLS=false
SHOW_HELP=false
OPTIMIZE=false
OPTIMIZE_MORE=false
RECORD=false
SKIP_OPTIMIZATION=false

# Recording settings
TERMINAL_WIDTH=120
TERMINAL_HEIGHT=30
DELAY_BETWEEN_CHARS=0.02
PAUSE_AFTER_COMMAND=0.5

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

show_help() {
    cat << 'EOF'
Demo Recording Script for TraceTap

USAGE:
    ./scripts/record-demos.sh [OPTIONS]

OPTIONS:
    --all                   Record all demo scenarios
    --demo <name>           Record specific demo (quickstart|regression|ai-suggestions|contract|report)
    --check-tools           Verify all required tools are installed
    --record                Start recording (used internally)
    --optimize              Optimize GIF file size
    --optimize-more         More aggressive optimization (quality trade-off)
    --skip-optimization     Don't optimize GIF file
    --help                  Show this help message

EXAMPLES:
    # Record all demos
    ./scripts/record-demos.sh --all

    # Record specific demo
    ./scripts/record-demos.sh --demo quickstart

    # Check if all tools are available
    ./scripts/record-demos.sh --check-tools

    # Record with custom settings
    ./scripts/record-demos.sh --demo regression --optimize

DEMOS:
    quickstart          60s  Install → capture → generate tests
    regression          30s  Snapshot regression generation
    ai-suggestions      45s  AI test suggestions workflow
    contract            40s  Contract verification
    report              30s  HTML report generation and viewing

REQUIREMENTS:
    - asciinema (terminal recording)
    - agg (asciinema to GIF conversion)
    - ImageMagick (convert command for optimization)

INSTALL TOOLS:
    macOS:
        brew install asciinema agg imagemagick

    Linux:
        sudo apt-get install asciinema imagemagick
        # For agg: cargo install agg

OUTPUT:
    GIFs are saved to: assets/demo-gifs/
    Each demo target size: < 5MB

For more details, see: docs/recording-guide.md
EOF
}

################################################################################
# Tool Checking Functions
################################################################################

check_tool() {
    local tool=$1
    if command -v "$tool" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $tool"
        return 0
    else
        echo -e "${RED}✗${NC} $tool (not found)"
        return 1
    fi
}

check_tools() {
    log_info "Checking required tools..."
    echo ""

    local all_found=true

    echo "Core tools:"
    check_tool "asciinema" || all_found=false
    check_tool "agg" || all_found=false
    check_tool "convert" || all_found=false

    echo ""
    echo "Optional tools:"
    check_tool "gifski" || true
    check_tool "scrot" || true
    check_tool "maim" || true

    echo ""

    if [ "$all_found" = true ]; then
        log_success "All required tools are installed!"
        return 0
    else
        log_error "Some required tools are missing."
        echo ""
        echo "Install on macOS:"
        echo "  brew install asciinema agg imagemagick"
        echo ""
        echo "Install on Linux:"
        echo "  sudo apt-get install asciinema imagemagick"
        echo "  cargo install agg  # requires Rust"
        return 1
    fi
}

################################################################################
# Directory Setup
################################################################################

setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$SCREENSHOTS_DIR"
    mkdir -p "$TEMP_DIR"

    log_success "Directories ready"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

################################################################################
# Recording Functions
################################################################################

record_demo() {
    local demo_name=$1
    local demo_script="$DEMOS_DIR/${demo_name}.sh"

    if [ ! -f "$demo_script" ]; then
        log_error "Demo script not found: $demo_script"
        return 1
    fi

    log_info "Recording demo: $demo_name"

    local cast_file="$TEMP_DIR/${demo_name}.cast"
    local gif_file="$OUTPUT_DIR/${demo_name}.gif"

    # Set up recording environment
    export TERM=xterm-256color
    export ASCIINEMA_REC="$cast_file"

    # Record the demo
    log_info "Recording terminal session..."
    if asciinema rec "$cast_file" < <(bash "$demo_script" 2>&1); then
        log_success "Recording completed: $cast_file"
    else
        log_error "Recording failed for demo: $demo_name"
        return 1
    fi

    # Convert to GIF
    convert_to_gif "$cast_file" "$gif_file"

    # Optimize GIF
    if [ "$SKIP_OPTIMIZATION" = false ]; then
        optimize_gif "$gif_file"
    fi

    # Show final stats
    if [ -f "$gif_file" ]; then
        local size=$(du -h "$gif_file" | cut -f1)
        log_success "Demo recorded: $gif_file ($size)"
        return 0
    else
        log_error "GIF creation failed for demo: $demo_name"
        return 1
    fi
}

convert_to_gif() {
    local cast_file=$1
    local gif_file=$2

    log_info "Converting to GIF: $(basename "$gif_file")"

    if agg "$cast_file" "$gif_file" --theme solarized-dark --speed 1.0; then
        log_success "GIF created successfully"
        return 0
    else
        log_error "GIF conversion failed"
        return 1
    fi
}

optimize_gif() {
    local gif_file=$1
    local temp_gif="${gif_file}.tmp"

    log_info "Optimizing GIF: $(basename "$gif_file")"

    # Color reduction + frame optimization + resize
    if convert "$gif_file" \
        -colors 128 \
        -fuzz 10% \
        -coalesce -deconstruct -layers OptimizeFrame \
        -resize 1200x \
        -strip \
        "$temp_gif"; then

        # Check if optimization reduced file size
        local original_size=$(stat -f%z "$gif_file" 2>/dev/null || stat -c%s "$gif_file" 2>/dev/null)
        local optimized_size=$(stat -f%z "$temp_gif" 2>/dev/null || stat -c%s "$temp_gif" 2>/dev/null)

        if [ "$optimized_size" -lt "$original_size" ]; then
            mv "$temp_gif" "$gif_file"
            log_success "Optimized successfully"
        else
            rm "$temp_gif"
            log_warning "Optimization didn't reduce size, keeping original"
        fi
    else
        log_error "GIF optimization failed"
        rm -f "$temp_gif"
        return 1
    fi
}

optimize_gif_more() {
    local gif_file=$1
    local temp_gif="${gif_file}.tmp"

    log_info "Applying aggressive optimization: $(basename "$gif_file")"

    # More aggressive: fewer colors + higher fuzz + scaling down
    if convert "$gif_file" \
        -colors 96 \
        -fuzz 15% \
        -coalesce -deconstruct -layers OptimizeFrame \
        -resize 960x \
        -strip \
        "$temp_gif"; then

        mv "$temp_gif" "$gif_file"
        log_success "Aggressive optimization applied"
    else
        log_error "Aggressive optimization failed"
        rm -f "$temp_gif"
        return 1
    fi
}

################################################################################
# Demo Scenario Functions
################################################################################

get_demo_list() {
    echo "quickstart regression ai-suggestions contract report"
}

validate_demo_name() {
    local demo=$1
    local valid_demos=$(get_demo_list)

    for valid_demo in $valid_demos; do
        if [ "$demo" = "$valid_demo" ]; then
            return 0
        fi
    done

    log_error "Unknown demo: $demo"
    echo ""
    echo "Available demos:"
    for demo in $valid_demos; do
        echo "  - $demo"
    done
    return 1
}

record_all_demos() {
    log_info "Recording all demos..."
    echo ""

    local demos=$(get_demo_list)
    local total=$(echo "$demos" | wc -w)
    local current=1

    for demo in $demos; do
        echo ""
        log_info "[$current/$total] Recording $demo..."

        if record_demo "$demo"; then
            log_success "[$current/$total] $demo completed"
        else
            log_warning "[$current/$total] $demo failed, continuing..."
        fi

        ((current++))
    done

    echo ""
    log_success "All demos recorded!"
    echo ""
    echo "Output directory: $OUTPUT_DIR"
    echo "Generated files:"
    ls -lh "$OUTPUT_DIR"/*.gif 2>/dev/null || true
}

################################################################################
# Statistics
################################################################################

show_statistics() {
    echo ""
    log_info "Recording Statistics"
    echo ""

    if [ ! -d "$OUTPUT_DIR" ]; then
        log_warning "No demos recorded yet"
        return
    fi

    local total_size=0
    local file_count=0

    echo "Generated GIFs:"
    for gif_file in "$OUTPUT_DIR"/*.gif; do
        if [ -f "$gif_file" ]; then
            local size=$(stat -f%z "$gif_file" 2>/dev/null || stat -c%s "$gif_file" 2>/dev/null)
            local size_mb=$((size / 1024 / 1024))
            local basename=$(basename "$gif_file")

            printf "  %-25s %5d MB\n" "$basename" "$size_mb"

            total_size=$((total_size + size))
            ((file_count++))
        fi
    done

    if [ "$file_count" -gt 0 ]; then
        echo ""
        local total_mb=$((total_size / 1024 / 1024))
        printf "Total: %d files, %d MB\n" "$file_count" "$total_mb"
    fi
}

################################################################################
# Demo Scenario Headers
################################################################################

demo_header() {
    local demo_name=$1
    local duration=$2
    local description=$3

    echo "#!/bin/bash"
    echo "# Demo: $demo_name"
    echo "# Duration: $duration seconds"
    echo "# Description: $description"
    echo ""
    echo "# Terminal size: ${TERMINAL_WIDTH}x${TERMINAL_HEIGHT}"
    echo "# This script is sourced by record-demos.sh"
    echo ""
}

################################################################################
# Main Entry Point
################################################################################

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                RECORD_ALL=true
                shift
                ;;
            --demo)
                DEMO_NAME="$2"
                shift 2
                ;;
            --check-tools)
                CHECK_TOOLS=true
                shift
                ;;
            --help)
                SHOW_HELP=true
                shift
                ;;
            --record)
                RECORD=true
                shift
                ;;
            --optimize)
                OPTIMIZE=true
                shift
                ;;
            --optimize-more)
                OPTIMIZE_MORE=true
                shift
                ;;
            --skip-optimization)
                SKIP_OPTIMIZATION=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Show help if requested or no arguments
    if [ "$SHOW_HELP" = true ] || ([ "$RECORD_ALL" = false ] && [ -z "$DEMO_NAME" ] && [ "$CHECK_TOOLS" = false ]); then
        show_help
        exit 0
    fi

    # Check tools
    if [ "$CHECK_TOOLS" = true ]; then
        if check_tools; then
            exit 0
        else
            exit 1
        fi
    fi

    # Verify tools are available
    if ! command -v asciinema &> /dev/null || ! command -v agg &> /dev/null; then
        log_error "Required tools not found (asciinema, agg)"
        echo ""
        show_help
        exit 1
    fi

    # Set up directories
    setup_directories

    # Handle optimization flags
    if [ "$OPTIMIZE_MORE" = true ]; then
        # Apply aggressive optimization to existing GIFs
        if [ -n "$DEMO_NAME" ]; then
            local gif_file="$OUTPUT_DIR/${DEMO_NAME}.gif"
            if [ -f "$gif_file" ]; then
                optimize_gif_more "$gif_file"
                show_statistics
                exit 0
            else
                log_error "GIF not found: $gif_file"
                exit 1
            fi
        else
            # Apply to all GIFs
            for gif_file in "$OUTPUT_DIR"/*.gif; do
                if [ -f "$gif_file" ]; then
                    optimize_gif_more "$gif_file"
                fi
            done
            show_statistics
            exit 0
        fi
    fi

    # Record demos
    if [ "$RECORD_ALL" = true ]; then
        record_all_demos
    elif [ -n "$DEMO_NAME" ]; then
        if validate_demo_name "$DEMO_NAME"; then
            record_demo "$DEMO_NAME"
        else
            exit 1
        fi
    fi

    # Show statistics
    show_statistics
}

# Run main function
main "$@"
