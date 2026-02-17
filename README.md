# CLIP Image Search

A desktop application for searching images using OpenAI's CLIP (Contrastive Language-Image Pre-training) model. Search your image collection using natural language text queries or by using another image as a reference.

## Features

- **Text Search**: Find images using natural language descriptions
- **Image Search**: Search by dropping or selecting an image
- **Multiple Models**: Choose from different CLIP models (ViT-B/32, ViT-B/16, ViT-L/14)
- **Local Embeddings**: Pre-compute and cache image embeddings for fast searching
- **Dark/Light Themes**: Toggle between dark and light themes
- **Drag & Drop**: Drag images directly into the app to search

## Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum (8GB recommended for larger image collections)
- **GPU**: Optional - CUDA support for faster embedding generation

## Installation

### Linux

Run the installation script:

```bash
chmod +x install_linux.sh
./install_linux.sh
```

The script will:
- Detect your package manager (apt/dnf)
- Install system dependencies for PyQt6
- Create a Python virtual environment
- Install Python dependencies

### Windows

Run the installation script:

```cmd
install_windows.bat
```

The script will:
- Check for Python installation
- Create a Python virtual environment
- Install Python dependencies

## Usage

### Linux

```bash
./run_linux.sh
```

Or manually:
```bash
source venv/bin/activate
python3 main.py
```

### Windows

```cmd
run_windows.bat
```

Or manually:
```cmd
venv\Scripts\activate.bat
python main.py
```

## How to Use

1. **Add Folders**: Click "Add Folder" to select directories containing images
2. **Generate Embeddings**: Click "Generate Embeddings" to pre-process images. This may take a while for large collections
3. **Search**: 
   - Enter a text query (e.g., "beach sunset", "cat photo", "black and white landscape")
   - Or drag and drop an image to find similar images
4. **View Results**: Click on any result to open the image, or right-click for more options

## Available CLIP Models

| Model | Description | Speed |
|-------|-------------|-------|
| clip-vit-base-patch32 | CLIP ViT-B/32 (default) | Fastest |
| clip-vit-base-patch16 | CLIP ViT-B/16 | Medium |
| clip-vit-large-patch14 | CLIP ViT-L/14 | Slowest, most accurate |

## Project Structure

```
imgsearch/
├── main.py              # Main application entry point
├── clip_service.py      # CLIP model wrapper
├── search_engine.py     # Search functionality
├── cache_manager.py     # Embedding cache management
├── requirements.txt     # Python dependencies
├── install_linux.sh    # Linux installation script
├── install_windows.bat  # Windows installation script
├── run_linux.sh        # Linux launch script
├── run_windows.bat     # Windows launch script
└── cache/              # Cached embeddings directory
```

## Dependencies

- torch
- transformers
- Pillow
- numpy
- PyQt6

## Troubleshooting

### Linux: Qt platform plugin error

If you see "Qt platform plugin 'xcb' could not be loaded", install the required Qt dependencies:

```bash
# Ubuntu/Debian
sudo apt install libxcb-cursor0 libxkbcommon0 libegl1

# Fedora
sudo dnf install xcb-util-cursor libxkbcommon mesa-libGL
```

### Out of memory errors

- Reduce the number of images in scanned folders
- Use a smaller CLIP model (ViT-B/32)
- Close other memory-intensive applications

### CUDA not detected

The application will automatically use GPU if available. Ensure you have CUDA drivers installed:

```bash
nvidia-smi  # Check CUDA availability
```

## License

MIT License
