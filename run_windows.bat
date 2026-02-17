@echo off
setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run install_windows.bat first.
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting CLIP Image Search...
python main.py
