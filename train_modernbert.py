#!/usr/bin/env python3
"""
Train ModernBERT for Footnote Classification

Uses labeled PDF corpus (from HTML label transfer) to train classifier.

Issue: https://github.com/donaldbraman/docling-testing/issues/4
"""

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


def train_with_setfit():
    """Train using SetFit (efficient few-shot learning framework)."""
    try:
        from setfit import SetFitModel, SetFitTrainer
        from sentence_transformers.losses import CosineSimilarityLoss
        from datasets import Dataset
    except ImportError:
        print("❌ SetFit not installed. Install with: pip install setfit")
        return None

    # Load corpus
    base_dir = Path(__file__).parent
    corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"

    if not corpus_path.exists():
        print(f"❌ Corpus not found: {corpus_path}")
        print("   Run match_html_pdf.py first to generate training data")
        return None

    df = pd.read_csv(corpus_path)
    print(f"\nLoaded corpus: {len(df):,} paragraphs")
    print(f"  Body text: {(df['html_label']=='body_text').sum():,}")
    print(f"  Footnotes: {(df['html_label']=='footnote').sum():,}")

    # Prepare data
    X = df['text'].tolist()
    y = [1 if label == 'footnote' else 0 for label in df['html_label']]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print(f"\nTrain set: {len(X_train):,} ({sum(y_train):,} footnotes)")
    print(f"Test set: {len(X_test):,} ({sum(y_test):,} footnotes)")

    # Prepare datasets
    train_dataset = Dataset.from_dict({"text": X_train, "label": y_train})
    eval_dataset = Dataset.from_dict({"text": X_test, "label": y_test})

    # Load ModernBERT
    print("\nInitializing ModernBERT model...")
    try:
        model = SetFitModel.from_pretrained(
            "answerdotai/ModernBERT-large",
            use_differentiable_head=True,
            head_params={"out_features": 2}
        )
        print("  ✓ Loaded ModernBERT-large")
    except Exception as e:
        print(f"  ⚠️  Could not load ModernBERT-large: {e}")
        print("  Falling back to sentence-transformers/paraphrase-mpnet-base-v2")
        model = SetFitModel.from_pretrained(
            "sentence-transformers/paraphrase-mpnet-base-v2",
            use_differentiable_head=True,
            head_params={"out_features": 2}
        )

    # Configure trainer
    print("\nTraining model...")
    trainer = SetFitTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        loss_class=CosineSimilarityLoss,
        batch_size=16,
        num_iterations=20,
        num_epochs=1,
        column_mapping={"text": "text", "label": "label"}
    )

    # Train
    trainer.train()

    # Evaluate
    print("\n" + "="*80)
    print("EVALUATION ON TEST SET")
    print("="*80)

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # Metrics
    print("\nClassification Report:")
    print(classification_report(
        y_test,
        y_pred,
        target_names=['body_text', 'footnote'],
        digits=3
    ))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:")
    print(f"              Predicted")
    print(f"              Body  Footnote")
    print(f"Actual Body   {cm[0,0]:5d}  {cm[0,1]:5d}")
    print(f"       Footnote {cm[1,0]:5d}  {cm[1,1]:5d}")

    # F1 score
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    accuracy = accuracy_score(y_test, y_pred)

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
    plt.title(f'Confusion Matrix (F1={f1:.3f})')

    results_dir = Path(__file__).parent / "results" / "confusion_matrices"
    results_dir.mkdir(parents=True, exist_ok=True)
    cm_path = results_dir / "modernbert_confusion_matrix.png"
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Confusion matrix saved: {cm_path}")

    # Save model
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "modernbert_footnote_classifier"

    model.save_pretrained(str(model_path))
    print(f"✓ Model saved: {model_path}")

    # Save metrics
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'train_size': len(X_train),
        'test_size': len(X_test),
    }

    metrics_path = results_dir.parent / "modernbert_metrics.json"
    import json
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved: {metrics_path}")

    return model, metrics


def main():
    """Train ModernBERT classifier."""
    print("="*80)
    print("TRAINING MODERNBERT FOOTNOTE CLASSIFIER")
    print("="*80)

    model, metrics = train_with_setfit()

    if model and metrics:
        print("\n" + "="*80)
        print("✓ TRAINING COMPLETE")
        print("="*80)
        print(f"\nFinal F1 Score: {metrics['f1_score']:.3f}")

        if metrics['f1_score'] >= 0.90:
            print("🎉 Excellent! F1 >= 0.90 target achieved!")
        elif metrics['f1_score'] >= 0.85:
            print("✅ Good! F1 >= 0.85 achieved")
        else:
            print("⚠️  F1 below target. Consider:")
            print("   - Collecting more training data")
            print("   - Improving HTML/PDF matching quality")
            print("   - Adding feature engineering")


if __name__ == "__main__":
    main()
