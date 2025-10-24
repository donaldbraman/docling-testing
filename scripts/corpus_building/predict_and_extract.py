#!/usr/bin/env python3
"""
Extract text blocks and auto-label using trained model.

Workflow:
1. Extract text blocks with 4 features
2. Auto-label body_text/footnote using HTML matching
3. Auto-label NEEDS_REVIEW blocks using trained model
4. Output CSV for manual review/correction

Production Optimization:
    For production use, this script can be optimized to use the cite-assist
    ModernBERT service for embeddings instead of loading the full model locally.
    This would reduce memory usage from ~600MB to ~1MB (classification head only).

Usage:
    uv run python scripts/corpus_building/predict_and_extract.py --pdf texas_law_review_state-regulation-online-behavior
"""

import argparse
import json

# Import extraction functions from existing script
import sys
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoTokenizer

sys.path.append(str(Path(__file__).parent))
from extract_text_blocks_simple import (
    auto_label_blocks,
    extract_text_blocks,
    load_ground_truth,
)


def load_model(model_dir: Path):
    """Load trained model and tokenizer."""
    # Import from training directory
    sys.path.append(str(Path(__file__).parent.parent / "training"))
    from train_simple_classifier import SimpleTextBlockClassifier

    print(f"\nLoading model from: {model_dir}")

    # Load label map
    label_map_path = model_dir / "label_map.json"
    with open(label_map_path) as f:
        label_info = json.load(f)

    id_to_label = {int(k): v for k, v in label_info["id_to_label"].items()}

    # Load tokenizer from base model (ModernBERT)
    # Note: Tokenizer save failed, so we load from base model
    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")

    # Load model
    model = SimpleTextBlockClassifier.from_pretrained(str(model_dir))
    model.eval()

    # Move to GPU if available (CUDA or MPS)
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    model = model.to(device)

    print(f"✓ Model loaded (device: {device})")

    return model, tokenizer, id_to_label, device


def predict_labels(
    blocks_df: pd.DataFrame,
    model,
    tokenizer,
    id_to_label: dict,
    device,
) -> pd.DataFrame:
    """Predict labels for NEEDS_REVIEW blocks using trained model."""

    # Filter to NEEDS_REVIEW blocks
    needs_review = blocks_df[blocks_df["suggested_label"] == "NEEDS_REVIEW"].copy()

    if len(needs_review) == 0:
        print("No NEEDS_REVIEW blocks to predict")
        return blocks_df

    print(f"\nPredicting labels for {len(needs_review)} NEEDS_REVIEW blocks...")

    # Prepare features
    texts = needs_review["text"].tolist()
    position_features = needs_review[
        ["page_number", "y_position_normalized", "normalized_font_size"]
    ].values

    # Tokenize
    encodings = tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    # Move to device
    input_ids = encodings["input_ids"].to(device)
    attention_mask = encodings["attention_mask"].to(device)
    position_tensor = torch.FloatTensor(position_features).to(device)

    # Predict in batches
    batch_size = 16
    all_predictions = []
    all_confidences = []

    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_input_ids = input_ids[i : i + batch_size]
            batch_attention_mask = attention_mask[i : i + batch_size]
            batch_position = position_tensor[i : i + batch_size]

            outputs = model(
                input_ids=batch_input_ids,
                attention_mask=batch_attention_mask,
                position_features=batch_position,
            )

            logits = outputs["logits"]
            probs = torch.softmax(logits, dim=-1)
            confidences, predictions = torch.max(probs, dim=-1)

            all_predictions.extend(predictions.cpu().numpy())
            all_confidences.extend(confidences.cpu().numpy())

    # Map predictions to labels
    predicted_labels = [id_to_label[pred] for pred in all_predictions]

    # Update dataframe
    needs_review.loc[:, "suggested_label"] = predicted_labels
    needs_review.loc[:, "prediction_confidence"] = all_confidences

    # Merge back into original dataframe
    blocks_df.loc[needs_review.index, "suggested_label"] = predicted_labels
    blocks_df.loc[needs_review.index, "prediction_confidence"] = all_confidences

    # Show prediction summary
    print("\nModel predictions:")
    for label in ["body_text", "footnote", "front_matter", "header"]:
        count = (needs_review["suggested_label"] == label).sum()
        if count > 0:
            avg_conf = needs_review[needs_review["suggested_label"] == label][
                "prediction_confidence"
            ].mean()
            print(f"  {label:15s} {count:5d} (avg confidence: {avg_conf:.3f})")

    return blocks_df


