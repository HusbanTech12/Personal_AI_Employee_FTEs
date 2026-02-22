# Skill: Task Processor (Skill Router)

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `task_processor` |
| **Tier** | Silver |
| **Version** | 2.0 |
| **Status** | Active |
| **Type** | Router/Orchestrator |

---

## Purpose

Act as the central **Skill Router** for the AI Employee system. This skill:

1. **Reads** task content from incoming task files
2. **Classifies** tasks into appropriate categories
3. **Selects** the most suitable specialized skill
4. **Routes** execution to the selected skill
5. **Orchestrates** the complete workflow from Inbox to Done

---

## Task Classification System

### Category Detection Matrix

| Category | Keywords & Indicators | Skill Router |
|----------|----------------------|--------------|
| `coding` | `code`, `function`, `API`, `script`, `implement`, `build`, `develop`, `refactor`, `debug`, `test`, `.py`, `.js`, `.sh` | `coding.SKILL.md` |
| `research` | `research`, `analyze`, `investigate`, `explore`, `compare`, `evaluate`, `study`, `find`, `search`, `review` | `research.SKILL.md` |
| `documentation` | `document`, `write`, `README`, `guide`, `tutorial`, `explain`, `describe`, `update docs`, `.md` | `documentation.SKILL.md` |
| `planning` | `plan`, `strategy`, `roadmap`, `design`, `architecture`, `outline`, `structure`, `organize`, `task`, `project` | `planner.SKILL.md` |

### Priority Detection

| Priority | Markers | Response Time |
|----------|---------|---------------|
| `urgent` | `[URGENT]`, `ASAP`, `critical`, `blocking`, `emergency` | Immediate |
| `high` | `[HIGH]`, `important`, `deadline`, `priority` | Next cycle |
| `standard` | *(default)* | Queue order |
| `low` | `[LOW]`, `optional`, `nice-to-have`, `when possible` | After higher |

**Detection Order:** Frontmatter → Content markers → Keywords → Default

---

## Input

| Source | Format | Trigger |
|--------|--------|---------|
| `/Needs_Action/` | `.md` files with frontmatter | Task queue scan |

**Expected Task Structure:**
```markdown
---
title: Task Name
status: needs_action
priority: standard
created: YYYY-MM-DD HH:MM:SS
skill: task_processor
---

Task description and requirements...
```

---

## Process: Skill Routing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    SKILL ROUTING PIPELINE                       │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │   INBOX     │  ← New task arrives
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Needs_Action│  ← Task enters queue
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────────┐
    │  SKILL SELECTION (task_processor)       │
    │  ┌─────────────────────────────────┐    │
    │  │ 1. Read task content            │    │
    │  │ 2. Extract keywords             │    │
    │  │ 3. Match against category matrix│    │
    │  │ 4. Select target skill          │    │
    │  └─────────────────────────────────┘    │
    └──────────────────┬──────────────────────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
           ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │  coding  │ │ research │ │ documentation│
    │  SKILL   │ │  SKILL   │ │    SKILL     │
    └──────────┘ └──────────┘ └──────────────┘
           │           │           │
           └───────────┼───────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────┐
    │         EXECUTION                       │
    │  - Run selected skill logic             │
    │  - Generate deliverables                │
    │  - Verify output quality                │
    └──────────────────┬──────────────────────┘
                       │
                       ▼
    ┌─────────────┐
    │    DONE     │  ← Task completed & archived
    └─────────────┘
```

---

## Skill Selection Algorithm

### Step 1: Content Analysis

```python
def analyze_task(task_content: str) -> dict:
    """Extract classification signals from task."""
    
    # Extract frontmatter metadata
    frontmatter = parse_frontmatter(task_content)
    
    # Extract body content
    body = extract_body(task_content)
    
    # Build keyword frequency map
    keywords = extract_keywords(body)
    
    return {
        'frontmatter': frontmatter,
        'keywords': keywords,
        'body_length': len(body),
        'has_code_blocks': '```' in body,
        'has_checklists': '- [ ]' in body
    }
```

### Step 2: Category Scoring

```python
def score_categories(analysis: dict) -> dict:
    """Score each category based on analysis."""
    
    scores = {
        'coding': 0,
        'research': 0,
        'documentation': 0,
        'planning': 0
    }
    
    # Check explicit skill hint
    if 'skill' in analysis['frontmatter']:
        hinted_skill = analysis['frontmatter']['skill']
        if hinted_skill in scores:
            scores[hinted_skill] += 10
    
    # Score based on keywords
    for keyword, category in KEYWORD_MAP.items():
        if keyword in analysis['keywords']:
            scores[category] += analysis['keywords'][keyword]
    
    # Boost coding if code blocks present
    if analysis['has_code_blocks']:
        scores['coding'] += 5
    
    # Boost documentation if checklists present
    if analysis['has_checklists']:
        scores['documentation'] += 3
    
    return scores
