# test-suite

Create or extend an automated test suite (unit, integration, e2e) and wire it into CI if requested.

## Arguments

$ARGUMENTS

Parse the following from the arguments:

- **target**: file path, module, or feature area to test (e.g., `src/preprocessing/`, `audio-pipeline`)
- **coverage_goal**: target coverage percentage (e.g., `80%`, `90%`)
- **test_kinds**: comma-separated list of test types: `unit`, `integration`, `e2e`, `smoke`, `load`
- **ci_provider**: (optional) CI system to integrate with: `github-actions`, `gitlab-ci`, `none`
- **seed_data**: (optional) path to fixtures, sample data, or instructions for generating test data

---

## Process

### 1. Inventory Existing Tests
- Scan the target path for existing test files.
- List current test coverage and identify which modules/functions lack tests.
- Report: `X tests found, Y modules untested, Z% estimated coverage`.

### 2. Identify Gaps
- Map acceptance criteria or public APIs to test cases.
- Prioritize gaps by risk: critical paths first, edge cases second, happy paths third.
- Produce a test plan table:

| Module / Function | Test Type | Status | Priority |
|---|---|---|---|
| `preprocess_image()` | unit | MISSING | HIGH |
| `POST /api/preprocess` | integration | EXISTS | — |

### 3. Write Tests
- Add tests following the project's existing test patterns and conventions.
- Use descriptive test names: `test_<what>_<condition>_<expected>`.
- Include:
  - **Happy path** tests for core functionality.
  - **Error/edge case** tests (invalid input, boundary values, empty data).
  - **Integration tests** for cross-module interactions.
- Group tests logically by module or feature.

### 4. Fixtures & Teardown
- Create reusable fixtures for common test data (images, audio files, model weights).
- Ensure proper teardown: clean temp files, reset state, close connections.
- If `seed_data` is provided, integrate it into fixtures.

### 5. Test Scripts
- Add or update test runner scripts:
  ```bash
  # Example entries
  pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
  ```
- Add convenience scripts (npm scripts, Makefile targets, or shell scripts) for:
  - `test` — run all tests
  - `test:unit` — unit tests only
  - `test:integration` — integration tests only
  - `test:coverage` — run with coverage report

### 6. CI Configuration (if requested)
- Generate CI config for the specified provider:
  - **github-actions**: `.github/workflows/test.yml`
  - **gitlab-ci**: `.gitlab-ci.yml`
- Include: install deps, run linter, run tests, upload coverage.
- Use caching for dependencies to speed up CI runs.

### 7. Run & Summarize
- Execute the full test suite.
- Report results:

```
## TEST RESULTS
- Total: X tests
- Passed: Y
- Failed: Z
- Coverage: N%

## NEW TESTS ADDED
- [list of new test files and what they cover]

## COMMANDS
- Run all: `pytest tests/ -v`
- Run unit: `pytest tests/unit/ -v`
- Coverage: `pytest --cov=src --cov-report=html`

## GAPS REMAINING
- [any untested areas and why]
```

---

## Output Requirements

- New test files in the appropriate `tests/` directory structure.
- Updated test runner scripts or Makefile targets.
- CI config file (if `ci_provider` specified).
- Coverage report path documented.
- Summary block with results and commands.

---

## Example Invocation

```
/test-suite target=src/vision/preprocessing coverage_goal=85% test_kinds=unit,integration ci_provider=github-actions
```
