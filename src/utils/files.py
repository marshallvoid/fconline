import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional, TypedDict

import shortuuid
from loguru import logger

from src.utils.platforms import PlatformManager


class HistoryEntry(TypedDict):
    event_timestamp: str
    event_kind: str
    event_value: str


class FileManager:
    JACKPOT_DUPLICATE_WINDOW_SECONDS: int = 60

    @classmethod
    def get_resource_path(cls, relative_path: str) -> str:
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    @classmethod
    def get_config_data_directory(cls) -> str:
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

    @classmethod
    def get_user_data_directory(cls) -> str:
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

    @classmethod
    def cleanup_user_data_directory(cls, user_data_dir: Optional[str] = None) -> None:
        if not user_data_dir or not os.path.exists(user_data_dir):
            return

        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)

        except Exception as error:
            logger.error(f"Failed to cleanup user data directory: {error}")

    @classmethod
    def save_jackpot_history(
        cls,
        event_name: str,
        event_kind: str,
        event_value: str,
        event_timestamp: Optional[str] = None,
    ) -> None:
        try:
            if event_timestamp is None:
                event_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create history entry
            history_entry: HistoryEntry = {
                "event_timestamp": event_timestamp,
                "event_kind": event_kind,
                "event_value": str(event_value),
            }

            # Get the jackpot history file path
            config_dir = cls.get_config_data_directory()
            history_file = os.path.join(config_dir, "jackpot_history.json")

            # Load existing history or create new
            history_data: Dict[str, List[HistoryEntry]] = {}
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except (json.JSONDecodeError, IOError) as error:
                    logger.warning(f"Failed to load existing jackpot history: {error}")
                    history_data = {}

            # Initialize event list if it doesn't exist
            if event_name not in history_data:
                history_data[event_name] = []

            # Duplicate filter: same event_value within a short time window
            # Assumption: two identical event_value entries can't occur within this window
            try:
                new_dt = datetime.strptime(event_timestamp, "%Y-%m-%d %H:%M:%S")
            except Exception:
                new_dt = datetime.now()

            is_duplicate = False
            for entry in reversed(history_data[event_name]):
                if str(entry["event_value"]) != str(event_value):
                    continue

                try:
                    old_ts = str(entry["event_timestamp"])
                    old_dt = datetime.strptime(old_ts, "%Y-%m-%d %H:%M:%S")

                except Exception:
                    # If cannot parse, treat as non-duplicate and continue search
                    continue

                # If the prior identical value is within the window, skip as duplicate
                if abs((new_dt - old_dt).total_seconds()) <= cls.JACKPOT_DUPLICATE_WINDOW_SECONDS:
                    is_duplicate = True

                break

            # Only append if not duplicate in the time window
            if not is_duplicate:
                history_data[event_name].append(history_entry)

                # Save updated history back to file
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, indent=3, ensure_ascii=False)

        except Exception as error:
            logger.error(f"Failed to save jackpot history: {error}")
