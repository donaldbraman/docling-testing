"""Shared test fixtures for docling-testing."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def models_dir(project_root) -> Path:
    """Return the models directory."""
    return project_root / "models"


@pytest.fixture
def data_dir(project_root) -> Path:
    """Return the data directory."""
    return project_root / "data"


@pytest.fixture
def scripts_dir(project_root) -> Path:
    """Return the scripts directory."""
    return project_root / "scripts"


@pytest.fixture
def main_model_dir(models_dir) -> Path:
    """Return the main production model directory."""
    return models_dir / "doclingbert-v2-rebalanced" / "final_model"


@pytest.fixture
def corpus_file(data_dir) -> Path:
    """Return the main corpus file."""
    return data_dir / "clean_7class_corpus.csv"
