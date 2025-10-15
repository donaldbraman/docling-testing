#!/usr/bin/env python3
"""
DoclingBert v2: Fine-tune ModernBERT for 7-class Document Structure Classification

Trains ModernBERT-base for comprehensive document structure classification:
- body_text: Main article content
- heading: Titles and section headers
- footnote: Footnote text
- caption: Figure and table captions
- page_header: Running headers
- page_footer: Running footers
- cover: Cover/title pages

Note: 'reference' and 'table' classes excluded due to no training samples.

Based on DocBank/PubLayNet research for optimal classification.

Version: v2 (cite-assist uses v1)

Issue: https://github.com/donaldbraman/docling-testing/issues/7
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
)
from sklearn.utils.class_weight import compute_class_weight
import matplotlib.pyplot as plt
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
)
from datasets import Dataset, DatasetDict


# Label mapping (7 classes - based on available data)
# Note: 'reference' and 'table' excluded due to no training samples
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


def compute_metrics(eval_pred):
    """Compute metrics for evaluation."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    return {
        'accuracy': accuracy_score(labels, predictions),
        'f1_macro': f1_score(labels, predictions, average='macro'),
        'f1_weighted': f1_score(labels, predictions, average='weighted'),
        'precision_macro': precision_score(labels, predictions, average='macro', zero_division=0),
        'recall_macro': recall_score(labels, predictions, average='macro', zero_division=0),
    }


def load_and_prepare_data(corpus_path: Path):
    """Load corpus and prepare for training."""
    print("\n" + "="*80)
    print("LOADING DATA")
    print("="*80)

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Corpus not found: {corpus_path}\n"
            "Run build_clean_corpus.py first to generate training data"
        )

    df = pd.read_csv(corpus_path)
    print(f"\nLoaded corpus: {len(df):,} paragraphs")

    # Show class distribution
    for label_name, label_id in LABEL_MAP.items():
        count = (df['label'] == label_name).sum()
        percentage = (count / len(df)) * 100
        print(f"  {label_name:15s} {count:5,} ({percentage:5.1f}%)")

    # Show source distribution
    print(f"\nData sources:")
    if 'source' in df.columns:
        for source in df['source'].unique():
            count = (df['source'] == source).sum()
            percentage = (count / len(df)) * 100
            print(f"  {source:20s} {count:5,} ({percentage:5.1f}%)")

    # Prepare data
    texts = df['text'].tolist()
    labels = [LABEL_MAP[label] for label in df['label']]

    # Check which classes are actually present
    unique_labels = np.unique(labels)
    present_classes = [ID_TO_LABEL[i] for i in unique_labels]

    print(f"\n⚠️  Warning: Only {len(unique_labels)} of 7 classes have training data:")
    print(f"  Present: {', '.join(present_classes)}")
    missing_classes = [name for name, id in LABEL_MAP.items() if id not in unique_labels]
    if missing_classes:
        print(f"  Missing: {', '.join(missing_classes)}")

    # Compute class weights to handle imbalance (only for present classes)
    class_weights_array = compute_class_weight(
        class_weight='balanced',
        classes=unique_labels,
        y=labels
    )

    # Create full weights array with 1.0 for missing classes
    class_weights = np.ones(len(LABEL_MAP))
    for i, label_id in enumerate(unique_labels):
        class_weights[label_id] = class_weights_array[i]

    print(f"\nClass weights (for imbalance correction):")
    for label_name, label_id in LABEL_MAP.items():
        if label_id in unique_labels:
            print(f"  {label_name:15s} {class_weights[label_id]:.3f}")
        else:
            print(f"  {label_name:15s} N/A (no training data)")

    # Train/val/test split (70/15/15)
    X_train, X_temp, y_train, y_temp = train_test_split(
        texts, labels, test_size=0.3, stratify=labels, random_state=42
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    print(f"\nDataset splits:")
    for split_name, y_split in [("Train", y_train), ("Val", y_val), ("Test", y_test)]:
        counts = [sum(1 for y in y_split if y == label_id) for label_id in range(len(LABEL_MAP))]
        counts_str = ", ".join([f"{count:,} {ID_TO_LABEL[i]}" for i, count in enumerate(counts)])
        print(f"  {split_name:5s} {len(y_split):,} ({counts_str})")

    return X_train, X_val, X_test, y_train, y_val, y_test, class_weights


def tokenize_data(tokenizer, X_train, X_val, X_test, y_train, y_val, y_test):
    """Tokenize data and create HuggingFace datasets."""
    print("\n" + "="*80)
    print("TOKENIZING DATA")
    print("="*80)

    def tokenize_function(examples):
        return tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=1024  # Optimal for MPS memory
        )

    # Create datasets
    train_dataset = Dataset.from_dict({'text': X_train, 'label': y_train})
    val_dataset = Dataset.from_dict({'text': X_val, 'label': y_val})
    test_dataset = Dataset.from_dict({'text': X_test, 'label': y_test})

    # Tokenize
    print("\nTokenizing train set...")
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    print("Tokenizing validation set...")
    val_dataset = val_dataset.map(tokenize_function, batched=True)
    print("Tokenizing test set...")
    test_dataset = test_dataset.map(tokenize_function, batched=True)

    return train_dataset, val_dataset, test_dataset


