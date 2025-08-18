import time

from notifypy import Notify

from src.utils import files

_notification = Notify(
    default_notification_title="FC Online Automation Tool",
    default_application_name="FC Online Automation Tool",
    default_notification_application_name="FC Online Automation Tool",
    default_notification_icon=files.resource_path("assets/icon.ico"),
    default_notification_audio=files.resource_path("assets/sounds/notification.wav"),
)


def send_notification(message: str, loop_count: int = 1, loop_interval: int = 1) -> None:
    _notification.message = message

    for _ in range(loop_count):
        _notification.send(False)
        time.sleep(loop_interval)