def main():
    parser = argparse.ArgumentParser(
        description="Extract text blocks and auto-label using trained model"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="PDF name (without .pdf extension)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/simple_text_classifier/final_model",
        help="Path to trained model directory",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="Fuzzy matching threshold for HTML (0-100, default: 80)",
    )

    args = parser.parse_args()

    # Setup paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    ground_truth_path = Path(
        f"results/ocr_pipeline_evaluation/ground_truth/{args.pdf}_ground_truth.json"
    )
    model_dir = Path(args.model)
    output_dir = Path("results/text_block_extraction")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    if not ground_truth_path.exists():
        print(f"Error: Ground truth not found: {ground_truth_path}")
        return 1

    if not model_dir.exists():
        print(f"Error: Model not found: {model_dir}")
        print("Train a model first using train_simple_classifier.py")
        return 1

    print("=" * 80)
    print("TEXT BLOCK EXTRACTION WITH MODEL PREDICTIONS")
    print("=" * 80)

    # Step 1: Extract text blocks
    print("\n[1/4] Extracting text blocks...")
    blocks = extract_text_blocks(pdf_path)

    # Step 2: Load ground truth
    print("\n[2/4] Loading ground truth...")
    body_texts, footnotes = load_ground_truth(ground_truth_path)

    # Step 3: Auto-label using HTML matching
    print("\n[3/4] Auto-labeling with HTML matching...")
    blocks = auto_label_blocks(blocks, body_texts, footnotes, args.threshold)

    # Convert to DataFrame
    blocks_df = pd.DataFrame(blocks)

    # Step 4: Auto-label NEEDS_REVIEW using model
    print("\n[4/4] Auto-labeling NEEDS_REVIEW blocks with trained model...")

    # Load model
    model, tokenizer, id_to_label, device = load_model(model_dir)

    # Predict
    blocks_df = predict_labels(blocks_df, model, tokenizer, id_to_label, device)

    # Save results (v2 = with model predictions)
    output_path = output_dir / f"{args.pdf}_blocks_v2_predicted.csv"
    blocks_df.to_csv(output_path, index=False)

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Saved to: {output_path}")

    # Show final distribution
    print("\nFinal label distribution:")
    for label in ["body_text", "footnote", "front_matter", "header"]:
        count = (blocks_df["suggested_label"] == label).sum()
        pct = 100 * count / len(blocks_df) if len(blocks_df) > 0 else 0
        print(f"  {label:15s} {count:5d} ({pct:5.1f}%)")

    # Show low-confidence predictions for review
    if "prediction_confidence" in blocks_df.columns:
        low_conf = blocks_df[
            (blocks_df["prediction_confidence"].notna())
            & (blocks_df["prediction_confidence"] < 0.7)
        ]
        if len(low_conf) > 0:
            print(f"\n⚠️  {len(low_conf)} predictions with confidence < 0.7 (review recommended)")
            print("\nLow-confidence predictions:")
            for _, row in low_conf.head(5).iterrows():
                print(
                    f"  Page {row['page_number']}, {row['suggested_label']:15s} "
                    f"(conf: {row['prediction_confidence']:.3f})"
                )
                print(f"    Text: {row['text'][:80]}...")

    print("\nNext steps:")
    print("1. Review predictions (especially low-confidence ones)")
    print("2. Correct any errors in the CSV")
    print(f"3. Save corrected version as: {args.pdf}_blocks_v3_labeled.csv")
    print("4. Use v3_labeled.csv for retraining on next document")

    return 0


if __name__ == "__main__":
    exit(main())
