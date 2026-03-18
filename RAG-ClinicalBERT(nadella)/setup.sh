#!/usr/bin/env bash
# Clinical Insight Bot — Reproducibility Setup Script
# This script sets up the environment for running the Medical RAG system.

set -e

echo "============================================="
echo "  Clinical Insight Bot — Environment Setup"
echo "============================================="

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python 3 is required but not found."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Found Python: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel --quiet

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "NOTE: No .env file found. Creating from template..."
    cp env.example .env
    echo "Please edit .env with your Neon PostgreSQL connection string."
    echo "  See: https://neon.tech for database setup"
    echo ""
fi

# Check for data directory
if [ ! -d "data" ] || [ -z "$(ls -A data/ 2>/dev/null)" ]; then
    echo ""
    echo "NOTE: No medical case data found in data/ directory."
    echo "  The system requires MIMIC-III case files."
    echo "  See PHYSIONET_GUIDE.md for data access instructions."
    echo ""
fi

# Setup frontend (optional)
if [ -d "frontend" ]; then
    if command -v npm &> /dev/null; then
        echo "Setting up frontend..."
        cd frontend
        npm install --quiet 2>/dev/null || echo "  Frontend npm install had warnings (non-critical)"
        cd ..
    else
        echo "NOTE: Node.js not found. Frontend setup skipped."
        echo "  The Flask backend UI is still available."
    fi
fi

echo ""
echo "============================================="
echo "  Setup complete!"
echo "============================================="
echo ""
echo "To start the system:"
echo "  source venv/bin/activate"
echo "  python3 load_and_run.py"
echo ""
echo "Then open http://localhost:5557 in your browser."
echo ""
