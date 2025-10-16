#!/usr/bin/env python3
"""Quick evaluation of DoclingBERT v3 final model."""

import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoTokenizer

from scripts.training.spatial_modernbert import SpatialModernBERT

# Load test data
df = pd.read_csv("data/spatial_7class_corpus.csv")

# Use the SAME label mapping as training
label_map = {
    "body_text": 0,
    "heading": 1,
    "footnote": 2,
    "caption": 3,
    "page_header": 4,
    "page_footer": 5,
    "cover": 6,
}

# Get actual classes present in data (in training order)
actual_classes = [
    k for k, v in sorted(label_map.items(), key=lambda x: x[1]) if k in df["label"].unique()
]
print(f"Classes in dataset (training order): {actual_classes}")

# Split data (same as training)
test_df = df.sample(frac=0.15, random_state=42)

id2label = {idx: label for label, idx in label_map.items()}

# Load model
model_path = "models/doclingbert-v3-spatial/final_model"
tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")
model = SpatialModernBERT.from_pretrained(model_path, num_labels=len(actual_classes))
model.eval()

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model.to(device)

# Evaluate
y_true = []
y_pred = []

print(f"\nEvaluating {len(test_df)} test samples...")

with torch.no_grad():
    for _, row in test_df.iterrows():
        # Tokenize
        inputs = tokenizer(
            row["text"], padding="max_length", truncation=True, max_length=512, return_tensors="pt"
        )

        # Prepare bbox features
        bbox = torch.tensor(
            [[row["x0"], row["y0"], row["x1"], row["y1"], row["width"], row["height"]]],
            dtype=torch.long,
        ).to(device)

        # Move inputs to device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Predict
        outputs = model(**inputs, bbox_features=bbox)
        pred = torch.argmax(outputs["logits"], dim=1).item()

        y_true.append(label_map[row["label"]])
        y_pred.append(pred)

# Print results
print("\n" + "=" * 80)
print("DOCLINGBERT V3 - FINAL EVALUATION")
print("=" * 80)
print(f"\nTest samples: {len(test_df)}")
print(f"Classes: {len(actual_classes)}")
print("\nClassification Report:")
print(classification_report(y_true, y_pred, target_names=actual_classes, digits=3))

print("\nConfusion Matrix:")
print(confusion_matrix(y_true, y_pred))
print("\nRow=True, Col=Predicted")
print(f"Class order: {actual_classes}")
