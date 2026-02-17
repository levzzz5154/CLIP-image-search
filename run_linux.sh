#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run install_linux.sh first."
    exit 1
fi

source venv/bin/activate

echo "Starting CLIP Image Search..."
python3 main.py
