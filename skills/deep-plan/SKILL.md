---
name: deep-plan
description: Creates detailed, sectionized, TDD-oriented implementation plans through research, stakeholder interviews, and multi-LLM review. Use when planning features that need thorough pre-implementation analysis.
license: MIT
compatibility: Requires uv (Python 3.11+), Gemini or OpenAI API key for external review
---

# Deep Planning Skill

Orchestrates a multi-step planning process: Research → Interview → External LLM Review → TDD Plan

## CRITICAL: First Actions

**BEFORE using any other tools**, do these in order:

### 1. Print Intro and Validate Environment

Print intro banner immediately:
```
⚠️  CONTEXT WARNING: This workflow is token-intensive. Consider compacting first.

═══════════════════════════════════════════════════════════════
DEEP-PLAN: AI-Assisted Implementation Planning
═══════════════════════════════════════════════════════════════
Research → Interview → External LLM Review → TDD Plan

DEEP-PLAN starts by running `validate-env.sh`. This script:
  - Checks env for external LLM auth values
  - Validates external LLM access by running tiny prompt(s) programmatically

SECURITY:
  - `validate-env.sh` reads secret auth values in order to validate LLM access
  - It never publishes these values or exposes them to claude
  
 Note: DEEP-PLAN will write many .md files to the planning directory you pass it
```

**Find and run validate-env.sh:**
```bash
find "$(pwd)" -path "*/deep_plan/scripts/checks/validate-env.sh" -type f 2>/dev/null | head -1
```

```bash
bash <script_path>
```

**Parse the JSON output:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "gemini_auth": "api_key",
  "openai_auth": true,
  "plugin_root": "/path/to/plugin"
}
```

**Store `plugin_root`** - it's used throughout the workflow.

### 2. Handle Environment Errors

If `valid == false`:
- Show the errors to the user
- Use AskUserQuestion: "Exit to fix credentials?" → "Exit" / "Continue anyway"
- If "Exit", stop the workflow

```
Environment validated:
  Gemini: {gemini_auth or "not configured"}
  OpenAI: {openai_auth ? "configured" : "not configured"}
```

### 3. Validate Spec File Input

**Check if user provided @file at invocation AND it's a spec file (ends with `.md`).**

If NO @file was provided OR the path doesn't end with `.md`, output this and STOP:
```
═══════════════════════════════════════════════════════════════
DEEP-PLAN: Spec File Required
═══════════════════════════════════════════════════════════════

This skill requires a markdown spec file path (must end with .md).
The planning directory is inferred from the spec file's parent directory.

To start a NEW plan:
  1. Create a markdown spec file describing what you want to build
  2. It can be as detailed or as vague as you like
  3. Place it in a directory where deep-plan can save planning files
  4. Run: /deep-plan @path/to/your-spec.md

To RESUME an existing plan:
  1. Run: /deep-plan @path/to/your-spec.md

Example: /deep-plan @planning/my-feature-spec.md
═══════════════════════════════════════════════════════════════
```
**Do not continue. Wait for user to re-invoke with a .md file path.**

### 4. Setup Planning Session

Run setup-planning-session.py with the spec file and plugin root:
```bash
uv run {plugin_root}/scripts/checks/setup-planning-session.py \
  --file "<file_path>" \
  --plugin-root "{plugin_root}"
```

**Parse the JSON output:**

This script:
1. Validates the spec file exists and has content
2. Creates `deep_plan_config.json` in the planning directory with `plugin_root`, `planning_dir`, and `initial_file`
3. Detects whether this is a new or resume session
4. Generates the TODO list

**If `success == false`:** The script failed validation. Display the error and stop:
```
═══════════════════════════════════════════════════════════════
DEEP-PLAN: Setup Failed
═══════════════════════════════════════════════════════════════
Error: {error}

