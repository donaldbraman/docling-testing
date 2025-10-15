#!/usr/bin/env python3
"""
DoclingBert v2: Rebalanced training for improved body_text recall (Issue #8)

Goal: Achieve 2:1 FP:FN ratio for body_text (prefer 2 footnotes in body_text over 1 body_text missing)
Strategy: Increase body_text class weight 3x to boost recall from 64.6% to 80-90%

Issue: https://github.com/donaldbraman/docling-testing/issues/8
"""

import sys
from pathlib import Path
import numpy as np
import train_multiclass_classifier


def main():
    """Train with 3x body_text weight to improve recall."""
    from transformers import TrainingArguments

    print("="*80)
    print("ISSUE #8: REBALANCED TRAINING FOR IMPROVED BODY_TEXT RECALL")
    print("="*80)
    print("\nTarget: 2:1 FP:FN ratio (prefer false positives over false negatives)")
    print("Strategy: 3x body_text class weight")
    print()

    base_dir = Path(__file__).parent
    corpus_path = base_dir / "data" / "clean_7class_corpus.csv"
    output_dir = base_dir / "models" / "doclingbert-v2-rebalanced"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data with default balanced weights
    X_train, X_val, X_test, y_train, y_val, y_test, class_weights = train_multiclass_classifier.load_and_prepare_data(corpus_path)

    print("\n" + "="*80)
    print("APPLYING 3X BODY_TEXT WEIGHT MULTIPLIER")
    print("="*80)

    # Get body_text label ID
    body_text_id = train_multiclass_classifier.LABEL_MAP['body_text']

    # Store original weight
    original_weight = class_weights[body_text_id]

    # Apply 3x multiplier to body_text
    class_weights[body_text_id] = original_weight * 3.0

    print(f"\nAdjusted class weights (3x multiplier on body_text):")
    for label_name, label_id in train_multiclass_classifier.LABEL_MAP.items():
        if label_id in [0, 2, 3]:  # body_text, footnote, caption (present in data)
            mult = "(3x)" if label_name == "body_text" else ""
            print(f"  {label_name:15s} {class_weights[label_id]:.3f} {mult}")
        else:
            print(f"  {label_name:15s} {class_weights[label_id]:.3f} (no data)")

    print(f"\nExpected impact:")
    print(f"  - body_text recall: 64.6% → 80-90% (reduce false negatives)")
    print(f"  - body_text precision: 88.4% → 70-80% (accept more false positives)")
    print(f"  - FP:FN ratio: 1:4.2 → 2:1 (target)")

    # Tokenize
    model_name = "answerdotai/ModernBERT-base"
    tokenizer = train_multiclass_classifier.AutoTokenizer.from_pretrained(model_name)
    train_dataset, val_dataset, test_dataset = train_multiclass_classifier.tokenize_data(
        tokenizer, X_train, X_val, X_test, y_train, y_val, y_test
    )

    # Training args - 100 steps for quick validation
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),

        # Quick test: 100 steps
        max_steps=100,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,

        # Evaluation every 25 steps
        eval_strategy="steps",
        eval_steps=25,
        save_strategy="steps",
        save_steps=25,
        save_total_limit=3,  # Keep last 3 checkpoints
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,

        # Logging
        logging_dir=str(output_dir / "logs"),
        logging_steps=10,
        report_to="none",

        # Performance - M1 Pro optimized
        fp16=False,
        gradient_accumulation_steps=16,
        gradient_checkpointing=True,
        dataloader_num_workers=0,

        # Reproducibility
        seed=42,
    )

    # Initialize model
    model = train_multiclass_classifier.AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=7,
        problem_type="single_label_classification",
    )

    # Train with rebalanced weights
    trainer = train_multiclass_classifier.WeightedLossTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=train_multiclass_classifier.compute_metrics,
    )

    print("\n" + "="*80)
    print("TRAINING FOR 100 STEPS (REBALANCED WEIGHTS)")
    print("="*80)
    print(f"Output: {output_dir}")
    print(f"ETA: ~18 minutes\n")

    # Train
    trainer.train()

    # Save final model
    final_dir = output_dir / "final_model"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    # Save metadata
    import json
    metadata = {
        "model_name": "DoclingBert v2 (Rebalanced)",
        "version": "v2-rebalanced",
        "issue": "https://github.com/donaldbraman/docling-testing/issues/8",
        "base_model": model_name,
        "training_steps": 100,
        "class_weight_multiplier": {
            "body_text": 3.0,
            "footnote": 1.0,
            "caption": 1.0,
        },
        "label_map": train_multiclass_classifier.LABEL_MAP,
        "target_metrics": {
            "body_text_recall": "80-90%",
            "fp_fn_ratio": "2:1",
        },
    }

    with open(final_dir / "label_map.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "="*80)
    print("✓ TRAINING COMPLETE")
    print("="*80)
    print(f"\nModel saved to: {final_dir}")
    print(f"\nNext steps:")
    print(f"  1. Evaluate: python evaluate_checkpoint.py --checkpoint {output_dir}/checkpoints/checkpoint-100")
    print(f"  2. Compare to baseline (step 50): body_text recall should be 80-90%")
    print(f"  3. Check FP:FN ratio in confusion matrix")
    print(f"  4. If insufficient, try 5x multiplier or threshold adjustment")


if __name__ == "__main__":
    main()
