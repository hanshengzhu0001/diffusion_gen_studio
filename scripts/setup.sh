#!/bin/bash
# DiffusionArt Gen Studio - Development Setup Script

set -e

echo "🚀 Setting up DiffusionArt Gen Studio development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.9+ is installed
print_status "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 9) else 1)'; then
        print_status "Python $PYTHON_VERSION found ✓"
    else
        print_error "Python 3.9+ required, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check if CUDA is available (optional)
print_status "Checking CUDA availability..."
if command -v nvidia-smi &> /dev/null; then
    CUDA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)
    print_status "NVIDIA GPU detected with driver version: $CUDA_VERSION ✓"
    export CUDA_AVAILABLE=true
else
    print_warning "CUDA not detected. Will use CPU-only mode."
    export CUDA_AVAILABLE=false
fi

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created ✓"
else
    print_status "Virtual environment already exists ✓"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install PyTorch (CUDA or CPU version)
print_status "Installing PyTorch..."
if [ "$CUDA_AVAILABLE" = true ]; then
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    print_status "PyTorch with CUDA support installed ✓"
else
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    print_status "PyTorch CPU-only version installed ✓"
fi

# Install requirements
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Install development dependencies
print_status "Installing development dependencies..."
pip install pytest pytest-cov black flake8 mypy pre-commit jupyter

# Setup pre-commit hooks
print_status "Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data/train data/val models checkpoints logs cache

# Download example model (placeholder)
print_status "Setting up model cache directory..."
export HF_HOME=$(pwd)/cache
export TRANSFORMERS_CACHE=$(pwd)/cache
export HF_DATASETS_CACHE=$(pwd)/cache

# Test installation
print_status "Testing installation..."
python -c "
import torch
import transformers
import diffusers
import flask
print('✓ PyTorch version:', torch.__version__)
print('✓ CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('✓ CUDA devices:', torch.cuda.device_count())
print('✓ Transformers version:', transformers.__version__)
print('✓ Diffusers version:', diffusers.__version__)
print('✓ Flask version:', flask.__version__)
"

# Create environment file
print_status "Creating environment configuration..."
cat > .env << EOF
# DiffusionArt Gen Studio Environment Configuration
FLASK_ENV=development
LOG_LEVEL=INFO
REDIS_HOST=localhost
REDIS_PORT=6379
MODEL_CACHE_DIR=./cache
MAX_BATCH_SIZE=4
DEFAULT_STEPS=30
MAX_STEPS=50
MAX_RESOLUTION=1024
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=8000

# HuggingFace Cache
HF_HOME=./cache
TRANSFORMERS_CACHE=./cache
HF_DATASETS_CACHE=./cache

# CUDA Settings (if available)
CUDA_VISIBLE_DEVICES=0
EOF

print_status "Environment file created ✓"

# Setup VS Code configuration (if .vscode doesn't exist)
if [ ! -d ".vscode" ]; then
    print_status "Setting up VS Code configuration..."
    mkdir -p .vscode
    
    cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/cache": true,
        "**/models": true
    }
}
EOF

    cat > .vscode/launch.json << EOF
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask API",
            "type": "python",
            "request": "launch",
            "program": "inference/api/app.py",
            "env": {
                "FLASK_ENV": "development"
            },
            "console": "integratedTerminal"
        },
        {
            "name": "Training",
            "type": "python",
            "request": "launch",
            "program": "training/train_diffusion.py",
            "args": ["--config", "training/configs/base_config.yaml"],
            "console": "integratedTerminal"
        }
    ]
}
EOF

    print_status "VS Code configuration created ✓"
fi

# Final instructions
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Start development server: python inference/api/app.py"
echo "3. Run tests: pytest tests/"
echo "4. Start training: python training/train_diffusion.py --config training/configs/base_config.yaml"
echo ""
echo "For Docker deployment:"
echo "1. Build image: docker build -f deployment/docker/Dockerfile -t diffusion-gen-studio ."
echo "2. Run container: docker run -p 5000:5000 diffusion-gen-studio"
echo ""
echo "For Kubernetes deployment:"
echo "1. Apply manifests: kubectl apply -f deployment/k8s/"
echo ""
print_status "Happy coding! 🚀"
