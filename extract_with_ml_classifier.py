#!/usr/bin/env python3
"""
Extract body text using ML-based footnote classification.

Replaces heuristic-based footnote detection with a fine-tuned ModernBERT classifier.
"""

import re
import time
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions


class FootnoteClassifier:
    """ML-based footnote classifier using fine-tuned ModernBERT."""

    def __init__(self, model_path: Path):
        """Load the trained classifier.

        Args:
            model_path: Path to trained model directory
        """
        print(f"Loading footnote classifier from {model_path}...")

        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
        self.model.eval()

        # Move to MPS if available
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = self.model.to(self.device)

        print(f"  ✓ Classifier loaded on {self.device}")

    def is_footnote(self, text: str) -> tuple[bool, float]:
        """Classify text as footnote or body text.

        Args:
            text: Text to classify

        Returns:
            (is_footnote, confidence) where confidence is 0-1
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            padding='max_length',
            truncation=True,
            max_length=1024,
            return_tensors='pt'
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            prediction = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][prediction].item()

        is_footnote = (prediction == 1)
        return is_footnote, confidence


def extract_body_text_ml(
    pdf_path: Path,
    model_path: Optional[Path] = None,
    confidence_threshold: float = 0.5
) -> dict:
    """Extract body text using ML-based footnote detection.

    Args:
        pdf_path: Path to PDF file
        model_path: Path to trained model (default: models/modernbert_footnote_classifier/final_model)
        confidence_threshold: Minimum confidence to classify as footnote (default: 0.5)

    Returns:
        dict with:
            - body_text: Extracted body text
            - footnote_count: Number of footnotes detected
            - body_para_count: Number of body paragraphs
            - stats: Classification statistics
    """
    # Default model path
    if model_path is None:
        base_dir = Path(__file__).parent
        model_path = base_dir / "models" / "modernbert_footnote_classifier" / "final_model"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found at {model_path}. "
            "Train model first: python train_modernbert_classifier.py"
        )

    # Load classifier
    classifier = FootnoteClassifier(model_path)

    # Extract text with docling
    print(f"\nExtracting text from {pdf_path.name}...")
    start_time = time.time()

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc_md = result.document.export_to_markdown()

    # Split into paragraphs
    paragraphs = [p.strip() for p in doc_md.split('\n\n') if p.strip()]
    print(f"  ✓ Extracted {len(paragraphs)} paragraphs in {time.time() - start_time:.1f}s")

    # Classify each paragraph
    print(f"\nClassifying paragraphs with ML model...")
    classify_start = time.time()

    body_paragraphs = []
    footnote_count = 0
    low_confidence_count = 0
    confidences = []

    for para in paragraphs:
        if len(para) < 20:  # Skip very short paragraphs
            continue

        is_footnote, confidence = classifier.is_footnote(para)
        confidences.append(confidence)

        if is_footnote and confidence >= confidence_threshold:
            footnote_count += 1
        else:
            body_paragraphs.append(para)

            if is_footnote and confidence < confidence_threshold:
                low_confidence_count += 1

    classify_time = time.time() - classify_start
    print(f"  ✓ Classified {len(paragraphs)} paragraphs in {classify_time:.1f}s")
    print(f"    ({classify_time/len(paragraphs)*1000:.1f}ms per paragraph)")

    # Combine body text
    body_text = '\n\n'.join(body_paragraphs)

    # Statistics
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    stats = {
        'total_paragraphs': len(paragraphs),
        'body_paragraphs': len(body_paragraphs),
        'footnote_paragraphs': footnote_count,
        'footnote_percentage': (footnote_count / len(paragraphs) * 100) if paragraphs else 0,
        'low_confidence_count': low_confidence_count,
        'avg_confidence': avg_confidence,
        'classification_time_ms': classify_time * 1000,
        'confidence_threshold': confidence_threshold
    }

    print(f"\nClassification Results:")
    print(f"  Body text:  {len(body_paragraphs)} paragraphs ({100-stats['footnote_percentage']:.1f}%)")
    print(f"  Footnotes:  {footnote_count} paragraphs ({stats['footnote_percentage']:.1f}%)")
    print(f"  Avg confidence: {avg_confidence:.3f}")
    print(f"  Low confidence: {low_confidence_count} paragraphs")

    return {
        'body_text': body_text,
        'footnote_count': footnote_count,
        'body_para_count': len(body_paragraphs),
        'stats': stats
    }


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_with_ml_classifier.py <pdf_path> [model_path] [confidence_threshold]")
        print("\nExample:")
        print("  python extract_with_ml_classifier.py sample.pdf")
        print("  python extract_with_ml_classifier.py sample.pdf models/my_model 0.7")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    model_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    confidence_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

    # Extract body text
    result = extract_body_text_ml(pdf_path, model_path, confidence_threshold)

    # Save to file
    output_path = pdf_path.with_suffix('.body.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result['body_text'])

    print(f"\n✓ Body text saved to: {output_path}")
    print(f"  {result['body_para_count']} paragraphs")
    print(f"  {len(result['body_text'])} characters")


if __name__ == "__main__":
    main()
