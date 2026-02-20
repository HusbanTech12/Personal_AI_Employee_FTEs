# START HERE

## AI Employee Vault - Hackathon Demo

**Welcome!** This is your Bronze Tier AI Employee automation system.

---

## 🚀 60-Second Demo

### Run in Order:

```
1. Open terminal → python filesystem_watcher.py
2. Copy Inbox/TASK_TEMPLATE.md → Inbox/my_first_task.md
3. Watch the magic happen! ✨
```

---

## What Just Happened?

```
You added task → Watcher detected → Copied to Needs_Action → Logged → Dashboard updated
```

**Real-time automation** - no manual intervention required!

---

## Folder Structure

| Folder | Purpose | You Should |
|--------|---------|------------|
| 📥 `Inbox/` | New tasks arrive here | Add tasks here |
| 📋 `Needs_Action/` | AI processes these | Watch AI work |
| ✅ `Done/` | Completed tasks | Review results |
| 📊 `Logs/` | Activity records | Check for debugging |
| 🛠️ `Skills/` | AI capabilities | Read to understand |

---

## Quick Reference

### Start Watcher
```bash
python filesystem_watcher.py
```

### Stop Watcher
```
Press Ctrl+C
```

### Create Task
1. Copy `Inbox/TASK_TEMPLATE.md`
2. Fill in your task
3. Save in `Inbox/`

### View Logs
- Activity: `Logs/activity_log.md`
- Errors: `Logs/error_*.md`
- Watcher: `Logs/watcher_*.log`

### Check Dashboard
Open `Dashboard.md` - updates automatically!

---

## Demo Script (For Presentations)

**1. Show Initial State**
- Open `Dashboard.md` - show current metrics
- Open `Logs/activity_log.md` - show log format

**2. Start the Engine**
```bash
python filesystem_watcher.py
```
- Show terminal output

**3. Add a Task**
- Create `Inbox/demo_presentation.md`
- Use template or quick create

**4. Watch Automation**
- Terminal shows detection
- File appears in `Needs_Action/`
- Activity log updates
- Dashboard metrics change

**5. Explain the Magic**
- Watcher uses `watchdog` library
- Metadata auto-populated
- Priority-based processing
- Full audit trail

**6. Show AI Processing** (Manual demo)
- Open task in `Needs_Action/`
- Generate output
- Move to `Done/`
- Log completion

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Auto-Detection** | New files detected within 1 second |
| 📝 **Metadata Injection** | Missing fields auto-populated |
| 🎯 **Priority Queue** | Urgent tasks processed first |
| 📊 **Live Dashboard** | Real-time metrics updates |
| 📜 **Full Logging** | Every action recorded |
| 🛡️ **Safe Operations** | Originals preserved, never deleted |

---

## File Overview

| File | What It Does |
|------|--------------|
| `filesystem_watcher.py` | Main automation - watches Inbox folder |
| `DEMO_TASK.md` | Detailed demo walkthrough |
| `Company_Handbook.md` | AI Employee operating rules |
| `Dashboard.md` | Live status display |

---

## Requirements

```bash
pip install watchdog
```

That's it! One dependency for full automation.

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `python filesystem_watcher.py` | Start automation |
| `Ctrl+C` | Stop automation |
| `ls Inbox/` | View pending tasks |
| `ls Needs_Action/` | View active queue |
| `ls Done/` | View completed work |

---

## Your First Task Template

```markdown
---
title: My First AI Task
status: inbox
priority: standard
created: 2026-02-20
skill: task_processor
---

## Description

What do you want the AI to do?

## Expected Output

What should the AI produce?

## Notes

Any additional context or requirements.
```

---

## Learning Path

```
START_HERE.md     ← You are here
    ↓
DEMO_TASK.md      ← Detailed walkthrough
    ↓
Company_Handbook.md ← AI rules & behavior
    ↓
AI_PROCESSING.md  ← How AI selects tasks
    ↓
task_processor.SKILL.md ← Technical spec
```

---

## Support

| Need | Check |
|------|-------|
| Watcher won't start | `pip install watchdog` |
| Task not detected | File must be `.md` |
| Dashboard not updating | Check file permissions |
| Errors occurring | Review `Logs/error_*.md` |

---

## Ready to Begin?

```bash
# Step 1: Start watcher
python filesystem_watcher.py

# Step 2: In another terminal or file explorer
# Copy Inbox/TASK_TEMPLATE.md to Inbox/my_task.md

# Step 3: Watch the automation! 🎉
```

---

**Version:** 1.0 | **Tier:** Bronze | **Status:** Ready for Demo
