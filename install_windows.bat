@echo off
setlocal enabledelayedexpansion

echo === CLIP Image Search - Windows Installation ===

:: Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    exit /b 1
)

:: Get Python version
for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info.major ^. ^. sys.version_info.minor)"') do set PYTHON_VERSION=%%v
echo Python version: %PYTHON_VERSION%

:: Check if Python version is >= 3.8
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python 3.8 or higher is required.
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Check for NVIDIA GPU and install PyTorch with CUDA support
echo Checking for NVIDIA GPU...
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    nvidia-smi >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo NVIDIA GPU detected! Installing PyTorch with CUDA support...
        pip install torch --index-url https://download.pytorch.org/whl/cu121
    ) else (
        echo No NVIDIA GPU detected. Installing CPU-only PyTorch...
        pip install torch
    )
) else (
    echo nvidia-smi not found. Installing CPU-only PyTorch...
    pip install torch
)

:: Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo === Installation complete! ===
echo.
echo To run the application:
echo   run_windows.bat
echo.
echo Or manually:
echo   venv\Scripts\activate.bat
echo   python main.py
echo.

endlocal
