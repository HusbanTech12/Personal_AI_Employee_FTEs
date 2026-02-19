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
