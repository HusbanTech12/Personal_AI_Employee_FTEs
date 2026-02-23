# Skill: Autonomy Loop (Ralph Wiggum Loop)

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `autonomy_loop` |
| **Tier** | Gold+ |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Meta-Skill / Orchestration |
| **Pattern** | Plan → Execute → Validate → Recover → Retry |

---

## Purpose

Enable autonomous multi-step task execution with self-recovery capabilities. This meta-skill:

1. **Plans** complex multi-step tasks
2. **Executes** steps sequentially or in parallel
3. **Validates** each step completion
4. **Recovers** from failures automatically
5. **Retries** failed steps with adjusted approach
6. **Continues** from partial completion state

---

## The Ralph Wiggum Loop

```
while goal_not_complete:
    plan()       # Generate/adjust plan
    execute()    # Run current step
    validate()   # Check step success
    recover()    # Handle failures
    retry()      # Retry with adjustments
```

Named after the autonomous execution pattern that keeps going until the goal is achieved.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Autonomy Loop Agent                          │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │   PLAN      │ → │  EXECUTE    │ → │  VALIDATE   │          │
│  │  Generator  │   │   Engine    │   │   Checker   │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│         ↑                                      │               │
│         │                                      ▼               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │   RETRY     │ ← │  RECOVER    │ ← │   FAILED    │          │
│  │  Manager    │   │   Handler   │   │   State     │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              State Persistence (JSON)                    │   │
│  │  • Current step  • Completed steps  • Failed attempts   │   │
│  │  • Variables     • Dependencies     • Recovery history  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Execution States

| State | Description | Transition |
|-------|-------------|------------|
| `planning` | Generating execution plan | → `executing` |
| `executing` | Running current step | → `validating` |
| `validating` | Checking step success | → `complete` or `failed` |
| `failed` | Step failed validation | → `recovering` |
| `recovering` | Attempting recovery | → `retrying` |
| `retrying` | Preparing retry attempt | → `executing` |
| `complete` | Goal achieved | Terminal |
| `blocked` | Cannot proceed | Terminal (requires intervention) |

---

## Step Definition

```yaml
step_id: unique_identifier
name: Human-readable name
action: skill/action to execute
dependencies: [step_id_1, step_id_2]  # Must complete first
inputs:  # Variables from previous steps
  - from: step_id
    variable: output_value
outputs:  # Values to store for later steps
  - variable: result
    extract: $.path.to.value
retry_policy:
  max_attempts: 3
  backoff: exponential
  timeout: 300
validation:
  type: output_exists | custom | api_check
  condition: validation_logic
```

---

## Execution Flow

### Phase 1: Planning

```
Read goal/task definition
↓
Break into atomic steps
↓
Identify dependencies
↓
Create execution graph
↓
Store plan in state
```

### Phase 2: Execution

```
Load current step from state
↓
Check dependencies complete
↓
Gather inputs from previous steps
↓
Execute step action
↓
Store outputs in state
```

### Phase 3: Validation

```
Run validation check
↓
If pass → Mark step complete, move to next
↓
If fail → Set failed state, trigger recovery
```

### Phase 4: Recovery

```
Analyze failure reason
↓
Determine recovery strategy:
  - Retry same action
  - Try alternative approach
  - Skip if optional
  - Request human intervention
↓
Update retry count
↓
Apply backoff delay
```

### Phase 5: Retry

```
Load previous step inputs
↓
Apply recovery adjustments
↓
Re-execute step
↓
Return to validation
```

---

## Retry Policies

### Fixed Backoff
```yaml
retry_policy:
  max_attempts: 3
  backoff: fixed
  delay_seconds: 10
```

### Exponential Backoff
```yaml
retry_policy:
  max_attempts: 5
  backoff: exponential
  base_delay: 5
  max_delay: 300
```

### Linear Backoff
```yaml
retry_policy:
  max_attempts: 5
  backoff: linear
  delay_increment: 30
```

---

## Recovery Strategies

| Strategy | When to Use | Action |
|----------|-------------|--------|
| `retry` | Transient failures | Retry same action |
| `alternative` | Known alternatives exist | Try different approach |
| `skip` | Optional step | Mark complete, continue |
| `partial` | Partial success acceptable | Store partial output |
| `escalate` | Cannot recover | Request human help |

