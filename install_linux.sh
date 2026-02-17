#!/bin/bash

set -e

echo "=== CLIP Image Search - Linux Installation ==="

# Detect package manager
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    echo "Detected: apt (Debian/Ubuntu)"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    echo "Detected: dnf (Fedora/RHEL)"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "Detected: yum (CentOS/RHEL)"
else
    echo "Warning: Could not detect package manager. You may need to install dependencies manually."
    PKG_MANAGER=""
fi

# Install system dependencies
echo "Installing system dependencies..."

if [ "$PKG_MANAGER" = "apt" ]; then
    sudo apt-get update
    sudo apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        libegl1 \
        libxkbcommon0 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-keysyms1 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxcb-xfixes0 \
        libgl1-mesa-glx \
        libgomp1 \
        libxcb1
elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
    sudo dnf install -y \
        python3 \
        python3-pip \
        python3-venv \
        mesa-libGL \
        libxkbcommon \
        xcb-util-cursor \
        xcb-util-keysyms \
        xcb-util-shape \
        xcb-util-xinerama \
        xcb-util-xfixes \
        libxcb \
        libgomp
fi

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Check for NVIDIA GPU and install PyTorch with CUDA support
echo "Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        echo "NVIDIA GPU detected! Installing with requirements-nvidia.txt..."
        pip install -r requirements-nvidia.txt
    else
        echo "No NVIDIA GPU detected. Installing with requirements-cpu.txt..."
        pip install -r requirements-cpu.txt
    fi
else
    echo "nvidia-smi not found. Installing with requirements-cpu.txt..."
    pip install -r requirements-cpu.txt
fi

echo ""
echo "=== Installation complete! ==="
echo ""
echo "To run the application:"
echo "  ./run_linux.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
