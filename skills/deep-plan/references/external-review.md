# External LLM Review Reference

This step sends `claude-plan.md` to external LLMs (Gemini and/or ChatGPT) for independent review.

The plan is self-contained - reviewers receive all context they need from this single file.

## Prerequisites

Before running external review:
1. Run Context Check Protocol (step 9)
2. Ensure `claude-plan.md` exists and includes full background/context

## Running Reviews

Use the unified review script:

```bash
uv run --directory {plugin_root} \
  scripts/llm_clients/review.py \
  --planning-dir "<planning_dir>"
```

The script automatically:
- Detects which LLMs are available (Gemini, OpenAI, or both)
- Runs available reviewers in parallel (if both) or single-threaded (if one)
- Writes results to `<planning_dir>/reviews/`

### Finding the Script

```
Use Glob to find: "**/deep_plan/scripts/llm_clients/review.py"
```

## Output Format

The script returns JSON:

```json
{
  "reviews": {
    "gemini": {
      "success": true,
      "provider": "gemini",
      "model": "gemini-2.0-flash",
      "auth_method": "vertex_ai_adc",
      "analysis": "... review content ..."
    },
    "openai": {
      "success": true,
      "provider": "openai",
      "model": "gpt-4o",
      "analysis": "... review content ..."
    }
  },
  "files_written": [
    "/path/to/reviews/iteration-1-gemini.md",
    "/path/to/reviews/iteration-1-openai.md"
  ],
  "gemini_available": true,
  "openai_available": true
}
```

## Review Files

Reviews are written to `<planning_dir>/reviews/`:
- `iteration-{N}-gemini.md`
- `iteration-{N}-openai.md`

Where N is the iteration number (default 1, pass `--iteration N` for subsequent rounds).

## Handling Failures

- If one LLM fails, the other still runs
- Failed reviews are recorded in the output JSON with `success: false`
- Review files are still written for failed reviews (containing error info)
- Script exits 0 if at least one review succeeds, 1 if all fail
