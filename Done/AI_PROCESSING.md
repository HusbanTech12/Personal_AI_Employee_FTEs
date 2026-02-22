---
title: AI Processing Rules
status: done
priority: standard
created: 2026-02-20
completed: 2026-02-22 20:30:05
skill: task_processor
---

# AI Processing Rules

## Overview

This document defines how the AI Employee selects, processes, and completes tasks from the `/Needs_Action` queue.

---

## Task Selection

### How AI Selects Next Task

The AI Employee processes tasks using a **priority-based queue system**:

```
1. Scan /Needs_Action for all .md files
2. Read frontmatter metadata from each file
3. Sort by priority and creation timestamp
4. Select highest-priority oldest task
```

**Selection Algorithm:**

| Order | Criteria | Sort Direction |
|-------|----------|----------------|
| 1 | Priority | `urgent` > `high` > `standard` > `low` |
| 2 | Created | Oldest first (ascending) |
| 3 | Status | `needs_action` only |

**Example Query Logic:**
```
SELECT * FROM Needs_Action
WHERE status = 'needs_action'
ORDER BY priority DESC, created ASC
LIMIT 1
```

---

## Priority Handling

### Priority Levels

| Priority | Description | Response Time | Marker |
|----------|-------------|---------------|--------|
| `urgent` | Time-critical, blocking | Immediate | `[URGENT]` |
| `high` | Important, near deadline | Within 1 cycle | `[HIGH]` |
| `standard` | Normal tasks | Queue order | *(default)* |
| `low` | Nice-to-have, no deadline | After higher priorities | `[LOW]` |

### Priority Detection

AI detects priority from:

1. **Frontmatter field:** `priority: urgent`
2. **Content markers:** `[URGENT]`, `[HIGH]`, `[LOW]`
3. **Keywords:** "ASAP", "critical", "optional"

**Precedence:** Frontmatter > Content markers > Keywords > Default

### Priority Escalation

AI may escalate priority when:
- Deadline mentioned and approaching
- Task marked `[REVIEW_REQUIRED]` by human
- Cascading blocker for other tasks

---

## Completion Definition

A task is considered **complete** when ALL criteria are met:

### Completion Criteria Checklist

- [ ] **Expected output delivered** - All requested work products generated
- [ ] **Quality verified** - Output reviewed for accuracy and completeness
- [ ] **Documentation updated** - Activity log entry created
- [ ] **Status changed** - Task frontmatter updated to `status: done`
- [ ] **Dashboard metrics refreshed** - Counts and timestamps updated

### Definition of Done

```
Task Complete = Output Generated + Logged + Moved to Done
```

**Incomplete Task Handling:**
- If criteria not met → Return to queue with notes
- If blocked → Flag with `[BLOCKED]` and reason
- If requires human input → Flag with `[REVIEW_REQUIRED]`

---

## Movement to Done Folder

### Transfer Process

```
┌──────────────────┐    ┌─────────────────┐    ┌─────────────┐
│  Needs_Action    │    │  Validation     │    │   Done      │
│  (Active Task)   │──→ │  (Check Done)   │──→ │ (Archive)   │
└──────────────────┘    └─────────────────┘    └─────────────┘
                               │
                               ▼
                         All criteria
                         met?
```

### Step-by-Step Movement

| Step | Action | Details |
|------|--------|---------|
| 1 | Verify completion | Check all completion criteria |
| 2 | Update frontmatter | Set `status: done`, add `completed: <timestamp>` |
| 3 | Write activity log | `timestamp | completed | <filename> | done` |
| 4 | Move file | Copy to `/Done/`, remove from `/Needs_Action/` |
| 5 | Move metadata | Move `.meta.md` file alongside |
| 6 | Update dashboard | Increment `Completed Tasks`, update `Last Activity` |
| 7 | Clean pending list | Remove from `Pending_Tasks` section |

### Movement Rules

| Rule | Description |
|------|-------------|
| **Never delete** | Always copy, then remove source |
| **Atomic operation** | All steps succeed or none do |
| **Preserve metadata** | `.meta.md` always moves with task |
| **Log everything** | Every movement recorded in activity_log.md |
| **Update dashboard** | Metrics must reflect current state |

### Rollback Procedure

If movement fails mid-operation:

1. **Log the failure** with error details
2. **Restore original location** if file was partially moved
3. **Flag task** with `[ERROR]` for human review
4. **Continue processing** other tasks

---

## Processing Loop

### AI Employee Cycle

```
while True:
    1. Scan Needs_Action folder
    2. Select next task (by priority)
    3. Read task content and metadata
    4. Execute required work
    5. Verify completion criteria
    6. If complete → Move to Done
    7. Log activity
    8. Update dashboard
    9. Repeat
```

### Exit Conditions

AI stops processing when:
- No tasks in `/Needs_Action/`
- All remaining tasks are blocked/waiting
- System receives stop signal

---

## Activity Log Format

Every action recorded in `Logs/activity_log.md`:

```
timestamp            | action    | file              | status
---------------------|-----------|-------------------|------------
2026-02-20 10:30:00  | created   | task_001.md       | inbox
2026-02-20 10:31:00  | selected  | task_001.md       | processing
2026-02-20 10:35:00  | completed | task_001.md       | done
```

**Action Types:**
- `created` - Task entered system
- `selected` - AI began processing
- `completed` - Task finished
- `blocked` - Task cannot proceed
- `moved` - File transferred between folders

---

## Version

- **Document Version:** 1.0
- **Effective Date:** 2026-02-20
- **Applies To:** Bronze Tier AI Employee

---

## Execution Plan

**Objective:** Validate AI processing rules document and archive to Done.

**Required Files:**
- `AI_PROCESSING.md` (this document)
- `Logs/activity_log.md` (for logging)
- `Dashboard.md` (for metrics update)

**Dependencies:** None - documentation validation only

**Steps:**
1. Read and validate document structure
2. Verify all sections are complete
3. Update task status to `in_progress`
4. Move to `In_Progress` folder
5. Validate content completeness
6. Update status to `done`
7. Move to `Done` folder
8. Log activity and update dashboard

---

## Progress Log

- **2026-02-22 20:30:00** - Started execution
- **2026-02-22 20:30:01** - Read and validated document structure
- **2026-02-22 20:30:02** - All sections verified complete
- **2026-02-22 20:30:03** - Content validation passed
- **2026-02-22 20:30:04** - Frontmatter updated with status: done
- **2026-02-22 20:30:05** - Ready to move to Done folder

---

## Completion Summary

**What was done:**
- Validated AI Processing Rules document structure
- Confirmed all sections are complete and well-formed
- Document serves as the official rules for AI Employee task processing

**Verification:**
- ✅ Task selection algorithm documented
- ✅ Priority handling defined
- ✅ Completion criteria specified
- ✅ Movement to Done folder process described
- ✅ Activity log format defined

**Next Steps:**
- Document is ready for reference by AI Employee system
- No further action required

---
