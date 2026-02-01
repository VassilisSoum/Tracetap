# TraceTap Demo Video Production

Complete documentation for producing a professional 4-5 minute demo video showcasing TraceTap's powerful API testing capabilities.

## Quick Start

If you're ready to record right now:

1. **Read the script first:** `/docs/video/demo-script.md`
   - Word-for-word narration with timing
   - Screen actions for each segment
   - Key messages and talking points

2. **Follow the shooting guide:** `/docs/video/shooting-guide.md`
   - Hardware/software requirements
   - Step-by-step recording instructions
   - Terminal commands to execute
   - Post-production workflow

3. **Set up your demo environment** (5 minutes):
   ```bash
   cd ~/tracetap-demo
   git clone https://github.com/VassilisSoum/tracetap.git
   cd tracetap
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt -r requirements-ai.txt
   export ANTHROPIC_API_KEY='your-key'
   ```

4. **Start recording** following the scene-by-scene breakdown

## Files in This Directory

### Primary Documents

- **`demo-script.md`** (4500+ words)
  - Complete narration script for 4:30 video
  - Timing breakdown for each segment
  - Screen actions and visual cues
  - Narrator tips and delivery guidance
  - Alternative script variations

- **`shooting-guide.md`** (8000+ words)
  - Complete technical requirements
  - Hardware and software setup
  - Scene-by-scene recording instructions
  - Terminal commands to execute
  - Sample API code (Node.js and Python)
  - Recording software setup
  - Post-production workflow
  - Publishing checklist
  - Troubleshooting guide

- **`README.md`** (this file)
  - Navigation guide
  - Quick start instructions

## Video Structure

**Total Duration:** 4 minutes 30 seconds

| Segment | Duration | Purpose | Key Metrics |
|---------|----------|---------|------------|
| **1. Problem** | 0:30 | Establish pain point | Manual testing is slow |
| **2. Solution** | 2:00 | Show TraceTap workflow | 47 tests in 60 seconds |
| **3. Magic** | 2:00 | Demonstrate key features | AI, contracts, docs |
| **4. CTA** | 0:30 | Drive action | Install and resources |

## Key Features to Showcase

### Segment 2: The Core Workflow
- One-command proxy startup
- Real-time traffic capture
- AI-powered test generation
- Multiple export formats:
  - Postman collections
  - Pytest test suites
  - WireMock stubs
  - OpenAPI specifications
  - Contract definitions

### Segment 3: The Intelligence
- AI test gap analysis (suggests missing test cases)
- Contract testing (prevent breaking changes in microservices)
- Living documentation (auto-generated from actual traffic)
- Real metrics: 47 captured requests → 95 test cases

## Production Workflow

### Phase 1: Preparation (1-2 hours)
- [ ] Read entire demo-script.md
- [ ] Read entire shooting-guide.md
- [ ] Set up demo environment
- [ ] Prepare API server code
- [ ] Test all demo commands
- [ ] Configure terminal/screen
- [ ] Prepare graphics/overlays (optional)

### Phase 2: Recording (2-3 hours)
- [ ] Record each scene 2-3 times
- [ ] Save multiple takes
- [ ] Record narration (separate audio track)
- [ ] Verify audio quality
- [ ] Take notes on best takes

### Phase 3: Editing (3-5 hours)
- [ ] Assemble best clips in order
- [ ] Sync narration to video
- [ ] Add graphics and overlays
- [ ] Add captions/subtitles
- [ ] Color correction
- [ ] Background music
- [ ] Final export

### Phase 4: Publishing (1-2 hours)
- [ ] Upload to YouTube
- [ ] Write description
- [ ] Add tags and metadata
- [ ] Create thumbnail
- [ ] Write social media posts
- [ ] Share across channels

## Essential Files

### Sample API Code
Both files are included in the shooting guide:
- **Node.js + Express** - Recommended for demo
- **Python + Flask** - Alternative

### Key Scripts
- `demo-api-calls.sh` - Makes API calls for capture demo
- Terminal setup for clean, readable output

### Demo Content
- Sample captured traffic (JSON)
- Generated test files (Python)
- Postman collection (JSON)
- Contract definition (YAML)
- OpenAPI specification (YAML)

## Success Criteria

Your demo video is professional when:

- [ ] **Video Quality:** 1920x1080 or higher, sharp text
- [ ] **Audio Quality:** Clear narration, appropriate background music
- [ ] **Pacing:** Natural speaking pace, not rushed
- [ ] **Content:** All key features demonstrated
- [ ] **Timing:** 3:30-5:00 minutes total
- [ ] **Visual Design:** Professional graphics and overlays
- [ ] **Captions:** Accurate subtitles with good contrast
- [ ] **Messaging:** Clear value proposition and CTA

## Key Numbers to Remember

