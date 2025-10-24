#!/bin/bash
# Run OCR on 3 test PDFs only
set -e

# Configuration
INSTANCE_ID="27233335"
SSH_PORT="33334"
SSH_HOST="ssh6.vast.ai"
SSH_KEY="$HOME/.ssh/id_ed25519"

# Test PDFs
TEST_PDFS=(
  "data/v3_data/raw_pdf/afrofuturism_in_protest__dissent_and_revolution.pdf"
  "data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf"
  "data/v3_data/raw_pdf/california_law_review_affirmative-asylum.pdf"
)

echo "════════════════════════════════════════════════════════"
echo "  Body Extractor - Test OCR (3 PDFs)"
echo "════════════════════════════════════════════════════════"
echo ""

# Upload script
echo "📤 Uploading OCR script..."
scp -i "$SSH_KEY" -P "$SSH_PORT" \
  scripts/vastai/run_ocr_extraction.py \
  root@"$SSH_HOST":/workspace/
echo "✅ Script uploaded"
echo ""

# Upload test PDFs
echo "📤 Uploading 3 test PDFs..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" "mkdir -p /workspace/test_data"

for pdf in "${TEST_PDFS[@]}"; do
  echo "  - $(basename "$pdf")"
  scp -i "$SSH_KEY" -P "$SSH_PORT" "$pdf" root@"$SSH_HOST":/workspace/test_data/
done
echo "✅ PDFs uploaded"
echo ""

# Run OCR
echo "🔄 Running OCR extraction..."
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" << 'ENDSSH'
cd /workspace
mkdir -p test_results

echo "🔄 Initializing EasyOCR (models already pre-downloaded)..."
python3 run_ocr_extraction.py \
  --batch \
  --input-dir ./test_data \
  --output-dir ./test_results

echo ""
echo "✅ OCR complete!"
echo ""
echo "Results:"
ls -lh test_results/ | tail -20
ENDSSH

echo ""
echo "✅ Extraction completed"
echo ""

# Download results
echo "📥 Downloading results..."
mkdir -p results_test

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  root@"$SSH_HOST":/workspace/test_results/ \
  results_test/

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ TEST OCR COMPLETE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Results: ./results_test/"
echo ""
echo "Files per PDF:"
echo "  • .txt - Plain text"
echo "  • .json - Bounding boxes + confidence"
echo "  • .csv - Coordinates"
echo "  • _annotated.pdf - Annotated PDF"
echo ""
ls -lh results_test/
echo ""
