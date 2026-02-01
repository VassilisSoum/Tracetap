# TraceTap Demo Video Script

**Duration:** 4 minutes 30 seconds (Professional video length)

**Target Audience:** Developers, QA engineers, DevOps teams

**Overall Tone:** Technical but accessible, emphasizing speed and value

---

## Table of Contents

1. [Segment 1: Problem](#segment-1-problem-0--30-seconds)
2. [Segment 2: Solution](#segment-2-solution-30--150-seconds)
3. [Segment 3: Magic](#segment-3-magic-150--240-seconds)
4. [Segment 4: Call to Action](#segment-4-call-to-action-240--270-seconds)

---

## SEGMENT 1: PROBLEM
**Duration:** 30 seconds | **Time:** 0:00-0:30

### Narration Script

> "How many hours have you spent manually documenting APIs? Writing test cases by hand? Creating mock servers for integration testing?
>
> Writing quality tests is essential. But it's also tedious, time-consuming, and error-prone. You're essentially doing the same work twice: once to build the API, and again to test it.
>
> What if there was a better way?"

### Screen Actions

**0:00-0:10** - Show split screen comparison
- LEFT: Developer typing test cases manually in VS Code
- RIGHT: Clock showing "⏱️ 2 hours per API"
- Text overlay: "Manual Testing: Slow & Repetitive"

**0:10-0:20** - Show frustrated developer with multiple documents
- Postman collection
- Test files
- API documentation
- Mock server setup
- Text overlay: "Maintaining Multiple Formats"

**0:20-0:30** - Transition to TraceTap logo with question
- Question text appears: "What if you could eliminate the busywork?"

### Technical Setup Required

None - Just screen captures with overlays

---

## SEGMENT 2: SOLUTION
**Duration:** 2 minutes (120 seconds) | **Time:** 0:30-2:30

### Narration Script

> "Introducing TraceTap. A single command that captures your API traffic and turns it into everything you need.
>
> [PAUSE] Here's how it works.
>
> Step one: Start the capture. Just one command.
> [SHOW COMMAND]
>
> Step two: Use your API normally. Make requests, execute workflows. TraceTap records everything happening in the background.
> [SHOW REQUESTS FLOWING]
>
> Step three: Stop and export. Instantly, you get Postman collections, test files, mock servers, and more.
> [SHOW GENERATED FILES]
>
> The best part? It's AI-powered. TraceTap analyzes your traffic to organize it logically, extract variables, and suggest improvements.
>
> Forty-seven tests generated in under sixty seconds. From nothing to a complete test suite.
>
> No more manual work. No more guessing. No more maintaining separate documentation."

### Screen Actions

**0:30-0:45** (15s) - Installation & Setup
- Terminal showing:
  ```bash
  $ pip install tracetap
  $ export ANTHROPIC_API_KEY='sk-...'
  ```
- Smooth typing with dark terminal theme (Dracula or similar)
- Text overlay: "Step 1: Install TraceTap"

**0:45-1:00** (15s) - Start capture
- Terminal showing capture command execution:
  ```bash
  $ python tracetap.py --listen 8080 \
    --export captured.json
  ```
- Output showing:
  ```
  [14:32:15] TraceTap HTTP Proxy started
  [14:32:15] Listening on 0.0.0.0:8080
  [14:32:15] Starting traffic capture...
  ```
- Text overlay: "Step 2: Start the Proxy"

**1:00-1:30** (30s) - API calls flowing in
- Split screen:
  - LEFT: Simple Node/Python app making API requests (use curl in loop)
  - RIGHT: Terminal showing real-time capture output:
    ```
    [14:32:20] GET https://api.example.com/users → 200 (45ms)
    [14:32:21] POST https://api.example.com/users → 201 (120ms)
    [14:32:22] GET https://api.example.com/users/1/posts → 200 (32ms)
    [14:32:23] PATCH https://api.example.com/users/1 → 200 (55ms)
    [14:32:24] DELETE https://api.example.com/users/2 → 204 (40ms)
    ```
- Counter showing: "📊 5 requests captured"
- Text overlay: "Step 3: Make API Calls (TraceTap Records)"

**1:30-1:50** (20s) - Generate tests
- Terminal showing AI generation:
  ```bash
  $ tracetap-ai-postman.py captured.json \
    -o postman-collection.json

  [14:32:30] Analyzing traffic...
  [14:32:35] Inferring request flows...
  [14:32:40] Generating Postman collection...
  ✓ Generated postman-collection.json
  ```
- VS Code opens showing generated `test_api_calls.py` file:
  - Test functions with clear names
  - Assertions checking status codes and response fields
  - Highlighted: "47 tests generated"
- Text overlay: "Step 4: Generate Tests (AI-Powered)"

**1:50-2:10** (20s) - Show generated artifacts
- File explorer showing generated files:
  ```
  project/
  ├── captured.json
  ├── postman-collection.json
  ├── test_api_calls.py
  ├── wiremock-stubs.json
  └── contract.yaml
  ```
- Each file appears with a label:
  - "✓ Postman Collection - Ready to import"
  - "✓ Pytest Tests - Run immediately"
  - "✓ WireMock Stubs - Mock your API"
  - "✓ Contract Spec - Prevent breaking changes"
- Text overlay: "Everything Generated. Everything Ready."

**2:10-2:30** (20s) - Speed comparison
- Before/After comparison graphic:
  ```
  BEFORE (Manual)         AFTER (TraceTap)
  ─────────────────────────────────────
  Write tests:    2 hours     Captured:    60 seconds
  Create mocks:   1 hour      Postman:     10 seconds
  Docs:           1.5 hours   Generated:   5 seconds
  ─────────────────────────────────────
  Total:          4.5 hours   Total:       75 seconds
  ```
- Pulsing text: "4.5 hours → 75 seconds"

### Technical Setup Required

- Sample API running (Node/Python app making requests via proxy)
- Terminal with proper styling (dark theme, 16pt+ font, 100 chars wide)
- VS Code with Python extension (for code highlighting)
- All commands pre-tested and timed

---

## SEGMENT 3: MAGIC
**Duration:** 2 minutes (120 seconds) | **Time:** 2:30-4:30

### Narration Script

> "But here's where it gets interesting. TraceTap doesn't just capture traffic. It understands your API.
>
> It uses AI to find gaps in your testing. It suggests test cases you might have missed. It spots potential issues before they become production problems.
>
> [PAUSE] Watch this.
>
> See how TraceTap analyzed your captures and suggested additional test cases? Cases for edge cases you didn't even think of. Error scenarios. Boundary conditions.
>
> That's the power of AI-driven testing. You're not just testing what you did—you're testing what could go wrong.
>
> Now let's talk about contract testing. In microservices, breaking changes are silent killers. Service A breaks because Service B changed their API. Nobody saw it coming.
>
> TraceTap creates contracts automatically. These are agreements between services about what the API looks like. You run these contracts in CI/CD. Breaking changes get caught in seconds, before they reach production.
>
> Same contract that prevented the breaking change? It also serves as living API documentation. Always accurate. Always up-to-date. No manual updates needed.
>
> This is modern testing. Intelligent. Automated. Preventive."

### Screen Actions

**2:30-3:00** (30s) - AI Test Suggestions Feature
- Browser window showing AI analysis results:
  - Title: "AI Test Gap Analysis"
  - Shows JSON of captured requests
  - Below: "Suggested Test Cases"
- Animated list appearing:
  ```
  ✓ Test: Missing authentication scenarios (Bearer token expiration)
  ✓ Test: Boundary testing - test with max/min field values
  ✓ Test: Test error responses (500, 503, rate limiting)
  ✓ Test: Test with invalid data types
  ✓ Test: Test concurrent requests (race conditions)
  ✓ Test: Test with malformed JSON
  ```
- Each suggestion appears with a "+" button to add to test suite
- Text overlay: "AI Identifies Test Gaps"
- Narrator emphasizes: "47 tests became 95 tests—all the important ones"

**3:00-3:30** (30s) - Contract Testing Demo
- Terminal showing contract verification:
  ```bash
  $ tracetap-contract-verify.py captured.json

  [14:35:10] Verifying contract: user-service-contract.yaml
  [14:35:11] ✓ GET /users returns {id, name, email, created_at}
  [14:35:12] ✓ POST /users accepts {name, email, password}
  [14:35:13] ✓ DELETE /users/{id} returns 204
  [14:35:14] ✓ Error responses include error_code and message

  ✅ Contract verification: PASSED
  All 12 endpoints verified. No breaking changes detected.
  ```
- Text overlay: "Contract Verification: PASSED"
- Split screen also showing:
  - LEFT: Service B about to deploy (deploy screen)
  - RIGHT: CI/CD pipeline running contract checks
  - Result: Green checkmark or Red X
- Narrator emphasizes: "Catch breaking changes before production"

**3:30-4:00** (30s) - Living Documentation
- VS Code showing generated contract file:
  ```yaml
  endpoints:
    - path: /users/{id}
      method: GET
      description: "Retrieve a single user by ID"
      response:
        type: object
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
- Browser showing OpenAPI/Swagger documentation auto-generated
- Text overlay: "OpenAPI Spec Generated Automatically"
- Narrator emphasizes: "Documentation that never goes stale"

**4:00-4:30** (30s) - Real-world impact montage
- Quick sequence of screens (3-4 seconds each):
  1. Developer working late → Now working on time (crossed out clock)
  2. Bug in production → Bug caught in CI (green checkmark)
  3. Frustrated team → Happy team (celebration emoji)
  4. Pile of documents → Single unified spec
  5. Duplicate work → Automated work
- Text overlays appearing:
  - "Ship with confidence"
  - "Tests run automatically"
  - "Zero manual documentation"
  - "Break changes caught instantly"
  - "Your team ships faster"
- Soft background music swelling

### Technical Setup Required

- Generate sample contract file (YAML or JSON)
- Prepare AI suggestions output (screenshot or live if API available)
- Pre-generate contract verification output
- Prepare OpenAPI/Swagger spec file
- Background music (royalty-free, tech-focused)

---

## SEGMENT 4: CALL TO ACTION
**Duration:** 30 seconds | **Time:** 4:30-5:00

### Narration Script

> "Ready to stop wasting time on manual testing?
>
> TraceTap is open source and free. Get started right now with one command.
>
> [PAUSE] Visit the GitHub repo for complete documentation, examples, and tutorials.
>
> Your next great test suite is just one capture away."

### Screen Actions

**4:30-4:45** (15s) - Installation CTA
- Terminal showing quick install:
  ```bash
  $ npm install -g tracetap
  $ tracetap --help
  ```
  OR
  ```bash
  $ pip install tracetap
  $ python tracetap.py --help
  ```
- Text overlay with animated typing:
  "Get Started Now"

**4:45-5:00** (15s) - Links & Resources
- Split screen ending:
  - LEFT: GitHub logo + "github.com/VassilisSoum/tracetap"
  - RIGHT: "Read the docs → docs.tracetap.dev"
  - BOTTOM: Twitter/LinkedIn social handles
- Final slide with:
  - "TraceTap: Intelligent API Testing"
  - "Open Source • Free • Production Ready"
  - Bouncing cursor animation
  - Fade to black with "Thank you" text

### Technical Setup Required

- GitHub repo link (clickable/visible)
- Documentation website URL
- Social media handles

---

## Timing Summary

| Segment | Duration | Content |
|---------|----------|---------|
| Problem | 0:30 | Pain points, motivation |
| Solution | 2:00 | Installation, capture, generation, speed |
| Magic | 2:00 | AI suggestions, contracts, docs |
| CTA | 0:30 | Installation, links |
| **TOTAL** | **4:30** | Complete demo |

---

## Script Delivery Tips

### Pacing
- Speak at natural pace (not rushed)
- Pause after key points for emphasis
- Let silence sit during visual demos (let the screens speak)
- Speed up slightly during "boring" technical parts

### Emphasis Keywords
Bold these words slightly when narrating:
- **one command**
- **instantly**
- **AI-powered**
- **everything you need**
- **no more manual work**
- **catch breaking changes**
- **open source**
- **free**

### Voice Characteristics
- Professional but friendly tone
- Conversational, not stiff
- Clear enunciation (especially for technical terms)
- Energetic but not hyper
- Warm and confident

### What NOT to Do
- Don't rush through the Solution segment (it's the longest)
- Don't spend too much time on installation details
- Don't use jargon without explaining it briefly
- Don't make promises the tool can't keep
- Don't sound "salesy" - let the product speak for itself

---

## Notes for Production

### Approval Steps
- [ ] Narrator records audio first
- [ ] Rough cut with narration (no final transitions)
- [ ] Get feedback on messaging and timing
- [ ] Record demo screens with approved narration
- [ ] Final edit and color correction
- [ ] Add captions/subtitles (WCAG compliant)
- [ ] A/B test thumbnail before publishing

### Post-Production Checklist
- [ ] Audio levels normalized (-3dB to -1dB)
- [ ] Video at 1080p or higher (YouTube recommended)
- [ ] Captions in English (SRT file)
- [ ] Intro sequence (5 seconds)
- [ ] Outro sequence (3 seconds)
- [ ] Smooth transitions (0.5s cross fades)
- [ ] Background music levels (not overpowering)
- [ ] Text overlays readable (contrast ratio >4.5:1)

---

## Alternative Script Variations

### Longer Version (5-6 minutes)
Add a full "Before & After" case study showing:
- Real testing challenge
- How it was solved before
- How TraceTap solves it
- Metrics/impact

### Shorter Version (2-3 minutes)
Remove AI suggestions and contract testing deep dive, focus only on:
- Problem
- Installation & capture
- Generated artifacts
- CTA

### Enterprise Version
Replace some technical language with business value:
- "reduce testing time by 80%"
- "ship with confidence"
- "eliminate manual test case writing"
- Focus on team productivity and cost savings
