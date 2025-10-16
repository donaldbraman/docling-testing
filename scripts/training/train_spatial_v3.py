#!/usr/bin/env python3
"""
DoclingBERT v3: Train Spatial ModernBERT for 7-Class Document Classification

Integrates spatial features (bounding boxes) with text for document structure
classification.

Architecture:
- Base: ModernBERT-base (152M params)
- Spatial: 6 embedding layers (x0, y0, x1, y1, width, height)
- Loss: Focal Loss (α=0.25, γ=2.0) for class imbalance
- Classes: body_text, heading, footnote, caption, page_header, page_footer, cover

Expected improvement over v2 text-only:
- body_text F1: 84% → 92%
- Overall F1 macro: 85% → 90%+

Issue: https://github.com/donaldbraman/docling-testing/issues/18
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer,
    ModernBertConfig,
    Trainer,
    TrainingArguments,
)

# Add scripts to path for imports
sys.path.append(str(Path(__file__).parent))
from spatial_modernbert import FocalLoss, SpatialModernBERT

# Label mapping (7 classes)
LABEL_MAP = {
    "body_text": 0,
    "heading": 1,
    "footnote": 2,
    "caption": 3,
    "page_header": 4,
    "page_footer": 5,
    "cover": 6,
}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}


def compute_metrics(eval_pred):
    """Compute metrics for evaluation."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1_macro": f1_score(labels, predictions, average="macro"),
        "f1_weighted": f1_score(labels, predictions, average="weighted"),
        "precision_macro": precision_score(labels, predictions, average="macro", zero_division=0),
        "recall_macro": recall_score(labels, predictions, average="macro", zero_division=0),
    }


