#!/bin/bash

# ML-MDM Cleanup Script
# Stops all running services and cleans up

echo "🧹 ML-MDM Cleanup"
echo "================="

# Kill all ML-MDM processes
echo "🛑 Stopping ML-MDM instances..."
pkill -f "generate_sample.py" 2>/dev/null || echo "   No ML-MDM instances running"

echo "🛑 Stopping load balancer..."
pkill -f "load_balancer.py" 2>/dev/null || echo "   No load balancer running"

# Kill Docker containers if running
echo "🛑 Stopping Docker containers..."
docker-compose down 2>/dev/null || echo "   No Docker containers running"

# Clean up PID files
echo "🧹 Cleaning up PID files..."
rm -f .instance1.pid .instance2.pid .instance3.pid .load_balancer.pid 2>/dev/null || true

# Free up ports
echo "🔓 Freeing up ports..."
lsof -ti:8080,8081,8082,5000 | xargs kill -9 2>/dev/null || echo "   Ports already free"

echo ""
echo "✅ Cleanup Complete!"
echo "==================="
echo ""
echo "All services stopped and ports freed."
echo "Ready for fresh deployment."
