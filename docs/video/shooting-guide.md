# TraceTap Demo Video Shooting Guide

Complete technical reference for recording a professional 4-5 minute demo video.

---

## Table of Contents

1. [Technical Requirements](#technical-requirements)
2. [Software Setup](#software-setup)
3. [Recording Environment](#recording-environment)
4. [Scene-by-Scene Breakdown](#scene-by-scene-breakdown)
5. [Terminal Commands](#terminal-commands)
6. [Sample API Setup](#sample-api-setup)
7. [Screen Recording Guide](#screen-recording-guide)
8. [Post-Production](#post-production)
9. [Publishing Checklist](#publishing-checklist)

---

## Technical Requirements

### Hardware Minimum Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Screen Resolution** | 1440x900 | 1920x1080 (native) |
| **Screen Density** | 100 DPI | 100-150 DPI |
| **Video Recorder** | 30 FPS | 60 FPS capability |
| **Monitor Size** | 24" | 27"+ (for scaling text) |
| **CPU** | i5/Ryzen 5 | i7/Ryzen 7 (for smooth recording) |
| **RAM** | 8GB | 16GB+ |
| **Storage** | 50GB free | 100GB+ (for multiple takes) |
| **Network** | Stable LAN | Wired connection (no WiFi for API demo) |

### Operating System

Recommended: **macOS** or **Linux** (Ubuntu 20.04+)
- More predictable terminal appearance
- Better audio capabilities
- Simpler screen recording workflow

Windows can work but requires:
- Windows Terminal (not cmd.exe)
- PowerShell 7+
- WSL2 for smooth demo experience

---

## Software Setup

### Pre-Recording Installation

```bash
# Create working directory for demo
mkdir ~/tracetap-demo
cd ~/tracetap-demo

# Clone TraceTap (if not already installed)
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ai.txt

# Set API key for AI features
export ANTHROPIC_API_KEY='your-api-key-here'

# Verify installation
python tracetap.py --help
```

### Screen Recording Software

#### macOS (Recommended)
**ScreenFlow** (Commercial, $99)
- Best quality output
- Built-in editing
- Handles full-screen terminal perfectly
- Audio mixing capabilities

Alternative: **OBS Studio** (Free, open-source)
```bash
brew install obs
```

#### Linux
**OBS Studio** (Recommended)
```bash
sudo apt-get install obs-studio
```

**SimpleScreenRecorder** (Alternative)
```bash
sudo apt-get install simplescreenrecorder
```

#### Windows
**OBS Studio** or **ScreenFlow (alternative)**
```powershell
choco install obs-studio
```

### Text Editor & IDE

**Visual Studio Code** (Free)
```bash
# Install if not present
brew install visual-studio-code  # macOS
# or download from code.visualstudio.com

# Install extensions:
# - Python (Microsoft)
# - Better Comments
# - One Dark Pro theme (or Dracula)
```

**Theme Settings (for clarity on video)**
```json
{
  "workbench.colorTheme": "Dracula",
  "editor.fontSize": 16,
  "editor.fontFamily": "Menlo, Monaco, Courier New",
  "editor.lineHeight": 1.6,
  "editor.wordWrap": "on"
}
```

### Terminal Emulator

**iTerm2** (macOS) or **GNOME Terminal** (Linux)

**Terminal Settings for Recording:**

```
Font: Monaco or Menlo, 16pt or larger
Colors: Dracula or One Dark Pro
Opacity: 100% (solid background)
Line spacing: 1.5
Character spacing: 1.2
Columns: ~100 characters (wide enough for commands)
Rows: ~30 rows (tall enough for output)
```

Example `.bash_profile` for clean terminal:
```bash
# Clear screen before demo
alias demo='clear && echo "Ready to record"'

# Custom prompt (short and clean)
PS1="\[\033[36m\]$ \[\033[0m\]"

# Disable git branch info for cleaner look
export PROMPT_COMMAND=""
```

### Audio Recording

**Separate Audio Track** (Recommended for professional quality)

Recording audio separately allows:
- Better control over levels
- Professional audio editing
- Easier to sync in post-production
- Backup if screen recording audio fails

Tools:
- **macOS**: Voice Memos app (built-in) or Audacity (free)
- **Linux/Windows**: Audacity (free, open-source)

```bash
# Install Audacity
brew install audacity  # macOS
sudo apt-get install audacity  # Linux
```

---

## Recording Environment

### Display Configuration

**Screen Layout:**
1. **Primary Monitor (Used for recording):** 1920x1080 native, 100% scale
2. **Secondary Monitor (Optional):** For viewing script/notes during recording

**Recommended Resolution:** 1920x1080 at 100% scale
- Provides crisp text for terminal and code
- YouTube standard 16:9 aspect ratio
- Easy to read for viewers

### Lighting

**For camera introduction/outro (if needed):**
- **Key light:** 45 degrees to left, 2-3 feet away
- **Fill light:** Opposite side, slightly dimmer
- **Avoid:** Direct overhead lighting or backlit situations
- **Color temp:** 5600K (daylight) or consistent LED

If recording screen-only: Proper room lighting prevents reflection on monitor.

### Audio Environment

**Recording Location Requirements:**
- Quiet room with minimal echo
- Close microphone (6-12 inches from mouth)
- External USB microphone recommended:
  - **Blue Yeti** (good budget option)
  - **Audio-Technica AT2020USB** (professional)
  - **Rode NT-USB** (compact and quality)

**Microphone Settings:**
- Gain: Set to peak around -6dB during normal speech
- Reduce room noise/echo in recording software
- Test record 30 seconds before full demo

### Background (Desktop)

**Keep Desktop Clean:**
```bash
# Create demo folder to organize everything
mkdir -p ~/tracetap-demo/{captures,tests,generated}

# Hide other applications from dock
# (System Preferences → Dock → minimize when opening)

# Set neutral desktop wallpaper (solid color or subtle)
# Avoid busy patterns or bright colors
```

---

## Scene-by-Scene Breakdown

### SCENE 1: Problem Segment (0:00-0:30)

**What You're Recording:**
- Problem statement graphics (created in post-production)
- Examples of manual testing pain points
- Side-by-side comparison

**Technical Notes:**
- This segment has **minimal live recording**
- Mostly graphics and overlays (created in post)
- You'll narrate over pre-made visuals

**Deliverable:**
- Narration audio (recorded separately)
- Screenshots of: VS Code with test code, Manual documentation

**Screenshot Preparation:**
```bash
# VS Code: Open and show typical test file
open -a "Visual Studio Code"

# Show file: tests/test_manual.py
# Contains: Manually written test functions
```

---

### SCENE 2: Solution Segment (0:30-2:30)

**Sub-Scene 2a: Installation (0:30-0:45)**

**Record These Commands:**
```bash
# Terminal: Show Python version
python3 --version
# Expected output: Python 3.8.x or higher

# Show pip version
pip --version

# Navigate to tracetap directory
cd ~/tracetap-demo/tracetap

# Activate virtual environment
source venv/bin/activate
# Prompt should show (venv) prefix

# Show help (to verify installation)
python tracetap.py --help
```

**Success Criteria:**
- Text is readable (16pt+ font)
- Commands execute without errors
- Output shows version info and help text
- Terminal background is solid (no transparency)

**Timing:**
- Type at **realistic human speed** (not too fast, not too slow)
- ~80-100 characters per minute
- ~2-3 seconds per command line

---

**Sub-Scene 2b: Start Capture (0:45-1:00)**

**Setup Before Recording:**

1. **Terminal Window 1: Proxy**
```bash
cd ~/tracetap-demo/tracetap
source venv/bin/activate

# Clean any previous captures
rm -f captured.json

# Ready command (don't run yet):
python tracetap.py --listen 8080 --export captured.json
```

2. **Terminal Window 2: Test Requests** (separate terminal tab)
```bash
# This terminal will make API calls
# (script provided below)
```

3. **Text Editor: Have a clean VS Code window ready**

**Record This Sequence:**

1. Type the capture command:
   ```bash
   python tracetap.py --listen 8080 --export captured.json
   ```
2. Press Enter
3. Show output:
   ```
   [14:32:15] TraceTap HTTP Proxy started
   [14:32:15] Listening on 0.0.0.0:8080
   [14:32:15] Waiting for traffic...
   ```

**Critical:** Let the output sit for 3-5 seconds so viewers can read it.

---

**Sub-Scene 2c: Make API Calls (1:00-1:30)**

**Before Recording:**

Create a shell script that makes API calls to your sample server:

File: `demo-api-calls.sh`
```bash
#!/bin/bash

# Set proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# API calls to capture
echo "Making API calls..."
sleep 2

# User endpoints
curl -X GET "http://localhost:3000/api/users" \
  -H "Content-Type: application/json"
sleep 1

curl -X POST "http://localhost:3000/api/users" \
  -H "Content-Type: application/json" \
  -d '{"name":"John","email":"john@example.com"}'
sleep 1

curl -X GET "http://localhost:3000/api/users/1" \
  -H "Content-Type: application/json"
sleep 1

curl -X PATCH "http://localhost:3000/api/users/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Updated"}'
sleep 1

curl -X DELETE "http://localhost:3000/api/users/2"
sleep 1

# Posts endpoints
curl -X GET "http://localhost:3000/api/users/1/posts" \
  -H "Content-Type: application/json"
sleep 1

echo "Done"
```

**Make it executable:**
```bash
chmod +x demo-api-calls.sh
```

**Record This Sequence:**

1. **Show Terminal 1:** Capture proxy running with "Waiting for traffic..."
2. **Show Terminal 2:** About to run API calls
3. **Run the script:**
   ```bash
   ./demo-api-calls.sh
   ```
4. **Switch back to Terminal 1:** Watch requests appear in real-time
   ```
   [14:32:20] GET http://localhost:3000/api/users → 200 (45ms)
   [14:32:21] POST http://localhost:3000/api/users → 201 (120ms)
   [14:32:22] GET http://localhost:3000/api/users/1 → 200 (32ms)
   [14:32:23] PATCH http://localhost:3000/api/users/1 → 200 (55ms)
   [14:32:24] DELETE http://localhost:3000/api/users/2 → 204 (40ms)
   [14:32:25] GET http://localhost:3000/api/users/1/posts → 200 (85ms)
   ```

**Pro Tip:** Make requests slow enough that viewer can see each line appear (not all at once).

**Duration:** ~30 seconds total for all requests

---

**Sub-Scene 2d: Generate Tests (1:30-1:50)**

**Before Recording:**

Prepare the captured.json file from previous step.

**Record This Sequence:**

1. **Terminal:** Show captured.json was created
   ```bash
   ls -lh captured.json
   # Output: -rw-r--r-- 1 user staff 15K Jan 1 14:32 captured.json
   ```

2. **Run AI generation:**
   ```bash
   export ANTHROPIC_API_KEY='your-api-key'
   python -m tracetap.ai.suggest captured.json
   ```
   (or use appropriate command based on your setup)

3. **Show output:**
   ```
   [14:32:30] Analyzing captured traffic...
   [14:32:35] Inferring request flows...
   [14:32:40] Organizing into folders...
   [14:32:45] Generating Postman collection...
   ✓ Generated: postman-collection.json (12KB)
   ```

4. **Optionally run test generator:**
   ```bash
   tracetap-playwright.py captured.json -o tests/
   ```
   Output:
   ```
   [14:32:50] Generating Playwright tests...
   [14:32:55] Creating test fixtures...
   ✓ Generated: tests/test_api_calls.py (8KB, 47 test cases)
   ```

5. **Open VS Code and show generated test file:**
   - Open: `tests/test_api_calls.py`
   - Scroll through showing test functions
   - Highlight test count: "47 tests generated"

**Timing Notes:**
- Let each command run to completion
- Don't cut off the output
- Wait 2-3 seconds after generation completes before moving to next step

---

**Sub-Scene 2e: Generated Artifacts Summary (1:50-2:10)**

**Record This Sequence:**

1. **Terminal:** List all generated files
   ```bash
   ls -lh *.json && ls -lh tests/
   ```
   Output:
   ```
   -rw-r--r-- 1 user staff 15K Jan 1 14:32 captured.json
   -rw-r--r-- 1 user staff 12K Jan 1 14:33 postman-collection.json
   -rw-r--r-- 1 user staff  5K Jan 1 14:33 contract.yaml

   tests/:
   -rw-r--r-- 1 user staff  8K Jan 1 14:33 test_api_calls.py
   -rw-r--r-- 1 user staff  2K Jan 1 14:33 conftest.py
   ```

2. **Show each file briefly in code editor:**
   - Postman collection (first 20 lines)
   - Test file (show first test function)
   - Contract file (show structure)

3. **Optional:** Tree view of generated files
   ```bash
   tree . -L 2 -I "__pycache__"
   ```

---

**Sub-Scene 2f: Speed Comparison (2:10-2:30)**

**This is graphics/overlay work (post-production):**
- Create comparison chart: "4.5 hours → 75 seconds"
- Show time savings visualization
- Can be text overlay or animated graphic

**Narration Timing:**
- Let chart sit on screen for full narration
- Narrator reads comparison during this segment

---

### SCENE 3: Magic Segment (2:30-4:30)

**Sub-Scene 3a: AI Test Suggestions (2:30-3:00)**

**Prepare Before Recording:**

Create a sample output file showing AI suggestions:

File: `ai-suggestions.json`
```json
{
  "analysis": {
    "requests_captured": 6,
    "test_coverage": "42%",
    "gaps_identified": 8
  },
  "suggestions": [
    {
      "type": "error_handling",
      "test": "Test 500 Internal Server Error response",
      "reason": "No error responses captured for error handling"
    },
    {
      "type": "authentication",
      "test": "Test with expired bearer token",
      "reason": "No authentication failure scenarios captured"
    },
    {
      "type": "boundary",
      "test": "Test with empty string for name field",
      "reason": "Edge case not covered in captures"
    },
    {
      "type": "concurrency",
      "test": "Test concurrent POST requests",
      "reason": "Race conditions not verified"
    },
    {
      "type": "validation",
      "test": "Test with invalid email format",
      "reason": "Input validation not tested"
    },
    {
      "type": "rate_limiting",
      "test": "Test exceeding rate limits",
      "reason": "API limits not tested"
    },
    {
      "type": "malformed",
      "test": "Test with malformed JSON body",
      "reason": "Error handling for bad input not verified"
    },
    {
      "type": "field_types",
      "test": "Test with wrong data types",
      "reason": "Type validation not tested"
    }
  ]
}
```

**Record This Sequence:**

1. **Terminal:** Show AI analysis running
   ```bash
   tracetap-ai-suggest.py captured.json
   ```
   (Or show it loading with spinner animation)

2. **Switch to browser/editor:** Show suggestions output
   - List of 8 suggestions appearing one at a time
   - Each shows: type, test name, reason

3. **Optional terminal:** Run suggest to generate new tests
   ```bash
   tracetap-ai-suggest.py captured.json --generate
   ```
   Output:
   ```
   ✓ Added 8 new test suggestions
   Total test coverage improved: 42% → 73%
   ```

4. **Show updated test file:**
   - Before: 47 tests
   - After: 95 tests (47 + 48 suggestions)
   - Highlight new tests in VS Code

**Duration:** 30 seconds total

---

**Sub-Scene 3b: Contract Testing (3:00-3:30)**

**Prepare Before Recording:**

Create sample contract file:

File: `user-service-contract.yaml`
```yaml
service: user-service
version: 1.0.0
endpoints:
  - path: /api/users
    method: GET
    description: List all users
    response:
      status: 200
      body:
        type: array
        items:
          type: object
          required: [id, name, email]
          properties:
            id:
              type: integer
            name:
              type: string
            email:
              type: string
            created_at:
              type: string
              format: date-time

  - path: /api/users/{id}
    method: GET
    description: Get single user by ID
    response:
      status: 200
      body:
        type: object
        required: [id, name, email]

  - path: /api/users/{id}
    method: DELETE
    description: Delete user by ID
    response:
      status: 204
```

**Record This Sequence:**

1. **Terminal:** Show contract verification starting
   ```bash
   tracetap-verify-contract.py captured.json --contract user-service-contract.yaml
   ```

2. **Show output with real-time verification:**
   ```
   [14:35:10] Verifying contract: user-service-contract.yaml
   [14:35:11] ✓ GET /api/users - 200 response contains required fields
   [14:35:12] ✓ GET /api/users/{id} - 200 response matches schema
   [14:35:13] ✓ DELETE /api/users/{id} - 204 response correct
   [14:35:14] ✓ POST /api/users - 201 response correct
   [14:35:15] ✓ All required fields present in responses
   [14:35:16] ✓ No breaking changes detected

   ✅ Contract Verification: PASSED
   12 endpoints verified. 100% compliance.
   ```

3. **Optional:** Show what would happen with breaking change
   - Modify contract (simulate breaking change)
   - Show verification fails with clear error message
   - Demonstrate how this catches issues

4. **Show contract in code editor:**
   - Highlight key required fields
   - Show how it's structured

5. **Optional:** Show CI/CD integration
   - Screenshot of GitHub Actions workflow
   - Show contract check as part of pipeline

**Duration:** 30 seconds total

---

**Sub-Scene 3c: Living Documentation (3:30-4:00)**

**Prepare Before Recording:**

Generate OpenAPI spec from captures:

File: `openapi.yaml` (generated by TraceTap)
```yaml
openapi: 3.0.0
info:
  title: User Service API
  version: 1.0.0
  description: API for managing users and their posts
servers:
  - url: http://localhost:3000
    description: Development server
paths:
  /api/users:
    get:
      summary: List all users
      tags: [Users]
      responses:
        '200':
          description: List of users
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
    post:
      summary: Create a new user
      tags: [Users]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name, email]
              properties:
                name:
                  type: string
                email:
                  type: string
      responses:
        '201':
          description: User created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
  /api/users/{id}:
    get:
      summary: Get user by ID
      tags: [Users]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: User details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      required: [id, name, email, created_at]
      properties:
        id:
          type: integer
        name:
          type: string
        email:
          type: string
        created_at:
          type: string
          format: date-time
```

**Record This Sequence:**

1. **Terminal:** Generate OpenAPI spec
   ```bash
   tracetap-export-openapi.py captured.json -o openapi.yaml
   ```
   Output:
   ```
   ✓ Generated OpenAPI specification: openapi.yaml
   ✓ Detected 6 endpoints
   ✓ Inferred 3 data schemas
   ```

2. **Show OpenAPI in editor:**
   - Scroll through showing structure
   - Highlight: endpoints, parameters, schemas

3. **Optional:** Show in browser with Swagger UI
   - Use Swagger Editor online (editor.swagger.io)
   - Paste YAML content
   - Show interactive documentation

4. **Comparison with manual docs:**
   - Old way: Manually maintain markdown files
   - New way: Auto-generated from actual traffic
   - Always accurate, never stale

**Duration:** 20 seconds

---

**Sub-Scene 3d: Impact Montage (4:00-4:30)**

**This is post-production graphics work:**
- Quick cuts (3-4 seconds each)
- Icons and animations
- Text overlays
- Background music building

**Sequence:**
1. ⏱️ Developer staying late → ✓ Developer leaving on time
2. 🐛 Bug in production → ✓ Bug caught in CI
3. 😞 Frustrated team → 🎉 Happy team celebrating
4. 📚 Stack of documentation → 📋 Single unified spec
5. ✍️ Manual test writing → ⚡ Automated tests
6. 🔄 Manual workflow → 🤖 AI-assisted workflow

**Text Overlays (appear one at a time):**
- "Ship with confidence"
- "Tests run automatically"
- "Documentation keeps itself updated"
- "Breaking changes caught instantly"
- "Your team ships faster"

**Audio:**
- Narrator concludes main message
- Background music swells
- Sound effects for each transition (subtle, professional)

**Duration:** 30 seconds

---

### SCENE 4: Call to Action (4:30-5:00)

**Sub-Scene 4a: Quick Install (4:30-4:45)**

**Record This Sequence:**

1. **Terminal:** Show npm or pip install
   ```bash
   npm install -g tracetap
   # or
   pip install tracetap
   ```

2. **Show help command:**
   ```bash
   tracetap --help
   ```

3. **Show one more quick command:**
   ```bash
   tracetap quickstart
   ```

**Duration:** 15 seconds

---

**Sub-Scene 4b: Resources & Links (4:45-5:00)**

**This is post-production graphics:**

**Final slide showing:**
```
╔════════════════════════════════════════╗
║                                        ║
║        TraceTap: Intelligent API       ║
║              Testing                   ║
║                                        ║
║  📖 GitHub: github.com/VassilisSoum/   ║
║     tracetap                           ║
║                                        ║
║  🌐 Docs: docs.tracetap.dev            ║
║  🐦 Twitter: @tracetap                 ║
║  💼 LinkedIn: /company/tracetap/       ║
║                                        ║
║  ⭐ Star on GitHub                     ║
║  🔗 Join the community                 ║
║                                        ║
╚════════════════════════════════════════╝
```

**Audio:**
- Closing narration
- Thank you message
- Background music fades

**Duration:** 15 seconds

---

## Terminal Commands

### Pre-Recording: Clean Setup

```bash
# Create demo directory
mkdir -p ~/tracetap-demo
cd ~/tracetap-demo

# Clone or navigate to tracetap
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ai.txt

# Set API key
export ANTHROPIC_API_KEY='sk-...'

# Test installation
python tracetap.py --help
```

### During Recording: Main Commands

```bash
# Command 1: Show proxy starting
python tracetap.py --listen 8080 --export captured.json

# Command 2: Make API calls (from separate terminal)
./demo-api-calls.sh

# Command 3: Generate AI test suggestions
export ANTHROPIC_API_KEY='your-api-key'
python -m tracetap.ai.suggest captured.json

# Command 4: Generate Playwright tests
tracetap-playwright.py captured.json -o tests/

# Command 5: Generate OpenAPI spec
tracetap-export-openapi.py captured.json -o openapi.yaml

# Command 6: Verify contract
tracetap-verify-contract.py captured.json --contract user-service-contract.yaml

# Command 7: Show files generated
ls -lh *.json tests/
```

### Terminal Display Settings

Make sure terminal text is readable:

```bash
# Check font size (should be 16pt or larger)
# In terminal preferences:
#   - Font: Monaco, Menlo, or Inconsolata
#   - Size: 16pt
#   - Line height: 1.6
#   - Width: 100-120 columns

# Verify screen resolution
system_profiler SPDisplaysDataType  # macOS
# or
xrandr  # Linux

# Set terminal to full screen for recording
# macOS: Press Control + Command + F
# Linux: F11
```

---

## Sample API Setup

### Option A: Node.js Express API (Recommended)

**File: `demo-api.js`**

```javascript
const express = require('express');
const app = express();

app.use(express.json());

// In-memory database for demo
let users = [
  { id: 1, name: 'Alice', email: 'alice@example.com', created_at: '2024-01-01T10:00:00Z' },
  { id: 2, name: 'Bob', email: 'bob@example.com', created_at: '2024-01-02T10:00:00Z' },
];

let nextUserId = 3;
let posts = [];

// Get all users
app.get('/api/users', (req, res) => {
  res.json(users);
});

// Get single user
app.get('/api/users/:id', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).json({ error: 'Not found' });
  res.json(user);
});

// Create user
app.post('/api/users', (req, res) => {
  const { name, email } = req.body;
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email required' });
  }
  const user = {
    id: nextUserId++,
    name,
    email,
    created_at: new Date().toISOString()
  };
  users.push(user);
  res.status(201).json(user);
});

// Update user
app.patch('/api/users/:id', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).json({ error: 'Not found' });

  Object.assign(user, req.body);
  res.json(user);
});

// Delete user
app.delete('/api/users/:id', (req, res) => {
  const index = users.findIndex(u => u.id === parseInt(req.params.id));
  if (index === -1) return res.status(404).json({ error: 'Not found' });

  users.splice(index, 1);
  res.status(204).send();
});

// Get user posts
app.get('/api/users/:id/posts', (req, res) => {
  const userPosts = posts.filter(p => p.user_id === parseInt(req.params.id));
  res.json(userPosts);
});

// Create post for user
app.post('/api/users/:id/posts', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).json({ error: 'User not found' });

  const post = {
    id: posts.length + 1,
    user_id: user.id,
    title: req.body.title,
    content: req.body.content,
    created_at: new Date().toISOString()
  };
  posts.push(post);
  res.status(201).json(post);
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Demo API running on http://localhost:${PORT}`);
});
```

**Setup and Run:**

```bash
# Create demo API
mkdir demo-api
cd demo-api
npm init -y
npm install express

# Copy the above code to demo-api.js

# Start the server (in separate terminal)
node demo-api.js
# Output: Demo API running on http://localhost:3000
```

### Option B: Python Flask API (Alternative)

```python
# demo-api.py
from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# In-memory database
users = [
    {'id': 1, 'name': 'Alice', 'email': 'alice@example.com', 'created_at': '2024-01-01T10:00:00Z'},
    {'id': 2, 'name': 'Bob', 'email': 'bob@example.com', 'created_at': '2024-01-02T10:00:00Z'},
]
next_user_id = 3

@app.route('/api/users', methods=['GET'])
def list_users():
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    global next_user_id
    data = request.get_json()

    if not data.get('name') or not data.get('email'):
        return jsonify({'error': 'Name and email required'}), 400

    user = {
        'id': next_user_id,
        'name': data['name'],
        'email': data['email'],
        'created_at': datetime.now().isoformat() + 'Z'
    }
    next_user_id += 1
    users.append(user)
    return jsonify(user), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(user)

@app.route('/api/users/<int:user_id>', methods=['PATCH'])
def update_user(user_id):
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        return jsonify({'error': 'Not found'}), 404

    user.update(request.get_json())
    return jsonify(user)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    global users
    users = [u for u in users if u['id'] != user_id]
    return '', 204

if __name__ == '__main__':
    app.run(port=3000, debug=False)
```

---

## Screen Recording Guide

### Using OBS Studio (Cross-Platform)

**Installation:**
```bash
# macOS
brew install obs

# Linux
sudo apt-get install obs-studio

# Windows
choco install obs-studio
```

**Setup Steps:**

1. **Create New Scene:**
   - Scene → "+" → Name: "Demo"

2. **Add Source:**
   - Right-click in Sources → "Display Capture" (or "Screen Capture")
   - Select your main monitor
   - Adjust size to fill canvas

3. **Configure Settings:**
   - Settings → Video
     - Base Resolution: 1920x1080
     - Output Resolution: 1920x1080
     - FPS: 60
   - Settings → Output
     - Recording Format: MP4 (H.264)
     - Quality: High (CRF 18-20)
     - Audio Codec: AAC

4. **Start Recording:**
   - Click "Start Recording"
   - Perform your demo
   - Click "Stop Recording"

**Output:** `output.mp4` (typically 2-3 GB for 5 minutes at 1080p60)

### Using ScreenFlow (macOS)

1. **Open ScreenFlow**
2. **Configure settings:**
   - Resolution: 1920x1080
   - Frame Rate: 30 fps (or 60 for smooth motion)
   - Audio: Built-in microphone or USB mic
3. **Start Recording:** Red record button
4. **Perform demo**
5. **Stop Recording:** Red stop button
6. **Edit (optional):** Trim, add music
7. **Export:** 1080p MP4

### Using SimpleScreenRecorder (Linux)

1. **Open SimpleScreenRecorder**
2. **Configure:**
   - Input: Your display (1920x1080)
   - Output: MP4 format
   - Quality: High
3. **Start Recording**
4. **Perform demo**
5. **Stop and save**

---

## Recording Checklist

Before hitting record, verify:

- [ ] Terminal font is 16pt or larger and readable
- [ ] Screen resolution is 1920x1080 or higher
- [ ] Only relevant applications are visible (hide Slack, email, etc.)
- [ ] API server is running on localhost:3000
- [ ] TraceTap venv is activated in terminal
- [ ] All demo scripts are prepared and tested
- [ ] Audio levels are set (if recording separately)
- [ ] Microphone is working (test record 30 seconds)
- [ ] Screen recording software is ready
- [ ] Disk has at least 50GB free space
- [ ] Unnecessary browser tabs are closed
- [ ] Desktop is clean (no clutter visible)
- [ ] All commands have been pre-typed in history (optional but helps)

---

## Multiple Takes Strategy

**Best Practices:**

1. **Record each scene separately:**
   - Easier to edit and replace bad takes
   - Reduces file size per take
   - Allows rework of individual segments

2. **Naming convention:**
   ```
   demo-scene-01-problem.mp4
   demo-scene-2a-install.mp4
   demo-scene-2b-capture-start.mp4
   demo-scene-2c-api-calls.mp4
   demo-scene-2d-generate-tests.mp4
   demo-scene-3a-ai-suggestions.mp4
   demo-scene-3b-contract-testing.mp4
   ```

3. **Target multiple good takes:**
   - Record each scene 2-3 times
   - Pick the best take in editing
   - Reduces pressure for perfect recording

4. **Common issues and retakes:**
   - Typo in command → Re-record from that point
   - Screen obscured by dialog → Re-record
   - Output scrolled off screen → Re-record
   - Audio too quiet → Re-record with adjusted mic
   - Pacing too fast → Re-record slower

---

## Post-Production

### Video Editing Workflow

**Recommended Software:**
- **macOS:** Final Cut Pro, Adobe Premiere, or DaVinci Resolve (free)
- **Windows/Linux:** DaVinci Resolve (free, professional quality)
- **Simple editing:** iMovie (macOS), Windows Photos (Windows)

### Assembly Steps

1. **Import clips** in chronological order
2. **Trim each clip** to remove mistakes/pauses
3. **Add narration** audio track
4. **Sync timing** to narration
5. **Add title** at beginning (3-5 seconds)
6. **Add graphics/overlays:**
   - Problem segment graphics
   - Speed comparison chart
   - Company logo/branding
   - Text overlays for key points
7. **Add music** to background (low volume, not distracting)
8. **Add captions** (auto-generate, then review/fix)
9. **Color correction:**
   - Ensure consistent brightness
   - Adjust color temperature if needed
   - Boost contrast slightly
10. **Final export** to MP4 1080p 30fps

### Audio Processing

**If recorded separately:**

1. **Import narration audio**
2. **Normalize levels:** -3dB to -1dB peak
3. **Remove background noise** (use Audacity or Adobe Audition)
4. **Add background music:**
   - Volume: -20dB (barely noticeable)
   - Fade in at start (2 seconds)
   - Fade out at end (2 seconds)
5. **Layer sound effects** (optional, subtle transitions)

### Caption Generation

**Using YouTube auto-captions:**
1. Upload to YouTube (unlisted)
2. Let YouTube auto-generate captions
3. Download SRT file
4. Review and fix errors
5. Embed in video during final edit

**Or use Descript (easy, automatic):**
```bash
# Descript provides transcript + captions
# Upload MP4 → Get captions → Download SRT
```

### Graphics & Overlays

**Create in Adobe Illustrator, Figma, or Canva:**

1. **Problem segment:**
   - "Before" timeline (manual testing)
   - "After" timeline (TraceTap)
   - Pain points icons

2. **Solution segment:**
   - "47 tests in 60 seconds" graphic
   - File type icons (Postman, Python, JSON)
   - Timing annotations

3. **Magic segment:**
   - Test gap analysis chart
   - Contract validation visual
   - Documentation schema

4. **CTA segment:**
   - GitHub link with QR code
   - Website URL
   - Social media handles

### Export Settings

**Final Export (for YouTube/production):**

| Setting | Value |
|---------|-------|
| Format | MP4 (H.264) |
| Resolution | 1920x1080 |
| Frame Rate | 30 fps |
| Bitrate | 8000-10000 kbps (video) |
| Audio | AAC, 128 kbps, 48 kHz |
| File Size | ~300-400 MB for 4:30 video |

**Command line export (macOS with FFmpeg):**
```bash
ffmpeg -i input.mov \
  -c:v libx264 \
  -preset slow \
  -crf 20 \
  -c:a aac \
  -b:a 128k \
  output.mp4
```

---

## Publishing Checklist

### Before Publishing

- [ ] Video is 1920x1080 or higher
- [ ] Audio is clear and normalized
- [ ] Captions are accurate and spell-checked
- [ ] All text overlays are readable (contrast >4.5:1)
- [ ] Total duration is 3:30-5:00 minutes
- [ ] No personal info visible (API keys, emails, etc.)
- [ ] Links are correct and not typos
- [ ] File size under 500 MB (for fastest upload)
- [ ] Watched entire video for quality issues
- [ ] Had colleague/friend review

### YouTube Upload

**Before Upload:**

1. Create compelling **title** (60 characters max):
   ```
   TraceTap: Generate 47 Tests in 60 Seconds
   ```

2. Write **description** (5000 characters available):
   ```
   Transform Your API Testing with TraceTap

   Stop wasting hours on manual test creation. TraceTap captures
   your API traffic and generates complete test suites instantly.

   Features Shown:
   ✓ One-command proxy setup
   ✓ Real-time traffic capture
   ✓ AI-powered test generation (47 tests in 60 seconds)
   ✓ Multiple export formats (Postman, Pytest)
   ✓ Contract testing for microservices
   ✓ Auto-generated API documentation

   Get Started:
   📦 npm install -g tracetap
   📖 Docs: docs.tracetap.dev
   🐙 GitHub: github.com/VassilisSoum/tracetap

   Chapters:
   0:00 - Problem: Manual Testing Pain
   0:30 - Solution: TraceTap Workflow
   2:30 - Magic: AI Suggestions & Contracts
   4:30 - Call to Action

   Credits:
   - Tool: TraceTap v1.0
   - Music: [Attribution if used]
   - Demo API: Node.js Express
   ```

3. Select **thumbnail:**
   - Use TraceTap logo prominently
   - Add "47" or "60 seconds" text
   - Bright, contrasting colors
   - Test size: Show in video player preview

4. Add **tags** (relevant keywords):
   ```
   tracetap, api testing, test automation, postman, pytest,
   playwright, contract testing, mitmproxy, devtools,
   qe automation, testing, api documentation, mock server,
   ai testing, intelligent testing, test generation
   ```

5. Select **category:** "Science & Technology"

6. Set **visibility:** Public (or Unlisted for initial review)

### Post-Upload

- [ ] Video processed (wait for HD quality to be available)
- [ ] Captions auto-generated and reviewed
- [ ] Pinned comment with links/timestamps
- [ ] Add to relevant playlist
- [ ] Share on social media
- [ ] Create blog post with transcript
- [ ] Monitor comments for feedback

### Social Media Posts

**Twitter:**
```
🎥 New Demo: TraceTap generates 47 tests in 60 seconds

Stop manual testing. Start AI-assisted API testing.

Watch how to:
- Capture API traffic in seconds
- Generate Postman collections instantly
- Create Pytest tests automatically
- Verify contracts before deployment

📺 Full demo: [YouTube link]
📖 Docs: docs.tracetap.dev
🐙 GitHub: github.com/VassilisSoum/tracetap

#APITesting #QA #DevTools #OpenSource
```

**LinkedIn:**
```
Excited to share the TraceTap demo video showing how to
eliminate manual API test creation.

The challenge: Testing APIs is tedious, error-prone, and
time-consuming. Most teams do it manually.

The solution: One command to capture traffic. AI-powered
analysis. Generate complete test suites instantly.

Key capabilities shown:
- HTTP/HTTPS traffic interception
- Multi-format export (Playwright tests, JSON captures)
- AI-driven test suggestions
- Contract testing for microservices
- Auto-generated documentation

Video: [YouTube link]
Get started: docs.tracetap.dev

#QA #Testing #DevTools #APIs #OpenSource #Automation
```

---

## Troubleshooting

### Screen Recording Issues

**Problem: Text is blurry in video**
- Solution: Increase terminal/editor font size to 18pt+
- Or: Increase screen scaling to 125%

**Problem: Terminal text cuts off**
- Solution: Make terminal window narrower (80-100 chars)
- Or: Reduce font size slightly

**Problem: Scrolling is jittery**
- Solution: Reduce frame rate to 30fps
- Or: Enable v-sync in recording software

### API Demo Issues

**Problem: API server not responding through proxy**
- Solution: Verify HTTP_PROXY env var is set
- Solution: Check that TraceTap is actually listening on port 8080
- Solution: Use `curl -v` to see full request/response

**Problem: Slow API responses during demo**
- Solution: Adjust demo-api-calls.sh sleep times
- Solution: Pre-generate captures instead of live demo
- Solution: Use local API (not over network)

**Problem: Commands don't appear in screen recording**
- Solution: Make sure you're typing in the recorded window
- Solution: Use larger font
- Solution: Type slower (human-readable pace)

### Audio Issues

**Problem: Microphone too quiet**
- Solution: Increase mic gain in recording software
- Solution: Record separately in Audacity with larger gain
- Solution: Use USB microphone (better input levels)

**Problem: Background noise in recording**
- Solution: Record in quieter room
- Solution: Use noise suppression in Audacity
- Solution: Record as separate track and mix in post

**Problem: Audio out of sync with video**
- Solution: In editor, manually adjust audio track position
- Solution: Re-record if only slightly off
- Solution: Add metadata about drift for editors to fix

---

## Quick Reference Card

**Print this and keep nearby while recording:**

```
═══════════════════════════════════════════════
           TraceTap Demo Recording Guide
═══════════════════════════════════════════════

BEFORE RECORDING:
□ Terminal: 16pt font, 100 chars wide
□ API server: Running on localhost:3000
□ TraceTap: Installed and tested
□ Proxy: Ready to listen on port 8080
□ Audio: Mic tested, levels set
□ Storage: 50GB+ free space

SCENE 1: Problem (0:30)
   Just show graphics/narration

SCENE 2a: Install (0:15)
   $ python3 --version
   $ python tracetap.py --help

SCENE 2b: Start Capture (0:15)
   $ python tracetap.py --listen 8080 --export captured.json

SCENE 2c: Make Requests (0:30)
   $ ./demo-api-calls.sh
   [Watch requests appear in proxy terminal]

SCENE 2d: Generate Tests (0:20)
   $ export ANTHROPIC_API_KEY='your-api-key'
   $ python -m tracetap.ai.suggest captured.json
   $ tracetap-playwright.py captured.json -o tests/

SCENE 2e: Show Files (0:20)
   $ ls -lh *.json tests/

SCENE 3: Magic (2:00)
   [Graphics, screenshots, post-production]

SCENE 4: CTA (0:30)
   $ npm install -g tracetap
   [Show links]

TOTAL RECORDING TIME: ~3 minutes (+ post-production)

KEY NUMBERS TO REMEMBER:
• 47 tests generated
• 60 seconds to completion
• 8 test gaps suggested by AI
• 4:30 total video duration

CONTACTS FOR HELP:
GitHub: github.com/VassilisSoum/tracetap
Docs: docs.tracetap.dev
═══════════════════════════════════════════════
```

---

## Notes for Future Recordings

After completing your first recording:

1. **Document what worked:**
   - Keep notes on best terminal settings
   - Screenshot your optimal OBS settings
   - Save successful command sequences

2. **What to improve next time:**
   - Faster pacing? Slower?
   - Need more dramatic graphics?
   - Is narration clear?
   - Are metrics compelling?

3. **Collect feedback:**
   - Internal team review
   - External beta testers
   - Comments on initial upload

4. **Build a template:**
   - Save editing project file (DaVinci/Premiere)
   - Keep captions file (SRT)
   - Archive narration audio track
   - Store all graphics/overlays for reuse

5. **Plan follow-up content:**
   - Feature deep-dives
   - Use case tutorials
   - User testimonials
   - Architecture explanations
