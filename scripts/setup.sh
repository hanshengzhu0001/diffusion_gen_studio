#!/bin/bash

# ML-MDM Horizontal Scaling Setup Script
# This script sets up the complete load balancing environment

set -e

echo "🚀 ML-MDM Horizontal Scaling Setup"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if model file exists
if [ ! -f "ml-mdm/ml-mdm-matryoshka/models/vis_model_64x64.pth" ]; then
    echo "⚠️  Model file not found. Please ensure vis_model_64x64.pth is in ml-mdm/ml-mdm-matryoshka/models/"
    echo "   You can download it from the ML-MDM repository or use your own trained model."
    exit 1
fi

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "generate_sample.py" 2>/dev/null || true
pkill -f "load_balancer.py" 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 2

# Start ML-MDM instances
echo "🎨 Starting ML-MDM instances..."
echo "   Instance 1 (port 8080)..."
cd ml-mdm/ml-mdm-matryoshka
source ../../venv/bin/activate
python ml_mdm/clis/generate_sample.py --port 8080 --config_path configs/models/cc12m_64x64.yaml --model-file vis_model_64x64.pth &
INSTANCE1_PID=$!

echo "   Instance 2 (port 8081)..."
python ml_mdm/clis/generate_sample.py --port 8081 --config_path configs/models/cc12m_64x64.yaml --model-file vis_model_64x64.pth &
INSTANCE2_PID=$!

echo "   Instance 3 (port 8082)..."
python ml_mdm/clis/generate_sample.py --port 8082 --config_path configs/models/cc12m_64x64.yaml --model-file vis_model_64x64.pth &
INSTANCE3_PID=$!

cd ../..

# Wait for instances to start
echo "⏳ Waiting for instances to initialize (30 seconds)..."
sleep 30

# Start load balancer
echo "⚖️  Starting load balancer..."
python load_balancer.py &
LOAD_BALANCER_PID=$!

# Wait for load balancer to start
sleep 5

# Test the setup
echo "🧪 Testing setup..."
echo "   Testing Instance 1..."
curl -s -o /dev/null -w "   Instance 1: %{http_code}\n" http://localhost:8080 || echo "   Instance 1: FAILED"

echo "   Testing Instance 2..."
curl -s -o /dev/null -w "   Instance 2: %{http_code}\n" http://localhost:8081 || echo "   Instance 2: FAILED"

echo "   Testing Instance 3..."
curl -s -o /dev/null -w "   Instance 3: %{http_code}\n" http://localhost:8082 || echo "   Instance 3: FAILED"

echo "   Testing Load Balancer..."
curl -s -o /dev/null -w "   Load Balancer: %{http_code}\n" http://localhost:5000 || echo "   Load Balancer: FAILED"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "🌐 Access Points:"
echo "   Load Balancer Dashboard: http://localhost:5000"
echo "   Instance 1: http://localhost:8080"
echo "   Instance 2: http://localhost:8081"
echo "   Instance 3: http://localhost:8082"
echo ""
echo "📊 Features:"
echo "   ✅ Real-time monitoring"
echo "   ✅ Load balancing"
echo "   ✅ Health checks"
echo "   ✅ Model caching"
echo ""
echo "🛑 To stop all services:"
echo "   pkill -f 'generate_sample.py'"
echo "   pkill -f 'load_balancer.py'"
echo ""
echo "🚀 Ready to generate images with horizontal scaling!"

# Save PIDs for cleanup
echo $INSTANCE1_PID > .instance1.pid
echo $INSTANCE2_PID > .instance2.pid
echo $INSTANCE3_PID > .instance3.pid
echo $LOAD_BALANCER_PID > .load_balancer.pid

echo ""
echo "💡 Open http://localhost:5000 in your browser to start generating images!"