#!/usr/bin/env python3
"""
Test the trained ModernBERT footnote classifier on sample PDFs.

Loads the fine-tuned classifier and tests it on paragraphs from test corpus
and new PDFs to evaluate real-world performance.

Usage:
    python test_modernbert_classifier.py
    python test_modernbert_classifier.py --pdf path/to/test.pdf
"""

import sys
from pathlib import Path

import pandas as pd
import torch
from docling.document_converter import DocumentConverter
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def load_classifier(model_path: Path):
    """Load trained ModernBERT classifier."""
    print(f"Loading classifier from {model_path}...")

    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    model.eval()

    # Move to MPS if available
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = model.to(device)

    print(f"  ✓ Loaded on {device}")
    return tokenizer, model, device


def classify_text(text: str, tokenizer, model, device) -> tuple[str, float]:
    """Classify a single text as body_text or footnote.

    Returns:
        (label, confidence) where label is 'body_text' or 'footnote'
    """
    # Tokenize
    inputs = tokenizer(
        text, padding="max_length", truncation=True, max_length=1024, return_tensors="pt"
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Predict
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        prediction = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][prediction].item()

    label = "footnote" if prediction == 1 else "body_text"
    return label, confidence


def test_on_corpus(model_path: Path, corpus_path: Path, n_samples: int = 20):
    """Test classifier on random samples from test corpus."""
    print("\n" + "=" * 80)
    print("TESTING ON CORPUS SAMPLES")
    print("=" * 80)

    # Load classifier
    tokenizer, model, device = load_classifier(model_path)

    # Load corpus
    df = pd.read_csv(corpus_path)

    # Get balanced samples (50% footnotes, 50% body)
    footnotes = df[df["html_label"] == "footnote"].sample(n=n_samples // 2, random_state=42)
    body = df[df["html_label"] == "body_text"].sample(n=n_samples // 2, random_state=42)
    samples = pd.concat([body, footnotes]).sample(frac=1, random_state=42)

    print(
        f"\nTesting on {len(samples)} samples ({n_samples // 2} body, {n_samples // 2} footnotes)"
    )

    # Test each sample
    correct = 0
    results = []

    for idx, row in samples.iterrows():
        text = row["text"]
        true_label = row["html_label"]

        pred_label, confidence = classify_text(text, tokenizer, model, device)

        is_correct = pred_label == true_label
        correct += is_correct

        results.append(
            {
                "text_preview": text[:80] + "..." if len(text) > 80 else text,
                "true_label": true_label,
                "pred_label": pred_label,
                "confidence": confidence,
                "correct": is_correct,
            }
        )

    # Print results
    accuracy = correct / len(samples)
    print(f"\nAccuracy: {accuracy:.2%} ({correct}/{len(samples)})")

    # Show some examples
    print("\nSample Predictions:")
    print("-" * 80)
    for i, result in enumerate(results[:5], 1):
        status = "✓" if result["correct"] else "✗"
        print(f"\n{i}. {status} [{result['confidence']:.2f}]")
        print(f"   True: {result['true_label']}, Predicted: {result['pred_label']}")
        print(f"   Text: {result['text_preview']}")

    # Show errors
    errors = [r for r in results if not r["correct"]]
    if errors:
        print(f"\n\nErrors ({len(errors)}):")
        print("-" * 80)
        for i, error in enumerate(errors[:3], 1):
            print(f"\n{i}. Confidence: {error['confidence']:.2f}")
            print(f"   True: {error['true_label']}, Predicted: {error['pred_label']}")
            print(f"   Text: {error['text_preview']}")


def test_on_pdf(model_path: Path, pdf_path: Path):
    """Test classifier on a new PDF."""
    print("\n" + "=" * 80)
    print(f"TESTING ON PDF: {pdf_path.name}")
    print("=" * 80)

    # Load classifier
    tokenizer, model, device = load_classifier(model_path)

    # Extract text with docling
    print("\nExtracting text with Docling...")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc_md = result.document.export_to_markdown()

    # Split into paragraphs (simple split on double newlines)
    paragraphs = [p.strip() for p in doc_md.split("\n\n") if p.strip()]
    print(f"  ✓ Extracted {len(paragraphs)} paragraphs")

    # Classify each paragraph
    print("\nClassifying paragraphs...")
    classifications = []

    for para in paragraphs:
        if len(para) < 20:  # Skip very short paragraphs
            continue

        label, confidence = classify_text(para, tokenizer, model, device)
        classifications.append({"text": para, "label": label, "confidence": confidence})

    # Summary
    footnote_count = sum(1 for c in classifications if c["label"] == "footnote")
    body_count = len(classifications) - footnote_count

    print("\nClassification Summary:")
    print(f"  Body text:  {body_count} ({body_count / len(classifications) * 100:.1f}%)")
    print(f"  Footnotes:  {footnote_count} ({footnote_count / len(classifications) * 100:.1f}%)")

    # Show examples
    print("\nSample Classifications:")
    print("-" * 80)

    # Show some body text
    body_examples = [c for c in classifications if c["label"] == "body_text"][:3]
    print("\nBody Text Examples:")
    for i, ex in enumerate(body_examples, 1):
        text_preview = ex["text"][:100] + "..." if len(ex["text"]) > 100 else ex["text"]
        print(f"{i}. [{ex['confidence']:.2f}] {text_preview}")

    # Show some footnotes
    footnote_examples = [c for c in classifications if c["label"] == "footnote"][:3]
    print("\nFootnote Examples:")
    for i, ex in enumerate(footnote_examples, 1):
        text_preview = ex["text"][:100] + "..." if len(ex["text"]) > 100 else ex["text"]
        print(f"{i}. [{ex['confidence']:.2f}] {text_preview}")


def main():
    base_dir = Path(__file__).parent
    model_path = base_dir / "models" / "modernbert_footnote_classifier" / "final_model"
    corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"

    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Train model first: python train_modernbert_classifier.py")
        sys.exit(1)

    # Test on corpus samples
    if corpus_path.exists():
        test_on_corpus(model_path, corpus_path, n_samples=20)

    # Test on PDF if provided
    if len(sys.argv) > 1:
        if sys.argv[1] == "--pdf" and len(sys.argv) > 2:
            pdf_path = Path(sys.argv[2])
            if not pdf_path.exists():
                print(f"Error: PDF not found: {pdf_path}")
                sys.exit(1)
            test_on_pdf(model_path, pdf_path)
        else:
            print("Usage: python test_modernbert_classifier.py [--pdf path/to/file.pdf]")
            sys.exit(1)

    print("\n" + "=" * 80)
    print("✓ TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
