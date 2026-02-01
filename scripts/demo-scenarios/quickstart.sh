#!/bin/bash
# Demo: Quickstart
# Duration: 60 seconds
# Description: Install → capture → generate tests workflow
# Shows the complete quickstart workflow for TraceTap

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Typing speed (seconds per character)
CHAR_DELAY=0.02

# Pause durations
SHORT_PAUSE=0.3
NORMAL_PAUSE=1.0
LONG_PAUSE=2.0

type_command() {
    local cmd="$1"
    local delay="${2:-$CHAR_DELAY}"

    # Print command with color
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

# Clear and start
clear
sleep 0.5

# Header
printf "${GREEN}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                        TraceTap Demo                           ║
║         HTTP Traffic Capture & API Documentation              ║
╚════════════════════════════════════════════════════════════════╝
EOF
printf "${NC}\n"
sleep 1.5

# Section 1: Show project structure
print_header "Step 1: Project Overview"

type_command "ls -la"
sleep 0.3
cat << 'EOF'
drwxrwxr-x  12 user user  4096 Feb  1 22:29 .
-rw-rw-r--   1 user user  2697 Feb  1 03:42 README.md
-rw-rw-r--   1 user user  1073 Feb  1 03:42 LICENSE
drwxrwxr-x   6 user user  4096 Feb  1 22:28 docs
drwxrwxr-x   4 user user  4096 Feb  1 21:06 src
-rw-rw-r--   1 user user  3445 Feb  1 20:52 pyproject.toml
EOF
sleep "$LONG_PAUSE"

# Section 2: Show help
print_header "Step 2: Check Available Commands"

type_command "tracetap --help"
sleep 0.3
cat << 'EOF'
usage: tracetap [-h] {capture,generate,mock,replay} ...

TraceTap: HTTP Traffic Capture & API Documentation

positional arguments:
  {capture,generate,mock,replay}
    capture              Capture HTTP traffic with mitmproxy
    generate             Generate API documentation
    mock                 Run mock HTTP server
    replay               Replay captured traffic

optional arguments:
  -h, --help            show this help message and exit
EOF
sleep "$LONG_PAUSE"

# Section 3: Start capture
print_header "Step 3: Start Traffic Capture"

type_command "tracetap capture --port 8080"
sleep 0.5
cat << 'EOF'
[INFO] Starting mitmproxy on port 8080...
[INFO] Certificate installed: /Users/user/.mitmproxy/mitmproxy-ca-cert.pem
[INFO] Listening on http://127.0.0.1:8080
[INFO] Ready to capture traffic...
[INFO] Waiting for requests...
EOF
sleep "$NORMAL_PAUSE"

type_output "[In another terminal, making API requests...]"
sleep "$NORMAL_PAUSE"

# Section 4: Show captured requests
print_header "Step 4: Requests Captured"

sleep 0.5
cat << 'EOF'
[INFO] Captured request:
  GET /api/users HTTP/1.1
  Host: jsonplaceholder.typicode.com
  User-Agent: curl/7.64.1

[INFO] Captured request:
  POST /api/users HTTP/1.1
  Host: jsonplaceholder.typicode.com
  Content-Type: application/json
  {
    "name": "John Doe",
    "email": "john@example.com"
  }

[INFO] Captured 2 requests in 5 seconds
[INFO] Stopping capture... (press Ctrl+C)
EOF
sleep "$LONG_PAUSE"

# Section 5: Generate Postman collection
print_header "Step 5: Generate Postman Collection"

type_command "tracetap generate --format postman --output collection.json"
sleep 0.5
cat << 'EOF'
[INFO] Analyzing captured traffic...
[INFO] Found 2 API endpoints:
  - GET /api/users
  - POST /api/users
[INFO] Generating Postman collection with AI enhancement...
[INFO] Collection saved: collection.json
EOF
sleep "$NORMAL_PAUSE"

type_command "ls -lh collection.json"
sleep 0.3
cat << 'EOF'
-rw-r--r--  1 user staff  4.2K Feb  1 22:35 collection.json
EOF
sleep "$NORMAL_PAUSE"

# Section 6: Show generated documentation
print_header "Step 6: View Generated Documentation"

type_command "cat collection.json | head -30"
sleep 0.3
cat << 'EOF'
{
  "info": {
    "name": "Captured API Collection",
    "description": "Auto-generated from HTTP traffic capture",
    "version": "1.0.0"
  },
  "item": [
    {
      "name": "Users",
      "item": [
        {
          "name": "Get All Users",
          "request": {
            "method": "GET",
            "url": "{{baseUrl}}/api/users",
            "description": "Retrieve list of all users"
          }
        }
      ]
    }
  ]
}
EOF
sleep "$LONG_PAUSE"

# Final summary
print_header "Summary"

printf "${GREEN}✓${NC} Traffic captured successfully\n"
sleep 0.3
printf "${GREEN}✓${NC} API documentation generated\n"
sleep 0.3
printf "${GREEN}✓${NC} Postman collection created\n"
sleep 0.3

printf "\n${YELLOW}Next steps:${NC}\n"
printf "1. Open collection.json in Postman\n"
printf "2. Set base URL variable\n"
printf "3. Run requests against your API\n"
printf "4. Use for testing and documentation\n"

sleep 2
