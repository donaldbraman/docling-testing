#!/usr/bin/env python3
"""
Benchmark ML classifier vs heuristic-based footnote detection.

Compares accuracy, speed, and resource usage to demonstrate
value proposition for Docling upstream integration.
"""

import time
from pathlib import Path
from typing import Callable

import pandas as pd
from extract_body_only import is_likely_citation
from extract_with_ml_classifier import FootnoteClassifier


def benchmark_heuristic(texts: list[str]) -> dict:
    """Benchmark heuristic-based classifier."""
    start = time.time()
    predictions = []

    for text in texts:
        is_footnote = is_likely_citation(text)
        predictions.append(is_footnote)

    elapsed = time.time() - start

    return {
        'method': 'heuristic',
        'predictions': predictions,
        'total_time_ms': elapsed * 1000,
        'avg_time_ms': (elapsed / len(texts)) * 1000,
        'throughput_per_sec': len(texts) / elapsed
    }


def benchmark_ml(texts: list[str], model_path: Path) -> dict:
    """Benchmark ML-based classifier."""
    # Load model (include in timing for first-run scenario)
    load_start = time.time()
    classifier = FootnoteClassifier(model_path)
    load_time = time.time() - load_start

    # Classify texts
    classify_start = time.time()
    predictions = []
    confidences = []

    for text in texts:
        is_footnote, confidence = classifier.is_footnote(text)
        predictions.append(is_footnote)
        confidences.append(confidence)

    classify_elapsed = time.time() - classify_start

    return {
        'method': 'ml',
        'predictions': predictions,
        'confidences': confidences,
        'load_time_ms': load_time * 1000,
        'classify_time_ms': classify_elapsed * 1000,
        'avg_time_ms': (classify_elapsed / len(texts)) * 1000,
        'throughput_per_sec': len(texts) / classify_elapsed
    }


def calculate_accuracy(predictions: list[bool], ground_truth: list[str]) -> dict:
    """Calculate accuracy metrics."""
    # Convert ground truth labels to boolean
    gt_bool = [label == 'footnote' for label in ground_truth]

    # Calculate metrics
    correct = sum(p == gt for p, gt in zip(predictions, gt_bool))
    accuracy = correct / len(predictions)

    # Confusion matrix
    tp = sum(p and gt for p, gt in zip(predictions, gt_bool))
    fp = sum(p and not gt for p, gt in zip(predictions, gt_bool))
    tn = sum(not p and not gt for p, gt in zip(predictions, gt_bool))
    fn = sum(not p and gt for p, gt in zip(predictions, gt_bool))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'true_positives': tp,
        'false_positives': fp,
        'true_negatives': tn,
        'false_negatives': fn
    }


