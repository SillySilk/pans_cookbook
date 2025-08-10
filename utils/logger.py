"""
Logging utilities for Pans Cookbook application.

Provides structured logging setup with proper formatting and file rotation.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys

from .config import get_config


def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up application logging with both console and file output.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR). Uses config if not provided.
        log_file: Log file path. Uses config if not provided.
    
    Returns:
        Configured logger instance
    """
    config = get_config()
    
    # Use provided values or fall back to config
    log_level = log_level or config.log_level
    log_file = log_file or config.log_file
    
    # Create logs directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger("pans_cookbook")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(file_handler)
    
    # Set up third-party library logging levels
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"pans_cookbook.{name}")


class ContextLogger:
    """Context manager for logging operations with timing"""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.log(self.level, f"Completed: {self.operation} ({duration:.2f}s)")
        else:
            self.logger.error(f"Failed: {self.operation} ({duration:.2f}s) - {exc_val}")
    
    def info(self, message: str):
        """Log info message within context"""
        self.logger.info(f"[{self.operation}] {message}")
    
    def warning(self, message: str):
        """Log warning message within context"""
        self.logger.warning(f"[{self.operation}] {message}")
    
    def error(self, message: str):
        """Log error message within context"""
        self.logger.error(f"[{self.operation}] {message}")


def log_operation(logger: logging.Logger, operation: str, level: int = logging.INFO):
    """Create a context logger for an operation"""
    return ContextLogger(logger, operation, level)