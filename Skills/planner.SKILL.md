# Skill: Planner

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `planner` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Planning & Strategy |

---

## Purpose

Transform vague goals, project ideas, and complex requirements into **actionable, structured plans**. This skill:

1. **Analyzes** project goals and constraints
2. **Decomposes** large objectives into manageable tasks
3. **Creates** timelines, roadmaps, and milestones
4. **Identifies** dependencies and critical paths
5. **Generates** clear execution steps

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Project Request** | High-level goal description | "Build a mobile app", "Launch marketing campaign" |
| **Task List** | Unorganized list of items | Bullet points, brainstorm dump |
| **Requirements Doc** | Detailed specifications | Feature lists, user stories |
| **Problem Statement** | Challenge to solve | "Reduce server costs by 30%" |
| **Meeting Notes** | Discussion outcomes | Action items, decisions made |

**Expected Format:**
```markdown
---
title: Project/Task Name
status: needs_action
priority: standard
skill: planner
---

## Goal
Clear statement of what needs to be achieved

## Context
Background information and constraints

## Requirements
- List of must-have outcomes
- Success criteria
```

---

## Execution Steps

### Step 1: Goal Clarification

```
Read task description
↓
Identify primary objective
↓
Extract success criteria
↓
Note constraints and deadlines
↓
Clarify ambiguities (if any)
```

**Output:** Clear, measurable goal statement

### Step 2: Scope Definition

```
Identify in-scope items
↓
Identify out-of-scope items
↓
Define boundaries
↓
Note assumptions
```

**Output:** Scope document with boundaries

### Step 3: Task Decomposition

```
Break goal into major phases
↓
Decompose phases into work packages
↓
Break work packages into individual tasks
↓
Estimate effort for each task
```

**Output:** Hierarchical task breakdown (WBS)

### Step 4: Dependency Mapping

```
Identify task dependencies
↓
Determine critical path
↓
Note parallel workstreams
↓
Identify external dependencies
```

**Output:** Dependency graph/matrix

### Step 5: Timeline Creation

```
Sequence tasks by dependencies
↓
Assign durations
↓
Calculate start/end dates
↓
Identify milestones
↓
Buffer for risks
```

**Output:** Project timeline with milestones

### Step 6: Resource Planning

```
Identify required skills
↓
Note tool/resource needs
↓
Flag potential bottlenecks
↓
Suggest team composition (if applicable)
```

**Output:** Resource requirements list

### Step 7: Risk Assessment

```
Identify potential risks
↓
Assess probability and impact
↓
Define mitigation strategies
↓
Create contingency plans
```

**Output:** Risk register

---

## Output Format

All planning outputs follow this structure:

```markdown
# Plan: {Project Name}

## Executive Summary
Brief overview of the plan (2-3 sentences)

## Goal Statement
Clear, measurable objective

## Scope

### In Scope
- Item 1
- Item 2

### Out of Scope
- Item 1
- Item 2

## Task Breakdown

### Phase 1: {Phase Name}
- [ ] Task 1.1 (Estimate: X hours/days)
- [ ] Task 1.2

### Phase 2: {Phase Name}
- [ ] Task 2.1
- [ ] Task 2.2

## Timeline

| Milestone | Target Date | Dependencies |
|-----------|-------------|--------------|
| M1: Phase 1 Complete | YYYY-MM-DD | - |
| M2: Phase 2 Complete | YYYY-MM-DD | M1 |

## Dependencies
- Task X must complete before Task Y
- External: {dependency}

## Resources Needed
- Skill: {skill}
- Tool: {tool}
- Access: {access}

## Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Risk 1 | Low/Med/High | Low/Med/High | Strategy |

## Next Actions
1. Immediate next step
2. Second step
3. Third step
```

---

## Completion Rules

A planning task is **complete** when ALL criteria are met:

### Mandatory Deliverables

- [ ] **Goal Statement** - Clear, measurable objective defined
- [ ] **Task Breakdown** - At least 3 levels of decomposition
- [ ] **Timeline** - Phases/milestones with estimated dates
- [ ] **Dependencies** - Key dependencies identified
- [ ] **Next Actions** - Immediate steps clearly specified

### Quality Checks

- [ ] Tasks are actionable (not vague)
- [ ] Estimates are realistic
- [ ] Dependencies are logical
- [ ] Risks are addressed
- [ ] Output is in correct format

### Documentation

- [ ] Plan saved in task file under `## Plan` section
- [ ] Activity log entry created
- [ ] Dashboard updated

---

## Planning Templates

### Simple Task Plan

```markdown
## Plan

**Objective:** {What}

**Steps:**
1. {First action}
2. {Second action}
3. {Third action}

**Done When:** {Success criteria}

**Estimated Time:** {Duration}
```

### Project Plan

```markdown
## Plan

### Overview
{2-3 sentence summary}

### Phases

**Phase 1: Discovery** (Week 1-2)
- Research requirements
- Interview stakeholders
- Document findings

**Phase 2: Design** (Week 3-4)
- Create architecture
- Review with team
- Finalize design

**Phase 3: Implementation** (Week 5-8)
- Build core features
- Write tests
- Fix bugs

**Phase 4: Launch** (Week 9)
- Deploy to production
- Monitor metrics
- Gather feedback

### Milestones
- M1: Requirements signed off (Week 2)
- M2: Design approved (Week 4)
- M3: Features complete (Week 8)
- M4: Production launch (Week 9)
```

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Plan requires code implementation | `coding` | Task breakdown, technical requirements |
| Plan requires research | `research` | Research questions, scope |
| Plan requires documentation | `documentation` | Outline, key points to document |

---

## Examples

### Example 1: Simple Task

**Input:**
```
I need to set up a new project repository
```

**Output:**
```markdown
## Plan: Repository Setup

**Steps:**
1. Create GitHub/GitLab repository
2. Initialize with README.md
3. Add .gitignore for language
4. Set up branch protection rules
5. Configure CI/CD pipeline
6. Invite team members

**Done When:** Repository is accessible, CI passes on test commit

**Estimated Time:** 2 hours
```

### Example 2: Complex Project

**Input:**
```
Build an e-commerce website with user authentication, product catalog, and payment processing
```

**Output:** Full project plan with phases, milestones, dependencies (as shown in template above)

---

## Error Handling

| Issue | Resolution |
|-------|------------|
| Goal is unclear | Flag `[CLARIFICATION_NEEDED]`, list specific questions |
| Missing constraints | Assume standard constraints, note assumptions |
| Scope too large | Break into multiple phases, suggest prioritization |
| Dependencies unknown | Mark as `[EXTERNAL_DEPENDENCY]`, flag for tracking |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-22 | Initial Silver Tier implementation |
