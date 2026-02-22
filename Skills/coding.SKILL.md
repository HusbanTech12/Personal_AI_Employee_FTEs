# Skill: Coding

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `coding` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Software Development |

---

## Purpose

Generate, modify, debug, and optimize **production-quality code**. This skill:

1. **Implements** features and functionality
2. **Refactors** existing code for clarity and performance
3. **Debugs** issues and fixes bugs
4. **Writes** unit and integration tests
5. **Documents** code with comments and docstrings
6. **Reviews** code for best practices

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Feature Request** | New functionality to build | "Add user login API", "Create data export function" |
| **Bug Report** | Issue to fix | "Null pointer in UserService", "API returns 500 error" |
| **Refactor Request** | Code improvement | "Optimize database queries", "Apply DRY principle" |
| **Code Review** | Review and improve | "Review this PR", "Check for security issues" |
| **Test Creation** | Write tests | "Add unit tests for auth module" |
| **Integration** | Connect systems | "Integrate Stripe payments", "Add Slack webhook" |

**Expected Format:**
```markdown
---
title: Coding Task
status: needs_action
priority: standard
skill: coding
---

## Requirement
Clear description of what needs to be built/fixed

## Context
- Language/Framework
- Existing code (if applicable)
- Constraints

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

---

## Execution Steps

### Step 1: Requirement Analysis

```
Read task description thoroughly
↓
Identify programming language/framework
↓
Note dependencies and constraints
↓
Clarify acceptance criteria
↓
Identify edge cases
```

**Output:** Clear technical specification

### Step 2: Design Approach

```
Determine architecture pattern
↓
Plan module/component structure
↓
Identify interfaces and contracts
↓
Consider error handling strategy
↓
Plan testing approach
```

**Output:** Implementation approach document

### Step 3: Code Implementation

```
Write clean, modular code
↓
Follow language conventions
↓
Add error handling
↓
Include logging where appropriate
↓
Add inline comments for complex logic
```

**Output:** Working code implementation

### Step 4: Code Review (Self)

```
Check code against requirements
↓
Verify error handling is complete
↓
Ensure no hardcoded values
↓
Check for security issues
↓
Verify naming conventions
```

**Output:** Reviewed, polished code

### Step 5: Testing

```
Write unit tests for new code
↓
Write integration tests if applicable
↓
Run existing test suite (if provided)
↓
Fix any failing tests
↓
Verify code coverage
```

**Output:** Test suite + results

### Step 6: Documentation

```
Add docstrings to functions/classes
↓
Update README if new feature
↓
Document API endpoints (if applicable)
↓
Add usage examples
```

**Output:** Documented code

### Step 7: Final Verification

```
Run linter/formatter
↓
Check for TODOs left in code
↓
Verify all acceptance criteria met
↓
Prepare summary of changes
```

**Output:** Ready-to-merge code

---

## Output Format

All coding outputs follow this structure:

```markdown
# Implementation: {Feature Name}

## Summary
Brief description of what was implemented

## Files Created/Modified

### `{path/to/file.py}`
```python
# Complete code with imports, classes, functions
```

### `{path/to/another_file.js}`
```javascript
// Additional code files
```

## Changes Made
- Created: `file1.py` - Description
- Modified: `file2.py` - Description of changes
- Deleted: `file3.py` - Reason (if applicable)

## Testing

### Unit Tests
```python
def test_feature_x():
    assert feature_x() == expected_result
```

### Test Results
```
✓ test_feature_x passed
✓ test_feature_y passed
✓ test_edge_case passed

3/3 tests passed (100%)
```

## Usage Example
```python
from module import feature_x

result = feature_x(param1, param2)
```

## Notes
- Any assumptions made
- Known limitations
- Future improvements

