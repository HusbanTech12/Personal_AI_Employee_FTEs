# Skill: Research

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `research` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Information Gathering & Analysis |

---

## Purpose

Conduct thorough **information gathering, analysis, and synthesis**. This skill:

1. **Investigates** topics, technologies, and solutions
2. **Compares** alternatives with objective criteria
3. **Analyzes** data and extracts insights
4. **Synthesizes** findings into actionable recommendations
5. **Cites** sources for verification and further reading

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Exploration Request** | Investigate a topic | "Research ML frameworks", "Explore cloud providers" |
| **Comparison Request** | Evaluate alternatives | "Compare PostgreSQL vs MongoDB", "React vs Vue" |
| **Best Practices** | Find recommended approaches | "Best practices for API design", "Security guidelines" |
| **Problem Investigation** | Understand root cause | "Why is build slow?", "What causes memory leaks?" |
| **Market/Competitor Analysis** | Understand landscape | "Competitor features analysis", "Market trends" |
| **Technical Deep-Dive** | Understand technology | "How does Kubernetes work?", "Explain blockchain" |

**Expected Format:**
```markdown
---
title: Research Task
status: needs_action
priority: standard
skill: research
---

## Research Question
Clear statement of what needs to be investigated

## Scope
- What to cover
- What to exclude
- Time constraints

## Output Needs
- Comparison matrix
- Recommendation
- Summary report
```

---

## Execution Steps

### Step 1: Question Clarification

```
Read research request thoroughly
↓
Identify primary research question
↓
Note secondary questions
↓
Define scope boundaries
↓
Clarify success criteria
```

**Output:** Clear research question statement

### Step 2: Source Identification

```
Identify relevant information sources
↓
Prioritize authoritative sources
↓
Note publication dates (recency matters)
↓
Plan search strategy
```

**Output:** Source list and search plan

### Step 3: Information Gathering

```
Collect information from multiple sources
↓
Take structured notes
↓
Record source citations
↓
Flag conflicting information
↓
Note information gaps
```

**Output:** Raw research notes with citations

### Step 4: Analysis

```
Organize information thematically
↓
Identify patterns and trends
↓
Compare alternatives objectively
↓
Evaluate trade-offs
↓
Assess credibility of sources
```

**Output:** Analyzed findings

### Step 5: Synthesis

```
Combine findings into coherent narrative
↓
Resolve conflicting information
↓
Draw evidence-based conclusions
↓
Formulate recommendations
↓
Note confidence levels
```

**Output:** Synthesized report

### Step 6: Validation

```
Cross-check key claims
↓
Verify citations are accurate
↓
Ensure conclusions follow from evidence
↓
Check for bias or assumptions
↓
Note limitations
```

**Output:** Validated research report

### Step 7: Recommendation Formulation

```
State clear recommendation
↓
Provide supporting evidence
↓
Note caveats and conditions
↓
Suggest next steps
```

**Output:** Actionable recommendation

---

## Output Format

All research outputs follow this structure:

```markdown
# Research Report: {Topic}

## Executive Summary
2-3 sentence summary of findings and recommendation

## Research Question
Clear statement of what was investigated

## Methodology
- Sources consulted
- Search strategy
- Time spent

## Findings

### Topic 1: {Theme}
Key findings with citations [1], [2]

### Topic 2: {Theme}
Key findings with citations [3], [4]

## Comparison Matrix

| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Cost | $X/mo | $Y/mo | $Z/mo |
| Ease of Use | High | Medium | Low |
| Features | 10/10 | 8/10 | 6/10 |
| Support | 24/7 | Business hrs | Community |
| **Total Score** | **9/10** | **7/10** | **5/10** |

## Analysis

### Strengths of Option A
- Point 1
- Point 2

### Weaknesses of Option A
- Point 1
- Point 2

### Trade-offs
- If you prioritize X, choose A
- If you prioritize Y, choose B

## Recommendation

**Recommended:** Option A

**Rationale:**
- Evidence-based reason 1
- Evidence-based reason 2
- Why this beats alternatives

**Confidence:** High/Medium/Low

## Caveats & Limitations
- Assumption made
- Information gap
- Area needing further research

## Sources

1. [Source Name](URL) - Publication Date
2. [Source Name](URL) - Publication Date
3. [Source Name](URL) - Publication Date

## Next Steps
1. Action to take based on recommendation
2. Follow-up research if needed
```

---

## Completion Rules

A research task is **complete** when ALL criteria are met:

### Mandatory Deliverables

