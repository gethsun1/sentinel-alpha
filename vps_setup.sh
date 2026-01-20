#!/bin/bash
# Sentinel Alpha - VPS Deployment Script
# Run this ON THE VPS after connecting

echo "🚀 SENTINEL ALPHA - VPS DEPLOYMENT"
echo "===================================="
echo ""

# Update system
echo "📦 Step 1: Updating system packages..."
apt update && apt upgrade -y

# Install Python and dependencies
echo "🐍 Step 2: Installing Python and tools..."
apt install -y python3 python3-pip python3-venv git curl wget nano htop tmux

# Create project directory
echo "📁 Step 3: Creating project directory..."
cd /root
mkdir -p sentinel-alpha
cd sentinel-alpha

# Install Python packages
echo "📚 Step 4: Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install requirements (will be populated after files are copied)
echo "⏳ Step 5: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Dependencies installed!"
else
    echo "⚠️  requirements.txt not found. Will install after files are copied."
    pip install pandas numpy pyyaml matplotlib requests python-dotenv
fi

# Get VPS IP
VPS_IP=$(curl -s ifconfig.me)
echo ""
echo "===================================="
echo "✅ VPS SETUP COMPLETE!"
echo "===================================="
echo ""
echo "Your STATIC IP: $VPS_IP"
echo ""
echo "Next steps:"
echo "1. Copy your project files from local machine"
echo "2. Copy your .env file with API credentials"
echo "3. Test the API connection"
echo ""
echo "From your LOCAL machine, run:"
echo "  cd /home/quantum/Documents/GKM/sentinel-alpha"
echo "  ./upload_to_vps.sh"
echo ""

