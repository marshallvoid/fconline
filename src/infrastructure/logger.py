import logging
import sys
from types import FrameType
from typing import Optional, cast

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

    handlers = [{"sink": sink, "level": logging_level, "format": loguru_format}]
    logger.configure(handlers=handlers)  # type: ignore

    # Mark logger as initialized
    _logger_initialized = True


# Auto-initialize logger on module import with default settings
init_logger()
