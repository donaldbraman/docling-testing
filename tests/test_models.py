"""Test model loading and basic inference."""

import json

import pytest


def test_main_model_directory_exists(main_model_dir):
    """Test that the main production model directory exists."""
    assert main_model_dir.exists(), f"Main model directory not found: {main_model_dir}"
    assert main_model_dir.is_dir(), f"Main model path is not a directory: {main_model_dir}"


def test_label_map_exists(main_model_dir):
    """Test that label_map.json exists in the main model."""
    label_map_path = main_model_dir / "label_map.json"
    assert label_map_path.exists(), "label_map.json not found in main model"


def test_label_map_structure(main_model_dir):
    """Test that label_map.json has the expected structure."""
    label_map_path = main_model_dir / "label_map.json"

    with open(label_map_path) as f:
        metadata = json.load(f)

    # Check required fields
    assert "model_name" in metadata, "Missing 'model_name' in label_map.json"
    assert "version" in metadata, "Missing 'version' in label_map.json"
    assert "base_model" in metadata, "Missing 'base_model' in label_map.json"
    assert "label_map" in metadata, "Missing 'label_map' in label_map.json"

    # Check types
    assert isinstance(metadata["model_name"], str)
    assert isinstance(metadata["version"], str)
    assert isinstance(metadata["base_model"], str)
    assert isinstance(metadata["label_map"], dict)


def test_label_map_has_7_classes(main_model_dir):
    """Test that the main model has 7 classes."""
    label_map_path = main_model_dir / "label_map.json"

    with open(label_map_path) as f:
        metadata = json.load(f)

    label_map = metadata["label_map"]
    assert len(label_map) == 7, f"Expected 7 classes, got {len(label_map)}"

    # Check for expected classes
    expected_classes = {
        "body_text",
        "heading",
        "footnote",
        "caption",
        "page_header",
        "page_footer",
        "cover",
    }
    actual_classes = set(label_map.keys())
    assert actual_classes == expected_classes, (
        f"Class mismatch. Expected {expected_classes}, got {actual_classes}"
    )


def test_model_files_exist(main_model_dir):
    """Test that model files exist."""
    # Check for at least one model file
    model_files = (
        list(main_model_dir.glob("*.safetensors"))
        + list(main_model_dir.glob("*.bin"))
        + list(main_model_dir.glob("*.pt"))
    )

    assert len(model_files) > 0, "No model files found (.safetensors, .bin, or .pt)"


def test_config_json_exists(main_model_dir):
    """Test that config.json exists (HuggingFace model)."""
    config_path = main_model_dir / "config.json"
    assert config_path.exists(), "config.json not found (not a HuggingFace model?)"


@pytest.mark.slow
def test_model_loads_with_transformers(main_model_dir):
    """Test that the model can be loaded with transformers library."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        pytest.skip("transformers not installed")

    # This is a slow test, so mark it as such
    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")
    model = AutoModelForSequenceClassification.from_pretrained(main_model_dir)

    assert model is not None
    assert tokenizer is not None
    assert model.config.num_labels == 7


@pytest.mark.slow
def test_basic_inference(main_model_dir):
    """Test basic inference on sample text."""
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        pytest.skip("transformers not installed")

    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")
    model = AutoModelForSequenceClassification.from_pretrained(main_model_dir)
    model.eval()

    # Sample text
    text = "This is a sample paragraph from a legal document."

    # Tokenize and run inference
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        predicted_class = torch.argmax(outputs.logits, dim=-1).item()

    # Check that prediction is within valid range
    assert 0 <= predicted_class < 7, f"Invalid prediction: {predicted_class}"
