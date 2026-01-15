"""Shared pytest fixtures for deep-plan tests."""

import pytest
import json
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config(fixtures_dir):
    """Load sample config for testing."""
    config_path = fixtures_dir / "sample_config.json"
    return json.loads(config_path.read_text())


@pytest.fixture
def sample_prompts_dir(fixtures_dir):
    """Return path to sample prompts directory."""
    return fixtures_dir / "sample_prompts"


@pytest.fixture
def sample_plan_content(fixtures_dir):
    """Load sample plan content for testing."""
    plan_path = fixtures_dir / "sample_plan.md"
    return plan_path.read_text()


@pytest.fixture
def mock_env(monkeypatch):
    """Factory fixture to set environment variables."""
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
    return _set_env
