# impl-feature

Plan and implement a complete feature end-to-end (design -> code -> tests -> docs -> demo) in its own branch.

## Arguments

$ARGUMENTS

Parse the following from the arguments:

- **feature_name**: `<kebab-case short name>` — used for branch name and doc file
- **scope**: `<ui|api|fullstack|agent|infra>` — which layers to touch
- **acceptance_criteria**: bullet list or Gherkin-style text defining "done"
- **tech_constraints**: (optional) stack limits, required integrations, library restrictions
- **priority**: `<p0|p1|p2>` — urgency level
- **perf_targets**: (optional) latency, throughput, memory goals
- **security_notes**: (optional) auth, encryption, compliance requirements

---

## Process

### 1. Understand & Plan
- Summarize the inputs back to confirm understanding.
- Write a **mini-PRD**: problem statement, target users, success metrics, constraints, risks.
- Outline the **architecture**: components, data model, APIs, sequence diagram (Mermaid OK).
- Define **acceptance tests** derived from the acceptance criteria.

### 2. Branch & Optional Worktree
- Create and checkout the feature branch:
  ```bash
  git checkout -b ai-feature/${feature_name}
  ```
- If parallel work is beneficial, create a git worktree:
  ```bash
  git worktree add ../vision-audio-ai-${feature_name} ai-feature/${feature_name}
  ```
- Work inside the branch/worktree for all changes.

### 3. Implementation
- Modify all necessary layers according to the **scope**.
- Keep **atomic Conventional Commits** (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
- Follow SOLID principles. Keep files small and modular.
- For major choices, list 2-3 alternatives with pros/cons before proceeding.

### 4. Tests
- Create or extend **unit + integration tests** matching acceptance criteria.
- Ensure the test command passes. Provide the exact command:
  ```bash
  # Example
  pytest tests/ -v --tb=short
  ```

### 5. Verification
- Build and run the application locally.
- Perform local smoke tests.
- Write a short **demo script** with commands and URLs.

### 6. Docs
- Update `README.md` with new feature information.
- Add `docs/${feature_name}.md` with: overview, architecture, endpoints, env vars, usage.
- Update `CHANGELOG.md` with an entry under Added/Changed/Removed.

### 7. Deliverables
- Provide a summary block:

```
## IMPLEMENTED
- [list of changes made]

## TESTED
- [test results and coverage]

## HOW TO RUN
- [exact commands to start, test, and demo]

## TRADEOFFS & FOLLOW-UPS
- [known limitations and future work]
```

---

## Error Handling

- On build/test failures: show logs, propose fixes, and retry.
- For missing information: make clearly labeled `ASSUMPTION`s, explain the assumption, and document how to change it later.
- If a task is too large for one pass, break it into incremental sub-tasks that each end in a testable, committable state.

---

## Output Requirements

- Branch `ai-feature/${feature_name}` containing code, tests, and docs.
- Summary block at the end: IMPLEMENTED | TESTED | HOW TO RUN.
- Fact Check List for any high-risk assumptions.
- A single runnable automation artifact (script or Makefile target) if multi-step setup is needed.

---

## Example Invocation

```
/impl-feature feature_name=image-preprocessing scope=api acceptance_criteria="- Accepts image upload via POST /api/preprocess\n- Supports min-max and z-score normalization\n- Returns normalized image as base64\n- Handles BGR/RGB/HSV conversions\n- Returns 400 on invalid input" priority=p0 perf_targets="<200ms per image at 1080p"
```