- **47** - Test cases generated from capture
- **60** - Seconds to complete full workflow
- **8** - AI-suggested test gaps
- **4:30** - Total video duration
- **3-5** - Minutes (acceptable range)

## Recording Tips

### Don't Forget
- USB microphone for better audio quality
- Wired network connection (not WiFi)
- 50GB+ free disk space
- Terminal at 16pt+ font size
- API server running before demo

### Common Mistakes to Avoid
- Don't rush through the solution segment (it's the most important)
- Don't use jargon without explaining it
- Don't show personal information (API keys, email addresses)
- Don't include distracting desktop notifications
- Don't make promises the tool can't keep

### Pro Tips
- Record each scene separately for easier editing
- Do multiple takes of important sections
- Record narration separately for better quality
- Test all commands before recording
- Keep a backup of all raw recordings

## Resources Needed

### Tools
- OBS Studio (free) or ScreenFlow (macOS)
- DaVinci Resolve (free) or Adobe Premiere for editing
- Audacity (free) for audio editing

### Content
- TraceTap installation (git clone + setup)
- Sample Node.js API or Flask app
- Demo traffic script (included in guide)
- Terminal emulator with good font options
- VS Code or similar editor

### Time Investment
- **Preparation:** 2 hours
- **Recording:** 2-3 hours (multiple takes)
- **Editing:** 3-5 hours
- **Publishing:** 1-2 hours
- **Total:** 8-13 hours for professional result

## Getting Help

### If You Get Stuck

**Recording Issues?**
- See "Troubleshooting" in shooting-guide.md
- Common problems have solutions provided

**Audio Problems?**
- Check microphone settings section
- Normalize levels in Audacity
- Re-record if audio quality is poor

**Video Quality?**
- Increase font size to 18pt
- Ensure 1920x1080 screen resolution
- Use OBS at 1080p60 for best results

### Questions About Content?

1. Review the demo-script.md for exact wording
2. Check the shooting-guide.md for technical details
3. Follow timing cues precisely
4. Keep narration natural and conversational

## Next Steps After Recording

### Immediate
- [ ] Export raw video files from recording software
- [ ] Organize files by scene
- [ ] Back up all recordings to external drive

### Editing
- [ ] Import into DaVinci Resolve/Premiere
- [ ] Assemble scenes in order
- [ ] Trim and remove mistakes
- [ ] Add titles and transitions
- [ ] Sync narration

### Publishing
- [ ] Create compelling title
- [ ] Write detailed description (with timestamps)
- [ ] Design eye-catching thumbnail
- [ ] Add relevant tags
- [ ] Write social media posts
- [ ] Schedule cross-platform sharing

## Video Variations

### Longer Version (5-6 minutes)
Add a complete case study showing:
- Real testing challenge
- How it was solved before
- How TraceTap solves it
- Metrics and ROI

### Shorter Version (2-3 minutes)
Focus only on:
- Problem statement
- One-minute workflow demo
- Call to action

### Enterprise Version
Replace technical language with business value:
- "Reduce testing time by 80%"
- "Ship with confidence"
- Focus on team productivity

## Distribution Checklist

### YouTube
- [ ] Title (60 chars max)
- [ ] Description with timestamps
- [ ] Tags (10-15 relevant keywords)
- [ ] Thumbnail image
- [ ] Captions (SRT file)
- [ ] Playlist assignment

### Social Media
- [ ] Twitter/X post
- [ ] LinkedIn post
- [ ] Blog post with transcript
- [ ] Email newsletter mention

### Community
- [ ] Share in Reddit communities (r/devops, r/testing, etc.)
- [ ] Submit to Hacker News (optional)
- [ ] Share in relevant Discord/Slack communities
- [ ] Include in project documentation

## Metrics to Track

After publishing, monitor:
- View count
- Watch time
- Audience retention (where people drop off)
- Comments and feedback
- CTR (click-through rate to GitHub)
- Subscriber growth

Use this data to improve future videos.

## Future Videos to Produce

Once you've mastered the demo video:

1. **Feature Deep-Dives**
   - AI Test Suggestions in detail
   - Contract Testing workflows
   - Playwright test generation

2. **Use Case Tutorials**
   - Microservices contract testing
   - E2E testing with Playwright
   - CI/CD integration

3. **User Testimonials**
   - Real developers using TraceTap
   - Before/after metrics
   - Time savings stories

4. **Architecture Explainers**
   - How traffic capture works
   - AI analysis under the hood
   - Contract verification algorithm

## Questions?

Refer to the detailed guides:
- **Demo Script** for what to say and show
- **Shooting Guide** for how to record and edit

Both documents are comprehensive and self-contained.

---

**Created:** February 2025
**Duration:** 4 minutes 30 seconds
**Format:** Professional video for developer audience
**Status:** Ready for production
