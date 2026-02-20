# Skill: Task Processor

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `task_processor` |
| **Tier** | Bronze |
| **Version** | 1.0 |
| **Status** | Active |

---

## Purpose

Process incoming tasks from the `/Inbox` folder, classify them, and manage their movement through the workflow pipeline.

---

## Input

| Source | Format | Trigger |
|--------|--------|---------|
| `/Inbox/` | Any file type | File creation event |

**Expected Input:**
- Text files (`.md`, `.txt`)
- Documents (`.pdf`, `.docx`)
- Data files (`.json`, `.csv`)

---

## Process

### Step 1: Detection
```
Watch /Inbox for new files
↓
Detect file creation event
↓
Validate file is not temporary (.tmp, .part)
```

### Step 2: Classification
```
Read file content
↓
Analyze for keywords/priority markers
↓
Assign category: URGENT, STANDARD, REVIEW, ARCHIVE
↓
Flag if [SENSITIVE] content detected
```

### Step 3: Movement
```
Copy file to /Needs_Action/
↓
Preserve original in /Inbox (safety)
↓
Generate metadata markdown
↓
Log the operation
```

### Step 4: Dashboard Update
```
Read Dashboard.md
↓
Add entry to Pending_Tasks section
↓
Update Timestamp
↓
Save changes
```

---

## Execution Lifecycle

### Phase 1: Task Selection

```
Scan /Needs_Action
↓
Read frontmatter from all .md files
↓
Sort by: priority (DESC), created (ASC)
↓
Select highest-priority oldest task
```

**Selection Criteria:**
- Only process `status: needs_action` tasks
- Priority order: `urgent` > `high` > `standard` > `low`
- Tie-breaker: Oldest `created` timestamp first

### Phase 2: Task Execution

```
Read task Description and Expected Output
↓
Execute required work
↓
Generate deliverables
↓
Verify output quality
```

**Execution Rules:**
- Follow task specifications exactly
- Flag ambiguities with `[REVIEW_REQUIRED]`
- Document decisions in task Notes section

### Phase 3: Completion Verification

```
Check all Expected Output delivered?
↓
Check activity log entry created?
↓
Check dashboard metrics updated?
↓
All YES → Mark complete
Any NO → Return to queue with notes
```

### Phase 4: Task Closure

```
Update frontmatter: status → done
↓
Write activity log entry
↓
Move file to /Done/
↓
Move metadata file to /Done/
↓
Update dashboard: increment completed count
↓
Remove from pending tasks list
```

---

## Priority Handling

| Priority | Marker | Response |
|----------|--------|----------|
| `urgent` | `[URGENT]` | Process immediately |
| `high` | `[HIGH]` | Next in queue |
| `standard` | *(default)* | Normal queue order |
| `low` | `[LOW]` | Process after higher priorities |

**Priority Detection Order:** Frontmatter field → Content markers → Keywords → Default

---

## Output

| Destination | Format | Content |
|-------------|--------|---------|
| `/Needs_Action/` | Original file | Task file ready for processing |
| `/Needs_Action/` | `.meta.md` | Metadata file |
| `/Logs/` | `.md` | Activity log entry |
| `Dashboard.md` | Updated section | New pending task listed |

### Metadata File Format

```markdown
# Task Metadata

- **Original File:** `{filename}`
- **Received:** `{timestamp}`
- **Category:** `{URGENT|STANDARD|REVIEW|ARCHIVE}`
- **Status:** `Pending`
- **Sensitive:** `{true|false}`
- **Source:** `/Inbox/{filename}`
```

---

## Folder Movement Logic

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   /Inbox    │ ──→ │  /Needs_Action   │ ──→ │   /Done     │
│  (Watch)    │     │   (Process)      │     │ (Complete)  │
└─────────────┘     └──────────────────┘     └─────────────┘
       │                    │                      │
       │                    │                      │
       ▼                    ▼                      ▼
   Read-only           Read/Write            Write only
   (Original           (Active               (Final
    preserved)          Queue)                Storage)
```

**Movement Rules:**
1. **Copy** from Inbox → Needs_Action (never move initially)
2. **Move** from Needs_Action → Done (after completion)
3. **Never delete** from Inbox (user manages cleanup)
4. **Always log** each movement operation

---

## Error Conditions

| Error | Handling |
|-------|----------|
| File locked/in-use | Retry 3x, then log error |
| Invalid characters in name | Sanitize filename, log warning |
| Destination full/no space | Halt, flag critical error |
| Dashboard locked | Queue update, retry on next cycle |

---

## Integration Points

- **Filesystem Watcher:** Triggers skill execution
- **Dashboard.md:** Receives task updates
- **Logs/:** Records all operations
- **Company_Handbook.md:** Provides classification rules

---

## Example Execution

**Input:** `/Inbox/meeting_notes.md`

**Process:**
1. File detected at 2026-02-19 10:30:00
2. Content analyzed → Category: STANDARD
3. Copied to `/Needs_Action/meeting_notes.md`
4. Metadata created: `/Needs_Action/meeting_notes.meta.md`
5. Dashboard updated with new pending task
6. Log entry written: `/Logs/activity_2026-02-19.md`

**Output:** Task ready for AI processing in Needs_Action queue.
