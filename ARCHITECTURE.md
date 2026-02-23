# AI Employee System Architecture

**Generated:** 2026-02-24 12:00:00
**Version:** Gold Tier
**Session:** 2026-02-24 10:00:00

---

## System Overview

The AI Employee is an autonomous multi-agent system that processes tasks through a pipeline of specialized agents, MCP servers, and skills.

### Key Components

| Component | Count | Description |
|-----------|-------|-------------|
| Agents | 16 | Autonomous task processors |
| MCP Servers | 5 | Service integration layer |
| Skills | 15 | Capability definitions |

---

## Agent Registry

| Agent | File | Priority | Executions | Failures | Status |
|-------|------|----------|------------|----------|--------|
| accounting | accounting_agent.py | high | 0 | 0 | unknown |
| approval | approval_agent.py | normal | 0 | 0 | unknown |
| audit | audit_agent.py | normal | 0 | 0 | unknown |
| autonomy_loop | autonomy_loop_agent.py | critical | 0 | 0 | unknown |
| ceo_briefing | ceo_briefing_agent.py | normal | 0 | 0 | unknown |
| coding | coding_agent.py | normal | 0 | 0 | unknown |
| documentation | documentation_agent.py | normal | 0 | 0 | unknown |
| domain_router | domain_router_agent.py | normal | 0 | 0 | unknown |
| email | email_agent.py | high | 0 | 0 | unknown |
| linkedin | linkedin_agent.py | normal | 0 | 0 | unknown |
| manager | manager_agent.py | normal | 0 | 0 | unknown |
| memory | memory_agent.py | normal | 0 | 0 | unknown |
| planner | planner_agent.py | normal | 0 | 0 | unknown |
| reasoning | reasoning_agent.py | normal | 0 | 0 | unknown |
| resilience | resilience_agent.py | critical | 0 | 0 | unknown |
| scheduler | scheduler_agent.py | normal | 0 | 0 | unknown |
| social_media | social_media_agent.py | normal | 0 | 0 | unknown |
| task_processor | task_processor_agent.py | normal | 0 | 0 | unknown |
| validator | validator_agent.py | normal | 0 | 0 | unknown |

---

## MCP Server Map

| Server | Port | Host | Actions | Status |
|--------|------|------|---------|--------|
| accounting_mcp | 8767 | 127.0.0.1 | invoice/create, expense/add, reports/summary, budget/status | unknown |
| automation_mcp | 8769 | 127.0.0.1 | file/copy, file/move, transform, webhook/trigger, tasks/list | unknown |
| email_mcp | 8765 | 127.0.0.1 | send, queue/add, flush, status, health | unknown |
| linkedin_mcp | 8766 | 127.0.0.1 | generate, publish, generate-and-publish, analytics, analytics/summary | unknown |
| social_mcp | 8768 | 127.0.0.1 | post/schedule, post/publish, analytics, calendar | unknown |

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Employee System                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Inbox     │ ──→ │   Domain    │ ──→ │   Planner   │
│  (Watch)    │     │   Router    │     │   Agent     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Manager Agent                              │
│              (Skill Selection & Orchestration)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Skill Agents   │ │  Approval       │ │  Resilience     │
│  (Execution)    │ │  Agent          │ │  Agent          │
└────────┬────────┘ └─────────────────┘ └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Server Layer                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  Email  │ │LinkedIn │ │Accounting│ │ Social  │ │Automation│ │
│  │ :8765   │ │ :8766   │ │ :8767   │ │ :8768   │ │ :8769   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Task Processing Pipeline

1. **Inbox Detection** → `filesystem_watcher.py`
2. **Domain Classification** → `domain_router_agent.py`
3. **Task Planning** → `planner_agent.py`
4. **Skill Selection** → `manager_agent.py`
5. **Execution** → Skill-specific agent
6. **Validation** → `validator_agent.py`
7. **Memory Update** → `memory_agent.py`

### Cross-Cutting Concerns

| Concern | Agent |
|---------|-------|
| Resilience | `resilience_agent.py` |
| Audit | `audit_agent.py` |
| Documentation | `documentation_agent.py` |
| Scheduling | `scheduler_agent.py` |
| CEO Briefing | `ceo_briefing_agent.py` |

---

## Configuration

### Directory Structure

```
AI_Employee_Vault/
├── Agents/           # Agent executables
├── Skills/           # Skill definitions (*.SKILL.md)
├── MCP/              # MCP servers
├── Domains/          # Domain separation
│   ├── Personal/
│   └── Business/
├── Logs/             # System logs
├── Audit/            # Audit trails
└── Done/             # Completed tasks
```

### Key Configuration Files

| File | Purpose |
|------|---------|
| `domains.md` | Domain routing rules |
| `schedule.md` | Scheduled tasks |
| `Company_Handbook.md` | System rules |
| `Dashboard.md` | System status |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total Executions | 0 |
| Total Failures | 0 |
| Total Recoveries | 0 |
| Documentation Updates | 1 |
| Uptime | 0m |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| Gold Tier | 2026-02-24 | Multi-agent with domains |
| Silver Tier | 2026-02-23 | MCP integration |
| Bronze Tier | 2026-02-20 | Initial release |

---

*Generated automatically by AI Employee Documentation Agent*
