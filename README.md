# DiffusionArt Gen Studio

A high-performance, scalable text-to-image generation platform built with PyTorch, deployed on AWS EKS with Kubernetes orchestration.

## 🎯 Project Overview

- **Multi-GPU Training**: Orchestrated text-to-image training using ml_mdm and CoreFlow pipelines
- **High-Performance Inference**: Flask backend with p95 < 5s latency for 1024x1024 images (30 steps)
- **Cloud-Native Deployment**: Kubernetes on AWS EKS with Horizontal Pod Autoscaling
- **Production-Ready**: REST API behind AWS Application Load Balancer

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │───▶│   AWS ALB       │───▶│  EKS Cluster    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                               │
                                               ├── Flask API Pods
                                               ├── HPA Controller
                                               └── Monitoring Stack
```

## 📁 Project Structure

```
diffusion-gen-studio/
├── training/                 # Multi-GPU training pipeline
│   ├── models/              # Diffusion model architectures
│   ├── data/                # Data loading and preprocessing
│   ├── pipelines/           # CoreFlow training pipelines
│   └── configs/             # Training configurations
├── inference/               # Inference service
│   ├── api/                 # Flask REST API
│   ├── models/              # Model loading and inference
│   └── optimizations/       # Performance optimizations
├── deployment/              # Kubernetes and infrastructure
│   ├── k8s/                 # Kubernetes manifests
│   ├── docker/              # Docker configurations
│   └── terraform/           # AWS infrastructure as code
├── monitoring/              # Observability stack
│   ├── prometheus/          # Metrics collection
│   ├── grafana/             # Dashboards
│   └── logging/             # Centralized logging
├── tests/                   # Test suites
└── docs/                    # Documentation
```

## 🚀 Quick Start

1. **Training Phase**
   ```bash
   # Multi-GPU training
   python training/train_diffusion.py --config configs/base_config.yaml --gpus 4
   ```

2. **Inference Service**
   ```bash
   # Local development
   python inference/api/app.py
   
   # Production deployment
   kubectl apply -f deployment/k8s/
   ```

## 📊 Performance Targets

- **Latency**: p95 < 5s for 1024x1024 images (30 steps)
- **Throughput**: Auto-scaling based on demand
- **Availability**: 99.9% uptime with Kubernetes health checks

## 🛠️ Technology Stack

- **ML Framework**: PyTorch, ml_mdm, CoreFlow
- **Backend**: Flask, Gunicorn
- **Containerization**: Docker, Kubernetes
- **Cloud**: AWS EKS, ALB, ECR
- **Monitoring**: Prometheus, Grafana, CloudWatch
- **CI/CD**: GitHub Actions, ArgoCD

## 📈 Development Roadmap

See the project board for detailed task tracking and Agile sprint planning.
