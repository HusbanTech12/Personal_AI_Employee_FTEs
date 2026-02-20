# Hackathon Demo Mode

## Quick Start Guide

Welcome to the AI Employee Vault demo! This guide walks you through the complete task automation workflow.

---

## What You'll See

This demo showcases a **Bronze Tier AI Employee** that:

- ✅ Watches for new tasks automatically
- ✅ Classifies and routes tasks through workflows
- ✅ Logs all activity
- ✅ Updates a live dashboard
- ✅ Processes tasks by priority

---

## Demo Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   INBOX     │ ──→ │ NEEDS_      │ ──→ │   PROCESS   │ ──→ │    DONE     │
│ (Add Task)  │     │ ACTION      │     │  (AI Work)  │     │ (Complete)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   LOGS      │     │  DASHBOARD  │
                    │ (Activity)  │     │  (Metrics)  │
                    └─────────────┘     └─────────────┘
```

---

## Step-by-Step Demo

### Step 1: Start the Filesystem Watcher

Open a terminal in the vault directory and run:

```bash
# Activate virtual environment (if needed)
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Start the watcher
python filesystem_watcher.py
```

**Expected Output:**
```
============================================================
AI Employee Filesystem Watcher (Bronze Tier)
============================================================
Base Directory: D:\Quarter_4\Hackathon_0\AI_Employee_Vault
Monitoring: D:\Quarter_4\Hackathon_0\AI_Employee_Vault\Inbox
Press Ctrl+C to stop
============================================================
Directory verified: ...\Inbox
Directory verified: ...\Needs_Action
Directory verified: ...\Logs
Filesystem watcher started successfully
```

> **Keep this terminal open** - the watcher runs continuously!

---

### Step 2: Add a Task to Inbox

**Option A: Use the Template**

1. Copy `Inbox/TASK_TEMPLATE.md`
2. Rename to `Inbox/demo_task_001.md`
3. Fill in the frontmatter:

```markdown
---
title: Demo Task - Generate Report
status: inbox
priority: standard
created: 2026-02-20
skill: task_processor
---

## Description

Generate a summary report of the Q4 hackathon progress.

## Expected Output

- 500-word summary document
- Key milestones listed
- Next steps outlined

## Notes

This is a demo task for the hackathon presentation.
```

**Option B: Create a Simple Task**

Create any `.md` file in `Inbox/`:

```bash
# Example: Create a demo task
echo "# Demo Task

This is a test task for the hackathon demo.

## Description
Process this task and confirm completion.

## Expected Output
Confirmation message in Notes section.
" > Inbox/demo_task_001.md
```

---

### Step 3: Watcher Activates (Automatic)

Within **1-2 seconds**, the watcher detects the new file:

**Terminal Output:**
```
2026-02-20 10:30:00 - INFO - New file detected: demo_task_001.md
2026-02-20 10:30:01 - INFO - Added missing metadata to: demo_task_001.md
2026-02-20 10:30:01 - INFO - Copied to Needs_Action: demo_task_001.md
2026-02-20 10:30:01 - INFO - Activity log updated: demo_task_001.md
2026-02-20 10:30:01 - INFO - Dashboard updated successfully
2026-02-20 10:30:01 - INFO - Successfully processed: demo_task_001.md
```

---

### Step 4: Task Moves Automatically

**Check the folders:**

| Folder | Expected Content |
|--------|------------------|
| `Inbox/` | Original `demo_task_001.md` (preserved) |
| `Needs_Action/` | Copy of `demo_task_001.md` (ready for processing) |

**The watcher:**
- Reads the task
- Adds missing metadata (if any)
- Copies to `Needs_Action/`
- **Never deletes** the original

---

### Step 5: Logs Generated

**Check `Logs/activity_log.md`:**

```
timestamp             | action  | file             | status
----------------------|---------|------------------|----------
2026-02-20 10:30:01   | created | demo_task_001.md | inbox
```

**Check `Logs/watcher_2026-02-20.log`:**

```
2026-02-20 10:30:00 - INFO - New file detected: demo_task_001.md
2026-02-20 10:30:01 - INFO - Copied to Needs_Action: demo_task_001.md
2026-02-20 10:30:01 - INFO - Activity log updated: demo_task_001.md
2026-02-20 10:30:01 - INFO - Dashboard updated successfully
```

---

### Step 6: Dashboard Updated

**Open `Dashboard.md` and check:**

**Metrics Section:**
```markdown
| Metric            | Value |
|-------------------|-------|
| Inbox Tasks Count | `1`   |
| Needs_Action Tasks| `1`   |
| Completed Tasks   | `0`   |
| Watcher Status    | `ACTIVE` |
| Last Activity     | `2026-02-20 10:30:01` |
```

**Pending Tasks Section:**
```markdown
- [ ] `demo_task_001.md` - Added: 2026-02-20 10:30:01
```

---

## Demo Scenarios

### Scenario 1: Priority Handling

Create an urgent task:

```markdown
---
title: URGENT - System Alert
status: inbox
priority: urgent
created: 2026-02-20
---

## Description

Critical system check required immediately.

## Expected Output

Confirmation of system status.
```

**Watch:** Urgent tasks are processed first!

---

### Scenario 2: Multiple Tasks

Add 3 tasks in quick succession:

```bash
echo "# Task A" > Inbox/task_a.md
echo "# Task B" > Inbox/task_b.md
echo "# Task C" > Inbox/task_c.md
```

**Watch:** Dashboard counts increment with each task!

---

### Scenario 3: AI Processing Demo

**Manual AI Processing Steps:**

1. Open `Needs_Action/demo_task_001.md`
2. Read the task
3. Execute the work (generate output)
4. Add completion notes:

```markdown
## Notes

✅ **Completed:** 2026-02-20 10:35:00
✅ Report generated successfully
✅ All milestones documented
```

5. Move file to `Done/` folder
6. Update activity log:

```
2026-02-20 10:35:00 | completed | demo_task_001.md | done
```

7. Update Dashboard metrics

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not starting | Check `pip install watchdog` |
| Task not detected | Ensure file is `.md` extension |
| Dashboard not updating | Check file permissions |
| Errors in logs | Review `Logs/error_*.md` files |

---

## Demo Checklist

Use this during your presentation:

- [ ] Watcher terminal running
- [ ] `Inbox/TASK_TEMPLATE.md` visible
- [ ] `Dashboard.md` open (showing initial state)
- [ ] `Logs/activity_log.md` open
- [ ] Create new task in `Inbox/`
- [ ] Show terminal detection output
- [ ] Show file in `Needs_Action/`
- [ ] Show updated activity log
- [ ] Show updated dashboard metrics
- [ ] (Optional) Manually complete a task
- [ ] Show task in `Done/` folder

---

## Files Reference

| File | Purpose |
|------|---------|
| `filesystem_watcher.py` | Main automation script |
| `Inbox/TASK_TEMPLATE.md` | Blank task template |
| `Dashboard.md` | Live metrics display |
| `Logs/activity_log.md` | All operations logged |
| `Company_Handbook.md` | AI Employee rules |
| `Needs_Action/AI_PROCESSING.md` | Processing rules |

---

## Next Steps

After the demo:

1. Review `Company_Handbook.md` for AI rules
2. Read `Needs_Action/AI_PROCESSING.md` for task selection logic
3. Explore `Skills/task_processor.SKILL.md` for capabilities
4. Customize templates for your use case

---

**Demo Version:** 1.0 | **Tier:** Bronze | **Hackathon:** 2026-Q4
