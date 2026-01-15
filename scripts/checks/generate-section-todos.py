#!/usr/bin/env python3
"""Generate section-specific TODOs for the deep-plan workflow.

This script generates the complete TODO list with section-specific items
expanded in place of "Write section files". It's called at step 19 after
index.md is validated.

Reads plugin_root and initial_file from the session config file
(deep_plan_config.json) in the planning directory.

Usage:
    uv run generate-section-todos.py --planning-dir "/path/to/planning"

Output:
    JSON with todos array ready to pass to TodoWrite, plus metadata.
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.config import load_session_config, ConfigError
from lib.sections import check_section_progress
from lib.todos import (
    GENERATE_SECTION_TODOS_STEP,
    generate_todos,
    generate_section_todo_items,
)


def generate_section_todos(planning_dir: Path, session_config: dict) -> dict:
    """Generate TODO list with section-specific items expanded.

    Args:
        planning_dir: Path to the planning directory
        session_config: Session config dict with plugin_root, planning_dir, initial_file

    Returns:
        dict with:
        - success: bool
        - error: error message if failed
        - todos: complete TODO list with sections expanded
        - state: current section state
        - total_sections: number of defined sections
        - completed_sections: number of completed sections
        - missing_sections: list of sections that need TODOs
    """
    # Extract paths and settings from session config for TODO context items
    plugin_root = session_config.get("plugin_root")
    config_planning_dir = session_config.get("planning_dir")
    initial_file = session_config.get("initial_file")
    context_check_enabled = session_config.get("context", {}).get("check_enabled", True)

    # Get section progress
    progress = check_section_progress(planning_dir)

    state = progress["state"]

    # Handle fresh state - no index exists
    if state == "fresh":
        return {
            "success": False,
            "error": "No sections/index.md found. Create the section index first (step 18).",
            "todos": [],
            "state": state,
            "total_sections": 0,
            "completed_sections": 0,
            "missing_sections": [],
        }

    # Handle invalid index
    if state == "invalid_index":
        index_format = progress.get("index_format", {})
        error_msg = index_format.get("error", "SECTION_MANIFEST block is invalid")
        return {
            "success": False,
            "error": f"Invalid index.md: {error_msg}",
            "todos": [],
            "state": state,
            "total_sections": 0,
            "completed_sections": 0,
            "missing_sections": [],
        }

    # Handle complete state - no section TODOs needed
    if state == "complete":
        # Generate todos without section expansion (will just have "Write section files")
        todos = generate_todos(
            current_step=GENERATE_SECTION_TODOS_STEP,
            section_todos=None,
            plugin_root=plugin_root,
            planning_dir=config_planning_dir,
            initial_file=initial_file,
            context_check_enabled=context_check_enabled,
        )
        return {
            "success": True,
            "error": None,
            "todos": todos,
            "state": state,
            "total_sections": len(progress["defined_sections"]),
            "completed_sections": len(progress["completed_sections"]),
            "missing_sections": [],
        }

    # Generate section-specific TODOs for all sections (completed ones marked as such)
    all_sections = progress["defined_sections"]
    completed_sections = progress["completed_sections"]
    section_todos = generate_section_todo_items(all_sections, completed_sections)

    # Generate complete TODO list with sections expanded
    todos = generate_todos(
        current_step=GENERATE_SECTION_TODOS_STEP,
        section_todos=section_todos,
        plugin_root=plugin_root,
        planning_dir=config_planning_dir,
        initial_file=initial_file,
        context_check_enabled=context_check_enabled,
    )

    return {
        "success": True,
        "error": None,
        "todos": todos,
        "state": state,
        "total_sections": len(all_sections),
        "completed_sections": len(completed_sections),
        "missing_sections": progress["missing_sections"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate section-specific TODOs for deep-plan workflow"
    )
    parser.add_argument(
        "--planning-dir",
        required=True,
        type=Path,
        help="Path to planning directory"
    )
    args = parser.parse_args()

    # Load session config (setup-planning-session.py should have created it)
    try:
        session_config = load_session_config(args.planning_dir)
    except ConfigError as e:
        result = {
            "success": False,
            "error": f"Session config not found. Run setup-planning-session.py first. Error: {e}",
            "todos": [],
            "state": "error",
            "total_sections": 0,
            "completed_sections": 0,
            "missing_sections": [],
        }
        print(json.dumps(result, indent=2))
        return 1

    result = generate_section_todos(args.planning_dir, session_config)
    print(json.dumps(result, indent=2))

    # Exit with error code if not successful
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
