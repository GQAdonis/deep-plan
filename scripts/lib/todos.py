"""Shared TODO list generation for deep-plan workflow.

Used by both setup-planning-session.py and generate-section-todos.py.
"""

# Canonical TODO list - single source of truth
# Each tuple: (content, activeForm, step_number)
# Steps 0-4 = setup, Steps 6-21 = workflow (step 5 removed after consolidation)
TODO_ITEMS = [
    ("Check context / offer compaction", "Checking context", 0),
    ("Print intro and validate environment", "Validating environment", 1),
    ("Handle environment errors", "Handling environment errors", 2),
    ("Validate spec file input", "Validating spec file input", 3),
    ("Setup planning session", "Setting up planning session", 4),
    ("Research decision", "Deciding on research approach", 6),
    ("Execute research", "Executing research", 7),
    ("Detailed interview", "Conducting detailed interview", 8),
    ("Save interview transcript", "Saving interview transcript", 9),
    ("Write initial spec", "Writing initial spec", 10),
    ("Generate implementation plan", "Generating implementation plan", 11),
    ("Context check (pre-review)", "Checking context (pre-review)", 12),
    ("External LLM review", "Running external LLM review", 13),
    ("Integrate external feedback", "Integrating external feedback", 14),
    ("User review of integrated plan", "Waiting for user review", 15),
    ("Apply TDD approach", "Applying TDD approach", 16),
    ("Context check (pre-split)", "Checking context (pre-split)", 17),
    ("Create section index", "Creating section index", 18),
    ("Generate section TODOs", "Generating section TODOs", 19),
    ("Write section files", "Writing section files", 20),
    ("Final status and cleanup", "Finalizing status and cleanup", 21),
    ("Output summary", "Outputting summary", 22),
]

STEP_NAMES = {
    0: "Context check",
    1: "Print intro and validate environment",
    2: "Handle environment errors",
    3: "Validate spec file input",
    4: "Setup planning session",
    6: "Research decision",
    7: "Execute research",
    8: "Detailed interview",
    9: "Save interview transcript",
    10: "Write initial spec",
    11: "Generate implementation plan",
    12: "Context check (pre-review)",
    13: "External LLM review",
    14: "Integrate external feedback",
    15: "User review of integrated plan",
    16: "Apply TDD approach",
    17: "Context check (pre-split)",
    18: "Create section index",
    19: "Generate section TODOs",
    20: "Write section files",
    21: "Final status and cleanup",
    22: "Output summary",
}

# The TODO items that get replaced with section-specific TODOs
GENERATE_SECTION_TODOS_CONTENT = "Generate section TODOs"
GENERATE_SECTION_TODOS_STEP = 19
WRITE_SECTIONS_CONTENT = "Write section files"
WRITE_SECTIONS_STEP = 20


def generate_todos(
    current_step: int,
    section_todos: list[dict] | None = None,
    plugin_root: str | None = None,
    planning_dir: str | None = None,
    initial_file: str | None = None,
    context_check_enabled: bool | None = None,
) -> list[dict]:
    """Generate TODO list with appropriate status for each item.

    Args:
        current_step: The step we're currently at (or resuming from)
        section_todos: Optional list of section-specific TODOs to insert.
                      When provided, replaces both "Generate section TODOs"
                      and "Write section files" placeholders with the
                      individual section TODOs.
        plugin_root: Path to plugin root (prepended as context item)
        planning_dir: Path to planning directory (prepended as context item)
        initial_file: Path to initial spec file (prepended as context item)
        context_check_enabled: Whether context prompts are enabled (prepended as context item)

    Returns:
        List of TODO items ready for TodoWrite
    """
    todos = []

    # Prepend context items (paths and settings) as completed items at the top
    # These provide persistent context that Claude can reference throughout
    if plugin_root:
        todos.append({
            "content": f"plugin_root={plugin_root}",
            "status": "completed",
            "activeForm": "Context: plugin_root",
        })
    if planning_dir:
        todos.append({
            "content": f"planning_dir={planning_dir}",
            "status": "completed",
            "activeForm": "Context: planning_dir",
        })
    if initial_file:
        todos.append({
            "content": f"initial_file={initial_file}",
            "status": "completed",
            "activeForm": "Context: initial_file",
        })
    if context_check_enabled is not None:
        todos.append({
            "content": f"context_check_enabled={str(context_check_enabled).lower()}",
            "status": "completed",
            "activeForm": "Context: context_check_enabled",
        })

    for content, active_form, step in TODO_ITEMS:
        # If we have section_todos, replace both placeholder items:
        # - "Generate section TODOs" gets skipped entirely
        # - "Write section files" gets replaced with individual section TODOs
        if section_todos is not None:
            if content == GENERATE_SECTION_TODOS_CONTENT:
                continue  # Skip this placeholder
            if content == WRITE_SECTIONS_CONTENT:
                todos.extend(section_todos)
                continue  # Replace with section todos

        # Determine status based on current step
        if step < current_step:
            status = "completed"
        elif step == current_step:
            status = "in_progress"
        else:
            status = "pending"

        todos.append({
            "content": content,
            "status": status,
            "activeForm": active_form,
        })

    return todos


def generate_section_todo_items(
    all_sections: list[str],
    completed_sections: list[str],
) -> list[dict]:
    """Generate TODO items for all sections with appropriate status.

    Args:
        all_sections: List of all section names (in order)
        completed_sections: List of section names that are already complete

    Returns:
        List of TODO items for all sections (completed ones marked as such)
    """
    completed_set = set(completed_sections)
    todos = []
    for section_name in all_sections:
        status = "completed" if section_name in completed_set else "pending"
        todos.append({
            "content": f"Read section-splitting.md and write {section_name}",
            "status": status,
            "activeForm": f"Writing {section_name}",
        })
    return todos