Please fix the issue and re-run: /deep-plan @path/to/your-spec.md
═══════════════════════════════════════════════════════════════
```
**Do not continue. Wait for user to fix the issue and re-invoke.**

Common errors:
- "Spec file not found" → User provided a path to a file that doesn't exist
- "Spec file is empty" → User provided an empty file with no content
- "Expected a spec file, got a directory" → User provided a directory path instead of a file

**The session config (`deep_plan_config.json`)** stores paths for subsequent scripts, so you don't need to pass them repeatedly.

**Pass `todos` array directly to TodoWrite.**

Print status:
```
Planning directory: {planning_dir}
Mode: {mode}
```

If `mode == "resume"`:
```
Resuming from step {resume_from_step}
To start fresh, delete the planning directory files.
```

If resuming, **skip to step {resume_from_step}** in the workflow below.

---

## Logging Format

```
═══════════════════════════════════════════════════════════════
STEP {N}/22: {STEP_NAME}
═══════════════════════════════════════════════════════════════
{details}
Step {N} complete: {summary}
───────────────────────────────────────────────────────────────
```

Prefixes: `STEP` `OK` `...` `FILE` `SEARCH` `WARN` `ERROR` `SAVED` `STATS`

---

## Workflow

**Note:** All scripts use `{plugin_root}` from step 1's validate-env.sh output.

### 6. Research Decision

See [research-protocol.md](references/research-protocol.md).

1. Read the spec file (from `initial_file` in TODO context items)
2. Extract potential research topics from the spec content (technologies, patterns, integrations)
3. Ask user about codebase research needs (existing code to analyze?)
4. Ask user about web research needs (present derived topics as multi-select options)
5. Record which research types to perform in step 7

**Always include testing** - either research existing test setup (codebase) or ask about preferences (new project).

### 7. Execute Research

See [research-protocol.md](references/research-protocol.md).

Based on decisions from step 6, launch research subagents:
- **Codebase research:** `Task(subagent_type=Explore)`
- **Web research:** `Task(subagent_type=web-search-researcher)`

If both are needed, launch both Task tools in parallel (single message with multiple tool calls).

**Important:** Subagents return their findings - they do NOT write files directly. After collecting results from all subagents, combine them and write to `<planning_dir>/claude-research.md`.

Skip this step entirely if user chose no research in step 6.

### 8. Detailed Interview

See [interview-protocol.md](references/interview-protocol.md)

Run in main context (AskUserQuestion requires it). The interview should be informed by:
- The initial spec (from `initial_file`)
- Research findings (from step 7, if any research was done)

### 9. Save Interview Transcript

Write Q&A to `<planning_dir>/claude-interview.md`

### 10. Write Initial Spec

Combine into `<planning_dir>/claude-spec.md`:
- **Initial input** (read the file from `initial_file` in the TODO list)
- **Research findings** (if step 7 was done)
- **Interview answers** (from step 8)

This synthesizes the user's raw requirements into a complete specification.

### 11. Generate Implementation Plan

Create detailed plan → `<planning_dir>/claude-plan.md`

**IMPORTANT**: Write for an unfamiliar reader. The plan must be fully self-contained - an engineer or LLM with no prior context should understand *what* we're building, *why*, and *how* just from reading this document. Don't write for yourself or the user; write for a stranger who will pick this up cold.

### 12. Context Check (Pre-External Review)

Check `context_check_enabled` in TODO context items. If `false`, skip to step 13.

If `true` or unsure about this value, see [context-check.md](references/context-check.md). Run the check script with upcoming operation "External LLM Review". If user chooses "Compact first", wait for them to compact and say "continue", then resume from this step.

### 13. External LLM Review

See [external-review.md](references/external-review.md)

Run unified review script (handles parallelism internally):
```bash
uv run --directory {plugin_root} scripts/llm_clients/review.py --planning-dir "<planning_dir>"
```

### 14. Integrate External Feedback

Analyze the suggestions in `<planning_dir>/reviews/`.

Remember that you are the authority on what to integrate or not. It's OK if you decide to not integrate anything.

**Step 1:** Write `<planning_dir>/claude-integration-notes.md` documenting:
- What suggestions you're integrating and why
- What suggestions you're NOT integrating and why

**Step 2:** Update `<planning_dir>/claude-plan.md` with the integrated changes.

### 15. User Review of Integrated Plan

Use AskUserQuestion:
```
The plan has been updated with external feedback. You can now review and edit claude-plan.md.

If you want Claude's help editing the plan, open a separate Claude session - this session
is mid-workflow and can't assist with edits until the workflow completes.

When you're done reviewing, select "Done" to continue.
```

Options: "Done reviewing"

Wait for user confirmation before proceeding.

### 16. Apply TDD Approach

See [tdd-approach.md](references/tdd-approach.md)

Verify testing context exists in `claude-research.md`. If missing, research (existing codebase) or recommend (new project). Then create `claude-plan-tdd.md` mirroring the plan structure with test stubs for each section.

### 17. Context Check (Pre-Section Split)

Check `context_check_enabled` in TODO context items. If `false`, skip to step 18.

If `true` or unsure about this value, see [context-check.md](references/context-check.md). Run the check script with upcoming operation "Section splitting". If user chooses "Compact first", wait for them to compact and say "continue", then resume from this step.

### 18. Create Section Index

See [section-index.md](references/section-index.md)

Read `claude-plan.md` and `claude-plan-tdd.md`. Identify natural section boundaries and create `<planning_dir>/sections/index.md`.

**CRITICAL:** index.md MUST start with a SECTION_MANIFEST block. See the reference for format requirements and examples.

Write `index.md` before proceeding to section file creation.

### 19. Generate Section TODOs

Run generate-section-todos.py to expand section-specific TODOs:
```bash
uv run {plugin_root}/scripts/checks/generate-section-todos.py \
  --planning-dir "<planning_dir>"
```

**Parse the JSON output** and handle based on result:
- If `success == false`: Read `error` and fix the issue (likely invalid index.md or missing config). Re-run until successful.
- If `state == "complete"`: All sections already written, skip to step 21.
- Otherwise: **Pass the entire `todos` array to TodoWrite** to replace the generic placeholders with individual section TODOs.

### 20. Write Section Files

See [section-splitting.md](references/section-splitting.md)

Follow the iteration loop until all sections are complete.

### 21. Final Status & Cleanup

Verify all section files were created successfully by running `check-sections.py` one final time. Confirm state is "complete".

### 22. Output Summary

Print generated files and next steps.
