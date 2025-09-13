# DiffusionArt Gen Studio - Deployment Guide

This guide covers deploying DiffusionArt Gen Studio to production on AWS EKS with Kubernetes orchestration.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Users/Apps    │───▶│   AWS ALB       │───▶│  EKS Cluster    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                               │
                                               ├── Flask API Pods
                                               ├── Redis Cache
                                               ├── HPA Controller
                                               └── Monitoring Stack
```

## 📋 Prerequisites

### Required Tools
- AWS CLI v2
- Docker
- kubectl
- Terraform >= 1.0
- Helm (optional, for monitoring stack)

### AWS Permissions
Your AWS user/role needs permissions for:
- EKS cluster management
- ECR repository access
- VPC and networking
- IAM role management
- CloudWatch logs
- Application Load Balancer

## 🚀 Quick Start

### 1. Setup Development Environment
```bash
# Clone and setup
git clone <repository>
cd diffusion-gen-studio
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Configure AWS
```bash
aws configure
# Enter your AWS credentials and region
```

### 3. Deploy Everything
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh -e production -t v1.0.0 -a
```

## 📖 Detailed Deployment Steps

### Step 1: Infrastructure Deployment

Deploy AWS infrastructure using Terraform:

```bash
cd deployment/terraform

# Initialize Terraform
terraform init

# Create production workspace
terraform workspace new production

# Review and apply
terraform plan -var="environment=production"
terraform apply
```

This creates:
- VPC with public/private subnets
- EKS cluster with GPU node groups
- ECR repository
- Application Load Balancer
- Security groups and IAM roles

### Step 2: Build and Push Docker Image

```bash
# Get ECR login
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# Build and tag image
docker build -f deployment/docker/Dockerfile -t diffusion-gen-studio:v1.0.0 .
docker tag diffusion-gen-studio:v1.0.0 <account-id>.dkr.ecr.us-west-2.amazonaws.com/diffusion-gen-studio:v1.0.0

# Push to ECR
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/diffusion-gen-studio:v1.0.0
```

### Step 3: Deploy to Kubernetes

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name diffusion-cluster

# Deploy application
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/configmap.yaml
kubectl apply -f deployment/k8s/redis.yaml
kubectl apply -f deployment/k8s/deployment.yaml
kubectl apply -f deployment/k8s/hpa.yaml
kubectl apply -f deployment/k8s/ingress.yaml

# Verify deployment
kubectl get pods -n diffusion-gen-studio
kubectl rollout status deployment/diffusion-api -n diffusion-gen-studio
```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `deployment/k8s/configmap.yaml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_BATCH_SIZE` | Maximum batch size for inference | `4` |
| `DEFAULT_STEPS` | Default inference steps | `30` |
| `MAX_STEPS` | Maximum allowed inference steps | `50` |
| `MAX_RESOLUTION` | Maximum image resolution | `1024` |
| `MODEL_CACHE_DIR` | Directory for model caching | `/app/cache` |

### Resource Limits

GPU node configuration in `deployment/k8s/deployment.yaml`:

```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "2"
    nvidia.com/gpu: 1
  limits:
    memory: "16Gi"
    cpu: "4"
    nvidia.com/gpu: 1
```

### Auto-scaling Configuration

HPA settings in `deployment/k8s/hpa.yaml`:

- **Min replicas**: 2
- **Max replicas**: 10
- **CPU target**: 70%
- **Memory target**: 80%
- **Custom metric**: Active requests < 5 per pod

## 📊 Monitoring and Observability

### Health Checks

The application provides several health endpoints:

- `GET /health` - Basic health check
- `GET /ready` - Readiness probe (checks model loading)
- `GET /metrics` - Prometheus metrics
- `GET /stats` - Detailed system statistics

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 120
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 5000
  initialDelaySeconds: 60
  periodSeconds: 10