- [ ] **Research Question** - Clearly stated
- [ ] **Findings** - Organized by theme/topic
- [ ] **Sources** - At least 3 credible sources cited
- [ ] **Analysis** - Objective evaluation
- [ ] **Recommendation** - Clear, actionable conclusion

### Quality Checks

- [ ] Sources are credible (official docs, peer-reviewed, reputable)
- [ ] Information is current (within 2 years for tech topics)
- [ ] Multiple perspectives considered
- [ ] Bias acknowledged if present
- [ ] Conclusions supported by evidence

### Documentation

- [ ] Activity log entry created
- [ ] Dashboard updated
- [ ] All URLs are working links

---

## Research Quality Standards

### Source Credibility Hierarchy

| Tier | Source Type | Weight |
|------|-------------|--------|
| 1 | Official documentation, RFCs, standards | Highest |
| 2 | Peer-reviewed papers, academic sources | High |
| 3 | Reputable tech blogs, company engineering blogs | Medium-High |
| 4 | Stack Overflow, GitHub issues | Medium |
| 5 | Forum posts, personal blogs | Low (corroborate) |

### Recency Guidelines

| Topic Type | Max Age |
|------------|---------|
| Fast-moving tech (AI, frameworks) | 1 year |
| Established tech (databases, OS) | 2 years |
| Fundamental concepts | 5 years |
| Historical/contextual | Any |

### Bias Detection

Check for:
- [ ] Confirmation bias (only finding supporting evidence)
- [ ] Recency bias (overweighting newest info)
- [ ] Authority bias (trusting source over evidence)
- [ ] Selection bias (cherry-picking data)

---

## Comparison Framework

### Evaluation Criteria Template

| Category | Criteria | Weight |
|----------|----------|--------|
| **Functionality** | Features, capabilities | 30% |
| **Usability** | Learning curve, DX | 20% |
| **Performance** | Speed, scalability | 20% |
| **Cost** | Price, TCO | 15% |
| **Support** | Documentation, community | 15% |

### Scoring Scale

| Score | Meaning |
|-------|---------|
| 10 | Best in class, industry standard |
| 8-9 | Excellent, minor weaknesses |
| 6-7 | Good, notable gaps |
| 4-5 | Average, significant limitations |
| 2-3 | Below average, major issues |
| 0-1 | Poor, not viable |

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Research informs implementation | `coding` | Technology choice, integration guide |
| Research informs plan | `planner` | Options analysis, recommendation |
| Research needs documentation | `documentation` | Research report, findings summary |

---

## Examples

### Example 1: Technology Comparison

**Input:**
```
Research and compare PostgreSQL vs MongoDB for a user analytics dashboard
```

**Output:**
```markdown
# Research Report: PostgreSQL vs MongoDB for Analytics

## Executive Summary
For a user analytics dashboard with structured event data and complex queries, **PostgreSQL** is recommended due to superior query capabilities, ACID compliance, and mature analytics extensions.

## Comparison Matrix

| Criteria | PostgreSQL | MongoDB |
|----------|------------|---------|
| Query Complexity | SQL, JOINs, window functions | Aggregation pipeline |
| Schema Flexibility | Rigid (but JSONB available) | Flexible document model |
| Analytics Features | Excellent (window functions, CTEs) | Good (aggregation framework) |
| ACID Compliance | Full | Document-level |
| Horizontal Scaling | Read replicas, sharding (complex) | Native sharding |
| Learning Curve | Moderate (SQL knowledge needed) | Moderate (MongoDB syntax) |
| **Analytics Score** | **9/10** | **7/10** |

## Recommendation

**Recommended:** PostgreSQL

**Rationale:**
- Window functions enable complex analytics natively
- JSONB provides flexibility when needed
- Mature ecosystem with proven analytics tools
- Better for complex joins across user/event tables

**Confidence:** High

## Sources
1. [PostgreSQL Documentation](https://postgresql.org/docs) - 2024
2. [MongoDB Manual](https://mongodb.com/docs) - 2024
3. [Database Benchmark Study](example.com) - 2023
```

### Example 2: Best Practices Research

**Input:**
```
Research best practices for REST API authentication
```

**Output:** Structured report on OAuth 2.0, JWT, API keys with recommendations.

---

## Error Handling

| Issue | Resolution |
|-------|------------|
| Insufficient sources | Flag `[LIMITED_DATA]`, note gaps, proceed with caveats |
| Conflicting information | Present both sides, note uncertainty, suggest validation |
| Topic too broad | Narrow scope, focus on specific aspect, note excluded areas |
| No clear recommendation | Present options with trade-offs, let requester decide |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-22 | Initial Silver Tier implementation |
