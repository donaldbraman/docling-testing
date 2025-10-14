#!/usr/bin/env python3
"""
Quick experiments to find optimal ModernBERT configuration for MPS memory.

Tests different combinations of:
- Model size (base vs large)
- Max sequence length (512, 1024, 2048)
- Batch size (1, 2, 4)
"""

import json
from pathlib import Path
import time
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
import pandas as pd
from sklearn.model_selection import train_test_split

# Experiment configurations
CONFIGS = [
    # ModernBERT-base experiments (149M params)
    {"name": "base_512_bs4", "model": "answerdotai/ModernBERT-base", "max_length": 512, "batch_size": 4},
    {"name": "base_512_bs2", "model": "answerdotai/ModernBERT-base", "max_length": 512, "batch_size": 2},
    {"name": "base_1024_bs2", "model": "answerdotai/ModernBERT-base", "max_length": 1024, "batch_size": 2},
    {"name": "base_1024_bs1", "model": "answerdotai/ModernBERT-base", "max_length": 1024, "batch_size": 1},

    # ModernBERT-large experiments (395M params) - conservative settings
    {"name": "large_512_bs1", "model": "answerdotai/ModernBERT-large", "max_length": 512, "batch_size": 1},
    {"name": "large_512_bs2", "model": "answerdotai/ModernBERT-large", "max_length": 512, "batch_size": 2},
]


def load_data_quick():
    """Load small subset for quick experiments."""
    corpus_path = Path("data/labeled_pdf_corpus.csv")
    df = pd.read_csv(corpus_path)

    # Use small subset for speed (200 examples)
    df_small = df.sample(n=min(200, len(df)), random_state=42)

    texts = df_small['text'].tolist()
    labels = [1 if label == 'footnote' else 0 for label in df_small['html_label']]

    X_train, X_val, y_train, y_val = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    return X_train, X_val, y_train, y_val


def test_config(config, X_train, X_val, y_train, y_val):
    """Test a single configuration."""
    print(f"\n{'='*80}")
    print(f"TESTING: {config['name']}")
    print(f"  Model: {config['model']}")
    print(f"  Max Length: {config['max_length']}")
    print(f"  Batch Size: {config['batch_size']}")
    print(f"{'='*80}")

    try:
        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(config['model'])
        model = AutoModelForSequenceClassification.from_pretrained(
            config['model'],
            num_labels=2,
            problem_type="single_label_classification",
        )

        # Tokenize
        def tokenize_function(examples):
            return tokenizer(
                examples['text'],
                padding='max_length',
                truncation=True,
                max_length=config['max_length']
            )

        train_dataset = Dataset.from_dict({'text': X_train, 'labels': y_train})
        val_dataset = Dataset.from_dict({'text': X_val, 'labels': y_val})

        train_dataset = train_dataset.map(tokenize_function, batched=True)
        val_dataset = val_dataset.map(tokenize_function, batched=True)

        # Training args - just 10 steps for quick test
        training_args = TrainingArguments(
            output_dir=f"models/experiments/{config['name']}",
            num_train_epochs=1,
            per_device_train_batch_size=config['batch_size'],
            per_device_eval_batch_size=config['batch_size'],
            max_steps=10,  # Just 10 steps for quick test
            logging_steps=5,
            eval_strategy="steps",
            eval_steps=5,
            save_strategy="no",
            report_to="none",
            disable_tqdm=False,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
        )

        # Try training
        print("\nStarting training...")
        start_time = time.time()
        train_result = trainer.train()
        elapsed = time.time() - start_time

        print(f"\n✓ SUCCESS!")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Loss: {train_result.training_loss:.4f}")

        # Evaluate
        print("\nEvaluating...")
        eval_result = trainer.evaluate()
        print(f"  Eval Loss: {eval_result['eval_loss']:.4f}")

        # Clean up
        del model
        del trainer
        torch.mps.empty_cache() if torch.backends.mps.is_available() else None

        return {
            'config': config['name'],
            'success': True,
            'time': elapsed,
            'train_loss': train_result.training_loss,
            'eval_loss': eval_result['eval_loss'],
            'error': None
        }

    except RuntimeError as e:
        if 'out of memory' in str(e).lower():
            print(f"\n❌ OOM Error: {str(e)[:100]}...")
            return {
                'config': config['name'],
                'success': False,
                'time': None,
                'train_loss': None,
                'eval_loss': None,
                'error': 'OOM'
            }
        else:
            raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {
            'config': config['name'],
            'success': False,
            'time': None,
            'train_loss': None,
            'eval_loss': None,
            'error': str(e)[:100]
        }
    finally:
        # Clean up
        torch.mps.empty_cache() if torch.backends.mps.is_available() else None


def main():
    print("="*80)
    print("MODERNBERT CONFIGURATION EXPERIMENTS")
    print("="*80)
    print("\nTesting different model sizes, sequence lengths, and batch sizes")
    print("to find optimal configuration for Apple Silicon MPS\n")

    # Load data once
    print("Loading data subset (200 examples)...")
    X_train, X_val, y_train, y_val = load_data_quick()
    print(f"  Train: {len(X_train)}")
    print(f"  Val: {len(X_val)}")

    # Run experiments
    results = []
    for config in CONFIGS:
        result = test_config(config, X_train, X_val, y_train, y_val)
        results.append(result)

        # Small delay between experiments
        time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("EXPERIMENT RESULTS SUMMARY")
    print("="*80)

    df_results = pd.DataFrame(results)
    print("\n" + df_results.to_string(index=False))

    # Save results
    results_file = Path("models/experiment_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {results_file}")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    successful = [r for r in results if r['success']]
    if successful:
        # Best by speed
        fastest = min(successful, key=lambda x: x['time'])
        print(f"\n⚡ Fastest: {fastest['config']} ({fastest['time']:.1f}s)")

        # Best by loss
        best_loss = min(successful, key=lambda x: x['eval_loss'])
        print(f"🎯 Best Loss: {best_loss['config']} (eval_loss={best_loss['eval_loss']:.4f})")

        # Recommended
        # Prefer large model if it fits, otherwise base with longest sequence
        large_configs = [r for r in successful if 'large' in r['config']]
        if large_configs:
            recommended = max(large_configs, key=lambda x: int(x['config'].split('_')[1]))
            print(f"\n💡 Recommended: {recommended['config']}")
            print(f"   Best balance of model size and sequence length")
        else:
            base_configs = [r for r in successful if 'base' in r['config']]
            if base_configs:
                recommended = max(base_configs, key=lambda x: int(x['config'].split('_')[1]))
                print(f"\n💡 Recommended: {recommended['config']}")
                print(f"   Best available configuration (large OOM)")
    else:
        print("\n⚠️  All configurations failed - may need CPU training")


if __name__ == "__main__":
    main()
