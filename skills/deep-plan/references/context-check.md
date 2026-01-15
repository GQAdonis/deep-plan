# Context Check Protocol

Before critical operations, optionally prompt the user about compacting context.

## Quick Check: TODO Context Item

After step 4 (setup-planning-session), the TODO list includes a context item:
```
context_check_enabled=true   (or false)
```

**If `context_check_enabled=false`**: Skip context checks entirely - proceed with the operation.

**If `context_check_enabled=true`**: then proceed with the instructions below

## Running the Script

If context_check_enabled=true or if you are unsure what the user wants, run the script below:

```bash
uv run {plugin_root}/scripts/checks/check-context-decision.py \
  --planning-dir "<planning_dir>" \
  --upcoming-operation "<operation_name>"
```

## Handling Script Output

| action | What to do |
|--------|------------|
| `skip` | Prompts disabled - proceed immediately |
| `prompt` | Use AskUserQuestion with `prompt.message` and `prompt.options` |

### If User Chooses "Compact first"

Wait for user to run `/compact` and say "continue", then re-run the current workflow step. The workflow's resume logic will pick up from the correct point.

## When to Run Context Checks

- Before External LLM Review (upcoming operation: "External LLM Review")
- Before Section Split (upcoming operation: "Section splitting")
- Between sections during section generation (upcoming operation: "Write next section")

## Configuration

In `config.json`:
```json
{
  "context": {
    "check_enabled": true
  }
}
```

Set `check_enabled` to `false` to skip all context prompts.
