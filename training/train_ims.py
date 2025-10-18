"""Training script for IMS model."""
import argparse
import pickle
from pathlib import Path
from datetime import datetime
import pandas as pd
from ims.train import IMSTrainer
from core.config import settings
from core.logging import logger


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train IMS model')
    parser.add_argument('--data', type=str, required=True, help='Path to training data CSV')
    parser.add_argument('--n-clusters', type=int, default=None, help='Number of k-means clusters')
    parser.add_argument('--output', type=str, default=None, help='Output model path')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    args = parser.parse_args()
    
    # Load data
    logger.info(f"Loading training data from {args.data}")
    df = pd.read_csv(args.data, parse_dates=['ts'])
    
    logger.info(f"Loaded {len(df)} samples")
    logger.info(f"Date range: {df['ts'].min()} to {df['ts'].max()}")
    
    # Initialize trainer
    n_clusters = args.n_clusters or settings.ims_kmeans_clusters
    trainer = IMSTrainer(n_clusters=n_clusters)
    
    # Train
    metrics = trainer.train(df)
    
    # Save model
    model_id = f"ims_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    output_path = args.output or Path(settings.artifacts_dir) / f"{model_id}.pkl"
    trainer.save(model_id, str(output_path))
    
    # Print summary
    logger.info("=" * 60)
    logger.info("IMS TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Model ID: {model_id}")
    logger.info(f"Training samples: {metrics['training_samples']}")
    logger.info(f"Clusters: {metrics['n_clusters']}")
    logger.info(f"tau_fast (p{settings.ims_tau_fast_percentile}): {metrics['tau_fast']:.4f}")
    logger.info(f"tau_persist (p{settings.ims_tau_persist_percentile}): {metrics['tau_persist']:.4f}")
    logger.info(f"Mean deviation: {metrics['mean_deviation']:.4f}")
    logger.info(f"Saved to: {output_path}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
