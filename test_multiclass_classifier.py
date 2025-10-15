#!/usr/bin/env python3
"""
DoclingBert v2: Test the fine-tuned 7-class classifier on PDFs.

Loads the trained model and tests it on sample PDFs to verify
it can correctly classify all 7 document structure elements:
- body_text, heading, footnote, caption, page_header, page_footer, cover

Note: 'reference' and 'table' classes excluded due to no training samples.

Version: v2 (cite-assist uses v1)

Issue: https://github.com/donaldbraman/docling-testing/issues/7
"""

import json
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from docling.document_converter import DocumentConverter


def load_model(model_path: Path):
    """Load the fine-tuned multi-class classifier."""
    print("="*80)
    print("LOADING MODEL")
    print("="*80)

    # Load label map and metadata
    label_map_path = model_path / "label_map.json"
    with open(label_map_path) as f:
        metadata = json.load(f)

    # Handle both old and new metadata format
    if "label_map" in metadata:
        # New format with version metadata
        label_map = metadata["label_map"]
        model_version = metadata.get("version", "unknown")
        print(f"\n✓ Model: {metadata.get('model_name', 'DoclingBert')} {model_version}")
    else:
        # Old format (backward compatibility)
        label_map = metadata
        model_version = "v1"

    id_to_label = {v: k for k, v in label_map.items()}

    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    model.eval()

    print(f"\n✓ Model loaded from: {model_path}")
    print(f"  Parameters: {model.num_parameters():,}")
    print(f"  Classes: {list(label_map.keys())}")

    return tokenizer, model, id_to_label


def classify_text(text: str, tokenizer, model, id_to_label) -> tuple[str, float]:
    """Classify a single text paragraph.

    Returns:
        (predicted_label, confidence)
    """
    # Tokenize
    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding='max_length',
        truncation=True,
        max_length=1024
    )

    # Predict
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.nn.functional.softmax(logits, dim=-1)

    # Get prediction
    pred_id = torch.argmax(probs, dim=-1).item()
    confidence = probs[0, pred_id].item()
    label = id_to_label[pred_id]

    return label, confidence


def test_on_samples(tokenizer, model, id_to_label):
    """Test on sample texts to verify classification."""
    print("\n" + "="*80)
    print("TESTING ON SAMPLE TEXTS")
    print("="*80)

    # Sample texts for all 7 classes
    samples = [
        ("body_text", "The Supreme Court held that the government must provide compensation when taking private property for public use. This principle, established in the Fifth Amendment, forms the foundation of takings jurisprudence."),
        ("body_text", "In recent decades, criminal justice reform has emerged as a critical policy priority. Scholars have identified prosecutorial discretion as a key factor in mass incarceration."),
        ("heading", "I. INTRODUCTION TO CONSTITUTIONAL LAW"),
        ("heading", "A. Historical Context and Development"),
        ("footnote", "1 See Lucas v. South Carolina Coastal Council, 505 U.S. 1003, 1029 (1992)."),
        ("footnote", "15 For a comprehensive discussion of background principles, see Rose, Property as Storytelling, 2 YALE J.L. & HUMAN. 37, 52-54 (1990)."),
        ("caption", "Figure 1. Distribution of prosecutorial decisions by jurisdiction, showing significant variation across counties (N=3,247 cases)."),
        ("caption", "Table 2. Summary statistics for conviction rates by offense type, controlling for demographic factors."),
        ("page_header", "HARVARD LAW REVIEW                                                  [Vol. 135:123"),
        ("page_footer", "2024]           PROSECUTORIAL DISCRETION AND REFORM                         147"),
        ("cover", "Downloaded from HeinOnline at 10.123.45.67 on 2024-01-15. Citation: 135 Harv. L. Rev. 123 (2021). Bluebook 21st ed.: Author, Title, 135 HARV. L. REV. 123 (2021)."),
        ("cover", "JSTOR is a not-for-profit service. Your use of the JSTOR archive indicates acceptance of Terms and Conditions of Use. Accessed: 2024-01-15 from www.jstor.org"),
    ]

    print("\nClassifying sample texts:\n")

    correct = 0
    for expected_label, text in samples:
        pred_label, confidence = classify_text(text, tokenizer, model, id_to_label)

        # Determine status
        match = "✓" if pred_label == expected_label else "✗"
        if pred_label == expected_label:
            correct += 1

        print(f"{match} Expected: {expected_label:12s} | Predicted: {pred_label:12s} (conf: {confidence:.3f})")
        print(f"  Text: {text[:80]}...")
        print()

    accuracy = correct / len(samples)
    print(f"Sample accuracy: {correct}/{len(samples)} ({accuracy:.1%})")


def test_on_pdf(pdf_path: Path, tokenizer, model, id_to_label):
    """Test on a real PDF."""
    print("\n" + "="*80)
    print(f"TESTING ON PDF: {pdf_path.name}")
    print("="*80)

    # Extract text with docling
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc_md = result.document.export_to_markdown()

    # Split into paragraphs
    paragraphs = [p.strip() for p in doc_md.split('\n\n') if p.strip() and len(p) >= 20]

    print(f"\nExtracted {len(paragraphs)} paragraphs")
    print(f"Classifying first 20 paragraphs:\n")

    # Classify first 20 paragraphs
    label_counts = {
        'body_text': 0, 'heading': 0, 'footnote': 0,
        'caption': 0, 'page_header': 0, 'page_footer': 0, 'cover': 0
    }

    for i, para in enumerate(paragraphs[:20], 1):
        pred_label, confidence = classify_text(para, tokenizer, model, id_to_label)
        if pred_label in label_counts:
            label_counts[pred_label] += 1

        # Show first 3 paragraphs in detail
        if i <= 3:
            print(f"{i}. {pred_label:12s} (conf: {confidence:.3f})")
            print(f"   {para[:100]}...")
            print()

    print(f"\nLabel distribution (first 20 paragraphs):")
    for label, count in label_counts.items():
        percentage = (count / 20) * 100
        print(f"  {label:12s} {count:3d} ({percentage:5.1f}%)")


def main():
    """Main test pipeline."""
    print("="*80)
    print("TESTING DOCLINGBERT V2: 7-CLASS CLASSIFIER")
    print("="*80)

    base_dir = Path(__file__).parent
    model_path = base_dir / "models" / "doclingbert-v2" / "final_model"

    if not model_path.exists():
        print(f"\n❌ Error: Model not found at {model_path}")
        print("Train the model first: python train_multiclass_classifier.py")
        return

    # Load model
    tokenizer, model, id_to_label = load_model(model_path)

    # Test on samples
    test_on_samples(tokenizer, model, id_to_label)

    # Test on PDFs
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")

    # Test on HeinOnline PDF (should have cover)
    heinonline_pdfs = list(pdf_dir.glob("*harvard*.pdf"))
    if heinonline_pdfs:
        test_on_pdf(heinonline_pdfs[0], tokenizer, model, id_to_label)

    # Test on JSTOR PDF (should have cover)
    jstor_pdfs = list(pdf_dir.glob("*jstor*.pdf")) or list(pdf_dir.glob("*.pdf"))
    if jstor_pdfs and jstor_pdfs[0] != heinonline_pdfs[0]:
        test_on_pdf(jstor_pdfs[0], tokenizer, model, id_to_label)

    print("\n" + "="*80)
    print("✓ TESTING COMPLETE")
    print("="*80)
    print(f"\nNext steps:")
    print(f"  1. Review classification results above")
    print(f"  2. Test on more PDFs if needed")
    print(f"  3. Integrate into document processing pipeline")


if __name__ == "__main__":
    main()
