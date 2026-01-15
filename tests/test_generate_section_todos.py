"""Tests for generate-section-todos.py script."""

import pytest
import subprocess
import json
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.config import create_session_config


class TestGenerateSectionTodos:
    """Tests for generate-section-todos.py script."""

    @pytest.fixture
    def script_path(self):
        """Return path to generate-section-todos.py."""
        return Path(__file__).parent.parent / "scripts" / "checks" / "generate-section-todos.py"

    @pytest.fixture
    def plugin_root(self):
        """Return path to plugin root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def run_script(self, script_path, plugin_root):
        """Factory fixture to run generate-section-todos.py."""
        def _run(planning_dir: Path, timeout=10):
            """Run the script with given planning directory.

            Creates session config if it doesn't exist.
            """
            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Create session config if needed
            config_path = planning_dir / "deep_plan_config.json"
            if not config_path.exists():
                create_session_config(
                    planning_dir=planning_dir,
                    plugin_root=str(plugin_root),
                    initial_file=str(planning_dir / "spec.md"),
                )

            result = subprocess.run(
                [
                    "uv", "run", str(script_path),
                    "--planning-dir", str(planning_dir),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        return _run

    @pytest.fixture
    def sample_index_content(self):
        """Sample index.md content with SECTION_MANIFEST block."""
        return """<!-- SECTION_MANIFEST
section-01-setup
section-02-api
section-03-database
section-04-integration
END_MANIFEST -->

# Implementation Sections Index

## Sections
"""

    def test_fresh_state_returns_error(self, run_script, tmp_path):
        """Should return error when no sections directory exists."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        result = run_script(planning_dir)

        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["success"] is False
        assert "index.md" in output["error"]
        assert output["state"] == "fresh"
        assert output["todos"] == []

    def test_invalid_index_returns_error(self, run_script, tmp_path):
        """Should return error when index.md has invalid SECTION_MANIFEST."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        # Index without SECTION_MANIFEST block
        (sections_dir / "index.md").write_text("# Index\n\nNo manifest here")

        result = run_script(planning_dir)

        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["success"] is False
        assert output["state"] == "invalid_index"
        assert "SECTION_MANIFEST" in output["error"]
        assert output["todos"] == []

    def test_complete_state_returns_todos_without_sections(self, run_script, tmp_path, sample_index_content):
        """Should return full TODO list when all sections are complete."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        (sections_dir / "index.md").write_text(sample_index_content)
        (sections_dir / "section-01-setup.md").write_text("# Section 1")
        (sections_dir / "section-02-api.md").write_text("# Section 2")
        (sections_dir / "section-03-database.md").write_text("# Section 3")
        (sections_dir / "section-04-integration.md").write_text("# Section 4")

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["state"] == "complete"
        assert output["total_sections"] == 4
        assert output["completed_sections"] == 4
        assert output["missing_sections"] == []

        # Should have full TODO list with "Write section files" (not expanded)
        todo_contents = [t["content"] for t in output["todos"]]
        assert "Write section files" in todo_contents

    def test_has_index_expands_all_sections(self, run_script, tmp_path, plugin_root, sample_index_content):
        """Should expand section TODOs when only index exists."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        (sections_dir / "index.md").write_text(sample_index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["state"] == "has_index"
        assert output["total_sections"] == 4
        assert output["completed_sections"] == 0
        assert len(output["missing_sections"]) == 4

        # Check that section TODOs are in the list
        todo_contents = [t["content"] for t in output["todos"]]
        assert "Read section-splitting.md and write section-01-setup" in todo_contents
        assert "Read section-splitting.md and write section-02-api" in todo_contents
        assert "Read section-splitting.md and write section-03-database" in todo_contents
        assert "Read section-splitting.md and write section-04-integration" in todo_contents

        # "Write section files" should NOT be in the list (replaced)
        assert "Write section files" not in todo_contents

    def test_partial_expands_remaining_sections(self, run_script, tmp_path, sample_index_content):
        """Should include all sections with completed ones marked as such."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        (sections_dir / "index.md").write_text(sample_index_content)
        (sections_dir / "section-01-setup.md").write_text("# Section 1")
        (sections_dir / "section-02-api.md").write_text("# Section 2")
        # section-03 and section-04 are missing

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["state"] == "partial"
        assert output["total_sections"] == 4
        assert output["completed_sections"] == 2
        assert len(output["missing_sections"]) == 2

        # Build a dict of section TODO statuses
        section_todos = {t["content"]: t["status"] for t in output["todos"] if "and write section-" in t["content"]}

        # All sections should be present
        assert "Read section-splitting.md and write section-01-setup" in section_todos
        assert "Read section-splitting.md and write section-02-api" in section_todos
        assert "Read section-splitting.md and write section-03-database" in section_todos
        assert "Read section-splitting.md and write section-04-integration" in section_todos

        # Completed sections should have status "completed"
        assert section_todos["Read section-splitting.md and write section-01-setup"] == "completed"
        assert section_todos["Read section-splitting.md and write section-02-api"] == "completed"

        # Missing sections should have status "pending"
        assert section_todos["Read section-splitting.md and write section-03-database"] == "pending"
        assert section_todos["Read section-splitting.md and write section-04-integration"] == "pending"

    def test_requires_session_config(self, script_path, tmp_path):
        """Should fail if session config doesn't exist."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        # Don't create session config - it should fail
        result = subprocess.run(
            [
                "uv", "run", str(script_path),
                "--planning-dir", str(planning_dir),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["success"] is False
        assert "config" in output["error"].lower()

    def test_section_todos_in_correct_position(self, run_script, tmp_path, sample_index_content):
        """Section TODOs should be in the correct position (replacing 'Write section files')."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        (sections_dir / "index.md").write_text(sample_index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)

        todo_contents = [t["content"] for t in output["todos"]]

        # Find positions
        create_index_pos = todo_contents.index("Create section index")
        section_01_pos = todo_contents.index("Read section-splitting.md and write section-01-setup")
        final_cleanup_pos = todo_contents.index("Final status and cleanup")

        # Section TODOs should be after "Create section index" and before "Final status and cleanup"
        assert create_index_pos < section_01_pos < final_cleanup_pos

    def test_todos_have_required_fields(self, run_script, tmp_path, sample_index_content):
        """All todos should have content, status, and activeForm."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        (sections_dir / "index.md").write_text(sample_index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)

        for todo in output["todos"]:
            assert "content" in todo
            assert "status" in todo
            assert "activeForm" in todo

    def test_section_todos_ordered_by_number(self, run_script, tmp_path):
        """Section TODOs should be in section number order."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        # Manifest has sections out of order (but parser sorts them)
        index_content = """<!-- SECTION_MANIFEST
section-03-third
section-01-first
section-02-second
END_MANIFEST -->
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Extract just the section todos
        section_todos = [t for t in output["todos"] if "and write section-" in t["content"]]

        # Should be sorted by section number
        assert section_todos[0]["content"] == "Read section-splitting.md and write section-01-first"
        assert section_todos[1]["content"] == "Read section-splitting.md and write section-02-second"
        assert section_todos[2]["content"] == "Read section-splitting.md and write section-03-third"

    def test_single_section_plan(self, run_script, tmp_path):
        """Should handle plans with only one section."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
section-01-only
END_MANIFEST -->
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["success"] is True

        section_todos = [t for t in output["todos"] if "and write section-" in t["content"]]
        assert len(section_todos) == 1
        assert section_todos[0]["content"] == "Read section-splitting.md and write section-01-only"