def load_and_prepare_data(corpus_path: Path):
    """Load spatial corpus and prepare for training.

    Expected columns: text, label, x0, y0, x1, y1, width, height, page, pdf
    """
    print("\n" + "=" * 80)
    print("LOADING SPATIAL CORPUS")
    print("=" * 80)

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Spatial corpus not found: {corpus_path}\n"
            "Run build_spatial_corpus_v3.py first to generate training data"
        )

    df = pd.read_csv(corpus_path)
    print(f"\nLoaded corpus: {len(df):,} text blocks")
    print(f"Columns: {list(df.columns)}")

    # Validate required columns
    required_cols = ["text", "label", "x0", "y0", "x1", "y1", "width", "height"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Show class distribution
    print("\nClass distribution:")
    for label_name, label_id in LABEL_MAP.items():
        count = (df["label"] == label_name).sum()
        percentage = (count / len(df)) * 100
        print(f"  {label_name:15s} {count:5,} ({percentage:5.1f}%)")

    # Show spatial feature statistics
    print("\nSpatial feature ranges:")
    for col in ["x0", "y0", "x1", "y1", "width", "height"]:
        print(f"  {col:10s} [{df[col].min():3d}, {df[col].max():3d}]  mean={df[col].mean():.1f}")

    # Prepare data
    texts = df["text"].tolist()
    labels = [LABEL_MAP[label] for label in df["label"]]

    # Prepare spatial features (6 features per sample)
    bbox_features = df[["x0", "y0", "x1", "y1", "width", "height"]].values

    # Validate bbox values are in [0-999]
    if bbox_features.min() < 0 or bbox_features.max() > 999:
        print("\n⚠️  Warning: Bbox features outside [0-999] range!")
        print(f"  Min: {bbox_features.min()}, Max: {bbox_features.max()}")
        # Clamp to valid range
        bbox_features = np.clip(bbox_features, 0, 999).astype(int)

    # Train/val/test split (70/15/15)
    X_train, X_temp, y_train, y_temp, bbox_train, bbox_temp = train_test_split(
        texts, labels, bbox_features, test_size=0.3, stratify=labels, random_state=42
    )

    X_val, X_test, y_val, y_test, bbox_val, bbox_test = train_test_split(
        X_temp, y_temp, bbox_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    print("\nDataset splits:")
    for split_name, y_split in [("Train", y_train), ("Val", y_val), ("Test", y_test)]:
        counts = [sum(1 for y in y_split if y == label_id) for label_id in range(len(LABEL_MAP))]
        counts_str = ", ".join([f"{count:,} {ID_TO_LABEL[i]}" for i, count in enumerate(counts)])
        print(f"  {split_name:5s} {len(y_split):5,} ({counts_str})")

    return (X_train, X_val, X_test, y_train, y_val, y_test, bbox_train, bbox_val, bbox_test)


def tokenize_data(
    tokenizer, X_train, X_val, X_test, y_train, y_val, y_test, bbox_train, bbox_val, bbox_test
):
    """Tokenize data and create datasets with spatial features."""
    print("\n" + "=" * 80)
    print("TOKENIZING DATA")
    print("=" * 80)

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=1024,  # Optimal for MPS memory
        )

    # Create datasets with spatial features
    train_dataset = Dataset.from_dict(
        {"text": X_train, "label": y_train, "bbox_features": bbox_train.tolist()}
    )
    val_dataset = Dataset.from_dict(
        {"text": X_val, "label": y_val, "bbox_features": bbox_val.tolist()}
    )
    test_dataset = Dataset.from_dict(
        {"text": X_test, "label": y_test, "bbox_features": bbox_test.tolist()}
    )

    # Tokenize
    print("\nTokenizing train set...")
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    print("Tokenizing validation set...")
    val_dataset = val_dataset.map(tokenize_function, batched=True)
    print("Tokenizing test set...")
    test_dataset = test_dataset.map(tokenize_function, batched=True)

    return train_dataset, val_dataset, test_dataset


class FocalLossTrainer(Trainer):
    """Custom Trainer that uses Focal Loss instead of cross-entropy."""

    def __init__(self, focal_loss, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.focal_loss = focal_loss

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        # Extract bbox_features from inputs
        bbox_features = inputs.pop("bbox_features")
        labels = inputs.pop("labels")

        # Forward pass with spatial features
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            bbox_features=bbox_features,
            labels=None,  # Don't use model's internal loss
            return_dict=True,
        )

        logits = outputs["logits"]

        # Apply Focal Loss
        loss = self.focal_loss(logits, labels)

        return (loss, outputs) if return_outputs else loss


def train_model(train_dataset, val_dataset, output_dir: Path, max_steps: int = 1000):
    """Train Spatial ModernBERT for 7-class classification."""
    print("\n" + "=" * 80)
    print("INITIALIZING SPATIAL MODERNBERT")
    print("=" * 80)

    # Load ModernBERT config and tokenizer
    model_name = "answerdotai/ModernBERT-base"
    print(f"\nLoading {model_name}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Create ModernBERT config
    config = ModernBertConfig.from_pretrained(model_name)

    # Initialize Spatial ModernBERT
    model = SpatialModernBERT(config, num_labels=7)

    # Load pre-trained weights for ModernBERT part
    from transformers import ModernBertModel

    pretrained = ModernBertModel.from_pretrained(model_name)
    model.modernbert.load_state_dict(pretrained.state_dict())

    print("  ✓ Model loaded with spatial embeddings")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"  Classes: {list(LABEL_MAP.keys())}")
    print(
        f"  Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'MPS' if torch.backends.mps.is_available() else 'CPU'}"
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        # Training hyperparameters
        max_steps=max_steps,  # ~1000 steps for quick test
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
        # Evaluation strategy
        eval_strategy="steps",
        eval_steps=50,  # Eval every 50 steps
        save_strategy="steps",
        save_steps=50,
        save_total_limit=5,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        # Logging
        logging_dir=str(output_dir / "logs"),
        logging_steps=10,
        report_to="none",
        # Performance
        fp16=torch.cuda.is_available(),
        gradient_accumulation_steps=2,  # Effective batch size = 8
        gradient_checkpointing=False,  # Disable for custom model
        # Reproducibility
        seed=42,
    )

    # Initialize Focal Loss
    focal_loss = FocalLoss(alpha=0.25, gamma=2.0)

    # Initialize trainer
    print("\n" + "=" * 80)
    print("TRAINING MODEL WITH FOCAL LOSS")
    print("=" * 80)
    print(f"  Max steps: {max_steps}")
    print(f"  Eval every: {training_args.eval_steps} steps")
    print(f"  Focal Loss: α={focal_loss.alpha}, γ={focal_loss.gamma}")

    trainer = FocalLossTrainer(
        focal_loss=focal_loss,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    # Train
    print("\nStarting training...")
    train_result = trainer.train()

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)
    print(f"\nTraining time: {train_result.metrics['train_runtime']:.2f}s")
    print(f"Samples/second: {train_result.metrics['train_samples_per_second']:.2f}")

    # Save model
    model_path = output_dir / "final_model"
    trainer.save_model(str(model_path))
    tokenizer.save_pretrained(str(model_path))

    # Save label mapping with version metadata
    label_map_path = model_path / "label_map.json"
    metadata = {
        "model_name": "DoclingBERT",
        "version": "v3",
        "base_model": "answerdotai/ModernBERT-base",
        "num_classes": 7,
        "spatial_features": ["x0", "y0", "x1", "y1", "width", "height"],
        "focal_loss": {"alpha": focal_loss.alpha, "gamma": focal_loss.gamma},
        "label_map": LABEL_MAP,
    }
    with open(label_map_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Model saved: {model_path}")
    print(f"✓ Model metadata saved: {label_map_path}")
    print("  Version: DoclingBERT v3 (spatial)")

    return trainer, tokenizer, model


def evaluate_model(trainer, test_dataset, output_dir: Path):
    """Evaluate model on test set."""
    print("\n" + "=" * 80)
    print("EVALUATING ON TEST SET")
    print("=" * 80)

    # Predict
    predictions = trainer.predict(test_dataset)
    y_pred = np.argmax(predictions.predictions, axis=-1)
    y_true = predictions.label_ids

    # Classification report
    print("\nClassification Report:")
    class_names = [ID_TO_LABEL[i] for i in range(len(LABEL_MAP))]
    print(classification_report(y_true, y_pred, target_names=class_names, digits=3))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    print("\nConfusion Matrix:")
    print("                Predicted")
    print(f"                {'  '.join([f'{name:10s}' for name in class_names])}")
    for i, true_label in enumerate(class_names):
        row = "  ".join([f"{cm[i, j]:10d}" for j in range(len(class_names))])
        print(f"Actual {true_label:10s} {row}")

    # Detailed metrics
    f1_macro = f1_score(y_true, y_pred, average="macro")
    f1_weighted = f1_score(y_true, y_pred, average="weighted")
    precision = precision_score(y_true, y_pred, average="macro")
    recall = recall_score(y_true, y_pred, average="macro")
    accuracy = accuracy_score(y_true, y_pred)

    print("\nKey Metrics:")
    print(f"  Accuracy:       {accuracy:.3f}")
    print(f"  F1 Macro:       {f1_macro:.3f}")
    print(f"  F1 Weighted:    {f1_weighted:.3f}")
    print(f"  Precision:      {precision:.3f}")
    print(f"  Recall:         {recall:.3f}")

    # Per-class F1
    f1_per_class = f1_score(y_true, y_pred, average=None)
    print("\nPer-class F1 Scores:")
    for i, label_name in enumerate(class_names):
        print(f"  {label_name:15s} {f1_per_class[i]:.3f}")

    # Save confusion matrix plot
    fig, ax = plt.subplots(figsize=(10, 8))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    plt.title(
        f"DoclingBERT v3: Spatial 7-Class Classifier\nF1 Macro={f1_macro:.3f}, Accuracy={accuracy:.3f}"
    )

    results_dir = output_dir / "evaluation"
    results_dir.mkdir(parents=True, exist_ok=True)
    cm_path = results_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\n✓ Confusion matrix saved: {cm_path}")

    # Save metrics
    metrics = {
        "accuracy": float(accuracy),
        "f1_macro": float(f1_macro),
        "f1_weighted": float(f1_weighted),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_per_class": {
            name: float(f1) for name, f1 in zip(class_names, f1_per_class, strict=False)
        },
        "test_size": len(y_true),
        "confusion_matrix": cm.tolist(),
    }

    metrics_path = results_dir / "test_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved: {metrics_path}")

    return metrics


