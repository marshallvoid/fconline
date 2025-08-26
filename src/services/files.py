import json
import os
import shutil
import sys
import tempfile
import time
from typing import Dict, List, Optional

import shortuuid
from deepmerge import always_merger
from loguru import logger

from src.services.jackpot_history import EventTimeline
from src.services.platforms import PlatformManager
from src.utils.contants import PROGRAM_NAME


class FileManager:
    @classmethod
    def get_resource_path(cls, relative_path: str) -> str:
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    @classmethod
    def get_configs_dicrectory(cls) -> str:
        if PlatformManager.is_windows():  # Windows
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            configs_dir = os.path.join(app_data, PROGRAM_NAME.replace(" ", ""))
        else:  # MacOS and Linux
            configs_dir = os.path.expanduser(f"~/.{PROGRAM_NAME.lower().replace(' ', '-')}")

        try:
            os.makedirs(configs_dir, exist_ok=True)

        except Exception as error:
            logger.error(f"Failed to create configs directory: {error}")
            configs_dir = tempfile.gettempdir()

        return configs_dir

    @classmethod
    def get_data_directory(cls) -> str:
        dir_name = f"{PROGRAM_NAME.lower().replace(' ', '-')}-{int(time.time())}-{shortuuid.uuid()}"

        if PlatformManager.is_windows():  # Windows
            temp_dir = os.environ.get("TEMP", os.environ.get("TMP", tempfile.gettempdir()))
            data_dir = os.path.join(temp_dir, dir_name)
        else:  # MacOS and Linux
            data_dir = os.path.join(tempfile.gettempdir(), dir_name)

        try:
            os.makedirs(data_dir, exist_ok=True)

        except Exception as error:
            logger.error(f"Failed to create data directory: {error}")
            data_dir = tempfile.gettempdir()

        return data_dir

    @classmethod
    def cleanup_data_directory(cls, data_dir: Optional[str] = None) -> None:
        if not data_dir or not os.path.exists(data_dir):
            return

        try:
            shutil.rmtree(data_dir, ignore_errors=True)

        except Exception as error:
            logger.error(f"Failed to cleanup data directory: {error}")

    @classmethod
    def save_jackpot_history(cls, data: Dict[str, List[EventTimeline]]) -> None:
        try:
            # Get the jackpot history file path
            config_dir = cls.get_configs_dicrectory()
            history_file = os.path.join(config_dir, "jackpot_history.json")

            # Load existing history or create new
            history_data: Dict[str, List[EventTimeline]] = {}
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        history_data = json.load(f)

                except (json.JSONDecodeError, IOError) as error:
                    logger.warning(f"Failed to load existing jackpot history: {error}")
                    history_data = {}

            history_data = always_merger.merge(history_data, data)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=4, ensure_ascii=False)

        except Exception as error:
            logger.error(f"Failed to save jackpot history: {error}")
