#!/bin/bash
# WEEX API Testing - Setup Script

echo "🚀 Setting up WEEX API Testing Environment..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✓ Setup complete!"
echo ""
echo "To run the API test:"
echo "  1. source venv/bin/activate"
echo "  2. python weex_api_test.py"
echo ""
echo "Or use the quick command:"
echo "  ./run_weex_test.sh"
echo ""


