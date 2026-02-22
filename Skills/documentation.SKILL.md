# Skill: Documentation

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `documentation` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Technical Writing |

---

## Purpose

Create clear, comprehensive, and user-friendly **technical documentation**. This skill:

1. **Writes** README files, guides, and tutorials
2. **Documents** APIs, architectures, and systems
3. **Creates** onboarding materials and runbooks
4. **Updates** existing documentation for accuracy
5. **Structures** information for easy navigation
6. **Explains** complex concepts in simple terms

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **README Request** | Create project documentation | "Write README for new project", "Update documentation" |
| **API Documentation** | Document endpoints/interfaces | "Document REST API", "Write OpenAPI spec" |
| **User Guide** | Create how-to documentation | "Write user manual", "Create setup guide" |
| **Tutorial** | Step-by-step instructions | "Tutorial for beginners", "Getting started guide" |
| **Architecture Doc** | Document system design | "Architecture overview", "System design doc" |
| **Runbook/SOP** | Operational procedures | "Deployment runbook", "Incident response guide" |
| **Release Notes** | Document changes | "Changelog for v2.0", "Release notes" |

**Expected Format:**
```markdown
---
title: Documentation Task
status: needs_action
priority: standard
skill: documentation
---

## Documentation Type
README / API Guide / Tutorial / Architecture / Other

## Target Audience
Developers / End Users / DevOps / Mixed

## Key Topics to Cover
- Topic 1
- Topic 2

## Existing Materials
Links to code, specs, or reference materials
```

---

## Execution Steps

### Step 1: Audience Analysis

```
Identify target readers
↓
Assess their technical level
↓
Determine their goals
↓
Note their pain points
↓
Define documentation scope
```

**Output:** Audience profile

### Step 2: Information Gathering

```
Collect source materials
↓
Review existing documentation
↓
Interview subject matter experts (if available)
↓
Test the system/feature firsthand
↓
Note gaps in information
```

**Output:** Source material collection

### Step 3: Structure Planning

```
Define document sections
↓
Create outline hierarchy
↓
Plan navigation flow
↓
Identify cross-references needed
↓
Determine visual aids needed
```

**Output:** Document outline

### Step 4: Content Creation

```
Write clear, concise prose
↓
Add code examples where relevant
↓
Include diagrams/visuals (ASCII or descriptions)
↓
Write descriptive headings
↓
Add tables for structured info
```

**Output:** First draft

### Step 5: Review & Refine

```
Check technical accuracy
↓
Verify all steps work (for tutorials)
↓
Ensure consistent terminology
↓
Remove jargon or define it
↓
Check readability and flow
```

**Output:** Reviewed draft

### Step 6: Formatting & Polish

```
Apply consistent formatting
↓
Add table of contents (if long)
↓
Include navigation links
↓
Add metadata (title, version, date)
↓
Proofread for grammar/spelling
```

**Output:** Polished document

### Step 7: Validation

```
Test any code examples
↓
Verify all links work
↓
Check images/diagrams render
↓
Ensure accessibility (alt text, etc.)
↓
Get feedback if possible
```

**Output:** Validated documentation

---

## Output Format

All documentation outputs follow this structure:

```markdown
# {Document Title}

## Overview
Brief description of what this document covers

## Table of Contents
- [Section 1](#section-1)
- [Section 2](#section-2)

## Section 1: {Title}

Content with clear explanations...

### Subsection

More detailed information...

```python
# Code example with syntax highlighting
def example():
    pass
```

## Section 2: {Title}

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data | Data | Data |

## Appendix

### Glossary
| Term | Definition |
|------|------------|
| Term | Definition |

### References
- [Related Doc 1](link)
- [Related Doc 2](link)
```

---

## Completion Rules

A documentation task is **complete** when ALL criteria are met:

### Mandatory Deliverables

- [ ] **Complete Content** - All requested topics covered
- [ ] **Clear Structure** - Logical organization with headings
- [ ] **Examples** - Code snippets or usage examples where relevant
- [ ] **Navigation** - Table of contents or section links
- [ ] **Accuracy** - Technical information verified

