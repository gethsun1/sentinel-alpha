#!/bin/bash
# Quick run script for WEEX API testing

echo "🚀 Running WEEX API Qualification Test..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Running setup..."
    ./setup_venv.sh
fi

# Activate and run
source venv/bin/activate
python weex_api_test.py


