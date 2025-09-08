import logging
import os
import sys
from types import FrameType
from typing import Any, Optional, cast

from loguru import logger

LOGURU_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{process.name}</level> | "
    "<level>{thread.name}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"
    "<cyan>{line}</cyan> - <level>{message}</level>"
)

# Global flag to track if logger has been initialized
_logger_initialized = False


def _get_log_file_path() -> str:
    try:
        # Try to use the same config directory as FileManager
        from src.core.managers.file import FileManager

        config_dir = FileManager.get_configs_dicrectory()
    except ImportError:
        # Fallback to user home directory if FileManager is not available
        config_dir = os.path.expanduser("~/.fc-online")

    # Ensure directory exists
    os.makedirs(config_dir, exist_ok=True)

    return os.path.join(config_dir, "app_error.log")


def _should_log_to_file(record: Any) -> bool:
    # Log ERROR and CRITICAL levels to file
    level_name = getattr(record.get("level"), "name", "")

    # Log if it's an error/critical level or if there's an exception
    return level_name in ("ERROR", "CRITICAL") or record.get("exception") is not None


class InterceptHandler(logging.Handler):
    loglevel_mapping = {
        50: "CRITICAL",
        40: "ERROR",
        30: "WARNING",
        20: "INFO",
        10: "DEBUG",
        0: "NOTSET",
    }

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        try:
            level = logger.level(record.levelname).name

        except ValueError:
            level = str(record.levelno)

        except AttributeError:
            level = self.loglevel_mapping[record.levelno]

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def init_logger(debug: Optional[bool] = False, loguru_format: str = LOGURU_FORMAT) -> None:
    global _logger_initialized

    # Prevent multiple logger initializations
    if _logger_initialized:
        return

    # logging configuration
    logging_level = logging.DEBUG if debug else logging.INFO
    loggers = (
        "aiohttp",
        "playwright",
        "browser_use",
    )

    logging.getLogger().handlers = [InterceptHandler()]
    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.propagate = False
        logging_logger.handlers = [InterceptHandler(level=logging_level)]

    # Handle case where sys.stderr might be None (e.g., in exe files)
    sink = sys.stderr if sys.stderr is not None else sys.stdout
    if sink is None:
        # Fallback to a file if both stderr and stdout are None
        import tempfile

        log_file = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        sink = log_file.name

    # Configure multiple handlers
    handlers = [
        # Console handler for all logs
        {"sink": sink, "level": logging_level, "format": loguru_format},
        # File handler for errors and exceptions with rotation
        {
            "sink": _get_log_file_path(),
            "level": "ERROR",
            "format": loguru_format,
            "rotation": "10 MB",  # Rotate when file reaches 10MB
            "retention": "7 days",  # Keep logs for 7 days
            "compression": "zip",  # Compress old log files
            "filter": _should_log_to_file,  # Only log errors and exceptions
            "backtrace": True,  # Include full traceback for exceptions
            "diagnose": True,  # Include variable values in traceback
        },
    ]
    logger.configure(handlers=handlers)  # type: ignore

    # Mark logger as initialized
    _logger_initialized = True
