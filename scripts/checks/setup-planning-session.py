#!/usr/bin/env python3
"""Setup planning session for deep-plan workflow.

Combined script that:
1. Validates the spec file input
2. Determines the planning directory (parent of spec file)
3. Creates the planning directory if needed
4. Checks planning state to determine new vs resume (including section progress)
5. Generates the TODO list

Usage:
    uv run setup-planning-session.py --file "/path/to/spec.md" --plugin-root "/path/to/plugin"
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.config import get_or_create_session_config, ConfigError
from lib.sections import check_section_progress
from lib.todos import TODO_ITEMS, STEP_NAMES, generate_todos


def scan_planning_files(planning_dir: Path) -> dict:
    """Scan planning directory for existing files."""
    files = {
        "research": (planning_dir / "claude-research.md").exists(),
        "interview": (planning_dir / "claude-interview.md").exists(),
        "spec": (planning_dir / "claude-spec.md").exists(),
        "plan": (planning_dir / "claude-plan.md").exists(),
        "integration_notes": (planning_dir / "claude-integration-notes.md").exists(),
        "plan_tdd": (planning_dir / "claude-plan-tdd.md").exists(),
        "reviews": [],
        "sections": [],
        "sections_index": False,
    }

    # Check for review files
    reviews_dir = planning_dir / "reviews"
    if reviews_dir.exists():
        files["reviews"] = [f.name for f in reviews_dir.glob("*.md")]

    # Check for section files
    sections_dir = planning_dir / "sections"
    if sections_dir.exists():
        files["sections"] = [f.name for f in sections_dir.glob("section-*.md")]
        files["sections_index"] = (sections_dir / "index.md").exists()

    return files


def infer_resume_step(files: dict, section_progress: dict) -> tuple[int | None, str]:
    """Infer which step to resume from based on files and section progress.

    Returns (resume_step, last_completed_description).
    Returns (None, "complete") if workflow is complete.
    Returns (6, "none") if fresh start.

    Step mapping (from SKILL.md):
    - 7: Execute research -> claude-research.md
    - 9: Save interview -> claude-interview.md
    - 10: Write spec -> claude-spec.md
    - 11: Generate plan -> claude-plan.md
    - 13: External review -> reviews/*.md
    - 14: Integrate feedback -> claude-integration-notes.md
    - 16: TDD approach -> claude-plan-tdd.md
    - 18: Create section index -> sections/index.md
    - 19: Generate section TODOs
    - 20: Write section files -> sections/section-*.md
    - Complete: ALL sections written (not just index.md)
    """
    # Check sections state - this is the final stage
    if files["sections_index"]:
        section_state = section_progress["state"]

        if section_state == "complete":
            # All sections written - workflow complete
            return None, "complete"
        elif section_state in ("partial", "has_index"):
            # Index exists, sections started but not complete - resume at step 19
            # (generate section TODOs, which will show progress)
            progress = section_progress["progress"]
            next_section = section_progress["next_section"]
            return 19, f"sections {progress}, next: {next_section}"

    # Check in reverse order (highest step first) for pre-section stages
    if files["sections"]:
        # Has section files but no index - resume at 18 to create index
        return 18, "section files exist but no index"

    if files["plan_tdd"]:
        # TDD plan done - resume at 17 (context check before split)
        return 17, "TDD plan complete"

    if files["integration_notes"]:
        # Integration done - resume at 15 (user review)
        return 15, "feedback integrated"

    if files["reviews"]:
        # Reviews done - resume at 14 (integrate feedback)
        return 14, "external review complete"

    if files["plan"]:
        # Plan done - resume at 12 (context check before review)
        return 12, "implementation plan complete"

    if files["spec"]:
        # Spec done - resume at 11 (generate plan)
        return 11, "spec complete"

    if files["interview"]:
        # Interview done - resume at 10 (write spec)
        return 10, "interview complete"

    if files["research"]:
        # Research done - resume at 8 (interview)
        return 8, "research complete"

    # No files - fresh start at step 6
    return 6, "none"


def build_files_summary(files: dict, section_progress: dict) -> list[str]:
    """Build a list of found files for display."""
    summary = []
    if files["research"]:
        summary.append("claude-research.md")
    if files["interview"]:
        summary.append("claude-interview.md")
    if files["spec"]:
        summary.append("claude-spec.md")
    if files["plan"]:
        summary.append("claude-plan.md")
    if files["integration_notes"]:
        summary.append("claude-integration-notes.md")
    if files["plan_tdd"]:
        summary.append("claude-plan-tdd.md")
    if files["reviews"]:
        summary.append(f"reviews/ ({len(files['reviews'])} files)")
    if files["sections"] or files["sections_index"]:
        progress = section_progress["progress"]
        state = section_progress["state"]
        if state == "complete":
            summary.append(f"sections/ ({progress} complete)")
        elif files["sections_index"]:
            summary.append(f"sections/ ({progress}, {state})")
        else:
            count = len(files['sections'])
            summary.append(f"sections/ ({count} files, no index)")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Setup planning session for deep-plan workflow")
    parser.add_argument(
        "--file",
        required=True,
        help="Path to spec file (planning dir is inferred from parent)"
    )
    parser.add_argument(
        "--plugin-root",
        required=True,
        help="Path to plugin root directory"
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    plugin_root = Path(args.plugin_root)

    # Handle relative paths
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    # Spec file must exist (it's the input to the planning workflow)
    if not file_path.exists():
        result = {
            "success": False,
            "error": f"Spec file not found: {file_path}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1

    # Check if it's a directory (not allowed)
    if file_path.is_dir():
        result = {
            "success": False,
            "error": f"Expected a spec file, got a directory: {file_path}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1

    # Spec file must have content
    if file_path.stat().st_size == 0:
        result = {
            "success": False,
            "error": f"Spec file is empty: {file_path}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1

    # Planning dir is always the parent of the spec file
    # (parent must exist since the file exists)
    planning_dir = file_path.parent

    # Create or validate session config
    try:
        session_config, config_created = get_or_create_session_config(
            planning_dir=planning_dir,
            plugin_root=str(plugin_root),
            initial_file=str(file_path),
        )
    except ConfigError as e:
        result = {
            "success": False,
            "error": f"Session config error: {e}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1

    # Scan for existing planning files
    files_found = scan_planning_files(planning_dir)

    # Check section progress (needed for accurate completion detection)
    section_progress = check_section_progress(planning_dir)

    # Infer resume step from files and section progress
    resume_step, last_completed = infer_resume_step(files_found, section_progress)

    # Build files summary
    files_summary = build_files_summary(files_found, section_progress)

    # Determine mode
    if resume_step is None:
        mode = "complete"
    elif resume_step == 6 and not files_summary:
        mode = "new"
    else:
        mode = "resume"

    # Build message
    if mode == "resume":
        step_name = STEP_NAMES.get(resume_step, f"Step {resume_step}")
        message = f"Resuming from step {resume_step} ({step_name}). Last completed: {last_completed}"
    elif mode == "complete":
        message = "Planning workflow complete - all sections written"
    elif not file_path.exists():
        message = f"Starting new session. Spec file will be created: {file_path}"
    else:
        message = f"Starting new planning session in: {planning_dir}"

    # Generate TODO list
    # Use step 6 as default for new sessions, or 22 for complete
    current_step = resume_step if resume_step is not None else 22
    context_check_enabled = session_config.get("context", {}).get("check_enabled", True)
    todos = generate_todos(
        current_step=current_step,
        plugin_root=str(plugin_root),
        planning_dir=str(planning_dir),
        initial_file=str(file_path),
        context_check_enabled=context_check_enabled,
    )

    # Build state_check for backward compatibility
    state_check = {
        "planning_dir_exists": planning_dir.exists(),
        "planning_dir": str(planning_dir),
        "files_found": files_found,
        "files_summary": files_summary,
        "recommended_action": mode if mode != "new" else "fresh",
        "resume_from_step": resume_step,
        "message": message,
        "section_progress": section_progress,
    }

    result = {
        "success": True,
        "mode": mode,
        "planning_dir": str(planning_dir),
        "initial_file": str(file_path),
        "plugin_root": str(plugin_root),
        "resume_from_step": resume_step,
        "config_created": config_created,
        "message": message,
        "state_check": state_check,
        "section_progress": section_progress,
        "todos": todos,
    }

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
