#!/bin/bash

# Docker Compose Testing Script
set -e

echo "🐳 Testing ML-MDM with Docker Compose (Horizontal Scaling Simulation)"

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down 2>/dev/null || true

# Build and start services
echo "🚀 Starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 60

# Test individual services
echo "🔍 Testing individual services..."
for port in 8080 8081 8082; do
    if curl -f http://localhost:$port/ > /dev/null 2>&1; then
        echo "✅ Service on port $port is healthy"
    else
        echo "❌ Service on port $port is not responding"
    fi
done

# Test load balancer
echo "⚖️ Testing load balancer..."
if curl -f http://localhost:80/ > /dev/null 2>&1; then
    echo "✅ Load balancer is working"
else
    echo "❌ Load balancer is not responding"
fi

# Show status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🌐 Access Points:"
echo "  Load Balancer: http://localhost:80"
echo "  Instance 1: http://localhost:8080"
echo "  Instance 2: http://localhost:8081"
echo "  Instance 3: http://localhost:8082"

echo ""
echo "📋 Management Commands:"
echo "  View logs: docker-compose logs -f"
echo "  Scale up: docker-compose up --scale ml-mdm-generator=5 -d"
echo "  Stop: docker-compose down"
echo "  Restart: docker-compose restart"
