"""
Logging configuration for the DocGen application
"""

import logging
import logging.config
import sys
from datetime import datetime
import os

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs only to console
    """
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # Define log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    detailed_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
    
    # Configure handlers
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'standard',
            'stream': sys.stdout
        }
    }
    
    formatters = {
        'standard': {
            'format': log_format,
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': detailed_format,
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    }
    
    # Add file handler if log_file is specified
    if log_file:
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',  # Always log debug to file
            'formatter': 'detailed',
            'filename': log_file,
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        }
    
    # Define loggers
    loggers = {
        '': {  # Root logger
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'backend.services.pdf_generator': {
            'level': 'DEBUG',  # Always debug for PDF generation
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'backend.routers.documents': {
            'level': 'DEBUG',  # Always debug for document operations
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'playwright': {
            'level': 'WARNING',  # Reduce playwright noise
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'urllib3': {
            'level': 'WARNING',  # Reduce HTTP client noise
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        }
    }
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'handlers': handlers,
        'loggers': loggers
    }
    
    logging.config.dictConfig(logging_config)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file or 'Console only'}")


def get_pdf_logger():
    """Get a logger specifically for PDF operations"""
    return logging.getLogger('backend.services.pdf_generator')


def get_documents_logger():
    """Get a logger specifically for document operations"""
    return logging.getLogger('backend.routers.documents')