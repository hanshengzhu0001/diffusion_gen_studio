#!/bin/bash

# ML-MDM Kubernetes Management Script
set -e

case "$1" in
    "status")
        echo "📊 ML-MDM Deployment Status"
        echo "=========================="
        echo ""
        echo "Pods:"
        kubectl get pods -l app=ml-mdm-generator -o wide
        echo ""
        echo "Services:"
        kubectl get services ml-mdm-generator-service
        echo ""
        echo "HPA:"
        kubectl get hpa ml-mdm-generator-hpa
        echo ""
        echo "Deployment:"
        kubectl get deployment ml-mdm-generator-advanced
        ;;
    
    "scale")
        if [ -z "$2" ]; then
            echo "Usage: $0 scale <number-of-replicas>"
            exit 1
        fi
        echo "🔄 Scaling to $2 replicas..."
        kubectl scale deployment ml-mdm-generator-advanced --replicas=$2
        kubectl rollout status deployment/ml-mdm-generator-advanced
        ;;
    
    "logs")
        echo "📋 Getting logs from all pods..."
        kubectl logs -l app=ml-mdm-generator --tail=50
        ;;
    
    "port-forward")
        echo "🌐 Setting up port forwarding..."
        echo "Access the service at: http://localhost:8080"
        kubectl port-forward service/ml-mdm-generator-service 8080:80
        ;;
    
    "delete")
        echo "🗑️ Deleting ML-MDM deployment..."
        kubectl delete -f k8s-deployment-advanced.yaml
        kubectl delete -f k8s-configmap.yaml
        echo "✅ Deployment deleted"
        ;;
    
    "restart")
        echo "🔄 Restarting deployment..."
        kubectl rollout restart deployment/ml-mdm-generator-advanced
        kubectl rollout status deployment/ml-mdm-generator-advanced
        ;;
    
    "test")
        echo "🧪 Testing the deployment..."
        # Get a pod name
        POD_NAME=$(kubectl get pods -l app=ml-mdm-generator -o jsonpath='{.items[0].metadata.name}')
        if [ -z "$POD_NAME" ]; then
            echo "❌ No pods found"
            exit 1
        fi
        
        echo "Testing pod: $POD_NAME"
        kubectl exec $POD_NAME -- curl -f http://localhost:8080/ || echo "❌ Health check failed"
        ;;
    
    *)
        echo "ML-MDM Kubernetes Management"
        echo "==========================="
        echo ""
        echo "Usage: $0 {status|scale|logs|port-forward|delete|restart|test}"
        echo ""
        echo "Commands:"
        echo "  status       - Show deployment status"
        echo "  scale <n>    - Scale to n replicas"
        echo "  logs         - Show logs from all pods"
        echo "  port-forward - Forward port 8080 to access service"
        echo "  delete       - Delete the deployment"
        echo "  restart      - Restart the deployment"
        echo "  test         - Test the deployment health"
        ;;
esac
