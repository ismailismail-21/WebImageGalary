#!/bin/bash

# Web Image Gallery - Setup Script

echo "🖼️  Web Image Gallery Setup"
echo "============================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the gallery:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run: python run.py"
echo ""
echo "Then open your browser to: http://localhost:5000"
