#!/bin/bash
# PlaylistGrab - Auto Setup and Run Script for Linux/Mac
# This script creates a virtual environment, installs dependencies, and runs the app

echo "============================================"
echo "PlaylistGrab - Setup and Run"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.7 or higher using your package manager."
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "Fedora: sudo dnf install python3 python3-pip"
    echo "Arch: sudo pacman -S python python-pip"
    echo "Mac: brew install python3"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[1/4] Checking Python installation..."
python3 --version
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[2/4] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment!"
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "Virtual environment created successfully."
    echo ""
else
    echo "[2/4] Virtual environment already exists."
    echo ""
fi

# Activate virtual environment
echo "[3/4] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment!"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi
echo ""

# Install/update dependencies
echo "[4/4] Installing/updating dependencies..."
echo "This may take a few minutes on first run..."
echo ""
python3 -m pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies!"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi
echo ""

# Run the application
echo "============================================"
echo "Starting PlaylistGrab..."
echo "============================================"
echo ""
python3 main.py

# Deactivate virtual environment when app closes
deactivate

echo ""
echo "Application closed."
read -p "Press Enter to exit..."
