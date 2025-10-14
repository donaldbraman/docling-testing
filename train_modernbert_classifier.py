#!/usr/bin/env python3
"""
Fine-tune ModernBERT for Binary Classification (Body Text vs Footnote)

Uses labeled PDF corpus from HTML/PDF label transfer to fine-tune
ModernBERT-large for footnote detection.

Issue: https://github.com/donaldbraman/docling-testing/issues/4
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


def compute_metrics(eval_pred):
    """Compute metrics for evaluation."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    return {
        'accuracy': accuracy_score(labels, predictions),
        'f1': f1_score(labels, predictions, average='binary'),
        'precision': precision_score(labels, predictions, average='binary'),
        'recall': recall_score(labels, predictions, average='binary'),
    }


def load_and_prepare_data(corpus_path: Path):
    """Load corpus and prepare for training."""
    print("\n" + "="*80)
    print("LOADING DATA")
    print("="*80)

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Corpus not found: {corpus_path}\n"
            "Run match_html_pdf.py first to generate training data"
        )

    df = pd.read_csv(corpus_path)
    print(f"\nLoaded corpus: {len(df):,} paragraphs")
    print(f"  Body text: {(df['html_label']=='body_text').sum():,}")
    print(f"  Footnotes: {(df['html_label']=='footnote').sum():,}")

    # Prepare data
    texts = df['text'].tolist()
    labels = [1 if label == 'footnote' else 0 for label in df['html_label']]

    # Train/val/test split (70/15/15)
    X_train, X_temp, y_train, y_temp = train_test_split(
        texts, labels, test_size=0.3, stratify=labels, random_state=42
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    print(f"\nDataset splits:")
    print(f"  Train: {len(X_train):,} ({sum(y_train):,} footnotes, {len(y_train)-sum(y_train):,} body)")
    print(f"  Val:   {len(X_val):,} ({sum(y_val):,} footnotes, {len(y_val)-sum(y_val):,} body)")
    print(f"  Test:  {len(X_test):,} ({sum(y_test):,} footnotes, {len(y_test)-sum(y_test):,} body)")

    return X_train, X_val, X_test, y_train, y_val, y_test


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
            max_length=1024  # Optimal for MPS memory: 1024 tokens
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


def train_model(train_dataset, val_dataset, output_dir: Path):
    """Fine-tune ModernBERT for classification."""
    print("\n" + "="*80)
    print("INITIALIZING MODEL")
    print("="*80)

    # Load ModernBERT
    model_name = "answerdotai/ModernBERT-base"  # Base model: best performance (eval_loss 0.296)
    print(f"\nLoading {model_name}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        problem_type="single_label_classification",
    )

    print(f"  ✓ Model loaded: {model_name}")
    print(f"  Parameters: {model.num_parameters():,}")
    print(f"  Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),

        # Training hyperparameters
        num_train_epochs=3,
        per_device_train_batch_size=2,  # Optimal batch size for MPS (from experiments)
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
        metric_for_best_model="f1",
        greater_is_better=True,

        # Logging
        logging_dir=str(output_dir / "logs"),
        logging_steps=50,
        report_to="none",  # Disable wandb/tensorboard

        # Performance
        fp16=torch.cuda.is_available(),  # Mixed precision if GPU available
        gradient_accumulation_steps=4,  # Effective batch size = 4 * 4 = 16
        gradient_checkpointing=True,  # Save memory

        # Reproducibility
        seed=42,
    )

    # Initialize trainer
    print("\n" + "="*80)
    print("TRAINING MODEL")
    print("="*80)

    trainer = Trainer(
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
    print(f"\n✓ Model saved: {model_path}")

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

    # Metrics
    print("\nClassification Report:")
    print(classification_report(
        y_true,
        y_pred,
        target_names=['body_text', 'footnote'],
        digits=3
    ))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    print("\nConfusion Matrix:")
    print(f"              Predicted")
    print(f"              Body  Footnote")
    print(f"Actual Body   {cm[0,0]:5d}  {cm[0,1]:5d}")
    print(f"       Footnote {cm[1,0]:5d}  {cm[1,1]:5d}")

    # Detailed metrics
    f1 = f1_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    accuracy = accuracy_score(y_true, y_pred)

    print(f"\nKey Metrics:")
    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1 Score:  {f1:.3f}")

    # Save confusion matrix plot
    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=['Body Text', 'Footnote']
    )
    disp.plot(ax=ax, cmap='Blues', values_format='d')
    plt.title(f'ModernBERT Fine-tuned Classifier\nF1={f1:.3f}, Accuracy={accuracy:.3f}')

    results_dir = output_dir / "evaluation"
    results_dir.mkdir(parents=True, exist_ok=True)
    cm_path = results_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✓ Confusion matrix saved: {cm_path}")

    # Save metrics
    metrics = {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'test_size': len(y_true),
        'confusion_matrix': {
            'true_negatives': int(cm[0,0]),
            'false_positives': int(cm[0,1]),
            'false_negatives': int(cm[1,0]),
            'true_positives': int(cm[1,1]),
        }
    }

    metrics_path = results_dir / "test_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved: {metrics_path}")

    return metrics


def main():
    """Main training pipeline."""
    print("="*80)
    print("FINE-TUNING MODERNBERT FOR FOOTNOTE CLASSIFICATION")
    print("="*80)

    base_dir = Path(__file__).parent
    corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"
    output_dir = base_dir / "models" / "modernbert_footnote_classifier"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for GPU
    if torch.cuda.is_available():
        print(f"\n✓ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    elif torch.backends.mps.is_available():
        print("\n✓ Apple Silicon MPS available - training will use Metal acceleration")
    else:
        print("\n⚠️  No GPU/MPS detected - training will use CPU")
        print("  Consider using Google Colab or a GPU-enabled machine")
        print("  Auto-continuing with available hardware...")

    try:
        # Load data
        X_train, X_val, X_test, y_train, y_val, y_test = load_and_prepare_data(corpus_path)

        # Tokenize
        model_name = "answerdotai/ModernBERT-base"  # Base model: best loss (0.296) with 1024 tokens
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        train_dataset, val_dataset, test_dataset = tokenize_data(
            tokenizer, X_train, X_val, X_test, y_train, y_val, y_test
        )

        # Train
        trainer, tokenizer, model = train_model(train_dataset, val_dataset, output_dir)

        # Evaluate
        metrics = evaluate_model(trainer, test_dataset, output_dir)

        # Final summary
        print("\n" + "="*80)
        print("✓ TRAINING PIPELINE COMPLETE")
        print("="*80)
        print(f"\nFinal F1 Score: {metrics['f1_score']:.3f}")
        print(f"Model saved to: {output_dir / 'final_model'}")

        if metrics['f1_score'] >= 0.90:
            print("\n🎉 Excellent! F1 >= 0.90 target achieved!")
        elif metrics['f1_score'] >= 0.85:
            print("\n✅ Good! F1 >= 0.85 achieved")
        else:
            print("\n⚠️  F1 below target. Consider:")
            print("   - Training for more epochs")
            print("   - Collecting more training data")
            print("   - Adjusting hyperparameters")

        print(f"\nNext steps:")
        print(f"  1. Test model on PDFs: python test_modernbert_classifier.py")
        print(f"  2. Integrate into pipeline: Update extract_body_only.py")
        print(f"  3. Compare with heuristic baseline")

    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