---

## State Persistence

### State File Structure

```json
{
  "goal": "Task goal description",
  "status": "executing",
  "created_at": "2026-02-24T10:00:00",
  "updated_at": "2026-02-24T10:05:00",
  "current_step": "step_3",
  "steps": {
    "step_1": {
      "status": "complete",
      "attempts": 1,
      "outputs": {"result": "value"},
      "completed_at": "2026-02-24T10:01:00"
    },
    "step_2": {
      "status": "complete",
      "attempts": 2,
      "outputs": {"result": "value"},
      "recovery": {
        "strategy": "retry",
        "reason": "timeout"
      },
      "completed_at": "2026-02-24T10:03:00"
    },
    "step_3": {
      "status": "executing",
      "attempts": 1,
      "started_at": "2026-02-24T10:04:00"
    }
  },
  "variables": {
    "shared_var": "value"
  },
  "recovery_history": [
    {
      "step": "step_2",
      "attempt": 1,
      "error": "timeout",
      "strategy": "retry",
      "timestamp": "2026-02-24T10:02:00"
    }
  ]
}
```

---

## Dependency Handling

### Sequential Dependencies
```yaml
steps:
  - step_id: fetch_data
    action: api_request
    
  - step_id: process_data
    action: transform
    dependencies: [fetch_data]
    inputs:
      - from: fetch_data
        variable: response
    
  - step_id: save_results
    action: file_write
    dependencies: [process_data]
    inputs:
      - from: process_data
        variable: transformed
```

### Parallel Execution
```yaml
steps:
  - step_id: fetch_users
    action: api_request
    parallel_group: A
    
  - step_id: fetch_orders
    action: api_request
    parallel_group: A
    
  - step_id: merge_data
    action: merge
    dependencies: [fetch_users, fetch_orders]
```

---

## Partial Completion Recovery

When a step partially succeeds:

```yaml
step_id: bulk_import
action: import_records
validation:
  type: custom
  condition: success_rate > 0.8
recovery:
  on_partial:
    strategy: retry_failed_only
    inputs:
      failed_records: $.failed
```

---

## Examples

### Example 1: Multi-Step Data Pipeline

```yaml
goal: Import and process customer data

steps:
  - step_id: extract
    action: database_query
    outputs:
      - variable: raw_data
    
  - step_id: transform
    action: data_transform
    dependencies: [extract]
    inputs:
      - from: extract
        variable: raw_data
    retry_policy:
      max_attempts: 3
      backoff: exponential
    
  - step_id: validate
    action: data_validation
    dependencies: [transform]
    inputs:
      - from: transform
        variable: transformed
    
  - step_id: load
    action: database_insert
    dependencies: [validate]
    inputs:
      - from: transform
        variable: transformed
```

### Example 2: Content Publishing Workflow

```yaml
goal: Create and publish blog post

steps:
  - step_id: generate_content
    action: ai_generate
    outputs:
      - variable: draft
    
  - step_id: review
    action: content_review
    dependencies: [generate_content]
    inputs:
      - from: generate_content
        variable: draft
    
  - step_id: publish
    action: cms_publish
    dependencies: [review]
    retry_policy:
      max_attempts: 5
      backoff: exponential
```

---

## Error Handling

| Error Type | Recovery Action |
|------------|-----------------|
| Timeout | Retry with increased timeout |
| Rate Limit | Exponential backoff |
| Validation Fail | Adjust inputs, retry |
| Dependency Fail | Wait and retry |
| System Error | Retry with backoff |
| Business Logic | Escalate to human |

---

## Monitoring

### Loop Metrics

```json
{
  "total_steps": 10,
  "completed_steps": 7,
  "failed_steps": 1,
  "retry_count": 5,
  "recovery_count": 3,
  "execution_time_seconds": 300,
  "success_rate": 0.875
}
```

### Progress Tracking

```
[████████████████░░░░] 70% - Step 7/10
Current: save_results (executing)
Failed: validate_format (recovered)
```

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Step requires approval | `approval` | Step details for approval |
| Step needs external API | `automation_mcp` | API request details |
| Step needs human help | Escalation | Context and error details |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial autonomy loop implementation |
