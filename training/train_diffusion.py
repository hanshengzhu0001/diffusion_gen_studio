"""
Multi-GPU Diffusion Model Training Pipeline
Uses ml_mdm and CoreFlow for orchestrated distributed training.
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
import wandb

# CoreFlow imports (placeholder - would be actual imports)
try:
    from coreflow import Pipeline, Stage, DataFlow
    from coreflow.distributed import MultiGPURunner
except ImportError:
    print("CoreFlow not available - using placeholder implementation")
    # Placeholder classes for demo
    class Pipeline: pass
    class Stage: pass
    class DataFlow: pass
    class MultiGPURunner: pass

# ml_mdm imports (placeholder - would be actual imports)
try:
    from ml_mdm import MultiModalDiffusionModel, TrainingConfig
    from ml_mdm.schedulers import CosineAnnealingLR
except ImportError:
    print("ml_mdm not available - using placeholder implementation")
    # Placeholder classes for demo
    class MultiModalDiffusionModel: pass
    class TrainingConfig: pass
    class CosineAnnealingLR: pass

from models.diffusion_architecture import UNetModel
from data.dataset_loader import TextImageDataset
from pipelines.training_pipeline import DiffusionTrainingPipeline

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DistributedTrainer:
    """Distributed training orchestrator for diffusion models."""
    
    def __init__(self, config: Dict[str, Any], rank: int, world_size: int):
        self.config = config
        self.rank = rank
        self.world_size = world_size
        self.device = torch.device(f"cuda:{rank}")
        
        # Initialize distributed training
        self._setup_distributed()
        
        # Initialize model and data
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.train_loader = None
        self.val_loader = None
        
        # CoreFlow pipeline
        self.pipeline = None
        
        # Metrics tracking
        self.global_step = 0
        self.epoch = 0
        
    def _setup_distributed(self):
        """Setup distributed training environment."""
        os.environ['MASTER_ADDR'] = 'localhost'
        os.environ['MASTER_PORT'] = '12355'
        
        dist.init_process_group(
            backend='nccl',
            rank=self.rank,
            world_size=self.world_size
        )
        
        torch.cuda.set_device(self.rank)
        
        if self.rank == 0:
            logger.info(f"Initialized distributed training with {self.world_size} GPUs")
    
    def setup_model(self):
        """Initialize and setup the diffusion model."""
        model_config = self.config['model']
        
        # Create model (placeholder - would use actual ml_mdm)
        self.model = UNetModel(
            in_channels=model_config['channels'],
            out_channels=model_config['channels'],
            model_channels=128,
            attention_resolutions=[4, 2, 1],
            num_res_blocks=2,
            channel_mult=[1, 2, 4, 4],
            num_heads=model_config['attention_heads'],
            use_spatial_transformer=True,
            context_dim=model_config['cross_attention_dim']
        )
        
        # Move to device and wrap with DDP
        self.model = self.model.to(self.device)
        self.model = DDP(self.model, device_ids=[self.rank])
        
        if self.rank == 0:
            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(f"Model initialized with {total_params:,} parameters")
    
    def setup_optimizer(self):
        """Setup optimizer and scheduler."""
        opt_config = self.config['optimizer']
        train_config = self.config['training']
        
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=train_config['learning_rate'],
            betas=(opt_config['beta1'], opt_config['beta2']),
            weight_decay=opt_config['weight_decay'],
            eps=opt_config['eps']
        )
        
        # Learning rate scheduler
        if train_config['lr_scheduler'] == 'cosine_with_restarts':
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
                self.optimizer,
                T_0=1000,
                T_mult=2,
                eta_min=1e-6
            )
        
        if self.rank == 0:
            logger.info(f"Optimizer initialized: {opt_config['type']}")
    
    def setup_data(self):
        """Setup data loaders."""
        data_config = self.config['data']
        
        # Training dataset
        train_dataset = TextImageDataset(
            data_dir=data_config['train_data_dir'],
            resolution=data_config['resolution'],
            center_crop=data_config['center_crop'],
            random_flip=data_config['random_flip']
        )
        
        # Distributed sampler
        train_sampler = torch.utils.data.distributed.DistributedSampler(
            train_dataset,
            num_replicas=self.world_size,
            rank=self.rank,
            shuffle=True
        )
        
        self.train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=self.config['training']['batch_size'],
            sampler=train_sampler,
            num_workers=data_config['num_workers'],
            pin_memory=data_config['pin_memory'],
            drop_last=True
        )
        
        # Validation dataset
        val_dataset = TextImageDataset(
            data_dir=data_config['val_data_dir'],
            resolution=data_config['resolution'],
            center_crop=True,
            random_flip=False
        )
        
        val_sampler = torch.utils.data.distributed.DistributedSampler(
            val_dataset,
            num_replicas=self.world_size,
            rank=self.rank,
            shuffle=False
        )
        
        self.val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=self.config['training']['batch_size'],
            sampler=val_sampler,
            num_workers=data_config['num_workers'],
            pin_memory=data_config['pin_memory'],
            drop_last=False
        )
        
        if self.rank == 0:
            logger.info(f"Data loaders initialized - Train: {len(train_dataset)}, Val: {len(val_dataset)}")
    
    def setup_coreflow_pipeline(self):
        """Setup CoreFlow training pipeline."""
        coreflow_config = self.config['coreflow']
        
        # Define pipeline stages (placeholder implementation)
        data_stage = Stage(
            name="data_loading",
            function=self._data_loading_stage,
            inputs=["batch_data"],
            outputs=["processed_batch"]
        )
        
        forward_stage = Stage(
            name="forward_pass",
            function=self._forward_stage,
            inputs=["processed_batch"],
            outputs=["loss", "metrics"]
        )
        
        backward_stage = Stage(
            name="backward_pass",
            function=self._backward_stage,
            inputs=["loss"],
            outputs=["gradients"]
        )
        
        # Create pipeline
        self.pipeline = Pipeline(
            name=coreflow_config['pipeline_name'],
            stages=[data_stage, forward_stage, backward_stage],
            enable_profiling=coreflow_config['enable_profiling']
        )
        
        if self.rank == 0:
            logger.info("CoreFlow pipeline initialized")
    
    def _data_loading_stage(self, batch_data):
        """Data loading and preprocessing stage."""
        # Placeholder implementation
        return {"processed_batch": batch_data}
    
    def _forward_stage(self, processed_batch):
        """Forward pass stage."""
        # Placeholder implementation
        batch = processed_batch["processed_batch"]
        
        # Forward pass through model
        with torch.cuda.amp.autocast(enabled=self.config['training']['mixed_precision'] == 'fp16'):
            loss = self.model(batch)
        
        return {"loss": loss, "metrics": {"train_loss": loss.item()}}
    
    def _backward_stage(self, loss):
        """Backward pass and optimization stage."""
        # Placeholder implementation
        loss_tensor = loss["loss"]
        
        # Backward pass
        self.optimizer.zero_grad()
        loss_tensor.backward()
        
        # Gradient clipping
        if self.config['training']['max_grad_norm'] > 0:
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config['training']['max_grad_norm']
            )
        
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        
        return {"gradients": "computed"}
    
    def train_epoch(self):
        """Train for one epoch."""
        self.model.train()
        epoch_loss = 0.0
        num_batches = len(self.train_loader)
        
        for batch_idx, batch in enumerate(self.train_loader):
            # Move batch to device
            batch = {k: v.to(self.device) if torch.is_tensor(v) else v for k, v in batch.items()}
            
            # Run CoreFlow pipeline
            if self.pipeline:
                results = self.pipeline.run(batch_data=batch)
                loss = results["loss"]
                metrics = results["metrics"]
            else:
                # Fallback to direct training
                with torch.cuda.amp.autocast(enabled=self.config['training']['mixed_precision'] == 'fp16'):
                    loss = self.model(batch)
                
                self.optimizer.zero_grad()
                loss.backward()
                
                if self.config['training']['max_grad_norm'] > 0:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.config['training']['max_grad_norm']
                    )
                
                self.optimizer.step()
                if self.scheduler:
                    self.scheduler.step()
                
                metrics = {"train_loss": loss.item()}
            
            epoch_loss += metrics["train_loss"]
            self.global_step += 1
            
            # Logging
            if self.rank == 0 and batch_idx % self.config['logging']['log_interval'] == 0:
                logger.info(
                    f"Epoch {self.epoch} [{batch_idx}/{num_batches}] "
                    f"Loss: {metrics['train_loss']:.4f} "
                    f"LR: {self.optimizer.param_groups[0]['lr']:.6f}"
                )
                
                # WandB logging
                if wandb.run:
                    wandb.log({
                        "train_loss": metrics["train_loss"],
                        "learning_rate": self.optimizer.param_groups[0]["lr"],
                        "global_step": self.global_step,
                        "epoch": self.epoch
                    })
        
        return epoch_loss / num_batches
    
    def validate(self):
        """Run validation."""
        self.model.eval()
        val_loss = 0.0
        num_batches = len(self.val_loader)
        
        with torch.no_grad():
            for batch in self.val_loader:
                batch = {k: v.to(self.device) if torch.is_tensor(v) else v for k, v in batch.items()}
                
                with torch.cuda.amp.autocast(enabled=self.config['training']['mixed_precision'] == 'fp16'):
                    loss = self.model(batch)
                
                val_loss += loss.item()
        
        val_loss /= num_batches
        
        if self.rank == 0:
            logger.info(f"Validation Loss: {val_loss:.4f}")
            
            if wandb.run:
                wandb.log({
                    "val_loss": val_loss,
                    "epoch": self.epoch
                })
        
        return val_loss
    
    def save_checkpoint(self, val_loss: float):
        """Save model checkpoint."""
        if self.rank != 0:
            return
        
        checkpoint_dir = Path(self.config['checkpointing']['save_dir'])
        checkpoint_dir.mkdir(exist_ok=True)
        
        checkpoint = {
            'epoch': self.epoch,
            'global_step': self.global_step,
            'model_state_dict': self.model.module.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'val_loss': val_loss,
            'config': self.config
        }
        
        # Save latest checkpoint
        checkpoint_path = checkpoint_dir / f'checkpoint_epoch_{self.epoch}.pt'
        torch.save(checkpoint, checkpoint_path)
        
        # Save best checkpoint
        if not hasattr(self, 'best_val_loss') or val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            best_path = checkpoint_dir / 'best_model.pt'
            torch.save(checkpoint, best_path)
            logger.info(f"New best model saved with val_loss: {val_loss:.4f}")
        
        logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    def train(self):
        """Main training loop."""
        if self.rank == 0:
            logger.info("Starting training...")
        
        for epoch in range(self.config['training']['num_epochs']):
            self.epoch = epoch
            
            # Train
            train_loss = self.train_epoch()
            
            # Validate
            if epoch % (self.config['logging']['eval_interval'] // len(self.train_loader)) == 0:
                val_loss = self.validate()
                
                # Save checkpoint
                if epoch % (self.config['logging']['save_interval'] // len(self.train_loader)) == 0:
                    self.save_checkpoint(val_loss)
        
        if self.rank == 0:
            logger.info("Training completed!")

def main():
    parser = argparse.ArgumentParser(description='Multi-GPU Diffusion Training')
    parser.add_argument('--config', type=str, required=True, help='Training configuration file')
    parser.add_argument('--gpus', type=int, default=1, help='Number of GPUs to use')
    parser.add_argument('--resume', type=str, help='Resume from checkpoint')
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize WandB (rank 0 only)
    if int(os.environ.get('LOCAL_RANK', 0)) == 0:
        wandb.init(
            project=config['logging']['wandb_project'],
            config=config,
            name=f"diffusion_training_{config['model']['name']}"
        )
    
    # Launch distributed training
    if args.gpus > 1:
        torch.multiprocessing.spawn(
            train_worker,
            args=(args.gpus, config, args.resume),
            nprocs=args.gpus
        )
    else:
        train_worker(0, 1, config, args.resume)

def train_worker(rank: int, world_size: int, config: Dict[str, Any], resume_path: Optional[str]):
    """Worker function for distributed training."""
    trainer = DistributedTrainer(config, rank, world_size)
    
    # Setup components
    trainer.setup_model()
    trainer.setup_optimizer()
    trainer.setup_data()
    trainer.setup_coreflow_pipeline()
    
    # Resume from checkpoint if specified
    if resume_path and os.path.exists(resume_path):
        checkpoint = torch.load(resume_path, map_location=trainer.device)
        trainer.model.load_state_dict(checkpoint['model_state_dict'])
        trainer.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        if trainer.scheduler and checkpoint['scheduler_state_dict']:
            trainer.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        trainer.epoch = checkpoint['epoch']
        trainer.global_step = checkpoint['global_step']
        
        if rank == 0:
            logger.info(f"Resumed training from epoch {trainer.epoch}")
    
    # Start training
    trainer.train()
    
    # Cleanup
    dist.destroy_process_group()

if __name__ == '__main__':
    main()
