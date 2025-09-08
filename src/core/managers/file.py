import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import shortuuid
from loguru import logger

from src.core.managers.platform import PlatformManager
from src.utils.contants import PROGRAM_NAME


class FileManager:
    @classmethod
    def get_resource_path(cls, relative_path: str) -> str:
        base_path: Path | str
        if hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)  # type: ignore
        else:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    @classmethod
    def get_configs_dicrectory(cls) -> str:
        if PlatformManager.is_windows():  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            configs_dir = os.path.join(app_data, PROGRAM_NAME.replace(" ", ""))
        else:  # MacOS and Linux
            configs_dir = os.path.expanduser(f"~/.{PROGRAM_NAME.casefold().replace(' ', '-')}")

        try:
            os.makedirs(configs_dir, exist_ok=True)

        except Exception as error:
            logger.exception(f"Failed to create configs directory: {error}")
            configs_dir = tempfile.gettempdir()

        return configs_dir

    @classmethod
    def get_data_directory(cls) -> str:
        dir_name = f"{PROGRAM_NAME.casefold().replace(' ', '-')}-{int(time.time())}-{shortuuid.uuid()}"

        if PlatformManager.is_windows():  # Windows
            temp_dir = os.environ.get("TEMP", os.environ.get("TMP", tempfile.gettempdir()))
            data_dir = os.path.join(temp_dir, dir_name)
        else:  # MacOS and Linux
            data_dir = os.path.join(tempfile.gettempdir(), dir_name)

        try:
            os.makedirs(data_dir, exist_ok=True)

        except Exception as error:
            logger.exception(f"Failed to create data directory: {error}")
            data_dir = tempfile.gettempdir()

        return data_dir

    @classmethod
    def cleanup_data_directory(cls, data_dir: Optional[str] = None) -> None:
        if not data_dir or not os.path.exists(data_dir):
            return

        try:
            shutil.rmtree(data_dir, ignore_errors=True)

        except Exception as error:
            logger.exception(f"Failed to cleanup data directory: {error}")