def main():
    """Run comprehensive benchmark."""
    base_dir = Path(__file__).parent
    corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"
    model_path = base_dir / "models" / "modernbert_footnote_classifier" / "final_model"

    if not corpus_path.exists():
        print(f"Error: Corpus not found at {corpus_path}")
        return

    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Train model first: python train_modernbert_classifier.py")
        return

    print("="*80)
    print("BENCHMARKING: ML CLASSIFIER VS HEURISTICS")
    print("="*80)

    # Load test set
    df = pd.read_csv(corpus_path)
    print(f"\nLoaded corpus: {len(df)} paragraphs")

    # Use balanced test set (equal footnotes and body text)
    footnotes = df[df['html_label'] == 'footnote'].sample(n=100, random_state=42)
    body = df[df['html_label'] == 'body_text'].sample(n=100, random_state=42)
    test_df = pd.concat([footnotes, body]).sample(frac=1, random_state=42)

    texts = test_df['text'].tolist()
    ground_truth = test_df['html_label'].tolist()

    print(f"Test set: {len(texts)} paragraphs (100 footnotes, 100 body)")

    # Benchmark heuristic method
    print("\n" + "="*80)
    print("HEURISTIC METHOD")
    print("="*80)

    heuristic_results = benchmark_heuristic(texts)
    heuristic_accuracy = calculate_accuracy(heuristic_results['predictions'], ground_truth)

    print(f"\nPerformance:")
    print(f"  Total time:     {heuristic_results['total_time_ms']:.2f}ms")
    print(f"  Per paragraph:  {heuristic_results['avg_time_ms']:.3f}ms")
    print(f"  Throughput:     {heuristic_results['throughput_per_sec']:.1f} paragraphs/sec")

    print(f"\nAccuracy:")
    print(f"  Accuracy:       {heuristic_accuracy['accuracy']:.2%}")
    print(f"  Precision:      {heuristic_accuracy['precision']:.2%}")
    print(f"  Recall:         {heuristic_accuracy['recall']:.2%}")
    print(f"  F1 Score:       {heuristic_accuracy['f1_score']:.2%}")

    print(f"\nConfusion Matrix:")
    print(f"  TP: {heuristic_accuracy['true_positives']:3d}  FP: {heuristic_accuracy['false_positives']:3d}")
    print(f"  FN: {heuristic_accuracy['false_negatives']:3d}  TN: {heuristic_accuracy['true_negatives']:3d}")

    # Benchmark ML method
    print("\n" + "="*80)
    print("ML METHOD (ModernBERT)")
    print("="*80)

    ml_results = benchmark_ml(texts, model_path)
    ml_accuracy = calculate_accuracy(ml_results['predictions'], ground_truth)

    print(f"\nPerformance:")
    print(f"  Model load:     {ml_results['load_time_ms']:.2f}ms (one-time)")
    print(f"  Classify time:  {ml_results['classify_time_ms']:.2f}ms")
    print(f"  Per paragraph:  {ml_results['avg_time_ms']:.3f}ms")
    print(f"  Throughput:     {ml_results['throughput_per_sec']:.1f} paragraphs/sec")

    print(f"\nAccuracy:")
    print(f"  Accuracy:       {ml_accuracy['accuracy']:.2%}")
    print(f"  Precision:      {ml_accuracy['precision']:.2%}")
    print(f"  Recall:         {ml_accuracy['recall']:.2%}")
    print(f"  F1 Score:       {ml_accuracy['f1_score']:.2%}")

    print(f"\nConfusion Matrix:")
    print(f"  TP: {ml_accuracy['true_positives']:3d}  FP: {ml_accuracy['false_positives']:3d}")
    print(f"  FN: {ml_accuracy['false_negatives']:3d}  TN: {ml_accuracy['true_negatives']:3d}")

    avg_confidence = sum(ml_results['confidences']) / len(ml_results['confidences'])
    print(f"\nAverage confidence: {avg_confidence:.3f}")

    # Comparison
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)

    accuracy_improvement = ml_accuracy['accuracy'] - heuristic_accuracy['accuracy']
    f1_improvement = ml_accuracy['f1_score'] - heuristic_accuracy['f1_score']
    speed_ratio = heuristic_results['avg_time_ms'] / ml_results['avg_time_ms']

    print(f"\nAccuracy:")
    print(f"  Heuristic:      {heuristic_accuracy['accuracy']:.2%}")
    print(f"  ML:             {ml_accuracy['accuracy']:.2%}")
    print(f"  Improvement:    {accuracy_improvement:+.2%}")

    print(f"\nF1 Score:")
    print(f"  Heuristic:      {heuristic_accuracy['f1_score']:.2%}")
    print(f"  ML:             {ml_accuracy['f1_score']:.2%}")
    print(f"  Improvement:    {f1_improvement:+.2%}")

    print(f"\nSpeed:")
    print(f"  Heuristic:      {heuristic_results['avg_time_ms']:.3f}ms/para")
    print(f"  ML:             {ml_results['avg_time_ms']:.3f}ms/para")
    if speed_ratio > 1:
        print(f"  ML is {speed_ratio:.1f}x SLOWER")
    else:
        print(f"  ML is {1/speed_ratio:.1f}x FASTER")

    # Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)

    if accuracy_improvement > 0.05 and ml_results['avg_time_ms'] < 50:
        print("\n✓ ML classifier shows significant accuracy improvement")
        print(f"  with acceptable speed ({ml_results['avg_time_ms']:.1f}ms per paragraph).")
        print("\n  RECOMMENDATION: Integrate as optional classifier in Docling")
        print("  - Opt-in via DocumentConverter parameter")
        print("  - Model auto-downloaded from Hugging Face Hub")
        print("  - Falls back to heuristics if model unavailable")
    elif accuracy_improvement > 0.05:
        print("\n~ ML classifier shows accuracy improvement but is slower")
        print(f"  ({ml_results['avg_time_ms']:.1f}ms vs {heuristic_results['avg_time_ms']:.3f}ms per paragraph)")
        print("\n  RECOMMENDATION: Offer as separate package")
        print("  - For users who prioritize accuracy over speed")
    else:
        print("\n✗ ML classifier does not show sufficient improvement")
        print(f"  Accuracy gain: {accuracy_improvement:+.2%}")
        print("\n  RECOMMENDATION: Further tuning needed")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
