import logging
import sys

from agents.common.config import SETTINGS
from agents.common.otel import OtelLogging


class Log:
    """Utility class for unified logging configuration and output"""

    @staticmethod
    def init():
        """Initialize logging configuration"""
        # Define unified log format with timestamp, level, filename, class name, function and line number
        if SETTINGS.OTEL_ENABLED:
            OtelLogging.init()
            log_format = f"%(asctime)s [%(levelname)s] [tid=%(otelTraceID)s sid=%(otelSpanID)s] %(filename)s:%(funcName)s:%(lineno)s - %(message)s"
        else:
            log_format = (
                "%(asctime)s [%(levelname)s] "
                "%(filename)s:%(name)s.%(funcName)s:%(lineno)d - "
                "%(message)s"
            )

        # Configure date format
        date_format = "%Y-%m-%d %H:%M:%S"

        # Create formatter
        formatter = logging.Formatter(
            fmt=log_format,
            datefmt=date_format,
        )

        # Clear existing handlers
        logging.root.handlers = []

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(SETTINGS.LOG_LEVEL)
        console_handler.setFormatter(formatter)

        # Configure root logger
        logging.root.setLevel(SETTINGS.LOG_LEVEL)
        logging.root.addHandler(console_handler)
