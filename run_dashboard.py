"""Launch the Skadi visualization dashboard.

This script starts the interactive dashboard showing:
- Real-time datacenter heatmaps
- Time series graphs
- IMS deviation scores
- MMS state tracking
- Optimizer actions
- Energy efficiency metrics

Usage:
    python run_dashboard.py
    
Then open browser to: http://localhost:8080
"""
import sys
import subprocess
import time
from core.logging import logger


def check_model():
    """Check if IMS model exists."""
    import glob
    model_files = glob.glob('artifacts/ims_*.pkl')
    if not model_files:
        logger.warning("=" * 60)
        logger.warning("No IMS model found!")
        logger.warning("=" * 60)
        logger.warning("Please generate training data and train a model first:")
        logger.warning("  1. python generate_training_data.py --all")
        logger.warning("  2. python -m training.train_ims --data data/training_ims.csv")
        logger.warning("")
        logger.warning("Or run with synthetic data (limited IMS functionality)")
        logger.warning("=" * 60)
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    else:
        latest = sorted(model_files)[-1]
        logger.info(f"Found IMS model: {latest}")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("SKADI VISUALIZATION DASHBOARD")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Features:")
    logger.info("  ✅ Real-time datacenter heatmaps (72 racks)")
    logger.info("  ✅ Time series graphs (temps, power, latency, throughput)")
    logger.info("  ✅ IMS deviation scores with thresholds")
    logger.info("  ✅ MMS state tracking")
    logger.info("  ✅ Optimizer action timeline")
    logger.info("  ✅ Energy efficiency gauge (J/prompt)")
    logger.info("  ✅ Demo scenarios (heat spike, overcooling)")
    logger.info("")
    
    # Check for model
    check_model()
    
    logger.info("")
    logger.info("Starting dashboard server...")
    logger.info("Open browser to: http://localhost:8080")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        # Run dashboard
        subprocess.run([
            sys.executable,
            "-m", "uvicorn",
            "viz.dashboard:app",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--reload"
        ])
    except KeyboardInterrupt:
        logger.info("\nShutting down dashboard...")
        sys.exit(0)


if __name__ == '__main__':
    main()
