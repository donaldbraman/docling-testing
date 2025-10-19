"""
Analyze GPU acceleration support for OCR engines.

Checks GPU availability and capabilities for:
- PyTorch/CUDA (for Docling)
- PaddleOCR GPU
- Tesseract GPU (if available)
"""

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any


def check_pytorch_gpu() -> dict[str, Any]:
    """Check PyTorch GPU availability.

    Returns:
        Dict with PyTorch GPU info
    """
    try:
        import torch

        return {
            "available": True,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
            "pytorch_version": torch.__version__,
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "device_names": [
                torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())
            ]
            if torch.cuda.is_available()
            else [],
        }
    except ImportError:
        return {
            "available": False,
            "error": "PyTorch not installed",
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }


def check_paddleocr_gpu() -> dict[str, Any]:
    """Check PaddleOCR GPU support.

    Returns:
        Dict with PaddleOCR GPU info
    """
    if importlib.util.find_spec("paddleocr") is None:
        return {
            "available": False,
            "error": "PaddleOCR not installed",
        }

    try:
        import paddle

        return {
            "available": True,
            "cuda_available": paddle.device.cuda.is_available(),
            "version": paddle.__version__,
            "device_names": [paddle.device.get_device()],
            "notes": "PaddleOCR supports GPU via PaddlePaddle",
        }
    except Exception:
        return {
            "available": True,
            "cuda_available": False,
            "notes": "PaddleOCR CPU mode only",
        }


def check_tesseract_gpu() -> dict[str, Any]:
    """Check Tesseract GPU support via ocrmypdf.

    Returns:
        Dict with Tesseract GPU info
    """
    if importlib.util.find_spec("ocrmypdf") is None:
        return {
            "available": False,
            "error": "ocrmypdf not installed",
        }

    try:
        # Check if tesseract is available
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)

        if result.returncode == 0:
            # Parse version info
            version_line = result.stdout.split("\n")[0]
            return {
                "available": True,
                "version": version_line,
                "notes": "Tesseract GPU support depends on libtesseract build",
                "gpu_support": "Limited - typically CPU only unless compiled with CUDA",
            }
        else:
            return {
                "available": False,
                "error": "Tesseract not found in PATH",
            }
    except FileNotFoundError:
        return {
            "available": False,
            "error": "Tesseract not found",
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }


def check_system_gpu() -> dict[str, Any]:
    """Check system GPU availability.

    Returns:
        Dict with GPU hardware info
    """
    import platform

    system_info = {
        "os": platform.system(),
        "platform": platform.platform(),
    }

    if platform.system() == "Darwin":  # macOS
        # Check for Metal GPU
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "GPU" in result.stdout or "Metal" in result.stdout:
                system_info["gpu_type"] = "Metal (Apple Silicon/Intel iGPU)"
                system_info["metal_available"] = True
        except Exception:
            pass

    return system_info


def main():
    """Analyze and report GPU support for all OCR engines."""
    output_dir = Path("results/ocr_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis = {
        "timestamp": __import__("time").time(),
        "system": check_system_gpu(),
        "pytorch": check_pytorch_gpu(),
        "paddleocr": check_paddleocr_gpu(),
        "tesseract": check_tesseract_gpu(),
        "recommendations": {},
    }

    # Generate recommendations
    if analysis["pytorch"]["available"] and analysis["pytorch"].get("cuda_available"):
        analysis["recommendations"]["docling"] = (
            "GPU available (CUDA). Docling will use PyTorch GPU automatically."
        )
    else:
        analysis["recommendations"]["docling"] = "CPU only"

    if analysis["paddleocr"]["available"]:
        if analysis["paddleocr"].get("cuda_available"):
            analysis["recommendations"]["paddleocr"] = (
                "GPU available. Use use_gpu=True in PaddleOCR init."
            )
        else:
            analysis["recommendations"]["paddleocr"] = (
                "CPU only. Consider installing paddlepaddle-gpu for CUDA support."
            )
    else:
        analysis["recommendations"]["paddleocr"] = (
            "Not installed. Install: pip install paddleocr paddlepaddle-gpu"
        )

    if analysis["tesseract"]["available"]:
        analysis["recommendations"]["tesseract"] = (
            "Available but typically CPU-only. OCRmyPDF will use Tesseract."
        )
    else:
        analysis["recommendations"]["tesseract"] = (
            "Not found. Install: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)"
        )

    # Save analysis
    output_file = output_dir / "gpu_analysis.json"
    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2)

    print("GPU ACCELERATION ANALYSIS")
    print("=" * 60)
    print(f"System: {analysis['system']['platform']}")

    print("\nPyTorch (Docling):")
    if analysis["pytorch"]["available"]:
        print(f"  ✓ Available (v{analysis['pytorch']['pytorch_version']})")
        print(f"  GPU: {analysis['pytorch']['cuda_available']}")
        if analysis["pytorch"]["cuda_available"]:
            print(f"  CUDA: {analysis['pytorch']['cuda_version']}")
            for device in analysis["pytorch"]["device_names"]:
                print(f"    - {device}")
    else:
        print(f"  ✗ {analysis['pytorch'].get('error', 'Not available')}")

    print("\nPaddleOCR:")
    if analysis["paddleocr"]["available"]:
        print("  ✓ Available")
        print(f"  GPU: {analysis['paddleocr'].get('cuda_available', False)}")
    else:
        print(f"  ✗ {analysis['paddleocr'].get('error', 'Not available')}")

    print("\nTesseract (OCRmyPDF):")
    if analysis["tesseract"]["available"]:
        print("  ✓ Available")
        print(f"  Version: {analysis['tesseract']['version']}")
    else:
        print(f"  ✗ {analysis['tesseract'].get('error', 'Not available')}")

    print("\nRecommendations:")
    for tool, rec in analysis["recommendations"].items():
        print(f"  {tool}: {rec}")

    print(f"\nDetailed analysis saved to {output_file}")


if __name__ == "__main__":
    main()
