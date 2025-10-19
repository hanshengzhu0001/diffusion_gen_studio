#!/bin/bash

# ML-MDM Kubernetes Deployment Script
set -e

echo "🚀 Deploying ML-MDM to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker build -t ml-mdm-generator:latest .

# Apply Kubernetes manifests
echo "🔧 Applying Kubernetes configurations..."

# Apply ConfigMap and Secrets
kubectl apply -f k8s-configmap.yaml

# Apply the advanced deployment
kubectl apply -f k8s-deployment-advanced.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ml-mdm-generator-advanced

# Get service information
echo "🌐 Getting service information..."
kubectl get services ml-mdm-generator-service

# Get pod status
echo "📊 Pod status:"
kubectl get pods -l app=ml-mdm-generator

# Get HPA status
echo "📈 HPA status:"
kubectl get hpa ml-mdm-generator-hpa

echo "✅ Deployment completed!"
echo ""
echo "To access the service:"
echo "1. Get external IP: kubectl get service ml-mdm-generator-service"
echo "2. Port forward: kubectl port-forward service/ml-mdm-generator-service 8080:80"
echo "3. Access: http://localhost:8080"
