import os
import shutil
import sys
import tempfile
import time
from typing import Optional

import shortuuid
from loguru import logger

from src.utils.platforms import PlatformManager


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_config_data_directory() -> str:
    if PlatformManager.is_windows():  # Windows
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        user_data_dir = os.path.join(app_data, "FCOnlineAutomation")
    else:  # MacOS and Linux
        user_data_dir = os.path.expanduser("~/.fconline-automation")

    try:
        os.makedirs(user_data_dir, exist_ok=True)

    except Exception as error:
        logger.error(f"Failed to create directory: {error}")

    return user_data_dir


def get_user_data_directory() -> str:
    timestamp, unique_id = int(time.time()), shortuuid.uuid()
    dir_name = f"fconline-automation-{timestamp}-{unique_id}"

    if PlatformManager.is_windows():  # Windows
        temp_dir = os.environ.get("TEMP", os.environ.get("TMP", tempfile.gettempdir()))
        user_data_dir = os.path.join(temp_dir, dir_name)
    else:  # MacOS and Linux
        user_data_dir = os.path.join(tempfile.gettempdir(), dir_name)

    try:
        os.makedirs(user_data_dir, exist_ok=True)

    except Exception as error:
        logger.error(f"Failed to create user data directory: {error}")

        fallback_dir = os.path.join(tempfile.gettempdir(), f"fconline-automation-fallback-{unique_id}")

        try:
            os.makedirs(fallback_dir, exist_ok=True)
            user_data_dir = fallback_dir

        except Exception as fallback_error:
            logger.error(f"Failed to create fallback directory: {fallback_error}")
            user_data_dir = tempfile.gettempdir()

    return user_data_dir


def cleanup_user_data_directory(user_data_dir: Optional[str] = None) -> None:
    if not user_data_dir or not os.path.exists(user_data_dir):
        return

    try:
        shutil.rmtree(user_data_dir, ignore_errors=True)

    except Exception as error:
        logger.error(f"Failed to cleanup user data directory: {error}")
