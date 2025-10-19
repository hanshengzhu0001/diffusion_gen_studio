# ML-MDM Kubernetes Deployment

This directory contains the Kubernetes deployment configuration for the ML-MDM text-to-image generation service.

## Architecture

- **Horizontal Scaling**: Multiple CPU-based pods for parallel image generation
- **Load Balancing**: Automatic request distribution across pods
- **Auto-scaling**: HPA scales based on CPU and memory usage
- **Persistent Storage**: Shared model storage and output directories

## Prerequisites

1. **Kubernetes cluster** (local or cloud)
2. **kubectl** configured to access your cluster
3. **Docker** for building the container image
4. **Model files** (vis_model_64x64.pth) in the ml-mdm directory

## Quick Start

1. **Deploy the service:**
   ```bash
   ./deploy.sh
   ```

2. **Check status:**
   ```bash
   ./manage.sh status
   ```

3. **Access the service:**
   ```bash
   ./manage.sh port-forward
   ```
   Then open http://localhost:8080

## Configuration

### Resource Allocation
- **CPU**: 1-2 cores per pod
- **Memory**: 2-4GB per pod
- **Storage**: 10GB for models, 20GB for outputs

### Scaling Configuration
- **Min replicas**: 2
- **Max replicas**: 15
- **Scale triggers**: CPU >70%, Memory >80%

### Generation Parameters
- **Batch size**: 4 (conservative for CPU)
- **Inference steps**: 8
- **Guidance scale**: 3.0

## Management Commands

```bash
# Check deployment status
./manage.sh status

# Scale to 5 replicas
./manage.sh scale 5

# View logs
./manage.sh logs

# Test health
./manage.sh test

# Restart deployment
./manage.sh restart

# Delete deployment
./manage.sh delete
```

## Performance Expectations

### Single Pod Performance
- **Generation time**: ~25-30 seconds for 4 images
- **Throughput**: ~8 images/minute per pod

### Scaled Performance
- **3 pods**: ~24 images/minute
- **10 pods**: ~80 images/minute
- **15 pods**: ~120 images/minute

## Monitoring

### Key Metrics
- **CPU utilization**: Target 70%
- **Memory utilization**: Target 80%
- **Request latency**: Monitor response times
- **Pod health**: Check readiness/liveness probes

### Scaling Behavior
- **Scale up**: When CPU >70% or Memory >80%
- **Scale down**: When resources are underutilized
- **Stabilization**: 60s scale-up, 300s scale-down

## Troubleshooting

### Common Issues

1. **Pods not starting:**
   ```bash
   kubectl describe pods -l app=ml-mdm-generator
   kubectl logs -l app=ml-mdm-generator
   ```

2. **High memory usage:**
   - Reduce batch size in ConfigMap
   - Increase memory limits
   - Scale up to distribute load

3. **Slow generation:**
   - Check CPU utilization
   - Scale up if CPU is maxed
   - Monitor network latency

### Performance Tuning

1. **Optimize batch size:**
   ```bash
   kubectl edit configmap ml-mdm-config
   # Change DEFAULT_BATCH_SIZE
   ```

2. **Adjust scaling:**
   ```bash
   kubectl edit hpa ml-mdm-generator-hpa
   # Modify minReplicas/maxReplicas
   ```

## Cost Optimization

### Resource Efficiency
- **CPU**: Use burstable instances for cost savings
- **Storage**: Use SSD for better I/O performance
- **Networking**: Optimize for your cloud provider

### Scaling Strategy
- **Predictive scaling**: Scale up before peak hours
- **Cost monitoring**: Set up alerts for resource usage
- **Spot instances**: Use for non-critical workloads

## Security Considerations

1. **Network policies**: Restrict pod-to-pod communication
2. **RBAC**: Limit access to deployment resources
3. **Secrets**: Store API keys in Kubernetes secrets
4. **Image security**: Scan container images for vulnerabilities

## Next Steps

1. **Production hardening**: Add monitoring, logging, and alerting
2. **Multi-region**: Deploy across multiple availability zones
3. **GPU support**: Add GPU nodes for faster generation
4. **API gateway**: Add rate limiting and authentication
