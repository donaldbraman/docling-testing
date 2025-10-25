#!/bin/bash
# Run OCR + Classification on vast.ai with auto-cleanup
set -e

# Parse arguments
INSTANCE_ID="${1:-}"
TEST_PDF="${2:-data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf}"
MODEL_PATH="${3:-models/doclingbert-v2-rebalanced/final_model}"
OUTPUT_DIR="${4:-results_classified}"
SSH_KEY="${5:-$HOME/.ssh/id_ed25519}"

# Robust file upload function with fallback methods
# Based on VASTAI_BEST_PRACTICES.md
upload_file() {
    local LOCAL_FILE="$1"
    local REMOTE_PATH="$2"
    local SSH_OPTS="-i $SSH_KEY -p $SSH_PORT -o ConnectTimeout=10 -o StrictHostKeyChecking=no"

    # Method 1: rsync (most robust, resumable)
    echo "   Trying rsync..."
    if rsync -avz --partial --timeout=300 -e "ssh $SSH_OPTS" \
         "$LOCAL_FILE" root@"$SSH_HOST":"$REMOTE_PATH" 2>/dev/null; then
        return 0
    fi

    # Method 2: Legacy SCP with -O flag (works with vast.ai ASCII art)
    echo "   rsync failed, trying legacy SCP..."
    if scp -O -q $SSH_OPTS "$LOCAL_FILE" root@"$SSH_HOST":"$REMOTE_PATH" 2>/dev/null; then
        return 0
    fi

    # Method 3: SSH pipe (always works, bypasses SCP protocol)
    echo "   SCP failed, trying SSH pipe..."
    local REMOTE_FILE=$(basename "$REMOTE_PATH")
    local REMOTE_DIR=$(dirname "$REMOTE_PATH")
    if cat "$LOCAL_FILE" | ssh $SSH_OPTS root@"$SSH_HOST" \
         "mkdir -p $REMOTE_DIR && cat > $REMOTE_PATH" 2>/dev/null; then
        return 0
    fi

    echo "   ❌ All upload methods failed"
    return 1
}

if [ -z "$INSTANCE_ID" ]; then
    echo "❌ Error: Instance ID required"
    echo ""
    echo "Usage: $0 <INSTANCE_ID> [TEST_PDF] [MODEL_PATH] [OUTPUT_DIR] [SSH_KEY]"
    echo ""
    echo "Arguments:"
    echo "  INSTANCE_ID    (required) vast.ai instance ID"
    echo "  TEST_PDF       (optional) Path to PDF to process"
    echo "                 Default: data/v3_data/raw_pdf/antitrusts_interdependence_paradox.pdf"
    echo "  MODEL_PATH     (optional) Path to trained model"
    echo "                 Default: models/doclingbert-v2-rebalanced/final_model"
    echo "  OUTPUT_DIR     (optional) Directory for results"
    echo "                 Default: results_classified"
    echo "  SSH_KEY        (optional) Path to SSH private key"
    echo "                 Default: ~/.ssh/id_ed25519"
    echo ""
    echo "Example:"
    echo "  $0 27241475"
    echo "  $0 27241475 data/test.pdf models/mymodel results/test"
    exit 1
fi

echo "════════════════════════════════════════════════════════"
echo "  Body Extractor - OCR + Classification Test"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Test PDF:    $TEST_PDF"
echo "Model:       $MODEL_PATH"
echo "Output Dir:  $OUTPUT_DIR"
echo "SSH Key:     $SSH_KEY"
echo ""

# Validate inputs
if [ ! -f "$TEST_PDF" ]; then
  echo "❌ Test PDF not found: $TEST_PDF"
  exit 1
fi

if [ ! -d "$MODEL_PATH" ]; then
  echo "❌ Model not found: $MODEL_PATH"
  exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found: $SSH_KEY"
  exit 1
fi

# Extract PDF basename for remote operations
PDF_BASENAME=$(basename "$TEST_PDF")

