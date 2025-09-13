#!/bin/bash
# DiffusionArt Gen Studio - Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="diffusion-gen-studio"
AWS_REGION="${AWS_REGION:-us-west-2}"
ECR_REPOSITORY="${ECR_REPOSITORY:-diffusion-gen-studio}"
CLUSTER_NAME="${CLUSTER_NAME:-diffusion-cluster}"
NAMESPACE="diffusion-gen-studio"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Deployment environment (dev|staging|production)"
    echo "  -t, --tag TAG           Docker image tag (default: latest)"
    echo "  -b, --build             Build and push Docker image"
    echo "  -i, --infrastructure    Deploy infrastructure with Terraform"
    echo "  -k, --kubernetes        Deploy to Kubernetes"
    echo "  -a, --all               Deploy everything (build + infra + k8s)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e production -t v1.0.0 -a    # Full production deployment"
    echo "  $0 -e staging -b -k              # Build and deploy to staging"
    echo "  $0 -e dev -k                     # Deploy to dev environment"
}

# Parse command line arguments
ENVIRONMENT=""
IMAGE_TAG="latest"
BUILD_IMAGE=false
DEPLOY_INFRASTRUCTURE=false
DEPLOY_KUBERNETES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -b|--build)
            BUILD_IMAGE=true
            shift
            ;;
        -i|--infrastructure)
            DEPLOY_INFRASTRUCTURE=true
            shift
            ;;
        -k|--kubernetes)
            DEPLOY_KUBERNETES=true
            shift
            ;;
        -a|--all)
            BUILD_IMAGE=true
            DEPLOY_INFRASTRUCTURE=true
            DEPLOY_KUBERNETES=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ -z "$ENVIRONMENT" ]]; then
    print_error "Environment must be specified with -e or --environment"
    usage
    exit 1
fi

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    print_error "Environment must be one of: dev, staging, production"
    exit 1
fi

print_header "Starting deployment for environment: $ENVIRONMENT"

# Check required tools
check_tools() {
    print_status "Checking required tools..."
    
    local tools=("aws" "docker" "kubectl" "terraform")
    for tool in "${tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            print_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    print_status "All required tools are available ✓"
}

# Configure AWS CLI
configure_aws() {
    print_status "Configuring AWS CLI..."
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure'"
        exit 1
    fi
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_status "Using AWS account: $ACCOUNT_ID"
}

# Build and push Docker image
build_and_push() {
    print_header "Building and pushing Docker image..."
    
    # Get ECR login token
    print_status "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Build image
    print_status "Building Docker image..."
    docker build -f deployment/docker/Dockerfile -t $ECR_REPOSITORY:$IMAGE_TAG .
    
    # Tag for ECR
    ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:latest
    
    # Push to ECR
    print_status "Pushing image to ECR..."
    docker push $ECR_URI:$IMAGE_TAG
    docker push $ECR_URI:latest
    
    print_status "Image pushed successfully ✓"
    echo "Image URI: $ECR_URI:$IMAGE_TAG"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    print_header "Deploying infrastructure with Terraform..."
    
    cd deployment/terraform
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Select workspace
    terraform workspace select $ENVIRONMENT || terraform workspace new $ENVIRONMENT
    
    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var="environment=$ENVIRONMENT" -out=tfplan
    
    # Apply deployment
    print_status "Applying Terraform deployment..."
    terraform apply tfplan
    
    # Get outputs
    CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint)
    CLUSTER_NAME=$(terraform output -raw cluster_name)
    ECR_REPOSITORY_URL=$(terraform output -raw ecr_repository_url)
    
    print_status "Infrastructure deployed successfully ✓"
    echo "Cluster endpoint: $CLUSTER_ENDPOINT"
    echo "ECR repository: $ECR_REPOSITORY_URL"
    
    cd ../..
}

# Deploy to Kubernetes
deploy_kubernetes() {
    print_header "Deploying to Kubernetes..."
    
    # Update kubeconfig
    print_status "Updating kubeconfig..."
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME-$ENVIRONMENT
    
    # Create namespace
    print_status "Creating namespace..."
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Update image in deployment manifest
    print_status "Updating deployment manifest..."
    ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
    sed -i.bak "s|image: .*|image: $ECR_URI:$IMAGE_TAG|" deployment/k8s/deployment.yaml
    
    # Apply Kubernetes manifests
    print_status "Applying Kubernetes manifests..."
    kubectl apply -f deployment/k8s/namespace.yaml
    kubectl apply -f deployment/k8s/configmap.yaml
    kubectl apply -f deployment/k8s/redis.yaml
    kubectl apply -f deployment/k8s/deployment.yaml
    kubectl apply -f deployment/k8s/hpa.yaml
    
    # Apply ingress for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        kubectl apply -f deployment/k8s/ingress.yaml
    fi
    
    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl rollout status deployment/diffusion-api -n $NAMESPACE --timeout=600s
    
    # Restore original deployment file
    mv deployment/k8s/deployment.yaml.bak deployment/k8s/deployment.yaml
    
    print_status "Kubernetes deployment completed ✓"
    
    # Show deployment status
    print_status "Deployment status:"
    kubectl get pods -n $NAMESPACE
    kubectl get services -n $NAMESPACE
    kubectl get hpa -n $NAMESPACE
}

# Health check
health_check() {
    print_header "Running health checks..."
    
    # Wait for pods to be ready
    print_status "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=diffusion-api -n $NAMESPACE --timeout=300s
    
    # Get service endpoint
    if [[ "$ENVIRONMENT" == "production" ]]; then
        ENDPOINT=$(kubectl get ingress diffusion-api-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
        HEALTH_URL="https://$ENDPOINT/health"
    else
        # Port forward for testing
        kubectl port-forward svc/diffusion-api-service 8080:80 -n $NAMESPACE &
        PORT_FORWARD_PID=$!
        sleep 5
        HEALTH_URL="http://localhost:8080/health"
    fi
    
    print_status "Checking health endpoint: $HEALTH_URL"
    
    # Health check with retry
    for i in {1..10}; do
        if curl -f -s "$HEALTH_URL" > /dev/null; then
            print_status "Health check passed ✓"
            break
        else
            print_warning "Health check failed, retrying in 10 seconds... ($i/10)"
            sleep 10
        fi
        
        if [[ $i -eq 10 ]]; then
            print_error "Health check failed after 10 attempts"
            exit 1
        fi
    done
    
    # Clean up port forward
    if [[ ! -z "${PORT_FORWARD_PID:-}" ]]; then
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
}

# Main deployment flow
main() {
    print_header "DiffusionArt Gen Studio Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "Image tag: $IMAGE_TAG"
    echo ""
    
    check_tools
    configure_aws
    
    if [[ "$BUILD_IMAGE" == true ]]; then
        build_and_push
    fi
    
    if [[ "$DEPLOY_INFRASTRUCTURE" == true ]]; then
        deploy_infrastructure
    fi
    
    if [[ "$DEPLOY_KUBERNETES" == true ]]; then
        deploy_kubernetes
        health_check
    fi
    
    print_header "Deployment completed successfully! 🎉"
    
    # Show useful information
    echo ""
    echo "Useful commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl logs -f deployment/diffusion-api -n $NAMESPACE"
    echo "  kubectl describe hpa diffusion-api-hpa -n $NAMESPACE"
    echo ""
}

# Run main function
main