### Quality Checks

- [ ] Writing is clear and concise
- [ ] No unexplained jargon
- [ ] Consistent terminology throughout
- [ ] Code examples are tested and working
- [ ] Formatting is consistent

### Documentation

- [ ] Activity log entry created
- [ ] Dashboard updated
- [ ] Document saved in appropriate location

---

## Documentation Quality Standards

### Writing Principles

| Principle | Description |
|-----------|-------------|
| **Clarity** | Use simple, direct language |
| **Conciseness** | Say more with less, avoid fluff |
| **Completeness** | Cover all necessary information |
| **Correctness** | Ensure technical accuracy |
| **Consistency** | Use consistent terms and formatting |

### Readability Guidelines

- Use active voice ("Click the button" not "The button should be clicked")
- Keep sentences under 25 words when possible
- Use bullet points for lists (3+ items)
- Include examples for abstract concepts
- Define acronyms on first use

### Code Example Standards

```markdown
✓ DO: Include context before the example
✓ DO: Use meaningful variable names
✓ DO: Add comments for complex logic
✓ DO: Show expected output
✗ DON'T: Use foo/bar without explanation
✗ DON'T: Leave TODOs in examples
```

---

## Documentation Types

### README Template

```markdown
# Project Name

Brief description (1-2 sentences)

## Features

- Feature 1
- Feature 2

## Quick Start

```bash
# Installation command
npm install package-name

# Basic usage
command --option value
```

## Usage

Detailed usage examples...

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | number | 3000 | Server port |

## Development

```bash
# Clone repository
git clone repo-url

# Install dependencies
npm install

# Run tests
npm test
```

## Contributing

Guidelines for contributions...

## License

MIT / Apache / etc.
```

### API Documentation Template

```markdown
# API Reference

## Authentication

Explain authentication method...

## Endpoints

### GET /resource

Description of endpoint...

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Resource ID |

**Response:**

```json
{
  "id": "123",
  "name": "Example"
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 404 | Not found |
| 500 | Server error |
```

### Tutorial Template

```markdown
# Tutorial: {Topic}

## Prerequisites

- Requirement 1
- Requirement 2

## What You'll Build

Description of final outcome...

## Step 1: Setup

Instructions with commands...

## Step 2: Implementation

Code examples...

## Step 3: Testing

How to verify it works...

## Conclusion

Summary and next steps...

## Complete Code

Full working example...
```

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Doc requires code samples | `coding` | Working code for examples |
| Doc requires research | `research` | Source materials, references |
| Doc is part of project plan | `planner` | Documentation milestones |

---

## Examples

### Example 1: README Creation

**Input:**
```
Write a README for a new Python CLI tool that converts Markdown to HTML
```

**Output:**
```markdown
# md2html

Convert Markdown files to HTML from the command line.

## Installation

```bash
pip install md2html
```

## Quick Start

```bash
# Convert a single file
md2html input.md -o output.html

# Convert multiple files
md2html *.md -o ./dist/
```

## Features

- Fast conversion with zero dependencies
- Support for GitHub-flavored Markdown
- Syntax highlighting for code blocks
- Custom CSS templates

## Usage

### Basic Conversion

```bash
md2html README.md
```

### With Custom Output

```bash
md2html input.md -o docs/output.html
```

### Batch Conversion

```bash
md2html docs/*.md -o ./dist/
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output file or directory |
| `--template` | `-t` | CSS template to use |
| `--watch` | `-w` | Watch for file changes |

## License

MIT
```

### Example 2: API Documentation

**Input:**
```
Document the user authentication API endpoints
```

**Output:** Structured API reference with all endpoints, parameters, and examples.

---

## Error Handling

| Issue | Resolution |
|-------|------------|
| Missing information | Flag `[INFO_NEEDED]`, list specific gaps |
| Unclear requirements | Flag `[CLARIFICATION_NEEDED]`, suggest options |
| Outdated source material | Note date, flag `[VERIFY_NEEDED]` |
| Complex topic | Break into multiple documents, create overview |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-22 | Initial Silver Tier implementation |
