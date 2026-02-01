# TraceTap Task Management Guide

This guide explains how to manage the 32 transformation tasks using both the JSON export and Claude Code's task system.

## Task Files

- **`tracetap-tasks.json`** - Complete task export in JIRA-like format
- **Claude Code Tasks** - Internal task tracking (use TaskUpdate, TaskList, TaskGet)

## Status Mapping

| JSON Status | Claude Code Status | Meaning |
|-------------|-------------------|---------|
| `PENDING` | `pending` | Task not started yet |
| `IN-PROGRESS` | `in_progress` | Currently being worked on |
| `COMPLETED` | `completed` | Task finished and verified |

## Working with Tasks

### 1. View All Tasks

```bash
# In Claude Code
Use TaskList tool to see all tasks
```

Example output:
```
#7  [pending] Create regression generator core engine
#11 [pending] Implement AI pattern analyzer
#15 [pending] Implement contract creator from traffic
...
```

### 2. Start Working on a Task

When you begin work on a task, update it to IN-PROGRESS:

```bash
# In Claude Code
TaskUpdate(taskId="7", status="in_progress")
```

**JSON equivalent:**
```json
{
  "id": "7",
  "status": "IN-PROGRESS"
}
```

### 3. Complete a Task

When you finish a task, mark it COMPLETED:

```bash
# In Claude Code
TaskUpdate(taskId="7", status="completed")
```

**JSON equivalent:**
```json
{
  "id": "7",
  "status": "COMPLETED"
}
```

### 4. Check Task Dependencies

Before starting a task, check if it's blocked:

```bash
# In Claude Code
TaskGet(taskId="8")
```

Output shows:
```
Blocked by: #7
Blocks: #9, #10
```

**Rule:** Only start tasks that have no blockedBy dependencies, or where all blocking tasks are completed.

## Recommended Workflow

### Week-by-Week Execution

**Week 1-2: Installation & Quick Start** (Tasks #1-6)
1. Start with #1, #2, #3, #4 (parallel - no dependencies)
2. Then #5 (quickstart CLI)
3. Then #6 (HTML reporter)

```bash
# Mark as in-progress when starting
TaskUpdate(taskId="1", status="in_progress")

# Mark as completed when done
TaskUpdate(taskId="1", status="completed")
```

**Week 3-4: Snapshot Regression** (Tasks #7-10)
1. Start #7 (regression core) - CRITICAL PATH
2. When #7 done → start #8 (assertion builder)
3. When #7 & #8 done → start #9 (CLI integration)
4. When all done → start #10 (tests)

**Week 5-6: AI Test Suggestions** (Tasks #11-14)
1. Start #11 (pattern analyzer) - CRITICAL PATH
2. When #11 done → start #12 (test suggester)
3. When #11 & #12 done → start #13 (CLI)
4. When all done → start #14 (tests)

**Week 7-8: Contract Guardian** (Tasks #15-19, #30)
1. Start #15 (contract creator) - CRITICAL PATH
2. When #15 done → start #16 (verifier)
3. When #15 & #16 done → start #17 (CLI)
4. When #17 done → start #18 (GitHub Action)
5. When #15, #16, #17 done → start #19 (tests)
6. Start #30 anytime (integration templates)

**Week 9: Marketing Assets** (Tasks #20-22, #24)
1. When #10, #14, #19 done → start #20 (demo video)
2. When #10, #14, #19 done → start #24 (GIFs)
3. Start #21 anytime (docs overhaul)
4. When #20 & #24 done → start #22 (README)

**Week 10: Community** (Tasks #23, #27-28)
1. When #10, #14, #19 done → start #23 (examples)
2. Start #27 anytime (GitHub setup)
3. When #20, #22, #24 done → start #28 (launch content)

**Week 11-12: Polish & Launch** (Tasks #25-26, #31-32, #29)
1. Start #25, #26 anytime (UX polish)
2. When #10, #14, #19, #22, #23, #26 done → start #31 (testing)
3. Start #32 anytime (metrics)
4. When #28 & #31 done → start #29 (LAUNCH!)

## Critical Path (Must Complete for Launch)

These tasks MUST be completed in order for successful launch:

```
#7 → #8 → #9 → #10 (Regression Generator)
                  ↓
#11 → #12 → #13 → #14 (AI Suggestions)
                  ↓
#15 → #16 → #17 → #19 (Contract Guardian)
                  ↓
#20, #24 (Demo Video & GIFs)
    ↓
#22 (README)
    ↓
#28 (Launch Content)
    ↓
#31 (Pre-launch Testing)
    ↓
#29 (LAUNCH!)
```

## Tracking Progress

### Daily Status Check

```bash
# View all pending tasks
TaskList

# Get details on specific task
TaskGet(taskId="7")
```

### Weekly Report

Count tasks by status:
- **Pending**: Not started
- **In Progress**: Currently working
- **Completed**: Done

**Target pace:**
- Week 4: ~10 tasks completed (Month 1 foundation)
- Week 8: ~20 tasks completed (Month 2 differentiation)
- Week 12: ~32 tasks completed (Month 3 launch)

## Task Metadata Reference

Each task includes metadata for filtering and organization:

```json
{
  "phase": "Month 1: Foundation | Month 2: Differentiation | Month 3: Awareness",
  "week": "1-2 | 3-4 | 5-6 | 7-8 | 9 | 10 | 11 | 11-12 | 12",
  "priority": "low | medium | high | critical",
  "complexity": "low | medium | high",
  "feature": "regression-generator | ai-suggestions | contract-guardian",
  "category": "installation | quickstart | documentation | marketing | ux-polish | community | launch | integrations | analytics"
}
```

## Quick Reference Commands

```bash
# List all tasks
TaskList

# Get task details
TaskGet(taskId="7")

# Start working on task
TaskUpdate(taskId="7", status="in_progress")

# Complete task
TaskUpdate(taskId="7", status="completed")

# Add custom metadata
TaskUpdate(taskId="7", metadata={"assignee": "your-name", "notes": "custom note"})
```

## Tips

1. **Work in parallel where possible**: Tasks #1-6 can all be done simultaneously
2. **Focus on critical path first**: Tasks #7-19 are the killer features
3. **Don't skip testing**: Tasks #10, #14, #19 ensure quality
4. **Marketing matters**: Allocate enough time for tasks #20-28
5. **Test before launch**: Task #31 is critical - don't rush it

## Exporting Updated Status

To re-export tasks with current status:

1. Update tasks in Claude Code using TaskUpdate
2. Run a script to read current statuses and regenerate JSON
3. Or manually update `tracetap-tasks.json` as you go

## Integration with External Tools

The JSON format is compatible with:
- **JIRA**: Import as bulk issues
- **Trello**: Convert to cards
- **GitHub Projects**: Create issues from JSON
- **Asana**: Import tasks
- **Monday.com**: Bulk task creation

## Status Summary Template

Copy this for weekly updates:

```
## Week X Status Report

**Completed (COMPLETED):** X tasks
- #1: Create one-line installer script ✓
- #2: Build optimized Docker image ✓

**In Progress (IN-PROGRESS):** X tasks
- #7: Create regression generator core engine 🔄

**Pending (PENDING):** X tasks
- #8: Build assertion builder
- #9: Integrate regression generator into CLI

**Blockers:** None / List any blockers

**Next Week Focus:**
- Complete #7
- Start #8, #9
```

---

**Last Updated:** 2026-02-01
**Total Tasks:** 32
**Current Status:** All tasks PENDING (ready to start!)
