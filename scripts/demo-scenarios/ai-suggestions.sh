#!/bin/bash
# Demo: AI Suggestions
# Duration: 45 seconds
# Description: AI-powered test improvement suggestions workflow

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Typing speed
CHAR_DELAY=0.025

# Pause durations
SHORT_PAUSE=0.3
NORMAL_PAUSE=0.8
LONG_PAUSE=1.2

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

printf "${MAGENTA}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                  AI Test Suggestions Demo                      ║
║              Intelligent Test Quality Improvements             ║
╚════════════════════════════════════════════════════════════════╝
EOF
printf "${NC}\n"
sleep 0.8

# Section 1: Show test file
print_header "Step 1: View Test File"

type_command "cat tests/test_api.py"
sleep 0.3
cat << 'EOF'
import requests

def test_get_user():
    response = requests.get("http://api.example.com/user/1")
    assert response.status_code == 200
    assert "name" in response.json()

def test_create_user():
    response = requests.post("http://api.example.com/user", json={
        "name": "John"
    })
    assert response.status_code == 201

def test_error_handling():
    response = requests.get("http://api.example.com/user/999")
    assert response.status_code == 404
EOF
sleep "$LONG_PAUSE"

# Section 2: Run AI analysis
print_header "Step 2: Run AI Analysis"

type_command "tracetap analyze tests/test_api.py --ai"
sleep 0.5
cat << 'EOF'
[INFO] Analyzing test file with AI...
[INFO] Sending to Claude Sonnet 4.5...
[INFO] Processing recommendations...
EOF
sleep "$NORMAL_PAUSE"

# Section 3: Show AI suggestions
print_header "Step 3: AI Suggestions Received"

sleep 0.3
printf "${CYAN}"
cat << 'EOF'
AI ANALYSIS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Test Quality Score: 62/100

🔍 FINDINGS:

1. Missing Response Structure Validation (HIGH)
   └─ Tests don't validate full JSON structure
   └─ Recommendation: Add jsonschema validation
   └─ Expected improvement: +15 points

2. No Error Message Validation (MEDIUM)
   └─ Error responses not checked for helpful messages
   └─ Recommendation: Validate error details
   └─ Expected improvement: +8 points

3. Hardcoded URLs (MEDIUM)
   └─ Should use environment variables
   └─ Recommendation: Use fixtures with BaseURL
   └─ Expected improvement: +10 points

4. Missing Edge Cases (MEDIUM)
   └─ No tests for empty responses, timeouts, retries
   └─ Expected improvement: +12 points

5. No Request/Response Logging (LOW)
   └─ Difficult to debug failures
   └─ Recommendation: Add fixture with request logging
   └─ Expected improvement: +5 points

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
printf "${NC}"
sleep "$LONG_PAUSE"

# Section 4: Show generated improvements
print_header "Step 4: Generated Improvements"

type_command "tracetap suggest tests/test_api.py --apply"
sleep 0.4
cat << 'EOF'
[INFO] Generating improved test file...
[INFO] Adding jsonschema validation...
[INFO] Adding error message checks...
[INFO] Converting to fixtures...
[INFO] Added 12 new assertions
[INFO] Created: tests/test_api_improved.py
EOF
sleep "$NORMAL_PAUSE"

# Section 5: Show improved code
print_header "Step 5: View Improvements"

type_command "diff -u tests/test_api.py tests/test_api_improved.py | head -40"
sleep 0.3
cat << 'EOF'
+import requests
+from jsonschema import validate
+import pytest
+
+BASE_URL = "http://api.example.com"
+USER_SCHEMA = {
+    "type": "object",
+    "required": ["id", "name", "email"]
+}
+
+@pytest.fixture
+def api_client():
+    return requests.Session()
+
-def test_get_user():
-    response = requests.get("http://api.example.com/user/1")
+def test_get_user(api_client):
+    response = api_client.get(f"{BASE_URL}/user/1")
     assert response.status_code == 200
+    data = response.json()
+    validate(instance=data, schema=USER_SCHEMA)
+    assert data["id"] == 1
EOF
sleep "$LONG_PAUSE"

# Section 6: Run improved tests
print_header "Step 6: Run Improved Tests"

type_command "pytest tests/test_api_improved.py -v"
sleep 0.4
cat << 'EOF'
collected 3 items

tests/test_api_improved.py::test_get_user PASSED        [33%]
tests/test_api_improved.py::test_create_user PASSED     [66%]
tests/test_api_improved.py::test_error_handling PASSED  [100%]

═════════════════════ 3 passed in 0.45s ═════════════════════
EOF
sleep "$NORMAL_PAUSE"

# Final summary
print_header "Summary"

printf "${MAGENTA}New Quality Score: 89/100${NC}\n"
sleep 0.3
printf "${GREEN}✓${NC} All 3 tests passing\n"
sleep 0.3
printf "${GREEN}✓${NC} 12 new assertions added\n"
sleep 0.3
printf "${GREEN}✓${NC} Better structure validation\n"
sleep 0.3

printf "\n${YELLOW}Improvements Made:${NC}\n"
printf "• Config management with fixtures\n"
printf "• Schema validation for responses\n"
printf "• Better error checking\n"
printf "• More comprehensive coverage\n"

sleep 1.2
