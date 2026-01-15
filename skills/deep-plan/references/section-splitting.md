# Section File Writing

Write individual section files from the plan. This step assumes `sections/index.md` already exists (created in step 18).

## Input Files

- `<planning_dir>/claude-plan.md` - implementation details
- `<planning_dir>/claude-plan-tdd.md` - test stubs mirroring plan structure
- `<planning_dir>/sections/index.md` - section definitions and dependencies

## Output

```
<planning_dir>/sections/
├── index.md (already exists)
├── section-01-<name>.md
├── section-02-<name>.md
└── ...
```


## Step 1: Iteration Loop

Section writing is a loop. Each iteration:

```
┌─────────────────────────────────────────────────────┐
│  ITERATION LOOP                                     │
│                                                     │
│  1. check-sections.py → get next_section            │
│  2. Decide if you need to refresh your memory:      │
│     a. <planning_dir>/claude-plan.md                │
│     b. <planning_dir>/claude-plan-tdd.md            │
│     c. <planning_dir>/sections/index.md             │
│  3. If unsure whether to refresh memory,            │
│     read all three files                            │
│  4. Write section file(s)                           │
│  5. Mark TODO complete                              │
│  6. Context check → prompt user if enabled          │
│  7. If more sections remain → goto 1                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 1.1 Check State

Run the check-sections script:

```bash
uv run {plugin_root}/scripts/checks/check-sections.py --planning-dir "<planning_dir>"
```

Output:
```json
{
  "state": "has_index" | "partial" | "complete",
  "defined_sections": ["section-01-setup", "section-02-api", ...],
  "completed_sections": ["section-01-setup"],
  "missing_sections": ["section-02-api", ...],
  "next_section": "section-02-api",
  "progress": "1/4"
}
```

**Based on state:**
- `has_index` → Start writing from first defined section
- `partial` → Resume from `next_section`
- `complete` → Done, exit loop

### 1.2 Write Section File(s)

For the next section (or batch of sections):

1. Read `claude-plan.md`, `claude-plan-tdd.md`, and `index.md` if needed
2. Write `section-NN-<name>.md` combining:
   - Test stubs from `claude-plan-tdd.md` (tests come FIRST)
   - Implementation details from `claude-plan.md`

**Batching is fine** - you can write multiple sections before the context check.

**IMPORTANT: Each section file must be completely self-contained.** The implementer reading a section file should NOT need to reference `claude-plan.md`, `claude-plan-tdd.md`, or any other document. They should be able to read the single section file, create a TODO list, and start implementing immediately without any outside context.

Include all necessary background, requirements, and implementation details within each section - don't assume the reader has seen the original plan.

### 1.3 Mark TODO Complete

After writing each section file, mark its corresponding TODO as completed via TodoWrite.

### 1.4 Context Check

Check `context_check_enabled` in TODO context items. If `false`, skip to step 1.5.

If `true` or unsure about this value, see [context-check.md](context-check.md). Run the check script with upcoming operation "Write next section".

If user chooses "Compact first", wait for them to run `/compact` and say "continue", then restart from step 1.1 of the loop. The state check will return `partial` with the correct `next_section`.

### 1.5 Loop Until Complete

Continue the iteration loop until `check-sections.py` returns `state: "complete"`.
