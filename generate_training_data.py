#!/usr/bin/env python
"""CLI script to generate synthetic training data for Skadi."""
import argparse
import sys
from pathlib import Path
from training.synthetic_data_generator import SyntheticDataGenerator, generate_all_training_data
from core.logging import logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic training data for Skadi IMS/MMS models"
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./data/training_main.csv',
        help='Output CSV path (default: ./data/training_main.csv)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=168,
        help='Duration in hours (default: 168 = 1 week)'
    )
    
    parser.add_argument(
        '--tick',
        type=int,
        default=60,
        help='Tick interval in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Generate all training datasets (main, IMS, validation)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.all:
            # Generate all datasets
            logger.info("Generating all training datasets...")
            datasets = generate_all_training_data()
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ SUCCESS: All training datasets generated!")
            logger.info("=" * 60)
            logger.info(f"Main training: {datasets['main']}")
            logger.info(f"IMS training:  {datasets['ims']}")
            logger.info(f"Validation:    {datasets['validation']}")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Review data: pandas.read_csv(datasets['main'])")
            logger.info("  2. Train IMS: python -m training.train_ims --data data/training_ims.csv")
            logger.info("  3. Verify: Check artifacts/ directory for model files")
            
        else:
            # Generate single dataset
            logger.info(f"Generating single dataset: {args.output}")
            logger.info(f"Duration: {args.duration} hours, Tick: {args.tick}s, Seed: {args.seed}")
            
            generator = SyntheticDataGenerator(seed=args.seed)
            output_path = generator.generate_training_dataset(
                output_path=args.output,
                duration_hours=args.duration,
                tick_seconds=args.tick
            )
            
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"✅ SUCCESS: Dataset generated at {output_path}")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Next steps:")
            logger.info(f"  1. Review data: pandas.read_csv('{output_path}')")
            logger.info(f"  2. Train IMS: python -m training.train_ims --data {output_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
