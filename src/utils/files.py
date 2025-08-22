import os
import sys

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

    # Create directory if it doesn't exist
    os.makedirs(user_data_dir, exist_ok=True)
    return user_data_dir
