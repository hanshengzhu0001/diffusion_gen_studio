"""
Performance optimization utilities for high-throughput inference.
"""

import torch
import contextlib
import logging
import time
from typing import Optional, Dict, Any
import psutil
import gc

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Performance optimization manager for inference."""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.optimization_stats = {
            "total_inferences": 0,
            "total_time": 0.0,
            "memory_optimizations": 0
        }
    
    @contextlib.contextmanager
    def optimize_inference(self):
        """Context manager for optimized inference execution."""
        start_time = time.time()
        
        # Pre-inference optimizations
        self._pre_inference_cleanup()
        
        try:
            # Set optimal inference settings
            with torch.inference_mode():
                if self.device == "cuda":
                    with torch.cuda.amp.autocast():
                        yield
                else:
                    yield
        finally:
            # Post-inference cleanup
            self._post_inference_cleanup()
            
            # Update stats
            inference_time = time.time() - start_time
            self.optimization_stats["total_inferences"] += 1
            self.optimization_stats["total_time"] += inference_time
    
    def _pre_inference_cleanup(self):
        """Clean up memory before inference."""
        if self.device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # Force garbage collection
        gc.collect()
        
        self.optimization_stats["memory_optimizations"] += 1
    
    def _post_inference_cleanup(self):
        """Clean up memory after inference."""
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        gc.collect()
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        stats = {
            "system_memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            }
        }
        
        if self.device == "cuda" and torch.cuda.is_available():
            stats["gpu_memory"] = {
                "allocated": torch.cuda.memory_allocated(),
                "reserved": torch.cuda.memory_reserved(),
                "max_allocated": torch.cuda.max_memory_allocated(),
                "total": torch.cuda.get_device_properties(0).total_memory
            }
        
        return stats
    
    def optimize_batch_size(self, base_batch_size: int = 1) -> int:
        """Dynamically optimize batch size based on available memory."""
        if self.device != "cuda":
            return base_batch_size
        
        try:
            # Get available GPU memory
            total_memory = torch.cuda.get_device_properties(0).total_memory
            allocated_memory = torch.cuda.memory_allocated()
            available_memory = total_memory - allocated_memory
            
            # Reserve 20% for safety
            usable_memory = available_memory * 0.8
            
            # Estimate memory per sample (rough approximation)
            # This would need to be calibrated for your specific model
            memory_per_sample = 2 * 1024**3  # 2GB per 1024x1024 image
            
            optimal_batch_size = max(1, int(usable_memory // memory_per_sample))
            
            logger.info(f"Optimized batch size: {optimal_batch_size}")
            return min(optimal_batch_size, base_batch_size * 4)  # Cap at 4x base
            
        except Exception as e:
            logger.warning(f"Could not optimize batch size: {e}")
            return base_batch_size
    
    def enable_torch_optimizations(self):
        """Enable PyTorch-specific optimizations."""
        if hasattr(torch.backends, 'cudnn'):
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            logger.info("Enabled cuDNN optimizations")
        
        # Enable TensorFloat-32 on Ampere GPUs
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            logger.info("Enabled TensorFloat-32")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get performance optimization statistics."""
        stats = self.optimization_stats.copy()
        
        if stats["total_inferences"] > 0:
            stats["average_time"] = stats["total_time"] / stats["total_inferences"]
        else:
            stats["average_time"] = 0.0
        
        return stats

class TensorRTOptimizer:
    """TensorRT optimization for NVIDIA GPUs (placeholder for future implementation)."""
    
    def __init__(self):
        self.enabled = False
        logger.info("TensorRT optimizer initialized (not implemented)")
    
    def optimize_model(self, model):
        """Optimize model with TensorRT (placeholder)."""
        # This would implement TensorRT optimization
        # For now, return the model unchanged
        logger.warning("TensorRT optimization not implemented yet")
        return model
