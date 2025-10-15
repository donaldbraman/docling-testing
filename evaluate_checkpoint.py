#!/usr/bin/env python3
"""
Evaluate a DoclingBert checkpoint on the test set with detailed per-class metrics.

Usage:
    python evaluate_checkpoint.py --checkpoint models/doclingbert-v2-quick-test/checkpoints/checkpoint-50
"""

import argparse
from pathlib import Path
import json
import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from datasets import Dataset
import numpy as np

# DoclingBert v2 label mapping (7 classes)
# MUST match train_multiclass_classifier.py exactly!
LABEL_MAP = {
    'body_text': 0,
    'heading': 1,
    'footnote': 2,
    'caption': 3,
    'page_header': 4,
    'page_footer': 5,
    'cover': 6,
}

ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}


def load_test_data(corpus_path: Path) -> tuple[Dataset, dict]:
    """Load test dataset using same split as training (random_state=42)."""
    print("="*80)
    print("LOADING TEST DATA")
    print("="*80)

    # Load corpus
    df = pd.read_csv(corpus_path)
    print(f"\n✓ Loaded corpus: {len(df):,} total samples")

    # Prepare data
    texts = df['text'].tolist()
    labels = [LABEL_MAP[label] for label in df['label']]

    # Recreate same train/val/test split as training (70/15/15)
    # IMPORTANT: Must use same random_state=42 to get identical split
    X_train, X_temp, y_train, y_temp = train_test_split(
        texts, labels, test_size=0.3, stratify=labels, random_state=42
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    print(f"\n✓ Test set: {len(X_test):,} samples (15% of corpus)")

    # Class distribution
    print("\nClass distribution in test set:")
    for label_name, label_id in LABEL_MAP.items():
        count = sum(1 for y in y_test if y == label_id)
        pct = (count / len(y_test)) * 100 if count > 0 else 0
        print(f"  {label_name:15s} {count:6,} ({pct:5.1f}%)")

    # Convert to HuggingFace Dataset
    test_data = {
        'text': X_test,
        'label_id': y_test,
        'label': [ID_TO_LABEL[y] for y in y_test]
    }
    test_dataset = Dataset.from_dict(test_data)

    return test_dataset, ID_TO_LABEL


def load_checkpoint(checkpoint_path: Path):
    """Load model and tokenizer from checkpoint."""
    print("\n" + "="*80)
    print("LOADING CHECKPOINT")
    print("="*80)

    print(f"\n✓ Loading from: {checkpoint_path}")

    # Load tokenizer from base model (checkpoint may not have all tokenizer files)
    base_model = "answerdotai/ModernBERT-base"
    print(f"✓ Loading tokenizer from: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    # Load model weights from checkpoint
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint_path)
    model.eval()

    # Check for MPS (Apple Silicon GPU)
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("✓ Using MPS (Apple Silicon GPU)")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print("✓ Using CUDA GPU")
    else:
        device = torch.device("cpu")
        print("✓ Using CPU")

    model.to(device)

    print(f"✓ Model parameters: {model.num_parameters():,}")
    print(f"✓ Num classes: {model.config.num_labels}")

    return tokenizer, model, device


def evaluate_model(model, tokenizer, device, test_dataset, id_to_label):
    """Run evaluation and compute per-class metrics."""
    print("\n" + "="*80)
    print("RUNNING EVALUATION")
    print("="*80)

    all_preds = []
    all_labels = []
    all_texts = []

    print(f"\nProcessing {len(test_dataset):,} test samples...")

    # Process in batches for efficiency
    batch_size = 8 if device.type == "mps" else 16

    for i in range(0, len(test_dataset), batch_size):
        batch = test_dataset[i:i+batch_size]
        texts = batch['text'] if isinstance(batch['text'], list) else [batch['text']]
        labels = batch['label_id'] if isinstance(batch['label_id'], list) else [batch['label_id']]

        # Tokenize
        inputs = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Predict
        with torch.no_grad():
            outputs = model(**inputs)
            preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy()

        all_preds.extend(preds)
        all_labels.extend(labels)
        all_texts.extend(texts)

        # Progress indicator
        if (i // batch_size) % 100 == 0:
            progress = (i / len(test_dataset)) * 100
            print(f"  {progress:5.1f}% complete ({i:,}/{len(test_dataset):,})")

    print("  100.0% complete\n")

    # Convert predictions to label names
    pred_labels = [id_to_label[p] for p in all_preds]
    true_labels = [id_to_label[l] for l in all_labels]

    return pred_labels, true_labels, all_texts


def print_results(pred_labels, true_labels, id_to_label):
    """Print detailed evaluation metrics."""
    print("="*80)
    print("EVALUATION RESULTS")
    print("="*80)

    # Get classes present in data (true or predicted)
    present_labels = sorted(set(true_labels) | set(pred_labels))

    # Classification report (only for present classes)
    print("\nPer-Class Metrics:")
    print("-" * 80)
    report = classification_report(
        true_labels,
        pred_labels,
        labels=present_labels,
        target_names=present_labels,
        digits=4,
        zero_division=0
    )
    print(report)

    # Get metrics as dict for emphasis
    from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score

    # Overall metrics
    accuracy = accuracy_score(true_labels, pred_labels)
    f1_macro = f1_score(true_labels, pred_labels, average='macro', zero_division=0)
    f1_weighted = f1_score(true_labels, pred_labels, average='weighted', zero_division=0)

    print("\n" + "="*80)
    print("SUMMARY METRICS")
    print("="*80)
    print(f"\nAccuracy:     {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"F1 Macro:     {f1_macro:.4f}")
    print(f"F1 Weighted:  {f1_weighted:.4f}")

    # Per-class F1 scores (sorted by class name)
    print("\n" + "-"*80)
    print("PER-CLASS F1 SCORES")
    print("-"*80)

    for label in sorted(id_to_label.values()):
        # Get F1 for this class
        f1 = f1_score(
            [1 if l == label else 0 for l in true_labels],
            [1 if p == label else 0 for p in pred_labels],
            zero_division=0
        )

        # Emphasize body_text
        marker = " ⭐ PRIMARY TARGET" if label == "body_text" else ""
        print(f"{label:15s} F1: {f1:.4f} ({f1*100:.2f}%){marker}")

    # Confusion matrix
    print("\n" + "-"*80)
    print("CONFUSION MATRIX")
    print("-"*80)
    cm = confusion_matrix(true_labels, pred_labels, labels=sorted(id_to_label.values()))

    labels = sorted(id_to_label.values())
    print("\nTrue \\ Pred  " + "  ".join(f"{l[:6]:>6s}" for l in labels))
    for i, label in enumerate(labels):
        row = "  ".join(f"{cm[i,j]:6d}" for j in range(len(labels)))
        print(f"{label:12s}  {row}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate checkpoint on test set")
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to checkpoint directory"
    )
    parser.add_argument(
        "--corpus",
        type=str,
        default="data/clean_7class_corpus.csv",
        help="Path to corpus CSV file"
    )

    args = parser.parse_args()

    base_dir = Path(__file__).parent
    checkpoint_path = base_dir / args.checkpoint
    corpus_path = base_dir / args.corpus

    if not checkpoint_path.exists():
        print(f"❌ Error: Checkpoint not found at {checkpoint_path}")
        return 1

    if not corpus_path.exists():
        print(f"❌ Error: Corpus not found at {corpus_path}")
        return 1

    print("="*80)
    print("DOCLINGBERT CHECKPOINT EVALUATION")
    print("="*80)
    print(f"\nCheckpoint: {checkpoint_path}")
    print(f"Corpus:     {corpus_path}")

    # Load data
    test_dataset, id_to_label = load_test_data(corpus_path)

    # Load model
    tokenizer, model, device = load_checkpoint(checkpoint_path)

    # Evaluate
    pred_labels, true_labels, all_texts = evaluate_model(
        model, tokenizer, device, test_dataset, id_to_label
    )

    # Print results
    print_results(pred_labels, true_labels, id_to_label)

    print("\n" + "="*80)
    print("✓ EVALUATION COMPLETE")
    print("="*80)

    return 0


if __name__ == "__main__":
    exit(main())
