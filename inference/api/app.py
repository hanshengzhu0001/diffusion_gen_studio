"""
DiffusionArt Gen Studio - High-Performance Inference API
Flask backend with optimized diffusion inference for production deployment.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import torch
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import redis
from PIL import Image
import io
import base64
import uuid

from models.diffusion_model import DiffusionInferenceEngine
from optimizations.performance import PerformanceOptimizer
from utils.monitoring import MetricsCollector, setup_logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Setup logging
logger = setup_logging()

# Initialize components
redis_client = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)
diffusion_engine = DiffusionInferenceEngine()
performance_optimizer = PerformanceOptimizer()
metrics_collector = MetricsCollector()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Kubernetes probes."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'gpu_available': torch.cuda.is_available(),
        'gpu_count': torch.cuda.device_count() if torch.cuda.is_available() else 0
    })

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint for Kubernetes."""
    try:
        # Check if model is loaded
        if not diffusion_engine.is_ready():
            return jsonify({'status': 'not ready', 'reason': 'model not loaded'}), 503
        
        # Check Redis connection
        redis_client.ping()
        
        return jsonify({'status': 'ready'})
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({'status': 'not ready', 'reason': str(e)}), 503

@app.route('/generate', methods=['POST'])
def generate_image():
    """
    Generate image from text prompt.
    
    Expected payload:
    {
        "prompt": "A beautiful landscape with mountains",
        "negative_prompt": "blurry, low quality",
        "width": 1024,
        "height": 1024,
        "num_inference_steps": 30,
        "guidance_scale": 7.5,
        "seed": 42
    }
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing required field: prompt'}), 400
        
        # Extract parameters with defaults
        prompt = data['prompt']
        negative_prompt = data.get('negative_prompt', '')
        width = data.get('width', 1024)
        height = data.get('height', 1024)
        num_inference_steps = data.get('num_inference_steps', 30)
        guidance_scale = data.get('guidance_scale', 7.5)
        seed = data.get('seed', None)
        
        # Validate parameters
        if width > 1024 or height > 1024:
            return jsonify({'error': 'Maximum resolution is 1024x1024'}), 400
        
        if num_inference_steps > 50:
            return jsonify({'error': 'Maximum inference steps is 50'}), 400
        
        logger.info(f"Request {request_id}: Generating image - {prompt[:50]}...")
        
        # Check cache first
        cache_key = f"img:{hash(str(data))}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Request {request_id}: Cache hit")
            metrics_collector.increment_counter('cache_hits')
            return jsonify({
                'request_id': request_id,
                'cached': True,
                'image': cached_result.decode('utf-8'),
                'generation_time': 0.0
            })
        
        # Generate image
        with performance_optimizer.optimize_inference():
            image = diffusion_engine.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=seed
            )
        
        # Convert to base64
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        # Cache result (expire in 1 hour)
        redis_client.setex(cache_key, 3600, img_base64)
        
        generation_time = time.time() - start_time
        
        # Record metrics
        metrics_collector.record_latency('image_generation', generation_time)
        metrics_collector.increment_counter('images_generated')
        
        logger.info(f"Request {request_id}: Generated in {generation_time:.2f}s")
        
        return jsonify({
            'request_id': request_id,
            'cached': False,
            'image': img_base64,
            'generation_time': generation_time,
            'parameters': {
                'width': width,
                'height': height,
                'steps': num_inference_steps,
                'guidance_scale': guidance_scale
            }
        })
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Request {request_id}: Error after {error_time:.2f}s - {str(e)}")
        metrics_collector.increment_counter('generation_errors')
        
        return jsonify({
            'error': 'Image generation failed',
            'request_id': request_id,
            'details': str(e)
        }), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Prometheus metrics endpoint."""
    return metrics_collector.get_prometheus_metrics()

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    return jsonify({
        'gpu_memory_used': torch.cuda.memory_allocated() if torch.cuda.is_available() else 0,
        'gpu_memory_total': torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0,
        'model_loaded': diffusion_engine.is_ready(),
        'cache_info': {
            'redis_connected': redis_client.ping(),
            'cache_size': redis_client.dbsize()
        }
    })

if __name__ == '__main__':
    # Initialize model on startup
    logger.info("Loading diffusion model...")
    diffusion_engine.load_model()
    logger.info("Model loaded successfully!")
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )
