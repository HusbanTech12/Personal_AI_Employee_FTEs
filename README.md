# AI Employee Vault - Bronze Tier

A Local-First Personal AI Employee (Digital FTE) built on Obsidian markdown workflow.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Employee System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────────┐    ┌──────────┐            │
│   │  Inbox   │───→│ Needs_Action │───→│   Done   │            │
│   │ (Watch)  │    │  (Process)   │    │ (Store)  │            │
│   └────┬─────┘    └──────┬───────┘    └──────────┘            │
│        │                 │                                      │
│        ▼                 ▼                                      │
│   ┌─────────────────────────────────┐                          │
│   │     filesystem_watcher.py       │                          │
│   │     (Watchdog Monitor)          │                          │
│   └─────────────────────────────────┘                          │
│                          │                                      │
│                          ▼                                      │
│   ┌─────────────────────────────────┐                          │
│   │      Qwen AI Agent              │                          │
│   │      (Task Processing)          │                          │
│   └─────────────────────────────────┘                          │
│                          │                                      │
│        ┌─────────────────┴─────────────────┐                   │
│        ▼                                   ▼                   │
│   ┌──────────┐                       ┌──────────┐             │
│   │Dashboard │                       │  Skills  │             │
│   │  (UI)    │                       │ (Logic)  │             │
│   └──────────┘                       └──────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
AI_Employee_Vault/
├── Dashboard.md              # Central status & task overview
├── Company_Handbook.md       # AI Employee rules & guidelines
├── filesystem_watcher.py     # Python watchdog script
├── README.md                 # This file
│
├── Inbox/                    # Incoming files (watched)
│   └── (drop files here)
│
├── Needs_Action/             # Active work queue
│   ├── *.md                  # Task files
│   └── *.meta.md             # Metadata files
│
├── Done/                     # Completed tasks (archived)
│   └── (moved after completion)
│
├── Skills/                   # AI skill definitions
│   └── task_processor.SKILL.md
│
└── Logs/                     # Activity & error logs
    ├── watcher_YYYY-MM-DD.log
    └── error_YYYY-MM-DD.md
```

### Folder Roles

| Folder | Purpose | AI Access | User Action |
|--------|---------|-----------|-------------|
| `Inbox/` | Drop zone for new tasks | Read (watch) | Add files here |
| `Needs_Action/` | Active processing queue | Read/Write | Review items |
| `Done/` | Completed task archive | Write (move) | Browse history |
| `Skills/` | Skill definitions | Read | Extend skills |
| `Logs/` | System activity logs | Write | Monitor health |

---

## Watcher Logic

The `filesystem_watcher.py` script:

1. **Monitors** `/Inbox` folder using `watchdog` library
2. **Detects** new file creation events
3. **Validates** file is not temporary (`.tmp`, `.part`, etc.)
4. **Copies** file to `/Needs_Action/` (preserves original)
5. **Creates** metadata file (`.meta.md`) with task info
6. **Updates** `Dashboard.md` pending tasks section
7. **Logs** all operations to `/Logs/`

### Watcher Behavior

```
File dropped in Inbox
        ↓
Watcher detects creation event
        ↓
Wait 0.5s (ensure file fully written)
        ↓
Validate file exists and readable
        ↓
Copy to Needs_Action/
        ↓
Create .meta.md metadata file
        ↓
Update Dashboard.md
        ↓
Log activity
        ↓
Ready for AI processing
```

---

## AI Task Lifecycle

### Workflow: Inbox → Needs_Action → Done

```
┌─────────────────────────────────────────────────────────────┐
│                    Task Lifecycle                           │
└─────────────────────────────────────────────────────────────┘

  1. INCOMING              2. PROCESSING           3. COMPLETE
  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
  │   /Inbox    │         │Needs_Action │         │    /Done    │
  │             │         │             │         │             │
  │  [file.md]  │──── ───→│  [file.md]  │──── ───→│  [file.md]  │
  │             │         │  [file.meta]│         │             │
  └─────────────┘         └──────┬──────┘         └─────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Qwen AI Reads  │
                        │  Processes Task │
                        │  Updates Status │
                        └─────────────────┘
