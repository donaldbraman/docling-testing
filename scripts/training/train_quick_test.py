#!/usr/bin/env python3
"""
DoclingBert v2: QUICK TEST - Train for 100 steps only for early validation.
"""

# Temporarily modify training args for quick testing
import train_multiclass_classifier as train_module

# Monkey-patch the training args
original_main = train_module.main


def quick_test_main():
    """Modified main with fast training settings."""
    from pathlib import Path

    import train_multiclass_classifier

    print("=" * 80)
    print("QUICK TEST: Training for 100 steps only (~9 minutes)")
    print("=" * 80)

    base_dir = Path(__file__).parent
    corpus_path = base_dir / "data" / "clean_7class_corpus.csv"
    output_dir = base_dir / "models" / "doclingbert-v2-quick-test"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    X_train, X_val, X_test, y_train, y_val, y_test, class_weights = (
        train_multiclass_classifier.load_and_prepare_data(corpus_path)
    )

    # Tokenize
    model_name = "answerdotai/ModernBERT-base"
    tokenizer = train_multiclass_classifier.AutoTokenizer.from_pretrained(model_name)
    train_dataset, val_dataset, test_dataset = train_multiclass_classifier.tokenize_data(
        tokenizer, X_train, X_val, X_test, y_train, y_val, y_test
    )

    # QUICK TEST TRAINING ARGS
    from transformers import TrainingArguments

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        # QUICK TEST: Only 100 steps
        max_steps=100,
        per_device_train_batch_size=1,  # Minimum for M1 Pro memory
        per_device_eval_batch_size=1,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
        # Evaluation every 25 steps
        eval_strategy="steps",
        eval_steps=25,
        save_strategy="steps",
        save_steps=25,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        # Logging
        logging_dir=str(output_dir / "logs"),
        logging_steps=10,
        report_to="none",
        # Performance - M1 Pro memory optimized
        fp16=False,  # MPS doesn't support fp16 well
        gradient_accumulation_steps=16,  # Effective batch = 16
        gradient_checkpointing=True,  # Save memory
        dataloader_num_workers=0,  # Avoid multiprocessing overhead
        # Reproducibility
        seed=42,
    )

    # Initialize model
    model = train_multiclass_classifier.AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=7,
        problem_type="single_label_classification",
    )

    # Train
    trainer = train_multiclass_classifier.WeightedLossTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=train_multiclass_classifier.compute_metrics,
    )

    print("\n" + "=" * 80)
    print("TRAINING FOR 100 STEPS")
    print("=" * 80)
    print("ETA: ~9 minutes\n")

    train_result = trainer.train()

    print("\n" + "=" * 80)
    print("QUICK TEST TRAINING COMPLETE")
    print("=" * 80)
    print(f"Training time: {train_result.metrics['train_runtime']:.2f}s")

    # Save model
    model_path = output_dir / "final_model"
    trainer.save_model(str(model_path))
    tokenizer.save_pretrained(str(model_path))

    # Save metadata
    import json

    metadata = {
        "model_name": "DoclingBert",
        "version": "v2-quick-test",
        "base_model": "answerdotai/ModernBERT-base",
        "num_classes": 7,
        "training_steps": 100,
        "label_map": train_multiclass_classifier.LABEL_MAP,
    }
    with open(model_path / "label_map.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Quick test model saved: {model_path}")
    print("\nNext step: Test with python test_multiclass_classifier.py")


if __name__ == "__main__":
    quick_test_main()
