#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Setting up Skyline LED Weather Display..."
echo "Working directory: $SCRIPT_DIR"
echo ""

# Update system packages
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Remove old venv if it exists with permission issues
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo ""
        echo "✓ Created .env file from template"
        echo "Please edit .env and add your OpenWeather API key:"
        echo "  nano .env"
    else
        echo "Warning: .env.example not found"
    fi
else
    echo "✓ .env file already exists"
fi

echo ""
echo "✓ Installation complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  cd $SCRIPT_DIR"
echo "  source venv/bin/activate"
echo ""
echo "Then run the program with:"
echo "  python main.py"
