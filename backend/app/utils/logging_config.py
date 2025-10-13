"""
Logging configuration for the Satellite Tracker application.
"""

import logging
import logging.config
import sys
from typing import Dict, Any
from pathlib import Path

from app.config import settings


class CorrelationFilter(logging.Filter):
    """
    Logging filter to add correlation ID to log records.
    """
    
    def filter(self, record):
        """Add correlation ID to log record if available."""
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = 'N/A'
        return True


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging.
    """
    
    def format(self, record):
        """Format log record with structured information."""
        # Create base log entry
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'N/A')
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'correlation_id']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        return str(log_entry)


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration based on environment settings.
    
    Returns:
        Dict containing logging configuration
    """
    
    # Determine log level
    log_level = getattr(settings, 'log_level', 'INFO').upper()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'correlation_filter': {
                '()': CorrelationFilter,
            },
        },
        'formatters': {
            'standard': {
                'format': '[{asctime}] {levelname} {name} [{correlation_id}] {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '[{asctime}] {levelname} {name} [{correlation_id}] {pathname}:{lineno} {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'structured': {
                '()': StructuredFormatter,
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'filters': ['correlation_filter'],
                'stream': sys.stdout
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filters': ['correlation_filter'],
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filters': ['correlation_filter'],
                'filename': 'logs/error.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'structured_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filters': ['correlation_filter'],
                'filename': 'logs/structured.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            'app': {
                'level': log_level,
                'handlers': ['console', 'file', 'error_file'],
                'propagate': False
            },
            'app.api': {
                'level': log_level,
                'handlers': ['console', 'file', 'structured_file'],
                'propagate': False
            },
            'app.services': {
                'level': log_level,
                'handlers': ['console', 'file', 'structured_file'],
                'propagate': False
            },
            'app.middleware': {
                'level': log_level,
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn.error': {
                'level': 'INFO',
                'handlers': ['console', 'error_file'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'sqlalchemy.engine': {
                'level': 'WARNING',
                'handlers': ['console', 'file'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'file']
        }
    }
    
    return config


def setup_logging():
    """
    Set up logging configuration for the application.
    """
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Log startup message
    logger = logging.getLogger('app')
    logger.info("Logging configuration initialized")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Performance monitoring logger
performance_logger = logging.getLogger('app.performance')

# Security logger for authentication and authorization events
security_logger = logging.getLogger('app.security')

# API logger for request/response logging
api_logger = logging.getLogger('app.api')

# External service logger for N2YO API calls
external_logger = logging.getLogger('app.external')