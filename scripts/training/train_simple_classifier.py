#!/usr/bin/env python3
"""
Train simple ModernBERT classifier with 4 features for 4-class document classification.

Features: page_number, y_position_normalized, normalized_font_size, text
Classes: body_text, footnote, front_matter, header

Note: footer class merged with footnote (both bottom of page, y > 0.9)

Production Optimization:
    For inference, the classification head can be separated and used with the
    cite-assist ModernBERT service to save ~600MB memory. Training still requires
    fine-tuning the full model locally.

Usage:
    uv run python scripts/training/train_simple_classifier.py --csv texas_law_review_extraterritoriality-patent-infringement_blocks.csv
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from datasets import Dataset
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer,
    ModernBertConfig,
    ModernBertModel,
    ModernBertPreTrainedModel,
    Trainer,
    TrainingArguments,
)

# 4-class label mapping
LABEL_MAP = {
    "body_text": 0,
    "footnote": 1,
    "front_matter": 2,
    "header": 3,
}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}


class SimpleTextBlockClassifier(ModernBertPreTrainedModel):
    """ModernBERT with 3 simple position features for document classification.

    Features:
    - Text: ModernBERT embeddings
    - page_number: Integer
    - y_position_normalized: Float [0, 1]
    - normalized_font_size: Float (relative to page median)
    """

    def __init__(self, config, num_labels=5):
        super().__init__(config)
        self.num_labels = num_labels

        # ModernBERT encoder
        self.modernbert = ModernBertModel(config)

        # Position encoder (3 features → 768 dim to match ModernBERT)
        self.position_encoder = nn.Linear(3, 768)

        # Classifier head (text + position → classes)
        dropout_prob = getattr(config, "classifier_dropout", 0.1)
        self.dropout = nn.Dropout(dropout_prob)
        self.classifier = nn.Linear(768 + 768, num_labels)

        # Initialize weights
        self.post_init()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        position_features=None,
        labels=None,
        return_dict=True,
    ):
        """Forward pass with position features."""

        if input_ids is None:
            raise ValueError("input_ids must be provided")
        if position_features is None:
            raise ValueError("position_features must be provided")

        # Get ModernBERT hidden states
        outputs = self.modernbert(
            input_ids=input_ids, attention_mask=attention_mask, return_dict=True
        )

        # Get [CLS] token representation
        text_emb = outputs.last_hidden_state[:, 0, :]  # [batch_size, 768]

        # Encode position features
        pos_emb = self.position_encoder(position_features)  # [batch_size, 768]

        # Combine text and position embeddings
        combined = torch.cat([text_emb, pos_emb], dim=-1)  # [batch_size, 1536]

        # Classification
        combined = self.dropout(combined)
        logits = self.classifier(combined)  # [batch_size, num_labels]

        # Calculate loss if labels provided
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

        if not return_dict:
            output = (logits,) + outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return {"loss": loss, "logits": logits}


class SimpleClassifierTrainer(Trainer):
    """Custom Trainer that handles position_features."""

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        position_features = inputs.pop("position_features")
        labels = inputs.pop("labels")

        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            position_features=position_features,
            labels=labels,
        )

        loss = outputs["loss"]
        return (loss, outputs) if return_outputs else loss


def load_and_prepare_data(csv_path: Path):
    """Load labeled CSV and prepare for training."""

    print("\n" + "=" * 80)
    print("LOADING LABELED DATA")
    print("=" * 80)

    df = pd.read_csv(csv_path)
    print(f"\nLoaded {len(df)} text blocks from {csv_path.name}")

    # Filter out NEEDS_REVIEW (not a training class)
    df = df[df["suggested_label"] != "NEEDS_REVIEW"]
    print(f"After filtering NEEDS_REVIEW: {len(df)} blocks")

    # Show class distribution
    print("\nClass distribution:")
    for label_name in LABEL_MAP:
        count = (df["suggested_label"] == label_name).sum()
        percentage = (count / len(df)) * 100
        print(f"  {label_name:15s} {count:5d} ({percentage:5.1f}%)")

    # Prepare features
    texts = df["text"].tolist()
    labels = [LABEL_MAP[label] for label in df["suggested_label"]]

    # Position features (3 features: page_number, y_position, font_size)
    position_features = df[["page_number", "y_position_normalized", "normalized_font_size"]].values

    print("\nPosition feature ranges:")
    print(
        f"  page_number:            [{position_features[:, 0].min():.0f}, {position_features[:, 0].max():.0f}]"
    )
    print(
        f"  y_position_normalized:  [{position_features[:, 1].min():.3f}, {position_features[:, 1].max():.3f}]"
    )
    print(
        f"  normalized_font_size:   [{position_features[:, 2].min():.3f}, {position_features[:, 2].max():.3f}]"
    )

    # Train/val/test split (70/15/15)
    X_train, X_temp, y_train, y_temp, pos_train, pos_temp = train_test_split(
        texts, labels, position_features, test_size=0.3, stratify=labels, random_state=42
    )

    X_val, X_test, y_val, y_test, pos_val, pos_test = train_test_split(
        X_temp, y_temp, pos_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    print("\nDataset splits:")
    print(f"  Train: {len(y_train):5d}")
    print(f"  Val:   {len(y_val):5d}")
    print(f"  Test:  {len(y_test):5d}")

    return (X_train, X_val, X_test, y_train, y_val, y_test, pos_train, pos_val, pos_test)


def tokenize_data(
    tokenizer, X_train, X_val, X_test, y_train, y_val, y_test, pos_train, pos_val, pos_test
):
    """Tokenize text and create datasets."""

    print("\n" + "=" * 80)
    print("TOKENIZING DATA")
    print("=" * 80)

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=512,  # Shorter for faster training
        )

    # Create datasets
    train_dataset = Dataset.from_dict(
        {
            "text": X_train,
            "label": y_train,
            "position_features": pos_train.tolist(),
        }
    )
    val_dataset = Dataset.from_dict(
        {
            "text": X_val,
            "label": y_val,
            "position_features": pos_val.tolist(),
        }
    )
    test_dataset = Dataset.from_dict(
        {
            "text": X_test,
            "label": y_test,
            "position_features": pos_test.tolist(),
        }
    )

    # Tokenize
    print("\nTokenizing datasets...")
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    val_dataset = val_dataset.map(tokenize_function, batched=True)
    test_dataset = test_dataset.map(tokenize_function, batched=True)

    return train_dataset, val_dataset, test_dataset


def compute_metrics(eval_pred):
    """Compute metrics for evaluation."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    # Accuracy per class
    accuracies = {}
    for label_id, label_name in ID_TO_LABEL.items():
        mask = labels == label_id
        if mask.sum() > 0:
            accuracies[label_name] = (predictions[mask] == labels[mask]).mean()

    return {
        "accuracy": (predictions == labels).mean(),
        **{f"acc_{name}": acc for name, acc in accuracies.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="Train simple text block classifier")
    parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Labeled CSV filename (in results/text_block_extraction/)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs (default: 10)",
    )

    args = parser.parse_args()

    # Setup paths
    csv_path = Path(f"results/text_block_extraction/{args.csv}")
    output_dir = Path("models/simple_text_classifier")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}")
        return 1

    print("=" * 80)
    print("SIMPLE TEXT BLOCK CLASSIFIER TRAINING")
    print("=" * 80)
    print(f"\nInput: {csv_path}")
    print(f"Output: {output_dir}")

    # Load data
    data = load_and_prepare_data(csv_path)
    X_train, X_val, X_test, y_train, y_val, y_test, pos_train, pos_val, pos_test = data

    # Load tokenizer
    print("\n" + "=" * 80)
    print("INITIALIZING MODEL")
    print("=" * 80)
    print("\nLoading ModernBERT tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")

    # Tokenize data
    train_dataset, val_dataset, test_dataset = tokenize_data(
        tokenizer, X_train, X_val, X_test, y_train, y_val, y_test, pos_train, pos_val, pos_test
    )

    # Initialize model
    print("\nInitializing SimpleTextBlockClassifier...")
    config = ModernBertConfig.from_pretrained("answerdotai/ModernBERT-base")
    model = SimpleTextBlockClassifier(config, num_labels=len(LABEL_MAP))

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=2e-5,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to="none",
        use_mps_device=True,  # Use Apple Silicon GPU
    )

    # Initialize trainer
    trainer = SimpleClassifierTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    # Train
    print("\n" + "=" * 80)
    print("TRAINING")
    print("=" * 80)
    trainer.train()

    # Evaluate on test set
    print("\n" + "=" * 80)
    print("EVALUATION ON TEST SET")
    print("=" * 80)
    test_results = trainer.predict(test_dataset)
    predictions = np.argmax(test_results.predictions, axis=-1)
    true_labels = test_results.label_ids

    # Classification report
    print("\nClassification Report:")
    print(
        classification_report(
            true_labels,
            predictions,
            target_names=list(LABEL_MAP.keys()),
            digits=3,
        )
    )

    # Confusion matrix
    print("\nConfusion Matrix:")
    cm = confusion_matrix(true_labels, predictions)
    print("           ", " ".join([f"{ID_TO_LABEL[i]:>12s}" for i in range(len(LABEL_MAP))]))
    for i, row in enumerate(cm):
        print(f"{ID_TO_LABEL[i]:>12s}", " ".join([f"{val:12d}" for val in row]))

    # Save model
    final_model_dir = output_dir / "final_model"
    print("\n" + "=" * 80)
    print("SAVING MODEL")
    print("=" * 80)
    print(f"\nSaving to: {final_model_dir}")

    model.save_pretrained(final_model_dir)
    tokenizer.save_pretrained(final_model_dir)

    # Save label map
    label_map_path = final_model_dir / "label_map.json"
    with open(label_map_path, "w") as f:
        json.dump(
            {
                "label_map": LABEL_MAP,
                "id_to_label": ID_TO_LABEL,
                "num_labels": len(LABEL_MAP),
            },
            f,
            indent=2,
        )

    print(f"✓ Model saved to: {final_model_dir}")
    print(f"✓ Label map saved to: {label_map_path}")

    return 0


if __name__ == "__main__":
    exit(main())
