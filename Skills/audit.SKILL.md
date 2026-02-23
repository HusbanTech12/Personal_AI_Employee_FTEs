# Skill: System Audit

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `system_audit` |
| **Tier** | Gold+ |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Compliance & Observability |
| **Retention** | 90 days (configurable) |

---

## Purpose

Comprehensive audit logging for all system activities. This skill:

1. **Logs** task lifecycle events
2. **Records** agent decisions
3. **Tracks** MCP calls (requests/responses)
4. **Documents** failures with context
5. **Captures** retry attempts and outcomes
6. **Maintains** immutable audit trail

---

## Audit Categories

| Category | Events Logged | Retention |
|----------|---------------|-----------|
| **Task Lifecycle** | created, started, completed, failed | 90 days |
| **Agent Decisions** | skill selection, routing, classification | 90 days |
| **MCP Calls** | request, response, error, latency | 30 days |
| **Failures** | error, context, stack trace, resolution | 180 days |
| **Retries** | attempt, backoff, outcome | 90 days |

---

## Storage Structure

```
Audit/
├── tasks/
│   └── YYYY-MM/
│       └── task_lifecycle.log
├── agents/
│   └── YYYY-MM/
│       └── agent_decisions.log
├── mcp/
│   └── YYYY-MM/
│       └── mcp_calls.log
├── failures/
│   └── YYYY-MM/
│       └── failures.log
├── retries/
│   └── YYYY-MM/
│       └── retries.log
└── summary/
    └── daily_audit_summary.md
```

---

## Log Format

### JSON Lines Format

```json
{"timestamp": "2026-02-24T10:30:00.123Z", "category": "task_lifecycle", "event": "task_created", "task_id": "task_001", "details": {...}}
{"timestamp": "2026-02-24T10:30:01.456Z", "category": "agent_decision", "event": "skill_selected", "agent_id": "manager", "details": {...}}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial audit skill |