def main():
    """Main training pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Train DoclingBERT v3 with spatial features")
    parser.add_argument("--max-steps", type=int, default=1000, help="Max training steps")
    parser.add_argument(
        "--corpus",
        type=str,
        default="data/spatial_7class_corpus.csv",
        help="Path to spatial corpus CSV",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("DOCLINGBERT V3: SPATIAL 7-CLASS DOCUMENT CLASSIFICATION")
    print("=" * 80)
    print("\nModel: DoclingBERT v3 (Spatial ModernBERT)")
    print("Architecture: Text + Bounding Box Embeddings")
    print("Loss: Focal Loss (α=0.25, γ=2.0)")
    print(f"\nTraining for {args.max_steps} steps\n")

    base_dir = Path(__file__).parent.parent.parent
    corpus_path = base_dir / args.corpus
    output_dir = base_dir / "models" / "doclingbert-v3-spatial"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for GPU
    if torch.cuda.is_available():
        print(f"\n✓ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    elif torch.backends.mps.is_available():
        print("\n✓ Apple Silicon MPS available - training will use Metal acceleration")
    else:
        print("\n⚠️  No GPU/MPS detected - training will use CPU")
        print("  Auto-continuing with available hardware...")

    try:
        # Load data
        (X_train, X_val, X_test, y_train, y_val, y_test, bbox_train, bbox_val, bbox_test) = (
            load_and_prepare_data(corpus_path)
        )

        # Tokenize
        model_name = "answerdotai/ModernBERT-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        train_dataset, val_dataset, test_dataset = tokenize_data(
            tokenizer,
            X_train,
            X_val,
            X_test,
            y_train,
            y_val,
            y_test,
            bbox_train,
            bbox_val,
            bbox_test,
        )

        # Train
        trainer, tokenizer, model = train_model(
            train_dataset, val_dataset, output_dir, max_steps=args.max_steps
        )

        # Evaluate
        metrics = evaluate_model(trainer, test_dataset, output_dir)

        # Final summary
        print("\n" + "=" * 80)
        print("✓ TRAINING PIPELINE COMPLETE")
        print("=" * 80)
        print(f"\nFinal F1 Macro: {metrics['f1_macro']:.3f}")
        print(f"Model saved to: {output_dir / 'final_model'}")

        # Compare with v2 target
        body_text_f1 = metrics["f1_per_class"].get("body_text", 0)
        print(f"\nbody_text F1: {body_text_f1:.3f}")
        if body_text_f1 >= 0.92:
            print("🎉 Excellent! body_text F1 >= 92% achieved (v3 target)!")
        elif body_text_f1 >= 0.84:
            print("✅ Good! body_text F1 >= 84% (v2 baseline)")

        if metrics["f1_macro"] >= 0.90:
            print("🎉 Excellent! F1 Macro >= 0.90 achieved!")
        elif metrics["f1_macro"] >= 0.85:
            print("✅ Good! F1 Macro >= 0.85 achieved")

        print("\nNext steps:")
        print("  1. Create PR for Issue #18")
        print("  2. Bump version to v3.0.0")
        print("  3. Merge and close issue")

    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