## Acceptance Criteria Status
- [x] Criterion 1 - Implemented in file1.py
- [x] Criterion 2 - Tested in test_file.py
```

---

## Completion Rules

A coding task is **complete** when ALL criteria are met:

### Mandatory Deliverables

- [ ] **Working Code** - Implements all requirements
- [ ] **Error Handling** - Graceful failure modes
- [ ] **Tests** - Unit tests for new functionality
- [ ] **Documentation** - Docstrings and usage examples
- [ ] **Code Quality** - Passes linting/formatting

### Quality Checks

- [ ] Code follows language conventions
- [ ] No hardcoded values (use constants/config)
- [ ] Functions are single-purpose
- [ ] Variable names are descriptive
- [ ] No duplicate code (DRY principle)
- [ ] Security considerations addressed

### Documentation

- [ ] Activity log entry created
- [ ] Dashboard updated
- [ ] Code comments explain "why" not "what"

---

## Code Quality Standards

### General Principles

| Principle | Description |
|-----------|-------------|
| **DRY** | Don't Repeat Yourself - eliminate duplication |
| **KISS** | Keep It Simple, Stupid - prefer simplicity |
| **SOLID** | Follow SOLID design principles |
| **YAGNI** | You Ain't Gonna Need It - avoid over-engineering |

### Security Checklist

- [ ] No hardcoded secrets/API keys
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] Authentication/authorization checks
- [ ] Error messages don't leak sensitive info

### Performance Checklist

- [ ] No unnecessary nested loops
- [ ] Database queries are optimized
- [ ] Caching considered for repeated operations
- [ ] Memory leaks avoided
- [ ] Async I/O where appropriate

---

## Language-Specific Guidelines

### Python

```python
# Follow PEP 8
# Use type hints
# Write docstrings (Google/NumPy style)

def calculate_total(items: list[float], tax_rate: float) -> float:
    """Calculate total cost including tax.
    
    Args:
        items: List of item prices
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%)
    
    Returns:
        Total cost including tax
    """
    subtotal = sum(items)
    tax = subtotal * tax_rate
    return subtotal + tax
```

### JavaScript/TypeScript

```typescript
// Use TypeScript when possible
// Follow Airbnb style guide
// Use async/await for async operations

/**
 * Fetches user data from API
 * @param userId - The user's unique identifier
 * @returns Promise resolving to user data
 */
async function getUserData(userId: string): Promise<User> {
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch user: ${response.status}`);
    }
    return response.json();
}
```

### Shell Scripts

```bash
#!/bin/bash
# Use strict mode
set -euo pipefail

# Document what the script does
# Handle errors gracefully
# Clean up temp files
```

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Code needs planning first | `planner` | Technical requirements, scope |
| Code needs API research | `research` | API options, comparison |
| Code needs documentation | `documentation` | Code overview, usage guide |

---

## Examples

### Example 1: Simple Function

**Input:**
```
Create a Python function that validates email format
```

**Output:**
```python
import re

def validate_email(email: str) -> bool:
    """
    Validate email format using RFC 5322 pattern.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Tests
assert validate_email('user@example.com') == True
assert validate_email('invalid-email') == False
```

### Example 2: API Endpoint

**Input:**
```
Create a Flask endpoint for user registration
```

**Output:**
```python
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash

app = Flask(__name__)

@app.route('/api/users', methods=['POST'])
def register_user():
    """Register a new user account."""
    data = request.get_json()
    
    # Validate required fields
    required = ['email', 'password', 'name']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate email format
    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password strength
    if len(data['password']) < 8:
        return jsonify({'error': 'Password too short'}), 400
    
    # Hash password and create user
    hashed_pw = generate_password_hash(data['password'])
    user = create_user_in_db(
        email=data['email'],
        password=hashed_pw,
        name=data['name']
    )
    
    return jsonify({'id': user.id, 'email': user.email}), 201
```

---

## Error Handling

| Issue | Resolution |
|-------|------------|
| Requirements unclear | Flag `[CLARIFICATION_NEEDED]`, list questions |
| Missing dependencies | Note required packages, suggest installation |
| Security concern found | Flag `[SECURITY_REVIEW]`, explain issue |
| Performance issue found | Flag `[PERFORMANCE_NOTE]`, suggest optimization |
| Breaking change required | Flag `[BREAKING_CHANGE]`, document migration |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-22 | Initial Silver Tier implementation |