```

### How Qwen Processes Tasks

1. **Read** `Dashboard.md` → Check `Pending_Tasks` section
2. **Navigate** to `/Needs_Action/` → Find task files
3. **Read** task content + metadata (`.meta.md`)
4. **Process** according to `Company_Handbook.md` rules
5. **Execute** skill logic from `Skills/task_processor.SKILL.md`
6. **Update** `Dashboard.md` with progress
7. **Move** completed task to `/Done/`
8. **Log** completion in `/Logs/`

---

## Setup Steps

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Obsidian (for vault viewing)

### Installation

**Step 1: Install Python dependencies**

```bash
pip install watchdog
```

**Step 2: Verify directory structure**

Ensure these folders exist in `AI_Employee_Vault/`:
- `Inbox/`
- `Needs_Action/`
- `Done/`
- `Skills/`
- `Logs/`

**Step 3: Open vault in Obsidian**

1. Open Obsidian
2. Click "Open folder as vault"
3. Select `AI_Employee_Vault/` folder

---

## Run Instructions

### Quick Start (Recommended)

**Start All Agents:**

```bash
bash run_agents.sh
```

This single command will:
- Activate the virtual environment
- Start the filesystem watcher (monitors Inbox/)
- Start the task executor (processes Needs_Action/)
- Run both agents concurrently
- Log all activity to `Logs/agents.log`
- Handle graceful shutdown on Ctrl+C

**Stop All Agents:**

Press `Ctrl+C` in the terminal to gracefully shutdown both agents.

---

### Manual Start (Individual Components)

If you prefer to run components separately:

**Start the Filesystem Watcher:**

**Windows (PowerShell):**
```powershell
cd D:\Quarter_4\Hackathon_0\AI_Employee_Vault
python filesystem_watcher.py
```

**Windows (Command Prompt):**
```cmd
cd D:\Quarter_4\Hackathon_0\AI_Employee_Vault
python filesystem_watcher.py
```

**Linux/Mac:**
```bash
cd /path/to/Hackathon_0/AI_Employee_Vault
python3 filesystem_watcher.py
```

### Stop the Watcher

Press `Ctrl+C` in the terminal to gracefully stop monitoring.

### Test the System

1. **Start** the watcher (see above)
2. **Create** a test file in `/Inbox/`:
   ```
   test_task.md
   ```
3. **Observe** console output:
   ```
   New file detected: test_task.md
   Copied to Needs_Action: test_task.md
   Created metadata: test_task.meta.md
   Dashboard updated successfully
   ```
4. **Check** `/Needs_Action/` for the copied file + metadata
5. **Open** `Dashboard.md` in Obsidian to see the pending task

---

## Configuration

### Windows Path Adjustment

If running on Windows, update `BASE_DIR` in `filesystem_watcher.py`:

```python
# Line 28-29
BASE_DIR = Path(r"D:\Quarter_4\Hackathon_0\AI_Employee_Vault")
```

### Log Retention

Logs are created daily:
- `watcher_YYYY-MM-DD.log` - Activity logs
- `error_YYYY-MM-DD.md` - Error logs (if any)

Manually archive or delete old logs as needed.

---

## Extending the System

### Add New Skills

1. Create new file in `/Skills/`
2. Follow `task_processor.SKILL.md` template
3. Define: Purpose, Input, Process, Output
4. Reference in `Company_Handbook.md`

### Customize Workflow

Edit `Company_Handbook.md` to:
- Add new task categories
- Modify folder movement rules
- Update sensitivity markers

### Dashboard Sections

Add AI-parsable sections to `Dashboard.md`:

```markdown
<!-- AI_PARSE_START: Custom_Section -->
Your content here
<!-- AI_PARSE_END: Custom_Section -->
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher doesn't start | Check Python installation, run `pip install watchdog` |
| Files not detected | Ensure file is fully written (not .tmp) |
| Dashboard not updating | Check file permissions, close in other apps |
| Path errors on Windows | Use raw string `r"..."` for BASE_DIR |

---

## Version Info

- **Version:** 1.1
- **Tier:** Silver
- **Created:** 2026-02-19
- **Updated:** 2026-02-22
- **Architecture:** Local-First
- **Platform:** Cross-platform (Windows/Linux/Mac/WSL)

---

## Silver Tier Features

| Feature | Description |
|---------|-------------|
| **Concurrent Agents** | Filesystem watcher + task executor run simultaneously |
| **Auto Startup** | Single `run_agents.sh` script starts all components |
| **Centralized Logging** | All agent output logged to `Logs/agents.log` |
| **Graceful Shutdown** | Clean termination with Ctrl+C |
| **Process Monitoring** | Auto-restart if an agent crashes |
| **WSL Compatible** | Works on Windows Subsystem for Linux |

---

## Next Steps (Silver/Gold Tier)

- [ ] Add email integration skill
- [ ] Implement auto-categorization with ML
- [ ] Add calendar/scheduling capabilities
- [ ] Create web dashboard interface
- [ ] Add multi-agent coordination
