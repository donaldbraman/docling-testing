#!/usr/bin/env python3
"""
EasyOCR + ModernBERT classification for vast.ai deployment.
Extracts text and classifies into 4 semantic classes.

Usage:
    python run_ocr_with_classification.py --input input.pdf --output-dir ./results
"""

# CRITICAL: Disable torch.compile BEFORE any imports
# This avoids Triton/CUDA development library requirements
import os

os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHDYNAMO_DISABLE"] = "1"

import argparse
import csv
import json
from pathlib import Path

import easyocr
import fitz  # PyMuPDF
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Additional safety: suppress dynamo errors
torch._dynamo.config.suppress_errors = True

# Class mapping: 7 original classes -> 4 target classes
CLASS_MAPPING = {
    "body_text": "body_text",
    "heading": "front_matter",
    "footnote": "footnote",
    "caption": "front_matter",
    "page_header": "page_header",
    "page_footer": "front_matter",
    "cover": "front_matter",
}

# Colors for PDF overlay (RGB)
CLASS_COLORS = {
    "body_text": (0.0, 0.5, 1.0),  # Blue
    "footnote": (1.0, 0.5, 0.0),  # Orange
    "page_header": (0.5, 0.0, 1.0),  # Purple
    "front_matter": (0.0, 0.8, 0.3),  # Green
}


def setup_ocr_reader(gpu=True):
    """Initialize EasyOCR reader."""
    print("🔄 Initializing EasyOCR...")
    reader = easyocr.Reader(["en"], gpu=gpu)
    print("✅ EasyOCR ready")
    return reader


def setup_classifier(model_path, gpu=True):
    """Initialize ModernBERT classifier."""
    print("🔄 Loading ModernBERT classifier...")

    device = "cuda" if gpu and torch.cuda.is_available() else "cpu"
    print(f"   Using device: {device}")

    # Load model and tokenizer with eager execution (no compilation)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path, attn_implementation="eager", _attn_implementation_internal="eager"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model.to(device)
    model.eval()

    # Force disable flash attention and torch.compile
    if hasattr(model.config, "use_flash_attention_2"):
        model.config.use_flash_attention_2 = False
    if hasattr(model.config, "_attn_implementation"):
        model.config._attn_implementation = "eager"

    # Load label map
    label_map_path = Path(model_path) / "label_map.json"
    with open(label_map_path) as f:
        label_info = json.load(f)

    # Reverse label map (id -> class name)
    id_to_label = {v: k for k, v in label_info["label_map"].items()}

    print(f"✅ Classifier ready ({label_info['model_name']})")
    print(f"   Original classes: {list(label_info['label_map'].keys())}")
    print(f"   Target classes: {list(set(CLASS_MAPPING.values()))}")

    return model, tokenizer, id_to_label, device


def classify_text(text, model, tokenizer, id_to_label, device):
    """Classify a single text block."""
    # Tokenize
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True).to(
        device
    )

    # Predict
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_id = torch.argmax(logits, dim=1).item()
        confidence = torch.softmax(logits, dim=1)[0][predicted_id].item()

    # Map to original class
    original_class = id_to_label[predicted_id]

    # Map to target class
    target_class = CLASS_MAPPING[original_class]

    return {
        "original_class": original_class,
        "target_class": target_class,
        "confidence": confidence,
    }


def extract_and_classify_pdf(pdf_path, ocr_reader, model, tokenizer, id_to_label, device):
    """Extract text from PDF and classify each block."""
    print(f"📄 Processing: {pdf_path}")

    pdf = fitz.open(pdf_path)
    all_results = []

    for page_num in range(len(pdf)):
        print(f"  Page {page_num + 1}/{len(pdf)}...")

        page = pdf[page_num]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")

        # OCR
        ocr_results = ocr_reader.readtext(img_data)

        # Classify each text block
        for bbox, text, ocr_conf in ocr_results:
            classification = classify_text(text, model, tokenizer, id_to_label, device)

            all_results.append(
                {
                    "page": page_num + 1,
                    "bbox": bbox,
                    "text": text,
                    "ocr_confidence": ocr_conf,
                    "original_class": classification["original_class"],
                    "target_class": classification["target_class"],
                    "class_confidence": classification["confidence"],
                }
            )

    pdf.close()
    print(f"✅ Extracted and classified {len(all_results)} text blocks")

    return all_results


def save_text_output(results, output_path):
    """Save plain text output."""
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(result["text"] + "\n")
    print(f"💾 Saved text: {output_path}")


