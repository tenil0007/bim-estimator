"""
Structured Logging Module
--------------------------
Production-grade logging using Loguru with JSON formatting,
rotation, and contextual metadata.
"""

import sys
from loguru import logger
from app.config import get_settings


def setup_logging():
    """Configure application-wide logging."""
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler with color
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )

    # File handler with rotation
    logger.add(
        "logs/bim_estimator_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
    )

    logger.info(f"Logging initialized | level={settings.log_level}")
    return logger


def get_logger(name: str = "bim_estimator"):
    """Get a contextualized logger instance."""
    return logger.bind(module=name)
