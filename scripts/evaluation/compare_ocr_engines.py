#!/usr/bin/env python3
"""
Compare OCR engines by measuring normalized text output quality.

Tests ocrmac (Neural Engine) and Tesseract (CPU) on same image-only PDF.
Compares against ground truth HTML (if available) after text normalization.

Both engines provide bounding boxes needed for our classification pipeline.

Usage:
    uv run python scripts/evaluation/compare_ocr_engines.py --pdf political_mootness
    uv run python scripts/evaluation/compare_ocr_engines.py --pdf political_mootness --max-pages 5
"""

import argparse
import json
import time
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for fair OCR comparison.

    Same normalization used in production pipeline.
    """
    import re
    import unicodedata

    # Normalize smart quotes and dashes
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # ' ' → '
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # " " → "
    text = text.replace("\u2014", "-").replace("\u2013", "-")  # — – → -

    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    # Keep only allowed characters
    allowed_chars = []
    for char in text:
        if char.isascii() and (char.isalnum() or char in " .,!?:;'\"-()[]/&\n\t") or char in "§¶":
            allowed_chars.append(char)
        elif unicodedata.category(char).startswith("L"):
            try:
                decomposed = unicodedata.normalize("NFD", char)
                if decomposed[0].isascii():
                    allowed_chars.append(char)
            except:
                pass

    text = "".join(allowed_chars)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_image_only_pdf(
    pdf_path: Path, output_dir: Path, max_pages: int | None = None, dpi: int = 300
) -> Path:
    """Create greyscale image-only PDF."""
    import fitz

    output_path = output_dir / f"{pdf_path.stem}_image_only_{dpi}dpi.pdf"

    if output_path.exists():
        print(f"  Using cached image-only PDF: {output_path.name}")
        return output_path

    print(f"  Creating greyscale image-only PDF at {dpi} DPI...")

    src_doc = fitz.open(str(pdf_path))
    total_pages = len(src_doc)
    page_count = min(max_pages, total_pages) if max_pages else total_pages

    img_doc = fitz.open()

    for i in range(page_count):
        print(f"    Page {i + 1}/{page_count}...")
        page = src_doc[i]

        # Render to greyscale image at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    print(f"  ✓ Created: {output_path.name} ({page_count} pages)")
    return output_path


def ocr_with_tesseract(image_pdf: Path) -> dict:
    """Run Tesseract OCR via pytesseract."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        return {
            "engine": "tesseract",
            "available": False,
            "error": f"Missing dependency: {e}",
        }

    print("\n[Tesseract]")
    print("  Running OCR...")

    start = time.time()

    try:
        # Convert PDF pages to images (match image PDF DPI for consistency)
        images = convert_from_path(str(image_pdf), dpi=600, grayscale=True)

        # OCR each page
        all_text = []
        for i, img in enumerate(images):
            print(f"    Page {i + 1}/{len(images)}...")
            text = pytesseract.image_to_string(img)
            all_text.append(text)

        combined_text = "\n\n".join(all_text)
        normalized_text = normalize_text_for_comparison(combined_text)

        elapsed = time.time() - start

        print(f"  ✓ Completed in {elapsed:.1f}s")

        return {
            "engine": "tesseract",
            "available": True,
            "raw_text": combined_text,
            "normalized_text": normalized_text,
            "pages_processed": len(images),
            "time_seconds": elapsed,
            "chars_extracted": len(normalized_text),
            "hardware": "CPU",
        }

    except Exception as e:
        return {
            "engine": "tesseract",
            "available": True,
            "error": str(e),
        }


