#!/bin/bash
# Automatically run classification test when instance is ready
set -e

INSTANCE_ID="${1:-}"
MAX_WAIT=600  # 10 minutes max wait

if [ -z "$INSTANCE_ID" ]; then
    echo "❌ Error: Instance ID required"
    echo ""
    echo "Usage: $0 <INSTANCE_ID> [TEST_PDF] [MODEL_PATH] [OUTPUT_DIR] [SSH_KEY]"
    echo ""
    echo "All arguments after INSTANCE_ID are passed to run_classification_test.sh"
    echo ""
    echo "Example:"
    echo "  $0 27241475"
    echo "  $0 27241475 data/test.pdf models/mymodel results/test"
    exit 1
fi

echo "════════════════════════════════════════════════════════"
echo "  Waiting for instance $INSTANCE_ID to be ready..."
echo "════════════════════════════════════════════════════════"
echo ""

# Wait for instance to be running
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(vastai show instances | grep $INSTANCE_ID | awk '{print $3}')

    if [ "$STATUS" = "running" ]; then
        echo "✅ Instance is RUNNING!"
        echo "⏳ Waiting additional 90 seconds for SSH to be ready..."
        sleep 90
        echo ""
        break
    elif [ "$STATUS" = "loading" ] || [ "$STATUS" = "created" ]; then
        echo "[$(date +%H:%M:%S)] Status: $STATUS (waited ${ELAPSED}s)"
        sleep 15
        ELAPSED=$((ELAPSED + 15))
    else
        echo "❌ Unexpected status: $STATUS"
        exit 1
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "❌ Timeout waiting for instance to start"
    exit 1
fi

# Run the classification test with all arguments
echo "🚀 Running classification test..."
echo ""
./run_classification_test.sh "$@"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ TEST COMPLETE!"
echo "════════════════════════════════════════════════════════"
