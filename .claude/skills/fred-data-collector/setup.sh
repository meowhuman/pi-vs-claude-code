#!/bin/bash
# FRED Data Collector - Setup Script
# This script sets up the FRED data collection environment

set -e  # Exit on error

echo "🚀 Setting up FRED Data Collector..."
echo "======================================"

# Check Python version
echo "→ Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Found Python $python_version"

# Install required packages
echo ""
echo "📦 Installing Python packages..."
pip3 install fredapi pandas requests

# Verify installation
echo ""
echo "✅ Verifying installation..."
python3 -c "
import fredapi
import pandas
import requests
print('  ✓ fredapi installed')
print('  ✓ pandas installed')
print('  ✓ requests installed')
"

# Check environment variables
echo ""
echo "🔑 Checking FRED API Key..."
if [ -n "$FRED_API_KEY" ]; then
    echo "  ✓ FRED_API_KEY is set"
    echo "    Key: ${FRED_API_KEY:0:8}..."
else
    echo "  ⚠️  FRED_API_KEY not set in current shell"
    echo "  Loading from .env file..."
    if [ -f ".env" ]; then
        source .env
        if [ -n "$FRED_API_KEY" ]; then
            echo "  ✓ FRED_API_KEY loaded from .env"
            echo "    Key: ${FRED_API_KEY:0:8}..."
        else
            echo "  ❌ FRED_API_KEY not found in .env"
            echo "  Please add: FRED_API_KEY=your_key_here"
            exit 1
        fi
    else
        echo "  ❌ .env file not found"
        exit 1
    fi
fi

# Test API connection
echo ""
echo "🧪 Testing API connection..."
python3 .claude/skills/fred-data-collector/scripts/test_fred.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Run interactive collection:"
    echo "   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py"
    echo ""
    echo "2. Or run automated collection:"
    echo "   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --auto"
    echo ""
    echo "3. Add to crontab for daily updates:"
    echo "   crontab -e"
    echo "   # Add: 0 7 * * * cd $(pwd) && python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --auto"
else
    echo ""
    echo "❌ Setup failed. Please check the error messages above."
    exit 1
fi
