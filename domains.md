# AI Employee Domain Configuration

## Overview

This file defines the domain structure for the AI Employee system.
Domains separate concerns and maintain isolated memory/knowledge bases.

---

## Domain Structure

```
Domains/
├── Personal/
│   ├── notes/           # Personal notes
│   ├── learning/        # Learning materials
│   ├── reminders/       # Personal reminders
│   └── health/          # Health & wellness
│
└── Business/
    ├── accounting/      # Financial records
    ├── marketing/       # Marketing materials
    ├── reporting/       # Business reports
    └── projects/        # Business projects
```

---

## Domain Definitions

### Personal Domain

**Purpose:** Handle personal life tasks and knowledge

**Categories:**
| Category | Description | Examples |
|----------|-------------|----------|
| `notes` | Personal notes & thoughts | Daily journal, ideas, reflections |
| `learning` | Learning materials | Courses, tutorials, study notes |
| `reminders` | Personal reminders | Appointments, birthdays, tasks |
| `health` | Health & wellness | Workout logs, meal plans, medical |

**Skills Available:**
- documentation (for notes)
- planner (for learning plans)
- research (for learning topics)

**Memory Location:** `Domains/Personal/memory.md`

---

### Business Domain

**Purpose:** Handle business/professional tasks and knowledge

**Categories:**
| Category | Description | Examples |
|----------|-------------|----------|
| `accounting` | Financial records | Invoices, expenses, budgets |
| `marketing` | Marketing activities | Social posts, campaigns, content |
| `reporting` | Business reports | Weekly reports, analytics, metrics |
| `projects` | Business projects | Project plans, deliverables |

**Skills Available:**
- email (business communication)
- linkedin_marketing (social media)
- coding (business tools)
- documentation (business docs)
- planner (project planning)
- research (market research)

**Memory Location:** `Domains/Business/memory.md`

---

## Domain Routing Rules

### Personal Domain Triggers

Route to Personal when task contains:

```yaml
keywords:
  - "personal"
  - "learn"
  - "study"
  - "course"
  - "reminder"
  - "appointment"
  - "health"
  - "workout"
  - "meal"
  - "family"
  - "friend"
  - "hobby"

skills:
  - "documentation" (for notes)
  - "planner" (for learning plans)
  - "research" (for learning topics)

folders:
  - "Personal/*"
```

### Business Domain Triggers

Route to Business when task contains:

```yaml
keywords:
  - "business"
  - "client"
  - "customer"
  - "invoice"
  - "payment"
  - "marketing"
  - "linkedin"
  - "report"
  - "meeting"
  - "project"
  - "deadline"
  - "revenue"
  - "expense"

skills:
  - "email"
  - "linkedin_marketing"
  - "coding"
  - "documentation"
  - "planner"
  - "research"
  - "approval"

folders:
  - "Business/*"
```

---

## Cross-Domain Tasks

Some tasks may span both domains:

| Task Type | Primary Domain | Secondary Domain |
|-----------|---------------|------------------|
| Work from home setup | Business | Personal |
| Professional development | Personal | Business |
| Tax preparation | Personal | Business |
| Business travel | Business | Personal |

**Handling:** Route to primary domain, share relevant info with secondary.

---

## Memory Separation

### Personal Memory

Stored in: `Domains/Personal/memory.md`

Contains:
- Personal preferences
- Learning history
- Personal contacts
- Health data
- Personal goals

### Business Memory

Stored in: `Domains/Business/memory.md`

Contains:
- Business contacts
- Client information
- Project history
- Business goals
- Professional network

### Shared Memory

Stored in: `Domains/shared_memory.md`

Contains:
- Calendar events
- General preferences
- System settings

---

## Domain Router Configuration

```yaml
router:
  default_domain: "Personal"
  auto_classify: true
  allow_cross_domain: true
  require_confirmation: false
  
classification:
  method: "keyword_and_skill"
  confidence_threshold: 0.7
  fallback: "ask_user"
```

---

## Task Flow with Domains

```
Inbox
  ↓
Domain Router (classify + route)
  ↓
Personal Domain          Business Domain
  ↓                        ↓
Planner                  Planner
  ↓                        ↓
Manager                  Manager
  ↓                        ↓
Skill Agents             Skill Agents
  ↓                        ↓
Personal Memory          Business Memory
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-23 | Initial domain configuration |
