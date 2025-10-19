"""
Training script using Apple's ml-mdm (Matryoshka Diffusion Models)
This script uses the actual Apple implementation for training.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add ml-mdm to Python path
ml_mdm_path = Path(__file__).parent.parent / "ml-mdm"
sys.path.insert(0, str(ml_mdm_path))

def setup_ml_mdm_environment():
    """Setup the ml-mdm environment and dependencies."""
    print("Setting up Apple ml-mdm environment...")
    
    # Install required dependencies for ml-mdm
    dependencies = [
        "torch",
        "torchvision", 
        "transformers",
        "diffusers",
        "accelerate",
        "wandb",
        "tensorboard",
        "numpy",
        "pillow",
        "opencv-python",
        "scikit-learn",
        "img2dataset"  # For data preparation
    ]
    
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"✓ Installed {dep}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {dep}: {e}")

def download_pretrained_models():
    """Download Apple's pretrained models."""
    print("Downloading Apple's pretrained models...")
    
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Download pretrained models (64x64 and 256x256)
    model_urls = {
        "vis_model_64x64.pth": "https://docs-assets.developer.apple.com/ml-research/models/mdm/flickr64/vis_model.pth",
        "vis_model_256x256.pth": "https://docs-assets.developer.apple.com/ml-research/models/mdm/flickr256/vis_model.pth"
    }
    
    for filename, url in model_urls.items():
        model_path = models_dir / filename
        if not model_path.exists():
            print(f"Downloading {filename}...")
            try:
                subprocess.run(["curl", "-L", url, "-o", str(model_path)], check=True)
                print(f"✓ Downloaded {filename}")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to download {filename}: {e}")
        else:
            print(f"✓ {filename} already exists")

def train_with_dummy_data():
    """Train using Apple's dummy data example."""
    print("Training with Apple's dummy data...")
    
    # Change to ml-mdm directory
    os.chdir(ml_mdm_path)
    
    # Run Apple's training command with dummy data
    cmd = [
        "torchrun", "--standalone", "--nproc_per_node=1",
        "ml_mdm/clis/train_parallel.py",
        "--file-list=tests/test_files/sample_training_0.tsv",
        "--multinode=0",
        "--output-dir=outputs",
        "--config_path", "configs/models/cc12m_64x64.yaml",
        "--num_diffusion_steps=10",
        "--num-training-steps=10"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Training completed successfully!")
        print("Model saved to: outputs/vis_model_000100.pth")
    except subprocess.CalledProcessError as e:
        print(f"✗ Training failed: {e}")
    except FileNotFoundError:
        print("✗ torchrun not found. Please install PyTorch with distributed training support.")

def generate_samples():
    """Generate samples from the trained model."""
    print("Generating samples...")
    
    model_path = ml_mdm_path / "outputs" / "vis_model_000100.pth"
    if not model_path.exists():
        print("✗ No trained model found. Please train first.")
        return
    
    # Change to ml-mdm directory
    os.chdir(ml_mdm_path)
    
    cmd = [
        "torchrun", "--standalone", "--nproc_per_node=1",
        "ml_mdm/clis/generate_batch.py",
        "--config_path", "configs/models/cc12m_64x64.yaml",
        "--min-examples", "3",
        "--test-file-list", "tests/test_files/sample_training_0.tsv",
        "--sample-image-size", "64",
        "--model-file", str(model_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Sample generation completed!")
    except subprocess.CalledProcessError as e:
        print(f"✗ Sample generation failed: {e}")

def run_web_demo(port=8080):
    """Run Apple's web demo."""
    print(f"Starting web demo on port {port}...")
    
    # Change to ml-mdm directory
    os.chdir(ml_mdm_path)
    
    cmd = [
        "torchrun", "--standalone", "--nproc_per_node=1",
        "ml_mdm/clis/generate_sample.py",
        "--port", str(port)
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"✗ Web demo failed: {e}")
    except KeyboardInterrupt:
        print("Web demo stopped by user")

def main():
    parser = argparse.ArgumentParser(description='Apple ml-mdm Training Pipeline')
    parser.add_argument('--setup', action='store_true', help='Setup ml-mdm environment')
    parser.add_argument('--download-models', action='store_true', help='Download pretrained models')
    parser.add_argument('--train', action='store_true', help='Train with dummy data')
    parser.add_argument('--generate', action='store_true', help='Generate samples')
    parser.add_argument('--demo', action='store_true', help='Run web demo')
    parser.add_argument('--port', type=int, default=8080, help='Port for web demo')
    parser.add_argument('--all', action='store_true', help='Run all steps')
    
    args = parser.parse_args()
    
    if args.all or args.setup:
        setup_ml_mdm_environment()
    
    if args.all or args.download_models:
        download_pretrained_models()
    
    if args.all or args.train:
        train_with_dummy_data()
    
    if args.all or args.generate:
        generate_samples()
    
    if args.demo:
        run_web_demo(args.port)
    
    if not any([args.setup, args.download_models, args.train, args.generate, args.demo, args.all]):
        print("No action specified. Use --help for options.")
        print("Try: python train_apple_mdm.py --all")

if __name__ == '__main__':
    main()