# Check if instance is already running
STATUS=$(vastai show instances | grep $INSTANCE_ID | awk '{print $3}')
if [ "$STATUS" != "running" ]; then
    echo "🔄 Starting vast.ai instance (current status: $STATUS)..."
    vastai start instance $INSTANCE_ID
    echo "Waiting for instance to be ready (Docker image loading may take 2-3 min)..."
    sleep 120  # Increased wait time for Docker image pull
else
    echo "✅ Instance already running, skipping restart..."
fi

# Get SSH connection info
SSH_INFO=$(vastai show instances | grep $INSTANCE_ID)
SSH_HOST=$(echo "$SSH_INFO" | awk '{print $10}')
SSH_PORT=$(echo "$SSH_INFO" | awk '{print $11}')

echo "✅ Instance ready: $SSH_HOST:$SSH_PORT"
echo ""

# Attach SSH key
echo "🔑 Attaching SSH key..."
vastai attach ssh $INSTANCE_ID "$(cat $SSH_KEY.pub)"
sleep 3
echo "✅ Done"
echo ""

echo "📤 Step 1/5: Uploading classification script..."
if ! upload_file scripts/vastai/run_ocr_with_classification.py /workspace/run_ocr_with_classification.py; then
    echo "❌ Failed to upload classification script"
    vastai destroy instance $INSTANCE_ID
    exit 1
fi
echo "✅ Done"

echo ""
echo "📤 Step 2/5: Uploading ModernBERT model (~500MB, may take 30-60 sec)..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" "mkdir -p /workspace/models/doclingbert-v2-rebalanced"
rsync -avz --progress -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  "$MODEL_PATH"/ \
  root@"$SSH_HOST":/workspace/models/doclingbert-v2-rebalanced/final_model/
echo "✅ Done"

echo ""
echo "📤 Step 3/5: Uploading PDF..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" "mkdir -p /workspace/test_input"
if ! upload_file "$TEST_PDF" "/workspace/test_input/$PDF_BASENAME"; then
    echo "❌ Failed to upload PDF"
    vastai destroy instance $INSTANCE_ID
    exit 1
fi
echo "✅ Done"

echo ""
echo "🔄 Step 4/5: Running OCR + Classification..."
echo ""

ssh -i "$SSH_KEY" -p "$SSH_PORT" root@"$SSH_HOST" bash << ENDSSH
cd /workspace
mkdir -p test_results

python3 run_ocr_with_classification.py \
  --input ./test_input/$PDF_BASENAME \
  --output-dir ./test_results \
  --model-path ./models/doclingbert-v2-rebalanced/final_model

echo ""
echo "Generated files:"
ls -lh test_results/
ENDSSH

echo ""
echo "📥 Step 5/5: Downloading results..."
mkdir -p "$OUTPUT_DIR"

rsync -avz -e "ssh -i $SSH_KEY -p $SSH_PORT" \
  root@"$SSH_HOST":/workspace/test_results/ \
  "$OUTPUT_DIR/"

echo "✅ Results downloaded"
echo ""

# Destroy instance to save money
echo "🗑️  Destroying vast.ai instance to save costs..."
vastai destroy instance $INSTANCE_ID
echo "✅ Instance destroyed"
echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ CLASSIFICATION TEST COMPLETE"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Results in: $OUTPUT_DIR/"
echo ""
ls -lh "$OUTPUT_DIR/"
echo ""
echo "Generated outputs:"
echo "  1. Plain text:           *.txt"
echo "  2. Text overlay PDF:     *_text_overlay.pdf"
echo "  3. Class overlay PDF:    *_class_overlay.pdf"
echo "  4. CSV with classes:     *.csv"
echo "  5. Full JSON metadata:   *.json"
echo ""
echo "View results:"
echo "  cat $OUTPUT_DIR/*.txt"
echo "  open $OUTPUT_DIR/*_text_overlay.pdf"
echo "  open $OUTPUT_DIR/*_class_overlay.pdf"
echo "  cat $OUTPUT_DIR/*.csv | column -t -s,"
echo ""