def save_json_output(results, output_path):
    """Save JSON output with all metadata."""
    json_results = []
    for r in results:
        json_results.append(
            {
                "page": r["page"],
                "bbox": [[float(x), float(y)] for x, y in r["bbox"]],
                "text": r["text"],
                "ocr_confidence": float(r["ocr_confidence"]),
                "original_class": r["original_class"],
                "target_class": r["target_class"],
                "class_confidence": float(r["class_confidence"]),
            }
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved JSON: {output_path}")


def save_csv_output(results, output_path):
    """Save CSV with text blocks and predicted classes."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "page",
                "text",
                "target_class",
                "class_confidence",
                "ocr_confidence",
                "x1",
                "y1",
                "x2",
                "y2",
            ]
        )

        for r in results:
            bbox = r["bbox"]
            x_coords = [float(p[0]) for p in bbox]
            y_coords = [float(p[1]) for p in bbox]

            writer.writerow(
                [
                    r["page"],
                    r["text"],
                    r["target_class"],
                    f"{r['class_confidence']:.4f}",
                    f"{r['ocr_confidence']:.4f}",
                    min(x_coords),
                    min(y_coords),
                    max(x_coords),
                    max(y_coords),
                ]
            )
    print(f"💾 Saved CSV: {output_path}")


def create_text_overlay_pdf(pdf_path, results, output_path):
    """Create PDF with text overlay (OCR text visible)."""
    print("📝 Creating text overlay PDF...")

    pdf = fitz.open(pdf_path)

    for result in results:
        page_num = result["page"] - 1
        page = pdf[page_num]

        bbox = result["bbox"]
        x_coords = [float(p[0]) for p in bbox]
        y_coords = [float(p[1]) for p in bbox]
        rect = fitz.Rect(min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        # Add text annotation
        page.add_freetext_annot(rect, result["text"], fontsize=8, fill_color=(1, 1, 0.9))

    pdf.save(output_path)
    pdf.close()
    print(f"💾 Saved text overlay PDF: {output_path}")


def create_class_overlay_pdf(pdf_path, results, output_path):
    """Create PDF with colored class overlay."""
    print("📝 Creating class overlay PDF...")

    pdf = fitz.open(pdf_path)

    for result in results:
        page_num = result["page"] - 1
        page = pdf[page_num]

        bbox = result["bbox"]
        x_coords = [float(p[0]) for p in bbox]
        y_coords = [float(p[1]) for p in bbox]
        rect = fitz.Rect(min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        # Get color for class
        color = CLASS_COLORS[result["target_class"]]

        # Draw colored rectangle
        page.draw_rect(rect, color=color, width=2)

        # Add class label
        label = f"{result['target_class'][:4]}"  # Abbreviated
        page.add_freetext_annot(
            fitz.Rect(rect.x0, rect.y0 - 15, rect.x0 + 50, rect.y0),
            label,
            fontsize=6,
            fill_color=color,
        )

    pdf.save(output_path)
    pdf.close()
    print(f"💾 Saved class overlay PDF: {output_path}")


def print_classification_summary(results):
    """Print summary statistics."""
    from collections import Counter

    class_counts = Counter(r["target_class"] for r in results)
    total = len(results)

    print("\n" + "=" * 60)
    print("CLASSIFICATION SUMMARY")
    print("=" * 60)
    print(f"\nTotal text blocks: {total}")
    print("\nClass distribution:")
    for class_name in sorted(class_counts.keys()):
        count = class_counts[class_name]
        pct = 100 * count / total
        print(f"  {class_name:15s}: {count:5d} ({pct:5.1f}%)")

    avg_ocr_conf = sum(r["ocr_confidence"] for r in results) / total
    avg_class_conf = sum(r["class_confidence"] for r in results) / total
    print(f"\nAverage OCR confidence: {avg_ocr_conf:.2%}")
    print(f"Average class confidence: {avg_class_conf:.2%}")
    print("=" * 60 + "\n")


def process_pdf(pdf_path, output_dir, ocr_reader, model, tokenizer, id_to_label, device):
    """Process a single PDF with OCR and classification."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem

    # Extract and classify
    results = extract_and_classify_pdf(pdf_path, ocr_reader, model, tokenizer, id_to_label, device)

    # Save all outputs
    save_text_output(results, output_dir / f"{stem}.txt")
    save_json_output(results, output_dir / f"{stem}.json")
    save_csv_output(results, output_dir / f"{stem}.csv")
    create_text_overlay_pdf(pdf_path, results, output_dir / f"{stem}_text_overlay.pdf")
    create_class_overlay_pdf(pdf_path, results, output_dir / f"{stem}_class_overlay.pdf")

    # Print summary
    print_classification_summary(results)

    print(f"✅ Completed: {pdf_path.name}")
    print(f"   Outputs: {output_dir / stem}.*\n")


def main():
    parser = argparse.ArgumentParser(
        description="EasyOCR + ModernBERT classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--input", type=str, required=True, help="Input PDF file")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results",
        help="Output directory (default: ./results)",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="/workspace/models/doclingbert-v2-rebalanced/final_model",
        help="Path to ModernBERT model",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Use CPU instead of GPU",
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        parser.error(f"Input file not found: {args.input}")

    # Initialize
    gpu = not args.no_gpu
    ocr_reader = setup_ocr_reader(gpu=gpu)
    model, tokenizer, id_to_label, device = setup_classifier(args.model_path, gpu=gpu)

    # Process
    process_pdf(args.input, args.output_dir, ocr_reader, model, tokenizer, id_to_label, device)


if __name__ == "__main__":
    main()
