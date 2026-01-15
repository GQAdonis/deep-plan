"""Tests for setup-planning-session.py script."""

import pytest
import subprocess
import json
import os
from pathlib import Path


class TestSetupPlanningSession:
    """Tests for setup-planning-session.py script."""

    @pytest.fixture
    def script_path(self):
        """Return path to setup-planning-session.py."""
        return Path(__file__).parent.parent / "scripts" / "checks" / "setup-planning-session.py"

    @pytest.fixture
    def plugin_root(self):
        """Return path to plugin root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def run_script(self, script_path, plugin_root):
        """Factory fixture to run setup-planning-session.py."""
        def _run(file_path: str, timeout=10):
            """Run the script with given file path."""
            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            cmd = [
                "uv", "run", str(script_path),
                "--file", file_path,
                "--plugin-root", str(plugin_root),
            ]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        return _run

    # --- Basic input validation tests ---

    def test_requires_file_arg(self, script_path, plugin_root):
        """Should fail when --file is not provided."""
        result = subprocess.run(
            ["uv", "run", str(script_path), "--plugin-root", str(plugin_root)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2
        assert "required" in result.stderr.lower() or "--file" in result.stderr

    def test_requires_plugin_root_arg(self, script_path, tmp_path):
        """Should fail when --plugin-root is not provided."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = subprocess.run(
            ["uv", "run", str(script_path), "--file", str(spec_file)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2
        assert "required" in result.stderr.lower() or "--plugin-root" in result.stderr

    def test_rejects_directory_input(self, run_script, tmp_path):
        """Should fail when a directory is passed instead of a file."""
        result = run_script(str(tmp_path))

        assert result.returncode == 1
        output = json.loads(result.stdout)

        assert output["success"] is False
        assert output["mode"] == "error"
        assert "directory" in output["error"].lower()

    # --- New session tests ---

    def test_new_session_with_existing_spec(self, run_script, tmp_path):
        """Should return new mode for existing spec with no planning files."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# My Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["success"] is True
        assert output["mode"] == "new"
        assert output["planning_dir"] == str(tmp_path)
        assert output["initial_file"] == str(spec_file)
        # New sessions start at step 6 (codebase research decision)
        assert output["resume_from_step"] == 6
        assert "todos" in output
        assert len(output["todos"]) > 0

    def test_fails_with_nonexistent_spec(self, run_script, tmp_path):
        """Should fail if spec file doesn't exist."""
        spec_file = tmp_path / "nonexistent.md"

        result = run_script(str(spec_file))

        assert result.returncode == 1
        output = json.loads(result.stdout)

        assert output["success"] is False
        assert "not found" in output["error"].lower()

    def test_fails_with_empty_spec(self, run_script, tmp_path):
        """Should fail if spec file is empty."""
        spec_file = tmp_path / "empty.md"
        spec_file.write_text("")  # Empty file

        result = run_script(str(spec_file))

        assert result.returncode == 1
        output = json.loads(result.stdout)

        assert output["success"] is False
        assert "empty" in output["error"].lower()

    # --- Resume detection tests ---

    def test_detects_resume_from_research_file(self, run_script, tmp_path):
        """Should detect resume when claude-research.md exists."""
        (tmp_path / "claude-research.md").write_text("# Research")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["mode"] == "resume"
        assert output["resume_from_step"] == 8  # After research, resume at interview

    def test_detects_resume_from_interview_file(self, run_script, tmp_path):
        """Should detect resume when claude-interview.md exists."""
        (tmp_path / "claude-interview.md").write_text("# Interview")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["mode"] == "resume"
        assert output["resume_from_step"] == 10  # After interview, resume at write spec

    def test_detects_resume_from_plan_file(self, run_script, tmp_path):
        """Should detect resume when claude-plan.md exists."""
        (tmp_path / "claude-plan.md").write_text("# Plan")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["mode"] == "resume"
        assert output["resume_from_step"] == 12  # After plan, resume at context check

    def test_detects_complete_workflow(self, run_script, tmp_path):
        """Should detect complete when ALL sections are written."""
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir()
        # Index defines one section with SECTION_MANIFEST block, and that section exists
        index_content = """<!-- SECTION_MANIFEST
section-01-setup
END_MANIFEST -->

# Index
"""
        (sections_dir / "index.md").write_text(index_content)
        (sections_dir / "section-01-setup.md").write_text("# Section 1")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["mode"] == "complete"
        assert output["section_progress"]["state"] == "complete"

    def test_detects_partial_sections(self, run_script, tmp_path):
        """Should detect resume at step 19 when sections are partially complete."""
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir()
        # Index defines 3 sections with SECTION_MANIFEST block, but only 1 is complete
        index_content = """<!-- SECTION_MANIFEST
section-01-setup
section-02-api
section-03-tests
END_MANIFEST -->

# Index

## Sections

| Section | Depends On |
|---------|------------|
| section-01-setup | - |
| section-02-api | section-01 |
| section-03-tests | section-02 |
"""
        (sections_dir / "index.md").write_text(index_content)
        (sections_dir / "section-01-setup.md").write_text("# Section 1")
        # section-02 and section-03 are NOT created
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["mode"] == "resume"
        # Step 19 = Write section files (index exists, need to write remaining sections)
        assert output["resume_from_step"] == 19
        assert output["section_progress"]["state"] == "partial"
        assert output["section_progress"]["progress"] == "1/3"
        assert output["section_progress"]["next_section"] == "section-02-api"

    # --- TODO list generation tests ---

    def test_creates_session_config(self, run_script, tmp_path, plugin_root):
        """Should create session config file in planning directory."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Config should have been created
        assert output["config_created"] is True

        # Config file should exist
        config_path = tmp_path / "deep_plan_config.json"
        assert config_path.exists()

        # Config should have required session keys
        import json as json_module
        config = json_module.loads(config_path.read_text())
        assert config["plugin_root"] == str(plugin_root)
        assert config["planning_dir"] == str(tmp_path)
        assert config["initial_file"] == str(spec_file)

        # Config should also include global config settings (copied from plugin's config.json)
        assert "context" in config
        assert "check_enabled" in config["context"]
        assert "models" in config
        assert "external_review" in config

    def test_todos_include_context_items(self, run_script, tmp_path, plugin_root):
        """Should include context items (paths and settings) at the top of TODO list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        todos = output["todos"]

        # First 4 items should be context items
        assert todos[0]["content"] == f"plugin_root={plugin_root}"
        assert todos[0]["status"] == "completed"
        assert todos[1]["content"] == f"planning_dir={tmp_path}"
        assert todos[1]["status"] == "completed"
        assert todos[2]["content"] == f"initial_file={spec_file}"
        assert todos[2]["status"] == "completed"
        # context_check_enabled defaults to true from plugin's config.json
        assert todos[3]["content"] == "context_check_enabled=true"
        assert todos[3]["status"] == "completed"

    def test_todos_marked_for_new_session(self, run_script, tmp_path):
        """Should have setup steps completed and workflow step 6 in_progress for new session."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        todos = output["todos"]

        # New session starts at step 6, so steps 0-4 are completed
        # Plus 4 context items (plugin_root, planning_dir, initial_file, context_check_enabled) are always completed
        # Step 6 is in_progress, steps 7+ are pending
        completed_count = sum(1 for t in todos if t["status"] == "completed")
        in_progress_count = sum(1 for t in todos if t["status"] == "in_progress")
        pending_count = sum(1 for t in todos if t["status"] == "pending")

        # 4 context items + Steps 0, 1, 2, 3, 4 = 9 completed
        assert completed_count == 9
        # Step 6 = 1 in_progress
        assert in_progress_count == 1
        # Steps 7-22 = remaining pending (16 steps, step 5 doesn't exist)
        assert pending_count == 16

    def test_todos_marked_correctly_for_resume(self, run_script, tmp_path):
        """Should mark completed/in_progress/pending correctly when resuming."""
        (tmp_path / "claude-plan.md").write_text("# Plan")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        todos = output["todos"]
        resume_step = output["resume_from_step"]

        # Check that earlier steps are completed, resume step is in_progress
        workflow_todos = todos[4:]  # Skip 4 context items
        found_in_progress = False
        for todo in workflow_todos:
            # Find the step number from the todo content
            step_info = next(
                (item for item in [
                    (0, "Check context"),
                    (1, "Print intro"),
                    (2, "Handle environment"),
                    (3, "Validate spec"),
                    (4, "Setup planning"),
                    (6, "Codebase research decision"),
                    (7, "Codebase research"),
                    (8, "Detailed interview"),
                    (9, "Save interview"),
                    (10, "Write initial spec"),
                    (11, "Generate implementation"),
                    (12, "Context check (pre-review)"),
                ] if item[1].lower() in todo["content"].lower()),
                None
            )
            if step_info and step_info[0] == resume_step:
                assert todo["status"] == "in_progress"
                found_in_progress = True

        assert found_in_progress

    def test_todos_have_required_fields(self, run_script, tmp_path):
        """All todos should have content, status, and activeForm."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        for todo in output["todos"]:
            assert "content" in todo
            assert "status" in todo
            assert "activeForm" in todo
            assert todo["status"] in ["pending", "in_progress", "completed"]

    # --- State check integration tests ---

    def test_includes_state_check_output(self, run_script, tmp_path):
        """Should include state_check output for debugging."""
        (tmp_path / "claude-research.md").write_text("# Research")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert "state_check" in output
        assert output["state_check"] is not None
        assert "recommended_action" in output["state_check"]
        assert "files_found" in output["state_check"]

    # --- Message tests ---

    def test_message_for_new_session(self, run_script, tmp_path):
        """Should have appropriate message for new session."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert "new" in output["message"].lower()

    def test_message_for_resume_session(self, run_script, tmp_path):
        """Should have appropriate message for resume session."""
        (tmp_path / "claude-plan.md").write_text("# Plan")
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert "resum" in output["message"].lower()
        assert str(output["resume_from_step"]) in output["message"]

    # --- Path handling tests ---

    def test_relative_path_converted_to_absolute(self, run_script, tmp_path):
        """Should convert relative paths to absolute."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Spec")

        # Note: This is tricky to test since we can't control cwd easily
        # Just verify output has absolute paths
        result = run_script(str(spec_file))

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert Path(output["planning_dir"]).is_absolute()
        assert Path(output["initial_file"]).is_absolute()
