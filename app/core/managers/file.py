import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import shortuuid
from loguru import logger

from app.core.managers.platform import platform_mgr
from app.core.settings import settings
from app.utils.decorators.singleton import singleton


@singleton
class FileManager:
    def get_resource_path(self, relative_path: str) -> str:
        base_path: Path | str
        if hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def get_configs_directory(self) -> str:
        if platform_mgr.is_windows:  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            configs_dir = os.path.join(app_data, settings.program_name.replace(" ", ""))
        else:  # MacOS and Linux
            configs_dir = os.path.expanduser(f"~/.{settings.program_name.casefold().replace(' ', '-')}")

        try:
            os.makedirs(configs_dir, exist_ok=True)

        except Exception as error:
            logger.exception(f"Failed to create configs directory: {error}")
            configs_dir = tempfile.gettempdir()

        return configs_dir

    def get_data_directory(self) -> str:
        dir_name = f"{settings.program_name.casefold().replace(' ', '-')}-{int(time.time())}-{shortuuid.uuid()}"

        if platform_mgr.is_windows:  # Windows
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

    def cleanup_data_directory(self, data_dir: Optional[str] = None) -> None:
        if not data_dir or not os.path.exists(data_dir):
            return

        try:
            shutil.rmtree(data_dir, ignore_errors=True)

        except Exception as error:
            logger.exception(f"Failed to cleanup data directory: {error}")


file_mgr = FileManager()
