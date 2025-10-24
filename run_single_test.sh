#!/bin/bash
# Run OCR on 1 test PDF
set -e

# Configuration
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_PORT="33334"
SSH_HOST="ssh6.vast.ai"

# Single test PDF
TEST_PDF="data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf"

echo "════════════════════════════════════════════════════════"
echo "  Body Extractor - Single PDF Test"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Testing: $(basename "$TEST_PDF")"
echo ""

# Upload script
echo "📤 Step 1/3: Uploading OCR script..."
scp -q -i "$SSH_KEY" -P "$SSH_PORT" \
  scripts/vastai/run_ocr_extraction.py \
  root@"$SSH_HOST":/workspace/
echo "✅ Done"

# Upload PDF
echo ""
echo "📤 Step 2/3: Uploading PDF..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" "mkdir -p /workspace/test_input"
scp -q -i "$SSH_KEY" -P "$SSH_PORT" "$TEST_PDF" root@"$SSH_HOST":/workspace/test_input/
echo "✅ Done"

# Run OCR
echo ""
echo "🔄 Step 3/3: Running OCR extraction..."
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" << 'ENDSSH'
cd /workspace
mkdir -p test_output

python3 run_ocr_extraction.py \
  --input ./test_input/antitrusts_interdependence_paradox.pdf \
  --output-dir ./test_output

echo ""
echo "Generated files:"
ls -lh test_output/
ENDSSH

# Download results
echo ""
echo "📥 Downloading results..."
mkdir -p results_single_test

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  root@"$SSH_HOST":/workspace/test_output/ \
  results_single_test/

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ SINGLE PDF TEST COMPLETE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Results in: ./results_single_test/"
echo ""
ls -lh results_single_test/
echo ""
echo "View results:"
echo "  cat results_single_test/antitrusts_interdependence_paradox.txt"
echo "  open results_single_test/antitrusts_interdependence_paradox_annotated.pdf"
echo ""
