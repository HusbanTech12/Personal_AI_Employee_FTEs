# Skill: Auto Documentation

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `auto_documentation` |
| **Tier** | Gold+ |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Documentation & Knowledge |
| **Auto-Update** | After each execution |

---

## Purpose

Automatically generate and maintain system documentation. This skill:

1. **Generates** ARCHITECTURE.md (system overview)
2. **Maintains** LESSONS_LEARNED.md (execution learnings)
3. **Updates** after each significant execution
4. **Tracks** system evolution over time
5. **Captures** operational knowledge

---

## Generated Documents

### ARCHITECTURE.md

- System overview
- Component diagram
- Agent registry
- MCP server map
- Data flows
- Configuration

### LESSONS_LEARNED.md

- Execution insights
- Failure patterns
- Recovery successes
- Optimization opportunities
- Best practices discovered

---

## Update Triggers

| Trigger | Documents Updated |
|---------|-------------------|
| New agent registered | ARCHITECTURE.md |
| Task completed | LESSONS_LEARNED.md |
| Failure recovered | LESSONS_LEARNED.md |
| MCP call pattern | ARCHITECTURE.md |
| Daily (scheduled) | Both documents |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial auto-documentation skill |
