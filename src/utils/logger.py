import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, '')}{log_message}{self.RESET}"


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    # File handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # File gets all messages
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


class LoggerContext:
    """Context manager for temporary logging configuration"""
    
    def __init__(self, log_level: str = 'INFO', log_file: Optional[str] = None):
        self.log_level = log_level
        self.log_file = log_file
        self.original_handlers = []
        self.original_level = None
    
    def __enter__(self):
        root_logger = logging.getLogger()
        self.original_level = root_logger.level
        self.original_handlers = root_logger.handlers.copy()
        
        setup_logging(self.log_level, self.log_file)
        return root_logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.handlers.extend(self.original_handlers)
        root_logger.setLevel(self.original_level)


class TimedLogger:
    """Logger that tracks execution time"""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration = end_time - self.start_time
        
        if exc_type is None:
            self.logger.log(self.level, f"Completed {self.operation} in {duration}")
        else:
            self.logger.error(f"Failed {self.operation} after {duration}: {exc_val}")


def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        # Create argument string for logging
        arg_strs = []
        if args:
            arg_strs.extend([str(arg) for arg in args[:3]])  # Limit to first 3 args
            if len(args) > 3:
                arg_strs.append(f"... (+{len(args)-3} more)")
        
        if kwargs:
            kwarg_strs = [f"{k}={v}" for k, v in list(kwargs.items())[:2]]  # Limit to first 2 kwargs
            if len(kwargs) > 2:
                kwarg_strs.append(f"... (+{len(kwargs)-2} more)")
            arg_strs.extend(kwarg_strs)
        
        args_str = ", ".join(arg_strs)
        logger.debug(f"Calling {func.__name__}({args_str})")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    
    return wrapper