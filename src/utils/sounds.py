import time

from loguru import logger
from notifypy import Notify

from src.utils import files
from src.utils.contants import PROGRAM_NAME


def send_notification(message: str, audio_name: str, loop_count: int = 1, loop_interval: int = 1) -> None:
    try:
        notification = Notify(
            default_notification_title=PROGRAM_NAME,
            default_notification_message=message,
            default_notification_application_name=PROGRAM_NAME,
            default_notification_icon=files.get_resource_path("assets/icon.ico"),
            default_notification_audio=files.get_resource_path(f"assets/sounds/{audio_name}.wav"),
        )

        for _ in range(loop_count):
            notification.send(False)
            time.sleep(loop_interval)

    except Exception as e:
        logger.error(f"Error sending notification: {e}")
