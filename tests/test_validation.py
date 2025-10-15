"""Test model metadata validation."""

from pathlib import Path


def test_validate_script_exists(scripts_dir):
    """Test that validate_model_metadata.py exists."""
    validation_script = scripts_dir / "utilities" / "validate_model_metadata.py"
    assert validation_script.exists(), "validate_model_metadata.py not found"


def test_validation_can_be_imported(project_root):
    """Test that validation script can be imported (has valid Python syntax)."""
    import sys

    sys.path.insert(0, str(project_root / "scripts" / "utilities"))

    try:
        import validate_model_metadata

        assert hasattr(validate_model_metadata, "ModelValidator")
        assert hasattr(validate_model_metadata, "main")
    finally:
        sys.path.pop(0)


def test_validator_required_fields():
    """Test that ModelValidator has correct required fields defined."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "utilities"))

    try:
        from validate_model_metadata import ModelValidator

        required_fields = ModelValidator.REQUIRED_METADATA_FIELDS
        assert "model_name" in required_fields
        assert "version" in required_fields
        assert "base_model" in required_fields
        assert "label_map" in required_fields
    finally:
        sys.path.pop(0)


def test_validator_finds_main_model(main_model_dir, models_dir):
    """Test that validator finds the main production model."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "utilities"))

    try:
        from validate_model_metadata import ModelValidator

        validator = ModelValidator(models_dir)
        model_dirs = validator.find_model_directories()

        # Check that main model is in the list
        main_model_found = any(str(main_model_dir) in str(model_dir) for model_dir in model_dirs)
        assert main_model_found, f"Main model not found in validation: {main_model_dir}"
    finally:
        sys.path.pop(0)


def test_validator_validates_main_model(main_model_dir, models_dir):
    """Test that validator validates the main model correctly."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "utilities"))

    try:
        from validate_model_metadata import ModelValidator

        validator = ModelValidator(models_dir)
        result = validator.validate_model(main_model_dir)

        assert result is not None
        assert "status" in result
        assert "errors" in result
        assert "warnings" in result

        # Main model should have minimal errors
        # (may have warnings for missing optional fields)
        assert result["status"] in ["valid", "warning"], (
            f"Main model validation failed with status: {result['status']}"
        )
    finally:
        sys.path.pop(0)
