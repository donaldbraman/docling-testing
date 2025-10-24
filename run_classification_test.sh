#!/bin/bash
# Run OCR + Classification on vast.ai
set -e

# Configuration
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_PORT="33334"
SSH_HOST="ssh6.vast.ai"

# Paths
TEST_PDF="data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf"
MODEL_PATH="models/doclingbert-v2-rebalanced/final_model"

echo "════════════════════════════════════════════════════════"
echo "  Body Extractor - OCR + Classification Test"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Testing: $(basename "$TEST_PDF")"
echo "Model: DoclingBERT v2-rebalanced"
echo ""

# Check if model exists locally
if [ ! -d "$MODEL_PATH" ]; then
  echo "❌ Model not found: $MODEL_PATH"
  echo "Please ensure the trained model is in models/doclingbert-v2-rebalanced/final_model/"
  exit 1
fi

echo "📤 Step 1/4: Uploading classification script..."
scp -q -i "$SSH_KEY" -P "$SSH_PORT" \
  scripts/vastai/run_ocr_with_classification.py \
  root@"$SSH_HOST":/workspace/
echo "✅ Done"

echo ""
echo "📤 Step 2/4: Uploading ModernBERT model (~500MB, may take 30-60 sec)..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" "mkdir -p /workspace/models/doclingbert-v2-rebalanced"
rsync -avz --progress -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  "$MODEL_PATH"/ \
  root@"$SSH_HOST":/workspace/models/doclingbert-v2-rebalanced/final_model/
echo "✅ Done"

echo ""
echo "📤 Step 3/4: Uploading PDF..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" "mkdir -p /workspace/test_input"
scp -q -i "$SSH_KEY" -P "$SSH_PORT" "$TEST_PDF" root@"$SSH_HOST":/workspace/test_input/
echo "✅ Done"

echo ""
echo "🔄 Step 4/4: Running OCR + Classification..."
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" << 'ENDSSH'
cd /workspace
mkdir -p test_results

python3 run_ocr_with_classification.py \
  --input ./test_input/antitrusts_interdependence_paradox.pdf \
  --output-dir ./test_results \
  --model-path ./models/doclingbert-v2-rebalanced/final_model

echo ""
echo "Generated files:"
ls -lh test_results/
ENDSSH

echo ""
echo "📥 Downloading results..."
mkdir -p results_classified

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  root@"$SSH_HOST":/workspace/test_results/ \
  results_classified/

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ CLASSIFICATION TEST COMPLETE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Results in: ./results_classified/"
echo ""
ls -lh results_classified/
echo ""
echo "Generated outputs:"
echo "  1. Plain text:           *.txt"
echo "  2. Text overlay PDF:     *_text_overlay.pdf"
echo "  3. Class overlay PDF:    *_class_overlay.pdf"
echo "  4. CSV with classes:     *.csv"
echo "  5. Full JSON metadata:   *.json"
echo ""
echo "View results:"
echo "  cat results_classified/*.txt"
echo "  open results_classified/*_text_overlay.pdf"
echo "  open results_classified/*_class_overlay.pdf"
echo "  cat results_classified/*.csv | column -t -s,"
echo ""