```

### Step 3: Skill Selection

```python
def select_skill(scores: dict) -> str:
    """Select the highest-scoring category."""
    
    # Get highest score
    max_score = max(scores.values())
    
    if max_score == 0:
        return 'planning'  # Default fallback
    
    # Return category with highest score
    for category, score in scores.items():
        if score == max_score:
            return category
```

---

## Execution Lifecycle

### Phase 1: Task Acquisition

```
Scan /Needs_Action for pending tasks
↓
Read frontmatter: status = 'needs_action'
↓
Load full task content
↓
Lock task to prevent duplicate processing
```

### Phase 2: Skill Routing

```
Analyze task content
↓
Score against all categories
↓
Select highest-matching skill
↓
Load skill definition from /Skills/{skill}.SKILL.md
↓
Log routing decision
```

### Phase 3: Delegated Execution

```
Invoke selected skill's execution logic
↓
Monitor progress
↓
Handle errors per skill definition
↓
Collect output/deliverables
```

### Phase 4: Completion & Closure

```
Verify all deliverables generated
↓
Update task frontmatter: status → done
↓
Write activity log entry
↓
Move task to /Done/
↓
Update Dashboard metrics
↓
Release task lock
```

---

## Available Skills

| Skill ID | File | Purpose |
|----------|------|---------|
| `planner` | `planner.SKILL.md` | Task breakdown, roadmaps, project planning |
| `coding` | `coding.SKILL.md` | Code generation, refactoring, debugging |
| `research` | `research.SKILL.md` | Information gathering, analysis, comparison |
| `documentation` | `documentation.SKILL.md` | Writing guides, READMEs, technical docs |

---

## Routing Decision Log

Every routing decision is logged:

```
timestamp            | task              | selected_skill | confidence
---------------------|-------------------|----------------|------------
2026-02-22 20:45:00  | build_api.md      | coding         | high
2026-02-22 20:46:00  | research_ml.md    | research       | high
2026-02-22 20:47:00  | update_readme.md  | documentation  | medium
2026-02-22 20:48:00  | project_plan.md   | planning       | high
```

**Confidence Levels:**
- `high` - Clear keyword match or explicit skill hint
- `medium` - Moderate keyword overlap
- `low` - Weak signals, used default fallback

---

## Error Handling

| Error | Handling Strategy |
|-------|-------------------|
| No matching skill | Default to `planning`, flag `[REVIEW_REQUIRED]` |
| Skill file missing | Log error, fallback to `task_processor` base logic |
| Execution failure | Retry once, then flag `[BLOCKED]` with error details |
| Circular routing | Detect loop, force `planning` skill |

---

## Output

| Destination | Format | Content |
|-------------|--------|---------|
| `/Done/` | Original task file | Completed task with updated frontmatter |
| `/Logs/` | `.log` | Routing decision + execution summary |
| `Dashboard.md` | Updated metrics | Completed count, last activity |
| `activity_log.md` | Log entry | `completed | {filename} | {skill}` |

---

## Integration Points

- **filesystem_watcher.py**: Moves tasks from Inbox → Needs_Action
- **task_executor.py**: Executes the skill routing logic
- **Dashboard.md**: Receives task status updates
- **Skills/*.SKILL.md**: Specialized skill definitions

---

## Example Routing Decision

**Input Task:** `/Needs_Action/build_api.md`

```markdown
---
title: Build REST API
status: needs_action
priority: high
---

Implement a REST API endpoint for user registration.
- Create POST /api/users endpoint
- Add input validation
- Write unit tests
```

**Routing Analysis:**
- Keywords detected: `implement` (+2 coding), `API` (+3 coding), `endpoint` (+2 coding), `tests` (+2 coding)
- Code-related terms: `POST`, `/api/`
- Explicit markers: None

**Decision:**
```
Selected Skill: coding
Confidence: high (score: 9)
Runner-up: planning (score: 0)
```

**Execution:** Routes to `coding.SKILL.md` for implementation.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-19 | Initial Bronze Tier implementation |
| 2.0 | 2026-02-22 | Silver Tier: Added skill routing, classification matrix |
