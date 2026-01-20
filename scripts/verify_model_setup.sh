#!/bin/bash
# Model Setup Verification Script
# Verifies LLaMA-2-7B model is properly installed and accessible

echo "======================================================================"
echo "LLaMA-2-7B MODEL SETUP VERIFICATION"
echo "======================================================================"

# Read model path from config
MODEL_DIR="/opt/llm_models/llama-2-7b"
MODEL_FILE="llama-2-7b-chat.Q4_K_M.gguf"
FULL_PATH="$MODEL_DIR/$MODEL_FILE"

echo ""
echo "Checking model directory: $MODEL_DIR"

# Check directory exists
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ ERROR: Model directory not found!"
    echo "   Expected: $MODEL_DIR"
    echo ""
    echo "To fix:"
    echo "  1. Download LLaMA-2-7B GGUF model"
    echo "  2. Create directory: sudo mkdir -p $MODEL_DIR"
    echo "  3. Move model file to: $FULL_PATH"
    echo "  4. Fix permissions: sudo chmod 644 $FULL_PATH"
    exit 1
fi

echo "✅ Model directory exists"

# Check directory permissions
if [ ! -r "$MODEL_DIR" ]; then
    echo "❌ ERROR: Model directory not readable!"
    echo "   Fix with: sudo chmod 755 $MODEL_DIR"
    exit 1
fi

echo "✅ Model directory is readable"

# Check model file exists
echo ""
echo "Checking model file: $MODEL_FILE"

if [ ! -f "$FULL_PATH" ]; then
    echo "❌ ERROR: Model file not found!"
    echo "   Expected: $FULL_PATH"
    echo ""
    echo "Available files in $MODEL_DIR:"
    ls -lh "$MODEL_DIR"
    exit 1
fi

echo "✅ Model file exists"

# Check file permissions
if [ ! -r "$FULL_PATH" ]; then
    echo "❌ ERROR: Model file not readable!"
    echo "   Fix with: sudo chmod 644 $FULL_PATH"
    exit 1
fi

echo "✅ Model file is readable"

# Get file size
FILE_SIZE=$(stat -f%z "$FULL_PATH" 2>/dev/null || stat -c%s "$FULL_PATH" 2>/dev/null)
FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))

echo ""
echo "Model file size: ${FILE_SIZE_MB} MB"

if [ $FILE_SIZE_MB -lt 1000 ]; then
    echo "⚠️  WARNING: File seems small for 4-bit model (< 1GB)"
    echo "   Expected size: ~3.5GB for LLaMA-2-7B Q4_K_M"
    echo "   File may be incomplete or corrupt"
fi

# Calculate checksum
echo ""
echo "Calculating checksum (this may take a moment)..."
CHECKSUM=$(sha256sum "$FULL_PATH" | awk '{print $1}')
echo "SHA256: $CHECKSUM"

# Check owner and permissions
echo ""
echo "File permissions:"
ls -lh "$FULL_PATH"

# Summary
echo ""
echo "======================================================================"
echo "✅ MODEL SETUP VERIFICATION COMPLETE"
echo "======================================================================"
echo "Model Path: $FULL_PATH"
echo "Size: ${FILE_SIZE_MB} MB"
echo "Checksum: $CHECKSUM"
echo ""
echo "Next steps:"
echo "  1. Run: python scripts/test_llm_inference.py"
echo "  2. Verify inference works correctly"
echo ""

exit 0