```

### Metrics Collection

Key metrics exposed at `/metrics`:

- `images_generated_total` - Total images generated
- `image_generation_duration_seconds` - Generation latency histogram
- `generation_errors_total` - Error count
- `cache_hits_total` - Cache hit count
- `gpu_memory_usage_bytes` - GPU memory usage

## 🔧 Performance Optimization

### GPU Optimization

The deployment is optimized for NVIDIA GPUs:

- **Mixed precision training**: FP16 for faster inference
- **Attention slicing**: Memory-efficient attention computation
- **Model compilation**: PyTorch 2.0 compilation for speed
- **xFormers**: Memory-efficient attention implementation

### Caching Strategy

- **Redis caching**: Generated images cached for 1 hour
- **Model caching**: Models cached in persistent volumes
- **HuggingFace cache**: Shared cache directory for model downloads

### Network Optimization

- **ALB configuration**: HTTP/2 enabled, connection pooling
- **Kubernetes networking**: CNI optimized for GPU workloads
- **Service mesh**: Optional Istio for advanced traffic management

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

The `.github/workflows/ci-cd.yml` implements:

1. **Testing**: Unit tests, linting, security scanning
2. **Building**: Docker image build and push to ECR
3. **Staging**: Automatic deployment to staging environment
4. **Production**: Manual deployment on release tags

### Deployment Environments

- **Development**: Local development with port-forwarding
- **Staging**: Automatic deployment from `develop` branch
- **Production**: Manual deployment from release tags

## 🛡️ Security

### Container Security

- **Non-root user**: Application runs as non-root user
- **Minimal base image**: NVIDIA CUDA base with minimal packages
- **Security scanning**: Trivy vulnerability scanning in CI
- **Read-only filesystem**: Where possible

### Network Security

- **Security groups**: Restrictive ingress/egress rules
- **WAF integration**: AWS WAF for API protection
- **TLS termination**: SSL/TLS at load balancer
- **Private subnets**: Application pods in private subnets

### Secrets Management

```bash
# Create secrets for sensitive data
kubectl create secret generic diffusion-secrets \
  --from-literal=redis-password=<password> \
  --from-literal=api-key=<api-key> \
  -n diffusion-gen-studio
```

## 📈 Scaling

### Horizontal Pod Autoscaling

Automatic scaling based on:
- CPU utilization (70%)
- Memory utilization (80%)
- Active requests per pod (< 5)

### Cluster Autoscaling

EKS cluster autoscaler automatically scales node groups:
- **General nodes**: m5.large to m5.xlarge (SPOT instances)
- **GPU nodes**: g4dn.xlarge to g4dn.2xlarge (On-Demand)

### Performance Targets

- **Latency**: p95 < 5s for 1024x1024 images (30 steps)
- **Throughput**: Auto-scaling to handle traffic spikes
- **Availability**: 99.9% uptime with health checks

## 🔍 Troubleshooting

### Common Issues

1. **Pod stuck in Pending**
   ```bash
   kubectl describe pod <pod-name> -n diffusion-gen-studio
   # Check for resource constraints or node selector issues
   ```

2. **Model loading failures**
   ```bash
   kubectl logs deployment/diffusion-api -n diffusion-gen-studio
   # Check HuggingFace token and network connectivity
   ```

3. **High memory usage**
   ```bash
   kubectl top pods -n diffusion-gen-studio
   # Monitor GPU memory usage and adjust batch sizes
   ```

### Debug Commands

```bash
# Check pod status
kubectl get pods -n diffusion-gen-studio -o wide

# View logs
kubectl logs -f deployment/diffusion-api -n diffusion-gen-studio

# Port forward for local testing
kubectl port-forward svc/diffusion-api-service 5000:80 -n diffusion-gen-studio

# Check HPA status
kubectl describe hpa diffusion-api-hpa -n diffusion-gen-studio

# Exec into pod
kubectl exec -it deployment/diffusion-api -n diffusion-gen-studio -- /bin/bash
```

## 📞 Support

For deployment issues:

1. Check the logs: `kubectl logs deployment/diffusion-api -n diffusion-gen-studio`
2. Verify health endpoints: `curl http://<endpoint>/health`
3. Review resource usage: `kubectl top pods -n diffusion-gen-studio`
4. Check HPA status: `kubectl get hpa -n diffusion-gen-studio`

For infrastructure issues, check the Terraform state and AWS console for resource status.
