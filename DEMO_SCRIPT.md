# TraceTap 2.0 Demo Video Script

**Duration:** 3 minutes
**Target Audience:** QA engineers, development teams
**Platform:** YouTube, Twitter, LinkedIn

---

## Opening (0:00-0:15)

**Voiceover:**
"Meet TraceTap 2.0 - the world's first tool that records your manual tests and generates Playwright code with AI."

**Screen:**
- Show TraceTap logo with animation
- Subtitle: "Record → Capture → Generate"
- Clean, professional typography

---

## Problem Statement (0:15-0:30)

**Voiceover:**
"Writing Playwright tests manually takes hours. You need to write selectors, add assertions, handle timing, and test edge cases."

**Screen:**
- Show developer hunched over desk writing test code
- Code editor showing boilerplate test code
- Clock ticking in corner
- Text overlay: "5-7 hours per test"
- Frustrated expression (stock footage or animation)

---

## Solution Intro (0:30-1:00)

**Voiceover:**
"With TraceTap, you just interact with your app normally. TraceTap records everything - your clicks, your typing, and all the API calls your app makes."

**Screen:**
- Terminal: `tracetap record https://demo.playwright.dev/todomvc/ -n demo`
- Browser opens automatically to TodoMVC
- User cursor visible
- User adds a todo item
- User completes the todo
- User filters todos
- Show real-time recording stats appearing (event count: 8, API calls: 4, etc.)
- Chat bubble: "Recording in progress..."

---

## The Magic Moment (1:00-1:30)

**Voiceover:**
"Then, Claude AI analyzes your recording and generates production-ready Playwright tests in seconds."

**Screen:**
- Terminal: `tracetap-generate-tests recordings/demo -o tests/demo.spec.ts`
- Show loading bar / progress indicator
- AI thinking animation (optional: Claude brain icon)
- Progress text: "Analyzing events..." → "Correlating API calls..." → "Generating tests..."
- File appears: `tests/demo.spec.ts`
- Code editor shows generated test with syntax highlighting
- Highlight key parts:
  - Import statements
  - Test description
  - UI action assertions
  - API response assertions
  - Comments explaining correlations

---

## Results & Execution (1:30-2:00)

**Voiceover:**
"Run your tests immediately. No manual coding required."

**Screen:**
- Terminal: `npx playwright test tests/demo.spec.ts`
- Show test execution in progress
- Each test case passing with green checkmark
- Summary: "3 passed (1.2s)"
- Show test timeline with passed indicators
- Celebration animation (optional confetti)

---

## Key Features Highlight (2:00-2:30)

**Voiceover:**
"TraceTap captures UI interactions, network traffic, and generates comprehensive tests with edge cases you might not think of."

**Screen:**
- **Split screen 1 (left):** Browser with user clicking buttons
- **Split screen 2 (right):** Network inspector showing correlated API calls
- Connector lines showing correlation between clicks and API calls
- Show confidence score badge: "92% confidence"
- Comparison table:
  - Before: Manual writing 5-7 hours
  - After: Record 10min + Generate 30sec = 10.5 minutes total
  - Badge: "95% faster"

---

## Call to Action (2:30-3:00)

**Voiceover:**
"Stop spending hours writing tests manually. Start with TraceTap 2.0 today."

**Screen:**
- Show installation command with copy-to-clipboard animation:
  ```bash
  pip install tracetap --upgrade
  ```
- Show GitHub link with icon
- Button: "Try it now →"
- Social proof: Display 3 testimonials in rotating cards:
  1. "20 minutes for 15 comprehensive tests" - QA Engineer
  2. "20% → 80% test coverage in 2 weeks" - Engineering Manager
  3. "AI catches edge cases we never thought of" - Senior QA

**End Card (2:50-3:00):**
- Large TraceTap logo
- Version badge: "v2.0"
- Text: "github.com/anthropics/tracetap"
- Button: "Start automating today"
- Music fades out smoothly

---

## Technical Specifications

### Video Properties
- **Resolution:** 1920x1080 (16:9)
- **Frame Rate:** 60 fps
- **Codec:** H.264
- **Audio:** 48kHz stereo
- **Background Music:** Upbeat but professional
- **Voice:** Clear, friendly narrator

### Screen Recording Tips
1. Use maximum screen resolution (1920x1080 or higher)
2. Maximize editor and terminal windows
3. Set font size to 18pt+ for readability
4. Clear any sensitive information from screenshots
5. Slow down terminal output for clarity (can speed up in video editing)

### UI Animations
- Use fade transitions between sections
- Highlight text/code with subtle animations
- Progress bars should move smoothly
- Code should syntax-highlight in real-time
- Checkmarks should appear with satisfying bounce

### Music & Sound
- Upbeat but not distracting background music
- Clear voiceover without music overlap
- Sound effects:
  - Subtle "ding" when test passes
  - Typewriter sound for code generation (optional)
  - Satisfying "whoosh" for transitions

---

## Script Timing Reference

| Section | Start | Duration | Notes |
|---------|-------|----------|-------|
| Opening | 0:00 | 15s | Logo animation + subtitle |
| Problem | 0:15 | 15s | Developer struggling |
| Solution | 0:30 | 30s | Recording in action |
| Magic | 1:00 | 30s | AI generation moment |
| Results | 1:30 | 30s | Tests running + passing |
| Features | 2:00 | 30s | Split screen comparison |
| Call to Action | 2:30 | 30s | Installation + testimonials |

---

## Alternative Shorter Version (1 minute)

If a 60-second version is needed:

1. **Opening (0-10s):** Logo + subtitle
2. **Problem (10-15s):** Developer writing tests (5 seconds)
3. **Solution (15-40s):** Record + generate (25 seconds)
4. **Results (40-50s):** Tests passing (10 seconds)
5. **CTA (50-60s):** GitHub link + install command (10 seconds)

---

## Social Media Versions

### Twitter/X (15 seconds)
Focus: Recording → Generation → Passing tests
Remove: Problem statement, testimonials, features
Add: Text overlay: "95% faster test writing"

### LinkedIn (30 seconds)
Focus: QA engineering workflow improvement
Add: Testimonial quote
Remove: Some technical details
Emphasize: Time savings for teams

### Facebook (45 seconds)
Focus: Ease of use
Add: More visual feedback
Remove: Technical jargon
Emphasize: "Anyone can do this"

---

## Accessibility Notes

- Provide captions for all dialogue
- Describe visual elements for screen readers
- Use high-contrast colors for text/code
- Avoid flashing animations (risk of photosensitive seizures)
- Provide transcript in video description

---

## Production Checklist

- [ ] Record actual screen capture of demo flow
- [ ] Get voice recording from professional narrator
- [ ] Generate/license royalty-free background music
- [ ] Create opening animation/logo treatment
- [ ] Add all text overlays and timing
- [ ] Color correct and enhance video
- [ ] Add captions/subtitles
- [ ] Create thumbnail image
- [ ] Write video description with links
- [ ] Test on YouTube, Twitter, LinkedIn
- [ ] Get accessibility review
- [ ] Final QA pass

---

## Content Notes

**Key Messages:**
1. TraceTap is world-first (UI + API + AI)
2. 95% faster than manual writing
3. Production-ready immediately
4. No special skills required
5. Works with existing tools (Playwright)

**Avoid:**
- Technical jargon without explanation
- Showing failed tests
- Showing error messages
- Credential exposure (API keys, etc.)
- Platform-specific features only (Linux, etc.)

**Emphasize:**
- Time savings
- Quality improvements
- Ease of use
- Real-world results
- Community adoption