class WeightedLossTrainer(Trainer):
    """Custom Trainer that applies class weights to loss."""

    def __init__(self, class_weights, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = torch.tensor(class_weights, dtype=torch.float32)

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        # Move class weights to same device as logits
        weights = self.class_weights.to(logits.device)

        # Weighted cross-entropy loss
        loss_fct = torch.nn.CrossEntropyLoss(weight=weights)
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))

        return (loss, outputs) if return_outputs else loss


def train_model(train_dataset, val_dataset, class_weights, output_dir: Path):
    """Fine-tune ModernBERT for multi-class classification."""
    print("\n" + "="*80)
    print("INITIALIZING MODEL")
    print("="*80)

    # Load ModernBERT
    model_name = "answerdotai/ModernBERT-base"
    print(f"\nLoading {model_name}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=7,  # 7-class classification (based on available data)
        problem_type="single_label_classification",
    )

    print(f"  ✓ Model loaded: {model_name}")
    print(f"  Parameters: {model.num_parameters():,}")
    print(f"  Classes: {list(LABEL_MAP.keys())}")
    print(f"  Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'MPS' if torch.backends.mps.is_available() else 'CPU'}")

    # Training arguments (same optimal config from binary classifier)
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),

        # Training hyperparameters
        num_train_epochs=3,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,

        # Evaluation strategy
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,

        # Logging
        logging_dir=str(output_dir / "logs"),
        logging_steps=50,
        report_to="none",

        # Performance
        fp16=torch.cuda.is_available(),
        gradient_accumulation_steps=4,  # Effective batch size = 16
        gradient_checkpointing=True,

        # Reproducibility
        seed=42,
    )

    # Initialize trainer with class weights
    print("\n" + "="*80)
    print("TRAINING MODEL")
    print("="*80)

    trainer = WeightedLossTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # Train
    print("\nStarting training...")
    train_result = trainer.train()

    print("\n" + "="*80)
    print("TRAINING COMPLETE")
    print("="*80)
    print(f"\nTraining time: {train_result.metrics['train_runtime']:.2f}s")
    print(f"Samples/second: {train_result.metrics['train_samples_per_second']:.2f}")

    # Save model
    model_path = output_dir / "final_model"
    trainer.save_model(str(model_path))
    tokenizer.save_pretrained(str(model_path))

    # Save label mapping with version metadata
    label_map_path = model_path / "label_map.json"
    metadata = {
        "model_name": "DoclingBert",
        "version": "v2",
        "base_model": "answerdotai/ModernBERT-base",
        "num_classes": 7,
        "label_map": LABEL_MAP
    }
    with open(label_map_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Model saved: {model_path}")
    print(f"✓ Model metadata saved: {label_map_path}")
    print(f"  Version: DoclingBert v2")

    return trainer, tokenizer, model


def evaluate_model(trainer, test_dataset, output_dir: Path):
    """Evaluate model on test set."""
    print("\n" + "="*80)
    print("EVALUATING ON TEST SET")
    print("="*80)

    # Predict
    predictions = trainer.predict(test_dataset)
    y_pred = np.argmax(predictions.predictions, axis=-1)
    y_true = predictions.label_ids

    # Classification report
    print("\nClassification Report:")
    class_names = [ID_TO_LABEL[i] for i in range(len(LABEL_MAP))]
    print(classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        digits=3
    ))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    print("\nConfusion Matrix:")
    print(f"                Predicted")
    print(f"                {'  '.join([f'{name:10s}' for name in class_names])}")
    for i, true_label in enumerate(class_names):
        row = "  ".join([f"{cm[i,j]:10d}" for j in range(len(class_names))])
        print(f"Actual {true_label:10s} {row}")

    # Detailed metrics
    f1_macro = f1_score(y_true, y_pred, average='macro')
    f1_weighted = f1_score(y_true, y_pred, average='weighted')
    precision = precision_score(y_true, y_pred, average='macro')
    recall = recall_score(y_true, y_pred, average='macro')
    accuracy = accuracy_score(y_true, y_pred)

    print(f"\nKey Metrics:")
    print(f"  Accuracy:       {accuracy:.3f}")
    print(f"  F1 Macro:       {f1_macro:.3f}")
    print(f"  F1 Weighted:    {f1_weighted:.3f}")
    print(f"  Precision:      {precision:.3f}")
    print(f"  Recall:         {recall:.3f}")

    # Per-class F1
    f1_per_class = f1_score(y_true, y_pred, average=None)
    print(f"\nPer-class F1 Scores:")
    for i, label_name in enumerate(class_names):
        print(f"  {label_name:15s} {f1_per_class[i]:.3f}")

    # Save confusion matrix plot
    fig, ax = plt.subplots(figsize=(10, 8))
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=class_names
    )
    disp.plot(ax=ax, cmap='Blues', values_format='d')
    plt.title(f'DoclingBert v2: 7-Class Document Structure Classifier\nF1 Macro={f1_macro:.3f}, Accuracy={accuracy:.3f}')

    results_dir = output_dir / "evaluation"
    results_dir.mkdir(parents=True, exist_ok=True)
    cm_path = results_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✓ Confusion matrix saved: {cm_path}")

    # Save metrics
    metrics = {
        'accuracy': float(accuracy),
        'f1_macro': float(f1_macro),
        'f1_weighted': float(f1_weighted),
        'precision_macro': float(precision),
        'recall_macro': float(recall),
        'f1_per_class': {name: float(f1) for name, f1 in zip(class_names, f1_per_class)},
        'test_size': len(y_true),
        'confusion_matrix': cm.tolist(),
    }

    metrics_path = results_dir / "test_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved: {metrics_path}")

    return metrics


