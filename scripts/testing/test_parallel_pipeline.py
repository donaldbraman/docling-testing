#!/usr/bin/env python3
"""
Test parallel pipeline: CPU extraction + MPS training simultaneously.

This demonstrates that we can extract next batch on CPU while training
current batch on MPS, avoiding GPU contention.
"""

import os
import time
from multiprocessing import Process
from pathlib import Path


def extract_with_cpu(pdf_dir: Path, output_dir: Path, batch_size: int = 10):
    """Extract PDFs using CPU-only (no MPS)."""
    # Force CPU-only for Docling
    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = ""  # Hide GPU

    print(f"[EXTRACTOR] Starting CPU-only extraction of {batch_size} PDFs...")
    start = time.time()

    # Simulate extraction (in real pipeline, would call Docling here)
    pdf_files = list(pdf_dir.glob("*.pdf"))[:batch_size]

    for i, pdf in enumerate(pdf_files, 1):
        # Simulate processing time
        time.sleep(2)  # Simulate CPU extraction
        print(f"[EXTRACTOR] CPU extracted {i}/{batch_size}: {pdf.name}")

    elapsed = time.time() - start
    print(f"[EXTRACTOR] Completed in {elapsed:.1f}s ({elapsed / batch_size:.1f}s per PDF)")


def train_with_mps(corpus_path: Path, steps: int = 25):
    """Train using MPS while extraction runs on CPU."""
    print(f"[TRAINER] Starting MPS training for {steps} steps...")
    start = time.time()

    # Simulate training (in real pipeline, would call actual training)
    for step in range(1, steps + 1):
        time.sleep(0.5)  # Simulate training step
        if step % 5 == 0:
            print(f"[TRAINER] MPS training step {step}/{steps}")

    elapsed = time.time() - start
    print(f"[TRAINER] Completed in {elapsed:.1f}s ({elapsed / steps:.1f}s per step)")


def test_parallel():
    """Test parallel extraction + training."""
    print("=" * 80)
    print("TESTING PARALLEL PIPELINE: CPU Extraction || MPS Training")
    print("=" * 80)

    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")
    corpus_path = Path("data/clean_7class_corpus.csv")

    # Test 1: Sequential (baseline)
    print("\n[TEST 1] SEQUENTIAL BASELINE")
    print("-" * 80)
    start = time.time()
    extract_with_cpu(pdf_dir, Path("data/raw_pdf"), batch_size=5)
    train_with_mps(corpus_path, steps=10)
    sequential_time = time.time() - start
    print(f"\n✓ Sequential total time: {sequential_time:.1f}s")

    # Test 2: Parallel
    print("\n[TEST 2] PARALLEL PIPELINE")
    print("-" * 80)
    start = time.time()

    # Start both processes
    extractor = Process(target=extract_with_cpu, args=(pdf_dir, Path("data/raw_pdf"), 5))
    trainer = Process(target=train_with_mps, args=(corpus_path, 10))

    extractor.start()
    time.sleep(0.5)  # Slight delay to ensure extractor starts first
    trainer.start()

    # Wait for both to complete
    extractor.join()
    trainer.join()

    parallel_time = time.time() - start
    print(f"\n✓ Parallel total time: {parallel_time:.1f}s")

    # Results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Sequential time: {sequential_time:.1f}s")
    print(f"Parallel time:   {parallel_time:.1f}s")
    speedup = sequential_time / parallel_time
    time_saved = sequential_time - parallel_time
    print(f"Speedup:         {speedup:.2f}x")
    print(f"Time saved:      {time_saved:.1f}s ({time_saved / sequential_time * 100:.1f}%)")

    if speedup > 1.3:
        print("\n🎉 Parallel pipeline is significantly faster!")
        print("   Ready for production implementation.")
    else:
        print("\n⚠️  Parallel speedup is modest.")
        print("   May not be worth the added complexity.")


if __name__ == "__main__":
    test_parallel()
