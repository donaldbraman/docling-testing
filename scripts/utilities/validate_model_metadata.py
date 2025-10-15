#!/usr/bin/env python3
"""
Validate model metadata across all models in models/ directory.

Checks for:
- label_map.json existence and validity
- Required metadata fields
- Model file presence
- Metrics documentation

Usage:
    python scripts/utilities/validate_model_metadata.py
    python scripts/utilities/validate_model_metadata.py --models-dir models/
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


class ModelValidator:
    """Validates model metadata and files."""

    REQUIRED_METADATA_FIELDS = {
        "model_name": str,
        "version": str,
        "base_model": str,
        "label_map": dict,
    }

    OPTIONAL_METADATA_FIELDS = {
        "metrics": dict,
        "training_issue": (str, int),
        "training_date": str,
        "description": str,
    }

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.results = []

    def find_model_directories(self) -> list[Path]:
        """Find all directories that might contain models."""
        model_dirs = []

        # Look for directories with label_map.json or model files
        for path in self.models_dir.rglob("*"):
            if path.is_dir():
                if (
                    (path / "label_map.json").exists()
                    or any(path.glob("*.safetensors"))
                    or any(path.glob("*.bin"))
                ):
                    model_dirs.append(path)

        return sorted(set(model_dirs))

    def validate_model(self, model_dir: Path) -> dict:
        """Validate a single model directory."""
        result = {
            "path": model_dir.relative_to(self.models_dir.parent),
            "status": "valid",
            "errors": [],
            "warnings": [],
            "metadata": {},
        }

        # Check for label_map.json
        label_map_path = model_dir / "label_map.json"
        if not label_map_path.exists():
            result["status"] = "error"
            result["errors"].append("label_map.json not found")
            return result

        # Load and validate label_map.json
        try:
            with label_map_path.open() as f:
                metadata = json.load(f)
            result["metadata"] = metadata
        except json.JSONDecodeError as e:
            result["status"] = "error"
            result["errors"].append(f"Invalid JSON in label_map.json: {e}")
            return result

        # Check required fields
        for field, expected_type in self.REQUIRED_METADATA_FIELDS.items():
            if field not in metadata:
                result["status"] = "error"
                result["errors"].append(f"Missing required field: {field}")
            elif not isinstance(metadata[field], expected_type):
                result["status"] = "error"
                result["errors"].append(
                    f"Field '{field}' should be {expected_type.__name__}, got {type(metadata[field]).__name__}"
                )

        # Check optional fields (warnings if missing)
        for field, expected_types in self.OPTIONAL_METADATA_FIELDS.items():
            if field not in metadata:
                result["warnings"].append(f"Missing optional field: {field}")
            elif not isinstance(metadata[field], expected_types):
                result["warnings"].append(
                    f"Field '{field}' has unexpected type: {type(metadata[field]).__name__}"
                )

        # Check for model files
        model_files = (
            list(model_dir.glob("*.safetensors"))
            + list(model_dir.glob("*.bin"))
            + list(model_dir.glob("*.pt"))
        )
        if not model_files:
            result["status"] = "warning" if result["status"] == "valid" else result["status"]
            result["warnings"].append("No model files found (.safetensors, .bin, or .pt)")
        else:
            result["metadata"]["model_files"] = [f.name for f in model_files]

        # Check for config.json (HuggingFace models)
        config_path = model_dir / "config.json"
        if not config_path.exists():
            result["warnings"].append("No config.json found (not a HuggingFace model?)")

        # Update status based on warnings
        if result["warnings"] and result["status"] == "valid":
            result["status"] = "warning"

        return result

    def validate_all(self) -> list[dict]:
        """Validate all models in the models directory."""
        model_dirs = self.find_model_directories()

        if not model_dirs:
            print(f"No model directories found in {self.models_dir}")
            return []

        for model_dir in model_dirs:
            result = self.validate_model(model_dir)
            self.results.append(result)

        return self.results

    def print_report(self):
        """Print validation report."""
        print("=" * 80)
        print("MODEL METADATA VALIDATION")
        print("=" * 80)
        print()

        # Group by status
        by_status = defaultdict(list)
        for result in self.results:
            by_status[result["status"]].append(result)

        # Print valid models
        if by_status["valid"]:
            print("✅ VALID MODELS")
            print("-" * 80)
            for result in by_status["valid"]:
                self._print_model_info(result)

        # Print models with warnings
        if by_status["warning"]:
            print("\n⚠️  MODELS WITH WARNINGS")
            print("-" * 80)
            for result in by_status["warning"]:
                self._print_model_info(result)

        # Print models with errors
        if by_status["error"]:
            print("\n❌ MODELS WITH ERRORS")
            print("-" * 80)
            for result in by_status["error"]:
                self._print_model_info(result)

        # Summary
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total models: {len(self.results)}")
        print(f"  Valid:    {len(by_status['valid'])} ✅")
        print(f"  Warnings: {len(by_status['warning'])} ⚠️")
        print(f"  Errors:   {len(by_status['error'])} ❌")

    def _print_model_info(self, result: dict):
        """Print information about a single model."""
        metadata = result["metadata"]

        print(f"\n{result['path']}")

        # Print metadata if available
        if "model_name" in metadata:
            print(f"  Model: {metadata['model_name']}")
        if "version" in metadata:
            print(f"  Version: {metadata['version']}")
        if "base_model" in metadata:
            print(f"  Base: {metadata['base_model']}")
        if "label_map" in metadata:
            classes = ", ".join(metadata["label_map"].keys())
            print(f"  Classes ({len(metadata['label_map'])}): {classes}")
        if "metrics" in metadata:
            metrics_str = ", ".join(
                f"{k}={v:.1f}%" if isinstance(v, (int, float)) else f"{k}={v}"
                for k, v in metadata["metrics"].items()
            )
            print(f"  Metrics: {metrics_str}")
        if "training_issue" in metadata:
            print(f"  Issue: #{metadata['training_issue']}")
        if "model_files" in metadata:
            print(f"  Files: {', '.join(metadata['model_files'])}")

        # Print warnings
        for warning in result["warnings"]:
            print(f"  ⚠️  Warning: {warning}")

        # Print errors
        for error in result["errors"]:
            print(f"  ❌ Error: {error}")


def main():
    parser = argparse.ArgumentParser(description="Validate model metadata")
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("models"),
        help="Path to models directory (default: models/)",
    )
    args = parser.parse_args()

    # Resolve relative to script location if not absolute
    if not args.models_dir.is_absolute():
        script_dir = Path(__file__).parent.parent.parent
        models_dir = script_dir / args.models_dir
    else:
        models_dir = args.models_dir

    if not models_dir.exists():
        print(f"❌ Error: Models directory not found: {models_dir}")
        return 1

    validator = ModelValidator(models_dir)
    validator.validate_all()
    validator.print_report()

    # Exit code: 0 if all valid, 1 if any errors, 2 if any warnings
    if any(r["status"] == "error" for r in validator.results):
        return 1
    if any(r["status"] == "warning" for r in validator.results):
        return 2
    return 0


if __name__ == "__main__":
    exit(main())