def ocr_with_ocrmac(image_pdf: Path) -> dict:
    """Run ocrmac (Apple Vision/Neural Engine)."""
    try:
        from ocrmac import ocrmac
        from pdf2image import convert_from_path
    except ImportError as e:
        return {
            "engine": "ocrmac",
            "available": False,
            "error": f"Missing dependency: {e}. Install: pip install ocrmac pdf2image",
        }

    import platform

    if platform.system() != "Darwin":
        return {
            "engine": "ocrmac",
            "available": False,
            "error": "ocrmac only works on macOS",
        }

    print("\n[ocrmac]")
    print("  Running OCR with Apple Neural Engine...")

    start = time.time()

    try:
        # Convert PDF to images (match image PDF DPI for consistency)
        images = convert_from_path(str(image_pdf), dpi=600, grayscale=True)

        # OCR each page
        all_text = []
        for i, img in enumerate(images):
            print(f"    Page {i + 1}/{len(images)}...")

            # Save temporary image for ocrmac
            temp_img = f"/tmp/ocr_page_{i}.png"
            img.save(temp_img)

            # Run OCR
            annotations = ocrmac.OCR(temp_img, recognition_level="accurate").recognize()
            page_text = " ".join([ann[0] for ann in annotations])
            all_text.append(page_text)

        combined_text = "\n\n".join(all_text)
        normalized_text = normalize_text_for_comparison(combined_text)

        elapsed = time.time() - start

        print(f"  ✓ Completed in {elapsed:.1f}s")

        return {
            "engine": "ocrmac",
            "available": True,
            "raw_text": combined_text,
            "normalized_text": normalized_text,
            "pages_processed": len(images),
            "time_seconds": elapsed,
            "chars_extracted": len(normalized_text),
            "hardware": "Neural Engine",
        }

    except Exception as e:
        return {
            "engine": "ocrmac",
            "available": True,
            "error": str(e),
        }


