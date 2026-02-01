#!/bin/bash
# Demo: HTML Report
# Duration: 30 seconds
# Description: HTML report generation and viewing

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
ORANGE='\033[0;33m'
NC='\033[0m'

# Typing speed
CHAR_DELAY=0.03

# Pause durations
SHORT_PAUSE=0.4
NORMAL_PAUSE=1.0
LONG_PAUSE=1.5

type_command() {
    local cmd="$1"
    local delay="${2:-$CHAR_DELAY}"

    printf "${BLUE}$ ${NC}"
    for ((i=0; i<${#cmd}; i++)); do
        printf "%s" "${cmd:$i:1}"
        sleep "$delay"
    done
    printf "\n"
    sleep "$SHORT_PAUSE"
}

type_output() {
    local output="$1"
    printf "%s\n" "$output"
}

print_header() {
    local text="$1"
    printf "\n${GREEN}=== $text ===${NC}\n\n"
    sleep "$NORMAL_PAUSE"
}

# Start
clear
sleep 0.5

printf "${ORANGE}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║              HTML Report Generation Demo                       ║
║           Comprehensive Test Results Visualization             ║
╚════════════════════════════════════════════════════════════════╝
EOF
printf "${NC}\n"
sleep 1.0

# Section 1: Run tests
print_header "Step 1: Run Test Suite"

type_command "pytest tests/ -v --tb=short"
sleep 0.5
cat << 'EOF'
collected 8 items

tests/test_users.py::test_list_users PASSED              [12%]
tests/test_users.py::test_get_user PASSED               [25%]
tests/test_users.py::test_create_user PASSED            [37%]
tests/test_posts.py::test_list_posts PASSED             [50%]
tests/test_posts.py::test_create_post PASSED            [62%]
tests/test_auth.py::test_login PASSED                   [75%]
tests/test_auth.py::test_logout PASSED                  [87%]
tests/test_auth.py::test_token_refresh PASSED           [100%]

═════════════════════ 8 passed in 2.34s ═════════════════════
EOF
sleep "$LONG_PAUSE"

# Section 2: Generate HTML report
print_header "Step 2: Generate HTML Report"

type_command "tracetap report tests/ --format html --output report.html"
sleep 0.4
cat << 'EOF'
[INFO] Analyzing test results...
[INFO] Generating coverage metrics...
[INFO] Creating HTML report...
[INFO] Optimizing assets...
[INFO] Report saved: report.html (156KB)
EOF
sleep "$NORMAL_PAUSE"

# Section 3: Show report stats
print_header "Step 3: Report Summary"

sleep 0.3
cat << 'EOF'
Report Statistics:
  • Tests run: 8
  • Passed: 8 (100%)
  • Failed: 0
  • Skipped: 0
  • Duration: 2.34s
  • Coverage: 87%

Modules:
  • test_users.py:     3/3 passed ✓
  • test_posts.py:     2/2 passed ✓
  • test_auth.py:      3/3 passed ✓
EOF
sleep "$LONG_PAUSE"

# Section 4: List generated files
print_header "Step 4: Generated Files"

type_command "ls -lh report.html report_assets/"
sleep 0.3
cat << 'EOF'
-rw-r--r--  1 user staff  156K Feb  1 22:45 report.html
drwxr-xr-x  3 user staff   96B Feb  1 22:45 report_assets/
  -rw-r--r--  1 user staff   45K   style.css
  -rw-r--r--  1 user staff   32K   charts.js
  -rw-r--r--  1 user staff   12K   theme.css
EOF
sleep "$LONG_PAUSE"

# Section 5: Open report
print_header "Step 5: Open Report in Browser"

type_command "open report.html"
sleep 0.5
cat << 'EOF'
[INFO] Opening report in default browser...
[Browser opens with report]

Test Results Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  8 Tests Passed (100%)
  ┌─────────────────────────────────┐
  │ ███████████████████████░░░░░░ │  (100%)
  └─────────────────────────────────┘

Test Execution Timeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_users.py        ▓▓▓ 450ms
test_posts.py        ▓▓   320ms
test_auth.py         ▓▓▓  570ms
                     └──────────────────────────────────────

Coverage Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
users.py        ██████████ 94%
posts.py        █████████░  87%
auth.py         ███████████ 100%
Overall:        ██████████░ 87%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
sleep 1.5

# Section 6: Show report features
print_header "Step 6: Report Features"

printf "${YELLOW}Available in HTML Report:${NC}\n"
sleep 0.3
printf "✓ Test execution timeline\n"
sleep 0.2
printf "✓ Coverage heatmap\n"
sleep 0.2
printf "✓ Performance metrics\n"
sleep 0.2
printf "✓ Failure details\n"
sleep 0.2
printf "✓ Interactive charts\n"
sleep 0.2
printf "✓ Trend analysis\n"

sleep "$LONG_PAUSE"

# Final summary
print_header "Summary"

printf "${GREEN}✓${NC} All 8 tests passed\n"
sleep 0.3
printf "${GREEN}✓${NC} Coverage: 87%\n"
sleep 0.3
printf "${GREEN}✓${NC} HTML report generated\n"
sleep 0.3
printf "${GREEN}✓${NC} Ready for sharing\n"

sleep 1.5
