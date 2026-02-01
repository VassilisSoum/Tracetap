#!/bin/bash
# Demo: Regression
# Duration: 30 seconds
# Description: Snapshot regression generation and comparison

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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
    sleep "$SHORT_PAUSE"
}

print_header() {
    local text="$1"
    printf "\n${GREEN}=== $text ===${NC}\n\n"
    sleep "$NORMAL_PAUSE"
}

# Start
clear
sleep 0.5

printf "${GREEN}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                   Regression Testing Demo                      ║
║              Response Snapshot Verification                    ║
╚════════════════════════════════════════════════════════════════╝
EOF
printf "${NC}\n"
sleep 1.0

# Section 1: Show existing snapshots
print_header "Step 1: Existing API Snapshots"

type_command "ls -lh snapshots/"
sleep 0.3
cat << 'EOF'
total 24K
-rw-r--r--  1 user staff  1.2K Jan 15 10:23 users_list.json
-rw-r--r--  1 user staff  0.8K Jan 15 10:23 user_detail.json
-rw-r--r--  1 user staff  1.5K Jan 15 10:23 posts_list.json
EOF
sleep "$LONG_PAUSE"

# Section 2: Run test with regression check
print_header "Step 2: Run Regression Tests"

type_command "pytest tests/ --regression"
sleep 0.5
cat << 'EOF'
collected 3 items

tests/test_users.py::test_list_users PASSED
tests/test_users.py::test_get_user FAILED
tests/test_posts.py::test_list_posts PASSED

FAILURES:
______________________ test_get_user _______________________________

Response mismatch detected!

Expected (snapshot):
{
  "id": 1,
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "status": "active"
}

Got (current):
{
  "id": 1,
  "name": "Alice J. Johnson",
  "email": "alice@example.com",
  "status": "active",
  "last_updated": "2024-02-01T10:30:00Z"
}

Differences:
  - name: changed
  - added: last_updated
EOF
sleep "$LONG_PAUSE"

# Section 3: Show diff details
print_header "Step 3: Detailed Comparison"

type_command "tracetap diff snapshots/user_detail.json current.json"
sleep 0.4
cat << 'EOF'
[INFO] Comparing snapshots...

${RED}Differences found:${NC}
  line 2:  - "name": "Alice Johnson",
  line 2:  + "name": "Alice J. Johnson",
  line 5:  + "last_updated": "2024-02-01T10:30:00Z"

${YELLOW}Severity:${NC} Minor
${YELLOW}Type:${NC} Response schema change
EOF
sleep "$LONG_PAUSE"

# Section 4: Generate HTML report
print_header "Step 4: Generate Regression Report"

type_command "tracetap report --format html --output regression_report.html"
sleep 0.4
cat << 'EOF'
[INFO] Generating regression report...
[INFO] Comparing 3 snapshots...
[INFO] Found 1 mismatch
[INFO] Analyzing differences...
[INFO] Report saved: regression_report.html
EOF
sleep "$NORMAL_PAUSE"

type_command "open regression_report.html"
sleep 0.3
printf "${YELLOW}Opening HTML report in browser...${NC}\n"
sleep "$LONG_PAUSE"

# Final summary
print_header "Summary"

printf "${RED}✗${NC} 1 regression detected (user_detail)\n"
sleep 0.3
printf "${GREEN}✓${NC} 2 tests passed\n"
sleep 0.3
printf "${YELLOW}→${NC} Review HTML report for details\n"
sleep 0.3

printf "\n${YELLOW}Next steps:${NC}\n"
printf "1. Review changes in regression_report.html\n"
printf "2. Update snapshots if changes are valid\n"
printf "3. Re-run tests to verify\n"

sleep 1.5
