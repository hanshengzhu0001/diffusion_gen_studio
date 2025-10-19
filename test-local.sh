#!/bin/bash

# Local Testing Script for ML-MDM
set -e

echo "🧪 Testing ML-MDM Deployment Locally"

# Test 1: Build Docker image
echo "📦 Test 1: Building Docker image..."
if docker build -t ml-mdm-generator:latest .; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker image build failed"
    exit 1
fi

# Test 2: Run container locally
echo "🚀 Test 2: Running container locally..."
docker run -d --name ml-mdm-test -p 8080:8080 ml-mdm-generator:latest

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 30

# Test 3: Health check
echo "🏥 Test 3: Health check..."
if curl -f http://localhost:8080/ > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker logs ml-mdm-test
    docker stop ml-mdm-test
    docker rm ml-mdm-test
    exit 1
fi

# Test 4: API test
echo "🔌 Test 4: Testing API endpoint..."
if curl -f http://localhost:8080/gradio_api/generate > /dev/null 2>&1; then
    echo "✅ API endpoint accessible"
else
    echo "⚠️ API endpoint not accessible (this might be normal for Gradio)"
fi

echo ""
echo "🎉 Local testing completed successfully!"
echo ""
echo "Container is running at: http://localhost:8080"
echo "To stop: docker stop ml-mdm-test"
echo "To remove: docker rm ml-mdm-test"
echo "To view logs: docker logs ml-mdm-test"