def main():
    """Main training pipeline."""
    print("="*80)
    print("DOCLINGBERT V2: 7-CLASS DOCUMENT STRUCTURE CLASSIFICATION")
    print("="*80)
    print("\nModel: DoclingBert v2 (ModernBERT-base fine-tuned)")
    print("Version: v2 (cite-assist uses v1)")
    print("\nUsing CLEAN ground truth labels from:")
    print("  - Semantic PDF tags (highest quality)")
    print("  - HTML-PDF text matching")
    print("  - Cover page patterns")
    print("  - Docling labels (corrected by semantic tags)\n")

    base_dir = Path(__file__).parent
    corpus_path = base_dir / "data" / "clean_7class_corpus.csv"
    output_dir = base_dir / "models" / "doclingbert-v2"
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
        X_train, X_val, X_test, y_train, y_val, y_test, class_weights = load_and_prepare_data(corpus_path)

        # Tokenize
        model_name = "answerdotai/ModernBERT-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        train_dataset, val_dataset, test_dataset = tokenize_data(
            tokenizer, X_train, X_val, X_test, y_train, y_val, y_test
        )

        # Train
        trainer, tokenizer, model = train_model(train_dataset, val_dataset, class_weights, output_dir)

        # Evaluate
        metrics = evaluate_model(trainer, test_dataset, output_dir)

        # Final summary
        print("\n" + "="*80)
        print("✓ TRAINING PIPELINE COMPLETE")
        print("="*80)
        print(f"\nFinal F1 Macro: {metrics['f1_macro']:.3f}")
        print(f"Model saved to: {output_dir / 'final_model'}")

        if metrics['f1_macro'] >= 0.85:
            print("\n🎉 Excellent! F1 Macro >= 0.85 achieved!")
        elif metrics['f1_macro'] >= 0.75:
            print("\n✅ Good! F1 Macro >= 0.75 achieved")
        else:
            print("\n⚠️  F1 below target. Consider:")
            print("   - Training for more epochs")
            print("   - Collecting more training data")
            print("   - Adjusting class weights or hyperparameters")

        print(f"\nNext steps:")
        print(f"  1. Test model: python test_multiclass_classifier.py")
        print(f"  2. Create PR for Issue #7")
        print(f"  3. Merge and close issue")

    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
