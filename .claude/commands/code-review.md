# code-review

Structured, example-driven code review for architecture, correctness, security, performance, and maintainability.

## Arguments

$ARGUMENTS

Parse the following from the arguments:

- **paths**: file paths or directories to review (comma-separated)
- **style_examples**: (optional) paths to exemplary files whose style/conventions should be matched
- **severity_threshold**: minimum severity to report: `critical`, `high`, `medium`, `low` (default: `medium`)

---

## Process

### 1. Learn Style from Examples
- If `style_examples` are provided, read those files first.
- Identify the core design style, coding conventions, naming patterns, and architectural principles.
- Use these as the baseline for evaluation — not generic rules, but **this project's** standards.
- If no examples are provided, infer conventions from the existing codebase.

### 2. Review Against Checklist

For each file in `paths`, evaluate against these dimensions:

#### Architecture & Design
- [ ] Single Responsibility: does each module/class/function have one clear purpose?
- [ ] Separation of Concerns: are layers (data, logic, presentation) properly separated?
- [ ] Dependency management: are dependencies explicit and minimal?
- [ ] Modularity: could components be swapped or tested independently?

#### Correctness
- [ ] Does the code do what it claims (docstrings, comments, function names)?
- [ ] Edge cases handled (null, empty, boundary values, concurrent access)?
- [ ] Error handling: are errors caught, logged, and propagated appropriately?
- [ ] Resource cleanup: files closed, connections released, temp data cleaned?

#### Security
- [ ] No hardcoded secrets, API keys, or credentials.
- [ ] Input validation and sanitization on all external inputs.
- [ ] SQL injection, XSS, command injection prevention.
- [ ] Proper authentication/authorization checks.
- [ ] Sensitive data not logged or exposed in error messages.

#### Performance
- [ ] Algorithm complexity appropriate for expected data sizes.
- [ ] No unnecessary I/O, network calls, or database queries in loops.
- [ ] Caching used where beneficial.
- [ ] Memory management: no obvious leaks, large allocations handled.
- [ ] For ML/AI: tensor operations vectorized, GPU utilization considered.

#### Maintainability
- [ ] Code is readable without excessive comments.
- [ ] Naming is clear and consistent with project conventions.
- [ ] Functions are appropriately sized (< 50 lines preferred).
- [ ] Test coverage exists for critical paths.
- [ ] No dead code, unused imports, or commented-out blocks.

### 3. Produce Issues with Suggested Patches

For each issue found at or above `severity_threshold`, output:

```
### [SEVERITY] Issue Title
**File:** `path/to/file.py:42`
**Category:** Security | Performance | Correctness | Architecture | Maintainability

**Problem:**
Brief description of what's wrong and why it matters.

**Current Code:**
<relevant code snippet>

**Suggested Fix:**
<patched code snippet>

**Impact:** What breaks or degrades if not fixed.
```

### 4. Summarize by Severity

```
## Review Summary

| Severity | Count | Categories |
|----------|-------|------------|
| CRITICAL | X | ... |
| HIGH | X | ... |
| MEDIUM | X | ... |
| LOW | X | ... |

### Top Priorities
1. [Most important fix and why]
2. [Second priority]
3. [Third priority]

### Positive Observations
- [Things done well that should be preserved/replicated]
```

### 5. Output PR Comment

Generate a ready-to-paste PR review comment in markdown format that can be directly posted to a pull request.

---

## Output Requirements

- Issue list organized by severity.
- Suggested patches for each issue (copy-pasteable).
- Summary table with counts by severity and category.
- Ready-to-paste PR comment.
- Positive observations (what's done well).

---

## Example Invocation

```
/code-review paths=src/vision/preprocessing.py,src/audio/feature_extraction.py style_examples=src/vision/motion_analyzer.py severity_threshold=medium
```
