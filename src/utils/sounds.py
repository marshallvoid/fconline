import time

from notifypy import Notify

from src.utils import files

_notification = Notify(
    default_notification_title="FC Online Automation Tool",
    default_application_name="FC Online Automation Tool",
    default_notification_application_name="FC Online Automation Tool",
    default_notification_icon=files.resource_path("assets/icon.ico"),
)


def send_notification(message: str, audio_name: str = "coin_flip", loop_count: int = 3, loop_interval: int = 1) -> None:
    _notification.message = message
    _notification._notification_audio = files.resource_path(f"assets/sounds/{audio_name}.wav")

    for _ in range(loop_count):
        _notification.send(False)
        time.sleep(loop_interval)
