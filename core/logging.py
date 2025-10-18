"""Centralized logging configuration."""
import logging
import sys
from typing import Optional
from core.config import settings


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """Configure application-wide logging.
    
    Args:
        log_level: Override log level from settings
        
    Returns:
        Configured logger instance
    """
    level = log_level or settings.log_level
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Get logger
    logger = logging.getLogger("skadi")
    logger.setLevel(getattr(logging, level))
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    return logger


# Global logger instance
logger = setup_logging()
