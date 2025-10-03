# ruff: noqa: E501
import logging
import os
import sys
from types import FrameType
from typing import TYPE_CHECKING, Optional, TextIO, cast

from loguru import logger

from src.core.managers.file import file_mgr

if TYPE_CHECKING:
    from loguru import Record

LOGURU_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{process.name}</level> | "
    "<level>{thread.name}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"
    "<cyan>{line}</cyan> - <level>{message}</level>"
)


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


def is_loggable_error(record: "Record") -> bool:
    return record["level"].name in ("ERROR", "CRITICAL") or record["exception"] is not None


def init_logger(debug: Optional[bool] = False) -> None:
    # logging configuration
    logging_level = logging.DEBUG if debug else logging.INFO
    loggers = ("aiohttp", "playwright", "browser_use")

    logging.getLogger().handlers = [InterceptHandler()]
    for logger_name in loggers:
        logging_logger = logging.getLogger(name=logger_name)
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
    logger.configure(
        handlers=[
            # Console handler for all logs
            {
                "sink": cast(TextIO, sink),
                "level": logging_level,
                "format": LOGURU_FORMAT,
                "backtrace": True,  # Include full traceback for exceptions
            },
            # Discord notification handler for errors
            # {
            #     "sink": notifier_mgr.discord_error_notifier,
            #     "level": "ERROR",
            #     "filter": lambda record: not record["extra"].get("apprise", False) and is_loggable_error(record=record),
            #     "backtrace": True,  # Include full traceback for exceptions
            # },
            # File handler for errors and exceptions with rotation
            {
                "sink": os.path.join(file_mgr.get_configs_directory(), "app_error.log"),
                "level": "ERROR",
                "format": LOGURU_FORMAT,
                "filter": is_loggable_error,  # Only log errors and exceptions
                "backtrace": True,  # Include full traceback for exceptions
                "diagnose": True,  # Include variable values in traceback
                "rotation": "10 MB",  # Rotate when file reaches 10MB
                "retention": "7 days",  # Keep logs for 7 days
                "compression": "zip",  # Compress old log files
            },
        ]
    )


original_error = logger.error
logger.error = lambda *args, **kwargs: logger.opt(exception=True).log("ERROR", *args, **kwargs)
