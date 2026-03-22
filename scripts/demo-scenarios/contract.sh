#!/bin/bash
# Demo: Contract Testing
# Duration: 40 seconds
# Description: Contract verification workflow

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Typing speed
CHAR_DELAY=0.025

# Pause durations
SHORT_PAUSE=0.3
NORMAL_PAUSE=0.9
LONG_PAUSE=1.3

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

printf "${CYAN}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                Contract Testing Demo                           ║
║        API Consumer-Provider Contract Verification             ║
╚════════════════════════════════════════════════════════════════╝
EOF
printf "${NC}\n"
sleep 1.0

# Section 1: Show contract file
print_header "Step 1: View API Contract"

type_command "cat contracts/user_api.yaml"
sleep 0.4
cat << 'EOF'
consumers:
  - web_client
  - mobile_app

interactions:
  - description: Get user by ID
    request:
      method: GET
      path: /api/users/{id}
      headers:
        Accept: application/json
    response:
      status: 200
      headers:
        Content-Type: application/json
      body:
        type: object
        required: [id, name, email]
        properties:
          id: { type: integer }
          name: { type: string }
          email: { type: string }

  - description: Create user
    request:
      method: POST
      path: /api/users
      body:
        required: [name, email]
    response:
      status: 201
EOF
sleep "$LONG_PAUSE"

# Section 2: Run contract verification
print_header "Step 2: Verify Against Contract"

type_command "tracetap verify-contracts --spec contracts/user_api.yaml"
sleep 0.5
cat << 'EOF'
[INFO] Loading contract specification...
[INFO] Found 2 interactions to verify
[INFO] Testing against live API...
EOF
sleep "$NORMAL_PAUSE"

# Section 3: Show verification results
print_header "Step 3: Verification Results"

sleep 0.3
printf "${CYAN}"
cat << 'EOF'
CONTRACT VERIFICATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

${GREEN}✓ Get user by ID${NC}
  Status: 200 ✓
  Response headers: ✓
  Required fields present: ✓
  Field types match: ✓

${GREEN}✓ Create user${NC}
  Status: 201 ✓
  Response headers: ✓
  Required fields in request: ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Verification Summary:
  ${GREEN}2 contracts verified${NC}
  ${GREEN}2 passed${NC}
  ${RED}0 failed${NC}

Result: ${GREEN}SUCCESS${NC}
EOF
printf "${NC}"
sleep "$LONG_PAUSE"

# Section 4: Check consumer compatibility
print_header "Step 4: Consumer Compatibility"

type_command "tracetap check-compatibility contracts/user_api.yaml"
sleep 0.4
cat << 'EOF'
[INFO] Checking consumer compatibility...
[INFO] Analyzing web_client...
[INFO] Analyzing mobile_app...
EOF
sleep "$NORMAL_PAUSE"

# Show compatibility matrix
printf "${CYAN}"
cat << 'EOF'
CONSUMER COMPATIBILITY MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

              │ Interaction 1 │ Interaction 2 │ Status
──────────────┼───────────────┼───────────────┼────────
web_client    │       ✓       │       ✓       │ READY
mobile_app    │       ✓       │       ✓       │ READY

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All consumers compatible with API version 2.1
EOF
printf "${NC}"
sleep "$LONG_PAUSE"

# Section 5: Generate compatibility report
print_header "Step 5: Generate Report"

type_command "tracetap report --type contract --output contract_report.json"
sleep 0.4
cat << 'EOF'
[INFO] Generating contract report...
[INFO] Saving to contract_report.json...
[INFO] Report complete
EOF
sleep "$NORMAL_PAUSE"

# Final summary
print_header "Summary"

printf "${GREEN}✓${NC} Contract verification passed\n"
sleep 0.3
printf "${GREEN}✓${NC} All consumers compatible\n"
sleep 0.3
printf "${GREEN}✓${NC} API is safe to deploy\n"
sleep 0.3

printf "\n${YELLOW}Key Metrics:${NC}\n"
printf "• 2 interactions verified\n"
printf "• 2 consumers satisfied\n"
printf "• 0 breaking changes detected\n"
printf "• Safe for production deployment\n"

sleep 1.3
