"""
Unit tests for the DiffusionArt Gen Studio API.
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

import sys
sys.path.append('../inference')

from inference.api.app import app
from inference.models.diffusion_model import DiffusionInferenceEngine

@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_diffusion_engine():
    """Mock diffusion engine fixture."""
    engine = Mock(spec=DiffusionInferenceEngine)
    engine.is_ready.return_value = True
    
    # Create a mock image
    mock_image = Image.new('RGB', (1024, 1024), color='red')
    engine.generate.return_value = mock_image
    
    return engine

@pytest.fixture
def mock_redis():
    """Mock Redis client fixture."""
    redis_mock = Mock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None  # No cache hit by default
    redis_mock.setex.return_value = True
    return redis_mock

class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'gpu_available' in data
    
    @patch('inference.api.app.diffusion_engine')
    @patch('inference.api.app.redis_client')
    def test_readiness_check_ready(self, mock_redis, mock_engine, client):
        """Test readiness check when service is ready."""
        mock_engine.is_ready.return_value = True
        mock_redis.ping.return_value = True
        
        response = client.get('/ready')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'ready'
    
    @patch('inference.api.app.diffusion_engine')
    def test_readiness_check_not_ready(self, mock_engine, client):
        """Test readiness check when model is not loaded."""
        mock_engine.is_ready.return_value = False
        
        response = client.get('/ready')
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert data['status'] == 'not ready'
        assert 'model not loaded' in data['reason']

class TestImageGeneration:
    """Test image generation endpoint."""
    
    @patch('inference.api.app.diffusion_engine')
    @patch('inference.api.app.redis_client')
    def test_generate_image_success(self, mock_redis, mock_engine, client):
        """Test successful image generation."""
        # Setup mocks
        mock_engine.is_ready.return_value = True
        mock_redis.get.return_value = None  # No cache
        
        # Create mock image
        mock_image = Image.new('RGB', (1024, 1024), color='blue')
        mock_engine.generate.return_value = mock_image
        
        # Test request
        payload = {
            'prompt': 'A beautiful landscape',
            'width': 1024,
            'height': 1024,
            'num_inference_steps': 30
        }
        
        response = client.post('/generate', 
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'request_id' in data
        assert 'image' in data
        assert data['cached'] == False
        assert 'generation_time' in data
        
        # Verify engine was called with correct parameters
        mock_engine.generate.assert_called_once()
        call_args = mock_engine.generate.call_args
        assert call_args.kwargs['prompt'] == 'A beautiful landscape'
        assert call_args.kwargs['width'] == 1024
        assert call_args.kwargs['height'] == 1024
        assert call_args.kwargs['num_inference_steps'] == 30
    
    @patch('inference.api.app.redis_client')
    def test_generate_image_cached(self, mock_redis, client):
        """Test cached image generation."""
        # Setup cache hit
        cached_image_b64 = base64.b64encode(b'fake_image_data').decode('utf-8')
        mock_redis.get.return_value = cached_image_b64.encode('utf-8')
        
        payload = {
            'prompt': 'A beautiful landscape',
            'width': 1024,
            'height': 1024
        }
        
        response = client.post('/generate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['cached'] == True
        assert data['image'] == cached_image_b64
        assert data['generation_time'] == 0.0
    
    def test_generate_image_missing_prompt(self, client):
        """Test image generation with missing prompt."""
        payload = {'width': 1024, 'height': 1024}
        
        response = client.post('/generate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Missing required field: prompt' in data['error']
    
    def test_generate_image_invalid_resolution(self, client):
        """Test image generation with invalid resolution."""
        payload = {
            'prompt': 'Test prompt',
            'width': 2048,  # Too large
            'height': 1024
        }
        
        response = client.post('/generate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Maximum resolution is 1024x1024' in data['error']
    
    def test_generate_image_invalid_steps(self, client):
        """Test image generation with too many steps."""
        payload = {
            'prompt': 'Test prompt',
            'num_inference_steps': 100  # Too many
        }
        
        response = client.post('/generate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Maximum inference steps is 50' in data['error']
    
    @patch('inference.api.app.diffusion_engine')
    def test_generate_image_model_error(self, mock_engine, client):
        """Test image generation when model fails."""
        mock_engine.is_ready.return_value = True
        mock_engine.generate.side_effect = Exception("Model error")
        
        payload = {
            'prompt': 'Test prompt',
            'width': 512,
            'height': 512
        }
        
        response = client.post('/generate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['error'] == 'Image generation failed'
        assert 'request_id' in data

class TestMetricsEndpoints:
    """Test metrics and monitoring endpoints."""
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get('/metrics')
        assert response.status_code == 200
        # Should return Prometheus format metrics
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.get_device_properties')
    def test_stats_endpoint(self, mock_props, mock_memory, mock_cuda, client):
        """Test stats endpoint."""
        mock_cuda.return_value = True
        mock_memory.return_value = 1024 * 1024 * 1024  # 1GB
        
        mock_device_props = Mock()
        mock_device_props.total_memory = 8 * 1024 * 1024 * 1024  # 8GB
        mock_props.return_value = mock_device_props
        
        response = client.get('/stats')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'gpu_memory_used' in data
        assert 'gpu_memory_total' in data
        assert 'model_loaded' in data
        assert 'cache_info' in data

class TestDiffusionInferenceEngine:
    """Test the DiffusionInferenceEngine class."""
    
    def test_init(self):
        """Test engine initialization."""
        engine = DiffusionInferenceEngine()
        assert engine.device in ['cuda', 'cpu']
        assert not engine.is_loaded
        assert engine.pipeline is None
    
    def test_is_ready_false(self):
        """Test is_ready when model not loaded."""
        engine = DiffusionInferenceEngine()
        assert not engine.is_ready()
    
    @patch('inference.models.diffusion_model.StableDiffusionXLPipeline')
    def test_load_model(self, mock_pipeline_class):
        """Test model loading."""
        mock_pipeline = Mock()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        mock_pipeline.to.return_value = mock_pipeline
        
        engine = DiffusionInferenceEngine()
        engine.load_model()
        
        assert engine.is_loaded
        assert engine.pipeline is not None
        mock_pipeline_class.from_pretrained.assert_called_once()
    
    def test_generate_not_loaded(self):
        """Test generate when model not loaded."""
        engine = DiffusionInferenceEngine()
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            engine.generate("test prompt")
    
    def test_get_model_info_not_loaded(self):
        """Test get_model_info when model not loaded."""
        engine = DiffusionInferenceEngine()
        info = engine.get_model_info()
        
        assert info['status'] == 'not_loaded'
    
    def test_unload_model(self):
        """Test model unloading."""
        engine = DiffusionInferenceEngine()
        engine.pipeline = Mock()
        engine.is_loaded = True
        
        engine.unload_model()
        
        assert not engine.is_loaded
        assert engine.pipeline is None

if __name__ == '__main__':
    pytest.main([__file__])
