# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install MLX for Apple Silicon (this will fail on Linux, but we'll handle it)
RUN pip install mlx || echo "MLX not available on this platform, will use CPU fallback"

# Copy the ml-mdm project
COPY ml-mdm/ /app/ml-mdm/

# Set environment variables
ENV PYTHONPATH=/app/ml-mdm/ml-mdm-matryoshka
ENV CUDA_VISIBLE_DEVICES=""
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Create directories for models and outputs
RUN mkdir -p /app/models /app/outputs

# Expose port
EXPOSE 8080

# Set the working directory to the ml-mdm project
WORKDIR /app/ml-mdm/ml-mdm-matryoshka

# Default command
CMD ["python", "ml_mdm/clis/generate_sample.py", "--port", "8080", "--config_path", "configs/models/cc12m_64x64.yaml", "--model-file", "vis_model_64x64.pth"]
