"""
Monitoring and observability utilities for the inference service.
"""

import time
import logging
import structlog
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import threading
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Prometheus metrics
IMAGES_GENERATED = Counter('images_generated_total', 'Total number of images generated')
GENERATION_ERRORS = Counter('generation_errors_total', 'Total number of generation errors')
CACHE_HITS = Counter('cache_hits_total', 'Total number of cache hits')
CACHE_MISSES = Counter('cache_misses_total', 'Total number of cache misses')

GENERATION_LATENCY = Histogram(
    'image_generation_duration_seconds',
    'Time spent generating images',
    buckets=[0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0]
)

GPU_MEMORY_USAGE = Gauge('gpu_memory_usage_bytes', 'GPU memory usage in bytes')
ACTIVE_REQUESTS = Gauge('active_requests', 'Number of active requests')

class MetricsCollector:
    """Centralized metrics collection and reporting."""
    
    def __init__(self):
        self.metrics = {
            'counters': defaultdict(int),
            'histograms': defaultdict(list),
            'gauges': defaultdict(float),
            'latencies': defaultdict(lambda: deque(maxlen=1000))
        }
        self.lock = threading.Lock()
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter metric."""
        with self.lock:
            self.metrics['counters'][name] += value
        
        # Update Prometheus metrics
        if name == 'images_generated':
            IMAGES_GENERATED.inc(value)
        elif name == 'generation_errors':
            GENERATION_ERRORS.inc(value)
        elif name == 'cache_hits':
            CACHE_HITS.inc(value)
        elif name == 'cache_misses':
            CACHE_MISSES.inc(value)
    
    def record_latency(self, name: str, value: float):
        """Record a latency measurement."""
        with self.lock:
            self.metrics['latencies'][name].append(value)
            self.metrics['histograms'][name].append(value)
        
        # Update Prometheus metrics
        if name == 'image_generation':
            GENERATION_LATENCY.observe(value)
    
    def set_gauge(self, name: str, value: float):
        """Set a gauge metric value."""
        with self.lock:
            self.metrics['gauges'][name] = value
        
        # Update Prometheus metrics
        if name == 'gpu_memory_usage':
            GPU_MEMORY_USAGE.set(value)
        elif name == 'active_requests':
            ACTIVE_REQUESTS.set(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self.lock:
            # Calculate percentiles for latencies
            percentiles = {}
            for name, values in self.metrics['latencies'].items():
                if values:
                    sorted_values = sorted(values)
                    n = len(sorted_values)
                    percentiles[name] = {
                        'p50': sorted_values[int(0.5 * n)],
                        'p95': sorted_values[int(0.95 * n)],
                        'p99': sorted_values[int(0.99 * n)],
                        'mean': sum(sorted_values) / n,
                        'count': n
                    }
            
            return {
                'counters': dict(self.metrics['counters']),
                'gauges': dict(self.metrics['gauges']),
                'percentiles': percentiles,
                'timestamp': time.time()
            }
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest()

def setup_logging() -> logging.Logger:
    """Setup structured logging with appropriate formatters."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup standard logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler()]
    )
    
    return structlog.get_logger()

class RequestTracker:
    """Track individual request metrics and lifecycle."""
    
    def __init__(self, request_id: str, metrics_collector: MetricsCollector):
        self.request_id = request_id
        self.metrics_collector = metrics_collector
        self.start_time = time.time()
        self.logger = structlog.get_logger().bind(request_id=request_id)
        
        # Increment active requests
        self.metrics_collector.set_gauge('active_requests', 
            self.metrics_collector.metrics['gauges']['active_requests'] + 1)
    
    def __enter__(self):
        self.logger.info("Request started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info("Request completed", duration=duration)
            self.metrics_collector.increment_counter('requests_completed')
        else:
            self.logger.error("Request failed", duration=duration, error=str(exc_val))
            self.metrics_collector.increment_counter('requests_failed')
        
        # Decrement active requests
        self.metrics_collector.set_gauge('active_requests',
            max(0, self.metrics_collector.metrics['gauges']['active_requests'] - 1))
        
        self.metrics_collector.record_latency('request_duration', duration)

class HealthChecker:
    """Health and readiness check utilities."""
    
    def __init__(self, diffusion_engine, redis_client):
        self.diffusion_engine = diffusion_engine
        self.redis_client = redis_client
    
    def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': time.time()
        }
        
        try:
            # Check model status
            health_status['checks']['model'] = {
                'status': 'healthy' if self.diffusion_engine.is_ready() else 'unhealthy',
                'loaded': self.diffusion_engine.is_ready()
            }
            
            # Check Redis connection
            try:
                self.redis_client.ping()
                health_status['checks']['redis'] = {'status': 'healthy'}
            except Exception as e:
                health_status['checks']['redis'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
            
            # Check GPU status
            import torch
            if torch.cuda.is_available():
                health_status['checks']['gpu'] = {
                    'status': 'healthy',
                    'device_count': torch.cuda.device_count(),
                    'memory_allocated': torch.cuda.memory_allocated(),
                    'memory_reserved': torch.cuda.memory_reserved()
                }
            else:
                health_status['checks']['gpu'] = {
                    'status': 'unavailable',
                    'message': 'CUDA not available'
                }
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