def load_ground_truth(pdf_name: str) -> str | None:
    """Load ground truth HTML text if available."""
    html_path = Path(f"data/v3_data/processed_html/{pdf_name}.json")

    if not html_path.exists():
        return None

    try:
        with open(html_path) as f:
            data = json.load(f)

        # Combine body and footnotes
        body_text = data.get("body_text", "")
        footnotes = data.get("footnotes", [])
        footnote_text = " ".join(footnotes) if isinstance(footnotes, list) else str(footnotes)

        combined = f"{body_text}\n\n{footnote_text}"
        return normalize_text_for_comparison(combined)

    except Exception as e:
        print(f"  Warning: Could not load ground truth: {e}")
        return None


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate text similarity using SequenceMatcher."""
    return SequenceMatcher(None, text1, text2).ratio()


def generate_html_diff(text1: str, text2: str, label1: str, label2: str, output_path: Path):
    """Generate HTML diff visualization between two texts."""
    import difflib

    # Split into lines for better diff visualization
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    # Generate HTML diff
    differ = difflib.HtmlDiff(wrapcolumn=80)
    html = differ.make_file(
        lines1,
        lines2,
        fromdesc=label1,
        todesc=label2,
        context=True,
        numlines=3,
    )

    # Save to file
    with open(output_path, "w") as f:
        f.write(html)

    print(f"  ✓ Diff saved: {output_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Compare OCR engines on normalized text output")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument("--max-pages", type=int, help="Limit to first N pages for testing")
    parser.add_argument(
        "--dpi", type=int, default=300, help="DPI for image rendering (default: 300)"
    )
    args = parser.parse_args()

    # Paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return

    # Organize by date and test parameters
    from datetime import date

    today = date.today().strftime("%Y%m%d")
    test_dir = Path(f"results/ocr_comparison/{today}/{args.pdf}_{args.dpi}dpi")
    test_dir.mkdir(parents=True, exist_ok=True)

    # Keep output_dir for backward compatibility with existing code
    output_dir = test_dir

    print(f"\n{'=' * 60}")
    print("OCR Engine Comparison")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    if args.max_pages:
        print(f"Pages: First {args.max_pages}")
    print()

    # Stage 1: Create image-only PDF
    print(f"[Stage 1] Creating image-only PDF at {args.dpi} DPI...")
    image_pdf = create_image_only_pdf(pdf_path, output_dir, args.max_pages, args.dpi)

    # Stage 2: Load ground truth (if available)
    print("\n[Stage 2] Loading ground truth...")
    ground_truth = load_ground_truth(args.pdf)
    if ground_truth:
        print(f"  ✓ Ground truth loaded: {len(ground_truth)} chars")
    else:
        print("  ⚠️  No ground truth available (accuracy metrics skipped)")

    # Stage 3: Run OCR engines
    print("\n[Stage 3] Running OCR engines...")

    results = {
        "ocrmac": ocr_with_ocrmac(image_pdf),
        "tesseract": ocr_with_tesseract(image_pdf),
    }

    # Stage 4: Calculate metrics and generate diffs
    print(f"\n{'=' * 60}")
    print("Results & Diff Generation")
    print(f"{'=' * 60}\n")

    comparison_data = []

    # Collect successful OCR results for pairwise diffs
    ocr_texts = {}

    for engine_name, result in results.items():
        if not result.get("available"):
            print(f"[{engine_name}] Not available: {result.get('error', 'Unknown')}")
            continue

        if "error" in result:
            print(f"[{engine_name}] Error: {result['error']}")
            continue

        # Calculate accuracy (if ground truth available)
        accuracy = None
        if ground_truth and "normalized_text" in result:
            accuracy = calculate_similarity(ground_truth, result["normalized_text"])

        # Store for pairwise comparisons
        if "normalized_text" in result:
            ocr_texts[engine_name] = result["normalized_text"]

        # Print summary
        print(f"[{engine_name}]")
        print(f"  Hardware: {result.get('hardware', 'N/A')}")
        print(f"  Time: {result.get('time_seconds', 0):.1f}s")
        print(
            f"  Speed: {result.get('pages_processed', 0) / result.get('time_seconds', 1):.2f} pages/sec"
        )
        print(f"  Chars extracted: {result.get('chars_extracted', 0):,}")
        if accuracy:
            print(f"  Accuracy vs ground truth: {accuracy * 100:.1f}%")
        print()

        comparison_data.append(
            {
                "engine": engine_name,
                "hardware": result.get("hardware", "N/A"),
                "time_seconds": result.get("time_seconds", 0),
                "speed_pages_per_sec": f"{result.get('pages_processed', 0) / result.get('time_seconds', 1):.2f}",
                "chars_extracted": result.get("chars_extracted", 0),
                "accuracy": f"{accuracy * 100:.1f}%" if accuracy else "N/A",
            }
        )

    # Stage 5: Generate pairwise diffs for quality review
    print(f"\n{'=' * 60}")
    print("Generating Quality Diffs")
    print(f"{'=' * 60}\n")

    diff_dir = output_dir / "diffs"
    diff_dir.mkdir(exist_ok=True)

    # Ground truth vs each engine
    if ground_truth:
        for engine_name, ocr_text in ocr_texts.items():
            diff_file = diff_dir / f"ground_truth_vs_{engine_name}.html"
            print(f"  Generating: ground_truth vs {engine_name}...")
            generate_html_diff(
                ground_truth, ocr_text, "Ground Truth (HTML)", f"{engine_name} (OCR)", diff_file
            )

    # Pairwise engine comparisons
    engine_names = list(ocr_texts.keys())
    for i, engine1 in enumerate(engine_names):
        for engine2 in engine_names[i + 1 :]:
            diff_file = diff_dir / f"{engine1}_vs_{engine2}.html"
            print(f"  Generating: {engine1} vs {engine2}...")
            generate_html_diff(
                ocr_texts[engine1],
                ocr_texts[engine2],
                f"{engine1} (OCR)",
                f"{engine2} (OCR)",
                diff_file,
            )

    print(f"\n  ✓ Diffs saved to: {diff_dir}/")
    print("  Open in browser for quality review")

    # Stage 6: Generate comparison table
    if comparison_data:
        df = pd.DataFrame(comparison_data)

        print(f"{'=' * 60}")
        print("Summary Table")
        print(f"{'=' * 60}\n")
        print(df.to_string(index=False))
        print()

        # Save results
        output_file = output_dir / "comparison.json"
        with open(output_file, "w") as f:
            json.dump(
                {
                    "pdf": args.pdf,
                    "max_pages": args.max_pages,
                    "ground_truth_available": ground_truth is not None,
                    "results": results,
                    "comparison": comparison_data,
                },
                f,
                indent=2,
            )

        print(f"Results saved to: {output_file}")

    # Recommendation
    print(f"\n{'=' * 60}")
    print("Recommendation")
    print(f"{'=' * 60}\n")

    available = [r for r in comparison_data if r.get("accuracy") != "N/A"]
    if available:
        best_accuracy = max(available, key=lambda x: float(x["accuracy"].rstrip("%")))
        best_speed = min(
            [r for r in comparison_data if r.get("time_seconds", float("inf")) > 0],
            key=lambda x: x.get("time_seconds", float("inf")),
        )

        print(f"Best accuracy: {best_accuracy['engine']} ({best_accuracy['accuracy']})")
        print(f"Fastest: {best_speed['engine']} ({best_speed['time_seconds']:.1f}s)")
        print()
        print("Both engines provide bounding boxes needed for classification pipeline.")
        if best_accuracy["engine"] == "ocrmac":
            print("Recommend: ocrmac (Neural Engine, faster)")
        else:
            print("Recommend: tesseract (better accuracy, cross-platform)")
    else:
        print("Both engines suitable for production:")
        print("  - ocrmac: Faster (Neural Engine), Mac-only")
        print("  - tesseract: Cross-platform, widely supported")


if __name__ == "__main__":
    main()
