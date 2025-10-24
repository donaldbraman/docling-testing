#!/usr/bin/env bash
# Parallel A/B/C test of EasyOCR worker configurations on vast.ai
# Tests 3 configurations simultaneously to find optimal GPU utilization

set -e

echo "==========================================="
echo "EASYOCR OPTIMIZATION TEST - VAST.AI"
echo "==========================================="
echo ""

# Test configurations (simpler arrays for compatibility)
CONFIGS=("0" "4" "8")
CONFIG_NAMES=("A" "B" "C")
CONFIG_LABELS=("No workers (Mac M1 style)" "Moderate workers" "High workers")

# Find 3 available RTX 4090 instances
echo "Step 1: Finding 3 available RTX 4090 instances..."
INSTANCES=$(uv run vastai search offers 'gpu_name=RTX_4090' -o 'dph+' --raw | \
    python3 -c "import json, sys; data = json.load(sys.stdin); print(' '.join(str(i['id']) for i in data[:3] if i.get('reliability2', 0) > 0.98))")

IFS=' ' read -ra INSTANCE_ARRAY <<< "$INSTANCES"

if [ ${#INSTANCE_ARRAY[@]} -lt 3 ]; then
    echo "Error: Could not find 3 suitable instances"
    exit 1
fi

echo "Found instances: ${INSTANCE_ARRAY[@]}"
echo ""

# Deploy function
deploy_instance() {
    local CONFIG=$1
    local WORKERS=$2
    local INSTANCE_ID=$3

    echo "[Config $CONFIG - Workers=$WORKERS] Creating instance $INSTANCE_ID..."

    # Create instance
    CREATE_OUTPUT=$(uv run vastai create instance $INSTANCE_ID \
        --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime \
        --disk 20 \
        --ssh)

    CONTRACT_ID=$(echo "$CREATE_OUTPUT" | sed -n 's/.*new_contract[^0-9]*\([0-9]*\).*/\1/p')

    echo "[Config $CONFIG] Waiting for startup..."
    sleep 30

    # Get SSH details
    SSH_INFO=$(uv run vastai ssh-url $CONTRACT_ID)
    PORT=$(echo $SSH_INFO | sed -n 's/.*:\([0-9]*\).*/\1/p')

    echo "[Config $CONFIG] Installing dependencies..."
    ssh -o StrictHostKeyChecking=no -p $PORT root@ssh9.vast.ai \
        'apt-get update -qq && apt-get install -y poppler-utils && \
         curl -LsSf https://astral.sh/uv/install.sh | sh && \
         /root/.cargo/bin/uv pip install --system easyocr pdf2image pillow pandas pymupdf rapidfuzz' > /dev/null 2>&1

    echo "[Config $CONFIG] Uploading files..."
    rsync -azq -e "ssh -p $PORT" \
        data/v3_data/raw_pdf/afrofuturism_in_protest__dissent_and_revolution.pdf \
        root@ssh9.vast.ai:/workspace/

    rsync -azq -e "ssh -p $PORT" \
        scripts/corpus_building/extract_with_easyocr.py \
        root@ssh9.vast.ai:/workspace/

    echo "[Config $CONFIG] Starting EasyOCR (workers=$WORKERS)..."
    ssh -p $PORT root@ssh9.vast.ai \
        "cd /workspace && EASYOCR_WORKERS=$WORKERS nohup python3 extract_with_easyocr.py \
         --pdf afrofuturism_in_protest__dissent_and_revolution --dpi 300 \
         > processing.log 2>&1 & echo \$!" > /tmp/pid_$CONFIG.txt

    echo "$CONTRACT_ID $PORT" > /tmp/instance_$CONFIG.txt
    echo "[Config $CONFIG] Processing started!"
}

# Deploy all 3 in parallel
echo "Step 2: Deploying 3 instances in parallel..."
deploy_instance "A" "${CONFIGS[0]}" "${INSTANCE_ARRAY[0]}" &
deploy_instance "B" "${CONFIGS[1]}" "${INSTANCE_ARRAY[1]}" &
deploy_instance "C" "${CONFIGS[2]}" "${INSTANCE_ARRAY[2]}" &

wait

echo ""
echo "Step 3: All instances deployed! Monitoring progress..."
echo ""

# Monitor function
monitor_instance() {
    local CONFIG=$1
    local WORKER_IDX=$2
    read CONTRACT_ID PORT < /tmp/instance_$CONFIG.txt

    START_TIME=$(date +%s)

    while true; do
        # Check if process is still running
        if ssh -p $PORT root@ssh9.vast.ai 'ps aux | grep extract_with_easyocr | grep -v grep' > /dev/null 2>&1; then
            # Get GPU utilization
            GPU_UTIL=$(ssh -p $PORT root@ssh9.vast.ai 'nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits' 2>/dev/null || echo "?")

            ELAPSED=$(($(date +%s) - START_TIME))
            echo "[Config $CONFIG - Workers=${CONFIGS[$WORKER_IDX]}] Running for ${ELAPSED}s - GPU: ${GPU_UTIL}%"
            sleep 10
        else
            END_TIME=$(date +%s)
            TOTAL_TIME=$((END_TIME - START_TIME))
            echo "[Config $CONFIG] COMPLETED in ${TOTAL_TIME}s"
            echo "$CONFIG $TOTAL_TIME ${CONFIGS[$WORKER_IDX]}" >> /tmp/results.txt
            break
        fi
    done
}

# Monitor all in parallel
monitor_instance "A" 0 &
monitor_instance "B" 1 &
monitor_instance "C" 2 &

wait

echo ""
echo "==========================================="
echo "RESULTS"
echo "==========================================="

sort -k2 -n /tmp/results.txt | while read CONFIG TIME WORKERS; do
    echo "Config $CONFIG (workers=$WORKERS): ${TIME}s"
done

# Clean up
echo ""
echo "Destroying instances..."
for CONFIG in A B C; do
    read CONTRACT_ID PORT < /tmp/instance_$CONFIG.txt
    uv run vastai destroy instance $CONTRACT_ID
done

rm -f /tmp/instance_*.txt /tmp/pid_*.txt /tmp/results.txt

echo "Test complete!"
