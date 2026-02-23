# Skill: CEO Briefing

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `ceo_briefing` |
| **Tier** | Gold+ |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Executive Reporting |
| **Frequency** | Weekly |

---

## Purpose

Generate executive-level weekly briefings for CEO/leadership. This skill:

1. **Aggregates** data from all business systems
2. **Analyzes** financial and operational metrics
3. **Identifies** risks and opportunities
4. **Generates** actionable recommendations
5. **Produces** CEO_WEEKLY_REPORT.md

---

## Data Sources

| Source | Location | Data Extracted |
|--------|----------|----------------|
| **Accounting** | `Logs/Accounting/` | Revenue, expenses, invoices |
| **Marketing** | `Domains/Business/Marketing/` | Social metrics, engagement |
| **Completed Tasks** | `Done/` | Task completion data |
| **Activity Logs** | `Logs/activity_log.md` | All system activity |

---

## Report Sections

1. **Executive Summary** - Key highlights
2. **Revenue Summary** - Financial performance
3. **Activity Report** - Operational metrics
4. **Risks Detected** - Issues requiring attention
5. **Recommendations** - Actionable items

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial CEO briefing skill |
